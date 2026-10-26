"""Atom-level novelty analysis (read-only; no execution, no outcomes read).

An *atom* is one arm's pooled out-of-fold score under one estimator, folds,
seeds and baseline: (arm, estimator, seeds, folds, baseline_id).

The harness computes each side of a comparison from that arm's own features
and estimator only (recipe_harness._run_pooled: score_a depends on
features_a/estimator_a/folds; deterministic fits; seeds only resample rows).
So a pair's AUCs are determined by its two atoms. A candidate whose two atoms
were already measured by earlier experiments adds no new predictive AUC
evidence, even when its measurement key is new.

Usage: python atom_analysis.py <repo_root>
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("C:/Prajwal MIT/Passion")
ARMS = ("A", "B", "C", "D")
ESTS = ("LogisticRegression", "LightGBM")
SEEDS = (42, 43, 44)
FOLDS = (2023, 2024, 2025)


def measured_keys(root: Path) -> set:
    state = root / "autonomous_agent/state/proposal_ledger.jsonl"
    cand = root / "autonomous_agent/candidates"
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


def atoms_of(key: tuple) -> set:
    arm_a, arm_b, est_a, est_b, seeds, folds, baseline = key
    return {(arm_a, est_a, seeds, folds, baseline), (arm_b, est_b, seeds, folds, baseline)}


def canonical_evidence(key: tuple) -> tuple:
    """Direction-free evidence identity: reversed pairs share AUC atoms."""
    arm_a, arm_b, est_a, est_b, seeds, folds, baseline = key
    if (arm_b, est_b) < (arm_a, est_a):
        arm_a, arm_b, est_a, est_b = arm_b, arm_a, est_b, est_a
    return (arm_a, arm_b, est_a, est_b, seeds, folds, baseline)


def main() -> None:
    measured = measured_keys(REPO)
    measured_atoms = set().union(*(atoms_of(k) for k in measured))
    baselines = {k[6] for k in measured}
    baseline = sorted(baselines)[0]
    print(json.dumps({"measured_keys": len(measured),
                      "measured_atoms": len(measured_atoms),
                      "baselines": sorted(baselines)}))
    print("measured atoms (arm, est):",
          sorted((a[0], a[1]) for a in measured_atoms))

    candidates = []
    for x, y in itertools.product(ARMS, ARMS):
        for est in ESTS:
            if x == y:
                key = (x, x, "LogisticRegression", "LightGBM", SEEDS, FOLDS, baseline)
            else:
                key = (x, y, est, est, SEEDS, FOLDS, baseline)
            candidates.append(("pair" if x != y else "arm_only", key))
    # Dedupe keyed candidates.
    seen = {}
    for kind, key in candidates:
        seen.setdefault(key, kind)

    rows = []
    for key, kind in seen.items():
        is_measured = key in measured
        atoms = atoms_of(key)
        new_atoms = atoms - measured_atoms
        rows.append({
            "kind": kind,
            "key": f"{key[0]}->{key[1]} {key[2]}/{key[3]}",
            "measured_key": is_measured,
            "new_atoms": sorted(f"{a[0]}:{a[1]}" for a in new_atoms),
            "reversed_of_measured": canonical_evidence(key) in
                {canonical_evidence(m) for m in measured} and not is_measured,
        })
    rows.sort(key=lambda r: (r["measured_key"], r["key"]))
    for row in rows:
        status = ("MEASURED" if row["measured_key"] else
                  "RECOMBINATION-ONLY (no new atoms)" if not row["new_atoms"] else
                  f"NEW ATOMS {row['new_atoms']}")
        print(f"{row['kind']:8s} {row['key']:45s} {status}"
              + ("  [reverse of measured]" if row["reversed_of_measured"] else ""))


if __name__ == "__main__":
    main()
