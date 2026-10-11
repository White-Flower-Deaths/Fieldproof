"""ECDSA P-256 record signing.

The private key is loaded from an environment variable or a file on the server
and NEVER leaves the process. Only the public half is stored in `signing_keys`
and served to clients for verification.

Signature scheme: ECDSA over P-256 over the SHA-256 digest of the canonical
record JSON (Prehashed SHA-256).
"""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from ..config import settings

DEV_KEY_PATH = Path("data") / "dev_signing_key.pem"
ALGORITHM = "ECDSA-P256-SHA256"

_private_key_cache: ec.EllipticCurvePrivateKey | None = None


class SigningError(Exception):
    pass


def _generate_dev_key() -> bytes:
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    DEV_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEV_KEY_PATH.write_bytes(pem)
    try:
        os.chmod(DEV_KEY_PATH, 0o600)
    except OSError:  # pragma: no cover - platform dependent
        pass
    return pem


def _load_private_key_pem() -> tuple[bytes, str]:
    env_name = settings.signing_key_env
    pem = os.environ.get(env_name)
    if pem and pem.strip():
        return pem.strip().encode("utf-8"), f"env:{env_name}"

    if settings.signing_key_file:
        path = Path(settings.signing_key_file)
        if not path.exists():
            raise SigningError(f"signing key file not found: {path}")
        return path.read_bytes(), f"file:{path}"

    if not settings.is_production:
        if DEV_KEY_PATH.exists():
            return DEV_KEY_PATH.read_bytes(), f"file:{DEV_KEY_PATH} (dev key)"
        return _generate_dev_key(), f"file:{DEV_KEY_PATH} (dev key, auto-generated)"

    raise SigningError(
        "No signing key configured. Set "
        f"{env_name} or FIELDPROOF_SIGNING_KEY_FILE in production."
    )


def get_private_key() -> ec.EllipticCurvePrivateKey:
    global _private_key_cache
    if _private_key_cache is None:
        pem, _source = _load_private_key_pem()
        key = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey):
            raise SigningError("signing key must be an ECDSA private key")
        if not isinstance(key.curve, ec.SECP256R1):
            raise SigningError("signing key must use the P-256 (secp256r1) curve")
        _private_key_cache = key
    return _private_key_cache


def signing_key_source() -> str:
    _pem, source = _load_private_key_pem()
    return source


def public_key_pem(private_key: ec.EllipticCurvePrivateKey | None = None) -> str:
    key = private_key or get_private_key()
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def key_id_for(pem_public: str) -> str:
    digest = hashlib.sha256(pem_public.encode("utf-8")).hexdigest()
    return f"fp-p256-{digest[:16]}"


def sign_hash(record_hash_hex: str) -> str:
    """Sign the record hash. Returns base64(signature)."""
    private_key = get_private_key()
    digest = bytes.fromhex(record_hash_hex)
    signature = private_key.sign(digest, ec.ECDSA(Prehashed(hashes.SHA256())))
    return base64.b64encode(signature).decode("ascii")


def verify_hash(public_pem: str, record_hash_hex: str, signature_b64: str) -> bool:
    try:
        key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
        if not isinstance(key, ec.EllipticCurvePublicKey):
            return False
        key.verify(
            base64.b64decode(signature_b64),
            bytes.fromhex(record_hash_hex),
            ec.ECDSA(Prehashed(hashes.SHA256())),
        )
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
