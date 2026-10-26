"""Validate the proposed measurement key against measured outcomes (read-only).

Measurement key = the config fields that determine the measured per-seed AUCs:
arm_a, arm_b, estimator_a, estimator_b, seeds, folds, baseline_id.
Excluded (they affect only the decision, not the measured AUC):
n_boot (bootstrap CI), evaluation_criteria (thresholds), hypothesis text.

The check: partition the 69 adjudicated experiments by (a) measured AUC pairs
and (b) the measurement key. If the key is a faithful identity of the measured
evidence, the two partitions are identical (same number of groups, same members).
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evidence_redundancy_audit import CANDIDATES, STATE, measured_outcome, spec_config  # noqa: E402

KEY_FIELDS = ("arm_a", "arm_b", "estimator_a", "estimator_b", "seeds", "folds", "baseline_id")


def measurement_key(cfg: dict) -> tuple:
    return tuple(json.dumps(cfg.get(f), sort_keys=True) for f in KEY_FIELDS)


def main() -> None:
    rows = [json.loads(line) for line in (STATE / "proposal_ledger.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()]
    adjudicated = [r for r in rows if r["row_type"] == "transition" and r["to"] == "ADJUDICATED"]
    by_outcome: dict[tuple, set] = collections.defaultdict(set)
    by_key: dict[tuple, set] = collections.defaultdict(set)
    key_fields_seen = collections.Counter()
    for row in adjudicated:
        exp_id = str(row["detail"].get("experiment_id"))
        spec = json.loads((CANDIDATES / exp_id / "spec.json").read_text(encoding="utf-8"))
        result = json.loads((CANDIDATES / exp_id / "result.json").read_text(encoding="utf-8"))
        cfg = spec_config(spec)
        by_outcome[measured_outcome(result)].add(exp_id)
        by_key[measurement_key(cfg)].add(exp_id)
        for f in KEY_FIELDS:
            if f not in cfg:
                key_fields_seen[f"missing:{f}"] += 1
    outcome_partition = {frozenset(v) for v in by_outcome.values()}
    key_partition = {frozenset(v) for v in by_key.values()}
    report = {
        "experiments": len(adjudicated),
        "measured_outcome_groups": len(by_outcome),
        "measurement_key_groups": len(by_key),
        "partitions_identical": outcome_partition == key_partition,
        "missing_key_fields": dict(key_fields_seen),
        "key_groups_not_matching_outcome": [
            sorted(g) for g in key_partition if g not in outcome_partition][:5],
        "outcome_groups_not_matching_key": [
            sorted(g) for g in outcome_partition if g not in key_partition][:5],
    }
    print(json.dumps(report, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
