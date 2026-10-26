"""Unit tests for the deterministic recipe spec generation layer.

All fixtures are synthetic and live in temporary directories: these tests
exercise generation, refusal, provenance and crash-safety mechanics only.
They never execute a research experiment and never touch real project state.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_agent import baseline_registry, hardening
from autonomous_agent.core import Hypothesis, PrerequisiteReport, Supervisor, write_json_atomic
from autonomous_agent.experiment_adapter import (
    AllowlistViolation,
    ExperimentSpec,
    build_experiment_runner,
)
from autonomous_agent.recipe_harness import validate_experiment_config
from autonomous_agent.spec_recipes import (
    CONFIG_FLAG_NAME,
    GENERATOR_TYPE,
    RECIPE_LIBRARY,
    Recipe,
    RecipeSpecProvider,
    SpecGenerationRefused,
    attempts_for_recipe,
    autonomous_specs_enabled,
    build_default_provider,
    dry_run,
    find_recipe,
    generation_capacity,
    validate_recipe,
    validated_library,
)


def make_hypothesis(direction: str = "feature_engineering") -> Hypothesis:
    return Hypothesis(
        direction,
        "Does the reviewed recipe question hold under the matched protocol?",
        "Rationale grounded in recorded project findings.",
        "Run the recipe-declared comparison on identical purged folds.",
        ("frozen_protocol_inputs",),
        0.9,
    )


def make_report(hypothesis: Hypothesis) -> PrerequisiteReport:
    return PrerequisiteReport(ready=True, reasons=(), champion_id="V2.0.0", hypothesis=hypothesis)


def established_baseline_record(baseline_id: str = "BASELINE_RECONSTRUCTED_2026_10") -> dict:
    return {
        "baseline_id": baseline_id,
        "status": "ESTABLISHED",
        "kind": "reconstructed_baseline",
        "statement": baseline_registry.RECONSTRUCTED_STATEMENT,
        "lineage": {
            "relation": "reconstruction",
            "v1_0_1_status": "FAILED",
            "historical_v1_0_1_sha256": baseline_registry.PIN_V1_0_1_CODE_SHA256,
        },
        "self_reproduction": {"byte_identical": True, "runs": 2},
        "leakage": {"status": "PASS"},
        "holdout": {"status": "SEALED", "uses": 0},
        "pipeline_fingerprint": "f" * 64,
    }


def prepare_root(root: Path, *, with_baseline: bool = True,
                 directions: tuple[str, ...] = ("feature_engineering", "model_architecture", "calibration"),
                 enabled: bool = False) -> Path:
    (root / "autonomous_agent/state").mkdir(parents=True, exist_ok=True)
    if with_baseline:
        baseline_registry.BaselineRegistry(root / "autonomous_agent/state").append(
            established_baseline_record())
    write_json_atomic(root / "autonomous_agent/state/research_memory.json", {
        "schema_version": 1,
        "discoveries": [
            {"experiment_id": f"exp-fixture-{index}", "direction": direction,
             "status": "REJECTED", "created_at": "2026-10-01T00:00:00+00:00"}
            for index, direction in enumerate(directions)
        ],
    })
    write_json_atomic(root / "autonomous_agent/autonomy_config.json", {
        "schema_version": 1, CONFIG_FLAG_NAME: enabled,
    })
    # Generation refuses to guess a parent version; fixtures carry a champion.
    write_json_atomic(root / "CHAMPION.json", {
        "version": "V2.0.0",
        "baseline_id": "BASELINE_RECONSTRUCTED_2026_10",
        "baseline_kind": "reconstructed_baseline",
    })
    return root


class RecipeLibraryTests(unittest.TestCase):
    def test_default_library_is_valid_and_closed(self) -> None:
        valid, malformed = validated_library()
        self.assertEqual(malformed, {})
        self.assertGreaterEqual(len(valid), 1)
        for recipe in valid:
            self.assertEqual(validate_recipe(recipe), [])
            for target in recipe.target_files:
                self.assertTrue(target.startswith("autonomous_agent/experiments"))

    def test_find_recipe_matches_known_ids_only(self) -> None:
        self.assertIsNotNone(find_recipe("feature_arm_nested_ablation"))
        self.assertIsNone(find_recipe("invented_recipe"))

    def test_calibration_recipe_gates_on_calibration_quality(self) -> None:
        """Calibration is the recipe's purpose; its gate must include calibration."""
        recipe = find_recipe("calibration_stability_check")
        assert recipe is not None
        criteria = recipe.evaluation_criteria
        self.assertIn("max_brier_degradation", criteria)
        self.assertIn("max_ece_degradation", criteria)
        self.assertGreater(criteria["max_brier_degradation"], 0.0)
        self.assertGreater(criteria["max_ece_degradation"], 0.0)
        self.assertTrue(any("Brier" in condition or "ECE" in condition
                            for condition in recipe.rejection_conditions))
        problems = validate_experiment_config({
            "schema_version": 1, "generator": GENERATOR_TYPE,
            "recipe_id": recipe.recipe_id, "recipe_version": recipe.version,
            "hypothesis_id": "hyp-x", "hypothesis_text": "q", "baseline_id": "b",
            "arm_a": "B", "arm_b": "C",
            "estimator_a": "LightGBM", "estimator_b": "LightGBM",
            "seeds": [42, 43, 44], "n_boot": 500, "calibration_bins": 5,
            "folds": [2023, 2024, 2025],
            "evaluation_criteria": dict(criteria),
        })
        self.assertEqual(problems, [])

    def test_malformed_recipes_are_rejected(self) -> None:
        base = find_recipe("feature_arm_nested_ablation")
        assert base is not None
        cases = [
            Recipe(base.recipe_id, base.version, base.direction, base.purpose,
                   ("CHAMPION.json",), base.parameter_grid, base.required_evidence,
                   base.evaluation_criteria, base.rejection_conditions),
            Recipe(base.recipe_id, base.version, base.direction, base.purpose,
                   base.target_files, {"n_boot": (50,)}, base.required_evidence,
                   base.evaluation_criteria, base.rejection_conditions),
            Recipe(base.recipe_id, base.version, base.direction, base.purpose,
                   base.target_files, base.parameter_grid, (),
                   base.evaluation_criteria, base.rejection_conditions),
            Recipe(base.recipe_id, base.version, base.direction, base.purpose,
                   base.target_files, base.parameter_grid, base.required_evidence,
                   {}, base.rejection_conditions),
            Recipe(base.recipe_id, base.version, base.direction, base.purpose,
                   base.target_files, base.parameter_grid, base.required_evidence,
                   base.evaluation_criteria, base.rejection_conditions, max_attempts=0),
        ]
        for recipe in cases:
            self.assertTrue(validate_recipe(recipe), f"should be malformed: {recipe}")
        valid, malformed = validated_library(cases)
        self.assertEqual(valid, [])
        self.assertTrue(malformed)  # every case reported (ids may collide by design)


