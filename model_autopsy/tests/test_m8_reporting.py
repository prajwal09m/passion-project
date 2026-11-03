"""M8 Workstream B: strict structured-report contract + adversarial recovery.

Uses the real contract: engine.validate_structured_summary (parse +
validate), causal.report_schema.validate (versioned schema m8-v1), and
causal.fallback.compose (deterministic, records-only, labeled).
"""
import json

import pytest

from model_autopsy.backend.db import SessionLocal, init_db

TURBINE = ("model_autopsy/tests/fixture_eval/investigator/"
           "turbine_output.csv")


def _setup(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "dummy-offline-placeholder")
    init_db()
    s = SessionLocal()
    from model_autopsy.backend import engine
    inv = engine.create_investigation(s, "ml", "t", "q",
                                      {"max_tool_calls": 5})
    h = engine.add_hypothesis(s, inv.id,
                              "capacity loss explains the miss",
                              source="test", rationale="recon")
    act = engine.run_tool(s, inv, "data_quality_profile",
                          {"predictions_path": TURBINE})
    assert act["ok"], act
    return s, inv, h["id"], act["action_id"]


def _valid_body(hid, aid):
    return {
        "conclusion": ("Partial capacity loss on 2026-08-10 with trip "
                       "flags explains the miss, though full dispatch logs "
                       "were unavailable; the degradation is supported by "
                       "the trip-flag evidence and calibrated output "
                       "intervals."),
        "status_recommendations": [
            {"hypothesis_id": hid, "status": "inconclusive",
             "basis": "trip-flag evidence with missing dispatch logs",
             "basis_action_ids": [aid]}],
        "uncertainties": ["dispatch logs for 2026-08-10 unavailable"],
        "recommended_next": "inspect maintenance logs before next run",
        "confidence": 60,
        "schema_version": "m8-v1",
    }


def _fenced(body: dict) -> str:
    return ("analysis text\n```investigation_summary\n"
            + json.dumps(body) + "\n```")


def test_valid_report_passes_with_version(monkeypatch):
    from model_autopsy.backend import engine
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        out = engine.validate_structured_summary(
            s, inv, _fenced(_valid_body(hid, aid)))
        assert out["valid"], out["errors"]
        assert out["schema_version"] == "m8-v1"
        assert out["summary"]["confidence"] == 60
    finally:
        s.close()


def test_unknown_schema_version_rejected(monkeypatch):
    from model_autopsy.backend.causal import report_schema as RS
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        bad = _valid_body(hid, aid)
        bad["schema_version"] = "m9-x"
        checked = RS.validate(bad, {hid}, {aid})
        assert not checked["valid"]
        assert any("schema_version" in e for e in checked["errors"])
    finally:
        s.close()


def test_confidence_hundred_rejected(monkeypatch):
    from model_autopsy.backend.causal import report_schema as RS
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        bad = _valid_body(hid, aid)
        bad["confidence"] = 100
        checked = RS.validate(bad, {hid}, {aid})
        assert not checked["valid"]
        assert any("certainty" in e for e in checked["errors"])
    finally:
        s.close()


def test_supported_requires_basis_actions(monkeypatch):
    from model_autopsy.backend.causal import report_schema as RS
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        bad = _valid_body(hid, aid)
        bad["status_recommendations"] = [
            {"hypothesis_id": hid, "status": "supported"}]
        checked = RS.validate(bad, {hid}, {aid})
        assert not checked["valid"]
        assert any("no evidence actions" in e or "no basis" in e
                   for e in checked["errors"])
    finally:
        s.close()


def test_malformed_json_recorded_not_trusted(monkeypatch):
    from model_autopsy.backend import engine
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        out = engine.validate_structured_summary(
            s, inv, "```investigation_summary\n{not json\n```")
        assert out["valid"] is False
        assert out["summary"] is None
        assert out["errors"]
    finally:
        s.close()


def test_empty_conclusion_and_wrong_types(monkeypatch):
    from model_autopsy.backend.causal import report_schema as RS
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        bad = _valid_body(hid, aid)
        bad["conclusion"] = "   "
        assert not RS.validate(bad, {hid}, {aid})["valid"]
        bad2 = _valid_body(hid, aid)
        bad2["status_recommendations"] = "just do it"
        checked = RS.validate(bad2, {hid}, {aid})
        assert not checked["valid"]
        assert any("status_recommendations" in e for e in checked["errors"])
    finally:
        s.close()


def test_truncated_conclusion_rejected(monkeypatch):
    from model_autopsy.backend.causal import report_schema as RS
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        bad = _valid_body(hid, aid)
        bad["conclusion"] = "x" * 6000
        checked = RS.validate(bad, {hid}, {aid})
        assert not checked["valid"]
        assert any("truncat" in e or "oversized" in e
                   for e in checked["errors"])
    finally:
        s.close()


