"""Step 3 smoke test against a running server (default http://127.0.0.1:8000).

Usage: python scripts/smoke_step3.py [base_url]
Covers: login -> sample -> test -> finalize -> export -> verify (PASS)
        -> tampered verify (FAIL).
"""
from __future__ import annotations

import json
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        token = client.post(
            "/api/auth/login",
            json={"username": "officer1", "password": "FieldProof#Demo1"},
        ).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        sample = client.post(
            "/api/samples",
            json={
                "appearance": "POWDER",
                "colour": "white",
                "gps_lat": 51.5007,
                "gps_lon": -0.1246,
                "gps_accuracy_m": 8,
            },
            headers=h,
        ).json()
        test = client.post(
            f"/api/samples/{sample['id']}/tests",
            json={
                "test_type": "COLOUR_REAGENT",
                "kit_code": "MARQUIS",
                "outcome_code": "PURPLE_BLACK",
            },
            headers=h,
        ).json()
        print(f"analysis after 1 test : {test['analysis']['status']} top={test['analysis']['top_match']['name']}")

        finalized = client.post(f"/api/samples/{sample['id']}/finalize", headers=h).json()
        record = finalized["record"]
        print(f"record                : {record['id']}")
        print(f"status                : {record['status']}")
        print(f"record_hash           : {record['record_hash'][:32]}...")
        print(f"signature             : {record['signature'][:24]}... (key {record['public_key_id']})")

        bundle = finalized["bundle"]
        verify = client.post(
            "/api/verify",
            files={"record": ("record.json", json.dumps(bundle).encode(), "application/json")},
            headers=h,
        ).json()
        print("verify clean          :", verify["overall"])
        for c in verify["checks"]:
            print(f"   [{c['status']:>7}] {c['label']} - {c['detail']}")

        tampered = json.loads(json.dumps(bundle))
        tampered["record"]["status"] = "CONFIRMED_BY_LAB"
        bad = client.post(
            "/api/verify",
            files={"record": ("record.json", json.dumps(tampered).encode(), "application/json")},
            headers=h,
        ).json()
        print("verify tampered       :", bad["overall"])
        for c in bad["checks"]:
            print(f"   [{c['status']:>7}] {c['label']} - {c['detail']}")

        ok = verify["overall"] == "PASS" and bad["overall"] == "FAIL"
        print("RESULT                :", "OK" if ok else "UNEXPECTED")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
