"""M15 Phase 1 tests: strict measurement + promotion gates (offline).

Real-data assertions live in the flagship demo (slow); here we
verify mathematics on synthetic data plus gate logic.
"""
import numpy as np


def test_auc_report_structure_and_ci():
    from model_autopsy.backend.perf import measure as M
    rng = np.random.default_rng(7)
    y = (rng.random(400) < 0.3).astype(int)
    s = y * 0.6 + rng.random(400) * 0.4
    r = M.auc_report(y, s, dataset="d", split="val (validation)",
                     positive="y=1", period="p", model_version="v")
    assert r["n"] == 400 and r["auc"] > 0.9
    assert r["auc_ci95"][0] <= r["auc"] <= r["auc_ci95"][1]
    for k in ("dataset", "split", "positive_class", "period",
              "model_version", "pr_auc", "brier", "base_rate"):
        assert k in r, k


def test_paired_delta_requires_identical_observations():
    from model_autopsy.backend.perf import measure as M
    import pytest
    with pytest.raises(AssertionError):
        M.paired_delta([0, 1], [0.1, 0.9], [0.2])


def test_paired_delta_detects_real_gain():
    from model_autopsy.backend.perf import measure as M
    rng = np.random.default_rng(7)
    y = (rng.random(2000) < 0.3).astype(int)
    b = y * 0.4 + rng.random(2000) * 0.6
    c = y * 0.7 + rng.random(2000) * 0.3
    d = M.paired_delta(y, b, c)
    assert d["delta"] > 0 and d["significant"] is True
    assert d["delta_ci95"][0] > 0


def test_subgroup_thin_is_inconclusive():
    from model_autopsy.backend.perf import measure as M
    out = M.subgroup_auc([0, 1, 0], [0.1, 0.9, 0.2], ["a", "a", "b"])
    assert out["b"]["auc"] is None and "inconclusive" in out["b"]["note"]


def test_promotion_gate_refuses_unreliable_delta():
    from model_autopsy.backend.perf import promote as PR
    g = PR.gate({"delta": 0.001, "delta_ci95": [-0.001, 0.003],
                 "n": 15000}, 0.14, 0.14,
                {"2025": {"auc": 0.74, "n": 999}},
                {"2025": {"auc": 0.74, "n": 999}})
    assert g["promote"] is False
    assert any("reliably positive" in r for r in g["reasons"])


def test_promotion_gate_blocks_subgroup_regression():
    from model_autopsy.backend.perf import promote as PR
    g = PR.gate({"delta": 0.005, "delta_ci95": [0.001, 0.009],
                 "n": 15000}, 0.14, 0.14,
                {"2026": {"auc": 0.67, "n": 999}},
                {"2026": {"auc": 0.64, "n": 999}})
    assert g["promote"] is False
    assert any("2026" in r for r in g["reasons"])


def test_lab_excludes_leakage_columns():
    from model_autopsy.backend.perf import lab as L
    import pandas as pd
    df = pd.DataFrame({
        "date": pd.to_datetime(["2023-01-01"] * 4),
        "ticker": list("ABCD"), "alpha_spy_2pct": [0, 1, 0, 1],
        "tb_label": [0, 0, 1, 1], "bench_x": [1, 2, 3, 4],
        "feat": [0.1, 0.2, 0.3, 0.4]})
    feats = L.features(df)
    assert feats == ["feat"], feats
    sp = L.chrono_splits(df, "2023-06-01", "2024-01-01")
    assert int(sp["train"].sum()) == 4  # all train: no future leak
    assert int(sp["test"].sum()) == 0
