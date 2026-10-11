"""Photo quality gates. A failed gate forces an INCONCLUSIVE reading."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import cv2
import numpy as np


@dataclass
class Gate:
    id: str
    label: str
    passed: bool
    value: float | None
    threshold: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _to_gray(region: np.ndarray) -> np.ndarray:
    if region.ndim == 2:
        return region
    return cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)


def check_resolution(image: np.ndarray, min_width: int, min_height: int) -> Gate:
    h, w = image.shape[:2]
    passed = w >= min_width and h >= min_height
    return Gate(
        id="resolution",
        label="Minimum resolution",
        passed=passed,
        value=float(min(w, h)),
        threshold=f"{min_width}x{min_height}px",
        message=(
            f"Image is {w}x{h}px."
            if passed
            else f"Image is {w}x{h}px - move closer or use a higher resolution ({min_width}x{min_height}px minimum)."
        ),
    )


def check_blur(roi: np.ndarray, min_variance: float) -> Gate:
    gray = _to_gray(roi).astype(np.float64)
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    passed = variance >= min_variance
    return Gate(
        id="blur",
        label="Focus / sharpness",
        passed=passed,
        value=round(variance, 1),
        threshold=f"variance of Laplacian >= {min_variance}",
        message=(
            f"Sharpness OK (variance {variance:.0f})."
            if passed
            else f"Image is too blurry (variance {variance:.0f} < {min_variance}). Hold steady and refocus."
        ),
    )


def check_exposure(roi: np.ndarray, min_mean: float, max_mean: float) -> Gate:
    from skimage.exposure import is_low_contrast

    gray = _to_gray(roi)
    mean = float(gray.mean())
    clipped = float((gray >= 250).mean())
    # a uniform sample is legitimately uniform; low contrast only matters when
    # combined with a blown-out or extreme exposure reading.
    washed_out = bool(is_low_contrast(gray, fraction_threshold=0.95)) and (
        mean > max_mean or mean < min_mean
    )
    passed = (min_mean <= mean <= max_mean) and clipped <= 0.25 and not washed_out
    reasons = []
    if mean < min_mean:
        reasons.append(f"too dark (mean {mean:.0f})")
    elif mean > max_mean:
        reasons.append(f"too bright (mean {mean:.0f})")
    if clipped > 0.25:
        reasons.append(f"{clipped * 100:.0f}% blown-out pixels")
    if washed_out:
        reasons.append("washed out (no contrast)")
    return Gate(
        id="exposure",
        label="Lighting / exposure",
        passed=passed,
        value=round(mean, 1),
        threshold=f"mean luminance {min_mean}-{max_mean}, clipped <= 25%",
        message=(
            f"Exposure OK (mean {mean:.0f})."
            if passed
            else "Lighting problem: " + ", ".join(reasons) + ". Adjust the angle or add light."
        ),
    )


def check_glare(roi: np.ndarray, max_fraction: float) -> Gate:
    if roi.ndim == 3:
        specular = np.all(roi >= 245, axis=-1)
    else:
        specular = roi >= 245
    fraction = float(specular.mean())
    passed = fraction <= max_fraction
    return Gate(
        id="glare",
        label="Glare / reflections",
        passed=passed,
        value=round(fraction, 4),
        threshold=f"specular highlight fraction <= {max_fraction}",
        message=(
            f"No significant glare ({fraction * 100:.1f}%)."
            if passed
            else f"Glare detected ({fraction * 100:.1f}% specular highlights). Tilt to avoid reflections."
        ),
    )


def check_card(detected: bool, marker_count: int, required: int) -> Gate:
    passed = detected and marker_count >= required
    return Gate(
        id="card",
        label="Reference card detected",
        passed=passed,
        value=float(marker_count),
        threshold=f"{required} ArUco corner markers",
        message=(
            f"Reference card detected ({marker_count} markers)."
            if passed
            else f"Reference card not usable: {marker_count}/{required} corner markers found. Frame the whole printed card."
        ),
    )


def check_calibration(rms_delta_e: float | None, max_rms: float) -> Gate:
    passed = rms_delta_e is not None and rms_delta_e <= max_rms
    return Gate(
        id="calibration",
        label="Colour calibration quality",
        passed=passed,
        value=None if rms_delta_e is None else round(rms_delta_e, 2),
        threshold=f"post-fit RMS delta E <= {max_rms}",
        message=(
            f"Calibration fits the reference card (RMS dE {rms_delta_e:.1f})."
            if passed
            else "Colour calibration failed - the card patches do not match their known values. "
            "Check lighting, dirt or a damaged card."
        ),
    )
