"""Per-tool argument schema validation tests (Phase 1B).

Every entry point funnels through validate_arguments(); nothing here trusts
the caller. Unknown params, wrong types, out-of-range values, oversized
strings, oversized payloads and array bound violations must be rejected with
structured errors — and rejected calls never execute the tool function.
"""
from __future__ import annotations

import json

import pytest

from model_autopsy.backend.tools_registry import (
    MAX_ARGUMENT_BYTES, meta_tool_schemas, validate_arguments)


def _call(tool, args, capsys=None):
    return validate_arguments(tool, args)


def test_unknown_param_rejected():
    with pytest.raises(ValueError, match="unknown parameter"):
        _call("classification_metrics", {"score_column": "LightGBM_C",
                                         "shell_command": "rm -rf /"})


def test_wrong_type_rejected():
    with pytest.raises(ValueError, match="expected an integer"):
        _call("grouped_auc_comparison", {"n_boot": "2000"})
    with pytest.raises(ValueError, match="expected a number"):
        _call("classification_metrics", {"threshold": "0.5"})
    with pytest.raises(ValueError, match="expected a boolean"):
        _call("check_apply_approval", {"owner_approved": "true"})


def test_boolean_not_confused_with_integer():
    with pytest.raises(ValueError):
        _call("grouped_auc_comparison", {"n_boot": True})


def test_out_of_range_rejected():
    with pytest.raises(ValueError, match="above maximum"):
        _call("grouped_auc_comparison", {"n_boot": 99999})
    with pytest.raises(ValueError, match="below minimum"):
        _call("calibration_and_error_analysis", {"bins": 1})
    with pytest.raises(ValueError, match="above maximum"):
        _call("classification_metrics", {"threshold": 1.5})


def test_missing_required_param_rejected():
    with pytest.raises(ValueError, match="missing required"):
        _call("feature_target_suspiciousness", {})
    with pytest.raises(ValueError, match="missing required"):
        _call("propose_hypothesis", {"rationale": "no text"})
    with pytest.raises(ValueError, match="missing required"):
        _call("read_changed_file_head", {})


def test_oversized_string_rejected():
    with pytest.raises(ValueError, match="exceeds"):
        _call("propose_hypothesis", {"text": "x" * 3000})


def test_oversized_payload_rejected():
    big = {"labels": "0" * (MAX_ARGUMENT_BYTES + 10)}
    with pytest.raises(ValueError, match="cap"):
        _call("artifact_summary", big)


def test_array_bounds_rejected():
    with pytest.raises(ValueError, match="exceeds"):
        _call("propose_revision_instructions",
              {"findings": ["f"], "instructions": ["i"] * 30})
    with pytest.raises(ValueError, match="needs at least"):
        _call("propose_revision_instructions",
              {"findings": [], "instructions": ["i"]})
    with pytest.raises(ValueError, match="expected an array"):
        _call("propose_revision_instructions",
              {"findings": "not a list", "instructions": ["i"]})


def test_unknown_tool_rejected():
    from model_autopsy.backend import config
    with pytest.raises(LookupError, match="unknown"):
        _call("delete_everything", {})


def test_generated_schemas_match_validation():
    """The Meta JSON Schemas must describe exactly what validation enforces."""
    schemas = {s["name"]: s for s in meta_tool_schemas("ml")}
    sch = schemas["classification_metrics"]["parameters"]
    assert sch["additionalProperties"] is False
    assert "score_column" in sch["properties"]
    assert sch["properties"]["threshold"]["minimum"] == 0.0
    assert sch["properties"]["threshold"]["maximum"] == 1.0
    # unknown keys are expressible as violations because additionalProperties
    # is False, and the backend rejects them anyway (see unknown-param test).
    assert "_note" not in sch["properties"]     # placeholder gone
    bound = schemas["grouped_auc_comparison"]["parameters"]
    assert bound["properties"]["n_boot"]["maximum"] == 5000


def test_propose_hypothesis_schema_uses_real_params():
    sch = {s["name"]: s for s in meta_tool_schemas("ml")}["propose_hypothesis"]
    props = sch["parameters"]["properties"]
    assert set(props) == {"text", "rationale", "predicted_observation",
                          "confidence_note"}
    assert props["text"]["minLength"] == 10
