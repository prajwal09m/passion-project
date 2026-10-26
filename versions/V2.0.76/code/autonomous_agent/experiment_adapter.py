"""Reviewed experiment adapter: the only bridge between the autonomous research
supervisor and the stock-research pipeline.

Design contract (see autonomous_agent/INPUT_REQUIREMENTS.md):

* No stock-model source file is ever modified. Every experiment executes in a
  temporary repository copy under ``autonomous_agent/candidates/<id>/workspace``.
  The original tree is hash-fingerprinted before and after each experiment; any
  drift rejects the experiment and destroys the candidate.
* Only a fixed, reviewed command registry is ever executed -- never a command
  chosen by an experiment spec or by repository content.
* Candidate changes are confined to the narrow allowlist
  ``autonomous_agent/experiments/**``. Paths outside it (stock-model source,
  protocol, archives, memory/history ledgers, sealed holdout, credentials,
  application files) are refused before anything runs.
* Any anomaly -- missing inputs, allowlist violation, holdout access, leakage
  tokens in outputs, input drift, failed gate, timeout, or unexpected error --
  rejects the experiment and destroys the candidate workspace. The supervisor
  result stays well-formed so the loop survives.
* No network access, no brokerage integration, no model deserialization.

Pipeline contract for candidate experiments (Phase 6/8): a candidate adds
``autonomous_agent/experiments/run_experiment.py`` (plus helpers/config) inside
the allowlist. The adapter executes exactly::

    python -m autonomous_agent.experiments.run_experiment

in the isolated workspace. That module must write ``outputs/evaluation.json``
with the documented evidence structure (see ``EVALUATION_CONTRACT``). Random
code mutations are prohibited: every candidate carries a written hypothesis and
an explicit list of changed files (``ExperimentSpec``).
"""
from __future__ import annotations

import argparse
import csv
import fnmatch

try:
    from autonomous_agent import baseline_registry, hardening
except ImportError:  # direct module execution inside autonomous_agent/
    import baseline_registry  # type: ignore
    import hardening  # type: ignore
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping

from autonomous_agent.core import (
    Hypothesis,
    PrerequisiteReport,
    PROJECT_ROOT,
    append_jsonl,
    read_json,
    sha256_file,
    tree_sha256,
    utc_now,
    write_json_atomic,
)

AGENT_ADAPTER_VERSION = "0.2.0"

CANDIDATES_ROOT = PROJECT_ROOT / "autonomous_agent" / "candidates"
STATE_ROOT = PROJECT_ROOT / "autonomous_agent" / "state"
BASELINE_STATE_NAME = "baseline_reproduction.json"
BASELINE_REPORT_MD = PROJECT_ROOT / "autonomous_agent" / "BASELINE_REPRODUCTION_REPORT.md"
JOURNAL_NAME = "adapter_events.jsonl"

# --- Phase 7 allowlist: narrow on purpose. Expand only after the adapter is
# proven reliable, and only with an explicit review of the new surface.
ALLOWED_CHANGE_PREFIXES = ("autonomous_agent/experiments",)

FORBIDDEN_CHANGE_PREFIXES = (
    "study_files/backend",                      # stock-model study source
    "study_files/Python",                       # legacy stock-model source
    "Python",                                   # legacy stock-model source
    "study_files/outputs/study_v1",             # immutable v1.0.1 archive
    "study_files/outputs/study_v1/prospective", # sealed final holdout
    "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",  # frozen protocol
    "study_files/backend/tests",                # historical test suite
    "application_files",                        # app/brokerage-adjacent files
    "versions", "CHAMPION.json",
    "VERSION_HISTORY.md", "RESEARCH_MEMORY.md", "EVOLUTION_HISTORY.md",
    "CHANGELOG.md", ".git",
)

# Tokens documented in RESEARCH_MEMORY.md as outcome-derived / leakage threats.
LEAKAGE_TOKENS = ("mfe_pct", "mae_pct", "forward_return")

# Expected identity pins recovered from the sanitized v1.0.1 manifest. These
# are verification targets, never something to fabricate data around.
PIN_PROTOCOL_SHA256_V1_0_1 = "486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07"
PIN_CODE_SHA256_V1_0_1 = "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b"
PIN_ROSTER_SHA256_V1_0_1 = "669ca1f5b21339b8cc26f6eb5cbeb22003ebafcd86b0d7e945f0db3d6517d71b"

# --- Reconstructed active-baseline track -----------------------------------
# Fully separated from the historical V1.0.1 reproduction track above. The
# historical record (baseline_reproduction.json) stays FAILED/BLOCKED and is
# never written by this track. A reconstructed baseline is explicitly NOT a
# reproduction of V1.0.1.
RECONSTRUCTED_STATEMENT = baseline_registry.RECONSTRUCTED_STATEMENT
DEFAULT_ESTABLISHED_BASELINE_ID = "BASELINE_RECONSTRUCTED_2026_10"
HISTORICAL_V1_0_1_STATUS = baseline_registry.HISTORICAL_V1_0_1_STATUS
# run_manifest keys allowed to differ between two clean establishment runs
# (absolute output paths and timing metadata). Every other key -- and every
# artifact file byte -- must be identical.
MANIFEST_VOLATILE_KEYS = ("artifact_directory", "data_directory", "runtime")

# Workspace copy exclusions: large local-only artifacts and agent runtime state.
COPY_IGNORE_PATTERNS = (
    ".git", "__pycache__", ".freebuff", "state", "candidates", "versions",
    "test-state", ".restoration_tmp", "node_modules", "*.pyc", "*.zip", "*.db",
)

DEFAULT_RESOURCE_LIMITS: dict[str, Any] = {
    "timeout_seconds": 3600.0,
    "max_output_bytes": 2_000_000,
    "max_workspace_files": 250_000,
    "max_workspace_bytes": 3_000_000_000,
}
REPRODUCTION_TIMEOUT_SECONDS = 14_400.0

EVALUATION_CONTRACT = {
    "output_file": "outputs/evaluation.json",
    "results_keys": (
        "primary_metric", "uncertainty_interval", "practical_effect",
        "decision_criteria_passed", "calibration", "subgroup_stability",
        "per_seed_metrics", "complexity_delta", "runtime_delta", "backtest",
    ),
    "walk_forward": ">=3 chronological folds with train_end < validation_start "
                    "and purge_verified: true",
    "release_metadata_keys": (
        "dataset_id", "dataset_sha256", "feature_set", "model",
        "target_definition", "training_period", "validation_period",
        "research_test_period", "metrics", "backtest", "known_limitations",
        "reproduction_command",
    ),
}


class AdapterError(Exception):
    """Base class for adapter-level failures."""


class AllowlistViolation(AdapterError):
    """A requested change targets a path outside the experimentable surface."""


class Anomaly(AdapterError):
    """Any condition that must reject the candidate and destroy its workspace."""


# ---------------------------------------------------------------------------
# Phase 1: machine-checkable input requirements (see INPUT_REQUIREMENTS.md)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InputRequirement:
    key: str
    title: str
    expected_locations: tuple[str, ...]
    why: str
    depends_on: str
    affects_reproducibility: bool
    required_for_reproduction: bool
    verify: str


REQUIRED_INPUTS: tuple[InputRequirement, ...] = (
    InputRequirement(
        key="v1_run_manifest",
        title="v1.0.1 run manifest",
        expected_locations=("study_files/outputs/study_v1/development/run_manifest.json",),
        why="Integrity manifest of the immutable v1.0.1 archive; the study test "
            "suite verifies artifact and model hashes against it.",
        depends_on="v1.0.1 archive verification; baseline reproduction comparison",
        affects_reproducibility=True,
        required_for_reproduction=True,
        verify="Parses as JSON; protocol_version=='1.0.1'; pinned protocol/code "
               "sha256; every artifact_sha256 and model_artifacts_sha256 matches.",
    ),
    InputRequirement(
        key="v2_roster_dataset",
        title="V2 row-level dataset (roster source)",
        expected_locations=("study_files/outputs/v2/demand_zone_v2_dataset.csv",),
        why="ROSTER_SOURCE for the frozen study: load_roster() requires exactly "
            "149 distinct tickers; universe hash and prospective lock depend on it.",
        depends_on="v1.0.2 frozen protocol; v1.0.1 manifest roster_source_sha256",
        affects_reproducibility=True,
        required_for_reproduction=True,
        verify="File exists; 'ticker' column yields exactly 149 distinct values; "
               "sha256 matches the v1.0.1 pin for exact parity.",
    ),
    InputRequirement(
        key="ohlcv_cache",
        title="Historical OHLCV cache (153 CSVs)",
        expected_locations=("study_files/outputs/v2/_ohlcv/",),
        why="Event construction, market features, and source hashes all read this "
            "cache; VIX is stored as XVIX.csv (^ -> X filename mapping).",
        depends_on="v1.0.2 protocol data section; v1.0.1 source_data_sha256",
        affects_reproducibility=True,
        required_for_reproduction=True,
        verify="Directory with >=153 CSVs including SPY/QQQ/IWM/XVIX and valid "
               "OHLCV headers; hashes match run_manifest.json when restored.",
    ),
    InputRequirement(
        key="v1_0_1_source",
        title="Original v1.0.1 study source",
        expected_locations=("study_files/research/demand-zone-ai-study/recovered_source/",),
        why="Feature parity FAILED in the reconstruction (rsi14, atr_pct, "
            "zone_width_pct); archived metrics are not attributable without it.",
        depends_on="v1.0.1 exact reproduction; champion REPRODUCED status",
        affects_reproducibility=True,
        required_for_reproduction=False,
        verify="Some file in the drop zone hashes to the manifest code_sha256 pin.",
    ),
    InputRequirement(
        key="feature_parity",
        title="v1.0.1 preprocessing / feature-parity evidence",
        expected_locations=("study_files/research/demand-zone-ai-study/recovered_source/",),
        why="Parity failure is a feature-definition mismatch; v1.0.1 attribution "
            "requires the original definitions (v1.0.2 fits transforms fold-locally).",
        depends_on="v1.0.1 exact reproduction",
        affects_reproducibility=True,
        required_for_reproduction=False,
        verify="AAL parity comparison against the archived event table passes for "
               "rsi14/atr_pct/zone_width_pct after v1_0_1_source is restored.",
    ),
    InputRequirement(
        key="v5_dataset",
        title="V5 row-level dataset",
        expected_locations=("study_files/outputs/v5/demand_zone_v5_dataset.csv",),
        why="Row-level dataset for the V5-V10 lineage (train_v5.py/train_v7.py).",
        depends_on="V5-V10 historical lineage",
        affects_reproducibility=True,
        required_for_reproduction=False,
        verify="File exists, non-empty, header includes ticker/date columns.",
    ),
    InputRequirement(
        key="v13_dataset",
        title="V13 dataset (lineage to rebuild V2)",
        expected_locations=("study_files/outputs/v13/demand_zone_ml_dataset_v13.csv",),
        why="Input of build_hold1_targets.py; only needed when rebuilding V2 from "
            "scratch (network rebuild is prohibited; restore V2 directly instead).",
        depends_on="V2 rebuild lineage",
        affects_reproducibility=False,
        required_for_reproduction=False,
        verify="File exists.",
    ),
    InputRequirement(
        key="hold1_dataset",
        title="hold1 dataset (lineage to rebuild V2)",
        expected_locations=("study_files/outputs/hold1/demand_zone_hold1_dataset_v1.csv",),
        why="Input of build_v2_dataset.py (184 v13 features); only needed when "
            "rebuilding V2 from scratch.",
        depends_on="V2 rebuild lineage",
        affects_reproducibility=False,
        required_for_reproduction=False,
        verify="File exists.",
    ),
)


