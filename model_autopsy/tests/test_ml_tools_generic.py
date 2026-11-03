"""Non-probability scores and custom label columns (COMPAS-driven).

classification_metrics must stay useful on rank-scale scores (AUC is
rank-based) instead of failing the whole diagnostic, and
feature_target_suspiciousness must accept a named label column instead
of KeyErroring on files without a 'label' column.
"""
import numpy as np
import pandas as pd

from model_autopsy.backend import ml_tools


def _write(tmp_path, monkeypatch, name, df):
    monkeypatch.setattr(ml_tools, "PROJECT_ROOT", tmp_path)
    p = tmp_path / name
    df.to_csv(p, index=False)
    return name


def test_classification_metrics_decile_scores(tmp_path, monkeypatch):
    rng = np.random.default_rng(7)
    y = (rng.random(200) < 0.4).astype(int)
    score = np.clip(y * 6 + rng.integers(1, 5, 200), 1, 10)
    name = _write(tmp_path, monkeypatch, "dec.csv",
                  pd.DataFrame({"decile_score": score, "label": y,
                                "grp": ["a"] * 100 + ["b"] * 100}))
    m = ml_tools.classification_metrics(predictions_path=name,
                                        score_column="decile_score",
                                        split_by="grp")
    assert m["ok"] and m["roc_auc"] is not None and m["roc_auc"] > 0.5
    assert m["brier"] is None and m["score_scale_note"]
    assert set(m["per_split_auc"]) == {"a", "b"}


def test_classification_metrics_probabilities_unchanged(tmp_path, monkeypatch):
    rng = np.random.default_rng(7)
    y = (rng.random(200) < 0.4).astype(int)
    p = np.clip(y * 0.6 + rng.random(200) * 0.3, 0.01, 0.99)
    name = _write(tmp_path, monkeypatch, "prob.csv",
                  pd.DataFrame({"score": p, "label": y}))
    m = ml_tools.classification_metrics(predictions_path=name,
                                        score_column="score")
    assert m["ok"] and m["brier"] is not None
    assert m["score_scale_note"] is None
    assert 0.0 <= m["precision_at_threshold"] <= 1.0


def test_suspiciousness_custom_label_single_file(tmp_path, monkeypatch):
    rng = np.random.default_rng(11)
    y = (rng.random(150) < 0.5).astype(int)
    name = _write(tmp_path, monkeypatch, "custom.csv",
                  pd.DataFrame({"two_year_recid": y,
                                "leak_like": y,
                                "noise": rng.random(150)}))
    s = ml_tools.feature_target_suspiciousness(
        feature_csv=name, label_column="two_year_recid")
    top = {r["feature"]: r["abs_r"] for r in s["top_correlations"]}
    assert top["leak_like"] > 0.9
    assert "two_year_recid" not in top


def test_suspiciousness_custom_label_separate_files(tmp_path, monkeypatch):
    rng = np.random.default_rng(11)
    y = (rng.random(150) < 0.5).astype(int)
    feats = _write(tmp_path, monkeypatch, "f.csv",
                   pd.DataFrame({"x": y, "z": rng.random(150)}))
    labs = _write(tmp_path, monkeypatch, "l.csv",
                  pd.DataFrame({"two_year_recid": y}))
    s = ml_tools.feature_target_suspiciousness(
        feature_csv=feats, label_csv=labs, label_column="two_year_recid")
    assert s["top_correlations"][0]["feature"] == "x"


def test_suspiciousness_legacy_label_default(tmp_path, monkeypatch):
    rng = np.random.default_rng(11)
    y = (rng.random(100) < 0.5).astype(int)
    name = _write(tmp_path, monkeypatch, "legacy.csv",
                  pd.DataFrame({"label": y, "x": y}))
    s = ml_tools.feature_target_suspiciousness(feature_csv=name)
    assert s["top_correlations"][0]["feature"] == "x"
