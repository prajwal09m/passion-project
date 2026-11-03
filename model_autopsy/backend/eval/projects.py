"""Benchmark project registry (Milestone 4).

Eight unfamiliar projects, disjoint from Milestone 3 scenarios in
story, domain, columns, and mechanisms. The investigator receives ONLY
the spec + artifact path + brief (see separation.discovery_input);
ground truth never leaves the evaluation environment.
"""
from __future__ import annotations

BASE = "model_autopsy/tests/fixture_eval/investigator"

PROJECTS: list[dict] = [
    {"id": "eval_credit", "family": "tabular classification",
     "spec": {"project_id": "eval_credit", "name": "Default risk review",
              "domain": "lending",
              "objective": "Card-default scores look uneven across regions.",
              "task_type": "classification",
              "target_definition": "Binary: default within 12 months",
              "evaluation_methodology": "AUC overall + per region, calibration",
              "model": {"name": "default-gbm", "framework": "xgboost",
                        "availability": "black_box"},
              "dataset": {"location": BASE + "/credit_default.csv",
                          "n_rows": 1500}},
     "artifact": BASE + "/credit_default.csv"},
    {"id": "eval_rent", "family": "regression",
     "spec": {"project_id": "eval_rent", "name": "Rent estimate audit",
              "domain": "housing",
              "objective": "Rent estimates for one district look off after "
                           "a schema update.",
              "task_type": "regression",
              "target_definition": "Numeric monthly rent",
              "evaluation_methodology": "MAE/RMSE, residual analysis",
              "model": {"name": "rent-rf", "framework": "sklearn",
                        "availability": "local"},
              "dataset": {"location": BASE + "/rent_estimates.csv",
                          "n_rows": 1200}},
     "artifact": BASE + "/rent_estimates.csv"},
    {"id": "eval_turbine", "family": "time-series forecasting",
     "spec": {"project_id": "eval_turbine", "name": "Turbine output forecast",
              "domain": "energy",
              "objective": "Output forecasts miss a recent level change.",
              "task_type": "forecasting",
              "target_definition": "Daily output (numeric)",
              "evaluation_methodology": "MAE by horizon, drift, split hygiene",
              "model": {"name": "turbine-ar", "framework": "statsmodels",
                        "availability": "black_box"},
              "dataset": {"location": BASE + "/turbine_output.csv",
                          "n_rows": 730}},
     "artifact": BASE + "/turbine_output.csv"},
    {"id": "eval_docs", "family": "clustering",
     "spec": {"project_id": "eval_docs", "name": "Document grouping",
              "domain": "text",
              "objective": "Are these document groups stable and separated?",
              "task_type": "clustering",
              "target_definition": "No labels: group assignment",
              "evaluation_methodology": "Silhouette, stability, size balance",
              "model": {"name": "doc-kmeans", "framework": "sklearn",
                        "availability": "local"},
              "dataset": {"location": BASE + "/doc_vectors.csv",
                          "n_rows": 600}},
     "artifact": BASE + "/doc_vectors.csv"},
    {"id": "eval_music", "family": "recommendation/ranking",
     "spec": {"project_id": "eval_music", "name": "Catalog ranking",
              "domain": "media",
              "objective": "Are top results relevant for every catalog slice?",
              "task_type": "ranking",
              "target_definition": "Relevance grade per query-item",
              "evaluation_methodology": "P@K per slice, pooled precision",
              "model": {"name": "rank-lgb", "framework": "lightgbm",
                        "availability": "black_box"},
              "dataset": {"location": BASE + "/music_rank.csv",
                          "n_rows": 1760}},
     "artifact": BASE + "/music_rank.csv"},
    {"id": "eval_claim", "family": "multi-stage pipeline",
     "spec": {"project_id": "eval_claim", "name": "Severity estimator",
              "domain": "insurance",
              "objective": "Severity estimates look systematically off since "
                           "a pipeline change.",
              "task_type": "regression",
              "target_definition": "Numeric claim severity",
              "evaluation_methodology": "MAE/RMSE, residual-vs-input analysis",
              "model": {"name": "sev-reg", "framework": "sklearn",
                        "availability": "local"},
              "dataset": {"location": BASE + "/claim_severity.csv",
                          "n_rows": 1500}},
     "artifact": BASE + "/claim_severity.csv"},
    {"id": "eval_wellness", "family": "clean control",
     "spec": {"project_id": "eval_wellness", "name": "Wellness index check",
              "domain": "health",
              "objective": "Routine check: is the wellness index model healthy?",
              "task_type": "regression",
              "target_definition": "Numeric wellness index",
              "evaluation_methodology": "MAE/RMSE, residual analysis",
              "model": {"name": "well-reg", "framework": "sklearn",
                        "availability": "local"},
              "dataset": {"location": BASE + "/wellness_index.csv",
                          "n_rows": 800}},
     "artifact": BASE + "/wellness_index.csv"},
    {"id": "eval_pilot", "family": "weak-evidence pilot",
     "spec": {"project_id": "eval_pilot", "name": "Pilot readout",
              "domain": "health",
              "objective": "Small pilot readout: is there a material issue, "
                           "or is more evidence required?",
              "task_type": "classification",
              "target_definition": "Binary pilot outcome",
              "evaluation_methodology": "AUC, calibration (small n)",
              "model": {"name": "pilot-lr", "framework": "sklearn",
                        "availability": "black_box"},
              "dataset": {"location": BASE + "/pilot_study.csv",
                          "n_rows": 120}},
     "artifact": BASE + "/pilot_study.csv"},
]


def get_project(pid: str) -> dict:
    for p in PROJECTS:
        if p["id"] == pid:
            return p
    raise LookupError(f"unknown eval project {pid!r}")


def load_truth() -> dict:
    import json
    from pathlib import Path
    return json.loads(
        (Path(__file__).resolve().parents[2]
         / "tests" / "fixture_eval" / "ground_truth_eval.json"
         ).read_text(encoding="utf-8"))
