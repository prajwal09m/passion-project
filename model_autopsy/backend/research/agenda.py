"""Autonomous research agenda (M9 Workstream 2).

The investigator decides what to investigate. Questions are generated
from project-grounded facts (recon + coverage gaps + families) — they
name real columns, segments, and horizons from the artifact, never
generic placeholders. Prioritization is qualitative and documented.
The agenda is durable (inv.config + events) and revises on new
evidence, weakened hypotheses, emerging confounders, and dead ends.
"""
from __future__ import annotations

QUESTION_FAMILIES = (
    "subgroup-performance",
    "distribution-shift",
    "feature-dependence",
    "metric-adequacy",
    "preprocessing-effect",
    "calibration-population",
    "temporal-stability",
    "error-concentration",
)


def knowledge_view(understanding: dict) -> dict:
    """Partition recon output into observed / inferred / missing /
    assumptions. An inference is never presented as an observed fact.
    """
    dataset = understanding.get("dataset") or {}
    observed = {
        "columns": list((understanding.get("receives") or {}).get(
            "columns", [])),
        "readable": bool(dataset.get("readable")),
        "n_rows_peek": dataset.get("n_rows_peek"),
        "null_counts": dict(dataset.get("null_counts") or {}),
        "temporal_hint": dataset.get("temporal_hint"),
        "spec_objective": understanding.get("predicting"),
        "evaluation_methodology": understanding.get("success"),
        "model_availability": ((understanding.get("model") or {}).get(
            "availability")),
    }
    inferred = {
        "has_labels": any(c in observed["columns"]
                          for c in ("label", "target", "y", "grade",
                                    "relevance")),
        "has_scores": any(c in observed["columns"]
                          for c in ("prediction", "score", "pred", "proba")),
        "possible_investigations": list(understanding.get("possible", [])),
        "inconsistencies": list(understanding.get("inconsistencies", [])),
    }
    missing = list(understanding.get("missing", [])) + list(
        understanding.get("impossible", []))
    assumptions = list(understanding.get("evaluation_assumptions", []))
    return {"observed": observed, "inferred": inferred,
            "missing": missing, "assumptions": assumptions,
            "provenance": (understanding.get("provenance") or {})}


def _segments(columns: list[str]) -> list[str]:
    # M14: extended grouping vocabulary (additive; the data-driven
    # fallback in invention.artifact_facts covers names outside it).
    return [c for c in ("region", "slice", "district", "ward",
                        "segment", "fold", "split", "machine",
                        "county", "sensor", "zone", "equipment",
                        "device", "site", "category", "group",
                        "cluster", "cohort", "area")
            if c in columns]


