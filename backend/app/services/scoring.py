"""Identification engine: data-driven evidence scoring.

Design rules (do not break):
  * NO substance-specific logic in this module. Every expected reaction comes
    from the `expected_reactions` table; every substance name comes from the
    `substances` table. The only domain knowledge here is the word list used to
    detect ambiguous/contradictory *patterns*, never to name drugs.
  * Equal priors, log-space multiplication of likelihoods, floor likelihood so an
    unexpected-but-possible outcome never eliminates a candidate.
  * Status ladder: NO_MATCH, WEAK_PRESUMPTIVE, PRESUMPTIVE, STRONG_PRESUMPTIVE,
    CONFIRMED_BY_LAB. A lab-confirmed status requires a LAB_CONFIRMATORY entry
    with a method and a recognised compound.
  * The hard rules (presumptive only / concentration not determinable) are
    emitted on every result.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..config import settings
from ..enums import CONCENTRATION_NOT_DETERMINABLE, DISCLAIMER, RESULT_STATUS
from ..database import utcnow

# --------------------------------------------------------------------------- #
# tunables
# --------------------------------------------------------------------------- #
FLOOR_LIKELIHOOD = 0.02      # unexpected-but-possible outcomes keep a chance
SUPPORT_THRESHOLD = 0.50     # likelihood at/above this => the test supports
CONTRADICT_THRESHOLD = 0.10  # likelihood at/below this => the test contradicts
NO_MATCH_THRESHOLD = 0.30    # normalised top score below this => NO_MATCH
CLOSE_MARGIN = 0.15          # top-two gap below this => ambiguous/mixture flag
STRONG_SCORE = 0.75
STRONG_GAP = 0.30
PRESUMPTIVE_SCORE = 0.50
MIN_SPECTROMETER_SCORE = 50.0

AMBIGUOUS_FLAG = "Possible mixture or ambiguous: refer to laboratory"

# confidence band (heuristic, documented in README/docs - not a statistical CI)
CONFIDENCE_PRIOR_BITS = 2.0   # evidence needed before the band narrows past ~50%
CONFIDENCE_LAB_BITS = 12.0    # a resolved lab-confirmatory reading pins the band
CONFIDENCE_NARROW = 0.25      # band width at/below this -> "narrow"
CONFIDENCE_MODERATE = 0.60    # band width at/below this -> "moderate"

_NORMALISE_RE = re.compile(r"[^a-z0-9]+")


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return _NORMALISE_RE.sub("", value.lower())


# --------------------------------------------------------------------------- #
# inputs
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Candidate:
    id: str
    code: str
    name: str
    aliases: tuple[str, ...] = ()


@dataclass
class Observation:
    """One test as entered by the officer / lab user."""

    ref: str
    test_type: str
    kit_id: str | None = None
    kit_code: str = ""
    kit_name: str = ""
    outcome_code: str | None = None
    outcome_label: str | None = None
    inconclusive: bool = False
    kit_batch: str | None = None
    # spectrometer
    library_match: str | None = None
    match_score: float | None = None
    # lab confirmatory
    lab_method: str | None = None
    lab_compound: str | None = None
    lab_reference: str | None = None
    purity_percent: float | None = None

    @property
    def label(self) -> str:
        if self.test_type == "LAB_CONFIRMATORY":
            return f"{self.lab_method or 'lab method'} -> {self.lab_compound or '?'}"
        if self.test_type == "SPECTROMETER":
            return f"{self.kit_code or 'spectrometer'} -> {self.library_match or '?'}"
        return f"{self.kit_code or self.kit_name} -> {self.outcome_label or self.outcome_code or '?'}"


@dataclass
class ReactionIndex:
    """Lookup table loaded from the database (never hardcoded here)."""

    candidates: list[Candidate]
    # (substance_id, kit_id, outcome_code) -> likelihood
    likelihoods: dict[tuple[str, str, str], float] = field(default_factory=dict)
    # (kit_id, outcome_code) -> list of known cross-reacting substances
    cross_reactions: dict[tuple[str, str], list[str]] = field(default_factory=dict)
    # kit code -> kit id (lets callers pass kit_code only)
    kit_ids: dict[str, str] = field(default_factory=dict)
    # (substance_id, kit_id, outcome_code) -> source citation for that row
    citations: dict[tuple[str, str, str], str] = field(default_factory=dict)

    def kit_id_for(self, obs: "Observation") -> str | None:
        if obs.kit_id:
            return obs.kit_id
        return self.kit_ids.get(obs.kit_code) if obs.kit_code else None

    def likelihood(
        self, substance_id: str, kit_id: str | None, outcome_code: str | None
    ) -> float:
        if not kit_id or not outcome_code:
            return FLOOR_LIKELIHOOD
        value = self.likelihoods.get((substance_id, kit_id, outcome_code))
        if value is None:
            return FLOOR_LIKELIHOOD
        return min(max(value, FLOOR_LIKELIHOOD), 1.0)

    def resolve(self, name: str | None) -> Candidate | None:
        """Resolve a free-text substance name to a candidate (data-driven)."""
        target = _norm(name)
        if not target:
            return None
        for cand in self.candidates:
            names = {_norm(cand.code), _norm(cand.name)} | {_norm(a) for a in cand.aliases}
            if target in names:
                return cand
        matches = [
            cand
            for cand in self.candidates
            if any(
                (alias and (alias in target or target in alias))
                for alias in (
                    _norm(cand.code),
                    _norm(cand.name),
                    *[_norm(a) for a in cand.aliases],
                )
                if len(alias) >= 4
            )
        ]
        return matches[0] if len(matches) == 1 else None

    def cross(self, kit_id: str | None, outcome_code: str | None) -> list[str]:
        if not kit_id or not outcome_code:
            return []
        return list(self.cross_reactions.get((kit_id, outcome_code), []))

    def citation(
        self, substance_id: str, kit_id: str | None, outcome_code: str | None
    ) -> str | None:
        """Source citation for one expected-reaction row (None when unlisted)."""
        if not kit_id or not outcome_code:
            return None
        return self.citations.get((substance_id, kit_id, outcome_code))


# --------------------------------------------------------------------------- #
# core scoring
# --------------------------------------------------------------------------- #
@dataclass
class EvidenceRow:
    ref: str
    test_type: str
    kit_code: str
    kit_name: str
    outcome_label: str
    informative: bool
    supports: bool | None          # None = not informative for the top match
    likelihood: float | None       # likelihood of observed outcome for top match
    note: str
    cross_reactions: list[str] = field(default_factory=list)
    source_citation: str | None = None  # expected-reaction row citation

    def as_dict(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "test_type": self.test_type,
            "kit_code": self.kit_code,
            "kit_name": self.kit_name,
            "outcome_label": self.outcome_label,
            "informative": self.informative,
            "supports": self.supports,
            "likelihood": self.likelihood,
            "note": self.note,
            "cross_reactions": self.cross_reactions,
            "source_citation": self.source_citation,
        }


def _classify(likelihood: float) -> tuple[bool | None, str]:
    if likelihood >= SUPPORT_THRESHOLD:
        return True, "supports"
    if likelihood <= CONTRADICT_THRESHOLD:
        return False, "contradicts"
    return None, "weak / not decisive"


def _per_observation_scores(
    index: ReactionIndex, obs: Observation
) -> dict[str, float] | None:
    """Return {substance_id: likelihood} for an informative observation.

    Returns None when the observation carries no usable evidence.
    """
    if obs.inconclusive:
        return None
    kit_id = index.kit_id_for(obs)
    if obs.test_type == "IMMUNOASSAY_STRIP":
        if obs.outcome_code in (None, "", "INVALID"):
            return None
        return {
            c.id: index.likelihood(c.id, kit_id, obs.outcome_code)
            for c in index.candidates
        }
    if obs.test_type == "COLOUR_REAGENT":
        if not obs.outcome_code:
            return None
        return {
            c.id: index.likelihood(c.id, kit_id, obs.outcome_code)
            for c in index.candidates
        }
    if obs.test_type == "SPECTROMETER":
        score = obs.match_score if obs.match_score is not None else 0.0
        resolved = index.resolve(obs.library_match)
        if resolved is None or score < MIN_SPECTROMETER_SCORE:
            return None
        strength = min(max(score / 100.0, FLOOR_LIKELIHOOD), 1.0)
        return {
            c.id: (strength if c.id == resolved.id else FLOOR_LIKELIHOOD)
            for c in index.candidates
        }
    if obs.test_type == "LAB_CONFIRMATORY":
        resolved = index.resolve(obs.lab_compound)
        if resolved is None or not obs.lab_method:
            return None
        return {
            c.id: (0.99 if c.id == resolved.id else FLOOR_LIKELIHOOD)
            for c in index.candidates
        }
    return None


def _discrimination_bits(per_sub: dict[str, float]) -> float:
    """KL(likelihood profile || uniform) in bits for one reading.

    How far one observation moves the candidates away from an uninformative
    reading; a profile where every candidate shares the same likelihood
    scores exactly 0.
    """
    values = list(per_sub.values())
    n = len(values)
    if n == 0:
        return 0.0
    total = sum(values)
    if total <= 0:
        return 0.0
    bits = 0.0
    for value in values:
        if value <= 0:
            continue
        p = value / total
        bits += p * math.log2(p * n)
    return max(bits, 0.0)


def _confidence_band(
    *,
    top_score: float,
    evidence_bits: float,
    contradictions: int,
    has_evidence: bool,
    lab_resolved: bool,
) -> dict[str, Any]:
    """Heuristic uncertainty band around the leading score.

    Starts at [0, 1] when no discriminating evidence exists and collapses
    toward the posterior score as KL bits accumulate; each contradiction
    halves the effective evidence; a resolved lab-confirmatory reading pins
    the band. Deliberately documented as a heuristic, not a statistical
    confidence interval.
    """
    method = (
        "Heuristic band: starts at 0-100% with no discriminating evidence and "
        "shrinks toward the score as evidence accumulates (each contradiction "
        "halves it). Not a statistical confidence interval."
    )
    if not has_evidence:
        return {
            "low": 0.0,
            "high": 1.0,
            "width": 1.0,
            "centre": 0.5,
            "evidence_bits": round(evidence_bits, 2),
            "label": "insufficient evidence",
            "method": method,
        }
    effective = evidence_bits * (0.5 ** contradictions)
    if lab_resolved:
        effective = max(effective, CONFIDENCE_LAB_BITS)
    w = effective / (effective + CONFIDENCE_PRIOR_BITS)
    centre = 0.5 + (top_score - 0.5) * w
    half = 0.5 * (1.0 - w)
    low = max(0.0, centre - half)
    high = min(1.0, centre + half)
    width = high - low
    if width <= CONFIDENCE_NARROW:
        label = "narrow"
    elif width <= CONFIDENCE_MODERATE:
        label = "moderate"
    else:
        label = "wide"
    return {
        "low": round(low, 4),
        "high": round(high, 4),
        "width": round(width, 4),
        "centre": round(centre, 4),
        "evidence_bits": round(evidence_bits, 2),
        "label": label,
        "method": method,
    }


def analyze(index: ReactionIndex, observations: Iterable[Observation]) -> dict[str, Any]:
    """Compute the explainable analysis result for a set of test observations."""
    observations = list(observations)
    candidates = index.candidates
    n_cand = max(len(candidates), 1)

    score_log: dict[str, float] = {c.id: -math.log(n_cand) for c in candidates}
    evidence: list[EvidenceRow] = []
    informative_refs: list[str] = []
    presumptive_informative = 0
    non_discriminating_refs: list[str] = []
    discriminating_evidence = False
    evidence_bits = 0.0
    lab_entry: dict[str, Any] | None = None
    flags: list[str] = []
    rule_notes: list[str] = []
    inconclusive_count = 0
    non_informative_count = 0

    for obs in observations:
        per_sub = _per_observation_scores(index, obs)
        cross = index.cross(index.kit_id_for(obs), obs.outcome_code)

        if obs.inconclusive:
            inconclusive_count += 1

        if per_sub is None:
            non_informative_count += 1
            reason = (
                "Inconclusive reading - not used as evidence."
                if obs.inconclusive
                else "Result not usable as evidence (invalid / inconclusive / unresolved)."
            )
            evidence.append(
                EvidenceRow(
                    ref=obs.ref,
                    test_type=obs.test_type,
                    kit_code=obs.kit_code,
                    kit_name=obs.kit_name,
                    outcome_label=obs.outcome_label
                    or obs.library_match
                    or obs.lab_compound
                    or "",
                    informative=False,
                    supports=None,
                    likelihood=None,
                    note=reason,
                    cross_reactions=cross,
                )
            )
            continue

        for cid, likelihood in per_sub.items():
            score_log[cid] += math.log(likelihood)
        evidence_bits += _discrimination_bits(per_sub)

        informative_refs.append(obs.ref)
        if obs.test_type == "LAB_CONFIRMATORY":
            resolved = index.resolve(obs.lab_compound)
            lab_entry = {
                "method": obs.lab_method,
                "compound": obs.lab_compound,
                "reference": obs.lab_reference,
                "purity_percent": obs.purity_percent,
                "substance_id": resolved.id if resolved else None,
                "substance_name": resolved.name if resolved else None,
                "ref": obs.ref,
            }
        else:
            presumptive_informative += 1

    # normalise log scores -> probabilities
    max_log = max(score_log.values()) if score_log else 0.0
    raw = {cid: math.exp(value - max_log) for cid, value in score_log.items()}
    total = sum(raw.values()) or 1.0
    probs = {cid: value / total for cid, value in raw.items()}

    ranked = sorted(
        (
            {"substance_id": c.id, "code": c.code, "name": c.name,
             "score": probs.get(c.id, 0.0), "percentage": round(probs.get(c.id, 0.0) * 100, 1)}
            for c in candidates
        ),
        key=lambda r: r["score"],
        reverse=True,
    )
    top = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None
    gap = (top["score"] - second["score"]) if (top and second) else (top["score"] if top else 0.0)

    # ------------------------------------------------------------------ rules
    contradictory_refs: list[str] = []
    supporting_refs: list[str] = []
    if top is not None:
        top_id = top["substance_id"]
        for obs in observations:
            per_sub = _per_observation_scores(index, obs)
            if per_sub is None:
                continue
            likelihood = per_sub.get(top_id, FLOOR_LIKELIHOOD)
            cross = index.cross(index.kit_id_for(obs), obs.outcome_code)
            citation = index.citation(top_id, index.kit_id_for(obs), obs.outcome_code)
            if len(set(per_sub.values())) == 1:
                # Every candidate shares the same expected likelihood for this
                # outcome: the reading carries no discriminating information
                # and must not be read as support or contradiction.
                non_discriminating_refs.append(obs.ref)
                evidence.append(
                    EvidenceRow(
                        ref=obs.ref,
                        test_type=obs.test_type,
                        kit_code=obs.kit_code,
                        kit_name=obs.kit_name,
                        outcome_label=obs.outcome_label
                        or obs.library_match
                        or obs.lab_compound
                        or "",
                        informative=True,
                        supports=None,
                        likelihood=round(likelihood, 4),
                        note=(
                            "The reference data gives every candidate the same "
                            f"expected likelihood ({likelihood:.2f}) for this "
                            "outcome, so the reading does not discriminate "
                            "between candidates."
                        ),
                        cross_reactions=cross,
                        source_citation=citation,
                    )
                )
                continue
            discriminating_evidence = True
            supports, word = _classify(likelihood)
            if obs.test_type == "SPECTROMETER":
                detail = f"library match '{obs.library_match}' at {obs.match_score}%"
            elif obs.test_type == "LAB_CONFIRMATORY":
                detail = f"{obs.lab_method} -> {obs.lab_compound}"
            else:
                detail = f"observed '{obs.outcome_label or obs.outcome_code}'"
            note = (
                f"{detail}: expected likelihood {likelihood:.2f} for "
                f"{top['name']} - {word}."
            )
            evidence.append(
                EvidenceRow(
                    ref=obs.ref,
                    test_type=obs.test_type,
                    kit_code=obs.kit_code,
                    kit_name=obs.kit_name,
                    outcome_label=obs.outcome_label
                    or obs.library_match
                    or obs.lab_compound
                    or "",
                    informative=True,
                    supports=supports,
                    likelihood=round(likelihood, 4),
                    note=note,
                    cross_reactions=cross,
                    source_citation=citation,
                )
            )
            if supports:
                supporting_refs.append(obs.ref)
            elif supports is False:
                contradictory_refs.append(obs.ref)

    if lab_entry is None and any(o.test_type == "LAB_CONFIRMATORY" for o in observations):
        flags.append(
            "Laboratory entry incomplete (method or compound missing/unrecognised) "
            "- not treated as confirmatory."
        )

    if contradictory_refs:
        rule_notes.append(
            f"{len(contradictory_refs)} test(s) contradict the leading candidate "
            f"(expected likelihood <= {CONTRADICT_THRESHOLD}), which can indicate a "
            "mixture, an adulterant or a cross-reaction."
        )

    if non_discriminating_refs:
        rule_notes.append(
            f"{len(non_discriminating_refs)} reading(s) had no discriminating "
            "expectation in the reference data (every candidate shares the same "
            "expected likelihood), so they neither supported nor contradicted "
            "any candidate."
        )

    has_evidence = len(informative_refs) > 0
    status = _resolve_status(
        top_score=top["score"] if top else 0.0,
        gap=gap,
        presumptive_informative=presumptive_informative,
        has_informative=has_evidence,
        has_any=len(observations) > 0,
        lab_entry=lab_entry,
        contradictory=bool(contradictory_refs),
        notes=rule_notes,
    )

    if contradictory_refs:
        flags.append(AMBIGUOUS_FLAG)
    elif (
        gap < CLOSE_MARGIN
        and len(ranked) > 1
        and presumptive_informative >= 1
        and discriminating_evidence
    ):
        flags.append(AMBIGUOUS_FLAG)
        rule_notes.append(
            f"The top two candidates are only {round(gap * 100, 1)} percentage points "
            "apart, which can indicate a mixture or an ambiguous reaction."
        )

    if inconclusive_count:
        flags.append(
            f"{inconclusive_count} inconclusive test reading(s) excluded from scoring."
        )

    confidence = _confidence_band(
        top_score=top["score"] if top else 0.0,
        evidence_bits=evidence_bits,
        contradictions=len(contradictory_refs),
        has_evidence=has_evidence,
        lab_resolved=bool(lab_entry and lab_entry.get("substance_id")),
    )

    # ----------------------------------------------------------------- output
    alternatives = [
        r for r in ranked[1:] if r["percentage"] >= 2.0
    ][:5]
    cross_reactions = []
    seen_cross: set[tuple[str, str]] = set()
    for row in evidence:
        if not row.cross_reactions:
            continue
        key = (row.kit_code, row.outcome_label)
        if key in seen_cross:
            continue
        seen_cross.add(key)
        cross_reactions.append(
            {
                "kit_code": row.kit_code,
                "outcome_label": row.outcome_label,
                "substances": row.cross_reactions,
            }
        )

    concentration = CONCENTRATION_NOT_DETERMINABLE
    if lab_entry and lab_entry.get("purity_percent") is not None:
        ref = f", lab ref {lab_entry['reference']}" if lab_entry.get("reference") else ""
        concentration = (
            f"Purity: {lab_entry['purity_percent']}% (laboratory quantitative method: "
            f"{lab_entry['method']}{ref})"
        )

    explanation = _explain(
        n_candidates=len(candidates),
        n_observations=len(observations),
        n_informative=len(informative_refs),
        presumptive_informative=presumptive_informative,
        ranked=ranked,
        evidence=evidence,
        status=status,
        flags=flags,
        rule_notes=rule_notes,
        lab_entry=lab_entry,
        top_score=top["score"] if top else 0.0,
        gap=gap,
    )
    if has_evidence:
        explanation += (
            f" Uncertainty band for the leading candidate: "
            f"{confidence['low'] * 100:.0f}% to {confidence['high'] * 100:.0f}% "
            f"({confidence['label']} band; heuristic, not a statistical "
            "confidence interval)."
        )

    return {
        "engine_version": settings.engine_version,
        "computed_at": utcnow().isoformat() + "Z",
        "status": status,
        "top_match": (
            {
                "substance_id": top["substance_id"],
                "code": top["code"],
                "name": top["name"],
                "percentage": top["percentage"],
            }
            if (top and has_evidence)
            else None
        ),
        "alternatives": alternatives,
        "ranked": ranked,
        "evidence": [row.as_dict() for row in evidence],
        "supporting_refs": supporting_refs,
        "contradicting_refs": contradictory_refs,
        "flags": flags,
        "rule_notes": rule_notes,
        "cross_reactions": cross_reactions,
        "concentration": concentration,
        "disclaimer": DISCLAIMER,
        "explanation": explanation,
        "confidence": confidence,
        "counts": {
            "tests_entered": len(observations),
            "informative": len(informative_refs),
            "presumptive_informative": presumptive_informative,
            "inconclusive": inconclusive_count,
            "non_informative": non_informative_count,
            "candidates": len(candidates),
        },
        "lab_confirmation": lab_entry,
        "lab_confirmed": status == "CONFIRMED_BY_LAB",
    }


def _resolve_status(
    *,
    top_score: float,
    gap: float,
    presumptive_informative: int,
    has_informative: bool,
    has_any: bool,
    lab_entry: dict[str, Any] | None,
    contradictory: bool,
    notes: list[str],
) -> str:
    if lab_entry is not None and lab_entry.get("substance_id"):
        notes.append(
            f"A laboratory confirmatory result ({lab_entry['method']}) for "
            f"{lab_entry['compound']} was entered by an authorised lab user, so the "
            "status is CONFIRMED_BY_LAB."
        )
        return "CONFIRMED_BY_LAB"

    if not has_any:
        notes.append("No tests were entered, so there is nothing to score.")
        return "NO_MATCH"

    if not has_informative:
        notes.append(
            "Every entered test was inconclusive or unusable, so no evidence was "
            "scored."
        )
        return "INCONCLUSIVE"

    if top_score < NO_MATCH_THRESHOLD:
        notes.append(
            f"The top normalised score ({round(top_score * 100, 1)}%) is below the "
            f"{int(NO_MATCH_THRESHOLD * 100)}% threshold, so the result is NO_MATCH."
        )
        return "NO_MATCH"

    if presumptive_informative == 1:
        notes.append(
            "Only one presumptive test was entered, so the status is capped at "
            "WEAK_PRESUMPTIVE."
        )
        status = "WEAK_PRESUMPTIVE"
    elif top_score >= STRONG_SCORE and gap >= STRONG_GAP and not contradictory:
        status = "STRONG_PRESUMPTIVE"
    elif top_score >= PRESUMPTIVE_SCORE:
        status = "PRESUMPTIVE"
    else:
        status = "WEAK_PRESUMPTIVE"

    if contradictory and status in {"STRONG_PRESUMPTIVE", "PRESUMPTIVE"}:
        status = "PRESUMPTIVE" if status == "STRONG_PRESUMPTIVE" else "WEAK_PRESUMPTIVE"
        notes.append(
            "At least one test contradicts the leading candidate, so the status is "
            "capped below its score-based level."
        )
    if gap < CLOSE_MARGIN and status == "STRONG_PRESUMPTIVE":
        status = "PRESUMPTIVE"
        notes.append(
            "The leading candidates are too close together for a STRONG_PRESUMPTIVE "
            "status."
        )
    return status


def _explain(
    *,
    n_candidates: int,
    n_observations: int,
    n_informative: int,
    presumptive_informative: int,
    ranked: list[dict[str, Any]],
    evidence: list[EvidenceRow],
    status: str,
    flags: list[str],
    rule_notes: list[str],
    lab_entry: dict[str, Any] | None,
    top_score: float,
    gap: float,
) -> str:
    parts: list[str] = []
    parts.append(
        f"{n_observations} test entr{'y' if n_observations == 1 else 'ies'} "
        f"{'was' if n_observations == 1 else 'were'} received; {n_informative} "
        f"carried usable evidence. All {n_candidates} "
        f"candidate substances started with an equal prior (1/{n_candidates})."
    )
    parts.append(
        f"Each test multiplied a candidate's score by the expected likelihood of the "
        f"observed outcome for that substance (floor {FLOOR_LIKELIHOOD} so unexpected "
        "but possible outcomes are not eliminated), then the scores were normalised "
        "to percentages."
    )

    if ranked and n_informative:
        top = ranked[0]
        drivers = [
            row.note
            for row in evidence
            if row.informative and row.supports
        ][:4]
        driver_text = " ".join(drivers) if drivers else "no test agreed with it"
        parts.append(
            f"{top['name']} ranks first at {top['percentage']}%. Supporting evidence: "
            f"{driver_text}"
        )
        if lab_entry:
            parts.append(
                f"Laboratory method {lab_entry['method']} identified "
                f"{lab_entry['compound']} (ref {lab_entry['reference'] or 'n/a'})."
            )
        others = [r for r in ranked[1:] if r["percentage"] >= 2.0][:3]
        if others:
            listing = ", ".join(f"{r['name']} {r['percentage']}%" for r in others)
            parts.append(f"Cannot yet be ruled out: {listing}.")
    elif n_observations:
        parts.append("No candidate could be supported by the evidence supplied.")

    for note in rule_notes:
        parts.append(note)
    for flag in flags:
        if flag == AMBIGUOUS_FLAG:
            parts.append(f"Flag raised: {flag}.")
        elif "inconclusive" in flag.lower():
            parts.append(flag)

    if presumptive_informative and lab_entry is None:
        parts.append(
            "This is a presumptive field result only; laboratory confirmation is "
            "required before any substance is considered identified."
        )
    parts.append(CONCENTRATION_NOT_DETERMINABLE + "." if lab_entry is None or lab_entry.get("purity_percent") is None else "")
    parts.append(f"Final status: {status}.")
    return " ".join(p for p in parts if p)


# --------------------------------------------------------------------------- #
# database helpers
# --------------------------------------------------------------------------- #
def build_reaction_index(db) -> ReactionIndex:
    """Load candidates + expected reactions from the database."""
    from ..models import ExpectedReaction, Kit, Substance, TestOutcome

    substances = (
        db.query(Substance).filter(Substance.is_active.is_(True)).all()
    )
    candidates = [
        Candidate(
            id=s.id,
            code=s.code,
            name=s.name,
            aliases=tuple(s.aliases or []),
        )
        for s in substances
    ]

    likelihoods: dict[tuple[str, str, str], float] = {}
    citations: dict[tuple[str, str, str], str] = {}
    for row in db.query(ExpectedReaction).all():
        outcome = db.get(TestOutcome, row.outcome_id)
        if outcome is None:
            continue
        key = (row.substance_id, row.kit_id, outcome.code)
        likelihoods[key] = row.likelihood
        if row.source_citation:
            citations[key] = row.source_citation

    cross: dict[tuple[str, str], list[str]] = {}
    for outcome in db.query(TestOutcome).all():
        if outcome.cross_reactions:
            cross[(outcome.kit_id, outcome.code)] = list(outcome.cross_reactions)

    kit_ids = {kit.code: kit.id for kit in db.query(Kit).all()}

    return ReactionIndex(
        candidates=candidates,
        likelihoods=likelihoods,
        cross_reactions=cross,
        kit_ids=kit_ids,
        citations=citations,
    )


def observation_from_sample_test(test) -> Observation:
    """Map a SampleTest row to an engine Observation."""
    kit = test.kit
    reading = test.reading_json or {}
    payload = {
        "ref": test.id,
        "test_type": test.test_type,
        "kit_id": kit.id if kit else None,
        "kit_code": kit.code if kit else "",
        "kit_name": kit.name if kit else "",
        "outcome_code": test.outcome_code,
        "outcome_label": test.outcome_label,
        "inconclusive": bool(reading.get("inconclusive")),
        "kit_batch": test.kit_batch,
        "library_match": (test.input_json or {}).get("library_match"),
        "match_score": (test.input_json or {}).get("match_score"),
        "lab_method": (test.input_json or {}).get("method"),
        "lab_compound": (test.input_json or {}).get("compound"),
        "lab_reference": (test.input_json or {}).get("lab_reference"),
        "purity_percent": (test.input_json or {}).get("purity_percent"),
    }
    return Observation(**payload)


def analyze_sample(db, sample) -> dict[str, Any]:
    index = build_reaction_index(db)
    observations = [observation_from_sample_test(t) for t in sample.tests]
    return analyze(index, observations)


VALID_STATUSES = set(RESULT_STATUS)
