"""Campaign 2 Stage 4 — shadow-only capability analysis (NEVER executes).

Builds a DISPOSABLE mirror of the real repository state (allowlisted evidence
sources only; the versions/ trees are reduced to their allowlisted
version.json/evaluation.json files), attaches an ANALYSIS-ONLY campaign
(``max_total_executions: 0``, ``require_human_approval: true``, no approver
=> nothing approves, nothing compiles, nothing executes), and runs 5 bounded
shadow cycles of ``run_proposal_cycle`` (seeds 101..105, fixed clock).

Then it computes the campaign's 17 evaluations over the proposals those
cycles created and prints the JSON result. The mirror lives in a temp
directory outside the real repository; the REAL repository is only ever read.

Usage:
    py -3 -X utf8 -m autonomous_agent.stage4_shadow_analysis before
    py -3 -X utf8 -m autonomous_agent.stage4_shadow_analysis after
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

from autonomous_agent.proposal_layer import (
    bias_governor, cycle, evidence_view, generator, ledger, schema, validator,
)
from autonomous_agent.test_proposal_layer import CAMPAIGN1_ATTEMPTS, FIXED_CLOCK

REPO = Path(__file__).resolve().parent.parent
CAMPAIGN = "campaign-2-stage-4-shadow-analysis"
SEEDS = (101, 102, 103, 104, 105)


def build_mirror() -> tuple[Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="stage4_shadow_"))
    root = tmp / "ws"
    (root / "autonomous_agent/state").mkdir(parents=True)
    shutil.copy2(REPO / "CHAMPION.json", root / "CHAMPION.json")
    shutil.copy2(REPO / "autonomous_agent/proposal_config.json",
                 root / "autonomous_agent/proposal_config.json")
    for item in sorted((REPO / "autonomous_agent/state").iterdir()):
        if item.is_file() and item.name not in ("campaign_config.json",
                                                "campaign_config.sha256"):
            shutil.copy2(item, root / "autonomous_agent/state" / item.name)
    for version_dir in sorted((REPO / "versions").iterdir()):
        if not version_dir.is_dir():
            continue
        target = root / "versions" / version_dir.name
        target.mkdir(parents=True, exist_ok=True)
        for name in ("version.json", "evaluation.json"):
            source = version_dir / name
            if source.is_file():
                shutil.copy2(source, target / name)
    protocol = root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"
    protocol.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",
                 protocol)
    table = root / "study_files/outputs/study_v1/development/event_table.csv"
    table.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        REPO / "study_files/outputs/study_v1/development/event_table.csv", table)
    audit_rel = (Path("autonomous_agent/MAIN AUDITS AND REFLECTIONS") /
                 "AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md")
    (root / audit_rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / audit_rel, root / audit_rel)
    # Analysis-only campaign: zero execution budget, human approval required,
    # no approver passed to run_proposal_cycle => nothing approves/compiles.
    config = {
        "schema_version": 1,
        "campaign_id": CAMPAIGN,
        "stage_id": "stage-4-shadow",
        "execution": {"max_total_executions": 0},
        "approval": {"approver": "policy:stage4-shadow"},
        "policy_overrides": {
            "campaign_id": CAMPAIGN,
            "max_total_proposals": 40,
            "max_per_direction": 8,
            "max_signature_count": 2,
            "min_falsification_share": 0.35,
            "max_replication_share": 0.5,
            "class_budgets": {"confirmatory": 12, "falsification": 12,
                              "replication": 4, "exploration": 4},
            "max_proposals_per_cycle": 3,
            "require_human_approval": True,
        },
        "seed_base": 20261004,
        "immutable": True,
    }
    path = root / "autonomous_agent/state/campaign_config.json"
    path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")
    (root / "autonomous_agent/state/campaign_config.sha256").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest() + "\n", encoding="utf-8")
    return root, tmp


def run_shadow(root: Path) -> list[dict]:
    summaries = []
    for seed in SEEDS:
        summaries.append(cycle.run_proposal_cycle(root, seed=seed,
                                                  clock=FIXED_CLOCK))
    return summaries


def compute_stats(root: Path, summaries: list[dict]) -> dict:
    ledger_path = root / "autonomous_agent/state/proposal_ledger.jsonl"
    proposal_ledger = ledger.ProposalLedger(ledger_path, clock=FIXED_CLOCK)
    rows = proposal_ledger.read_rows(strict=True)
    created = [pid for s in summaries for pid in s["created"]]
    awaiting = [pid for s in summaries for pid in s.get("awaiting_approval", [])]
    refused = [pid for s in summaries for pid in s.get("refused", [])]
    failed_validation = [pid for s in summaries
                         for pid in s.get("failed_validation", [])]
    compiled = [pid for s in summaries for pid in s.get("compiled", [])]
    payloads = {}
    for pid in created + awaiting + refused + failed_validation:
        merged = proposal_ledger.get(pid)
        if merged:
            payloads[pid] = merged["proposal"]
    status_hist: dict[str, int] = {}
    reason_hist: dict[str, int] = {}
    classes: dict[str, int] = {}
    directions: dict[str, int] = {}
    primitives: dict[str, int] = {}
    param_combos: set[str] = set()
    fingerprints: set[str] = set()
    signatures: set[str] = set()
    null_capable = 0
    falsification_count = 0
    free_code = 0
    holdout_refs = 0
    for pid, payload in payloads.items():
        status = proposal_ledger.status(pid)
        status_hist[status] = status_hist.get(status, 0) + 1
        for transition in proposal_ledger.transitions_of(pid):
            if transition.get("to") in ("REFUSED", "FAILED_VALIDATION"):
                code = transition.get("reason_code")
                reason_hist[code] = reason_hist.get(code, 0) + 1
        cls = payload["proposal_class"]
        classes[cls] = classes.get(cls, 0) + 1
        directions[payload["direction"]] = \
            directions.get(payload["direction"], 0) + 1
        entry = (payload.get("design") or {}).get("primitives", [{}])[0]
        primitive_id = entry.get("primitive_id")
        primitives[primitive_id] = primitives.get(primitive_id, 0) + 1
        param_combos.add(json.dumps(entry.get("params"), sort_keys=True))
        fingerprints.add(payload["proposal_fingerprint"])
        signatures.add(payload["design_signature"])
        rule = payload.get("falsification_rule") or {}
        if rule.get("comparator") == "<" \
                and rule.get("metric") in schema.FALSIFICATION_METRICS:
            null_capable += 1
        if cls == "falsification":
            falsification_count += 1
        blob = json.dumps({"design": payload.get("design"),
                           "parameters": payload.get("parameters")})
        if schema.looks_like_code(blob) or schema.looks_like_path(blob):
            free_code += 1
        if "/prospective/" in json.dumps(payload):
            holdout_refs += 1
    total = len(payloads)
    prior = [row for row in rows
             if row.get("row_type") == "proposal"
             and row.get("proposal_id") not in payloads]
    prior_status: dict[str, int] = {}
    for row in prior:
        status = proposal_ledger.status(row["proposal_id"])
        prior_status[status] = prior_status.get(status, 0) + 1
    # Campaign 1 replay probe (duplicate memory is global and permanent).
    view = evidence_view.build(root, clock=FIXED_CLOCK,
                               ledger_rows=proposal_ledger.read_rows())
    policy = cycle._load_policy(root)
    mapping = {"feature_arm_nested_ablation": "feature_arm_comparison",
               "model_class_matched_comparison": "model_class_comparison",
               "calibration_stability_check": "calibration_stability_check"}
    duplicate_refused = 0
    for attempt in CAMPAIGN1_ATTEMPTS:
        payload = generator.payload_for(
            view, mapping[attempt["recipe_id"]],
            attempt["selected_parameters"], "replication")
        report = validator.validate_proposal(
            payload, root=root, view=view,
            merged_history=proposal_ledger.all_proposals(),
            policy=policy, proposal_id="none")
        if not report.passed and report.reason_code == schema.RC_DUPLICATE:
            duplicate_refused += 1
    # Outcome-blindness probe.
    governor = bias_governor.BiasGovernor(policy)
    candidate = {"direction": "validation", "proposal_class": "falsification",
                 "novelty_score": 0.7, "evidence_gap_score": 0.5,
                 "quota_pressure": 1.0, "priority": 0.9,
                 "attempts_in_direction": 2}
    perturbed = dict(candidate)
    perturbed["predicted_delta"] = 0.42
    score_equal = governor.score(candidate) == governor.score(perturbed)
    inputs_closed = set(governor.selection_inputs(candidate)) == \
        set(bias_governor.SELECTION_INPUT_FIELDS)
    # Quota probes.
    over_state = {"total": 41,
                  "by_class": {"falsification": 20, "confirmatory": 20,
                               "replication": 1, "exploration": 0},
                  "by_direction": {"validation": 9},
                  "by_signature": {"sig": 3}}
    probes = {
        "over_total": not governor.check_accept(
            {"proposal_class": "falsification", "direction": "validation",
             "design_signature": "sig"}, over_state)[0],
        "over_direction": not governor.check_accept(
            {"proposal_class": "falsification", "direction": "validation",
             "design_signature": "sig2"}, over_state)[0],
        "over_signature": not governor.check_accept(
            {"proposal_class": "falsification", "direction": "calibration",
             "design_signature": "sig"}, over_state)[0],
        "below_falsification_floor": not governor.check_accept(
            {"proposal_class": "confirmatory", "direction": "calibration",
             "design_signature": "s2"},
            {"total": 1, "by_class": {"confirmatory": 1},
             "by_direction": {"calibration": 1},
             "by_signature": {"s2": 1}})[0],
    }
    # Holdout injection probe.
    holdout_payload = generator.payload_for(
        view, "feature_arm_comparison",
        {"arm_pair": "C->D", "estimator": "LogisticRegression", "n_boot": 500},
        "falsification")
    holdout_payload["hypothesis"] = (
        "probe study_files/outputs/study_v1/prospective/secret.csv")
    holdout_payload["proposal_fingerprint"] = schema.proposal_fingerprint(
        holdout_payload)
    holdout_report = validator.validate_proposal(
        holdout_payload, root=root, view=view,
        merged_history=proposal_ledger.all_proposals(),
        policy=policy, proposal_id="none")
    scheduler = generator.scheduler_report(view, policy)
    return {
        "created": total,
        "awaiting_approval": len(awaiting),
        "refused": len(refused),
        "failed_validation": len(failed_validation),
        "compiled": len(compiled),
        "status_histogram": status_hist,
        "refusal_reasons": reason_hist,
        "falsification_share": (round(falsification_count / total, 4)
                                if total else 0.0),
        "replication_share": (round(classes.get("replication", 0) / total, 4)
                              if total else 0.0),
        "class_mix": classes,
        "distinct_fingerprints": len(fingerprints),
        "distinct_signatures": len(signatures),
        "exact_duplicates_in_run": total - len(fingerprints),
        "near_duplicate_refusals": reason_hist.get("NEAR_DUPLICATE", 0),
        "duplicate_refusals": reason_hist.get("DUPLICATE", 0),
        "prior_proposals": len(prior),
        "prior_status": prior_status,
        "c1_replay_refused_duplicate": f"{duplicate_refused}/8",
        "holdout_refs_in_payloads": holdout_refs,
        "holdout_injection_gate": [holdout_report.failed_gate,
                                   holdout_report.reason_code],
        "free_code_payloads": free_code,
        "validation_bypass": (
            "all_created_in_validating_or_refused"
            if set(status_hist) <= {"VALIDATING", "REFUSED",
                                    "FAILED_VALIDATION"}
            else f"UNEXPECTED {status_hist}"),
        "outcome_blind_score_equal": score_equal,
        "selection_inputs_closed": inputs_closed,
        "quota_probes_refused": probes,
        "primitives_reached": primitives,
        "directions_reached": directions,
        "distinct_param_combos": len(param_combos),
        "null_adverse_capable": f"{null_capable}/{total}",
        "scheduler": {key: scheduler.get(key) for key in
                      ("candidates_remaining", "excluded_recipe_signatures",
                       "excluded_asked_signatures", "excluded_signature_cap",
                       "excluded_exhausted_directions", "exhausted")},
        "per_cycle_created": [len(s["created"]) for s in summaries],
    }


def main(argv: list[str]) -> int:
    tag = argv[1] if len(argv) > 1 else "run"
    root, tmp = build_mirror()
    initial_rows = len(
        (root / "autonomous_agent/state/proposal_ledger.jsonl")
        .read_text("utf-8").splitlines())
    summaries = run_shadow(root)
    stats = compute_stats(root, summaries)
    stats["tag"] = tag
    stats["mirror"] = str(tmp)
    stats["initial_ledger_rows"] = initial_rows
    stats["executable_primitives"] = sorted(
        primitive.primitive_id
        for primitive in __import__(
            "autonomous_agent.proposal_layer.primitives", fromlist=["LIBRARY"]
        ).LIBRARY if primitive.executable)
    output = tmp / f"stats_{tag}.json"
    output.write_text(json.dumps(stats, indent=1, sort_keys=True),
                      encoding="utf-8")
    print(json.dumps(stats, indent=1, sort_keys=True))
    print(f"stats written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
