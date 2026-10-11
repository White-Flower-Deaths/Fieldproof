from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from ..audit import audit
from ..deps import DbSession, RequireOfficer, client_ip
from ..models import Kit, Record, Sample, SampleTest, TestOutcome
from ..schemas import SampleCreate, SampleOut, SampleTestOut, TestCreate, TestCreateOut
from ..services.records import bundle_with_key, create_record
from ..services.scoring import analyze_sample

router = APIRouter(prefix="/samples", tags=["samples"])

INPUT_REQUIRED = {
    "SPECTROMETER": ("library_match", "match_score"),
    "LAB_CONFIRMATORY": ("method", "compound"),
}


def _next_sample_code(db) -> str:
    import datetime as _dt

    day = _dt.datetime.utcnow().strftime("%Y%m%d")
    like = f"S-{day}-%"
    count = db.scalar(
        select(func.count()).select_from(Sample).where(Sample.sample_code.like(like))
    )
    return f"S-{day}-{(count or 0) + 1:04d}"


def _get_sample(db, sample_id: str) -> Sample:
    sample = db.get(Sample, sample_id)
    if sample is None:
        raise HTTPException(status_code=404, detail="Sample not found.")
    return sample


@router.post("", response_model=SampleOut, status_code=status.HTTP_201_CREATED)
def create_sample(
    payload: SampleCreate, request: Request, user: RequireOfficer, db: DbSession
) -> SampleOut:
    sample = Sample(
        sample_code=_next_sample_code(db),
        operator_id=user.id,
        appearance=payload.appearance,
        colour=payload.colour,
        approximate_weight=payload.approximate_weight,
        notes=payload.notes,
        photo_sha256=payload.photo_sha256,
        gps_lat=payload.gps_lat,
        gps_lon=payload.gps_lon,
        gps_accuracy_m=payload.gps_accuracy_m,
        gps_mock_location=payload.gps_mock_location,
        device_timestamp=payload.device_timestamp,
        status="OPEN",
    )
    db.add(sample)
    audit(
        db,
        action="sample.create",
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        entity_type="sample",
        entity_id=sample.id,
        detail={"appearance": payload.appearance, "gps_mock": payload.gps_mock_location},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(sample)
    return SampleOut.model_validate(sample)


@router.get("", response_model=list[SampleOut])
def list_samples(
    user: RequireOfficer,
    db: DbSession,
    mine: bool = False,
    q: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[SampleOut]:
    query = select(Sample)
    if mine:
        query = query.where(Sample.operator_id == user.id)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(Sample.sample_code.like(like))
    if status_filter:
        query = query.where(Sample.status == status_filter)
    rows = db.scalars(
        query.order_by(Sample.created_at.desc()).limit(min(limit, 200))
    ).all()
    return [SampleOut.model_validate(r) for r in rows]


@router.get("/{sample_id}", response_model=SampleOut)
def get_sample(sample_id: str, user: RequireOfficer, db: DbSession) -> SampleOut:
    return SampleOut.model_validate(_get_sample(db, sample_id))


@router.post("/{sample_id}/tests", response_model=TestCreateOut)
def add_test(
    sample_id: str,
    payload: TestCreate,
    request: Request,
    user: RequireOfficer,
    db: DbSession,
) -> TestCreateOut:
    sample = _get_sample(db, sample_id)
    if sample.status == "SIGNED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This sample has already been finalised; records are append-only.",
        )

    if payload.test_type == "LAB_CONFIRMATORY" and user.role not in {"LAB", "ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Laboratory confirmatory results may only be entered by LAB or ADMIN users.",
        )

    kit = None
    if payload.kit_code:
        kit = db.scalar(select(Kit).where(Kit.code == payload.kit_code))
        if kit is None or not kit.is_active:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown or inactive kit '{payload.kit_code}'.",
            )
        if kit.test_type != payload.test_type:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Kit '{kit.code}' is a {kit.test_type} kit and cannot be used "
                    f"as {payload.test_type}."
                ),
            )
    elif payload.test_type in {"COLOUR_REAGENT", "IMMUNOASSAY_STRIP"}:
        raise HTTPException(
            status_code=422,
            detail=f"kit_code is required for {payload.test_type} tests.",
        )

    outcome = None
    if payload.outcome_code:
        if kit is None:
            raise HTTPException(
                status_code=422,
                detail="outcome_code requires a kit_code.",
            )
        outcome = db.scalar(
            select(TestOutcome).where(
                TestOutcome.kit_id == kit.id, TestOutcome.code == payload.outcome_code
            )
        )
        if outcome is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Outcome '{payload.outcome_code}' is not part of kit '{kit.code}'."
                ),
            )

    reading = payload.reading or {}
    if payload.test_type in {"COLOUR_REAGENT", "IMMUNOASSAY_STRIP"}:
        if outcome is None and not reading.get("inconclusive"):
            raise HTTPException(
                status_code=422,
                detail=(
                    "An observed outcome is required (choose an outcome_code, or mark "
                    "the camera reading as inconclusive)."
                ),
            )

    for field_name in INPUT_REQUIRED.get(payload.test_type, ()):
        if payload.input.get(field_name) in (None, ""):
            raise HTTPException(
                status_code=422,
                detail=f"'{field_name}' is required for {payload.test_type} tests.",
            )

    if payload.is_override and not (payload.override_reason or "").strip():
        raise HTTPException(
            status_code=422,
            detail="An override requires a reason, which is stored in the audit trail.",
        )

    test = SampleTest(
        sample_id=sample.id,
        kit_id=kit.id if kit else None,
        operator_id=user.id,
        test_type=payload.test_type,
        kit_batch=payload.kit_batch,
        outcome_id=outcome.id if outcome else None,
        outcome_code=outcome.code if outcome else None,
        outcome_label=outcome.label if outcome else None,
        input_json=payload.input,
        time_since_reaction_seconds=payload.time_since_reaction_seconds,
        image_sha256=payload.image_sha256,
        calibration_json=payload.calibration,
        reading_json=payload.reading,
        source=payload.source,
        is_override=payload.is_override,
        override_reason=payload.override_reason,
        overridden_outcome_code=payload.overridden_outcome_code,
    )
    db.add(test)

    action = "test.override" if payload.is_override else "test.create"
    audit(
        db,
        action=action,
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        entity_type="sample_test",
        entity_id=test.id,
        detail={
            "sample_id": sample.id,
            "test_type": payload.test_type,
            "kit": payload.kit_code,
            "outcome": test.outcome_code,
            "override_reason": payload.override_reason,
            "overridden_outcome_code": payload.overridden_outcome_code,
        },
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(test)
    analysis = analyze_sample(db, sample)
    return TestCreateOut(test=SampleTestOut.model_validate(test), analysis=analysis)


@router.get("/{sample_id}/analysis")
def get_analysis(sample_id: str, user: RequireOfficer, db: DbSession) -> dict:
    sample = _get_sample(db, sample_id)
    return analyze_sample(db, sample)


@router.post("/{sample_id}/finalize")
def finalize(
    sample_id: str,
    request: Request,
    user: RequireOfficer,
    db: DbSession,
) -> dict:
    sample = _get_sample(db, sample_id)
    if not sample.tests:
        raise HTTPException(
            status_code=422,
            detail="Add at least one test before finalising.",
        )
    existing = db.scalar(
        select(func.count()).select_from(Record).where(Record.sample_id == sample.id)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This sample has already been finalised.",
        )

    try:
        record = create_record(db, sample, user, ip_address=client_ip(request))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(record)

    stored = db.get(Record, record.id)
    return {
        "record": {
            "id": stored.id,
            "sample_id": stored.sample_id,
            "status": stored.status,
            "record_hash": stored.record_hash,
            "previous_record_hash": stored.previous_record_hash,
            "signature": stored.signature,
            "public_key_id": stored.public_key_id,
            "server_timestamp": stored.server_timestamp.isoformat() + "Z",
        },
        "bundle": bundle_with_key(db, stored),
        "analysis": stored.analysis,
        "disclaimer": stored.disclaimer,
    }
