"""M11 research-team roles (offline, deterministic).

Six roles with explicit contracts. Each role receives ONLY the
inputs its job needs — agents never share full internal state:

- lead: agenda + assignments (owns what is pursued, not conclusions).
- data_scientist: schema/hygiene brief from artifact facts.
- model_analyst: error brief from executed action results.
- experiment_designer: discriminating specs via invention.propose.
- skeptic: challenges against hypotheses + evidence (can block).
- judge: INDEPENDENT verdicts from hypotheses + evidence only —
  its signature excludes lead/designer outputs by construction.

No provider, no randomness: the same evidence always yields the
same briefs, challenges, and verdicts.
"""
from __future__ import annotations


def lead(questions: list[dict], hypotheses: list[dict],
         budget_left: int) -> dict:
    """Own the agenda: order open questions, assign roles, cap scope."""
    open_q = [q for q in questions if q.get("status") == "open"]
    order = {"high": 0, "medium": 1, "low": 2}
    ranked = sorted(open_q, key=lambda q: (
        order.get(q.get("priority", "medium"), 1), q.get("family", "")))
    plan = [{"question_id": q.get("id"),
             "assignee": ("model_analyst"
                          if q.get("family") in (
                              "temporal-stability", "metric-adequacy")
                          else "data_scientist"),
             "priority": q.get("priority")} for q in ranked]
    return {"assignments": plan[:max(budget_left, 0)],
            "deferred": [q.get("id") for q in ranked][max(
                budget_left, 0):],
            "rationale": f"{len(plan)} questions assigned within "
                         f"budget {budget_left}; remainder deferred, "
                         f"not dropped"}


def data_scientist(facts: dict) -> dict:
    """Dataset structure, missingness, subgroup and temporal shape."""
    cols = facts.get("columns") or []
    return {"role": "data_scientist",
            "n_columns": len(cols),
            "segments": facts.get("segments", []),
            "temporal": facts.get("temporal_col"),
            "split": facts.get("split_col"),
            "score_col": facts.get("score_col"),
            "label_col": facts.get("label_col"),
            "readable": facts.get("readable", False),
            "limitations": ["peek is 2000 rows; full-frame stats "
                            "come from executed tools, not this brief"]}


def model_analyst(actions: list[dict]) -> dict:
    """Error brief: what executed measurements actually show."""
    brief = []
    for a in actions:
        res = a.get("result") or {}
        brief.append({"tool": a.get("tool"),
                      "establishes": res.get("establishes"),
                      "does_not_establish": res.get(
                          "does_not_establish"),
                      "keys": sorted([k for k in res
                                      if k not in (
                                          "ok", "establishes",
                                          "does_not_establish")])[:8]})
    return {"role": "model_analyst", "measurements": brief,
            "limitations": ["tools establish facts, never causes; "
                            "causation needs competing-hypothesis "
                            "tests"]}


def experiment_designer(question: dict, hypotheses: list[dict],
                        facts: dict, ran: list[dict],
                        budget_left: dict | None = None) -> dict:
    """Propose the most discriminating affordable spec (M9 inventor)."""
    from ..research import invention as INV
    cands = INV.propose(question, hypotheses, facts, ran,
                        budget_left or {"experiments": 1})
    if not cands:
        return {"role": "experiment_designer", "spec": None,
                "reason": "nothing discriminating and affordable"}
    return {"role": "experiment_designer", "spec": cands[0],
            "alternatives": len(cands) - 1,
            "reason": cands[0].get("distinguishes", "")}


