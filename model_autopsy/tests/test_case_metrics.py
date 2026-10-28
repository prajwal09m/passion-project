"""Chart-data endpoint module (Phase 3): real recomputation from frozen
artifacts; skipped honestly when the artifact is absent."""
from __future__ import annotations

from pathlib import Path

import pytest

from model_autopsy.backend import ml_tools
from model_autopsy.backend.meta_api import case_metrics

OOF = Path(ml_tools.CASE_STUDY_CONFIG["oof_csv"])
pytestmark = pytest.mark.skipif(not OOF.exists(),
                                reason="v1.0.2 OOF artifact not present")


def test_pooled_auc_reproduces_known_values():
    m = case_metrics.build_case_metrics(n_boot=120)
    assert m["recomputed_live"] is True and m["n_rows"] == 41221
    assert abs(m["pooled_auc"]["LightGBM_A"] - 0.671835) < 0.001
    assert abs(m["pooled_auc"]["LightGBM_C"] - 0.683495) < 0.001
    assert abs(m["pooled_auc"]["LogisticRegression_A"] - 0.590078) < 0.001


def test_delta_pairs_and_bootstrap_honesty():
    m = case_metrics.build_case_metrics(n_boot=120)
    by_pair = {(p["score_a"], p["score_b"]): p for p in m["delta_auc_pairs"]}
    p = by_pair[("LogisticRegression_A", "LightGBM_A")]
    assert abs(p["delta"] - 0.081757) < 0.002
    assert p["ci_low"] < p["delta"] < p["ci_high"]
    assert "design" in p and "sampling_unit" in p
    # bootstrap assumption must be reported, either cluster or labeled row-level
    assert "bootstrap" in p["design"]
    assert p["sampling_unit"] in ("ticker", "row")
    if p["sampling_unit"] == "row":
        assert "LIMITATION" in p["design"]     # row-level must be labeled


def test_calibration_and_chronology_present():
    m = case_metrics.build_case_metrics(n_boot=100)
    c = m["calibration"]
    assert c["arm"] == "LightGBM_C" and len(c["reliability_bins"]) >= 5
    chron = m["chronology"]
    assert chron["non_overlapping_adjacent_folds"] is True
    assert set(m["fold_sizes"]) == {"2023", "2024", "2025"}
    assert m["label_balance"]["n_rows"] == 41221
    assert "cannot be recomputed" in m["historical_claim_note"]
