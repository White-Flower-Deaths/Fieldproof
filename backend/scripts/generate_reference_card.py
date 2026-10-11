"""Generate the printable reference card PDF (docs/reference-card.pdf).

Run:  python scripts/generate_reference_card.py
Print at 100% scale (no page-fit) on white paper, matte preferred.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.services.imaging.card_config import load_card_spec

OUT = Path(__file__).resolve().parents[2] / "docs" / "reference-card.pdf"


def _marker_image(marker_id: int, dictionary: str, px: int = 160) -> np.ndarray:
    aruco_dict = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary))
    return cv2.aruco.generateImageMarker(aruco_dict, marker_id, px)


def build() -> Path:
    spec = load_card_spec()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    page_w, page_h = A4
    c = canvas.Canvas(str(OUT), pagesize=A4)
    margin = 18 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, page_h - 22 * mm, "FieldProof - Printable Reference Colour Card")
    c.setFont("Helvetica", 9)
    c.drawString(
        margin,
        page_h - 27 * mm,
        "Print at 100% scale on matte paper. Measure the outline: it must be "
        f"{spec.width_mm:.0f} x {spec.height_mm:.0f} mm.",
    )
    c.setFillColor(HexColor("#7A0019"))
    c.drawString(
        margin,
        page_h - 32.5 * mm,
        "DEMO calibration aid - verify patch colours against the kit manufacturer's chart "
        "before real use.",
    )

    card_x = margin
    card_y = page_h - 36 * mm - spec.height_mm * mm
    card_w = spec.width_mm * mm
    card_h = spec.height_mm * mm

    c.setFillColor(white)
    c.setStrokeColor(HexColor("#6B7280"))
    c.setLineWidth(1)
    c.rect(card_x, card_y, card_w, card_h, fill=1, stroke=1)

    mmx = lambda v: card_x + v * mm  # noqa: E731
    mmy = lambda v: card_y + card_h - v * mm  # noqa: E731

    for patch in spec.patches:
        c.setFillColor(HexColor(patch.hex))
        c.rect(
            mmx(patch.x_mm),
            mmy(patch.y_mm + patch.h_mm),
            patch.w_mm * mm,
            patch.h_mm * mm,
            fill=1,
            stroke=0,
        )
        c.setFillColor(black)
        c.setFont("Helvetica", 5.5)
        c.drawCentredString(
            mmx(patch.x_mm + patch.w_mm / 2),
            mmy(patch.y_mm + patch.h_mm) - 7,
            patch.code,
        )

    marker_px = spec.marker_size_mm * mm
    for marker in spec.markers:
        image = _marker_image(marker["id"], spec.dictionary)
        tmp = OUT.parent / f"_marker_{marker['id']}.png"
        cv2.imwrite(str(tmp), image)
        c.drawImage(
            str(tmp),
            mmx(marker["x_mm"]),
            mmy(marker["y_mm"] + spec.marker_size_mm),
            marker_px,
            marker_px,
        )
        tmp.unlink(missing_ok=True)

    # --- patch table ----------------------------------------------------
    y = card_y - 12 * mm
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Known patch values (sRGB hex / CIELAB):")
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    for patch in spec.patches:
        lab = ", ".join(f"{v:.1f}" for v in patch.lab)
        c.drawString(margin, y, f"{patch.code:<10} {patch.hex}   Lab {lab}")
        y -= 4.2 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "ArUco markers:")
    y -= 5 * mm
    c.setFont("Helvetica", 8)
    c.drawString(margin, y, f"Dictionary {spec.dictionary}, {spec.marker_size_mm:.0f} mm, ids 0-3 at the four corners.")
    y -= 4.2 * mm
    for marker in spec.markers:
        c.drawString(
            margin,
            y,
            f"id {marker['id']}  {marker['corner']}  at ({marker['x_mm']:.1f}, {marker['y_mm']:.1f}) mm",
        )
        y -= 4.2 * mm

    y -= 4 * mm
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#444444"))
    c.drawString(margin, y, f"Source: {spec.source_citation}")
    y -= 3.6 * mm
    c.drawString(
        margin,
        y,
        "Field tests are presumptive only. Confirmatory laboratory testing is required "
        "before any identification is treated as confirmed.",
    )

    c.showPage()
    c.save()
    return OUT


if __name__ == "__main__":
    print(f"wrote {build()}")