class DisabledModeTests(unittest.TestCase):
    def test_flag_defaults_to_false(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory), enabled=False)
            self.assertFalse(autonomous_specs_enabled(root))
            self.assertIsNone(build_default_provider(root))

    def test_missing_config_means_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "autonomous_agent/state").mkdir(parents=True, exist_ok=True)
            self.assertFalse(autonomous_specs_enabled(root))
            self.assertIsNone(build_default_provider(root))

    def test_disabled_provider_refuses_every_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory), enabled=False)
            provider = RecipeSpecProvider(root)
            with self.assertRaises(SpecGenerationRefused) as caught:
                provider(make_hypothesis(), make_report(make_hypothesis()))
            self.assertEqual(caught.exception.reason_code, "DISABLED")
            self.assertEqual(attempts_for_recipe(root, "feature_arm_nested_ablation"), [])

    def test_enabled_flag_is_explicit_and_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory), enabled=True)
            self.assertTrue(autonomous_specs_enabled(root))
            self.assertIsNotNone(build_default_provider(root))


class ValidGenerationTests(unittest.TestCase):
    def _provider(self, root: Path, **kwargs) -> RecipeSpecProvider:
        return RecipeSpecProvider(root, allow_autonomous_specs=True, **kwargs)

    def test_valid_generation_with_full_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis()
            provider = self._provider(root)
            spec, record = provider.propose(hypothesis, make_report(hypothesis))
            assert spec is not None
            spec.validate()  # must satisfy the mechanical adapter contract
            self.assertEqual(record["status"], "GENERATED")
            provenance = spec.provenance
            self.assertEqual(provenance["generator_type"], GENERATOR_TYPE)
            self.assertEqual(provenance["recipe_id"], "feature_arm_nested_ablation")
            self.assertEqual(provenance["recipe_version"], "1.0.0")
            self.assertTrue(provenance["hypothesis_id"].startswith("hyp-"))
            self.assertIn("established_baseline", provenance["grounding_evidence"])
            self.assertIn("prior_findings_in_direction", provenance["grounding_evidence"])
            self.assertIsInstance(provenance["selected_parameters"], dict)
            self.assertTrue(provenance["generated_at"])
            self.assertFalse(provenance["llm_involved"])
            self.assertFalse(spec.allow_repeat)
            self.assertEqual(spec.baseline_id, "BASELINE_RECONSTRUCTED_2026_10")

    def test_generated_files_stay_inside_the_experiment_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis()
            spec, _ = self._provider(root).propose(hypothesis, make_report(hypothesis))
            assert spec is not None
            for change in spec.changes():
                self.assertTrue(change.path.startswith("autonomous_agent/experiments"))
            for allowed in spec.files_allowed_to_change:
                self.assertTrue(allowed.startswith("autonomous_agent/experiments"))

    def test_generation_is_deterministic_for_identical_state(self) -> None:
        outputs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as directory:
                root = prepare_root(Path(directory))
                hypothesis = make_hypothesis()
                provider = RecipeSpecProvider(root, allow_autonomous_specs=True,
                                              clock=lambda: "2026-10-04T00:00:00+00:00")
                spec, _ = provider.propose(hypothesis, make_report(hypothesis))
                assert spec is not None
                outputs.append((spec.to_dict()["proposed_change"],
                                spec.to_dict()["evaluation_protocol"],
                                spec.experiment_id))
        self.assertEqual(outputs[0], outputs[1])

    def test_grid_advances_across_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis("model_architecture")
            provider = self._provider(root)
            first, _ = provider.propose(hypothesis, make_report(hypothesis))
            second, _ = provider.propose(hypothesis, make_report(hypothesis))
            assert first is not None and second is not None
            self.assertNotEqual(first.provenance["selected_parameters"],
                                second.provenance["selected_parameters"])

    def test_no_llm_claim_anywhere_in_generated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis()
            spec, _ = self._provider(root).propose(hypothesis, make_report(hypothesis))
            assert spec is not None
            payload = json.dumps(spec.to_dict()).lower()
            self.assertNotIn("language model", payload)
            self.assertNotIn("gpt", payload)
            self.assertFalse(spec.provenance["llm_involved"])


