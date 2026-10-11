"""Seed eight demo samples/records through the real services.

Every record is created exactly like a live entry would be: the router
functions in ``app.routers.samples`` build the sample/tests, the scoring
engine computes the analysis, and ``create_record`` produces canonical JSON,
its SHA-256, an ECDSA P-256 signature and the hash-chain link. Nothing is
hand-written into the database and no signature is faked. Camera records go
through the real image pipeline (``POST /api/images/analyze``) on the
synthetic scenes in ``docs/images/``.

Run from ``backend/``:

    python -m app.seed_demo            # add any missing demo records
    python -m app.seed_demo --reset    # rebuild reference data first
                                       # (fresh chain -> full timestamp spread)

The eight records cover NO_MATCH, WEAK_PRESUMPTIVE, PRESUMPTIVE,
STRONG_PRESUMPTIVE, INCONCLUSIVE (failed camera reading), a close-call
"possible mixture or ambiguous" record, a camera CAPTURE record and
CONFIRMED_BY_LAB (lab confirmatory entry by lab1). Timestamps are spread
across the last week; on a database whose chain already contains newer
records the server timestamps are clamped to the chain tip instead (the
chain requires non-decreasing timestamps) and a hint to use ``--reset`` is
printed. Each sample carries a ``[seed_demo]`` note so re-runs skip records
that already exist.

Every seeded record is re-verified through ``verify_record`` before the
script reports success; any status mismatch or verification FAIL exits 1.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import func, select
from starlette.datastructures import Headers, UploadFile

from .database import SessionFactory, init_db
from .enums import CONCENTRATION_NOT_DETERMINABLE
from .models import Record, Sample, SampleTest, User
from .routers.imaging import analyze_uploaded_image
from .routers.samples import add_test, create_sample, finalize
from .schemas import SampleCreate, TestCreate
from .seed import reset_database, seed_demo as seed_reference
from .services import records as records_mod
from .services import scoring as scoring_mod
from .services.images import load_image, save_image
from .services.verify import verify_record

MARKER = "[seed_demo]"
GUIDE_ROI = {"x": 0.12, "y": 0.31, "w": 0.26, "h": 0.38}
SCENES_DIR = Path(__file__).resolve().parents[2] / "docs" / "images"
AMBIGUOUS_FLAG = "Possible mixture or ambiguous: refer to laboratory"
INCONCLUSIVE_FLAG = "1 inconclusive test reading(s) excluded from scoring."
LAB_REFERENCE = "FS-2026-0431"

_ORIG_UTCNOW = (records_mod.utcnow, scoring_mod.utcnow)


class _FakeRequest:
    """Stand-in for FastAPI's Request - only client_ip() touches it."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.client = SimpleNamespace(host="127.0.0.1")


@contextmanager
def _clock(at: datetime):
    """Run the record/scoring clock at ``at`` (chain-safe backdating)."""
    records_mod.utcnow = lambda: at
    scoring_mod.utcnow = lambda: at
    try:
        yield
    finally:
        records_mod.utcnow, scoring_mod.utcnow = _ORIG_UTCNOW