def skeptic(hypotheses: list[dict], actions: list[dict]) -> dict:
    """Challenge conclusions. Returns blocking challenges + falsifiers.

    Challenge types: unsupported-support (supported/comfortable
    status with <2 moving supports), confounder-ignored (a supported
    segment claim with no composition check), missing-falsification
    (leading hypothesis never contradicted-tested).
    """
    by_action = {a.get("id"): a for a in actions}
    challenges = []
    for h in hypotheses:
        refs = h.get("evidence_refs") or []
        moving_sup = [r for r in refs
                      if r.get("relation") == "supports"]
        moving_con = [r for r in refs
                      if r.get("relation") == "contradicts"]
        tools = {(by_action.get(r.get("action_id")) or {}).get("tool")
                 for r in refs}
        tools.discard(None)
        if h.get("status") == "supported" and len(moving_sup) < 2:
            challenges.append({
                "type": "unsupported-support",
                "hypothesis_id": h.get("id"),
                "blocks": True,
                "detail": f"status=supported with only "
                          f"{len(moving_sup)} moving supports; "
                          f"corroboration unattested",
                "proposed_test": "run an independent second probe "
                                 "of the same mechanism"})
        text = (h.get("text") or "").lower()
        if (any(w in text for w in ("segment", "ward", "district",
                                    "subgroup", "slice", "across"))
                and h.get("status") in ("supported", "investigating")
                and not any("confound" in str(
                    (by_action.get(r.get("action_id")) or {}).get(
                        "tool", "")) for r in refs)):
            challenges.append({
                "type": "confounder-ignored",
                "hypothesis_id": h.get("id"),
                "blocks": False,
                "detail": "segment claim without a composition/ "
                          "prevalence check on record",
                "proposed_test": "prevalence-aware recomputation or "
                                 "confounder screen"})
        if moving_sup and not moving_con and h.get("status") in (
                "supported", "investigating"):
            # M17: actionable — a leading explanation that was never
            # contradiction-tested blocks advancement until a falsifying
            # probe runs (or dissent is preserved). Once per hypothesis
            # (dedupe lives in live/skeptic.review).
            challenges.append({
                "type": "missing-falsification",
                "hypothesis_id": h.get("id"),
                "blocks": True,
                "detail": "leading explanation never survived a "
                          "contradiction test",
                "proposed_test": "run the strongest rival "
                                 "mechanism's discriminating probe"})
        if moving_sup and moving_con and h.get("status") in (
                "supported", "investigating"):
            # M17: contradictory evidence on record blocks advancement
            # until a discriminating probe separates the rivals.
            challenges.append({
                "type": "contradictory-evidence",
                "hypothesis_id": h.get("id"),
                "blocks": True,
                "detail": "supporting and contradicting measurements "
                          "coexist; rivals undiscriminated",
                "proposed_test": "run a discriminating probe that "
                                 "separates the rival mechanisms"})
    return {"role": "skeptic", "challenges": challenges,
            "blocking": [c for c in challenges if c.get("blocks")],
            "limitations": ["challenges are heuristic screens, not "
                            "proofs; evidence decides"]}


def judge(hypotheses: list[dict]) -> dict:
    """Independent verdicts from hypotheses + recorded evidence ONLY.

    The signature takes no lead/designer/skeptic outputs: agreement
    with the lead is coincidence-or-evidence, never copying. A
    verdict is upheld only with >=1 moving evidence ref; otherwise
    the judge downgrades to investigating (never to supported).
    """
    verdicts = []
    for h in hypotheses:
        refs = h.get("evidence_refs") or []
        moving = [r for r in refs if r.get("relation") in (
            "supports", "contradicts")]
        n_sup = sum(1 for r in moving
                    if r.get("relation") == "supports")
        n_con = sum(1 for r in moving
                    if r.get("relation") == "contradicts")
        if h.get("status") == "supported" and n_sup >= 2 \
                and n_con == 0:
            v = "upheld"
        elif h.get("status") == "supported":
            v = "overturned-to-investigating"
        elif h.get("status") == "rejected" and n_con >= 2:
            v = "upheld"
        elif h.get("status") == "rejected":
            v = "overturned-to-investigating"
        elif n_sup >= 2 and n_con == 0:
            v = "would-support"
        elif n_con >= 2:
            v = "would-reject"
        else:
            v = "undecided-correct"
        verdicts.append({"hypothesis_id": h.get("id"),
                         "system_status": h.get("status"),
                         "independent_verdict": v,
                         "moving_refs": len(moving),
                         "provenance_ok": all(
                             r.get("action_id") for r in moving)})
    return {"role": "judge", "verdicts": verdicts,
            "limitations": ["verdicts audit recorded evidence; they "
                            "do not re-run measurements"]}
