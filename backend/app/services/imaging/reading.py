"""ROI colour extraction and CIEDE2000 matching against kit outcome colours."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ...config import imaging_settings
from ...color import delta_e_ciede2000, lab_to_hex, rgb_to_lab

ROI_DEFAULT = {"x": 0.30, "y": 0.30, "w": 0.40, "h": 0.40}


def normalize_roi(roi: dict[str, float] | None, image_shape: tuple[int, ...]) -> dict[str, int]:
    """Convert a normalized {x,y,w,h} ROI to integer pixel bounds."""
    h, w = image_shape[:2]
    roi = roi or ROI_DEFAULT
    x0 = int(round(float(roi.get("x", 0.3)) * w))
    y0 = int(round(float(roi.get("y", 0.3)) * h))
    x1 = int(round((float(roi.get("x", 0.3)) + float(roi.get("w", 0.4))) * w))
    y1 = int(round((float(roi.get("y", 0.3)) + float(roi.get("h", 0.4))) * h))
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, w), min(y1, h)
    if x1 - x0 < 8 or y1 - y0 < 8:
        raise ValueError("region of interest is too small - check the ROI coordinates")
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1}


def median_rgb(region: np.ndarray) -> tuple[float, float, float]:
    pixels = region.reshape(-1, region.shape[-1]).astype(np.float64)
    med = np.median(pixels, axis=0)
    return (float(med[0]), float(med[1]), float(med[2]))


@dataclass
class OutcomeMatch:
    best: dict[str, Any] | None
    second: dict[str, Any] | None
    delta_e: float | None
    second_delta_e: float | None
    margin: float | None
    status: str  # MATCH | INCONCLUSIVE
    reasons: list[str]
    ranked: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.best,
            "delta_e": self.delta_e,
            "second_outcome": self.second,
            "second_delta_e": self.second_delta_e,
            "margin": self.margin,
            "status": self.status,
            "reasons": self.reasons,
            "ranked": self.ranked,
            "thresholds": {
                "max_delta_e": imaging_settings.max_delta_e,
                "min_margin": imaging_settings.min_margin,
            },
        }


def match_outcomes(
    lab: tuple[float, float, float], outcomes: list[dict[str, Any]]
) -> OutcomeMatch:
    """Match a measured Lab colour to the kit's published outcome colours."""
    ranked: list[dict[str, Any]] = []
    for outcome in outcomes:
        ref = outcome.get("ref_lab")
        if not ref or len(ref) != 3:
            continue
        d_e = delta_e_ciede2000(lab, tuple(float(v) for v in ref))
        ranked.append(
            {
                "code": outcome["code"],
                "label": outcome["label"],
                "ref_lab": [float(v) for v in ref],
                "ref_hex": outcome.get("ref_hex"),
                "delta_e": round(d_e, 2),
                "interpretation": outcome.get("interpretation"),
                "cross_reactions": outcome.get("cross_reactions") or [],
            }
        )
    ranked.sort(key=lambda r: r["delta_e"])

    if not ranked:
        return OutcomeMatch(
            best=None,
            second=None,
            delta_e=None,
            second_delta_e=None,
            margin=None,
            status="INCONCLUSIVE",
            reasons=["This kit has no reference colours configured."],
            ranked=[],
        )

    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    delta_e = best["delta_e"]
    second_delta_e = second["delta_e"] if second else None
    margin = (
        round(second_delta_e - delta_e, 2) if second_delta_e is not None else None
    )

    reasons: list[str] = []
    status = "MATCH"
    if delta_e > imaging_settings.max_delta_e:
        status = "INCONCLUSIVE"
        reasons.append(
            f"Nearest outcome is {delta_e:.1f} ΔE away (limit "
            f"{imaging_settings.max_delta_e}) - colour does not match any published "
            "outcome for this kit."
        )
    if margin is not None and margin < imaging_settings.min_margin:
        status = "INCONCLUSIVE"
        reasons.append(
            f"Margin to the second-nearest outcome is only {margin:.1f} ΔE (minimum "
            f"{imaging_settings.min_margin}) - too close to call."
        )
    if margin is None and delta_e > imaging_settings.max_delta_e * 0.6:
        status = "INCONCLUSIVE"
        reasons.append("Only one reference colour is configured for this kit.")

    return OutcomeMatch(
        best=best,
        second=second,
        delta_e=delta_e,
        second_delta_e=second_delta_e,
        margin=margin,
        status=status,
        reasons=reasons,
        ranked=ranked,
    )


def describe_colour(lab: tuple[float, float, float], rgb) -> dict[str, Any]:
    return {
        "hex": lab_to_hex(*lab),
        "lab": [round(v, 3) for v in lab],
        "rgb": [int(round(min(max(v, 0), 255))) for v in rgb],
    }


def rgb_to_lab_tuple(rgb) -> tuple[float, float, float]:
    return rgb_to_lab(*rgb)
