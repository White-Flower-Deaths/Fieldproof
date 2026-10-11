"""End-to-end chain smoke: login -> sample -> test -> analysis -> finalize -> verify.

Run against a live server (default http://127.0.0.1:8000):

    python scripts/smoke_e2e.py [base_url]
"""
from __future__ import annotations

import io
import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
CONCENTRATION = "Concentration: not determinable from presumptive tests"
DISCLAIMER_MARK = "PRESUMPTIVE FIELD RESULT ONLY"


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    return ok


def main() -> int:
    results: list[bool] = []
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        # ---------------------------------------------------------- health
        health = client.get("/api/health")
        results.append(check("backend health", health.status_code == 200, f"{health.status_code}"))

        # ----------------------------------------------------------- login
        login = client.post(
            "/api/auth/login",
            json={"username": "officer1", "password": "FieldProof#Demo1"},
        )
        ok = login.status_code == 200 and "access_token" in login.json()
        results.append(check("login (officer1)", ok, f"{login.status_code}"))
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # ---------------------------------------------------------- image
        from app.services.imaging import encode_png, render_scene

        scene = render_scene("#3B1F4A")
        png = encode_png(scene["image"])
        upload = client.post(
            "/api/images",
            files={"file": ("scene.png", io.BytesIO(png), "image/png")},
            headers=headers,
        )
        ok = upload.status_code == 201
        image_sha = upload.json().get("sha256") if ok else None
        results.append(check("upload image", ok, f"{upload.status_code} sha={str(image_sha)[:12]}"))

        # --------------------------------------------------------- sample
        sample = client.post(
            "/api/samples",
            json={
                "appearance": "POWDER",
                "colour": "off-white",
                "photo_sha256": image_sha,
            },
            headers=headers,
        )
        ok = sample.status_code == 201
        results.append(check("create sample", ok, f"{sample.status_code}"))
        sample_id = sample.json().get("id")

        # ----------------------------------------------------------- test
        test = client.post(
            f"/api/samples/{sample_id}/tests",
            json={
                "test_type": "COLOUR_REAGENT",
                "kit_code": "MARQUIS",
                "outcome_code": "PURPLE_BLACK",
                "image_sha256": image_sha,
                "time_since_reaction_seconds": 90,
            },
            headers=headers,
        )
        ok = test.status_code == 200
        results.append(check("add test (MARQUIS/PURPLE_BLACK)", ok, f"{test.status_code}"))

        # ------------------------------------------------------- analysis
        analysis = client.get(f"/api/samples/{sample_id}/analysis", headers=headers)
        body = analysis.json() if analysis.status_code == 200 else {}
        ok = (
            analysis.status_code == 200
            and body.get("disclaimer", "").startswith(DISCLAIMER_MARK)
            and body.get("concentration") == CONCENTRATION
            and body.get("top_match") is not None
        )
        results.append(
            check(
                "get analysis",
                ok,
                f"{analysis.status_code} status={body.get('status')} "
                f"top={((body.get('top_match') or {}).get('code'))}",
            )
        )

        # -------------------------------------------------------- finalize
        final = client.post(f"/api/samples/{sample_id}/finalize", headers=headers)
        fbody = final.json() if final.status_code == 200 else {}
        record = fbody.get("record") or {}
        bundle = fbody.get("bundle") or {}
        payload = bundle.get("record") or {}
        ok = (
            final.status_code == 200
            and len(record.get("record_hash", "")) == 64
            and record.get("signature")
            and fbody.get("disclaimer", "").startswith(DISCLAIMER_MARK)
            and payload.get("disclaimer", "").startswith(DISCLAIMER_MARK)
            and payload.get("concentration") == CONCENTRATION
            and fbody.get("analysis", {}).get("concentration") == CONCENTRATION
        )
        results.append(
            check(
                "finalize (signed record)",
                ok,
                f"{final.status_code} hash={str(record.get('record_hash'))[:12]}… "
                f"status={record.get('status')}",
            )
        )

        # ------------------------------------------ analysis (record copy)
        # --------------------------------------------------------- verify
        verify = client.post(
            "/api/verify",
            files={
                "record": (
                    "record.json",
                    io.BytesIO(json.dumps(bundle).encode()),
                    "application/json",
                ),
                "image": ("scene.png", io.BytesIO(png), "image/png"),
            },
            headers=headers,
        )
        vbody = verify.json() if verify.status_code == 200 else {}
        statuses = {c["id"]: c["status"] for c in vbody.get("checks", [])}
        ok = (
            verify.status_code == 200
            and vbody.get("overall") == "PASS"
            and statuses.get("image_hash") == "PASS"
            and statuses.get("record_hash") == "PASS"
            and statuses.get("signature") == "PASS"
            and statuses.get("chain") == "PASS"
        )
        results.append(
            check(
                "verify (record + image)",
                ok,
                f"{verify.status_code} overall={vbody.get('overall')} {statuses}",
            )
        )

        # ------------------------------------------------ tamper regression
        tampered_record = json.loads(json.dumps(bundle))
        tampered_record["record"]["status"] = "CONFIRMED_BY_LAB"
        bad = client.post(
            "/api/verify",
            files={
                "record": (
                    "record.json",
                    io.BytesIO(json.dumps(tampered_record).encode()),
                    "application/json",
                )
            },
            headers=headers,
        ).json()
        bad_statuses = {c["id"]: c["status"] for c in bad.get("checks", [])}
        ok = bad.get("overall") == "FAIL" and bad_statuses.get("record_hash") == "FAIL"
        results.append(
            check("verify detects tampered field", ok, f"overall={bad.get('overall')} {bad_statuses}")
        )

        mutated = bytearray(png)
        mutated[200] ^= 0xFF
        bad_img = client.post(
            "/api/verify",
            files={
                "record": ("record.json", io.BytesIO(json.dumps(bundle).encode()), "application/json"),
                "image": ("scene.png", io.BytesIO(bytes(mutated)), "image/png"),
            },
            headers=headers,
        ).json()
        bad_img_statuses = {c["id"]: c["status"] for c in bad_img.get("checks", [])}
        ok = bad_img.get("overall") == "FAIL" and bad_img_statuses.get("image_hash") == "FAIL"
        results.append(
            check("verify detects 1-byte image change", ok, f"overall={bad_img.get('overall')} {bad_img_statuses}")
        )

    print("E2E SMOKE:", "PASS" if all(results) else "FAIL")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
