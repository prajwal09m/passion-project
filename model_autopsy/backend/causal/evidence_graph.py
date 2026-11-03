"""Evidence graph and provenance (M6 Part 2D).

Connects project observations → anomalies → hypotheses → experiments →
diagnostic results → evidence → confidence updates → conclusions.
Every conclusion traces to recorded action ids. Never manufactures
evidence: nodes come only from session rows (hypotheses, actions,
events, findings, report).

Answers: why believed, which experiment, what contradicts, which
alternatives remain, what would establish the cause.
"""
from __future__ import annotations


def build_graph(session, investigation_id: str) -> dict:
    from ..db import Action, Event, Hypothesis
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == investigation_id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == investigation_id).order_by(Action.seq).all()
    nodes: list[dict] = []
    edges: list[dict] = []
    for h in hyps:
        nodes.append({"id": f"hyp:{h.id}", "kind": "hypothesis",
                      "label": h.text[:120], "status": h.status,
                      "confidence": h.confidence})
        for r in (h.evidence_refs or []):
            aid = r.get("action_id")
            if aid:
                edges.append({"from": f"exp:{aid}", "to": f"hyp:{h.id}",
                              "relation": r.get("relation", "supports")})
    for a in acts:
        nodes.append({"id": f"exp:{a.id}", "kind": "experiment",
                      "label": f"{a.tool_name} #{a.seq}", "status": a.status})
    return {"nodes": nodes, "edges": edges,
            "counts": {"hypotheses": len(hyps), "experiments": len(acts)}}


def trace_conclusion(session, investigation_id: str,
                     hypothesis_id: str) -> dict:
    """Why believed / what contradicts / alternatives / what is needed."""
    from ..db import Action, Hypothesis
    h = session.get(Hypothesis, hypothesis_id)
    if h is None or h.investigation_id != investigation_id:
        raise LookupError("hypothesis not found in this investigation")
    refs = list(h.evidence_refs or [])
    supports = [r for r in refs if r.get("relation") == "supports"]
    contradicts = [r for r in refs if r.get("relation") == "contradicts"]
    others = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == investigation_id,
        Hypothesis.id != hypothesis_id).all()
    alternatives = [{"id": o.id, "text": o.text[:140], "status": o.status}
                    for o in others if o.status not in ("rejected",)]
    needs = []
    if h.status in ("proposed", "investigating"):
        needs.append("independent corroborating diagnostic with a distinct method")
    if not supports:
        needs.append("at least one supporting experiment with recorded action id")
    if h.status != "rejected" and not contradicts:
        needs.append("an explicit falsification attempt (a test that could reject it)")
    return {"hypothesis": {"id": h.id, "text": h.text, "status": h.status,
                           "confidence": h.confidence,
                           "justification": getattr(h, "status_justification", None)},
            "why_believed": supports,
            "what_contradicts": contradicts,
            "alternatives_remaining": alternatives,
            "what_would_establish": needs or ["already meets supported bar; see diagnosis gate"]}