def generate(knowledge: dict, coverage_missing: list[str],
             budget_state: dict | None = None) -> list[dict]:
    """Project-grounded research questions.

    Each question names the concrete artifact facts that motivate it
    and states what measurement would answer it. No fixed catalog:
    families instantiate only when the facts support them.
    """
    obs = knowledge.get("observed", {})
    inf = knowledge.get("inferred", {})
    cols = obs.get("columns") or []
    segs = _segments(cols)
    has_labels = inf.get("has_labels", False)
    has_scores = inf.get("has_scores", False)
    temporal = bool(obs.get("temporal_hint"))
    questions: list[dict] = []

    def add(family: str, text: str, motivates: list[str],
            answers: list[str]) -> None:
        questions.append({"id": family + ":" + str(len(questions)),
                          "family": family, "text": text,
                          "motivated_by": motivates,
                          "answered_by": answers, "status": "open",
                          "priority_reason": ""})

    if segs and has_labels and has_scores:
        add("subgroup-performance",
            f"Does model performance differ across {segs[0]} values, and "
            f"does the pooled metric hide a failing segment?",
            [f"segment column observed: {segs[0]}",
             "labels and scores observed"],
            [f"per-{segs[0]} metric comparison",
             "pooled-vs-segmented gap"])
    if temporal:
        hint = obs.get("temporal_hint") or {}
        add("temporal-stability",
            "Is performance stable over time, or does error concentrate "
            "in a recent period (drift, regime change, or split artifact)?",
            [f"temporal column observed: "
             f"{hint.get('column', 'date-like')}"],
            ["changepoint scan", "early-vs-late error comparison",
             "split chronology check"])
    if has_labels and has_scores:
        add("feature-dependence",
            "Does model error depend excessively on a particular input, "
            "suggesting stale/lagged features or a schema-handling fault?",
            ["numeric feature columns observed: "
             + ", ".join([c for c in cols
                           if c not in ("label", "target", "score",
                                        "prediction")][:6]) or "none"],
            ["residual-feature dependence screen",
             "grouped error comparison"])
    if has_labels and has_scores:
        add("metric-adequacy",
            "Is the reported pooled metric adequate, or does it mask a "
            "concentrated failure the evaluation methodology misses?",
            [f"evaluation methodology: {obs.get('evaluation_methodology')}",
             f"segments available: {segs or 'none'}"],
            ["segmented recomputation of the headline metric"])
    if any("schema" in (m or "").lower() or "pipeline" in (m or "").lower()
           for m in [obs.get("spec_objective")]):
        add("preprocessing-effect",
            "Did a pipeline or schema change alter the inputs for some "
            "rows, and can before/after rows be compared?",
            ["objective mentions a pipeline/schema change"],
            ["unaffected-row comparison", "temporal alignment"])
    if has_labels and has_scores:
        add("calibration-population",
            "Is the model calibrated where it matters, and does "
            "calibration differ across populations?",
            ["labels and scores observed",
             f"segments available: {segs or 'none'}"],
            ["reliability analysis", "per-segment calibration"])
    if coverage_missing:
        add("error-concentration",
            "Unresolved measurements remain: "
            + ", ".join(coverage_missing[:4])
            + ". Which open question does each answer?",
            ["diagnostic coverage gaps"],
            coverage_missing[:4])
    return questions


PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def prioritize(questions: list[dict], state: dict) -> list[dict]:
    """Rank questions; every rank carries its reason.

    Signals (qualitative): evidence availability, uncertainty,
    discriminating power between live hypotheses, feasibility within
    remaining budget. Costly or infeasible questions sink with reasons.
    """
    budget_left = int((state.get("budget_left") or {}).get(
        "experiments", 0)) if isinstance(state.get("budget_left"),
                                         dict) else 0
    n_open_h = len(state.get("open_hypotheses") or [])
    ranked = []
    for q in questions:
        if q.get("status") != "open":
            continue
        fam = q.get("family", "")
        if fam in ("subgroup-performance", "metric-adequacy") and \
                state.get("segments"):
            pri, why = "high", ("segments observed and pooled metrics "
                                "can hide concentrated failure")
        elif fam == "temporal-stability" and state.get("temporal"):
            pri, why = "high", "temporal column observed; drift vs split " \
                                 "artifact is highly discriminating"
        elif fam == "preprocessing-effect":
            pri, why = "high", ("a pipeline/schema change is a known "
                                "confounder until ruled out")
        elif fam == "error-concentration":
            pri, why = "medium", "answers named coverage gaps"
        else:
            pri, why = "medium", "feasible diagnostic exists"
        if budget_left and budget_left <= 1 and pri == "high":
            pri, why = "medium", why + "; budget nearly exhausted, " \
                       "cheapest discriminating test first"
        ranked.append({**q, "priority": pri, "priority_reason": why})
    ranked.sort(key=lambda r: (PRIORITY_ORDER[r["priority"]],
                               r["family"]))
    return ranked