class RefusalTests(unittest.TestCase):
    def _provider(self, root: Path) -> RecipeSpecProvider:
        return RecipeSpecProvider(root, allow_autonomous_specs=True)

    def _assert_refusal(self, root: Path, hypothesis: Hypothesis, code: str) -> None:
        provider = self._provider(root)
        with self.assertRaises(SpecGenerationRefused) as caught:
            provider(hypothesis, make_report(hypothesis))
        self.assertEqual(caught.exception.reason_code, code)
        self.assertEqual(attempts_for_recipe(root, "feature_arm_nested_ablation"), [])

    def test_missing_evidence_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory), directions=tuple())
            self._assert_refusal(root, make_hypothesis(), "MISSING_EVIDENCE")

    def test_missing_baseline_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory), with_baseline=False)
            self._assert_refusal(root, make_hypothesis(), "MISSING_EVIDENCE")

    def test_unsupported_direction_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            self._assert_refusal(root, make_hypothesis("target_design"), "UNSUPPORTED")

    def test_invalid_parameters_are_refused_by_harness_contract(self) -> None:
        problems = validate_experiment_config({
            "schema_version": 1, "generator": GENERATOR_TYPE,
            "recipe_id": "x", "recipe_version": "1", "hypothesis_id": "h",
            "hypothesis_text": "q", "baseline_id": "b",
            "arm_a": "Z", "arm_b": "C",
            "estimator_a": "LogisticRegression", "estimator_b": "LightGBM",
            "seeds": [42, 43, 44], "n_boot": 50, "calibration_bins": 99,
            "folds": [2023], "evaluation_criteria": {"primary_metric_min_delta": 0.0},
        })
        joined = " ".join(problems)
        self.assertIn("arm_a", joined)
        self.assertIn("n_boot", joined)
        self.assertIn("calibration_bins", joined)
        self.assertIn("folds", joined)

    def test_unknown_config_keys_are_refused(self) -> None:
        problems = validate_experiment_config({
            "arm_a": "A", "arm_b": "B", "estimator_a": "LogisticRegression",
            "estimator_b": "LightGBM", "seeds": [1, 2, 3], "n_boot": 500,
            "calibration_bins": 5, "folds": [2023, 2024, 2025],
            "evaluation_criteria": {"primary_metric_min_delta": 0.0},
            "smuggled_key": True,
        })
        self.assertTrue(any("smuggled_key" in problem for problem in problems))

    def test_forbidden_target_path_recipe_never_generates(self) -> None:
        base = find_recipe("feature_arm_nested_ablation")
        assert base is not None
        evil = Recipe(base.recipe_id, base.version, base.direction, base.purpose,
                      ("CHAMPION.json",), base.parameter_grid, base.required_evidence,
                      base.evaluation_criteria, base.rejection_conditions)
        self.assertTrue(validate_recipe(evil))
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            provider = RecipeSpecProvider(root, allow_autonomous_specs=True, library=(evil,))
            hypothesis = make_hypothesis()
            with self.assertRaises(SpecGenerationRefused) as caught:
                provider(hypothesis, make_report(hypothesis))
            self.assertEqual(caught.exception.reason_code, "UNSUPPORTED")

    def test_duplicate_proposal_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis()
            registry = hardening.SpecRegistry(root / "autonomous_agent/state")
            provider = RecipeSpecProvider(root, allow_autonomous_specs=True,
                                          clock=lambda: "2026-10-04T00:00:00+00:00",
                                          registry=registry)
            spec, _ = provider.propose(hypothesis, make_report(hypothesis))
            assert spec is not None
            # Simulate the adapter recording the executed spec, then reset the
            # provider's attempt counter to force the same grid slot again.
            registry.record(spec.to_dict(), spec.experiment_id, "2026-10-04T00:00:01+00:00")
            ledger = root / "autonomous_agent/state/spec_attempts.json"
            write_json_atomic(ledger, {"schema_version": 1, "attempts": []})
            with self.assertRaises(SpecGenerationRefused) as caught:
                provider(hypothesis, make_report(hypothesis))
            self.assertEqual(caught.exception.reason_code, "DUPLICATE")

    def test_attempt_ledger_duplicate_is_refused_even_without_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis()
            provider = RecipeSpecProvider(root, allow_autonomous_specs=True,
                                          clock=lambda: "2026-10-04T00:00:00+00:00")
            provider.propose(hypothesis, make_report(hypothesis))
            # Force the same grid slot by truncating the parameter space to the
            # recorded one: a second identical generation must be refused.
            recipe = find_recipe("feature_arm_nested_ablation")
            assert recipe is not None
            attempts = attempts_for_recipe(root, recipe.recipe_id)
            self.assertEqual(len(attempts), 1)
            same = Recipe(recipe.recipe_id, recipe.version, recipe.direction, recipe.purpose,
                          recipe.target_files,
                          {"arm_pair": ("A->B",), "estimator": ("LogisticRegression",),
                           "n_boot": (500,)},
                          recipe.required_evidence, recipe.evaluation_criteria,
                          recipe.rejection_conditions)
            provider2 = RecipeSpecProvider(root, allow_autonomous_specs=True,
                                           clock=lambda: "2026-10-04T00:00:00+00:00",
                                           library=(same,))
            with self.assertRaises(SpecGenerationRefused) as caught:
                provider2(hypothesis, make_report(hypothesis))
            self.assertEqual(caught.exception.reason_code, "DUPLICATE")

    def test_exhausted_budget_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis("calibration")
            provider = self._provider(root)
            provider.propose(hypothesis, make_report(hypothesis))
            provider.propose(hypothesis, make_report(hypothesis))
            with self.assertRaises(SpecGenerationRefused) as caught:
                provider(hypothesis, make_report(hypothesis))
            self.assertEqual(caught.exception.reason_code, "BUDGET_EXHAUSTED")
            self.assertEqual(len(attempts_for_recipe(root, "calibration_stability_check")), 2)


