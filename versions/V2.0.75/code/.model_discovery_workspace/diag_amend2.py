"""Diagnostic (read-only): amended generator on the REAL measured-key set.

Reuses benchmark_generator's truth_key/history_truth_keys/universe via import.
"""
import json
import sys
from collections import Counter
from pathlib import Path

DEV = Path(r"C:/Prajwal MIT/Passion/.model_discovery_workspace/dev")
REPO = Path(r"C:/Prajwal MIT/Passion")
WS = Path(r"C:/Prajwal MIT/Passion/.model_discovery_workspace")

_saved = sys.argv
sys.argv = [_saved[0], str(DEV), "dedup_amend", str(REPO), str(WS / "_unused_diag.json")]
sys.path.insert(0, str(WS))
import benchmark_generator as bg  # noqa: E402
sys.argv = _saved

from autonomous_agent.proposal_layer import evidence_view, generator  # noqa: E402
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor  # noqa: E402

policy = json.loads((REPO / "autonomous_agent/proposal_layer/bias_policy.json").read_text("utf-8"))
policy.update({"campaign_id": "bench-fresh-budget-2026-10-17",
               "max_total_proposals": 64, "max_proposals_per_cycle": 3})
measured = bg.history_truth_keys(REPO)
view = evidence_view.build(REPO, clock=lambda: "2026-10-17T00:00:00+00:00")
universe = bg.universe()
print("measured history keys:", len(measured), "universe:", len(universe),
      "unmeasured:", len(universe - measured))

# Unfiltered floor-off candidates, classified by their REAL measurement key.
probe_policy = dict(policy, min_falsification_share=0.0)
cands = generator._build_candidates(view, probe_policy, BiasGovernor(probe_policy), measured_keys=None)
novel_by_class = Counter()
novel_by_prim = Counter()
for c in cands:
    payload = generator._make_payload(c, view)
    key = bg.truth_key(payload)
    if key[0] == "uncompilable" or key in measured:
        continue
    novel_by_class[c["proposal_class"]] += 1
    novel_by_prim[c["primitive_id"]] += 1
print("novel candidates by class (floor-off, real keys):", dict(novel_by_class))
print("novel candidates by primitive:", dict(novel_by_prim))

print("helper novel_falsification_available(real measured):",
      generator._novel_falsification_available(view, policy, measured))

amended = dict(policy, falsification_floor_vacuous_when_no_novel=True)
out = generator.generate_proposals(view, amended, seed=0, limit=3, measured_keys=measured)
print("amended cycle-0 emitted:", len(out), [p["proposal_class"] for p in out])
