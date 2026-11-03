"""M9 Workstream 3/5/6: adapters, data profile, research memory."""
import pytest

from model_autopsy.backend.db import SessionLocal, init_db


def test_adapter_registry_reports_honestly():
    from model_autopsy.backend import model_adapters as MA
    fw = {f["framework"]: f for f in MA.supported_frameworks()}
    assert fw["sklearn"]["usable"] is True
    assert "prediction_inspection" in fw["sklearn"]["capabilities"]
    assert fw["tensorflow"]["usable"] is False
    assert "not installed" in fw["tensorflow"]["reason"] or \
        "not implemented" in fw["tensorflow"]["reason"]
    with pytest.raises(LookupError):
        MA.get_adapter("no_such_framework")


def test_sklearn_adapter_end_to_end_predictions():
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from model_autopsy.backend import model_adapters as MA
    import pandas as pd
    df = pd.read_csv("model_autopsy/tests/fixture_eval/investigator/"
                     "credit_default.csv", nrows=400)
    X = df[["age", "income", "tenure", "delinq"]].to_numpy(float)
    y = df["label"].to_numpy(int)
    est = LogisticRegression(max_iter=2000).fit(X, y)
    ad = MA.get_adapter("sklearn", {"estimator": est})
    assert "feature_importance" in ad.capabilities()
    preds = ad.predict(X[:5])
    assert len(preds) == 5
    imp = ad.feature_importance()
    assert imp["method"] == "coef_" and len(imp["values"]) == 4


def test_pytorch_adapter_predict_only_and_guarded_absent():
    import numpy as np
    from model_autopsy.backend import model_adapters as MA
    import torch.nn as nn
    ad = MA.get_adapter("pytorch", {"module": nn.Linear(2, 1)})
    assert ad.capabilities() == ["prediction_inspection", "error_analysis"]
    out = ad.predict(np.zeros((3, 2)))
    assert out.shape == (3,)
    tf = MA.get_adapter("tensorflow")
    with pytest.raises(MA.CapabilityError):
        tf.capabilities()
    with pytest.raises(MA.CapabilityError):
        MA.get_adapter("sklearn", {}).predict(np.zeros((2, 2)))


def test_data_profile_reports_facts_with_limits():
    from model_autopsy.backend.research import data_profile as DP
    p = DP.profile("model_autopsy/tests/fixture_eval/investigator/"
                   "rent_estimates.csv")
    assert p["readable"] is True
    assert p["subgroup_structure"]["column"] == "district"
    assert set(p["subgroup_structure"]["cardinality"]) == {"A", "B", "C"}
    assert "label_prevalence" in p["subgroup_structure"]
    assert p["assumptions"] and p["limits"]
    clf = DP.profile("model_autopsy/tests/fixture_eval/investigator/"
                     "credit_default.csv")
    assert clf["class_imbalance_ratio"] > 1.0
    assert clf["subgroup_structure"]["column"] == "region"
    bad = DP.profile("no/such.csv")
    assert bad["readable"] is False


def test_memory_store_requires_provenance():
    from model_autopsy.backend.research import memory as MEM
    init_db()
    s = SessionLocal()
    try:
        with pytest.raises(ValueError):
            MEM.store(s, "methodology", "f", "m", "s", {})
        with pytest.raises(ValueError):
            MEM.store(s, "gossip", "f", "m", "s", {"run_id": "r"})
    finally:
        s.close()


def test_memory_retrieve_and_transfer_rules():
    from model_autopsy.backend.research import memory as MEM
    init_db()
    s = SessionLocal()
    try:
        MEM.store(s, "methodology", "regression", "district bias screen",
                  "grouped MAE comparison", {"run_id": "r1",
                                             "artifact": "rent.csv"})
        MEM.store(s, "finding", "regression", "district C fails",
                  "C MAE 6x", {"run_id": "r1", "artifact": "rent.csv"})
        MEM.store(s, "failure", "regression", "pooled metric suffices",
                  "missed segment", {"run_id": "r1",
                                     "artifact": "rent.csv"})
        res = MEM.retrieve(s, "regression", "district bias screening")
        kinds = {e["kind"]: e["transfer"] for e in res["entries"]}
        assert kinds["methodology"] == "reuse"
        assert kinds["finding"] == "verify-first"
        assert kinds["failure"] == "avoid-repeat"
        # Other families never transfer.
        assert MEM.retrieve(s, "ranking", "district bias")["n"] == 0
    finally:
        s.close()


def test_applicable_prior_demands_same_artifact():
    from model_autopsy.backend.research import memory as MEM
    init_db()
    s = SessionLocal()
    try:
        MEM.store(s, "methodology", "classification", "region AUC split",
                  "split_by region", {"run_id": "r2",
                                      "artifact": "credit.csv"})
        out = MEM.applicable_prior(s, "classification",
                                   "region AUC split", "other.csv")
        assert out["reusable"] == []
        assert out["warnings"], "different artifact: verify-first"
        out2 = MEM.applicable_prior(s, "classification",
                                    "region AUC split", "credit.csv")
        assert len(out2["reusable"]) == 1
    finally:
        s.close()
