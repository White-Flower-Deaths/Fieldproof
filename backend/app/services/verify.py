"""Record verification: image hash, record hash, signature, chain integrity."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import CONCENTRATION_NOT_DETERMINABLE
from ..models import Record, SigningKey
from .canonical import canonical_json, sha256_hex
from .signing import verify_hash

CHECK_LABELS = {
    "image_hash": "Original image hash (SHA-256)",
    "record_hash": "Record hash (SHA-256 of canonical JSON)",
    "signature": "Digital signature (ECDSA P-256)",
    "chain": "Hash-chain integrity",
    "registry": "Matches server registry copy",
}


def _check(check_id: str, status: str, detail: str) -> dict[str, str]:
    return {
        "id": check_id,
        "label": CHECK_LABELS[check_id],
        "status": status,
        "detail": detail,
    }


def _extract(obj: dict[str, Any]) -> dict[str, Any]:
    """Normalise a bundle or bare record payload."""
    if "canonical_json" in obj or "record_hash" in obj:
        record_obj = obj.get("record")
        if record_obj is None and obj.get("canonical_json"):
            record_obj = json.loads(obj["canonical_json"])
        return {
            "record": record_obj,
            "canonical_json": obj.get("canonical_json"),
            "record_hash": obj.get("record_hash"),
            "signature": obj.get("signature"),
            "public_key_id": obj.get("public_key_id"),
            "public_key_pem": obj.get("public_key_pem"),
        }
    return {
        "record": obj,
        "canonical_json": None,
        "record_hash": None,
        "signature": None,
        "public_key_id": None,
        "public_key_pem": None,
    }


def verify_payload(
    db: Session, payload: dict[str, Any], image_bytes: bytes | None = None
) -> dict[str, Any]:
    warnings: list[str] = []
    try:
        parts = _extract(payload)
        record_obj = parts["record"]
        if not isinstance(record_obj, dict):
            raise ValueError("bundle does not contain a record payload")
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            "overall": "FAIL",
            "record_id": None,
            "checks": [
                _check("record_hash", "FAIL", f"Could not read record: {exc}")
            ],
            "warnings": warnings,
        }

    record_id = record_obj.get("record_id")

    # ---------------------------------------------------------------- image hash
    expected_image = record_obj.get("image_sha256")
    if image_bytes is not None:
        if expected_image:
            actual = sha256_hex(image_bytes)
            image_check = (
                _check(
                    "image_hash",
                    "PASS",
                    f"Image SHA-256 matches the record ({actual[:16]}…).",
                )
                if actual == expected_image
                else _check(
                    "image_hash",
                    "FAIL",
                    f"Image SHA-256 mismatch: record stores {expected_image}, "
                    f"supplied image hashes to {actual}.",
                )
            )
        else:
            image_check = _check(
                "image_hash",
                "SKIPPED",
                "Record contains no image hash, so there is nothing to compare.",
            )
    elif expected_image:
        image_check = _check(
            "image_hash",
            "SKIPPED",
            "No image supplied for this verification run.",
        )
        warnings.append("Image not supplied - image hash check skipped.")
    else:
        image_check = _check(
            "image_hash", "SKIPPED", "Record contains no image hash."
        )

    # --------------------------------------------------------------- record hash
    computed_canonical = canonical_json(record_obj)
    stored_canonical = parts["canonical_json"]
    hash_failures: list[str] = []
    if stored_canonical is not None and stored_canonical != computed_canonical:
        hash_failures.append(
            "canonical_json does not match the record fields (the payload was edited "
            "after signing)"
        )
    canonical_used = stored_canonical or computed_canonical
    digest = sha256_hex(canonical_used.encode("utf-8"))
    provided_hash = parts["record_hash"]
    if not provided_hash:
        hash_failures.append("bundle does not include a record_hash")
    elif provided_hash != digest:
        hash_failures.append(
            f"hash mismatch: bundle says {provided_hash}, recomputed {digest}"
        )

    record_check = (
        _check(
            "record_hash",
            "PASS",
            f"SHA-256 of canonical JSON matches ({digest[:16]}…).",
        )
        if not hash_failures
        else _check("record_hash", "FAIL", "; ".join(hash_failures))
    )

    # ----------------------------------------------------------------- signature
    signature = parts["signature"]
    public_pem: str | None = None
    key_source = ""
    if parts["public_key_id"]:
        row = db.scalar(
            select(SigningKey).where(SigningKey.key_id == parts["public_key_id"])
        )
        if row:
            public_pem = row.public_key_pem
            key_source = "server key registry"
    if not public_pem and parts["public_key_pem"]:
        public_pem = parts["public_key_pem"]
        key_source = "bundled public key (not in this server's registry)"
        warnings.append(
            "Public key was taken from the uploaded bundle and is not in the "
            "server key registry - establish key authenticity separately."
        )

    if not signature:
        sig_check = _check("signature", "FAIL", "Bundle does not include a signature.")
    elif not public_pem:
        sig_check = _check(
            "signature",
            "FAIL",
            f"Public key for key id {parts['public_key_id'] or 'unknown'} not found.",
        )
    elif verify_hash(public_pem, digest, signature):
        sig_check = _check(
            "signature",
            "PASS",
            f"Signature valid for hash {digest[:16]}… (key {parts['public_key_id']}, "
            f"via {key_source}).",
        )
    else:
        sig_check = _check(
            "signature",
            "FAIL",
            "ECDSA verification failed - the signature does not match this hash "
            "and public key.",
        )

    # --------------------------------------------------------------------- chain
    prev_hash = record_obj.get("previous_record_hash")
    stored = db.get(Record, record_id) if record_id else None
    chain_failures: list[str] = []
    chain_notes: list[str] = []

    if stored is not None:
        if stored.record_hash != digest:
            chain_failures.append(
                "this record exists in the registry with a different hash "
                f"({stored.record_hash[:16]}…) - the uploaded copy was modified"
            )
        if prev_hash != stored.previous_record_hash:
            chain_failures.append("previous_record_hash differs from the registry copy")
        if prev_hash:
            previous = db.scalar(
                select(Record).where(Record.record_hash == prev_hash)
            )
            if previous is None:
                chain_failures.append("previous record not found in the registry")
            elif previous.server_timestamp > stored.server_timestamp:
                chain_failures.append("previous record is newer than this record")
            else:
                chain_notes.append(f"links back to {previous.id}")
        else:
            older = db.scalar(
                select(Record.id)
                .where(Record.server_timestamp < stored.server_timestamp)
                .limit(1)
            )
            if older:
                chain_failures.append(
                    "record claims to be the first in the chain, but older records exist"
                )
            else:
                chain_notes.append("first record in the chain")
    else:
        if prev_hash:
            previous = db.scalar(select(Record).where(Record.record_hash == prev_hash))
            if previous is None:
                chain_failures.append(
                    "previous record hash not found in this server's registry"
                )
            else:
                chain_notes.append(f"links back to registry record {previous.id}")
        else:
            chain_notes.append(
                "no previous link and record not in this registry - chain cannot be "
                "confirmed here"
            )
            warnings.append(
                "Record is not present in this server's registry; chain start could "
                "not be confirmed."
            )

    chain_check = (
        _check("chain", "PASS", "; ".join(chain_notes) or "chain intact")
        if not chain_failures
        else _check("chain", "FAIL", "; ".join(chain_failures))
    )

    # ------------------------------------------------------------------ registry
    checks = [image_check, record_check, sig_check, chain_check]
    if stored is not None:
        registry_ok = (
            stored.record_hash == digest
            and stored.canonical_json == computed_canonical
            and (stored_canonical is None or stored_canonical == stored.canonical_json)
        )
        checks.append(
            _check(
                "registry",
                "PASS",
                "Uploaded record is byte-identical to the server registry copy.",
            )
            if registry_ok
            else _check(
                "registry",
                "FAIL",
                "Uploaded record differs from the server registry copy "
                "(fields or canonical JSON were modified after signing).",
            )
        )

    overall = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "PASS"
    return {
        "overall": overall,
        "record_id": record_id,
        "status": record_obj.get("status"),
        "sample_id": record_obj.get("sample_id"),
        "sample_code": record_obj.get("sample_code"),
        "server_timestamp": record_obj.get("server_timestamp"),
        "checks": checks,
        "warnings": warnings,
        "disclaimer": record_obj.get("disclaimer"),
        "concentration": record_obj.get("concentration"),
        "concentration_note": CONCENTRATION_NOT_DETERMINABLE,
    }


def verify_record(db: Session, record: Record, image_bytes: bytes | None = None) -> dict:
    from .records import bundle_with_key

    return verify_payload(db, bundle_with_key(db, record), image_bytes)
