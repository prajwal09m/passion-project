"""Dev-only as-of replay of experiment-selection policies (no training, no AUC).

Usage: py -3 phase3_selector_replay.py <repo_root> <out.json>

At each adjudicated experiment i (time order), the candidate pool is the set of
measurement groups with an observation strictly before obs[i].at. Each policy
picks one group from that pool using only that history:

  ledger_actual   the group the ledger really proposed (legacy behaviour)
  exploit         highest outcome-aware posterior mean
  uncertainty     highest outcome-aware posterior SD (where evidence is thin)
  dedup_only      only groups with NO prior evidence are admissible; the pool
                  of never-measured groups is empty here, so this stalls

Reported per policy: admissible steps, picks, repeat picks (group already
measured), distinct groups covered, and mean posterior SD at pick time.
These measure diversity, redundancy, and uncertainty. They say nothing about
predictive value, which is not measured here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO, OUT = Path(sys.argv[1]), Path(sys.argv[2])
WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
sys.path.insert(0, str(WS / "dev"))

from autonomous_agent.proposal_layer import outcome_ranking as ork  # noqa: E402
from phase3_temporal_ranker import load_observations  # noqa: E402


def pick(policy, obs, i, groups, direction):
    history = ork.known_before(obs, obs[i].at)
    ests = {g: ork.estimate(history, cutoff=obs[i].at, direction=direction, primitive_id=g)
            for g in groups}
    if policy == "exploit":
        g = max(sorted(groups), key=lambda g: ests[g].mean)
    elif policy == "uncertainty":
        g = max(sorted(groups), key=lambda g: ests[g].sd)
    else:
        raise ValueError(policy)
    return g, ests[g].sd


def replay(obs):
    stats = {p: {"admissible_steps": 0, "picks": 0, "repeat_picks": 0,
                 "groups": set(), "sd_at_pick": []}
             for p in ("ledger_actual", "exploit", "uncertainty", "dedup_only")}
    for i in range(1, len(obs)):
        history = ork.known_before(obs, obs[i].at)
        groups = sorted({o.primitive_id for o in history})
        actual = obs[i].primitive_id
        # ledger_actual: the real pick; it is a repeat if the group was seen earlier.
        s = stats["ledger_actual"]
        s["admissible_steps"] += 1
        s["picks"] += 1
        s["repeat_picks"] += actual in groups
        s["groups"].add(actual)
        if not groups:
            continue
        for name in ("exploit", "uncertainty"):
            g, sd = pick(name, obs, i, groups, obs[i].direction)
            s = stats[name]
            s["admissible_steps"] += 1
            s["picks"] += 1
            s["repeat_picks"] += 1  # pool contains only already-measured groups
            s["groups"].add(g)
            s["sd_at_pick"].append(sd)
        # dedup_only: admissible only for never-measured groups, which this pool lacks.
        stats["dedup_only"]["admissible_steps"] += 0
    out = {}
    for name, s in stats.items():
        sds = s["sd_at_pick"]
        out[name] = {
            "admissible_steps": s["admissible_steps"],
            "picks": s["picks"],
            "repeat_picks": s["repeat_picks"],
            "repeat_rate": round(s["repeat_picks"] / s["picks"], 4) if s["picks"] else None,
            "distinct_groups_covered": len(s["groups"]),
            "mean_sd_at_pick": round(sum(sds) / len(sds), 6) if sds else None,
        }
    return out


def main():
    obs = load_observations(REPO)
    total_groups = len({o.primitive_id for o in obs})
    result = {
        "n_adjudicated": len(obs),
        "groups_in_ledger": total_groups,
        "policies": replay(obs),
        "note": ("Pool = groups measured before each cutoff. Repeat rate is structural "
                 "for exploit/uncertainty because the pool holds only measured groups. "
                 "dedup_only has no admissible never-measured group, so it stalls. "
                 "The bottleneck is the candidate universe, not the selection rule."),
    }
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
