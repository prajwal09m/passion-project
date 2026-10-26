"""Temporal replay of outcome-aware priors on the REAL adjudication ledger.

For each adjudicated experiment i (in time order) the prior uses ONLY
observations whose ledger time is strictly before experiment i's time.
Groups are the measurement keys (production-renderer identity) and the
direction comes from the evidence view. Scored with Brier against a
base-rate predictor that uses the same earlier observations.

Read-only against the repo. Writes outcome_replay.json next to this file.
"""
import json
import sys
from pathlib import Path

WS = Path(r"C:/Prajwal MIT/Passion/.model_discovery_workspace")
REPO = Path(r"C:/Prajwal MIT/Passion")
DEV = WS / "dev"
sys.path.insert(0, str(DEV))

from autonomous_agent.proposal_layer import evidence_view  # noqa: E402
from autonomous_agent.proposal_layer import outcome_ranking as ork  # noqa: E402

rows = [json.loads(line) for line in
        (REPO / "autonomous_agent/state/proposal_ledger.jsonl").read_text("utf-8").splitlines()]
adj = [r for r in rows if r.get("row_type") == "transition" and r.get("to") == "ADJUDICATED"]

view = evidence_view.build(REPO, clock=lambda: "2026-10-17T00:00:00+00:00")
def _proposal_direction(row: dict):
    payload = row.get("proposal") if isinstance(row.get("proposal"), dict) else row
    return payload.get("direction") or (payload.get("payload") or {}).get("direction")


# Direction comes from the proposal's own ledger row (the evidence view's
# prior_experiments ids do not cover these adjudicated experiments).
direction_by_pid = {str(r["proposal_id"]): str(_proposal_direction(r) or "unknown")
                    for r in rows if r.get("row_type") == "proposal"}


def group_key(experiment_id: str) -> str:
    spec = json.loads((REPO / "autonomous_agent/candidates" / experiment_id / "spec.json")
                      .read_text("utf-8"))
    cfg = {}
    for item in spec.get("proposed_change", {}).get("files", []):
        if str(item.get("path", "")).endswith("experiment_config.json"):
            cfg = json.loads(item["content"])
    return "|".join(str(cfg.get(k)) for k in
                    ("arm_a", "arm_b", "estimator_a", "estimator_b", "seeds", "folds", "baseline_id"))


obs = []
for r in adj:
    d = r["detail"]
    eid = str(d["experiment_id"])
    obs.append(ork.Observation(
        at=str(r["at"]), direction=direction_by_pid.get(str(r["proposal_id"]), "unknown"),
        proposal_class="experiment", primitive_id=group_key(eid),
        passed=bool(d.get("decision_criteria_passed"))))
obs.sort(key=lambda o: o.at)

# Temporal leakage check: an estimate at the first observation's time must
# refuse any observation at or after its cutoff.
leak_refused = False
try:
    ork.estimate(obs, cutoff=obs[0].at, direction=obs[0].direction,
                 primitive_id=obs[0].primitive_id)
except ork.LeakageError:
    leak_refused = True

preds_prior, preds_base, outcomes = [], [], []
for i in range(1, len(obs)):
    cutoff = obs[i].at
    history = ork.known_before(obs, cutoff)
    if not history:
        continue
    est = ork.estimate(history, cutoff=cutoff, direction=obs[i].direction,
                       primitive_id=obs[i].primitive_id)
    base = sum(o.passed for o in history) / len(history)
    preds_prior.append(est.mean)
    preds_base.append(min(max(base, 1e-6), 1 - 1e-6))
    outcomes.append(obs[i].passed)

n = len(outcomes)
result = {
    "n_adjudicated": len(obs),
    "n_scored": n,
    "pass_rate_all": round(sum(o.passed for o in obs) / len(obs), 4),
    "distinct_groups": len({o.primitive_id for o in obs}),
    "distinct_directions": len({o.direction for o in obs}),
    "brier_outcome_aware": round(ork.brier(preds_prior, outcomes), 6) if n else None,
    "brier_base_rate": round(ork.brier(preds_base, outcomes), 6) if n else None,
    "leakage_guard_refuses_future": leak_refused,
    "measured_at_range": [obs[0].at, obs[-1].at],
}
(WS / "outcome_replay.json").write_text(json.dumps(result, indent=2, sort_keys=True), "utf-8")
print(json.dumps(result, indent=2, sort_keys=True))
