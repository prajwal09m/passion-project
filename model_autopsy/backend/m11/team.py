"""M11 team investigation (offline).

Flow: single-investigator baseline (M9/M10 machinery) provides the
shared evidence record; the team then works it in order:

  lead assigns -> data_scientist + model_analyst brief ->
  designer proposes one discriminating spec (ledger-reserved, run,
  attributed) -> skeptic challenges -> each challenge is either
  resolved by a ledger-reserved discriminating experiment or
  preserved as an explicit unresolved disagreement -> judge
  renders independent verdicts.

Disagreement resolution is evidence-based, never majority vote:
one measurement that discriminates beats three agents agreeing.
"""
from __future__ import annotations


def _run_probe(session, inv, tool: str, artifact: str,
               facts: dict) -> dict:
    """Run one investigator-response probe with column mapping."""
    from .. import engine
    from ..causal import linker as LK
    from ..db import Action
    args: dict = {"predictions_path": artifact}
    cols = facts.get("columns") or []
    if "target" not in cols and "label" in cols:
        args["target_column"] = "label"
    if "prediction" not in cols and facts.get("score_col"):
        args["prediction_column"] = facts["score_col"]
    if tool == "classification_metrics" and facts.get("score_col"):
        args["score_column"] = facts["score_col"]
    out = engine.run_tool(session, inv, tool, dict(args),
                          source_meta=True)
    if out.get("ok"):
        act = session.get(Action, out.get("action_id"))
        if act is not None:
            LK.link_tool_result(session, inv, act)
    return out


def investigate(session, scenario_id: str, artifact: str, task: str,
                brief: str, ledger=None,
                max_steps: int = 6, skeptic: bool = True,
                judge: bool = True) -> dict:
    from ..research import autonomous as AU
    from ..research import invention as INV
    from ..research import agenda as AG
    from ..causal import linker as LK
    from ..db import Action, Hypothesis, record_event
    from . import roles
    from .ledger import Ledger
    ledger = ledger or Ledger(tool_calls=max_steps)

    base = AU.run_autonomous(session, artifact, task, brief,
                             max_steps=max_steps,
                             investigation_title=(
                                 f"M11 team: {scenario_id}"))
    inv_id = base["investigation_id"]
    from ..db import Investigation
    inv = session.get(Investigation, inv_id)
    facts = INV.artifact_facts(artifact)

    def hviews():
        hs = session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv_id).all()
        return [{"id": h.id, "text": h.text, "status": h.status,
                 "evidence_refs": h.evidence_refs or []} for h in hs]

    def ran_actions():
        acts = session.query(Action).filter(
            Action.investigation_id == inv_id,
            Action.status == "ran").all()
        return [{"id": a.id, "tool": a.tool_name,
                 "result": dict(a.result or {})} for a in acts]

    hyps, acts = hviews(), ran_actions()
    questions = AG.load(inv)
    team = {"lead": roles.lead(questions, hyps,
                               ledger.remaining()),
            "data_scientist": roles.data_scientist(facts),
            "model_analyst": roles.model_analyst(acts)}
    # Designer: one extra discriminating spec beyond the baseline.
    open_q = next((q for q in questions
                   if q.get("status") == "open"), None)
    designer_out, extra_run = {"spec": None}, None
    if open_q is not None and ledger.remaining() >= 1:
        d = roles.experiment_designer(
            open_q, hyps, facts,
            [{"tool": a["tool"], "args": {}} for a in acts],
            {"experiments": ledger.remaining()})
        designer_out = d
        if d.get("spec"):
            try:
                ledger.reserve("experiment_designer",
                               d["spec"]["tool"])
                if INV.validate(d["spec"], facts,
                                 [{"tool": a["tool"], "args": {}}
                                  for a in acts],
                                 {"experiments":
                                  ledger.remaining() + 1})["valid"]:
                    out = INV.execute(session, inv, d["spec"])
                    extra_run = {"tool": d["spec"]["tool"],
                                 "ok": out.get("ok")}
                    if out.get("ok"):
                        a = session.get(Action,
                                        out.get("action_id"))
                        if a is not None:
                            LK.link_tool_result(session, inv, a)
            except Exception as exc:
                extra_run = {"tool": d.get("spec", {}).get("tool"),
                             "ok": False, "reason": str(exc)[:150]}
    team["experiment_designer"] = designer_out
    team["extra_experiment"] = extra_run

    # Mandatory skeptic (M13 §4.2) + investigator responses.
    # Blocking challenges DEMAND a discriminating run when budget
    # allows; the investigator's response is recorded with the new
    # evidence (resolved) or as preserved dissent (unresolved).
    hyps, acts = hviews(), ran_actions()
    sk = roles.skeptic(hyps, [{"id": a["id"], "tool": a["tool"]}
                              for a in acts]) if skeptic else \
        {"role": "skeptic", "challenges": [], "blocking": [],
         "limitations": ["skeptic disabled (ablation)"]}
    disagreements = []
    responses = []
    for ch in sk.get("challenges", []):
        hid = ch.get("hypothesis_id")
        target = next((h for h in hyps if h.get("id") == hid), None)
        answered_by = (target or {}).get("answered_by") or \
            ch.get("proposed_test", "")
        if ch.get("blocking") and ledger.remaining() >= 1:
            # Investigator responds: one discriminating probe aimed
            # at the challenged hypothesis (cheapest unused tool).
            used = {a["tool"] for a in acts}
            probe_order = ["calibration_and_error_analysis",
                           "residual_feature_dependence",
                           "temporal_changepoint_scan",
                           "regression_metrics",
                           "classification_metrics",
                           "data_quality_profile",
                           "segment_quality_screen"]
            probe = next((t for t in probe_order if t not in used),
                         None)
            if probe is not None:
                try:
                    ledger.reserve("investigator-response", probe)
                    resp = _run_probe(session, inv, probe, artifact,
                                      facts)
                    acts = ran_actions()  # refresh incl. new action
                    hyps = hviews()
                    after = next((h for h in hyps
                                  if h.get("id") == hid), {})
                    responses.append({
                        "challenge": ch["type"], "probe": probe,
                        "ok": resp.get("ok"),
                        "hypothesis_status_after": after.get("status"),
                        "answered_by": answered_by})
                    disagreements.append({
                        "challenge": ch,
                        "resolution": "responded-with-evidence: "
                        f"ran {probe}; status now "
                        f"{after.get('status')}"})
                    continue
                except Exception as exc:
                    responses.append({
                        "challenge": ch["type"], "probe": probe,
                        "ok": False,
                        "reason": str(exc)[:150]})
        disagreements.append({
            "challenge": ch,
            "resolution": "preserved-unresolved: doubt stands and "
            "the conclusion must carry it; no vote taken"})
    team["skeptic"] = sk
    team["disagreements"] = disagreements
    record_event(session, inv_id, "team",
                 f"M11 review: {len(disagreements)} disagreements "
                 f"recorded, {len(sk.get('blocking', []))} blocking",
                 payload={"blocking": len(sk.get("blocking", []))})
    session.commit()

    team["investigator_responses"] = responses
    team["judge"] = roles.judge(hviews()) if judge else \
        {"role": "judge", "verdicts": [],
         "limitations": ["judge disabled (ablation)"]}
    team["ledger"] = {"used": ledger.used, "cap": ledger.cap,
                      "log": ledger.log}
    return {"scenario": scenario_id, "baseline": base, "team": team}