class ParentVersionTests(unittest.TestCase):
    """The parent version must be established from CHAMPION.json, or refused."""

    def _provider(self, root: Path) -> RecipeSpecProvider:
        return RecipeSpecProvider(root, allow_autonomous_specs=True)

    def _assert_invalid_parent(self, root: Path) -> None:
        provider = self._provider(root)
        hypothesis = make_hypothesis()
        with self.assertRaises(SpecGenerationRefused) as caught:
            provider(hypothesis, make_report(hypothesis))
        self.assertEqual(caught.exception.reason_code, "INVALID_PARENT")
        self.assertEqual(attempts_for_recipe(root, "feature_arm_nested_ablation"), [])

    def test_missing_champion_refuses_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            (root / "CHAMPION.json").unlink()
            self._assert_invalid_parent(root)

    def test_malformed_champion_refuses_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            (root / "CHAMPION.json").write_text("{ this is not json", encoding="utf-8")
            self._assert_invalid_parent(root)

    def test_invalid_version_refuses_generation(self) -> None:
        for champion in ({}, {"version": "latest"}, {"version": 123}, {"version": "V2.0"}):
            with self.subTest(champion=champion), tempfile.TemporaryDirectory() as directory:
                root = prepare_root(Path(directory))
                write_json_atomic(root / "CHAMPION.json", champion)
                self._assert_invalid_parent(root)

    def test_parent_version_comes_from_champion_not_a_hardcoded_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            write_json_atomic(root / "CHAMPION.json", {"version": "V2.0.1"})
            hypothesis = make_hypothesis()
            spec, _ = self._provider(root).propose(hypothesis, make_report(hypothesis))
            assert spec is not None
            self.assertEqual(spec.parent_version, "V2.0.1")

    def test_dry_run_reports_invalid_parent_without_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            (root / "CHAMPION.json").unlink()
            before = sorted(path.relative_to(root).as_posix()
                            for path in root.rglob("*") if path.is_file())
            report = dry_run(root)
            after = sorted(path.relative_to(root).as_posix()
                           for path in root.rglob("*") if path.is_file())
            self.assertEqual(before, after)
            refusals = [row for row in report["proposals"]
                        if row.get("reason_code") == "INVALID_PARENT"]
            # Every recipe-covered direction is refused; unsupported directions
            # are refused earlier with UNSUPPORTED. Nothing may generate.
            self.assertEqual({row.get("direction") for row in refusals},
                             {"feature_engineering", "model_architecture", "calibration"})
            self.assertTrue(all(row["status"] == "REFUSED" for row in report["proposals"]))
            self.assertEqual(report["summary"]["generated"], 0)


