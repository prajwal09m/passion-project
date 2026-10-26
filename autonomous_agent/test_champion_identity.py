"""Tests for champion identity reconciliation (state/registry divergence).

Synthetic tests build a minimal but structurally faithful tree (CHAMPION.json
+ versions/<V>/{version.json,parent_champion.json} + agent_state.json). The
live test is era-pinned to this checkout's real state, where reconciliation
is expected to move the stale V2.0.8 projection to the live champion.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from autonomous_agent.champion_identity import (
    ChampionIdentityError,
    check_divergence,
    reconcile,
    verify_canonical,
)


def state_root_of(root: Path) -> Path:
    return root / "autonomous_agent" / "state"

WORKSPACE = Path(__file__).resolve().parents[1]

CLOCK = lambda: "2026-10-25T00:00:00+00:00"  # noqa: E731 - deterministic stamp


def make_tree(root: Path, *,
              canonical_version: str = "V2.0.74",
              parent_version: str = "V2.0.73",
              artifact: str = "a" * 64,
              parent_artifact: str = "p" * 64) -> None:
    (root / "versions" / canonical_version).mkdir(parents=True, exist_ok=True)
    (root / "versions" / parent_version).mkdir(parents=True, exist_ok=True)
    (root / "versions" / canonical_version / "version.json").write_text(
        json.dumps({"artifact_sha256": artifact,
                    "baseline_id": "BASELINE_RECONSTRUCTED_2026_10"}),
        encoding="utf-8")
    (root / "versions" / canonical_version / "parent_champion.json").write_text(
        json.dumps({"version": parent_version,
                    "artifact_sha256": parent_artifact}), encoding="utf-8")
    (root / "versions" / parent_version / "version.json").write_text(
        json.dumps({"artifact_sha256": parent_artifact}), encoding="utf-8")
    (root / "CHAMPION.json").write_text(json.dumps({
        "version": canonical_version, "artifact_sha256": artifact,
        "parent_champion": parent_version,
        "baseline_id": "BASELINE_RECONSTRUCTED_2026_10",
        "dataset_sha256": "d" * 64,
        "holdout_policy": {"status": "SEALED", "uses": 0},
        "created_at": "2026-10-25T14:31:56+00:00",
    }, indent=1), encoding="utf-8")


def write_agent_state(root: Path, version: str | None, *,
                      artifact: str = "s" * 64) -> None:
    state_dir = root / "autonomous_agent" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = {"schema_version": 1, "experiments": []}
    if version is not None:
        state["champion"] = {"version": version, "artifact_sha256": artifact}
    (state_dir / "agent_state.json").write_text(json.dumps(state, indent=1),
                                                encoding="utf-8")


def test_canonical_tree_verifies(tmp_path: Path) -> None:
    make_tree(tmp_path)
    report = verify_canonical(tmp_path)
    assert report["verified"] is True
    assert report["version"] == "V2.0.74"
    assert report["parent"] == "V2.0.73"


def test_broken_snapshot_fails_closed(tmp_path: Path) -> None:
    make_tree(tmp_path)
    path = tmp_path / "versions" / "V2.0.74" / "version.json"
    path.write_text(json.dumps({"artifact_sha256": "f" * 64}),
                    encoding="utf-8")
    report = verify_canonical(tmp_path)
    assert report["verified"] is False
    assert "restate" in report["detail"]


def test_broken_parent_anchor_fails_closed(tmp_path: Path) -> None:
    make_tree(tmp_path)
    path = tmp_path / "versions" / "V2.0.73" / "version.json"
    path.write_text(json.dumps({"artifact_sha256": "q" * 64}),
                    encoding="utf-8")
    report = verify_canonical(tmp_path)
    assert report["verified"] is False
    assert "parent" in report["detail"]


def test_missing_champion_fails_closed(tmp_path: Path) -> None:
    report = verify_canonical(tmp_path)
    assert report["verified"] is False


def test_stale_projection_is_drift_not_divergence(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write_agent_state(tmp_path, "V2.0.8")
    assert check_divergence(tmp_path, state_root_of(tmp_path)) is None


def test_ahead_of_canonical_is_divergence(tmp_path: Path) -> None:
    make_tree(tmp_path, canonical_version="V2.0.10",
              parent_version="V2.0.9")
    write_agent_state(tmp_path, "V2.0.74")
    detail = check_divergence(tmp_path, state_root_of(tmp_path))
    assert detail is not None and "ahead" in detail


def test_corrupt_projection_is_divergence(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write_agent_state(tmp_path, "banana")
    assert check_divergence(tmp_path, state_root_of(tmp_path)) is not None


def test_current_projection_is_not_divergence(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write_agent_state(tmp_path, "V2.0.74")
    assert check_divergence(tmp_path, state_root_of(tmp_path)) is None


def test_missing_state_or_no_champion_is_not_divergence(tmp_path: Path) -> None:
    make_tree(tmp_path)
    assert check_divergence(tmp_path, state_root_of(tmp_path)) is None
    write_agent_state(tmp_path, None)
    assert check_divergence(tmp_path, state_root_of(tmp_path)) is None


def test_dry_run_does_not_touch_state(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write_agent_state(tmp_path, "V2.0.8")
    report = reconcile(tmp_path, state_root_of(tmp_path), apply=False, now=CLOCK)
    assert report["status"] == "stale"
    state = json.loads((tmp_path / "autonomous_agent/state/agent_state.json")
                       .read_text(encoding="utf-8"))
    assert state["champion"]["version"] == "V2.0.8"
    assert "champion_projection_history" not in state


def test_reconcile_repairs_and_retires_history(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write_agent_state(tmp_path, "V2.0.8")
    report = reconcile(tmp_path, state_root_of(tmp_path), apply=True, now=CLOCK)
    assert report["status"] == "reconciled"
    assert report["before"] == "V2.0.8" and report["after"] == "V2.0.74"
    state = json.loads((tmp_path / "autonomous_agent/state/agent_state.json")
                       .read_text(encoding="utf-8"))
    assert state["champion"]["version"] == "V2.0.74"
    assert state["champion"]["parent_champion"] == "V2.0.73"
    assert state["champion"]["holdout_policy"] == {"status": "SEALED", "uses": 0}
    history = state["champion_projection_history"]
    assert len(history) == 1 and history[0]["champion"]["version"] == "V2.0.8"
    assert "CHAMPION.json" not in state["champion"]


def test_reconcile_then_consistent_no_history_growth(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write_agent_state(tmp_path, "V2.0.8")
    reconcile(tmp_path, state_root_of(tmp_path), apply=True, now=CLOCK)
    second = reconcile(tmp_path, state_root_of(tmp_path), apply=True, now=CLOCK)
    assert second["status"] == "consistent"
    state = json.loads((tmp_path / "autonomous_agent/state/agent_state.json")
                       .read_text(encoding="utf-8"))
    assert len(state["champion_projection_history"]) == 1


def test_reconcile_history_capped(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write_agent_state(tmp_path, None)
    state_path = tmp_path / "autonomous_agent/state/agent_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["champion"] = {"version": "V999.0.0"}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    report = reconcile(tmp_path, state_root_of(tmp_path), apply=True, now=CLOCK)
    # V999.0.0 is a parseable version, so verify_canonical does not object;
    # the retirement path must still cap the history instead of growing.
    assert report["status"] == "reconciled"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert len(state["champion_projection_history"]) <= 10


def test_reconcile_refuses_when_canonical_unverifiable(tmp_path: Path) -> None:
    make_tree(tmp_path)
    write_agent_state(tmp_path, "V2.0.8")
    # Break the snapshot: reconciliation must refuse, not trust CHAMPION.json.
    (tmp_path / "versions" / "V2.0.74" / "version.json").write_text(
        json.dumps({"artifact_sha256": "f" * 64}), encoding="utf-8")
    report = reconcile(tmp_path, tmp_path, apply=True, now=CLOCK)
    assert report["status"] == "refused"
    state = json.loads((tmp_path / "autonomous_agent/state/agent_state.json")
                       .read_text(encoding="utf-8"))
    assert state["champion"]["version"] == "V2.0.8"  # untouched


def test_reconcile_refuses_corrupt_agent_state(tmp_path: Path) -> None:
    make_tree(tmp_path)
    state_dir = tmp_path / "autonomous_agent" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "agent_state.json").write_text("{not json", encoding="utf-8")
    report = reconcile(tmp_path, state_root_of(tmp_path), apply=True, now=CLOCK)
    assert report["status"] == "refused"


@pytest.mark.skipif(not (WORKSPACE / "CHAMPION.json").is_file(),
                    reason="live checkout unavailable")
def test_live_projection_reconciles_to_live_champion() -> None:
    """Era-pinned: in this checkout the stale projection must reach the live
    champion after a verified reconciliation, and no divergence may remain.
    """
    champion = json.loads((WORKSPACE / "CHAMPION.json").read_text(
        encoding="utf-8"))
    live = str(champion.get("version"))
    assert isinstance(live, str) and live.startswith("V2.")
    verification = verify_canonical(WORKSPACE)
    assert verification["verified"] is True, verification["detail"]
    state_root = WORKSPACE / "autonomous_agent" / "state"
    report = reconcile(WORKSPACE, state_root, apply=True)
    assert report["status"] in ("consistent", "reconciled", "no_state"), report
    assert report["verification"] == verification or \
        report["status"] == "no_state"
    state_path = state_root / "agent_state.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(state.get("champion"), dict):
            assert state["champion"]["version"] == live
    assert check_divergence(WORKSPACE, state_root) is None
