"""Reference-card geometry and known patch values (loaded from config JSON)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ...color import hex_to_lab

CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "reference_card.json"

# Marker ids assigned to the four card corners (see config/reference_card.json).
CORNER_ORDER = ("TL", "TR", "BR", "BL")


@dataclass(frozen=True)
class PatchSpec:
    code: str
    label: str
    hex: str
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float

    @property
    def lab(self) -> tuple[float, float, float]:
        return hex_to_lab(self.hex)


@dataclass(frozen=True)
class CardSpec:
    width_mm: float
    height_mm: float
    px_per_mm: int
    dictionary: str
    marker_size_mm: float
    markers: tuple[dict[str, Any], ...]
    patches: tuple[PatchSpec, ...]
    name: str
    version: int
    source_citation: str

    @property
    def width_px(self) -> int:
        return int(round(self.width_mm * self.px_per_mm))

    @property
    def height_px(self) -> int:
        return int(round(self.height_mm * self.px_per_mm))

    @property
    def marker_ids(self) -> tuple[int, ...]:
        return tuple(m["id"] for m in self.markers)

    def marker_center_px(self, corner: str) -> tuple[float, float]:
        for marker in self.markers:
            if marker["corner"] == corner:
                size_px = self.marker_size_mm * self.px_per_mm
                cx = (marker["x_mm"] + self.marker_size_mm / 2) * self.px_per_mm
                cy = (marker["y_mm"] + self.marker_size_mm / 2) * self.px_per_mm
                _ = size_px
                return (cx, cy)
        raise KeyError(corner)

    @property
    def canonical_centers(self) -> list[tuple[float, float]]:
        """Marker centres in canonical pixel order TL, TR, BR, BL."""
        return [self.marker_center_px(corner) for corner in CORNER_ORDER]

    def patch_rect_px(self, patch: PatchSpec) -> tuple[int, int, int, int]:
        """(x, y, w, h) in canonical pixels."""
        s = self.px_per_mm
        return (
            int(round(patch.x_mm * s)),
            int(round(patch.y_mm * s)),
            int(round(patch.w_mm * s)),
            int(round(patch.h_mm * s)),
        )


@lru_cache
def load_card_spec(path: str | None = None) -> CardSpec:
    config_path = Path(path) if path else CONFIG_PATH
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    card = raw["card"]
    aruco = raw["aruco"]
    patches = tuple(
        PatchSpec(
            code=p["code"],
            label=p["label"],
            hex=p["hex"],
            x_mm=p["x_mm"],
            y_mm=p["y_mm"],
            w_mm=p["w_mm"],
            h_mm=p["h_mm"],
        )
        for p in raw["patches"]
    )
    return CardSpec(
        width_mm=card["width_mm"],
        height_mm=card["height_mm"],
        px_per_mm=int(card["canonical_px_per_mm"]),
        dictionary=aruco["dictionary"],
        marker_size_mm=aruco["marker_size_mm"],
        markers=tuple(aruco["markers"]),
        patches=patches,
        name=raw["name"],
        version=int(raw.get("version", 1)),
        source_citation=raw["source_citation"],
    )


def card_public_dict() -> dict[str, Any]:
    """Patch table + layout for the API / docs (no internal helpers)."""
    spec = load_card_spec()
    return {
        "name": spec.name,
        "version": spec.version,
        "card": {
            "width_mm": spec.width_mm,
            "height_mm": spec.height_mm,
            "canonical_px_per_mm": spec.px_per_mm,
        },
        "aruco": {
            "dictionary": spec.dictionary,
            "marker_size_mm": spec.marker_size_mm,
            "markers": list(spec.markers),
        },
        "patches": [
            {
                "code": p.code,
                "label": p.label,
                "hex": p.hex,
                "lab": [round(v, 3) for v in p.lab],
                "x_mm": p.x_mm,
                "y_mm": p.y_mm,
                "w_mm": p.w_mm,
                "h_mm": p.h_mm,
            }
            for p in spec.patches
        ],
        "source_citation": spec.source_citation,
    }
