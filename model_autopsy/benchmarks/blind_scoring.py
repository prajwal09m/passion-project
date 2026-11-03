"""Machine-checkable contract for the Phase D blind quality rubric (v1).

The narrative rubric is `phase_d_blind_scoring_rubric_v1.md`; this module is
its executable mirror so the later analysis cannot silently change the scale.
It performs no I/O and makes no provider calls.

Six dimensions, integer scores 0-2 each, unweighted maximum 12. Structured-
summary validity is deliberately NOT part of this total.
"""
from __future__ import annotations

RUBRIC_VERSION = "v1"

DIMENSIONS: tuple[tuple[str, str], ...] = (
    ("mechanism_identification", "Mechanism identification"),
    ("numeric_grounding", "Numeric grounding"),
    ("evidence_linkage", "Evidence linkage"),
    ("calibration", "Calibration"),
    ("diagnostic_reasoning", "Diagnostic reasoning"),
    ("execution_honesty", "Execution honesty"),
)

ALLOWED_SCORES = (0, 1, 2)
MAX_TOTAL = 2 * len(DIMENSIONS)  # 12
assert MAX_TOTAL == 12


class ScoringError(ValueError):
    """A score set does not match the frozen rubric contract."""


def validate_scores(scores: dict) -> dict[str, int]:
    """Return a clean {dimension_key: score} mapping or raise ScoringError.

    Rejects missing/unknown dimensions, non-integers (including bools), and
    any value outside {0, 1, 2}. No weights, half points, or bonuses.
    """
    if not isinstance(scores, dict):
        raise ScoringError("scores must be a mapping of dimension -> 0|1|2")
    expected = {key for key, _ in DIMENSIONS}
    unknown = set(scores) - expected
    missing = expected - set(scores)
    if unknown or missing:
        raise ScoringError(
            f"dimension mismatch: missing={sorted(missing)} "
            f"unknown={sorted(unknown)}")
    clean: dict[str, int] = {}
    for key, _label in DIMENSIONS:
        value = scores[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ScoringError(f"{key} must be an integer 0, 1, or 2")
        if value not in ALLOWED_SCORES:
            raise ScoringError(f"{key}={value} is outside {{0, 1, 2}}")
        clean[key] = value
    return clean


def total_score(scores: dict) -> int:
    """Unweighted sum of the six validated dimension scores (0-12)."""
    return sum(validate_scores(scores).values())
