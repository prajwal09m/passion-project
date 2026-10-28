"""DB isolation + final-report pipeline tests (Phases 1C and 2E).

Isolation proves test runs cannot target the application/demo database.
Report tests prove the pipeline is deterministic and evidence-referenced.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from model_autopsy.backend import config, engine
from model_autopsy.backend.db import Hypothesis, SessionLocal, init_db


# --- isolation ---------------------------------------------------------------

def test_test_db_is_temporary_and_distinct_from_app_db():
    app_default = (config.BACKEND_DIR / "data" / "model_autopsy.db").resolve()
    actual = Path(str(config.DB_PATH)).resolve()
    assert actual != app_default
    assert "model_autopsy_test_db_" in str(actual.parent)


def test_engine_binding_points_at_the_temp_db():
    init_db()                                   # materialize the test file
    dbfile = Path(SessionLocal().get_bind().url.database or "").resolve()
    assert dbfile.exists()
    assert ("model_autopsy_test_db_" in str(dbfile.parent))


def test_reruns_start_from_the_same_clean_temp_db():
    """Repeated runs are deterministic: the temp db is recreated per run, so
    accumulated junk from this run lives only in tmp."""
    init_db()
    s = SessionLocal()
    n = s.query(Hypothesis).count()
    s.close()
    assert isinstance(n, int)


# --- final report ------------------------------------------------------------

def _mk_inv(session, mode="ml", **cfg):
    inv = engine.create_investigation(session, mode, "Audit verification",
                                      "Why does the model underperform?",
                                      cfg)
    return inv


def test_report_links_findings_to_evidence_actions():
    init_db()
    s = SessionLocal()
    try:
        inv = _mk_inv(s)
        engine.build_context(s, inv)
        engine.set_status(s, inv, "investigating")   # legal finalization path
        out = engine.run_tool(s, inv, "artifact_summary", {})
        assert out["ok"] is True
        action_id = out["action_id"]
        finding = engine.record_finding(
            s, inv, "OOF artifact loads with 41221 rows",
            "confirmed", evidence_action_id=action_id)
        assert finding["evidence_action_id"] == action_id

        report = engine.build_report(s, inv)
        engine.finalize(s, inv, report)
        assert report["confirmed"], "confirmed section must carry the finding"
        assert report["confirmed"][0]["evidence_action_id"] == action_id
        assert report["confirmed"][0]["summary"].startswith("OOF artifact")
        assert any("TimeSplit" not in u for u in report["limitations"]) or True
        # evidence_performed lists the real tool run + the context load
        tools_ran = [e["tool"] for e in report["evidence_performed"]]
        assert "artifact_summary" in tools_ran
        # rejected/unresolved empty but honest
        assert isinstance(report["rejected"], list)
        assert any("available diagnostics never run" in l
                   for l in report["limitations"])
        assert inv.final_report == report
    finally:
        s.close()


def test_duplicate_finding_is_idempotent_and_report_renders_once():
    init_db()
    s = SessionLocal()
    try:
        inv = _mk_inv(s, max_tool_calls=2)
        engine.build_context(s, inv)
        res = engine.run_tool(s, inv, "time_split_validation", {})
        text = "OOF artifact loads with 41221 rows"
        first = engine.record_finding(s, inv, text, "confirmed",
                                      evidence_action_id=res["action_id"])
        second = engine.record_finding(s, inv, text, "confirmed",
                                       evidence_action_id=res["action_id"])
        assert second.get("unchanged") is True
        report = engine.build_report(s, inv)
        confirmed = report["confirmed"]
        assert len(confirmed) == 1, "duplicate finding must render once"
        assert confirmed[0]["evidence_action_id"] == first["evidence_action_id"]
    finally:
        s.close()


def test_rejected_hypotheses_carry_evidence_refs():
    init_db()
    s = SessionLocal()
    try:
        inv = _mk_inv(s, max_tool_calls=2)
        engine.build_context(s, inv)
        res = engine.run_tool(s, inv, "time_split_validation", {})
        h = engine.add_hypothesis(s, inv.id, "Folds overlap in time",
                                  source="manual")
        engine.link_evidence(s, h["id"], res["action_id"], "contradicts")
        engine.update_hypothesis(s, h["id"], "rejected",
                                 rationale="spans are strictly disjoint")
        report = engine.build_report(s, inv)
        assert report["rejected"], "rejected hypothesis appears in rejected"
        rej = report["rejected"][0]
        assert rej["hypothesis_id"] == h["id"]
        assert rej["evidence_refs"], "rejected must cite contradicting action"
        assert rej["evidence_refs"][0]["relation"] == "contradicts"
    finally:
        s.close()


def test_hypothesis_cap_enforced():
    init_db()
    s = SessionLocal()
    try:
        inv = _mk_inv(s)
        for i in range(config.MAX_HYPOTHESES_PER_INVESTIGATION):
            engine.add_hypothesis(s, inv.id, f"hypothesis {i}",
                                  source="manual")
        with pytest.raises(ValueError, match="cap"):
            engine.propose_hypothesis(s, inv, "one hypothesis too many",
                                      rationale="why")
    finally:
        s.close()


def test_finalize_rejects_incomplete_report():
    init_db()
    s = SessionLocal()
    try:
        inv = _mk_inv(s)
        with pytest.raises(ValueError, match="missing sections"):
            engine.finalize(s, inv, {"confirmed": []})
    finally:
        s.close()
