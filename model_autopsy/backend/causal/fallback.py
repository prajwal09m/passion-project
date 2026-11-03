"""Deterministic fallback report (M8 Workstream B, extended in M20 Phase 5).

When the model's structured summary fails validation AND the bounded
repair fails (or is ineligible), this composes a fallback conclusion
STRICTLY from recorded state — hypotheses, ran actions, drafted report
sections, verification/resolution events. It is explicitly labeled
(`kind`, provenance) and never claims model authorship. Validity False
is preserved alongside it: a fallback is a reproducible research
record, not a valid model summary.

M20: the fallback now covers the full section shape (identification,
findings split by state, per-finding evidence, contradictions,
verification, adversarial outcome, tool summary, usage, limitations,
resolution, generation statement). Every section is records-only; when
information was never recorded the section says so explicitly instead
of inventing content. All M8 keys are preserved unchanged.
"""
from __future__ import annotations

FALLBACK_VERSION = "m8-fallback-v2"


def _finding_entry(f: dict) -> dict:
    return {"summary": f.get("summary"),
            "evidence_action_id": f.get("evidence_action_id")}


def _hyp_entry(h: dict, refs_key: str = "evidence_refs") -> dict:
    refs = h.get(refs_key) or []
    return {"hypothesis_id": h.get("hypothesis_id"),
            "text": h.get("text"),
            "status": h.get("status"),
            "evidence_refs": [
                {"action_id": r.get("action_id"), "tool": r.get("tool"),
                 "relation": r.get("relation")}
                for r in refs if isinstance(r, dict)][:20]}


def _event_trail(session, inv_id: str, kinds: tuple) -> list[dict]:
    if session is None:
        return []
    from ..db import Event
    try:
        evs = session.query(Event).filter(
            Event.investigation_id == inv_id).order_by(Event.seq).all()
    except Exception:
        return []
    return [{"title": e.title, "payload": e.payload or {}}
            for e in evs if e.kind in kinds]


