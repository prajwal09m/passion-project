"""Bounded Windows-rename retry and phase-watchdog tests (separate changes).

Contract under test:
  * ``rename_with_bounded_retry`` retries ONLY the same atomic ``os.replace``
    a bounded number of times, never overwrites an existing destination, and
    re-raises after exhaustion — it cannot bypass the caller's existence
    checks, validation, or any authorization/recovery logic.
  * The loop watchdog fires only at a clean cycle boundary, uses the
    standard durable stop path (state + summary + journal), and is disabled
    by default so unrelated behavior is unchanged.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from autonomous_agent.core import rename_with_bounded_retry
from autonomous_agent.continuous_loop import LoopStop, ResearchLoop
from autonomous_agent.test_continuous_loop import (LoopTestCase,
                                                   MockExecutor,
                                                   write_launch_gates)


class RenameRetryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="rename_retry_test_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_successful_rename_is_atomic_and_target_replaces(self):
        source = self.tmp / "a.json"
        destination = self.tmp / "b.json"
        source.write_text("payload", encoding="utf-8")
        rename_with_bounded_retry(source, destination)
        assert not source.exists()
        assert destination.read_text(encoding="utf-8") == "payload"

    def test_never_overwrites_existing_destination(self):
        source = self.tmp / "a.json"
        destination = self.tmp / "b.json"
        source.write_text("payload", encoding="utf-8")
        destination.write_text("existing", encoding="utf-8")
        with self.assertRaises((OSError,)):  # FileExistsError on most platforms
            rename_with_bounded_retry(source, destination, attempts=2)
        assert destination.read_text(encoding="utf-8") == "existing"

    def test_exhaustion_reraises_and_logs_each_attempt(self):
        holder_dir = self.tmp / "locked"
        holder_dir.mkdir()
        source = self.tmp / "a.json"
        source.write_text("payload", encoding="utf-8")
        attempt_log: list[str] = []
        with mock.patch("os.replace",
                                 side_effect=lambda *_: (_ for _ in ()).throw(
                                     PermissionError("simulated Windows lock"))):
            with self.assertRaises(PermissionError):
                rename_with_bounded_retry(source, holder_dir / "b.json",
                                          attempts=3, delay_seconds=0.0,
                                          log=attempt_log.append)
        self.assertEqual(len(attempt_log), 2)  # failures before each retry
        # The source was never consumed: no half-applied rename can exist.
        assert source.read_text(encoding="utf-8") == "payload"

    def test_transient_permission_error_is_retried_then_succeeds(self):
        source = self.tmp / "a.json"
        destination = self.tmp / "b.json"
        source.write_text("payload", encoding="utf-8")
        calls = {"n": 0}
        real_replace = os.replace
        def flaky(replace_source, replace_destination):
            calls["n"] += 1
            if calls["n"] == 1:
                raise PermissionError("transient reader lock")
            return real_replace(replace_source, replace_destination)
        logged: list[str] = []
        with mock.patch("os.replace", side_effect=flaky):
            rename_with_bounded_retry(source, destination, attempts=3,
                                      delay_seconds=0.0, log=logged.append)
        self.assertEqual(calls["n"], 2)
        assert logged and "attempt 1/3" in logged[0]
        assert destination.read_text(encoding="utf-8") == "payload"


class WatchdogTestCase(LoopTestCase):
    """Loop watchdog tests reuse the standard loop fixture infrastructure."""

    def test_watchdog_disabled_by_default_runs_normally(self):
        write_launch_gates(self.root, decided=True)
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=2, executor=executor).run()
        self.assertEqual(summary["cycles"], 2)
        self.assertNotIn("WATCHDOG_CYCLE_OVERFLOW",
                         summary.get("stop_reason") or "")

    def test_watchdog_stops_at_clean_boundary_with_durable_log(self):
        write_launch_gates(self.root, decided=True)
        executor = MockExecutor(self.root)
        loop = self.make_loop(max_cycles=3, executor=executor,
                              max_cycle_seconds=0.0)
        summary = loop.run()
        self.assertEqual(summary["stop_reason"], "WATCHDOG_CYCLE_OVERFLOW")
        state = json.loads(loop.state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["last_stop_reason"], "WATCHDOG_CYCLE_OVERFLOW")
        self.assertEqual(state["status"], "STOPPED")
        journal = [json.loads(line) for line in
                   loop.journal_path.read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        overflow = [row for row in journal
                    if row.get("event") == "phase_watchdog_overflow"]
        self.assertEqual(len(overflow), 1)
        self.assertEqual(overflow[0]["bound_seconds"], 0.0)
        # Exactly one cycle actually ran: the watchdog never skips forward.
        self.assertEqual(summary["cycles"], 1)
