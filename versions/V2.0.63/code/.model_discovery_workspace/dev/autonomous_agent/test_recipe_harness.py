"""End-to-end tests for the recipe experiment harness (``recipe_harness.run_from_config``).

These tests execute the *exact* command path the autonomous supervisor uses for
the ``experiment`` role -- ``python -m autonomous_agent.experiments.run_experiment``
with cwd = the candidate workspace, the scrubbed environment and the network
guard on ``PYTHONPATH`` (via ``ExperimentAdapter._run_role`` and the reviewed
``_default_command_factory``) -- against a controlled fixture workspace that
carries the real frozen study module, the real frozen protocol file, and a
deterministic sample of the real retained development event table schema.

Everything lives in temporary directories: real project state is never touched,
no holdout data exists or is read, and no experiment attempt is spent. The
``unit_tests`` role is not exercised here; the frozen-study suite is tested
separately (study_files/backend/tests).
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from autonomous_agent import hardening
from autonomous_agent.core import sha256_file
from autonomous_agent.experiment_adapter import (
    EVALUATION_CONTRACT,
    ExperimentAdapter,
)
from autonomous_agent.recipe_harness import (
    decision_criteria_pass,
    validate_experiment_config,
    _load_frozen_study,
)
from autonomous_agent.spec_recipes import (
    EXPERIMENT_ENTRYPOINT,
    INIT_CONTENT,
    RecipeSpecProvider,
)
from autonomous_agent.test_spec_recipes import (
    make_hypothesis,
    make_report,
    prepare_root,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Data and code inputs are explicit staged fixtures, never implicit imports
# from the source checkout. The separate hash manifest records provenance.
FIXTURE_STUDY = PROJECT_ROOT / "study_files/backend/demand_zone_study_v1.py"
FIXTURE_EVENT_TABLE = PROJECT_ROOT / "study_files/outputs/study_v1/development/event_table.csv"
SAMPLE_ROWS_PER_YEAR = 300


def valid_config(**overrides) -> dict:
    config = {
        "schema_version": 1, "generator": "deterministic_recipe",
        "recipe_id": "calibration_stability_check", "recipe_version": "1.0.0",
        "hypothesis_id": "hyp-x", "hypothesis_text": "q", "baseline_id": "b",
        "arm_a": "B", "arm_b": "C",
        "estimator_a": "LightGBM", "estimator_b": "LightGBM",
        "seeds": [42, 43, 44], "n_boot": 500, "calibration_bins": 5,
        "folds": [2023, 2024, 2025],
        "evaluation_criteria": {"primary_metric_min_delta": 0.0,
                                "ci_lower_min": -0.01,
                                "max_brier_degradation": 0.005,
                                "max_ece_degradation": 0.02},
    }
    config.update(overrides)
    return config


class DecisionCriteriaTests(unittest.TestCase):
    """The predeclared gate: calibration margins must gate when declared."""

    CALIBRATION = {"brier_a": 0.200, "brier_b": 0.203,
                   "ece_a": 0.050, "ece_b": 0.060}
    CRITERIA = {"primary_metric_min_delta": 0.0, "ci_lower_min": -0.01,
                "max_brier_degradation": 0.005, "max_ece_degradation": 0.02}

    def test_within_margins_passes(self) -> None:
        passed, detail = decision_criteria_pass(0.01, -0.005, 3,
                                                self.CALIBRATION, self.CRITERIA)
        self.assertTrue(passed)
        self.assertIn("brier_within_margin", detail["checks"])
        self.assertIn("ece_within_margin", detail["checks"])
        self.assertAlmostEqual(detail["brier_delta"], 0.003)
        self.assertAlmostEqual(detail["ece_delta"], 0.010)

    def test_brier_degradation_beyond_margin_fails(self) -> None:
        calibration = {**self.CALIBRATION, "brier_b": 0.220}
        passed, detail = decision_criteria_pass(0.01, -0.005, 3,
                                                calibration, self.CRITERIA)
        self.assertFalse(passed)
        self.assertFalse(detail["checks"]["brier_within_margin"])

    def test_ece_degradation_beyond_margin_fails(self) -> None:
        calibration = {**self.CALIBRATION, "ece_b": 0.100}
        passed, detail = decision_criteria_pass(0.01, -0.005, 3,
                                                calibration, self.CRITERIA)
        self.assertFalse(passed)
        self.assertFalse(detail["checks"]["ece_within_margin"])

    def test_discrimination_gates_still_apply(self) -> None:
        passed, _ = decision_criteria_pass(-0.001, -0.005, 3,
                                           self.CALIBRATION, self.CRITERIA)
        self.assertFalse(passed)  # delta below min_delta
        passed, _ = decision_criteria_pass(0.01, -0.02, 3,
                                           self.CALIBRATION, self.CRITERIA)
        self.assertFalse(passed)  # CI below floor
        passed, _ = decision_criteria_pass(0.01, -0.005, 2,
                                           self.CALIBRATION, self.CRITERIA)
        self.assertFalse(passed)  # too few folds

    def test_undeclared_margins_do_not_gate(self) -> None:
        criteria = {"primary_metric_min_delta": 0.0, "ci_lower_min": -0.01}
        calibration = {**self.CALIBRATION, "brier_b": 0.900, "ece_b": 0.900}
        passed, detail = decision_criteria_pass(0.01, -0.005, 3,
                                                calibration, criteria)
        self.assertTrue(passed)
        self.assertNotIn("brier_within_margin", detail["checks"])
        self.assertNotIn("ece_within_margin", detail["checks"])


class MarginValidationTests(unittest.TestCase):
    def test_valid_margins_are_accepted(self) -> None:
        self.assertEqual(validate_experiment_config(valid_config()), [])

    def test_out_of_range_margin_is_refused(self) -> None:
        for bad in (5, -0.1, True, "0.01"):
            with self.subTest(margin=bad):
                criteria = {"primary_metric_min_delta": 0.0,
                            "max_brier_degradation": bad}
                problems = validate_experiment_config(
                    valid_config(evaluation_criteria=criteria))
                self.assertTrue(any("max_brier_degradation" in p for p in problems))

    def test_unknown_criterion_is_still_refused(self) -> None:
        criteria = {"primary_metric_min_delta": 0.0, "sharpe_ratio": 2.0}
        problems = validate_experiment_config(
            valid_config(evaluation_criteria=criteria))
        self.assertTrue(any("sharpe_ratio" in p for p in problems))


class HarnessEndToEndTests(unittest.TestCase):
    """Run the real harness through the supervisor's real experiment command."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._class_tmp = tempfile.TemporaryDirectory()
        cls.sample_table = Path(cls._class_tmp.name) / "event_table_sample.csv"
        # Controlled fixture: a deterministic per-year sample of the REAL
        # retained development event table (same schema, dtypes and semantics).
        if not FIXTURE_STUDY.is_file() or not FIXTURE_EVENT_TABLE.is_file():
            raise RuntimeError(
                "development fixture missing frozen study/event table; "
                "run .model_discovery_workspace/restore_dev_test_fixtures.py")
        study = _load_frozen_study(PROJECT_ROOT)
        features = sorted({name for arm in study.FEATURE_ARMS.values() for name in arm})
        usecols = ["date", "exit_date", "label"] + features
        frame = pd.read_csv(
            FIXTURE_EVENT_TABLE,
            usecols=usecols)
        years = pd.to_datetime(frame["date"]).dt.year
        parts = [group.sample(n=min(SAMPLE_ROWS_PER_YEAR, len(group)), random_state=42)
                 for _, group in frame.groupby(years)]
        sample = pd.concat(parts)
        if set(sample["label"].astype(int).unique()) != {0, 1}:
            raise AssertionError("fixture sample must contain both label classes")
        sample.to_csv(cls.sample_table, index=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._class_tmp.cleanup()

    # -- fixture workspace --------------------------------------------------
    def _build_workspace(self, root: Path, *, with_event_table: bool = True):
        """Build the workspace and install the provider-generated candidate files."""
        package_dir = PROJECT_ROOT / "autonomous_agent"
        target_pkg = root / "autonomous_agent"
        (target_pkg / "state").mkdir(parents=True, exist_ok=True)
        shutil.copy2(package_dir / "__init__.py", target_pkg / "__init__.py")
        shutil.copy2(package_dir / "recipe_harness.py", target_pkg / "recipe_harness.py")
        study_target = root / "study_files" / "backend"
        study_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FIXTURE_STUDY, study_target / "demand_zone_study_v1.py")
        shutil.copy2(PROJECT_ROOT / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",
                     root / "study_files" / "MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json")
        dev_dir = root / "study_files" / "outputs" / "study_v1" / "development"
        dev_dir.mkdir(parents=True, exist_ok=True)
        if with_event_table:
            shutil.copy2(self.sample_table, dev_dir / "event_table.csv")
        # Generation-side fixtures (evidence, review switch, champion) and the
        # generated candidate files exactly as the reviewed provider emits them.
        prepare_root(root, directions=("calibration",), enabled=True)
        hypothesis = make_hypothesis("calibration")
        provider = RecipeSpecProvider(root, allow_autonomous_specs=True)
        spec, record = provider.propose(hypothesis, make_report(hypothesis))
        assert spec is not None
        self.assertEqual(record["status"], "GENERATED")
        for change in spec.changes():
            target = root / change.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change.content, encoding="utf-8", newline="\n")
        return spec

    def _run_experiment_role(self, root: Path, spec):
        """Execute the supervisor's real ``experiment`` role against the workspace."""
        hardening.install_network_guard(root)
        adapter = ExperimentAdapter(
            root=root,
            candidates_root=root / "autonomous_agent" / "candidates",
            state_root=root / "autonomous_agent" / "state",
        )
        return adapter._run_role(spec, root, "experiment")

    # -- tests --------------------------------------------------------------
    def test_end_to_end_produces_valid_evaluation_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            spec = self._build_workspace(root)
            # The runtime path is the reviewed fixed shim plus the rendered config.
            entry = root / "autonomous_agent/experiments/run_experiment.py"
            self.assertEqual(entry.read_text(encoding="utf-8"), EXPERIMENT_ENTRYPOINT)
            self.assertEqual(
                (root / "autonomous_agent/experiments/__init__.py").read_text(encoding="utf-8"),
                INIT_CONTENT)
            config_path = root / "autonomous_agent/experiments/experiment_config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_experiment_config(config), [])

            run = self._run_experiment_role(root, spec)
            self.assertFalse(run.timed_out)
            self.assertEqual(run.returncode, 0, msg=run.stderr)

            evaluation_path = root / "outputs" / "evaluation.json"
            self.assertTrue(evaluation_path.is_file())
            self.assertEqual(
                [p.name for p in (root / "outputs").iterdir()], ["evaluation.json"])
            evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
            results = evaluation["results"]
            for key in EVALUATION_CONTRACT["results_keys"]:
                self.assertIn(key, results)

            # The decision must be exactly the predeclared criteria -- including
            # the calibration margins -- applied to the reported numbers.
            criteria = config["evaluation_criteria"]
            calibration = results["calibration"]
            folds = evaluation["walk_forward"]["folds"]
            passed, detail = decision_criteria_pass(
                results["primary_metric"]["delta"],
                results["uncertainty_interval"]["lower"],
                len(folds), calibration, criteria)
            self.assertEqual(results["decision_criteria_passed"], passed)
            self.assertIn("brier_within_margin", detail["checks"])
            self.assertIn("ece_within_margin", detail["checks"])
            self.assertEqual(detail["brier_delta"], calibration["brier_delta"])
            self.assertEqual(detail["ece_delta"], calibration["ece_delta"])

            # Walk-forward contract: chronological, purged, three folds.
            self.assertIs(evaluation["walk_forward"]["purge_verified"], True)
            self.assertEqual(len(folds), 3)
            previous_end = ""
            for fold in folds:
                self.assertLess(fold["train_end"], fold["validation_start"])
                self.assertLessEqual(fold["validation_start"], fold["validation_end"])
                self.assertGreaterEqual(fold["validation_start"], previous_end)
                previous_end = fold["validation_end"]

            # Release metadata contract and provenance honesty.
            release = evaluation["release_metadata"]
            for key in EVALUATION_CONTRACT["release_metadata_keys"]:
                self.assertNotIn(release.get(key), (None, "", [], {}), msg=key)
            self.assertEqual(
                release["dataset_sha256"],
                sha256_file(root / "study_files/outputs/study_v1/development/event_table.csv"))
            self.assertTrue(any("NOT a reproduction of V1.0.1" in str(item)
                                for item in release["known_limitations"]))
            self.assertEqual(release["backtest"]["status"], "NOT_RUN")

            # The sealed holdout is never created or touched by a candidate run.
            self.assertFalse(
                (root / "study_files/outputs/study_v1/prospective").exists())

    def test_invalid_config_fails_without_fabricating_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            spec = self._build_workspace(root)
            config_path = root / "autonomous_agent/experiments/experiment_config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["folds"] = [2023]  # outside the reviewed fold contract
            config_path.write_text(json.dumps(config), encoding="utf-8")
            run = self._run_experiment_role(root, spec)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("Recipe experiment config refused", run.stderr)
            self.assertFalse((root / "outputs" / "evaluation.json").exists())

    def test_missing_event_table_fails_without_fabricating_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace"
            root.mkdir()
            spec = self._build_workspace(root, with_event_table=False)
            run = self._run_experiment_role(root, spec)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("Retained development event table is missing", run.stderr)
            self.assertFalse((root / "outputs" / "evaluation.json").exists())


if __name__ == "__main__":
    unittest.main()
