"""Diagnostic capability ontology (M13A.1).

Structured knowledge of what Model Autopsy can investigate: each
dimension names what can be measured, which registered tools
measure it, preconditions on artifact facts, expected outputs,
limitations, confounders, which hypothesis families the
measurement bears on, and whether an INDEPENDENT second
measurement exists (required before strong conclusions).

This is a capability map, not a failure-label list: entries
describe measurements and their bearing, never diagnoses.
Unknown capabilities are explicit: `capable()` returns False
with the missing precondition, so the system knows what it
cannot do.
"""
from __future__ import annotations

DIMENSIONS: list[dict] = [
    {"id": "data_quality", "tools": ["data_quality_profile",
                                     "segment_quality_screen"],
     "needs": ["readable"], "outputs": ["nulls", "duplicate_rows",
                                        "per-segment rates"],
     "limitations": ["hygiene facts only; impact needs error join"],
     "confounders": ["segment mix"], "families": ["quality"],
     "independent": True},
    {"id": "input_distributions", "tools": ["distribution_shift_profile"],
     "needs": ["readable", "split_col"], "outputs": ["by_split stats",
                                                     "mean_shift"],
     "limitations": ["level shift only; shape changes need screens"],
     "confounders": ["sample size per split"], "families": ["drift"],
     "independent": True},
    {"id": "feature_dependence", "tools": ["residual_feature_dependence",
                                           "feature_target_suspiciousness"],
     "needs": ["readable", "target_or_label", "prediction_or_score"],
     "outputs": ["ranked |r|", "top correlations"],
     "limitations": ["linear screening only; correlation ≠ cause"],
     "confounders": ["collinear inputs"], "families": [
         "input-dependence", "leakage"], "independent": True},
    {"id": "target_construction", "tools": ["distribution_shift_profile",
                                            "regression_metrics"],
     "needs": ["readable", "target_or_label"], "outputs": ["level",
                                                           "spread",
                                                           "fit"],
     "limitations": ["construction logic itself is out of scope"],
     "confounders": ["relabeling between splits"],
     "families": ["drift", "quality"], "independent": False},
    {"id": "label_quality", "tools": ["feature_target_suspiciousness",
                                      "data_quality_profile"],
     "needs": ["readable", "label"], "outputs": ["label-duplicate "
                                                 "screen", "hygiene"],
     "limitations": ["near-duplicates only; semantic errors need review"],
     "confounders": ["legitimate predictive features"],
     "families": ["leakage", "quality"], "independent": True},
    {"id": "temporal_behavior", "tools": ["temporal_changepoint_scan",
                                          "residual_time_analysis",
                                          "forecast_diagnostics"],
     "needs": ["readable", "temporal_col", "target_or_label"],
     "outputs": ["break point", "recent-vs-persistent pattern",
                 "drift curve"],
     "limitations": ["needs enough history; thin series inconclusive"],
     "confounders": ["seasonality", "known events"],
     "families": ["drift", "misspecification", "split-hygiene"],
     "independent": True},
    {"id": "calibration", "tools": ["calibration_and_error_analysis",
                                    "calibration_snapshot"],
     "needs": ["readable", "label", "score_col"],
     "outputs": ["reliability bins", "gaps", "bias vs spread"],
     "limitations": ["bins with n<30 ignored; thin data inconclusive"],
     "confounders": ["prevalence shift", "threshold choice"],
     "families": ["calibration", "bias"], "independent": True},
    {"id": "ranking_discrimination", "tools": ["classification_metrics",
                                               "grouped_auc_comparison"],
     "needs": ["readable", "label", "score_col"],
     "outputs": ["AUC", "per-split AUC", "deltas"],
     "limitations": ["AUC hides operating-point failures"],
     "confounders": ["prevalence", "segment mix"],
     "families": ["subgroup", "calibration"], "independent": True},
    {"id": "subgroup_performance", "tools": ["classification_metrics",
                                             "regression_metrics"],
     "needs": ["readable", "segments", "target_or_label"],
     "outputs": ["per-group metrics", "spread", "ratio"],
     "limitations": ["small segments noisy; needs adequate samples"],
     "confounders": ["prevalence", "difficulty mix"],
     "families": ["subgroup"], "independent": True},
    {"id": "distribution_shift", "tools": ["distribution_shift_profile",
                                           "temporal_changepoint_scan"],
     "needs": ["readable", "split_col"], "outputs": ["shift size",
                                                     "break"],
     "limitations": ["first-two-splits comparison"],
     "confounders": ["label shift vs covariate shift"],
     "families": ["drift"], "independent": True},
    {"id": "train_eval_separation", "tools": ["forecast_diagnostics",
                                              "time_split_validation",
                                              "distribution_shift_profile"],
     "needs": ["readable", "split_col"], "outputs": ["overlap hint",
                                                     "chronology"],
     "limitations": ["date/overlap signals only; access patterns "
                     "out of scope"],
     "confounders": ["legitimate re-sampling"],
     "families": ["split-hygiene", "leakage"], "independent": True},
    {"id": "model_implementation", "tools": [],
     "needs": ["model_access"], "outputs": [],
     "limitations": ["black-box availability: not investigable"],
     "confounders": [], "families": [], "independent": False},
    {"id": "inference_behavior", "tools": ["residual_feature_dependence",
                                           "calibration_snapshot"],
     "needs": ["readable", "target_or_label", "prediction_or_score"],
     "outputs": ["input tracking", "bias vs spread"],
     "limitations": ["offline artifact only; live path unobserved"],
     "confounders": ["stale inputs"], "families": [
         "input-dependence", "bias"], "independent": True},
    {"id": "preprocessing_consistency", "tools": ["regression_metrics",
                                                  "distribution_shift_profile"],
     "needs": ["readable", "segments"], "outputs": ["group error",
                                                    "level shift"],
     "limitations": ["pipeline logic itself out of scope; effects only"],
     "confounders": ["true segment differences"],
     "families": ["subgroup", "drift"], "independent": True},
    {"id": "decision_thresholds", "tools": [
        "calibration_and_error_analysis"],
     "needs": ["readable", "label", "score_col"],
     "outputs": ["reliability by score range"],
     "limitations": ["cost model comes from the operator, not the data"],
     "confounders": ["operating-point choice"],
     "families": ["calibration"], "independent": False},
    {"id": "robustness", "tools": ["residual_time_analysis",
                                   "regression_metrics"],
     "needs": ["readable", "target_or_label"], "outputs": [
         "error persistence", "pooled fit"],
     "limitations": ["observational; no perturbations run"],
     "confounders": [], "families": ["misspecification"],
     "independent": False},
    {"id": "reproducibility", "tools": [],
     "needs": ["environment_record"], "outputs": [],
     "limitations": ["assessed by M12 repro grades, not a diagnostic"],
     "confounders": [], "families": [], "independent": False},
    {"id": "operational_behavior", "tools": [],
     "needs": ["operational_access"], "outputs": [],
     "limitations": ["no latency/cost/dependency telemetry"],
     "confounders": [], "families": [], "independent": False},
    {"id": "resource_constraints", "tools": [],
     "needs": ["budget_ledger"], "outputs": [],
     "limitations": ["budget accounting only (M11 ledger, M12)"],
     "confounders": [], "families": [], "independent": False},
]

