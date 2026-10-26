"""Tests for the proposed gate guards. Fixtures live in temp dirs; the real
gate record is only read, never written."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_agent import gate_enforcement as ge
from autonomous_agent import launch_readiness_check as lrc

REAL_ROOT = Path(__file__).resolve().parents[3]  # repository root: dev/autonomous_agent -> dev -> .model_discovery_workspace -> repo (read-only use)


def _gates(root: Path, *, omit: str | None = None, decided_false: str | None = None) -> Path:
    evidence = root / "evidence.md"
    evidence.write_text("evidence", encoding="utf-8")
    data = {}
    for name, _ in lrc.HUMAN_GATES:
        if name == omit:
            continue
        data[name] = {"decided": name != decided_false, "decided_by": "owner",
                      "date": "2026-10-17", "evidence_path": "evidence.md"}
    path = root / "gates.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class HumanGateGuard(unittest.TestCase):
    def test_all_gates_recorded_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ge.require_human_gates(root, _gates(root))

    def test_missing_gate_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ge.GateError):
                ge.require_human_gates(root, _gates(root, omit="review_received"))

    def test_undecided_gate_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ge.GateError):
                ge.require_human_gates(root, _gates(root, decided_false="launch_authorized"))

    def test_absent_gate_file_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ge.GateError):
                ge.require_human_gates(Path(tmp), Path(tmp) / "missing.json")

    def test_malformed_gate_file_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / "gates.json"
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ge.GateError):
                ge.require_human_gates(root, bad)

    def test_real_gate_record_is_read_only_checked(self) -> None:
        # Read-only: reports what the guard WOULD decide today. Does not write.
        gates = REAL_ROOT / "stat_validation_h10/launch_gates.json"
        if not gates.is_file():
            self.skipTest("real gate record not present")
        before = gates.read_bytes()
        try:
            ge.require_human_gates(REAL_ROOT, gates)
            outcome = "passes (all gates recorded)"
        except ge.GateError as error:
            outcome = f"refuses: {error}"
        self.assertEqual(before, gates.read_bytes())
        print("\n[real gate record] guard outcome:", outcome[:200])


class AutoApprovalGuard(unittest.TestCase):
    def test_human_approval_on_needs_nothing(self) -> None:
        ge.require_authorized_auto_approval(".", {}, {"require_human_approval": True})

    def test_auto_approval_without_record_refuses(self) -> None:
        with self.assertRaises(ge.GateError):
            ge.require_authorized_auto_approval(".", {}, {"require_human_approval": False})

    def test_auto_approval_with_missing_evidence_refuses(self) -> None:
        campaign = {"auto_approval_authorization": {
            "evidence_path": "nope.md", "decided_by": "owner", "date": "2026-10-17"}}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ge.GateError):
                ge.require_authorized_auto_approval(tmp, campaign,
                                                    {"require_human_approval": False})

    def test_auto_approval_with_named_record_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "auth.md").write_text("owner authorization", encoding="utf-8")
            campaign = {"auto_approval_authorization": {
                "evidence_path": "auth.md", "decided_by": "owner", "date": "2026-10-17"}}
            ge.require_authorized_auto_approval(tmp, campaign,
                                                {"require_human_approval": False})


if __name__ == "__main__":
    unittest.main()
