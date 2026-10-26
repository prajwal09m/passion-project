"""Tests for the reconstructed active-baseline track.

All fixtures are synthetic and live in temporary directories. They prove:
baseline establishment with dual-run byte-equality, refusal on discrepancy,
immutability of the historical V1.0.1 FAILED record, champion lineage scoping,
active-baseline gating, leakage and holdout protection, promotion through the
reconstructed V2+ series, crash recovery, resume behavior, and bounded-loop
operation without manual restart. No test fabricates research data or claims
V1.0.1 reproduction.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from autonomous_agent.baseline_registry import (
    PIN_V1_0_1_CODE_SHA256,
    RECONSTRUCTED_STATEMENT,
    BaselineRegistry,
)
from autonomous_agent.core import (
    Hypothesis,
    PrerequisiteReport,
    Supervisor,
    VersionManager,
    bootstrap_champion,
    parse_champion,
    read_json,
    sha256_file,
    utc_now,
    write_json_atomic,
)
from autonomous_agent.experiment_adapter import (
    ExperimentAdapter,
    ExperimentResult,
    ExperimentSpec,
)
from autonomous_agent.test_experiment_adapter import (
    ACCEPTANCE_BODY,
    make_adapter,
    make_project,
    make_spec,
    module_with,
)

BASELINE_ID = "BASELINE_RECONSTRUCTED_2026_10"


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------

def make_establishable_project(root: Path) -> None:
    """A synthetic project whose inputs satisfy verify_inputs() entirely."""
    make_project(root)
    (root / "autonomous_agent/experiments").mkdir(parents=True, exist_ok=True)
    development = root / "study_files/outputs/study_v1/development"
    models = root / "study_files/outputs/study_v1/models"
    development.mkdir(parents=True)
    models.mkdir(parents=True)
    (development / "event_table.csv").write_text("event_id\n1\n", encoding="utf-8")
    (development / "oof_predictions.csv").write_text("event_id\n1\n", encoding="utf-8")
    (models / "LightGBM_A.joblib").write_bytes(b"fixture-model-bytes")

    def _sha(path: Path) -> str:
        return sha256_file(path)

    manifest = {
        "protocol_version": "1.0.1",
        "protocol_sha256": "486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07",
        "code_sha256": PIN_V1_0_1_CODE_SHA256,
        "artifact_sha256": {
            "event_table.csv": _sha(development / "event_table.csv"),
            "oof_predictions.csv": _sha(development / "oof_predictions.csv"),
        },
        "model_artifacts_sha256": {"LightGBM_A.joblib": _sha(models / "LightGBM_A.joblib")},
    }
    (development / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    v2 = root / "study_files/outputs/v2"
    v2.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(f"T{i:03d},2025-01-02" for i in range(149))
    (v2 / "demand_zone_v2_dataset.csv").write_text(f"ticker,date\n{rows}\n", encoding="utf-8")
    cache = v2 / "_ohlcv"
    cache.mkdir(exist_ok=True)
    header = "Date,Open,High,Low,Close,Volume\n2025-01-02,1,1,1,1,100\n"
    for name in [f"S{i:03d}" for i in range(149)] + ["SPY", "QQQ", "IWM", "XVIX"]:
        (cache / f"{name}.csv").write_text(header, encoding="utf-8")

    (root / "study_files/outputs/v5").mkdir(parents=True, exist_ok=True)
    (root / "study_files/outputs/v5/demand_zone_v5_dataset.csv").write_text(
        "ticker,date,x\nAAA,2025-01-02,1\n", encoding="utf-8")
    (root / "study_files/outputs/v13").mkdir(parents=True, exist_ok=True)
    (root / "study_files/outputs/v13/demand_zone_ml_dataset_v13.csv").write_text("x\n", encoding="utf-8")
    (root / "study_files/outputs/hold1").mkdir(parents=True, exist_ok=True)
    (root / "study_files/outputs/hold1/demand_zone_hold1_dataset_v1.csv").write_text("x\n", encoding="utf-8")

    (root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json").write_text(
        json.dumps({"protocol_id": "DZAI-MARKET-STRUCTURE-ABLATION-V1", "protocol_version": "1.0.2"}),
        encoding="utf-8")
    backend = root / "study_files/backend"
    (backend / "tests").mkdir(parents=True, exist_ok=True)
    (backend / "demand_zone_study_v1.py").write_text(
        "\"\"\"Synthetic reconstructed study module fixture.\"\"\"\n", encoding="utf-8")
    (backend / "tests/test_demand_zone_study_v1.py").write_text(
        "\"\"\"Synthetic test suite fixture.\"\"\"\n", encoding="utf-8")


DEVELOP_TEMPLATE = (
    "import hashlib, json, os\n"
    "from pathlib import Path\n"
    "out = Path('study_files/outputs/study_v1_reproduction/development')\n"
    "out.mkdir(parents=True, exist_ok=True)\n"
    "__EXTRA__"
    "(out / 'event_table.csv').write_text('event_id,label\\n1,__SEED__\\n', encoding='utf-8')\n"
    "(out / 'oof_predictions.csv').write_text(__OOF__, encoding='utf-8')\n"
    "model = out / 'LightGBM_A.joblib'\n"
    "model.write_bytes(b'model-__SEED__')\n"
    "def sha(p):\n"
    "    return hashlib.sha256(p.read_bytes()).hexdigest()\n"
    "manifest = {\n"
    "    'protocol_version': '1.0.2', 'protocol_sha256': 'proto', 'universe_sha256': 'universe',\n"
    "    'feature_arms': {'arm_a': ['f1', 'f2']},\n"
    "    'pooled_oof_metrics': {'roc_auc_oof': 0.7},\n"
    "    'artifact_sha256': {'event_table.csv': sha(out / 'event_table.csv'),\n"
    "                        'oof_predictions.csv': sha(out / 'oof_predictions.csv')},\n"
    "    'model_artifacts_sha256': {'LightGBM_A.joblib': sha(model)},\n"
    "    'artifact_directory': os.path.abspath(str(out)),\n"
    "    'data_directory': 'C:\\\\synthetic\\\\__SEED__',\n"
    "    'runtime': {'wall_seconds': '__SEED__'},\n"
    "}\n"
    "(out / 'run_manifest.json').write_text(json.dumps(manifest), encoding='utf-8')\n"
)


def develop_script(seed: str, mode: str) -> str:
    extra = ""
    oof = "'event_id,score\\n1,0.5\\n'"
    if mode == "leak":
        oof = "'event_id,score,forward_return\\n1,0.5,0.01\\n'"
    if mode == "holdout":
        extra = (
            "hold = Path('study_files/outputs/study_v1/prospective')\n"
            "hold.mkdir(parents=True, exist_ok=True)\n"
            "(hold / 'pred.csv').write_text('x\\n1\\n', encoding='utf-8')\n"
        )
    script = (DEVELOP_TEMPLATE
              .replace("__EXTRA__", extra)
              .replace("__OOF__", oof)
              .replace("__SEED__", seed))
    return script


def establish_factory(mode: str = "ok", seed_a: str = "A", seed_b: str = "A"):
    """Command factory for the two establishment runs.

    The seed is chosen per workspace directory, so run 1 and run 2 can be made
    identical (seed_a == seed_b) or deliberately different.
    """
    def factory(workspace: Path) -> dict[str, list[str]]:
        seed = seed_a if "baseline-establish-1" in str(workspace) else seed_b
        return {
            "unit_tests": [sys.executable, "-c", "print('unit ok')"],
            "audit": [sys.executable, "-c", "print('audit ok')"],
            "development": [sys.executable, "-c", develop_script(seed, mode)],
            "experiment": [sys.executable, "-c", "print('experiment ok')"],
        }
    return factory


def make_establish_adapter(root: Path, factory=None) -> ExperimentAdapter:
    return ExperimentAdapter(
        root=root,
        candidates_root=root / "autonomous_agent/candidates",
        state_root=root / "autonomous_agent/state",
        command_factory=factory or establish_factory(),
    )


def reconstructed_champion_dict(version: str = "V2.0.0") -> dict:
    return {
        "version": version,
        "baseline_id": BASELINE_ID,
        "baseline_kind": "reconstructed_baseline",
        "code_revision": "f" * 64,
        "dataset_id": "demand_zone_v2_dataset (restored v1.0.1 roster source)",
        "dataset_sha256": "a" * 64,
        "feature_set": ["arm_a"],
        "model": ["LightGBM_A.joblib"],
        "target_definition": "frozen label; retrospective development only",
        "training_period": "expanding windows before each fold",
        "validation_period": "2023/2024/2025 folds",
        "research_test_period": "NONE: final holdout SEALED",
        "holdout_policy": {"status": "SEALED", "uses": 0, "policy": "sealed"},
        "metrics": {"scope": "retrospective"},
        "backtest": {"scope": "retrospective"},
        "leakage_status": "PASS",
        "validation_status": "SELF_REPRODUCED",
        "validation_scope": f"Self-reproduction of {BASELINE_ID} only. {RECONSTRUCTED_STATEMENT}",
        "known_limitations": [RECONSTRUCTED_STATEMENT],
        "reproduction_command": "py -3 -m autonomous_agent.experiment_adapter establish-baseline",
        "v1_0_1_status": "FAILED",
        "historical_v1_0_1_sha256": PIN_V1_0_1_CODE_SHA256,
        "reconstructed_source_sha256": "f" * 64,
        "self_reproduction": {"byte_identical": True, "runs": 2},
        "pipeline_fingerprint": "e" * 64,
        "lineage": {"relation": "reconstruction", "parent": "V1.0.1",
                    "v1_0_1_status": "FAILED",
                    "historical_v1_0_1_sha256": PIN_V1_0_1_CODE_SHA256},
        "created_at": utc_now(),
    }


def rejected_outcome(baseline_id: str | None = BASELINE_ID) -> dict:
    return {
        "status": "REJECTED",
        "checks": {key: "NOT_RUN" for key in
                   ("unit", "data_integrity", "leakage", "walk_forward", "robustness", "evaluation")},
        "results": {},
        "candidate_path": "autonomous_agent/candidates/x",
        "holdout_touched": False,
        "baseline_id": baseline_id,
    }


# ---------------------------------------------------------------------------
# Baseline establishment
# ---------------------------------------------------------------------------

class BaselineEstablishmentTests(unittest.TestCase):
    def test_establish_baseline_dual_run_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root)
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
            self.assertEqual(record["statement"], RECONSTRUCTED_STATEMENT)
            self.assertEqual(record["lineage"]["v1_0_1_status"], "FAILED")
            self.assertEqual(record["lineage"]["historical_v1_0_1_sha256"], PIN_V1_0_1_CODE_SHA256)
            self.assertEqual(record["lineage"]["relation"], "reconstruction")
            self.assertTrue(record["dual_run"]["byte_identical"])
            self.assertGreaterEqual(record["dual_run"]["artifact_files_compared"], 3)
            self.assertEqual(record["self_reproduction"]["runs"], 2)
            self.assertEqual(record["leakage"]["status"], "PASS")
            self.assertEqual(record["holdout"], {"status": "SEALED", "uses": 0,
                                                 "detail": "final holdout artifacts absent; holdout remains sealed"})
            self.assertTrue(record["pipeline_fingerprint"])
            self.assertEqual(record["inputs"]["ohlcv_count"], 153)
            self.assertIn("event_table.csv", record["outputs"]["artifact_sha256"])
            self.assertIn("LightGBM_A.joblib", record["outputs"]["model_artifacts_sha256"])
            self.assertEqual(record["source"]["sha256"], sha256_file(
                root / "study_files/backend/demand_zone_study_v1.py"))
            self.assertEqual(record["test_suite"]["sha256"], sha256_file(
                root / "study_files/backend/tests/test_demand_zone_study_v1.py"))
            self.assertTrue(record["historical_record_unchanged"])
            self.assertEqual(BaselineRegistry(root / "autonomous_agent/state").ids(), [BASELINE_ID])
            baseline_id, active, reasons = adapter.experiment_baseline()
            self.assertEqual(baseline_id, BASELINE_ID)
            self.assertEqual(active["baseline_id"], BASELINE_ID)
            self.assertEqual(reasons, [])

    def test_establish_refuses_non_identical_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root, establish_factory(seed_a="A", seed_b="B"))
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "FAILED")
            self.assertIn("byte-identical", record["error"])
            self.assertFalse(record["dual_run"]["byte_identical"])
            self.assertTrue(record["workspaces_preserved_for_inspection"])
            self.assertEqual(BaselineRegistry(root / "autonomous_agent/state").ids(), [])

    def test_establish_refuses_leakage_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root, establish_factory(mode="leak", seed_a="A", seed_b="A"))
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "FAILED")
            self.assertIn("leakage", record["error"].lower())
            self.assertEqual(BaselineRegistry(root / "autonomous_agent/state").ids(), [])

    def test_establish_refuses_holdout_touch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root, establish_factory(mode="holdout", seed_a="A", seed_b="A"))
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "FAILED")
            self.assertIn("holdout", record["error"].lower())
            self.assertEqual(BaselineRegistry(root / "autonomous_agent/state").ids(), [])

    def test_historical_v1_0_1_record_stays_failed_and_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            state_root = root / "autonomous_agent/state"
            state_root.mkdir(parents=True, exist_ok=True)
            historical = state_root / "baseline_reproduction.json"
            write_json_atomic(historical, {
                "status": "FAILED",
                "reproduction": {"drift": ["artifact_sha256", "pooled_oof_metrics"]},
                "acceptance_recommendation": "STOP_AUTONOMOUS_EXPERIMENTATION",
            })
            before = historical.read_bytes()
            adapter = make_establish_adapter(root)
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
            self.assertEqual(historical.read_bytes(), before)
            self.assertTrue(record["historical_record_unchanged"])
            self.assertEqual(record["lineage"]["v1_0_1_record_status"], "FAILED")
            self.assertEqual(record["lineage"]["v1_0_1_status"], "FAILED")
            self.assertIn("49", " ".join(record["known_limitations"]))
            self.assertEqual(read_json(historical, {})["status"], "FAILED")

    def test_establish_refuses_duplicate_baseline_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root)
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
            with self.assertRaises(FileExistsError):
                adapter.run_establish_baseline(baseline_id=BASELINE_ID)


# ---------------------------------------------------------------------------
# Active-baseline gating
# ---------------------------------------------------------------------------

class ActiveBaselineGateTests(unittest.TestCase):
    def test_gate_closed_without_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root)
            baseline_id, _active, reasons = adapter.experiment_baseline()
            self.assertIsNone(baseline_id)
            self.assertTrue(any("historical V1.0.1 reproduction status" in reason for reason in reasons))
            result = adapter.run_experiment(make_spec(ACCEPTANCE_BODY))
            self.assertEqual(result.status, "BLOCKED")
            self.assertEqual(result.acceptance_recommendation, "STOP_AUTONOMOUS_EXPERIMENTATION")
            self.assertIsNone(result.baseline_id)
            self.assertFalse((root / "autonomous_agent/candidates/exp-fixture-1/workspace").exists())

    def test_gate_opens_with_established_baseline_and_scopes_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root)
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
            result = adapter.run_experiment(make_spec(ACCEPTANCE_BODY))
            self.assertNotEqual(result.status, "BLOCKED")
            self.assertEqual(result.baseline_id, BASELINE_ID)
            self.assertEqual(result.runtime["baseline_id"], BASELINE_ID)

    def test_spec_with_wrong_baseline_id_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root)
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
            spec = ExperimentSpec(
                experiment_id="exp-fixture-2", parent_version="V2.0.0",
                hypothesis="Scoped hypothesis for the wrong-baseline guard test.",
                proposed_change={"summary": "no-op", "files": [
                    {"path": "autonomous_agent/experiments/x.py", "content": "x = 1\n"}]},
                files_allowed_to_change=("autonomous_agent/experiments",),
                evaluation_protocol={"acceptance_criteria": {}}, random_seed=42,
                resource_limits={}, timeout=60.0, baseline_id="SOME_OTHER_BASELINE")
            result = adapter.run_experiment(spec)
            self.assertEqual(result.status, "BLOCKED")
            self.assertIn("does not match", result.blockers[0])

    def test_stale_pipeline_fingerprint_closes_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root)
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
            (root / "study_files/backend/demand_zone_study_v1.py").write_text(
                "\"\"\"Changed pipeline.\"\"\"\n", encoding="utf-8")
            active, reasons = adapter.active_baseline()
            self.assertIsNone(active)
            self.assertTrue(any("stale" in reason for reason in reasons))


# ---------------------------------------------------------------------------
# Champion lineage and bootstrap
# ---------------------------------------------------------------------------

class ChampionLineageTests(unittest.TestCase):
    def test_reconstructed_champion_parses_when_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CHAMPION.json"
            path.write_text(json.dumps(reconstructed_champion_dict()), encoding="utf-8")
            champion, errors = parse_champion(path)
            self.assertIsNotNone(champion, errors)
            self.assertEqual(champion["baseline_id"], BASELINE_ID)

    def test_champion_rejects_relabel_and_missing_lineage(self) -> None:
        corruptions = {
            "missing lineage": lambda c: c.pop("lineage"),
            "lineage without relation": lambda c: c.update(lineage={"parent": "V1.0.1"}),
            "v1_0_1_status relabeled": lambda c: c.update(v1_0_1_status="REPRODUCED"),
            "historical pin replaced": lambda c: c.update(historical_v1_0_1_sha256="0" * 64),
            "validation_status claims reproduction": lambda c: c.update(validation_status="REPRODUCED"),
            "validation scope silent": lambda c: c.update(validation_scope="self-reproduced baseline"),
            "self reproduction missing": lambda c: c.pop("self_reproduction"),
            "self reproduction not byte identical": lambda c: c.update(
                self_reproduction={"byte_identical": False, "runs": 2}),
            "unknown baseline kind": lambda c: c.update(baseline_kind="mystery"),
            "baseline_id missing": lambda c: c.pop("baseline_id"),
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CHAMPION.json"
            for label, corrupt in corruptions.items():
                with self.subTest(label=label):
                    champion = reconstructed_champion_dict()
                    corrupt(champion)
                    path.write_text(json.dumps(champion), encoding="utf-8")
                    parsed, errors = parse_champion(path)
                    self.assertIsNone(parsed, label)
                    self.assertTrue(errors, label)
            path.unlink()

    def test_historical_reproduction_champion_shape_still_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "CHAMPION.json"
            champion = reconstructed_champion_dict()
            champion.update({
                "baseline_kind": "historical_reproduction",
                "baseline_id": "V1.0.1_REPRODUCED",
                "lineage": {"relation": "reproduction", "parent": "V1.0.1"},
                "validation_status": "REPRODUCED",
                "v1_0_1_status": "REPRODUCED",
            })
            for key in ("validation_scope", "self_reproduction", "pipeline_fingerprint",
                        "historical_v1_0_1_sha256", "reconstructed_source_sha256", "created_at"):
                champion.pop(key, None)
            path.write_text(json.dumps(champion), encoding="utf-8")
            parsed, errors = parse_champion(path)
            self.assertIsNotNone(parsed, errors)

    def test_bootstrap_champion_valid_immutable_and_versioned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root)
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
            champion = bootstrap_champion(root, root / "autonomous_agent/state")
            self.assertEqual(champion["version"], "V2.0.0")
            self.assertEqual(champion["baseline_id"], BASELINE_ID)
            self.assertEqual(champion["baseline_kind"], "reconstructed_baseline")
            self.assertEqual(champion["v1_0_1_status"], "FAILED")
            self.assertEqual(champion["historical_v1_0_1_sha256"], PIN_V1_0_1_CODE_SHA256)
            self.assertEqual(champion["validation_status"], "SELF_REPRODUCED")
            self.assertIn("NOT a reproduction of V1.0.1", champion["validation_scope"])
            self.assertEqual(champion["self_reproduction"]["byte_identical"], True)
            self.assertEqual(champion["pipeline_fingerprint"], record["pipeline_fingerprint"])
            self.assertEqual(champion["reconstructed_source_sha256"], record["source"]["sha256"])
            parsed, errors = parse_champion(root / "CHAMPION.json")
            self.assertIsNotNone(parsed, errors)
            with self.assertRaises(FileExistsError):
                bootstrap_champion(root, root / "autonomous_agent/state")

    def test_bootstrap_refuses_historical_version_series(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_establishable_project(root)
            adapter = make_establish_adapter(root)
            record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
            self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
            with self.assertRaises(ValueError):
                bootstrap_champion(root, root / "autonomous_agent/state", version="V1.0.0")


# ---------------------------------------------------------------------------
# Promotion, crash recovery, resume, bounded loop
# ---------------------------------------------------------------------------

class PromotionTests(unittest.TestCase):
    def _bootstrap(self, root: Path) -> dict:
        make_establishable_project(root)
        adapter = make_establish_adapter(root)
        record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
        self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
        return bootstrap_champion(root, root / "autonomous_agent/state")

    def test_promote_stays_in_reconstructed_series_with_baseline_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            champion = self._bootstrap(root)
            candidate = root / "autonomous_agent/candidates/exp-1"
            candidate.mkdir(parents=True)
            (candidate / "model.py").write_text("model = 'candidate'\n", encoding="utf-8")
            artifact_hash = tree_sha = __import__("autonomous_agent.core", fromlist=["tree_sha256"]).tree_sha256(candidate)
            metadata = {
                "dataset_id": "dataset-v2", "dataset_sha256": "datahash2",
                "feature_set": ["x", "z"], "model": "baseline+z", "target_definition": "target",
                "training_period": "train", "validation_period": "valid",
                "research_test_period": "research", "metrics": {"auc": 0.72},
                "backtest": {"note": "simulation"}, "known_limitations": ["synthetic test"],
                "reproduction_command": "python -m test",
            }
            experiment = {"id": "exp-1", "status": "ACCEPTED", "hypothesis": "h"}
            outcome = {
                "status": "ACCEPTED",
                "checks": {key: "PASS" for key in
                           ("unit", "data_integrity", "leakage", "walk_forward", "robustness", "evaluation")},
                "results": {"primary_metric": 0.72, "uncertainty_interval": [0.7, 0.73],
                            "practical_effect": 0.02, "decision_criteria_passed": True,
                            "calibration": {}, "subgroup_stability": {},
                            "per_seed_metrics": [0.72], "complexity_delta": 1,
                            "runtime_delta": 0.1, "backtest": {}},
                "candidate_path": str(candidate), "reproduction_command": "python -m test",
                "artifact_sha256": artifact_hash, "release_metadata": metadata,
                "holdout_touched": False, "baseline_id": BASELINE_ID,
            }
            released = VersionManager(root).promote(champion, experiment, outcome)
            self.assertEqual(released.name, "V2.0.1")
            new_champion = json.loads((root / "CHAMPION.json").read_text(encoding="utf-8"))
            self.assertEqual(new_champion["version"], "V2.0.1")
            self.assertEqual(new_champion["baseline_id"], BASELINE_ID)
            self.assertEqual(new_champion["validation_status"], "SELF_REPRODUCED")
            self.assertEqual(new_champion["v1_0_1_status"], "FAILED")
            parsed, errors = parse_champion(root / "CHAMPION.json")
            self.assertIsNotNone(parsed, errors)
            version_manifest = json.loads((released / "version.json").read_text(encoding="utf-8"))
            self.assertEqual(version_manifest["baseline_id"], BASELINE_ID)

    def test_promote_refuses_reconstructed_champion_on_v1_ladder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            champion = self._bootstrap(root)
            champion["version"] = "V1.0.9"
            candidate = root / "autonomous_agent/candidates/exp-2"
            candidate.mkdir(parents=True)
            (candidate / "m.py").write_text("m = 1\n", encoding="utf-8")
            tree_sha256 = __import__("autonomous_agent.core", fromlist=["tree_sha256"]).tree_sha256
            metadata = {
                "dataset_id": "d", "dataset_sha256": "h", "feature_set": ["x"], "model": "m",
                "target_definition": "t", "training_period": "tr", "validation_period": "v",
                "research_test_period": "r", "metrics": {"auc": 0.7}, "backtest": {},
                "known_limitations": ["x"], "reproduction_command": "cmd",
            }
            experiment = {"id": "exp-2", "status": "ACCEPTED", "hypothesis": "h"}
            outcome = {
                "status": "ACCEPTED",
                "checks": {key: "PASS" for key in
                           ("unit", "data_integrity", "leakage", "walk_forward", "robustness", "evaluation")},
                "results": {"primary_metric": 0.72, "uncertainty_interval": [0.7, 0.73],
                            "practical_effect": 0.02, "decision_criteria_passed": True,
                            "calibration": {}, "subgroup_stability": {},
                            "per_seed_metrics": [0.72], "complexity_delta": 1,
                            "runtime_delta": 0.1, "backtest": {}},
                "candidate_path": str(candidate), "reproduction_command": "cmd",
                "artifact_sha256": tree_sha256(candidate), "release_metadata": metadata,
                "holdout_touched": False,
            }
            with self.assertRaises(ValueError):
                VersionManager(root).promote(champion, experiment, outcome)


class LoopTests(unittest.TestCase):
    def _ready_root(self, root: Path) -> dict:
        make_establishable_project(root)
        adapter = make_establish_adapter(root)
        record = adapter.run_establish_baseline(baseline_id=BASELINE_ID)
        self.assertEqual(record["status"], "ESTABLISHED", record.get("error"))
        champion = bootstrap_champion(root, root / "autonomous_agent/state")
        (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        (root / "VERSION_HISTORY.md").write_text("# Version History\n", encoding="utf-8")
        return champion

    def test_bounded_loop_runs_continuously_without_manual_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._ready_root(root)
            outcomes = []

            def runner(hypothesis, report):
                outcome = rejected_outcome()
                outcomes.append(outcome)
                return outcome

            supervisor = Supervisor(root=root, state_root=root / "autonomous_agent/state",
                                    idle_seconds=0.1, max_cycles=2, experiment_runner=runner)
            self.assertEqual(supervisor.run(), 0)
            self.assertEqual(len(outcomes), 2)
            state = read_json(root / "autonomous_agent/state/agent_state.json", {})
            self.assertEqual(len(state["experiments"]), 2)
            self.assertEqual(state["active_baseline_id"], BASELINE_ID)
            self.assertTrue(all(exp.get("baseline_id") == BASELINE_ID
                                for exp in state["experiments"]))
            journal = (root / "autonomous_agent/state/events.jsonl").read_text(encoding="utf-8")
            self.assertIn("supervisor_stopped", journal)
            memory = read_json(root / "autonomous_agent/state/research_memory.json", {})
            self.assertGreaterEqual(len(memory["discoveries"]), 2)

    def test_crash_recovery_then_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._ready_root(root)
            state_root = root / "autonomous_agent/state"
            supervisor = Supervisor(root=root, state_root=state_root,
                                    idle_seconds=0.1, max_cycles=1,
                                    experiment_runner=lambda h, r: rejected_outcome())
            state = supervisor.load_state()
            state["experiments"].append({
                "id": "exp-crashed", "created_at": utc_now(), "direction": "validation",
                "hypothesis": "interrupted", "status": "RUNNING", "baseline_id": BASELINE_ID,
                "checks": {}, "outcome_recorded": False,
            })
            supervisor.save_state(state)
            supervisor._recover_interrupted_experiment(state)
            self.assertEqual(state["experiments"][-1]["status"], "FAILED_RECOVERED")
            self.assertEqual(supervisor.run(), 0)
            state = supervisor.load_state()
            statuses = [exp["status"] for exp in state["experiments"]]
            self.assertIn("FAILED_RECOVERED", statuses)
            self.assertGreaterEqual(len(state["experiments"]), 2)
            memory = read_json(state_root / "research_memory.json", {})
            recovered = [item for item in memory["discoveries"]
                         if item.get("experiment_id") == "exp-crashed"]
            self.assertTrue(recovered)


if __name__ == "__main__":
    unittest.main()
