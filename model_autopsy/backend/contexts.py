"""Project-independent context packages (Phase 8).

A context package carries identity, state, and EVIDENCE REFERENCES (action
ids) instead of repeated full outputs. Full sends everything; Delta sends
only what changed since the provider-retained history. Strategy choice is
explicit and measured — never assumed cheaper.
"""
from __future__ import annotations

from . import db


def build_context_package(session, inv, project_brief: str = "",
                          capabilities: list | None = None) -> dict:
    """Full package: identity + objective + state + references (no blobs)."""
    from . import engine
    from .db import Action, Hypothesis
    actions = (session.query(Action)
               .filter(Action.investigation_id == inv.id)
               .order_by(Action.seq.asc()).all())
    hyps = (session.query(Hypothesis)
            .filter(Hypothesis.investigation_id == inv.id).all())
    return {
        "package_version": "v1",
        "project": {"mode": inv.mode,
                    "objective": inv.question,
                    "brief": project_brief,
                    "capabilities": list(capabilities or [])},
        "state": {"status": inv.status,
                  "tool_calls_used": inv.tool_call_count,
                  "max_tool_calls": inv.max_tool_calls,
                  "iterations_used": inv.iteration_count,
                  "max_iterations": inv.max_iterations},
        "hypotheses": [{"id": h.id, "status": h.status,
                        "text": h.text[:200]} for h in hyps],
        "findings": [{"status": f.get("status"),
                      "summary": str(f.get("summary"))[:220],
                      "evidence_action_id": f.get("evidence_action_id")}
                     for f in (inv.latest_findings or [])],
        # References only: full outputs stay in durable records.
        "evidence_refs": [{"action_id": a.id, "seq": a.seq,
                           "tool": a.tool_name, "status": a.status}
                          for a in actions],
        "unresolved": [h.text[:160] for h in hyps
                       if h.status in ("proposed", "investigating",
                                       "inconclusive")]}


def build_delta_package(session, inv, previous_package: dict,
                        project_brief: str = "") -> dict:
    """Delta package: only entries newer than the previous package."""
    full = build_context_package(session, inv, project_brief)
    prev_refs = {r.get("action_id") for r in
                 (previous_package.get("evidence_refs") or [])}
    prev_hyps = {h.get("id"): h.get("status") for h in
                 (previous_package.get("hypotheses") or [])}
    return {
        "package_version": "v1",
        "strategy": "delta",
        "project": full["project"],
        "state": full["state"],
        "hypotheses": [h for h in full["hypotheses"]
                       if prev_hyps.get(h["id"]) != h["status"]
                       or h["id"] not in prev_hyps],
        "findings": full["findings"][len(previous_package.get("findings") or []):],
        "evidence_refs": [r for r in full["evidence_refs"]
                          if r["action_id"] not in prev_refs],
        "unresolved": full["unresolved"],
        "context_source": ("retained server-side history; delta only; full "
                           "outputs remain in durable records by action id")}


def package_delta_savings(full: dict, delta: dict) -> dict:
    """Honest size comparison of two packages (chars, not billed tokens)."""
    import json
    f = len(json.dumps(full, sort_keys=True, default=str))
    d = len(json.dumps(delta, sort_keys=True, default=str))
    return {"full_chars": f, "delta_chars": d,
            "reduction_pct": round(100 * (f - d) / f, 1) if f else 0.0,
            "note": "character size is a proxy; billed savings must be "
                    "measured from provider usage, per project"}
