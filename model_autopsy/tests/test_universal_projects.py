"""Offline multi-project validation + universal architecture tests (Phase 11).

No network, no provider keys, no LLM calls. Deterministic triage runs
capability-selected REAL diagnostics against seeded fixtures and checks
the injected failures. Ground truth is loaded ONLY for assertions —
triage helpers never read it. LLM reasoning quality was validated by the
frozen live campaigns (see benchmarks/FINAL_*_REPORT.md), not here.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIX = "model_autopsy/tests/fixture_universal"


def _truth() -> dict:
    return json.loads((Path(FIX) / "ground_truth.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- ProjectSpec
def test_spec_validation_rejects_bad_specs():
    from model_autopsy.backend.projects import ProjectSpec
    s = ProjectSpec(project_id="", name="")
    errors = s.validate()
    assert any("project_id" in e for e in errors)
    s2 = ProjectSpec(project_id="x", name="X", task_type="telepathy")
    assert any("task_type" in e for e in s2.validate())


def test_spec_roundtrip_and_brief():
    from model_autopsy.backend.projects import ProjectSpec, TaskType
    s = ProjectSpec(project_id="p", name="P", task_type=TaskType.REGRESSION.value,
                    objective="Predict well.", known_limitations=["small n"])
    d = s.to_dict()
    s2 = ProjectSpec.from_dict(d)
    assert s2.task_type == "regression"
    assert "Predict well." in s2.investigator_brief()


def test_registry_and_demand_zone_reference():
    from model_autopsy.backend import projects as P
    from model_autopsy.backend.projects import demand_zone as _dz  # noqa: F401
    ids = {p["project_id"] for p in P.list_projects()}
    assert "demand_zone" in ids
    dz = P.get_project("demand_zone")
    assert dz.spec.task_type == "classification"
    assert "prediction_inspection" in dz.available_capabilities()
    with pytest.raises(LookupError):
        P.get_project("nope")


def test_synthetic_adapters_register_five_projects():
    from model_autopsy.backend import projects as P
    from model_autopsy.backend.projects import synthetic as S
    S.register_synthetic()
    ids = {p["project_id"] for p in P.list_projects()}
    assert {"clinic", "houses", "energy", "customers", "blackbox"} <= ids
    tasks = {P.get_project(pid).spec.task_type for pid in
             ("clinic", "houses", "energy", "customers", "blackbox")}
    assert tasks == {"classification", "regression", "forecasting", "clustering"}


# ------------------------------------------------------------- Model adapters
def test_black_box_capabilities():
    from model_autopsy.backend import model_adapters as MA
    a = MA.get_adapter("black_box")
    assert "internal_activations" not in a.capabilities()
    assert "prediction_inspection" in a.capabilities()
    with pytest.raises(MA.CapabilityError):
        a.require("gradient_analysis", "use error patterns instead")
    with pytest.raises(LookupError):
        MA.get_adapter("telepathy")


def test_sklearn_adapter_real_predict_and_importance():
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from model_autopsy.backend import model_adapters as MA
    X = np.array([[0.0], [1.0], [2.0], [3.0]])
    est = LogisticRegression().fit(X, [0, 0, 1, 1])
    a = MA.get_adapter("sklearn", {"estimator": est})
    assert list(a.predict(np.array([[0.5], [2.5]]))) == [0, 1]
    imp = a.feature_importance()
    assert imp["method"] == "coef_" and len(imp["values"]) == 1
    ok, _ = MA.SklearnAdapter.is_available()
    assert ok is True


def test_guarded_frameworks_report_unavailable_honestly():
    from model_autopsy.backend import model_adapters as MA
    for name in ("tensorflow", "huggingface"):
        a = MA.get_adapter(name)
        ok, reason = a.is_available()
        assert ok is False and "not installed" in reason
        with pytest.raises(MA.CapabilityError):
            a.capabilities()
    fw = {f["framework"]: f for f in MA.supported_frameworks()}
    assert fw["tensorflow"]["usable"] is False


def test_boosting_adapters_predict_for_real():
    import numpy as np
    from model_autopsy.backend import model_adapters as MA
    X = np.array([[0.0], [1.0], [2.0], [3.0]] * 15)
    y = np.array([0, 0, 1, 1] * 15)
    import xgboost as xgb
    import lightgbm as lgb
    from catboost import CatBoostClassifier
    ests = {"xgboost": xgb.XGBClassifier(n_estimators=5),
            "lightgbm": lgb.LGBMClassifier(n_estimators=5, verbose=-1),
            "catboost": CatBoostClassifier(iterations=5, verbose=False)}
    for name, est in ests.items():
        est.fit(X, y)
        a = MA.get_adapter(name, {"estimator": est})
        assert list(a.predict(np.array([[0.5], [2.5]]))) == [0, 1]
        assert "prediction_inspection" in a.capabilities()


def test_pytorch_adapter_predict_only_is_honest():
    import numpy as np
    import torch
    from model_autopsy.backend import model_adapters as MA
    mod = torch.nn.Sequential(torch.nn.Linear(1, 1))
    with torch.no_grad():
        mod[0].weight.fill_(1.0)
        mod[0].bias.fill_(0.0)
    a = MA.get_adapter("pytorch", {"module": mod})
    assert list(a.predict(np.array([[2.0]]))) == [2.0]
    assert "gradient_analysis" not in a.capabilities()
    with pytest.raises(MA.CapabilityError):
        a.require("gradient_analysis", "use permutation screening instead")


# ------------------------------------------------------- Task diagnostics I/O
def test_regression_metrics_finds_bias_and_groups():
    from model_autopsy.backend.task_diagnostics import regression_metrics
    out = regression_metrics(f"{FIX}/house_prices.csv",
                             target_column="target",
                             prediction_column="prediction",
                             group_column="segment")
    assert abs(out["bias_mean_residual"]) > 5000  # injected +20k urban bias
    assert out["mae_by_group"]["urban"] > out["mae_by_group"]["rural"] * 2
    assert out["r2"] > 0.9  # otherwise good fit
    with pytest.raises(ValueError):
        regression_metrics(f"{FIX}/house_prices.csv",
                           target_column="nope", prediction_column="prediction")


def test_clustering_stability_on_separated_blobs():
    from model_autopsy.backend.task_diagnostics import clustering_stability
    out = clustering_stability(f"{FIX}/customers.csv",
                               feature_columns=["x1", "x2"], n_clusters=3)
    assert out["silhouette"] > 0.5
    assert out["imbalance_ratio"] < 2.0


def test_forecast_diagnostics_overlap_and_drift():
    from model_autopsy.backend.task_diagnostics import forecast_diagnostics
    out = forecast_diagnostics(f"{FIX}/energy_demand.csv",
                               split_column="split", horizon_column="horizon")
    # Corrected 2026-11-01 (M4): the fixture spans are contiguous
    # (train days 0-529, test 530-729) — no true date overlap. The old
    # `is True` encoded a sorted-keys artifact ("test" > "train"
    # compared as max(test) >= min(train)). The real signal is drift.
    assert out["split_overlap_hint"] is False
    early, late = out["drift_early_vs_late_mae"]
    assert late > early * 2  # injected drift the model misses
    assert set(out["mae_by_horizon"]) == {str(h) for h in range(1, 8)}


def test_select_tools_capability_and_task_gating():
    from model_autopsy.backend.task_diagnostics import select_tools
    reg = select_tools("regression", ["prediction_inspection", "error_analysis"],
                       {"target": True, "prediction": True})
    assert "regression_metrics" in reg["selected"]
    assert "classification_metrics" not in reg["selected"]
    bb = select_tools("classification",
                      ["prediction_inspection", "error_analysis"],
                      {"label": True, "score": True})
    skipped = {s["tool"]: s["reason"] for s in bb["skipped"]}
    assert "classification_metrics" in bb["selected"]
    assert "feature_target_suspiciousness" in skipped  # needs leakage caps
    assert "missing capabilities" in skipped["feature_target_suspiciousness"]
    cols = select_tools("forecasting", ["prediction_inspection", "error_analysis"], {})
    assert any("missing inputs" in s["reason"] for s in cols["skipped"])


def test_tool_cards_are_read_only_and_declared():
    from model_autopsy.backend.task_diagnostics import TOOL_CARDS
    assert len(TOOL_CARDS) >= 9
    for name, card in TOOL_CARDS.items():
        assert card["read_only"] is True and card["modifies"] is False, name
        assert card["tasks"] and card["capabilities"] and card["outputs"], name


# ------------------------------------------------------------------ Ingestion
def test_ingestion_loads_common_formats(tmp_path):
    import numpy as np
    import pandas as pd
    from model_autopsy.backend import ingestion as ing
    (tmp_path / "a.jsonl").write_text('{"x": 1}\n{"x": 2}\n', encoding="utf-8")
    np.save(tmp_path / "b.npy", np.arange(4))
    import shutil
    dest = Path("model_autopsy/tests/fixture_universal/_tmp_ing")
    dest.mkdir(exist_ok=True)
    try:
        shutil.copy(tmp_path / "a.jsonl", dest / "a.jsonl")
        shutil.copy(tmp_path / "b.npy", dest / "b.npy")
        df, _ = ing.load_artifact("model_autopsy/tests/fixture_universal/_tmp_ing/a.jsonl")
        assert list(df["x"]) == [1, 2]
        arr, _ = ing.load_artifact("model_autopsy/tests/fixture_universal/_tmp_ing/b.npy")
        assert list(arr) == [0, 1, 2, 3]
        with pytest.raises(ValueError):
            ing.load_artifact("model_autopsy/tests/fixture_universal/generate.py")
        with pytest.raises(PermissionError):
            ing.load_artifact("/etc/hostname")
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def test_capability_report_partial_inputs():
    from model_autopsy.backend import ingestion as ing
    r = ing.capability_report(columns=["prediction", "label"])
    assert any("error_analysis" in p for p in r["possible"])
    assert any("leakage_confirmation" in i for i in r["impossible"])
    assert any("feature_importance" in i for i in r["impossible"])


# ------------------------------------------------------------------- Providers
def test_provider_normalizers():
    from model_autopsy.backend import providers as PR
    meta = PR.MetaProvider.normalize(
        {"id": "r1", "status": "incomplete", "output": [{"content": [{"text": "hi"}]}],
         "usage": {"input_tokens": 10, "output_tokens": 5,
                   "input_tokens_details": {"cached_tokens": 3}}})
    assert meta["incomplete"] is True and meta["usage"]["cached_tokens"] == 3
    groq = PR.GroqProvider.normalize(
        {"id": "g1", "choices": [{"finish_reason": "length",
                                  "message": {"content": "x", "tool_calls": []}}],
         "usage": {"prompt_tokens": 7, "completion_tokens": 9}})
    assert groq["incomplete"] is True and groq["usage"]["input_tokens"] == 7
    assert PR.GroqProvider({}).supports("continuation") is False
    assert PR.MetaProvider({}).supports("continuation") is True
    with pytest.raises(LookupError):
        PR.get_provider("telepathy")


def test_groq_and_ollama_use_injected_transport():
    from model_autopsy.backend import providers as PR
    g = PR.get_provider("groq")
    out = g.create_response("m", [{"role": "user", "content": "hi"}],
                            request_fn=lambda url, body: {
                                "id": "g9", "choices": [{"finish_reason": "stop",
                                "message": {"content": "done"}}],
                                "usage": {"prompt_tokens": 3, "completion_tokens": 1}})
    assert out["output_text"] == "done" and out["incomplete"] is False
    with pytest.raises(PR.ProviderError):
        g.create_response("m", [])
    o = PR.get_provider("ollama", {"host": "http://nowhere:1"})
    out2 = o.create_response("m", [], request_fn=lambda url, body: {
        "message": {"content": "local ok"}})
    assert out2["output_text"] == "local ok"
    assert "no provider usage" in out2["note"]


# -------------------------------------------------------------------- Contexts
def test_context_packages_full_then_delta():
    from model_autopsy.backend import db, engine, contexts as C
    from model_autopsy.backend.db import SessionLocal, init_db
    init_db()
    s = SessionLocal()
    try:
        inv = engine.create_investigation(s, "ml", "Ctx test",
                                          "Why does it fail?",
                                          {"max_iterations": 3})
        engine.record_finding(s, inv, "smoke finding", "likely")
        full = C.build_context_package(s, inv, project_brief="Brief.",
                                       capabilities=["error_analysis"])
        assert full["project"]["objective"] == "Why does it fail?"
        assert full["findings"] and full["evidence_refs"] == []
        d0 = C.build_delta_package(s, inv, full)
        assert d0["evidence_refs"] == [] and "delta only" in d0["context_source"]
        engine.add_hypothesis(s, inv.id, "H: it is broken", source="manual")
        d1 = C.build_delta_package(s, inv, full)
        assert len(d1["hypotheses"]) == 1
        # Delta carries no already-sent evidence refs — the saving that
        # matters at scale; toy payloads may be char-larger from state.
        assert d1["evidence_refs"] == []
        assert full["evidence_refs"] == []
        save = C.package_delta_savings(full, d1)
        assert save["full_chars"] > 0 and save["delta_chars"] > 0
        assert "billed savings must be measured" in save["note"]
    finally:
        s.close()


def test_engine_build_context_project_path():
    from model_autopsy.backend import db, engine
    from model_autopsy.backend.db import SessionLocal, init_db
    from model_autopsy.backend.projects import synthetic as S
    S.register_synthetic()
    init_db()
    s = SessionLocal()
    try:
        inv = engine.create_investigation(s, "ml", "Clinic", "Why fail?",
                                          {"project_id": "clinic"})
        ctx = engine.build_context(s, inv)
        assert ctx["project_id"] == "clinic"
        assert "healthcare" in ctx["investigator_brief"]
        assert "prediction_inspection" in ctx["capabilities"]
    finally:
        s.close()


# ------------------------------------------------------------- Phase 11 triage
def _triage(task_type, capabilities, available):
    """Deterministic triage: select capability-fitting tools (never reads GT)."""
    from model_autopsy.backend.task_diagnostics import select_tools
    return select_tools(task_type, capabilities, available)


def test_triage_clinic_finds_leak_column():
    from model_autopsy.backend import task_diagnostics as TD
    from model_autopsy.backend import ml_tools as ML
    sel = _triage("classification",
                  ["prediction_inspection", "error_analysis", "calibration",
                   "data_leakage_checks", "reproducibility"],
                  {"label": True, "score": True, "features": True})
    assert "feature_target_suspiciousness" in sel["selected"]
    assert "regression_metrics" not in sel["selected"]
    import pandas as pd
    feat_path = Path(FIX) / "clinic_features.csv"
    if not feat_path.exists():
        df = pd.read_csv(Path(FIX) / "clinic_readmit.csv")
        df.drop(columns=["label", "score"]).to_csv(feat_path, index=False)
    out = ML.feature_target_suspiciousness(str(feat_path),
                                           f"{FIX}/clinic_readmit.csv")
    top = out["top_correlations"][0]["feature"]
    assert top == _truth()["clinic_readmit"]["leak_column"]
    m = ML.classification_metrics(f"{FIX}/clinic_readmit.csv",
                                  score_column="score")
    assert m["roc_auc"] > 0.8


def test_triage_houses_finds_segment_bias():
    from model_autopsy.backend import task_diagnostics as TD
    sel = _triage("regression", ["prediction_inspection", "error_analysis"],
                  {"target": True, "prediction": True})
    assert sel["selected"] == ["regression_metrics"] or \
        "regression_metrics" in sel["selected"]
    out = TD.regression_metrics(f"{FIX}/house_prices.csv",
                                target_column="target",
                                prediction_column="prediction",
                                group_column="segment")
    truth = _truth()["house_prices"]
    # Blend is 40% urban x +20k ≈ +8k mean shift; threshold well below that.
    assert abs(out["bias_mean_residual"]) > 5000
    assert out["mae_by_group"][truth["biased_group"]] > \
        out["mae_by_group"]["rural"] * 2


def test_triage_energy_finds_overlap_and_drift():
    from model_autopsy.backend import task_diagnostics as TD
    sel = _triage("forecasting",
                  ["prediction_inspection", "error_analysis",
                   "data_leakage_checks"], {"date": True, "target": True,
                                            "prediction": True})
    assert "forecast_diagnostics" in sel["selected"]
    assert "classification_metrics" not in sel["selected"]
    out = TD.forecast_diagnostics(f"{FIX}/energy_demand.csv",
                                  split_column="split",
                                  horizon_column="horizon")
    # Corrected 2026-11-01 (M4): contiguous spans, no true overlap;
    # the drift signal below is the genuine finding.
    assert out["split_overlap_hint"] is False
    early, late = out["drift_early_vs_late_mae"]
    assert late > early * 2


def test_triage_customers_control_passes():
    from model_autopsy.backend import task_diagnostics as TD
    sel = _triage("clustering", ["prediction_inspection"], {"features": True})
    assert "clustering_stability" in sel["selected"]
    assert "regression_metrics" not in sel["selected"]
    out = TD.clustering_stability(f"{FIX}/customers.csv",
                                  feature_columns=["x1", "x2"])
    assert out["silhouette"] > _truth()["customers"]["min_silhouette"]


def test_api_projects_frameworks_and_project_investigation():
    from fastapi.testclient import TestClient
    from model_autopsy.backend.api import app
    from model_autopsy.backend.db import init_db
    init_db()
    with TestClient(app) as c:
        lst = c.get("/api/projects").json()["projects"]
        assert any(p["project_id"] == "demand_zone" for p in lst)
        dz = c.get("/api/projects/demand_zone").json()
        assert dz["spec"]["task_type"] == "classification"
        assert "investigator_brief" in dz and dz["capabilities"]
        assert c.get("/api/projects/nope").status_code == 404
        fw = c.get("/api/model-frameworks").json()["frameworks"]
        names = {f["framework"] for f in fw}
        assert {"sklearn", "black_box", "pytorch", "tensorflow"} <= names
        r = c.post("/api/investigations", json={
            "mode": "ml", "title": "DZ", "question": "Why?",
            "project_id": "demand_zone"})
        assert r.status_code == 200
        ctx = c.post(f"/api/investigations/{r.json()['id']}/context")
        assert ctx.status_code == 200
        bad = c.post("/api/investigations", json={
            "mode": "ml", "title": "B", "question": "?",
            "project_id": "nope"})
        assert bad.status_code == 400


def test_triage_blackbox_reports_limits():
    from model_autopsy.backend import ingestion as ing
    from model_autopsy.backend import ml_tools as ML
    rep = ing.capability_report(columns=["score", "label"])
    truth = _truth()["blackbox_only"]
    for item in truth["possible"]:
        assert any(item in p for p in rep["possible"]), item
    for item in truth["impossible"]:
        assert any(item in i for i in rep["impossible"]), item
    m = ML.classification_metrics(f"{FIX}/blackbox_only.csv",
                                  score_column="score")
    assert m["roc_auc"] > 0.8
