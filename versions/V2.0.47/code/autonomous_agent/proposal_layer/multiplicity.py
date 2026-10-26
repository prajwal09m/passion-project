"""Per-campaign multiplicity control (H-6/H-10b) + provisional→formal firewall.

Authorized for implementation 2026-10-12 (gate 3, D2-independent subset; see
``autonomous_agent/MAIN AUDITS AND REFLECTIONS/
HARNESS_V1_1_0_GATE3_AUTHORIZATION_RECORD_2026_10_12.md``).

Design boundaries (read before changing anything here):

* **Inert by construction.** No existing code path imported this module
  before 2026-10-12 and nothing here is wired into a gate, a threshold, a
  budget, or an approval. Every entry point must be called explicitly.
* **Exactly one statistical method is adopted, by recorded owner
  decision.** H-10/D2 were resolved on 2026-10-14: the owner adopted
  method (b) week-level sign-flip Monte-Carlo p-values (M = 1000) with
  Holm step-down (familywise alpha = 0.05), method name
  ``week_level_signflip_holm``, on the strength of Result 2′ only
  (procedure-level validity). ``APPROVED_P_VALUE_METHODS`` contains
  exactly that name and ``adjust_family()`` refuses every other value
  (``PValueMethodUnresolved``). There is no silent fallback to an
  unapproved construction. Adding or removing a method name requires a
  new recorded owner decision — an owner decision, never a code-only
  change (decision record:
  ``stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md``).
* **Fail-closed everywhere.** Missing multiplicity record → every provisional
  signal resolves INCONCLUSIVE. Infeasible granularity → no formal refutation
  can exist. Unavailable members → p = 1.0, counted toward family size,
  never REFUTED (C-2 Option A; counting them strictens, never loosens, the
  remaining members' Holm thresholds). Feasibility requires BOTH the
  bootstrap count n_boot AND the sign-flip count M (n_flips): a feasibility
  verdict recorded on n_boot alone can disagree with the actual p-value
  resolution, so a missing n_flips is infeasible, never silently feasible
  (D2 review 2026-10-13, freeze-test gap / Condition 3).
* **The bare label ``REFUTED`` is reserved** for the campaign-end
  multiplicity record. Pre-campaign-end artifacts may carry only
  ``refutation_signal`` / ``formal_refutation: false``.

Statistical roles, unchanged from the pinned plan: IUT governs ROBUST
(promotion-eligible) claims; Holm governs formal refutation claims only.
Nothing in this module can make a candidate pass an evaluation gate.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

FAMILYWISE_ALPHA = 0.05
MIN_N_BOOT = 1000          # H-10b provisional floor for any family member test
MIN_N_FLIPS = 1000         # H-10b floor for the sign-flip count M (method (b))
MAX_FAMILY_SIZE_M = 50     # D4 (m <= 50 at B = 1000 and at M = 1000)
FEASIBILITY_FACTOR = 20    # analytic bound: B + 1 >= 20 * m and M + 1 >= 20 * m

# Frozen family membership rules (plan §"Multiplicity handling"). Membership
# rules are frozen before generation; the concrete member count depends only
# on how many experiments of that primitive the campaign adjudicates.
FAMILIES: dict[str, dict[str, Any]] = {
    "regime": {"primitive": "regime_split_analysis",
               "members_per_experiment": 2, "member_bound": 24},
    "horizon": {"primitive": "target_horizon_robustness",
                "members_per_experiment": 3, "member_bound": 36},
    "purge": {"primitive": "purge_sensitivity_probe",
              "members_per_experiment": 3, "member_bound": 36},
    "complexity": {"primitive": "complexity_reduction_check",
                   "members_per_experiment": 1, "member_bound": 12},
}
PRIMITIVE_TO_FAMILY: dict[str, str] = {spec["primitive"]: name
                                       for name, spec in FAMILIES.items()}
# Campaign 1-3 tests and every primitive not named above are never pooled in.
EXCLUDED_PRIMITIVES: frozenset[str] = frozenset({
    "feature_arm_comparison", "model_class_comparison",
    "calibration_stability_check", "year_stability_falsifier",
    "minimum_effect_falsifier", "complexity_premium_check",
    "seed_set_replication", "point_in_time_data_audit",
})

STATUS_AVAILABLE = "AVAILABLE"
STATUS_UNAVAILABLE = "UNAVAILABLE"
LABEL_UNAVAILABLE = "unavailable"
LABEL_PROVISIONAL_REFUTATION = "provisional_refutation_signal"
LABEL_NO_SIGNAL = "no_refutation_signal"

FORMAL_REFUTED = "REFUTED"
FORMAL_INCONCLUSIVE = "INCONCLUSIVE"
FORMAL_UNAVAILABLE = LABEL_UNAVAILABLE

REFUTATION_SIGNAL_FIELD = "refutation_signal"
FORMAL_REFUTATION_FIELD = "formal_refutation"
REFUTATION_SIGNAL_VALUE = "unadjusted"

RECORD_TYPE = "campaign_end_multiplicity"
RECORD_SCHEMA_VERSION = 1

# H-10 / D2: RESOLVED 2026-10-14 by the owner's recorded decision
# (stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md).
# Exactly one method is approved; every other name raises.
APPROVED_P_VALUE_METHODS: frozenset[str] = frozenset({"week_level_signflip_holm"})
P_VALUE_GATE_BASIS = (
    "H-10 RESOLVED 2026-10-14: the owner's recorded decision "
    "(stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md) "
    "adopts method (b) week-level sign-flip Monte-Carlo p-values, M=1000, "
    "Holm step-down, familywise alpha=0.05 (week_level_signflip_holm), "
    "under the disclosed-substitute AI review with its conflict-of-"
    "interest disclosure. Validity is procedure-level (Result 2'-B, "
    "marginal over the recorded data-independent flip draw), never "
    "conditional on the realized flip set; Result 2 is retracted.")
# New stops this module's signals map onto (wired in continuous_loop.py).
STOP_POINT_IN_TIME_CONTAMINATION = "point_in_time_contamination_detected"
STOP_UNVERIFIABLE_LINEAGE = "unverifiable_lineage_detected"
AUDIT_STOP_CONDITIONS: frozenset[str] = frozenset(
    {STOP_POINT_IN_TIME_CONTAMINATION, STOP_UNVERIFIABLE_LINEAGE})


class MultiplicityError(Exception):
    """Invalid multiplicity usage (bad members, bad family, bad input)."""


class PValueMethodUnresolved(MultiplicityError):
    """Fail-closed: the caller named no method that the recorded H-10
    owner decision approves (exactly one is approved since 2026-10-14)."""


class GranularityInfeasible(MultiplicityError):
    """Fail-closed: B + 1 < 20 * m (or m/​B out of bounds) blocks freeze."""


class FirewallViolation(Exception):
    """A formal-refutation label appeared where it is not yet permitted."""


# --------------------------------------------------------------------- input
@dataclass(frozen=True)
class FamilyMember:
    """One predeclared refutation test entering a family at campaign end.

    ``unadjusted_p`` must come from the *approved* method once one exists;
    this module never computes it. ``ci_upper`` is the percentile-bootstrap
    upper bound kept as a disclosed provisional/effect-size functional (D3).
    """
    member_id: str
    family: str
    primitive: str
    experiment_id: str
    status: str = STATUS_AVAILABLE
    unadjusted_p: float | None = None
    ci_upper: float | None = None
    delta: float | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise MultiplicityError(
                f"undeclared family {self.family!r}; families are frozen "
                f"before generation and may not be broadened after results "
                f"exist (declared: {sorted(FAMILIES)})")
        if self.primitive != FAMILIES[self.family]["primitive"]:
            raise MultiplicityError(
                f"family {self.family!r} is defined for "
                f"{FAMILIES[self.family]['primitive']!r}, not {self.primitive!r}")
        if self.primitive in EXCLUDED_PRIMITIVES:
            raise MultiplicityError(
                f"{self.primitive!r} never enters a Holm family")
        if self.status not in (STATUS_AVAILABLE, STATUS_UNAVAILABLE):
            raise MultiplicityError(f"unknown member status {self.status!r}")
        if self.status == STATUS_AVAILABLE:
            if self.unadjusted_p is None or not 0.0 <= float(self.unadjusted_p) <= 1.0:
                raise MultiplicityError(
                    f"available member {self.member_id!r} needs a p-value in "
                    f"[0, 1] (got {self.unadjusted_p!r})")
        # C-2: an unavailable member's p is pinned to 1.0 by construction; it
        # is never stored as anything else and can never be REFUTED.

    @property
    def effective_p(self) -> float:
        """C-2 Option A: unavailable members count toward m at p = 1.0."""
        return 1.0 if self.status == STATUS_UNAVAILABLE else float(self.unadjusted_p)

    @property
    def provisional_signal(self) -> bool:
        """Unadjusted CI signal (upper < 0). Provisional, never a claim."""
        return self.ci_upper is not None and float(self.ci_upper) < 0.0

    def signal_fields(self) -> dict[str, Any]:
        """The ONLY refutation fields a pre-campaign-end artifact may carry."""
        return {
            REFUTATION_SIGNAL_FIELD: REFUTATION_SIGNAL_VALUE,
            FORMAL_REFUTATION_FIELD: False,
            "provisional_label": (LABEL_PROVISIONAL_REFUTATION
                                  if self.provisional_signal else LABEL_NO_SIGNAL),
            "provisional_displays_as": ("provisional, not a refutation claim"
                                        if self.provisional_signal else
                                        "no provisional signal"),
        }


@dataclass(frozen=True)
class MemberDecision:
    member_id: str
    family: str
    experiment_id: str
    status: str
    raw_delta: float | None
    raw_ci_upper: float | None
    unadjusted_p: float | None
    adjusted_p: float | None
    raw_label: str
    formal_status: str
    survived_adjustment: bool
    ci_disagrees_with_p: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_id": self.member_id, "family": self.family,
            "experiment_id": self.experiment_id, "status": self.status,
            "raw_delta": self.raw_delta, "raw_ci_upper": self.raw_ci_upper,
            "unadjusted_p": self.unadjusted_p, "adjusted_p": self.adjusted_p,
            "raw_label": self.raw_label, "formal_status": self.formal_status,
            "survived_adjustment": self.survived_adjustment,
            "ci_disagrees_with_p": self.ci_disagrees_with_p,
            "reason": self.reason,
        }


# ----------------------------------------------------------------- p gate
def approved_p_value_methods() -> frozenset[str]:
    return APPROVED_P_VALUE_METHODS


def require_approved_method(method: str | None) -> str:
    """Fail-closed gate. Raises unless the caller names the recorded method.

    This is the single choke point for adjusted p-values: exactly the
    owner-recorded method (``week_level_signflip_holm``) passes; every
    other name, including plausible-sounding variants and the empty set,
    raises, so no artifact can carry an adjusted p-value computed by an
    unapproved construction.
    """
    if not APPROVED_P_VALUE_METHODS:
        raise PValueMethodUnresolved(
            f"refusing to compute adjusted p-values: {P_VALUE_GATE_BASIS}")
    if method is None or str(method) not in APPROVED_P_VALUE_METHODS:
        raise PValueMethodUnresolved(
            f"p-value method {method!r} is not among the approved methods "
            f"{sorted(APPROVED_P_VALUE_METHODS)}")
    return str(method)


# -------------------------------------------------------------------- Holm
def holm_step_down(p_values: Sequence[float],
                   alpha: float = FAMILYWISE_ALPHA
                   ) -> tuple[list[float], list[bool]]:
    """Holm step-down: (adjusted p-values, rejection flags) at familywise α.

    Adjusted values are monotone (max over the prefix) and capped at 1.0;
    rejection stops at the first non-rejection, exactly as the step-down
    procedure requires. Input order is preserved.
    """
    p_list = [float(p) for p in p_values]
    if not p_list:
        raise MultiplicityError("Holm requires at least one member test")
    if any(not 0.0 <= p <= 1.0 for p in p_list):
        raise MultiplicityError(f"p-values must lie in [0, 1]: {p_list!r}")
    if not 0.0 < float(alpha) < 1.0:
        raise MultiplicityError(f"alpha must be in (0, 1): {alpha!r}")
    m = len(p_list)
    order = sorted(range(m), key=lambda i: (p_list[i], i))
    adjusted = [0.0] * m
    rejects = [False] * m
    running = 0.0
    rejecting = True
    for rank, index in enumerate(order):
        scale = m - rank                       # (m - k + 1)
        running = max(running, min(1.0, scale * p_list[index]))
        adjusted[index] = running
        if rejecting and p_list[index] <= alpha / scale:
            rejects[index] = True
        else:
            rejecting = False                  # step-down stops here
    return adjusted, rejects


def feasibility(n_boot: int, family_size: int,
                n_flips: int | None = None) -> tuple[bool, list[str]]:
    """H-10b freeze-time feasibility on BOTH counts, plus D4 bounds.

    The bootstrap count n_boot governs the CI's granularity; the sign-flip
    count M (``n_flips``) governs the p-value's resolution: the smallest
    representable p is 1/(M+1), so a formal refutation at Holm's first
    threshold alpha/m is attainable only while M + 1 >= 20*m. A feasibility
    verdict recorded on n_boot alone can therefore disagree with what the
    p-value can actually resolve -- conservative in effect, but wrongly
    labelled feasible. ``n_flips=None`` (not recorded) is infeasible, with
    the missing value named in the reasons; it is never silently feasible.
    """
    reasons: list[str] = []
    if family_size <= 0:
        reasons.append("family is empty")
    if family_size > MAX_FAMILY_SIZE_M:
        reasons.append(f"family size m={family_size} exceeds the D4 cap "
                       f"{MAX_FAMILY_SIZE_M}")
    if int(n_boot) < MIN_N_BOOT:
        reasons.append(f"n_boot={n_boot} is below the H-10b floor {MIN_N_BOOT}")
    if int(n_boot) + 1 < FEASIBILITY_FACTOR * family_size:
        reasons.append(f"n_boot+1={int(n_boot) + 1} < 20*m="
                       f"{FEASIBILITY_FACTOR * family_size}")
    if n_flips is None:
        reasons.append("n_flips (M) not recorded: the p-value resolution "
                       "cannot be verified, so feasibility on n_boot alone "
                       "may not certify a formal refutation")
    else:
        if int(n_flips) < MIN_N_FLIPS:
            reasons.append(f"n_flips={n_flips} is below the H-10b floor "
                           f"{MIN_N_FLIPS}")
        if int(n_flips) + 1 < FEASIBILITY_FACTOR * family_size:
            reasons.append(f"n_flips+1={int(n_flips) + 1} < 20*m="
                           f"{FEASIBILITY_FACTOR * family_size}")
    return (not reasons), reasons


def require_feasible(n_boot: int, family_size: int,
                     n_flips: int | None = None) -> None:
    """Freeze-block variant: raises instead of returning the reasons."""
    ok, reasons = feasibility(n_boot, family_size, n_flips)
    if not ok:
        raise GranularityInfeasible(
            "freeze blocked: " + "; ".join(reasons))


# ---------------------------------------------------------------- adjusting
def adjust_family(members: Sequence[FamilyMember], *,
                  n_boot: int, p_value_method: str | None,
                  n_flips: int | None = None,
                  alpha: float = FAMILYWISE_ALPHA) -> list[MemberDecision]:
    """Holm-adjust one declared family at campaign end (fail-closed).

    Order of refusals matters and is deliberate:
      1. p-value method gate (H-10 open → nothing is computed at all);
      2. family coherence (one declared family, frozen membership rules);
      3. granularity feasibility on BOTH counts (n_boot and n_flips=M;
         infeasible → every member INCONCLUSIVE, never REFUTED, so an
         infeasible experiment can never produce a formal refutation).
    """
    require_approved_method(p_value_method)              # 1
    items = list(members)
    if not items:
        raise MultiplicityError("cannot adjust an empty family")
    families = {item.family for item in items}
    if len(families) != 1:
        raise MultiplicityError(
            f"family members must share one declared family, got {sorted(families)}")
    family = next(iter(families))
    primitives = {item.primitive for item in items}
    if primitives != {FAMILIES[family]["primitive"]}:
        raise MultiplicityError(
            f"family {family!r} accepts only "
            f"{FAMILIES[family]['primitive']!r} tests, got {sorted(primitives)}")
    m = len(items)                                        # 2: C-2 counts all
    ok, reasons = feasibility(int(n_boot), m, n_flips)    # 3
    if not ok:
        return [MemberDecision(
            member_id=item.member_id, family=item.family,
            experiment_id=item.experiment_id, status=item.status,
            raw_delta=item.delta, raw_ci_upper=item.ci_upper,
            unadjusted_p=(None if item.status == STATUS_UNAVAILABLE
                          else item.unadjusted_p),
            adjusted_p=None,
            raw_label=(LABEL_UNAVAILABLE if item.status == STATUS_UNAVAILABLE
                       else (LABEL_PROVISIONAL_REFUTATION
                             if item.provisional_signal else LABEL_NO_SIGNAL)),
            formal_status=(FORMAL_UNAVAILABLE if item.status == STATUS_UNAVAILABLE
                           else FORMAL_INCONCLUSIVE),
            survived_adjustment=False, ci_disagrees_with_p=False,
            reason="granularity_infeasible: " + "; ".join(reasons))
            for item in items]

    adjusted, rejects = holm_step_down([item.effective_p for item in items], alpha)
    decisions: list[MemberDecision] = []
    for item, adj, reject in zip(items, adjusted, rejects):
        if item.status == STATUS_UNAVAILABLE:
            decisions.append(MemberDecision(
                member_id=item.member_id, family=item.family,
                experiment_id=item.experiment_id, status=item.status,
                raw_delta=item.delta, raw_ci_upper=item.ci_upper,
                unadjusted_p=None, adjusted_p=adj,
                raw_label=LABEL_UNAVAILABLE, formal_status=FORMAL_UNAVAILABLE,
                survived_adjustment=False, ci_disagrees_with_p=False,
                reason="C-2: unavailable member counted toward m at p=1.0; "
                       "never formally REFUTED"))
            continue
        formal = FORMAL_REFUTED if reject else FORMAL_INCONCLUSIVE
        raw_label = (LABEL_PROVISIONAL_REFUTATION if item.provisional_signal
                     else LABEL_NO_SIGNAL)
        # Disclosed reconciliation (D3/D4): formal decisions follow the
        # adjusted p-value only; the CI signal is kept beside it and any
        # disagreement is recorded, never silently absorbed.
        disagrees = reject != item.provisional_signal
        decisions.append(MemberDecision(
            member_id=item.member_id, family=item.family,
            experiment_id=item.experiment_id, status=item.status,
            raw_delta=item.delta, raw_ci_upper=item.ci_upper,
            unadjusted_p=item.unadjusted_p, adjusted_p=adj,
            raw_label=raw_label, formal_status=formal,
            survived_adjustment=reject, ci_disagrees_with_p=disagrees,
            reason="holm_step_down"))
    return decisions


def assemble_record(*, campaign_id: str,
                    family_decisions: Mapping[str, Sequence[MemberDecision]],
                    n_boot: int, p_value_method: str | None,
                    n_flips: int | None = None,
                    alpha: float = FAMILYWISE_ALPHA,
                    ledger_sha256: str | None = None) -> dict[str, Any]:
    """Format already-adjusted decisions into the campaign-end record.

    Performs **no statistics**: it only assembles decisions that
    ``adjust_family`` produced, and re-checks the frozen family bounds so a
    record can never be written for a family larger than its declared cap.
    Every member row must carry the unadjusted numbers alongside the
    adjusted ones (H-6 unadjusted retention).
    """
    if not family_decisions:
        raise MultiplicityError("no families supplied for the campaign-end record")
    out_families: dict[str, Any] = {}
    for family, decisions in family_decisions.items():
        items = list(decisions)
        declared = FAMILIES.get(family)
        if declared is None:
            raise MultiplicityError(f"undeclared family {family!r}")
        if not items:
            raise MultiplicityError(f"family {family!r} has no decisions")
        bound = int(declared["member_bound"])
        if len(items) > bound:
            raise MultiplicityError(
                f"family {family!r} has {len(items)} members but its frozen "
                f"member bound is {bound}; a family may never exceed its "
                f"declared bound after results exist")
        rows = []
        for decision in items:
            row = decision.to_dict()
            if decision.formal_status == FORMAL_REFUTED \
                    and decision.adjusted_p is None:
                raise MultiplicityError(
                    f"member {decision.member_id!r} claims a formal status "
                    f"without an adjusted p-value")
            rows.append(row)
        ok, reasons = feasibility(int(n_boot), len(items), n_flips)
        out_families[family] = {
            "m": len(items),
            "member_bound": bound,
            "primitive": declared["primitive"],
            "alpha": alpha,
            "feasibility": {"n_boot": int(n_boot),
                            "n_flips": (None if n_flips is None
                                        else int(n_flips)),
                            "rules": ["n_boot + 1 >= 20 * m",
                                      "n_flips + 1 >= 20 * m"],
                            "feasible": ok,
                            "reasons": reasons},
            "members": rows,
        }
    return {
        "record_type": RECORD_TYPE,
        "schema_version": RECORD_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "p_value_method": p_value_method,
        "familywise_alpha": alpha,
        "ledger_sha256": ledger_sha256,
        "unadjusted_retained": True,
        "note": ("Formal REFUTED status is assigned by this record only. "
                 "Unadjusted signals that did not survive adjustment are "
                 "INCONCLUSIVE, never refutations. Monte-Carlo resolution "
                 "disclosure: the sign-flip p-value grid is (1+k)/(M+1); its "
                 "floor 1/(M+1) reaches Holm's first threshold alpha/m only "
                 "while m <= alpha*(M+1) (m <= 50 at M=1000), and borderline "
                 "members (true p near a threshold) are resolved with low "
                 "probability, always biased toward non-rejection; validity "
                 "is procedure-level (marginal over the recorded flip draw), "
                 "never conditional on the realized flip set (D2 review + "
                 "Addendum A, 2026-10-13)."),
        "families": out_families,
    }


def campaign_end_record(*, campaign_id: str, families: Mapping[str, Sequence[FamilyMember]],
                        n_boot: int, p_value_method: str | None,
                        n_flips: int | None = None,
                        alpha: float = FAMILYWISE_ALPHA,
                        ledger_sha256: str | None = None) -> dict[str, Any]:
    """The append-only campaign-end multiplicity record (H-6), computed.

    Lists every member test with its unadjusted numbers *and* its adjusted
    decision side by side; nothing is erased. Family sizes are checked
    against the frozen bounds on BOTH counts (n_boot and n_flips=M) before
    the record can exist.
    """
    require_approved_method(p_value_method)
    adjusted: dict[str, list[MemberDecision]] = {}
    for family, members in families.items():
        items = list(members)
        declared = FAMILIES.get(family)
        if declared is None:
            raise MultiplicityError(f"undeclared family {family!r}")
        require_feasible(int(n_boot), len(items), n_flips)
        adjusted[family] = adjust_family(items, n_boot=int(n_boot),
                                         p_value_method=p_value_method,
                                         n_flips=n_flips, alpha=alpha)
    return assemble_record(campaign_id=campaign_id, family_decisions=adjusted,
                           n_boot=int(n_boot), p_value_method=p_value_method,
                           n_flips=n_flips, alpha=alpha,
                           ledger_sha256=ledger_sha256)


def append_record(path: Path | str, record: Mapping[str, Any]) -> dict[str, Any]:
    """Append one campaign-end record. Append-only and idempotent-safe.

    Refuses to write a second record for the same campaign: the multiplicity
    record is finalized once, and re-running must not silently re-decide.
    """
    path = Path(path)
    campaign_id = str(record.get("campaign_id"))
    if record.get("record_type") != RECORD_TYPE:
        raise MultiplicityError("refusing to append a non-multiplicity record")
    existing: list[str] = []
    if path.is_file():
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row.get("record_type") != RECORD_TYPE:
                raise MultiplicityError("multiplicity record file contains a "
                                        "foreign row type; refusing to append")
            existing.append(str(row.get("campaign_id")))
    if campaign_id in existing:
        raise MultiplicityError(
            f"a campaign-end multiplicity record for {campaign_id!r} already "
            f"exists; it may never be recomputed or overwritten")
    line = json.dumps(dict(record), sort_keys=True, default=str) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())
    return dict(record)


def read_records(path: Path | str) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.is_file():
        return []
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def formal_refuted_members(record: Mapping[str, Any]) -> list[str]:
    """Member ids the record marks REFUTED (empty for anything malformed)."""
    out: list[str] = []
    for family in (record.get("families") or {}).values():
        for member in (family.get("members") or []):
            if member.get("formal_status") == FORMAL_REFUTED:
                out.append(str(member.get("member_id")))
    return sorted(out)


# --------------------------------------------------------------- fail-closed
def resolve_without_record(members: Sequence[FamilyMember]) -> list[MemberDecision]:
    """No multiplicity record exists → every provisional signal is INCONCLUSIVE.

    Fail-closed default: a campaign that terminated before the campaign-end
    pass (exhaustion, manual stop, crash) can never produce a formal
    refutation. Signals are preserved, never promoted.
    """
    decisions = []
    for item in members:
        decisions.append(MemberDecision(
            member_id=item.member_id, family=item.family,
            experiment_id=item.experiment_id, status=item.status,
            raw_delta=item.delta, raw_ci_upper=item.ci_upper,
            unadjusted_p=(None if item.status == STATUS_UNAVAILABLE
                          else item.unadjusted_p),
            adjusted_p=None,
            raw_label=(LABEL_UNAVAILABLE if item.status == STATUS_UNAVAILABLE
                       else (LABEL_PROVISIONAL_REFUTATION
                             if item.provisional_signal else LABEL_NO_SIGNAL)),
            formal_status=(FORMAL_UNAVAILABLE if item.status == STATUS_UNAVAILABLE
                           else FORMAL_INCONCLUSIVE),
            survived_adjustment=False, ci_disagrees_with_p=False,
            reason="no_campaign_end_multiplicity_record"))
    return decisions


# ------------------------------------------------------------------ firewall
_REFUTED_TOKEN = re.compile(r"(?<![A-Za-z_])REFUTED(?![A-Za-z_])")


def find_formal_refutation_labels(value: Any, path: str = "$") -> list[str]:
    """Locate every standalone ``REFUTED`` label in an artifact tree.

    ``provisional_refutation_signal`` and ``formal_refutation`` do NOT match
    (the token is bounded by non-word characters), so provisional markers
    are legal everywhere; the bare formal label is not.
    """
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            hits.extend(find_formal_refutation_labels(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            hits.extend(find_formal_refutation_labels(item, f"{path}[{index}]"))
    elif isinstance(value, str) and _REFUTED_TOKEN.search(value):
        hits.append(f"{path}={value!r}")
    return hits


def assert_firewall_intact(value: Any, *, context: str) -> None:
    """Raise unless the artifact is free of premature formal-refutation labels."""
    hits = find_formal_refutation_labels(value)
    if hits:
        raise FirewallViolation(
            f"{context}: bare REFUTED label(s) before the campaign-end "
            f"multiplicity record exists: {hits[:5]} (record only "
            f"refutation_signal / formal_refutation=false until then)")


def scan_text_for_formal_refutation(text: str, *, context: str) -> None:
    """Same firewall for free-text artifacts (reports, stdout capture)."""
    if _REFUTED_TOKEN.search(text):
        raise FirewallViolation(
            f"{context}: free text asserts a formal refutation before the "
            f"campaign-end multiplicity record exists")


def describe_provisional(decisions: Sequence[MemberDecision]) -> list[dict[str, Any]]:
    """Render decisions for pre-campaign-end readers: never a refutation claim."""
    out = []
    for decision in decisions:
        row = decision.to_dict()
        row.pop("formal_status", None)
        row.pop("survived_adjustment", None)
        row[FORMAL_REFUTATION_FIELD] = False
        row[REFUTATION_SIGNAL_FIELD] = REFUTATION_SIGNAL_VALUE
        row["provisional_displays_as"] = ("provisional, not a refutation claim"
                                          if decision.raw_label ==
                                          LABEL_PROVISIONAL_REFUTATION else
                                          "no provisional signal")
        out.append(row)
    return out


# ------------------------------------------------- audit stop signals (H-2)
_CONTAMINATION_MARKERS = ("CONFIRMED_CONTAMINATION", "CONTAMINATION_CONFIRMED")
_LINEAGE_STOP_MARKERS = ("UNVERIFIABLE_LINEAGE", "LINEAGE_UNVERIFIABLE")
# Keys that carry an audit verdict. Census column entries use ``verdict``,
# never ``status``: a disclosed Tier-2 column being UNVERIFIABLE is expected
# and must never halt a campaign, whereas an audit-level lineage verdict of
# UNVERIFIABLE must.
_AUDIT_STATUS_KEYS = ("status", "lineage_status", "audit_status")


def _walk_status_fields(node: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(node, Mapping):
        for key, item in node.items():
            child = f"{path}.{key}"
            if key in _AUDIT_STATUS_KEYS and isinstance(item, str):
                yield child, item
            yield from _walk_status_fields(item, child)
    elif isinstance(node, (list, tuple)):
        for index, item in enumerate(node):
            yield from _walk_status_fields(item, f"{path}[{index}]")


def audit_stop_signal(outcome: Mapping[str, Any]) -> tuple[str, str] | None:
    """Map a completed experiment's audit fields onto a fail-closed stop.

    Contract (declared, not inferred): an outcome whose point-in-time audit
    reports confirmed contamination halts the campaign for human data-lineage
    review; an outcome whose lineage is UNVERIFIABLE halts the campaign
    because lineage cannot be proven. Absence of these fields signals
    nothing — v1.0.0 outcomes never carry them, so this is inert today.
    """
    for where, raw in _walk_status_fields(outcome):
        verdict = raw.upper()
        if any(marker in verdict for marker in _CONTAMINATION_MARKERS):
            return (STOP_POINT_IN_TIME_CONTAMINATION,
                    f"point_in_time_data_audit reported {raw!r} at {where}")
        if where.rsplit(".", 1)[-1] in ("lineage_status", "audit_status") \
                and "UNVERIFIABLE" in verdict:
            return (STOP_UNVERIFIABLE_LINEAGE,
                    f"{raw!r} at {where}")
        if any(marker in verdict for marker in _LINEAGE_STOP_MARKERS):
            return (STOP_UNVERIFIABLE_LINEAGE,
                    f"{raw!r} at {where}")
    return None


def recorded_audit_stop(rows: Iterable[Mapping[str, Any]]) -> tuple[str, str] | None:
    """Fold durable ledger rows: a recorded audit stop survives restarts."""
    for row in rows:
        detail = row.get("detail")
        if not isinstance(detail, Mapping):
            continue
        stop = audit_stop_signal(detail)
        if stop is not None:
            return stop
    return None


def family_of(primitive: str) -> str | None:
    return PRIMITIVE_TO_FAMILY.get(primitive)


def family_manifest() -> dict[str, Any]:
    """The frozen family table (for config reconciliation and freeze checks)."""
    return {
        "families": {name: dict(spec) for name, spec in FAMILIES.items()},
        "max_family_size_m": MAX_FAMILY_SIZE_M,
        "min_n_boot": MIN_N_BOOT,
        "min_n_flips": MIN_N_FLIPS,
        "feasibility_rule": ("n_boot + 1 >= 20 * m AND n_flips + 1 >= 20 * m "
                             "for every declared family (both counts "
                             "required; a missing n_flips is infeasible)"),
        "familywise_alpha": FAMILYWISE_ALPHA,
        "correction": "holm_step_down",
        "pooling": "campaign_end_over_complete_family",
        "missing_member_rule": "C-2 Option A: counts toward m at p=1.0, "
                               "labelled unavailable, never formally "
                               "REFUTED; counting strictens, never loosens, "
                               "the remaining members' thresholds",
        "approved_p_value_methods": sorted(APPROVED_P_VALUE_METHODS),
        "p_value_gate": P_VALUE_GATE_BASIS,
    }
