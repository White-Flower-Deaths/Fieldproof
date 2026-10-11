from app.services.imaging import analyze_image, encode_png, render_scene

outcomes = [
    {"code": "PURPLE_BLACK", "label": "Purple turning black", "ref_lab": [25.0, 20.0, -30.0], "ref_hex": "#3B1F4A"},
    {"code": "NO_REACTION_ORANGE", "label": "Orange", "ref_lab": [65.0, 35.0, 55.0], "ref_hex": "#E08A2E"},
    {"code": "BROWN", "label": "Brown", "ref_lab": [35.0, 15.0, 25.0], "ref_hex": "#6B4A2B"},
]

CASES = [
    ("ideal", {}),
    ("warm", {"lighting": (1.18, 0.96, 0.78)}),
    ("blurred", {"blur_ksize": 21}),
    ("glare", {"glare": True}),
    ("missing-marker", {"drop_marker": 2}),
    ("dark", {"lighting": (0.22, 0.22, 0.22)}),
    ("lowres", {}),
]

for name, kw in CASES:
    if name == "lowres":
        full = render_scene("#3B1F4A", **kw)
        import cv2

        small = cv2.resize(full["image"], (320, 240), interpolation=cv2.INTER_AREA)
        scene = {"image": small, "roi": full["roi"]}
    else:
        scene = render_scene("#3B1F4A", **kw)
    png = encode_png(scene["image"])
    rep = analyze_image(png, outcomes, roi=scene["roi"], kit_code="MARQUIS", kit_name="Marquis")
    gates = {g["id"]: g["passed"] for g in rep["quality"]["gates"]}
    corrected = rep["corrected_colour"]["hex"] if rep["corrected_colour"] else None
    m = rep["match"]
    line = f"{name:16} status={rep['status']:13} corrected={corrected} gates_failed={[k for k,v in gates.items() if not v]}"
    print(line)
    if m:
        print(f"{'':16} match={m['outcome']['code'] if m['outcome'] else None} dE={m['delta_e']} margin={m['margin']} reasons={m['reasons']}")
    if rep["calibration"]["rms_delta_e"] is not None:
        print(f"{'':16} calib rms={rep['calibration']['rms_delta_e']} raw_rms={rep['calibration']['raw_rms_delta_e']}")