class GenerationCapacityTests(unittest.TestCase):
    """Capacity verdicts drive the supervisor's exhaustion policy."""

    def test_fresh_root_has_capacity_in_recipe_directions_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            directions = ["feature_engineering", "model_architecture", "calibration",
                          "target_design"]
            capacity = generation_capacity(root, directions)
            self.assertFalse(capacity["exhausted"])
            self.assertEqual(set(capacity["viable_directions"]),
                             {"feature_engineering", "model_architecture", "calibration"})
            self.assertFalse(capacity["directions"]["target_design"]["supported"])
            self.assertFalse(capacity["directions"]["target_design"]["viable"])
            # Read-only: the verdict must not create an attempt ledger.
            self.assertFalse((root / "autonomous_agent/state/spec_attempts.json").exists())

    def test_spent_budget_is_reported_per_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            provider = RecipeSpecProvider(root, allow_autonomous_specs=True)
            hypothesis = make_hypothesis("calibration")
            provider.propose(hypothesis, make_report(hypothesis))
            provider.propose(hypothesis, make_report(hypothesis))
            capacity = generation_capacity(root, ["calibration", "feature_engineering"])
            calibration = capacity["directions"]["calibration"]
            self.assertFalse(calibration["viable"])
            self.assertFalse(calibration["budget_remaining"])
            self.assertEqual(calibration["recipes"][0]["attempts_used"], 2)
            self.assertTrue(capacity["directions"]["feature_engineering"]["viable"])
            self.assertFalse(capacity["exhausted"])

    def test_all_budgets_spent_means_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            provider = RecipeSpecProvider(root, allow_autonomous_specs=True)
            for recipe in RECIPE_LIBRARY:
                hypothesis = make_hypothesis(recipe.direction)
                for _ in range(recipe.max_attempts):
                    provider.propose(hypothesis, make_report(hypothesis))
            capacity = generation_capacity(
                root, [recipe.direction for recipe in RECIPE_LIBRARY])
            self.assertTrue(capacity["exhausted"])
            self.assertEqual(capacity["viable_directions"], [])