def _check_v1_run_manifest(root: Path) -> tuple[bool, str, dict[str, bool]]:
    path = root / "study_files/outputs/study_v1/development/run_manifest.json"
    if not path.is_file():
        return False, f"missing: {path.relative_to(root).as_posix()}", {"exists": False}
    manifest = read_json(path, None)
    if not isinstance(manifest, dict):
        return False, "manifest exists but is not a JSON object", {"exists": True, "parses": False}
    checks: dict[str, bool] = {"exists": True, "parses": True}
    checks["protocol_version_1.0.1"] = manifest.get("protocol_version") == "1.0.1"
    checks["protocol_sha256_pin"] = manifest.get("protocol_sha256") == PIN_PROTOCOL_SHA256_V1_0_1
    checks["code_sha256_pin"] = manifest.get("code_sha256") == PIN_CODE_SHA256_V1_0_1
    # Informational only: the v1.0.1 manifest pinned the protocol as it existed
    # then; the current frozen protocol file is v1.0.2 and legitimately differs.
    protocol_path = root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"
    checks["info_protocol_file_hash"] = (
        protocol_path.is_file() and sha256_file(protocol_path) == manifest.get("protocol_sha256")
    )
    for name, expected in (manifest.get("artifact_sha256") or {}).items():
        target = path.parent / name
        checks[f"artifact:{name}"] = target.is_file() and sha256_file(target) == expected
    for name, expected in (manifest.get("model_artifacts_sha256") or {}).items():
        target = root / "study_files/outputs/study_v1/models" / name
        checks[f"model:{name}"] = target.is_file() and sha256_file(target) == expected
    required_checks = {name: passed for name, passed in checks.items() if not name.startswith("info_")}
    ok = bool(required_checks) and all(required_checks.values()) and len(required_checks) > 3
    failed = [name for name, passed in required_checks.items() if not passed]
    detail = "all pinned hashes and artifact hashes verified" if ok else f"failed checks: {failed}"
    return ok, detail, checks


def _check_v2_roster(root: Path) -> tuple[bool, str, dict[str, bool]]:
    path = root / "study_files/outputs/v2/demand_zone_v2_dataset.csv"
    if not path.is_file():
        return False, f"missing: {path.relative_to(root).as_posix()}", {"exists": False}
    checks: dict[str, bool] = {"exists": True}
    try:
        tickers: set[str] = set()
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or "ticker" not in reader.fieldnames:
                return False, "file has no 'ticker' column", {**checks, "ticker_column": False}
            for row in reader:
                value = (row.get("ticker") or "").strip()
                if value:
                    tickers.add(value)
        checks["ticker_column"] = True
        checks["distinct_tickers_149"] = len(tickers) == 149
        checks["info_sha256_pin"] = sha256_file(path) == PIN_ROSTER_SHA256_V1_0_1
        ok = checks["distinct_tickers_149"]
        detail = (f"{len(tickers)} distinct tickers; sha256 pin "
                  f"{'matches' if checks['info_sha256_pin'] else 'does not match (exact v1.0.1 parity)'}")
        return ok, detail, checks
    except OSError as error:
        return False, f"unreadable: {error}", {**checks, "readable": False}


def _check_ohlcv_cache(root: Path) -> tuple[bool, str, dict[str, bool]]:
    directory = root / "study_files/outputs/v2/_ohlcv"
    if not directory.is_dir():
        return False, f"missing directory: {directory.relative_to(root).as_posix()}", {"exists": False}
    csvs = sorted(directory.glob("*.csv"))
    checks: dict[str, bool] = {"exists": True, "file_count_ge_153": len(csvs) >= 153}
    required = ("SPY.csv", "QQQ.csv", "IWM.csv", "XVIX.csv")
    needed = {"date", "open", "high", "low", "close", "volume"}
    for name in required:
        path = directory / name
        present = path.is_file()
        checks[f"benchmark:{name}"] = present
        if present:
            with path.open("r", encoding="utf-8", newline="") as stream:
                header = {(cell or "").strip().lower() for cell in next(csv.reader(stream), [])}
            checks[f"columns:{name}"] = needed.issubset(header)
    ok = all(checks.values())
    return ok, f"{len(csvs)} CSV files; required benchmarks {'verified' if ok else 'incomplete'}", checks


def _check_plain_csv(root: Path, relative: str, *, header_subset: tuple[str, ...] = ()) -> tuple[bool, str, dict[str, bool]]:
    path = root / relative
    if not path.is_file():
        return False, f"missing: {relative}", {"exists": False}
    if path.stat().st_size == 0:
        return False, f"empty: {relative}", {"exists": True, "non_empty": False}
    checks: dict[str, bool] = {"exists": True, "non_empty": True}
    if header_subset:
        with path.open("r", encoding="utf-8", newline="") as stream:
            header = {(cell or "").strip().lower() for cell in next(csv.reader(stream), [])}
        checks["header_columns"] = all(any(token in column for column in header) for token in header_subset)
    ok = all(checks.values())
    return ok, "present", checks


def _check_v1_0_1_source(root: Path) -> tuple[bool, str, dict[str, bool]]:
    drop_zone = root / "study_files/research/demand-zone-ai-study/recovered_source"
    if not drop_zone.is_dir():
        return False, "recovered source not provided; drop zone absent", {"drop_zone_exists": False}
    for path in sorted(drop_zone.rglob("*")):
        if path.is_file() and sha256_file(path) == PIN_CODE_SHA256_V1_0_1:
            return True, f"source recovered and hash-matched: {path.relative_to(root).as_posix()}", {"hash_match": True}
    return False, "drop zone present but no file matches the v1.0.1 code_sha256 pin", {"hash_match": False}


def _check_exists(root: Path, relative: str) -> tuple[bool, str, dict[str, bool]]:
    path = root / relative
    if path.is_file():
        return True, "present", {"exists": True}
    return False, f"missing: {relative}", {"exists": False}


_INPUT_CHECKS: dict[str, Callable[[Path], tuple[bool, str, dict[str, bool]]]] = {
    "v1_run_manifest": _check_v1_run_manifest,
    "v2_roster_dataset": _check_v2_roster,
    "ohlcv_cache": _check_ohlcv_cache,
    "v1_0_1_source": _check_v1_0_1_source,
    "feature_parity": lambda root: (False, "established only by the AAL parity comparison after v1_0_1_source is restored", {"automated": False}),
    "v5_dataset": lambda root: _check_plain_csv(root, "study_files/outputs/v5/demand_zone_v5_dataset.csv", header_subset=("ticker", "date")),
    "v13_dataset": lambda root: _check_exists(root, "study_files/outputs/v13/demand_zone_ml_dataset_v13.csv"),
    "hold1_dataset": lambda root: _check_exists(root, "study_files/outputs/hold1/demand_zone_hold1_dataset_v1.csv"),
}


def verify_inputs(root: Path) -> dict[str, Any]:
    """Verify every required research input without fabricating anything."""
    root = root.resolve()
    inputs: dict[str, Any] = {}
    for requirement in REQUIRED_INPUTS:
        present, detail, checks = _INPUT_CHECKS[requirement.key](root)
        inputs[requirement.key] = {
            "title": requirement.title,
            "expected_locations": list(requirement.expected_locations),
            "why": requirement.why,
            "depends_on": requirement.depends_on,
            "affects_reproducibility": requirement.affects_reproducibility,
            "required_for_reproduction": requirement.required_for_reproduction,
            "verify": requirement.verify,
            "present": present,
            "detail": detail,
            "checks": checks,
        }
    holdout_dir = root / "study_files/outputs/study_v1/prospective"
    sealed = {
        "compliant": not holdout_dir.exists(),
        "detail": ("final holdout artifacts absent; holdout remains sealed"
                   if not holdout_dir.exists()
                   else "prospective/holdout artifacts exist; final holdout is not sealed"),
    }
    blockers = [key for key, row in inputs.items()
                if row["required_for_reproduction"] and not row["present"]]
    attribution_blockers = [key for key, row in inputs.items()
                            if not row["required_for_reproduction"] and row["affects_reproducibility"]
                            and not row["present"]]
    return {
        "checked_at": utc_now(),
        "root": str(root),
        "inputs": inputs,
        "required_blockers": blockers,
        "attribution_blockers": attribution_blockers,
        "sealed_holdout": sealed,
    }


# ---------------------------------------------------------------------------
# Phase 4: serializable experiment interface
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileChange:
    path: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "content": self.content}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FileChange":
        return cls(path=str(value["path"]), content=str(value["content"]))


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    parent_version: str
    hypothesis: str
    proposed_change: dict[str, Any]
    files_allowed_to_change: tuple[str, ...]
    evaluation_protocol: dict[str, Any]
    random_seed: int
    resource_limits: dict[str, Any]
    timeout: float
    allow_repeat: bool = False  # duplicate specs are refused unless deliberately intended
    baseline_id: str | None = None  # scope to the active experiment baseline
    # Generation provenance (metadata only; never trusted or executed). Written
    # by the reviewed spec provider -- see autonomous_agent/spec_recipes.py.
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "parent_version": self.parent_version,
            "hypothesis": self.hypothesis,
            "proposed_change": self.proposed_change,
            "files_allowed_to_change": list(self.files_allowed_to_change),
            "evaluation_protocol": self.evaluation_protocol,
            "random_seed": self.random_seed,
            "resource_limits": self.resource_limits,
            "timeout": self.timeout,
            "allow_repeat": bool(self.allow_repeat),
            "baseline_id": self.baseline_id,
            "provenance": dict(self.provenance),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentSpec":
        return cls(
            experiment_id=str(value["experiment_id"]),
            parent_version=str(value["parent_version"]),
            hypothesis=str(value["hypothesis"]),
            proposed_change=dict(value["proposed_change"]),
            files_allowed_to_change=tuple(value["files_allowed_to_change"]),
            evaluation_protocol=dict(value["evaluation_protocol"]),
            random_seed=int(value["random_seed"]),
            resource_limits=dict(value["resource_limits"]),
            timeout=float(value["timeout"]),
            allow_repeat=bool(value.get("allow_repeat", False)),
            baseline_id=value.get("baseline_id"),
            provenance=dict(value.get("provenance") or {}),
        )

    def changes(self) -> list[FileChange]:
        files = self.proposed_change.get("files") or []
        return [FileChange.from_dict(item) for item in files]

    def validate(self) -> None:
        if not self.experiment_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in self.experiment_id):
            raise AdapterError(f"Invalid experiment_id: {self.experiment_id!r}")
        if not isinstance(self.parent_version, str) or not self.parent_version.startswith("V"):
            raise AdapterError("parent_version must be an explicit champion version.")
        if not self.hypothesis or not self.hypothesis.strip():
            raise AdapterError("Every candidate requires a written hypothesis; random mutations are prohibited.")
        summary = self.proposed_change.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise AdapterError("proposed_change.summary must state exactly what the candidate intends to change.")
        changes = self.changes()
        if not changes:
            raise AdapterError("proposed_change.files must contain at least one explicit file change.")
        if not self.files_allowed_to_change:
            raise AdapterError("files_allowed_to_change must be a non-empty allowlist.")
        for allowed in self.files_allowed_to_change:
            _require_allowed_path(allowed)
        for change in changes:
            _require_allowed_path(change.path)
            if not _matches_allowlist(change.path, self.files_allowed_to_change):
                raise AllowlistViolation(f"Change to {change.path} is outside files_allowed_to_change.")
        if not isinstance(self.evaluation_protocol, dict) or "acceptance_criteria" not in self.evaluation_protocol:
            raise AdapterError("evaluation_protocol must predeclare acceptance_criteria.")
        if isinstance(self.random_seed, bool) or not isinstance(self.random_seed, int):
            raise AdapterError("random_seed must be an integer.")
        if not isinstance(self.timeout, (int, float)) or self.timeout <= 0 or self.timeout > 86_400:
            raise AdapterError("timeout must be in (0, 86400] seconds.")
        if self.baseline_id is not None and not isinstance(self.baseline_id, str):
            raise AdapterError("baseline_id must be a string when provided.")
        if not isinstance(self.provenance, dict):
            raise AdapterError("provenance must be a metadata mapping when provided.")


