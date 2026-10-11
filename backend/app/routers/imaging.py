from __future__ import annotations

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..audit import audit
from ..deps import CurrentUser, DbSession, RequireOfficer
from ..models import Kit, TestOutcome
from ..services.imaging.card_config import card_public_dict
from ..services.imaging.pipeline import analyze_image

router = APIRouter(tags=["images"])


def _outcomes_for(db, kit: Kit) -> list[dict]:
    rows = (
        db.query(TestOutcome)
        .filter(TestOutcome.kit_id == kit.id)
        .order_by(TestOutcome.sort_order)
        .all()
    )
    return [
        {
            "code": r.code,
            "label": r.label,
            "ref_lab": [r.ref_l, r.ref_a, r.ref_b],
            "ref_hex": r.hex,
            "interpretation": r.interpretation,
            "cross_reactions": r.cross_reactions or [],
            "source_citation": r.source_citation,
        }
        for r in rows
    ]


@router.post("/images/analyze")
async def analyze_uploaded_image(
    user: RequireOfficer,
    db: DbSession,
    file: UploadFile = File(...),
    kit_code: str = Form(...),
    roi: str | None = Form(None),
    time_since_reaction_seconds: int | None = Form(None),
) -> dict:
    kit = db.query(Kit).filter(Kit.code == kit_code).first()
    if kit is None or not kit.is_active:
        raise HTTPException(status_code=422, detail=f"Unknown kit '{kit_code}'.")
    if kit.test_type != "COLOUR_REAGENT":
        raise HTTPException(
            status_code=422,
            detail="Camera colour reading is only available for COLOUR_REAGENT kits.",
        )

    roi_dict = None
    if roi:
        try:
            roi_dict = json.loads(roi)
            if not isinstance(roi_dict, dict):
                raise ValueError("ROI must be an object")
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(
                status_code=422, detail=f"Invalid roi: {exc}"
            ) from exc

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        report = analyze_image(
            data,
            outcomes=_outcomes_for(db, kit),
            roi=roi_dict,
            kit_code=kit.code,
            kit_name=kit.name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    report["time_since_reaction_seconds"] = time_since_reaction_seconds
    audit(
        db,
        action="image.analyze",
        actor_id=user.id,
        actor_username=user.username,
        actor_role=user.role,
        entity_type="image",
        entity_id=None,
        detail={
            "kit": kit.code,
            "status": report["status"],
            "failed_gates": [
                g["id"] for g in report["quality"]["gates"] if not g["passed"]
            ],
        },
        commit=True,
    )
    return report


@router.get("/reference-card")
def reference_card(user: CurrentUser) -> dict:
    """Printable card layout + known patch values (also used by the capture overlay)."""
    return card_public_dict()
