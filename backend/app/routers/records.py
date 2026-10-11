from __future__ import annotations

import csv
import io
import json
import math

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from ..audit import audit
from ..deps import DbSession, RequireOfficer, CurrentUser, client_ip
from ..enums import CONCENTRATION_NOT_DETERMINABLE, DISCLAIMER
from ..models import AuditLog, Record, Sample, User
from ..schemas import RecordListOut, RecordSummary
from ..services.images import load_image, save_image
from ..services.records import bundle_with_key
from ..services.verify import verify_record, verify_payload

router = APIRouter(prefix="/records", tags=["records"])
verify_router = APIRouter(prefix="/verify", tags=["verify"])
images_router = APIRouter(prefix="/images", tags=["images"])

CSV_COLUMNS = [
    "record_id",
    "sample_code",
    "status",
    "top_substance",
    "operator",
    "kit_codes",
    "server_timestamp",
    "latitude",
    "longitude",
    "accuracy_m",
    "image_sha256",
    "record_hash",
    "previous_record_hash",
    "public_key_id",
    "engine_version",
    "disclaimer",
    "concentration_note",
]


def _summary(
    record: Record,
    sample_code: str | None = None,
    operator_username: str | None = None,
) -> RecordSummary:
    return RecordSummary(
        id=record.id,
        sample_id=record.sample_id,
        sample_code=sample_code or record.sample_id,
        status=record.status,
        operator_id=record.operator_id,
        operator_username=operator_username,
        kit_codes=list(record.kit_codes or []),
        top_substance_code=record.top_substance_code,
        top_substance_name=record.top_substance_name,
        server_timestamp=record.server_timestamp,
        record_hash=record.record_hash,
        previous_record_hash=record.previous_record_hash,
        public_key_id=record.public_key_id,
        gps_lat=record.gps_lat,
        gps_lon=record.gps_lon,
        gps_accuracy_m=record.gps_accuracy_m,
        gps_mock_location=record.gps_mock_location,
        image_sha256=record.image_sha256,
        engine_version=record.engine_version,
        disclaimer=record.disclaimer,
    )


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def _filtered_query(
    db,
    *,
    q: str | None,
    status_filter: str | None,
    operator: str | None,
    kit: str | None,
    substance: str | None,
    date_from: str | None,
    date_to: str | None,
):
    query = select(Record, Sample.sample_code, User.username).join(
        Sample, Record.sample_id == Sample.id
    ).join(User, Record.operator_id == User.id)

    if q:
        needle = q.strip()
        like = f"%{needle}%"
        query = query.where(
            (Record.id.like(like))
            | (Record.sample_id.like(like))
            | (Sample.sample_code.like(like))
            | (Sample.id.like(like))
        )
    if status_filter:
        query = query.where(Record.status == status_filter)
    if operator:
        like = f"%{operator.strip()}%"
        query = query.where((User.username.like(like)) | (User.id.like(like)))
    if kit:
        query = query.where(Record.kit_codes_csv.like(f"%{kit.strip()}%"))
    if substance:
        like = f"%{substance.strip()}%"
        query = query.where(
            (Record.top_substance_code.like(like))
            | (Record.top_substance_name.like(like))
        )
    if date_from:
        query = query.where(Record.server_timestamp >= date_from)
    if date_to:
        query = query.where(Record.server_timestamp <= date_to + "T23:59:59")
    return query


