"""Synthetic project adapters for the offline multi-project suite.

Five non-finance projects across task types. Each points at committed
seeded fixtures; ground truth lives in the test fixtures directory and
is NEVER consulted here.
"""
from __future__ import annotations

from . import (DatasetMetadata, ModelAvailability, ModelMetadata, ProjectAdapter,
               ProjectSpec, TaskType, register_project)

FIX = "model_autopsy/tests/fixture_universal"


def _spec(pid: str, name: str, domain: str, objective: str, task: str,
          target: str, evaluation: str, model_name: str, framework: str,
          availability: str, location: str, n_rows: int,
          extra_caps: list | None = None) -> ProjectSpec:
    return ProjectSpec(
        project_id=pid, name=name, domain=domain, objective=objective,
        task_type=task, target_definition=target,
        evaluation_methodology=evaluation,
        model=ModelMetadata(name=model_name, framework=framework,
                            availability=availability),
        dataset=DatasetMetadata(location=location, n_rows=n_rows))


class SyntheticAdapter(ProjectAdapter):
    def __init__(self, spec: ProjectSpec, caps: list | None = None):
        super().__init__(spec)
        self._caps = caps or ["prediction_inspection", "error_analysis"]

    def available_capabilities(self) -> list[str]:
        return list(self._caps)


def register_synthetic() -> None:
    defs = [
        (_spec("clinic", "Clinic readmission", "healthcare",
               "Why are readmission predictions underperforming on new wards?",
               TaskType.CLASSIFICATION.value, "Binary: 30-day readmission",
               "AUC, precision/recall, calibration", "readmit-xgb",
               "xgboost", ModelAvailability.BLACK_BOX.value,
               FIX + "/clinic_readmit.csv", 2000),
         ["prediction_inspection", "error_analysis", "calibration",
          "data_leakage_checks", "reproducibility"]),
        (_spec("houses", "House prices", "real_estate",
               "Why do price predictions skew high in one segment?",
               TaskType.REGRESSION.value, "Numeric sale price",
               "MAE/RMSE/R², residual analysis", "price-rf", "sklearn",
               ModelAvailability.LOCAL.value, FIX + "/house_prices.csv", 1500),
         ["prediction_inspection", "error_analysis", "reproducibility"]),
        (_spec("energy", "Energy demand", "utilities",
               "Why does the forecaster miss recent demand growth?",
               TaskType.FORECASTING.value, "Daily demand (numeric)",
               "MAE by horizon, drift, split hygiene", "demand-ar",
               "statsmodels", ModelAvailability.BLACK_BOX.value,
               FIX + "/energy_demand.csv", 730),
         ["prediction_inspection", "error_analysis", "data_leakage_checks"]),
        (_spec("customers", "Customer segments", "retail",
               "Are the discovered segments stable and separated?",
               TaskType.CLUSTERING.value, "No labels: segment assignment",
               "Silhouette, stability, size balance", "seg-kmeans",
               "sklearn", ModelAvailability.LOCAL.value,
               FIX + "/customers.csv", 600),
         ["prediction_inspection"]),
        (_spec("blackbox", "Black-box scores", "general",
               "What can be learned from predictions and labels alone?",
               TaskType.CLASSIFICATION.value, "Binary label",
               "AUC, calibration (no pipeline access)", "unknown-remote",
               "api", ModelAvailability.BLACK_BOX.value,
               FIX + "/blackbox_only.csv", 2000),
         ["prediction_inspection", "error_analysis"]),
    ]
    for spec, caps in defs:
        register_project(SyntheticAdapter(spec, caps))