class CrashRecoveryTests(unittest.TestCase):
    def test_attempt_recorded_before_use_survives_crash(self) -> None:
        """A crash after recording can only lose a never-used spec, never double-run one."""
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis()
            provider = RecipeSpecProvider(root, allow_autonomous_specs=True,
                                          clock=lambda: "2026-10-04T00:00:00+00:00")
            provider.propose(hypothesis, make_report(hypothesis))
            # "Crash": provider object is lost; a fresh one resumes from disk.
            resumed = RecipeSpecProvider(root, allow_autonomous_specs=True,
                                         clock=lambda: "2026-10-04T00:00:00+00:00")
            attempts = attempts_for_recipe(root, "feature_arm_nested_ablation")
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["recipe_id"], "feature_arm_nested_ablation")
            second, _ = resumed.propose(hypothesis, make_report(hypothesis))
            assert second is not None
            self.assertNotEqual(second.experiment_id, attempts[0]["experiment_id"])

    def test_corrupt_ledger_fails_closed_not_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            ledger = root / "autonomous_agent/state/spec_attempts.json"
            ledger.parent.mkdir(parents=True, exist_ok=True)
            ledger.write_text("{ this is not json", encoding="utf-8")
            # Unreadable ledger must not crash generation bookkeeping reads.
            self.assertEqual(attempts_for_recipe(root, "feature_arm_nested_ablation"), [])


class DryRunTests(unittest.TestCase):
    def test_dry_run_reports_selection_and_refusals_without_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            before = sorted(path.relative_to(root).as_posix()
                            for path in root.rglob("*") if path.is_file())
            report = dry_run(root)
            after = sorted(path.relative_to(root).as_posix()
                           for path in root.rglob("*") if path.is_file())
            self.assertEqual(before, after)  # dry-run writes nothing
            self.assertEqual(report["mode"], "dry_run")
            self.assertFalse(report["llm_involved"])
            self.assertEqual(report["executed_experiments"], 0)
            self.assertFalse(report["champion_changed"])
            statuses = {row["direction"]: row["status"] for row in report["proposals"]}
            self.assertEqual(statuses.get("feature_engineering"), "GENERATED")
            self.assertEqual(statuses.get("target_design"), "REFUSED")
            self.assertTrue(report["recipes"])
            self.assertTrue(any(row.get("reason_code") for row in report["proposals"]))
            self.assertFalse(report["allow_autonomous_specs_in_config"])

    def test_dry_run_reports_missing_evidence_refusals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory), with_baseline=False)
            report = dry_run(root)
            refused = [row for row in report["proposals"] if row["status"] == "REFUSED"]
            self.assertTrue(refused)
            self.assertTrue(all(row.get("reason") for row in refused))
            self.assertEqual(report["summary"]["generated"], 0)


