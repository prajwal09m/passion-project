"""Unit tests for the experiment adapter; synthetic fixtures only.

These tests prove the execution mechanics (isolation, allowlist, evaluation
gates, fail-safe destruction, supervisor contract). They never fabricate
research data: all fixtures live in temporary directories and every candidate
"pipeline" is an obviously synthetic test module.
"""
from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from autonomous_agent.core import (
    Hypothesis,
    PrerequisiteReport,
    Supervisor,
    tree_sha256,
    write_json_atomic,
)
from autonomous_agent.experiment_adapter import (
    AllowlistViolation,
    ExperimentAdapter,
    ExperimentResult,
    ExperimentSpec,
    FileChange,
    build_experiment_runner,
)


def make_project(root: Path) -> None:
    (root / "autonomous_agent/experiments").mkdir(parents=True)
    (root / "autonomous_agent/__init__.py").write_text("", encoding="utf-8")
    (root / "autonomous_agent/experiments/__init__.py").write_text("", encoding="utf-8")
    (root / "study_files/outputs").mkdir(parents=True)
    (root / "study_files/inputs.csv").write_text("ticker,date\nAAA,2025-01-02\n", encoding="utf-8")


def benign_factory(workspace: Path) -> dict[str, list[str]]:
    return {
        "unit_tests": [sys.executable, "-c", "print('unit ok')"],
        "experiment": [sys.executable, "-m", "autonomous_agent.experiments.run_experiment"],
    }


def counting_factory(calls: list) -> object:
    def factory(workspace: Path) -> dict[str, list[str]]:
        calls.append(str(workspace))
        return benign_factory(workspace)
    return factory


def evaluation_payload(**overrides):
    payload = {
        "results": {
            "primary_metric": {"name": "pooled_roc_auc", "value": 0.71, "champion_value": 0.70, "delta": 0.01},
            "uncertainty_interval": {"level": 0.95, "lower": 0.001, "upper": 0.02},
            "practical_effect": {"description": "small positive effect"},
            "decision_criteria_passed": True,
            "calibration": {"brier_score": 0.19},
            "subgroup_stability": {"by_year": {"2023": 0.01, "2024": 0.02, "2025": 0.008}},
            "per_seed_metrics": {"42": {"auc": 0.71}, "43": {"auc": 0.709}, "44": {"auc": 0.711}},
            "complexity_delta": {"parameters": 0},
            "runtime_delta": {"seconds": 1.5},
            "backtest": {"profit_factor": 1.02},
        },
        "walk_forward": {
            "purge_verified": True,
            "folds": [
                {"name": "2023", "train_end": "2022-12-31", "validation_start": "2023-01-01", "validation_end": "2023-12-31"},
                {"name": "2024", "train_end": "2023-12-31", "validation_start": "2024-01-01", "validation_end": "2024-12-31"},
                {"name": "2025", "train_end": "2024-12-31", "validation_start": "2025-01-01", "validation_end": "2025-12-31"},
            ],
        },
        "release_metadata": {
            "dataset_id": "fixture-dataset",
            "dataset_sha256": "0" * 64,
            "feature_set": ["fixture_feature_a", "fixture_feature_b"],
            "model": "fixture-model",
            "target_definition": "fixture-target",
            "training_period": "2021-2022",
            "validation_period": "2023-2025",
            "research_test_period": "none (final holdout sealed)",
            "metrics": {"pooled_roc_auc": 0.71},
            "backtest": {"profit_factor": 1.02},
            "known_limitations": ["synthetic fixture; not research evidence"],
            "reproduction_command": "py -3 -m autonomous_agent.experiments.run_experiment",
        },
    }
    for key, value in overrides.items():
        payload[key] = value
    return payload


def module_with(body: str) -> str:
    return (
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "def main():\n"
        "    outputs = Path('outputs')\n"
        "    outputs.mkdir(exist_ok=True)\n"
        + textwrap.indent(body, "    ")
        + "\n\nif __name__ == '__main__':\n"
        "    main()\n"
    )


