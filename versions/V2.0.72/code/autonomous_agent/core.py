"""Safe orchestration for autonomous, evidence-gated research.

This module deliberately does not execute project training scripts, edit arbitrary
source, load serialized models, access networks, or touch brokerage systems. A
research adapter can be added only after its inputs and evaluation contract have
been independently verified. In the current repository the adapter is blocked:
there is no clean, reproducible champion or frozen-study input data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import sys
import time
import traceback
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


try:
    from autonomous_agent.baseline_registry import (
        PIN_V1_0_1_CODE_SHA256,
        RECONSTRUCTED_STATEMENT,
        BaselineRegistry,
        validate_established_record,
    )
except ImportError:  # direct module execution
    from baseline_registry import (  # type: ignore
        PIN_V1_0_1_CODE_SHA256,
        RECONSTRUCTED_STATEMENT,
        BaselineRegistry,
        validate_established_record,
    )

AGENT_VERSION = "0.2.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = PROJECT_ROOT / "autonomous_agent" / "state"

# A validated champion requires every field and explicit evidence. Historical
# README metrics are not enough to satisfy these fields.
CHAMPION_FIELDS = (
    "code_revision", "dataset_id", "dataset_sha256", "feature_set",
    "model", "target_definition", "training_period", "validation_period",
    "research_test_period", "holdout_policy", "metrics", "backtest",
    "leakage_status", "known_limitations", "reproduction_command",
    # Every champion is explicitly scoped to an experiment baseline.
    "baseline_id", "baseline_kind", "lineage",
)

# Additional provenance required only for champions scoped to a reconstructed
# baseline. These fields pin the champion to BASELINE_RECONSTRUCTED_2026_10's
# evidence and make a V1.0.1 reproduction claim impossible to express.
RECONSTRUCTED_CHAMPION_FIELDS = (
    "v1_0_1_status", "historical_v1_0_1_sha256", "reconstructed_source_sha256",
    "self_reproduction", "pipeline_fingerprint", "validation_scope", "created_at",
)

RECONSTRUCTED_SCOPE_MARKER = "NOT a reproduction of V1.0.1"


@dataclass(frozen=True)
class Hypothesis:
    direction: str
    question: str
    rationale: str
    experiment: str
    required_inputs: tuple[str, ...]
    priority: float


@dataclass(frozen=True)
class PrerequisiteReport:
    ready: bool
    reasons: tuple[str, ...]
    champion_id: str | None
    hypothesis: Hypothesis | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    """Hash a candidate tree deterministically, including relative paths."""
    digest = hashlib.sha256()
    entries = sorted(path.rglob("*"))
    if any(item.is_symlink() for item in entries):
        raise ValueError("Candidate trees may not contain symlinks.")
    for file_path in (item for item in entries if item.is_file()):
        relative = file_path.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(sha256_file(file_path)))
    return digest.hexdigest()


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "agent_version": AGENT_VERSION,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "champion": None,
        # Never infer the next release number until a reproducible champion exists.
        "next_patch": None,
        "version_baseline": None,
        "active_baseline_id": None,
        "holdout": {"status": "sealed", "uses": 0, "policy": "Do not access for research tuning; no approved final evaluation run."},
        "experiments": [],
        "direction_stats": {},
        "consecutive_rejections": 0,
        "stagnation_mode": False,
        "last_error": None,
    }


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def parse_champion(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.exists():
        return None, ["No champion manifest exists; historical version labels are not sufficient proof."]
    try:
        with path.open("r", encoding="utf-8") as stream:
            champion = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"Champion manifest cannot be read: {error}"]
    if not isinstance(champion, dict):
        return None, ["Champion manifest must contain a JSON object."]
    missing = [key for key in CHAMPION_FIELDS if champion.get(key) in (None, "", [], {})]
    if missing:
        return None, [f"Champion manifest is incomplete: {', '.join(missing)}."]
    if champion.get("leakage_status") != "PASS":
        return None, ["Champion leakage status is not PASS."]
    baseline_kind = champion.get("baseline_kind")
    if baseline_kind not in ("reconstructed_baseline", "historical_reproduction"):
        return None, ["Champion must declare baseline_kind as 'reconstructed_baseline' or "
                      "'historical_reproduction'."]
    if not isinstance(champion.get("baseline_id"), str) or not champion["baseline_id"]:
        return None, ["Champion must be explicitly scoped to a baseline_id."]
    lineage = champion.get("lineage")
    if not isinstance(lineage, dict) or not lineage.get("relation"):
        return None, ["Champion must carry a lineage block stating its relation."]
    if baseline_kind == "reconstructed_baseline":
        missing = [key for key in RECONSTRUCTED_CHAMPION_FIELDS
                   if champion.get(key) in (None, "", [], {})]
        if missing:
            return None, [f"Reconstructed-baseline champion is missing: {', '.join(missing)}."]
        if champion.get("validation_status") != "SELF_REPRODUCED":
            return None, ["Reconstructed-baseline champions require validation_status "
                          "'SELF_REPRODUCED'; V1.0.1 reproduction claims are prohibited."]
        if champion.get("v1_0_1_status") != "FAILED":
            return None, ["Reconstructed-baseline champions must preserve v1_0_1_status == "
                          "'FAILED'; relabeling the historical verdict is prohibited."]
        if champion.get("historical_v1_0_1_sha256") != PIN_V1_0_1_CODE_SHA256:
            return None, ["Champion must preserve the original historical V1.0.1 SHA-256 pin."]
        if lineage.get("relation") != "reconstruction":
            return None, ["Champion lineage must state relation == 'reconstruction'."]
        self_reproduction = champion.get("self_reproduction")
        if not isinstance(self_reproduction, dict) or self_reproduction.get("byte_identical") is not True:
            return None, ["Champion requires valid self-reproduction evidence (byte_identical)."]
        if RECONSTRUCTED_SCOPE_MARKER not in str(champion.get("validation_scope", "")):
            return None, [f"Champion validation_scope must explicitly state: {RECONSTRUCTED_SCOPE_MARKER}."]
    else:  # historical_reproduction
        if champion.get("validation_status") != "REPRODUCED":
            return None, ["Historical-reproduction champions require validation_status 'REPRODUCED'."]
        if champion.get("v1_0_1_status") == "FAILED":
            return None, ["A historical-reproduction champion cannot carry v1_0_1_status 'FAILED'."]
    holdout_policy = champion.get("holdout_policy")
    if not isinstance(holdout_policy, dict) or holdout_policy.get("status") != "SEALED":
        return None, ["A sealed final-holdout policy is required."]
    if not isinstance(champion.get("version"), str) or not champion["version"].startswith("V"):
        return None, ["Champion version identity is invalid."]
    if not isinstance(champion.get("metrics"), dict) or not isinstance(champion.get("backtest"), dict):
        return None, ["Champion metrics and backtest must be structured evidence records."]
    if not isinstance(champion.get("known_limitations"), list):
        return None, ["Champion known limitations must be recorded as a list."]
    if not isinstance(champion.get("feature_set"), list) or not champion["feature_set"]:
        return None, ["Champion feature set must be a non-empty explicit list."]
    return champion, []


class ResearchPlanner:
    """Rank research questions from repository findings and accumulated outcomes.

    The planner proposes questions only. It will not modify source or invent
    test results. Directions are interpreted from observed evidence signals,
    then diversified by normalized historical success and recency.
    """

    BASE_DIRECTIONS = (
        Hypothesis("data_quality", "Are the available inputs point-in-time and complete enough for a valid comparison?",
                   "Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.",
                   "Verify source vintage, universe membership, timestamps, and target maturity before modeling.",
                   ("point_in_time_source_data", "point_in_time_universe", "matured_labels"), 1.0),
        Hypothesis("validation", "Would stronger purging and independent time-block inference change the ranking of feature arms?",
                   "The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.",
                   "Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.",
                   ("frozen_protocol_inputs", "reproducible_feature_builder", "research_folds"), 0.99),
        Hypothesis("feature_engineering", "Do market-structure features add information beyond a matched baseline without future-data dependence?",
                   "The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.",
                   "Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.",
                   ("frozen_protocol_inputs", "matched_event_cohort", "fold_local_preprocessing"), 0.92),
        Hypothesis("calibration", "Are probability estimates stable across years, tickers, and market regimes?",
                   "Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.",
                   "Evaluate calibration and subgroup reliability on untouched chronological research folds.",
                   ("reproducible_oof_predictions", "ticker_and_regime_metadata"), 0.82),
        Hypothesis("error_analysis", "Are errors concentrated by time, ticker, volatility regime, or prediction confidence?",
                   "The project has substantial history, but current audited artifacts do not establish robust error slices.",
                   "Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.",
                   ("reproducible_oof_predictions", "timestamped_market_context"), 0.78),
        Hypothesis("model_complexity", "Can the model be simplified without sacrificing stable out-of-sample performance?",
                   "The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.",
                   "Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.",
                   ("frozen_protocol_inputs", "fixed_seed_policy", "matched_event_cohort"), 0.72),
        Hypothesis("target_design", "Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?",
                   "V2–V10 used different target definitions and AUC alone does not establish utility or profitability.",
                   "First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.",
                   ("point_in_time_source_data", "predeclared_target_protocol", "realistic_cost_model"), 0.65),
        Hypothesis("model_architecture", "Does a different model class generalize better than the strongest matched component?",
                   "Historical architecture results are not comparable across changing datasets and labels.",
                   "Compare model classes under one fixed cohort, target, feature contract, and chronological folds.",
                   ("frozen_protocol_inputs", "fold_local_preprocessing", "fixed_seed_policy"), 0.60),
    )

    def __init__(self, memory_path: Path):
        self.memory_path = memory_path

    def plan(self, state: dict[str, Any],
             allowed_directions: Iterable[str] | None = None) -> Hypothesis:
        memory = read_json(self.memory_path, {"schema_version": 1, "discoveries": []})
        discoveries = memory.get("discoveries", [])
        stats = state.get("direction_stats", {})
        blocked_directions = {
            item.get("direction") for item in discoveries
            if item.get("status") == "BLOCKED" and item.get("permanent", False)
        }
        eligible = [h for h in self.BASE_DIRECTIONS if h.direction not in blocked_directions]
        if allowed_directions is not None:
            # Caller-declared capacity filter (e.g. the closed recipe library's
            # remaining generation capacity): never propose a direction that is
            # permanently unsupported or out of attempt budget while another
            # viable direction exists.
            allowed = set(allowed_directions)
            viable = [h for h in eligible if h.direction in allowed]
            if viable:
                eligible = viable
        if not eligible:
            eligible = list(self.BASE_DIRECTIONS)

        def score(hypothesis: Hypothesis) -> tuple[float, float, str]:
            outcome = stats.get(hypothesis.direction, {})
            attempts = int(outcome.get("attempts", 0))
            accepted = int(outcome.get("accepted", 0))
            # Lightweight UCB-style exploration; does not reward raw noisy metric deltas.
            success_rate = accepted / attempts if attempts else 0.5
            exploration = 0.02 / (attempts + 1)
            blocked = int(outcome.get("blocked", 0))
            discovery_count = sum(1 for item in discoveries if item.get("direction") == hypothesis.direction)
            stagnation_bonus = 0.3 if state.get("stagnation_mode") and hypothesis.direction in {"target_design", "validation", "data_quality", "model_architecture"} else 0.0
            # Rotate away from directions that cannot be investigated under the
            # current missing-input state; blocked is not treated as model failure.
            readiness_penalty = 10.0 * max(blocked, discovery_count)
            return (hypothesis.priority + 0.18 * success_rate + 0.08 * exploration + stagnation_bonus - readiness_penalty, -attempts, hypothesis.direction)

        chosen = max(eligible, key=score)
        return chosen


def check_prerequisites(root: Path, state: dict[str, Any], planner: ResearchPlanner,
                        champion_path: Path | None = None, adapter_ready: bool = False,
                        state_root: Path | None = None,
                        allowed_directions: Iterable[str] | None = None) -> PrerequisiteReport:
    root = root.resolve()
    protocol = root / "study_files" / "MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"
    event_table = root / "study_files" / "outputs" / "study_v1" / "development" / "event_table.csv"
    source_data_candidates = [
        root / "outputs" / "v2" / "demand_zone_v2_dataset.csv",
        root / "outputs" / "v5" / "demand_zone_v5_dataset.csv",
        # Canonical study locations (study scripts resolve ROOT to study_files/).
        root / "study_files" / "outputs" / "v2" / "demand_zone_v2_dataset.csv",
        root / "study_files" / "outputs" / "v5" / "demand_zone_v5_dataset.csv",
    ]
    point_in_time_sources: list[Path] = []
    for ohlcv_cache in (root / "outputs" / "v2" / "_ohlcv",
                        root / "study_files" / "outputs" / "v2" / "_ohlcv"):
        if ohlcv_cache.is_dir():
            point_in_time_sources.extend(ohlcv_cache.glob("*.csv"))
    manifest_path = champion_path or (root / "CHAMPION.json")
    champion, reasons = parse_champion(manifest_path)
    if champion is None:
        # Detailed known project facts are intentionally explicit and machine-auditable.
        reasons.extend([
            "The retained v1.0.1 archive is not source/feature reproduced; scoped parity failed for rsi14, atr_pct, and zone_width_pct.",
            "The V2 roster dataset and the 153-symbol OHLCV source set are restored and hash-verified; the remaining blockers are baseline provenance, not missing inputs.",
            "The archived V1.0.1 scores are retrospective development results, not a clean current champion or prospective holdout.",
            "V2–V10 changed datasets, targets, features, or validation; their reported metrics are not a matched version ladder.",
        ])
    registry_root = Path(state_root) if state_root is not None else root / "autonomous_agent" / "state"
    if champion is not None and champion.get("baseline_kind") == "reconstructed_baseline":
        record = BaselineRegistry(registry_root).find(str(champion.get("baseline_id")))
        if record is None:
            reasons.append("Champion is scoped to a baseline_id that is not in the baseline registry.")
        else:
            record_reasons = validate_established_record(record)
            if record_reasons:
                reasons.extend(record_reasons)
            elif record.get("pipeline_fingerprint") != champion.get("pipeline_fingerprint"):
                reasons.append("Champion self-reproduction evidence does not match the registered "
                               "baseline record.")
    if not protocol.is_file():
        reasons.append("Frozen protocol file is missing.")
    if not event_table.is_file():
        reasons.append("Retained historical event table is missing.")
    if not any(path.is_file() for path in source_data_candidates):
        reasons.append("No V2/V5 row-level source dataset is present; local source/roster requirements cannot be reconstructed here.")
    if len(point_in_time_sources) < 153:
        reasons.append(f"The frozen study requires the historical 153-symbol OHLCV source set; found {len(point_in_time_sources)} CSVs.")
    if state.get("holdout", {}).get("status") != "sealed":
        reasons.append("Final holdout is not sealed; no research run may proceed.")
    if not adapter_ready:
        reasons.append("No reviewed project-specific experiment adapter is implemented; arbitrary scripts will not be executed.")
    hypothesis = planner.plan(state, allowed_directions=allowed_directions)
    return PrerequisiteReport(ready=not reasons, reasons=tuple(dict.fromkeys(reasons)),
                              champion_id=champion.get("version") if champion else None,
                              hypothesis=hypothesis)

def append_discovery(memory_path: Path, record: dict[str, Any]) -> None:
    memory = read_json(memory_path, {"schema_version": 1, "discoveries": []})
    discoveries = memory.setdefault("discoveries", [])
    experiment_id = record.get("experiment_id")
    if experiment_id and any(item.get("experiment_id") == experiment_id for item in discoveries):
        return
    discoveries.append(record)
    memory["updated_at"] = utc_now()
    write_json_atomic(memory_path, memory)


def prior_evidence(memory_path: Path, direction: str, limit: int = 3) -> list[dict[str, Any]]:
    """Lessons from earlier experiments in the same direction (dedupe grounding)."""
    discoveries = read_json(memory_path, {}).get("discoveries", [])
    return [
        {"experiment_id": item.get("experiment_id"), "status": item.get("status"),
         "lesson": item.get("lesson", "")}
        for item in discoveries if item.get("direction") == direction
    ][-limit:]


def build_research_record(experiment: Mapping[str, Any],
                          hypothesis: Hypothesis | None,
                          outcome: Mapping[str, Any] | None,
                          memory_path: Path) -> dict[str, Any]:
    """TASK 3 research record: hypothesis -> motivation -> evidence -> result -> next step."""
    hypothesis = hypothesis
    direction = experiment.get("direction", "unknown")
    status = experiment.get("status", "UNKNOWN")
    results = (outcome or {}).get("results") or experiment.get("results") or {}
    primary = results.get("primary_metric")
    if isinstance(primary, Mapping):
        actual = (f"status={status}; primary delta={primary.get('delta')}; "
                  f"decision_criteria_passed={results.get('decision_criteria_passed')}")
    else:
        actual = f"status={status}; {experiment.get('failure') or experiment.get('rejection_reason') or 'no metric summary recorded'}"
    evidence = prior_evidence(memory_path, direction)
    if status == "ACCEPTED":
        next_step = (f"Build on accepted direction {direction!r} from the new champion; "
                     "keep testing unresolved questions in other directions.")
    elif status == "BLOCKED":
        next_step = (f"Resolve prerequisite blockers before retrying direction {direction!r}; "
                     "this record is not evidence against the hypothesis.")
    else:
        next_step = (f"Direction {direction!r} did not clear the gates under this design; "
                     "change the design or pivot to a structural question rather than "
                     "making tiny variations.")
    return {
        "baseline_id": experiment.get("baseline_id"),
        "hypothesis": experiment.get("hypothesis", "not recorded"),
        "motivation": experiment.get("rationale") or (hypothesis.rationale if hypothesis else "not recorded"),
        "prior_evidence": evidence or ["no prior experiments in this direction"],
        "proposed_change": experiment.get("experiment_design") or (hypothesis.experiment if hypothesis else "not recorded"),
        "expected_outcome": (experiment.get("expected_outcome")
                             or "All predeclared acceptance criteria pass with a positive "
                                "primary-metric delta (see the experiment specification)."),
        "actual_result": actual,
        "conclusion": experiment.get("failure") or experiment.get("rejection_reason")
                      or "Candidate result recorded; review detailed evaluation artifacts.",
        "next_research_implication": next_step,
    }


def append_human_memory(path: Path, record: dict[str, Any]) -> None:
    """Append a concise, explicitly non-claim entry to the durable Markdown log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    heading = f"## {record.get('status', 'UNKNOWN')} {record.get('experiment_id', 'experiment')}"
    if path.exists() and heading in path.read_text(encoding="utf-8"):
        return
    entry = (
        f"\n{heading}"
        f" — {record.get('created_at', utc_now())}\n\n"
        f"- **Direction:** {record.get('direction', 'unknown')}\n"
        f"- **Hypothesis / question:** {record.get('question', 'not recorded')}\n"
        f"- **Motivation:** {record.get('motivation', 'not recorded')}\n"
        f"- **Prior evidence:** {record.get('prior_evidence', 'not recorded')}\n"
        f"- **Proposed change:** {record.get('proposed_change', 'not recorded')}\n"
        f"- **Expected outcome:** {record.get('expected_outcome', 'not recorded')}\n"
        f"- **Actual result:** {record.get('actual_result', 'not recorded')}\n"
        f"- **Conclusion:** {record.get('lesson', 'No evaluated lesson yet; this is not a scientific claim.')}\n"
        f"- **Next research implication:** {record.get('next_research_implication', 'not recorded')}\n"
        f"- **Scientific claim:** No\n"
    )
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(entry)
        stream.flush()
        os.fsync(stream.fileno())


