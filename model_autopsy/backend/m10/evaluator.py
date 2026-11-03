"""M10 independent evaluator (post-freeze scoring only).

Grades discovery WITHOUT rewarding lucky guesses: a mechanism counts
as discovered only when a hypothesis naming it carries moving
(supports/contradicts) evidence from a real executed action.

Grades: discovered (1.0) / partial (0.5) / relevant-only (0.25) /
incorrect (0.0) / unsupported (0.0) / inconclusive-correct (1.0 when
the truth grade is inconclusive/correct-null and the system stayed
uncommitted).
"""
from __future__ import annotations

_FAMILY_WORDS = {
    "subgroup": ("ward", "district", "slice", "segment", "subgroup",
                 "uneven", "gap", "concentrat", "one district",
                 "east", "across"),
    "leakage": ("leak", "proxy", "duplicat", "near-duplicate",
                "derived_flag", "skill"),
    "calibration": ("calibrat", "threshold", "hot", "over-scor",
                    "biased high", "reliability"),
    "misspecification": ("lag", "stale", "persist", "autocorr",
                         "trail"),
    "drift": ("drift", "shift", "growth", "level", "recent",
              "change"),
    "clean": ("healthy", "sound", "no defect", "null result"),
    "thin": ("inconclusive", "more evidence", "thin", "small sample"),
    # M14 new families (additive; existing families untouched).
    "interaction": ("interact", "joint", "combined", "conditional",
                    "together", "concentrat", "segment"),
    "robustness": ("scale", "unit", "fault", "sensitiv", "robust",
                    "degrad", "perturb", "concentrat", "segment",
                    "gap"),
}


def _names_family(hyp_text: str, truth: dict) -> bool:
    fam = truth.get("family", "")
    words = _FAMILY_WORDS.get(fam, ())
    t = (hyp_text or "").lower()
    if fam in ("clean", "thin"):
        return any(w in t for w in words)
    mech = (truth.get("mechanism") or "").lower()
    mech_words = [w for w in mech.replace("-", " ").split()
                  if len(w) > 3]
    return any(w in t for w in words) or any(
        w in t for w in mech_words)


def grade(scenario_id: str, behavior: dict, truth: dict | None = None,
          session=None) -> dict:
    """Grade one investigated scenario. Needs DB session for evidence."""
    from .sealed import load_truth
    truth = truth or load_truth()[scenario_id]
    hyps = []
    if session is not None and behavior.get("investigation_id"):
        from ..db import Hypothesis
        hyps = session.query(Hypothesis).filter(
            Hypothesis.investigation_id ==
            behavior["investigation_id"]).all()
        hyps = [{"text": h.text, "status": h.status,
                 "evidence_refs": h.evidence_refs or []} for h in hyps]
    moving = [h for h in hyps
              if _names_family(h.get("text", ""), truth)
              and any(r.get("relation") in ("supports", "contradicts")
                      for r in h.get("evidence_refs", []))]
    supported = [h for h in moving if h.get("status") in (
        "supported", "investigating")]
    grade_expect = truth.get("grade", "discovered")
    if grade_expect in ("inconclusive", "correct-null"):
        bad = [h for h in hyps if h.get("status") == "supported"]
        return {"scenario": scenario_id, "grade": "inconclusive-correct"
                if not bad else "incorrect",
                "score": 1.0 if not bad else 0.0,
                "detail": f"{len(bad)} unsupported supports; "
                          f"{len(hyps)} hypotheses",
                "naming_hypotheses": len(moving)}
    if supported:
        full = (behavior.get("specs_executed") and
                truth.get("key_tool") in
                (behavior.get("specs_executed") or []))
        return {"scenario": scenario_id,
                "grade": "discovered" if full else "partial",
                "score": 1.0 if full else 0.5,
                "detail": f"{len(supported)} naming hypotheses with "
                          f"moving evidence; key tool "
                          f"{'measured' if full else 'missing'}",
                "naming_hypotheses": len(moving)}
    topical = [h for h in hyps
               if _names_family(h.get("text", ""), truth)]
    if topical:
        return {"scenario": scenario_id, "grade": "relevant-only",
                "score": 0.25,
                "detail": f"{len(topical)} naming hypotheses, none "
                          f"with moving evidence",
                "naming_hypotheses": len(moving)}
    if any(h.get("status") == "supported" for h in hyps):
        return {"scenario": scenario_id, "grade": "unsupported",
                "score": 0.0,
                "detail": "supported conclusion without mechanism "
                          "evidence",
                "naming_hypotheses": 0}
    return {"scenario": scenario_id, "grade": "incorrect", "score": 0.0,
            "detail": "mechanism never named",
            "naming_hypotheses": 0}
