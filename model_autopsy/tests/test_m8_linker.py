"""M8 Workstream C: the linker connects subgroup/calibration evidence.

These run the REAL tools on the REAL fixtures and verify the backend —
not the model — links the measured gaps to the matching hypotheses
with the honest direction. Single evidence moves a hypothesis to
`investigating`, never straight to `supported` (corroboration bar).
"""
from model_autopsy.backend.db import Action, SessionLocal, init_db

CREDIT = "model_autopsy/tests/fixture_eval/investigator/credit_default.csv"
RENT = "model_autopsy/tests/fixture_eval/investigator/rent_estimates.csv"


def _inv(s, tool, args, htext):
    import os
    os.environ["MODEL_AUTOPSY_TESTING"] = "1"
    from model_autopsy.backend import engine
    inv = engine.create_investigation(s, "ml", "t", "q",
                                      {"max_tool_calls": 6})
    h = engine.add_hypothesis(s, inv.id, htext, source="test")
    out = engine.run_tool(s, inv, tool, args, source_meta=True)
    assert out["ok"], out
    return inv, h["id"], s.get(Action, out["action_id"])


def test_per_region_auc_gap_links_subgroup_hypothesis():
    from model_autopsy.backend.causal import linker as LK
    init_db()
    s = SessionLocal()
    try:
        inv, hid, act = _inv(
            s, "classification_metrics",
            {"predictions_path": CREDIT, "score_column": "score",
             "split_by": "region"},
            "Ranking performance shows an uneven regional gap")
        per = act.result["per_split_auc"]
        assert max(per.values()) - min(per.values()) >= 0.10
        applied = LK.link_tool_result(s, inv, act)
        assert applied, "wide regional gap must link"
        assert applied[0]["direction"] == "supports"
        from model_autopsy.backend.db import Hypothesis
        h = s.get(Hypothesis, hid)
        assert h.status == "investigating"  # one item: not yet supported
        assert any(r["action_id"] == act.id for r in h.evidence_refs)
    finally:
        s.close()


def test_uniform_regions_contradict_subgroup_hypothesis():
    from model_autopsy.backend.causal import linker as LK
    # Direct rule checks on controlled inputs: uniform -> contradicts.
    rules = LK._rules("classification_metrics",
                      {"per_split_auc": {"a": 0.91, "b": 0.92}})
    assert rules and rules[0][1] == "contradicts"
    # Indecision band: spread between 0.03 and 0.10 links nothing.
    assert LK._rules("classification_metrics",
                     {"per_split_auc": {"a": 0.85, "b": 0.90}}) == []
    # Single group: no comparison possible, no link.
    assert LK._rules("classification_metrics",
                     {"per_split_auc": {"a": 0.9}}) == []


def test_district_mae_concentration_links_subgroup():
    from model_autopsy.backend.causal import linker as LK
    init_db()
    s = SessionLocal()
    try:
        inv, hid, act = _inv(
            s, "regression_metrics",
            {"predictions_path": RENT, "group_column": "district"},
            "Estimates are systematically worse in one district")
        per = act.result["mae_by_group"]
        assert max(per.values()) / min(per.values()) >= 1.5
        applied = LK.link_tool_result(s, inv, act)
        assert applied and applied[0]["direction"] == "supports"
        from model_autopsy.backend.db import Hypothesis
        assert s.get(Hypothesis, hid).status == "investigating"
    finally:
        s.close()


def test_miscalibration_links_calibration_hypothesis():
    from model_autopsy.backend.causal import linker as LK
    init_db()
    s = SessionLocal()
    try:
        inv, hid, act = _inv(
            s, "calibration_and_error_analysis",
            {"predictions_path": CREDIT, "score_column": "score"},
            "The model is miscalibrated at high scores")
        applied = LK.link_tool_result(s, inv, act)
        assert applied and applied[0]["direction"] == "supports"
        assert "reliability gap" in applied[0]["justification"]
    finally:
        s.close()


def test_evidence_never_fabricates_for_unrelated_hypothesis():
    from model_autopsy.backend.causal import linker as LK
    init_db()
    s = SessionLocal()
    try:
        inv, hid, act = _inv(
            s, "classification_metrics",
            {"predictions_path": CREDIT, "score_column": "score",
             "split_by": "region"},
            "A sudden level shift after day 500 degrades forecasts")
        applied = LK.link_tool_result(s, inv, act)
        assert applied == [], "drift hypothesis gets no subgroup link"
        from model_autopsy.backend.db import Hypothesis
        assert s.get(Hypothesis, hid).status == "proposed"
    finally:
        s.close()


