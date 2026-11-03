"""M16 P1-3: skeptic-lite live review (offline-capable, budgeted).

Runs inside the live turn (no new budget): reviews hypotheses +
recorded evidence WITHOUT receiving the investigator's conclusion,
flags unsupported claims / metric-granularity mismatches / missing
falsification, and may request ONE additional probe when justified.
Dissent is preserved when evidence cannot resolve it. Never exceeds
the experiment budget; reuses the reservation when the probe matches.
"""
from __future__ import annotations


def enabled(inv_config: dict | None) -> bool:
    """Arm flag: comparison arms may set m16_skeptic=False. Default on."""
    return bool((inv_config or {}).get("m16_skeptic", True))


def _state(inv) -> dict:
    """Open/answered blocking challenges persisted on the investigation."""
    return dict((inv.config or {}).get("m17_skeptic") or
                {"open": [], "resolved": []})


def _save_state(session, inv, state: dict) -> None:
    inv.config = {**(inv.config or {}), "m17_skeptic": state}
    session.commit()


def blocking_open(session, inv, hypothesis_id: str) -> list[dict]:
    """Unanswered blocking challenges against one hypothesis."""
    return [c for c in _state(inv).get("open", [])
            if c.get("hypothesis_id") == hypothesis_id]


def mark_answered(session, inv, hypothesis_id: str, how: str) -> None:
    """Release the gate: probe ran, falsification tested, or dissent
    explicitly preserved. The acknowledgment stays visible in resolved."""
    state = _state(inv)
    still = []
    for c in state.get("open", []):
        if c.get("hypothesis_id") == hypothesis_id:
            state.setdefault("resolved", []).append(
                {**c, "resolution": how})
        else:
            still.append(c)
    state["open"] = still
    _save_state(session, inv, state)


def _granularity_challenges(hviews: list[dict],
                            acts: list[dict]) -> list[dict]:
    from ..causal import attribution as AT
    ran = [a for a in acts if a.get("status") == "ran"]
    out = []
    seg_args = {"split_by", "group_column", "slice_column",
                "segment_column", "group", "segment", "slice"}
    seg_measured = any(seg_args & set((a.get("args") or {}).keys())
                       for a in ran)
    slice_measured = any(a.get("tool") == "ranking_slice_diagnostics"
                         for a in ran)
    for h in hviews:
        if h.get("status") not in ("proposed", "investigating",
                                    "supported"):
            continue
        text = h.get("text") or ""
        # Missing-or-pooled coverage: a segment-specific claim with no
        # segment-broken measurement on record (whether or not refs
        # exist — pooled runs often link nothing at all).
        if AT._names_segment(text) and not seg_measured:
            out.append({
                "type": "metric-granularity-mismatch",
                "hypothesis_id": h.get("id"),
                "blocks": True,
                "detail": "segment-specific claim has no "
                          "segment-broken measurement on record; needs "
                          "the grouped/slice probe",
                "proposed_tool": "ranking_slice_diagnostics"})
        if AT._names_ranking_claim(text) and not slice_measured:
            out.append({
                "type": "ranking-metric-mismatch",
                "hypothesis_id": h.get("id"),
                "blocks": True,
                "detail": "ranking/top-K claim has no slice P@K "
                          "measurement on record; needs the slice probe",
                "proposed_tool": "ranking_slice_diagnostics"})
    return out


