"""Image quality gates, reference-card calibration and colour matching."""
from .card import (
    CardDetection,
    PatchSample,
    apply_correction,
    calibration_rms,
    detect_card,
    fit_correction_matrix,
    sample_patches,
    warp_card,
)
from .pipeline import analyze_image, decode_image
from .reading import match_outcomes, normalize_roi
from .synth import encode_jpeg, encode_png, render_card, render_scene

__all__ = [
    "CardDetection",
    "PatchSample",
    "analyze_image",
    "apply_correction",
    "calibration_rms",
    "decode_image",
    "detect_card",
    "encode_jpeg",
    "encode_png",
    "fit_correction_matrix",
    "match_outcomes",
    "normalize_roi",
    "render_card",
    "render_scene",
    "sample_patches",
    "warp_card",
]
