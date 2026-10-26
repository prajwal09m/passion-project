"""Synthetic-only tests for the Campaign 5 authorization preflight."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from autonomous_agent.campaign5_authorization import (
    check_campaign5_authorization, sha256_json,
    sign_for_test, validate_authorization,
)
from autonomous_agent.experiment_adapter import (
    ExperimentAdapter, ExperimentResult, ExperimentSpec,
)

NOW = datetime(2026, 10, 18, 16, 0, tzinfo=timezone.utc)
OWNER_KEY = b"owner synthetic test key" * 2
REVIEWER_KEY = b"independent reviewer synthetic key" * 2


def write_c5_campaign(root: Path) -> dict:
    state = root / "autonomous_agent/state"
    state.mkdir(parents=True, exist_ok=True)
    campaign = {
        "campaign_id": "campaign-5-synthetic-denial",
        "protocol_id": "synthetic-protocol",
        "protocol_version": "0.test",
        "protocol_sha256": "a" * 64,
        "authorization_scope": {},
    }
    path = state / "campaign_config.json"
    path.write_text(json.dumps(campaign, sort_keys=True) + "\n", encoding="utf-8")
    (state / "campaign_config.sha256").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest() + "\n", encoding="utf-8")
    return campaign


def valid_record(predecl_sha: str | None = None) -> dict:
    scope = {
        "model_families": ["logistic_regression"],
        "candidate_generation_method": "fixed synthetic fixture only",
        "comparisons": ["synthetic A minus B"],
        "measurements": ["synthetic unit metrics"],
        "operations": ["fit_synthetic_fixture"],
        "permitted_changes": [],
    }
    scope_sha = sha256_json(scope)
    protocol_sha = "a" * 64
    predecl_sha = predecl_sha or "b" * 64
    common = {
        "decision": "approve", "campaign_id": "campaign-5-test",
        "protocol_sha256": protocol_sha, "scope_sha256": scope_sha,
        "predeclaration_sha256": predecl_sha,
    }
    record = {
        "schema": "campaign5-authorization/v1", "record_class": "synthetic",
        "record_id": "SYNTHETIC-ONLY-TEST-NON-AUTHORITATIVE",
        "status": "approved", "issued_at": "2026-10-18T15:00:00Z",
        "expires_at": "2026-10-19T15:00:00Z",
        "campaign_id": "campaign-5-test",
        "execution_scope": "real_market_evaluation",
        "protocol": {"id": "synthetic-protocol", "version": "0.test",
                     "sha256": protocol_sha},
        "scope": scope, "scope_sha256": scope_sha,
        "data_boundary": {
            "record_id": "SYNTHETIC-BOUNDARY-ONLY",
            "record_path": "synthetic_boundary.json",
            "record_sha256": "c" * 64,
            "permission_status": "explicitly_permitted",
            "permitted_datasets": [{"dataset_id": "synthetic-only",
                                     "sha256": "d" * 64,
                                     "operations": ["fit_synthetic_fixture"]}],
            "denied_paths": ["synthetic/prospective/", "synthetic/holdout/"],
        },
        "predeclaration": {
            "id": "synthetic-predecl", "version": "0.test",
            "path": "synthetic_predecl.md", "sha256": predecl_sha,
            "protocol_sha256": protocol_sha, "scope_sha256": scope_sha,
            "approval_status": "approved",
        },
        "owner_approval": {**common, "actor_id": "synthetic-owner",
                           "decided_at": "2026-10-18T15:01:00Z"},
        "independent_review": {
            **common, "actor_id": "synthetic-reviewer",
            "decided_at": "2026-10-18T15:02:00Z",
            "qualifications": ["synthetic test credential"],
            "independent": True, "conflicts_disclosed": True,
            "conflict_present": False,
        },
        "signatures": {},
    }
    record["signatures"] = {
        "owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
        "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY),
    }
    return record


class ReviewModeAmendmentTests(unittest.TestCase):
    """2026-10-22 owner-authorized amendment: opt-in AI-substitute review mode.

    Fail-closed contract verified here: the mode only validates with the exact
    disclosure fields, with booleans that state the limitation truthfully
    (independent=False, conflict_present=True), with a mandatory COI disclosure
    mentioning the conflict, and with a decision basis naming the authentic
    signed owner document. Unknown/absent/mixed modes stay rejected, and the
    absent-mode default remains the unchanged independent-human contract.
    """

    def setUp(self) -> None:
        self.record = valid_record()
        self.scope = self.record["scope"]

    def validate(self, record=None) -> list[str]:
        return validate_authorization(
            self.record if record is None else record, self.scope,
            owner_key=OWNER_KEY, reviewer_key=REVIEWER_KEY,
            now=NOW, allow_synthetic=True)

    def _signed(self, record: dict) -> dict:
        record["signatures"] = {
            "owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
            "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY),
        }
        return record

    def _ai_mode_record(self) -> dict:
        record = json.loads(json.dumps(self.record))
        review = record["independent_review"]
        review["review_mode"] = "ai_substitute_owner_authorized"
        review["independent"] = False
        review["conflicts_disclosed"] = True
        review["conflict_present"] = True
        review["decision_basis"] = [
            "stat_validation_h10/C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md"]
        review["disclosure"] = [
            "Reviewer is the implementing AI; owner accepted the disclosed "
            "conflict of interest for campaign-5 with acknowledged limitations."]
        return self._signed(record)

    def test_full_ai_substitute_disclosure_passes(self):
        self.assertEqual(self.validate(self._ai_mode_record()), [])

    def test_missing_disclosure_field_is_malformed(self):
        record = self._ai_mode_record()
        del record["independent_review"]["disclosure"]
        self.assertIn("independent_review_malformed", self.validate(record))
        record = self._ai_mode_record()
        del record["independent_review"]["decision_basis"]
        self.assertIn("independent_review_malformed", self.validate(record))

    def test_wrong_token_or_missing_conflict_word_has_no_passage(self):
        record = self._ai_mode_record()
        record["independent_review"]["decision_basis"] = ["some/other_doc.md"]
        self._signed(record)
        self.assertIn("independent_review_not_qualified_independent_approved",
                      self.validate(record))
        record = self._ai_mode_record()
        record["independent_review"]["disclosure"] = [
            "Reviewer agrees with the implementation; nothing is disclosed."]
        self._signed(record)
        self.assertIn("independent_review_not_qualified_independent_approved",
                      self.validate(record))

    def test_false_independence_claim_or_mixed_mode_is_rejected(self):
        record = self._ai_mode_record()
        record["independent_review"]["independent"] = True
        self._signed(record)
        self.assertIn("independent_review_not_qualified_independent_approved",
                      self.validate(record))
        record = self._ai_mode_record()
        record["independent_review"]["review_mode"] = "undisclosed_mode"
        self._signed(record)
        self.assertIn("independent_review_malformed", self.validate(record))
        record = json.loads(json.dumps(self.record))  # independent mode
        record["independent_review"]["disclosure"] = ["extra field"]
        self._signed(record)
        self.assertIn("independent_review_malformed", self.validate(record))


class AuthorizationRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = valid_record()
        self.scope = self.record["scope"]

    def validate(self, record=None, scope=None, *, owner_key=OWNER_KEY,
                 reviewer_key=REVIEWER_KEY):
        return validate_authorization(
            self.record if record is None else record,
            self.scope if scope is None else scope,
            owner_key=owner_key, reviewer_key=reviewer_key,
            now=NOW, allow_synthetic=True)

    def test_synthetic_positive_control_is_structurally_valid_only(self):
        self.assertEqual(self.validate(), [])
        self.assertIn("authorization_record_not_authoritative",
                      validate_authorization(
                          self.record, self.scope, owner_key=OWNER_KEY,
                          reviewer_key=REVIEWER_KEY, now=NOW))

    def test_missing_authorization_and_human_decisions_fail_closed(self):
        self.assertIn("authorization_record_missing_or_not_object",
                      self.validate(record=[]))
        for key, reason in (("owner_approval", "owner_approval_missing"),
                            ("independent_review", "independent_review_not_qualified_independent_approved")):
            record = json.loads(json.dumps(self.record))
            record[key]["decision"] = "pending"
            record["signatures"] = {
                "owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
                "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY),
            }
            self.assertIn(reason, self.validate(record))

    def test_reviewer_must_be_independent_qualified_and_distinct(self):
        record = json.loads(json.dumps(self.record))
        record["independent_review"]["independent"] = False
        record["signatures"] = {"owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
                                "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY)}
        self.assertIn("independent_review_not_qualified_independent_approved",
                      self.validate(record))
        record = json.loads(json.dumps(self.record))
        record["independent_review"]["actor_id"] = "synthetic-owner"
        record["signatures"] = {"owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
                                "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY)}
        self.assertIn("reviewer_not_independent_of_owner", self.validate(record))

    def test_version_scope_digest_and_prehash_mismatches_block(self):
        record = json.loads(json.dumps(self.record))
        record["protocol"]["version"] = "unapproved"
        record["signatures"] = {"owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
                                "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY)}
        self.assertIn("planned_scope_mismatch", self.validate(record, {"changed": True}))
        record = json.loads(json.dumps(self.record))
        record["scope_sha256"] = "0" * 64
        self.assertIn("scope_digest_mismatch", self.validate(record))
        record = json.loads(json.dumps(self.record))
        record["predeclaration"]["protocol_sha256"] = "f" * 64
        record["signatures"] = {"owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
                                "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY)}
        self.assertIn("predeclaration_protocol_sha256_mismatch", self.validate(record))

    def test_unclear_data_permission_and_missing_denial_block(self):
        for field, value, expected in (
            ("permission_status", "unknown", "data_permission_missing_or_unclear"),
            ("permitted_datasets", [], "permitted_datasets_missing"),
            ("denied_paths", [], "protected_data_denial_missing"),
        ):
            record = json.loads(json.dumps(self.record))
            record["data_boundary"][field] = value
            record["signatures"] = {"owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
                                    "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY)}
            self.assertIn(expected, self.validate(record))

    def test_revocation_malformed_unknown_future_stale_expired_and_bad_key_block(self):
        record = json.loads(json.dumps(self.record))
        record["status"] = "revoked"
        record["signatures"] = {"owner_hmac_sha256": sign_for_test(record, OWNER_KEY),
                                "reviewer_hmac_sha256": sign_for_test(record, REVIEWER_KEY)}
        self.assertIn("authorization_not_active_approved", self.validate(record))
        self.assertIn("authorization_record_fields_mismatch",
                      self.validate({**self.record, "future_field": True}))
        self.assertIn("authorization_expired", validate_authorization(
            self.record, self.scope, owner_key=OWNER_KEY,
            reviewer_key=REVIEWER_KEY,
            now=datetime(2030, 1, 1, tzinfo=timezone.utc), allow_synthetic=True))
        self.assertIn("authorization_trust_keys_unavailable",
                      self.validate(owner_key=None))
        self.assertIn("owner_signature_invalid",
                      self.validate(owner_key=b"wrong key"))
        self.assertIn("authorization_signatures_missing_or_malformed",
                      self.validate({**self.record, "signatures": {}}))

    def test_record_loading_and_audit_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = check_campaign5_authorization(
                root, {"campaign_id": "campaign-5-test"}, self.scope)
            self.assertFalse(result["allowed"])
            self.assertIn("authorization_record_unavailable", result["reason_codes"])
            self.assertTrue((root / "autonomous_agent/state/campaign5_preflight_audit.jsonl").is_file())
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(Path, "open", side_effect=OSError("synthetic audit failure")):
                result = check_campaign5_authorization(
                    Path(tmp), {"campaign_id": "campaign-5-test"}, self.scope)
                self.assertFalse(result["allowed"])
                self.assertIn("preflight_audit_unavailable", result["reason_codes"])


class ExecutionBoundaryTests(unittest.TestCase):
    def test_non_c5_adapter_spec_is_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "autonomous_agent").mkdir()
            adapter = ExperimentAdapter(root=root, candidates_root=root / "candidates",
                                        state_root=root / "state")
            # The guard must be NOT_APPLICABLE before spec validation/execution.
            result = check_campaign5_authorization(root, {"campaign_id": "campaign-4-test"})
            self.assertTrue(result["allowed"])
            self.assertEqual(result["status"], "NOT_APPLICABLE")

    def test_c5_adapter_denial_precedes_execution_subprocess_and_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.mkdir(exist_ok=True)
            calls = []
            spec = ExperimentSpec(
                experiment_id="synthetic-c5-denied",
                parent_version="V2.0.0", hypothesis="synthetic no-op",
                proposed_change={"summary": "synthetic", "files": [
                    {"path": "autonomous_agent/experiments/run_experiment.py",
                     "content": "print('must never execute')"}]},
                files_allowed_to_change=("autonomous_agent/experiments",),
                evaluation_protocol={"acceptance_criteria": {}},
                random_seed=1, resource_limits={}, timeout=5,
                provenance={"campaign_id": "campaign-5-test", "authorization_scope": {}},
            )
            adapter = ExperimentAdapter(
                root=root, candidates_root=root / "autonomous_agent/candidates",
                state_root=root / "autonomous_agent/state",
                command_factory=lambda workspace: calls.append(workspace) or {})
            with patch.dict("os.environ", {}, clear=True):
                result = adapter.run_experiment(spec)
            self.assertEqual(result.status, "BLOCKED")
            self.assertEqual(calls, [])
            self.assertFalse((root / "autonomous_agent/candidates/synthetic-c5-denied/workspace").exists())
            self.assertTrue((root / "autonomous_agent/candidates/synthetic-c5-denied/result.json").is_file())

    def test_retry_resume_and_direct_adapter_paths_are_denied_without_records(self):
        # All adapter invocations share the same guarded method; call paths
        # cannot bypass it by reusing/reconstructing a serialized spec.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls = []
            adapter = ExperimentAdapter(
                root=root, candidates_root=root / "candidates", state_root=root / "state",
                command_factory=lambda workspace: calls.append(workspace) or {})
            spec = ExperimentSpec(
                experiment_id="synthetic-c5-retry", parent_version="V2.0.0",
                hypothesis="synthetic retry", proposed_change={"summary": "synthetic", "files": [
                    {"path": "autonomous_agent/experiments/run_experiment.py", "content": "pass"}]},
                files_allowed_to_change=("autonomous_agent/experiments",),
                evaluation_protocol={"acceptance_criteria": {}}, random_seed=1,
                resource_limits={}, timeout=5,
                provenance={"campaign_id": "campaign-5-test", "authorization_scope": {}},
            )
            for _ in range(2):
                self.assertEqual(adapter.run_experiment(ExperimentSpec.from_dict(spec.to_dict())).status,
                                 "BLOCKED")
            self.assertEqual(calls, [])

    def test_continuous_loop_blocks_direct_cycle_execution_and_restart(self):
        from unittest.mock import MagicMock
        from autonomous_agent.continuous_loop import LoopStop, ResearchLoop

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_c5_campaign(root)
            calls = []
            loop = ResearchLoop(root, max_cycles=1,
                                executor=lambda spec: calls.append(spec) or {})
            recovery = MagicMock()
            loop._recover_interrupted = recovery

            with self.assertRaises(LoopStop) as direct_execution:
                loop.phase_execute_one()
            self.assertEqual(direct_execution.exception.reason,
                             "CAMPAIGN5_AUTHORIZATION_BLOCKED")
            with self.assertRaises(LoopStop) as direct_cycle:
                loop.cycle_once()
            self.assertEqual(direct_cycle.exception.reason,
                             "CAMPAIGN5_AUTHORIZATION_BLOCKED")
            recovery.assert_not_called()
            self.assertEqual(calls, [])

            # Restart rejects before lock acquisition, recovery, proposal generation,
            # or the injected executor can run.
            with self.assertRaises(LoopStop) as restart:
                loop.run()
            self.assertEqual(restart.exception.reason, "CAMPAIGN5_AUTHORIZATION_BLOCKED")
            recovery.assert_not_called()
            self.assertEqual(calls, [])
            self.assertFalse((root / "autonomous_agent/state/loop.lock").exists())
            audit = root / "autonomous_agent/state/campaign5_preflight_audit.jsonl"
            self.assertTrue(audit.is_file())

    def test_adapter_reproduction_cli_and_baseline_establishment_fail_closed(self):
        from autonomous_agent.experiment_adapter import AdapterError, main as adapter_main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_c5_campaign(root)
            calls = []
            adapter = ExperimentAdapter(
                root=root, candidates_root=root / "autonomous_agent/candidates",
                state_root=root / "autonomous_agent/state",
                command_factory=lambda workspace: calls.append(workspace) or {})
            with patch.object(adapter, "verify_inputs") as verify_inputs:
                reproduction = adapter.run_reproduction(force=True)
                self.assertEqual(reproduction.status, "BLOCKED")
                with self.assertRaises(AdapterError):
                    adapter.run_establish_baseline()
                verify_inputs.assert_not_called()
            self.assertEqual(calls, [])

            # Exercise supported adapter CLI dispatch: it reports BLOCKED with
            # the regular refusal code and never reaches child commands.
            self.assertEqual(adapter_main(["reproduce", "--root", str(root)]), 3)
            self.assertEqual(calls, [])

    def test_core_runner_denies_campaign5_even_when_decision_record_cannot_be_audited(self):
        from unittest.mock import MagicMock
        from autonomous_agent.core import Hypothesis, PrerequisiteReport, Supervisor

        runner = MagicMock(return_value={})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_c5_campaign(root)
            state = {"experiments": [], "direction_stats": {},
                     "seen_blocked_fingerprints": [], "consecutive_rejections": 0}
            supervisor = Supervisor(root=root, state_root=root / "state",
                                    experiment_runner=runner)
            hypothesis = Hypothesis(direction="validation", question="synthetic",
                                    rationale="synthetic", experiment="synthetic",
                                    required_inputs=(), priority=1.0)
            report = PrerequisiteReport(ready=True, reasons=(),
                                        champion_id="fixture", hypothesis=hypothesis)
            with patch("autonomous_agent.core.check_prerequisites", return_value=report), \
                 patch("autonomous_agent.campaign5_authorization._audit", return_value=False):
                supervisor.cycle(state)
            self.assertEqual(runner.call_count, 0)
            self.assertEqual(state["experiments"][0]["status"], "BLOCKED")
            self.assertIn("preflight_audit_unavailable",
                          state["experiments"][0]["blockers"][0])

    def test_supervisor_runner_cannot_bypass_missing_campaign_authorization(self):
        from autonomous_agent.core import Hypothesis, PrerequisiteReport, Supervisor
        from unittest.mock import MagicMock
        runner = MagicMock(return_value={})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "autonomous_agent/state/campaign_config.json"
            config.parent.mkdir(parents=True)
            config.write_text(json.dumps({
                "campaign_id": "campaign-5-test",
                "authorization_scope": {"synthetic": "planned"},
                "protocol_id": "synthetic-protocol", "protocol_version": "0.test",
                "protocol_sha256": "a" * 64,
            }), encoding="utf-8")
            state = {"experiments": [], "direction_stats": {}, "seen_blocked_fingerprints": [],
                     "consecutive_rejections": 0}
            supervisor = Supervisor(root=root, state_root=root / "state", experiment_runner=runner)
            hypothesis = Hypothesis(direction="validation", question="synthetic", rationale="synthetic",
                                    experiment="synthetic", required_inputs=(), priority=1.0)
            report = PrerequisiteReport(ready=True, reasons=(), champion_id="fixture", hypothesis=hypothesis)
            with patch("autonomous_agent.core.check_prerequisites", return_value=report):
                supervisor.cycle(state)
            self.assertEqual(runner.call_count, 0)
            self.assertIn("authorization preflight blocked execution",
                          state["experiments"][0]["failure"])


if __name__ == "__main__":
    unittest.main()
