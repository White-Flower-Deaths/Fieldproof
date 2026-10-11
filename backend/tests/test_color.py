from __future__ import annotations

import math

from app.color import delta_e_ciede2000, hex_to_lab, hex_to_rgb, lab_to_hex


def test_hex_to_rgb():
    assert hex_to_rgb("#FF0000") == (255, 0, 0)
    assert hex_to_rgb("00ff00") == (0, 255, 0)


def test_white_and_black_lab():
    l, a, b = hex_to_lab("#FFFFFF")
    assert math.isclose(l, 100.0, abs_tol=0.5)
    assert abs(a) < 0.5 and abs(b) < 0.5

    l, a, b = hex_to_lab("#000000")
    assert l < 1.0


def test_primary_red_lab_reference():
    l, a, b = hex_to_lab("#FF0000")
    # sRGB D65 reference values
    assert math.isclose(l, 53.2428, abs_tol=0.05)
    assert math.isclose(a, 80.0925, abs_tol=0.1)
    assert math.isclose(b, 67.2032, abs_tol=0.1)


def test_delta_e_zero_for_identical():
    lab = hex_to_lab("#3B1F4A")
    assert delta_e_ciede2000(lab, lab) == 0.0


def test_delta_e_sharma_reference_pairs():
    # Sharma, Wu & Dalal (2005) CIEDE2000 test data.
    pairs = [
        ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
        ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
        ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
        ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
        ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ]
    for lab1, lab2, expected in pairs:
        got = delta_e_ciede2000(lab1, lab2)
        assert math.isclose(got, expected, abs_tol=0.005), (lab1, lab2, got, expected)
        assert math.isclose(got, delta_e_ciede2000(lab2, lab1), abs_tol=1e-9)


def test_delta_e_symmetry_on_real_colours():
    purple = hex_to_lab("#3B1F4A")
    orange = hex_to_lab("#E08A2E")
    assert math.isclose(
        delta_e_ciede2000(purple, orange),
        delta_e_ciede2000(orange, purple),
        abs_tol=1e-9,
    )
    assert delta_e_ciede2000(purple, orange) > 30


def test_lab_hex_roundtrip_is_close():
    for hexv in ("#3B1F4A", "#E08A2E", "#2E7D4F", "#1F5FA8"):
        lab = hex_to_lab(hexv)
        back = lab_to_hex(*lab)
        d_e = delta_e_ciede2000(lab, hex_to_lab(back))
        assert d_e < 1.0, (hexv, back, d_e)