def save(session, inv, questions: list[dict], event: str) -> dict:
    """Persist the agenda durably (config + timeline event)."""
    from ..db import record_event
    agenda = {"questions": questions,
              "revised_at": __import__("datetime").datetime.now(
                  __import__("datetime").timezone.utc).isoformat()}
    inv.config = {**(inv.config or {}), "research_agenda": agenda}
    session.commit()
    record_event(session, inv.id, "agenda", event,
                 payload={"n_questions": len(questions),
                          "open": sum(1 for q in questions
                                      if q.get("status") == "open"),
                          "families": sorted({q.get("family", "?")
                                              for q in questions})})
    session.commit()
    return agenda


def load(inv) -> list[dict]:
    return list(((inv.config or {}).get("research_agenda") or {}).get(
        "questions", []))


def detect_pivot(hypotheses_before: list[dict],
                 hypotheses_after: list[dict]) -> dict | None:
    """M13A.4: did evidence overturn the leading explanation?

    Compares moving-support counts before/after a measurement. A pivot
    is recorded when the previous leader lost its lead to a rival —
    the planner must then change direction, not defend the old lead.
    Returns None when no lead change occurred (common case)."""
    def lead(hyps):
        scored = []
        for h in hyps:
            refs = h.get("evidence_refs") or []
            sup = sum(1 for r in refs
                      if r.get("relation") == "supports")
            con = sum(1 for r in refs
                      if r.get("relation") == "contradicts")
            scored.append((sup - con, h.get("id")))
        scored.sort(reverse=True)
        return scored[0][1] if scored else None
    before, after = lead(hypotheses_before), lead(hypotheses_after)
    if before and after and before != after:
        return {"from": before, "to": after,
                "note": "leading explanation overturned by new "
                "evidence; rival lines take priority"}
    return None


def revise_on_evidence(session, inv, hypotheses: list[dict],
                       confounders: dict) -> dict:
    """Abandon answered/weakened lines, open confounder-driven ones."""
    from . import agenda as _self  # noqa: F401 (explicit re-export guard)
    questions = load(inv)
    changed = False
    h_by_text = {h.get("id"): h for h in hypotheses}
    for q in questions:
        if q.get("status") != "open":
            continue
        # A question whose linked hypotheses all resolved is answered.
        linked = [h for hid, h in h_by_text.items()
                  if hid in (q.get("hypothesis_ids") or [])]
        if linked and all(h.get("status") in ("supported", "rejected",
                                              "inconclusive")
                          for h in linked):
            q["status"] = "answered"
            q["resolution"] = ("all linked hypotheses resolved; see "
                               "hypothesis records")
            changed = True
    pivot = detect_pivot(getattr(inv, "_prev_hviews", None) or [],
                         hypotheses)
    inv._prev_hviews = [dict(h) for h in hypotheses]  # transient only
    if pivot:
        from ..db import record_event as _record
        _record(session, inv.id, "agenda",
                f"Research pivot: lead moved {pivot['from'][:8]} → "
                f"{pivot['to'][:8]}; rival lines prioritized",
                payload={"pivot": pivot})
        for q in questions:
            if q.get("status") == "open":
                q["priority_reason"] = (q.get("priority_reason", "")
                                         + "; pivot: rival explanations "
                                         "lead, re-ranked").strip("; ")
        changed = True
    if confounders.get("needs_discrimination") and not any(
            q.get("family") == "confounder-discrimination"
            and q.get("status") == "open" for q in questions):
        questions.append({
            "id": f"confounder-discrimination:{len(questions)}",
            "family": "confounder-discrimination",
            "text": ("One observation supports two different mechanisms; "
                     "which discriminating measurement separates them?"),
            "motivated_by": ["shared-evidence analysis flagged "
                             "common-cause candidates"],
            "answered_by": ["run the proposed discriminating measurement",
                            "re-attribute the shared evidence"],
            "status": "open", "priority": "high",
            "priority_reason": "confounded evidence cannot support any "
                               "conclusion until separated"})
        changed = True
    if changed:
        save(session, inv, questions,
             "Agenda revised on evidence/confounders")
    return {"questions": questions, "changed": changed}
