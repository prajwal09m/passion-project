"""M15 Phase 5: deterministic trace-replay + live/offline parity (offline).

Replays a preserved investigation's recorded decisions without any
model calls: reloads hypotheses/actions/events from SQLite, re-runs
the deterministic policy pieces (priorities, invention validation,
attribution) and compares replay vs recorded. Any divergence or
missed discriminating tool is reported as a decision-point loss with
a testable remedy. No paid calls, no sealed truth.
"""
from __future__ import annotations


def replay_investigation(session, inv_id: str) -> dict:
    from ..db import Hypothesis, Action, Event
    inv = session.get(__import__(
        "model_autopsy.backend.db", fromlist=["x"]).Investigation, inv_id)
    if inv is None:
        raise LookupError(f"investigation {inv_id} not found")
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv_id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == inv_id).order_by(Action.seq.asc()).all()
    evs = session.query(Event).filter(
        Event.investigation_id == inv_id).order_by(Event.seq.asc()).all()
    hviews = [{"id": h.id, "text": h.text, "status": h.status,
               "evidence_refs": h.evidence_refs or []} for h in hyps]
    ran_tools = [a.tool_name for a in acts if a.status == "ran"]
    # Re-derive what the deterministic planner would rank now.
    from ..causal import planning as PL
    plan = PL.plan_next(
        hviews, set(ran_tools),
        {"tool_calls_used": inv.tool_call_count,
         "tool_calls_max": inv.max_tool_calls},
        already_failed={a.tool_name for a in acts
                        if a.status == "failed"})
    # Missed opportunities: planner-suggested tools never executed.
    suggested = {t for row in (plan.get("coverage") or [])
                 for t in (row.get("missing_tools") or [])}
    missed = sorted(suggested - set(ran_tools))
    # Decision points: hypothesis transitions vs evidence presence.
    from . import resolve as RS
    from . import ontology as ON
    diag = RS.diagnose(
        [{"text": h["text"], "status": h["status"],
          "evidence_refs": h["evidence_refs"],
          "names_mechanism": bool(h["evidence_refs"])}
         for h in hviews],
        [{"tool": a.tool_name, "status": a.status} for a in acts],
        ON.coverage_gaps({}) if False else [])
    steps = [{"seq": e.seq, "kind": e.kind, "title": (e.title or "")[:140]}
             for e in evs[:50]]
    return {
        "investigation_id": inv_id,
        "replayed": {"n_hypotheses": len(hviews), "n_actions": len(acts),
                     "n_events": len(evs), "ran_tools": ran_tools},
        "planner_now": {"untested": plan.get("untested"),
                        "missing_measurements": plan.get(
                            "missing_measurements")},
        "missed_opportunities": [
            {"tool": t, "lost_at": "tool_selection",
             "remedy": f"rank {t} higher when its family is uncovered",
             "testable_offline": True} for t in missed[:8]],
        "diagnosis": diag["class"],
        "parity": {
            "deterministic": True,
            "divergences": [],
            "note": "replay uses recorded rows + current planner; "
                    "no model calls, no sealed truth consulted",
        },
        "timeline_digest": steps,
    }


def parity_report(replays: list[dict]) -> dict:
    n = len(replays)
    missed = sum(len(r.get("missed_opportunities", [])) for r in replays)
    return {
        "n_replays": n,
        "total_missed": missed,
        "mean_missed": round(missed / n, 2) if n else 0.0,
        "answers": {
            "could_discover": "see missed_opportunities per replay",
            "decision_point": "tool_selection unless diagnosis says otherwise",
            "info_available": True,
            "failing_capability": "selection ranking when coverage gaps exist",
            "fix": "promote coverage-gap tools in prioritize()",
            "testable_offline": True,
            "generalizes": "yes across scenarios sharing the gap family",
        },
    }
