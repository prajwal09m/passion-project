"""Unit tests for the supervisor; these use only temporary synthetic state."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_agent.core import (
    VersionManager,
    ResearchPlanner,
    Supervisor,
    tree_sha256,
    check_prerequisites,
    initial_state,
    parse_champion,
    write_json_atomic,
)
from autonomous_agent.spec_recipes import RECIPE_LIBRARY


class PlannerTests(unittest.TestCase):
    def test_planner_proposes_question_from_historical_findings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            planner = ResearchPlanner(Path(directory) / "memory.json")
            hypothesis = planner.plan(initial_state())
            self.assertEqual(hypothesis.direction, "data_quality")
            self.assertIn("point-in-time", hypothesis.question)
            self.assertTrue(hypothesis.required_inputs)

    def test_planner_uses_stagnation_to_prioritize_structural_directions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            planner = ResearchPlanner(Path(directory) / "memory.json")
            state = initial_state()
            state["stagnation_mode"] = True
            state["direction_stats"] = {"data_quality": {"attempts": 100, "accepted": 0}}
            state["experiments"] = [{} for _ in range(100)]
            chosen = planner.plan(state)
            self.assertIn(chosen.direction, {"data_quality", "validation", "target_design", "model_architecture"})

    def test_permanently_blocked_direction_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            memory_path = Path(directory) / "memory.json"
            memory_path.write_text(json.dumps({"discoveries": [{"direction": "data_quality", "status": "BLOCKED", "permanent": True}]}), encoding="utf-8")
            chosen = ResearchPlanner(memory_path).plan(initial_state())
            self.assertNotEqual(chosen.direction, "data_quality")

    def test_planner_respects_allowed_direction_filter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            planner = ResearchPlanner(Path(directory) / "memory.json")
            chosen = planner.plan(initial_state(), allowed_directions={"model_architecture"})
            self.assertEqual(chosen.direction, "model_architecture")
            # Without a filter the planner keeps its full exploration surface.
            self.assertIn(planner.plan(initial_state()).direction,
                          {h.direction for h in ResearchPlanner.BASE_DIRECTIONS})


class ReadinessTests(unittest.TestCase):
    def test_missing_champion_and_source_inputs_block_research(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "study_files").mkdir()
            (root / "study_files" / "MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json").write_text("{}", encoding="utf-8")
            (root / "study_files" / "outputs" / "study_v1" / "development").mkdir(parents=True)
            (root / "study_files" / "outputs" / "study_v1" / "development" / "event_table.csv").touch()
            state_root = root / "state"
            planner = ResearchPlanner(state_root / "memory.json")
            report = check_prerequisites(root, initial_state(), planner)
            self.assertFalse(report.ready)
            self.assertIsNone(report.champion_id)
            self.assertTrue(any("champion" in reason.lower() for reason in report.reasons))
            self.assertTrue(any("153-symbol" in reason for reason in report.reasons))

    def test_champion_requires_reproduced_evidence_and_sealed_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CHAMPION.json"
            path.write_text(json.dumps({"version": "V1.0.1", "leakage_status": "PASS"}), encoding="utf-8")
            champion, reasons = parse_champion(path)
            self.assertIsNone(champion)
            self.assertTrue(reasons)


class VersionManagerTests(unittest.TestCase):
    def test_patch_version_increment_handles_two_digit_patch(self) -> None:
        self.assertEqual(VersionManager.next_version("V1.0.9"), "V1.0.10")
        self.assertEqual(VersionManager.next_version("V1.0.10"), "V1.0.11")

    def test_promote_snapshots_only_verified_candidate_and_updates_champion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "autonomous_agent" / "candidates" / "exp-1"
            candidate.mkdir(parents=True)
            (candidate / "model.py").write_text("model = 'candidate'\n", encoding="utf-8")
            artifact_hash = tree_sha256(candidate)
            champion = {
                "version": "V1.0.9", "code_revision": "old", "dataset_id": "dataset",
                "dataset_sha256": "datahash", "feature_set": ["x"], "model": "baseline",
                "baseline_id": "TEST_BASELINE", "baseline_kind": "historical_reproduction",
                "lineage": {"relation": "reproduction", "parent": "V1.0.1"},
                "target_definition": "target", "training_period": "train", "validation_period": "valid",
                "research_test_period": "research", "holdout_policy": {"status": "SEALED"},
                "metrics": {"auc": 0.70}, "backtest": {"note": "simulation"},
                "leakage_status": "PASS", "validation_status": "REPRODUCED",
                "known_limitations": ["synthetic baseline"], "reproduction_command": "python -m test",
            }
            metadata = {
                "dataset_id": "dataset-v2", "dataset_sha256": "datahash2", "feature_set": ["x", "z"],
                "model": "baseline+z", "target_definition": "target", "training_period": "train",
                "validation_period": "valid", "research_test_period": "research", "metrics": {"auc": 0.72},
                "backtest": {"note": "simulation"}, "known_limitations": ["synthetic test"],
                "reproduction_command": "python -m test",
            }
            experiment = {"id": "exp-1", "status": "ACCEPTED", "hypothesis": "test hypothesis"}
            (root / "CHAMPION.json").write_text(json.dumps(champion), encoding="utf-8")
            (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
            (root / "VERSION_HISTORY.md").write_text("# Version History\n", encoding="utf-8")
            outcome = {
                "status": "ACCEPTED", "checks": {key: "PASS" for key in ("unit", "leakage", "walk_forward", "robustness", "evaluation")},
                "results": {"primary_metric": 0.72, "uncertainty_interval": [0.7, 0.73], "practical_effect": 0.02,
                            "decision_criteria_passed": True, "calibration": {}, "subgroup_stability": {},
                            "per_seed_metrics": [0.72, 0.71], "complexity_delta": 1, "runtime_delta": 0.1, "backtest": {}},
                "candidate_path": str(candidate), "reproduction_command": "python -m test",
                "artifact_sha256": artifact_hash, "release_metadata": metadata, "holdout_touched": False,
            }
            released = VersionManager(root).promote(champion, experiment, outcome)
            self.assertEqual(released.name, "V1.0.10")
            self.assertEqual(json.loads((root / "CHAMPION.json").read_text(encoding="utf-8"))["version"], "V1.0.10")
            self.assertTrue((released / "version.json").is_file())
            self.assertTrue((released / "CHANGELOG.md").is_file())
            with self.assertRaises(ValueError):
                VersionManager(root).promote(champion, experiment, outcome)

    def test_promote_refuses_candidate_outside_sandbox(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "outside"
            candidate.mkdir()
            with self.assertRaises(ValueError):
                VersionManager(root).promote({}, {"status": "ACCEPTED"}, {"candidate_path": str(candidate)})


class GateTests(unittest.TestCase):
    def test_leakage_failure_rejects_even_with_high_metrics(self) -> None:
        experiment = {}
        outcome = {
            "status": "ACCEPTED",
            "checks": {"unit": "PASS", "leakage": "FAIL", "walk_forward": "PASS", "robustness": "PASS", "evaluation": "PASS"},
            "results": {"primary_metric": 0.99, "uncertainty_interval": [0.98, 0.995], "practical_effect": 0.1, "complexity_delta": 0, "runtime_delta": 0},
            "candidate_path": "candidate",
            "reproduction_command": "python -m experiment",
            "artifact_sha256": "abc",
        }
        Supervisor._validate_outcome(experiment, outcome)
        self.assertEqual(outcome["status"], "REJECTED")

    def test_holdout_access_rejects_candidate(self) -> None:
        experiment = {}
        outcome = {
            "status": "ACCEPTED",
            "checks": {key: "PASS" for key in ("unit", "leakage", "walk_forward", "robustness", "evaluation")},
            "results": {"primary_metric": 0.8, "uncertainty_interval": [0.75, 0.85], "practical_effect": 0.01, "decision_criteria_passed": True, "calibration": {}, "subgroup_stability": {}, "per_seed_metrics": [], "complexity_delta": 0, "runtime_delta": 0, "backtest": {}},
            "candidate_path": "candidate",
            "reproduction_command": "python -m experiment",
            "artifact_sha256": "abc",
            "holdout_touched": True,
        }
        Supervisor._validate_outcome(experiment, outcome)
        self.assertEqual(outcome["status"], "REJECTED")

    def test_acceptance_requires_all_metrics_and_artifact_fingerprints(self) -> None:
        outcome = {
            "status": "ACCEPTED",
            "checks": {key: "PASS" for key in ("unit", "leakage", "walk_forward", "robustness", "evaluation")},
            "results": {"primary_metric": 0.8},
            "candidate_path": "candidate",
            "reproduction_command": "python -m experiment",
            "artifact_sha256": "abc",
        }
        with self.assertRaises(ValueError):
            Supervisor._validate_outcome({}, outcome)


class RejectionReasonTests(unittest.TestCase):
    """Meaningful rejection reasons (e.g. provider refusal codes) are preserved."""

    def _failing_gate_outcome(self, **overrides):
        outcome = {
            "status": "ACCEPTED",
            "checks": {"unit": "PASS", "leakage": "PASS", "walk_forward": "PASS",
                       "robustness": "PASS", "evaluation": "FAIL"},
            "results": {},
            "candidate_path": "candidate",
        }
        outcome.update(overrides)
        return outcome

    def test_existing_rejection_reason_is_not_masked(self) -> None:
        reason = "[BUDGET_EXHAUSTED] recipe attempt budget exhausted (3/3); refused."
        outcome = self._failing_gate_outcome(rejection_reason=reason)
        Supervisor._validate_outcome({}, outcome)
        self.assertEqual(outcome["status"], "REJECTED")
        self.assertEqual(outcome["rejection_reason"], reason)

    def test_generic_gate_message_only_fills_a_missing_reason(self) -> None:
        outcome = self._failing_gate_outcome()
        Supervisor._validate_outcome({}, outcome)
        self.assertEqual(outcome["status"], "REJECTED")
        self.assertEqual(outcome["rejection_reason"],
                         "One or more mandatory scientific gates did not PASS.")
        blank = self._failing_gate_outcome(rejection_reason="   ")
        Supervisor._validate_outcome({}, blank)
        self.assertEqual(blank["rejection_reason"],
                         "One or more mandatory scientific gates did not PASS.")

    def test_preservation_never_relaxes_the_fail_closed_decision(self) -> None:
        outcome = self._failing_gate_outcome(rejection_reason="[UNSUPPORTED] no recipe covers it")
        Supervisor._validate_outcome({}, outcome)
        # A preserved reason must never leave the outcome non-REJECTED.
        self.assertEqual(outcome["status"], "REJECTED")


def prepare_generation_root(root: Path, *, enabled: bool = True,
                            spent: dict | None = None) -> Path:
    """Minimal fixture for the supervisor's autonomous-generation gating."""
    (root / "autonomous_agent" / "state").mkdir(parents=True, exist_ok=True)
    write_json_atomic(root / "autonomous_agent" / "autonomy_config.json",
                      {"schema_version": 1, "allow_autonomous_specs": enabled})
    write_json_atomic(root / "CHAMPION.json", {"version": "V2.0.0"})
    attempts = []
    for recipe in RECIPE_LIBRARY:
        for index in range((spent or {}).get(recipe.recipe_id, 0)):
            attempts.append({"recipe_id": recipe.recipe_id,
                             "experiment_id": f"exp-{recipe.recipe_id}-{index}",
                             "spec_sha256": f"{index:064d}",
                             "at": "2026-10-04T00:00:00+00:00"})
    write_json_atomic(root / "autonomous_agent" / "state" / "spec_attempts.json",
                      {"schema_version": 1, "attempts": attempts})
    return root


