from __future__ import annotations

import hashlib
import io
import json

from app.services.canonical import canonical_json, hash_json, sha256_hex
from app.services.signing import sign_hash, verify_hash

from tests.conftest import login


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _headers(client, username="officer1", password="FieldProof#Demo1"):
    return login(client, username, password)


def _create_sample(client, headers, **kw):
    response = client.post("/api/samples", json=kw, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _add_colour_test(client, headers, sample_id, kit_code, outcome_code, **kw):
    payload = {
        "test_type": "COLOUR_REAGENT",
        "kit_code": kit_code,
        "outcome_code": outcome_code,
        **kw,
    }
    response = client.post(
        f"/api/samples/{sample_id}/tests", json=payload, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def _finalize(client, headers, sample_id):
    response = client.post(f"/api/samples/{sample_id}/finalize", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _make_bundle(client, headers):
    sample = _create_sample(client, headers, appearance="POWDER", colour="white")
    _add_colour_test(client, headers, sample["id"], "MARQUIS", "PURPLE_BLACK")
    result = _finalize(client, headers, sample["id"])
    return sample, result


# --------------------------------------------------------------------------- #
# canonical json + hashing
# --------------------------------------------------------------------------- #
def test_canonical_json_is_sorted_and_compact():
    a = canonical_json({"b": 1, "a": 2, "c": {"z": 1, "y": 2}})
    b = canonical_json({"c": {"y": 2, "z": 1}, "a": 2, "b": 1})
    assert a == b == '{"a":2,"b":2,"c":{"y":2,"z":1}}'.replace('"b":2', '"b":1')
    assert " " not in a
    assert a == canonical_json(json.loads(a))


def test_canonical_json_unicode_stable():
    payload = {"name": "Münich ✅", "n": 1}
    text = canonical_json(payload)
    assert "Münich" in text
    assert hash_json(payload) == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_hash_json_matches_manual_sha256():
    payload = {"a": 1, "b": [1, 2, {"c": None}]}
    expected = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    assert hash_json(payload) == expected
    assert len(expected) == 64


def test_signature_roundtrip_and_tamper_detection():
    digest = hash_json({"record_id": "abc"})
    signature = sign_hash(digest)
    public_pem = __import__("app.services.signing", fromlist=["public_key_pem"]).public_key_pem()

    assert verify_hash(public_pem, digest, signature) is True
    tampered = hash_json({"record_id": "abd"})
    assert verify_hash(public_pem, tampered, signature) is False
    # corrupt a byte inside the signature itself
    idx = 10
    flipped = "A" if signature[idx] != "A" else "B"
    mutated = signature[:idx] + flipped + signature[idx + 1 :]
    assert verify_hash(public_pem, digest, mutated) is False
    assert verify_hash(public_pem, digest, "not-base64!!") is False


# --------------------------------------------------------------------------- #
# record creation + chain
# --------------------------------------------------------------------------- #
def test_finalize_creates_signed_record(client):
    headers = _headers(client)
    before = client.get("/api/records?page_size=1", headers=headers).json()

    sample, result = _make_bundle(client, headers)
    record = result["record"]

    assert record["status"] in {
        "WEAK_PRESUMPTIVE",
        "PRESUMPTIVE",
        "STRONG_PRESUMPTIVE",
        "NO_MATCH",
        "INCONCLUSIVE",
        "CONFIRMED_BY_LAB",
    }
    assert len(record["record_hash"]) == 64
    assert record["signature"]
    assert record["public_key_id"].startswith("fp-p256-")

    after = client.get("/api/records?page_size=1", headers=headers).json()
    assert after["total"] == before["total"] + 1

    # payload hard rules
    payload = json.loads(result["bundle"]["canonical_json"])
    assert "PRESUMPTIVE FIELD RESULT ONLY" in payload["disclaimer"]
    assert payload["disclaimer"] == result["analysis"]["disclaimer"]
    assert payload["concentration"].startswith("Concentration: not determinable")
    assert payload["previous_record_hash"] is None or payload["previous_record_hash"]
    assert payload["engine_version"]


def test_chain_links_successive_records(client):
    headers = _headers(client)
    tip_before = client.get("/api/records?page_size=1", headers=headers).json()
    tip_hash = tip_before["items"][0]["record_hash"] if tip_before["items"] else None

    sample_a = _create_sample(client, headers)
    _add_colour_test(client, headers, sample_a["id"], "MARQUIS", "PURPLE_BLACK")
    rec_a = _finalize(client, headers, sample_a["id"])["record"]

    sample_b = _create_sample(client, headers)
    _add_colour_test(client, headers, sample_b["id"], "SCOTT", "BLUE")
    rec_b = _finalize(client, headers, sample_b["id"])["record"]

    assert rec_a["previous_record_hash"] == tip_hash
    assert rec_b["previous_record_hash"] == rec_a["record_hash"]
    assert rec_a["record_hash"] != rec_b["record_hash"]


def test_records_are_append_only(client):
    from app.database import SessionFactory
    from app.models import Record
    from sqlalchemy import select

    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)

    with SessionFactory() as db:
        record = db.scalar(select(Record).where(Record.id == result["record"]["id"]))
        record.status = "NO_MATCH"
        try:
            db.commit()
            raised = False
        except Exception:  # noqa: BLE001
            db.rollback()
            raised = True
        assert raised, "UPDATE on records must be rejected"

        try:
            db.delete(record)
            db.commit()
            raised = False
        except Exception:  # noqa: BLE001
            db.rollback()
            raised = True
        assert raised, "DELETE on records must be rejected"


def test_cannot_finalize_twice_or_add_tests_afterwards(client):
    headers = _headers(client)
    sample = _create_sample(client, headers)
    _add_colour_test(client, headers, sample["id"], "MARQUIS", "BROWN")
    _finalize(client, headers, sample["id"])

    again = client.post(f"/api/samples/{sample['id']}/finalize", headers=headers)
    assert again.status_code == 409

    late = client.post(
        f"/api/samples/{sample['id']}/tests",
        json={
            "test_type": "COLOUR_REAGENT",
            "kit_code": "SCOTT",
            "outcome_code": "BLUE",
        },
        headers=headers,
    )
    assert late.status_code == 409


def test_finalize_requires_at_least_one_test(client):
    headers = _headers(client)
    sample = _create_sample(client, headers)
    response = client.post(f"/api/samples/{sample['id']}/finalize", headers=headers)
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# roles / validation
# --------------------------------------------------------------------------- #
def test_officer_cannot_enter_lab_confirmatory(client):
    headers = _headers(client)
    sample = _create_sample(client, headers)
    response = client.post(
        f"/api/samples/{sample['id']}/tests",
        json={
            "test_type": "LAB_CONFIRMATORY",
            "input": {"method": "GC-MS", "compound": "Cocaine (hydrochloride salt)"},
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_lab_user_can_enter_lab_confirmatory(client):
    officer = _headers(client)
    lab = _headers(client, "lab1", "FieldProof#Lab1")
    sample = _create_sample(client, officer)

    response = client.post(
        f"/api/samples/{sample['id']}/tests",
        json={
            "test_type": "LAB_CONFIRMATORY",
            "input": {
                "method": "GC-MS",
                "compound": "Cocaine (hydrochloride salt)",
                "lab_reference": "FS-9",
                "purity_percent": 64.0,
            },
        },
        headers=lab,
    )
    assert response.status_code == 200, response.text
    analysis = response.json()["analysis"]
    assert analysis["status"] == "CONFIRMED_BY_LAB"
    assert "64.0" in analysis["concentration"]

    finalized = _finalize(client, officer, sample["id"])
    assert finalized["record"]["status"] == "CONFIRMED_BY_LAB"
    assert "Purity: 64.0%" in finalized["analysis"]["concentration"]


def test_override_requires_reason_and_is_audited(client):
    headers = _headers(client)
    sample = _create_sample(client, headers)

    bad = client.post(
        f"/api/samples/{sample['id']}/tests",
        json={
            "test_type": "COLOUR_REAGENT",
            "kit_code": "MARQUIS",
            "outcome_code": "BROWN",
            "is_override": True,
            "overridden_outcome_code": "PURPLE_BLACK",
        },
        headers=headers,
    )
    assert bad.status_code == 422

    good = client.post(
        f"/api/samples/{sample['id']}/tests",
        json={
            "test_type": "COLOUR_REAGENT",
            "kit_code": "MARQUIS",
            "outcome_code": "BROWN",
            "is_override": True,
            "overridden_outcome_code": "PURPLE_BLACK",
            "override_reason": "Glare on pouch; read against the reference card.",
        },
        headers=headers,
    )
    assert good.status_code == 200, good.text

    admin = _headers(client, "admin", "FieldProof#Admin1")
    listed = client.get(f"/api/records?q={sample['id']}", headers=admin)
    assert listed.status_code == 200

    from app.database import SessionFactory
    from app.models import AuditLog
    from sqlalchemy import select

    with SessionFactory() as db:
        rows = db.scalars(
            select(AuditLog).where(AuditLog.action == "test.override")
        ).all()
        assert rows, "override must be recorded in the audit trail"
        assert rows[-1].detail.get("override_reason")


def test_unknown_kit_or_outcome_rejected(client):
    headers = _headers(client)
    sample = _create_sample(client, headers)
    bad_kit = client.post(
        f"/api/samples/{sample['id']}/tests",
        json={"test_type": "COLOUR_REAGENT", "kit_code": "NOPE", "outcome_code": "X"},
        headers=headers,
    )
    assert bad_kit.status_code == 422

    bad_outcome = client.post(
        f"/api/samples/{sample['id']}/tests",
        json={
            "test_type": "COLOUR_REAGENT",
            "kit_code": "MARQUIS",
            "outcome_code": "NOT_A_COLOUR",
        },
        headers=headers,
    )
    assert bad_outcome.status_code == 422


def test_analysis_endpoint_reflects_added_tests(client):
    headers = _headers(client)
    sample = _create_sample(client, headers)
    _add_colour_test(client, headers, sample["id"], "MARQUIS", "PURPLE_BLACK")
    analysis = client.get(f"/api/samples/{sample['id']}/analysis", headers=headers).json()
    # purple-black alone is shared by MDMA and heroin in the seeded data
    assert analysis["top_match"]["code"] in {"MDMA", "HEROIN"}
    assert analysis["counts"]["tests_entered"] == 1


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #
def test_verify_endpoint_passes_for_fresh_record(client):
    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)
    bundle = result["bundle"]
    assert "PRIVATE" not in json.dumps(bundle)

    files = {"record": ("record.json", json.dumps(bundle).encode(), "application/json")}
    response = client.post("/api/verify", files=files, headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["overall"] == "PASS", body
    statuses = {c["id"]: c["status"] for c in body["checks"]}
    assert statuses["record_hash"] == "PASS"
    assert statuses["signature"] == "PASS"
    assert statuses["chain"] == "PASS"
    assert statuses["registry"] == "PASS"


def test_verify_detects_tampered_canonical_json(client):
    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)
    bundle = result["bundle"]
    payload = json.loads(bundle["canonical_json"])
    payload["status"] = "CONFIRMED_BY_LAB"  # attacker edits the payload
    bundle["canonical_json"] = canonical_json(payload)

    files = {"record": ("record.json", json.dumps(bundle).encode(), "application/json")}
    body = client.post("/api/verify", files=files, headers=headers).json()
    statuses = {c["id"]: c["status"] for c in body["checks"]}
    assert body["overall"] == "FAIL"
    assert statuses["record_hash"] == "FAIL"
    assert statuses["signature"] == "FAIL"


def test_verify_detects_tampered_record_fields(client):
    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)
    bundle = result["bundle"]
    bundle["record"]["status"] = "CONFIRMED_BY_LAB"  # fields edited, canonical kept

    files = {"record": ("record.json", json.dumps(bundle).encode(), "application/json")}
    body = client.post("/api/verify", files=files, headers=headers).json()
    statuses = {c["id"]: c["status"] for c in body["checks"]}
    assert statuses["record_hash"] == "FAIL"
    assert "canonical_json does not match" in [
        c["detail"] for c in body["checks"] if c["id"] == "record_hash"
    ][0]


def test_verify_detects_chain_break(client):
    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)
    bundle = result["bundle"]
    # keep canonical_json consistent by rebuilding everything, but break the link
    payload = json.loads(bundle["canonical_json"])
    payload["previous_record_hash"] = "0" * 64
    bundle["record"] = payload
    bundle["canonical_json"] = canonical_json(payload)
    bundle["record_hash"] = sha256_hex(bundle["canonical_json"].encode("utf-8"))
    # signature is now stale -> also fails, and registry cross-check flags it
    files = {"record": ("record.json", json.dumps(bundle).encode(), "application/json")}
    body = client.post("/api/verify", files=files, headers=headers).json()
    statuses = {c["id"]: c["status"] for c in body["checks"]}
    assert body["overall"] == "FAIL"
    assert statuses["chain"] == "FAIL"


def test_verify_image_hash_pass_and_fail(client):
    headers = _headers(client)
    image_bytes = b"\xff\xd8\xff\xe0FAKEJPEG" + bytes(range(256)) * 4

    upload = client.post(
        "/api/images",
        files={"file": ("pouch.jpg", io.BytesIO(image_bytes), "image/jpeg")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    digest = upload.json()["sha256"]
    assert digest == hashlib.sha256(image_bytes).hexdigest()

    sample = _create_sample(client, headers, photo_sha256=digest)
    _add_colour_test(
        client, headers, sample["id"], "MARQUIS", "PURPLE_BLACK", image_sha256=digest
    )
    result = _finalize(client, headers, sample["id"])
    bundle = result["bundle"]
    assert bundle["record"]["image_sha256"] == digest

    ok = client.post(
        "/api/verify",
        files={
            "record": ("record.json", json.dumps(bundle).encode(), "application/json"),
            "image": ("pouch.jpg", io.BytesIO(image_bytes), "image/jpeg"),
        },
        headers=headers,
    ).json()
    statuses = {c["id"]: c["status"] for c in ok["checks"]}
    assert statuses["image_hash"] == "PASS", ok
    assert ok["overall"] == "PASS"

    tampered = client.post(
        "/api/verify",
        files={
            "record": ("record.json", json.dumps(bundle).encode(), "application/json"),
            "image": ("pouch.jpg", io.BytesIO(image_bytes + b"!"), "image/jpeg"),
        },
        headers=headers,
    ).json()
    statuses = {c["id"]: c["status"] for c in tampered["checks"]}
    assert statuses["image_hash"] == "FAIL"
    assert tampered["overall"] == "FAIL"

    # hard rule: change exactly ONE existing byte of the image -> image_hash
    # must fail (and only because of the image), not some other check
    mutated = bytearray(image_bytes)
    mutated[120] ^= 0xFF
    assert bytes(mutated) != image_bytes
    one_byte = client.post(
        "/api/verify",
        files={
            "record": ("record.json", json.dumps(bundle).encode(), "application/json"),
            "image": ("pouch.jpg", io.BytesIO(bytes(mutated)), "image/jpeg"),
        },
        headers=headers,
    ).json()
    one_byte_statuses = {c["id"]: c["status"] for c in one_byte["checks"]}
    assert one_byte_statuses["image_hash"] == "FAIL", one_byte
    assert one_byte_statuses["record_hash"] == "PASS", one_byte
    assert one_byte_statuses["signature"] == "PASS", one_byte
    assert one_byte["overall"] == "FAIL"
    assert "SHA-256 mismatch" in [
        c["detail"] for c in one_byte["checks"] if c["id"] == "image_hash"
    ][0]

    # stored copy comes back byte-identical
    fetched = client.get(f"/api/images/{digest}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.content == image_bytes


def test_verify_fails_when_exactly_one_image_byte_is_changed(client):
    """Hard rule: flip ONE byte of the stored image -> image_hash must FAIL."""
    headers = _headers(client)
    image_bytes = b"\xff\xd8\xff\xe0ONEBYTE" + bytes(range(256)) * 2

    upload = client.post(
        "/api/images",
        files={"file": ("pouch.jpg", io.BytesIO(image_bytes), "image/jpeg")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    digest = upload.json()["sha256"]

    sample = _create_sample(client, headers, photo_sha256=digest)
    _add_colour_test(
        client, headers, sample["id"], "MARQUIS", "PURPLE_BLACK", image_sha256=digest
    )
    bundle = _finalize(client, headers, sample["id"])["bundle"]

    mutated = bytearray(image_bytes)
    mutated[50] ^= 0xFF  # exactly one existing byte, same length
    assert len(mutated) == len(image_bytes)
    assert bytes(mutated) != image_bytes

    body = client.post(
        "/api/verify",
        files={
            "record": ("record.json", json.dumps(bundle).encode(), "application/json"),
            "image": ("pouch.jpg", io.BytesIO(bytes(mutated)), "image/jpeg"),
        },
        headers=headers,
    ).json()
    statuses = {c["id"]: c["status"] for c in body["checks"]}
    assert statuses["image_hash"] == "FAIL", body
    assert statuses["record_hash"] == "PASS", body
    assert statuses["signature"] == "PASS", body
    assert statuses["chain"] == "PASS", body
    assert body["overall"] == "FAIL"


# --------------------------------------------------------------------------- #
# log + export + audit
# --------------------------------------------------------------------------- #
def test_records_list_filters_and_pagination(client):
    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)
    record_id = result["record"]["id"]

    page = client.get("/api/records?page_size=1&page=1", headers=headers).json()
    assert page["page_size"] == 1
    assert len(page["items"]) == 1
    assert page["total"] >= 1

    hit = client.get(f"/api/records?q={record_id}", headers=headers).json()
    assert hit["total"] == 1
    assert hit["items"][0]["id"] == record_id

    by_status = client.get(
        f"/api/records?status_filter={result['record']['status']}", headers=headers
    ).json()
    assert by_status["total"] >= 1

    by_kit = client.get("/api/records?kit=MARQUIS", headers=headers).json()
    assert by_kit["total"] >= 1

    # the substance filter matches on the record's own top match (a lone
    # purple-black reading is a genuine MDMA/heroin tie - use whichever won)
    top_name = hit["items"][0]["top_substance_name"]
    assert top_name
    by_substance = client.get(
        f"/api/records?substance={top_name}", headers=headers
    ).json()
    assert by_substance["total"] >= 1


def test_record_detail_includes_verification_and_audit(client):
    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)
    record_id = result["record"]["id"]

    detail = client.get(f"/api/records/{record_id}", headers=headers).json()
    assert detail["verification"]["overall"] == "PASS"
    assert detail["analysis"]["disclaimer"]
    assert detail["bundle"]["record"]["record_id"] == record_id
    actions = [a["action"] for a in detail["audit_trail"]]
    assert "record.view" in actions

    # viewing again appends another audit row
    client.get(f"/api/records/{record_id}", headers=headers)
    detail2 = client.get(f"/api/records/{record_id}", headers=headers).json()
    assert [a["action"] for a in detail2["audit_trail"]].count("record.view") >= 2


def test_export_json_and_csv(client):
    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)
    record_id = result["record"]["id"]

    json_export = client.get(f"/api/records/{record_id}/export?format=json", headers=headers)
    assert json_export.status_code == 200
    bundle = json.loads(json_export.text)
    assert bundle["format"] == "fieldproof-record/1"
    assert bundle["record"]["disclaimer"]
    # hard rule: every export carries the disclaimer AND the exact
    # concentration line
    from app.enums import CONCENTRATION_NOT_DETERMINABLE, DISCLAIMER

    assert bundle["disclaimer"] == DISCLAIMER
    assert bundle["concentration_note"] == CONCENTRATION_NOT_DETERMINABLE
    assert "PRIVATE KEY" not in json_export.text

    csv_export = client.get(f"/api/records/{record_id}/export?format=csv", headers=headers)
    assert csv_export.status_code == 200
    assert "record_hash" in csv_export.text
    assert DISCLAIMER in csv_export.text
    assert CONCENTRATION_NOT_DETERMINABLE in csv_export.text

    list_csv = client.get("/api/records/export", headers=headers)
    assert list_csv.status_code == 200
    assert "record_id" in list_csv.text
    assert DISCLAIMER in list_csv.text
    assert CONCENTRATION_NOT_DETERMINABLE in list_csv.text

    from app.database import SessionFactory
    from app.models import AuditLog
    from sqlalchemy import select

    with SessionFactory() as db:
        exports = db.scalars(
            select(AuditLog).where(AuditLog.action == "record.export")
        ).all()
        assert len(exports) >= 3


def test_private_key_material_never_exposed(client):
    headers = _headers(client)
    _sample, result = _make_bundle(client, headers)
    record_id = result["record"]["id"]
    for url in (f"/api/records/{record_id}", f"/api/records/{record_id}/export?format=json"):
        text = client.get(url, headers=headers).text
        assert "BEGIN PRIVATE KEY" not in text
        assert "BEGIN EC PRIVATE" not in text
    admin = _headers(client, "admin", "FieldProof#Admin1")
    keys = client.get("/api/admin/signing-keys", headers=admin).json()["items"]
    assert keys and "BEGIN PRIVATE" not in json.dumps(keys)
    assert keys[0]["public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")
