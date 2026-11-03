"""M15 Phase 2: scientific-resolution engine (offline, deterministic).

Replaces generic "inconclusive" with 1 of 13 evidence-derived
classes, runs the mandatory A–H resolution procedure, and emits a
resolution contract with 1 of 6 distinct final statuses. Never
relabels unresolved work as confirmed.
"""
from __future__ import annotations

CLASSES = (
    "insufficient-observations",
    "insufficient-diagnostic-coverage",
    "weak-hypothesis",
    "poorly-discriminating-experiment",
    "experiment-execution-failure",
    "contradictory-evidence",
    "confounding",
    "mechanism-not-identifiable",
    "reproduction-failure",
    "verified-null",
    "multiple-explanations",
    "technical-defect",
    "reasoning-failure",
)

STATUSES = ("confirmed", "strongly-supported", "falsified",
            "verified-null", "partially-resolved", "unresolved")


def diagnose(hypotheses: list[dict], actions: list[dict],
             coverage_gaps: list[dict] | None = None,
             verifications: list[dict] | None = None) -> dict:
    """Evidence-derived classification of why resolution failed."""
    moving = [r for h in hypotheses for r in (h.get("evidence_refs")
                                              or [])
              if r.get("relation") in ("supports", "contradicts")]
    failed = [a for a in actions if a.get("status") != "ran"]
    sup = sum(1 for r in moving if r.get("relation") == "supports")
    con = sum(1 for r in moving if r.get("relation") == "contradicts")
    if failed and not moving:
        return {"class": "experiment-execution-failure",
                "why": f"{len(failed)} executed actions failed; no "
                       "moving evidence exists",
                "evidence": [a.get("tool") for a in failed]}
    n_obs = sum(a.get("n", 0) for a in actions if a.get("n")) or None
    if n_obs is not None and n_obs < 100 and not moving:
        return {"class": "insufficient-observations",
                "why": f"only ~{n_obs} observations behind measurements",
                "evidence": []}
    if con > 0 and sup > 0:
        return {"class": "contradictory-evidence",
                "why": f"{sup} supporting vs {con} contradicting "
                       "moving refs across hypotheses",
                "evidence": []}
    if (verifications and
            all(v.get("grade") in ("not-reproduced", "impossible")
                for v in verifications) and sup > 0):
        return {"class": "reproduction-failure",
                "why": "moving evidence exists but no independent "
                       "probe reproduces it",
                "evidence": [v.get("grade") for v in verifications]}
    naming = [h for h in hypotheses if h.get("names_mechanism")]
    if not naming and not moving:
        return {"class": "weak-hypothesis",
                "why": "no hypothesis names a mechanism with evidence",
                "evidence": []}
    gaps = coverage_gaps or []
    if gaps and not moving:
        return {"class": "insufficient-diagnostic-coverage",
                "why": f"unmeasured dimensions: "
                       f"{[g.get('dimension') for g in gaps[:3]]}",
                "evidence": []}
    supported = [h for h in hypotheses
                 if h.get("status") == "supported"]
    if len(supported) >= 2:
        return {"class": "multiple-explanations",
                "why": f"{len(supported)} hypotheses supported; no "
                       "discriminating experiment separated them",
                "evidence": []}
    if not moving and not failed:
        return {"class": "poorly-discriminating-experiment",
                "why": "experiments ran but produced no moving "
                       "evidence; outcomes could not change beliefs",
                "evidence": [a.get("tool") for a in actions]}
    return {"class": "mechanism-not-identifiable",
            "why": "evidence exists but cannot isolate a mechanism "
                   "with available data",
            "evidence": []}


def next_experiment(diagnosis: dict, facts: dict,
                    ran: list[dict]) -> dict:
    """Step C: propose the discriminating follow-up (or say why not)."""
    cls = diagnosis.get("class", "")
    if cls == "experiment-execution-failure":
        return {"action": "fix-and-rerun",
                "detail": "repair the failed tool arguments (e.g. "
                          "column aliases) and rerun once; do not "
                          "repeat blindly",
                "tool": None}
    if cls in ("insufficient-diagnostic-coverage",
               "poorly-discriminating-experiment",
               "contradictory-evidence",
               "multiple-explanations"):
        return {"action": "discriminate",
                "detail": "run one experiment whose possible outcomes "
                          "separate the leading explanations; rank by "
                          "expected belief change per cost",
                "tool": "see invention ranking"}
    if cls == "insufficient-observations":
        return {"action": "blocked",
                "detail": "no discriminating experiment is justified "
                          "below adequate sample size; report bound",
                "tool": None}
    return {"action": "bound",
            "detail": f"class {cls}: state the precise limit and stop",
            "tool": None}