class VersionManager:
    """Materialize an accepted candidate as an immutable local version snapshot."""

    VERSION_PATTERN = re.compile(r"^V(\d+)\.(\d+)\.(\d+)$")

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.versions_dir = self.root / "versions"

    @classmethod
    def next_version(cls, current: str) -> str:
        match = cls.VERSION_PATTERN.fullmatch(current)
        if not match:
            raise ValueError(f"Unrecognized champion version: {current!r}")
        major, minor, patch = map(int, match.groups())
        return f"V{major}.{minor}.{patch + 1}"

    def promote(self, champion: dict[str, Any], experiment: dict[str, Any], outcome: dict[str, Any]) -> Path:
        if experiment.get("status") != "ACCEPTED":
            raise ValueError("Only fully accepted candidates can be versioned.")
        self._validate_outcome(experiment, outcome)
        if champion.get("baseline_kind") == "reconstructed_baseline":
            match = self.VERSION_PATTERN.fullmatch(str(champion.get("version", "")))
            if not match or int(match.group(1)) < 2:
                raise ValueError("Reconstructed-baseline champions must use the V2+ version series; "
                                 "the historical V1.0.x ladder is reserved for the V1.0.1 "
                                 "reproduction lineage.")
        candidate = Path(outcome["candidate_path"]).resolve()
        sandbox_root = (self.root / "autonomous_agent" / "candidates").resolve()
        if not candidate.is_relative_to(sandbox_root) or not candidate.is_dir():
            raise ValueError("Candidate must be an existing directory inside the isolated agent candidate sandbox.")
        metadata = outcome.get("release_metadata")
        if not isinstance(metadata, dict):
            raise ValueError("Accepted release requires complete release_metadata.")
        required_metadata = ("dataset_id", "dataset_sha256", "feature_set", "model", "target_definition",
                             "training_period", "validation_period", "research_test_period", "metrics",
                             "backtest", "known_limitations", "reproduction_command")
        missing = [key for key in required_metadata if metadata.get(key) in (None, "", [], {})]
        if missing:
            raise ValueError(f"Release metadata missing: {', '.join(missing)}")
        # Re-check the parent at promotion time so stale in-memory state cannot
        # overwrite an independently advanced champion.
        current_champion, errors = parse_champion(self.root / "CHAMPION.json")
        if current_champion is None or current_champion.get("version") != champion.get("version"):
            raise ValueError("Champion changed or failed validation during this experiment; do not promote stale results. " + "; ".join(errors))
        version = self.next_version(champion["version"])
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        destination = self.versions_dir / version
        if destination.exists():
            raise FileExistsError(f"Immutable version already exists: {destination}")
        staging = self.versions_dir / f".{version}.{uuid.uuid4().hex}.tmp"
        staging.mkdir(parents=True)
        try:
            shutil.copytree(candidate, staging / "code", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
            snapshot_hash = tree_sha256(staging / "code")
            if tree_sha256(candidate) != snapshot_hash or outcome.get("artifact_sha256") != snapshot_hash:
                raise ValueError("Candidate artifact hash does not match the isolated code snapshot.")
            manifest = {
                "version": version,
                "parent_champion": champion["version"],
                "baseline_id": champion.get("baseline_id"),
                "baseline_kind": champion.get("baseline_kind"),
                "created_at": utc_now(),
                "experiment_id": experiment["id"],
                "hypothesis": experiment["hypothesis"],
                "release_metadata": metadata,
                "evaluation": outcome,
                "holdout_touched": False,
                "artifact_sha256": snapshot_hash,
                "reproduction_command": metadata["reproduction_command"],
            }
            write_json_atomic(staging / "parent_champion.json", champion)
            write_json_atomic(staging / "evaluation.json", outcome)
            write_json_atomic(staging / "version.json", manifest)
            version_changelog = (
                f"# {version}\n\n## Hypothesis\n\n{experiment['hypothesis']}\n\n"
                f"## Changes and results\n\nSee `version.json` and `evaluation.json` for the immutable code/config, "
                f"data fingerprints, metrics, robustness gates, and reproduction command.\n\n"
                f"## Decision\n\nACCEPTED relative to {champion['version']}; all required checks passed.\n"
            )
            (staging / "CHANGELOG.md").write_text(version_changelog, encoding="utf-8")
            os.replace(staging, destination)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        new_champion = {
            "version": version,
            "code_revision": tree_sha256(destination / "code"),
            "dataset_id": metadata["dataset_id"],
            "dataset_sha256": metadata["dataset_sha256"],
            "feature_set": metadata["feature_set"],
            "model": metadata["model"],
            "target_definition": metadata["target_definition"],
            "training_period": metadata["training_period"],
            "validation_period": metadata["validation_period"],
            "research_test_period": metadata["research_test_period"],
            "holdout_policy": champion["holdout_policy"],
            "metrics": metadata["metrics"],
            "backtest": metadata["backtest"],
            "leakage_status": "PASS",
            "validation_status": ("SELF_REPRODUCED"
                                  if champion.get("baseline_kind") == "reconstructed_baseline"
                                  else "REPRODUCED"),
            "validation_scope": champion.get("validation_scope"),
            "known_limitations": metadata["known_limitations"],
            "reproduction_command": metadata["reproduction_command"],
            "parent_champion": champion["version"],
            "experiment_id": experiment["id"],
            "artifact_sha256": snapshot_hash,
            "baseline_id": champion.get("baseline_id"),
            "baseline_kind": champion.get("baseline_kind"),
            "lineage": champion.get("lineage"),
            "v1_0_1_status": champion.get("v1_0_1_status"),
            "historical_v1_0_1_sha256": champion.get("historical_v1_0_1_sha256"),
            "reconstructed_source_sha256": champion.get("reconstructed_source_sha256"),
            "self_reproduction": champion.get("self_reproduction"),
            "pipeline_fingerprint": champion.get("pipeline_fingerprint"),
            "created_at": utc_now(),
            "immutable_provenance": {
                "champion_chain": True,
                "baseline_registry": "autonomous_agent/state/baseline_registry.json",
            },
        }
        self._append_release_ledgers(version, champion["version"], experiment, metadata, champion)
        write_json_atomic(self.root / "CHAMPION.json", new_champion)
        return destination

    def _append_release_ledgers(self, version: str, parent: str, experiment: dict[str, Any],
                                metadata: dict[str, Any], champion: dict[str, Any] | None = None) -> None:
        champion = champion or {}
        baseline_line = (
            f"\n### Baseline scope\n\n`{champion.get('baseline_id')}` "
            f"({champion.get('baseline_kind')}); v1_0_1_status: "
            f"{champion.get('v1_0_1_status', 'not recorded')}.\n"
        )
        section = (
            f"\n## {version}\n\n### Hypothesis\n\n{experiment['hypothesis']}\n\n"
            f"### Results\n\n```json\n{json.dumps(metadata['metrics'], sort_keys=True, indent=2)}\n```\n\n"
            f"### Robustness\n\nAll mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.\n"
            f"{baseline_line}\n"
            f"### Decision\n\nACCEPTED vs {parent}; see `versions/{version}/evaluation.json` and immutable snapshot.\n"
        )
        version_row = f"| {version} | Accepted version | Immutable | Parent {parent}; experiment {experiment['id']}; artifact {tree_sha256(self.versions_dir / version / 'code')} |"
        changelog = self.root / "CHANGELOG.md"
        history = self.root / "VERSION_HISTORY.md"
        for path, content, marker in ((changelog, section, f"## {version}"), (history, f"\n{version_row}\n", version_row)):
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            if marker not in existing:
                with path.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())

    @staticmethod
    def _validate_outcome(experiment: dict[str, Any], outcome: dict[str, Any]) -> None:
        Supervisor._validate_outcome(experiment, outcome)
        if outcome.get("status") != "ACCEPTED":
            raise ValueError("Candidate failed one or more release gates.")


