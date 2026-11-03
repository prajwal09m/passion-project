"""Demand Zone AI reference adapter (Phase 2).

The original project, unchanged in behavior, expressed through the
universal interface. Existing diagnostics, benchmarks, and dashboard
routes keep working; this adapter only *describes* the project.
"""
from __future__ import annotations

from . import (DatasetMetadata, ModelAvailability, ModelMetadata, ProjectAdapter,
               ProjectSpec, TaskType, register_project)


def demand_zone_spec() -> ProjectSpec:
    from .. import config
    root = str(config.PROJECT_ROOT)
    return ProjectSpec(
        project_id="demand_zone",
        name="Demand Zone AI",
        description="Frozen v1.0.2 champion: tabular stock-movement classifier "
                    "investigated for out-of-fold underperformance.",
        domain="finance",
        objective="Why does the model underperform on out-of-fold data?",
        task_type=TaskType.CLASSIFICATION.value,
        target_definition="Binary label: 1 = favorable price movement, 0 = otherwise.",
        evaluation_methodology="Out-of-fold ROC-AUC pooled and per-fold, plus "
                               "calibration (Brier, reliability bins).",
        known_limitations=["historical 0.97→0.676 AUC narrative refers to a "
                           "dataset not present in this repository"],
        model=ModelMetadata(
            name="LightGBM_C (champion)",
            architecture="gradient-boosted decision trees",
            framework="lightgbm",
            version="v1.0.2 frozen",
            task="classification",
            output_schema={"score_columns": ["LogisticRegression_A", "LightGBM_A",
                                            "LogisticRegression_B", "LightGBM_B",
                                            "LogisticRegression_C", "LightGBM_C",
                                            "LogisticRegression_D", "LightGBM_D"]},
            artifacts={"oof_csv": root + "/study_files/outputs/study_v1/"
                                    "development/oof_predictions.csv"},
            availability=ModelAvailability.BLACK_BOX.value),
        dataset=DatasetMetadata(
            location="study_files/outputs/study_v1/development/oof_predictions.csv",
            target={"name": "label", "type": "binary", "values": [0, 1]},
            n_rows=41221,
            partitions={"folds": ["2023", "2024", "2025"]},
            temporal_structure={"grouping": "ticker", "date_columns": ["date"]},
            provenance="frozen v1.0.2 study outputs"))


class DemandZoneAdapter(ProjectAdapter):
    def available_capabilities(self) -> list[str]:
        return ["prediction_inspection", "error_analysis", "calibration",
                "data_leakage_checks", "reproducibility"]


register_project(DemandZoneAdapter(demand_zone_spec()))
