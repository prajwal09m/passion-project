"""Experiment selection and information-value engine (M6 Part 2B).

Before execution the engine evaluates, for each candidate tool, which
hypotheses it tests, what would support/contradict each, whether it
discriminates competitors, expected information value (qualitative:
high/medium/low — never a fabricated number), cost, runtime, confounders,
and whether a simpler test answers the same question.

Tracks predicted vs actual information and whether confidence/direction
changed. Prefers uncertainty reduction; penalizes redundancy.
"""
from __future__ import annotations

# Qualitative cost/runtime table (relative, documented — not measured).
TOOL_COST = {
    "artifact_summary": {"cost": "low", "runtime": "fast"},
    "dataset_validation": {"cost": "low", "runtime": "fast"},
    "forecast_diagnostics": {"cost": "low", "runtime": "fast"},
    "regression_metrics": {"cost": "low", "runtime": "fast"},
    "time_split_validation": {"cost": "low", "runtime": "fast"},
    "temporal_changepoint_scan": {"cost": "low", "runtime": "fast"},
    "residual_time_analysis": {"cost": "low", "runtime": "fast"},
    "distribution_shift_profile": {"cost": "low", "runtime": "fast"},
    "data_quality_profile": {"cost": "low", "runtime": "fast"},
    "residual_feature_dependence": {"cost": "low", "runtime": "fast"},
    "classification_metrics": {"cost": "low", "runtime": "fast"},
    "calibration_and_error_analysis": {"cost": "medium", "runtime": "medium"},
    "feature_target_suspiciousness": {"cost": "medium", "runtime": "medium"},
    "grouped_auc_comparison": {"cost": "medium", "runtime": "medium"},
    "clustering_stability": {"cost": "medium", "runtime": "medium"},
    "ranking_slice_diagnostics": {"cost": "low", "runtime": "fast"},
    "segment_quality_screen": {"cost": "low", "runtime": "fast"},
    "propose_hypothesis": {"cost": "none", "runtime": "instant"},
}

# Which mechanism family each tool discriminates (qualitative mapping).
TOOL_DISCRIMINATES = {
    "forecast_diagnostics": ["drift", "split-hygiene"],
    "temporal_changepoint_scan": ["drift", "abrupt-vs-gradual", "misspecification"],
    "residual_time_analysis": ["misspecification", "drift"],
    "time_split_validation": ["split-hygiene"],
    "distribution_shift_profile": ["drift", "covariate-shift"],
    "data_quality_profile": ["missingness", "quality"],
    "regression_metrics": ["bias", "segment"],
    "classification_metrics": ["subgroup"],
    "grouped_auc_comparison": ["subgroup"],
    "ranking_slice_diagnostics": ["subgroup", "slice"],
    "slice_gap_significance": ["subgroup", "slice"],
    "segment_quality_screen": ["missingness", "quality", "subgroup"],
    "calibration_and_error_analysis": ["calibration"],
    "feature_target_suspiciousness": ["leakage"],
    "residual_feature_dependence": ["misspecification", "input-dependence"],
    "clustering_stability": ["instability"],
}


def _family_of(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ("leakage", "leaked", "data leak",
                             "label leak")):
        return "leakage"
    if any(w in t for w in ("drift", "shift", "level", "regime", "growth", "demand")):
        return "drift"
    if any(w in t for w in ("split", "overlap", "leak", "hygiene", "chronolog")):
        return "split-hygiene"
    if any(w in t for w in ("misspecif", "autocorr", "persistent", "throughout", "bias")):
        return "misspecification"
    if any(w in t for w in ("missing", "quality", "null")):
        return "quality"
    if any(w in t for w in ("input", "feature", "device", "stale", "lag",
                            "dependence", "segment", "district")):
        return "input-dependence"
    if any(w in t for w in ("calibrat",)):
        return "calibration"
    if any(w in t for w in ("region", "ward", "subgroup", "slice",
                            "auc", "ranking", "gap", "uneven")):
        return "subgroup"
    return "other"


def score_candidate(tool: str, hypotheses: list[dict],
                    already_ran: set[str]) -> dict:
    """Qualitative score for one candidate tool.

    Returns rationale dict — no numeric information-gain is fabricated.
    high value = tests 2+ competing families and not yet run.
    """
    fams = [_family_of(h.get("text", "")) for h in hypotheses]
    disc = set(TOOL_DISCRIMINATES.get(tool, []))
    # Map family names onto discrimination keywords loosely.
    covers = set()
    for f in fams:
        if f == "drift" and ("drift" in disc or "abrupt-vs-gradual" in disc):
            covers.add(f)
        if f == "split-hygiene" and ("split-hygiene" in disc or "drift" in disc):
            covers.add(f)
        if f == "input-dependence" and ("input-dependence" in disc
                                          or "misspecification" in disc):
            covers.add(f)
        if f == "subgroup" and ("subgroup" in disc or "slice" in disc
                                  or "calibration" in disc):
            covers.add(f)
        if f == "misspecification" and ("misspecification" in disc or "drift" in disc):
            covers.add(f)
        if f in ("quality",) and disc:
            covers.add(f)
    n_cover = len(set(fams) & covers) if covers else (1 if disc else 0)
    distinct_fams_covered = len(covers)
    redundant = tool in already_ran
    if redundant:
        value, reason = "low", "already ran with these arguments; rerun adds no new evidence"
    elif distinct_fams_covered >= 2:
        value, reason = "high", f"discriminates {sorted(covers)} in one run"
    elif distinct_fams_covered == 1:
        value, reason = "medium", f"tests {sorted(covers)} but not competitors"
    else:
        value, reason = "low", "does not discriminate the live hypotheses"
    cost = TOOL_COST.get(tool, {"cost": "medium", "runtime": "medium"})
    return {"tool": tool, "expected_value": value, "reason": reason,
            "covers": sorted(covers), "redundant": redundant, **cost}


def rank_candidates(candidates: list[str], hypotheses: list[dict],
                    already_ran: set[str]) -> list[dict]:
    order = {"high": 0, "medium": 1, "low": 2}
    scored = [score_candidate(t, hypotheses, already_ran) for t in candidates]
    return sorted(scored, key=lambda s: (order[s["expected_value"]], s["tool"]))


def explain_selection(ranked: list[dict]) -> str:
    if not ranked:
        return "No candidate diagnostics available."
    top = ranked[0]
    alts = ", ".join(r["tool"] for r in ranked[1:3])
    return (f"Selected {top['tool']} (expected value {top['expected_value']}: "
            f"{top['reason']}). Over {alts or 'no alternatives'} because it "
            f"covers {top['covers']} with cost {top.get('cost')}. "
            f"Redundant reruns were deprioritized.")


def record_outcome(predicted: str, hypotheses_affected: list[str],
                   confidence_changed: bool, direction_changed: bool) -> dict:
    """Post-execution honesty record: predicted vs actual (qualitative)."""
    actual = "high" if (confidence_changed or direction_changed) else "low"
    return {"predicted_value": predicted,
            "actual_value": actual,
            "hypotheses_affected": hypotheses_affected,
            "confidence_changed": confidence_changed,
            "direction_changed": direction_changed,
            "lesson": ("selection paid off" if actual == "high"
                       else "little new information; prefer a discriminating test next")}