def fully_spent() -> dict:
    return {recipe.recipe_id: recipe.max_attempts for recipe in RECIPE_LIBRARY}


class ExhaustionPolicyTests(unittest.TestCase):
    """When nothing can ever be generated again, stop proposing doomed attempts."""

    def test_all_budgets_spent_marks_research_exhausted_and_proposes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            prepare_generation_root(root, spent=fully_spent())
            state_root = root / "autonomous_agent" / "state"
            calls = []
            supervisor = Supervisor(root=root, state_root=state_root,
                                    experiment_runner=lambda *_: calls.append("ran") or {})
            state, report = supervisor.cycle(supervisor.load_state())
            self.assertTrue(state["research_exhausted"])
            self.assertEqual(state["last_cycle_status"], "RESEARCH_EXHAUSTED")
            self.assertFalse(report.ready)
            self.assertIsNone(report.hypothesis)
            self.assertEqual(state["experiments"], [])  # no doomed experiment record
            self.assertEqual(calls, [])  # no attempt was generated or executed
            self.assertIn("research_exhausted",
                          (state_root / "events.jsonl").read_text(encoding="utf-8"))

    def test_research_exhaustion_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            prepare_generation_root(root, spent=fully_spent())
            state_root = root / "autonomous_agent" / "state"
            first = Supervisor(root=root, state_root=state_root,
                               experiment_runner=lambda *_: {})
            state, _ = first.cycle(first.load_state())
            self.assertTrue(state["research_exhausted"])
            # A fresh supervisor (crash/restart) re-derives the terminal state
            # from the durable ledger and still proposes nothing.
            second = Supervisor(root=root, state_root=state_root,
                                experiment_runner=lambda *_: {}) 
            state2, report2 = second.cycle(second.load_state())
            self.assertTrue(state2["research_exhausted"])
            self.assertEqual(state2["experiments"], [])
            self.assertFalse(report2.ready)
            # And the run loop exits without generating any attempt.
            runner = Supervisor(root=root, state_root=state_root, max_cycles=5,
                                idle_seconds=0.01, experiment_runner=lambda *_: {})
            self.assertEqual(runner.run(), 0)
            final = runner.load_state()
            self.assertTrue(final["research_exhausted"])
            self.assertEqual(final["experiments"], [])

    def test_partial_capacity_restricts_proposals_to_viable_directions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            spent = {recipe.recipe_id: recipe.max_attempts
                     for recipe in RECIPE_LIBRARY if recipe.direction == "calibration"}
            prepare_generation_root(root, spent=spent)
            state_root = root / "autonomous_agent" / "state"
            supervisor = Supervisor(root=root, state_root=state_root,
                                    experiment_runner=lambda *_: {})
            state, report = supervisor.cycle(supervisor.load_state())
            self.assertFalse(state.get("research_exhausted", False))
            self.assertEqual(state["experiments"][-1]["status"], "BLOCKED")
            # The calibration recipe is out of budget; the planner must not
            # propose it while viable directions remain.
            self.assertIn(state["experiments"][-1]["direction"],
                          {"feature_engineering", "model_architecture"})
            self.assertIsNotNone(report.hypothesis)

    def test_disabled_flag_leaves_supervisor_behavior_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            prepare_generation_root(root, enabled=False, spent=fully_spent())
            state_root = root / "autonomous_agent" / "state"
            supervisor = Supervisor(root=root, state_root=state_root,
                                    experiment_runner=lambda *_: {})
            state, _ = supervisor.cycle(supervisor.load_state())
            self.assertFalse(state.get("research_exhausted", False))
            self.assertEqual(len(state["experiments"]), 1)  # normal blocked flow
            self.assertEqual(state["experiments"][-1]["status"], "BLOCKED")