ACCEPTANCE_BODY = (
    "payload = PAYLOAD_JSON\n"
    "(outputs / 'evaluation.json').write_text(json.dumps(payload), encoding='utf-8')\n"
).replace("PAYLOAD_JSON", repr(evaluation_payload()))


def make_spec(body: str, *, change_path: str = "autonomous_agent/experiments/run_experiment.py",
              timeout: float = 120.0) -> ExperimentSpec:
    return ExperimentSpec(
        experiment_id="exp-fixture-1",
        parent_version="V1.0.1",
        hypothesis="A written, evidence-grounded hypothesis for the synthetic fixture experiment.",
        proposed_change={
            "summary": "Add the fixture experiment module under the experimentable surface.",
            "files": [{"path": change_path, "content": module_with(body)}],
        },
        files_allowed_to_change=("autonomous_agent/experiments",),
        evaluation_protocol={"acceptance_criteria": {"primary_metric_min_delta": 0.0}},
        random_seed=42,
        resource_limits={},
        timeout=timeout,
    )


def make_adapter(root: Path, factory=None) -> ExperimentAdapter:
    return ExperimentAdapter(
        root=root,
        candidates_root=root / "autonomous_agent/candidates",
        state_root=root / "autonomous_agent/state",
        command_factory=factory or benign_factory,
    )


def mark_baseline_reproduced(adapter: ExperimentAdapter) -> None:
    write_json_atomic(adapter.baseline_state_path, {
        "status": "REPRODUCED",
        "pipeline_fingerprint": adapter.pipeline_fingerprint(),
        "result": ExperimentResult(experiment_id="baseline-reproduction", status="REPRODUCED").to_dict(),
    })


class SpecTests(unittest.TestCase):
    def test_spec_round_trip_serialization(self) -> None:
        spec = make_spec(ACCEPTANCE_BODY)
        restored = ExperimentSpec.from_dict(json.loads(json.dumps(spec.to_dict())))
        self.assertEqual(restored, spec)
        self.assertEqual(len(restored.changes()), 1)

    def test_result_round_trip_serialization(self) -> None:
        result = ExperimentResult(experiment_id="exp-1", status="REJECTED", blockers=["x"],
                                  error={"message": "nope"}, metrics={"a": 1})
        restored = ExperimentResult.from_dict(json.loads(json.dumps(result.to_dict())))
        self.assertEqual(restored.to_dict(), result.to_dict())

    def test_spec_rejects_forbidden_and_unsafe_paths(self) -> None:
        for path in ("study_files/backend/demand_zone_study_v1.py",
                     "CHAMPION.json",
                     "../escape.py",
                     "/absolute/escape.py"):
            with self.subTest(path=path), self.assertRaises(AllowlistViolation):
                make_spec(ACCEPTANCE_BODY, change_path=path).validate()

    def test_spec_requires_written_hypothesis_and_change_summary(self) -> None:
        spec = make_spec(ACCEPTANCE_BODY)
        blank = ExperimentSpec.from_dict({**spec.to_dict(), "hypothesis": "   "})
        with self.assertRaises(Exception):
            blank.validate()
        empty_files = ExperimentSpec.from_dict({**spec.to_dict(),
                                                "proposed_change": {"summary": "s", "files": []}})
        with self.assertRaises(Exception):
            empty_files.validate()

    def test_spec_refuses_changes_outside_declared_allowlist(self) -> None:
        spec = ExperimentSpec.from_dict({
            **make_spec(ACCEPTANCE_BODY).to_dict(),
            "files_allowed_to_change": ("autonomous_agent/experiments/only_here.py",),
        })
        with self.assertRaises(AllowlistViolation):
            spec.validate()


