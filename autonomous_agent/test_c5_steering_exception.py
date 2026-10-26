"""Pinned behavior of the owner-signed C5 steering exception (Option A).

The exception admits exactly the 5 predeclared error-cluster axis rows
(exploration class, error_analysis direction) through the post-creation
falsification-share steering rule, strictly scoped by
``C5_STEERING_EXCEPTION_DECISION_A_2026_10_25.json`` + its sha256 pin.
Everything this file pins is fail-closed: any byte change to the record
fails loudly here, and any scope change disables the exception instead of
widening it.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from autonomous_agent.proposal_layer import cycle
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor
from autonomous_agent.proposal_layer.generator import _project_quota_state
from autonomous_agent.proposal_layer import schema

WORKSPACE = Path(__file__).resolve().parents[1]
RECORD_REL = Path(cycle.C5_EXCEPTION_RECORD_RELATIVE_PATH)


def _repo_record_bytes() -> bytes:
    return (WORKSPACE / RECORD_REL).read_bytes()


def _fixture_root(record_bytes: bytes | None = None,
                  pin_bytes: str | None = None) -> tuple[Path, Path]:
    """Tmp workspace root with the (optionally altered) record + pin."""
    tmp = Path(tempfile.mkdtemp(prefix="c5_exception_test_"))
    root = tmp / "ws"
    (root / "autonomous_agent" / "state").mkdir(parents=True, exist_ok=True)
    dest = root / RECORD_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    if record_bytes is None:
        record_bytes = _repo_record_bytes()
    dest.write_bytes(record_bytes)
    if pin_bytes is None:
        pin_bytes = (hashlib.sha256(record_bytes).hexdigest() + "\n"
                     + dest.name + "\n")
    (root / cycle.C5_EXCEPTION_PIN_RELATIVE_PATH).write_text(
        pin_bytes, encoding="utf-8")
    (root / "autonomous_agent" / "state" / "campaign_config.json").write_text(
        json.dumps({"campaign_id":
                    "campaign-5-regime-error-analysis-2026-10-22",
                    "policy_overrides": {
                        # Campaign-5 class budgets: scoped so the steering
                        # tests below reach the share rule, not the class
                        # budget (mirrors the frozen real config).
                        "class_budgets": {"confirmatory": 12,
                                          "exploration": 16,
                                          "falsification": 24,
                                          "replication": 8},
                        "max_per_direction": 15,
                        "max_total_proposals": 45}}),
        encoding="utf-8")
    return root, dest


class SteeringExceptionTests(unittest.TestCase):
    # Repo-level tamper evidence: the shipped record must hash to its pin.
    def test_shipped_record_matches_its_pin(self) -> None:
        record_bytes = _repo_record_bytes()
        pin = (WORKSPACE / cycle.C5_EXCEPTION_PIN_RELATIVE_PATH).read_text(
            encoding="utf-8").strip().splitlines()[0].strip()
        self.assertEqual(hashlib.sha256(record_bytes).hexdigest(), pin)

    def test_shipped_record_binds_the_declared_scope(self) -> None:
        record = json.loads(_repo_record_bytes().decode("utf-8"))
        self.assertEqual(record["decision"], "Option A")
        self.assertEqual(record["campaign_id"],
                         "campaign-5-regime-error-analysis-2026-10-22")
        self.assertEqual(record["primitive_id"], "error_clustering_analysis")
        self.assertEqual(record["proposal_class"], "exploration")
        self.assertEqual(record["axes"], [
            "vix_regime", "first_retest", "volume_confirmation",
            "departure_magnitude", "departure_candle_direction"])
        self.assertEqual((record["per_axis_limit"], record["total_rows_limit"]),
                         (1, 5))

    def test_load_policy_injects_exception_for_scoped_campaign(self) -> None:
        root, _ = _fixture_root()
        policy = cycle._load_policy(root)
        exception = policy.get("c5_steering_exception")
        self.assertIsNotNone(exception)
        self.assertEqual(len(exception["design_signatures"]), 5)
        # The signatures must be exactly the 5 axis signatures computed the
        # same deterministic way the generator computes them.
        expected = [
            schema.design_signature(
                primitive_ids=("error_clustering_analysis",),
                params={"error_cluster_axis": axis})
            for axis in record_axes()]
        self.assertEqual(sorted(exception["design_signatures"]),
                         sorted(expected))

    def test_exception_admits_predeclared_axis_row_despite_share_floor(self):
        root, _ = _fixture_root()
        policy = cycle._load_policy(root)
        governor = BiasGovernor(policy)
        exception = policy["c5_steering_exception"]
        base_state = {
            "total": 23,
            "by_class": {"confirmatory": 10, "exploration": 3,
                         "falsification": 7, "replication": 3},
            "by_direction": {"validation": 15},
            "by_signature": {},
        }
        signature = exception["design_signatures"][0]
        projected = _project_quota_state(
            base_state, direction="error_analysis",
            proposal_class="exploration", signature=signature)
        ok, reason, detail = governor.check_accept(
            {"proposal_class": "exploration", "direction": "error_analysis",
             "design_signature": signature}, projected)
        self.assertTrue(ok)
        self.assertIsNone(reason)
        # Disclosure must ride in the admission detail (ledger provenance).
        self.assertIn("c5_steering_exception", detail)
        self.assertIn("C5_STEERING_EXCEPTION_A_2026_10_25", detail)

    def test_non_exception_exploration_still_refused(self):
        root, _ = _fixture_root()
        policy = cycle._load_policy(root)
        governor = BiasGovernor(policy)
        base_state = {
            "total": 23,
            "by_class": {"confirmatory": 10, "exploration": 3,
                         "falsification": 7, "replication": 3},
            "by_direction": {},
            "by_signature": {},
        }
        projected = _project_quota_state(
            base_state, direction="calibration",
            proposal_class="exploration", signature="some-unlisted-signature")
        ok, reason, _ = governor.check_accept(
            {"proposal_class": "exploration", "direction": "calibration",
             "design_signature": "some-unlisted-signature"}, projected)
        self.assertFalse(ok)
        self.assertEqual(reason, schema.RC_BIAS_QUOTA)

    def test_per_axis_recreation_refused_after_failed_attempt(self):
        root, _ = _fixture_root()
        policy = cycle._load_policy(root)
        governor = BiasGovernor(policy)
        exception = policy["c5_steering_exception"]
        signature = exception["design_signatures"][0]
        # One record of this axis already exists in the ledger (its creation
        # failed validation later): the ledger keeps failed records, so any
        # re-creation projects count 2 > per_axis_limit 1.
        base_state = {
            "total": 23,
            "by_class": {"falsification": 7},
            "by_direction": {},
            "by_signature": {signature: 1},
        }
        state = _project_quota_state(
            base_state, direction="error_analysis",
            proposal_class="exploration", signature=signature)
        ok, reason, _ = governor.check_accept(
            {"proposal_class": "exploration", "direction": "error_analysis",
             "design_signature": signature}, state)
        self.assertFalse(ok)
        self.assertEqual(reason, schema.RC_BIAS_QUOTA)

    def test_total_rows_limit_blocks_admission(self):
        root, _ = _fixture_root()
        policy = cycle._load_policy(root)
        governor = BiasGovernor(policy)
        # Only the in-memory copy is altered here: this pins the helper's
        # grant accounting (state rows > limit => refuse). The shipped
        # record's limits are pinned separately in test_shipped_record_binds
        # _the_declared_scope.
        exception = dict(policy["c5_steering_exception"])
        exception["total_rows_limit"] = 4
        state = {
            "total": 27,
            "by_class": {"exploration": 8, "falsification": 7},
            "by_direction": {},
            "by_signature": {sig: 1 for sig in exception["design_signatures"]},
        }
        self.assertFalse(governor._exception_admits(
            {"proposal_class": "exploration",
             "design_signature": exception["design_signatures"][0]},
            state, exception))

    def test_tampered_record_bytes_fail_loudly(self):
        record_bytes = _repo_record_bytes().replace(b"Option A", b"Option Z")
        root, _ = _fixture_root(record_bytes=record_bytes)  # pin recomputed
        with self.assertRaises(ValueError):
            cycle._load_policy(root)

    def test_stale_pin_fails_loudly(self):
        stale = "0" * 64 + "\nshipped_pinned_name.json\n"
        root, _ = _fixture_root(pin_bytes=stale)
        with self.assertRaises(ValueError):
            cycle._load_policy(root)

    def test_missing_pin_file_fails_loudly(self):
        root, dest = _fixture_root()
        (root / cycle.C5_EXCEPTION_PIN_RELATIVE_PATH).unlink()
        with self.assertRaises(ValueError):
            cycle._load_policy(root)

    def test_unparseable_record_with_matching_pin_fails_loudly(self):
        broken = b"{not json"
        root, _ = _fixture_root(record_bytes=broken)
        with self.assertRaises(ValueError):
            cycle._load_policy(root)

    def test_other_campaign_record_disables_exception_without_raising(self):
        rebuilt = json.loads(_repo_record_bytes().decode("utf-8"))
        rebuilt["campaign_id"] = "campaign-4-reconstruction-2026-10-10"
        root, _ = _fixture_root()  # valid frozen record for campaign-5
        # A config for a different campaign: record valid, not applicable.
        (root / "autonomous_agent" / "state" / "campaign_config.json").write_text(
            json.dumps({"campaign_id": "campaign-4-reconstruction-2026-10-10"}),
            encoding="utf-8")
        policy = cycle._load_policy(root)
        self.assertNotIn("c5_steering_exception", policy)

    def test_missing_record_keeps_exception_off(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="c5_exception_absent_"))
        root = tmp / "ws"
        (root / "autonomous_agent" / "state").mkdir(parents=True)
        policy = cycle._load_policy(root)
        self.assertNotIn("c5_steering_exception", policy)


def record_axes() -> list[str]:
    return json.loads(_repo_record_bytes().decode("utf-8"))["axes"]


if __name__ == "__main__":
    raise SystemExit(unittest.main())