def review(session, inv, budget, experiments_left: int | None = None,
           facts: dict | None = None) -> dict:
    """One skeptic pass. Returns challenges, probe outcome, dissent.

    Pure budget discipline: a probe runs only when experiments
    remain; an already-ran tool+args is reused, never re-executed.
    """
    from ..db import Hypothesis, Action, record_event
    from ..m11 import roles as R
    from ..research import invention as INV
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == inv.id).all()
    hviews = [{"id": h.id, "text": h.text, "status": h.status,
               "evidence_refs": h.evidence_refs or []} for h in hyps]
    aviews = [{"id": a.id, "tool": a.tool_name, "status": a.status,
               "args": dict(a.arguments or {})} for a in acts]
    sk = R.skeptic(hviews, [{"id": a["id"], "tool": a["tool"]}
                            for a in aviews])
    challenges = list(sk.get("challenges") or [])
    challenges += _granularity_challenges(hviews, aviews)
    blocking = [c for c in challenges if c.get("blocks")]
    # M17: once per (type, hypothesis) — already-answered challenges
    # never re-block; unanswered ones persist across turns until a
    # probe, a falsification test, or explicit dissent resolves them.
    state = _state(inv)
    done_keys = {(r.get("type"), r.get("hypothesis_id"))
                 for r in state.get("resolved", [])}
    for c in blocking:
        key = (c.get("type"), c.get("hypothesis_id"))
        if key not in done_keys and not any(
                (o.get("type"), o.get("hypothesis_id")) == key
                for o in state.get("open", [])):
            state.setdefault("open", []).append(
                {"type": c.get("type"),
                 "hypothesis_id": c.get("hypothesis_id"),
                 "detail": (c.get("detail") or "")[:200]})
    _save_state(session, inv, state)
    actionable = [c for c in state.get("open", [])
                  if any((c.get("type") or "") == (b.get("type") or "")
                         and (c.get("hypothesis_id") or "") == (
                             b.get("hypothesis_id") or "")
                         for b in blocking
                         if b.get("proposed_tool") or b.get("proposed_test"))]
    rec = {"n_challenges": len(challenges),
           "n_blocking": len(blocking),
           "challenge_types": sorted({c.get("type") for c in challenges}),
           "probe": None, "dissent": []}
    remaining = inv.max_tool_calls - inv.tool_call_count
    if experiments_left is not None:
        remaining = min(remaining, max(0, experiments_left))
    if not actionable or remaining < 1:
        if actionable and remaining < 1:
            rec["dissent"] = []
            for b in actionable:
                rec["dissent"].append({
                    "challenge": b.get("type"),
                    "hypothesis_id": b.get("hypothesis_id"),
                    "resolution": "preserved-unresolved: no experiment "
                                  "budget left for the demanded probe"})
                # Acknowledged dissent satisfies the response
                # obligation; the objection stays visible in resolved.
                mark_answered(session, inv, b.get("hypothesis_id"),
                              "dissent: no budget")
        record_event(session, inv.id, "skeptic",
                     f"Skeptic-lite: {len(challenges)} challenges, "
                     f"{len(blocking)} blocking, probe: none",
                     payload={**rec, "limitations": sk.get("limitations")})
        session.commit()
        return rec
    # Every blocking challenge gets a probe or a preserved dissent.
    # Snapshots refresh after each execution so a second challenge
    # cannot re-spend on an exact duplicate (engine dedup returns the
    # prior result; the budget is released, never charged for reuse).
    from ..live import governor as GOV
    from ..live import accounting as ACCT
    probes: list[dict] = []
    for target in actionable:
        remaining = inv.max_tool_calls - inv.tool_call_count
        if experiments_left is not None:
            remaining = min(remaining, max(0, experiments_left
                                          - sum(1 for p in probes
                                                if not p.get(
                                                    "reused_reservation"))))
        if remaining < 1:
            rec["dissent"].append({
                "challenge": target.get("type"),
                "hypothesis_id": target.get("hypothesis_id"),
                "resolution": "preserved-unresolved: no experiment "
                              "budget left for the demanded probe"})
            mark_answered(session, inv, target.get("hypothesis_id"),
                          "dissent: no budget")
            continue
        acts = session.query(Action).filter(
            Action.investigation_id == inv.id).all()
        aviews = [{"id": a.id, "tool": a.tool_name,
                   "status": a.status,
                   "args": dict(a.arguments or {})} for a in acts]
        ran = [{"tool": a.tool_name, "args": dict(a.arguments or {})}
               for a in acts if a.status == "ran" and a.tool_name]
        spec = None
        if facts is not None:
            cands = INV.propose(
                {"id": "skeptic-probe", "family": "challenge",
                 "text": target.get("detail", "")},
                hviews, facts, ran, {"experiments": remaining})
            for c in cands:
                if INV.validate(c, facts, ran,
                                {"experiments": remaining})["valid"]:
                    spec = c
                    break
        if spec is None:
            # No inventable spec: the challenge stands as dissent,
            # not a forced low-quality run.
            rec["dissent"].append({
                "challenge": target.get("type"),
                "hypothesis_id": target.get("hypothesis_id"),
                "resolution": "preserved-unresolved: no valid "
                              "discriminating probe inventable"})
            mark_answered(session, inv, target.get("hypothesis_id"),
                          "dissent: no inventable probe")
            continue
        try:
            tok = ACCT.reserve_experiment(
                session, inv, budget, spec["tool"],
                purpose="skeptic challenge probe: " +
                str(target.get("type", ""))[:160],
                hypothesis_id=target.get("hypothesis_id"),
                kind="skeptic", experiments_left=experiments_left)
        except (GOV.BudgetExceeded, ValueError) as exc:
            rec["dissent"].append({
                "challenge": target.get("type"),
                "hypothesis_id": target.get("hypothesis_id"),
                "resolution": "preserved-unresolved: "
                              f"budget refused ({exc})"})
            mark_answered(session, inv, target.get("hypothesis_id"),
                          "dissent: budget refused")
            continue
        out = INV.execute(session, inv, spec)
        if out.get("reused"):
            # Engine dedup: the prior result stands; release the
            # reservation instead of charging for a free reuse.
            ACCT.release_experiment(session, inv, budget, tok,
                                    spec["tool"], "skeptic",
                                    "dedup reuse: prior result stands")
            mark_answered(session, inv, target.get("hypothesis_id"),
                          "probe-reuse:" + spec["tool"])
            probes.append({"tool": spec["tool"],
                           "ok": out.get("ok"),
                           "action_id": out.get("action_id"),
                           "challenge": target.get("type"),
                           "hypothesis_id": target.get("hypothesis_id"),
                           "reused_reservation": True})
            continue
        ACCT.settle_experiment(session, inv, budget, tok, spec["tool"],
                               "skeptic", bool(out.get("ok")),
                               action_id=out.get("action_id"),
                               error=out.get("error"))
        # The demanded probe ran: mark answered BEFORE linking so the
        # probe's own result is judged on evidence, not gated by the
        # challenge it resolves.
        mark_answered(session, inv, target.get("hypothesis_id"),
                      "probe:" + spec["tool"])
        if out.get("ok"):
            from ..causal import linker as LK
            act = session.get(Action, out.get("action_id"))
            if act is not None:
                LK.link_tool_result(session, inv, act)
        probes.append({"tool": spec["tool"], "ok": out.get("ok"),
                       "action_id": out.get("action_id"),
                       "challenge": target.get("type"),
                       "hypothesis_id": target.get("hypothesis_id"),
                       "reused_reservation": False})
    if probes:
        rec["probe"] = probes[0]
        rec["probes"] = probes
    state_now = _state(inv)
    rec["open"] = len(state_now.get("open", []))
    rec["resolved"] = len(state_now.get("resolved", []))
    record_event(session, inv.id, "skeptic",
                 f"Skeptic-lite: {len(challenges)} challenges, probe "
                 f"{(rec['probe'] or {}).get('tool', 'none')}",
                 payload={**rec, "limitations": sk.get("limitations")})
    session.commit()
    return rec
