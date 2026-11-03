"""Advanced hypothesis management (M6 Part 2A).

Every hypothesis keeps: unique id, explanation (text), expected observable
consequences (predicted_observation + expected_consequences JSON),
supporting / contradicting evidence (evidence_refs with relation),
missing evidence (missing_evidence JSON), discriminating experiments,
confidence (uncalibrated model note unless updated by evidence),
status (proposed/investigating/supported/rejected/inconclusive/blocked),
and explicit justification for every status change (revisions + status_justification).

What this establishes: structured competition between explanations with
auditable transitions. What it does not establish: truth — statuses are
evidence grades, not causal proof (see diagnosis.py).
"""
from __future__ import annotations

import re

VALID_STATUSES = ("proposed", "investigating", "supported", "rejected",
                  "inconclusive", "blocked")

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def normalize(text: str) -> str:
    return " ".join(sorted(_tokens(text)))


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def is_duplicate(a: str, b: str, threshold: float = 0.72) -> bool:
    """Qualitative duplicate check (Jaccard over tokens), not a number claim."""
    return similarity(a, b) >= threshold


_OPPOSITIONS = [
    ({"drift", "shift", "change", "growth"}, {"no", "absent", "clean", "stable", "artifact"}),
    ({"leak", "leakage", "overlap"}, {"no", "clean", "chronological"}),
    ({"bias", "misspecif"}, {"drift", "shift"}),
]


def relation(a: str, b: str) -> str:
    """One of: duplicate | contradicts | compatible.

    Qualitative only: duplicates share most tokens; contradicts match a
    known opposition pattern or explicit negation; otherwise compatible
    (could both be true, e.g. drift + misspecification).
    """
    if is_duplicate(a, b):
        return "duplicate"
    ta, tb = _tokens(a), _tokens(b)
    joined = ta | tb
    neg = {"not", "no", "never", "artifact", "instead", "rather", "rules", "contradicts"}
    if (ta & neg) ^ (tb & neg) and len(ta & tb) >= 3:
        return "contradicts"
    for pos, negset in _OPPOSITIONS:
        if (ta & pos and tb & negset) or (tb & pos and ta & negset):
            if len(ta & tb) >= 2:
                return "contradicts"
    # Explicit mechanism opposition: drift vs split-hygiene vs persistent misspec.
    families = [
        {"drift", "shift", "level", "regime", "growth"},
        {"split", "overlap", "leakage", "hygiene", "chronological"},
        {"misspecification", "misspecified", "persistent", "throughout", "autocorrelated"},
    ]
    hit_a = [i for i, f in enumerate(families) if ta & f]
    hit_b = [i for i, f in enumerate(families) if tb & f]
    if hit_a and hit_b and not (set(hit_a) & set(hit_b)) and len((ta & tb)) <= 4:
        # Different mechanism families with little overlap: competing.
        return "contradicts"
    return "compatible"


def analyze_competition(hypotheses: list[dict]) -> dict:
    """Pairwise competition map over hypothesis dicts with id/text."""
    pairs = []
    for i in range(len(hypotheses)):
        for j in range(i + 1, len(hypotheses)):
            a, b = hypotheses[i], hypotheses[j]
            rel = relation(a.get("text", ""), b.get("text", ""))
            pairs.append({"a": a.get("id"), "b": b.get("id"), "relation": rel})
    return {"pairs": pairs,
            "duplicates": [p for p in pairs if p["relation"] == "duplicate"],
            "contradictions": [p for p in pairs if p["relation"] == "contradicts"]}


def confidence_step(current: int | None, direction: str) -> int:
    """Qualitative evidence-graded confidence (not a probability).

    support: +15 capped at 90 (never 100 — proof needs diagnosis gate).
    contradict: -25 floored at 5. Corroboration is bounded so a single
    diagnostic cannot establish a cause.
    """
    base = 40 if current is None else int(current)
    if direction == "supports":
        return min(90, base + 15)
    if direction == "contradicts":
        return max(5, base - 25)
    return base


