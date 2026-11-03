"""M17 Phase 2: live verification caller (budgeted, recorded).

`maybe_verify` is the live loop's single caller into the existing
offline verification machinery (`m10.replication`, `research.
verification`, `research.resolve`). It never manufactures confirmation:

- Eligibility: hypothesis with >=1 moving support, zero contradicts,
  status investigating/supported. The second probe COMPLETES
  corroboration; it does not require it upfront.
- Independence: the probe runs through `replication.replicate`
  (different-tool rule, own action id + provenance, result linked,
  contradictions preserved). Same-tool reruns are refused and never
  counted as verification.
- Budget: one experiment reserved on the shared Budget before dispatch;
  pre-dispatch refusals release the hold, post-dispatch work settles it.
  If the budget cannot support verification, the finding is preserved
  as unresolved with a recorded reason.
- Confirmation: only when the post-probe state shows >=2 independent
  moving supports, still zero contradicts, AND the adversarial
  checklist (`research.verification.review_claim`) upholds. Otherwise
  the outcome stays unresolved and `resolve.contract` says so.
- A resolution contract is built from recorded state on EVERY path
  (verified, failed, skipped) and recorded as a `resolution` event.
"""
from __future__ import annotations


def _moving(refs):
    sup_tools, con_tools = set(), set()
    for r in refs or []:
        rel = r.get("relation")
        tool = r.get("tool") or "?"
        if rel == "supports":
            sup_tools.add(tool)
        elif rel == "contradicts":
            con_tools.add(tool)
    return len(sup_tools), len(con_tools), sup_tools, con_tools


def _family_for(text):
    from ..causal import attribution as AT
    from ..causal import selection as SEL
    if AT._names_ranking_claim(text or ""):
        return "ranking"
    return SEL._family_of(text or "")


