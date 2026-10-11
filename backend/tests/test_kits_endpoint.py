from __future__ import annotations

from conftest import login


def test_kits_endpoint_lists_active_kits_with_outcomes(client):
    response = client.get("/api/kits")
    assert response.status_code == 200, response.text
    kits = response.json()
    assert len(kits) == 6, "seed must expose 6 kits"

    by_code = {k["code"]: k for k in kits}
    assert set(by_code) == {
        "MARQUIS",
        "MECKE",
        "MANDELIN",
        "SCOTT",
        "DUQUENOIS_LEVINE",
        "FENT_STRIP",
    }

    marquis = by_code["MARQUIS"]
    assert marquis["test_type"] == "COLOUR_REAGENT"
    assert marquis["outcomes"], "every kit must expose its observed outcomes"
    codes = [o["code"] for o in marquis["outcomes"]]
    assert "PURPLE_BLACK" in codes
    assert all(o["label"] for o in marquis["outcomes"])

    strip = by_code["FENT_STRIP"]
    assert strip["test_type"] == "IMMUNOASSAY_STRIP"
    assert strip["outcomes"], "immunoassay strips must list their readings"

    # reference data carries the demo citation (hard rule)
    assert all(k["source_citation"] for k in kits)


def test_kits_endpoint_never_leaks_expected_reactions(client):
    response = client.get("/api/kits")
    body = response.text
    assert "likelihood" not in body
    assert "expected_reactions" not in body


def test_kits_endpoint_accepts_anonymous_but_matches_authed(client):
    anonymous = client.get("/api/kits").json()
    headers = login(client, "officer1", "FieldProof#Demo1")
    authed = client.get("/api/kits", headers=headers).json()
    assert anonymous == authed