def next_status_on_evidence(status: str, direction: str, n_contradict: int = 0) -> tuple[str, str]:
    """Recommend the next status after one linked evidence item.

    Rules (discipline, not automation — caller records justification):
    - 2+ contradicting items, or 1 strong contradiction of the core
      prediction → rejected.
    - 1 contradiction → investigating (demoted, not rescued by narrative).
    - 2+ supports and no contradiction → supported.
    - else investigating.
    Rejected/support require cited action ids (enforced by caller).
    """
    if direction == "contradicts" and n_contradict >= 1:
        # Second contradiction (or caller passes cumulative count>=2) rejects.
        if n_contradict >= 2 or status in ("investigating", "supported"):
            return "rejected", "core prediction contradicted by recorded evidence"
        return "investigating", "contradictory evidence recorded; hypothesis demoted"
    if direction == "supports":
        if status == "supported":
            return "supported", "further corroboration recorded"
        return "investigating", "supporting evidence recorded; needs independent corroboration"
    return status, "no change"


def update_with_evidence(session, hypothesis_id: str, action_id: str,
                         direction: str, justification: str) -> dict:
    """Link evidence + revise confidence + recommend status, atomically.

    Never fabricates: both ids must exist in the same investigation;
    direction must be supports/contradicts; justification required.
    Returns the updated hypothesis view for the audit trail.
    """
    from .. import engine
    from ..db import Hypothesis
    if direction not in ("supports", "contradicts"):
        raise ValueError("direction must be 'supports' or 'contradicts'")
    if not (justification or "").strip():
        raise ValueError("justification is required for evidence updates")
    h = session.get(Hypothesis, hypothesis_id)
    if h is None:
        raise LookupError("hypothesis not found")
    linked = engine.link_evidence(session, hypothesis_id, action_id, direction)
    refs = linked.get("evidence_refs") or []
    # M13 §6: corroboration requires INDEPENDENT measurements.
    # Two refs from the same tool (e.g. one reliability curve at
    # two bin resolutions) are one observation, not corroboration.
    # Count distinct tools per direction; same-tool repeats still
    # record (visible) but never promote on their own.
    tools_for = lambda rel: {r.get("tool") or "?" for r in refs
                             if r.get("relation") == rel}
    n_con = len(tools_for("contradicts"))
    n_sup = len(tools_for("supports"))
    raw_con = sum(1 for r in refs if r.get("relation") == "contradicts")
    raw_sup = sum(1 for r in refs if r.get("relation") == "supports")
    new_conf = confidence_step(h.confidence, direction)
    # M17 Phase 3: the skeptic gate. A falsification test answers an
    # open challenge; advancement to supported waits for that answer.
    from ..db import Investigation as _INV_T
    from ..live import skeptic as _SK
    _inv = session.get(_INV_T, h.investigation_id)
    if direction == "contradicts" and _inv is not None:
        _SK.mark_answered(session, _inv, hypothesis_id,
                          "falsification tested")
        _inv = session.get(_INV_T, h.investigation_id)
    _gate_open = (_inv is not None and direction == "supports"
                   and bool(_SK.blocking_open(session, _inv,
                                               hypothesis_id)))
    if direction == "contradicts" and n_con >= 2:
        new_status, why = "rejected", ("two independent contradicting "
                                        "measurements recorded")
    elif direction == "contradicts":
        new_status, why = ("investigating", "contradictory evidence recorded; demoted")
        if h.status in ("supported",):
            new_status, why = "rejected", "core prediction contradicted by recorded evidence"
    elif direction == "supports" and n_sup >= 2 and n_con == 0:
        if _gate_open:
            new_status, why = ("investigating", "two independent "
                               "supports recorded but an unanswered "
                               "skeptic challenge must be resolved first")
        else:
            new_status, why = "supported", ("two independent supporting "
                                            "measurements, no contradiction")
    else:
        extra = "" if raw_sup <= n_sup else \
            f" ({raw_sup - n_sup} same-tool repeat(s) recorded, " \
            "not independent corroboration)"
        new_status, why = ("investigating", "supporting evidence recorded; needs independent corroboration" + extra)
        if h.status in ("supported",):
            new_status, why = h.status, "further corroboration recorded"
    full_just = f"{justification.strip()} [{why}; action {action_id}]"
    out = engine.update_hypothesis(session, hypothesis_id, new_status,
                                   confidence=new_conf, rationale=full_just)
    # Persist explicit justification + missing-evidence pointer.
    h2 = session.get(Hypothesis, hypothesis_id)
    h2.status_justification = full_just  # type: ignore[attr-defined]
    session.commit()
    return {"id": hypothesis_id, "status": out["status"],
            "confidence": out["confidence"], "justification": full_just,
            "supports": n_sup, "contradicts": n_con,
            "independent_tools": True}
