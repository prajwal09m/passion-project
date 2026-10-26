"""Dev-only: which measurement keys does dedup+quota emit? (no execution, no AUC)

Usage: py -3 phase3_quota_keys.py <code_root> <repo_root>
"""
import json
import sys
from pathlib import Path

CODE_ROOT, REPO_ROOT = sys.argv[1], Path(sys.argv[2])
sys.path.insert(0, CODE_ROOT)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import benchmark_keys as bk  # noqa: E402
from autonomous_agent.proposal_layer import generator, evidence_view  # noqa: E402
from autonomous_agent.proposal_layer import search_space as ss  # noqa: E402

policy = json.loads((REPO_ROOT / "autonomous_agent/proposal_layer/bias_policy.json")
                    .read_text(encoding="utf-8"))
policy.update({"campaign_id": "bench-fresh-budget-2026-10-17",
               "max_total_proposals": 64, "max_proposals_per_cycle": 3,
               "falsification_floor_vacuous_when_no_novel": True,
               "replication_cap_min_portfolio": 3})
view = evidence_view.build(REPO_ROOT, clock=lambda: "2026-10-17T00:00:00+00:00")
measured = bk.history_truth_keys(REPO_ROOT)
seen = set()
out = []
for cycle in range(40):
    payloads = generator.generate_proposals(view, policy, seed=cycle, limit=3,
                                            measured_keys=measured | seen)
    if not payloads:
        break
    for p in payloads:
        key = bk.truth_key(p)
        seen.add(key)
        seeds = key[4] if len(key) > 4 else None
        out.append({"cycle": cycle, "key": [str(x) for x in key],
                    "class": p.get("proposal_class"), "direction": p.get("direction"),
                    "seed_set": "replication" if tuple(seeds or ()) == ss.REPLICATION_SEEDS
                    else "default",
                    "status": ss.classify(key, measured)[0]})
    for p in payloads:
        view["already_asked"].append({"design_signature": p["design_signature"],
                                      "fingerprint": p["proposal_fingerprint"],
                                      "proposal_class": p["proposal_class"],
                                      "direction": p["direction"],
                                      "campaign_id": policy["campaign_id"]})
print(json.dumps(out, indent=2))