def compose(inv, final_report: dict, errors: list,
            session=None, usage: dict | None = None) -> dict:
    """Build the labeled fallback from records only. No model text used.

    `session` (optional) unlocks the verification/resolution/adversarial
    sections from recorded events. `usage` (optional) carries recorded
    token/financial figures; absence is reported explicitly, never
    filled in.
    """
    unresolved = final_report.get("unresolved", [])
    supported = final_report.get("supported_hypotheses", [])
    rejected = final_report.get("rejected", [])
    confirmed = final_report.get("confirmed", [])
    likely = final_report.get("likely", [])
    if supported:
        head = ("Best-supported explanation (recorded evidence only): "
                + (supported[0].get("text") or "")[:300])
    elif unresolved:
        head = ("Inconclusive: no hypothesis met the supported bar. "
                "Leading open explanation: "
                + (unresolved[0].get("text") or "")[:300])
    else:
        head = "Inconclusive: no supported or open hypotheses recorded."
    uncertainties = [
        f"Open: {(u.get('text') or '')[:160]}" for u in unresolved[:10]]
    if not uncertainties:
        uncertainties = ["none recorded; see evidence trail"]
    evidence_ids = [e.get("action_id") for e in
                    final_report.get("evidence_performed", [])
                    if e.get("action_id")]
    # Per-finding evidence, split by state (records only). build_report's
    # unresolved entries carry no evidence_refs, so when a session is
    # available the authoritative hypothesis rows are the source; the
    # report dicts are the offline fallback.
    evidence_source = None
    if session is not None:
        try:
            from ..db import Hypothesis as _H
            _db = session.query(_H).filter(
                _H.investigation_id == getattr(inv, "id", None)).all()
            if _db:
                evidence_source = [
                    {"hypothesis_id": h.id, "text": h.text,
                     "status": h.status,
                     "evidence_refs": h.evidence_refs or []} for h in _db]
        except Exception:
            evidence_source = None
    if evidence_source is not None:
        evidence_for = [{**_hyp_entry(h),
                         "finding_state": h.get("status")} for h in
                        evidence_source]
        _con_pool = evidence_source
    else:
        evidence_for = ([{**_hyp_entry(h), "finding_state": "supported"}
                         for h in supported]
                        + [{**_hyp_entry(h), "finding_state": "unresolved"}
                           for h in unresolved]
                        + [{**_hyp_entry(h), "finding_state": "rejected"}
                           for h in rejected])
        _con_pool = supported + unresolved + rejected
    contradictory = []
    for h in _con_pool:
        for r in (h.get("evidence_refs") or []):
            if isinstance(r, dict) and r.get("relation") == "contradicts":
                contradictory.append(
                    {"hypothesis_id": h.get("hypothesis_id"),
                     "action_id": r.get("action_id"),
                     "tool": r.get("tool")})
    trail = _event_trail(session, getattr(inv, "id", None),
                         ("verification", "resolution", "skeptic"))
    ver_events = [t for t in trail if "verif" in (t["title"] or "").lower()
                  or t["payload"].get("confirmed") is not None]
    independent_verification: dict
    if ver_events:
        last = ver_events[-1]["payload"]
        independent_verification = {
            "performed": True,
            "confirmed": bool(last.get("confirmed")),
            "detail": (ver_events[-1]["title"] or "")[:300]}
    else:
        independent_verification = {
            "performed": False,
            "confirmed": False,
            "detail": "no independent probe was run or recorded"}
    res_events = [t for t in trail
                  if isinstance(t["payload"].get("status"), str)
                  and "resolution" in (t["title"] or "").lower()]
    if res_events:
        final_resolution = {
            "status": res_events[-1]["payload"].get("status"),
            "conclusion": str(res_events[-1]["payload"].get(
                "conclusion") or "")[:500]}
    else:
        final_resolution = {"status": "not recorded",
                            "conclusion": "no resolution contract recorded"}
    skeptic_titles = [t["title"] for t in trail if t not in ver_events
                      and t not in res_events]
    adversarial_outcome: dict
    if skeptic_titles:
        adversarial_outcome = {
            "reviewed": True,
            "notes": [str(t)[:200] for t in skeptic_titles[-5:]]}
    else:
        adversarial_outcome = {
            "reviewed": False,
            "notes": ["no adversarial review recorded"]}
    performed = final_report.get("evidence_performed", [])
    ran = [e for e in performed if e.get("status") == "ran"]
    failed = [e for e in performed if e.get("status") == "failed"]
    budget = final_report.get("budget", {}) if isinstance(
        final_report.get("budget"), dict) else {}
    usage_section: dict = {"budget": budget or "not recorded"}
    tokens = (usage or {}).get("tokens") if isinstance(usage, dict) else None
    if tokens:
        usage_section["tokens"] = tokens
    else:
        usage_section["tokens"] = ("not recorded in this context; "
                                   "see the run usage rollup")
    if isinstance(usage, dict) and usage.get("financial") is not None:
        usage_section["financial"] = usage["financial"]
    else:
        usage_section["financial"] = "not recorded in this context"
    return {
        "schema_version": "m8-v1",
        "kind": "deterministic-fallback",
        "fallback_version": FALLBACK_VERSION,
        "conclusion": head,
        "status_recommendations": [],
        "uncertainties": uncertainties,
        "recommended_next": str(
            (final_report.get("recommended_next") or [{}])[0].get(
                "action", "collect the missing measurements"))[:300],
        "evidence_action_ids": evidence_ids[:50],
        "model_summary_errors": list(errors or [])[:8],
        "provenance": ("composed deterministically from recorded "
                       "hypotheses/actions/report; the investigator's "
                       "invalid response was preserved, not repaired away"),
        # M20 Phase 5 sections (all records-only, gaps explicit).
        "investigation": {
            "investigation_id": getattr(inv, "id", None),
            "mode": getattr(inv, "mode", None),
            "question": (getattr(inv, "question", None) or "")[:500],
            "generated_at": final_report.get("generated_at"),
        },
        "main_findings": [_finding_entry(f) for f in confirmed + likely],
        "confirmed_findings": [_finding_entry(f) for f in confirmed],
        "supported_but_unconfirmed": [
            _hyp_entry(h) for h in supported],
        "rejected_findings": [_hyp_entry(h) for h in rejected],
        "unresolved_hypotheses": [
            {"hypothesis_id": h.get("hypothesis_id"),
             "text": h.get("text"), "status": h.get("status"),
             "origin": h.get("origin")}
            for h in unresolved],
        "evidence_for_each_finding": evidence_for,
        "contradictory_evidence": (contradictory
                                   or "none recorded"),
        "independent_verification": independent_verification,
        "adversarial_outcome": adversarial_outcome,
        "experiment_tool_summary": {
            "ran_count": len(ran),
            "failed_count": len(failed),
            "tools": performed,
        },
        "token_financial_usage": usage_section,
        "limitations": final_report.get("limitations",
                                        ["not recorded"]),
        "final_scientific_resolution": final_resolution,
        "generation_statement": (
            "This report was generated deterministically from recorded "
            "investigation state without model dependence, because the "
            "model's summary output was missing or invalid and bounded "
            "repair did not produce a valid replacement."),
    }
