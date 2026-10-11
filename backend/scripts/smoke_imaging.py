"""Step-4 live smoke: start the server first, then run this script.

  python -m uvicorn app.main:app --port 8017   (in backend/)
  python scripts/smoke_imaging.py
"""
from __future__ import annotations

import json

import httpx

from app.services.imaging import encode_png, render_scene

BASE = "http://127.0.0.1:8017"
CONCENTRATION = "Concentration: not determinable from presumptive tests"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        health = client.get("/api/health")
        health.raise_for_status()

        login = client.post(
            "/api/auth/login",
            json={"username": "officer1", "password": "FieldProof#Demo1"},
        )
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        scene = render_scene("#3B1F4A")
        png = encode_png(scene["image"])
        response = client.post(
            "/api/images/analyze",
            headers=headers,
            files={"file": ("scene_ideal.png", png, "image/png")},
            data={
                "kit_code": "MARQUIS",
                "roi": json.dumps(scene["roi"]),
                "time_since_reaction_seconds": "180",
            },
        )
        response.raise_for_status()
        body = response.json()
        match = body["match"]
        print("ideal scene:")
        print(f"  status    : {body['status']}")
        print(f"  gates     : passed={body['quality']['passed']}")
        print(f"  corrected : {body['corrected_colour']['hex']}")
        print(f"  match     : {match['outcome']['code']} (dE {match['delta_e']}, margin {match['margin']})")
        print(f"  concentration line present: {body['concentration'] == CONCENTRATION}")
        assert body["status"] == "OK", body
        assert match["outcome"]["code"] == "PURPLE_BLACK", match
        assert body["concentration"] == CONCENTRATION

        bad = client.post(
            "/api/images/analyze",
            headers=headers,
            files={"file": ("scene_dark.png", encode_png(render_scene("#3B1F4A", lighting=(0.1, 0.1, 0.1))["image"]), "image/png")},
            data={"kit_code": "MARQUIS", "roi": json.dumps(scene["roi"])},
        )
        bad_body = bad.json()
        failed = [g["id"] for g in bad_body["quality"]["gates"] if not g["passed"]]
        print("dark scene:")
        print(f"  status    : {bad_body['status']}")
        print(f"  failed    : {failed}")
        assert bad_body["status"] == "INCONCLUSIVE", bad_body

        card = client.get("/api/reference-card", headers=headers)
        card.raise_for_status()
        print(f"reference card: {len(card.json()['patches'])} patches, {len(card.json()['aruco']['markers'])} markers")

    print("STEP 4 SMOKE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
