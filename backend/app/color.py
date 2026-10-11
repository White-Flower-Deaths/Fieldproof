"""Colour utilities: sRGB -> CIELAB and CIEDE2000.

Used by the seed (reference Lab values) and by the image pipeline (step 4).
"""
from __future__ import annotations

import math
import re

_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    match = _HEX_RE.match(value.strip())
    if not match:
        raise ValueError(f"invalid hex colour: {value!r}")
    raw = match.group(1)
    return (
        int(raw[0:2], 16),
        int(raw[2:4], 16),
        int(raw[4:6], 16),
    )


def rgb_to_lab(r: float, g: float, b: float) -> tuple[float, float, float]:
    """sRGB (0-255) -> CIELAB (D65)."""

    def lin(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_l, g_l, b_l = lin(r), lin(g), lin(b)
    x = r_l * 0.4124564 + g_l * 0.3575761 + b_l * 0.1804375
    y = r_l * 0.2126729 + g_l * 0.7151522 + b_l * 0.0721750
    z = r_l * 0.0193339 + g_l * 0.1191920 + b_l * 0.9503041

    xn, yn, zn = 0.95047, 1.00000, 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x / xn), f(y / yn), f(z / zn)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def hex_to_lab(value: str) -> tuple[float, float, float]:
    return rgb_to_lab(*hex_to_rgb(value))


def lab_to_hex(l: float, a: float, b: float) -> str:
    """Approximate inverse of hex_to_lab (for swatch previews only)."""
    fy = (l + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200

    def finv(t: float) -> float:
        t3 = t**3
        return t3 if t3 > 0.008856 else (t - 16 / 116) / 7.787

    x, y, z = finv(fx) * 0.95047, finv(fy) * 1.0, finv(fz) * 1.08883

    r = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
    g = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
    bb = x * 0.0556434 + y * -0.2040259 + z * 1.0572252

    def gamma(c: float) -> int:
        c = min(max(c, 0.0), 1.0)
        c = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        return int(round(c * 255))

    return "#{:02X}{:02X}{:02X}".format(gamma(r), gamma(g), gamma(bb))


def delta_e_ciede2000(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
    k_l: float = 1.0,
    k_c: float = 1.0,
    k_h: float = 1.0,
) -> float:
    """CIEDE2000 colour difference (Sharma, Wu, Dalal 2005 notation)."""
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2.0
    c_bar7 = c_bar**7
    g = 0.5 * (1 - math.sqrt(c_bar7 / (c_bar7 + 25.0**7))) if c_bar7 else 0.0
    a1p, a2p = (1 + g) * a1, (1 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360

    d_lp = l2 - l1
    d_cp = c2p - c1p
    if c1p * c2p == 0:
        d_hp = 0.0
    else:
        d_hp_raw = h2p - h1p
        if d_hp_raw > 180:
            d_hp_raw -= 360
        elif d_hp_raw < -180:
            d_hp_raw += 360
        d_hp = d_hp_raw
    d_hp_rad = math.radians(d_hp)

    d_lp_s = d_lp
    d_cp_s = d_cp
    d_hp_s = 2 * math.sqrt(c1p * c2p) * math.sin(d_hp_rad / 2)

    l_bar_p = (l1 + l2) / 2
    c_bar_p = (c1p + c2p) / 2
    if c1p * c2p == 0:
        h_bar_p = h1p + h2p
    else:
        h_sum = h1p + h2p
        h_diff = abs(h1p - h2p)
        if h_diff <= 180:
            h_bar_p = h_sum / 2
        elif h_sum < 360:
            h_bar_p = (h_sum + 360) / 2
        else:
            h_bar_p = (h_sum - 360) / 2

    t = (
        1
        - 0.17 * math.cos(math.radians(h_bar_p - 30))
        + 0.24 * math.cos(math.radians(2 * h_bar_p))
        + 0.32 * math.cos(math.radians(3 * h_bar_p + 6))
        - 0.20 * math.cos(math.radians(4 * h_bar_p - 63))
    )
    delta_theta = 30 * math.exp(-(((h_bar_p - 275) / 25) ** 2))
    rc = 2 * math.sqrt(c_bar_p**7 / (c_bar_p**7 + 25.0**7))
    sl = 1 + (0.015 * (l_bar_p - 50) ** 2) / math.sqrt(20 + (l_bar_p - 50) ** 2)
    sc = 1 + 0.045 * c_bar_p
    sh = 1 + 0.015 * c_bar_p * t
    rt = -math.sin(math.radians(2 * delta_theta)) * rc

    term_l = d_lp_s / (k_l * sl)
    term_c = d_cp_s / (k_c * sc)
    term_h = d_hp_s / (k_h * sh)
    return math.sqrt(term_l**2 + term_c**2 + term_h**2 + rt * term_c * term_h)
