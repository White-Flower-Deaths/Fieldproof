"""Canonical JSON serialisation and hashing.

Canonical form: UTF-8, object keys sorted, no insignificant whitespace,
no NaN/Infinity, `null` for JSON null. The same payload always produces the
same bytes, which is what makes SHA-256 hash-chaining verifiable.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_json(payload: Any) -> str:
    return sha256_hex(canonical_json(payload).encode("utf-8"))


def hash_image(data: bytes) -> str:
    """SHA-256 of the original, unmodified image bytes."""
    return sha256_hex(data)
