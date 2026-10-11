from __future__ import annotations

import math
from pathlib import Path

from app.enums import CONCENTRATION_NOT_DETERMINABLE, DISCLAIMER
from app.models import Kit, TestOutcome as OutcomeModel
from app.services.scoring import (
    AMBIGUOUS_FLAG,
    FLOOR_LIKELIHOOD,
    Candidate,
    Observation,
    ReactionIndex,
    analyze,
    build_reaction_index,
)

# --------------------------------------------------------------------------- #
# helpers (synthetic, domain-free fixtures - no drug names in logic tests)
# --------------------------------------------------------------------------- #
CANDIDATES = [Candidate(id=f"c{i}", code=f"CAND_{i}", name=f"Candidate {i}") for i in range(1, 7)]
KIT_IDS = {"KIT": "kit-1"}


def synth_index(likelihoods: dict, cross: dict | None = None) -> ReactionIndex:
    return ReactionIndex(
        candidates=CANDIDATES,
        likelihoods=likelihoods,
        cross_reactions=cross or {},
        kit_ids=KIT_IDS,
    )


def colour(ref: str, outcome: str, **kw) -> Observation:
    return Observation(
        ref=ref,
        test_type="COLOUR_REAGENT",
        kit_id="kit-1",
        kit_code="KIT",
        kit_name="Reference kit",
        outcome_code=outcome,
        outcome_label=kw.pop("label", outcome),
        **kw,
    )


def lab(ref: str, compound: str, method: str = "GC-MS", purity=None, **kw) -> Observation:
    return Observation(
        ref=ref,
        test_type="LAB_CONFIRMATORY",
        lab_method=method,
        lab_compound=compound,
        purity_percent=purity,
        lab_reference=kw.pop("lab_reference", "LAB-123"),
        **kw,
    )


# --------------------------------------------------------------------------- #
# synthetic logic tests
# --------------------------------------------------------------------------- #
def test_equal_priors_and_normalisation():
    index = synth_index({("c1", "kit-1", "O1"): 0.9, ("c2", "kit-1", "O1"): 0.5})
    result = analyze(index, [colour("t1", "O1")])

    total = sum(r["percentage"] for r in result["ranked"])
    assert math.isclose(total, 100.0, abs_tol=0.5)
    assert result["top_match"]["code"] == "CAND_1"
    assert result["ranked"][0]["percentage"] > result["ranked"][1]["percentage"]
    # floor keeps every other candidate alive (never zeroed out)
    assert all(r["percentage"] > 0 for r in result["ranked"])
    assert result["ranked"][-1]["score"] > 0
    assert result["counts"]["candidates"] == 6


def test_single_test_capped_at_weak():
    index = synth_index({("c1", "kit-1", "O1"): 0.95})
    result = analyze(index, [colour("t1", "O1")])
    assert result["status"] == "WEAK_PRESUMPTIVE"
    assert any("Only one presumptive test" in n for n in result["rule_notes"])
    assert result["counts"]["presumptive_informative"] == 1


def test_agreeing_tests_raise_confidence():
    index = synth_index(
        {
            ("c1", "kit-1", "O1"): 0.9,
            ("c1", "kit-1", "O2"): 0.85,
            ("c2", "kit-1", "O1"): 0.4,
            ("c2", "kit-1", "O2"): 0.05,
        }
    )
    single = analyze(index, [colour("t1", "O1")])
    both = analyze(index, [colour("t1", "O1"), colour("t2", "O2")])

    assert both["top_match"]["percentage"] > single["top_match"]["percentage"]
    assert both["status"] in {"PRESUMPTIVE", "STRONG_PRESUMPTIVE"}
    assert len(both["supporting_refs"]) == 2
    assert both["contradicting_refs"] == []
    assert AMBIGUOUS_FLAG not in both["flags"]


def test_contradicting_tests_flagged_and_capped():
    index = synth_index(
        {
            ("c1", "kit-1", "O1"): 0.9,
            ("c1", "kit-1", "O2"): FLOOR_LIKELIHOOD,
            ("c2", "kit-1", "O1"): FLOOR_LIKELIHOOD,
            ("c2", "kit-1", "O2"): 0.9,
        }
    )
    result = analyze(index, [colour("t1", "O1"), colour("t2", "O2")])

    assert AMBIGUOUS_FLAG in result["flags"]
    assert result["contradicting_refs"]
    assert result["status"] in {"WEAK_PRESUMPTIVE", "PRESUMPTIVE"}
    assert "STRONG" not in result["status"]
    assert any("contradict" in n.lower() for n in result["rule_notes"])


