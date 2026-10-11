"""End-to-end image analysis: quality gates -> calibration -> ROI -> matching.

Any failed quality gate or failed calibration forces INCONCLUSIVE (hard rule).
"""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from ...config import imaging_settings
from ...enums import CONCENTRATION_NOT_DETERMINABLE, DISCLAIMER
from . import card as card_ops
from . import quality as quality_ops
from .reading import (
    describe_colour,
    match_outcomes,
    median_rgb,
    normalize_roi,
    rgb_to_lab_tuple,
)


def decode_image(data: bytes) -> np.ndarray:
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("file could not be decoded as an image")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def analyze_image(
    data: bytes,
    outcomes: list[dict[str, Any]],
    roi: dict[str, float] | None = None,
    kit_code: str | None = None,
    kit_name: str | None = None,
) -> dict[str, Any]:
    s = imaging_settings
    reasons: list[str] = []

    image = decode_image(data)
    height, width = image.shape[:2]

    # ------------------------------------------------------------------- ROI
    try:
        roi_px = normalize_roi(roi, image.shape)
    except ValueError as exc:
        return _inconclusive([], None, None, None, str(exc), width, height, kit_code, kit_name, outcomes)

    roi_region = image[roi_px["y0"] : roi_px["y1"], roi_px["x0"] : roi_px["x1"]]

    # ------------------------------------------------------------------ card
    detection = card_ops.detect_card(image)
    gates: list[quality_ops.Gate] = []
    patches: list[card_ops.PatchSample] = []
    matrix: np.ndarray | None = None
    rms = None
    raw_rms = None

    if detection.detected:
        try:
            warped = card_ops.warp_card(image, detection)
            patches = card_ops.sample_patches(warped)
            matrix = card_ops.fit_correction_matrix(patches)
            rms = card_ops.calibration_rms(patches, matrix)
            raw_rms = card_ops.raw_calibration_rms(patches)
        except Exception as exc:  # noqa: BLE001 - report, never crash the request
            detection.message = f"card processing failed: {exc}"
            detection.detected = False

    # --------------------------------------------------------------- quality
    gates.append(quality_ops.check_resolution(image, s.min_width, s.min_height))
    gates.append(quality_ops.check_blur(roi_region, s.min_blur_variance))
    gates.append(
        quality_ops.check_exposure(
            roi_region, s.exposure_min_mean, s.exposure_max_mean
        )
    )
    gates.append(quality_ops.check_glare(roi_region, s.glare_max_fraction))
    gates.append(quality_ops.check_card(detection.detected, len(detection.marker_ids), 4))
    gates.append(quality_ops.check_calibration(rms, s.max_calibration_rms))

    failed = [g for g in gates if not g.passed]
    if failed:
        reasons.extend(f"{g.label}: {g.message}" for g in failed)

    # -------------------------------------------------- corrected ROI colour
    measured_rgb = median_rgb(roi_region)
    measured_lab = rgb_to_lab_tuple(measured_rgb)
    corrected_rgb = measured_rgb
    corrected_lab = measured_lab

    if matrix is not None:
        corrected = np.clip(np.array(measured_rgb, dtype=np.float64) @ matrix, 0, 255)
        corrected_rgb = (float(corrected[0]), float(corrected[1]), float(corrected[2]))
        corrected_lab = rgb_to_lab_tuple(corrected_rgb)

    match = None
    status = "OK"
    if failed:
        status = "INCONCLUSIVE"
        match = None
    else:
        match = match_outcomes(corrected_lab, outcomes)
        if match.status == "INCONCLUSIVE":
            status = "INCONCLUSIVE"
            reasons.extend(match.reasons)

    result: dict[str, Any] = {
        "status": status,
        "kit_code": kit_code,
        "kit_name": kit_name,
        "image": {"width": width, "height": height},
        "roi": {
            **roi_px,
            "normalized": roi or {"x": 0.3, "y": 0.3, "w": 0.4, "h": 0.4},
        },
        "quality": {
            "passed": not failed,
            "gates": [g.as_dict() for g in gates],
        },
        "calibration": {
            "detected": detection.detected,
            "detection": detection.as_dict(),
            "matrix": None if matrix is None else np.round(matrix, 6).tolist(),
            "patches": [p.as_dict() for p in patches],
            "rms_delta_e": None if rms is None else round(rms, 2),
            "raw_rms_delta_e": None if raw_rms is None else round(raw_rms, 2),
        },
        "measured_colour": describe_colour(measured_lab, measured_rgb),
        "corrected_colour": describe_colour(corrected_lab, corrected_rgb),
        "match": None if match is None else match.as_dict(),
        "reasons": reasons,
        "thresholds": {
            "max_delta_e": s.max_delta_e,
            "min_margin": s.min_margin,
            "min_blur_variance": s.min_blur_variance,
            "min_resolution": [s.min_width, s.min_height],
        },
        "concentration": CONCENTRATION_NOT_DETERMINABLE,
        "disclaimer": DISCLAIMER,
    }
    return result


def _inconclusive(
    gates,
    match,
    matrix,
    patches,
    reason: str,
    width: int,
    height: int,
    kit_code,
    kit_name,
    outcomes,
) -> dict[str, Any]:
    return {
        "status": "INCONCLUSIVE",
        "kit_code": kit_code,
        "kit_name": kit_name,
        "image": {"width": width, "height": height},
        "roi": None,
        "quality": {"passed": False, "gates": gates},
        "calibration": {
            "detected": False,
            "detection": {"detected": False, "message": reason},
            "matrix": None,
            "patches": patches or [],
            "rms_delta_e": None,
        },
        "measured_colour": None,
        "corrected_colour": None,
        "match": None,
        "reasons": [reason],
        "concentration": CONCENTRATION_NOT_DETERMINABLE,
        "disclaimer": DISCLAIMER,
    }