@router.get("", response_model=RecordListOut)
def list_records(
    user: CurrentUser,
    db: DbSession,
    q: str | None = None,
    status_filter: str | None = None,
    operator: str | None = None,
    kit: str | None = None,
    substance: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float | None = None,
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "server_timestamp",
    sort_dir: str = "desc",
) -> RecordListOut:
    query = _filtered_query(
        db,
        q=q,
        status_filter=status_filter,
        operator=operator,
        kit=kit,
        substance=substance,
        date_from=date_from,
        date_to=date_to,
    )
    rows = db.execute(query).all()

    if lat is not None and lon is not None and radius_km:
        rows = [
            r
            for r in rows
            if r.Record.gps_lat is not None
            and r.Record.gps_lon is not None
            and _haversine_km(lat, lon, r.Record.gps_lat, r.Record.gps_lon)
            <= radius_km
        ]

    sort_column = {
        "server_timestamp": lambda r: r.Record.server_timestamp,
        "status": lambda r: r.Record.status,
        "sample_code": lambda r: r.sample_code,
        "record_hash": lambda r: r.Record.record_hash,
    }.get(sort_by, lambda r: r.Record.server_timestamp)
    rows.sort(key=sort_column, reverse=(sort_dir.lower() == "desc"))

    total = len(rows)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    start = (page - 1) * page_size
    slice_ = rows[start : start + page_size]

    return RecordListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            RecordSummary(
                id=r.Record.id,
                sample_id=r.Record.sample_id,
                sample_code=r.sample_code,
                status=r.Record.status,
                operator_id=r.Record.operator_id,
                operator_username=r.username,
                operator_badge=None,
                kit_codes=list(r.Record.kit_codes or []),
                top_substance_code=r.Record.top_substance_code,
                top_substance_name=r.Record.top_substance_name,
                server_timestamp=r.Record.server_timestamp,
                record_hash=r.Record.record_hash,
                previous_record_hash=r.Record.previous_record_hash,
                public_key_id=r.Record.public_key_id,
                gps_lat=r.Record.gps_lat,
                gps_lon=r.Record.gps_lon,
                gps_accuracy_m=r.Record.gps_accuracy_m,
                gps_mock_location=r.Record.gps_mock_location,
                image_sha256=r.Record.image_sha256,
                engine_version=r.Record.engine_version,
                disclaimer=r.Record.disclaimer,
            )
            for r in slice_
        ],
    )


@router.get("/export")
def export_list_csv(
    user: CurrentUser,
    db: DbSession,
    request: Request,
    q: str | None = None,
    status_filter: str | None = None,
    operator: str | None = None,
    kit: str | None = None,
    substance: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> StreamingResponse:
    query = _filtered_query(
        db,
        q=q,
        status_filter=status_filter,
        operator=operator,
        kit=kit,
        substance=substance,
        date_from=date_from,
        date_to=date_to,
    )
    rows = db.execute(query).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for r in rows:
        writer.writerow(
            [
                r.Record.id,
                r.sample_code,
                r.Record.status,
                r.Record.top_substance_name or "",
                r.username,
                ",".join(r.Record.kit_codes or []),
                r.Record.server_timestamp.isoformat() + "Z",
                r.Record.gps_lat,
                r.Record.gps_lon,
                r.Record.gps_accuracy_m,
                r.Record.image_sha256 or "",
                r.Record.record_hash,
                r.Record.previous_record_hash or "",
                r.Record.public_key_id or "",
                r.Record.engine_version,
                r.Record.disclaimer,
                CONCENTRATION_NOT_DETERMINABLE,
            ]
        )
    audit(
        db,
        action="record.export",
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        entity_type="record_list",
        entity_id=None,
        detail={"format": "csv", "rows": len(rows)},
        ip_address=client_ip(request),
        commit=True,
    )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="fieldproof-records.csv"'},
    )


