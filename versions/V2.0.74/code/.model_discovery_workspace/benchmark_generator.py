"""Offline benchmark of one generator version (no execution, no outcomes).

Usage: py -3 benchmark_generator.py <code_root> <mode: legacy|dedup> <repo_root> <out.json>

* ``code_root`` is the directory whose ``autonomous_agent`` package is tested
  (the repo for ``legacy``, the dev copy for ``dedup``).
* ``repo_root`` supplies the REAL evidence view (read-only).
* Budget: a fresh campaign scope of 64 proposals, 3 per cycle, up to 40 cycles.
  Each emitted proposal is assumed executed before the next cycle, so its
  evidence becomes known. Only the measured-evidence identity is scored; no AUC
  is read or predicted.
* Ground truth for scoring: ``compiler._render_config`` (the production
  renderer), not the mirror used by the candidate code under test.
* ``dedup`` mode additionally feeds measured evidence back into
  ``generate_proposals(..., measured_keys=...)``. ``legacy`` mode cannot see it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CODE_ROOT, MODE, REPO_ROOT, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
sys.path.insert(0, CODE_ROOT)

from autonomous_agent.proposal_layer import compiler, evidence_view, generator  # noqa: E402
from autonomous_agent.proposal_layer.primitives import LIBRARY, get  # noqa: E402

CYCLES, PER_CYCLE, BUDGET = 40, 3, 64
KEY_FIELDS_RENDERED = ("arm_a", "arm_b", "estimator_a", "estimator_b", "seeds", "folds", "baseline_id")


def truth_key(payload: dict):
    """Measured-evidence identity from the PRODUCTION renderer."""
    primitive = get(payload["design"]["primitives"][0]["primitive_id"])
    try:
        cfg = compiler._render_config(
            {"research_question_id": payload.get("research_question_id"),
             "hypothesis": payload.get("hypothesis"),
             "baseline_id": payload.get("baseline_id")},
            primitive, dict(payload["parameters"]))
    except compiler.CompileError:
        return ("uncompilable", payload["proposal_fingerprint"])
    return (cfg["arm_a"], cfg["arm_b"], cfg["estimator_a"], cfg["estimator_b"],
            tuple(cfg["seeds"]), tuple(cfg["folds"]), cfg["baseline_id"])


def history_truth_keys(view_root: Path) -> set:
    """Keys of the 69 adjudicated experiments, from their executed specs."""
    state = view_root / "autonomous_agent/state/proposal_ledger.jsonl"
    cand = view_root / "autonomous_agent/candidates"
    keys = set()
    for line in state.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("row_type") != "transition" or row.get("to") != "ADJUDICATED":
            continue
        spec = json.loads((cand / str(row["detail"]["experiment_id"]) / "spec.json")
                          .read_text(encoding="utf-8"))
        cfg = {}
        for item in spec.get("proposed_change", {}).get("files", []):
            if str(item.get("path", "")).endswith("experiment_config.json"):
                cfg = json.loads(item["content"])
        keys.add((cfg["arm_a"], cfg["arm_b"], cfg["estimator_a"], cfg["estimator_b"],
                  tuple(cfg["seeds"]), tuple(cfg["folds"]), cfg["baseline_id"]))
    return keys


def universe() -> set:
    keys = set()
    for primitive in LIBRARY:
        if not primitive.executable:
            continue
        for params in generator._param_grid(primitive):
            payload = {"research_question_id": "rq", "hypothesis": "h",
                       "baseline_id": "BASELINE_RECONSTRUCTED_2026_10",
                       "design": {"primitives": [{"primitive_id": primitive.primitive_id}]},
                       "parameters": params, "proposal_fingerprint": "x"}
            keys.add(truth_key(payload))
    keys.discard(None)
    return keys


def main() -> None:
    policy = json.loads((REPO_ROOT / "autonomous_agent/proposal_layer/bias_policy.json")
                        .read_text(encoding="utf-8"))
    policy.update({"campaign_id": "bench-fresh-budget-2026-10-17",
                   "max_total_proposals": BUDGET,
                   "max_proposals_per_cycle": PER_CYCLE})
    if MODE == "dedup_amend":
        policy["falsification_floor_vacuous_when_no_novel"] = True  # dev prototype only
        policy["replication_cap_min_portfolio"] = 3                  # dev prototype only
    view = evidence_view.build(REPO_ROOT, clock=lambda: "2026-10-17T00:00:00+00:00")
    measured = history_truth_keys(REPO_ROOT)
    seen_sim: set = set()
    u = universe()
    stats = {"emitted": 0, "redundant_vs_history": 0, "repeat_within_run": 0,
             "novel": 0, "uncompilable": 0, "cycles_run": 0, "stopped": "cycle_limit"}
    first_cycle_fp = []
    for cycle in range(CYCLES):
        if stats["emitted"] >= BUDGET:
            stats["stopped"] = "budget"
            break
        kwargs = {"seed": cycle, "limit": PER_CYCLE}
        if MODE in ("dedup", "dedup_amend"):
            kwargs["measured_keys"] = measured | seen_sim
        payloads = generator.generate_proposals(view, policy, **kwargs)
        stats["cycles_run"] = cycle + 1
        if cycle == 0:
            first_cycle_fp = [p["proposal_fingerprint"] for p in payloads]
        if not payloads:
            stats["stopped"] = "no_admissible_candidate"
            break
        for payload in payloads:
            stats["emitted"] += 1
            key = truth_key(payload)
            if key[0] == "uncompilable":
                stats["uncompilable"] += 1
            elif key in measured:
                stats["redundant_vs_history"] += 1
            elif key in seen_sim:
                stats["repeat_within_run"] += 1
            else:
                stats["novel"] += 1
            if key[0] != "uncompilable":
                seen_sim.add(key)
            # Same bookkeeping the production view uses for duplicate memory.
            view["already_asked"].append({
                "design_signature": payload["design_signature"],
                "fingerprint": payload["proposal_fingerprint"],
                "proposal_class": payload["proposal_class"],
                "direction": payload["direction"],
                "campaign_id": policy["campaign_id"],
            })
    result = {
        "mode": MODE,
        "code_root": CODE_ROOT,
        "budget": BUDGET,
        "per_cycle": PER_CYCLE,
        "measured_history_keys": len(measured),
        "evidence_universe_keys": len(u),
        "evidence_universe_unmeasured": len(u - measured),
        "novel_keys_reached": len(seen_sim - measured),
        "stats": stats,
        "duplicate_rate": round(
            (stats["redundant_vs_history"] + stats["repeat_within_run"]) / stats["emitted"], 4)
        if stats["emitted"] else None,
        "first_cycle_fingerprints": first_cycle_fp,
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "first_cycle_fingerprints"},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
