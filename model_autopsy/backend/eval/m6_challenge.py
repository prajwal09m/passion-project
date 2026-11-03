"""M6 independent challenge suite (Part 4).

Concealed ground truth: the investigator receives ONLY spec + artifact
(see `public_brief`). Truth lives in `_TRUTH` in this module, which the
evaluation harness reads post-freeze — never passed to the investigator.

Coverage (12 scenarios): single-cause, competing explanations,
interacting mechanisms, weak signals, distractors, no-failure,
inconclusive-required, multi-experiment, must-reject-initial-plausible,
correlation-vs-causation — across tabular, regression, forecasting,
finance, ranking, clustering, pipelines, black-box.

Sample-size limitation is documented in the validation report; this
suite is offline evidence, not a generalization claim.
"""
from __future__ import annotations

UNI = "model_autopsy/tests/fixture_universal"
CH = "model_autopsy/tests/fixture_challenge"
FE = "model_autopsy/tests/fixture_eval/investigator"

SCENARIOS: list[dict] = [
    {"id": "m6_single_tabular", "family": "tabular classification",
     "kind": "single", "requires": ["classification_metrics"],
     "spec": {"project_id": "m6_tab", "name": "Card review",
              "domain": "lending", "objective": "Scores look uneven across regions.",
              "task_type": "classification", "target_definition": "Binary default",
              "evaluation_methodology": "AUC overall + per region",
              "model": {"name": "m6-gbm", "framework": "xgboost", "availability": "black_box"},
              "dataset": {"location": FE + "/credit_default.csv", "n_rows": 1500}},
     "artifact": FE + "/credit_default.csv"},
    {"id": "m6_competing_regression", "family": "regression",
     "kind": "competing", "requires": ["regression_metrics", "distribution_shift_profile"],
     "spec": {"project_id": "m6_rent", "name": "Rent audit",
              "domain": "housing", "objective": "Estimates off in one district after a schema update.",
              "task_type": "regression", "target_definition": "Numeric rent",
              "evaluation_methodology": "MAE/RMSE, residual analysis",
              "model": {"name": "m6-rf", "framework": "sklearn", "availability": "local"},
              "dataset": {"location": FE + "/rent_estimates.csv", "n_rows": 1200}},
     "artifact": FE + "/rent_estimates.csv"},
    {"id": "m6_drift_forecast", "family": "time-series forecasting",
     "kind": "single", "requires": ["temporal_changepoint_scan", "residual_time_analysis"],
     "spec": {"project_id": "m6_turb", "name": "Turbine forecast",
              "domain": "energy", "objective": "Forecasts miss a recent level change.",
              "task_type": "forecasting", "target_definition": "Daily output",
              "evaluation_methodology": "MAE by horizon, drift, split hygiene",
              "model": {"name": "m6-ar", "framework": "statsmodels", "availability": "black_box"},
              "dataset": {"location": FE + "/turbine_output.csv", "n_rows": 730}},
     "artifact": FE + "/turbine_output.csv"},
    {"id": "m6_interacting_pipeline", "family": "complex preprocessing pipeline",
     "kind": "interacting", "requires": ["regression_metrics", "data_quality_profile"],
     "spec": {"project_id": "m6_claim", "name": "Severity estimator",
              "domain": "insurance", "objective": "Estimates off since a pipeline change.",
              "task_type": "regression", "target_definition": "Numeric severity",
              "evaluation_methodology": "MAE/RMSE, residual-vs-input",
              "model": {"name": "m6-reg", "framework": "sklearn", "availability": "local"},
              "dataset": {"location": FE + "/claim_severity.csv", "n_rows": 1500}},
     "artifact": FE + "/claim_severity.csv"},
    {"id": "m6_weak_signal", "family": "weak and ambiguous signals",
     "kind": "weak", "requires": ["classification_metrics"],
     "spec": {"project_id": "m6_pilot", "name": "Pilot readout",
              "domain": "health", "objective": "Small pilot: material issue or more evidence needed?",
              "task_type": "classification", "target_definition": "Binary outcome",
              "evaluation_methodology": "AUC, calibration (small n)",
              "model": {"name": "m6-lr", "framework": "sklearn", "availability": "black_box"},
              "dataset": {"location": FE + "/pilot_study.csv", "n_rows": 120}},
     "artifact": FE + "/pilot_study.csv"},
    {"id": "m6_distractor", "family": "misleading distractors",
     "kind": "distractor", "requires": ["forecast_diagnostics", "time_split_validation"],
     "spec": {"project_id": "m6_turb2", "name": "Turbine hygiene check",
              "domain": "energy", "objective": "Are recent misses a validation artifact?",
              "task_type": "forecasting", "target_definition": "Daily output",
              "evaluation_methodology": "MAE by horizon, drift, split hygiene",
              "model": {"name": "m6-ar2", "framework": "statsmodels", "availability": "black_box"},
              "dataset": {"location": FE + "/turbine_output.csv", "n_rows": 730}},
     "artifact": FE + "/turbine_output.csv"},
    {"id": "m6_no_failure", "family": "no-failure control",
     "kind": "clean", "requires": ["regression_metrics"],
     "spec": {"project_id": "m6_well", "name": "Wellness check",
              "domain": "health", "objective": "Routine check: is the index model healthy?",
              "task_type": "regression", "target_definition": "Numeric index",
              "evaluation_methodology": "MAE/RMSE, residual analysis",
              "model": {"name": "m6-reg2", "framework": "sklearn", "availability": "local"},
              "dataset": {"location": FE + "/wellness_index.csv", "n_rows": 800}},
     "artifact": FE + "/wellness_index.csv"},
    {"id": "m6_inconclusive", "family": "inconclusive-required",
     "kind": "limited", "requires": ["classification_metrics"],
     "spec": {"project_id": "m6_pilot2", "name": "Pilot readout 2",
              "domain": "health", "objective": "Tiny sample: decide or declare inconclusive?",
              "task_type": "classification", "target_definition": "Binary outcome",
              "evaluation_methodology": "AUC, calibration (small n)",
              "model": {"name": "m6-lr2", "framework": "sklearn", "availability": "black_box"},
              "dataset": {"location": FE + "/pilot_study.csv", "n_rows": 120}},
     "artifact": FE + "/pilot_study.csv"},
    {"id": "m6_multi_experiment", "family": "requires several experiments",
     "kind": "multi", "requires": ["classification_metrics", "grouped_auc_comparison"],
     "spec": {"project_id": "m6_credit2", "name": "Default review deep",
              "domain": "lending", "objective": "Which region fails and is it stable?",
              "task_type": "classification", "target_definition": "Binary default",
              "evaluation_methodology": "AUC overall + per region, calibration",
              "model": {"name": "m6-gbm2", "framework": "xgboost", "availability": "black_box"},
              "dataset": {"location": FE + "/credit_default.csv", "n_rows": 1500}},
     "artifact": FE + "/credit_default.csv"},
    {"id": "m6_reject_plausible", "family": "initially plausible must be rejected",
     "kind": "reject", "requires": ["feature_target_suspiciousness"],
     "spec": {"project_id": "m6_credit3", "name": "Leakage screen",
              "domain": "lending", "objective": "Is the good AUC from leakage or skill?",
              "task_type": "classification", "target_definition": "Binary default",
              "evaluation_methodology": "AUC, leakage screen",
              "model": {"name": "m6-gbm3", "framework": "xgboost", "availability": "black_box"},
              "dataset": {"location": FE + "/credit_default.csv", "n_rows": 1500}},
     "artifact": FE + "/credit_default.csv"},
    {"id": "m6_correlation_causation", "family": "correlation vs causation",
     "kind": "correlation", "requires": ["residual_time_analysis", "distribution_shift_profile"],
     "spec": {"project_id": "m6_energy", "name": "Demand forecaster",
              "domain": "utilities", "objective": "Does demand growth cause the miss or just correlate?",
              "task_type": "forecasting", "target_definition": "Daily demand",
              "evaluation_methodology": "MAE by horizon, drift, split hygiene",
              "model": {"name": "m6-ar3", "framework": "statsmodels", "availability": "black_box"},
              "dataset": {"location": UNI + "/energy_demand.csv", "n_rows": 730}},
     "artifact": UNI + "/energy_demand.csv"},
    {"id": "m6_ranking_slice", "family": "recommendation and ranking",
     "kind": "single", "requires": ["regression_metrics"],
     "spec": {"project_id": "m6_music", "name": "Catalog ranking",
              "domain": "media", "objective": "Are top results relevant for every slice?",
              "task_type": "ranking", "target_definition": "Relevance grade",
              "evaluation_methodology": "P@K per slice",
              "model": {"name": "m6-rank", "framework": "lightgbm", "availability": "black_box"},
              "dataset": {"location": FE + "/music_rank.csv", "n_rows": 1760}},
     "artifact": FE + "/music_rank.csv"},
]

