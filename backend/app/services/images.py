"""Original image storage: unmodified bytes on disk, named by SHA-256."""
from __future__ import annotations

from pathlib import Path

from ..config import settings

IMAGES_DIR = Path("data") / "images"
_EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/bmp": ".bmp",
}


def _resolve_dir() -> Path:
    # keep images next to the database file when using the default sqlite setup
    db_url = settings.database_url
    if db_url.startswith("sqlite") and "///" in db_url:
        db_path = db_url.split("///", 1)[-1]
        base = Path(db_path).parent
        if str(base) not in ("", "."):
            return base / "images"
    return IMAGES_DIR


def save_image(data: bytes, content_type: str | None = None) -> tuple[str, str]:
    """Persist raw bytes unmodified. Returns (sha256, relative filename)."""
    from .canonical import sha256_hex

    digest = sha256_hex(data)
    ext = _EXT_BY_TYPE.get((content_type or "").lower(), ".bin")
    target_dir = _resolve_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{digest}{ext}"
    if not path.exists():  # never rewrite an existing (hash-named) file
        path.write_bytes(data)
    return digest, path.name


def load_image(sha256_hex_str: str) -> bytes | None:
    target_dir = _resolve_dir()
    if not target_dir.exists():
        return None
    for path in target_dir.glob(f"{sha256_hex_str}.*"):
        return path.read_bytes()
    return None


def image_exists(sha256_hex_str: str) -> bool:
    return load_image(sha256_hex_str) is not None