def collect_transitions(session, inv_id: str) -> list[dict]:
    """M18 Phase 3: genuine hypothesis status transitions as events.

    Reads durable records (Hypothesis.revisions + kind=`hypothesis`
    events with from/to payloads). Snapshot views (current status +
    evidence counts) are NOT transitions. Each transition carries the
    investigation/hypothesis ids, previous/new status, timestamp or
    sequence, triggering evidence reference, triggering action, and
    actor where recorded. Returns [] when nothing ever advanced.
    """
    from ..db import Hypothesis, Event
    out: list[dict] = []
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv_id).all()
    by_id = {h.id: h for h in hyps}
    # Primary source: per-hypothesis revision log (from/to/at).
    for h in hyps:
        for i, rev in enumerate(h.revisions or []):
            try:
                frm = rev.get("from")
                to = rev.get("to")
            except AttributeError:
                continue
            if not frm or not to or frm == to:
                continue
            out.append({"investigation_id": inv_id,
                        "hypothesis_id": h.id,
                        "hypothesis": (h.text or "")[:80],
                        "from": frm, "to": to,
                        "at": rev.get("at"), "seq": i,
                        "trigger": "evidence update",
                        "actor": "backend"})
    # Enrich with triggering evidence/action where the matching event
    # recorded it (update_hypothesis payload: from{status}, action ids
    # in rationale/links). Creation events (no from) are not transitions.
    try:
        evs = session.query(Event).filter(
            Event.investigation_id == inv_id,
            Event.kind == "hypothesis").order_by(Event.id.asc()).all()
    except Exception:
        evs = []
    _used = 0
    for e in evs:
        p = e.payload or {}
        hid = p.get("hypothesis_id")
        frm = (p.get("from") or {}).get("status") if isinstance(
            p.get("from"), dict) else p.get("from")
        to = p.get("status")
        if not hid or hid not in by_id or not frm or not to or frm == to:
            continue
        # Attach evidence/action context to the matching revision entry.
        for t in out:
            if t["hypothesis_id"] == hid and t["from"] == frm \
                    and t["to"] == to and "event_id" not in t:
                t["event_id"] = e.id
                t["title"] = (e.title or "")[:160]
                if p.get("action_id"):
                    t["evidence_action_id"] = p["action_id"]
                _used += 1
                break
    return out


def contract(question: str, hypotheses: list[dict],
             experiments: list[dict], failed: list[dict],
             transitions: list[dict], competing: list[str],
             contradictions: list[str], conclusion: str,
             confidence: dict, verification: dict,
             uncertainty: str, limit: str) -> dict:
    sup = [h for h in hypotheses if h.get("status") == "supported"]
    rej = [h for h in hypotheses if h.get("status") == "rejected"]
    moving = [r for h in hypotheses for r in (h.get("evidence_refs")
                                              or [])
              if r.get("relation") in ("supports", "contradicts")]
    if conclusion.startswith("CONFIRMED"):
        status = "confirmed"
    elif conclusion.startswith("FALSIFIED"):
        status = "falsified"
    elif conclusion.startswith("NULL"):
        status = "verified-null"
    elif sup and not competing:
        status = "strongly-supported"
    elif sup or rej or any(
            (t.get("to") in ("supported", "rejected"))
            for t in (transitions or []) if isinstance(t, dict)):
        # M18 Phase 3: partially-resolved requires a REAL advancement
        # (some hypothesis reached supported/rejected). Evidence attached
        # to still-investigating hypotheses is "collected but unresolved",
        # not partial resolution — the M17 snapshot bug counted mere
        # evidence presence as progress.
        status = "partially-resolved"
    else:
        status = "unresolved"
    assert status in STATUSES
    return {
        "question": question,
        "initial_hypotheses": [h.get("text", "")[:160]
                               for h in hypotheses],
        "evidence_gathered": len(moving),
        "experiments": experiments,
        "failed_or_skipped": failed,
        "hypothesis_changes": transitions,
        "competing_explanations": competing,
        "contradictory_evidence": contradictions,
        "conclusion": conclusion,
        "confidence": confidence,
        "verification": verification,
        "uncertainty": uncertainty,
        "resolution_limit": limit,
        "status": status,
        "note": "unresolved is never relabeled confirmed",
    }