def _at(now: datetime, days_ago: int, hour: int, minute: int) -> datetime:
    return (now - timedelta(days=days_ago)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


def _scenarios(now: datetime) -> list[dict]:
    """Creation order == ascending desired server timestamps (chain order)."""
    return [
        {
            "slug": "no-match",
            "label": "NO_MATCH - single MECKE blue-grey (no published expectation)",
            "expected": "NO_MATCH",
            "flags": [],
            "operator": "officer1",
            "ts": _at(now, 6, 9, 15),
            "appearance": "POWDER",
            "colour": "pale yellow",
            "weight": "0.4 g",
            "gps": (51.5074, -0.1278, 9.0),
            "tests": [
                {
                    "key": ("COLOUR_REAGENT", "MECKE", "BLUE_GREY", "MANUAL"),
                    "user": "officer1",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MECKE",
                        "kit_batch": "DEMO-01",
                        "outcome_code": "BLUE_GREY",
                        "time_since_reaction_seconds": 120,
                    },
                },
            ],
        },
        {
            "slug": "weak-strip",
            "label": "WEAK_PRESUMPTIVE - single fentanyl strip positive",
            "expected": "WEAK_PRESUMPTIVE",
            "flags": [],
            "operator": "officer2",
            "ts": _at(now, 5, 10, 40),
            "appearance": "CRYSTALS",
            "colour": "white",
            "weight": "0.2 g",
            "gps": (51.5090, -0.1301, 12.0),
            "tests": [
                {
                    "key": ("IMMUNOASSAY_STRIP", "FENT_STRIP", "POSITIVE", "MANUAL"),
                    "user": "officer2",
                    "payload": {
                        "test_type": "IMMUNOASSAY_STRIP",
                        "kit_code": "FENT_STRIP",
                        "kit_batch": "DEMO-02",
                        "outcome_code": "POSITIVE",
                        "time_since_reaction_seconds": 300,
                    },
                },
            ],
        },
        {
            "slug": "presumptive-meth",
            "label": "PRESUMPTIVE - MARQUIS orange-red + MECKE no-reaction",
            "expected": "PRESUMPTIVE",
            "flags": [],
            "operator": "officer1",
            "ts": _at(now, 4, 8, 5),
            "appearance": "CRYSTALS",
            "colour": "clear",
            "weight": "0.6 g",
            "gps": (51.5063, -0.1240, 7.5),
            "tests": [
                {
                    "key": ("COLOUR_REAGENT", "MARQUIS", "ORANGE_RED", "MANUAL"),
                    "user": "officer1",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MARQUIS",
                        "kit_batch": "DEMO-03",
                        "outcome_code": "ORANGE_RED",
                        "time_since_reaction_seconds": 120,
                    },
                },
                {
                    "key": ("COLOUR_REAGENT", "MECKE", "NO_REACTION_ORANGE", "MANUAL"),
                    "user": "officer1",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MECKE",
                        "kit_batch": "DEMO-03",
                        "outcome_code": "NO_REACTION_ORANGE",
                        "time_since_reaction_seconds": 90,
                    },
                },
            ],
        },
        {
            "slug": "strong-mdma",
            "label": "STRONG_PRESUMPTIVE - MARQUIS purple-black + MECKE purple",
            "expected": "STRONG_PRESUMPTIVE",
            "flags": [],
            "operator": "officer1",
            "ts": _at(now, 3, 14, 20),
            "appearance": "PILL_TABLET",
            "colour": "beige",
            "weight": "0.3 g",
            "gps": (51.5118, -0.1290, 5.5),
            "tests": [
                {
                    "key": ("COLOUR_REAGENT", "MARQUIS", "PURPLE_BLACK", "MANUAL"),
                    "user": "officer1",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MARQUIS",
                        "kit_batch": "DEMO-04",
                        "outcome_code": "PURPLE_BLACK",
                        "time_since_reaction_seconds": 120,
                    },
                },
                {
                    "key": ("COLOUR_REAGENT", "MECKE", "PURPLE", "MANUAL"),
                    "user": "officer1",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MECKE",
                        "kit_batch": "DEMO-04",
                        "outcome_code": "PURPLE",
                        "time_since_reaction_seconds": 90,
                    },
                },
            ],
        },
        {
            "slug": "inconclusive-camera",
            "label": "INCONCLUSIVE - camera reading failed the quality gates",
            "expected": "INCONCLUSIVE",
            "flags": [INCONCLUSIVE_FLAG],
            "operator": "officer2",
            "ts": _at(now, 2, 11, 30),
            "appearance": "POWDER",
            "colour": "dark residue",
            "weight": "0.1 g",
            "gps": (51.5058, -0.1332, 15.0),
            "camera": "scene_dark.png",
            "tests": [
                {
                    "key": ("COLOUR_REAGENT", "MARQUIS", None, "CAMERA"),
                    "user": "officer2",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MARQUIS",
                        "kit_batch": "DEMO-05",
                        "time_since_reaction_seconds": 180,
                        "source": "CAMERA",
                    },
                },
            ],
        },
        {
            "slug": "mixture-flag",
            "label": "PRESUMPTIVE + mixture flag - SCOTT blue + MARQUIS orange-red",
            "expected": "PRESUMPTIVE",
            "flags": [AMBIGUOUS_FLAG],
            "operator": "officer2",
            "ts": _at(now, 1, 15, 45),
            "appearance": "POWDER",
            "colour": "white",
            "weight": "0.8 g",
            "gps": (51.5085, -0.1255, 10.5),
            "tests": [
                {
                    "key": ("COLOUR_REAGENT", "SCOTT", "BLUE", "MANUAL"),
                    "user": "officer2",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "SCOTT",
                        "kit_batch": "DEMO-06",
                        "outcome_code": "BLUE",
                        "time_since_reaction_seconds": 60,
                    },
                },
                {
                    "key": ("COLOUR_REAGENT", "MARQUIS", "ORANGE_RED", "MANUAL"),
                    "user": "officer2",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MARQUIS",
                        "kit_batch": "DEMO-06",
                        "outcome_code": "ORANGE_RED",
                        "time_since_reaction_seconds": 120,
                    },
                },
            ],
        },
        {
            "slug": "camera-match",
            "label": "WEAK_PRESUMPTIVE - camera capture (heroin/MDMA ambiguous)",
            "expected": "WEAK_PRESUMPTIVE",
            "flags": [AMBIGUOUS_FLAG],
            "operator": "officer1",
            "ts": _at(now, 1, 17, 10),
            "appearance": "POWDER",
            "colour": "violet",
            "weight": "0.3 g",
            "gps": (51.5101, -0.1213, 6.0),
            "camera": "scene_ideal.png",
            "tests": [
                {
                    "key": ("COLOUR_REAGENT", "MARQUIS", None, "CAMERA"),
                    "user": "officer1",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MARQUIS",
                        "kit_batch": "DEMO-07",
                        "time_since_reaction_seconds": 180,
                        "source": "CAMERA",
                    },
                },
            ],
        },
        {
            "slug": "lab-confirmed",
            "label": "CONFIRMED_BY_LAB - presumptive MDMA + GC-MS by lab1",
            "expected": "CONFIRMED_BY_LAB",
            "flags": [],
            "operator": "officer1",
            "ts": now - timedelta(minutes=45),
            "appearance": "BLOTTER",
            "colour": "light blue",
            "weight": "0.1 g",
            "gps": (51.5130, -0.1268, 4.5),
            "tests": [
                {
                    "key": ("COLOUR_REAGENT", "MARQUIS", "PURPLE_BLACK", "MANUAL"),
                    "user": "officer1",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MARQUIS",
                        "kit_batch": "DEMO-08",
                        "outcome_code": "PURPLE_BLACK",
                        "time_since_reaction_seconds": 120,
                    },
                },
                {
                    "key": ("COLOUR_REAGENT", "MECKE", "PURPLE", "MANUAL"),
                    "user": "officer1",
                    "payload": {
                        "test_type": "COLOUR_REAGENT",
                        "kit_code": "MECKE",
                        "kit_batch": "DEMO-08",
                        "outcome_code": "PURPLE",
                        "time_since_reaction_seconds": 90,
                    },
                },
                {
                    "key": ("LAB_CONFIRMATORY", None, None, "MANUAL"),
                    "user": "lab1",
                    "payload": {
                        "test_type": "LAB_CONFIRMATORY",
                        "input": {
                            "method": "GC-MS",
                            "compound": "MDMA",
                            "lab_reference": LAB_REFERENCE,
                        },
                    },
                },
            ],
        },
    ]


