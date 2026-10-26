"""Integrity-boundary tests for original_fingerprint and snapshot anchors.

The performance fix excluded ``versions/`` from the original-tree
fingerprint (13 h/cycle -> minutes). These tests pin the boundary: the
exclusion must stay a closed allowlist, must never cover protected source
paths, and post-promotion snapshot integrity must come from each snapshot's
own recorded ``artifact_sha256`` anchor — not from the exclusion-based
fingerprint.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from autonomous_agent.champion_identity import verify_snapshot_code
from autonomous_agent.experiment_adapter import ExperimentAdapter

WORKSPACE = Path(__file__).resolve().parents[1]


def make_tree(root: Path) -> None:
    (root / "study_files/backend").mkdir(parents=True, exist_ok=True)
    (root / "study_files/backend/study.py").write_text("print('v1')\n",
                                                        encoding="utf-8")
    (root / "versions/V2.0.74").mkdir(parents=True, exist_ok=True)
    (root / "versions/V2.0.74/snapshot.json").write_text("immutably stored\n",
                                                         encoding="utf-8")


def adapter_for(root: Path) -> ExperimentAdapter:
    return ExperimentAdapter(root=root, candidates_root=root / "candidates",
                             state_root=root / "autonomous_agent/state")


def test_protected_change_detected_despite_versions_exclusion(tmp_path: Path) -> None:
    make_tree(tmp_path)
    adapter = adapter_for(tmp_path)
    before = adapter.original_fingerprint()
    (tmp_path / "study_files/backend/study.py").write_text("print('v2')\n",
                                                            encoding="utf-8")
    assert adapter.original_fingerprint() != before
    (tmp_path / "study_files/backend/study.py").write_text("print('v1')\n",
                                                            encoding="utf-8")
    assert adapter.original_fingerprint() == before  # restorable -> deterministic


def test_versions_tampering_is_out_of_boundary_but_snapshot_verifiable(
        tmp_path: Path) -> None:
    """Documents the intended split: the original-tree fingerprint is
    unchanged by snapshot edits; snapshot integrity is owned by the recorded
    anchor, which detects the tamper."""
    make_tree(tmp_path)
    snapshot = tmp_path / "versions/V2.0.74/code"
    snapshot.mkdir(parents=True, exist_ok=True)
    (snapshot / "module.py").write_text("a = 1\n", encoding="utf-8")
    # Anchor is computed from the file's actual bytes (independent of the
    # hashing module under test), mirroring the promotion-time anchor format.
    relative = b"module.py"
    payload = (snapshot / "module.py").read_bytes()
    recorded = hashlib.sha256()
    recorded.update(len(relative).to_bytes(8, "big"))
    recorded.update(relative)
    recorded.update(bytes.fromhex(hashlib.sha256(payload).hexdigest()))
    (tmp_path / "versions/V2.0.74/version.json").write_text(json.dumps(
        {"artifact_sha256": recorded.hexdigest()}), encoding="utf-8")
    anchor = adapter_for(tmp_path).original_fingerprint()
    (snapshot / "module.py").write_text("a = 2\n", encoding="utf-8")
    assert adapter_for(tmp_path).original_fingerprint() == anchor
    report = verify_snapshot_code(tmp_path, "V2.0.74")
    assert report["verified"] is False
    (snapshot / "module.py").write_text("a = 1\n", encoding="utf-8")
    assert verify_snapshot_code(tmp_path, "V2.0.74")["verified"] is True


def test_snapshot_without_recorded_anchor_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "versions/V9.9.9").mkdir(parents=True, exist_ok=True)
    (tmp_path / "versions/V9.9.9/version.json").write_text(json.dumps(
        {"artifact_sha256": "too-short"}), encoding="utf-8")
    report = verify_snapshot_code(tmp_path, "V9.9.9")
    assert report["verified"] is False


def test_exclusion_boundary_is_a_closed_allowlist() -> None:
    adapter = adapter_for(WORKSPACE)
    exclusions = adapter._fingerprint_exclusions()
    allowed = {
        "autonomous_agent/state",        # runtime state, never source
        "autonomous_agent/candidates",   # agent output, never source
        "autonomous_agent/BASELINE_REPRODUCTION_REPORT.md",
        "autonomous_agent/BASELINE_RECONSTRUCTED_REPORT.md",
    }
    assert set(exclusions) == allowed
    for item in exclusions:
        assert item.startswith("autonomous_agent/") and \
            not item.startswith("autonomous_agent/proposal_layer") and \
            not item.startswith("autonomous_agent/experiments")


def test_heartbeat_preserves_hash_and_emits_final_beat(tmp_path: Path) -> None:
    make_tree(tmp_path)
    adapter = adapter_for(tmp_path)
    baseline = adapter.original_fingerprint()
    beats: list[dict] = []
    withheartbeat = adapter.original_fingerprint(
        progress_callback=beats.append, heartbeat_seconds=0.0)
    assert withheartbeat == baseline
    assert beats, "heartbeat callback must fire"
    assert beats[-1]["final"] is True
    assert all(b["event"] == "original_fingerprint_heartbeat" for b in beats)
    files = beats[-1]["files_hashed"]
    assert files == 1  # study file only: versions/ and candidates/ excluded
    assert beats[-1]["last_path"].endswith("study_files/backend/study.py")


def test_heartbeat_callback_errors_propagate(tmp_path: Path) -> None:
    make_tree(tmp_path)
    adapter = adapter_for(tmp_path)
    def boom(_payload: dict) -> None:
        raise RuntimeError("listener failure")
    try:
        adapter.original_fingerprint(progress_callback=boom,
                                     heartbeat_seconds=0.0)
    except RuntimeError:
        pass
    else:  # pragma: no cover - fail-closed contract
        raise AssertionError("callback errors must propagate")


@pytest.mark.skipif(not (WORKSPACE / "CHAMPION.json").is_file(),
                    reason="live checkout unavailable")
def test_live_champion_snapshot_matches_recorded_anchor() -> None:
    """Era-pinned, bounded: exactly one snapshot tree is re-hashed — the live
    champion's — and its code tree must match the promotion-time anchor."""
    import sys
    sys.path.insert(0, str(WORKSPACE))
    from autonomous_agent.champion_identity import verify_canonical
    champion = json.loads((WORKSPACE / "CHAMPION.json").read_text(
        encoding="utf-8"))
    version = str(champion.get("version"))
    assert verify_canonical(WORKSPACE)["verified"] is True
    report = verify_snapshot_code(WORKSPACE, version)
    assert report["verified"] is True, report["detail"]
