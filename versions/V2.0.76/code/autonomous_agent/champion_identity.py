"""Champion identity reconciliation (state/registry divergence guard).

The canonical champion identity lives in ``CHAMPION.json``, cross-anchored by
the immutable ``versions/<V>/`` snapshot tree: ``version.json`` must restate
the same ``artifact_sha256`` and ``baseline_id``, and the parent named there
must itself be snapshot-anchored (``versions/<parent>/version.json`` and the
``parent_champion.json`` copy must agree on the parent artifact).

``agent_state.json`` carries only a *projection* of the champion for legacy
consumers (``core.Supervisor`` writes it; nothing in the wired proposal loop
reads it). Because the supervisor path was retired after Campaign 1 while the
loop kept promoting versions, that projection is never refreshed at runtime
and can drift arbitrarily far behind the live champion -- which is exactly
what happened (it pinned V2.0.8 while the champion advanced to V2.0.74).
Consumers reading it would see a seven-week-old champion as current.

This module therefore:

  * verifies the canonical champion against its snapshot chain (fail-closed:
    a canonical identity that cannot be verified is never used to rewrite
    anything);
  * detects real divergence in ``agent_state`` (a champion version that is
    unparseable, or *ahead of* the live champion -- a state that has no
    legitimate writer);
  * repairs the projection, retiring the stale value into
    ``champion_projection_history``. CHAMPION.json itself is never modified.

A projection that is merely *older* than the live champion is reported but
does not stop the loop: there is no legitimate writer that moves the
projection forward, so behindness is drift by design; forwardness/corruption
is a genuine anomaly.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

VERSION_RE = re.compile(r"^V(\d+)\.(\d+)\.(\d+)$")
_HISTORY_CAP = 10


class ChampionIdentityError(RuntimeError):
    """Raised when the canonical champion cannot be verified (fail-closed)."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_version(version: Any) -> tuple[int, int, int] | None:
    if not isinstance(version, str):
        return None
    match = VERSION_RE.match(version)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def _load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ChampionIdentityError(f"{path} is not valid JSON: {error}") from error


# ------------------------------------------------------------------ verification
def verify_canonical(root: Path) -> dict[str, Any]:
    """Verify CHAMPION.json against its versions/ snapshot chain.

    Returns ``{verified: bool, version, artifact_sha256, parent, checks,
    detail}``. A missing/unparseable component or any hash mismatch makes the
    whole verification fail; nothing downstream may then rewrite state from
    these sources.
    """
    root = Path(root)
    checks: dict[str, Any] = {}
    try:
        champion = _load_json(root / "CHAMPION.json")
    except (FileNotFoundError, ChampionIdentityError) as error:
        return {"verified": False, "checks": checks, "detail": str(error)}
    if not isinstance(champion, dict):
        return {"verified": False, "checks": checks,
                "detail": "CHAMPION.json is not a JSON object"}
    version = champion.get("version")
    parsed = parse_version(version)
    checks["champion_version_parseable"] = parsed is not None
    if parsed is None:
        return {"verified": False, "version": version, "checks": checks,
                "detail": f"CHAMPION.json version {version!r} is not a V2.0.N identity"}
    assert isinstance(version, str)

    artifact_sha = champion.get("artifact_sha256")
    checks["champion_has_artifact_sha256"] = isinstance(artifact_sha, str) \
        and len(artifact_sha) == 64
    if not checks["champion_has_artifact_sha256"]:
        return {"verified": False, "version": version, "checks": checks,
                "detail": "CHAMPION.json is missing a 64-hex artifact_sha256"}

    snapshot_path = root / "versions" / version / "version.json"
    try:
        snapshot = _load_json(snapshot_path)
    except (FileNotFoundError, ChampionIdentityError) as error:
        return {"verified": False, "version": version, "checks": checks,
                "detail": f"snapshot chain incomplete: {error}"}
    checks["snapshot_artifact_matches"] = \
        isinstance(snapshot, dict) and snapshot.get("artifact_sha256") == artifact_sha
    baseline = champion.get("baseline_id")
    checks["snapshot_baseline_matches"] = (baseline is None) or (
        isinstance(snapshot, dict) and snapshot.get("baseline_id") == baseline)
    if not (checks["snapshot_artifact_matches"]
            and checks["snapshot_baseline_matches"]):
        return {"verified": False, "version": version, "checks": checks,
                "detail": (
                    f"versions/{version}/version.json does not restate the "
                    "CHAMPION.json artifact/baseline")}

    parent = champion.get("parent_champion")
    if isinstance(parent, str) and parse_version(parent) is not None:
        parent_snapshot_path = root / "versions" / parent / "version.json"
        try:
            parent_snapshot = _load_json(parent_snapshot_path)
        except (FileNotFoundError, ChampionIdentityError) as error:
            return {"verified": False, "version": version, "checks": checks,
                    "detail": f"parent snapshot broken: {error}"}
        parent_copy_path = root / "versions" / version / "parent_champion.json"
        try:
            parent_copy = _load_json(parent_copy_path)
        except (FileNotFoundError, ChampionIdentityError) as error:
            return {"verified": False, "version": version, "checks": checks,
                    "detail": f"parent-champion copy broken: {error}"}
        checks["parent_version_parseable"] = parse_version(parent) is not None
        checks["parent_copy_matches_parent"] = (
            isinstance(parent_copy, dict)
            and parent_copy.get("version") == parent)
        parent_artifact = (parent_snapshot.get("artifact_sha256")
                           if isinstance(parent_snapshot, dict) else None)
        checks["parent_artifact_anchored"] = (
            isinstance(parent_copy, dict)
            and parent_copy.get("artifact_sha256") == parent_artifact
            and parent_artifact is not None)
        checks["parent_is_older"] = parse_version(parent) < parsed  # type: ignore[operator]
        if not all(checks[key] for key in (
                "parent_copy_matches_parent", "parent_artifact_anchored",
                "parent_is_older")):
            return {"verified": False, "version": version, "checks": checks,
                    "detail": f"parent snapshot chain for {parent} does not anchor"}

    return {"verified": True, "version": version, "artifact_sha256": artifact_sha,
            "parent": parent, "checks": checks, "detail": "canonical champion verified"}


