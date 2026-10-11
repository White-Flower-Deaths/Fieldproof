from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .models import AuditLog


def audit(
    db: Session,
    *,
    action: str,
    actor_id: str | None = None,
    actor_username: str | None = None,
    actor_role: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
    commit: bool = False,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail or {},
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
    else:
        db.flush()
    return entry