class InputVerificationTests(unittest.TestCase):
    def test_missing_inputs_reported_without_fabricating_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
            verification = adapter.verify_inputs()
            after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
            self.assertEqual(before, after, "verification must be read-only")
            self.assertEqual(verification["required_blockers"],
                             ["v1_run_manifest", "v2_roster_dataset", "ohlcv_cache"])
            self.assertIn("v1_0_1_source", verification["attribution_blockers"])
            self.assertTrue(verification["sealed_holdout"]["compliant"])
            self.assertFalse(verification["inputs"]["v5_dataset"]["present"])

    def test_restored_synthetic_inputs_are_recognized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            development = root / "study_files/outputs/study_v1/development"
            models = root / "study_files/outputs/study_v1/models"
            development.mkdir(parents=True)
            models.mkdir(parents=True)
            (development / "event_table.csv").write_text("event_id\n1\n", encoding="utf-8")
            (development / "oof_predictions.csv").write_text("event_id\n1\n", encoding="utf-8")
            (models / "LightGBM_A.joblib").write_bytes(b"fixture-model-bytes")
            manifest = {
                "protocol_version": "1.0.1",
                "protocol_sha256": "486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07",
                "code_sha256": "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b",
                "artifact_sha256": {
                    "event_table.csv": _sha(development / "event_table.csv"),
                    "oof_predictions.csv": _sha(development / "oof_predictions.csv"),
                },
                "model_artifacts_sha256": {"LightGBM_A.joblib": _sha(models / "LightGBM_A.joblib")},
            }
            (development / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            v2 = root / "study_files/outputs/v2"
            v2.mkdir(parents=True)
            rows = "\n".join(f"T{i:03d},2025-01-02" for i in range(149))
            (v2 / "demand_zone_v2_dataset.csv").write_text(f"ticker,date\n{rows}\n", encoding="utf-8")
            cache = v2 / "_ohlcv"
            cache.mkdir()
            header = "Date,Open,High,Low,Close,Volume\n2025-01-02,1,1,1,1,100\n"
            names = [f"S{i:03d}" for i in range(149)] + ["SPY", "QQQ", "IWM", "XVIX"]
            for name in names:
                (cache / f"{name}.csv").write_text(header, encoding="utf-8")

            v5 = root / "study_files/outputs/v5"
            v5.mkdir(parents=True)
            (v5 / "demand_zone_v5_dataset.csv").write_text("ticker,date,x\nAAA,2025-01-02,1\n", encoding="utf-8")
            (root / "study_files/outputs/v13").mkdir(parents=True)
            (root / "study_files/outputs/v13/demand_zone_ml_dataset_v13.csv").write_text("x\n", encoding="utf-8")
            (root / "study_files/outputs/hold1").mkdir(parents=True)
            (root / "study_files/outputs/hold1/demand_zone_hold1_dataset_v1.csv").write_text("x\n", encoding="utf-8")

            verification = make_adapter(root).verify_inputs()
            for key in ("v1_run_manifest", "v2_roster_dataset", "ohlcv_cache",
                        "v5_dataset", "v13_dataset", "hold1_dataset"):
                self.assertTrue(verification["inputs"][key]["present"], key)
            self.assertEqual(verification["required_blockers"], [])


def _sha(path: Path) -> str:
    from autonomous_agent.core import sha256_file
    return sha256_file(path)


class OriginalFingerprintTests(unittest.TestCase):
    def test_promotion_snapshots_excluded_but_real_tampering_still_detected(self) -> None:
        """The `versions/` promotion snapshot store is excluded from the immutability
        fingerprint (it is agent-created, hash-verified at promotion time, and grew
        to ~444k files); any change to the guarded original tree must still flip it."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            snapshot = root / "versions/V2.0.99/code"
            snapshot.mkdir(parents=True)
            (snapshot / "note.txt").write_text("snapshot at promotion", encoding="utf-8")
            before = adapter.original_fingerprint()
            # Mutating or adding files inside versions/ must NOT change the fingerprint.
            (snapshot / "note.txt").write_text("tampered", encoding="utf-8")
            (snapshot / "extra.txt").write_text("added later", encoding="utf-8")
            self.assertEqual(adapter.original_fingerprint(), before)
            # But changing the guarded original tree must still change it.
            probe = root / "study_files/inputs.csv"
            probe.write_text(probe.read_text(encoding="utf-8") + "BBB,2025-01-03\n", encoding="utf-8")
            self.assertNotEqual(adapter.original_fingerprint(), before)


class ReproductionTests(unittest.TestCase):
    def test_reproduction_is_blocked_and_executes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            calls: list = []
            adapter = make_adapter(root, counting_factory(calls))
            result = adapter.run_reproduction()
            self.assertEqual(result.status, "BLOCKED")
            self.assertEqual(calls, [], "no pipeline command may run when inputs are missing")
            self.assertEqual(result.acceptance_recommendation, "STOP_AUTONOMOUS_EXPERIMENTATION")
            for key in ("v1_run_manifest", "v2_roster_dataset", "ohlcv_cache"):
                self.assertIn(key, result.blockers)
            state = json.loads(adapter.baseline_state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "BLOCKED")
            report = (root / "autonomous_agent/BASELINE_REPRODUCTION_REPORT.md").read_text(encoding="utf-8")
            self.assertIn("STOPPED", report)
            self.assertFalse(adapter.is_baseline_reproduced()[0])


class ExperimentLifecycleTests(unittest.TestCase):
    def test_end_to_end_accept_preserves_candidate_and_matches_supervisor_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            mark_baseline_reproduced(adapter)
            before = adapter.original_fingerprint()
            result = adapter.run_experiment(make_spec(ACCEPTANCE_BODY))
            self.assertEqual(result.status, "ACCEPTED", result.error)
            self.assertEqual(adapter.original_fingerprint(), before, "original tree must not change")
            candidate = Path(result.candidate_path)
            self.assertTrue(candidate.is_dir())
            self.assertEqual(result.artifacts["tree_sha256"], tree_sha256(candidate))
            outcome = result.to_supervisor_outcome()
            Supervisor._validate_outcome({"id": "exp-fixture-1"}, outcome)
            self.assertEqual(outcome["status"], "ACCEPTED")
            self.assertEqual(outcome["artifact_sha256"], result.artifacts["tree_sha256"])
            self.assertFalse(outcome["holdout_touched"])
            for key in ("dataset_id", "reproduction_command", "known_limitations"):
                self.assertIn(key, outcome["release_metadata"])

    def test_leakage_tokens_reject_and_destroy_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            mark_baseline_reproduced(adapter)
            payload = evaluation_payload()
            payload["results"]["forward_return_20d"] = 0.05
            body = f"payload = {payload!r}\n(outputs / 'evaluation.json').write_text(json.dumps(payload), encoding='utf-8')"
            result = adapter.run_experiment(make_spec(body))
            self.assertEqual(result.status, "REJECTED")
            self.assertEqual(result.leakage_status, "FAIL")
            self.assertIn("forward_return", result.error["message"])
            self.assertFalse((root / "autonomous_agent/candidates/exp-fixture-1/workspace").exists())

    def test_holdout_access_rejects_and_flags_holdout_touched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            mark_baseline_reproduced(adapter)
            body = (
                f"payload = {evaluation_payload()!r}\n"
                "(outputs / 'evaluation.json').write_text(json.dumps(payload), encoding='utf-8')\n"
                "prospective = Path('study_files/outputs/study_v1/prospective')\n"
                "prospective.mkdir(parents=True, exist_ok=True)\n"
                "(prospective / 'lock.json').write_text('{}', encoding='utf-8')\n"
            )
            result = adapter.run_experiment(make_spec(body))
            self.assertEqual(result.status, "REJECTED")
            self.assertEqual(result.holdout_status, "TOUCHED")
            outcome = result.to_supervisor_outcome()
            self.assertTrue(outcome["holdout_touched"])
            self.assertFalse((root / "autonomous_agent/candidates/exp-fixture-1/workspace").exists())

    def test_allowlist_violation_is_rejected_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            calls: list = []
            adapter = make_adapter(root, counting_factory(calls))
            mark_baseline_reproduced(adapter)
            result = adapter.run_experiment(
                make_spec(ACCEPTANCE_BODY, change_path="study_files/backend/demand_zone_study_v1.py"))
            self.assertEqual(result.status, "REJECTED")
            self.assertEqual(calls, [], "no command may run for a forbidden change")
            self.assertFalse((root / "autonomous_agent/candidates/exp-fixture-1/workspace").exists())

    def test_timeout_rejects_and_destroys_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            mark_baseline_reproduced(adapter)
            body = "import time\ntime.sleep(30)\n"
            result = adapter.run_experiment(make_spec(body, timeout=1.0))
            self.assertEqual(result.status, "REJECTED")
            roles = {run["role"]: run for run in result.runtime["commands"]}
            self.assertTrue(roles["experiment"]["timed_out"])
            self.assertFalse((root / "autonomous_agent/candidates/exp-fixture-1/workspace").exists())

    def test_original_tree_drift_rejects_and_destroys_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            mark_baseline_reproduced(adapter)
            drift_target = root / "drift.txt"
            body = (
                f"Path({str(drift_target)!r}).write_text('x', encoding='utf-8')\n"
                f"payload = {evaluation_payload()!r}\n"
                "(outputs / 'evaluation.json').write_text(json.dumps(payload), encoding='utf-8')\n"
            )
            result = adapter.run_experiment(make_spec(body))
            self.assertEqual(result.status, "REJECTED")
            self.assertIn("Original working tree changed", result.error["message"])
            self.assertFalse((root / "autonomous_agent/candidates/exp-fixture-1/workspace").exists())

    def test_runner_refuses_until_baseline_is_reproduced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            calls: list = []
            adapter = make_adapter(root, counting_factory(calls))
            runner = build_experiment_runner(adapter)
            hypothesis = Hypothesis("data_quality", "question?", "rationale", "experiment", (), 1.0)
            report = PrerequisiteReport(ready=True, reasons=(), champion_id="V1.0.1", hypothesis=hypothesis)
            outcome = runner(hypothesis, report)
            self.assertEqual(outcome["status"], "REJECTED")
            self.assertFalse(outcome["holdout_touched"])
            self.assertEqual(outcome["acceptance_recommendation"], "STOP_AUTONOMOUS_EXPERIMENTATION")
            self.assertEqual(calls, [])
            Supervisor._validate_outcome({"id": "exp"}, outcome)

    def test_runner_refuses_candidate_without_reviewed_spec_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            mark_baseline_reproduced(adapter)
            runner = build_experiment_runner(adapter)
            hypothesis = Hypothesis("data_quality", "question?", "rationale", "experiment", (), 1.0)
            report = PrerequisiteReport(ready=True, reasons=(), champion_id="V1.0.1", hypothesis=hypothesis)
            outcome = runner(hypothesis, report)
            self.assertEqual(outcome["status"], "REJECTED")
            self.assertIn("random code mutations are prohibited", outcome["rejection_reason"])

    def test_result_json_recorded_even_after_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_project(root)
            adapter = make_adapter(root)
            mark_baseline_reproduced(adapter)
            adapter.run_experiment(make_spec(ACCEPTANCE_BODY, change_path="study_files/backend/x.py"))
            record = json.loads((root / "autonomous_agent/candidates/exp-fixture-1/result.json").read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "REJECTED")
            self.assertEqual(record["experiment_id"], "exp-fixture-1")


if __name__ == "__main__":
    unittest.main()
