"""Dev-only helpers shared by the Phase 3 benchmarks (read-only; no execution).

``truth_key`` mirrors ``benchmark_generator.truth_key`` and uses the production
renderer (``compiler._render_config``) as ground truth. ``history_truth_keys``
reads the executed specs of the adjudicated experiments from the evidence view.
"""
from __future__ import annotations

import json
from pathlib import Path

from autonomous_agent.proposal_layer import compiler
from autonomous_agent.proposal_layer.primitives import get


def truth_key(payload: dict):
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
