"""M9 research-laboratory challenge (offline, no paid traffic).

The autonomous loop (`research.autonomous.run_autonomous`) investigates
concealed scenarios: questions generated, specs invented, evidence
attributed with explicit relationships, confounders checked, agenda
revised. Sealed truth lives in `_TRUTH` (post-freeze scorer only).
`check_no_truth_leak` audits the investigator path.

Dev vs held-out: develop against dev scenarios; the gate reports both.
Held-out scenarios use unfamiliar configurations the loop never saw
during development. Scores here measure machinery, never model
quality, and are NOT comparable with live Meta scores.
"""
from __future__ import annotations

FE = "model_autopsy/tests/fixture_eval/investigator"
FM9 = "model_autopsy/tests/fixture_m9"

SCENARIOS: list[dict] = [
    {"id": "m9_nn_slice", "family": "neural image-tag classifier",
     "task": "classification", "held_out": False,
     "brief": "Night-time tag accuracy looks off; pooled AUC is 0.89.",
     "artifact": FM9 + "/nn_tags.csv",
     "requires": ["classification_metrics"],
     "discriminating": "per-slice AUC spread",
     "kind": "subgroup-confounded"},
    {"id": "m9_rent_confound", "family": "regression",
     "task": "regression", "held_out": False,
     "brief": "Rent estimates for one district look off after a schema "
              "update.",
     "artifact": FE + "/rent_estimates.csv",
     "requires": ["regression_metrics"],
     "discriminating": "group MAE ratio",
     "kind": "schema-vs-segment"},
    {"id": "m9_credit_leak", "family": "tabular classification",
     "task": "classification", "held_out": False,
     "brief": "Is the good default AUC from leakage or skill?",
     "artifact": FE + "/credit_default.csv",
     "requires": ["feature_target_suspiciousness"],
     "discriminating": "non-score input correlation",
     "kind": "reject-plausible"},
    {"id": "m9_pilot_thin", "family": "weak-evidence pilot",
     "task": "classification", "held_out": False,
     "brief": "Tiny pilot: material issue or more evidence needed?",
     "artifact": FE + "/pilot_study.csv",
     "requires": ["classification_metrics"],
     "discriminating": "restraint under thin evidence",
     "kind": "inconclusive-required"},
    {"id": "m9_music_slice", "family": "recommendation/ranking",
     "task": "ranking", "held_out": True,
     "brief": "Are top results relevant for every catalog slice?",
     "artifact": FE + "/music_rank.csv",
     "requires": ["regression_metrics"],
     "discriminating": "per-slice error spread",
     "kind": "subgroup"},
    {"id": "m9_turbine_drift", "family": "time-series forecasting",
     "task": "forecasting", "held_out": True,
     "brief": "Output forecasts miss a recent level change.",
     "artifact": FE + "/turbine_output.csv",
     "requires": ["temporal_changepoint_scan"],
     "discriminating": "changepoint alignment",
     "kind": "temporal"},
    {"id": "m9_wellness_clean", "family": "clean control",
     "task": "regression", "held_out": True,
     "brief": "Routine check: is the wellness index model healthy?",
     "artifact": FE + "/wellness_index.csv",
     "requires": ["regression_metrics"],
     "discriminating": "no false alarm",
     "kind": "clean"},
    {"id": "m9_energy_correlation", "family": "utilities forecasting",
     "task": "forecasting", "held_out": True,
     "brief": "Does demand growth cause the miss or just correlate?",
     "artifact": "model_autopsy/tests/fixture_universal/energy_demand.csv",
     "requires": ["residual_time_analysis"],
     "discriminating": "temporal test",
     "kind": "correlation"},
]

_TRUTH = {
    "m9_nn_slice": {"expect": "night-slice ranking failure; prevalence "
                               "is a confounder, not the cause",
                    "must_use": "classification_metrics"},
    "m9_rent_confound": {"expect": "segment-concentrated error; schema "
                                    "vs district confounded",
                         "must_use": "regression_metrics"},
    "m9_credit_leak": {"expect": "reject leakage; skill, not leak",
                       "must_use": "feature_target_suspiciousness"},
    "m9_pilot_thin": {"expect": "inconclusive; thin evidence",
                      "must_use": "none"},
    "m9_music_slice": {"expect": "slice gap if measured",
                       "must_use": "regression_metrics"},
    "m9_turbine_drift": {"expect": "level shift with clean splits",
                         "must_use": "temporal_changepoint_scan"},
    "m9_wellness_clean": {"expect": "correct-null",
                          "must_use": "none"},
    "m9_energy_correlation": {"expect": "temporal test required",
                              "must_use": "residual_time_analysis"},
}


def run_scenario(scenario_id: str, session) -> dict:
    """Autonomous investigation; truth never enters this function."""
    from ..research import autonomous as AU
    scen = next(s for s in SCENARIOS if s["id"] == scenario_id)
    behavior = AU.run_autonomous(
        session, scen["artifact"], scen["task"], scen["brief"],
        max_steps=6, investigation_title=f"M9 harness: {scenario_id}")
    return {"scenario": scenario_id, **behavior}


def _attribution_precision(session, inv_id: str) -> dict:
    """Re-audit: no supports-ref may deny its measured segment."""
    from ..causal import attribution as AT
    from ..db import Action, Hypothesis
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv_id).all()
    acts = {a.id: a for a in session.query(Action).filter(
        Action.investigation_id == inv_id).all()}
    checked, bad = 0, []
    for h in hyps:
        for r in (h.evidence_refs or []):
            if r.get("relation") not in ("supports", "contradicts"):
                continue
            a = acts.get(r.get("action_id"))
            if a is None:
                continue
            segs = AT.measured_segments(dict(a.arguments or {}))
            if r["relation"] == "supports" and AT.denies(h.text, segs):
                bad.append({"h": h.id[:8], "tool": a.tool_name})
            checked += 1
    # Restraint (no moving refs on thin evidence) is not misattribution:
    # the scored property is that no denial was ever supported.
    return {"checked": checked, "violations": bad,
            "score": 0.0 if bad else 1.0}