def test_mixture_flag_when_top_two_close():
    index = synth_index(
        {
            ("c1", "kit-1", "O1"): 0.9,
            ("c2", "kit-1", "O1"): 0.9,
            ("c1", "kit-1", "O2"): 0.7,
            ("c2", "kit-1", "O2"): 0.7,
        }
    )
    result = analyze(index, [colour("t1", "O1"), colour("t2", "O2")])
    assert AMBIGUOUS_FLAG in result["flags"]
    assert "STRONG" not in result["status"]
    assert result["top_match"]["percentage"] < 60


def test_no_match_below_threshold():
    index = synth_index({(c.id, "kit-1", "O1"): 0.5 for c in CANDIDATES})
    result = analyze(index, [colour("t1", "O1")])
    assert result["status"] == "NO_MATCH"
    assert result["top_match"]["percentage"] < 40


def test_no_tests_is_no_match():
    result = analyze(synth_index({}), [])
    assert result["status"] == "NO_MATCH"
    assert result["top_match"] is None
    assert result["counts"]["tests_entered"] == 0


def test_inconclusive_only_reads_as_inconclusive():
    result = analyze(synth_index({}), [colour("t1", "O1", inconclusive=True)])
    assert result["status"] == "INCONCLUSIVE"
    assert result["counts"]["informative"] == 0
    assert result["evidence"][0]["informative"] is False
    assert "inconclusive" in result["flags"][0].lower()


def test_invalid_immunoassay_is_not_evidence():
    obs = Observation(
        ref="s1",
        test_type="IMMUNOASSAY_STRIP",
        kit_id="kit-1",
        kit_code="KIT",
        outcome_code="INVALID",
        outcome_label="Invalid",
    )
    result = analyze(synth_index({}), [obs])
    assert result["status"] == "INCONCLUSIVE"
    assert result["counts"]["informative"] == 0


def test_lab_confirmatory_overrides_field_result():
    index = synth_index({("c1", "kit-1", "O1"): 0.95, ("c2", "kit-1", "O1"): 0.02})
    result = analyze(
        index,
        [colour("t1", "O1"), lab("t2", "Candidate 2", method="LC-MS", purity=62.0)],
    )
    assert result["status"] == "CONFIRMED_BY_LAB"
    assert result["lab_confirmed"] is True
    assert result["top_match"]["code"] == "CAND_2"
    assert result["concentration"].startswith("Purity: 62.0%")
    assert "LC-MS" in result["concentration"]


def test_lab_entry_without_recognised_compound_is_not_confirmed():
    index = synth_index({("c1", "kit-1", "O1"): 0.9})
    result = analyze(
        index, [colour("t1", "O1"), lab("t2", "Unrecognised-ZZZ", method="GC-MS")]
    )
    assert result["status"] != "CONFIRMED_BY_LAB"
    assert result["lab_confirmed"] is False
    assert any("Laboratory entry incomplete" in f for f in result["flags"])


def test_presumptive_result_never_says_confirmed():
    index = synth_index({("c1", "kit-1", "O1"): 0.9, ("c1", "kit-1", "O2"): 0.9})
    result = analyze(index, [colour("t1", "O1"), colour("t2", "O2")])
    assert result["status"] in {"PRESUMPTIVE", "STRONG_PRESUMPTIVE"}
    assert result["lab_confirmed"] is False
    assert "CONFIRMED_BY_LAB" not in result["explanation"]
    assert "confirmed" not in result["explanation"].lower().replace("confirmatory", "")
    assert result["disclaimer"] == DISCLAIMER


def test_concentration_line_hard_rule_for_presumptive():
    result = analyze(synth_index({("c1", "kit-1", "O1"): 0.9}), [colour("t1", "O1")])
    assert result["concentration"] == CONCENTRATION_NOT_DETERMINABLE
    assert CONCENTRATION_NOT_DETERMINABLE in result["explanation"]


