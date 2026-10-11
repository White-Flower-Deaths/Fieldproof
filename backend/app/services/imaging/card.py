"""Reference card: ArUco detection, perspective warp, patch sampling,
3x3 least-squares colour correction."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from ...color import delta_e_ciede2000, hex_to_lab, rgb_to_lab
from .card_config import CORNER_ORDER, CardSpec, load_card_spec


@dataclass
class PatchSample:
    code: str
    label: str
    expected_hex: str
    measured_rgb: tuple[float, float, float]
    expected_lab: tuple[float, float, float]
    measured_lab: tuple[float, float, float]
    delta_e: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "expected_hex": self.expected_hex,
            "measured_hex": "#{:02X}{:02X}{:02X}".format(
                *[int(round(min(max(v, 0), 255))) for v in self.measured_rgb]
            ),
            "expected_lab": [round(v, 3) for v in self.expected_lab],
            "measured_lab": [round(v, 3) for v in self.measured_lab],
            "delta_e": round(self.delta_e, 2),
        }


@dataclass
class CardDetection:
    detected: bool
    marker_ids: list[int] = field(default_factory=list)
    src_centers: list[tuple[float, float]] = field(default_factory=list)
    homography: np.ndarray | None = None
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "marker_ids": self.marker_ids,
            "dictionary": load_card_spec().dictionary,
            "message": self.message,
        }


def _aruco_components():
    dictionary = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, load_card_spec().dictionary)
    )
    parameters = cv2.aruco.DetectorParameters()
    return dictionary, parameters


def detect_card(image: np.ndarray, spec: CardSpec | None = None) -> CardDetection:
    spec = spec or load_card_spec()
    dictionary, parameters = _aruco_components()

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    if hasattr(cv2.aruco, "ArucoDetector"):
        detector = cv2.aruco.ArucoDetector(dictionary, parameters)
        corners, ids, _ = detector.detectMarkers(gray)
    else:  # pragma: no cover - older OpenCV
        corners, ids, _ = cv2.aruco.detectMarkers(
            gray, dictionary, parameters=parameters
        )

    if ids is None or len(ids) == 0:
        return CardDetection(False, message="no ArUco markers found")

    found: dict[int, np.ndarray] = {}
    for marker_id, marker_corners in zip(ids.flatten().tolist(), corners):
        found[int(marker_id)] = marker_corners.reshape(-1, 2)

    expected = spec.marker_ids
    missing = [mid for mid in expected if mid not in found]
    if missing:
        return CardDetection(
            False,
            marker_ids=sorted(found),
            message=f"missing marker id(s): {', '.join(str(m) for m in missing)}",
        )

    src_centers = [tuple(found[mid].mean(axis=0)) for mid in expected]
    dst_centers = spec.canonical_centers
    homography = cv2.getPerspectiveTransform(
        np.float32(src_centers), np.float32(dst_centers)
    )
    return CardDetection(
        True,
        marker_ids=list(expected),
        src_centers=[(float(x), float(y)) for x, y in src_centers],
        homography=homography,
        message="card detected",
    )


def warp_card(image: np.ndarray, detection: CardDetection, spec: CardSpec | None = None) -> np.ndarray:
    spec = spec or load_card_spec()
    if not detection.detected or detection.homography is None:
        raise ValueError("card was not detected")
    return cv2.warpPerspective(
        image,
        detection.homography,
        (spec.width_px, spec.height_px),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def _median_rgb(region: np.ndarray) -> tuple[float, float, float]:
    pixels = region.reshape(-1, region.shape[-1]).astype(np.float64)
    med = np.median(pixels, axis=0)
    return (float(med[0]), float(med[1]), float(med[2]))


def sample_patches(
    warped: np.ndarray, spec: CardSpec | None = None
) -> list[PatchSample]:
    spec = spec or load_card_spec()
    samples: list[PatchSample] = []
    for patch in spec.patches:
        x, y, w, h = spec.patch_rect_px(patch)
        inset_x, inset_y = int(w * 0.25), int(h * 0.25)
        roi = warped[y + inset_y : y + h - inset_y, x + inset_x : x + w - inset_x]
        if roi.size == 0:
            continue
        measured = _median_rgb(roi)
        expected_lab = hex_to_lab(patch.hex)
        measured_lab = rgb_to_lab(*measured)
        samples.append(
            PatchSample(
                code=patch.code,
                label=patch.label,
                expected_hex=patch.hex,
                measured_rgb=measured,
                expected_lab=expected_lab,
                measured_lab=measured_lab,
                delta_e=delta_e_ciede2000(measured_lab, expected_lab),
            )
        )
    return samples


def fit_correction_matrix(samples: list[PatchSample]) -> np.ndarray:
    """Least-squares 3x3 matrix M such that measured @ M ~= expected (sRGB)."""
    if len(samples) < 3:
        raise ValueError("need at least 3 patches to fit a colour correction")
    x = np.array([s.measured_rgb for s in samples], dtype=np.float64)
    y = np.array(
        [_hex_to_rgb_tuple(s.expected_hex) for s in samples], dtype=np.float64
    )
    matrix, *_ = np.linalg.lstsq(x, y, rcond=None)
    return matrix


def _hex_to_rgb_tuple(hex_value: str) -> tuple[int, int, int]:
    from ...color import hex_to_rgb

    return hex_to_rgb(hex_value)


def apply_correction(matrix: np.ndarray, image: np.ndarray) -> np.ndarray:
    """Apply the 3x3 matrix to an RGB image (H, W, 3) or a pixel array (N, 3)."""
    if image.ndim == 2:
        corrected = image @ matrix
        return np.clip(corrected, 0, 255)
    flat = image.reshape(-1, image.shape[-1]).astype(np.float64)
    corrected = flat @ matrix
    corrected = np.clip(corrected, 0, 255).astype(image.dtype)
    return corrected.reshape(image.shape)


def calibration_rms(samples: list[PatchSample], matrix: np.ndarray) -> float:
    """RMS delta E between corrected measurements and the known patch values."""
    if not samples:
        return float("inf")
    total = 0.0
    for sample in samples:
        corrected = np.clip(
            np.array(sample.measured_rgb, dtype=np.float64) @ matrix, 0, 255
        )
        d_e = delta_e_ciede2000(rgb_to_lab(*corrected), sample.expected_lab)
        total += d_e**2
    return float(np.sqrt(total / len(samples)))


def raw_calibration_rms(samples: list[PatchSample]) -> float:
    if not samples:
        return float("inf")
    return float(np.sqrt(np.mean([s.delta_e**2 for s in samples])))


# re-export for callers that only need ordering knowledge
__all__ = [
    "CORNER_ORDER",
    "CardDetection",
    "PatchSample",
    "apply_correction",
    "calibration_rms",
    "detect_card",
    "fit_correction_matrix",
    "raw_calibration_rms",
    "sample_patches",
    "warp_card",
]
