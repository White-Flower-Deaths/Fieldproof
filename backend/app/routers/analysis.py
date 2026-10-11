from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..deps import CurrentUser, DbSession
from ..schemas import AnalysisPreviewIn
from ..services.scoring import Observation, analyze, build_reaction_index

router = APIRouter(prefix="/analysis", tags=["analysis"])

ALLOWED_TYPES = {
    "COLOUR_REAGENT",
    "IMMUNOASSAY_STRIP",
    "SPECTROMETER",
    "LAB_CONFIRMATORY",
}


@router.post("/preview")
def preview(payload: AnalysisPreviewIn, user: CurrentUser, db: DbSession) -> dict:
    """Score a set of observations without persisting anything.

    Lets the engine be exercised (and demoed) before a sample exists. The stored
    version, GET /samples/{id}/analysis, arrives with the sample workflow.
    """
    for obs in payload.observations:
        if obs.test_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown test type '{obs.test_type}'.",
            )
        if obs.test_type == "LAB_CONFIRMATORY" and user.role not in {"LAB", "ADMIN"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Laboratory confirmatory results may only be entered by LAB or ADMIN users.",
            )

    index = build_reaction_index(db)
    observations = [
        Observation(
            ref=obs.ref or f"obs-{i + 1}",
            test_type=obs.test_type,
            kit_id=obs.kit_id,
            kit_code=obs.kit_code,
            kit_name=obs.kit_name,
            outcome_code=obs.outcome_code,
            outcome_label=obs.outcome_label,
            inconclusive=obs.inconclusive,
            kit_batch=obs.kit_batch,
            library_match=obs.library_match,
            match_score=obs.match_score,
            lab_method=obs.lab_method,
            lab_compound=obs.lab_compound,
            lab_reference=obs.lab_reference,
            purity_percent=obs.purity_percent,
        )
        for i, obs in enumerate(payload.observations)
    ]
    return analyze(index, observations)
