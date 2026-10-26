#!/usr/bin/env python3
"""SCRATCH — build the Campaign 4 freeze-readiness candidate config (2026-10-13).

Reads the pinned draft (never modified), applies the reconciliation section-6
amendment for the first time in a versioned candidate, and writes:
  - CAMPAIGN_4_CONFIG_CANDIDATE_2026_10_13.json (+ .sha256 sidecar)

Nothing frozen, nothing loaded: the live state/ config stays Campaign 3.
"""
import copy
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from autonomous_agent.proposal_layer import schema  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DRAFT = (ROOT / "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
                "CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json")
OUT = (ROOT / "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
              "CAMPAIGN_4_CONFIG_CANDIDATE_2026_10_13.json")

C3_STOPS = [
    "max_total_executions_reached",
    "portfolio_minimums_met_and_no_admissible_proposal",
    "holdout_or_prospective_access_detected",
    "arbitrary_code_or_executor_bypass_detected",
    "validation_or_approval_bypass_detected",
    "provenance_loss_or_ledger_corruption",
    "budget_inconsistency_or_negative_capacity",
    "duplicate_execution_detected",
    "invalid_lifecycle_transition",
    "repeated_crash_threshold_exceeded",
    "stale_loop_lock",
    "research_proposal_direction_or_class_exhaustion",
    "explicit_STOP_file_present",
    "campaign_config_hash_mismatch",
]
NEW_STOPS = ["point_in_time_contamination_detected",
             "unverifiable_lineage_detected"]


