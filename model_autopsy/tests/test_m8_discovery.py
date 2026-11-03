"""M8 Workstream C: diagnostic coverage, selection relevance, stopping."""
import pytest


def _h(hid, text, status="proposed", refs=None):
    return {"id": hid, "text": text, "status": status,
            "evidence_refs": refs or []}


def test_coverage_maps_family_to_measurements():
    from model_autopsy.backend.causal import coverage as CV
    hyps = [_h("h1", "A sudden level shift after day 500 degrades forecasts")]
    cov = CV.coverage(hyps, set())
    assert cov[0]["family"] == "drift"
    assert "temporal_changepoint_scan" in cov[0]["missing"]
    assert cov[0]["covered"] is False
    cov2 = CV.coverage(hyps, {"temporal_changepoint_scan",
                              "residual_time_analysis",
                              "distribution_shift_profile",
                              "forecast_diagnostics"})
    assert cov2[0]["missing"] == []
    assert cov2[0]["covered"] is True
    assert CV.missing_union(hyps, set())


def test_subgroup_gap_demands_per_region_measurement():
    # The M7 lesson: a regional-performance hypothesis must surface the
    # per-region diagnostic as missing — never silently pass on a global
    # metric alone.
    from model_autopsy.backend.causal import coverage as CV
    hyps = [_h("h1", "Ranking performance shows an uneven regional gap; "
                     "one ward underperforms the rest")]
    missing = CV.missing_union(hyps, {"classification_metrics"})
    assert "grouped_auc_comparison" in missing
    cov = CV.coverage(
        hyps, {"classification_metrics", "grouped_auc_comparison"})
    assert cov[0]["missing"] == []


def test_no_hardcoded_benchmark_answers():
    from model_autopsy.backend.causal import coverage as CV
    from model_autopsy.backend.causal import selection as SEL
    for text in ("eval_turbine fails badly", "the turbine artifact is wrong",
                 "m7 scenario seven", "sealed ground truth says nothing"):
        assert CV.family_of(text) == "other", text
        assert SEL._family_of(text) == "other", text


def test_plan_boosts_missing_measurement_with_reason():
    from model_autopsy.backend.causal import planning as PL
    hyps = [_h("h1", "A sudden level shift after day 500 degrades forecasts",
               refs=[{"action_id": "a1"}])]
    plan = PL.plan_next(hyps, {"data_quality_profile"}, {"experiments": 5},
                        already_failed={"artifact_summary"})
    assert "temporal_changepoint_scan" in plan["missing_measurements"]
    assert plan["recommended"], "must recommend something"
    # Every recommended tool fills a missing drift measurement, so each
    # carries the explicit boost rationale.
    assert all("missing measurement" in r["reason"]
               for r in plan["recommended"]), plan["recommended"]
    assert all(r["expected_value"] == "high"
               for r in plan["recommended"])
    assert "artifact_summary" in plan["failed_skipped"]
    assert plan["untested"] == []


def test_plan_first_turn_recommends_safe_starters():
    from model_autopsy.backend.causal import planning as PL
    plan = PL.plan_next([], set(), {"experiments": 6})
    assert plan["recommended"], "first turn must not be an empty brief"
    assert plan["missing_measurements"] == []
    assert plan["coverage"] == []


def test_plan_rejected_not_pursued_and_untested():
    from model_autopsy.backend.causal import planning as PL
    hyps = [_h("h1", "level shift degrades forecasts", status="rejected",
               refs=[{"action_id": "a1"}]),
            _h("h2", "null values corrupt training")]
    plan = PL.plan_next(hyps, set(), {"experiments": 6})
    assert plan["rejected_not_pursued"] == ["h1"]
    assert plan["untested"] == ["h2"]


def test_plan_never_recommends_inapplicable_tools():
    from model_autopsy.backend.causal import planning as PL
    hyps = [_h("h1", "One ward underperforms the rest")]
    plan = PL.plan_next(hyps, set(), {"experiments": 6},
                        already_inapplicable={"grouped_auc_comparison"})
    assert "grouped_auc_comparison" not in plan["ranked_all"]
    assert plan["inapplicable_skipped"] == ["grouped_auc_comparison"]


def test_stopping_rules():
    from model_autopsy.backend.causal import planning as PL
    # All resolved -> stop, even with budget left.
    stop, why = PL.stopping(
        "investigating", [_h("h1", "x", status="supported")], 1, 6)
    assert stop and "resolved" in why
    # Budget exhausted with untested hypotheses -> stop, honestly.
    stop, why = PL.stopping(
        "investigating", [_h("h1", "level shift x")], 6, 6)
    assert stop and "never tested" in why
    # Open + untested + budget left -> continue.
    stop, why = PL.stopping(
        "investigating", [_h("h1", "level shift x")], 1, 6)
    assert not stop and "remain" in why


def test_selection_explains_rejection_of_redundant():
    from model_autopsy.backend.causal import selection as SEL
    hyps = [{"text": "A sudden level shift after day 500 degrades forecasts"}]
    ranked = SEL.rank_candidates(["temporal_changepoint_scan",
                                  "data_quality_profile"], hyps,
                                 {"temporal_changepoint_scan"})
    dup = [r for r in ranked
           if r["tool"] == "temporal_changepoint_scan"][0]
    assert dup["redundant"] is True
    assert dup["expected_value"] == "low"
    expl = SEL.explain_selection(ranked)
    assert "temporal_changepoint_scan" in expl or "data_quality" in expl
