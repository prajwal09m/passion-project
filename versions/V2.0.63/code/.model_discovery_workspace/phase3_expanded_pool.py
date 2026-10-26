"""Dev-only: measure the expanded predictive candidate pool (no training, no AUC).

Usage: py -3 phase3_expanded_pool.py <code_root> <repo_root> <out.json>

The expanded pool (``search_space.expanded_keys``) is NOT wired into
``generator.py``; this script simulates the pool directly so the expanded
modes can be compared with the generator-based modes on the same measured
history. Each emitted key is assumed executed before the next cycle.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CODE_ROOT, REPO_ROOT, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, CODE_ROOT)

from autonomous_agent import recipe_harness as rh  # noqa: E402
from autonomous_agent.proposal_layer import compiler  # noqa: E402
from autonomous_agent.proposal_layer.primitives import LIBRARY  # noqa: E402
from autonomous_agent.proposal_layer import search_space as ss  # noqa: E402

BASELINE = "BASELINE_RECONSTRUCTED_2026_10"
CYCLES, PER_CYCLE, BUDGET = 40, 3, 64


def history_keys(view_root: Path) -> set:
    """Keys of the adjudicated experiments, from their executed specs (read-only)."""
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


def base_config() -> dict:
    """A config rendered by the production compiler for one legal candidate."""
    for primitive in LIBRARY:
        if not primitive.executable or primitive.harness_min_version != "1.1.0":
            continue
        payload_params = next(iter(_grid(primitive)))
        return compiler._render_config(
            {"research_question_id": "rq", "hypothesis": "h", "baseline_id": BASELINE},
            primitive, dict(payload_params))
    raise RuntimeError("no executable v1.1.0 primitive to render a base config")


def _grid(primitive):
    from autonomous_agent.proposal_layer import generator
    return generator._param_grid(primitive)


def main() -> None:
    measured = history_keys(REPO_ROOT)
    measured_canon = {ss.canonical_key(k) for k in measured}
    base = base_config()

    pool = ss.distinct_evidence(ss.expanded_keys(BASELINE))
    raw = ss.expanded_keys(BASELINE)
    problems = {}
    valid = []
    for key in pool:
        arm_a, arm_b, est_a, _est_b = key[:4]
        p = ss.harness_contract_problems(base, arm_a, arm_b, est_a)
        if p:
            problems[str(key)] = p
        else:
            valid.append(key)

    def status(key):
        return ss.classify(key, measured)[0]

    substantive = [k for k in valid if k[4] == ss.DEFAULT_SEEDS]
    replication = [k for k in valid if k[4] == ss.REPLICATION_SEEDS]
    admissible = [k for k in valid if ss.canonical_key(k) not in measured_canon]

    # Simulated cycle run: 3 per cycle, budget 64, executed before next cycle.
    emitted, cycles, seen = [], 0, set()
    queue = list(admissible)
    stop = "pool_exhausted"
    for cycle in range(CYCLES):
        if len(emitted) >= BUDGET:
            stop = "budget"
            break
        batch = [k for k in queue if ss.canonical_key(k) not in seen][:PER_CYCLE]
        if not batch:
            stop = "no_admissible_candidate"
            break
        cycles = cycle + 1
        for k in batch:
            emitted.append(k)
            seen.add(ss.canonical_key(k))

    atoms_default = set()
    for k in measured:
        if k[4] == ss.DEFAULT_SEEDS:
            atoms_default |= ss.atoms(k)
    new_default_atoms = set()
    for k in substantive:
        new_default_atoms |= ss.atoms(k)
    new_default_atoms -= atoms_default

    result = {
        "raw_expanded_keys": len(raw),
        "distinct_evidence_after_direction_dedup": len(pool),
        "harness_invalid_keys": len(problems),
        "harness_valid_keys": len(valid),
        "substantive_default_seed_keys": len(substantive),
        "replication_seed_keys": len(replication),
        "measured_history_keys": len(measured),
        "measured_canonical_keys": len(measured_canon),
        "admissible_after_history_dedup": len(admissible),
        "status_counts": {s: sum(1 for k in valid if status(k) == s)
                          for s in (ss.MEASURED, ss.REVERSED_DUPLICATE,
                                    ss.RECOMBINATION_ONLY, ss.NEW_EVIDENCE)},
        "default_seed_model_atoms_total": 8,
        "default_seed_model_atoms_measured": len(atoms_default),
        "default_seed_model_atoms_new": len(new_default_atoms),
        "simulated_emitted": len(emitted),
        "simulated_cycles": cycles,
        "simulated_stop": stop,
        "simulated_substantive_emitted": sum(1 for k in emitted if k[4] == ss.DEFAULT_SEEDS),
        "simulated_replication_emitted": sum(1 for k in emitted if k[4] == ss.REPLICATION_SEEDS),
        "harness_problem_samples": dict(list(problems.items())[:3]),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
