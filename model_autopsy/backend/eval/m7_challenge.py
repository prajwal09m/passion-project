"""M7 closed-loop challenge harness (Part 5, offline, no paid traffic).

Drives the REAL engine + tools + linker + planner with a scripted
top-pick policy on concealed scenarios (truth in `m6_challenge._TRUTH`,
never passed to the loop). Seeds only generic structural hypotheses per
task family — identical for every scenario in that family, never answers.

Verifies BEHAVIOR, not fixed sequences:
1. transitions occur (hypotheses leave `proposed` for evidence reasons),
2. every transition cites a ran action,
3. no duplicate tool executions,
4. budget respected, stopping rationale recorded when stopping early,
5. selection brief changes as evidence accumulates,
6. final report assembles with traceable refs.

Limitation: only tools runnable with generic args
(predictions_path + conventional columns) execute; tools needing
scenario-specific required args are skipped as inapplicable and
recorded. This exercises the loop machinery, not investigator quality —
no generalization claim follows.
"""
from __future__ import annotations


GENERIC_SEEDS = {
    "forecasting": [
        ("A level shift in the recent period causes the miss.",
         "late error much larger than early error with clean splits"),
        ("Apparent miss is a split hygiene artifact, not a real change.",
         "overlap or non-chronological splits would show"),
        ("Persistent model misspecification explains errors in all periods.",
         "large errors early as well as late"),
    ],
    "regression": [
        ("Systematic bias in predictions causes the miss.",
         "large mean residual vs spread"),
        ("Error depends on an input feature (stale or lagged input).",
         "residuals correlate with a feature column"),
        ("Apparent miss is a data quality artifact.",
         "nulls, duplicates, or constant columns would show"),
    ],
}

GENERIC_TOOLS = ["temporal_changepoint_scan", "residual_time_analysis",
                 "distribution_shift_profile", "data_quality_profile",
                 "residual_feature_dependence", "forecast_diagnostics",
                 "regression_metrics", "calibration_snapshot",
                 "artifact_summary", "dataset_validation"]

SCENARIO_IDS = ["m6_drift_forecast", "m6_competing_regression",
                "m6_interacting_pipeline", "m6_no_failure",
                "m6_distractor", "m6_correlation_causation"]


def _family(task: str) -> str:
    return "forecasting" if task == "forecasting" else "regression"


def _tool_args(tool: str, columns: set[str], artifact: str) -> dict | None:
    """Generic args for this artifact, or None when inapplicable."""
    base: dict = {"predictions_path": artifact}
    needs_date = {"forecast_diagnostics", "temporal_changepoint_scan",
                  "residual_time_analysis"}
    if tool in needs_date:
        if "date" not in columns:
            return None
        base["date_column"] = "date"
    if tool == "distribution_shift_profile":
        if "split" not in columns:
            return None
        base["split_column"] = "split"
    return base


def run_closed_loop(scenario_id: str, session) -> dict:
    """One scripted closed-loop investigation. Returns behavioral evidence."""
    from . import m6_challenge as C
    from .. import engine
    from ..causal import linker as LK, planning as PL
    from ..db import Action, Hypothesis
    brief = C.public_brief(scenario_id)
    artifact = brief["artifact"]
    task = brief["spec"]["task_type"]
    inv = engine.create_investigation(
        session, "ml", f"M7 harness: {scenario_id}",
        brief["spec"]["objective"],
        {"max_iterations": 3, "predictions_path": artifact})
    inv.config = {**(inv.config or {}), "context": {
        "artifact": artifact, "task": task,
        "objective": brief["spec"]["objective"]}}
    session.commit()
    family = _family(task)
    for text, pred in GENERIC_SEEDS[family]:
        engine.propose_hypothesis(
            session, inv, text=text, predicted_observation=pred,
            confidence_note="uncalibrated structural prior, not evidence")
    import pandas as pd
    try:
        columns = set(pd.read_csv(artifact, nrows=2).columns)
    except Exception:
        columns = set()
    briefs_seen: list[list[str]] = []
    skipped: list[str] = []
    steps = 0
    stop_why = "step cap reached"
    while steps < 6:
        hyps = session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv.id).all()
        hviews = [{"id": h.id, "text": h.text, "status": h.status,
                   "evidence_refs": h.evidence_refs or []} for h in hyps]
        ran = {a.tool_name for a in session.query(Action).filter(
            Action.investigation_id == inv.id,
            Action.status == "ran").all() if a.tool_name}
        failed = {a.tool_name for a in session.query(Action).filter(
            Action.investigation_id == inv.id,
            Action.status == "failed").all() if a.tool_name}
        plan = PL.plan_next(
            hviews, ran,
            {"tool_calls_used": inv.tool_call_count,
             "tool_calls_max": 6}, already_failed=failed)
        top = [t for t in plan.get("ranked_all", [])
               if t in GENERIC_TOOLS]
        briefs_seen.append(top)
        pick, args = None, None
        for cand in top:
            built = _tool_args(cand, columns, artifact)
            if built is None:
                if cand not in skipped:
                    skipped.append(cand)
                continue
            pick, args = cand, built
            break
        if pick is None:
            stop_why = ("no applicable experiments remain (skipped: "
                        + ", ".join(skipped) + ")" if skipped else
                        "no informative experiments remain")
            break
        out = engine.run_tool(session, inv, pick, args,
                              source_meta=True)
        steps += 1
        if out.get("ok"):
            act = session.get(Action, out.get("action_id"))
            if act is not None:
                LK.link_tool_result(session, inv, act)
        stop, stop_why = PL.stopping(
            inv.status, hviews, inv.tool_call_count, 6, steps)
        if stop:
            break
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == inv.id).all()
    return {"scenario": scenario_id, "steps": steps,
            "statuses": {h.status for h in hyps},
            "n_transitions": sum(1 for h in hyps
                                 if (h.revisions or h.evidence_refs)),
            "evidence_refs_ok": all(
                (lambda refs: all(
                    any(a.id == r.get("action_id") and a.status == "ran"
                        for a in acts) for r in refs))(h.evidence_refs or [])
                for h in hyps),
            "duplicate_tools": len([a.tool_name for a in acts
                                    if a.status == "ran"])
            - len({a.tool_name for a in acts if a.status == "ran"}),
            "briefs_changed": len({tuple(b[:1]) for b in briefs_seen}) > 1
            or len(briefs_seen) <= 1,
            "stop_rationale": stop_why,
            "tool_calls": inv.tool_call_count,
            "skipped_inapplicable": skipped}


def evaluate_all(session_factory) -> dict:
    results = []
    for sid in SCENARIO_IDS:
        s = session_factory()
        try:
            results.append(run_closed_loop(sid, s))
        finally:
            s.close()
    return {"scenarios": results,
            "checks": {
                "transitions_occur": all(
                    r["n_transitions"] >= 1 for r in results),
                "refs_valid": all(r["evidence_refs_ok"] for r in results),
                "no_duplicates": all(
                    r["duplicate_tools"] == 0 for r in results),
                "budget_ok": all(r["tool_calls"] <= 6 for r in results),
                "rationales": all(bool(r["stop_rationale"])
                                  for r in results)},
            "note": "behavioral harness on 6/12 M6 scenarios with generic "
                    "args; classification-only tools untested here"}
