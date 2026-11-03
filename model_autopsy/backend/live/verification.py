"""Verification workflow: plan -> execute-or-explain (Eval v3, Stage 5).

Existing `live.verify.maybe_verify` (eligibility, independence, budget,
resolution contract) is KEPT and delegated to — this module adds the
missing planning layer and structured non-verification records so that
"proposed" and "executed" are always distinguishable:

- `plan_verification`: records a `verification_plan` event naming the claim,
  the independent probe tool, and the expected pro/con observations.
  Never dispatches; never spends.
- `record_non_verification`: records a `non_verification` event with a
  machine-readable reason code when no probe can run.
- `run_verification_phase`: bounded driver entry point — plans the top
  eligible hypothesis, delegates execution to `verify.maybe_verify`,
  maps skip paths to reason codes. At most one probe per hypothesis per
  phase; all existing budgets, timeouts, and stopping rules unchanged.
- `verification_status`: read-only summary for reports and scorer v3.

Reason codes: no_suitable_tool | insufficient_data | budget_exhausted |
unsafe_or_inappropriate | info_unavailable | experiment_failed |
stopped_before_verification | already_measured (same-tool repeat refused).
"""
from __future__ import annotations

REASON_CODES = ("no_suitable_tool", "insufficient_data",
                "budget_exhausted", "unsafe_or_inappropriate",
                "info_unavailable", "experiment_failed",
                "stopped_before_verification", "already_measured")


def _eligible(session, inv):
    from ..db import Hypothesis
    from .verify import _moving
    out = []
    for h in session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv.id).all():
        n_sup, n_con, _, _ = _moving(h.evidence_refs or [])
        if h.status in ("investigating", "supported") \
                and n_sup >= 1 and n_con == 0:
            out.append(h)
    out.sort(key=lambda h: (h.status == "supported",
                            len(h.evidence_refs or "")), reverse=True)
    return out


def _probe_for(session, inv, hyp):
    """Independent probe tool for this hypothesis family, or a reason."""
    from .verify import _family_for
    from ..m10 import replication as REP
    family = _family_for(hyp.text)
    if family not in REP.SECOND_PROBE:
        return None, family, "no_suitable_tool"
    from ..db import Action
    ran_tools = {a.tool_name for a in session.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").all() if a.tool_name}
    tool, _ = REP.SECOND_PROBE[family]
    if tool in ran_tools:
        return None, family, "already_measured"
    return tool, family, None


def plan_verification(session, inv, hypothesis_id: str) -> dict:
    """Record a verification plan. Read-only w.r.t. budget and tools."""
    from ..db import Hypothesis, record_event
    hyp = session.get(Hypothesis, hypothesis_id)
    if hyp is None or hyp.investigation_id != inv.id:
        return {"planned": False, "reason": "info_unavailable"}
    tool, family, blocked = _probe_for(session, inv, hyp)
    if blocked is not None:
        return record_non_verification(
            session, inv, hyp.id, blocked,
            f"family={family}: independent probe unavailable")
    remaining = inv.max_tool_calls - inv.tool_call_count
    plan = {"planned": True, "hypothesis_id": hyp.id, "family": family,
            "tool": tool, "budget_ok": remaining >= 1,
            "expected_if_true": (f"independent {tool} reproduces the "
                                 f"{family} effect"),
            "expected_if_false": (f"independent {tool} finds no effect "
                                   f"(gap within noise / spread uniform)")}
    record_event(session, inv.id, "verification_plan",
                 f"Verification planned: {tool} for hypothesis "
                 f"{hyp.id[:8]}", payload=plan)
    session.commit()
    return plan


def record_non_verification(session, inv, hypothesis_id: str | None,
                            reason: str, detail: str = "") -> dict:
    """Record WHY verification did not run. Never executes anything."""
    from ..db import record_event
    if reason not in REASON_CODES:
        reason = "info_unavailable"
    rec = {"planned": False, "executed": False,
           "hypothesis_id": hypothesis_id, "reason": reason,
           "detail": detail[:300]}
    record_event(session, inv.id, "non_verification",
                 f"Verification not executed: {reason}",
                 payload=rec)
    session.commit()
    return rec


def _reason_from_outcome(result: dict) -> tuple[str, str]:
    title = str((result.get("verification") or {}).get("title", ""))
    reason = str((result.get("verification") or {}).get("reason", ""))
    blob = (title + " " + reason).lower()
    if "budget" in blob:
        return "budget_exhausted", reason
    if "no independent probe" in blob or "no eligible" in blob:
        return "no_suitable_tool", reason
    if "not dispatched" in blob or "already measured" in blob:
        return "already_measured", reason
    if "error" in blob:
        return "experiment_failed", reason
    return "stopped_before_verification", reason


def run_verification_phase(session, inv, budget, experiments_left=None,
                           artifact=None) -> dict:
    """Bounded verification: plan, delegate, explain. See module doc."""
    from . import verify as _verify_live
    eligible = _eligible(session, inv)
    if not eligible:
        record_non_verification(session, inv, None, "insufficient_data",
                                "no hypothesis with >=1 moving support "
                                "and zero contradicts")
    else:
        plan_verification(session, inv, eligible[0].id)
    result = _verify_live.maybe_verify(
        session, inv, budget, experiments_left=experiments_left,
        artifact=artifact)
    if not result.get("verified"):
        code, detail = _reason_from_outcome(result)
        record_non_verification(session, inv,
                                (result.get("verification") or {}).get(
                                    "hypothesis_id"), code, detail)
    return result


def verification_status(session, inv) -> dict:
    """Read-only rollup of plans, executions, and explicit non-runs."""
    from ..db import Event
    planned, executed, unexecuted = [], [], []
    try:
        events = session.query(Event).filter(
            Event.investigation_id == inv.id,
            Event.kind.in_(("verification_plan", "verification",
                            "non_verification"))).order_by(Event.seq).all()
    except Exception:
        return {"planned": planned, "executed": executed,
                "unexecuted": unexecuted}
    for e in events:
        p = dict(e.payload or {})
        if e.kind == "verification_plan" and p.get("planned"):
            planned.append({"hypothesis_id": p.get("hypothesis_id"),
                            "tool": p.get("tool"),
                            "expected_if_true": p.get("expected_if_true"),
                            "expected_if_false": p.get(
                                "expected_if_false")})
        elif e.kind == "verification" and p.get("confirmed") is True:
            executed.append({"hypothesis_id": p.get("hypothesis_id"),
                             "tool": p.get("tool"),
                             "action_id": p.get("action_id"),
                             "result": "corroborated"})
        elif e.kind == "verification" and p.get("action_id"):
            executed.append({"hypothesis_id": p.get("hypothesis_id"),
                             "tool": p.get("tool"),
                             "action_id": p.get("action_id"),
                             "result": "recorded without corroboration"})
        elif e.kind == "non_verification":
            unexecuted.append({"hypothesis_id": p.get("hypothesis_id"),
                               "reason": p.get("reason"),
                               "detail": p.get("detail")})
    return {"planned": planned, "executed": executed,
            "unexecuted": unexecuted}