def _load_record(db, record_id: str) -> Record:
    record = db.get(Record, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found.")
    return record


@router.get("/{record_id}")
def get_record(record_id: str, user: CurrentUser, db: DbSession, request: Request) -> dict:
    record = _load_record(db, record_id)
    sample = db.get(Sample, record.sample_id)
    operator = db.get(User, record.operator_id)
    bundle = bundle_with_key(db, record)
    verification = verify_record(db, record)
    audit(
        db,
        action="record.view",
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        entity_type="record",
        entity_id=record.id,
        ip_address=client_ip(request),
        commit=True,
    )
    trail = db.scalars(
        select(AuditLog)
        .where(
            (AuditLog.entity_id == record.id)
            | (AuditLog.entity_id == record.sample_id)
            | (AuditLog.entity_id.in_([t["test_id"] for t in record.test_inputs or []]))
        )
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    ).all()
    return {
        "summary": _summary(
            record,
            sample.sample_code if sample else None,
            operator.username if operator else None,
        ).model_dump(),
        "operator": (
            {
                "id": operator.id,
                "username": operator.username,
                "full_name": operator.full_name,
                "badge_number": operator.badge_number,
                "role": operator.role,
            }
            if operator
            else None
        ),
        "sample": (
            {
                "id": sample.id,
                "sample_code": sample.sample_code,
                "appearance": sample.appearance,
                "colour": sample.colour,
                "approximate_weight": sample.approximate_weight,
                "notes": sample.notes,
                "gps_lat": sample.gps_lat,
                "gps_lon": sample.gps_lon,
                "gps_accuracy_m": sample.gps_accuracy_m,
            }
            if sample
            else None
        ),
        "tests": record.test_inputs,
        "analysis": record.analysis,
        "calibration": record.calibration,
        "bundle": bundle,
        "verification": verification,
        "audit_trail": [
            {
                "id": a.id,
                "action": a.action,
                "actor": a.actor_username,
                "role": a.actor_role,
                "detail": a.detail,
                "ip": a.ip_address,
                "created_at": a.created_at.isoformat() + "Z",
            }
            for a in trail
        ],
    }


@router.get("/{record_id}/export")
def export_record(
    record_id: str,
    user: CurrentUser,
    db: DbSession,
    request: Request,
    format: str = "json",
) -> StreamingResponse:
    record = _load_record(db, record_id)
    fmt = format.lower()
    if fmt not in {"json", "csv"}:
        raise HTTPException(
            status_code=422,
            detail=f"Format '{format}' is not available yet (json and csv are).",
        )

    audit(
        db,
        action="record.export",
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        entity_type="record",
        entity_id=record.id,
        detail={"format": fmt},
        ip_address=client_ip(request),
        commit=True,
    )

    if fmt == "json":
        bundle = bundle_with_key(db, record)
        body = json.dumps(bundle, indent=2, ensure_ascii=False)
        return StreamingResponse(
            iter([body]),
            media_type="application/json",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="fieldproof-{record.id}.json"'
                )
            },
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["field", "value"])
    payload = json.loads(record.canonical_json)
    for key in sorted(payload):
        value = payload[key]
        writer.writerow([key, json.dumps(value, ensure_ascii=False)])
    writer.writerow(["record_hash", record.record_hash])
    writer.writerow(["signature", record.signature])
    writer.writerow(["public_key_id", record.public_key_id])
    # Hard rule: every export carries the disclaimer and the exact
    # concentration line, even when the payload's own `concentration` holds a
    # lab-entered purity value.
    writer.writerow(["disclaimer", record.disclaimer])
    writer.writerow(["concentration_note", CONCENTRATION_NOT_DETERMINABLE])
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="fieldproof-{record.id}.csv"'
        },
    )


# --------------------------------------------------------------------------- #
# verification (record JSON + optional image)
# --------------------------------------------------------------------------- #
@verify_router.post("")
async def verify_upload(
    user: CurrentUser,
    db: DbSession,
    record: UploadFile = File(...),
    image: UploadFile | None = File(None),
) -> dict:
    raw = await record.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Record file is not valid JSON: {exc}",
        ) from exc

    image_bytes = await image.read() if image is not None else None
    result = verify_payload(db, payload, image_bytes)
    return result


# --------------------------------------------------------------------------- #
# images: stored unmodified, named by SHA-256
# --------------------------------------------------------------------------- #
@images_router.post("", status_code=status.HTTP_201_CREATED)
async def upload_image(user: CurrentUser, file: UploadFile = File(...)) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    digest, filename = save_image(data, file.content_type)
    return {
        "sha256": digest,
        "filename": filename,
        "size_bytes": len(data),
        "content_type": file.content_type,
    }


@images_router.get("/{image_sha256}")
def get_image(image_sha256: str, user: CurrentUser):
    from fastapi.responses import Response

    data = load_image(image_sha256)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found.")
    media = "image/jpeg" if data[:2] == b"\xff\xd8" else "application/octet-stream"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        media = "image/png"
    return Response(content=data, media_type=media)
