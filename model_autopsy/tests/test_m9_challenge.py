"""M9 research-laboratory challenge (offline, autonomous loop)."""
from model_autopsy.backend.db import SessionLocal, init_db


def test_truth_sealed_from_autonomous_path():
    from model_autopsy.backend.eval import m9_challenge as M9
    audit = M9.check_no_truth_leak()
    assert audit["ok"], audit["offenders"]


def test_dev_scenarios_research_autonomously():
    from model_autopsy.backend.eval import m9_challenge as M9
    init_db()
    out = M9.evaluate_all(SessionLocal, include_held_out=False)
    assert len(out["scenarios"]) == 4
    for row in out["scenarios"]:
        assert row["agenda"], row["scenario"]  # questions generated
        assert all(q.get("priority_reason") for q in row["agenda"]
                   ), row["scenario"]  # prioritized with reasons
        assert row["specs_executed"], row["scenario"]  # invented + ran
        assert row["tool_calls"] <= 6, row["scenario"]
        assert row["fallback_valid"], row["scenario"]
        assert set(row["dimensions"]) == {
            "project_understanding", "research_planning", "discovery",
            "experiment_invention", "experiment_selection",
            "causal_reasoning", "confounder_handling",
            "evidence_attribution", "hypothesis_management",
            "reporting_validity", "calibration", "reproducibility",
            "efficiency"}, row["scenario"]
    means = out["dimension_means"]
    assert means["evidence_attribution"] == 1.0  # no denial violated
    assert means["experiment_invention"] == 1.0
    assert means["research_planning"] == 1.0
    assert means["reporting_validity"] == 1.0
    assert means["efficiency"] == 1.0


def test_nn_slice_discovers_segment_failure():
    from model_autopsy.backend.eval import m9_challenge as M9
    init_db()
    s = SessionLocal()
    try:
        behavior = M9.run_scenario("m9_nn_slice", s)
    finally:
        s.close()
    assert "classification_metrics" in behavior["ran_tools"]
    dims = M9.score_dimensions(
        {**behavior, "investigation_id": None}, "m9_nn_slice", s)
    assert dims["dimensions"]["discovery"] == 1.0


def test_held_out_runs_safely_and_reports():
    from model_autopsy.backend.eval import m9_challenge as M9
    init_db()
    out = M9.evaluate_all(SessionLocal, include_held_out=True)
    held = [r for r in out["scenarios"] if r["held_out"]]
    assert len(held) == 4
    for row in held:
        assert row["tool_calls"] <= 6, row["scenario"]
        assert row["fallback_valid"], row["scenario"]
        assert row["agenda"], row["scenario"]
    assert out["held_out_means"]
