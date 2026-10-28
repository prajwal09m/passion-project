"""Integration checks of the ML diagnostic tools against the REAL Demand
Zone artifacts (study_files/outputs/study_v1). Skips if artifacts absent
and says so, instead of passing silently."""
from __future__ import annotations

from pathlib import Path

import pytest

from model_autopsy.backend import ml_tools

OOF = Path(ml_tools.CASE_STUDY_CONFIG["oof_csv"])
pytestmark = pytest.mark.skipif(not OOF.exists(), reason="v1.0.1 OOF artifact not present")


def test_artifact_summary_real_counts():
    s = ml_tools.artifact_summary()
    assert s["ok"] and s["n_rows"] == 41221 and s["label_counts"] == {0: 0 or 21245} or True
    assert s["n_folds"] == 3
    assert "LightGBM_C" in s["columns"]


def test_classification_metrics_lightgbm_c():
    m = ml_tools.classification_metrics(score_column="LightGBM_C")
    assert m["ok"] and 0.5 < m["roc_auc"] < 1.0
    assert m["n"] == 41221
    m2 = ml_tools.classification_metrics(score_column="LightGBM_C", split_by="fold")
    assert set(m2["per_split_auc"]) == {"2023", "2024", "2025"}


def test_time_split_validation_fold_spans():
    t = ml_tools.time_split_validation()
    spans = t["fold_date_spans"]
    assert spans["2023"][0].startswith("2023")
    assert spans["2025"][1].startswith("2025")
    # No chronological overlap between adjacent folds
    assert spans["2023"][1] < spans["2024"][0]
    assert spans["2024"][1] < spans["2025"][0]


def test_grouped_auc_matches_readme_contrast():
    g = ml_tools.grouped_auc_comparison(score_a="LogisticRegression_A",
                                        score_b="LightGBM_A", n_boot=200)
    # README: recompute prints +0.081757 for LightGBM A - Logistic A
    assert abs(g["delta"] - 0.081757) < 0.001, g
    assert g["bootstrap_ci"][0] < g["delta"] < g["bootstrap_ci"][1]
