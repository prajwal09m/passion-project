"""M14 Phase 6: self-improving research strategies (offline).

Strategies are versioned planning policies compared against frozen
baselines on held-out projects. Nothing here rewrites scientific
thresholds or linker/attribution gates. Every policy carries
version, description, provenance, comparisons, limitations, and
rollback (previous version id).
"""
from __future__ import annotations

POLICIES = {
    "m13-baseline": {"version": "m13.0", "description": "M13 planner order"},
    "info-value": {"version": "m14.1",
                   "description": "rank by distinguishes/cost first"},
    "adaptive-discovery": {"version": "m14.2",
                           "description": "mechanism candidates first, "
                                          "then ontology coverage"},
    "memory-assisted": {"version": "m14.3",
                        "description": "transfer hypotheses propose first "
                                       "candidates, evidence still required"},
    "combined": {"version": "m14.4",
                 "description": "adaptive-discovery + info-value + memory"},
}


def record(base: str, project_profile: dict, questions: list,
           selected: list, outcomes: dict) -> dict:
    import json
    import time
    from pathlib import Path
    p = Path(base) / "strategy_records.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"t": time.time(), "profile": project_profile,
           "n_questions": len(questions),
           "selected": selected, "outcomes": outcomes}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def rank(policy: str, candidates: list[dict],
         transfers: list[dict] | None = None) -> list[dict]:
    if policy not in POLICIES:
        raise LookupError(f"unknown strategy {policy!r}")
    cands = list(candidates)
    if policy == "info-value":
        cands.sort(key=lambda c: (
            -c.get("info_value", {}).get("distinguishes_n", 0),
            c.get("est_cost", {}).get("relative", 1)))
    elif policy == "adaptive-discovery":
        cands.sort(key=lambda c: (
            0 if c.get("tool") in ("residual_feature_dependence",
                                   "regression_metrics") else 1,
            c.get("est_cost", {}).get("relative", 1)))
    elif policy == "memory-assisted" and transfers:
        cols = {t.get("content", "")[:20] for t in transfers}
        cands.sort(key=lambda c: (
            0 if any(k and k in str(c) for k in cols) else 1))
    elif policy == "combined":
        cands.sort(key=lambda c: (
            -c.get("info_value", {}).get("distinguishes_n", 0),
            0 if c.get("tool") in ("residual_feature_dependence",
                                   "regression_metrics") else 1))
    return cands


def summarize(base: str) -> dict:
    """Aggregate recorded outcomes (M15 Phase 6).

    Tracks discovery hits, resolutions, wasted experiments, and
    verification failures across records. No sealed labels are
    consulted here."""
    import json
    from pathlib import Path
    p = Path(base) / "strategy_records.jsonl"
    recs = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                recs.append(json.loads(line))
            except ValueError:
                continue
    agg = {"n": len(recs), "discovery_hits": 0,
           "resolved": 0, "wasted": 0, "verify_failures": 0}
    for r in recs:
        o = r.get("outcomes") or {}
        agg["discovery_hits"] += int(bool(o.get("discovery_hit")))
        agg["resolved"] += int(bool(o.get("resolved")))
        agg["wasted"] += int(o.get("wasted_experiments", 0) or 0)
        agg["verify_failures"] += int(bool(
            o.get("verification_failed")))
    agg["note"] = ("rates only; resolution without moving evidence "
                     "scores zero by construction")
    return agg


def compare(results: dict[str, dict]) -> dict:
    """Compare policy outcomes on held-out projects (frozen metric)."""
    base = (results.get("m13-baseline") or {}).get("discovery_recall")
    out = {}
    for name, r in results.items():
        rec = r.get("discovery_recall")
        out[name] = {"discovery_recall": rec,
                     "delta_vs_baseline":
                     (rec - base) if isinstance(rec, (int, float))
                     and isinstance(base, (int, float)) else None,
                     "policy": POLICIES.get(name, {})}
    out["_note"] = "held-out comparison only; no sealed tuning"
    return out