# Concealed truth — harness-only, never handed to the investigator.
_TRUTH = {
    "m6_single_tabular": {"expect": "subgroup failure", "must_use": "classification_metrics"},
    "m6_competing_regression": {"expect": "segment bias vs schema change", "must_use": "regression_metrics"},
    "m6_drift_forecast": {"expect": "level shift with clean splits", "must_use": "temporal_changepoint_scan"},
    "m6_interacting_pipeline": {"expect": "input dependence", "must_use": "regression_metrics"},
    "m6_weak_signal": {"expect": "inconclusive", "must_use": "none"},
    "m6_distractor": {"expect": "no leakage; drift only", "must_use": "time_split_validation"},
    "m6_no_failure": {"expect": "correct-null", "must_use": "none"},
    "m6_inconclusive": {"expect": "inconclusive", "must_use": "none"},
    "m6_multi_experiment": {"expect": "subgroup failure, needs 2+ diagnostics", "must_use": "grouped_auc_comparison"},
    "m6_reject_plausible": {"expect": "reject leakage", "must_use": "feature_target_suspiciousness"},
    "m6_correlation_causation": {"expect": "temporal test required", "must_use": "residual_time_analysis"},
    "m6_ranking_slice": {"expect": "slice gap", "must_use": "regression_metrics"},
}