def _normalized_relative(path: str) -> str:
    candidate = PurePosixPath(path.replace("\\", "/"))
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
        raise AllowlistViolation(f"Unsafe change path: {path!r}")
    return candidate.as_posix()


def _within_prefixes(relative: str, prefixes: Iterable[str]) -> bool:
    for prefix in prefixes:
        cleaned = prefix.rstrip("/")
        if relative == cleaned or relative.startswith(cleaned + "/"):
            return True
        if fnmatch.fnmatch(relative, cleaned):
            return True
    return False


def _require_allowed_path(path: str) -> str:
    relative = _normalized_relative(path)
    if _within_prefixes(relative, FORBIDDEN_CHANGE_PREFIXES):
        raise AllowlistViolation(f"Path is on the forbidden surface: {relative}")
    if not _within_prefixes(relative, ALLOWED_CHANGE_PREFIXES):
        raise AllowlistViolation(f"Path is outside the experiment allowlist: {relative}")
    return relative


def _matches_allowlist(path: str, allowed: Iterable[str]) -> bool:
    relative = _normalized_relative(path)
    return _within_prefixes(relative, tuple(allowed))


@dataclass
class ExperimentResult:
    experiment_id: str
    status: str
    candidate_version: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    checks: dict[str, str] = field(default_factory=dict)
    leakage_status: str = "NOT_RUN"
    holdout_status: str = "SEALED"
    robustness_status: str = "NOT_RUN"
    runtime: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    acceptance_recommendation: str = "REJECT"
    candidate_path: str | None = None
    release_metadata: dict[str, Any] | None = None
    reproduction_command: str | None = None
    blockers: list[str] = field(default_factory=list)
    baseline_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "status": self.status,
            "candidate_version": self.candidate_version,
            "metrics": self.metrics,
            "checks": self.checks,
            "leakage_status": self.leakage_status,
            "holdout_status": self.holdout_status,
            "robustness_status": self.robustness_status,
            "runtime": self.runtime,
            "artifacts": self.artifacts,
            "error": self.error,
            "acceptance_recommendation": self.acceptance_recommendation,
            "candidate_path": self.candidate_path,
            "release_metadata": self.release_metadata,
            "reproduction_command": self.reproduction_command,
            "blockers": self.blockers,
            "baseline_id": self.baseline_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentResult":
        return cls(
            experiment_id=str(value["experiment_id"]),
            status=str(value["status"]),
            candidate_version=value.get("candidate_version"),
            metrics=dict(value.get("metrics") or {}),
            checks=dict(value.get("checks") or {}),
            leakage_status=str(value.get("leakage_status", "NOT_RUN")),
            holdout_status=str(value.get("holdout_status", "SEALED")),
            robustness_status=str(value.get("robustness_status", "NOT_RUN")),
            runtime=dict(value.get("runtime") or {}),
            artifacts=dict(value.get("artifacts") or {}),
            error=value.get("error"),
            acceptance_recommendation=str(value.get("acceptance_recommendation", "REJECT")),
            candidate_path=value.get("candidate_path"),
            release_metadata=value.get("release_metadata"),
            reproduction_command=value.get("reproduction_command"),
            blockers=list(value.get("blockers") or []),
            baseline_id=value.get("baseline_id"),
        )

    def to_supervisor_outcome(self) -> dict[str, Any]:
        """Map to the supervisor's outcome contract (core.Supervisor._validate_outcome)."""
        checks = {
            "unit": "NOT_RUN", "data_integrity": "NOT_RUN", "leakage": "NOT_RUN",
            "walk_forward": "NOT_RUN", "robustness": "NOT_RUN", "evaluation": "NOT_RUN",
        }
        checks.update({key: str(val) for key, val in self.checks.items()})
        accepted = self.status == "ACCEPTED"
        outcome: dict[str, Any] = {
            "status": "ACCEPTED" if accepted else "REJECTED",
            "checks": checks,
            "results": self.metrics,
            "candidate_path": self.candidate_path,
            "holdout_touched": self.holdout_status == "TOUCHED",
            "error": self.error,
            "blockers": self.blockers,
            "acceptance_recommendation": self.acceptance_recommendation,
            "runtime": self.runtime,
            "leakage_status": self.leakage_status,
            "robustness_status": self.robustness_status,
            "baseline_id": self.baseline_id,
        }
        if not accepted:
            outcome["rejection_reason"] = (
                (self.error or {}).get("message")
                or self.acceptance_recommendation
                or "Candidate did not pass every mandatory gate."
            )
        else:
            outcome["artifact_sha256"] = self.artifacts.get("tree_sha256")
            outcome["release_metadata"] = self.release_metadata
            outcome["reproduction_command"] = self.reproduction_command
        return outcome


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

@dataclass
class CommandRun:
    role: str
    argv: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role, "argv": list(self.argv), "returncode": self.returncode,
            "stdout": self.stdout, "stderr": self.stderr,
            "duration_seconds": self.duration_seconds, "timed_out": self.timed_out,
        }


def _default_command_factory(workspace: Path) -> dict[str, list[str]]:
    """The fixed, reviewed command registry. Nothing else is ever executed."""
    python = sys.executable
    return {
        "unit_tests": [python, "-m", "unittest", "discover",
                       "-s", "study_files/backend/tests", "-v"],
        "audit": [python, str(workspace / "study_files/backend/demand_zone_study_v1.py"), "audit"],
        "development": [python, str(workspace / "study_files/backend/demand_zone_study_v1.py"),
                        "development", "--artifact-dir",
                        str(workspace / "study_files/outputs/study_v1_reproduction")],
        "experiment": [python, "-m", "autonomous_agent.experiments.run_experiment"],
    }


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} characters]"


def _iter_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _iter_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


