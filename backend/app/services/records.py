"""Tamper-evident record creation: canonical payload -> SHA-256 -> ECDSA -> chain."""
from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import utcnow
from ..enums import CONCENTRATION_NOT_DETERMINABLE, DISCLAIMER
from ..models import Record, Sample, SigningKey, User
from .canonical import canonical_json, sha256_hex
from .scoring import analyze_sample
from .signing import (
    ALGORITHM,
    key_id_for,
    public_key_pem,
    sign_hash,
    signing_key_source,
)

BUNDLE_FORMAT = "fieldproof-record/1"


def ensure_signing_key(db: Session) -> SigningKey:
    """Register the active public key (private half never leaves the server)."""
    pem = public_key_pem()
    kid = key_id_for(pem)
    row = db.scalar(select(SigningKey).where(SigningKey.key_id == kid))
    if row is None:
        row = SigningKey(
            key_id=kid,
            algorithm=ALGORITHM,
            public_key_pem=pem,
            private_key_source=signing_key_source(),
            is_active=True,
        )
        db.add(row)
        db.flush()
    return row


def chain_tip(db: Session) -> Record | None:
    return db.scalar(
        select(Record).order_by(Record.created_at.desc(), Record.id.desc()).limit(1)
    )


def _iso(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat() + "Z"
    return str(value)


def _test_entry(test) -> dict[str, Any]:
    kit = test.kit
    payload = test.input_json or {}
    return {
        "test_id": test.id,
        "test_type": test.test_type,
        "kit_code": kit.code if kit else None,
        "kit_name": kit.name if kit else None,
        "kit_batch": test.kit_batch,
        "outcome_code": test.outcome_code,
        "outcome_label": test.outcome_label,
        "input": payload,
        "time_since_reaction_seconds": test.time_since_reaction_seconds,
        "image_sha256": test.image_sha256,
        "calibration": test.calibration_json,
        "reading": test.reading_json,
        "source": test.source,
        "is_override": bool(test.is_override),
        "override_reason": test.override_reason,
        "overridden_outcome_code": test.overridden_outcome_code,
        "entered_at": _iso(test.created_at),
        "entered_by": test.operator_id,
    }


def build_record_payload(
    db: Session, sample: Sample, operator: User, analysis: dict[str, Any]
) -> dict[str, Any]:
    tests = sorted(sample.tests, key=lambda t: (t.created_at, t.id))
    previous = chain_tip(db)

    kit_codes = [t.kit.code for t in tests if t.kit is not None]
    kit_batches = sorted({t.kit_batch for t in tests if t.kit_batch})
    calibrations = [
        {"test_id": t.id, "kit_code": t.kit.code if t.kit else None, **(t.calibration_json or {})}
        for t in tests
        if t.calibration_json
    ]
    image_sha = next(
        (t.image_sha256 for t in reversed(tests) if t.image_sha256),
        sample.photo_sha256,
    )

    return {
        "record_id": str(uuid.uuid4()),
        "sample_id": sample.id,
        "sample_code": sample.sample_code,
        "operator_id": operator.id,
        "operator_username": operator.username,
        "operator_badge": operator.badge_number,
        "kit_types": kit_codes,
        "kit_batches": kit_batches,
        "tests": [_test_entry(t) for t in tests],
        "analysis": analysis,
        "status": analysis["status"],
        "calibration": calibrations or None,
        "gps": {
            "latitude": sample.gps_lat,
            "longitude": sample.gps_lon,
            "accuracy_m": sample.gps_accuracy_m,
            "mock_location": bool(sample.gps_mock_location),
        },
        "device_timestamp": _iso(sample.device_timestamp),
        "server_timestamp": _iso(utcnow()),
        "image_sha256": image_sha,
        "previous_record_hash": previous.record_hash if previous else None,
        "engine_version": settings.engine_version,
        "disclaimer": DISCLAIMER,
        "concentration": analysis["concentration"],
        "correction_of": None,
    }


def create_record(
    db: Session, sample: Sample, operator: User, *, ip_address: str | None = None
) -> Record:
    """Finalise a sample into an append-only, signed, hash-chained record."""
    from ..audit import audit

    if not sample.tests:
        raise ValueError("cannot finalise a sample with no tests")

    analysis = analyze_sample(db, sample)
    payload = build_record_payload(db, sample, operator, analysis)
    canonical = canonical_json(payload)
    digest = sha256_hex(canonical.encode("utf-8"))

    key = ensure_signing_key(db)
    signature = sign_hash(digest)
    top = analysis.get("top_match") or {}

    record = Record(
        id=payload["record_id"],
        sample_id=sample.id,
        operator_id=operator.id,
        status=analysis["status"],
        kit_codes=payload["kit_types"],
        kit_batches=payload["kit_batches"],
        kit_codes_csv=",".join(sorted(set(payload["kit_types"]))),
        top_substance_code=top.get("code"),
        top_substance_name=top.get("name"),
        test_inputs=payload["tests"],
        analysis=analysis,
        calibration=payload["calibration"],
        gps_lat=sample.gps_lat,
        gps_lon=sample.gps_lon,
        gps_accuracy_m=sample.gps_accuracy_m,
        gps_mock_location=bool(sample.gps_mock_location),
        device_timestamp=sample.device_timestamp,
        server_timestamp=utcnow(),
        image_sha256=payload["image_sha256"],
        previous_record_hash=payload["previous_record_hash"],
        record_hash=digest,
        canonical_json=canonical,
        signature=signature,
        public_key_id=key.key_id,
        engine_version=settings.engine_version,
        disclaimer=DISCLAIMER,
        correction_of=None,
    )
    db.add(record)
    sample.status = "SIGNED"
    audit(
        db,
        action="record.create",
        actor_id=operator.id,
        actor_username=operator.username,
        actor_role=operator.role,
        entity_type="record",
        entity_id=record.id,
        detail={
            "sample_id": sample.id,
            "record_hash": digest,
            "status": record.status,
            "previous_record_hash": payload["previous_record_hash"],
        },
        ip_address=ip_address,
    )
    db.flush()
    return record


def record_bundle(record: Record) -> dict[str, Any]:
    """Everything needed to verify the record offline."""
    from ..models import SigningKey

    pem = None
    # resolved by the caller when a session is available; kept optional here
    return {
        "format": BUNDLE_FORMAT,
        "record": json.loads(record.canonical_json),
        "canonical_json": record.canonical_json,
        "record_hash": record.record_hash,
        "signature": record.signature,
        "public_key_id": record.public_key_id,
        "public_key_pem": pem,
        "disclaimer": record.disclaimer,
        "concentration_note": CONCENTRATION_NOT_DETERMINABLE,
    }


def bundle_with_key(db: Session, record: Record) -> dict[str, Any]:
    from ..models import SigningKey

    bundle = record_bundle(record)
    if record.public_key_id:
        row = db.scalar(
            select(SigningKey).where(SigningKey.key_id == record.public_key_id)
        )
        if row:
            bundle["public_key_pem"] = row.public_key_pem
    return bundle