def test_leakage_screen_contradicts_without_label_duplicate():
    from model_autopsy.backend.causal import linker as LK
    init_db()
    s = SessionLocal()
    try:
        inv, hid, act = _inv(
            s, "feature_target_suspiciousness",
            {"feature_csv": CREDIT, "label_csv": CREDIT},
            "The score's apparent strength comes from leakage, not skill")
        applied = LK.link_tool_result(s, inv, act)
        # No non-score input tracks the label (max |r| ~ 0.37): the screen
        # contradicts leakage and demotes the hypothesis — the M6 "reject
        # plausible" behavior, produced by the backend, not the model.
        assert applied and applied[0]["direction"] == "contradicts"
        from model_autopsy.backend.db import Hypothesis
        assert s.get(Hypothesis, hid).status == "investigating"
    finally:
        s.close()


def test_leakage_rule_ignores_label_and_score_columns():
    from model_autopsy.backend.causal import linker as LK
    # Label self-correlation (r=1.0) and a strong score must not read as
    # leakage: only non-score inputs count, with a wide indecision band.
    assert LK._rules("feature_target_suspiciousness",
                     {"top_correlations": [
                         {"feature": "label", "abs_r": 1.0},
                         {"feature": "score", "abs_r": 0.83}]}) == []
    supports = LK._rules("feature_target_suspiciousness",
                         {"top_correlations": [
                             {"feature": "mystery_col", "abs_r": 0.97}]})
    assert supports and supports[0][1] == "supports"


def test_leakage_rule_supports_strong_sub_duplicate_association():
    from model_autopsy.backend.causal import linker as LK
    # The multi_clinic leak (|r|=0.912) sat in the old [0.5, 0.95)
    # indecision band and linked to nothing: the probe measured the leak
    # while the leak hypothesis starved. A strong non-score association
    # now supports (corroboration still needed); the band below 0.7 is
    # still indecision, and <0.5 still contradicts.
    supports = LK._rules("feature_target_suspiciousness",
                         {"top_correlations": [
                             {"feature": "leak_flag", "abs_r": 0.9123}]})
    assert supports and supports[0][0] == "leakage" \
        and supports[0][1] == "supports"
    assert LK._rules("feature_target_suspiciousness",
                     {"top_correlations": [
                         {"feature": "x", "abs_r": 0.6}]}) == []
    assert LK._rules("feature_target_suspiciousness",
                     {"top_correlations": [
                         {"feature": "x", "abs_r": 0.4}]})[0][1] \
        == "contradicts"


def test_measured_leak_links_leak_hypothesis():
    from model_autopsy.backend.causal import linker as LK
    init_db()
    s = SessionLocal()
    try:
        inv, hid, act = _inv(
            s, "feature_target_suspiciousness",
            {"feature_csv":
             "model_autopsy/tests/fixture_challenge/multi_clinic.csv",
             "label_csv":
             "model_autopsy/tests/fixture_challenge/multi_clinic.csv"},
            "Model failure is driven by label leakage via leak_flag "
            "duplicating label information")
        top = max(r["abs_r"] for r in act.result["top_correlations"]
                  if r["feature"] == "leak_flag")
        assert top >= 0.7, "fixture must carry the leak"
        applied = LK.link_tool_result(s, inv, act)
        assert applied and applied[0]["direction"] == "supports"
        from model_autopsy.backend.db import Hypothesis
        h = s.get(Hypothesis, hid)
        assert h.status == "investigating"
        assert any(r["action_id"] == act.id for r in h.evidence_refs)
    finally:
        s.close()


def test_failed_actions_never_generate_evidence():
    from model_autopsy.backend.causal import linker as LK
    init_db()
    s = SessionLocal()
    try:
        from model_autopsy.backend import engine
        import os
        os.environ["MODEL_AUTOPSY_TESTING"] = "1"
        inv = engine.create_investigation(s, "ml", "t", "q", {})
        h = engine.add_hypothesis(s, inv.id, "regional gap exists",
                                  source="test")
        out = engine.run_tool(s, inv, "classification_metrics",
                              {"predictions_path": CREDIT,
                               "score_column": "no_such_col"},
                              source_meta=True)
        assert not out["ok"]
        act = s.get(Action, out["action_id"])
        assert act.status == "failed"
        assert LK.link_tool_result(s, inv, act) == []
    finally:
        s.close()
