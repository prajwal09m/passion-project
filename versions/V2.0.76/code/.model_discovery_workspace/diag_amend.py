"""Diagnostic: why does the amended (floor-vacuous) generator still emit nothing?

Read-only. Reuses the benchmark's real evidence view and measured-key set.
"""
import json
import sys
from collections import Counter
from pathlib import Path

DEV = Path(r"C:/Prajwal MIT/Passion/.model_discovery_workspace/dev")
REPO = Path(r"C:/Prajwal MIT/Passion")
sys.path.insert(0, str(DEV))

from autonomous_agent.proposal_layer import evidence_view, generator  # noqa: E402
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor  # noqa: E402

policy = json.loads((REPO / "autonomous_agent/proposal_layer/bias_policy.json").read_text("utf-8"))
view = evidence_view.build(REPO, clock=lambda: "2026-10-17T00:00:00+00:00")

measured = set()
for c in generator._build_candidates(view, policy, BiasGovernor(policy), measured_keys=None):
    pass  # warm check that the candidate builder runs on the real view

probe_all = generator._build_candidates(view, dict(policy, min_falsification_share=0.0),
                                        BiasGovernor(dict(policy, min_falsification_share=0.0)),
                                        measured_keys=None)
print("candidates with floor ignored, no key filter:", len(probe_all))
print("by class:", dict(Counter(c["proposal_class"] for c in probe_all)))
print("by primitive:", dict(Counter(c["primitive_id"] for c in probe_all)))
print("novel falsification available (helper):",
      generator._novel_falsification_available(view, policy, set()))
print("policy class_budgets:", policy.get("class_budgets"))
print("policy min_falsification_share:", policy.get("min_falsification_share"))
