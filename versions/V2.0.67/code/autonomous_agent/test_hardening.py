"""Hardening and bounded autonomous-loop tests (MAIN TASK 5 §10).

Verified here:
* network denial inside the experiment sandbox,
* credential-variable scrubbing and GPU disabling,
* whole-process-tree termination on timeout,
* duplicate experiment prevention via spec-hash registry,
* global kill switch terminating the active subprocess tree,
* a bounded multi-experiment loop: hypothesis generation -> isolation ->
  evaluation -> accept/reject -> version promotion -> research-memory updates ->
  crash recovery -> restart/resume -> stop behavior.

All fixtures are synthetic test scaffolding; no real market data is used and no
scientific claim is produced by these tests.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from autonomous_agent import hardening
from autonomous_agent.core import Supervisor, tree_sha256

PY = sys.executable


class NetworkDenialTests(unittest.TestCase):
    def test_network_access_is_denied_in_the_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            guard = hardening.install_network_guard(workspace)
            env = hardening.scrubbed_environment(os.environ, seed=42, experiment_id="net-test")
            env["PYTHONPATH"] = str(guard)
            outcome = hardening.run_with_limits(
                [PY, "-c", "import socket; socket.create_connection(('127.0.0.1', 9), 1)"],
                cwd=workspace, env=env, timeout=30.0, limits=hardening.DEFAULT_LIMITS,
            )
            self.assertNotEqual(outcome["returncode"], 0)
            self.assertIn("Network access is disabled", outcome["stderr"])

    def test_explicitly_reviewed_network_access_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            guard = hardening.install_network_guard(workspace)
            env = hardening.scrubbed_environment(os.environ, seed=42, experiment_id="net-allow",
                                                 allow_network=True)
            env["PYTHONPATH"] = str(guard)
            outcome = hardening.run_with_limits(
                [PY, "-c", "import socket; s=socket.socket(); s.close(); print('ok')"],
                cwd=workspace, env=env, timeout=30.0, limits=hardening.DEFAULT_LIMITS,
            )
            self.assertEqual(outcome["returncode"], 0)


class EnvironmentScrubbingTests(unittest.TestCase):
    def test_credentials_are_scrubbed_and_gpu_disabled(self) -> None:
        base = dict(os.environ)
        base["MY_BROKER_TOKEN"] = "super-secret"
        base["SOME_API_KEY"] = "abc"
        base["CUDA_VISIBLE_DEVICES"] = "0"
        env = hardening.scrubbed_environment(base, seed=7, experiment_id="env-test")
        self.assertNotIn("MY_BROKER_TOKEN", env)
        self.assertNotIn("SOME_API_KEY", env)
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(env["NVIDIA_VISIBLE_DEVICES"], "none")
        self.assertEqual(env["AUTONOMOUS_ALLOW_NETWORK"], "0")
        self.assertEqual(env["PYTHONHASHSEED"], "7")


class ProcessTreeTests(unittest.TestCase):
    def test_timeout_terminates_the_whole_process_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            pidfile = workspace / "pids.txt"
            parent_code = (
                "import os, subprocess, sys, time\n"
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
                f"open({str(pidfile)!r}, 'w').write(f'{{os.getpid()}},{{child.pid}}')\n"
                "time.sleep(120)\n"
            )
            env = hardening.scrubbed_environment(os.environ, seed=1, experiment_id="tree-test")
            outcome = hardening.run_with_limits(
                [PY, "-c", parent_code], cwd=workspace, env=env,
                timeout=3.0, limits={**hardening.DEFAULT_LIMITS, "timeout_seconds": 3.0},
            )
            self.assertTrue(outcome["timed_out"])
            parent_pid, child_pid = (int(part) for part in pidfile.read_text().split(","))
            self.assertFalse(hardening.process_alive(parent_pid))
            self.assertFalse(hardening.process_alive(child_pid))

    def test_kill_switch_terminates_the_recorded_active_tree(self) -> None:
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            state_root = Path(directory)
            process = subprocess.Popen([PY, "-c", "import time; time.sleep(120)"])
            hardening.record_active_child(state_root, process.pid, "exp-x", "experiment")
            result = hardening.kill_active_subprocess_tree(state_root)
            self.assertTrue(result["killed"])
            self.assertFalse(hardening.process_alive(process.pid))
            self.assertFalse(hardening.active_child_path(state_root).exists())


class DuplicatePreventionTests(unittest.TestCase):
    SPEC = {
        "experiment_id": "exp-1", "parent_version": "V1.0.1",
        "hypothesis": "A written hypothesis for the duplicate-prevention fixture.",
        "proposed_change": {
            "summary": "Add one fixture module under the experimentable surface.",
            "files": [{"path": "autonomous_agent/experiments/run_experiment.py",
                       "content": "print('fixture candidate')\n"}],
        },
        "files_allowed_to_change": ["autonomous_agent/experiments"],
        "evaluation_protocol": {"acceptance_criteria": {"primary_metric_min_delta": 0.0}},
        "random_seed": 42, "resource_limits": {}, "timeout": 60.0,
        "allow_repeat": False,
    }

    def test_duplicate_spec_is_refused_unless_explicitly_intended(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = hardening.SpecRegistry(Path(directory))
            allowed, _ = registry.check(self.SPEC)
            self.assertTrue(allowed)
            registry.record(self.SPEC, "exp-1", "2026-10-02T00:00:00+00:00")
            same = {**self.SPEC, "experiment_id": "exp-2"}  # same science, new id
            allowed, reason = registry.check(same)
            self.assertFalse(allowed)
            self.assertIn("Duplicate experiment specification", reason)
            deliberate = {**same, "allow_repeat": True}
            allowed, _ = registry.check(deliberate)
            self.assertTrue(allowed)

    def test_adapter_blocks_duplicate_specs_without_running_commands(self) -> None:
        from autonomous_agent.experiment_adapter import ExperimentAdapter, ExperimentSpec
        calls: list[str] = []

        def factory(workspace: Path) -> dict[str, list[str]]:
            calls.append(str(workspace))
            return {"unit_tests": [PY, "-c", "print('ok')"]}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "autonomous_agent/experiments").mkdir(parents=True)
            adapter = ExperimentAdapter(root=root, command_factory=factory)
            spec_dict = dict(self.SPEC)
            spec = ExperimentSpec.from_dict({**spec_dict, "experiment_id": "dup-a"})
            state = {"status": "REPRODUCED", "pipeline_fingerprint": adapter.pipeline_fingerprint()}
            adapter.baseline_state_path.parent.mkdir(parents=True, exist_ok=True)
            adapter.baseline_state_path.write_text(json.dumps(state), encoding="utf-8")
            first = adapter.run_experiment(spec)
            self.assertNotEqual(first.status, "BLOCKED")  # may fail on evaluation, not on dedupe
            second = adapter.run_experiment(
                ExperimentSpec.from_dict({**spec_dict, "experiment_id": "dup-b"}))
            self.assertEqual(second.status, "BLOCKED")
            self.assertTrue(any("Duplicate" in blocker for blocker in second.blockers))


class BoundedAutonomousLoopTests(unittest.TestCase):
    """TASK 5 §10: one bounded multi-experiment run exercising the full loop."""

    def _ready_root(self, root: Path) -> dict:
        (root / "study_files/outputs/study_v1/development").mkdir(parents=True)
        (root / "study_files/outputs/v2/_ohlcv").mkdir(parents=True)
        (root / "study_files/outputs/study_v1/development/event_table.csv").write_text("x\n1\n")
        (root / "study_files/outputs/v2/demand_zone_v2_dataset.csv").write_text(
            "ticker,date\nAAA,2025-01-02\n")
        for index in range(153):
            (root / f"study_files/outputs/v2/_ohlcv/T{index:03d}.csv").write_text(
                "date,open,high,low,close,volume\n")
        (root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json").write_text("{}")
        champion = {
            "version": "V1.0.1", "code_revision": "rev", "dataset_id": "dataset",
            "dataset_sha256": "datahash", "feature_set": ["x"], "model": "baseline",
            "baseline_id": "TEST_BASELINE", "baseline_kind": "historical_reproduction",
            "lineage": {"relation": "reproduction", "parent": "V1.0.1"},
            "target_definition": "target", "training_period": "train",
            "validation_period": "valid", "research_test_period": "research",
            "holdout_policy": {"status": "SEALED"}, "metrics": {"auc": 0.70},
            "backtest": {"note": "simulation"}, "leakage_status": "PASS",
            "validation_status": "REPRODUCED", "known_limitations": ["synthetic"],
            "reproduction_command": "python -m test",
        }
        (root / "CHAMPION.json").write_text(json.dumps(champion), encoding="utf-8")
        (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        (root / "VERSION_HISTORY.md").write_text("# Version History\n", encoding="utf-8")
        return champion

    def _accept_outcome(self, root: Path) -> dict:
        candidate = root / "autonomous_agent/candidates/exp-accept"
        candidate.mkdir(parents=True, exist_ok=True)
        (candidate / "model.py").write_text("model = 'candidate'\n", encoding="utf-8")
        metadata = {
            "dataset_id": "dataset-v2", "dataset_sha256": "datahash2",
            "feature_set": ["x", "z"], "model": "baseline+z", "target_definition": "target",
            "training_period": "train", "validation_period": "valid",
            "research_test_period": "research", "metrics": {"auc": 0.72},
            "backtest": {"note": "simulation"}, "known_limitations": ["synthetic test"],
            "reproduction_command": "python -m test",
        }
        return {
            "status": "ACCEPTED",
            "checks": {key: "PASS" for key in
                       ("unit", "leakage", "walk_forward", "robustness", "evaluation")},
            "results": {"primary_metric": 0.72, "uncertainty_interval": [0.7, 0.73],
                        "practical_effect": 0.02, "decision_criteria_passed": True,
                        "calibration": {}, "subgroup_stability": {},
                        "per_seed_metrics": [0.72, 0.71], "complexity_delta": 1,
                        "runtime_delta": 0.1, "backtest": {}},
            "candidate_path": str(candidate), "reproduction_command": "python -m test",
            "artifact_sha256": tree_sha256(candidate), "release_metadata": metadata,
            "holdout_touched": False,
        }

    def _reject_outcome(self, root: Path) -> dict:
        return {
            "status": "REJECTED",
            "checks": {"unit": "PASS", "leakage": "FAIL", "walk_forward": "PASS",
                       "robustness": "PASS", "evaluation": "PASS"},
            "results": {}, "candidate_path": str(root / "autonomous_agent/candidates/exp-reject"),
            "holdout_touched": False,
            "rejection_reason": "Synthetic gate failure for loop testing.",
        }

    def test_bounded_multi_experiment_loop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            state_root = Path(directory) / "state"
            root.mkdir()
            self._ready_root(root)
            calls: list[str] = []

            def runner(hypothesis, report):
                calls.append(hypothesis.direction)
                if len(calls) == 1:
                    return self._accept_outcome(root)
                if len(calls) == 2:
                    return self._reject_outcome(root)
                if len(calls) == 3:
                    raise RuntimeError("synthetic model crash")
                (state_root / "STOP").write_text("stop\n", encoding="utf-8")
                return self._reject_outcome(root)

            supervisor = Supervisor(root=root, state_root=state_root,
                                    idle_seconds=0.0, max_cycles=4, experiment_runner=runner)
            state = supervisor.load_state()
            state.setdefault("holdout", {})["status"] = "sealed"
            supervisor.save_state(state)

            # Cycle 1: hypothesis generated -> ACCEPTED -> version promoted.
            state, report = supervisor.cycle(state)
            self.assertTrue(report.ready)
            self.assertEqual(calls[0], report.hypothesis.direction)
            self.assertEqual(state["experiments"][-1]["status"], "ACCEPTED")
            champion = json.loads((root / "CHAMPION.json").read_text(encoding="utf-8"))
            self.assertEqual(champion["version"], "V1.0.2")
            self.assertTrue((root / "versions" / "V1.0.2").is_dir())
            self.assertEqual(state["experiments"][-1]["accepted_version"], "V1.0.2")

            # Research memory carries the mandated research-record fields.
            memory = json.loads(
                (state_root / "research_memory.json").read_text(encoding="utf-8"))
            record = memory["discoveries"][-1]
            for field in ("hypothesis", "motivation", "prior_evidence", "proposed_change",
                          "expected_outcome", "actual_result", "conclusion",
                          "next_research_implication"):
                self.assertIn(field, record, f"research record missing {field}")
            human = (root / "RESEARCH_MEMORY.md").read_text(encoding="utf-8")
            self.assertIn("Next research implication", human)

            # Cycle 2: REJECTED -> recorded, champion untouched.
            state, _ = supervisor.cycle(state)
            self.assertEqual(state["experiments"][-1]["status"], "REJECTED")
            self.assertIsNone(state["experiments"][-1].get("accepted_version"))
            champion_after = json.loads((root / "CHAMPION.json").read_text(encoding="utf-8"))
            self.assertEqual(champion_after["version"], "V1.0.2")
            self.assertEqual(state["consecutive_rejections"], 1)

            # Cycle 3: runner crash -> supervisor survives and records the failure.
            state, _ = supervisor.cycle(state)
            self.assertEqual(state["experiments"][-1]["status"], "FAILED")
            self.assertIn("synthetic model crash", state["experiments"][-1]["failure"])

            # Restart/resume: a fresh supervisor instance sees all prior records.
            resumed = Supervisor(root=root, state_root=state_root,
                                 idle_seconds=0.0, max_cycles=1, experiment_runner=runner)
            state2 = resumed.load_state()
            self.assertEqual(len(state2["experiments"]), 3)
            # Crash recovery: an interrupted RUNNING experiment is marked, not trusted.
            state2["experiments"][-1]["status"] = "RUNNING"
            resumed._recover_interrupted_experiment(state2)
            self.assertIn(state2["experiments"][-1]["status"],
                          {"FAILED_RECOVERED", "REJECTED", "FAILED"})

            # Stop behavior: the runner requests STOP during its first cycle and
            # the loop must end immediately, before any further experiments.
            supervisor2 = Supervisor(root=root, state_root=state_root,
                                     idle_seconds=0.0, max_cycles=5, experiment_runner=runner)
            result = supervisor2.run()
            self.assertEqual(result, 0)
            state3 = supervisor2.load_state()
            self.assertEqual(len(state3["experiments"]), 4)  # one cycle, then STOP
            self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    unittest.main()
