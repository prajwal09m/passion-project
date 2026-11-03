"""Adaptive investigation planning + stopping policy (M7 Parts 2C/2D).

`plan_next` rebuilds the investigation plan after every experiment from
recorded state: unresolved hypotheses are re-ranked, rejected ones stop
consuming resources, and discriminating tools are preferred. `stopping`
decides whether to continue, with a recorded rationale — a justified
inconclusive always outranks a forced answer.
"""
from __future__ import annotations


def open_hypotheses(hypotheses: list[dict]) -> list[dict]:
    return [h for h in hypotheses
            if h.get("status") in ("proposed", "investigating")]


def plan_next(hypotheses: list[dict], already_ran: set[str],
              budget_left: dict,
              already_failed: set[str] | frozenset = frozenset(),
              already_inapplicable: set[str] | frozenset = frozenset()
              ) -> dict:
    """Durable plan from recorded state (no model judgment, no truth)."""
    from .selection import rank_candidates, explain_selection
    from .hypotheses import analyze_competition
    from . import coverage as _coverage
    open_h = open_hypotheses(hypotheses)
    # M8 coverage boost: tools filling a missing measurement for an open
    # hypothesis outrank generic family matches.
    _missing = set(_coverage.missing_union(open_h, already_ran)) \
        if open_h else set()
    rejected = [h for h in hypotheses if h.get("status") == "rejected"]
    candidates = ["temporal_changepoint_scan", "residual_time_analysis",
                  "distribution_shift_profile", "data_quality_profile",
                  "residual_feature_dependence", "forecast_diagnostics",
                  "regression_metrics", "time_split_validation",
                  "classification_metrics", "grouped_auc_comparison",
                  "calibration_and_error_analysis",
                  "feature_target_suspiciousness", "clustering_stability",
                  "artifact_summary", "dataset_validation",
                  "ranking_slice_diagnostics",
                  "segment_quality_screen"]
    failed = set(already_failed or ())
    inapplicable = set(already_inapplicable or ())
    candidates = [c for c in candidates
                if c not in failed and c not in inapplicable]
    if open_h:
        ranked = rank_candidates(candidates, open_h, already_ran)
        for r in ranked:
            if r["tool"] in _missing and not r["redundant"] \
                    and r["expected_value"] != "high":
                r["expected_value"] = "high"
                r["reason"] += (" Fills a missing measurement for an "
                                  "open hypothesis.")
        _order = {"high": 0, "medium": 1, "low": 2}
        ranked.sort(key=lambda s: (_order[s["expected_value"]],
                                    s["tool"]))
    else:
        # No hypotheses yet (first turn): recommend safe task-agnostic
        # starters instead of an empty brief the model must ignore.
        ranked = rank_candidates(
            ["artifact_summary", "dataset_validation",
             "data_quality_profile"],
            [{"text": "establish baseline facts about the artifact"}],
            already_ran)
    top = [r for r in ranked if not r["redundant"]][:3]
    ranked_all = [r["tool"] for r in ranked if not r["redundant"]]
    return {"open": [{"id": h.get("id"), "text": (h.get("text") or "")[:140],
                      "status": h.get("status")} for h in open_h],
            "rejected_not_pursued": [h.get("id") for h in rejected],
            "competition": analyze_competition(
                [{"id": h.get("id"), "text": h.get("text", "")}
                 for h in hypotheses]) if len(hypotheses) >= 2 else {},
            "recommended": top,
            "ranked_all": ranked_all,
            "explanation": explain_selection(ranked) if ranked else
            "No open hypotheses; no further experiments recommended.",
            "budget_left": budget_left,
            "untested": [h.get("id") for h in open_h
                         if not (h.get("evidence_refs") or [])],
            "failed_skipped": sorted(failed),
            "inapplicable_skipped": sorted(inapplicable),
            "missing_measurements": sorted(_missing),
            "coverage": _coverage.coverage(open_h, already_ran)}


def stopping(inv_status: str, hypotheses: list[dict],
             tool_calls_used: int, tool_calls_max: int,
             min_rounds_done: int = 1) -> tuple[bool, str]:
    """(stop, rationale). Pure function of recorded state + budget."""
    open_h = open_hypotheses(hypotheses)
    untested = [h for h in open_h if not (h.get("evidence_refs") or [])]
    if not open_h:
        # M22: distinguish "none ever proposed" (empty roster, nothing to
        # target) from "all resolved" — the old text claimed resolution
        # when nothing had been investigated at all.
        if not hypotheses:
            return True, ("no hypotheses on record; no experiment can be "
                          "targeted until hypotheses are proposed")
        return True, ("all hypotheses resolved (supported/rejected/blocked); "
                      "further experiments cannot change the conclusion")
    if tool_calls_used >= tool_calls_max:
        if untested:
            return True, (f"tool budget exhausted "
                          f"({tool_calls_used}/{tool_calls_max}) with "
                          f"{len(untested)} hypotheses never tested; "
                          "remaining uncertainty is reported, not guessed")
        return True, (f"tool budget exhausted "
                      f"({tool_calls_used}/{tool_calls_max}); stopping with "
                      "recorded evidence")
    supported = [h for h in hypotheses if h.get("status") == "supported"]
    if supported and not open_h:
        return True, ("diagnosis supported with cited evidence and no open "
                      "competitors; stopping")
    if min_rounds_done < 1 and not supported:
        return False, "insufficient investigation depth; continue"
    return False, (f"{len(open_h)} hypotheses open "
                   f"({len(untested)} never tested); informative experiments "
                   f"remain within budget")