class ExperimentAdapter:
    """Prepare, run, evaluate, and (fail-safely) destroy isolated experiments."""

    def __init__(self, root: Path = PROJECT_ROOT, candidates_root: Path | None = None,
                 state_root: Path | None = None,
                 command_factory: Callable[[Path], dict[str, list[str]]] | None = None,
                 journal_name: str = JOURNAL_NAME):
        self.root = root.resolve()
        self.candidates_root = (candidates_root or (self.root / "autonomous_agent/candidates")).resolve()
        self.state_root = (state_root or (self.root / "autonomous_agent/state")).resolve()
        self.command_factory = command_factory or _default_command_factory
        self.journal_path = self.state_root / journal_name
        self.baseline_state_path = self.state_root / BASELINE_STATE_NAME

    # --- original-tree immutability ---------------------------------------
    def _fingerprint_heartbeat(self, phase: str) -> Callable[[Any], None]:
        """Journal bounded phase heartbeats while a full fingerprint runs.

        Re-hashing the guarded tree can take minutes; without a heartbeat a
        stalled or pathologically slow disk looks identical to a healthy
        long pass. Heartbeats are journal events only: they never change the
        hash, the exclusion boundary, or any fail-closed decision, and they
        appear at most once per heartbeat window to keep the journal bounded.
        Callback/listener errors propagate (fail-closed).
        """
        def callback(payload: Any) -> None:
            append_jsonl(self.journal_path,
                         {**payload, "phase": phase, "at": utc_now()})
        return callback
    def _fingerprint_exclusions(self) -> tuple[str, ...]:
        return ("autonomous_agent/state", "autonomous_agent/candidates",
                "autonomous_agent/BASELINE_REPRODUCTION_REPORT.md",
                "autonomous_agent/BASELINE_RECONSTRUCTED_REPORT.md")

    def original_fingerprint(self, progress_callback: Callable[[Any], None] | None = None,
                             heartbeat_seconds: float = 60.0) -> str:
        """Deterministic hash of the original tree the agent must never modify.

        ``progress_callback`` receives a phase-heartbeat dict every
        ``heartbeat_seconds`` of wall time (and once at the end) so long
        fingerprint passes are observable in the journal without changing the
        hash, the boundary, or any fail-closed behavior. Callback errors
        propagate (fail-closed), they are never swallowed.
        """
        exclusions = self._fingerprint_exclusions()
        # `versions` holds frozen promotion snapshots (full copies of the tree,
        # ~6k entries each; 72 snapshots = ~444k files as of 2026-10-25). They are
        # validated and hash-verified at promotion time and are agent-created
        # output, not the guarded original source: hashing them here made the
        # check grow past 13 h/cycle (see CAMPAIGN_4 operations audit item 9).
        skipped_names = {".git", "__pycache__", ".freebuff", "node_modules",
                         ".restoration_tmp", "versions"}
        digest = hashlib.sha256()
        started = time.monotonic()
        last_beat = started
        files_hashed = 0
        bytes_hashed = 0
        current = ""

        def beat(final: bool = False) -> None:
            if progress_callback is None:
                return
            progress_callback({"event": "original_fingerprint_heartbeat",
                               "files_hashed": files_hashed,
                               "bytes_hashed": bytes_hashed,
                               "elapsed_seconds": round(time.monotonic() - started, 3),
                               "last_path": current,
                               "final": final})

        for path in sorted(self.root.rglob("*"), key=lambda item: item.relative_to(self.root).as_posix()):
            relative = path.relative_to(self.root).as_posix()
            parts = PurePosixPath(relative).parts
            if any(part in skipped_names for part in parts):
                continue
            if any(relative == item or relative.startswith(item + "/") for item in exclusions):
                continue
            if path.is_symlink():
                raise Anomaly(f"Symlink in original tree: {relative}")
            if path.is_file():
                digest.update(relative.encode("utf-8"))
                size = path.stat().st_size
                digest.update(bytes.fromhex(sha256_file(path)))
                files_hashed += 1
                bytes_hashed += size
                current = relative
                now = time.monotonic()
                if now - last_beat >= heartbeat_seconds:
                    last_beat = now
                    beat()
        beat(final=True)
        return digest.hexdigest()

    def assert_original_unchanged(self, fingerprint: str,
                                  progress_callback: Callable[[Any], None] | None = None) -> None:
        if self.original_fingerprint(progress_callback) != fingerprint:
            raise Anomaly("Original working tree changed during the experiment; "
                          "the repository is not in a known-safe state.")

    # --- input verification -------------------------------------------------
    def verify_inputs(self) -> dict[str, Any]:
        return verify_inputs(self.root)

    def pipeline_fingerprint(self, verification: Mapping[str, Any] | None = None) -> str:
        verification = verification or self.verify_inputs()
        parts = []
        for relative in ("study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",
                         "study_files/backend/demand_zone_study_v1.py",
                         "study_files/backend/tests/test_demand_zone_study_v1.py"):
            path = self.root / relative
            parts.append(f"{relative}={sha256_file(path) if path.is_file() else 'absent'}")
        for key in ("v2_roster_dataset", "ohlcv_cache", "v1_run_manifest"):
            row = verification["inputs"][key]
            parts.append(f"{key}={row['detail']}")
        return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()

    # --- workspace lifecycle ------------------------------------------------
    def _prepare_workspace(self, spec: ExperimentSpec, candidate_dir: Path) -> Path:
        workspace = candidate_dir / "workspace"
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
        workspace.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.root, workspace, ignore=shutil.ignore_patterns(*COPY_IGNORE_PATTERNS))
        hardening.install_network_guard(workspace)
        self._enforce_workspace_limits(workspace, spec)
        self._apply_changes(spec, workspace)
        self._enforce_workspace_limits(workspace, spec)
        return workspace

    def _enforce_workspace_limits(self, workspace: Path, spec: ExperimentSpec) -> None:
        limits = {**DEFAULT_RESOURCE_LIMITS, **(spec.resource_limits or {})}
        files = 0
        total = 0
        for path in workspace.rglob("*"):
            if path.is_file():
                files += 1
                total += path.stat().st_size
                if files > int(limits["max_workspace_files"]):
                    raise Anomaly("Candidate workspace exceeded the file-count resource limit.")
                if total > int(limits["max_workspace_bytes"]):
                    raise Anomaly("Candidate workspace exceeded the size resource limit.")
        if workspace.is_symlink():
            raise Anomaly("Candidate workspace may not be a symlink.")

    def _apply_changes(self, spec: ExperimentSpec, workspace: Path) -> None:
        for change in spec.changes():
            relative = _require_allowed_path(change.path)
            if not _matches_allowlist(relative, spec.files_allowed_to_change):
                raise AllowlistViolation(f"Change to {relative} is outside files_allowed_to_change.")
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            parts = PurePosixPath(relative).parts
            for depth in range(1, len(parts)):
                ancestor = workspace.joinpath(*parts[:depth])
                if ancestor.is_symlink():
                    raise AllowlistViolation(f"Symlinked candidate path refused: {relative}")
            if target.is_symlink():
                raise AllowlistViolation(f"Symlinked candidate target refused: {relative}")
            resolved = target.resolve()
            if not resolved.is_relative_to(workspace.resolve()):
                raise AllowlistViolation(f"Change escapes the isolated workspace: {relative}")
            temporary = target.with_suffix(target.suffix + ".tmp")
            temporary.write_text(change.content, encoding="utf-8", newline="\n")
            os.replace(temporary, target)

    def _run_role(self, spec: ExperimentSpec, workspace: Path, role: str,
                  timeout: float | None = None) -> CommandRun:
        registry = self.command_factory(workspace)
        argv = registry.get(role)
        if not argv:
            raise AdapterError(f"Command role {role!r} is not in the reviewed registry; refusing to execute.")
        limits = {**DEFAULT_RESOURCE_LIMITS, **(spec.resource_limits or {})}
        env = hardening.scrubbed_environment(
            os.environ, seed=spec.random_seed, experiment_id=spec.experiment_id,
            allow_network=bool(limits.get("allow_network", False)),
            gpu_enabled=bool(limits.get("gpu_enabled", False)),
        )
        guard_dir = workspace / "_agent_sandbox"
        if guard_dir.is_dir():
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = str(guard_dir) + (os.pathsep + existing if existing else "")
        outcome = hardening.run_with_limits(
            [str(part) for part in argv], cwd=workspace, env=env,
            timeout=timeout if timeout is not None else float(spec.timeout),
            limits=limits, state_root=self.state_root,
            experiment_id=spec.experiment_id, role=role,
        )
        started = time.monotonic() - outcome["duration_seconds"]
        timed_out = bool(outcome["timed_out"])
        stdout, stderr = outcome["stdout"], outcome["stderr"]
        returncode: int | None = outcome["returncode"]
        limit = int(limits["max_output_bytes"])
        run = CommandRun(role=role, argv=[str(part) for part in argv], returncode=returncode,
                         stdout=_truncate(stdout, limit), stderr=_truncate(stderr, limit),
                         duration_seconds=round(max(time.monotonic() - started, 0.0), 3), timed_out=timed_out)
        append_jsonl(self.journal_path, {"event": "command_run", "experiment_id": spec.experiment_id,
                                        "role": role, "returncode": returncode,
                                        "timed_out": timed_out, "at": utc_now()})
        return run

    def destroy_candidate(self, workspace: Path) -> None:
        """Fail-safe destruction; quarantines on failure instead of losing evidence."""
        if not workspace.exists():
            return
        try:
            shutil.rmtree(workspace)
        except OSError:
            quarantine = workspace.with_name(f"{workspace.name}.quarantine-{uuid.uuid4().hex[:8]}")
            try:
                os.replace(workspace, quarantine)
            except OSError as error:
                raise Anomaly(f"Candidate destruction failed and quarantine failed: {error}")

    # --- evaluation (Phase 8) ----------------------------------------------
    def evaluate(self, spec: ExperimentSpec, runs: list[CommandRun],
                 evaluation: Mapping[str, Any] | None, *, integrity_ok: bool,
                 holdout_touched: bool) -> tuple[dict[str, str], str, list[str], dict[str, Any]]:
        checks: dict[str, str] = {}
        reasons: list[str] = []
        metrics = dict((evaluation or {}).get("results") or {})

        unit_runs = [run for run in runs if run.role == "unit_tests"]
        if not unit_runs:
            checks["unit"] = "NOT_RUN"
            reasons.append("Unit tests were not run.")
        elif all(run.returncode == 0 and not run.timed_out for run in unit_runs):
            checks["unit"] = "PASS"
        else:
            checks["unit"] = "FAIL"
            reasons.append("Unit tests failed.")

        checks["data_integrity"] = "PASS" if integrity_ok else "FAIL"
        if not integrity_ok:
            reasons.append("Read-only inputs changed inside the isolated workspace.")

        leak_hits = sorted({token for token in LEAKAGE_TOKENS
                            for key in _iter_keys(evaluation or {})
                            if token in key.lower()})
        outputs_dir = self.candidates_root / spec.experiment_id / "workspace" / "outputs"
        if outputs_dir.is_dir():
            for artifact in sorted(outputs_dir.rglob("*.csv")):
                with artifact.open("r", encoding="utf-8", errors="replace") as stream:
                    header = next(csv.reader(stream), [])
                leak_hits.extend(token for token in LEAKAGE_TOKENS
                                 if any(token in column.lower() for column in header))
        if leak_hits:
            checks["leakage"] = "FAIL"
            reasons.append(f"Leakage-prone tokens in candidate outputs: {sorted(set(leak_hits))}")
        elif holdout_touched:
            checks["leakage"] = "FAIL"
            reasons.append("Final holdout was touched during the experiment.")
        else:
            checks["leakage"] = "PASS"
        self_leakage = "FAIL" if checks["leakage"] != "PASS" else "PASS"

        walk_forward = (evaluation or {}).get("walk_forward") or {}
        folds = walk_forward.get("folds") if isinstance(walk_forward, dict) else None
        temporal_ok = False
        if isinstance(folds, list) and len(folds) >= 3 and walk_forward.get("purge_verified") is True:
            temporal_ok = True
            previous_end = ""
            for fold in folds:
                train_end = str(fold.get("train_end") or "")
                start = str(fold.get("validation_start") or "")
                end = str(fold.get("validation_end") or "")
                if not (train_end and start and end) or not train_end < start <= end or start < previous_end:
                    temporal_ok = False
                    break
                previous_end = end
        checks["walk_forward"] = "PASS" if temporal_ok else "FAIL"
        if not temporal_ok:
            reasons.append("Walk-forward folds are missing, non-chronological, or unpurged.")

        per_seed = metrics.get("per_seed_metrics")
        subgroup = metrics.get("subgroup_stability")
        interval = metrics.get("uncertainty_interval") or {}
        robust_ok = (
            isinstance(per_seed, dict) and len(per_seed) >= 3
            and isinstance(subgroup, dict) and bool(subgroup)
            and isinstance(interval, dict)
            and isinstance(interval.get("lower"), (int, float))
            and isinstance(interval.get("upper"), (int, float))
            and interval["lower"] <= interval["upper"]
        )
        checks["robustness"] = "PASS" if robust_ok else "FAIL"
        robustness_status = checks["robustness"]
        if not robust_ok:
            reasons.append("Robustness evidence is incomplete (need >=3 seeds, subgroup stability, uncertainty interval).")

        missing_results = [key for key in EVALUATION_CONTRACT["results_keys"] if key not in metrics]
        primary = metrics.get("primary_metric") or {}
        criteria = spec.evaluation_protocol.get("acceptance_criteria") or {}
        min_delta = float(criteria.get("primary_metric_min_delta", 0.0))
        release_metadata = (evaluation or {}).get("release_metadata") or {}
        missing_metadata = [key for key in EVALUATION_CONTRACT["release_metadata_keys"]
                            if release_metadata.get(key) in (None, "", [], {})]
        evaluation_ok = (
            not missing_results
            and metrics.get("decision_criteria_passed") is True
            and isinstance(primary, dict)
            and isinstance(primary.get("delta"), (int, float))
            and primary["delta"] >= min_delta
            and not missing_metadata
        )
        checks["evaluation"] = "PASS" if evaluation_ok else "FAIL"
        if not evaluation_ok:
            reasons.append(
                "Evaluation evidence is incomplete or predeclared acceptance criteria "
                f"failed (missing results: {missing_results}; missing release metadata: "
                f"{missing_metadata})."
            )

        gates = ("unit", "data_integrity", "leakage", "walk_forward", "robustness", "evaluation")
        decision = "ACCEPT" if all(checks.get(name) == "PASS" for name in gates) else "REJECT"
        # A metric improvement alone is never sufficient; every gate must pass.
        return checks, decision, reasons, metrics

    def _candidate_outputs(self, spec: ExperimentSpec) -> Path:
        return self.candidates_root / spec.experiment_id / "workspace" / "outputs"

    # --- Phase 5: baseline reproduction ------------------------------------
    def is_baseline_reproduced(self) -> tuple[bool, dict[str, Any]]:
        state = read_json(self.baseline_state_path, {})
        if state.get("status") != "REPRODUCED":
            return False, state
        current = self.pipeline_fingerprint()
        if state.get("pipeline_fingerprint") != current:
            return False, {**state, "stale": "pipeline or inputs changed since the recorded reproduction"}
        return True, state

    def run_reproduction(self, *, force: bool = False) -> ExperimentResult:
        """Phase 5: reproduce the documented baseline before any candidate work."""
        from autonomous_agent.campaign5_authorization import check_campaign5_authorization
        campaign = read_json(self.root / "autonomous_agent/state/campaign_config.json", {}) or {}
        campaign_id = campaign.get("campaign_id")
        preflight = check_campaign5_authorization(self.root, campaign, campaign.get("authorization_scope"))
        if (isinstance(campaign_id, str) and campaign_id.startswith("campaign-5")
                and not preflight["allowed"]):
            return ExperimentResult(
                experiment_id="baseline-reproduction", status="BLOCKED",
                blockers=list(preflight["reason_codes"]),
                error={"message": "Campaign 5 authorization preflight blocked reproduction.",
                       "reason_codes": list(preflight["reason_codes"])},
                acceptance_recommendation="STOP_AUTONOMOUS_EXPERIMENTATION")
        if not force:
            reproduced, state = self.is_baseline_reproduced()
            if reproduced:
                return ExperimentResult.from_dict(state["result"])
        verification = self.verify_inputs()
        record = self._baseline_record(verification)
        record["inputs_detail"] = {key: row["detail"] for key, row in verification["inputs"].items()}
        blockers = list(verification["required_blockers"])
        if blockers:
            result = ExperimentResult(
                experiment_id="baseline-reproduction",
                status="BLOCKED",
                error={"message": "Required research inputs are missing; the documented "
                                  "baseline cannot be reproduced in this checkout.",
                       "blockers": blockers},
                acceptance_recommendation="STOP_AUTONOMOUS_EXPERIMENTATION",
                blockers=blockers,
                runtime=record.get("runtime", {}),
            )
            record["status"] = "BLOCKED"
            record["blockers"] = blockers
            record["attribution_blockers"] = list(verification["attribution_blockers"])
            record["result"] = result.to_dict()
            self._persist_baseline(record)
            return result

        original_hash = self.original_fingerprint(
            progress_callback=self._fingerprint_heartbeat("baseline_pre"))
        candidate_dir = self.candidates_root / "baseline-reproduction"
        workspace = candidate_dir / "workspace"
        result = ExperimentResult(experiment_id="baseline-reproduction", status="FAILED",
                                  acceptance_recommendation="STOP_AUTONOMOUS_EXPERIMENTATION")
        produced_manifest: dict[str, Any] | None = None
        try:
            spec = ExperimentSpec(
                experiment_id="baseline-reproduction",
                parent_version="V1.0.1",
                hypothesis="Reproduction run: the unmodified pipeline must reproduce "
                           "the documented baseline. This is not an improvement experiment.",
                proposed_change={"summary": "No change; reproduction only.", "files": []},
                files_allowed_to_change=tuple(ALLOWED_CHANGE_PREFIXES),
                evaluation_protocol={"acceptance_criteria": {}},
                random_seed=42,
                resource_limits={},
                timeout=REPRODUCTION_TIMEOUT_SECONDS,
            )
            workspace = self._prepare_workspace(spec, candidate_dir)
            runs: list[CommandRun] = []
            for role in ("unit_tests", "audit", "development"):
                run = self._run_role(spec, workspace, role, timeout=REPRODUCTION_TIMEOUT_SECONDS)
                runs.append(run)
                if run.timed_out or run.returncode != 0:
                    raise Anomaly(f"Reproduction step {role!r} failed (rc={run.returncode}, timed_out={run.timed_out}).")
            produced_path = workspace / "study_files/outputs/study_v1_reproduction/development/run_manifest.json"
            produced_manifest = read_json(produced_path, None)
            archived_manifest = read_json(self.root / "study_files/outputs/study_v1/development/run_manifest.json", None)
            if not isinstance(produced_manifest, dict) or not isinstance(archived_manifest, dict):
                raise Anomaly("Reproduction did not yield a comparison manifest.")
            drift = _manifest_drift(
                archived_manifest, produced_manifest,
                expected_archived_protocol=PIN_PROTOCOL_SHA256_V1_0_1,
                expected_produced_protocol=sha256_file(
                    self.root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"),
            )
            record["reproduction"] = {
                "artifact_hashes_match": not drift,
                "drift": drift,
                "produced_metrics": produced_manifest.get("pooled_oof_metrics"),
            }
            if drift:
                result.status = "FAILED"
                result.error = {"message": "Reproduction drift: produced artifacts/metrics "
                                           "do not match the restored manifest.",
                               "drift": drift}
                result.metrics = {"comparison": record["reproduction"]}
            else:
                result.status = "REPRODUCED"
                result.acceptance_recommendation = "PROCEED_TO_CANDIDATES"
                result.metrics = {"comparison": record["reproduction"]}
        except Exception as error:  # fail safe: never propagate, always record
            result.status = "FAILED"
            result.error = {"message": f"{type(error).__name__}: {error}",
                            "traceback": traceback.format_exc(limit=10)}
        finally:
            self.destroy_candidate(workspace)

        # Immutability enforcement must never swallow the run record: record
        # first (so the evidence survives), then enforce. A changed original
        # tree is still an anomaly that aborts autonomation afterwards.
        tree_unchanged = True
        try:
            self.assert_original_unchanged(
                original_hash,
                progress_callback=self._fingerprint_heartbeat("experiment_post"))
        except Anomaly as anomaly:
            tree_unchanged = False
            record["original_tree_violation"] = str(anomaly)
            if result.status == "REPRODUCED":
                result.status = "FAILED"
                result.error = {"message": str(anomaly)}
                result.acceptance_recommendation = "STOP_AUTONOMOUS_EXPERIMENTATION"
        record["original_tree_unchanged"] = tree_unchanged
        record["status"] = result.status
        record["blockers"] = list(result.blockers)
        record["result"] = result.to_dict()
        self._persist_baseline(record)
        if not tree_unchanged:
            raise Anomaly("Original working tree changed during the reproduction; "
                          "the repository is not in a known-safe state.")
        return result

    def _baseline_record(self, verification: Mapping[str, Any]) -> dict[str, Any]:
        """Phase 5 record: commit, checksums, config, features, model, seed,
        intervals, metrics, runtime, environment -- honest about gaps."""
        protocol = read_json(self.root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json", {}) or {}
        sanitized = read_json(
            self.root / "study_files/research/demand-zone-ai-study/run_manifest_sanitized.json", {}) or {}
        dataset_checksums: dict[str, Any] = {}
        archive_dir = self.root / "study_files/outputs/study_v1/development"
        for name in ("event_table.csv", "oof_predictions.csv"):
            path = archive_dir / name
            dataset_checksums[f"study_files/outputs/study_v1/development/{name}"] = (
                sha256_file(path) if path.is_file() else "MISSING")
        models_dir = self.root / "study_files/outputs/study_v1/models"
        for path in sorted(models_dir.glob("*.joblib")) if models_dir.is_dir() else []:
            dataset_checksums[f"study_files/outputs/study_v1/models/{path.name}"] = sha256_file(path)
        dataset_checksums["study_files/outputs/v2/demand_zone_v2_dataset.csv"] = (
            "MISSING" if not verification["inputs"]["v2_roster_dataset"]["present"]
            else verification["inputs"]["v2_roster_dataset"]["detail"])
        dataset_checksums["study_files/outputs/v2/_ohlcv/ (153 CSVs)"] = (
            "MISSING" if not verification["inputs"]["ohlcv_cache"]["present"]
            else verification["inputs"]["ohlcv_cache"]["detail"])
        folds = [fold for fold in
                 ((protocol.get("historical_development_evaluation") or {}).get("folds") or [])]
        estimators = protocol.get("estimators") or {}
        record = {
            "recorded_at": utc_now(),
            "status": "PENDING",
            "commit": _git_identity(self.root),
            "protocol": {
                "id": protocol.get("protocol_id"),
                "version": protocol.get("protocol_version"),
                "sha256": sha256_file(self.root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json")
                if (self.root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json").is_file() else None,
            },
            "dataset_checksums": dataset_checksums,
            "configuration": {"estimators": estimators,
                              "replay_cutoff": protocol.get("historical_development_evaluation", {}).get("replay_signal_date_cutoff_exclusive")},
            "feature_set": {
                "arms": {name: len(features) for name, features in
                         ((sanitized.get("feature_arms") or {}).items())} or "see protocol feature_groups",
                "feature_arms_sha256": sanitized.get("feature_arms_sha256"),
            },
            "models": sorted(estimators.keys()) or ["LogisticRegression", "LightGBM"],
            "random_seed": 42,
            "intervals": {
                "training": "expanding windows, train signal dates strictly before each fold start "
                            "with target-maturity purge (train exit < validation start)",
                "validation_folds": folds,
                "test": "FINAL HOLDOUT SEALED: zero prospective predictions exist; no test interval has been evaluated.",
            },
            "metrics": {
                "source": "ARCHIVED v1.0.1 values (sanitized manifest) -- NOT REPRODUCED",
                "pooled_oof_metrics": sanitized.get("pooled_oof_metrics"),
            },
            "runtime": {"reproduction_executed": False},
            "environment": _environment_info(),
        }
        return record

    def _persist_baseline(self, record: dict[str, Any]) -> None:
        write_json_atomic(self.baseline_state_path, record)
        lines = [
            "# Baseline Reproduction Report",
            "",
            f"Generated by `py -3 -m autonomous_agent.experiment_adapter reproduce` at {record['recorded_at']}.",
            "",
            f"**Status: `{record['status']}`**",
            "",
        ]
        if record["status"] != "REPRODUCED":
            lines += [
                "> **Autonomous experimentation is STOPPED.** Per the research contract,",
                "> no candidate experiment may run, and no version may be promoted, until",
                "> the documented baseline reproduces. Do not optimize around an",
                "> unreproducible baseline.",
                "",
            ]
        blockers = record.get("blockers") or []
        if blockers:
            lines += ["## What is preventing reproduction", ""]
            for key in blockers:
                detail = record.get("inputs_detail", {}).get(key, "missing required input")
                lines.append(f"- `{key}`: {detail}")
            lines += ["", "See `autonomous_agent/INPUT_REQUIREMENTS.md` for restoration instructions.", ""]
        lines += [
            "## Phase 5 record",
            "",
            f"- **Exact commit/version:** `{json.dumps(record.get('commit', {}))}`",
            f"- **Protocol:** `{json.dumps(record.get('protocol', {}))}`",
            f"- **Dataset checksums:** `{json.dumps(record.get('dataset_checksums', {}), indent=2)}`",
            f"- **Configuration:** `{json.dumps(record.get('configuration', {}), indent=2)[:2000]}`",
            f"- **Feature set:** `{json.dumps(record.get('feature_set', {}))}`",
            f"- **Model:** {', '.join(record.get('models') or [])}",
            f"- **Seed:** {record.get('random_seed')}",
            f"- **Training/validation/test intervals:** `{json.dumps(record.get('intervals', {}), indent=2)}`",
            f"- **Metrics:** {json.dumps(record.get('metrics', {}), indent=2)[:3000]}",
            f"- **Runtime:** `{json.dumps(record.get('runtime', {}))}`",
            f"- **Environment:** `{json.dumps(record.get('environment', {}), indent=2)}`",
            "",
        ]
        if record.get("reproduction"):
            lines += ["## Reproduction comparison", "",
                      f"```json\n{json.dumps(record['reproduction'], indent=2, sort_keys=True)[:4000]}\n```", ""]
        report_path = self.root / "autonomous_agent/BASELINE_REPRODUCTION_REPORT.md"
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        append_jsonl(self.journal_path, {"event": "baseline_reproduction", "status": record["status"],
                                        "at": utc_now()})

    # --- Phase 5b: reconstructed active baseline ---------------------------
    def baseline_registry(self) -> baseline_registry.BaselineRegistry:
        return baseline_registry.BaselineRegistry(self.state_root)

    def active_baseline(self) -> tuple[dict[str, Any] | None, list[str]]:
        """The established reconstructed baseline, or the reasons there is none."""
        record = self.baseline_registry().active()
        if record is None:
            return None, ["No established reconstructed baseline is registered "
                          "(run establish-baseline); the historical V1.0.1 reproduction is a "
                          "separate, currently non-reproduced track."]
        reasons = baseline_registry.validate_established_record(record)
        if reasons:
            return None, reasons
        if record.get("pipeline_fingerprint") != self.pipeline_fingerprint():
            return None, ["Established baseline is stale: the pipeline or its inputs changed "
                          "since the baseline was established."]
        return record, []

    def experiment_baseline(self) -> tuple[str | None, dict[str, Any] | None, list[str]]:
        """Candidate-experiment gate: historical reproduction OR established baseline.

        The two tracks are distinct: "V1.0.1_REPRODUCED" can only come from the
        historical reproduction record; anything else is scoped to the active
        reconstructed baseline's baseline_id.
        """
        reproduced, state = self.is_baseline_reproduced()
        if reproduced:
            return "V1.0.1_REPRODUCED", state, []
        record, reasons = self.active_baseline()
        if record is not None:
            return str(record["baseline_id"]), record, []
        historical = f"historical V1.0.1 reproduction status: {(state or {}).get('status', 'NOT_RUN')}"
        return None, state, [historical, *reasons]

    def run_establish_baseline(self, baseline_id: str = DEFAULT_ESTABLISHED_BASELINE_ID) -> dict[str, Any]:
        """Establish a reconstructed baseline from the verified reconstruction.

        Two independent clean isolated executions (unit tests + audit +
        development) must produce byte-identical outputs. On success an
        append-only ESTABLISHED record is registered under ``baseline_id``.
        The historical V1.0.1 reproduction record is read only to verify it
        remains FAILED/BLOCKED and is never modified.
        """
        if not baseline_id or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in baseline_id):
            raise AdapterError(f"Invalid baseline_id: {baseline_id!r}")
        from autonomous_agent.campaign5_authorization import check_campaign5_authorization
        campaign = read_json(self.root / "autonomous_agent/state/campaign_config.json", {}) or {}
        campaign_id = campaign.get("campaign_id")
        preflight = check_campaign5_authorization(self.root, campaign, campaign.get("authorization_scope"))
        if (isinstance(campaign_id, str) and campaign_id.startswith("campaign-5")
                and not preflight["allowed"]):
            raise AdapterError("Campaign 5 authorization preflight blocked baseline establishment: "
                               + ",".join(preflight["reason_codes"]))
        registry = self.baseline_registry()
        if registry.find(baseline_id) is not None:
            raise FileExistsError(f"Baseline {baseline_id} is already registered; records are immutable.")
        historical_bytes = self.baseline_state_path.read_bytes() if self.baseline_state_path.is_file() else None
        historical_state = read_json(self.baseline_state_path, {}) or {}
        observed = historical_state.get("status")
        if observed not in (None, "FAILED", "BLOCKED"):
            raise Anomaly("The historical V1.0.1 record is not FAILED/BLOCKED; refusing to "
                          "establish a reconstructed baseline beside it.")
        verification = self.verify_inputs()
        if verification["required_blockers"]:
            raise AdapterError(f"Required research inputs are missing: "
                               f"{verification['required_blockers']}")
        if not verification["sealed_holdout"]["compliant"]:
            raise Anomaly("Final holdout is not sealed; no baseline may be established.")

        record: dict[str, Any] = {
            "baseline_id": baseline_id,
            "kind": "reconstructed_baseline",
            "status": "ESTABLISHING",
            "statement": RECONSTRUCTED_STATEMENT,
            "established_at": utc_now(),
            "lineage": {
                "relation": "reconstruction",
                "parent": "V1.0.1",
                "v1_0_1_status": HISTORICAL_V1_0_1_STATUS,
                "v1_0_1_record_status": observed,
                "historical_v1_0_1_sha256": PIN_CODE_SHA256_V1_0_1,
                "v1_0_1_evidence": "autonomous_agent/state/baseline_reproduction.json (unchanged)",
                "note": "The reconstructed implementation differs from historical V1.0.1: "
                        "49 known feature-column differences (rsi14, atr_pct, zone_width_pct, "
                        "14 zone-base and 32 order-block features).",
            },
        }
        try:
            spec = ExperimentSpec(
                experiment_id="baseline-establish",
                parent_version=baseline_id,
                hypothesis="Baseline establishment: two independent clean runs of the verified "
                           "reconstructed implementation must produce byte-identical outputs. "
                           "This is not an improvement experiment.",
                proposed_change={"summary": "No change; establishment runs only.", "files": []},
                files_allowed_to_change=tuple(ALLOWED_CHANGE_PREFIXES),
                evaluation_protocol={"acceptance_criteria": {}},
                random_seed=42,
                resource_limits={},
                timeout=REPRODUCTION_TIMEOUT_SECONDS,
                baseline_id=baseline_id,
            )
            manifests: list[dict[str, Any]] = []
            artifact_maps: list[dict[str, str]] = []
            runs_log: list[dict[str, Any]] = []
            for run_index in (1, 2):
                candidate_dir = self.candidates_root / f"baseline-establish-{run_index}"
                workspace = self._prepare_workspace(spec, candidate_dir)
                run_summaries = []
                for role in ("unit_tests", "audit", "development"):
                    run = self._run_role(spec, workspace, role, timeout=REPRODUCTION_TIMEOUT_SECONDS)
                    run_summaries.append(run.to_dict())
                    if run.timed_out or run.returncode != 0:
                        raise Anomaly(f"Baseline establishment step {role!r} failed "
                                      f"(rc={run.returncode}, timed_out={run.timed_out}).")
                artifact_dir = workspace / "study_files/outputs/study_v1_reproduction"
                manifest_path = artifact_dir / "development/run_manifest.json"
                manifest = read_json(manifest_path, None)
                if not isinstance(manifest, dict):
                    raise Anomaly("Establishment run did not produce a run manifest.")
                if (workspace / "study_files/outputs/study_v1/prospective").exists():
                    raise Anomaly("Final holdout was touched during establishment.")
                manifests.append(manifest)
                artifact_maps.append(_collect_artifact_map(artifact_dir))
                runs_log.append({"run": run_index, "commands": run_summaries,
                                 "run_manifest_sha256": sha256_file(manifest_path)})
                write_json_atomic(candidate_dir / "run_manifest.json", manifest)
            map_1, map_2 = artifact_maps
            manifest_rel = "development/run_manifest.json"
            # The run manifest embeds absolute output paths, so it is compared
            # field-wise (volatile keys excluded); every artifact file byte must
            # be strictly identical.
            full_diff = sorted(
                (set(map_1) ^ set(map_2))
                | {key for key in set(map_1) & set(map_2) if map_1[key] != map_2[key]})
            artifact_diff = [key for key in full_diff if key != manifest_rel]
            stable_1 = _manifest_stable(manifests[0])
            stable_2 = _manifest_stable(manifests[1])
            differing_keys = sorted(key for key in set(manifests[0]) | set(manifests[1])
                                    if manifests[0].get(key) != manifests[1].get(key))
            if artifact_diff or stable_1 != stable_2 or not set(full_diff) <= {manifest_rel}:
                record["dual_run"] = {
                    "runs": 2, "byte_identical": False,
                    "artifact_differences": artifact_diff,
                    "full_file_map_differences": full_diff,
                    "manifest_differing_keys": differing_keys,
                    "manifest_volatile_keys_excluded": list(MANIFEST_VOLATILE_KEYS),
                }
                raise Anomaly("The two clean runs are NOT byte-identical: "
                              f"artifact_differences={artifact_diff}, "
                              f"full_file_map_differences={full_diff}, "
                              f"manifest_differing_keys={differing_keys}")
            leakage_hits = _outputs_leakage_hits(
                self.candidates_root / "baseline-establish-2/workspace/"
                "study_files/outputs/study_v1_reproduction")
            if leakage_hits:
                raise Anomaly(f"Outcome-derived leakage tokens in baseline outputs: {leakage_hits}")

            source_path = self.root / "study_files/backend/demand_zone_study_v1.py"
            suite_path = self.root / "study_files/backend/tests/test_demand_zone_study_v1.py"
            protocol_path = self.root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"
            sanitized = read_json(
                self.root / "study_files/research/demand-zone-ai-study/run_manifest_sanitized.json", {}) or {}
            ohlcv_dir = self.root / "study_files/outputs/v2/_ohlcv"
            ohlcv_hashes = {path.stem: sha256_file(path) for path in sorted(ohlcv_dir.glob("*.csv"))}
            pinned_sources = sanitized.get("source_data_sha256") or {}
            mismatches = sorted(symbol for symbol, digest in pinned_sources.items()
                                if ohlcv_hashes.get(symbol) != digest)
            roster_path = self.root / "study_files/outputs/v2/demand_zone_v2_dataset.csv"
            manifest_path = self.root / "study_files/outputs/study_v1/development/run_manifest.json"
            record.update({
                "source": {"path": "study_files/backend/demand_zone_study_v1.py",
                           "sha256": sha256_file(source_path),
                           "bytes": source_path.stat().st_size},
                "test_suite": {"path": "study_files/backend/tests/test_demand_zone_study_v1.py",
                               "sha256": sha256_file(suite_path)},
                "protocol": {"path": "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",
                             "sha256": sha256_file(protocol_path),
                             "version": manifests[0].get("protocol_version")},
                "inputs": {
                    "v1_run_manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
                    "v2_roster_dataset_sha256": sha256_file(roster_path) if roster_path.is_file() else None,
                    "universe_sha256": manifests[0].get("universe_sha256"),
                    "ohlcv_count": len(ohlcv_hashes),
                    "ohlcv_source_data_sha256": ohlcv_hashes,
                    "ohlcv_matches_sanitized_pins": (not mismatches
                                                     and len(ohlcv_hashes) == len(pinned_sources)),
                    "ohlcv_mismatches": mismatches,
                    "v1_0_1_source_pin_sha256": PIN_CODE_SHA256_V1_0_1,
                },
                "outputs": {
                    "artifact_files_sha256": map_1,
                    "artifact_sha256": manifests[0].get("artifact_sha256"),
                    "model_artifacts_sha256": manifests[0].get("model_artifacts_sha256"),
                    "pooled_oof_metrics": manifests[0].get("pooled_oof_metrics"),
                    "feature_arms": manifests[0].get("feature_arms"),
                    "protocol_sha256": manifests[0].get("protocol_sha256"),
                    "universe_sha256": manifests[0].get("universe_sha256"),
                    "run_manifest_sha256": [row["run_manifest_sha256"] for row in runs_log],
                },
                "models": sorted((manifests[0].get("model_artifacts_sha256") or {}).keys()),
                "dual_run": {"runs": 2, "byte_identical": True,
                             "artifact_files_compared": len(map_1),
                             "artifact_byte_equality": "strict",
                             "manifest_compared_by": "stable fields; volatile keys excluded",
                             "full_file_map_differences": full_diff,
                             "manifest_stable_fields_equal": True,
                             "manifest_volatile_keys_excluded": list(MANIFEST_VOLATILE_KEYS),
                             "manifest_differing_keys": differing_keys},
                "tests": {"study_unit_tests": {"passed": True, "runs": 2,
                                               "per_run": [row["commands"][0] for row in runs_log]}},
                "leakage": {"status": "PASS", "tokens_checked": list(LEAKAGE_TOKENS), "hits": []},
                "holdout": {"status": "SEALED", "uses": 0,
                            "detail": verification["sealed_holdout"]["detail"]},
                "pipeline_fingerprint": self.pipeline_fingerprint(verification),
                "environment": _environment_info(),
                "git": _git_identity(self.root),
                "commands": {entry["role"]: entry["argv"]
                             for entry in runs_log[0]["commands"]},
                "known_limitations": [
                    RECONSTRUCTED_STATEMENT,
                    "The implementation differs from historical V1.0.1 with 49 known "
                    "feature-column differences (rsi14, atr_pct, zone_width_pct, 14 zone-base "
                    "and 32 order-block features); see autonomous_agent/state/"
                    "baseline_reproduction.json drift record.",
                    "Outputs are retrospective development artifacts; the final holdout "
                    "remains sealed and no prospective claim exists.",
                ],
                "feature_drift_vs_v1_0_1": {
                    "columns": 49,
                    "families": {"rsi14": 1, "atr_pct": 1, "zone_width_pct": 1,
                                 "zone_base_*": 14, "order_block_*": 32},
                    "historical_drift_keys": (historical_state.get("reproduction") or {}).get("drift") or [],
                    "source": "autonomous_agent/state/baseline_reproduction.json",
                },
                "self_reproduction": {"byte_identical": True, "runs": 2,
                                      "verified_at": utc_now(),
                                      "artifact_files_compared": len(map_1)},
                "immutable_provenance": {
                    "registry": "autonomous_agent/state/baseline_registry.json",
                    "append_only": True,
                    "historical_record_path": "autonomous_agent/state/baseline_reproduction.json",
                },
            })
            record["status"] = "ESTABLISHED"
        except Exception as error:  # noqa: BLE001 - evidence tooling
            record["status"] = "FAILED"
            record["error"] = f"{type(error).__name__}: {error}"
            record["workspaces_preserved_for_inspection"] = True
        current_bytes = self.baseline_state_path.read_bytes() if self.baseline_state_path.is_file() else None
        record["historical_record_unchanged"] = current_bytes == historical_bytes
        self._write_establish_report(record)
        append_jsonl(self.journal_path, {"event": "establish_baseline", "baseline_id": baseline_id,
                                        "status": record["status"], "at": utc_now()})
        if record["status"] == "ESTABLISHED":
            registry.append(record)
        return record

    def _write_establish_report(self, record: Mapping[str, Any]) -> None:
        lines = [
            "# Baseline Establishment Report (Reconstructed Track)", "",
            f"Baseline: `{record.get('baseline_id')}` — status `{record.get('status')}`", "",
            f"> **{RECONSTRUCTED_STATEMENT}**", "",
            "The historical V1.0.1 reproduction record remains ",
            "`autonomous_agent/state/baseline_reproduction.json` (FAILED/BLOCKED) and was not modified.",
            "",
            f"- **Historical record unchanged:** `{record.get('historical_record_unchanged')}`",
            f"- **Lineage:** `{json.dumps(record.get('lineage', {}), sort_keys=True)}`",
            f"- **Source:** `{json.dumps(record.get('source', {}), sort_keys=True)}`",
            f"- **Test suite:** `{json.dumps(record.get('test_suite', {}), sort_keys=True)}`",
            f"- **Protocol:** `{json.dumps(record.get('protocol', {}), sort_keys=True)}`",
            f"- **Dual run:** `{json.dumps(record.get('dual_run', {}), sort_keys=True)}`",
            f"- **Leakage:** `{json.dumps(record.get('leakage', {}), sort_keys=True)}`",
            f"- **Holdout:** `{json.dumps(record.get('holdout', {}), sort_keys=True)}`",
            f"- **Pipeline fingerprint:** `{record.get('pipeline_fingerprint')}`",
            f"- **Self-reproduction:** `{json.dumps(record.get('self_reproduction', {}), sort_keys=True)}`",
            "",
            "## Known limitations", "",
        ]
        for limitation in record.get("known_limitations") or []:
            lines.append(f"- {limitation}")
        if record.get("error"):
            lines += ["", "## Discrepancy", "", f"`{record['error']}`", ""]
        (self.root / "autonomous_agent/BASELINE_RECONSTRUCTED_REPORT.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # --- Phase 3/6/8/11: candidate experiment ------------------------------
    def run_experiment(self, spec: ExperimentSpec) -> ExperimentResult:
        """Run one candidate end-to-end. Never raises: anomalies reject and destroy."""
        from autonomous_agent.campaign5_authorization import check_campaign5_authorization
        campaign_id = (spec.provenance.get("campaign_id")
                       if isinstance(spec.provenance, dict) else None)
        active_campaign = read_json(
            self.root / "autonomous_agent/state/campaign_config.json", {}) or {}
        active_campaign_id = active_campaign.get("campaign_id")
        execution_campaign_id = (active_campaign_id
                                 if isinstance(active_campaign_id, str)
                                 and active_campaign_id.startswith("campaign-5")
                                 else campaign_id)
        if (isinstance(execution_campaign_id, str)
                and execution_campaign_id.startswith("campaign-5")
                and campaign_id and campaign_id != execution_campaign_id):
            preflight = {"allowed": False, "reason_codes": ["campaign_identity_mismatch"]}
        else:
            preflight = check_campaign5_authorization(
                self.root, {"campaign_id": execution_campaign_id,
                            **{key: active_campaign[key] for key in
                               ("protocol_id", "protocol_version", "protocol_sha256",
                                "authorization_scope") if key in active_campaign}},
                active_campaign.get("authorization_scope")
                if isinstance(active_campaign, dict) else None)
        safe_id = _safe_experiment_id(getattr(spec, "experiment_id", ""))
        if not preflight["allowed"]:
            result = ExperimentResult(
                experiment_id=str(getattr(spec, "experiment_id", "")) or "invalid-spec",
                status="BLOCKED", blockers=list(preflight["reason_codes"]),
                error={"message": "Campaign 5 authorization preflight blocked execution.",
                       "reason_codes": list(preflight["reason_codes"])},
                acceptance_recommendation="REJECT")
            candidate_dir = self.candidates_root / safe_id
            candidate_dir.mkdir(parents=True, exist_ok=True)
            write_json_atomic(candidate_dir / "result.json", result.to_dict())
            return result
        candidate_dir = self.candidates_root / safe_id
        workspace = candidate_dir / "workspace"
        result = ExperimentResult(
            experiment_id=str(getattr(spec, "experiment_id", "")) or "invalid-spec",
            status="FAILED",
            candidate_version=None,
            acceptance_recommendation="REJECT",
        )
        original_hash: str | None = None
        started = time.monotonic()
        runs: list[CommandRun] = []
        try:
            spec.validate()
            registry = hardening.SpecRegistry(self.state_root)
            allowed, registry_reason = registry.check(spec.to_dict())
            if not allowed:
                result.status = "BLOCKED"
                result.blockers = [registry_reason]
                result.error = {"message": registry_reason}
                result.acceptance_recommendation = "REJECT"
                return result
            registry.record(spec.to_dict(), safe_id, utc_now())
            result.candidate_version = f"{spec.parent_version}-candidate"
            original_hash = self.original_fingerprint(
                progress_callback=self._fingerprint_heartbeat("experiment_pre"))
            baseline_id, baseline, baseline_reasons = self.experiment_baseline()
            if baseline_id is None:
                result.status = "BLOCKED"
                result.blockers = list(baseline_reasons) or [
                    "No experiment baseline is established; candidate experiments are prohibited."]
                result.error = {"message": result.blockers[0],
                                "baseline": (baseline or {}).get("status")}
                result.runtime = {"baseline_status": (baseline or {}).get("status"),
                                  "baseline_reasons": list(baseline_reasons)}
                result.acceptance_recommendation = "STOP_AUTONOMOUS_EXPERIMENTATION"
                return result
            if spec.baseline_id and spec.baseline_id != baseline_id:
                result.status = "BLOCKED"
                result.blockers = [f"Spec baseline_id {spec.baseline_id!r} does not match the "
                                   f"active experiment baseline {baseline_id!r}."]
                result.error = {"message": result.blockers[0]}
                result.acceptance_recommendation = "REJECT"
                return result
            result.baseline_id = baseline_id
            workspace = self._prepare_workspace(spec, candidate_dir)
            write_json_atomic(candidate_dir / "spec.json", spec.to_dict())
            inputs_before = self._workspace_inputs_fingerprint(workspace)
            runs.append(self._run_role(spec, workspace, "unit_tests"))
            runs.append(self._run_role(spec, workspace, "experiment"))
            inputs_after = self._workspace_inputs_fingerprint(workspace)
            integrity_ok = inputs_before == inputs_after
            evaluation = read_json(workspace / "outputs/evaluation.json", None)
            holdout_dir = workspace / "study_files/outputs/study_v1/prospective"
            holdout_touched = holdout_dir.exists()
            checks, decision, reasons, metrics = self.evaluate(
                spec, runs, evaluation if isinstance(evaluation, dict) else None,
                integrity_ok=integrity_ok, holdout_touched=holdout_touched)
            result.checks = checks
            result.metrics = metrics
            result.leakage_status = checks.get("leakage", "NOT_RUN")
            result.robustness_status = checks.get("robustness", "NOT_RUN")
            result.holdout_status = "TOUCHED" if holdout_touched else "SEALED"
            result.runtime = {
                "baseline_id": baseline_id,
                "total_seconds": round(time.monotonic() - started, 3),
                "commands": [run.to_dict() for run in runs],
            }
            if holdout_touched:
                result.error = {"message": "Final holdout access is prohibited; candidate rejected."}
            if decision == "ACCEPT":
                _strip_bytecode(workspace)
                result.status = "ACCEPTED"
                result.acceptance_recommendation = "PROMOTE"
                result.candidate_path = str(workspace)
                result.release_metadata = dict((evaluation or {}).get("release_metadata") or {})
                result.reproduction_command = result.release_metadata.get("reproduction_command")
                result.artifacts = self._collect_artifacts(workspace)
            else:
                result.status = "REJECTED"
                result.acceptance_recommendation = "REJECT"
                result.error = {"message": "; ".join(reasons) or "Candidate failed one or more mandatory gates."}
        except Exception as error:  # Phase 11: any anomaly rejects and destroys
            result.status = "REJECTED"
            result.error = {"message": f"{type(error).__name__}: {error}",
                            "traceback": traceback.format_exc(limit=10)}
            result.acceptance_recommendation = "REJECT"
        finally:
            if result.status != "ACCEPTED":
                self.destroy_candidate(workspace)
            if original_hash is not None:
                try:
                    self.assert_original_unchanged(
                        original_hash,
                        progress_callback=self._fingerprint_heartbeat(
                            "experiment_post"))
                except Anomaly as error:
                    result.status = "REJECTED"
                    result.acceptance_recommendation = "REJECT"
                    result.error = {"message": str(error)}
                    self.destroy_candidate(workspace)
            write_json_atomic(candidate_dir / "result.json", result.to_dict())
            append_jsonl(self.journal_path, {"event": "experiment_finished",
                                            "experiment_id": result.experiment_id,
                                            "status": result.status, "at": utc_now()})
        return result

    def _workspace_inputs_fingerprint(self, workspace: Path) -> str:
        """Hash everything in the workspace the candidate is NOT allowed to change."""
        digest = hashlib.sha256()
        for path in sorted(workspace.rglob("*")):
            relative = path.relative_to(workspace).as_posix()
            if relative.split("/", 1)[0] == "outputs" or relative.startswith("autonomous_agent/experiments"):
                continue
            if path.is_file():
                digest.update(relative.encode("utf-8"))
                digest.update(bytes.fromhex(sha256_file(path)))
        return digest.hexdigest()

    def _collect_artifacts(self, workspace: Path) -> dict[str, Any]:
        artifacts: dict[str, Any] = {"tree_sha256": tree_sha256(workspace)}
        outputs = workspace / "outputs"
        if outputs.is_dir():
            for path in sorted(outputs.rglob("*")):
                if path.is_file():
                    artifacts[path.relative_to(workspace).as_posix()] = sha256_file(path)
        return artifacts


def _safe_experiment_id(value: Any) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    if isinstance(value, str) and value not in {"", ".", ".."} and all(ch in allowed for ch in value):
        return value
    return "invalid-spec"


def _strip_bytecode(workspace: Path) -> None:
    """Keep accepted snapshots byte-stable for the version manager's tree hash."""
    for path in sorted(workspace.rglob("__pycache__"), reverse=True):
        shutil.rmtree(path, ignore_errors=True)
    for path in sorted(workspace.rglob("*.pyc"), reverse=True):
        try:
            path.unlink()
        except OSError:
            pass


def _stdout_from_expired(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _collect_artifact_map(artifact_dir: Path) -> dict[str, str]:
    """sha256 of every file under a run's artifact directory (relative -> hash)."""
    mapping: dict[str, str] = {}
    if not artifact_dir.is_dir():
        return mapping
    for path in sorted(artifact_dir.rglob("*")):
        if path.is_file():
            mapping[path.relative_to(artifact_dir).as_posix()] = sha256_file(path)
    return mapping


def _manifest_stable(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Manifest without the volatile keys allowed to differ across clean runs."""
    return {key: value for key, value in manifest.items() if key not in MANIFEST_VOLATILE_KEYS}


def _outputs_leakage_hits(artifact_dir: Path) -> list[str]:
    """Outcome-derived tokens must never appear in produced output columns/keys."""
    hits: set[str] = set()
    if not artifact_dir.is_dir():
        return []
    for path in sorted(artifact_dir.rglob("*.csv")):
        with path.open("r", encoding="utf-8", errors="replace", newline="") as stream:
            header = next(csv.reader(stream), [])
        for column in header:
            for token in LEAKAGE_TOKENS:
                if token in (column or "").lower():
                    hits.add(f"{path.name}:{column}")
    for path in sorted(artifact_dir.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for key in _iter_keys(payload):
            for token in LEAKAGE_TOKENS:
                if token in key.lower():
                    hits.add(f"{path.name}:{key}")
    return sorted(hits)


def _manifest_drift(archived: Mapping[str, Any], produced: Mapping[str, Any],
                    *, expected_archived_protocol: str | None = None,
                    expected_produced_protocol: str | None = None) -> list[str]:
    drift: list[str] = []
    for key in ("protocol_sha256", "universe_sha256", "artifact_sha256", "pooled_oof_metrics"):
        if archived.get(key) == produced.get(key):
            continue
        if key == "protocol_sha256" and expected_archived_protocol and expected_produced_protocol:
            # Documented cross-version provenance: the immutable v1.0.1 archive
            # pinned the protocol file as it existed then (v1.0.1), while any
            # reproduction run pins the current frozen protocol file (v1.0.2);
            # the two files legitimately differ. Accept only when BOTH sides
            # match their own pinned expected hashes; all other keys must be
            # strictly equal.
            if (archived.get(key) == expected_archived_protocol
                    and produced.get(key) == expected_produced_protocol):
                continue
        drift.append(key)
    return drift


def _git_identity(root: Path) -> dict[str, Any]:
    identity: dict[str, Any] = {"sha": None, "branch": None, "dirty": None}

    def _run(args: list[str]) -> str | None:
        try:
            completed = subprocess.run(args, cwd=str(root), capture_output=True, text=True,
                                       encoding="utf-8", errors="replace", timeout=10)
        except (OSError, subprocess.SubprocessError):
            return None
        return completed.stdout.strip() if completed.returncode == 0 else None

    identity["sha"] = _run(["git", "rev-parse", "HEAD"])
    identity["branch"] = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    status = _run(["git", "status", "--porcelain"])
    if status is not None:
        identity["dirty"] = bool(status.strip())
    return identity


def _environment_info() -> dict[str, Any]:
    info: dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "executable": sys.executable,
        "adapter_version": AGENT_ADAPTER_VERSION,
    }
    try:
        from importlib.metadata import version
        for package in ("numpy", "pandas", "scikit-learn", "lightgbm", "joblib", "xgboost", "catboost"):
            try:
                info[package] = version(package)
            except Exception:
                info[package] = "not installed"
    except Exception:
        pass
    return info


# ---------------------------------------------------------------------------
# Supervisor integration (Phases 6/10)
# ---------------------------------------------------------------------------

def build_experiment_runner(
    adapter: ExperimentAdapter,
    spec_provider: Callable[[Hypothesis, PrerequisiteReport], ExperimentSpec] | None = None,
) -> Callable[[Hypothesis, PrerequisiteReport], dict[str, Any]]:
    """Return a runner matching ``Supervisor(experiment_runner=...)``.

    The runner always attempts the Phase 5 baseline reproduction first. While
    reproduction is not REPRODUCED every attempt is refused (recorded as a
    rejection with the exact blockers) and no candidate is created. Candidate
    specs must come from a reviewed provider -- the agent never invents random
    code mutations.
    """
    def run(hypothesis: Hypothesis, report: PrerequisiteReport) -> dict[str, Any]:
        baseline_id, baseline, baseline_reasons = adapter.experiment_baseline()
        if baseline_id is None:
            return ExperimentResult(
                experiment_id="baseline-gate", status="REJECTED",
                error={"message": "No experiment baseline is established; candidate experiments "
                                  "are prohibited. The historical V1.0.1 reproduction is a "
                                  "separate, currently non-reproduced track.",
                       "baseline": (baseline or {}).get("status")},
                blockers=list(baseline_reasons),
                acceptance_recommendation="STOP_AUTONOMOUS_EXPERIMENTATION",
            ).to_supervisor_outcome()
        if spec_provider is None:
            return ExperimentResult(
                experiment_id="pending-candidate", status="REJECTED",
                error={"message": "No reviewed ExperimentSpec provider is registered; "
                                   "random code mutations are prohibited."},
                acceptance_recommendation="REJECT",
            ).to_supervisor_outcome()
        try:
            spec = spec_provider(hypothesis, report)
            return adapter.run_experiment(spec).to_supervisor_outcome()
        except Exception as error:
            return ExperimentResult(
                experiment_id="candidate", status="REJECTED",
                error={"message": f"{type(error).__name__}: {error}"},
                acceptance_recommendation="REJECT",
            ).to_supervisor_outcome()
    return run


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Research input verification and baseline reproduction.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify_parser = subparsers.add_parser("verify-inputs", help="Verify required research inputs (read-only).")
    verify_parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    reproduce_parser = subparsers.add_parser("reproduce", help="Attempt the baseline reproduction run.")
    reproduce_parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    reproduce_parser.add_argument("--force", action="store_true")
    establish_parser = subparsers.add_parser(
        "establish-baseline",
        help="Establish the reconstructed active baseline via two clean byte-identical runs.")
    establish_parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    establish_parser.add_argument("--baseline-id", default=DEFAULT_ESTABLISHED_BASELINE_ID)
    args = parser.parse_args(list(argv) if argv is not None else None)

    adapter = ExperimentAdapter(root=args.root)
    if args.command == "verify-inputs":
        print(json.dumps(adapter.verify_inputs(), indent=2, sort_keys=True))
        return 0
    if args.command == "establish-baseline":
        record = adapter.run_establish_baseline(baseline_id=args.baseline_id)
        print(json.dumps(record, indent=2, sort_keys=True, default=str))
        return 0 if record.get("status") == "ESTABLISHED" else 4
    result = adapter.run_reproduction(force=args.force)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True, default=str))
    return {"REPRODUCED": 0, "BLOCKED": 3, "FAILED": 4}.get(result.status, 5)


if __name__ == "__main__":
    raise SystemExit(main())
