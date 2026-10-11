"""Read-only probe: validate the 8 seed_demo record designs against live seed data."""
from __future__ import annotations

import sys

from app.database import SessionFactory
from app.models import Kit
from app.services.scoring import Observation, analyze, build_reaction_index

KIT_CODES = [
    "MARQUIS",
    "MECKE",
    "MANDELIN",
    "FENT_STRIP",
    "SCOTT",
    "DUQUENOIS_LEVINE",
]


def o(**kw):
    return Observation(**kw)


def show(label: str, index, obs_list: list[Observation], expect_status: str) -> bool:
    result = analyze(index, obs_list)
    top = result["top_match"] or {}
    flags = result["flags"]
    ok = result["status"] == expect_status
    print(
        f"[{'OK ' if ok else 'BAD'}] {label}: status={result['status']} "
        f"(expected {expect_status}) top={top.get('code')} "
        f"{top.get('percentage')}% flags={flags}"
    )
    if result["rule_notes"]:
        for note in result["rule_notes"]:
            print(f"        note: {note}")
    return ok


def main() -> int:
    with SessionFactory() as db:
        index = build_reaction_index(db)
        for code in KIT_CODES:
            kit = db.query(Kit).filter(Kit.code == code).first()
            if kit is None:
                print(f"MISSING KIT {code}")
                continue
            print(f"{code}: {[x.code for x in kit.outcomes]}")

        scenarios = [
            (
                "1 NO_MATCH (MECKE blue-grey - no published expectation)",
                [o(ref="t1", test_type="COLOUR_REAGENT", kit_code="MECKE",
                   outcome_code="BLUE_GREY", outcome_label="Blue-grey")],
                "NO_MATCH",
            ),
            (
                "2 WEAK (single FENT_STRIP positive)",
                [o(ref="t1", test_type="IMMUNOASSAY_STRIP", kit_code="FENT_STRIP",
                   outcome_code="POSITIVE", outcome_label="Positive")],
                "WEAK_PRESUMPTIVE",
            ),
            (
                "3 PRESUMPTIVE (MARQUIS orange-red + MECKE no-reaction)",
                [
                    o(ref="t1", test_type="COLOUR_REAGENT", kit_code="MARQUIS",
                      outcome_code="ORANGE_RED", outcome_label="Orange-red"),
                    o(ref="t2", test_type="COLOUR_REAGENT", kit_code="MECKE",
                      outcome_code="NO_REACTION_ORANGE", outcome_label="No reaction (orange)"),
                ],
                "PRESUMPTIVE",
            ),
            (
                "4 STRONG (MARQUIS purple-black + MECKE purple)",
                [
                    o(ref="t1", test_type="COLOUR_REAGENT", kit_code="MARQUIS",
                      outcome_code="PURPLE_BLACK", outcome_label="Purple-black"),
                    o(ref="t2", test_type="COLOUR_REAGENT", kit_code="MECKE",
                      outcome_code="PURPLE", outcome_label="Purple"),
                ],
                "STRONG_PRESUMPTIVE",
            ),
            (
                "5 INCONCLUSIVE (camera reading marked inconclusive)",
                [o(ref="t1", test_type="COLOUR_REAGENT", kit_code="MARQUIS",
                   outcome_code=None, inconclusive=True)],
                "INCONCLUSIVE",
            ),
            (
                "6 MIXTURE flag (SCOTT blue + MARQUIS orange-red)",
                [
                    o(ref="t1", test_type="COLOUR_REAGENT", kit_code="SCOTT",
                      outcome_code="BLUE", outcome_label="Blue"),
                    o(ref="t2", test_type="COLOUR_REAGENT", kit_code="MARQUIS",
                      outcome_code="ORANGE_RED", outcome_label="Orange-red"),
                ],
                "PRESUMPTIVE",
            ),
            (
                "7 LAB confirmed (MDMA presumptive + GC-MS)",
                [
                    o(ref="t1", test_type="COLOUR_REAGENT", kit_code="MARQUIS",
                      outcome_code="PURPLE_BLACK", outcome_label="Purple-black"),
                    o(ref="t2", test_type="COLOUR_REAGENT", kit_code="MECKE",
                      outcome_code="PURPLE", outcome_label="Purple"),
                    o(ref="t3", test_type="LAB_CONFIRMATORY", lab_method="GC-MS",
                      lab_compound="MDMA", lab_reference="FS-2026-0431"),
                ],
                "CONFIRMED_BY_LAB",
            ),
            (
                "8 CAMERA single-test (MARQUIS purple-black)",
                [o(ref="t1", test_type="COLOUR_REAGENT", kit_code="MARQUIS",
                   outcome_code="PURPLE_BLACK", outcome_label="Purple-black")],
                "WEAK_PRESUMPTIVE",
            ),
        ]

        results = []
        for label, obs_list, expected in scenarios:
            results.append(show(label, index, obs_list, expected))

        # flag expectations
        mix = analyze(index, scenarios[5][1])
        flag_ok = "Possible mixture or ambiguous: refer to laboratory" in mix["flags"]
        print(f"[{'OK ' if flag_ok else 'BAD'}] 6 carries AMBIGUOUS flag")
        nomatch = analyze(index, scenarios[0][1])
        print(f"        1 flags: {nomatch['flags']}")
        lab = analyze(index, scenarios[6][1])
        conc_ok = lab["concentration"] == "Concentration: not determinable from presumptive tests"
        print(f"[{'OK ' if conc_ok else 'BAD'}] 7 concentration line")
        results.extend([flag_ok, conc_ok])
        print(f"\n{sum(results)}/{len(results)} design checks pass")
        return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
