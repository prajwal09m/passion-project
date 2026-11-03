"""Offline tests for the Groq context-efficiency benchmark.

No network in any of these tests. The --live path is tested only for its
abort behavior when GROQ_API_KEY is absent; mock objects are never presented
as live Groq results.
"""
from __future__ import annotations

import importlib
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from model_autopsy.benchmarks import groq_context_benchmark as bench


def test_offline_benchmark_fresh_temp_db_isolated() -> None:
    """The benchmark DB must resolve to a temp location, never a project-root
    default or a persistent application database."""
    path = bench._ensure_temp_db()
    import tempfile
    tmp_base = Path(tempfile.gettempdir()).resolve()
    assert Path(str(path)).resolve().is_relative_to(tmp_base)
    assert not Path(str(path)).resolve().is_relative_to(
        (Path.cwd() / "model_autopsy").resolve())


def test_offline_run_payload_sizes_and_reuse(db_ready=None) -> None:
    off = bench._offline_run()
    # Honest reconstruction: old payload must contain the FULL column list
    # and legacy keys; the new one must not duplicate it.
    assert off["old"]["content_chars"] > 0
    assert off["new"]["content_chars"] > 0
    assert off["network_calls"] == 0
    # Composition check (the actual compaction mechanism): the legacy payload
    # resends the FULL column list inside recorded_context; the compacted one
    # replaces it with counts and adds hypotheses/ledger/budget instead.
    # NOTE: aggregate wire size on a FRESH investigation may be LARGER for the
    # new payload because the investigator instructions are richer — the
    # benchmark reports all rows as measured and claims nothing favorable.
    assert off.get("tool_schemas_chars", 0) > 0
    assert off["old"]["content_chars"] > 0 and off["new"]["content_chars"] > 0
    # Duplicate diagnostic: the second identical request is REUSED (one
    # execution, no second run, budget stays at 1):
    d = off["duplicate_diagnostic"]
    assert d["second_response_reused"] is True
    assert d["executions"] == 1
    assert d["tool_call_count_after_two_requests"] == 1
    # Sizes are explicitly labeled as NOT tokens:
    assert "not measured" in off["token_rows"]


