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
import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath
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
    """Normalize a workspace-relative path without erasing traversal syntax.

    Leading ``./`` is harmless. Parent components, absolute paths, drive or
    UNC prefixes are rejected before allowlist matching or filesystem access.
    """
    if not isinstance(relative, str) or not relative:
        raise EvidenceViewError("Evidence source path must be a non-empty string.")
    if "\x00" in relative:
        raise EvidenceViewError("Evidence source path contains a NUL byte.")
    normalized = relative.replace("\\", "/")
    posix = PurePosixPath(normalized)
    windows = PureWindowsPath(relative)
    if (posix.is_absolute() or windows.is_absolute() or windows.drive
            or any(part == ".." for part in posix.parts)):
        raise EvidenceViewError(f"Refusing absolute or traversing source path {relative!r}.")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("/") or not normalized or any(
            part in ("", ".", "..") for part in normalized.split("/")):
        raise EvidenceViewError(f"Refusing malformed source path {relative!r}.")
    return normalized


def is_denied(relative: str) -> bool:
    """Deny rules: any path component naming the sealed holdout."""
    parts = [part.lower() for part in _normalize(relative).split("/")]
    return "prospective" in parts or "holdout" in parts


def _pattern_matches(rel: str, pattern: str) -> bool:
    """Allowlist matching, component-wise (fail closed).

    Plain ``fnmatch`` cannot be used on the whole path: its ``*`` spans
    separator characters, so ``versions/a/b/version.json`` matched
    ``versions/*/version.json`` even though the reviewed allowlist is one
    directory deep. And ``fnmatch.fnmatch`` folds case only on some
    platforms (case-insensitive on Windows, case-sensitive on POSIX),
    which is preserved here deliberately — each platform's filesystem
    behavior is mirrored so allowlist matching cannot diverge from what
    ``open()`` would actually resolve.
    """
    rel_parts = rel.split("/")
    pattern_parts = pattern.split("/")
    if len(rel_parts) != len(pattern_parts):
        return False
    return all(
        fnmatch.fnmatchcase(os.path.normcase(part), os.path.normcase(pat))
        for part, pat in zip(rel_parts, pattern_parts))


def is_allowed_source(relative: str) -> bool:
    """Allowlist check with deny precedence. Fail closed."""
    try:
        rel = _normalize(relative)
    except EvidenceViewError:
        return False
    if is_denied(rel):
        return False
    return (any(_pattern_matches(rel, pattern) for pattern in ALLOWED_SOURCE_PATTERNS)
            or rel in METADATA_ONLY_PATTERNS)