def maybe_verify(session, inv, budget, experiments_left=None, artifact=None):
    """Run one budgeted verification + resolution contract. See module doc."""
    from ..db import Hypothesis, Action, record_event
    from .. import engine as ENG
    from ..live import governor as GOV
    from ..m10 import replication as REP
    from ..research import verification as VER
    from ..research import resolve as RES

    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    eligible = []
    for h in hyps:
        n_sup, n_con, _, _ = _moving(h.evidence_refs or [])
        if h.status in ("investigating", "supported") \
                and n_sup >= 1 and n_con == 0:
            eligible.append((h, n_sup))
    eligible.sort(key=lambda t: (t[0].status == "supported", t[1]),
                  reverse=True)

    def _contract(verification, conclusion, uncertainty):
        acts = session.query(Action).filter(
            Action.investigation_id == inv.id).all()
        # Re-read hypotheses: the probe may have moved statuses since
        # eligibility was computed; the contract must see final state.
        fresh = session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv.id).all()
        views = [{"text": h.text, "status": h.status,
                  "evidence_refs": h.evidence_refs or []}
                 for h in fresh]
        ran = [a for a in acts if a.status == "ran"]
        failed = [{"tool": a.tool_name, "error": (a.error or "")[:160]}
                  for a in acts if a.status == "failed"]
        moving = [r for h in views for r in (h.get("evidence_refs") or [])
                  if r.get("relation") in ("supports", "contradicts")]
        # M18 Phase 3: genuine transition events, never status snapshots.
        # A hypothesis that merely collected evidence while staying
        # `investigating` contributes zero advancement transitions, so
        # the contract reports `unresolved`, not `partially-resolved`.
        transitions = RES.collect_transitions(session, inv.id)
        competing = [h["text"][:120] for h in views
                     if h["status"] in ("investigating", "supported")]
        contradictions = [h["text"][:120] for h in views
                          if h["status"] == "rejected"]
        return RES.contract(
            inv.question or "", views,
            [{"tool": a.tool_name, "ok": True} for a in ran],
            failed, transitions, competing, contradictions,
            conclusion, {"level": "recorded",
                         "basis": str(len(moving)) + " moving refs"},
            verification, uncertainty,
            "budget experiments " + str(budget.experiments_used) + "/"
            + str(budget.caps["experiments"]))

    def _finish(verification, resolution):
        record_event(session, inv.id, "verification",
                     verification.get("title", "verification"),
                     payload={k: v for k, v in verification.items()
                              if k != "title"})
        session.commit()
        record_event(session, inv.id, "resolution",
                     "Resolution contract: " + str(resolution.get("status")),
                     payload=resolution)
        session.commit()
        return {"verified": bool(verification.get("confirmed")),
                "verification": verification, "resolution": resolution}

    if not eligible:
        verification = {"title": "Verification skipped: no eligible "
                                 "hypothesis",
                        "confirmed": False,
                        "reason": "no hypothesis with >=1 moving support "
                                  "and zero contradicts"}
        resolution = _contract(verification, "Unresolved: no finding met "
                             "the verification bar", "which hypothesis, "
                             "if any, the evidence supports")
        return _finish(verification, resolution)

    hyp, _ = eligible[0]
    family = _family_for(hyp.text)
    if family not in REP.SECOND_PROBE:
        verification = {"title": "Verification skipped: no independent "
                                 "probe for family",
                        "confirmed": False, "hypothesis_id": hyp.id,
                        "family": family,
                        "reason": "no replication probe for " + family}
        resolution = _contract(verification, "Unresolved: verification "
                             "impossible for the leading family",
                             "an independent probe for family " + family)
        return _finish(verification, resolution)

    remaining = inv.max_tool_calls - inv.tool_call_count
    if experiments_left is not None:
        remaining = min(remaining, max(0, experiments_left))
    if remaining < 1:
        verification = {"title": "Verification skipped: no experiment "
                                 "budget left",
                        "confirmed": False, "hypothesis_id": hyp.id,
                        "family": family,
                        "reason": "budget cannot support verification; "
                                  "finding preserved as unresolved"}
        resolution = _contract(verification, "Unresolved: budget "
                             "exhausted before verification",
                             "whether the leading finding reproduces")
        return _finish(verification, resolution)

    ran = [{"tool": a.tool_name, "args": dict(a.arguments or {})}
           for a in session.query(Action).filter(
               Action.investigation_id == inv.id,
               Action.status == "ran").all() if a.tool_name]
    tool, _question = REP.SECOND_PROBE[family]
    from ..live import accounting as ACCT
    try:
        tok = ACCT.reserve_experiment(
            session, inv, budget, tool,
            purpose="independent verification of hypothesis " +
            hyp.id[:8],
            hypothesis_id=hyp.id, kind="verification",
            experiments_left=experiments_left)
    except (GOV.BudgetExceeded, ValueError) as exc:
        verification = {"title": "Verification refused by budget",
                        "confirmed": False, "hypothesis_id": hyp.id,
                        "family": family, "reason": str(exc)}
        resolution = _contract(verification, "Unresolved: verification "
                             "refused by budget", "whether the leading "
                             "finding reproduces")
        return _finish(verification, resolution)

    art = artifact or (inv.config or {}).get("predictions_path") or ""
    try:
        out = REP.replicate(session, inv, hyp.id, family, art, ran)
    except Exception as exc:  # conservative: it may have dispatched
        ACCT.settle_experiment(session, inv, budget, tok, tool,
                               "verification", False,
                               error=f"{type(exc).__name__}: {exc}"[:200])
        verification = {"title": "Verification error (settled)",
                        "confirmed": False, "hypothesis_id": hyp.id,
                        "family": family,
                        "reason": (type(exc).__name__ + ": "
                                   + str(exc))[:200]}
        resolution = _contract(verification, "Unresolved: verification "
                             "errored", str(exc)[:200])
        return _finish(verification, resolution)
    if not out.get("ok"):
        # Pre-dispatch refusal (same tool already ran / unknown args):
        # nothing was spent, release the hold.
        ACCT.release_experiment(
            session, inv, budget, tok, tool, "verification",
            "verification not dispatched: "
            + str(out.get("reason", ""))[:100])
        verification = {"title": "Verification not dispatched",
                        "confirmed": False, "hypothesis_id": hyp.id,
                        "family": family,
                        "reason": out.get("reason", "replication refused")}
        resolution = _contract(verification, "Unresolved: independent "
                             "probe could not be dispatched",
                             str(out.get("reason", ""))[:200])
        return _finish(verification, resolution)
    ACCT.settle_experiment(session, inv, budget, tok, tool,
                           "verification", True,
                           action_id=out.get("action_id"))

    # Post-probe corroboration audit from recorded refs (reloaded).
    h2 = session.get(Hypothesis, hyp.id)
    n_sup, n_con, sup_tools, _ = _moving(h2.evidence_refs or [])
    probe_action = out.get("action_id")
    if n_sup >= 2 and n_con == 0:
        probe_act = session.get(Action, probe_action)
        probe_res = dict((probe_act.result if probe_act is not None
                          else {}) or {})
        slice_ns = [v for v in (probe_res.get("per_slice_n") or {}).values()
                    if isinstance(v, int)]
        claim = {"summary": (h2.text or "")[:200],
                 "n": min(slice_ns) if slice_ns else 0,
                 "method": "independent " + tool,
                 "numbers": {"independent_supports": n_sup},
                 "refute_criteria": "a contradicting measurement"}
        review = VER.review_claim(claim, [{"tool": tool}])
        VER.record_review(session, inv, hyp.id, review)
        if review.get("verdict") == "upheld":
            finding = ENG.record_finding(
                session, inv, "Confirmed: " + (h2.text or "")[:220],
                "confirmed", evidence_action_id=probe_action)
            verification = {"title": "Verified: independent probe "
                                     "corroborates",
                            "confirmed": True, "hypothesis_id": hyp.id,
                            "family": family, "tool": tool,
                            "action_id": probe_action,
                            "independent_supports": sorted(sup_tools),
                            "finding": finding.get("summary", "")[:200]}
            resolution = _contract(
                verification, "CONFIRMED: " + (h2.text or "")[:200],
                "causal mechanism behind the confirmed slice effect")
            return _finish(verification, resolution)
        verification = {"title": "Verification checklist downgraded; "
                                 "not confirmed",
                        "confirmed": False, "hypothesis_id": hyp.id,
                        "family": family, "tool": tool,
                        "reason": review.get("disagreement",
                                             "review downgraded")}
    else:
        verification = {"title": "Verification inconclusive; not confirmed",
                        "confirmed": False, "hypothesis_id": hyp.id,
                        "family": family, "tool": tool,
                        "reason": "post-probe state: " + str(n_sup)
                                  + " independent supports, " + str(n_con)
                                  + " contradicts; bar is 2+/0"}
    resolution = _contract(verification, "Unresolved: independent probe "
                         "did not complete corroboration",
                         "a second independent supporting measurement")
    return _finish(verification, resolution)
