"""Shared three-valued result model for harness v1.1.0 primitives.

Authorized by the owner's R-3 grant (2026-10-12); see
``autonomous_agent/MAIN AUDITS AND REFLECTIONS/PRIMITIVE_ACTIVATION_GRANT_R3_2026_10_12.md``.

The model (pinned plan, "Shared three-valued result model"):

* **ROBUST** — every predeclared primary condition passes, **including its
  CI requirement**. Only ROBUST can satisfy an evaluation gate.
* **REFUTED** — a predeclared primary condition is refuted *under the
  multiplicity rule*. This module never emits REFUTED: formal refutation is
  assigned only by the campaign-end multiplicity record, and while H-10 is
  open the p-value gate refuses, so nothing here can produce one. What it
  emits is a **provisional refutation signal**, which is a different thing
  and is labelled as such.
* **INCONCLUSIVE** — neither, including every under-powered, under-sized, or
  wide-CI outcome. INCONCLUSIVE consumes its execution slot, fails the
  evaluation gate, cannot promote, and is never upgraded.

Two rules this module enforces structurally:

1. **No point-estimate-only pass.** Every pass condition is a pair
   (point threshold, CI requirement). A condition whose CI requirement is
   absent or unmet cannot pass, whatever its point estimate says.
2. **IUT, not Holm, governs ROBUSTness.** A claim is ROBUST only when every
   member condition independently passes. Holm governs refutation claims
   only and is applied elsewhere (``proposal_layer.multiplicity``); the two
   mechanisms never substitute for one another.

Nothing here computes a p-value, reads data, or touches the holdout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

ROBUST = "ROBUST"
INCONCLUSIVE = "INCONCLUSIVE"
# Formal REFUTED is reserved for the campaign-end multiplicity record. The
# provisional signal this module emits is deliberately a different token so
# no reader can mistake one for the other.
FORMAL_REFUTED = "REFUTED"
PROVISIONAL_REFUTATION_SIGNAL = "provisional_refutation_signal"

# H-1: -0.01 is a PROVISIONAL study-consistency margin carried from the
# existing gates' ci_lower_min. It is NOT statistically validated: no cost
# model exists (backtest NOT_RUN; trading claims prohibited), so no
# domain-derived equivalence bound can be computed.
PROVISIONAL_MARGIN = -0.01
MARGIN_PROVENANCE = (
    "PROVISIONAL study-consistency margin carried from the existing gates' "
    "ci_lower_min = -0.01; not statistically validated (H-1). No cost model "
    "exists, so no domain-derived equivalence bound is available."
)

# -- Frozen ladders (plan, "Multiplicity handling" and per-primitive sections)
# Enumerated, never computed at runtime: a rung may not be invented after
# results exist.
PURGE_RUNGS_SESSIONS = (0, 5, 10)
HORIZON_RUNGS_SESSIONS = (1, 2, 3)
REGIME_CELLS = ("above_sma200", "below_sma200")
COMPLEXITY_PRIMARY_RUNG = "primary"

# Sample floors. A run below its floor is under-sized and must be
# INCONCLUSIVE — never a pass, never a refutation.
MIN_FOLD_ROWS = 30
MIN_CELL_ROWS = 50
MIN_CELL_EVENTS = 5
MIN_BOOT_FOR_INFERENCE = 1000          # H-10b floor for any family member test


class ThreeValuedError(Exception):
    """A condition or result violates the frozen three-valued contract."""


@dataclass(frozen=True)
class Margin:
    """A predeclared acceptance margin, always paired with a CI requirement.

    ``value`` is the point threshold; ``ci_lower_min`` is the CI requirement
    that must ALSO hold. ``provisional`` marks margins carried from H-1 that
    are not statistically validated (every ladder margin in this project).
    """

    value: float
    ci_lower_min: float | None
    direction: str = "min"          # "min": metric >= value  |  "max": metric <= value
    provisional: bool = True
    provenance: str = MARGIN_PROVENANCE

    def __post_init__(self) -> None:
        if self.direction not in ("min", "max"):
            raise ThreeValuedError(f"unknown margin direction {self.direction!r}")
        if self.ci_lower_min is None:
            # Point-estimate-only pass conditions are forbidden (H-1).
            raise ThreeValuedError(
                "a margin without a CI requirement would allow a "
                "point-estimate-only pass, which is forbidden (H-1)")

    def point_passes(self, point: float) -> bool:
        return point >= self.value if self.direction == "min" else point <= self.value

    def ci_passes(self, ci_lower: float) -> bool:
        return float(ci_lower) >= float(self.ci_lower_min)


@dataclass(frozen=True)
class ConditionResult:
    """One predeclared condition evaluated against one rung/cell/member."""

    name: str
    status: str                       # ROBUST | INCONCLUSIVE | provisional_refutation_signal
    reason: str = ""
    point: float | None = None
    ci_lower: float | None = None
    n_rows: int | None = None
    n_events: int | None = None
    detail: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "reason": self.reason,
                "point": self.point, "ci_lower": self.ci_lower,
                "n_rows": self.n_rows, "n_events": self.n_events,
                "detail": dict(self.detail)}


@dataclass(frozen=True)
class ThreeValuedResult:
    """A primitive's verdict, with every member condition retained."""

    primitive_id: str
    status: str                       # ROBUST | INCONCLUSIVE
    conditions: tuple[ConditionResult, ...]
    provisional_refutation_signals: tuple[str, ...] = ()
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "status": self.status,
            "formal_refutation": False,          # firewall: never formal here
            "refutation_signal": "unadjusted" if self.provisional_refutation_signals else None,
            "provisional_refutation_conditions": list(self.provisional_refutation_signals),
            "provisional_displays_as": ("provisional, not a refutation claim"
                                        if self.provisional_refutation_signals else
                                        "no provisional signal"),
            "conditions": [condition.to_dict() for condition in self.conditions],
            "note": self.note,
        }


