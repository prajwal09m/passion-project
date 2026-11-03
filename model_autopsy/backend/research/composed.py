"""M14 Phase 2: autonomous experiment invention (offline).

Composed experiments assemble existing primitives (subset select,
perturbation, recompute, compare, subgroup, uncertainty) into a
justified procedure. Every proposal carries the full section 2.2
schema; validate() enforces section 2.3 (relevance, executability,
inputs, no sealed truth, meaningful measurement, decision-changing
potential, budget). Creativity is scored by usefulness, never
novelty alone (section 2.4).
"""
from __future__ import annotations

import uuid

REQUIRED = ("research_question", "hypotheses", "expected",
            "data", "preconditions", "procedure", "metrics",
            "limitations", "info_value", "cost", "confounders",
            "stop_conditions")

PRIMITIVES = ("subset", "perturb", "recompute", "compare",
              "subgroup", "uncertainty", "baseline")


def propose(question: str, hyp_ids: list[str], expected: dict,
            data: dict, procedure: list[dict], metrics: list[str],
            cost: int = 1, confounders: list[str] | None = None,
            stop: str = "") -> dict:
    return {
        "id": "exp_" + uuid.uuid4().hex[:10],
        "research_question": question,
        "hypotheses": list(hyp_ids),
        "expected": dict(expected),
        "data": dict(data),
        "preconditions": [f"artifact readable: "
                          f"{data.get('artifact', '?')}"],
        "procedure": list(procedure),
        "metrics": list(metrics),
        "limitations": "observational unless a perturbation primitive "
                       "with isolated copy is present",
        "info_value": {"distinguishes": len(hyp_ids),
                       "decision_relevance": "decisive"
                       if len(hyp_ids) >= 2 else "supporting"},
        "cost": int(cost),
        "confounders": list(confounders or []),
        "stop_conditions": stop or "stop when the expected contrast "
                           "is measured or budget exhausts",
        "novel": any(p.get("op") == "perturb" for p in procedure),
    }


def validate(prop: dict, facts: dict, budget_left: int,
             sealed_tokens: set[str] | None = frozenset()) -> dict:
    errors: list[str] = []
    for key in REQUIRED:
        if key not in prop:
            errors.append(f"missing {key}")
    if len(prop.get("hypotheses", [])) < 1:
        errors.append("no hypotheses distinguished")
    if not prop.get("procedure"):
        errors.append("empty procedure")
    else:
        ops = [p.get("op") for p in prop["procedure"]]
        if any(o not in PRIMITIVES for o in ops):
            errors.append(f"unknown primitive in {ops}")
    cols = set(facts.get("columns") or [])
    for needed in prop.get("data", {}).get("columns_needed", []):
        if needed not in cols:
            errors.append(f"required column {needed!r} absent")
    text = (prop.get("research_question", "") + " " +
            str(prop.get("expected", ""))).lower()
    leak = (sealed_tokens or set()) & set(text.replace(",", " ").split())
    if leak:
        errors.append(f"sealed truth leak: {sorted(leak)[:3]}")
    if budget_left < int(prop.get("cost", 1)):
        errors.append("insufficient budget")
    if not prop.get("metrics"):
        errors.append("no measurable outcome; cannot change a decision")
    return {"valid": not errors, "errors": errors,
            "id": prop.get("id")}


def creativity(prop: dict, ran_similar: int = 0) -> dict:
    """Usefulness-first creativity score (novelty never substitutes)."""
    info = prop.get("info_value", {})
    distinguishes = int(info.get("distinguishes", 0))
    useful = distinguishes * 2 + (1 if prop.get("metrics") else 0)
    novelty = (1 if prop.get("novel") else 0) - min(ran_similar, 1)
    return {"usefulness": useful, "novelty": max(novelty, 0),
            "score": useful,  # novelty reported, usefulness decides
            "note": "novelty must never substitute for usefulness"}