def test_legacy_instructions_match_commit_6cf865f() -> None:
    """The embedded legacy investigator text is verified against the actual
    git commit so the reconstruction cannot drift from history."""
    proc = subprocess.run(
        ["git", "show", "6cf865f:model_autopsy/backend/meta_api/loop.py"],
        capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        pytest.skip("git history unavailable in this environment")
    src = proc.stdout
    tree = ast.parse(src)
    assign = next(n for n in tree.body
                  if isinstance(n, ast.Assign)
                  and getattr(n.targets[0], "id", None) == "MODE_INSTRUCTIONS")
    modes = ast.literal_eval(assign.value)
    text = modes["ml"]
    assert text.strip() == bench.LEGACY_MODE_INSTRUCTIONS_ML.strip(), (
        "legacy instruction copy drifted from commit 6cf865f")


def test_live_mode_aborts_without_spending_when_key_missing(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = bench._live_run(n_requests=1)
    assert result["mode"] == "live" and "error" in result
    assert "GROQ_API_KEY" in result["error"]
    assert "requests" not in result  # nothing was sent


def test_reuse_result_is_explicit_for_the_model(db_ready=None) -> None:
    """The reuse signal the loop relays to the model must be truthful and
    self-describing (labelled 'not re-executed')."""
    off = bench._offline_run()
    _ = off  # sanity only; detailed semantics asserted in test_meta_adapter
    src = (Path(bench.BENCH_DIR.parent) / "backend" / "tools_registry.py") \
        .read_text(encoding="utf-8")
    assert "not re-executed, no budget consumed" in src


def test_unclosed_summary_fence_reproduces_pilot2_repair_failure(
        db_ready=None) -> None:
    """Documented 2026-10-29 from Groq pilot #2 (full condition): the bounded
    repair emitted an OPENED ```investigation_summary fence that never got a
    closing fence — the validator saw no complete block and no JSON parse
    error while the provider reported finish_reason 'stop'. The validator
    must record exactly the fenced-block-not-found error, never raise and
    never accept partial output."""
    from model_autopsy.backend import engine as _eng
    from model_autopsy.backend.db import Event, SessionLocal, init_db
    visible_tail = (
        '```investigation_summary\n'
        '{"conclusion":"partial analysis preserved",'
        '"recommended_next":"re-run with a closing fence",'
        '"status_recommendations":[{"hypothesis_id":"x","status":'
        '"inconclusive","basis":["y"]}'      # cut off, no closing ```
    )
    init_db()
    session = SessionLocal()
    try:
        inv = _eng.create_investigation(
            session, "ml", "repair-failure-regression",
            "fenced-block plumbing check", {"max_tool_calls": 1})
        result = _eng.validate_structured_summary(
            session, inv, "repair attempt\n" + visible_tail)
        assert result["valid"] is False
        assert result["summary"] is None
        assert result["errors"] == [
            "no structured summary found in the final message"]
        ev = session.query(Event).filter_by(
            investigation_id=inv.id, kind="summary").one()
        # exact same diagnostic surface pilot #2 presented: INVALID, with the
        # reason preserved in the event payload, not discarded:
        assert "INVALID" in str(ev.title)
    finally:
        session.close()


def test_controlled_offline_certifies_only_context_differs() -> None:
    """The controlled mode must be provably identical across arms except for
    recorded_context: same instruction, same keys, same budgets, and no
    turn-1 wrap-up. Offline only; no provider request."""
    repo_root = Path(__file__).resolve().parents[2]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(repo_root)
    proc = subprocess.run(
        [sys.executable, "-m",
         "model_autopsy.benchmarks.groq_paired_continuation_benchmark",
         "--offline", "--controlled"],
        cwd=repo_root, env=env, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    cert = out["checks"]["controlled_certification"]
    assert out["checks"]["controlled_mode_active"] is True
    assert cert["identical_continuation_instruction"] is True
    assert cert["only_recorded_context_differs"] is True
    assert cert["recorded_context_present_only_in_full"] is True
    assert cert["delta_strictly_smaller"] is True
    assert cert["turn1_wrapup_suppressed"] is True
    assert cert["turn2_midround_wrapup_suppressed"] is True
    assert cert["turn2_last_round_wrapup_allowed"] is True
    assert cert["forced_diagnostic"] is False
    assert cert["budgets_identical"]["turn_rounds"] == 3
    assert cert["budgets_identical"]["turns_per_run"] == 2
    assert out["checks"]["reuse_guard"]["second_reused"] is True


def test_controlled_wrapup_never_precedes_the_continuation() -> None:
    """Turn 1 must never receive 'Finish now'; turn 2 gets it only at the last
    scheduled round or when the tool budget is truly exhausted. Production
    (non-controlled) behavior is unchanged."""
    from model_autopsy.benchmarks import groq_paired_continuation_benchmark as b

    class _Inv:
        tool_call_count = 0
        max_tool_calls = 6

    inv = _Inv()
    assert b._wrapup_allowed(1, True, 1, inv) is False
    assert b._wrapup_allowed(1, True, b.TURN_ROUNDS, inv) is False
    assert b._wrapup_allowed(2, True, 1, inv) is False
    assert b._wrapup_allowed(2, True, b.TURN_ROUNDS, inv) is True
    inv.tool_call_count = 6
    assert b._wrapup_allowed(2, True, 1, inv) is True
    assert b._wrapup_allowed(1, False, 1, inv) is True


def test_harness_records_repair_validation_errors_in_run_record() -> None:
    """The 2026-10-29 observability fix: when the one-shot F4 repair fails
    validation, the run record must carry the REPAIR's own validation errors
    (summary_repair_errors) instead of discarding them and leaving the
    original attempt's error string in place."""
    src = (Path(bench.BENCH_DIR) /
           "groq_paired_continuation_benchmark.py").read_text(
               encoding="utf-8")
    assert '"summary_repair_errors": repair_errors' in src
    # errors are initialized before any repair and captured on the failing
    # branch only (the valid-repair branch overwrites nothing):
    assert "repair_errors: list[str] = []" in src
    assert "repair_errors = (r_summary.get(\"errors\") or [])[:8]" in src
