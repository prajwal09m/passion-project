"""Read-only redundancy audit of the autonomous engine's historical evidence.

For every adjudicated experiment it reads (never writes):
  * the ledger proposal (parameters, direction, class),
  * the executed spec.json (the effective model/evaluation configuration),
  * result.json per-seed AUC metrics (the measured evidence).

It measures:
  1. how many distinct measured outcomes the 69 adjudications contain,
  2. which proposal parameters ever change the measured AUC,
  3. the effective (non-parameter) configuration of each experiment.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
STATE = ROOT / "autonomous_agent/state"
CANDIDATES = ROOT / "autonomous_agent/candidates"


def spec_config(spec: dict) -> dict:
    for item in spec.get("proposed_change", {}).get("files", []):
        if str(item.get("path", "")).endswith("experiment_config.json"):
            return json.loads(item["content"])
    return {}


def measured_outcome(result: dict) -> tuple:
    per_seed = (result.get("metrics") or {}).get("per_seed_metrics") or {}
    pairs = tuple(sorted(
        (seed, round(float(m["auc_a"]), 9), round(float(m["auc_b"]), 9))
        for seed, m in per_seed.items()))
    return pairs


def main() -> None:
    rows = [json.loads(line) for line in (STATE / "proposal_ledger.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()]
    proposals = {r["proposal_id"]: r["proposal"] for r in rows if r["row_type"] == "proposal"}
    adjudicated = [r for r in rows if r["row_type"] == "transition" and r["to"] == "ADJUDICATED"]

    records = []
    for row in adjudicated:
        pid = row["proposal_id"]
        proposal = proposals.get(pid, {})
        exp_id = row["detail"].get("experiment_id")
        spec_path = CANDIDATES / str(exp_id) / "spec.json"
        result_path = CANDIDATES / str(exp_id) / "result.json"
        if not spec_path.exists() or not result_path.exists():
            continue
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        cfg = spec_config(spec)
        params = {}
        for primitive in proposal.get("design", {}).get("primitives", []):
            params = dict(primitive.get("params") or {})
        records.append({
            "proposal_id": pid,
            "direction": proposal.get("direction"),
            "class": proposal.get("proposal_class"),
            "primitive": (proposal.get("design", {}).get("primitives") or [{}])[0].get("primitive_id"),
            "params": params,
            "outcome": measured_outcome(result),
            "primary_delta": row["detail"].get("primary_delta"),
            "effective_config": {
                "estimator_a": cfg.get("estimator_a"),
                "estimator_b": cfg.get("estimator_b"),
                "folds": cfg.get("folds"),
                "seeds": (cfg.get("seeds") if "seeds" in cfg else None),
                "n_boot": cfg.get("n_boot"),
                "primary_metric_min_delta": (cfg.get("evaluation_criteria") or {}).get("primary_metric_min_delta"),
            },
        })

    outcomes = collections.Counter(r["outcome"] for r in records)
    summary = {
        "adjudicated_with_evidence": len(records),
        "distinct_measured_outcomes": len(outcomes),
        "largest_group_size": max(outcomes.values()) if outcomes else 0,
        "groups_with_more_than_one_proposal": sum(1 for v in outcomes.values() if v > 1),
        "proposals_in_repeated_groups": sum(v for v in outcomes.values() if v > 1),
    }

    # Which parameters change the measured outcome? For each (primitive, param),
    # count distinct outcomes across its values, holding everything else fixed is
    # not possible here, so we report the within-primitive spread instead.
    by_primitive = collections.defaultdict(list)
    for r in records:
        by_primitive[r["primitive"]].append(r)
    prim_report = {}
    for prim, items in sorted(by_primitive.items()):
        prim_report[prim] = {
            "experiments": len(items),
            "distinct_outcomes": len({i["outcome"] for i in items}),
            "distinct_effective_configs": len({json.dumps(i["effective_config"], sort_keys=True)
                                               for i in items}),
            "distinct_param_settings": len({json.dumps(i["params"], sort_keys=True) for i in items}),
        }

    # Effective configs: do different parameter settings map to one configuration?
    config_groups = collections.defaultdict(set)
    for r in records:
        config_groups[json.dumps(r["effective_config"], sort_keys=True)].add(
            json.dumps(r["params"], sort_keys=True))

    out = {
        "summary": summary,
        "by_primitive": prim_report,
        "effective_configs_seen": len(config_groups),
        "param_settings_per_effective_config": sorted(len(v) for v in config_groups.values()),
        "mean_abs_auc_pair_per_outcome_group": None,
    }
    print(json.dumps(out, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