def test_every_result_carries_disclaimer_and_engine_version():
    result = analyze(synth_index({("c1", "kit-1", "O1"): 0.9}), [colour("t1", "O1")])
    assert result["disclaimer"] == DISCLAIMER
    assert "presumptive" in result["disclaimer"].lower()
    assert result["engine_version"]
    assert result["computed_at"].endswith("Z")


def test_cross_reactions_surfaced_for_tests_used():
    index = synth_index(
        likelihoods={("c1", "kit-1", "O1"): 0.9},
        cross={("kit-1", "O1"): ["Substance X", "Substance Y"]},
    )
    result = analyze(index, [colour("t1", "O1")])
    assert result["cross_reactions"][0]["substances"] == ["Substance X", "Substance Y"]
    assert result["cross_reactions"][0]["kit_code"] == "KIT"


def test_explanation_is_plain_language_and_mentions_counts():
    index = synth_index({("c1", "kit-1", "O1"): 0.9, ("c1", "kit-1", "O2"): 0.8})
    result = analyze(index, [colour("t1", "O1"), colour("t2", "O2")])
    text = result["explanation"]
    assert "equal prior" in text
    assert "floor" in text
    assert "Final status" in text
    assert "presumptive" in text.lower()


def test_engine_source_has_no_hardcoded_domain_logic():
    """Data-driven guard: no substance or kit names inside the engine module."""
    source = Path("app/services/scoring.py").read_text(encoding="utf-8").lower()
    banned = [
        "cocaine", "heroin", "methamphetamine", "mdma", "cannabis", "fentanyl",
        "marquis", "mecke", "mandelin", "scott", "duquenois", "ehrlich",
        "ecstasy", "amphetamine", "opiate", "opioid",
    ]
    found = [word for word in banned if word in source]
    assert found == [], f"engine must stay substance-agnostic, found: {found}"


# --------------------------------------------------------------------------- #
# database-backed scenarios (seed data)
# --------------------------------------------------------------------------- #
def _colour_obs(db, kit_code: str, outcome_code: str, ref: str) -> Observation:
    kit = db.query(Kit).filter(Kit.code == kit_code).one()
    outcome = (
        db.query(OutcomeModel)
        .filter(OutcomeModel.kit_id == kit.id, OutcomeModel.code == outcome_code)
        .one()
    )
    return Observation(
        ref=ref,
        test_type=kit.test_type,
        kit_id=kit.id,
        kit_code=kit.code,
        kit_name=kit.name,
        outcome_code=outcome.code,
        outcome_label=outcome.label,
    )


def test_seed_single_colour_test(db_session):
    index = build_reaction_index(db_session)
    obs = _colour_obs(db_session, "MARQUIS", "PURPLE_BLACK", "m1")
    result = analyze(index, [obs])
    assert result["status"] == "WEAK_PRESUMPTIVE"
    # purple-black is genuinely shared by two candidates in the seeded data -
    # a lone reading must not pretend to separate them.
    assert result["top_match"]["code"] in {"MDMA", "HEROIN"}
    assert result["concentration"] == CONCENTRATION_NOT_DETERMINABLE
    assert result["disclaimer"] == DISCLAIMER


def test_seed_agreeing_tests_strong(db_session):
    index = build_reaction_index(db_session)
    result = analyze(
        index,
        [
            _colour_obs(db_session, "MARQUIS", "PURPLE_BLACK", "m1"),
            _colour_obs(db_session, "MECKE", "PURPLE", "m2"),
        ],
    )
    assert result["status"] == "STRONG_PRESUMPTIVE"
    assert result["top_match"]["code"] == "MDMA"
    assert result["top_match"]["percentage"] > 90
    assert len(result["supporting_refs"]) == 2
    assert AMBIGUOUS_FLAG not in result["flags"]


def test_seed_contradictory_tests(db_session):
    index = build_reaction_index(db_session)
    result = analyze(
        index,
        [
            # purple-black + purple + green: an MDMA-leaning combination where
            # the green reading (methamphetamine) directly contradicts MDMA
            _colour_obs(db_session, "MARQUIS", "PURPLE_BLACK", "m1"),
            _colour_obs(db_session, "MECKE", "PURPLE", "m2"),
            _colour_obs(db_session, "MANDELIN", "GREEN", "m3"),
        ],
    )
    assert AMBIGUOUS_FLAG in result["flags"]
    assert result["contradicting_refs"]
    assert "STRONG" not in result["status"]
    assert result["top_match"]["code"] == "MDMA"


