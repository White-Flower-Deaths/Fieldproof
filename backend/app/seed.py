"""Reference seed data: kits, substances and expected reactions.

EVERY expected-reaction row is sourced from published forensic methods and
peer-reviewed studies and carries the exact citation(s) it derives from.
The full verbatim research - colour statements, source URLs, the seven
documented source conflicts and the twelve NOT FOUND cells - lives in
`docs/reaction-data.md`. Nothing here is a colour chart in itself: where
sources disagreed, both readings are seeded and marked; where no source was
found, no rows are seeded (the engine reports such readings as
non-discriminating).

Likelihood scheme (applied consistently, see docs/reaction-data.md):
    0.90   >=3 independent sources agree, no material conflict
    0.85   2 independent sources agree
    0.70   one authoritative source (validation study / official method)
    0.60   one source only (low-to-moderate evidence)
    0.55 / 0.30-0.35   documented conflict: majority reading / documented
           dissent (both seeded, never averaged)
    0.15   documented secondary reading (endpoint / variant nuance)
    unlisted outcome for a seeded pair -> engine floor likelihood (0.02)
    pair with no published data -> no rows at all

Substance descriptions (appearance / aliases) are generic field metadata and
still carry `DEMO_CITATION` - they are not reaction data.

Run:
    python -m app.seed            # create tables + load reference data (idempotent)
    python -m app.seed --reset    # DROP and rebuild the database, then seed
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from .color import hex_to_lab
from .config import settings
from .database import Base, SessionFactory, engine, init_db
from .enums import DEMO_CITATION
from .models import (
    ExpectedReaction,
    Kit,
    Sample,
    SampleTest,
    Substance,
    TestOutcome,
    User,
)
from .security import hash_password

# --------------------------------------------------------------------------- #
# source citations (verbatim identity of each source; row citations may append
# section numbers). `tests/test_auth.py` asserts that kit/outcome/reaction rows
# carry only citations from this set.
# --------------------------------------------------------------------------- #
CITE_ONEAL = (
    "O'Neal CL, Crouch DJ, Fatah AA. Validation of twelve chemical spot tests "
    "for the detection of drugs of abuse. Forensic Science International 109 "
    "(2000) 189-201, Table 2; reproduced in NIJ Standard-0604.01 (July 2000, "
    "NCJ 183258), App. A Table 1"
)
CITE_SIRCHIE = "SIRCHIE NARK Color Identification Chart, NARK20016_621ENG-REV12 (2020)"
CITE_WAKE = (
    "Wake County Bureau of Forensic Services, Drug Chemistry Unit Technical "
    "Procedures, Ch. 7 Color Tests, effective 2021-08-25"
)
CITE_SANDIEGO = "City of San Diego Police Dept., Narcotics Method Manual, July 2017"
CITE_DARSIGNY = (
    "Darsigny C, Couture ML, Desgagne-Penix I. Forensic Chemistry of Alkaloids: "
    "Presumptive Color Test. Austin J Forensic Sci Criminol 2018;5(1):1074, "
    "Tables 2-3"
)
CITE_FCS10 = (
    "District of Columbia Dept. of Forensic Sciences, FCS10 Procedure for "
    "Chemical Spot Tests, Rev. 5 (2018-10-31)"
)
CITE_DANCESAFE = "DanceSafe, Drug Checking Kits / Testing Instructions, V16 (Fall 2022)"
CITE_EPGP = (
    "UGC e-PG Pathshala, Forensic Science Paper 9 Module 25, Colour Tests for "
    "Drug Identification"
)
CITE_UNODC_COC = (
    "UNODC, Recommended Methods for the Identification and Analysis of Cocaine "
    "in Seized Materials, ST/NAR/7/Rev.1 (2012)"
)
CITE_UNODC_CAN = (
    "UNODC, Recommended Methods for the Identification and Analysis of Cannabis "
    "in Seized Materials, ST/NAR/40 (2009)"
)
CITE_JACS = (
    "Canoura J, Alkhamis O, Venzke M, Ly PT, Xiao Y. Developing Aptamer-Based "
    "Colorimetric Opioid Tests. JACS Au 2024;4(3):1059-1072, "
    "doi:10.1021/jacsau.3c00801"
)
CITE_SCITEC16 = (
    "UNODC SCITEC, Screening Colour Test and Specific Colour Tests for MDA and "
    "Amphetamine-Type Stimulants, SCITEC/16"
)
CITE_BTNX = (
    "BTNX Inc., Rapid Response Fentanyl Test Strip product insert 1110027361 "
    "REV 2.0 (effective 2021-01-20)"
)
CITE_LOCKWOOD = (
    "Lockwood TL, Vervoordt A, Lieberman M. High concentrations of illicit "
    "stimulants and cutting agents cause false positives on fentanyl test "
    "strips. Harm Reduct J 2021;18:30, doi:10.1186/s12954-021-00478-4"
)
CITE_HALIFAX = (
    "Halifax JC, Lim L, Ciccarone D, Lynch KL. Testing the test strips: "
    "laboratory performance of fentanyl test strips. Harm Reduct J 2024;21:14, "
    "doi:10.1186/s12954-023-00921-8"
)
CITE_KOSECKI = (
    "Kosecki TL, Brooke C, Canonico DL. Fentanyl as a potential false positive "
    "with color tests commonly used for presumptive cocaine identification. J "
    "Forensic Sci 2022;67(5):2082-2088 (abstract), "
    "doi:10.1111/1556-4029.15090"
)

# Source-identity markers: every kit/outcome/reaction citation must contain at
# least one of these (tests/test_auth.py enforces it, so no row can carry an
# unlabelled or placeholder citation).
CITATION_MARKERS: set[str] = {
    "O'Neal",
    "NIJ",
    "SIRCHIE",
    "Wake County",
    "San Diego",
    "Darsigny",
    "District of Columbia",
    "DanceSafe",
    "e-PG Pathshala",
    "UNODC",
    "JACS Au",
    "BTNX",
    "Lockwood",
    "Halifax",
    "Kosecki",
}

# --------------------------------------------------------------------------- #
# demo accounts (passwords are intentionally simple and documented in the README)
# --------------------------------------------------------------------------- #
DEMO_USERS = [
    {
        "username": "officer1",
        "password": "FieldProof#Demo1",
        "full_name": "A. Rivera",
        "badge_number": "FP-1042",
        "role": "OFFICER",
        "agency": "Metro Police - Field Operations",
    },
    {
        "username": "officer2",
        "password": "FieldProof#Demo2",
        "full_name": "J. Okonkwo",
        "badge_number": "FP-1188",
        "role": "OFFICER",
        "agency": "Metro Police - Field Operations",
    },
    {
        "username": "lab1",
        "password": "FieldProof#Lab1",
        "full_name": "M. Chen",
        "badge_number": "LAB-0071",
        "role": "LAB",
        "agency": "Forensic Science Laboratory",
    },
    {
        "username": "admin",
        "password": "FieldProof#Admin1",
        "full_name": "System Administrator",
        "badge_number": None,
        "role": "ADMIN",
        "agency": "FieldProof Programme Office",
    },
]

# --------------------------------------------------------------------------- #
# kits (reagent composition / procedure / colour outcomes per cited sources)
# --------------------------------------------------------------------------- #
KIT_MARQUIS_CITE = (
    "NIJ Standard-0604.01 (July 2000, NCJ 183258), App. A (reagent A.5); "
    "colour charts: O'Neal et al., Forensic Sci Int 109 (2000) Table 2; "
    "SIRCHIE NARK20016 (2020)"
)
KIT_MECKE_CITE = (
    "SIRCHIE NARK20016 (2020) Test 11; reagent: City of San Diego Narcotics "
    "Method Manual (2017) Sec. 15; colours: Darsigny et al. 2018 Tables 2-3"
)
KIT_MANDELIN_CITE = (
    "NIJ Standard-0604.01 (2000), App. A (reagent A.4); colours: O'Neal et "
    "al. (2000) Table 2; Darsigny et al. 2018"
)
KIT_SCOTT_CITE = (
    "UNODC ST/NAR/7/Rev.1 (2012) Sec. 5.3.1.1 (modified Scott test); NIJ "
    "Standard-0604.01 (2000), App. A (A.1); SIRCHIE NARK20016 (2020) Test 7"
)
KIT_DL_CITE = (
    "UNODC ST/NAR/40 (2009) Sec. 5.4.3.1; DC DFS FCS10 Rev. 5 (2018) "
    "Sec. 7.8.4; O'Neal et al. (2000) Table 2 (A.3)"
)
KIT_STRIP_CITE = CITE_BTNX

KIT_DEFS: list[dict] = [
    {
        "code": "MARQUIS",
        "name": "Marquis reagent",
        "test_type": "COLOUR_REAGENT",
        "manufacturer": "Generic field reagent - method per source citation",
        "description": "Formaldehyde in concentrated sulphuric acid; classic spot test.",
        "instructions": "Add 1-2 drops to a small sample. Read colour at 30-60 s.",
        "reaction_time_seconds": 45,
        "requires_photo": True,
        "citation": KIT_MARQUIS_CITE,
        "outcomes": [
            ("NO_REACTION_ORANGE", "Orange - no characteristic reaction", "#E08A2E",
             "Reagent colour unchanged; documented for cocaine (and expected when "
             "no reactive substance is present).", []),
            ("ORANGE_RED", "Orange-red", "#D9541E",
             "Reported for amphetamine-type stimulants; some SOPs record "
             "salmon/light pink for cocaine.", []),
            ("BROWN", "Brown", "#6B4A2B",
             "Reported as the methamphetamine endpoint and by one peer-reviewed "
             "study for fentanyl.", []),
            ("PURPLE_BLACK", "Purple turning black", "#3B1F4A",
             "Reported for MDMA and for heroin/opiates.",
             ["MDEA / MDMA analogues", "Morphine / codeine (opiates)"]),
            ("YELLOW", "Yellow", "#E3B23C",
             "Weak or ambiguous reaction; treat as inconclusive.", []),
        ],
    },
    {
        "code": "MECKE",
        "name": "Mecke reagent",
        "test_type": "COLOUR_REAGENT",
        "manufacturer": "Generic field reagent - method per source citation",
        "description": "Selenious acid in concentrated sulphuric acid.",
        "instructions": "Add 1-2 drops. Read colour at 30-60 s.",
        "reaction_time_seconds": 45,
        "requires_photo": True,
        "citation": KIT_MECKE_CITE,
        "outcomes": [
            ("NO_REACTION_ORANGE", "Orange - no characteristic reaction", "#E08A2E",
             "Reagent colour unchanged; documented for cocaine and "
             "methamphetamine.", []),
            ("GREEN", "Green", "#2E7D4F",
             "Reported for heroin/opiates and some tryptamines.",
             ["Certain plant-derived indole alkaloids"]),
            ("PURPLE", "Purple", "#5B2C6F",
             "Reported for MDMA-type substances.",
             ["Some tryptamines", "Adulterants with aromatic amines"]),
            ("BLUE_GREY", "Blue-grey", "#6E8CA0",
             "Weak/ambiguous reaction; treat as inconclusive.", []),
        ],
    },
    {
        "code": "MANDELIN",
        "name": "Mandelin reagent",
        "test_type": "COLOUR_REAGENT",
        "manufacturer": "Generic field reagent - method per source citation",
        "description": "Ammonium vanadate in concentrated sulphuric acid.",
        "instructions": "Add 1-2 drops. Read colour at 30-60 s.",
        "reaction_time_seconds": 45,
        "requires_photo": True,
        "citation": KIT_MANDELIN_CITE,
        "outcomes": [
            ("NO_REACTION_YELLOW", "Yellow - no characteristic reaction", "#D9B44A",
             "Reagent colour unchanged; one source records no reaction for "
             "methamphetamine (dissent).", []),
            ("GREEN", "Green", "#2F7D32",
             "Reported yellowish-green for amphetamine-type stimulants.",
             ["Some local anaesthetics"]),
            ("ORANGE_BROWN", "Orange-brown", "#A6572B",
             "Reported for cocaine ('deep orange yellow') and heroin "
             "('moderate reddish brown').", []),
            ("BLUE", "Blue", "#2A6F9E",
             "Reported for MDMA ('dark blue').", ["Ketamine (reported)"]),
        ],
    },
    {
        "code": "SCOTT",
        "name": "Scott reagent (cocaine presumptive)",
        "test_type": "COLOUR_REAGENT",
        "manufacturer": "Generic field reagent - method per source citation",
        "description": "Three-stage cobalt thiocyanate colour test for cocaine.",
        "instructions": "Follow the kit's A/B/C stage sequence; read blue colour.",
        "reaction_time_seconds": 30,
        "requires_photo": True,
        "citation": KIT_SCOTT_CITE,
        "outcomes": [
            ("BLUE", "Blue", "#1F5FA8",
             "Reported for cocaine and cocaine salts; documented false positive "
             "for fentanyl.",
             ["Fentanyl (documented false positive, Kosecki 2022)",
              "Procaine", "Tropacocaine"]),
            ("PALE_NO_REACTION", "Pale / no colour change", "#DCE3E8",
             "No characteristic blue reaction.", []),
            ("GREEN", "Green", "#3E8E41",
             "Ambiguous; treat as inconclusive.",
             ["Some adulterant mixtures"]),
        ],
    },
    {
        "code": "DUQUENOIS_LEVINE",
        "name": "Duquenois-Levine",
        "test_type": "COLOUR_REAGENT",
        "manufacturer": "Generic field reagent - method per source citation",
        "description": "Spray test for cannabis plant material.",
        "instructions": "Spray, wait, add concentrated HCl and read purple colour.",
        "reaction_time_seconds": 60,
        "requires_photo": True,
        "citation": KIT_DL_CITE,
        "outcomes": [
            ("PURPLE", "Purple", "#5B2C6F",
             "Positive for cannabinoids (cannabis/THC).",
             ["Patchouli, cypress, eucalyptus (documented false positives)",
              "Henna, nutmeg, mace, agrimony (documented false positives)"]),
            ("PALE_GREY", "Pale grey - no characteristic reaction", "#DDE5EA",
             "No purple reaction.", []),
            ("BROWN", "Brown", "#7A5230",
             "Ambiguous; treat as inconclusive.", ["Some woody plant material"]),
        ],
    },
    {
        "code": "FENT_STRIP",
        "name": "Fentanyl immunoassay strip",
        "test_type": "IMMUNOASSAY_STRIP",
        "manufacturer": "BTNX Inc. (Rapid Response)",
        "description": "Lateral-flow immunoassay for fentanyl and analogues.",
        "instructions": (
            "Dilute the sample, immerse the strip to the MAX mark for 10-15 s; "
            "read between 5 and 10 minutes. A faint test line near the cut-off "
            "requires a repeat test."
        ),
        "reaction_time_seconds": 300,
        "requires_photo": False,
        "citation": KIT_STRIP_CITE,
        "outcomes": [
            ("POSITIVE", "Positive (test line present)", "#C0392B",
             "Fentanyl or a cross-reactive analogue indicated; documented false "
             "positives with high-concentration stimulants.",
             ["Fentanyl analogues (cross-react)",
              "Methamphetamine (false positive at >= 1.5 mg/mL)",
              "MDMA (false positive at >= 2 mg/mL)",
              "Diphenhydramine (false positive at >= 1 mg/mL)"]),
            ("NEGATIVE", "Negative (control line only)", "#2E7D5B",
             "No fentanyl detected by this strip (below cut-off levels can read "
             "negative).", []),
            ("INVALID", "Invalid (no control line)", "#7F8C8D",
             "Test did not run correctly; repeat.", []),
        ],
    },
]

# --------------------------------------------------------------------------- #
# substances (generic field metadata - still DEMO_CITATION: not reaction data)
# --------------------------------------------------------------------------- #
SUBSTANCE_DEFS: list[dict] = [
    {"code": "COCAINE", "name": "Cocaine (hydrochloride salt)",
     "aliases": ["coke", "blow", "flake"], "substance_class": "Stimulant",
     "notes": "Typically a white crystalline powder or 'rock'."},
    {"code": "HEROIN", "name": "Heroin (diacetylmorphine)",
     "aliases": ["diamorphine", "brown sugar", "H"], "substance_class": "Opioid",
     "notes": "Ranges from white powder to brown/tan granular material."},
    {"code": "METHAMPHETAMINE", "name": "Methamphetamine",
     "aliases": ["crystal meth", "ice", "tina"], "substance_class": "Stimulant",
     "notes": "Often clear/white crystals, sometimes powder."},
    {"code": "MDMA", "name": "MDMA",
     "aliases": ["ecstasy", "molly", "adam"], "substance_class": "Empathogen / stimulant",
     "notes": "Found as powder, crystals or pressed tablets."},
    {"code": "CANNABIS", "name": "Cannabis (plant material)",
     "aliases": ["marijuana", "weed", "hashish"], "substance_class": "Cannabinoid",
     "notes": "Dried plant material, resin or extracted material."},
    {"code": "FENTANYL", "name": "Fentanyl",
     "aliases": ["designer opioid", "illicit fentanyl"], "substance_class": "Synthetic opioid",
     "notes": "Often present as an adulterant; potency is very high."},
]

# --------------------------------------------------------------------------- #
# expected reactions: (substance, kit, outcome, likelihood, citation)
# Values follow the documented scheme in the module docstring. Pairs with no
# published data are intentionally absent (engine floor 0.02 applies; readings
# with no expectation anywhere are reported as non-discriminating).
# Verbatim source quotes and conflict records: docs/reaction-data.md.
# --------------------------------------------------------------------------- #
REACTIONS: list[tuple[str, str, str, float, str]] = [
    # --- Marquis -----------------------------------------------------------
    ("COCAINE", "MARQUIS", "NO_REACTION_ORANGE", 0.60,
     f"{CITE_DARSIGNY}; {CITE_SANDIEGO}; {CITE_DANCESAFE}; conflict: {CITE_FCS10} Sec. 7.1.4"),
    ("COCAINE", "MARQUIS", "ORANGE_RED", 0.35,
     f"{CITE_FCS10} Sec. 7.1.4 (salmon); {CITE_DANCESAFE} (light pink or no change)"),
    ("HEROIN", "MARQUIS", "PURPLE_BLACK", 0.90,
     f"{CITE_ONEAL}; {CITE_SIRCHIE}; {CITE_WAKE}; {CITE_SANDIEGO}"),
    ("METHAMPHETAMINE", "MARQUIS", "ORANGE_RED", 0.80,
     f"{CITE_ONEAL}; {CITE_SIRCHIE}; {CITE_WAKE}; {CITE_SANDIEGO}"),
    ("METHAMPHETAMINE", "MARQUIS", "BROWN", 0.15,
     f"{CITE_SIRCHIE} (orange to brown); {CITE_ONEAL} (final dark reddish brown)"),
    ("MDMA", "MARQUIS", "PURPLE_BLACK", 0.90,
     f"{CITE_SIRCHIE}; {CITE_WAKE}; {CITE_DARSIGNY}; {CITE_EPGP}; "
     f"outlier: {CITE_SANDIEGO} Sec. 2.2.1 lists green and/or purple-black"),
    ("FENTANYL", "MARQUIS", "ORANGE_RED", 0.60,
     f"{CITE_WAKE}; {CITE_SANDIEGO}"),
    ("FENTANYL", "MARQUIS", "BROWN", 0.35, CITE_JACS),
    # --- Mecke -------------------------------------------------------------
    ("COCAINE", "MECKE", "NO_REACTION_ORANGE", 0.60, CITE_DARSIGNY),
    ("HEROIN", "MECKE", "GREEN", 0.85,
     f"{CITE_DARSIGNY} (deep bluish green); {CITE_SIRCHIE}; {CITE_SANDIEGO}"),
    ("METHAMPHETAMINE", "MECKE", "NO_REACTION_ORANGE", 0.60, CITE_DARSIGNY),
    ("MDMA", "MECKE", "PURPLE", 0.60, f"{CITE_DARSIGNY}; {CITE_EPGP}"),
    ("MDMA", "MECKE", "GREEN", 0.35, f"{CITE_SANDIEGO} Sec. 2.2.1 (green/blue - dissent)"),
    # --- Mandelin ----------------------------------------------------------
    ("COCAINE", "MANDELIN", "ORANGE_BROWN", 0.85,
     f"{CITE_ONEAL} (deep orange yellow); {CITE_DARSIGNY} (+)"),
    ("HEROIN", "MANDELIN", "ORANGE_BROWN", 0.70, CITE_ONEAL),
    ("METHAMPHETAMINE", "MANDELIN", "GREEN", 0.65,
     f"{CITE_ONEAL} (dark yellowish green); {CITE_SIRCHIE} (yellow-green); {CITE_SCITEC16}"),
    ("METHAMPHETAMINE", "MANDELIN", "NO_REACTION_YELLOW", 0.30,
     f"{CITE_DARSIGNY} (no change - dissent)"),
    ("MDMA", "MANDELIN", "BLUE", 0.70, f"{CITE_DARSIGNY} (dark blue); {CITE_EPGP} (blue/black)"),
    # --- Scott -------------------------------------------------------------
    ("COCAINE", "SCOTT", "BLUE", 0.90,
     f"{CITE_UNODC_COC} Sec. 5.3.1.1; {CITE_ONEAL}; {CITE_SIRCHIE}; {CITE_WAKE}"),
    ("HEROIN", "SCOTT", "PALE_NO_REACTION", 0.55,
     f"{CITE_DARSIGNY} (Cobalt '-' for codeine and morphine; no heroin row in "
     f"{CITE_UNODC_COC} or {CITE_SIRCHIE} - unresolved, see docs/reaction-data.md)"),
    ("HEROIN", "SCOTT", "BLUE", 0.30, f"{CITE_EPGP} Sec. 4.2 (single affirmative source - unresolved)"),
    ("METHAMPHETAMINE", "SCOTT", "PALE_NO_REACTION", 0.60, CITE_DARSIGNY),
    ("MDMA", "SCOTT", "PALE_NO_REACTION", 0.65, f"{CITE_DARSIGNY} (Cobalt '-'; mechanistic rationale)"),
    ("FENTANYL", "SCOTT", "BLUE", 0.60,
     f"{CITE_KOSECKI}; {CITE_SANDIEGO} (CoSCN blue on particles)"),
    # --- Duquenois-Levine --------------------------------------------------
    ("CANNABIS", "DUQUENOIS_LEVINE", "PURPLE", 0.90,
     f"{CITE_UNODC_CAN} Sec. 5.4.3.1; {CITE_FCS10} Sec. 7.8.4; {CITE_SANDIEGO} Sec. 8.1.3"),
    # --- Fentanyl strip ----------------------------------------------------
    ("FENTANYL", "FENT_STRIP", "POSITIVE", 0.90, f"{CITE_BTNX}; {CITE_HALIFAX}"),
    ("FENTANYL", "FENT_STRIP", "NEGATIVE", 0.08, f"{CITE_BTNX} (negative possible below the cut-off)"),
    ("COCAINE", "FENT_STRIP", "NEGATIVE", 0.90, f"{CITE_LOCKWOOD}; {CITE_HALIFAX}"),
    ("HEROIN", "FENT_STRIP", "NEGATIVE", 0.90, CITE_HALIFAX),
    ("METHAMPHETAMINE", "FENT_STRIP", "NEGATIVE", 0.70, f"{CITE_LOCKWOOD}; {CITE_HALIFAX}"),
    ("METHAMPHETAMINE", "FENT_STRIP", "POSITIVE", 0.25,
     f"{CITE_LOCKWOOD} (false positive at >= 1.5 mg/mL); {CITE_HALIFAX}"),
    ("MDMA", "FENT_STRIP", "NEGATIVE", 0.70, f"{CITE_LOCKWOOD}; {CITE_HALIFAX}"),
    ("MDMA", "FENT_STRIP", "POSITIVE", 0.25,
     f"{CITE_LOCKWOOD} (false positive at >= 2 mg/mL); {CITE_HALIFAX}"),
]


def seed_demo(db, *, reset: bool = False) -> dict:
    """Idempotent reference seed. Returns counts of inserted rows."""
    if reset:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()

    counts = {"users": 0, "kits": 0, "outcomes": 0, "substances": 0, "reactions": 0}

    if db.scalar(select(User.id).limit(1)) is None:
        for u in DEMO_USERS:
            db.add(
                User(
                    username=u["username"],
                    full_name=u["full_name"],
                    badge_number=u["badge_number"],
                    role=u["role"],
                    agency=u["agency"],
                    password_hash=hash_password(u["password"]),
                    is_active=True,
                )
            )
            counts["users"] += 1

    kit_by_code: dict[str, Kit] = {}
    if db.scalar(select(Kit.id).limit(1)) is None:
        for kd in KIT_DEFS:
            kit = Kit(
                code=kd["code"],
                name=kd["name"],
                test_type=kd["test_type"],
                manufacturer=kd["manufacturer"],
                description=kd["description"],
                instructions=kd["instructions"],
                reaction_time_seconds=kd["reaction_time_seconds"],
                requires_photo=kd["requires_photo"],
                is_demo=True,
                source_citation=kd["citation"],
            )
            db.add(kit)
            db.flush()
            kit_by_code[kd["code"]] = kit
            counts["kits"] += 1
            for idx, (code, label, hexv, interp, cross) in enumerate(kd["outcomes"]):
                l_ref, a_ref, b_ref = hex_to_lab(hexv)
                db.add(
                    TestOutcome(
                        kit_id=kit.id,
                        code=code,
                        label=label,
                        hex=hexv,
                        ref_l=round(l_ref, 3),
                        ref_a=round(a_ref, 3),
                        ref_b=round(b_ref, 3),
                        interpretation=interp,
                        cross_reactions=list(cross),
                        sort_order=idx,
                        is_demo=True,
                        source_citation=kd["citation"],
                    )
                )
                counts["outcomes"] += 1
    else:
        rows = db.scalars(select(Kit)).all()
        kit_by_code = {k.code: k for k in rows}

    substance_by_code: dict[str, Substance] = {}
    if db.scalar(select(Substance.id).limit(1)) is None:
        for sd in SUBSTANCE_DEFS:
            sub = Substance(
                code=sd["code"],
                name=sd["name"],
                aliases=sd["aliases"],
                substance_class=sd["substance_class"],
                notes=sd["notes"],
                is_demo=True,
                is_active=True,
                source_citation=DEMO_CITATION,
            )
            db.add(sub)
            db.flush()
            substance_by_code[sd["code"]] = sub
            counts["substances"] += 1
    else:
        rows = db.scalars(select(Substance)).all()
        substance_by_code = {s.code: s for s in rows}

    if db.scalar(select(ExpectedReaction.id).limit(1)) is None:
        outcome_index: dict[tuple[str, str], TestOutcome] = {}
        for outcome in db.scalars(select(TestOutcome)).all():
            kit = db.get(Kit, outcome.kit_id)
            outcome_index[(kit.code, outcome.code)] = outcome

        for sub_code, kit_code, outcome_code, likelihood, citation in REACTIONS:
            sub = substance_by_code.get(sub_code)
            kit = kit_by_code.get(kit_code)
            outcome = outcome_index.get((kit_code, outcome_code))
            if not (sub and kit and outcome):
                raise RuntimeError(
                    f"seed reference missing: {sub_code}/{kit_code}/{outcome_code}"
                )
            db.add(
                ExpectedReaction(
                    substance_id=sub.id,
                    kit_id=kit.id,
                    outcome_id=outcome.id,
                    likelihood=likelihood,
                    is_demo=True,
                    source_citation=citation,
                )
            )
            counts["reactions"] += 1

    db.commit()
    return counts


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FieldProof seed script")
    parser.add_argument("--reset", action="store_true", help="drop and rebuild tables")
    args = parser.parse_args(argv)

    if args.reset:
        reset_database()
    else:
        init_db()

    with SessionFactory() as db:
        counts = seed_demo(db, reset=False)

    print("FieldProof seed complete.")
    print(f"  inserted: {counts}")
    print("  demo accounts (password / role):")
    for u in DEMO_USERS:
        print(f"    {u['username']:<10} {u['password']:<20} {u['role']}")
    print(f"  reactions/kits/outcomes cite published sources ({len(REACTIONS)} rows);")
    print(f"  substance metadata keeps: {DEMO_CITATION}")
    print("  full source report: docs/reaction-data.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