def projection_of(champion: Mapping[str, Any]) -> dict[str, Any]:
    """A compact, refreshable projection consumed by legacy readers."""
    projection = {key: champion.get(key) for key in (
        "version", "artifact_sha256", "parent_champion", "created_at",
        "baseline_id", "baseline_kind", "dataset_id", "dataset_sha256",
        "experiment_id", "holdout_policy")}
    projection["projection"] = {
        "kind": "champion_identity.v1",
        "note": "Derived from CHAMPION.json and refreshed by "
                "autonomous_agent.champion_identity; not a full release "
                "record. The authoritative record is versions/<version>/.",
    }
    return projection


# ------------------------------------------------------------------- divergence
def check_divergence(root: Path, state_root: Path) -> str | None:
    """Return a detail string if agent_state's champion is genuinely corrupt.

    ``None`` means: no divergence the loop must stop for. Unreadable files
    return None here (the loop's own CHAMPION_UNREADABLE / state-recovery
    stops cover those), so this check narrowly owns the identity question.
    """
    root, state_root = Path(root), Path(state_root)
    try:
        canonical_version = _load_json(root / "CHAMPION.json").get("version")
    except (FileNotFoundError, ChampionIdentityError, AttributeError):
        return None
    canonical = parse_version(canonical_version)
    if canonical is None:
        return None
    state_path = state_root / "agent_state.json"
    if not state_path.is_file():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict):
        return None
    champion = state.get("champion")
    if not isinstance(champion, dict):
        return None
    state_version = champion.get("version")
    if state_version == canonical_version:
        return None
    state_parsed = parse_version(state_version)
    if state_parsed is None:
        return f"agent_state.champion.version {state_version!r} is not a " \
               f"valid champion identity next to live {canonical_version}"
    if state_parsed > canonical:
        return (f"agent_state.champion {state_version} is ahead of the live "
                f"CHAMPION.json {canonical_version}; no legitimate writer can "
                "produce that state")
    return None  # behind-by-design projection: drift, not divergence


