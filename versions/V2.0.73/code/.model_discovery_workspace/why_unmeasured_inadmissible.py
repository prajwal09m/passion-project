"""Diagnose why the unmeasured evidence keys are not admissible (read-only)."""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
sys.path.insert(0, str(REPO))

from autonomous_agent.proposal_layer import evidence_view, generator, schema  # noqa: E402
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor  # noqa: E402
from autonomous_agent.proposal_layer.primitives import LIBRARY  # noqa: E402
sys.path.insert(0, str(Path(__file__).parent))
_saved_argv = sys.argv
sys.argv = [_saved_argv[0], "", "legacy", str(REPO), str(Path(__file__).parent / "_unused.json")]
import benchmark_generator as bg  # noqa: E402  (module import only; main() not called)
sys.argv = _saved_argv


def main() -> None:
    policy = json.loads((REPO / "autonomous_agent/proposal_layer/bias_policy.json").read_text("utf-8"))
    policy.update({"campaign_id": "bench-fresh-budget-2026-10-17", "max_total_proposals": 64,
                   "max_proposals_per_cycle": 3})
    view = evidence_view.build(REPO, clock=lambda: "2026-10-17T00:00:00+00:00")
    measured = bg.history_truth_keys(REPO)
    governor = BiasGovernor(policy)
    stats: dict = {}
    generator._build_candidates(view, policy, governor, stats=stats)
    print("scheduler stats:", json.dumps({k: v for k, v in stats.items()
                                          if not isinstance(v, list) or v}, default=str))

    asked = {item.get("design_signature") for item in view.get("already_asked", [])}
    recipe_sigs = set()
    for row in view.get("recipe_attempts", []):
        sig = schema.signature_from_recipe_attempt(row.get("recipe_id"), row.get("selected_parameters") or {})
        if sig:
            recipe_sigs.add(sig)
    unmeasured = collections.Counter()
    reasons = collections.defaultdict(list)
    for primitive in LIBRARY:
        if not primitive.executable:
            continue
        for params in generator._param_grid(primitive):
            payload = {"research_question_id": "rq", "hypothesis": "h",
                       "baseline_id": "BASELINE_RECONSTRUCTED_2026_10",
                       "design": {"primitives": [{"primitive_id": primitive.primitive_id}]},
                       "parameters": params, "proposal_fingerprint": "x"}
            key = bg.truth_key(payload)
            if key in measured or key[0] == "uncompilable":
                continue
            sig = schema.design_signature(primitive_ids=(primitive.primitive_id,), params=params)
            why = []
            if sig in recipe_sigs:
                why.append("recipe_signature_excluded")
            if sig in asked:
                why.append("already_asked_signature")
            unmeasured[str(key[:4])] += 1
            reasons[str(key[:4])].append({"primitive": primitive.primitive_id,
                                          "params": params, "why": why or ["admissible?"]})
    print("unmeasured evidence keys (arm_a, arm_b, est_a, est_b) and candidate grid cells:")
    for k, n in unmeasured.items():
        print(" ", k, "cells:", n)
        for item in reasons[k][:4]:
            print("     ", item)


if __name__ == "__main__":
    main()