def test_unknown_and_duplicate_refs(monkeypatch):
    from model_autopsy.backend.causal import report_schema as RS
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        bad = _valid_body(hid, aid)
        bad["status_recommendations"] = [
            {"hypothesis_id": "deadbeef", "status": "rejected",
             "basis_action_ids": [aid]}]
        checked = RS.validate(bad, {hid}, {aid})
        assert not checked["valid"]
        assert any("unknown hypothesis" in e for e in checked["errors"])
        dup = _valid_body(hid, aid)
        dup["status_recommendations"] = [
            {"hypothesis_id": hid, "status": "supported",
             "basis_action_ids": [aid]},
            {"hypothesis_id": hid, "status": "rejected",
             "basis_action_ids": [aid]}]
        checked = RS.validate(dup, {hid}, {aid})
        assert not checked["valid"]
        assert any("uplicate" in e or "contradict" in e
                   for e in checked["errors"])
    finally:
        s.close()


def test_missing_uncertainties_warns_not_fails(monkeypatch):
    from model_autopsy.backend.causal import report_schema as RS
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        body = _valid_body(hid, aid)
        del body["uncertainties"]
        checked = RS.validate(body, {hid}, {aid})
        assert checked["valid"]
        assert any("uncertaint" in w or "overconfidence" in w
                   for w in checked["warnings"])
    finally:
        s.close()


def test_inconclusive_is_a_valid_outcome(monkeypatch):
    from model_autopsy.backend import engine
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        body = _valid_body(hid, aid)
        body["status"] = "inconclusive"
        body["confidence"] = 25
        body["conclusion"] = ("Evidence was thin: one diagnostic ran and "
                              "dispatch logs were missing, so no mechanism "
                              "can be confirmed or ruled out.")
        out = engine.validate_structured_summary(s, inv, _fenced(body))
        assert out["valid"], out["errors"]
    finally:
        s.close()


def test_fallback_deterministic_records_only_labeled(monkeypatch):
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import fallback as FB
    s, inv, hid, aid = _setup(monkeypatch)
    try:
        engine.ensure_finalizable(s, inv)
        report = engine.build_report(s, inv)
        final = engine.finalize(s, inv, report)
        bad_text = ("```investigation_summary\n"
                    "{\"conclusion\": \"QUANTUM FLUX did it\", "
                    "\"status_recommendations\": [{\"hypothesis_id\": "
                    "\"no-such-hyp\", \"status\": \"rejected\", "
                    "\"basis_action_ids\": []}]}\n```")
        parsed = engine.validate_structured_summary(s, inv, bad_text)
        assert parsed["valid"] is False
        fb1 = FB.compose(inv, final, parsed["errors"])
        fb2 = FB.compose(inv, final, parsed["errors"])
        assert fb1 == fb2  # deterministic
        assert fb1["schema_version"] == "m8-v1"
        assert fb1["kind"] == "deterministic-fallback"
        assert "fallback_version" in fb1 and "provenance" in fb1
        substantive = " ".join([fb1["conclusion"],
                                  *fb1["uncertainties"],
                                  str(fb1["recommended_next"])])
        assert "QUANTUM FLUX" not in substantive  # records only
        assert fb1["model_summary_errors"] == parsed["errors"]
        assert fb1["evidence_action_ids"] == [aid]
    finally:
        s.close()


def test_loop_composes_fallback_on_unrepairable_summary(monkeypatch):
    """End-to-end: invalid summary + failed repair -> labeled fallback,
    original preserved, no fabrication."""
    from model_autopsy.backend.meta_api import client as MC
    from model_autopsy.backend.meta_api import loop as ML
    s, inv, hid, aid = _setup(monkeypatch)
    import json as _json

    def _resp(text, rid):
        return {"id": rid, "status": "completed",
                "output": [{"type": "message",
                            "content": [{"type": "output_text",
                                         "text": text}]}],
                "usage": {"input_tokens": 50, "output_tokens": 20,
                          "total_tokens": 70}}

    script = [_resp("no summary here, just prose", "r1"),
              _resp("still no structured block", "r2")]
    calls = []

    def fake(**kw):
        calls.append(kw)
        return script[min(len(calls) - 1, 1)]
    monkeypatch.setattr(MC, "create_response", fake)
    out = ML.run_meta_turn(s, inv, max_rounds=1)
    s.close()
    assert out["status"] == "ok"
    assert out["summary"]["valid"] is False
    assert out["fallback"] is not None
    assert out["fallback"]["kind"] == "deterministic-fallback"
    assert out["fallback"]["evidence_action_ids"] == [aid]
    # Repair was attempted exactly once (bounded), then fallback.
    assert len(calls) == 2
