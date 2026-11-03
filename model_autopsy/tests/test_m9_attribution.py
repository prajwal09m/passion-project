"""M9 Workstream 3.2: explicit evidence relationships.

Reproduces the M8 live defect (district-concentration evidence linked
supports to H3, which explicitly denies district failure) and proves
the redesigned semantics. Mentioning a segment is never support.
"""
from model_autopsy.backend.causal import attribution as AT

ARGS = {"predictions_path": "x.csv", "group_column": "district"}
REASON = "group MAE ratio 6.23 (worst 583.99); errors concentrate"

H1 = ("Predictions have systematic district-specific bias caused by "
      "schema update mishandling of district feature")
H2 = ("Errors are driven by mis-scaled numeric feature after schema "
      "update, not by district membership itself")
H3 = ("Model has global miscalibration affecting all districts similarly, "
      "with no true district-specific failure")
DRIFT = "A sudden level shift after day 500 degrades forecasts"


def test_district_bias_hypothesis_supported():
    out = AT.classify(H1, "subgroup", "supports", REASON, ARGS, n=1200)
    assert out["relationship"] == "supports"
    assert out["moves_belief"] is True


def test_denial_flips_to_contradicts():
    # H3 denies district failure; district concentration contradicts it.
    # (M8 linked supports here — the exact defect being fixed.)
    out = AT.classify(H3, "subgroup", "supports", REASON, ARGS, n=1200)
    assert out["relationship"] == "contradicts"
    assert out["moves_belief"] is True


def test_denied_alternative_contradicted():
    out = AT.classify(H2, "subgroup", "supports", REASON, ARGS, n=1200)
    assert out["relationship"] == "contradicts"
    assert out["moves_belief"] is True


def test_absence_evidenced_supports_denial():
    out = AT.classify(
        H3, "subgroup", "contradicts",
        "group MAE ratio 1.05: uniform", ARGS, n=1200)
    assert out["relationship"] == "supports"
    assert out["moves_belief"] is True


def test_unrelated_hypothesis_is_neutral():
    out = AT.classify(DRIFT, "subgroup", "supports", REASON, ARGS, n=1200)
    assert out["relationship"] == "neutral"
    assert out["moves_belief"] is False


def test_topical_only_is_relevant_not_support():
    # Leakage-flavored hypothesis: topically near subgroup work, but the
    # district measurement does not test leakage — visible, non-moving.
    out = AT.classify(
        "Bias across folds suggests possible leakage of future rows",
        "subgroup", "supports", REASON, ARGS, n=1200)
    assert out["relationship"] in ("relevant_to", "uncertain", "mentions")
    assert out["moves_belief"] is False


def test_small_n_is_insufficient():
    out = AT.classify(H1, "subgroup", "supports", REASON, ARGS, n=12)
    assert out["relationship"] == "insufficient"
    assert out["moves_belief"] is False


def test_all_relationships_valid_enum():
    assert set(AT.RELATIONSHIPS) == {
        "supports", "contradicts", "relevant_to", "mentions", "neutral",
        "insufficient", "uncertain"}


def test_linker_records_denial_as_contradicts_not_supports():
    """End-to-end on the M8 live shape: H3 must move against, not for."""
    from model_autopsy.backend.db import SessionLocal, init_db
    from model_autopsy.backend.causal import linker as LK
    import os
    os.environ["MODEL_AUTOPSY_TESTING"] = "1"
    init_db()
    s = SessionLocal()
    try:
        from model_autopsy.backend import engine
        inv = engine.create_investigation(s, "ml", "t", "q",
                                          {"max_tool_calls": 6})
        h3 = engine.add_hypothesis(s, inv.id, H3, source="test")
        out = engine.run_tool(
            s, inv, "regression_metrics",
            {"predictions_path":
             "model_autopsy/tests/fixture_eval/investigator/"
             "rent_estimates.csv",
             "group_column": "district"}, source_meta=True)
        assert out["ok"], out
        from model_autopsy.backend.db import Action, Hypothesis
        act = s.get(Action, out["action_id"])
        applied = LK.link_tool_result(s, inv, act)
        assert applied, "district concentration must bear on H3"
        assert applied[0]["direction"] == "contradicts", applied
        h = s.get(Hypothesis, h3["id"])
        assert h.status == "investigating"
        assert not [r for r in h.evidence_refs
                    if r.get("relation") == "supports"]
    finally:
        s.close()
