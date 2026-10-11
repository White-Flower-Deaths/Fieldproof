"""Synthetic test images: reference card + sample pouch under varied lighting.

Used by the demo image generator and by the unit tests to prove the calibration
pipeline works without needing a camera.
"""
from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from ...color import hex_to_rgb
from .card_config import CardSpec, load_card_spec


def render_card(
    spec: CardSpec | None = None, px_per_mm: int | None = None, drop_marker: int | None = None
) -> np.ndarray:
    """Render the printed reference card as an RGB image."""
    spec = spec or load_card_spec()
    scale = px_per_mm or spec.px_per_mm
    width = int(round(spec.width_mm * scale))
    height = int(round(spec.height_mm * scale))
    card = np.full((height, width, 3), 255, dtype=np.uint8)

    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, spec.dictionary))
    marker_px = int(round(spec.marker_size_mm * scale))
    for marker in spec.markers:
        if drop_marker is not None and marker["id"] == drop_marker:
            continue
        bitmap = cv2.aruco.generateImageMarker(dictionary, marker["id"], marker_px)
        x = int(round(marker["x_mm"] * scale))
        y = int(round(marker["y_mm"] * scale))
        card[y : y + marker_px, x : x + marker_px] = cv2.cvtColor(bitmap, cv2.COLOR_GRAY2RGB)

    for patch in spec.patches:
        x = int(round(patch.x_mm * scale))
        y = int(round(patch.y_mm * scale))
        w = int(round(patch.w_mm * scale))
        h = int(round(patch.h_mm * scale))
        card[y : y + h, x : x + w] = hex_to_rgb(patch.hex)

    # thin border so the card edge is visible against light backgrounds
    cv2.rectangle(card, (0, 0), (width - 1, height - 1), (170, 175, 180), max(1, scale // 10))
    return card


def render_scene(
    pouch_hex: str = "#3B1F4A",
    *,
    lighting: tuple[float, float, float] = (1.0, 1.0, 1.0),
    gamma: float = 1.0,
    noise: float = 0.0,
    blur_ksize: int = 0,
    glare: bool = False,
    drop_marker: int | None = None,
    width: int = 1280,
    height: int = 960,
    seed: int = 7,
    card_px_per_mm: int = 6,
) -> dict[str, Any]:
    """Compose a scene: table background + reference card + sample pouch.

    Returns {"image": RGB uint8, "roi": normalized {x,y,w,h}, "pouch_box": px}.
    """
    rng = np.random.default_rng(seed)
    scene = np.empty((height, width, 3), dtype=np.uint8)

    # background: light neutral surface with a gentle vertical gradient
    gradient = np.linspace(236, 214, height, dtype=np.float64)[:, None]
    scene[:] = np.clip(gradient[:, :, None], 0, 255).astype(np.uint8)

    spec = load_card_spec()
    card = render_card(spec, px_per_mm=card_px_per_mm, drop_marker=drop_marker)
    ch, cw = card.shape[:2]
    card_x, card_y = width - cw - 40, (height - ch) // 2
    if card_x < 0 or card_y < 0:
        raise ValueError("scene is too small for the reference card")
    scene[card_y : card_y + ch, card_x : card_x + cw] = card

    # sample pouch / tube area on the left
    pouch_w, pouch_h = int(width * 0.30), int(height * 0.42)
    pouch_x, pouch_y = int(width * 0.10), (height - pouch_h) // 2
    base = np.array(hex_to_rgb(pouch_hex), dtype=np.float64)
    texture = rng.normal(0, 6.0, size=(pouch_h, pouch_w, 3))
    pouch = np.clip(base[None, None, :] + texture, 0, 255).astype(np.uint8)
    scene[pouch_y : pouch_y + pouch_h, pouch_x : pouch_x + pouch_w] = pouch
    cv2.rectangle(
        scene,
        (pouch_x - 6, pouch_y - 6),
        (pouch_x + pouch_w + 6, pouch_y + pouch_h + 6),
        (120, 124, 128),
        4,
    )

    # lighting: per-channel gain + gamma
    out = scene.astype(np.float64) / 255.0
    gains = np.array(lighting, dtype=np.float64).reshape(1, 1, 3)
    out = np.clip(out, 0, 1) ** gamma * gains
    out = np.clip(out, 0, 1) * 255.0

    if noise > 0:
        out += rng.normal(0, noise, size=out.shape)

    image = np.clip(out, 0, 255).astype(np.uint8)

    if blur_ksize and blur_ksize >= 3:
        k = int(blur_ksize) | 1
        image = cv2.GaussianBlur(image, (k, k), 0)

    if glare:
        cx, cy = pouch_x + pouch_w // 3, pouch_y + pouch_h // 3
        cv2.ellipse(
            image,
            (cx, cy),
            (pouch_w // 4, pouch_h // 5),
            20,
            0,
            360,
            (255, 255, 255),
            -1,
        )

    roi = {
        "x": round((pouch_x + 20) / width, 4),
        "y": round((pouch_y + 20) / height, 4),
        "w": round((pouch_w - 40) / width, 4),
        "h": round((pouch_h - 40) / height, 4),
    }
    return {
        "image": image,
        "roi": roi,
        "pouch_box": (pouch_x, pouch_y, pouch_w, pouch_h),
        "card_box": (card_x, card_y, cw, ch),
    }


def encode_png(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not ok:
        raise RuntimeError("could not encode PNG")
    return buffer.tobytes()


def encode_jpeg(image: np.ndarray, quality: int = 92) -> bytes:
    ok, buffer = cv2.imencode(
        ".jpg", cv2.cvtColor(image, cv2.COLOR_RGB2BGR), [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    )
    if not ok:
        raise RuntimeError("could not encode JPEG")
    return buffer.tobytes()