def evaluate_condition(*, name: str, point: float, ci_lower: float,
                       margin: Margin, n_rows: int | None = None,
                       n_events: int | None = None,
                       min_rows: int = MIN_FOLD_ROWS,
                       min_events: int = MIN_CELL_EVENTS) -> ConditionResult:
    """Evaluate ONE condition: power floor, then paired point+CI gate.

    Ordering matters and is deliberate: an under-sized run is INCONCLUSIVE
    *regardless of how good its numbers look*, so a small sample can never
    pass and never refute.
    """
    if n_rows is not None and int(n_rows) < int(min_rows):
        return ConditionResult(
            name=name, status=INCONCLUSIVE,
            reason=f"under-sized: {n_rows} rows < floor {min_rows}",
            point=point, ci_lower=ci_lower, n_rows=n_rows, n_events=n_events)
    if n_events is not None and int(n_events) < int(min_events):
        return ConditionResult(
            name=name, status=INCONCLUSIVE,
            reason=f"under-powered: {int(n_events)} events < floor {min_events}",
            point=point, ci_lower=ci_lower, n_rows=n_rows, n_events=n_events)
    point_ok = margin.point_passes(point)
    ci_ok = margin.ci_passes(ci_lower)
    if point_ok and ci_ok:
        return ConditionResult(name=name, status=ROBUST,
                               reason="point and CI requirements both met",
                               point=point, ci_lower=ci_lower,
                               n_rows=n_rows, n_events=n_events)
    if point_ok and not ci_ok:
        # The CI is the binding requirement: a point pass with an unmet CI is
        # INCONCLUSIVE, never a pass, and never a refutation either (the
        # effect is simply not resolved).
        return ConditionResult(
            name=name, status=INCONCLUSIVE,
            reason=(f"point estimate passes ({point} vs margin {margin.value}) "
                    f"but the CI requirement fails (ci_lower {ci_lower} < "
                    f"{margin.ci_lower_min}); a point-estimate-only pass is "
                    f"forbidden (H-1)"),
            point=point, ci_lower=ci_lower, n_rows=n_rows, n_events=n_events)
    # Unadjusted refutation signal: the point estimate is on the wrong side of
    # the margin AND the CI excludes the margin. Provisional only — the formal
    # decision belongs to the campaign-end multiplicity record.
    return ConditionResult(
        name=name, status=PROVISIONAL_REFUTATION_SIGNAL,
        reason=(f"unadjusted signal: point {point} is on the wrong side of "
                f"margin {margin.value} and ci_lower {ci_lower} excludes it; "
                f"provisional, not a refutation claim"),
        point=point, ci_lower=ci_lower, n_rows=n_rows, n_events=n_events)


def combine_iut(primitive_id: str, conditions: Sequence[ConditionResult], *,
                note: str = "") -> ThreeValuedResult:
    """Intersection-union combination: ROBUST iff EVERY condition is ROBUST.

    INCONCLUSIVE from any member propagates (a partially-answered question is
    not an answer). Provisional refutation signals are collected but never
    promoted to REFUTED — that is the campaign-end record's job alone.
    """
    if not conditions:
        raise ThreeValuedError(
            f"{primitive_id}: an experiment with no predeclared conditions "
            f"cannot be evaluated (refusing to invent a verdict)")
    signals = tuple(condition.name for condition in conditions
                    if condition.status == PROVISIONAL_REFUTATION_SIGNAL)
    if all(condition.status == ROBUST for condition in conditions):
        status = ROBUST
    else:
        status = INCONCLUSIVE
    return ThreeValuedResult(
        primitive_id=primitive_id, status=status,
        conditions=tuple(conditions),
        provisional_refutation_signals=signals, note=note)