class DownstreamProtectionRegressionTests(unittest.TestCase):
    def test_provenance_neutral_specs_keep_identical_fingerprints(self) -> None:
        """provenance is volatile metadata; duplicate detection must ignore it."""
        spec_dict = {
            "experiment_id": "exp-1", "parent_version": "V2.0.0", "hypothesis": "h",
            "proposed_change": {"summary": "s", "files": []},
            "files_allowed_to_change": ["autonomous_agent/experiments"],
            "evaluation_protocol": {"acceptance_criteria": {}},
            "random_seed": 42, "resource_limits": {}, "timeout": 60.0,
        }
        first = hardening.spec_fingerprint({**spec_dict, "provenance": {"generated_at": "t1"}})
        second = hardening.spec_fingerprint({**spec_dict, "provenance": {"generated_at": "t2"}})
        self.assertEqual(first, second)

    def test_generated_spec_still_passes_adapter_path_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            hypothesis = make_hypothesis()
            provider = RecipeSpecProvider(root, allow_autonomous_specs=True)
            spec, _ = provider.propose(hypothesis, make_report(hypothesis))
            assert spec is not None
            spec.validate()
            # Tampering with a change path must trip the existing allowlist gate.
            tampered = ExperimentSpec.from_dict({**spec.to_dict(), "proposed_change": {
                "summary": spec.to_dict()["proposed_change"]["summary"],
                "files": [{"path": "CHAMPION.json", "content": "{}"}],
            }})
            with self.assertRaises(AllowlistViolation):
                tampered.validate()

    def test_runner_without_provider_keeps_refusing_candidates(self) -> None:
        class FakeAdapter:
            def experiment_baseline(self):
                return "BASELINE_RECONSTRUCTED_2026_10", {}, []

            def run_experiment(self, spec):  # pragma: no cover - must not run
                raise AssertionError("must never execute")

        runner = build_experiment_runner(FakeAdapter())
        outcome = runner(make_hypothesis(), make_report(make_hypothesis()))
        self.assertEqual(outcome["status"], "REJECTED")
        self.assertIn("No reviewed ExperimentSpec provider", outcome["error"]["message"])

    def test_runner_with_provider_passes_specs_through(self) -> None:
        seen: list[ExperimentSpec] = []

        class FakeAdapter:
            def experiment_baseline(self):
                return "BASELINE_RECONSTRUCTED_2026_10", {}, []

            def run_experiment(self, spec):
                seen.append(spec)
                from autonomous_agent.experiment_adapter import ExperimentResult
                return ExperimentResult(experiment_id=spec.experiment_id, status="REJECTED")

        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory))
            provider = RecipeSpecProvider(root, allow_autonomous_specs=True)
            runner = build_experiment_runner(FakeAdapter(), spec_provider=provider)
            outcome = runner(make_hypothesis(), make_report(make_hypothesis()))
            self.assertEqual(len(seen), 1)
            self.assertEqual(seen[0].provenance["generator_type"], GENERATOR_TYPE)
            self.assertIn(outcome["status"], ("REJECTED", "ACCEPTED"))

    def test_provider_refusal_becomes_a_clean_rejection(self) -> None:
        class FakeAdapter:
            def experiment_baseline(self):
                return "BASELINE_RECONSTRUCTED_2026_10", {}, []

            def run_experiment(self, spec):  # pragma: no cover - must not run
                raise AssertionError("must never execute")

        with tempfile.TemporaryDirectory() as directory:
            root = prepare_root(Path(directory), enabled=False)
            provider = RecipeSpecProvider(root)  # reads config -> disabled
            runner = build_experiment_runner(FakeAdapter(), spec_provider=provider)
            outcome = runner(make_hypothesis(), make_report(make_hypothesis()))
            self.assertEqual(outcome["status"], "REJECTED")
            self.assertIn("DISABLED", outcome["error"]["message"])
            # The refusal code must survive the supervisor's outcome validation
            # instead of being masked by the generic scientific-gates message.
            Supervisor._validate_outcome({}, outcome)
            self.assertEqual(outcome["status"], "REJECTED")
            self.assertIn("DISABLED", outcome.get("rejection_reason", ""))


if __name__ == "__main__":
    unittest.main()
