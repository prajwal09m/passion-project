"""M16 P0-1: discriminating-probe reservation (offline-capable).

Reserves ONE diagnostic experiment inside the existing experiment
budget, selected by the invention engine (not the model) for its
ability to distinguish competing hypotheses. Enforced before
dispatch via the shared Budget: no budget, no reservation. Never
forces a low-quality spec: when no valid discriminating spec
exists the reservation is explicitly declined with reasons.

No paid calls. Deterministic given recorded state.
"""
from __future__ import annotations


def _open_competing(hviews: list[dict]) -> list[dict]:
    return [h for h in hviews
            if h.get("status") in ("proposed", "investigating")]


def select(session, inv, facts: dict, budget_left: int) -> dict:
    """Choose the reserved spec; validate; do not execute.

    Returns {reserved: bool, spec|reason, ...}. Execution is left
    to the caller so budget reservation stays at the dispatch site.
    """
    from ..research import invention as INV
    from ..db import Hypothesis, Action
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    hviews = [{"id": h.id, "text": h.text, "status": h.status,
               "evidence_refs": h.evidence_refs or []} for h in hyps]
    open_h = _open_competing(hviews)
    if len(open_h) < 2:
        return {"reserved": False,
                "reason": "fewer than 2 open hypotheses; no "
                          "discrimination to buy"}
    # One open question synthesised from the competition (the
    # invention engine needs a question object, not a blank).
    from ..causal.hypotheses import analyze_competition
    comp = analyze_competition(
        [{"id": h["id"], "text": h["text"]} for h in open_h])
    question = {"id": "live-reservation",
                "family": "discriminate",
                "text": "which open hypothesis best explains the "
                        "recorded evidence?"}
    ran = [{"tool": a.tool_name, "args": dict(a.arguments or {})}
           for a in session.query(Action).filter(
               Action.investigation_id == inv.id,
               Action.status == "ran").all() if a.tool_name]
    cands = INV.propose(question, hviews, facts, ran,
                        {"experiments": budget_left})
    valid = [c for c in cands
             if INV.validate(c, facts, ran,
                             {"experiments": budget_left})["valid"]]
    # Prefer genuine discrimination; never fill with exploratory noise.
    discrim = [c for c in valid
               if c.get("info_value", {}).get("decision_relevance")
               in ("decisive", "supporting")]
    if not discrim:
        return {"reserved": False,
                "reason": "no valid discriminating spec inventable "
                          "within budget/args",
                "n_proposed": len(cands), "n_valid": len(valid),
                "competition": comp}
    spec = discrim[0]
    return {"reserved": True, "spec": spec,
            "why": spec.get("distinguishes", ""),
            "decision_relevance": spec.get("info_value", {}).get(
                "decision_relevance"),
            "competition": comp}


def run_reserved(session, inv, facts: dict, budget,
                 experiments_left: int | None = None) -> dict:
    """Enforce the reservation: reserve budget, execute, link, record.

    Returns a durable record; also recorded as a 'reservation' event
    so the dashboard and audits can show it. Declines cleanly.
    """
    from .. import engine as ENG
    from ..causal import linker as LK
    from ..live import governor as GOV
    from ..live import accounting as ACCT
    from ..db import record_event
    remaining = inv.max_tool_calls - inv.tool_call_count
    if experiments_left is not None:
        remaining = min(remaining, max(0, experiments_left))
    if remaining < 2:
        # One for the reservation, one left for the model: the model
        # must retain control over the remaining allocation.
        rec = {"reserved": False,
               "reason": f"only {remaining} experiment(s) left; "
                         "reservation needs 1 + 1 for the model"}
        record_event(session, inv.id, "reservation",
                     "Reservation declined: " + rec["reason"],
                     payload=rec)
        session.commit()
        return rec
    # M18 Phase 2: the verification hold applies to the reservation too.
    _ok_hold, _why_hold = ACCT.can_spend_for(
        session, inv, budget, "reservation", experiments_left)
    if not _ok_hold:
        rec = {"reserved": False, "reason": _why_hold}
        record_event(session, inv.id, "reservation",
                     "Reservation declined: " + _why_hold, payload=rec)
        session.commit()
        return rec
    # The investigation must already carry a reservation decision...
    sel = select(session, inv, facts, remaining)
    if not sel.get("reserved"):
        record_event(session, inv.id, "reservation",
                     "Reservation declined: " + sel.get("reason", "?"),
                     payload=sel)
        session.commit()
        return sel
    spec = sel["spec"]
    try:
        tok = ACCT.reserve_experiment(
            session, inv, budget, spec["tool"],
            purpose="reserved discriminating probe: " +
            str(sel.get("why", ""))[:200],
            kind="reservation", experiments_left=experiments_left)
    except (GOV.BudgetExceeded, ValueError) as exc:
        rec = {"reserved": False,
               "reason": f"budget refused: {exc}",
               "spec_tool": spec["tool"]}
        record_event(session, inv.id, "reservation",
                     "Reservation refused by budget", payload=rec)
        session.commit()
        return rec
    from ..research import invention as INV
    out = INV.execute(session, inv, spec)
    if out.get("reused"):
        ACCT.release_experiment(session, inv, budget, tok, spec["tool"],
                                "reservation",
                                "dedup reuse: prior result stands")
    else:
        ACCT.settle_experiment(session, inv, budget, tok, spec["tool"],
                               "reservation", bool(out.get("ok")),
                               action_id=out.get("action_id"),
                               error=out.get("error"))
    rec = {"reserved": bool(out.get("ok")), "spec_tool": spec["tool"],
           "why": sel.get("why"), "action_id": out.get("action_id"),
           "error": out.get("error")}
    if out.get("ok"):
        from ..db import Action
        act = session.get(Action, out.get("action_id"))
        if act is not None:
            rec["links_applied"] = LK.link_tool_result(session, inv, act)
    record_event(session, inv.id, "reservation",
                 f"Reserved probe ran: {spec['tool']} — "
                 f"{sel.get('why', '')}"[:300] if out.get("ok")
                 else f"Reserved probe failed: {spec['tool']}",
                 payload=rec)
    session.commit()
    return rec