def test_seed_immunoassay_strip_single(db_session):
    index = build_reaction_index(db_session)
    kit = db_session.query(Kit).filter(Kit.code == "FENT_STRIP").one()
    obs = Observation(
        ref="f1",
        test_type="IMMUNOASSAY_STRIP",
        kit_id=kit.id,
        kit_code=kit.code,
        kit_name=kit.name,
        outcome_code="POSITIVE",
        outcome_label="Positive (test line present)",
    )
    result = analyze(index, [obs])
    assert result["status"] == "WEAK_PRESUMPTIVE"
    assert result["top_match"]["code"] == "FENTANYL"
    assert result["cross_reactions"], "strip cross-reactivity must be surfaced"


def test_seed_spectrometer_match(db_session):
    index = build_reaction_index(db_session)
    kit = db_session.query(Kit).filter(Kit.code == "MARQUIS").one()
    result = analyze(
        index,
        [
            Observation(
                ref="r1",
                test_type="SPECTROMETER",
                kit_code="HANDHELD_RAMAN",
                kit_name="Handheld Raman",
                library_match="Methamphetamine",
                match_score=88.0,
            ),
            _colour_obs(db_session, "MARQUIS", "ORANGE_RED", "m1"),
        ],
    )
    assert result["top_match"]["code"] == "METHAMPHETAMINE"
    assert result["status"] in {"PRESUMPTIVE", "STRONG_PRESUMPTIVE"}
    assert len(result["supporting_refs"]) == 2


def test_seed_unresolved_spectrometer_is_not_evidence(db_session):
    index = build_reaction_index(db_session)
    obs = Observation(
        ref="r1",
        test_type="SPECTROMETER",
        kit_code="HANDHELD_RAMAN",
        library_match="Unknown Peak ZZZ",
        match_score=91.0,
    )
    result = analyze(index, [obs])
    assert result["status"] == "INCONCLUSIVE"
    assert result["counts"]["informative"] == 0


def test_seed_lab_confirmation_via_database_names(db_session):
    index = build_reaction_index(db_session)
    result = analyze(
        index,
        [
            _colour_obs(db_session, "SCOTT", "BLUE", "s1"),
            Observation(
                ref="l1",
                test_type="LAB_CONFIRMATORY",
                lab_method="GC-MS",
                lab_compound="Cocaine (hydrochloride salt)",
                lab_reference="FS-2026-0042",
                purity_percent=71.5,
            ),
        ],
    )
    assert result["status"] == "CONFIRMED_BY_LAB"
    assert result["top_match"]["code"] == "COCAINE"
    assert "71.5" in result["concentration"]
    assert "GC-MS" in result["concentration"]
    assert "FS-2026-0042" in result["concentration"]


def test_seed_kits_and_substances_all_cited(db_session):
    index = build_reaction_index(db_session)
    assert len(index.candidates) == 6
    assert index.kit_ids["MARQUIS"]
    assert index.likelihoods, "expected reactions must load from the database"


# --------------------------------------------------------------------------- #
# uniform readings (no published expectation) + confidence bands
# --------------------------------------------------------------------------- #
def test_uniform_reading_does_not_support_or_contradict():
    # every candidate shares the same expected likelihood for this outcome
    index = synth_index({(c.id, "kit-1", "O1"): 0.5 for c in CANDIDATES})
    result = analyze(index, [colour("t1", "O1")])

    assert result["status"] == "NO_MATCH"
    assert result["supporting_refs"] == []
    assert result["contradicting_refs"] == []
    assert AMBIGUOUS_FLAG not in result["flags"]
    row = result["evidence"][0]
    assert row["supports"] is None
    assert "does not discriminate" in row["note"]
    assert any("discriminating" in n for n in result["rule_notes"])


def test_uniform_reading_does_not_trigger_close_gap_flag():
    # three flat readings: scores tie exactly, but nothing discriminates -
    # the AMBIGUOUS (possible mixture) flag must not fire
    index = synth_index({(c.id, "kit-1", "O1"): 0.5 for c in CANDIDATES})
    result = analyze(
        index,
        [
            colour("t1", "O1"),
            colour("t2", "O2"),
            colour("t3", "O3"),
        ],
    )
    assert AMBIGUOUS_FLAG not in result["flags"]
    assert result["contradicting_refs"] == []
    assert result["supporting_refs"] == []


