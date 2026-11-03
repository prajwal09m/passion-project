"""M14 Phase 4-8 tests (offline, deterministic)."""


def test_live_audit_and_tracking():
    from model_autopsy.backend.live import audit as A
    out = A.audit_run("model_autopsy/benchmarks/live_runs/live-d8b174527ca5")
    assert out["stages"]["reporting"]["has_report"] is True
    assert out["opportunities"], "every tool is an opportunity row"
    assert all("lost_at" in o for o in out["opportunities"])
    t = A.track("x", True, False, False, True, False, False, False)
    assert t["lost_at"] == "recognized" and t["diagnosable"]


def test_parity_replay_offline():
    from model_autopsy.backend.live import parity as P
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm
    from model_autopsy.backend import db as DB
    from model_autopsy.backend import engine
    e = _ce("sqlite:///:memory:")
    DB.Base.metadata.create_all(e)
    s = _sm(bind=e, autoflush=False, expire_on_commit=False)()
    try:
        inv = engine.create_investigation(
            s, "ml", "parity", "b",
            {"max_iterations": 3,
             "predictions_path":
             "model_autopsy/tests/fixture_eval/investigator/credit_default.csv"})
        out = P.replay(
            "model_autopsy/benchmarks/live_runs/live-d8b174527ca5",
            s, inv)
        assert out["ok"] in (True, False)
        assert "note" in out
    finally:
        s.close()


def test_risk_hypotheses_are_priorities_not_defects():
    from model_autopsy.backend.research import risk as R
    from model_autopsy.backend.research import invention as INV
    facts = INV.artifact_facts(
        "model_autopsy/tests/fixture_m10b/b_unit_shift.csv")
    risks = R.prioritize(R.hypothesize(facts))
    assert risks and all(r["status"] == "risk-hypothesis" for r in risks)
    assert all(r["missing_evidence"] for r in risks)
    w = R.early_warning(risks[0],
                        "model_autopsy/tests/fixture_m10b/b_unit_shift.csv")
    assert w["tool"] and w["why"]


def test_strategy_rank_and_compare():
    from model_autopsy.backend.research import strategies as S
    cands = [{"tool": "data_quality_profile",
              "info_value": {"distinguishes_n": 1},
              "est_cost": {"relative": 2}},
             {"tool": "residual_feature_dependence",
              "info_value": {"distinguishes_n": 2},
              "est_cost": {"relative": 1}}]
    assert S.rank("info-value", cands)[0]["tool"] == \
        "residual_feature_dependence"
    assert S.rank("m13-baseline", cands)
    cmp_ = S.compare({"m13-baseline": {"discovery_recall": 0.5},
                      "combined": {"discovery_recall": 0.7}})
    import pytest as _pt
    assert cmp_["combined"]["delta_vs_baseline"] == _pt.approx(0.2)


def test_falsification_and_confidence_layers():
    from model_autopsy.backend.m12 import falsify as F
    plan = F.falsification_plan({"id": "h", "text": "zone gap",
                                 "predicted_observation": "persists"})
    assert plan["outcome"] == "not-run" and plan["survived"] is None
    layers = F.confidence_layers([{"relation": "supports"}],
                                 [{"grade": "reproduced"}])
    assert layers["causal"] == "low"  # never auto-high
    assert layers["reproduction"] == "high"
    rep = F.structured_report({"confirmed": [1], "rejected": [2]})
    assert set(rep) == {"confirmed", "strong", "plausible",
                        "unresolved", "rejected", "untested_risks",
                        "inconclusive"}


def test_network_transfer_requires_evidence():
    from model_autopsy.backend.m12 import network as N
    rel = N.relationships([{"id": "a", "columns": ["zone", "x"]},
                           {"id": "b", "columns": ["zone", "y"]}])
    assert rel["edges"]
    p = N.propose_transfer({"project_id": "a", "content": "zone gap"},
                           {"id": "b"})
    assert p["treat_as"].startswith("hypothesis")
    v = N.validate_transfer(p, [{"relation": "supports"}], True)
    assert v["validated"] is True
    v2 = N.validate_transfer(p, [{"relation": "relevant_to"}], False)
    assert v2["validated"] is False
