"""Dev-only chronological replay of group-weighted outcome ranking.

Read-only on adjudicated ledger/spec rows; no training, candidate execution,
or market AUC. Each prediction is made strictly before its outcome. Run from
workspace root: py -3 phase3_temporal_ranker.py <repo_root> <out.json>
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path

_repo = Path(sys.argv[1]).resolve()
REPO = _repo.parent if _repo.name == ".model_discovery_workspace" else _repo
_arg = Path(sys.argv[2])
OUT = _arg if _arg.is_absolute() else Path(__file__).resolve().parent / _arg
sys.path.insert(0, str(Path(__file__).resolve().parent / "dev"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from autonomous_agent.proposal_layer import outcome_ranking as ork  # noqa: E402


def load_observations(repo: Path):
    ledger = repo / "autonomous_agent/state/proposal_ledger.jsonl"
    rows = [json.loads(line) for line in ledger.read_text("utf-8").splitlines() if line.strip()]
    directions = {}
    for row in rows:
        if row.get("row_type") == "proposal":
            p = row.get("proposal") if isinstance(row.get("proposal"), dict) else row
            directions[str(row.get("proposal_id"))] = str(
                p.get("direction") or (p.get("payload") or {}).get("direction") or "unknown")
    observations = []
    for row in rows:
        if row.get("row_type") != "transition" or row.get("to") != "ADJUDICATED":
            continue
        detail = row["detail"]
        spec = json.loads((repo / "autonomous_agent/candidates" /
                           str(detail["experiment_id"]) / "spec.json").read_text("utf-8"))
        config = {}
        for item in spec.get("proposed_change", {}).get("files", []):
            if str(item.get("path", "")).endswith("experiment_config.json"):
                config = json.loads(item["content"])
        group = "|".join(str(config.get(k)) for k in
                         ("arm_a", "arm_b", "estimator_a", "estimator_b",
                          "seeds", "folds", "baseline_id"))
        observations.append(ork.Observation(
            at=str(row["at"]), direction=directions.get(str(row["proposal_id"]), "unknown"),
            proposal_class="adjudicated", primitive_id=group,
            passed=bool(detail["decision_criteria_passed"])))
    return sorted(observations, key=lambda o: (o.at, o.primitive_id))


def _base(history):
    return (sum(o.passed for o in history) + 1.0) / (len(history) + 2.0)


def _metrics(rows, label):
    if not rows:
        return {"label": label, "n": 0, "groups": 0}
    y = [r["passed"] for r in rows]
    out = {"label": label, "n": len(rows), "n_pass": sum(y),
           "groups": len({r["group"] for r in rows}),
           "unique_unseen_groups": len({r["group"] for r in rows if r.get("unseen", False)}),
           "methods": {}}
    for name in ("base_rate", "group_mean", "last_group", "outcome_aware", "random_probability"):
        p = [r[name] for r in rows]
        brier = sum((x - int(t)) ** 2 for x, t in zip(p, y)) / len(y)
        positive = [x for x, t in zip(p, y) if t]
        negative = [x for x, t in zip(p, y) if not t]
        auc = (sum(1.0 if a > b else .5 if a == b else 0.0
                   for a in positive for b in negative) / (len(positive)*len(negative))
               if positive and negative else None)
        out["methods"][name] = {"brier": round(brier, 6), "auc": auc}
    return out


def replay(observations):
    rng = random.Random(20261017)
    rows = []
    for target in observations:
        history = ork.known_before(observations, target.at)
        if not history:
            continue
        estimate = ork.estimate(history, cutoff=target.at, direction=target.direction,
                                primitive_id=target.primitive_id)
        same = [o for o in history if o.primitive_id == target.primitive_id]
        group_mean = ((sum(o.passed for o in same) + 1) / (len(same) + 2)
                      if same else _base(history))
        last = (float(same[-1].passed) if same else _base(history))
        rows.append({"at": target.at, "group": target.primitive_id,
                     "direction": target.direction, "passed": target.passed,
                     "unseen": not bool(same), "n_history": len(history),
                     "base_rate": _base(history), "group_mean": group_mean,
                     "last_group": last, "outcome_aware": estimate.mean,
                     "random_probability": rng.random()})
    return rows


def cluster_bootstrap_delta(rows, *, reps=2000, seed=0):
    """Paired Brier delta bootstrap resampling measurement groups."""
    groups = sorted({(row["direction"], row["group"]) for row in rows})
    rng = random.Random(seed)
    deltas = []
    for _ in range(reps):
        draw = [rng.choice(groups) for _ in groups]
        sample = [row for group in draw for row in rows
                  if (row["direction"], row["group"]) == group]
        if not sample:
            continue
        y = [row["passed"] for row in sample]
        a = [row["outcome_aware"] for row in sample]
        b = [row["base_rate"] for row in sample]
        deltas.append(sum((x-int(t))**2-(z-int(t))**2
                          for x,z,t in zip(a,b,y))/len(y))
    deltas.sort()
    if not deltas:
        return None
    return [deltas[int(.025*len(deltas))], deltas[min(len(deltas)-1, int(.975*len(deltas))-1)]]


def first_occurrence_rows(observations):
    seen = set()
    out = []
    for target in observations:
        group = (target.direction, target.primitive_id)
        if group in seen:
            continue
        seen.add(group)
        history = ork.known_before(observations, target.at)
        if not history:
            continue
        estimate = ork.estimate(history, cutoff=target.at, direction=target.direction,
                                primitive_id=target.primitive_id)
        base = _base(history)
        out.append({"at": target.at, "group": target.primitive_id,
                    "direction": target.direction, "passed": target.passed,
                    "unseen": True, "outcome_aware": estimate.mean,
                    "base_rate": base, "group_mean": base,
                    "last_group": base, "random_probability": 0.5})
    return out


def main():
    obs = load_observations(REPO)
    rows = replay(obs)
    first_groups = first_occurrence_rows(obs)
    first_metric = _metrics(first_groups, "first_measurement_per_group")
    first_metric["outcome_aware_minus_base_cluster_bootstrap_95ci"] = cluster_bootstrap_delta(
        first_groups)
    rows_metric = _metrics(rows, "all_as_of_rows")
    unseen = [r for r in rows if r["unseen"]]
    repeat = [r for r in rows if not r["unseen"]]
    cut = len(obs) // 2
    flipped = [ork.Observation(o.at, o.direction, o.proposal_class, o.primitive_id,
                               not o.passed if i >= cut else o.passed)
               for i, o in enumerate(obs)]
    future_stable = replay(flipped)
    prefix = [r for r in rows if r["at"] < obs[cut].at]
    prefix_changed = [r for r in future_stable if r["at"] < obs[cut].at]
    result = {
        "ranker_revision": "group_weighted-v2; one beta trial per (direction, measurement key)",
        "n_adjudicated": len(obs), "n_scored": len(rows),
        "groups": len({o.primitive_id for o in obs}),
        "directions": len({o.direction for o in obs}),
        "pass_rate": sum(o.passed for o in obs) / len(obs),
        "measured_at_range": [obs[0].at, obs[-1].at],
        "chronological_period_counts": {p: sum(o.at[:7] == p for o in obs)
                                        for p in sorted({o.at[:7] for o in obs})},
        "splits": [rows_metric, first_metric,
                   _metrics(unseen, "first_occurrence_rows_with_prior"),
                   _metrics(repeat, "repeat_group_rows")],
        "leakage": {"future_flip_prefix_unchanged": len(prefix) == len(prefix_changed)
                    and all(all(abs(a[k]-b[k]) < 1e-12 for k in
                                ("base_rate", "group_mean", "last_group", "outcome_aware",
                                 "random_probability")) for a,b in zip(prefix,prefix_changed)),
                    "future_flip_prefix_rows": len(prefix)},
        "uncertainty_note": "Small single-month history; outcome-aware first-seen group performance uses paired cluster bootstrap by (direction,measurement key). Other row-wise summaries are descriptive; no ranker is promoted.",
    }
    try:
        ork.estimate(obs, cutoff=obs[0].at, direction=obs[0].direction,
                     primitive_id=obs[0].primitive_id)
        result["leakage"]["direct_future_input_refused"] = False
    except ork.LeakageError:
        result["leakage"]["direct_future_input_refused"] = True
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
