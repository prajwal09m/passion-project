"""Fail-closed, holdout-blind EvidenceView builder (Phase 1 component 1).

The generator never receives a filesystem handle — only the serialized view
this module builds. Sources are an explicit allowlist; the sealed holdout
(``study_files/outputs/study_v1/prospective``) can never be opened through
this module: path checks run BEFORE any read, and deny rules win over allow
rules (fail closed, never guess).
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from autonomous_agent.proposal_layer import schema

# Explicit allowlist (Phase 1 C.6). Deny rules below always win.
ALLOWED_SOURCE_PATTERNS: tuple[str, ...] = (
    "CHAMPION.json",
    "autonomous_agent/state/agent_state.json",
    "autonomous_agent/state/events.jsonl",
    "autonomous_agent/state/adapter_events.jsonl",
    "autonomous_agent/state/research_memory.json",
    "autonomous_agent/state/spec_attempts.json",
    "autonomous_agent/state/experiment_registry.json",
    "autonomous_agent/state/baseline_registry.json",
    "autonomous_agent/state/baseline_reproduction.json",
    "autonomous_agent/state/proposal_ledger.jsonl",
    "versions/*/version.json",
    "versions/*/evaluation.json",
    "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md",
)

# Never-auto-loaded metadata source: hashed via CHAMPION, stat()ed here, and
# only explicitly re-hashed by the validator (never embedded in the view).
DATASET_PATH = "study_files/outputs/study_v1/development/event_table.csv"
# Allowed for citation/re-hash purposes, but excluded from auto-embedding so
# building a view never reads the 100 MB table.
METADATA_ONLY_PATTERNS: tuple[str, ...] = (DATASET_PATH,)

# Sources whose *content* is embedded in the view (and therefore strip-scanned).
_EMBEDDED_JSON = frozenset({"CHAMPION.json",
                            "autonomous_agent/state/agent_state.json",
                            "autonomous_agent/state/spec_attempts.json"})


class EvidenceViewError(Exception):
    """Fail-closed: the view could not be proven safe, so it was not built."""


def _normalize(relative: str) -> str:
    return relative.replace("\\", "/").lstrip("./")


def is_denied(relative: str) -> bool:
    """Deny rules: any path component naming the sealed holdout."""
    parts = [part.lower() for part in _normalize(relative).split("/")]
    return "prospective" in parts or "holdout" in parts


def is_allowed_source(relative: str) -> bool:
    """Allowlist check with deny precedence. Fail closed."""
    rel = _normalize(relative)
    if is_denied(rel):
        return False
    return (any(fnmatch.fnmatch(rel, pattern) for pattern in ALLOWED_SOURCE_PATTERNS)
            or rel in METADATA_ONLY_PATTERNS)


def assert_source_allowed(relative: str) -> str:
    rel = _normalize(relative)
    if is_denied(rel):
        raise EvidenceViewError(
            f"Refusing sealed-holdout path {relative!r}: never readable.")
    if not (any(fnmatch.fnmatch(rel, pattern) for pattern in ALLOWED_SOURCE_PATTERNS)
            or rel in METADATA_ONLY_PATTERNS):
        raise EvidenceViewError(
            f"Source {relative!r} is not on the EvidenceView allowlist.")
    return rel


def _strip_forbidden(value: Any) -> tuple[Any, bool]:
    """Recursively remove values that reference the holdout path. Returns
    (cleaned, stripped). Policy/status text without a holdout *path* survives."""
    stripped = False
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if isinstance(item, str) and schema.contains_holdout_path(item):
                stripped = True
                continue
            new_item, sub = _strip_forbidden(item)
            stripped = stripped or sub
            cleaned[key] = new_item
        return cleaned, stripped
    if isinstance(value, list):
        kept = []
        for item in value:
            if isinstance(item, str) and schema.contains_holdout_path(item):
                stripped = True
                continue
            new_item, sub = _strip_forbidden(item)
            stripped = stripped or sub
            kept.append(new_item)
        return kept, stripped
    if isinstance(value, str) and schema.contains_holdout_path(value):
        return None, True
    return value, False


def _read_bytes(root: Path, relative: str) -> bytes:
    """The single read gate: allowlist + denylist checked before any open()."""
    rel = assert_source_allowed(relative)
    path = root / rel
    if not path.is_file():
        raise EvidenceViewError(f"Allowed source missing: {rel}")
    return path.read_bytes()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _matches(rel: str) -> bool:
    return (any(fnmatch.fnmatch(rel, pattern) for pattern in ALLOWED_SOURCE_PATTERNS)
            or rel in METADATA_ONLY_PATTERNS)


def _iter_source_paths(root: Path) -> Iterable[str]:
    """Existing allowlisted files, deterministically ordered (metadata-only
    patterns excluded — the dataset is never loaded while building a view)."""
    found: set[str] = set()
    for pattern in ALLOWED_SOURCE_PATTERNS:
        if "*" in pattern:
            for path in sorted(root.glob(pattern)):
                if path.is_file():
                    found.add(_normalize(str(path.relative_to(root))))
        else:
            candidate = root / pattern
            if candidate.is_file():
                found.add(pattern)
    return sorted(found)


def build(root: Path | str, *, clock: Callable[[], str],
          ledger_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build the serialized evidence document handed to the generator.

    Fail-closed behaviors:
      * CHAMPION.json must exist, parse, and carry a valid-looking version.
      * Any allowlisted path that also trips a deny rule raises (config bug).
      * Content referencing the holdout path is stripped and stamped.
      * The dataset is stat()ed + cited from CHAMPION; it is never opened here.
    """
    root = Path(root)
    champion_bytes = _read_bytes(root, "CHAMPION.json")
    try:
        champion_raw = json.loads(champion_bytes)
    except json.JSONDecodeError as error:
        raise EvidenceViewError(f"CHAMPION.json unparseable: {error}") from error
    if not isinstance(champion_raw, dict) or not isinstance(champion_raw.get("version"), str):
        raise EvidenceViewError("CHAMPION.json missing a valid version field.")

    sources: list[dict[str, Any]] = []
    embedded: dict[str, Any] = {}
    stripped_any = False
    for rel in _iter_source_paths(root):
        data = _read_bytes(root, rel)          # deny/allow enforced inside
        sources.append({"path": rel, "sha256": _sha256(data), "bytes": len(data)})
        if rel in _EMBEDDED_JSON:
            try:
                parsed = json.loads(data)
            except json.JSONDecodeError as error:
                raise EvidenceViewError(f"{rel} unparseable: {error}") from error
            cleaned, stripped = _strip_forbidden(parsed)
            stripped_any = stripped_any or stripped
            embedded[rel] = cleaned

    champion = embedded.get("CHAMPION.json", {})
    agent_state = embedded.get("autonomous_agent/state/agent_state.json", {})
    recipe_attempts = (embedded.get("autonomous_agent/state/spec_attempts.json", {})
                       .get("attempts", []))
    if not isinstance(recipe_attempts, list):
        recipe_attempts = []

    # Dataset: metadata only. Cited hash comes from CHAMPION; size via stat().
    dataset_rel = _normalize(DATASET_PATH)
    if is_denied(dataset_rel) or not _matches(dataset_rel):
        raise EvidenceViewError("Dataset path failed allowlist sanity check.")
    dataset_path = root / dataset_rel
    dataset = {
        "path": dataset_rel,
        "sha256": str(champion.get("dataset_sha256", "")),
        "bytes": dataset_path.stat().st_size if dataset_path.is_file() else None,
        "present": dataset_path.is_file(),
        "opened_by_evidence_view": False,
    }

    experiments = agent_state.get("experiments", [])
    prior_experiments = [
        {key: item.get(key) for key in
         ("id", "direction", "status", "created_at", "finished_at", "accepted_version")}
        for item in experiments if isinstance(item, dict)
    ]
    holdout_policy = champion.get("holdout_policy") or {}

    # F.5: already_asked = every prior proposal (any status) with its
    # fingerprint, signature, and refusal/outcome codes — cumulative,
    # permanent, and restart-safe (folds transitions from the ledger rows).
    latest_status: dict[str, str] = {}
    latest_reason: dict[str, Any] = {}
    for row in (ledger_rows or []):
        if row.get("row_type") == "transition":
            pid = str(row.get("proposal_id"))
            latest_status[pid] = str(row.get("to"))
            if row.get("reason_code") is not None:
                latest_reason[pid] = row.get("reason_code")
    already_asked = []
    for row in (ledger_rows or []):
        if row.get("row_type") == "proposal":
            payload = row.get("proposal") or {}
            pid = str(row.get("proposal_id"))
            entry, _ = _strip_forbidden({
                "proposal_id": row.get("proposal_id"),
                "fingerprint": payload.get("proposal_fingerprint"),
                "design_signature": payload.get("design_signature"),
                "hypothesis": payload.get("hypothesis"),
                "direction": payload.get("direction"),
                "proposal_class": payload.get("proposal_class"),
                "campaign_id": payload.get("campaign_id"),
                "status": latest_status.get(pid, schema.STATUS_PROPOSED),
                "last_reason_code": latest_reason.get(pid),
            })
            already_asked.append(entry)

    view: dict[str, Any] = {
        "schema_version": 1,
        "sources": sources,
        "champion": {key: champion.get(key) for key in (
            "version", "parent_champion", "created_at", "artifact_sha256",
            "experiment_id", "baseline_id", "metrics", "validation_status",
            "dataset_sha256", "pipeline_fingerprint")},
        "holdout_policy": {key: holdout_policy.get(key)
                           for key in ("status", "uses", "policy")
                           if key in holdout_policy},
        "baseline": {"baseline_id": champion.get("baseline_id")},
        "dataset": dataset,
        "prior_experiments": prior_experiments,
        "direction_stats": agent_state.get("direction_stats", {}),
        "recipe_attempts": [
            {key: row.get(key) for key in
             ("experiment_id", "recipe_id", "selected_parameters", "spec_sha256")}
            for row in recipe_attempts if isinstance(row, dict)],
        "already_asked": already_asked,
        "holdout_reference_stripped": bool(stripped_any),
    }
    view["evidence_view_sha256"] = schema.sha256_hex(
        schema.canonical_json(view))
    return view


def source_hash(view: dict[str, Any], relative: str) -> str | None:
    rel = _normalize(relative)
    for row in view.get("sources", []):
        if row.get("path") == rel:
            return row.get("sha256")
    if rel == _normalize(DATASET_PATH):
        return (view.get("dataset") or {}).get("sha256")
    return None