class Supervisor:
    """Long-lived loop around isolated, bounded experiment attempts."""

    def __init__(self, root: Path = PROJECT_ROOT, state_root: Path = STATE_ROOT,
                 stop_file: Path | None = None, idle_seconds: float = 300.0,
                 max_cycles: int | None = None,
                 experiment_runner: Callable[[Hypothesis, PrerequisiteReport], dict[str, Any]] | None = None):
        self.root = root.resolve()
        self.state_root = state_root.resolve()
        self.state_path = self.state_root / "agent_state.json"
        self.journal_path = self.state_root / "events.jsonl"
        self.memory_path = self.state_root / "research_memory.json"
        self.human_memory_path = self.root / "RESEARCH_MEMORY.md"
        self.stop_file = (stop_file or self.state_root / "STOP").resolve()
        self.idle_seconds = max(0.1, idle_seconds)
        self.max_cycles = max_cycles
        self.experiment_runner = experiment_runner
        self.stop_requested = False
        self._lock_fd: int | None = None
        self._lock_identity: tuple[int, int] | None = None
        self._lock_path = self.state_root / "supervisor.lock"

    def load_state(self) -> dict[str, Any]:
        state = read_json(self.state_path, None)
        if not isinstance(state, dict) or state.get("schema_version") != 1:
            return initial_state()
        state.setdefault("experiments", [])
        state.setdefault("direction_stats", {})
        state.setdefault("holdout", initial_state()["holdout"])
        state.setdefault("active_baseline_id", None)
        if state.get("champion") is None:
            champion, _ = parse_champion(self.root / "CHAMPION.json")
            if champion is not None:
                state["champion"] = champion
                state["version_baseline"] = champion["version"]
                state["next_patch"] = int(champion["version"].rsplit(".", 1)[1]) + 1
        return state

    def save_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = utc_now()
        write_json_atomic(self.state_path, state)

    def acquire_lock(self) -> bool:
        self.state_root.mkdir(parents=True, exist_ok=True)
        lock_path = self._lock_path
        try:
            self._lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            # Recover only a lock whose recorded owner is provably gone. Malformed
            # locks fail closed and can be inspected/removed manually.
            try:
                raw = lock_path.read_text(encoding="utf-8").strip()
                owner_pid = int(raw.split("pid=", 1)[1].split()[0])
                os.kill(owner_pid, 0)
            except ProcessLookupError:
                try:
                    lock_path.unlink()
                except FileNotFoundError:
                    pass
                return self.acquire_lock()
            except OSError as error:
                # Windows reports a nonexistent PID as a generic OSError rather
                # than ProcessLookupError; only ESRCH/invalid-PID proves staleness.
                if getattr(error, "errno", None) == getattr(os, "ESRCH", 3) or getattr(error, "winerror", None) in (87, 1168):
                    try:
                        lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    return self.acquire_lock()
                return False
            except (ValueError, IndexError):
                return False
            return False
        os.write(self._lock_fd, f"pid={os.getpid()} started={utc_now()}\n".encode("utf-8"))
        os.fsync(self._lock_fd)
        lock_stat = os.fstat(self._lock_fd)
        self._lock_identity = (lock_stat.st_dev, lock_stat.st_ino)
        return True

    def release_lock(self) -> None:
        if self._lock_fd is None:
            return
        try:
            os.close(self._lock_fd)
        finally:
            self._lock_fd = None
            lock_path = self._lock_path
            try:
                current = lock_path.stat()
                if self._lock_identity == (current.st_dev, current.st_ino):
                    lock_path.unlink()
            except FileNotFoundError:
                pass
            self._lock_identity = None

    def request_stop(self, *_: Any) -> None:
        self.stop_requested = True

    def _recover_interrupted_experiment(self, state: dict[str, Any]) -> None:
        changed = False
        for pending in state["experiments"]:
            if pending.get("status") != "RUNNING":
                continue
            pending["status"] = "FAILED_RECOVERED"
            pending["finished_at"] = utc_now()
            pending["outcome_recorded"] = False
            pending["failure"] = "Supervisor restarted while this experiment was marked RUNNING; candidate workspace is retained if created."
            stats = state["direction_stats"].setdefault(pending["direction"], {"attempts": 0, "accepted": 0, "rejected": 0, "failed": 0})
            stats["failed"] = stats.get("failed", 0) + 1
            append_jsonl(self.journal_path, {"event": "experiment_recovered_after_crash", "experiment_id": pending["id"], "at": utc_now()})
            changed = True
        if changed:
            self.save_state(state)

    @staticmethod
    def _blocked_key(report_reasons: Iterable[str], direction: str) -> str:
        return hashlib.sha256(("\n".join(report_reasons) + "\n" + direction).encode("utf-8")).hexdigest()

    def _autonomous_capacity(self, state: dict[str, Any]) -> set[str] | None:
        """Refresh the terminal research-exhaustion state; return viable directions.

        Returns ``None`` when autonomous recipe generation is disabled (no
        gating; supervisor behavior is unchanged). When enabled, returns the
        directions that still have recipe coverage and attempt budget and
        maintains the persisted ``research_exhausted`` flag so the supervisor
        stops proposing doomed experiments instead of endlessly recording
        rejections. The verdict is recomputed from the append-only attempt
        ledger on every call, so it survives restarts and crashes even if the
        persisted flag is ever lost.
        """
        try:
            from autonomous_agent.spec_recipes import (
                autonomous_specs_enabled,
                generation_capacity,
            )
        except ImportError:
            return None
        if not autonomous_specs_enabled(self.root):
            return None
        capacity = generation_capacity(
            self.root, [h.direction for h in ResearchPlanner.BASE_DIRECTIONS])
        viable = set(capacity["viable_directions"])
        exhausted = not viable
        previous = bool(state.get("research_exhausted"))
        state["research_exhausted"] = exhausted
        if previous != exhausted:
            append_jsonl(self.journal_path, {
                "event": "research_exhausted" if exhausted else "research_capacity_restored",
                "at": utc_now(),
                "viable_directions": sorted(viable),
            })
        return viable

    def cycle(self, state: dict[str, Any]) -> tuple[dict[str, Any], PrerequisiteReport]:
        self._recover_interrupted_experiment(state)
        self._reconcile_unlogged_outcomes(state)
        allowed_directions = self._autonomous_capacity(state)
        if state.get("research_exhausted"):
            # Terminal state: every direction is permanently unsupported or out
            # of attempt budget. Do not propose, do not record an attempt.
            state["last_cycle_status"] = "RESEARCH_EXHAUSTED"
            self.save_state(state)
            return state, PrerequisiteReport(
                ready=False,
                reasons=("Autonomous research capacity exhausted: every direction is "
                         "permanently unsupported by the closed recipe library or has "
                         "spent its attempt budget; no further attempts will be proposed.",),
                champion_id=None, hypothesis=None)
        planner = ResearchPlanner(self.memory_path)
        initial_report = check_prerequisites(self.root, state, planner, adapter_ready=self.experiment_runner is not None,
                                             state_root=self.state_root,
                                             allowed_directions=allowed_directions)
        # When prerequisites are incomplete, explore all distinct research questions
        # once before idling; don't mistake a different question for new readiness.
        planner_state = dict(state)
        planner_state["direction_stats"] = {key: dict(value) for key, value in state.get("direction_stats", {}).items()}
        if state.get("seen_blocked_fingerprints"):
            for hypothesis_option in planner.BASE_DIRECTIONS:
                key = self._blocked_key(initial_report.reasons, hypothesis_option.direction)
                if key in state.get("seen_blocked_fingerprints", []):
                    planner_state["direction_stats"].setdefault(hypothesis_option.direction, {})["blocked"] = max(
                        planner_state["direction_stats"].get(hypothesis_option.direction, {}).get("blocked", 0), 1
                    )
        report = check_prerequisites(self.root, planner_state, planner, adapter_ready=self.experiment_runner is not None,
                                     state_root=self.state_root,
                                     allowed_directions=allowed_directions)
        seen_directions = {hypothesis.direction for hypothesis in planner.BASE_DIRECTIONS
                           if self._blocked_key(initial_report.reasons, hypothesis.direction) in state.get("seen_blocked_fingerprints", [])}
        if not report.ready and len(seen_directions) == len(planner.BASE_DIRECTIONS):
            state["last_cycle_status"] = "WAITING_ON_PREREQUISITES"
            self._reconcile_unlogged_outcomes(state)
            self.save_state(state)
            return state, report
        blocker_fingerprint = self._blocked_key(initial_report.reasons, report.hypothesis.direction)
        seen_blockers = set(state.get("seen_blocked_fingerprints", []))
        if not report.ready and blocker_fingerprint in seen_blockers:
            state["last_cycle_status"] = "WAITING_ON_PREREQUISITES"
            self._reconcile_unlogged_outcomes(state)
            self.save_state(state)
            return state, report
        hypothesis = report.hypothesis
        experiment = {
            "id": f"exp-{uuid.uuid4().hex[:12]}",
            "created_at": utc_now(),
            "direction": hypothesis.direction,
            "hypothesis": hypothesis.question,
            "rationale": hypothesis.rationale,
            "experiment_design": hypothesis.experiment,
            "status": "BLOCKED" if not report.ready else "RUNNING",
            "candidate_version": None,
            "champion_id": report.champion_id,
            "baseline_id": state.get("active_baseline_id"),
            "holdout_touched": False,
            "checks": {"unit": "NOT_RUN", "leakage": "NOT_RUN", "walk_forward": "NOT_RUN", "robustness": "NOT_RUN", "evaluation": "NOT_RUN"},
            "outcome_recorded": False,
            "blockers": list(report.reasons),
        }
        state["experiments"].append(experiment)
        state["last_cycle_status"] = experiment["status"]
        # Persist both blocked hypotheses and running intent before non-transactional
        # memory/journal writes so a restart can reconcile an interrupted record.
        self.save_state(state)
        if report.ready:
            stats = state["direction_stats"].setdefault(hypothesis.direction, {"attempts": 0, "accepted": 0, "rejected": 0, "failed": 0})
            stats["attempts"] = stats.get("attempts", 0) + 1
            # Persist intent before invoking an adapter so restart can recognize an
            # interrupted attempt instead of losing its experiment record.
            self.save_state(state)
        else:
            seen_blockers.add(blocker_fingerprint)
            state["seen_blocked_fingerprints"] = sorted(seen_blockers)
            blocked_stats = state["direction_stats"].setdefault(hypothesis.direction, {"attempts": 0, "accepted": 0, "rejected": 0, "failed": 0, "blocked": 0})
            blocked_stats["blocked"] = blocked_stats.get("blocked", 0) + 1
        if not report.ready:
            discovery = {
                "experiment_id": experiment["id"], "created_at": experiment["created_at"],
                "direction": hypothesis.direction, "question": hypothesis.question,
                "rationale": hypothesis.rationale, "design": hypothesis.experiment,
                "status": experiment["status"], "blockers": experiment["blockers"],
                "lesson": experiment.get("failure") or experiment.get("rejection_reason", "Prerequisite failure or adapter result recorded; no scientific conclusion."),
                "scientific_claim": False,
            }
            discovery.update(build_research_record(experiment, hypothesis, None, self.memory_path))
            append_discovery(self.memory_path, discovery)
            append_human_memory(self.human_memory_path, discovery)
            experiment["outcome_recorded"] = True
            self.save_state(state)
        if report.ready:
            # There is intentionally no implicit command execution. The adapter is
            # explicitly registered by code, not selected from repository scripts.
            try:
                from autonomous_agent.campaign5_authorization import check_campaign5_authorization
                campaign = read_json(self.root / "autonomous_agent/state/campaign_config.json", {}) or {}
                preflight = check_campaign5_authorization(
                    self.root, campaign, campaign.get("authorization_scope"))
                if not preflight["allowed"]:
                    raise RuntimeError("Campaign 5 authorization preflight blocked execution: "
                                       + ",".join(preflight["reason_codes"]))
                outcome = self.experiment_runner(hypothesis, report)
                self._validate_outcome(experiment, outcome)
                experiment.update(outcome)
                experiment["finished_at"] = utc_now()
                experiment["outcome_recorded"] = False
                if experiment.get("baseline_id"):
                    state["active_baseline_id"] = experiment["baseline_id"]
                accepted = experiment["status"] == "ACCEPTED"
                if accepted:
                    champion, champion_errors = parse_champion(self.root / "CHAMPION.json")
                    if champion is None:
                        raise ValueError("Candidate was accepted but no valid immutable CHAMPION.json exists: " + "; ".join(champion_errors))
                    release_path = VersionManager(self.root).promote(champion, experiment, outcome)
                    state["champion"] = read_json(self.root / "CHAMPION.json", None)
                    state["next_patch"] = int(state["champion"]["version"].rsplit(".", 1)[1]) + 1
                    state["version_baseline"] = state["champion"]["version"]
                    experiment["accepted_version"] = state["champion"]["version"]
                    experiment["release_path"] = str(release_path.relative_to(self.root))
                stats["accepted" if accepted else "rejected"] = stats.get("accepted" if accepted else "rejected", 0) + 1
                if accepted:
                    state["consecutive_rejections"] = 0
                else:
                    state["consecutive_rejections"] = state.get("consecutive_rejections", 0) + 1
            except Exception as error:  # supervisor survives candidate failures
                experiment["status"] = ("BLOCKED" if "authorization preflight" in str(error).lower()
                                         else "FAILED")
                experiment["finished_at"] = utc_now()
                experiment["failure"] = f"{type(error).__name__}: {error}"
                experiment["traceback"] = traceback.format_exc(limit=20)
                experiment["outcome_recorded"] = False
                if experiment["status"] == "BLOCKED":
                    experiment["blockers"] = [str(error)]
                else:
                    stats["failed"] = stats.get("failed", 0) + 1
                    state["consecutive_rejections"] = state.get("consecutive_rejections", 0) + 1
                state["last_error"] = experiment["failure"]
            memory_record = {
                "experiment_id": experiment["id"], "created_at": experiment["finished_at"],
                "direction": hypothesis.direction, "question": hypothesis.question,
                "status": experiment["status"], "blockers": experiment.get("blockers", []),
                "lesson": experiment.get("failure") or experiment.get("rejection_reason", "Candidate result recorded; review detailed evaluation artifacts."),
                "scientific_claim": False,
            }
            memory_record.update(build_research_record(experiment, hypothesis, None, self.memory_path))
            # Persist the evaluation before append-only memory writes; if the
            # process dies midway, reconciliation can safely finish those writes.
            self.save_state(state)
            append_discovery(self.memory_path, memory_record)
            append_human_memory(self.human_memory_path, memory_record)
            experiment["outcome_recorded"] = True
            self.save_state(state)
        if state.get("consecutive_rejections", 0) >= 5:
            state["stagnation_mode"] = True
        if not report.ready:
            state["last_cycle_status"] = "BLOCKED"
        append_jsonl(self.journal_path, {"event": "experiment_cycle", "experiment_id": experiment["id"],
                                        "status": experiment["status"], "direction": hypothesis.direction,
                                        "at": utc_now()})
        self.save_state(state)
        return state, report

    def _reconcile_unlogged_outcomes(self, state: dict[str, Any]) -> None:
        """Finish memory updates after a crash between evaluation and journal commit."""
        discoveries = read_json(self.memory_path, {}).get("discoveries", [])
        recorded_ids = {item.get("experiment_id") for item in discoveries}
        changed = False
        for experiment in state["experiments"]:
            if experiment.get("status") not in {"ACCEPTED", "REJECTED", "FAILED", "FAILED_RECOVERED", "BLOCKED"}:
                continue
            if experiment.get("outcome_recorded"):
                continue
            # A crash immediately after persisting a new blocked attempt is normal;
            # reconcile it only if its machine-readable entry reached disk.
            if experiment.get("status") == "BLOCKED" and experiment.get("id") not in recorded_ids:
                continue
            record = {
                "experiment_id": experiment["id"], "created_at": experiment.get("finished_at", utc_now()),
                "direction": experiment["direction"], "question": experiment["hypothesis"],
                "status": experiment["status"], "blockers": experiment.get("blockers", []),
                "lesson": experiment.get("failure") or experiment.get("rejection_reason", "Outcome restored from durable state; review attached evidence."),
                "scientific_claim": False,
            }
            append_discovery(self.memory_path, record)
            append_human_memory(self.human_memory_path, record)
            experiment["outcome_recorded"] = True
            changed = True
        if changed:
            self.save_state(state)

    @staticmethod
    def _validate_outcome(experiment: dict[str, Any], outcome: dict[str, Any]) -> None:
        if not isinstance(outcome, dict):
            raise TypeError("Experiment adapter must return a result mapping.")
        if outcome.get("holdout_touched", False):
            outcome["status"] = "REJECTED"
            outcome["rejection_reason"] = "Final holdout access is prohibited during continuous research."
            return
        required = ("status", "checks", "results", "candidate_path")
        missing = [key for key in required if key not in outcome]
        if missing:
            raise ValueError(f"Experiment result missing required fields: {', '.join(missing)}")
        checks = outcome["checks"]
        required_checks = ("unit", "leakage", "walk_forward", "robustness", "evaluation")
        if any(checks.get(name) != "PASS" for name in required_checks):
            outcome["status"] = "REJECTED"
            # Never mask a meaningful, already-recorded rejection reason (e.g. an
            # autonomous-spec refusal code like UNSUPPORTED/BUDGET_EXHAUSTED) with
            # the generic gate message; the generic text is only a fallback.
            existing_reason = str(outcome.get("rejection_reason") or "").strip()
            if not existing_reason:
                outcome["rejection_reason"] = "One or more mandatory scientific gates did not PASS."
        if outcome["status"] not in {"ACCEPTED", "REJECTED"}:
            raise ValueError("Experiment status must be ACCEPTED or REJECTED.")
        if outcome["status"] == "ACCEPTED":
            required_metrics = (
                "primary_metric", "uncertainty_interval", "practical_effect",
                "decision_criteria_passed", "calibration", "subgroup_stability",
                "per_seed_metrics", "complexity_delta", "runtime_delta", "backtest",
            )
            if any(key not in outcome["results"] for key in required_metrics):
                raise ValueError("Acceptance requires statistical, practical, calibration, subgroup, multi-seed, cost, and backtest evidence.")
            if outcome["results"]["decision_criteria_passed"] is not True:
                raise ValueError("Predeclared practical and statistical acceptance criteria did not pass.")
            if not outcome.get("reproduction_command") or not outcome.get("artifact_sha256"):
                raise ValueError("Accepted candidate requires reproducibility command and artifact hash.")
            if not isinstance(outcome.get("candidate_path"), str):
                raise ValueError("Accepted candidate requires an isolated candidate workspace path.")
            if not isinstance(outcome.get("release_metadata"), dict):
                raise ValueError("Accepted candidate requires complete release metadata.")

    def run(self) -> int:
        if not self.acquire_lock():
            print("Another supervisor holds the lock; exiting.", file=sys.stderr)
            return 2
        previous_handlers: dict[int, Any] = {}
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[sig] = signal.signal(sig, self.request_stop)
        count = 0
        try:
            state = self.load_state()
            self._recover_interrupted_experiment(state)
            # Refresh terminal research exhaustion from the durable ledger so the
            # state survives restarts and crashes.
            self._autonomous_capacity(state)
            self.save_state(state)
            # A prior stop request is one-shot; this explicit new start clears it.
            try:
                self.stop_file.unlink()
            except FileNotFoundError:
                pass
            append_jsonl(self.journal_path, {"event": "supervisor_started", "at": utc_now(), "pid": os.getpid()})
            if self.max_cycles == 0 or self.stop_requested or self.stop_file.exists():
                return 0
            while not self.stop_requested and not self.stop_file.exists() \
                    and not state.get("research_exhausted"):
                count += 1
                try:
                    state, report = self.cycle(state)
                    print(json.dumps({"cycle": count, "ready": report.ready,
                                      "status": state.get("last_cycle_status", "UNKNOWN"),
                                      "hypothesis": report.hypothesis.question if report.hypothesis else None,
                                      "blockers": list(report.reasons)}, ensure_ascii=False), flush=True)
                    if state.get("research_exhausted"):
                        # Terminal state: stop generating attempts entirely.
                        break
                    delay = self.idle_seconds if report.ready else min(max(self.idle_seconds, 300.0), 3600.0)
                except Exception as error:
                    # Candidate/evaluation/storage errors are persisted and retried by
                    # the living supervisor; process-level startup/lock errors still
                    # escape to the outer handler.
                    state["last_error"] = f"cycle {type(error).__name__}: {error}"
                    self.save_state(state)
                    append_jsonl(self.journal_path, {"event": "cycle_error", "at": utc_now(),
                                                    "error": state["last_error"],
                                                    "traceback": traceback.format_exc(limit=20)})
                    delay = min(max(self.idle_seconds, 60.0), 3600.0)
                if self.max_cycles is not None and count >= self.max_cycles:
                    break
                # Idle longer when blocked or recovering, avoiding tight failure loops.
                deadline = time.monotonic() + delay
                while time.monotonic() < deadline and not self.stop_requested and not self.stop_file.exists():
                    time.sleep(min(1.0, deadline - time.monotonic()))
            append_jsonl(self.journal_path, {"event": "supervisor_stopped", "at": utc_now(), "cycles": count})
            return 0
        except Exception as error:
            state = self.load_state()
            state["last_error"] = f"supervisor {type(error).__name__}: {error}"
            self.save_state(state)
            append_jsonl(self.journal_path, {"event": "supervisor_error", "at": utc_now(),
                                            "error": state["last_error"], "traceback": traceback.format_exc(limit=20)})
            raise
        finally:
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)
            self.release_lock()