def _user(db, username: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise SystemExit(
            f"missing demo user '{username}' - run 'python -m app.seed' first."
        )
    return user


def _find_sample(db, slug: str) -> Sample | None:
    return db.scalar(
        select(Sample).where(Sample.notes.like(f"{MARKER} {slug} %"))
    )


def _has_record(db, sample_id: str) -> bool:
    return (
        db.scalar(select(func.count()).select_from(Record).where(Record.sample_id == sample_id))
        or 0
    ) > 0


def _test_key(test: SampleTest) -> tuple:
    return (test.test_type, test.kit.code if test.kit else None, test.outcome_code, test.source)


def _camera_test(db, user: User, spec: dict) -> dict:
    """Run the real image pipeline + image store for one camera scene."""
    scene = SCENES_DIR / spec["camera"]
    if not scene.exists():
        raise SystemExit(f"missing demo scene: {scene}")

    async def _analyze():
        upload = UploadFile(
            file=BytesIO(scene.read_bytes()),
            filename=scene.name,
            headers=Headers({"content-type": "image/png"}),
        )
        return await analyze_uploaded_image(
            user,
            db,
            file=upload,
            kit_code=spec["payload"]["kit_code"],
            roi=json.dumps(GUIDE_ROI),
            time_since_reaction_seconds=spec["payload"].get("time_since_reaction_seconds"),
        )

    report = asyncio.run(_analyze())
    digest, _ = save_image(scene.read_bytes(), "image/png")

    outcome = (report.get("match") or {}).get("outcome")
    usable = report["status"] == "OK" and outcome is not None
    detected = outcome if usable else None
    match = report.get("match") or {}
    measured = report.get("measured_colour") or {}
    corrected = report.get("corrected_colour") or {}

    payload = dict(spec["payload"])
    payload.update(
        outcome_code=detected["code"] if detected else None,
        image_sha256=digest,
        input={
            "analysis_status": report["status"],
            "image": report["image"],
            "roi": report["roi"],
        },
        calibration=report["calibration"],
        reading={
            "status": report["status"],
            "inconclusive": not usable,
            "quality_passed": report["quality"]["passed"],
            "detected_outcome_code": detected["code"] if detected else None,
            "detected_outcome_label": detected["label"] if detected else None,
            "delta_e": match.get("delta_e"),
            "second_delta_e": match.get("second_delta_e"),
            "margin": match.get("margin"),
            "match_status": match.get("status"),
            "measured_hex": measured.get("hex"),
            "corrected_hex": corrected.get("hex"),
            "reasons": report["reasons"],
            "concentration": report["concentration"],
        },
    )
    return payload


def _seed_one(db, scenario: dict, req: _FakeRequest, prev_desired: datetime | None):
    slug = scenario["slug"]
    ts = scenario["ts"]
    desired = ts + timedelta(minutes=30)
    if prev_desired is not None and desired <= prev_desired:
        raise RuntimeError(f"scenario '{slug}' timestamp does not follow the chain order")

    notes = (
        f"{MARKER} {slug} - synthetic demo record created by "
        f"python -m app.seed_demo; not a real field test."
    )
    operator = _user(db, scenario["operator"])

    sample = _find_sample(db, slug)
    if sample is not None and _has_record(db, sample.id):
        return sample, None, "skipped"
    if sample is None:
        gps_lat, gps_lon, gps_acc = scenario["gps"]
        out = create_sample(
            SampleCreate(
                appearance=scenario["appearance"],
                colour=scenario["colour"],
                approximate_weight=scenario["weight"],
                notes=notes,
                gps_lat=gps_lat,
                gps_lon=gps_lon,
                gps_accuracy_m=gps_acc,
                gps_mock_location=True,
                device_timestamp=ts,
            ),
            req,
            operator,
            db,
        )
        sample = db.get(Sample, out.id)
        sample.created_at = ts
        db.commit()

    existing_keys = {_test_key(t) for t in sample.tests}
    camera_report = scenario.get("camera")
    for index, spec in enumerate(scenario["tests"]):
        if spec["key"] in existing_keys:
            continue
        actor = _user(db, spec["user"])
        if camera_report:
            spec = dict(spec, camera=camera_report)
            payload = _camera_test(db, actor, spec)
        else:
            payload = spec["payload"]
        out = add_test(sample.id, TestCreate(**payload), req, actor, db)
        test = db.get(SampleTest, out.test.id)
        test.created_at = ts + timedelta(minutes=3 * (index + 1))
        db.commit()
        camera_report = None

    db.refresh(sample, ["tests"])

    if _has_record(db, sample.id):
        return sample, None, "skipped"

    tip = db.scalar(
        select(Record).order_by(Record.created_at.desc(), Record.id.desc()).limit(1)
    )
    desired = ts + timedelta(minutes=30)
    server_at = desired
    clamped = False
    if tip is not None and desired < tip.server_timestamp:
        server_at = tip.server_timestamp
        clamped = True

    with _clock(server_at):
        finalize(sample.id, req, operator, db)
    record = db.scalar(select(Record).where(Record.sample_id == sample.id))
    return sample, record, "clamped" if clamped else "created"


def _check(db, scenario: dict, sample: Sample, record: Record) -> list[str]:
    problems: list[str] = []
    analysis = record.analysis or {}
    if record.status != scenario["expected"]:
        problems.append(f"status {record.status} != {scenario['expected']}")
    if analysis.get("flags") != scenario["flags"]:
        problems.append(f"flags {analysis.get('flags')} != {scenario['flags']}")
    if analysis.get("concentration") != CONCENTRATION_NOT_DETERMINABLE:
        problems.append("missing exact concentration line")
    if not record.disclaimer:
        problems.append("missing disclaimer")

    image_bytes = load_image(record.image_sha256) if record.image_sha256 else None
    result = verify_record(db, record, image_bytes)
    if result["overall"] != "PASS":
        failing = [c["label"] for c in result["checks"] if c["status"] == "FAIL"]
        problems.append(f"verification FAIL: {', '.join(failing)}")
    if record.image_sha256:
        image_check = next(c for c in result["checks"] if c["id"] == "image_hash")
        if image_check["status"] != "PASS":
            problems.append("camera image hash did not verify")
    if sample.notes is None or not sample.notes.startswith(MARKER):
        problems.append("sample is not marked as demo")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed eight demo samples/records via the real services."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop and rebuild reference data first (fresh chain = full spread)",
    )
    args = parser.parse_args(argv)

    init_db()
    if args.reset:
        reset_database()
    with SessionFactory() as db:
        seed_reference(db)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        scenarios = _scenarios(now)
        req = _FakeRequest()
        rows: list[tuple] = []
        failures: list[str] = []
        clamped = skipped = 0
        prev_desired: datetime | None = None

        for scenario in scenarios:
            desired = scenario["ts"] + timedelta(minutes=30)
            sample, record, state = _seed_one(db, scenario, req, prev_desired)
            prev_desired = desired
            if state == "skipped":
                skipped += 1
                record = db.scalar(
                    select(Record).where(Record.sample_id == sample.id)
                )
                state = "skipped (already seeded)"
            elif state == "clamped":
                clamped += 1

            if record is None:
                failures.append(f"{scenario['slug']}: no record after finalize")
                continue
            problems = _check(db, scenario, sample, record)
            failures.extend(f"{scenario['slug']}: {p}" for p in problems)
            rows.append(
                (
                    scenario["slug"],
                    sample.sample_code,
                    record.status,
                    record.server_timestamp.isoformat(sep=" ", timespec="seconds"),
                    "FAIL" if problems else "PASS",
                    state,
                    record.record_hash[:16],
                )
            )

        print("\nDemo records seeded through the real service path:\n")
        header = ("slug", "sample", "status", "server time", "verify", "state", "hash")
        widths = [max(len(str(r[i])) for r in rows + [header]) for i in range(len(header))]
        for line in (header, *rows):
            print("  " + "  ".join(str(v).ljust(w) for v, w in zip(line, widths)))
        print(f"\n  created: {len(rows) - skipped}   skipped: {skipped}   clamped: {clamped}")
        if clamped:
            print(
                "  note: the chain already had newer records, so server timestamps\n"
                "        were clamped to the chain tip. Run 'python -m app.seed --reset'\n"
                "        (or 'python -m app.seed_demo --reset') before seeding for a\n"
                "        full week-long spread."
            )

        if failures:
            print("\nFAILED checks:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        print(f"\nAll {len(rows)} demo records verify PASS.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