_BY_ID = {d["id"]: d for d in DIMENSIONS}


def get(dimension_id: str) -> dict:
    if dimension_id not in _BY_ID:
        raise LookupError(f"unknown diagnostic dimension {dimension_id}")
    return _BY_ID[dimension_id]


def _fact_present(facts: dict, need: str) -> bool:
    cols = facts.get("columns") or []
    if need == "readable":
        return bool(facts.get("readable"))
    if need == "split_col":
        return bool(facts.get("split_col"))
    if need == "temporal_col":
        return bool(facts.get("temporal_col"))
    if need == "segments":
        return bool(facts.get("segments"))
    if need == "label":
        return "label" in cols
    if need == "score_col":
        return bool(facts.get("score_col"))
    if need == "target_or_label":
        return any(c in cols for c in ("target", "label", "relevance"))
    if need == "prediction_or_score":
        return any(c in cols for c in ("prediction", "score", "pred"))
    return False  # model_access, operational_access, etc: unavailable


def capable(dimension_id: str, facts: dict) -> dict:
    """Can this dimension be investigated? Missing needs are explicit."""
    dim = get(dimension_id)
    missing = [n for n in dim["needs"] if not _fact_present(facts, n)]
    return {"dimension": dimension_id, "capable": not missing,
            "missing": missing, "tools": dim["tools"] if not missing
            else []}


def coverage_gaps(facts: dict) -> list[dict]:
    """Dimensions that matter but cannot be measured — visible gaps."""
    return [{"dimension": d["id"], "missing": c["missing"],
             "why": "; ".join(_BY_ID[d["id"]]["limitations"])}
            for d in DIMENSIONS
            for c in [capable(d["id"], facts)] if not c["capable"]]


def measurable(facts: dict) -> list[dict]:
    return [capable(d["id"], facts) for d in DIMENSIONS
            if capable(d["id"], facts)["capable"]]