def _default_experiment_runner(root: Path) -> Callable[[Hypothesis, PrerequisiteReport], dict[str, Any]] | None:
    """Register the reviewed adapter when available; never invent one.

    Candidate specs come from the deterministic, closed recipe provider only
    when the reviewed ``autonomy_config.json`` explicitly sets
    ``allow_autonomous_specs`` (default: false). When disabled -- the default --
    the runner behaves exactly as before and refuses every candidate spec.
    """
    try:
        from autonomous_agent.experiment_adapter import ExperimentAdapter, build_experiment_runner
        from autonomous_agent.spec_recipes import build_default_provider
    except ImportError:
        return None
    return build_experiment_runner(ExperimentAdapter(root=root),
                                   spec_provider=build_default_provider(root))


def bootstrap_champion(root: Path, state_root: Path, version: str = "V2.0.0") -> dict[str, Any]:
    """Create the first immutable CHAMPION.json from the established baseline.

    Only a reconstructed baseline with valid self-reproduction evidence can be
    bootstrapped, and the resulting champion is scoped so it can never be read
    as a claim that V1.0.1 was reproduced.
    """
    root = root.resolve()
    champion_path = root / "CHAMPION.json"
    if champion_path.exists():
        raise FileExistsError("CHAMPION.json already exists; champions are immutable.")
    registry = BaselineRegistry(Path(state_root))
    record = registry.active()
    if record is None:
        raise ValueError("No established baseline is registered; run establish-baseline first.")
    reasons = validate_established_record(record)
    if reasons:
        raise ValueError("Established baseline record is invalid: " + "; ".join(reasons))
    if record.get("kind") != "reconstructed_baseline":
        raise ValueError("bootstrap-champion supports reconstructed baselines only.")
    match = VersionManager.VERSION_PATTERN.fullmatch(version)
    if not match or int(match.group(1)) < 2:
        raise ValueError("Reconstructed-baseline champions must start in the V2+ version series.")
    outputs = record.get("outputs") or {}
    inputs = record.get("inputs") or {}
    champion: dict[str, Any] = {
        "version": version,
        "champion_origin": f"bootstrap from established baseline {record['baseline_id']}",
        "baseline_id": record["baseline_id"],
        "baseline_kind": "reconstructed_baseline",
        "code_revision": (record.get("source") or {}).get("sha256"),
        "dataset_id": "demand_zone_v2_dataset (restored v1.0.1 roster source)",
        "dataset_sha256": inputs.get("v2_roster_dataset_sha256"),
        "feature_set": sorted((outputs.get("feature_arms") or {}).keys()) or ["see baseline record"],
        "model": record.get("models") or [],
        "target_definition": "Frozen v1 label definition per MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json "
                             "with target-maturity purge; retrospective development only.",
        "training_period": "Expanding historical windows strictly before each fold start "
                           "(see baseline record; no future data).",
        "validation_period": "Chronological folds 2023/2024/2025 per the frozen protocol.",
        "research_test_period": "NONE: final holdout SEALED; no test interval has been evaluated.",
        "holdout_policy": {"status": "SEALED", "uses": 0,
                           "policy": "Do not access for research tuning; no approved final evaluation run."},
        "metrics": {"scope": f"Retrospective development OOF metrics of {record['baseline_id']}",
                    "pooled_oof_metrics": outputs.get("pooled_oof_metrics")},
        "backtest": {"scope": "Retrospective development artifacts only; see baseline record.",
                     "artifact_sha256": outputs.get("artifact_sha256")},
        "leakage_status": "PASS",
        "validation_status": "SELF_REPRODUCED",
        "validation_scope": (f"Self-reproduction of {record['baseline_id']} only (two byte-identical "
                             f"clean runs). {RECONSTRUCTED_STATEMENT}"),
        "known_limitations": list(record.get("known_limitations") or []),
        "reproduction_command": ("py -3 -m autonomous_agent.experiment_adapter establish-baseline "
                                 f"--baseline-id {record['baseline_id']}"),
        "v1_0_1_status": "FAILED",
        "historical_v1_0_1_sha256": PIN_V1_0_1_CODE_SHA256,
        "reconstructed_source_sha256": (record.get("source") or {}).get("sha256"),
        "self_reproduction": record.get("self_reproduction"),
        "pipeline_fingerprint": record.get("pipeline_fingerprint"),
        "lineage": dict(record.get("lineage") or {}),
        "created_at": utc_now(),
        "immutable_provenance": {
            "baseline_registry": "autonomous_agent/state/baseline_registry.json",
            "baseline_record_sha256": hashlib.sha256(
                json.dumps(record, sort_keys=True).encode("utf-8")).hexdigest(),
            "statement": RECONSTRUCTED_STATEMENT,
        },
    }
    champion["lineage"].setdefault("relation", "reconstruction")
    temporary = root / "CHAMPION.json.bootstrap-tmp"
    write_json_atomic(temporary, champion)
    parsed, errors = parse_champion(temporary)
    if parsed is None:
        temporary.unlink(missing_ok=True)
        raise ValueError("Bootstrapped champion failed validation: " + "; ".join(errors))
    os.replace(temporary, champion_path)
    return parsed


