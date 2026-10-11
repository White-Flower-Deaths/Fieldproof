"""Generate demo/test scene images under docs/images (README + manual testing).

Run:  python scripts/generate_test_images.py
"""
from __future__ import annotations

from pathlib import Path

from app.services.imaging import encode_png, render_scene

OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "images"

CASES = {
    "scene_ideal.png": {},
    "scene_warm_light.png": {"lighting": (1.18, 0.96, 0.78)},
    "scene_blurred.png": {"blur_ksize": 21},
    "scene_glare.png": {"glare": True},
    "scene_missing_marker.png": {"drop_marker": 2},
    "scene_dark.png": {"lighting": (0.15, 0.15, 0.15)},
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, kwargs in CASES.items():
        scene = render_scene("#3B1F4A", **kwargs)
        path = OUT_DIR / name
        path.write_bytes(encode_png(scene["image"]))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
