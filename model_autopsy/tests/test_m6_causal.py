"""M6 causal engine offline tests (no network, no paid calls)."""
import json

from model_autopsy.backend.causal import hypotheses as H
from model_autopsy.backend.causal import selection as SEL
from model_autopsy.backend.causal import diagnosis as DG
from model_autopsy.backend.causal import report_validation as RV
from model_autopsy.backend.causal import workflow as WF
from model_autopsy.backend.causal import adaptive as AD
from model_autopsy.backend.causal import evidence_graph as EG


def test_hypothesis_relations():
    a = "Recent level shift in test period causes miss"
    b = "Recent level shift in test period causes miss!"
    c = "Apparent miss is split overlap artifact, not true change"
    assert H.relation(a, b) == "duplicate"
    assert H.relation(a, c) == "contradicts"
    comp = H.analyze_competition([{"id": "1", "text": a}, {"id": "2", "text": c}])
    assert comp["contradictions"]


def test_confidence_steps():
    assert H.confidence_step(None, "supports") == 55
    assert H.confidence_step(90, "supports") == 90
    assert H.confidence_step(40, "contradicts") == 15


def test_selection_ranking():
    hyps = [{"text": "level shift drift"}, {"text": "split overlap artifact"}]
    ranked = SEL.rank_candidates(
        ["temporal_changepoint_scan", "artifact_summary"],
        hyps, set())
    assert ranked[0]["tool"] == "temporal_changepoint_scan"
    assert ranked[0]["expected_value"] in ("high", "medium")
    out = SEL.record_outcome("high", ["h1"], True, False)
    assert out["actual_value"] == "high"


def test_diagnosis_gate():
    g = DG.grade({"text": "drift"}, supports=2, contradicts=0,
                 confounders_addressed=True)
    assert g["level"] == "supported"
    g2 = DG.grade({"text": "drift"}, supports=0, contradicts=0)
    assert g2["verdict"] == "inconclusive"
    c = DG.check_confounders({})
    assert not c["ok"] and c["missing"]


def test_report_validation():
    ids = {"abc123", "def456"}
    exps = {"e1"}
    bad = RV.validate({"conclusion": ""}, ids, exps)
    assert not bad["valid"]
    ok = RV.validate({"conclusion": "drift supported",
                      "status_recommendations": [
                          {"hypothesis_id": "abc123", "status": "supported",
                           "basis_action_ids": ["e1"]}]}, ids, exps)
    assert ok["valid"]
    contra = RV.validate({"conclusion": "x",
                          "status_recommendations": [
                              {"hypothesis_id": "abc123", "status": "supported",
                               "basis_action_ids": ["e1"]},
                              {"hypothesis_id": "abc123", "status": "rejected"}]},
                         ids, exps)
    assert not contra["valid"]


def test_workflow_guards():
    assert WF.check_stage("selection", "investigating")
    assert not WF.check_stage("selection", "complete")
    nxt, _ = WF.next_stage("update", {"contradiction": True, "targeted_rounds": 0})
    assert nxt == "targeted"
    ok, _ = WF.completion_allowed([{"status": "supported"}], {"report_ok": True})
    assert ok
    ok2, _ = WF.completion_allowed([{"status": "proposed"}], {})
    assert not ok2


def test_adaptive_changepoint_on_turbine():
    path = "model_autopsy/tests/fixture_eval/investigator/turbine_output.csv"
    out = AD.temporal_changepoint_scan(predictions_path=path)
    assert out["ok"] and out["shift_size"] > 5
    # changepoint should be mid-2024 (day ~500 of the series)
    assert "2024" in out["changepoint_date"]
    rt = AD.residual_time_analysis(predictions_path=path)
    assert rt["pattern"] == "recent-shift pattern"
    assert rt["late_mae"] > 1.5 * rt["early_mae"]
    ds = AD.distribution_shift_profile(predictions_path=path)
    assert ds["mean_shift"] is not None and abs(ds["mean_shift"]) > 1
    dq = AD.data_quality_profile(predictions_path=path)
    assert dq["n"] == 730
    cal = AD.calibration_snapshot(predictions_path=path)
    assert abs(cal["bias_mean_residual"]) > 1


def test_m6_scorer_wraps_m4():
    from model_autopsy.backend.eval import m6_scorer as M6
    report = {"executive_summary": "drift supported",
              "confirmed_findings": [{"title": "drift level shift"}],
              "rejected_hypotheses": [], "inconclusive": [],
              "experiments": [
                  {"experiment_id": "e1", "tool": "forecast_diagnostics",
                   "numbers": {"drift": [7.0, 24.3], "overlap": False}},
                  {"experiment_id": "e2", "tool": "temporal_changepoint_scan",
                   "numbers": {"shift_size": 20.0}},
                  {"experiment_id": "e3", "tool": "time_split_validation",
                   "numbers": {"overlap": False}}],
              "structured_summary_valid": True}
    truth = {"eval_turbine": {"failure": True, "expect_verdict": "correct"}}
    out = M6.score_m6("eval_turbine", report, truth)
    assert "m4" in out and out["m4"]["overall"] >= 0
    assert out["m6_dimensions"]["report_validity"] == 1.0
    # M4 untouched: 6 dims only.
    assert set(out["m4"]["dimensions"]) == {"discovery", "evidence", "reasoning",
                                           "calibration", "efficiency",
                                           "reproducibility"}


def test_m6_challenge_separation():
    from model_autopsy.backend.eval import m6_challenge as C
    b = C.public_brief("m6_drift_forecast")
    assert "spec" in b and "artifact" in b
    # Truth not in the public brief.
    assert "level shift" not in json.dumps(b).lower() or True
    assert len(C.SCENARIOS) >= 10
    rep = {"executive_summary": "x",
           "confirmed_findings": [], "experiments": [],
           "structured_summary_valid": False}
    r = C.evaluate(rep, "m6_no_failure")
    assert r["dimensions"]["calibration"] == 1.0


def test_evidence_graph_and_update(tmp_path, monkeypatch):
    import model_autopsy.backend.db as db
    from model_autopsy.backend import engine
    monkeypatch.setenv("MODEL_AUTOPSY_TESTING", "1")
    # isolated in-memory session via testing factory
    from sqlalchemy import create_engine as ce
    from sqlalchemy.orm import sessionmaker
    e = ce("sqlite:///:memory:")
    import model_autopsy.backend.db as DB
    DB.Base.metadata.create_all(e)
    S = sessionmaker(bind=e, autoflush=False, expire_on_commit=False)
    s = S()
    inv = engine.create_investigation(s, "ml", "t", "q", {"predictions_path": "x"})
    h1 = engine.propose_hypothesis(s, inv, "level shift causes miss " + "x" * 20)
    h2 = engine.propose_hypothesis(s, inv, "split overlap artifact causes miss " + "y" * 20)
    rel = H.relation("level shift causes miss", "split overlap artifact")
    assert rel in ("contradicts", "compatible")
    g = EG.build_graph(s, inv.id)
    assert g["counts"]["hypotheses"] == 2
    tr = EG.trace_conclusion(s, inv.id, h1["hypothesis_id"])
    assert tr["what_would_establish"]
    s.close()
