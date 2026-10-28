from __future__ import annotations

from pathlib import Path

import pytest

from model_autopsy.backend import config, engine, tools_registry
from model_autopsy.backend import software_tools as sw
from model_autopsy.backend.db import SessionLocal, init_db, Investigation

FAST_TESTS_DIR = Path(__file__).resolve().parent / "fixture"


def _session():
    init_db()
    s = SessionLocal()
    yield s
    s.close()


def test_git_status_and_diff_on_real_repo():
    out = sw.git_status_and_diff(root=".", max_diff_chars=500)
    assert out["ok"] is True
    assert "workspace" in out and "status" in out


def test_list_changed_files():
    out = sw.list_changed_files(root=".")
    assert out["ok"] and isinstance(out["changed_files"], list)


def test_read_file_rejects_outside_root():
    with pytest.raises(PermissionError):
        sw.read_changed_file_head(root=".", file_path=r"C:\Windows\win.ini")


def test_run_tests_real_pass_and_fail():
    ok = sw.run_tests(root=".", test_path=str(FAST_TESTS_DIR))
    assert ok["ok"] and ok["exit_code"] == 0 and ok["passed"] is True
    failing = FAST_TESTS_DIR.parent / "fixture_failing"
    res = sw.run_tests(root=".", test_path=str(failing))
    assert res["ok"] and res["passed"] is False


def test_compare_results_flags_regression():
    before = {"exit_code": 0, "passed": True}
    after = {"exit_code": 1, "passed": False}
    assert sw.compare_test_results(before, after)["regression"] is True
    assert sw.compare_test_results(before, before)["regression"] is False


def test_apply_approval_never_from_meta():
    assert sw.check_apply_approval(requested_by_meta=True)["apply_allowed"] is False
    assert sw.check_apply_approval(owner_approved=True)["apply_allowed"] is True


def test_engine_budgets_are_capped():
    mit, mtc = engine.budgets_for({"max_iterations": 10, "max_tool_calls": 999})
    assert mit == config.ABSOLUTE_MAX_ITERATIONS
    assert mtc == config.ABSOLUTE_MAX_TOOL_CALLS


def test_engine_illegal_transition():
    for session in _session():
        inv = engine.create_investigation(session, "ml", "title", "question")
        with pytest.raises(ValueError):
            engine.set_status(session, inv, "complete")
        assert inv.status == "created"


def test_engine_tool_budget_blocks_at_cap():
    for session in _session():
        inv = engine.create_investigation(
            session, "ml", "t", "q", {"max_tool_calls": 1})
        r1 = engine.run_tool(session, inv, "artifact_summary", {})
        assert r1["ok"] is True
        r2 = engine.run_tool(session, inv, "artifact_summary", {})
        assert r2["ok"] is False and r2["error"] == "tool_call_budget_exhausted"


def test_engine_unknown_tool_recorded_as_failure():
    for session in _session():
        inv = engine.create_investigation(session, "ml", "t", "q")
        out = engine.run_tool(session, inv, "invented_tool", {})
        assert out["ok"] is False
        inv = session.refresh(inv) or session.get(Investigation, inv.id)
        failed = [a for a in inv.actions if a.status == "failed"]
        assert failed  # honest record, not silent
        assert inv.tool_call_count == 0   # invalid calls spend no budget