def public_brief(scenario_id: str) -> dict:
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return {"id": s["id"], "spec": s["spec"], "artifact": s["artifact"],
                    "family": s["family"], "kind": s["kind"]}
    raise LookupError(f"unknown scenario {scenario_id!r}")


def evaluate(report: dict, scenario_id: str) -> dict:
    """Independent scoring (harness-only truth access)."""
    truth = _TRUTH[scenario_id]
    scen = next(s for s in SCENARIOS if s["id"] == scenario_id)
    exps = report.get("experiments", []) or []
    tools = {e.get("tool") for e in exps}
    required = set(scen.get("requires", []))
    used_required = bool(tools & required) if required != {"none"} else True
    confirmed = [c.get("title", "") for c in report.get("confirmed_findings", [])]
    text = " ".join(confirmed).lower()
    kind = scen["kind"]
    if kind in ("clean",):
        discovery = 1.0 if not confirmed else 0.0
    elif kind in ("weak", "limited"):
        discovery = 1.0 if not confirmed else 0.0  # correct = no overclaim
    else:
        discovery = 1.0 if (text and used_required) else (0.4 if text else 0.0)
    evidence = 1.0 if (discovery == 1.0 and all(bool(e.get("numbers")) for e in exps)) \
        else (0.5 if exps else 0.0)
    reasoning = 1.0 if (discovery == 1.0 and len(exps) >= 2) else (0.6 if text else 0.0)
    calibration = 1.0 if (kind in ("clean", "weak", "limited") and not confirmed) \
        else (0.6 if discovery >= 0.4 else 0.0)
    selection = 1.0 if used_required and len(exps) >= 2 else (0.5 if exps else 0.0)
    causal = 0.7 if (discovery == 1.0 and len(exps) >= 2) else (0.5 if not confirmed else 0.3)
    efficiency = 1.0 if len(exps) <= 4 else max(0.0, 1.0 - 0.2 * (len(exps) - 4))
    repro = 1.0 if report.get("executive_summary") else 0.0
    report_v = 1.0 if report.get("structured_summary_valid") else 0.4
    dims = {"discovery": discovery, "evidence": evidence, "reasoning": reasoning,
            "calibration": calibration, "experiment_selection": selection,
            "causal_diagnosis": causal, "efficiency": efficiency,
            "reproducibility": repro, "report_validity": report_v}
    overall = round(sum(dims.values()) / len(dims), 3)
    return {"scenario": scenario_id, "dimensions": dims, "overall": overall,
            "used_required": used_required, "truth_expect": truth["expect"]}