def assert_source_allowed(relative: str) -> str:
    rel = _normalize(relative)
    if is_denied(rel):
        raise EvidenceViewError(
            f"Refusing sealed-holdout path {relative!r}: never readable.")
    if not (any(_pattern_matches(rel, pattern) for pattern in ALLOWED_SOURCE_PATTERNS)
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
            if isinstance(key, str) and schema.contains_holdout_path(key):
                stripped = True
                continue
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


def _resolved_path_inside_root(root: Path | str, relative: str) -> Path:
    """Resolve a path and reject symlink escapes from the workspace root."""
    rel = _normalize(relative)
    root_path = Path(root).resolve()
    path = (root_path / rel).resolve()
    try:
        path.relative_to(root_path)
    except ValueError as error:
        raise EvidenceViewError(
            f"Refusing source that resolves outside the EvidenceView root: {rel}") from error
    return path


def _resolve_inside_root(root: Path | str, relative: str) -> Path:
    """Resolve an allowlisted source and reject symlink escapes from root."""
    rel = assert_source_allowed(relative)
    return _resolved_path_inside_root(root, rel)


def _read_bytes(root: Path, relative: str) -> bytes:
    """The single read gate: allowlist + denylist checked before any open().

    Reads go through ``_open_contained_bytes`` so containment and file
    identity are enforced on the file actually opened, not only on a path
    string that was checked earlier.
    """
    rel = assert_source_allowed(relative)
    _resolve_inside_root(root, rel)
    return _open_contained_bytes(root, rel)


def _fd_read_all(fd: int, rel: str) -> bytes:
    """Read a whole file from an already-open descriptor and close it.

    Identity + type are re-verified on the OPEN DEVICE (fstat), never on a
    pre-checked path string: a non-regular file — FIFO, device, directory —
    or anything that changed type between check and read fails closed.
    """
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise EvidenceViewError(
                f"Allowed source is missing or not a regular file: {rel}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _posix_chain_open_fd(root: Path, rel: str) -> int:
    """POSIX: descriptor-relative, no-follow open of EVERY component.

    The root directory is opened with ``O_DIRECTORY``; each intermediate
    component is opened ``O_RDONLY|O_DIRECTORY|O_NOFOLLOW`` relative to the
    previous descriptor, and the final component ``O_RDONLY|O_NOFOLLOW``.
    Consequences (all deliberate, fail closed):
      * a symlink in ANY component cannot switch targets after the
        containment check — ``O_NOFOLLOW`` fails the open itself (ELOOP);
      * traversal cannot escape the root by construction: every open is
        relative to the previous in-root directory descriptor;
    Returns the final file descriptor. Raises OSError for callers to map.
    """
    flags_dir = (os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                 | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW)
    flags_file = (os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
                  | getattr(os, "O_NONBLOCK", 0) | os.O_NOFOLLOW)
    parts = rel.split("/")
    dir_fd = os.open(str(root), flags_dir)
    try:
        for component in parts[:-1]:
            next_fd = os.open(component, flags_dir, dir_fd=dir_fd)
            os.close(dir_fd)
            dir_fd = next_fd
        fd = os.open(parts[-1], flags_file, dir_fd=dir_fd)
    finally:
        os.close(dir_fd)
    return fd


def _windows_open_bytes(root: Path, rel: str) -> bytes:
    """Windows: no dir_fd/O_NOFOLLOW in the standard library — substitute
    the strongest stdlib defenses instead, all fail closed:

      1. ``lstat`` refuses any reparse point (symlink, junction, mount
         point) as the final component BEFORE opening;
      2. the pre-checked file's per-volume identity (``st_dev, st_ino`` —
         the NTFS file index, unique per file) is captured and the OPENED
         descriptor's ``fstat`` must match it exactly: a substitution of
         the path target between check and open — in or out of the root —
         cannot change identity undetected;
      3. ``fstat`` must report a regular file; one identity is captured,
         one open, one identity verification per read — nothing is cached.

    The check below the identity itself is deliberately strict: a volume
    that exposes no per-file identity (``st_ino`` == 0, e.g. FAT/exFAT)
    cannot enforce opened-file identity at all, so the read is refused
    there (fail closed). In-place content edits do not change the inode —
    they are bounded separately by the content-hash discipline of every
    consumer (claimed/recorded hash comparisons). Standard library only:
    no ctypes, no third-party dependency (ctypes is banned in this layer).
    """
    expected = str(Path(root).resolve() / rel)
    try:
        lst = os.lstat(expected)
    except FileNotFoundError:
        raise EvidenceViewError(f"Allowed source missing: {rel}")
    if getattr(lst, "st_file_attributes", 0) & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise EvidenceViewError(
            f"Refusing reparse point (symlink/junction) source: {rel}")
    pre_identity = (getattr(lst, "st_dev", None), getattr(lst, "st_ino", None))
    if not pre_identity[1]:
        raise EvidenceViewError(
            f"Source volume exposes no per-file identity (st_ino) for {rel}; "
            "opened-file identity cannot be enforced, so the read fails "
            "closed")
    flags = (os.O_RDONLY | getattr(os, "O_BINARY", 0)
             | getattr(os, "O_NOINHERIT", 0))
    fd = os.open(expected, flags)
    try:
        checked = os.fstat(fd)
        if (checked.st_dev, checked.st_ino) != pre_identity:
            raise EvidenceViewError(
                f"Opened file's identity differs from the pre-checked path "
                f"for {rel} (st_dev/st_ino {pre_identity!r} -> "
                f"{(checked.st_dev, checked.st_ino)!r}); a substitution "
                "between the check and the open was refused")
        return _fd_read_all(fd, rel)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _open_contained_bytes(root: Path, rel: str) -> bytes:
    """Containment + identity enforced on the file actually opened."""
    if os.name == "nt":
        return _windows_open_bytes(root, rel)
    if hasattr(os, "O_NOFOLLOW"):
        try:
            fd = _posix_chain_open_fd(root, rel)
            return _fd_read_all(fd, rel)
        except EvidenceViewError:
            raise
        except FileNotFoundError:
            raise EvidenceViewError(f"Allowed source missing: {rel}")
        except OSError as error:
            raise EvidenceViewError(
                f"Refusing source read {rel} (no-follow open failed: "
                f"{error})") from error
    raise EvidenceViewError(
        f"Refusing source read {rel}: this platform exposes neither the "
        "Windows post-open identity check nor POSIX O_NOFOLLOW "
        "descriptor-relative opens; the boundary cannot be enforced, so "
        "the read fails closed")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _matches(rel: str) -> bool:
    return (any(_pattern_matches(rel, pattern) for pattern in ALLOWED_SOURCE_PATTERNS)
            or rel in METADATA_ONLY_PATTERNS)


def _iter_source_paths(root: Path) -> Iterable[str]:
    """Existing allowlisted files, deterministically ordered (metadata-only
    patterns excluded — the dataset is never loaded while building a view)."""
    found: set[str] = set()
    root = Path(root).resolve()
    for pattern in ALLOWED_SOURCE_PATTERNS:
        if "*" in pattern:
            # Traverse one component at a time instead of Path.glob(pattern):
            # glob may follow a symlinked directory while enumerating matches.
            paths = [""]
            for component in pattern.split("/"):
                next_paths: list[str] = []
                for prefix in paths:
                    if "*" in component:
                        directory = (_resolved_path_inside_root(root, prefix)
                                     if prefix else root)
                        if not directory.is_dir():
                            continue
                        for child in sorted(directory.iterdir()):
                            if fnmatch.fnmatchcase(child.name, component):
                                next_paths.append("/".join(
                                    part for part in (prefix, child.name) if part))
                    else:
                        relative = "/".join(part for part in (prefix, component) if part)
                        next_paths.append(relative)
                paths = next_paths
            for relative in paths:
                if is_denied(relative):
                    continue
                resolved = _resolve_inside_root(root, relative)
                if resolved.is_file():
                    found.add(relative)
        else:
            candidate = _resolve_inside_root(root, pattern)
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
    dataset_path = _resolve_inside_root(root, dataset_rel)
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
    """Recorded hash of a cited source inside a built evidence view.

    The lookup folds case the same way the allowlist matcher does
    (``os.path.normcase``): on a case-insensitive filesystem a case-variant
    citation path resolves to the very same file, so it must resolve to the
    same recorded hash — otherwise staleness checks could be silently
    skipped by respelling a known path. Case-sensitive filesystems (POSIX)
    are unaffected: ``normcase`` is the identity there.
    """
    rel = _normalize(relative)
    key = os.path.normcase(rel)
    for row in view.get("sources", []):
        if os.path.normcase(str(row.get("path", ""))) == key:
            return row.get("sha256")
    if key == os.path.normcase(_normalize(DATASET_PATH)):
        return (view.get("dataset") or {}).get("sha256")
    return None