def test_confidence_band_is_full_width_without_evidence():
    index = synth_index({("c1", "kit-1", "O1"): 0.9, ("c2", "kit-1", "O1"): 0.4})
    result = analyze(index, [colour("t1", "O1", inconclusive=True)])
    band = result["confidence"]
    assert band["low"] == 0.0
    assert band["high"] == 1.0
    assert band["label"] == "insufficient evidence"
    assert band["evidence_bits"] == 0.0
    assert "not a statistical confidence interval" in band["method"].lower()


def test_confidence_band_contains_score_and_narrows_with_evidence():
    index = synth_index(
        {
            ("c1", "kit-1", "O1"): 0.9,
            ("c1", "kit-1", "O2"): 0.85,
            ("c2", "kit-1", "O1"): 0.4,
            ("c2", "kit-1", "O2"): 0.05,
        }
    )
    single = analyze(index, [colour("t1", "O1")])
    both = analyze(index, [colour("t1", "O1"), colour("t2", "O2")])

    for result in (single, both):
        band = result["confidence"]
        p = result["top_match"]["percentage"] / 100
        assert band["low"] <= p <= band["high"]
        assert 0.0 < band["width"] <= 1.0
        assert band["label"] in {"wide", "moderate", "narrow"}
    assert both["confidence"]["width"] < single["confidence"]["width"]
    assert both["confidence"]["evidence_bits"] > single["confidence"]["evidence_bits"]
    # the band must be part of the explanation, never as a confirmation claim
    assert "Uncertainty band" in both["explanation"]
    assert "confirmed" not in both["explanation"].lower().replace("confirmatory", "")


def test_confidence_band_widens_with_contradiction():
    agreeing = synth_index(
        {("c1", "kit-1", "O1"): 0.9, ("c1", "kit-1", "O2"): 0.9}
    )
    contradicting = synth_index(
        {
            ("c1", "kit-1", "O1"): 0.9,
            ("c1", "kit-1", "O2"): FLOOR_LIKELIHOOD,
            ("c2", "kit-1", "O1"): FLOOR_LIKELIHOOD,
            ("c2", "kit-1", "O2"): 0.9,
        }
    )
    ok = analyze(agreeing, [colour("t1", "O1"), colour("t2", "O2")])
    bad = analyze(contradicting, [colour("t1", "O1"), colour("t2", "O2")])

    assert ok["contradicting_refs"] == []
    assert bad["contradicting_refs"]
    assert bad["confidence"]["width"] > ok["confidence"]["width"]
    # even contradicted, the band still brackets the reported score
    p = bad["top_match"]["percentage"] / 100
    assert bad["confidence"]["low"] <= p <= bad["confidence"]["high"]


def test_confidence_band_narrows_with_lab_result():
    index = synth_index(
        {("c1", "kit-1", "O1"): 0.9, ("c2", "kit-1", "O1"): 0.02}
    )
    presumptive = analyze(index, [colour("t1", "O1")])
    confirmed = analyze(index, [colour("t1", "O1"), lab("t2", "Candidate 1")])

    assert presumptive["status"] == "WEAK_PRESUMPTIVE"
    assert confirmed["status"] == "CONFIRMED_BY_LAB"
    assert confirmed["confidence"]["width"] < presumptive["confidence"]["width"]


def test_seed_evidence_rows_carry_source_citations(db_session):
    index = build_reaction_index(db_session)
    result = analyze(
        index,
        [
            _colour_obs(db_session, "MARQUIS", "PURPLE_BLACK", "m1"),
            _colour_obs(db_session, "MECKE", "PURPLE", "m2"),
        ],
    )
    cited = [row for row in result["evidence"] if row["source_citation"]]
    assert cited, "expected-reaction rows must surface their citations"
    for row in cited:
        assert "DEMO" not in row["source_citation"]
        assert len(row["source_citation"]) > 20
    # the whole analysis carries an uncertainty band for the leader
    band = result["confidence"]
    p = result["top_match"]["percentage"] / 100
    assert band["low"] <= p <= band["high"]

