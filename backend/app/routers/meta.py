from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from ..config import settings
from ..database import utcnow
from ..deps import DbSession, RequireAdmin
from ..models import AuditLog, Kit, SigningKey, User
from ..schemas import HealthOut, KitOut, KitOutcomeOut, MetaOut, UserOut
from ..enums import (
    APPEARANCE,
    CONCENTRATION_NOT_DETERMINABLE,
    DISCLAIMER,
    RESULT_STATUS,
    ROLES,
    TEST_TYPE,
)

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthOut)
def health(db: DbSession) -> HealthOut:
    try:
        db.execute(select(1))
        db_status = "ok"
    except Exception:  # noqa: BLE001
        db_status = "error"
    return HealthOut(
        status="ok" if db_status == "ok" else "degraded",
        database=db_status,
        version=settings.engine_version,
        time=utcnow(),
    )


@router.get("/meta", response_model=MetaOut)
def meta() -> MetaOut:
    return MetaOut(
        app_name=settings.app_name,
        environment=settings.environment,
        engine_version=settings.engine_version,
        disclaimer=DISCLAIMER,
        concentration_note=CONCENTRATION_NOT_DETERMINABLE,
        roles=list(ROLES),
        appearance_options=list(APPEARANCE),
        test_types=list(TEST_TYPE),
        result_statuses=list(RESULT_STATUS),
        demo_mode_default=settings.seed_demo,
    )


@router.get("/kits", response_model=list[KitOut])
def list_kits(db: DbSession) -> list[KitOut]:
    """Reference data for the entry wizard: active kits with their outcomes."""
    rows = db.scalars(
        select(Kit).where(Kit.is_active.is_(True)).order_by(Kit.name)
    ).all()
    return [
        KitOut(
            code=k.code,
            name=k.name,
            test_type=k.test_type,
            manufacturer=k.manufacturer,
            description=k.description,
            instructions=k.instructions,
            reaction_time_seconds=k.reaction_time_seconds,
            requires_photo=k.requires_photo,
            is_demo=k.is_demo,
            source_citation=k.source_citation,
            outcomes=[
                KitOutcomeOut(
                    code=o.code,
                    label=o.label,
                    hex=o.hex,
                    interpretation=o.interpretation,
                    sort_order=o.sort_order,
                )
                for o in k.outcomes
            ],
        )
        for k in rows
    ]


# --------------------------------------------------------------------------- #
# Admin (kept small in step 1; full CRUD lands in step 8)
# --------------------------------------------------------------------------- #
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/users", response_model=list[UserOut])
def list_users(admin: RequireAdmin, db: DbSession) -> list[UserOut]:
    rows = db.scalars(select(User).order_by(User.username)).all()
    return [UserOut.model_validate(r) for r in rows]


@admin_router.get("/audit-log")
def list_audit_log(
    admin: RequireAdmin,
    db: DbSession,
    limit: int = 100,
    offset: int = 0,
    entity_id: str | None = None,
) -> dict:
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    rows = db.scalars(query.offset(offset).limit(min(limit, 500))).all()
    return {
        "total": len(rows),
        "items": [
            {
                "id": r.id,
                "actor": r.actor_username,
                "role": r.actor_role,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "detail": r.detail,
                "ip": r.ip_address,
                "created_at": r.created_at.isoformat() + "Z",
            }
            for r in rows
        ],
    }


@admin_router.get("/signing-keys")
def list_signing_keys(admin: RequireAdmin, db: DbSession) -> dict:
    rows = db.scalars(select(SigningKey).order_by(SigningKey.created_at.desc())).all()
    return {
        "items": [
            {
                "key_id": r.key_id,
                "algorithm": r.algorithm,
                "public_key_pem": r.public_key_pem,
                "private_key_source": r.private_key_source,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() + "Z",
            }
            for r in rows
        ]
    }
