"""BiasGovernor: portfolio quotas + outcome-blind selection schema (Phase 1 F).

Two responsibilities:

1. ``selection_inputs`` / ``score`` — the ONLY inputs proposal ranking may
   use. ``preregistered_expectation`` and any predicted result are structurally
   excluded (closed input set), so expected outcomes can never act as a hidden
   acceptance criterion.
2. ``check_accept`` — hard portfolio constraints from ``bias_policy.json``:
   minimum falsification share, maximum replication share, per-direction and
   per-class budgets, total cap, per-signature cap.
"""
from __future__ import annotations

from typing import Any, Mapping

from autonomous_agent.proposal_layer import schema

# The closed set of ranking inputs. Anything else is not an input — by code.
SELECTION_INPUT_FIELDS = (
    "direction",
    "proposal_class",
    "novelty_score",
    "evidence_gap_score",
    "quota_pressure",
    "priority",
    "attempts_in_direction",
)

_DEFAULT_POLICY: dict[str, Any] = {
    "schema_version": 1,
    "policy_version": "1.0.0",
    "directions": [],
    "direction_priorities": {},
    "max_total_proposals": 20,
    "max_per_direction": 4,
    "max_signature_count": 2,
    "min_falsification_share": 0.35,
    "max_replication_share": 0.50,
    "class_budgets": {"confirmatory": 8, "falsification": 8,
                      "replication": 2, "exploration": 2},
    "max_proposals_per_cycle": 3,
    "allow_future_primitives": False,
    "require_human_approval": True,
    "near_duplicate_text_threshold": schema.NEAR_DUPLICATE_TEXT_THRESHOLD,
    "score_weights": {"quota": 0.40, "novelty": 0.30, "evidence_gap": 0.15,
                      "priority": 0.10, "exploration": 0.05},
}