def main() -> None:
    cfg = copy.deepcopy(json.loads(DRAFT.read_text("utf-8")))
    draft_sha = hashlib.sha256(DRAFT.read_bytes()).hexdigest()
    print("draft sha256 (must stay 307e98ab...):", draft_sha[:16])

    cfg.pop("_DRAFT_STATUS", None)
    cfg["_CANDIDATE_STATUS"] = {
        "state": "CANDIDATE_NOT_FROZEN_NOT_LOADED",
        "prepared_at": "2026-10-13",
        "prepared_by": "coding agent (Campaign 4 remediation task, owner-directed)",
        "derived_from": (
            "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
            "CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json (sha256 "
            f"{draft_sha[:16]}..., byte-untouched) + the section-6 amendment "
            "of CAMPAIGN_4_CONFIG_RECONCILIATION_2026_10_12.md, applied here "
            "for the first time in a versioned candidate"),
        "reason": (
            "Freeze-readiness candidate. NOT autonomous_agent/state/"
            "campaign_config.json, never read by the loop, and NOT frozen: "
            "freeze requires the recorded gate-6 approval, then copy to "
            "state/ with a fresh sha-256 pin and fingerprint recompute. The "
            "live loop_state/ledger/config remain Campaign 3 artifacts, "
            "untouched."),
        "stop_count_resolution": (
            "Owner remediation instruction of 2026-10-13 ('reconcile and "
            "declare all 16 required stops') resolves reconciliation finding "
            "A as 14 C3 stops verbatim + the two wired v1.1.0 audit stops = "
            "16. The implementation plan's '15 original' wording is treated "
            "as a documented error, not silently reconciled. The "
            "UNVERIFIABLE stop identifier is the one already wired and "
            "tested: unverifiable_lineage_detected."),
        "fingerprint_method": (
            "protocol_fingerprint = sha256 of schema.canonical_json(config "
            "minus the protocol_fingerprint key). The Campaign 3 value's "
            "generation method is not recorded in the repository; the freeze "
            "step must recompute with whatever method the proposal layer "
            "adopts and this note must be updated then."),
        "activation_requires": [
            "D2 decided (adopt) with the protocol amendment signed",
            "C-3 ratified",
            "Owner confirms the census freeze-time rulings "
            "(expected-column set and Tier-1 float tolerances) -- see the "
            "census candidate manifest",
            "Gate 6 freeze approval recorded",
            "Copied to autonomous_agent/state/campaign_config.json with a "
            "fresh SHA-256 pin written to campaign_config.sha256; pin verified",
            "protocol_fingerprint recomputed by the adopted method and verified",
            "Gate 7 readiness re-verification, then gate 8 launch authorization",
        ],
    }

    cid = "campaign-4-continuous-2026-10-13"
    cfg["campaign_id"] = cid
    cfg["created_at"] = "2026-10-13T00:00:00+00:00"
    cfg["seed_base"] = 20261013
    cfg["approval"]["approver"] = f"policy:{cid}"
    cfg["approval"]["rationale"] = (
        "CANDIDATE prepared 2026-10-13 under the Campaign 4 decision "
        "approvals recorded in "
        "CAMPAIGN_3_POST_CAMPAIGN_AUDIT_AND_CAMPAIGN_4_PROPOSAL_2026_10_09.md "
        "and the owner remediation instruction of 2026-10-13 (harness v1.1.0 "
        "= yes, dual-comparison rule = yes, budget 30/45 = yes). The final "
        "human authorization prompt must restate: new frozen epoch, 30 "
        "executions / 45 proposals. Not an approval by itself.")
    cfg["policy_overrides"]["campaign_id"] = cid

    cfg["stop_conditions"] = C3_STOPS + NEW_STOPS
    cfg["_stop_condition_notes"] = {
        "point_in_time_contamination_detected": (
            "v1.1.0 audit stop: harness primitive point_in_time_data_audit "
            "reporting confirmed contamination halts the campaign for human "
            "data-lineage review. Enforcement: continuous_loop.py "
            "(audit_stop_signal / durable AUDIT_STOP transition + restart "
            "guard); covered by the config-to-code correspondence test."),
        "unverifiable_lineage_detected": (
            "v1.1.0 audit stop: an audit-level lineage verdict of "
            "UNVERIFIABLE halts the campaign fail-closed. Identifier "
            "confirmed by the owner remediation instruction of 2026-10-13 "
            "(it is the already-wired, already-tested name). Enforcement: "
            "continuous_loop.py (recorded_audit_stop)."),
    }

    cfg["multiplicity_policy"] = {
        "_status": "APPLIED_IN_CANDIDATE_2026_10_13_NOT_FROZEN",
        "correction": "holm_step_down",
        "familywise_alpha": 0.05,
        "pooling": "campaign_end_over_complete_family",
        "n_boot": 1000,
        "n_boot_floor": 1000,
        "n_flips": 1000,
        "n_flips_floor": 1000,
        "n_flips_note": (
            "M = the week-level sign-flip count. The recorded feasibility "
            "must include M: the p-value's resolution is 1/(M+1), so a "
            "formal refutation at Holm's first threshold alpha/m is "
            "attainable only while M + 1 >= 20*m. feasibility() now "
            "enforces both counts and treats a missing M as infeasible "
            "(never silently feasible)."),
        "feasibility_rule": (
            "n_boot + 1 >= 20 * m AND n_flips + 1 >= 20 * m for every "
            "declared family; otherwise freeze blocked (fail-closed)"),
        "max_family_size_m": 50,
        "families": {
            "regime": {"primitive": "regime_split_analysis",
                       "members_per_experiment": 2, "member_bound": 24},
            "horizon": {"primitive": "target_horizon_robustness",
                        "members_per_experiment": 3, "member_bound": 36},
            "purge": {"primitive": "purge_sensitivity_probe",
                      "members_per_experiment": 3, "member_bound": 36},
            "complexity": {"primitive": "complexity_reduction_check",
                           "members_per_experiment": 1, "member_bound": 12},
        },
        "pooling_exclusions": ["campaign_1_2_3_tests",
                               "primitives_not_named_above"],
        "missing_member_rule": "C-2_option_A",
        "missing_member_p": 1.0,
        "missing_member_label": "unavailable",
        "missing_member_never_refuted": True,
        "missing_member_effect": (
            "Counting an unavailable member toward m at p=1.0 STRICTENS, "
            "never loosens, the remaining members' Holm thresholds "
            "(corrected wording; the pinned decision sheet's 'thresholds "
            "are unchanged' is wrong -- see "
            "D2_REVIEW_SUPERSESSION_NOTE_2026_10_13.md item 1)."),
        "p_value_method": "UNRESOLVED_H10_FAIL_CLOSED",
        "p_value_note": (
            "Writing Holm machinery into a config does not adopt method "
            "(b). The p-value method stays UNRESOLVED until the owner "
            "records D2; the campaign-end record gate refuses to compute "
            "adjusted p-values until then. Validity, once adopted, is "
            "procedure-level (marginal over the recorded flip draw), never "
            "conditional on the realized flip set (D2 review + Addendum A, "
            "2026-10-13)."),
        "mc_resolution_note": (
            "At M=1000 the minimum representable p is 1/1001; at Holm's "
            "first threshold a member must produce the minimum "
            "representable p to survive for m in 36-50, and borderline "
            "members are resolved with 25-48% probability, always biased "
            "toward non-rejection. Disclosed in the campaign-end record "
            "note."),
        "campaign_end_record_required": True,
        "no_multiplicity_record_outcome": "INCONCLUSIVE",
    }

    fp = schema.sha256_hex(schema.canonical_json(
        {k: v for k, v in cfg.items() if k != "protocol_fingerprint"}))
    cfg["protocol_fingerprint"] = fp

    text = json.dumps(cfg, indent=2, sort_keys=True) + "\n"
    OUT.write_text(text, "utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    OUT.with_suffix(".json.sha256").write_text(
        f"{digest}  {OUT.name}\n", "utf-8")
    print("candidate:", OUT.relative_to(ROOT))
    print("sha256:", digest)
    print("protocol_fingerprint:", fp)
    print("stops:", len(cfg["stop_conditions"]))


if __name__ == "__main__":
    main()