class SupervisorTests(unittest.TestCase):
    def test_blocked_cycle_records_hypothesis_without_running_scripts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            state_root = Path(directory) / "state"
            calls = []
            supervisor = Supervisor(root=root, state_root=state_root,
                                    experiment_runner=lambda *_: calls.append("ran") or {})
            state, report = supervisor.cycle(supervisor.load_state())
            self.assertFalse(report.ready)
            self.assertEqual(state["experiments"][-1]["status"], "BLOCKED")
            self.assertEqual(calls, [])
            self.assertTrue((state_root / "agent_state.json").is_file())
            self.assertTrue((state_root / "research_memory.json").is_file())
            self.assertTrue((state_root / "events.jsonl").is_file())

    def test_blocked_planner_explores_distinct_directions_then_idles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            state_root = Path(directory) / "state"
            supervisor = Supervisor(root=root, state_root=state_root)
            state = supervisor.load_state()
            directions = []
            for _ in range(12):
                state, _ = supervisor.cycle(state)
                if state["experiments"] and state["experiments"][-1]["status"] == "BLOCKED":
                    directions.append(state["experiments"][-1]["direction"])
                if state.get("last_cycle_status") == "WAITING_ON_PREREQUISITES":
                    directions.pop()  # final WAITING cycle reports previous experiment in state
                    break
            self.assertEqual(len(directions), len(set(directions)))
            self.assertEqual(state["last_cycle_status"], "WAITING_ON_PREREQUISITES")
            count = len(state["experiments"])
            state, _ = supervisor.cycle(state)
            self.assertEqual(len(state["experiments"]), count)

    def test_stale_lock_recovers_and_live_lock_is_not_stolen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_root = Path(directory) / "state"
            state_root.mkdir()
            lock = state_root / "supervisor.lock"
            lock.write_text("pid=999999999 started=old\n", encoding="utf-8")
            supervisor = Supervisor(state_root=state_root)
            self.assertTrue(supervisor.acquire_lock())
            self.assertFalse(Supervisor(state_root=state_root).acquire_lock())
            supervisor.release_lock()
            self.assertFalse(lock.exists())

    def test_crash_recovery_marks_all_running_experiments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_root = Path(directory)
            supervisor = Supervisor(state_root=state_root)
            state = initial_state()
            state["experiments"] = [
                {"id": "exp-1", "direction": "validation", "status": "RUNNING"},
                {"id": "exp-2", "direction": "features", "status": "RUNNING"},
            ]
            supervisor._recover_interrupted_experiment(state)
            self.assertTrue(all(item["status"] == "FAILED_RECOVERED" for item in state["experiments"]))
            self.assertEqual(len((state_root / "events.jsonl").read_text(encoding="utf-8").splitlines()), 2)
            second_state = initial_state()
            supervisor._recover_interrupted_experiment(second_state)
            self.assertEqual(len((state_root / "events.jsonl").read_text(encoding="utf-8").splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
