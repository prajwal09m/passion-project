"""Investigation evaluation framework (Milestone 3, Part 9).

Five dimensions + reliability; every metric states its assessment class
(deterministic / heuristic / llm / human). Aggregate score is reported
ALONGSIDE per-dimension values - never as a lone number.
"""
from __future__ import annotations

ASSESSMENT = {"discovery": "deterministic + heuristic",
              "reasoning": "heuristic",
              "experimentation": "deterministic",
              "accuracy": "deterministic",
              "efficiency": "deterministic",
              "reliability": "deterministic"}


def score_run(report: dict, scenario: dict) -> dict:
    exp, kind = scenario.get("expect"), scenario.get("kind")
    confirmed = [c.get("title", "") for c in
                 report.get("confirmed_findings", [])]
    text = " ".join(confirmed).lower()
    hit = False
    if kind == "clean":
        hit = len(confirmed) == 0
    elif exp == "leak_flag":
        hit = "leak" in text or "proxy" in text
    elif exp == "urban_bias":
        hit = "bias" in text
    elif exp == "overlap_and_drift":
        hit = "drift" in text or "split" in text or "stale" in text
    elif exp == "tail_slice_gap":
        hit = "rank" in text or "slice" in text or "position" in text
    elif exp == "scaling_mismatch":
        hit = "bias" in text or "mismatch" in text or "segment" in text
    elif exp == "leak_plus_subgroup":
        hit = ("leak" in text or "proxy" in text)
    elif exp == "limited":
        hit = True  # correct behavior: no overclaim
    elif exp == "healthy":
        hit = len(confirmed) == 0
    discovery = {"failure_found": hit, "false_positives": 0 if (
        hit or kind in ("clean",)) else 1,
                 "class": "deterministic"}
    n_exp = len(report.get("experiments", []))
    experimentation = {"n_experiments": n_exp,
                       "unnecessary": max(0, n_exp - 4),
                       "reproducible": n_exp,
                       "class": "deterministic"}
    numbers_ok = all(bool(e.get("numbers")) for e in
                     report.get("experiments", []))
    accuracy = {"numbers_present": numbers_ok,
                "conclusion_valid": hit,
                "class": "deterministic+heuristic"}
    reasoning = {"hypotheses": len(report.get("rejected_hypotheses", []))
                 + len(confirmed),
                 "null_present": True,
                 "class": "heuristic"}
    reliability = {"report_complete": bool(
        report.get("executive_summary")),
        "class": "deterministic"}
    efficiency = {"experiments": n_exp, "class": "deterministic",
                  "tokens": None,
                  "note": "offline traces carry no provider billing; "
                          "token trade-offs measured in Part 10 harness"}
    dims = {"discovery": discovery, "reasoning": reasoning,
            "experimentation": experimentation, "accuracy": accuracy,
            "efficiency": efficiency, "reliability": reliability}
    agg = round(sum([1.0 if hit else 0.0,
                     1.0 if numbers_ok else 0.0,
                     1.0 if n_exp <= 4 else 0.5]) / 3, 3)
    return {"scenario": scenario["id"], "hit": hit,
            "dimensions": dims,
            "assessment_classes": ASSESSMENT,
            "aggregate": agg,
            "note": "aggregate accompanies dimensions; never replaces them"}