# ------------------------------------------------------------------ reconcile
def reconcile(root: Path, state_root: Path, *, apply: bool = False,
              now: Any = _utc_now) -> dict[str, Any]:
    """Align agent_state's champion projection with the verified canonical.

    Verifies the canonical champion first (fail-closed: refusal to touch
    state when the identity cannot be proven). With ``apply`` the stale
    projection is retired into ``champion_projection_history`` (capped) and a
    compact projection of CHAMPION.json is written.
    """
    root, state_root = Path(root), Path(state_root)
    verification = verify_canonical(root)
    if not verification["verified"]:
        return {"status": "refused", "verification": verification,
                "detail": "canonical champion could not be verified; "
                          "agent_state was left untouched"}
    canonical_version = str(verification["version"])
    state_path = state_root / "agent_state.json"
    if not state_path.is_file():
        return {"status": "no_state", "verification": verification,
                "detail": "agent_state.json absent; nothing to reconcile"}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"status": "refused", "verification": verification,
                "detail": f"agent_state.json unreadable: {error}; "
                          "agent_state was left untouched"}
    if not isinstance(state, dict):
        return {"status": "refused", "verification": verification,
                "detail": "agent_state.json is not a JSON object"}
    champion = state.get("champion")
    if isinstance(champion, dict) and champion.get("version") == canonical_version:
        return {"status": "consistent", "verification": verification,
                "detail": f"agent_state champion already {canonical_version}"}
    before = champion.get("version") if isinstance(champion, dict) else None
    if apply:
        champion = state["champion"] = projection_of(json.loads(
            (root / "CHAMPION.json").read_text(encoding="utf-8")))
        champion["projection"]["reconciled_at"] = now()
        if before is not None:
            history = state.setdefault("champion_projection_history", [])
            history = [entry for entry in history if isinstance(entry, dict)]
            history.append({"retired_at": now(), "reason": (
                f"stale projection {before!r} replaced by verified "
                f"{canonical_version}"), "champion": {"version": before}})
            state["champion_projection_history"] = history[-_HISTORY_CAP:]
        if not isinstance(state.get("schema_version"), int):
            state.setdefault("schema_version", 1)
        write_state_atomic(state_path, state)
        return {"status": "reconciled", "before": before, "after": canonical_version,
                "verification": verification,
                "detail": f"projection refreshed {before!r} -> {canonical_version}"}
    return {"status": "stale", "before": before, "after": canonical_version,
            "verification": verification,
            "detail": f"agent_state champion {before!r} is stale "
                      f"(live: {canonical_version}); pass apply=True to repair"}


def write_state_atomic(path: Path, state: dict[str, Any]) -> None:
    """Atomic JSON write with Windows-safe re-protection (same pattern as core)."""
    body = json.dumps(state, indent=1, sort_keys=True) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(body, encoding="utf-8", newline="")
        os_replace(tmp, path)
    except PermissionError:
        # Windows: a concurrent reader may hold the destination open briefly.
        os_replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def os_replace(source: Path, destination: Path) -> None:
    import os
    os.replace(source, destination)


# ------------------------------------------------- snapshot post-hoc verification
def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_sha256(path: Path) -> str:
    """Same deterministic algorithm as core.tree_sha256 (kept import-free here
    to avoid pulling the whole adapter stack into a small state utility)."""
    digest = hashlib.sha256()
    entries = sorted(path.rglob("*"))
    if any(item.is_symlink() for item in entries):
        raise ChampionIdentityError("Snapshot trees may not contain symlinks.")
    for file_path in (item for item in entries if item.is_file()):
        relative = file_path.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(bytes.fromhex(_sha256_file(file_path)))
    return digest.hexdigest()


def verify_snapshot_code(root: Path, version: str) -> dict[str, Any]:
    """Re-derive a promoted snapshot's code tree hash from its recorded anchor.

    ``versions/<V>/version.json`` records ``artifact_sha256`` = the promotion-
    time tree hash of ``versions/<V>/code``. Recomputing it detects any post-
    promotion tampering of a frozen snapshot — the one integrity property the
    ``original_fingerprint`` boundary intentionally does NOT provide: that
    fingerprint excludes ``versions/`` by design (performance; snapshots are
    promotion-time-verified agent *output*), so post-hoc snapshot integrity
    must come from the snapshot's own recorded anchor, not from the original-
    tree fingerprint. One version per call keeps the cost bounded (~one
    snapshot tree, not the whole archive).
    """
    root = Path(root)
    snapshot_dir = root / "versions" / version
    version_json = snapshot_dir / "version.json"
    try:
        manifest = _load_json(version_json)
    except (FileNotFoundError, ChampionIdentityError) as error:
        return {"verified": False, "version": version, "detail": str(error)}
    recorded = (manifest.get("artifact_sha256") if isinstance(manifest, dict)
                else None)
    if not isinstance(recorded, str) or len(recorded) != 64:
        return {"verified": False, "version": version,
                "detail": "version.json does not record a 64-hex artifact_sha256"}
    code_dir = snapshot_dir / "code"
    if not code_dir.is_dir():
        return {"verified": False, "version": version,
                "detail": "snapshot has no code/ tree to hash"}
    try:
        actual = _tree_sha256(code_dir)
    except ChampionIdentityError as error:
        return {"verified": False, "version": version, "detail": str(error)}
    ok = actual == recorded
    return {"verified": ok, "version": version,
            "recorded_sha256": recorded, "actual_sha256": actual,
            "detail": ("snapshot code tree matches its recorded anchor"
                       if ok else
                       f"snapshot code tree {actual[:16]}.. does not match "
                       f"the recorded anchor {recorded[:16]}..")}
