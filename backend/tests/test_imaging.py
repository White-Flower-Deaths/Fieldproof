"""Step 4: image quality gates, reference-card calibration, colour matching."""
from __future__ import annotations

import json

import cv2
import numpy as np
import pytest

from app.color import delta_e_ciede2000, hex_to_lab
from app.config import imaging_settings
from app.enums import CONCENTRATION_NOT_DETERMINABLE, DISCLAIMER
from app.services.imaging import (
    analyze_image,
    detect_card,
    encode_png,
    match_outcomes,
    normalize_roi,
    render_card,
    render_scene,
    sample_patches,
    warp_card,
)
from app.services.imaging.card import fit_correction_matrix, raw_calibration_rms
from app.services.imaging.reading import ROI_DEFAULT
from tests.conftest import login

PURPLE = "#3B1F4A"
OUTCOMES = [
    {
        "code": "PURPLE_BLACK",
        "label": "Purple turning black",
        "ref_hex": PURPLE,
        "ref_lab": list(hex_to_lab(PURPLE)),
    },
    {
        "code": "NO_REACTION_ORANGE",
        "label": "Orange",
        "ref_hex": "#E08A2E",
        "ref_lab": list(hex_to_lab("#E08A2E")),
    },
    {
        "code": "BROWN",
        "label": "Brown",
        "ref_hex": "#6B4A2B",
        "ref_lab": list(hex_to_lab("#6B4A2B")),
    },
]


def _scene(**kwargs):
    scene = render_scene(PURPLE, **kwargs)
    return scene, encode_png(scene["image"])


def _gate(report: dict, gate_id: str) -> dict:
    for gate in report["quality"]["gates"]:
        if gate["id"] == gate_id:
            return gate
    raise AssertionError(f"gate {gate_id} missing from report")


# --------------------------------------------------------------- card / colour


def test_reference_card_detected_and_patches_sampled():
    card = render_card()
    detection = detect_card(card)
    assert detection.detected
    assert len(detection.marker_ids) == 4
    warped = warp_card(card, detection)
    patches = sample_patches(warped)
    assert len(patches) >= 7
    assert raw_calibration_rms(patches) < 3.0
    matrix = fit_correction_matrix(patches)
    assert matrix.shape == (3, 3)


def test_warm_lighting_is_corrected_by_reference_card():
    scene, png = _scene(lighting=(1.18, 0.96, 0.78))
    report = analyze_image(png, OUTCOMES, roi=scene["roi"], kit_code="MARQUIS")
    calib = report["calibration"]
    assert calib["detected"]
    assert calib["raw_rms_delta_e"] > calib["rms_delta_e"], "correction must help"
    assert calib["rms_delta_e"] <= imaging_settings.max_calibration_rms
    assert report["status"] == "OK"
    assert report["match"]["outcome"]["code"] == "PURPLE_BLACK"
    assert report["match"]["delta_e"] <= imaging_settings.max_delta_e


def test_ideal_scene_matches_expected_outcome():
    scene, png = _scene()
    report = analyze_image(png, OUTCOMES, roi=scene["roi"], kit_code="MARQUIS")
    assert report["status"] == "OK"
    assert report["quality"]["passed"]
    match = report["match"]
    assert match["outcome"]["code"] == "PURPLE_BLACK"
    assert match["status"] == "MATCH"
    assert match["delta_e"] < imaging_settings.max_delta_e
    assert match["margin"] >= imaging_settings.min_margin
    assert report["concentration"] == CONCENTRATION_NOT_DETERMINABLE
    assert report["disclaimer"] == DISCLAIMER
    assert report["corrected_colour"]["hex"]


# ------------------------------------------------------------------ quality


def test_low_resolution_fails_resolution_gate():
    scene, _ = _scene()
    small = cv2.resize(scene["image"], (320, 240), interpolation=cv2.INTER_AREA)
    report = analyze_image(encode_png(small), OUTCOMES, roi=scene["roi"])
    assert not _gate(report, "resolution")["passed"]
    assert report["status"] == "INCONCLUSIVE"
    assert report["match"] is None


def test_blurry_image_fails_blur_gate():
    scene, png = _scene(blur_ksize=21)
    report = analyze_image(png, OUTCOMES, roi=scene["roi"])
    assert not _gate(report, "blur")["passed"]
    assert report["status"] == "INCONCLUSIVE"


def test_glare_fails_glare_gate():
    scene, png = _scene(glare=True)
    report = analyze_image(png, OUTCOMES, roi=scene["roi"])
    assert not _gate(report, "glare")["passed"]
    assert report["status"] == "INCONCLUSIVE"


def test_missing_marker_fails_card_gate():
    scene, png = _scene(drop_marker=2)
    report = analyze_image(png, OUTCOMES, roi=scene["roi"])
    assert not _gate(report, "card")["passed"]
    assert not _gate(report, "calibration")["passed"]
    assert report["status"] == "INCONCLUSIVE"


def test_dark_image_fails_exposure_gate():
    scene, png = _scene(lighting=(0.15, 0.15, 0.15))
    report = analyze_image(png, OUTCOMES, roi=scene["roi"])
    assert not _gate(report, "exposure")["passed"]
    assert report["status"] == "INCONCLUSIVE"


def test_undecodable_bytes_raise_value_error():
    with pytest.raises(ValueError):
        analyze_image(b"not an image at all", OUTCOMES)