def underpowered_wide_ci_result(primitive_id: str, *, name: str,
                                point: float, ci_lower: float,
                                n_rows: int | None = None,
                                n_events: int | None = None) -> ThreeValuedResult:
    """The explicit underpowered/wide-CI fixture shape: INCONCLUSIVE, always.

    Kept as a named constructor because the plan requires this exact outcome
    to be tested: an underpowered wide-CI run must return INCONCLUSIVE, never
    pass, whatever its point estimate.
    """
    condition = ConditionResult(
        name=name, status=INCONCLUSIVE,
        reason="underpowered/wide-CI: the effect is not resolved; "
               "INCONCLUSIVE consumes its slot and cannot promote",
        point=point, ci_lower=ci_lower, n_rows=n_rows, n_events=n_events)
    return ThreeValuedResult(primitive_id=primitive_id, status=INCONCLUSIVE,
                             conditions=(condition,))


# -- Frozen ladder enumeration (never computed at runtime) -------------------
def ladder_for(primitive_id: str) -> dict[str, Any]:
    """The frozen rung/cell enumeration for a v1.1.0 primitive.

    Enumerated from the frozen tables above. A primitive with no ladder
    (complexity reduction has a single primary rung) returns its explicit
    single-member ladder, so the enumeration is never empty and never
    derived from data.
    """
    ladders: dict[str, dict[str, Any]] = {
        "purge_sensitivity_probe": {
            "kind": "purge_run", "rungs": list(PURGE_RUNGS_SESSIONS),
            "unit": "sessions", "members_per_experiment": len(PURGE_RUNGS_SESSIONS),
            "family": "purge",
        },
        "target_horizon_robustness": {
            "kind": "horizon_run", "rungs": list(HORIZON_RUNGS_SESSIONS),
            "unit": "sessions", "members_per_experiment": len(HORIZON_RUNGS_SESSIONS),
            "family": "horizon",
        },
        "regime_split_analysis": {
            "kind": "regime_cell", "rungs": list(REGIME_CELLS),
            "unit": "cell", "members_per_experiment": len(REGIME_CELLS),
            "family": "regime",
        },
        "complexity_reduction_check": {
            "kind": "reduction_rung", "rungs": [COMPLEXITY_PRIMARY_RUNG],
            "unit": "rung", "members_per_experiment": 1,
            "family": "complexity",
            "related_primitive": "model_class_comparison",
        },
        "point_in_time_data_audit": {
            "kind": "audit_suite", "rungs": ["source_vintage", "universe_membership",
                                             "timestamps", "label_maturity"],
            "unit": "check", "members_per_experiment": 4,
            "family": None,        # the audit never enters a Holm family
        },
    }
    ladder = ladders.get(primitive_id)
    if ladder is None:
        raise ThreeValuedError(f"{primitive_id!r} has no frozen ladder; "
                               f"ladders may not be invented at runtime")
    return dict(ladder)


def audit_tri_state(checks: Mapping[str, str]) -> str:
    """Point-in-time audit outcome: CLEAN / UNVERIFIABLE / CONFIRMED.

    Ruling R-4 (owner, 2026-10-12): a run whose only defects are disclosed
    Tier-2 (parity-UNVERIFIABLE) columns is an **audit FAIL, no partial
    pass**, never contamination. A value mismatch on a Tier-2 column can
    never yield CONFIRMED; an unrecoverable source is UNVERIFIABLE; anything
    else that fails is CONFIRMED and halts the campaign.
    """
    allowed = {"CLEAN", "UNVERIFIABLE", "CONFIRMED_CONTAMINATION"}
    for name, verdict in checks.items():
        if verdict not in allowed:
            raise ThreeValuedError(
                f"audit check {name!r} returned unknown verdict {verdict!r}; "
                f"the tri-state vocabulary is {sorted(allowed)}")
    values = set(checks.values())
    if "CONFIRMED_CONTAMINATION" in values:
        return "CONFIRMED_CONTAMINATION"
    if "UNVERIFIABLE" in values:
        return "UNVERIFIABLE"
    return "CLEAN"


def tier2_only_defect_is_fail(unverifiable_columns: Iterable[str],
                              mismatched_columns: Iterable[str]) -> str:
    """R-4: disclosed Tier-2 defects are an audit FAIL, never a pass.

    A mismatch on a disclosed Tier-2 (parity-UNVERIFIABLE) column is a
    provenance limitation, not evidence of look-ahead, so it never becomes
    CONFIRMED_CONTAMINATION — but it is also never a clean bill of health.
    """
    tier2 = set(unverifiable_columns)
    mismatched = set(mismatched_columns)
    if mismatched - tier2:
        return "CONFIRMED_CONTAMINATION"     # a non-Tier-2 column disagreed
    if mismatched & tier2:
        return "FAIL"                        # R-4: disclosed Tier-2 defect
    return "CLEAN"
