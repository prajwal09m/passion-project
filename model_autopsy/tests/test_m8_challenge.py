"""M8 Workstream D: blind challenge over all 12 scenarios (offline)."""
from model_autopsy.backend.db import SessionLocal, init_db


def test_truth_sealed_from_investigator_path():
    from model_autopsy.backend.eval import m8_challenge as M8
    audit = M8.check_no_truth_leak()
    assert audit["ok"], audit["offenders"]


def test_all_twelve_scenarios_behave():
    from model_autopsy.backend.eval import m8_challenge as M8
    init_db()
    out = M8.evaluate_all(SessionLocal)
    assert len(out["scenarios"]) == 12
    for row in out["scenarios"]:
        assert row["evidence_refs_ok"], row["scenario"]
        assert row["failed_refs"] == 0, row["scenario"]
        assert row["duplicate_tools"] == 0, row["scenario"]
        assert row["tool_calls"] <= 6, row["scenario"]
        assert row["stop_rationale"], row["scenario"]
        assert row["single_evidence_supported"] == 0, row["scenario"]
        assert row["fallback_valid"], row["scenario"]
        assert row["report_keys_ok"], row["scenario"]
        assert set(row["dimensions"]) == {
            "discovery", "diagnostic_coverage", "experiment_selection",
            "evidence_quality", "hypothesis_management", "causal_reasoning",
            "calibration", "reporting_validity", "efficiency",
            "reproducibility"}, row["scenario"]
    means = out["dimension_means"]
    # Hard behavioral floors: provenance, corroboration discipline, budget.
    assert means["evidence_quality"] == 1.0
    assert means["causal_reasoning"] >= 0.5
    assert means["efficiency"] == 1.0
    assert means["reporting_validity"] == 1.0


def test_subgroup_scenarios_resolve_coverage():
    from model_autopsy.backend.eval import m8_challenge as M8
    init_db()
    s = SessionLocal()
    try:
        tab = M8.run_closed_loop("m6_single_tabular", s)
    finally:
        s.close()
    assert "classification_metrics" in tab["ran_tools"]
    # Per-region AUC ran: the missing set strictly shrinks. Full 1.0 is not
    # expected: grouped_auc_comparison needs two score columns and this
    # artifact has one — honestly skipped as inapplicable, not faked.
    assert set(tab["missing_after"]) < set(tab["missing_before"]), tab
    assert "grouped_auc_comparison" in tab["skipped_inapplicable"], tab
    dims = M8.score_dimensions(tab, "m6_single_tabular")
    assert dims["dimensions"]["discovery"] == 1.0
    assert dims["dimensions"]["diagnostic_coverage"] > 0, tab


def test_correct_null_scenarios_do_not_overclaim():
    from model_autopsy.backend.eval import m8_challenge as M8
    init_db()
    for sid in ("m6_no_failure", "m6_weak_signal", "m6_inconclusive"):
        s = SessionLocal()
        try:
            behavior = M8.run_closed_loop(sid, s)
        finally:
            s.close()
        assert "supported" not in behavior["statuses"], sid
        dims = M8.score_dimensions(behavior, sid)
        assert dims["dimensions"]["calibration"] == 1.0, sid