def test_roi_out_of_bounds_returns_inconclusive():
    _, png = _scene()
    report = analyze_image(
        png, OUTCOMES, roi={"x": 0.995, "y": 0.995, "w": 0.5, "h": 0.5}
    )
    assert report["status"] == "INCONCLUSIVE"
    assert any("ROI" in r or "region" in r for r in report["reasons"])


# ----------------------------------------------------------------- matching


def test_match_exact_reference_colour():
    match = match_outcomes(tuple(hex_to_lab(PURPLE)), OUTCOMES)
    assert match.status == "MATCH"
    assert match.best["code"] == "PURPLE_BLACK"
    assert match.delta_e < 2.0
    assert match.margin >= imaging_settings.min_margin


def test_match_far_off_colour_is_inconclusive():
    off_lab = (92.0, -48.0, 62.0)
    match = match_outcomes(off_lab, OUTCOMES)
    assert match.status == "INCONCLUSIVE"
    assert match.reasons


def test_match_ambiguous_when_margin_too_small():
    near = [
        {"code": "A", "label": "A", "ref_lab": [50.0, 10.0, 5.0]},
        {"code": "B", "label": "B", "ref_lab": [54.0, 12.0, 7.0]},
    ]
    match = match_outcomes((52.0, 11.0, 6.0), near)
    assert match.status == "INCONCLUSIVE"
    assert any("too close" in r for r in match.reasons)


def test_match_without_references_is_inconclusive():
    match = match_outcomes((50.0, 10.0, 10.0), [])
    assert match.status == "INCONCLUSIVE"
    assert "no reference colours" in match.reasons[0]


def test_delta_e_identical_colour_is_zero():
    lab = hex_to_lab(PURPLE)
    assert delta_e_ciede2000(lab, lab) == pytest.approx(0.0, abs=1e-9)


def test_normalize_roi_default_and_clamping():
    roi = normalize_roi(None, (960, 1280, 3))
    assert roi["x0"] == int(round(ROI_DEFAULT["x"] * 1280))
    clamped = normalize_roi({"x": -0.2, "y": -0.2, "w": 1.4, "h": 1.4}, (960, 1280, 3))
    assert clamped["x0"] == 0 and clamped["x1"] == 1280
    with pytest.raises(ValueError):
        normalize_roi({"x": 0.0, "y": 0.0, "w": 0.001, "h": 0.001}, (960, 1280, 3))


# -------------------------------------------------------------------- API


def test_analyze_requires_auth(client):
    scene, png = _scene()
    response = client.post(
        "/api/images/analyze",
        files={"file": ("scene.png", png, "image/png")},
        data={"kit_code": "MARQUIS"},
    )
    assert response.status_code == 401


def test_analyze_endpoint_happy_path(client, db_session):
    headers = login(client, "officer1", "FieldProof#Demo1")
    scene, png = _scene()
    response = client.post(
        "/api/images/analyze",
        headers=headers,
        files={"file": ("scene.png", png, "image/png")},
        data={
            "kit_code": "MARQUIS",
            "roi": json.dumps(scene["roi"]),
            "time_since_reaction_seconds": "180",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "OK"
    assert body["quality"]["passed"] is True
    assert body["match"]["outcome"]["code"] == "PURPLE_BLACK"
    assert body["concentration"] == CONCENTRATION_NOT_DETERMINABLE
    assert body["disclaimer"] == DISCLAIMER
    assert body["time_since_reaction_seconds"] == 180

    from app.models import AuditLog

    entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "image.analyze")
        .order_by(AuditLog.created_at.desc())
        .first()
    )
    assert entry is not None
    assert entry.actor_username == "officer1"
    assert entry.detail["kit"] == "MARQUIS"


def test_analyze_rejects_non_colour_reagent_kit(client):
    headers = login(client, "officer1", "FieldProof#Demo1")
    _, png = _scene()
    response = client.post(
        "/api/images/analyze",
        headers=headers,
        files={"file": ("scene.png", png, "image/png")},
        data={"kit_code": "FENT_STRIP"},
    )
    assert response.status_code == 422
    assert "COLOUR_REAGENT" in response.json()["detail"]


def test_analyze_rejects_unknown_kit(client):
    headers = login(client, "officer1", "FieldProof#Demo1")
    _, png = _scene()
    response = client.post(
        "/api/images/analyze",
        headers=headers,
        files={"file": ("scene.png", png, "image/png")},
        data={"kit_code": "NOPE"},
    )
    assert response.status_code == 422


def test_analyze_rejects_corrupt_file(client):
    headers = login(client, "officer1", "FieldProof#Demo1")
    response = client.post(
        "/api/images/analyze",
        headers=headers,
        files={"file": ("bad.png", b"garbage", "image/png")},
        data={"kit_code": "MARQUIS"},
    )
    assert response.status_code == 422
    assert "decoded" in response.json()["detail"]


def test_analyze_rejects_invalid_roi(client):
    headers = login(client, "officer1", "FieldProof#Demo1")
    _, png = _scene()
    response = client.post(
        "/api/images/analyze",
        headers=headers,
        files={"file": ("scene.png", png, "image/png")},
        data={"kit_code": "MARQUIS", "roi": "not-json"},
    )
    assert response.status_code == 422


def test_reference_card_endpoint(client):
    response = client.get("/api/reference-card")
    assert response.status_code == 401
    headers = login(client, "officer1", "FieldProof#Demo1")
    response = client.get("/api/reference-card", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["aruco"]["markers"]) == 4
    assert len(body["patches"]) >= 7
    assert body["card"]["width_mm"] == 100
    assert body["source_citation"]