def status(root: Path = PROJECT_ROOT, state_root: Path = STATE_ROOT) -> dict[str, Any]:
    experiment_runner = _default_experiment_runner(root)
    supervisor = Supervisor(root=root, state_root=state_root, experiment_runner=experiment_runner)
    state = supervisor.load_state()
    report = check_prerequisites(root, state, ResearchPlanner(supervisor.memory_path),
                                 adapter_ready=supervisor.experiment_runner is not None,
                                 state_root=state_root)
    active_baseline = BaselineRegistry(Path(state_root)).active()
    historical_v1_0_1 = read_json(Path(state_root) / "baseline_reproduction.json", {}) or {}
    return {
        "agent_version": AGENT_VERSION,
        "ready": report.ready,
        "champion": state.get("champion") or read_json(root / "CHAMPION.json", None),
        "holdout": state.get("holdout"),
        "next_patch": state.get("next_patch"),
        "version_baseline": state.get("version_baseline"),
        "stagnation_mode": state.get("stagnation_mode", False),
        "active_baseline": {
            "baseline_id": (active_baseline or {}).get("baseline_id"),
            "status": (active_baseline or {}).get("status"),
            "statement": RECONSTRUCTED_STATEMENT,
            "registry": "autonomous_agent/state/baseline_registry.json",
        },
        "historical_v1_0_1_reproduction": {
            "record": "autonomous_agent/state/baseline_reproduction.json",
            "status": historical_v1_0_1.get("status", "NOT_RUN"),
            "note": "Historical track; never modified by the reconstructed-baseline track.",
        },
        "pending_hypothesis": asdict(report.hypothesis) if report.hypothesis else None,
        "blockers": list(report.reasons),
        "experiments_recorded": len(state.get("experiments", [])),
        "final_holdout_policy": "SEALED: supervisor does not read or access holdout rows.",
        "planner_mode": "Transparent deterministic evidence-driven planner; no LLM provider is configured.",
        "experiment_engine": (
            "Reviewed experiment adapter implemented (autonomous_agent/experiment_adapter.py): "
            "isolated candidate workspaces, allowlisted changes, gated evaluation, fail-safe "
            "destruction. Execution additionally requires a REPRODUCED baseline; without one the "
            "adapter refuses every candidate."
            if supervisor.experiment_runner is not None else
            "Unavailable: the reviewed project-specific adapter could not be imported."
        ),
        "real_money_trading": "PROHIBITED: no brokerage integration or order capability exists.",
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("status", help="Show evidence-gated readiness without running experiments.")
    inspect_parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    inspect_parser.add_argument("--state-dir", type=Path, default=STATE_ROOT)

    run_parser = subparsers.add_parser("run", help="Start the long-running supervisor; Ctrl-C or STOP file stops it.")
    run_parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    run_parser.add_argument("--state-dir", type=Path, default=STATE_ROOT)
    run_parser.add_argument("--idle-seconds", type=float, default=300.0)
    run_parser.add_argument("--max-cycles", type=int, default=None, help="Optional bound useful for verification.")
    stop_parser = subparsers.add_parser("stop", help="Request stop by creating the state STOP file.")
    stop_parser.add_argument("--state-dir", type=Path, default=STATE_ROOT)
    bootstrap_parser = subparsers.add_parser(
        "bootstrap-champion",
        help="Create the first immutable CHAMPION.json from the established reconstructed baseline.")
    bootstrap_parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    bootstrap_parser.add_argument("--state-dir", type=Path, default=STATE_ROOT)
    bootstrap_parser.add_argument("--version", default="V2.0.0")
    args = parser.parse_args(argv)
    if args.command == "bootstrap-champion":
        champion = bootstrap_champion(args.root, args.state_dir, version=args.version)
        print(json.dumps(champion, indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        result = status(root=args.root, state_root=args.state_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command == "stop":
        args.state_dir.mkdir(parents=True, exist_ok=True)
        (args.state_dir / "STOP").write_text("stop requested\n", encoding="utf-8")
        print(f"Stop requested via {args.state_dir / 'STOP'}")
        try:
            from autonomous_agent import hardening
        except ImportError:  # direct module execution
            import hardening  # type: ignore
        killed = hardening.kill_active_subprocess_tree(args.state_dir)
        if killed.get("killed"):
            print(f"Terminated active experiment subprocess tree (pid {killed.get('pid')}).")
        return 0
    supervisor = Supervisor(root=args.root, state_root=args.state_dir,
                            idle_seconds=args.idle_seconds, max_cycles=args.max_cycles,
                            experiment_runner=_default_experiment_runner(args.root))
    return supervisor.run()


if __name__ == "__main__":
    raise SystemExit(main())