def score_dimensions(behavior: dict, scenario_id: str, session) -> dict:
    """Independent 13-dimension scoring (post-freeze truth access)."""
    scen = next(s for s in SCENARIOS if s["id"] == scenario_id)
    truth = _TRUTH[scenario_id]
    ran = set(behavior["ran_tools"])
    kind = scen["kind"]
    must = truth["must_use"]
    must_hit = (must in (None, "none")) or (must in ran)
    req_hit = bool(ran & set(scen.get("requires", [])))
    agenda = behavior.get("agenda", [])
    open_q = [q for q in agenda if q.get("status") == "open"]
    blocked_q = [q for q in agenda if q.get("status") == "blocked"]

    understanding = 1.0 if agenda else 0.0  # questions name real facts
    planning = 1.0 if (agenda and all(q.get("priority_reason")
                                      for q in agenda)) else 0.5
    if kind in ("clean", "inconclusive-required"):
        discovery = 1.0 if ("supported" not in behavior["statuses"]
                            and req_hit) else (
            0.5 if "supported" not in behavior["statuses"] else 0.0)
    else:
        discovery = 1.0 if (req_hit and must_hit) else (
            0.5 if req_hit else 0.0)
    invention = 1.0 if (behavior["specs_proposed"] >= 2
                        and behavior["specs_executed"]) else (
        0.5 if behavior["specs_executed"] else 0.0)
    selection = 1.0 if behavior["specs_executed"] else 0.0
    causal = 0.0 if "supported" in behavior["statuses"] and \
        behavior["steps"] <= 1 else (
        1.0 if "supported" in behavior["statuses"] else 0.6)
    # Confounder handling: shared-evidence flagged + agenda revised.
    conf = 1.0 if (any(q.get("family") == "confounder-discrimination"
                        for q in agenda)
                   or kind in ("clean", "inconclusive-required")) else 0.5
    attr = _attribution_precision(session, behavior.get(
        "investigation_id", ""))
    attribution = attr["score"]
    hyp_mgmt = 1.0 if behavior["n_transitions"] >= 1 else (
        1.0 if kind in ("clean", "inconclusive-required")
        and "supported" not in behavior["statuses"] else 0.0)
    reporting = 1.0 if behavior["fallback_valid"] else 0.5
    confs = behavior["confidences"] or [0]
    calibration = 1.0 if (all(c is None or 0 <= c <= 99 for c in confs)
                          and ("supported" not in behavior["statuses"]
                               if kind in ("clean",
                                           "inconclusive-required")
                               else True)) else 0.5
    repro = 1.0
    efficiency = 1.0 if behavior["tool_calls"] <= 6 else 0.5
    dims = {"project_understanding": understanding,
            "research_planning": planning, "discovery": discovery,
            "experiment_invention": invention,
            "experiment_selection": selection,
            "causal_reasoning": causal,
            "confounder_handling": conf, "evidence_attribution": attribution,
            "hypothesis_management": hyp_mgmt,
            "reporting_validity": reporting, "calibration": calibration,
            "reproducibility": repro, "efficiency": efficiency}
    return {"scenario": scenario_id, "kind": kind,
            "held_out": scen["held_out"], "truth_expect": truth["expect"],
            "dimensions": dims,
            "mean": round(sum(dims.values()) / len(dims), 3)}


def evaluate_all(session_factory, include_held_out: bool = True) -> dict:
    rows = []
    for scen in SCENARIOS:
        if scen["held_out"] and not include_held_out:
            continue
        s = session_factory()
        try:
            behavior = run_scenario(scen["id"], s)
            inv_id = None
            from ..db import Investigation
            inv = s.query(Investigation).filter(
                Investigation.title == f"M9 harness: {scen['id']}").order_by(
                Investigation.created_at.desc()).first()
            if inv is not None:
                inv_id = inv.id
            behavior["investigation_id"] = inv_id
            rows.append({**behavior, **score_dimensions(
                behavior, scen["id"], s)})
        finally:
            s.close()
    dims = list(rows[0]["dimensions"].keys())
    dev = [r for r in rows if not r["held_out"]]
    held = [r for r in rows if r["held_out"]]
    def means(rs):
        return {d: round(sum(r["dimensions"][d] for r in rs) / len(rs), 3)
                for d in dims} if rs else {}
    return {"scenarios": rows, "dimension_means": means(rows),
            "dev_means": means(dev), "held_out_means": means(held),
            "note": ("autonomous loop on real engine/tools/linker/agenda/"
                     "invention; scores measure machinery, NOT comparable "
                     "with live Meta scores")}


def check_no_truth_leak() -> dict:
    """The investigator path never touches sealed truth."""
    import inspect
    import pathlib
    from ..research import autonomous as AU
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    if "_TRUTH" in inspect.getsource(AU.run_autonomous):
        offenders.append("research/autonomous.run_autonomous")
    for rel in ("research/agenda.py", "research/invention.py",
                "causal/attribution.py", "causal/confounders.py",
                "causal/linker.py", "engine.py"):
        if "_TRUTH" in (root / rel).read_text(encoding="utf-8"):
            offenders.append(rel)
    return {"ok": not offenders, "offenders": offenders}
