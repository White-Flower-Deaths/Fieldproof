"""Shared string enums.

Stored as plain strings in the database so the schema stays portable
between SQLite (development) and PostgreSQL (production).
"""
from __future__ import annotations

from typing import Literal

Role = Literal["OFFICER", "LAB", "ADMIN"]
ROLES = ("OFFICER", "LAB", "ADMIN")

APPEARANCE = (
    "POWDER",
    "CRYSTALS",
    "PILL_TABLET",
    "PLANT_MATERIAL",
    "BLOTTER",
    "LIQUID",
    "OTHER",
)

TEST_TYPE = ("COLOUR_REAGENT", "IMMUNOASSAY_STRIP", "SPECTROMETER", "LAB_CONFIRMATORY")

RESULT_STATUS = (
    "NO_MATCH",
    "WEAK_PRESUMPTIVE",
    "PRESUMPTIVE",
    "STRONG_PRESUMPTIVE",
    "INCONCLUSIVE",
    "CONFIRMED_BY_LAB",
)

# Statuses that carry the "needs a human look" meaning in the UI.
AMBIGUOUS_STATUSES = ("INCONCLUSIVE",)

DISCLAIMER = (
    "PRESUMPTIVE FIELD RESULT ONLY. Not a substitute for laboratory "
    "confirmatory testing. Colour and immunoassay tests are presumptive; "
    "confirmatory methods (GC-MS, LC-MS, FTIR, etc.) are required before any "
    "substance is considered identified."
)

CONCENTRATION_NOT_DETERMINABLE = "Concentration: not determinable from presumptive tests"

DEMO_CITATION = (
    "DEMO DATA - verify against UNODC Recommended Methods and the kit "
    "manufacturer's colour chart before real use"
)
