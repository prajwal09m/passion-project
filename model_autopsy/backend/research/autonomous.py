"""Autonomous research loop (M9 flagship machinery, offline).

Question-centric investigation over REAL engine/tools/linker/planner:

  recon knowledge → questions → prioritize → agenda →
  per top question: competing hypotheses (seeded per family, generic) →
  invent spec → validate → execute → attribute (linker+attribution) →
  confounder check → revise agenda → stop when answered / budget out /
  nothing discriminating remains.

Deterministic policy (no provider): proves the machinery — question
generation, invention, attribution, confounder handling, agenda
revision, stopping — behaves end to end. Model quality is NOT what
this demonstrates; the live evaluation covers the model.
"""
from __future__ import annotations


SEEDS = {
    "classification": [
        ("One subgroup performs materially worse than the rest.",
         "per-split metric spread with adequate samples"),
        ("The score's apparent strength comes from leakage, not skill.",
         "suspicious input correlation or clean validation"),
        ("The model is miscalibrated in the operating range.",
         "reliability gap in populated bins"),
    ],
    "regression": [
        ("Systematic bias in predictions causes the miss.",
         "large mean residual vs spread"),
        ("Error depends on an input feature or segment.",
         "residuals correlate with a feature or concentrate by group"),
        ("Apparent miss is a data quality artifact.",
         "nulls, duplicates, or constant columns would show"),
    ],
    "forecasting": [
        ("A level shift in the recent period causes the miss.",
         "late error much larger than early error with clean splits"),
        ("Apparent miss is a split hygiene artifact.",
         "overlap or non-chronological splits would show"),
        ("Persistent misspecification explains all periods.",
         "large errors early as well as late"),
    ],
    "ranking": [
        ("Relevance is uneven across slices.",
         "per-slice metric spread"),
        ("Scores systematically misestimate relevance.",
         "large mean residual vs spread"),
        ("Apparent slice gap is a data quality artifact.",
         "nulls or duplicates concentrated in low slices"),
    ],
}