def merge_policy(overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    policy = dict(_DEFAULT_POLICY)
    if overrides:
        policy.update(dict(overrides))
    return policy


class BiasGovernor:
    def __init__(self, policy: Mapping[str, Any]) -> None:
        self.policy = merge_policy(policy)

    # -- closed selection schema -------------------------------------------
    def selection_inputs(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        """Extract exactly the allowed ranking inputs. Raises on absence so
        callers cannot silently fall back to outcome-like fields."""
        missing = [field for field in SELECTION_INPUT_FIELDS
                   if field not in candidate]
        if missing:
            raise KeyError(f"Selection input(s) missing: {missing}")
        return {field: candidate[field] for field in SELECTION_INPUT_FIELDS}

    def score(self, candidate: Mapping[str, Any]) -> float:
        inputs = self.selection_inputs(candidate)
        weights = self.policy["score_weights"]
        priority_norm = float(inputs["priority"])  # already 0..1 in the registry
        exploration = 0.08 / (float(inputs["attempts_in_direction"]) + 1.0)
        return (
            float(weights["quota"]) * float(inputs["quota_pressure"])
            + float(weights["novelty"]) * float(inputs["novelty_score"])
            + float(weights["evidence_gap"]) * float(inputs["evidence_gap_score"])
            + float(weights["priority"]) * priority_norm
            + float(weights["exploration"]) * exploration
        )

    # -- portfolio accounting ------------------------------------------------
    def quota_state(self, merged_proposals: list[Mapping[str, Any]],
                    *, campaign_id: str | None = None) -> dict[str, Any]:
        """Post-creation quota picture.

        ``campaign_id`` scopes BUDGET accounting to one campaign: only
        proposals carrying that campaign id count against caps/quotas.
        Prior-campaign records are excluded from budgets but remain fully
        visible to the DUPLICATE gate (already-asked memory is global and
        permanent — budget scoping never weakens duplicate protection).
        Default ``None`` = count every record (legacy behavior).
        """
        by_class: dict[str, int] = {}
        by_direction: dict[str, int] = {}
        by_signature: dict[str, int] = {}
        total = 0
        seen_fingerprints: set[str] = set()
        for item in merged_proposals:
            payload = item.get("proposal") or {}
            if campaign_id is not None and \
                    payload.get("campaign_id") != campaign_id:
                continue
            # Exact re-asks (identical proposal_fingerprint) collapse into
            # the original: caps count DISTINCT designs. The re-ask itself
            # is still refused permanently by the DUPLICATE gate — dedupe
            # here only prevents a copy from inflating budget/quota usage.
            fingerprint = payload.get("proposal_fingerprint")
            if isinstance(fingerprint, str) and fingerprint:
                if fingerprint in seen_fingerprints:
                    continue
                seen_fingerprints.add(fingerprint)
            # Distinct refusals/failures still consume budget (permanent
            # record) — forgetting refusals is the bias risk, not counting them.
            total += 1
            cls = str(payload.get("proposal_class"))
            by_class[cls] = by_class.get(cls, 0) + 1
            direction = str(payload.get("direction"))
            by_direction[direction] = by_direction.get(direction, 0) + 1
            sig = str(payload.get("design_signature"))
            by_signature[sig] = by_signature.get(sig, 0) + 1
        falsification = by_class.get("falsification", 0)
        replication = by_class.get("replication", 0)
        return {
            "total": total,
            "by_class": by_class,
            "by_direction": by_direction,
            "by_signature": by_signature,
            "falsification_share": (falsification / total) if total else 0.0,
            "replication_share": (replication / total) if total else 0.0,
        }

    # -- acceptance gate -----------------------------------------------------
    def check_accept(self, payload: Mapping[str, Any],
                     state: Mapping[str, Any]) -> tuple[bool, str | None, str]:
        """Hard portfolio constraints. Returns (ok, reason_code, detail).

        Accounting contract: ``state`` is post-creation (it INCLUDES the
        proposal under review), so caps compare with ``>``: a budget of N
        admits exactly N recorded proposals of that kind.
        """
        total = int(state["total"])
        cls = str(payload.get("proposal_class"))
        direction = str(payload.get("direction"))
        signature = str(payload.get("design_signature"))

        max_total = int(self.policy["max_total_proposals"])
        if total > max_total:
            return False, schema.RC_BUDGET_EXHAUSTED, \
                f"total {total} exceeds max_total {max_total}"

        max_dir = int(self.policy["max_per_direction"])
        if int(state["by_direction"].get(direction, 0)) > max_dir:
            return False, schema.RC_BUDGET_EXHAUSTED, \
                f"direction {direction} exceeds {max_dir}"

        class_budgets = self.policy.get("class_budgets") or {}
        if cls in class_budgets and \
                int(state["by_class"].get(cls, 0)) > int(class_budgets[cls]):
            return False, schema.RC_BUDGET_EXHAUSTED, \
                f"class {cls} budget {class_budgets[cls]} exceeded"

        # Minimum falsification share: steering — while the share is below the
        # floor, only falsification-class proposals may be accepted.
        min_fals = float(self.policy["min_falsification_share"])
        if cls != "falsification" and total >= 1:
            fals_count = int(state["by_class"].get("falsification", 0))
            share = fals_count / total
            if share < min_fals:
                exception = self.policy.get("c5_steering_exception")
                if exception is not None \
                        and self._exception_admits(payload, state, exception):
                    # Owner-authorized narrow exception (C5 Option A,
                    # 2026-10-25): the disclosure is carried into every
                    # admission detail so the ledger records the dip.
                    return True, None, (
                        "within portfolio policy "
                        f"[c5_steering_exception {exception['decision_id']} "
                        f"| authorization {exception['authorization_id']}] "
                        + str(exception["disclosure"]))
                return False, schema.RC_BIAS_QUOTA, (
                    f"accepting {cls} keeps falsification share at "
                    f"{share:.2f} < required {min_fals:.2f}")

        max_repl = float(self.policy["max_replication_share"])
        if cls == "replication" and total >= 1:
            share = int(state["by_class"].get("replication", 0)) / total
            if share > max_repl:
                return False, schema.RC_BIAS_QUOTA, (
                    f"replication share {share:.2f} > cap {max_repl:.2f}")

        max_sig = int(self.policy["max_signature_count"])
        if int(state["by_signature"].get(signature, 0)) > max_sig:
            return False, schema.RC_SIGNATURE_CAP, (
                f"design signature already used {max_sig} times")

        return True, None, "within portfolio policy"

    def _exception_admits(self, payload: Mapping[str, Any],
                          state: Mapping[str, Any],
                          exception: Mapping[str, Any]) -> bool:
        """Closed check for the owner-signed C5 steering exception.

        Post-creation accounting (same contract as the caps above): ``state``
        includes the proposal under review, so limits compare with ``>`` —
        the projected counts are identical at creation and at validation,
        and a re-creation after a failed attempt is refused, honestly.
        """
        if str(payload.get("proposal_class")) \
                != str(exception.get("proposal_class")):
            return False
        signature = str(payload.get("design_signature"))
        signatures = set(exception.get("design_signatures") or ())
        if signature not in signatures:
            return False
        if int(state["by_signature"].get(signature, 0)) \
                > int(exception.get("per_axis_limit", 1)):
            return False
        exception_total = sum(int(state["by_signature"].get(sig, 0))
                              for sig in signatures)
        if exception_total > int(exception.get("total_rows_limit", 5)):
            return False
        return True


def load_policy(policy: Mapping[str, Any] | None) -> dict[str, Any]:
    return merge_policy(policy)
