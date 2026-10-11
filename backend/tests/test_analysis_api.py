from __future__ import annotations

from tests.conftest import login


def _obs(**kw):
    base = {
        "test_type": "COLOUR_REAGENT",
        "kit_code": "MARQUIS",
        "outcome_code": "PURPLE_BLACK",
        "outcome_label": "Purple turning black",
    }
    base.update(kw)
    return base


def test_preview_requires_auth(client):
    response = client.post("/api/analysis/preview", json={"observations": [_obs()]})
    assert response.status_code == 401


def test_preview_scores_colour_observations(client):
    headers = login(client, "officer1", "FieldProof#Demo1")
    response = client.post(
        "/api/analysis/preview",
        json={"observations": [_obs(ref="a"), _obs(ref="b", kit_code="MECKE",
                                                    outcome_code="PURPLE",
                                                    outcome_label="Purple")]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] in {"PRESUMPTIVE", "STRONG_PRESUMPTIVE"}
    assert body["top_match"]["code"] == "MDMA"
    assert body["concentration"].startswith("Concentration: not determinable")
    assert "PRESUMPTIVE FIELD RESULT ONLY" in body["disclaimer"]
    assert body["explanation"]


def test_preview_officer_cannot_submit_lab_result(client):
    headers = login(client, "officer1", "FieldProof#Demo1")
    payload = {
        "observations": [
            _obs(),
            {
                "test_type": "LAB_CONFIRMATORY",
                "lab_method": "GC-MS",
                "lab_compound": "Cocaine (hydrochloride salt)",
                "purity_percent": 70,
            },
        ]
    }
    response = client.post("/api/analysis/preview", json=payload, headers=headers)
    assert response.status_code == 403


def test_preview_lab_user_can_submit_lab_result(client):
    headers = login(client, "lab1", "FieldProof#Lab1")
    payload = {
        "observations": [
            {
                "test_type": "LAB_CONFIRMATORY",
                "lab_method": "GC-MS",
                "lab_compound": "Cocaine (hydrochloride salt)",
                "purity_percent": 70.0,
                "lab_reference": "FS-1",
            }
        ]
    }
    response = client.post("/api/analysis/preview", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "CONFIRMED_BY_LAB"
    assert body["top_match"]["code"] == "COCAINE"
    assert "Purity: 70.0%" in body["concentration"]


def test_preview_rejects_unknown_test_type(client):
    headers = login(client, "officer1", "FieldProof#Demo1")
    response = client.post(
        "/api/analysis/preview",
        json={"observations": [{"test_type": "TELEPATHY"}]},
        headers=headers,
    )
    assert response.status_code == 422
