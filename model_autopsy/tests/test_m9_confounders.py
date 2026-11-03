"""M9 Workstream 3.3: confounder identification."""
from model_autopsy.backend.causal import confounders as CF

H_DISTRICT = ("Predictions have systematic district-specific bias caused "
              "by schema update mishandling of district feature")
H_FEATURE = ("Errors are driven by mis-scaled numeric feature after "
             "schema update, not by district membership itself")
H_GLOBAL = ("Model has global miscalibration affecting all districts "
            "similarly, with no true district-specific failure")


def _hyps():
    return [
        {"id": "h1", "text": H_DISTRICT,
         "evidence_refs": [{"action_id": "a1", "tool": "regression_metrics",
                            "relation": "supports"}]},
        {"id": "h2", "text": H_FEATURE,
         "evidence_refs": [{"action_id": "a1", "tool": "regression_metrics",
                            "relation": "supports"}]},
        {"id": "h3", "text": H_GLOBAL,
         "evidence_refs": [{"action_id": "a1", "tool": "regression_metrics",
                            "relation": "contradicts"}]},
    ]


def test_shared_supports_flag_common_cause():
    cands = CF.shared_evidence_candidates(_hyps())
    assert len(cands) == 1
    assert cands[0]["action_id"] == "a1"
    assert set(cands[0]["hypothesis_ids"]) == {"h1", "h2"}
    assert len(cands[0]["mechanisms"]) >= 2
    assert "discriminate" in cands[0]["note"]


def test_same_mechanism_twice_is_corroboration_not_confounding():
    hyps = [{"id": "h1", "text": H_DISTRICT,
             "evidence_refs": [{"action_id": "a1", "relation": "supports"}]},
            {"id": "h1b", "text": H_DISTRICT + " in the east",
             "evidence_refs": [{"action_id": "a1", "relation": "supports"}]}]
    assert CF.shared_evidence_candidates(hyps) == []


def test_checklist_grounds_in_artifact_facts():
    facts = {"segments": ["district"], "temporal": False,
             "schema_note": "schema update last quarter",
             "brief": "rent off in one district after schema update"}
    checks = {c["confounder"]: c for c in CF.checklist(facts)}
    assert checks["preprocessing"]["applicable"] is True
    assert checks["composition"]["applicable"] is True
    assert checks["temporal"]["applicable"] is False  # no date column
    assert all("ruled_out_by" in c for c in checks.values())


def test_discriminating_measurements_carry_interpretation_rules():
    ms = CF.discriminating_measurements(
        {}, ["regression_metrics", "temporal_changepoint_scan"],
        "rent.csv", ["district"], temporal_col="date")
    by_tool = {m["tool"]: m for m in ms}
    assert by_tool["regression_metrics"]["args"]["group_column"] == "district"
    assert "interpretation" in by_tool["regression_metrics"]
    assert "inconclusive" in by_tool["regression_metrics"]["interpretation"]
    assert by_tool["temporal_changepoint_scan"]["args"]["date_column"] == "date"


def test_analyze_marks_need_for_discrimination():
    facts = {"segments": ["district"], "temporal": False,
             "schema_note": "x", "brief": "rent district schema"}
    out = CF.analyze(_hyps(), facts, ["regression_metrics"], "rent.csv")
    assert out["needs_discrimination"] is True
    assert out["shared_evidence"] and out["discriminating_measurements"]
