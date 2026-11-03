"""M18 Phase 1+2: authoritative experiment accounting + verification hold.

A hypothesis is a claim; registering, updating, or retiring it is NOT an
executed scientific experiment. Only actual measurement/intervention
dispatches consume the 6-slot experiment budget.

All live experiment spenders (model loop, reservation, skeptic,
verification) route through this module so there is exactly ONE place
where experiment capacity is granted, charged, released, and audited.
"""
from __future__ import annotations

# Hypothesis lifecycle ops: bookkeeping, never experiments.
HYPOTHESIS_OPS = frozenset({
    "propose_hypothesis",
    "propose_revision_instructions",
})

# One experiment slot is held for independent verification while the
# investigation can still plausibly need it (Phase 2 guarantee).
VERIFICATION_HOLD = 1


def is_experiment(tool_name: str | None) -> bool:
    """True when dispatching this tool is an actual scientific experiment."""
    return (tool_name or "") not in HYPOTHESIS_OPS


def experiments_remaining(budget, experiments_left: int | None = None) -> int:
    """Smallest credible remaining count across Budget cap, inv cap, caller."""
    from ..db import Investigation as _INV  # noqa: F401 (documented coupling)
    rem = budget.caps["experiments"] - budget.experiments_used - _held(budget)
    if experiments_left is not None:
        rem = min(rem, max(0, experiments_left))
    return max(0, rem)


def _held(budget) -> int:
    try:
        return budget._held("experiments")
    except Exception:
        return 0


def _verification_terminal(session, inv_id: str) -> bool:
    """True once verification reached a recorded terminal state."""
    from ..db import Event
    evs = session.query(Event).filter(
        Event.investigation_id == inv_id,
        Event.kind == "verification").all()
    for e in evs:
        p = e.payload or {}
        t = (e.title or "").lower()
        if p.get("confirmed") is True:
            return True
        if any(k in t for k in ("verified", "corroborat", "inconclusive",
                                "not dispatched", "no experiment",
                                "no eligible", "impossible", "refused",
                                "checklist downgraded", "skipped", "error")):
            # Any recorded verification outcome (success or honest terminal
            # skip) releases the hold — the question is answered on record.
            return True
    return False


def verification_hold_active(session, inv, budget) -> bool:
    """Whether the 1-slot verification hold currently applies.

    Hold is active when verification has no recorded terminal outcome AND an
    eligible candidate exists on record: a proposed/investigating/supported
    hypothesis with >=1 moving support and zero contradicts. Before any
    candidate exists the hold is deliberately OFF — otherwise the first
    evidence-gathering experiments (which are what CREATE the candidate)
    would deadlock against the hold. Once a candidate emerges, no further
    non-verification experiment may consume the final slot; verification
    itself may always consume it. Releases on terminal verification or when
    no candidate remains.
    """
    try:
        if _verification_terminal(session, inv.id):
            return False
        from ..db import Hypothesis
        hyps = session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv.id).all()
        for h in hyps:
            if h.status not in ("proposed", "investigating", "supported"):
                continue
            refs = h.evidence_refs or []
            sup = any(r.get("relation") == "supports" for r in refs)
            con = any(r.get("relation") == "contradicts" for r in refs)
            if sup and not con:
                return True
        return False
    except Exception:
        return False


def can_spend_for(session, inv, budget, kind: str,
                  experiments_left: int | None = None) -> tuple[bool, str]:
    """Gate a non-verification experiment against the verification hold."""
    rem = experiments_remaining(budget, experiments_left)
    need = 1 + (VERIFICATION_HOLD if (
        kind != "verification" and verification_hold_active(session, inv, budget)
    ) else 0)
    if rem < need:
        if kind == "verification":
            return False, (f"no experiment budget left ({rem} remaining)")
        return False, (f"preserving verification capacity "
                       f"({rem} remaining, hold={VERIFICATION_HOLD})")
    return True, ""


def reserve_experiment(session, inv, budget, tool: str, purpose: str,
                       hypothesis_id: str | None = None,
                       kind: str = "diagnostic",
                       experiments_left: int | None = None) -> str:
    """Single choke point for experiment spend. Returns the hold token.

    Raises BudgetExceeded when unsafe (including verification-hold refusal
    for non-verification kinds). Records an auditable `experiment_ledger`
    event with purpose, hypothesis link, tool identity, and charge.
    """
    from ..db import record_event
    from . import governor as GOV
    if not is_experiment(tool):
        raise ValueError(f"{tool!r} is a hypothesis op, not an experiment")
    ok, why = can_spend_for(session, inv, budget, kind, experiments_left)
    if not ok:
        raise GOV.BudgetExceeded(why)
    tok = budget.reserve("experiments", 1, note=f"{kind}:{tool}"[:120])
    record_event(session, inv.id, "experiment_ledger",
                 f"Experiment reserved: {tool} ({kind})",
                 payload={"tool": tool, "kind": kind, "purpose": purpose[:300],
                          "hypothesis_id": hypothesis_id,
                          "token": tok, "status": "reserved"})
    session.commit()
    return tok


def settle_experiment(session, inv, budget, token: str, tool: str,
                      kind: str, ok: bool, action_id: str | None = None,
                      error: str | None = None) -> None:
    """Charge a dispatched experiment exactly once."""
    from ..db import record_event
    budget.settle(token, 1)  # started = counted, even on failure (M8 rule)
    record_event(session, inv.id, "experiment_ledger",
                 f"Experiment settled: {tool} ({kind}, "
                 f"{'ok' if ok else 'failed'})",
                 payload={"tool": tool, "kind": kind, "token": token,
                          "status": "settled", "ok": bool(ok),
                          "action_id": action_id, "error": (error or "")[:200]})
    session.commit()


def release_experiment(session, inv, budget, token: str, tool: str,
                       kind: str, reason: str) -> None:
    """Free a hold when nothing was dispatched (dedup reuse / refusal)."""
    from ..db import record_event
    budget.release(token, reason[:160])
    record_event(session, inv.id, "experiment_ledger",
                 f"Experiment released: {tool} ({kind})",
                 payload={"tool": tool, "kind": kind, "token": token,
                          "status": "released", "reason": reason[:200]})
    session.commit()