def run_autonomous(session, artifact: str, task_family: str, brief: str,
                   max_steps: int = 6, investigation_title: str = "M9 auto",
                   seed_hypotheses: bool = True) -> dict:
    """Execute the full loop. Returns behavior + agenda + specs."""
    from .. import engine
    from ..causal import linker as LK, planning as PL
    from ..causal import confounders as CF
    from ..db import Action, Hypothesis
    from . import agenda as AG, invention as INV

    inv = engine.create_investigation(
        session, "ml", investigation_title, brief,
        {"max_iterations": 3, "predictions_path": artifact})
    facts = INV.artifact_facts(artifact)
    knowledge = {"observed": {
        "columns": facts.get("columns", []), "readable": facts.get(
            "readable", False),
        "evaluation_methodology": "see brief",
        "spec_objective": brief,
        "temporal_hint": ({"column": facts.get("temporal_col")}
                          if facts.get("temporal_col") else None)},
        "inferred": {"has_labels": bool(facts.get("label_col")),
                     "has_scores": bool(facts.get("score_col")),
                     "possible_investigations": [],
                     "inconsistencies": []},
        "missing": [] if facts.get("readable") else ["readable_artifact"],
        "assumptions": ["artifact columns taken at face value"],
        "provenance": {"built_by": "autonomous.run_autonomous"}}
    if seed_hypotheses:
        for text, pred in SEEDS.get(task_family, SEEDS["regression"]):
            engine.propose_hypothesis(
                session, inv, text=text, predicted_observation=pred,
                confidence_note="structural prior for the family, not "
                                "evidence")
        # M13A.2: project-grounded segment hypothesis. When the artifact
        # carries a real segment column, one hypothesis must name it so
        # unfamiliar manifestations (zone, region, fold) are discoverable
        # rather than silently uncoverable by family priors alone.
        segs = facts.get("segments") or []
        if segs:
            engine.propose_hypothesis(
                session, inv,
                text=f"One {segs[0]} value performs materially worse "
                     f"than the rest (segment-concentrated failure).",
                predicted_observation=f"per-{segs[0]} metric spread with "
                                      f"adequate samples",
                confidence_note="project-grounded: segment column "
                                f"{segs[0]} observed in artifact, not "
                                "evidence")
    questions = AG.generate(knowledge, [], {"experiments": max_steps})
    AG.save(session, inv, questions, "initial autonomous agenda")
    specs_executed: list[dict] = []
    specs_proposed = 0
    stop_why = "step cap reached"
    steps = 0
    blocked_ids: set[str] = set()
    failed_sigs: set[tuple] = set()
    while steps < max_steps:
        hyps = session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv.id).all()
        hviews = [{"id": h.id, "text": h.text, "status": h.status,
                   "evidence_refs": h.evidence_refs or []} for h in hyps]
        ran = [{"tool": a.tool_name, "args": dict(a.arguments or {})}
               for a in session.query(Action).filter(
                   Action.investigation_id == inv.id,
                   Action.status == "ran").all() if a.tool_name]
        ranked = AG.prioritize(
            AG.load(inv),
            {"segments": facts.get("segments", []),
             "temporal": bool(facts.get("temporal_col")),
             "budget_left": {"experiments": max_steps - steps},
             "open_hypotheses": [h for h in hviews
                                 if h["status"] in ("proposed",
                                                    "investigating")]})
        # Persist ranks+reasons (prioritize returns copies): the stored
        # agenda always states why each question is ranked where it is.
        stored = AG.load(inv)
        by_id = {q.get("id"): q for q in ranked}
        for q in stored:
            if q.get("id") in by_id:
                q["priority"] = by_id[q["id"]]["priority"]
                q["priority_reason"] = by_id[q["id"]]["priority_reason"]
        AG.save(session, inv, stored,
                "agenda prioritized" if steps == 0
                else "agenda reprioritized")
        open_q = next((q for q in ranked
                       if q.get("status") == "open"
                       and q.get("id") not in blocked_ids), None)
        if open_q is None:
            stop_why = "no open research questions remain"
            break
        cands = INV.propose(open_q, hviews, facts, ran,
                            {"experiments": max_steps - steps})
        valid = [c for c in cands
                 if (c["tool"], tuple(sorted(c["args"].items())))
                 not in failed_sigs
                 and INV.validate(c, facts, ran,
                                  {"experiments":
                                   max_steps - steps})["valid"]]
        specs_proposed += len(cands)
        if not valid:
            # Prioritize returns copies: mark the stored question, and
            # remember it locally so a stale read can never re-pick it.
            blocked_ids.add(open_q.get("id"))
            stored = AG.load(inv)
            for q in stored:
                if q.get("id") == open_q.get("id"):
                    q["status"] = "blocked"
                    q["resolution"] = ("no valid discriminating "
                                        "experiment inventable within "
                                        "budget/args")
            AG.save(session, inv, stored,
                    "question blocked: nothing inventable")
            continue
        spec = valid[0]
        out = INV.execute(session, inv, spec)
        steps += 1
        specs_executed.append(spec)
        if not out.get("ok"):
            # Never replay a failed execution identically: record its
            # signature so the next iteration must invent something else.
            failed_sigs.add((spec["tool"],
                             tuple(sorted(spec["args"].items()))))
        if out.get("ok"):
            act = session.get(Action, out.get("action_id"))
            if act is not None:
                LK.link_tool_result(session, inv, act)
        hyps2 = session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv.id).all()
        hviews2 = [{"id": h.id, "text": h.text, "status": h.status,
                    "evidence_refs": h.evidence_refs or []} for h in hyps2]
        recon_facts = {"segments": facts.get("segments", []),
                       "temporal": bool(facts.get("temporal_col")),
                       "schema_note": ("schema" in brief.lower()),
                       "brief": brief,
                       "temporal_col": facts.get("temporal_col"),
                       "split_col": facts.get("split_col")}
        conf = CF.analyze(
            hviews2, recon_facts,
            [t for t in sorted({r["tool"] for r in ran})],
            artifact)
        AG.revise_on_evidence(session, inv, hviews2, conf)
        stop, why = PL.stopping(inv.status, hviews2,
                                inv.tool_call_count, max_steps, steps)
        if stop:
            stop_why = why
            break
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == inv.id).all()
    # M15 Phase 2: terminal resolution diagnosis (additive: recorded
    # as an event and returned; never changes loop behavior).
    from . import resolve as _RS, ontology as _ON
    _hviews = [{"id": h.id, "text": h.text, "status": h.status,
                "evidence_refs": h.evidence_refs or []} for h in hyps]
    _acts = [{"tool": a.tool_name, "status": a.status,
              "n": (a.result or {}).get("n")
              if isinstance(a.result, dict) else None}
             for a in acts]
    _diag = _RS.diagnose(_hviews, _acts, _ON.coverage_gaps(facts))
    _next = _RS.next_experiment(_diag, facts, [
        {"tool": a.tool_name, "args": dict(a.arguments or {})}
        for a in acts if a.tool_name])
    from ..db import record_event as _record
    _record(session, inv.id, "resolution",
            f"Terminal diagnosis: {_diag['class']} — {_diag['why']}; "
            f"next: {_next['action']}: {_next['detail']}"[:400],
            payload={"class": _diag["class"],
                     "next_action": _next["action"]})
    session.commit()
    resolution = {"diagnosis": _diag, "next_experiment": _next}
    engine.ensure_finalizable(session, inv)
    report = engine.build_report(session, inv)
    final = engine.finalize(session, inv, report)
    from ..causal import fallback as FB, report_schema as RS
    fb = FB.compose(inv, final, ["autonomous: no model summary"])
    fb_valid = RS.validate(
        {"conclusion": fb["conclusion"],
         "uncertainties": fb["uncertainties"], "schema_version": "m8-v1"},
        {h.id for h in hyps}, {a.id for a in acts})["valid"]
    return {"steps": steps, "specs_proposed": specs_proposed,
            "investigation_id": inv.id,
            "specs_executed": [s["tool"] for s in specs_executed],
            "statuses": sorted({h.status for h in hyps}),
            "n_transitions": sum(1 for h in hyps
                                if (h.revisions or h.evidence_refs)),
            "stop_rationale": stop_why,
            "tool_calls": inv.tool_call_count,
            "ran_tools": sorted({a.tool_name for a in acts
                                 if a.status == "ran"}),
            "agenda": AG.load(inv),
            "fallback_valid": fb_valid,
            "resolution": resolution,
            "confidences": [h.confidence for h in hyps]}
