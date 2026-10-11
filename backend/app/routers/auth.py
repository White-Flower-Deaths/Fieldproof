from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from ..audit import audit
from ..config import settings
from ..database import utcnow
from ..deps import CurrentUser, DbSession, client_ip
from ..models import User
from ..rate_limit import login_limiter
from ..schemas import LoginRequest, MessageOut, RegisterRequest, TokenResponse, UserOut
from ..security import (
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

USERNAME_RE = re.compile(r"[A-Za-z0-9._-]+\Z")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    ip = client_ip(request)
    key = f"{ip}:{payload.username.lower()}"
    allowed, retry_after = login_limiter.check(key)
    if not allowed:
        audit(
            db,
            action="auth.login.rate_limited",
            actor_username=payload.username,
            detail={"retry_after": retry_after},
            ip_address=ip,
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Too many sign-in attempts. Try again in {retry_after} seconds."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    user = db.scalar(select(User).where(func.lower(User.username) == payload.username.lower()))

    if user is None or not user.is_active or not verify_password(
        user.password_hash, payload.password
    ):
        login_limiter.record_failure(key)
        audit(
            db,
            action="auth.login.failed",
            actor_id=user.id if user else None,
            actor_username=payload.username,
            actor_role=user.role if user else None,
            detail={"reason": "invalid_credentials" if user else "unknown_user"},
            ip_address=ip,
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect operator ID or password.",
        )

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    login_limiter.reset(key)
    user.last_login_at = utcnow()
    audit(
        db,
        action="auth.login.success",
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        ip_address=ip,
        commit=True,
    )

    token = create_access_token(user_id=user.id, username=user.username, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register(payload: RegisterRequest, request: Request, db: DbSession) -> TokenResponse:
    ip = client_ip(request)
    key = f"register:{ip}"
    allowed, retry_after = login_limiter.check(key)
    if not allowed:
        audit(
            db,
            action="auth.register.rate_limited",
            actor_username=payload.username,
            detail={"retry_after": retry_after},
            ip_address=ip,
            commit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many sign-up attempts. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    username = payload.username.strip()
    password = payload.password
    error: str | None = None
    if not 3 <= len(username) <= 32 or not USERNAME_RE.match(username):
        error = (
            "Operator ID must be 3-32 characters: letters, digits, dot, "
            "dash or underscore."
        )
    elif not 8 <= len(password) <= 128:
        error = "Password must be 8-128 characters."

    if error is None:
        existing = db.scalar(
            select(User).where(func.lower(User.username) == username.lower())
        )
        if existing is not None:
            login_limiter.record_failure(key)
            audit(
                db,
                action="auth.register.rejected",
                actor_username=username,
                detail={"reason": "username_taken"},
                ip_address=ip,
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="That operator ID is already taken.",
            )
    else:
        login_limiter.record_failure(key)
        audit(
            db,
            action="auth.register.rejected",
            actor_username=username,
            detail={"reason": "validation"},
            ip_address=ip,
            commit=True,
        )
        raise HTTPException(status_code=422, detail=error)

    # Self-registration can only ever mint field-officer accounts; LAB/ADMIN
    # roles are provisioned by an administrator.
    user = User(
        username=username,
        role="OFFICER",
        password_hash=hash_password(password),
        last_login_at=utcnow(),
    )
    db.add(user)
    db.flush()
    login_limiter.reset(key)
    audit(
        db,
        action="auth.register",
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        detail={"role": user.role},
        ip_address=ip,
        commit=True,
    )
    token = create_access_token(user_id=user.id, username=user.username, role=user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/logout", response_model=MessageOut)
def logout(user: CurrentUser, db: DbSession, request: Request) -> MessageOut:
    audit(
        db,
        action="auth.logout",
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        ip_address=client_ip(request),
        commit=True,
    )
    return MessageOut(detail="Signed out.")
