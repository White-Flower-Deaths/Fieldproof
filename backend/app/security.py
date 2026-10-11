"""Password hashing (argon2) and JWT issuing/verification for API auth.

NOTE: this is *session* auth. The ECDSA P-256 record-signing key is a separate
key held only on the server (see services/signing.py in step 3).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from .config import settings

_hasher = PasswordHasher(time_cost=2, memory_cost=64 * 1024, parallelism=2)


class TokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception:  # noqa: BLE001 - never leak hash internals
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:  # noqa: BLE001
        return False


def create_access_token(
    *,
    user_id: str,
    username: str,
    role: str,
    expires_minutes: int | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    minutes = expires_minutes or settings.access_token_expire_minutes
    payload: dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "role": role,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=minutes),
        "iss": "fieldproof",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer="fieldproof",
            options={"require": ["exp", "sub", "role"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Session expired. Please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid session token.") from exc
