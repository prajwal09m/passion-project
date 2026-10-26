"""Phase 2 tests for the evidence-grounded proposal layer.

Covers the 18 Phase 1 tests (T1-T18) plus the Phase 2 extra requirements
(Campaign 1 immutability, holdout access refusal, arbitrary-code refusal,
no-execution guarantee, duplicate refusal, evidence-hash mismatch refusal,
NOT_FALSIFIABLE refusal, quota enforcement, already-asked persistence,
deterministic regeneration, compiler boundary, post-compilation spec
validation).

All proposal-layer activity runs inside temporary fixture trees. The only
time real repository files are touched is read-only hashing in
``test_campaign1_evidence_unchanged``. No experiment is executed anywhere in
this module.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from autonomous_agent.proposal_layer import (
    bias_governor, compiler, cycle, evidence_view, generator, ledger, primitives,
    proposals_enabled, schema, validator,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXED_CLOCK = lambda: "2026-10-04T00:00:00+00:00"  # noqa: E731


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


# Frozen Campaign 1 parameters, copied from the immutable attempt ledger as
# recorded in the Campaign 1 audit (used by the T7 replay regression).
CAMPAIGN1_ATTEMPTS = [
    {"experiment_id": "exp-calibration-stability-check-a00",
     "recipe_id": "calibration_stability_check",
     "selected_parameters": {"arm_pair": "B->C", "estimator": "LightGBM",
                             "calibration_bins": 5, "n_boot": 500}},
    {"experiment_id": "exp-feature-arm-nested-ablation-a00",
     "recipe_id": "feature_arm_nested_ablation",
     "selected_parameters": {"arm_pair": "A->B",
                             "estimator": "LogisticRegression", "n_boot": 500}},
    {"experiment_id": "exp-model-class-matched-comparison-a00",
     "recipe_id": "model_class_matched_comparison",
     "selected_parameters": {"arm": "B", "n_boot": 500}},
    {"experiment_id": "exp-calibration-stability-check-a01",
     "recipe_id": "calibration_stability_check",
     "selected_parameters": {"arm_pair": "B->C", "estimator": "LightGBM",
                             "calibration_bins": 10, "n_boot": 500}},
    {"experiment_id": "exp-feature-arm-nested-ablation-a01",
     "recipe_id": "feature_arm_nested_ablation",
     "selected_parameters": {"arm_pair": "A->B",
                             "estimator": "LogisticRegression", "n_boot": 1000}},
    {"experiment_id": "exp-model-class-matched-comparison-a01",
     "recipe_id": "model_class_matched_comparison",
     "selected_parameters": {"arm": "B", "n_boot": 1000}},
    {"experiment_id": "exp-feature-arm-nested-ablation-a02",
     "recipe_id": "feature_arm_nested_ablation",
     "selected_parameters": {"arm_pair": "A->B", "estimator": "LightGBM",
                             "n_boot": 500}},
    {"experiment_id": "exp-model-class-matched-comparison-a02",
     "recipe_id": "model_class_matched_comparison",
     "selected_parameters": {"arm": "C", "n_boot": 500}},
]

# Campaign 1 evidence that policy declares immutable (append-only ledgers and
# mutable champion records are deliberately excluded: future campaigns extend
# them without altering these files).
CAMPAIGN1_FROZEN_HASHES = {
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md":
        "47904cb1ba0f7b58f63a3c19a3853c10d8dcf7f673e060039ac9d076cdfab3e0",
    "autonomous_agent/state/baseline_reproduction.json":
        "a5c6d30370866a265e9b8fb174f8338207b127bb4fcacf42faa2eaec4bf9d914",
    "autonomous_agent/candidates/exp-calibration-stability-check-a00/spec.json":
        "c603b943b8d336c5c8832f534ef5f009b215cfe83f719b31788edd1243745f59",
    "autonomous_agent/candidates/exp-calibration-stability-check-a00/result.json":
        "e900eea261de2196a47dea42892ef22619822e551acc0a1fd96e63d198c65ae2",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a00/spec.json":
        "73a41652e4962d0a01e83d3a359e83e004c2b05d2ce2535ee6455edf8a385b51",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a00/result.json":
        "3590074eb23525f6e1ec7cb0ace1a10b87d3e57edfb1c292d2236daab6a0d92d",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a00/spec.json":
        "d66310eab0d0d88ab4f72cf477c56307c5198da2ee20eec2ecf07f6401ec04fc",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a00/result.json":
        "49250b39f8155fec3a60c977ff9b9fcbf25d3cfa7f6388e4453d7f966e38f00a",
    "autonomous_agent/candidates/exp-calibration-stability-check-a01/spec.json":
        "836d7729fdebcc5464cba45d1d525c7a53c68bb9c435973537c7f46bb04e4719",
    "autonomous_agent/candidates/exp-calibration-stability-check-a01/result.json":
        "a006942f5282a118facec41c136670629dd9e560f432b614db20351454aba535",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a01/spec.json":
        "7c02cd7be762f194089e083a3aa4bac4839d64b37cd1e1c8cf3c6c4cb371051b",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a01/result.json":
        "2727ea7623c504782aadd019d53cf6d63f022de9f0b97111eb0640127a428d67",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a01/spec.json":
        "98aefdb443966fd72da78dbcc5957d84017035d3adaa3a094b4d40237b4e42ee",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a01/result.json":
        "def26799f8cbe31269ab17e5cbcef6830e233b2bcc3b3d7c0dcc4c4d603cc67f",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a02/spec.json":
        "dc397c8087bd0752d0607d9045201a6e64a1149d26199f164b65d1587a8e994f",
    "autonomous_agent/candidates/exp-feature-arm-nested-ablation-a02/result.json":
        "28e95ee0bb945f357603091045f775f924b289594992020297de0e1ead9f66cd",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a02/spec.json":
        "955d228c7a53de3b8f316bf308ad930e9ffa12bd616e15a4637f41327620fd7b",
    "autonomous_agent/candidates/exp-model-class-matched-comparison-a02/result.json":
        "526af856841f9e613129069a7be972374103132c148e32038af6b695207bbca8",
    "versions/V2.0.1/version.json":
        "c5a9483b7a78c6eac5cb65a9166bf3ae56ac6be52f9044c35fcd430baf454236",
    "versions/V2.0.2/version.json":
        "0042642c17a4b37132951ea061c2379b5db5234c8b390387c401ac0786835473",
    "versions/V2.0.3/version.json":
        "5783e9fa86228e255d2de5c831b186ca7b01789f81aceb7dcba6fbb5294693eb",
    "versions/V2.0.4/version.json":
        "f8fe5f972df5e5f233405e2f8c3a3e54fc1a0a2a668ed253994e4a66ef9782a5",
    "versions/V2.0.5/version.json":
        "865a46c9a1e9228f12b5e46a51e55cfb75a814dd3bade768469c99a008703790",
    "versions/V2.0.6/version.json":
        "83826793ca7c49ec1aca6ac0fdfcf228a4078292a14ec50e440fff95406e2822",
    "versions/V2.0.7/version.json":
        "66f1eb0ba836060ff728f4e004933d8a8ef7e1192045d91aa531724fc4c324eb",
    "versions/V2.0.8/version.json":
        "1e53902c57800871909afe3b9401ef66fd9cbde7940b001d82e7dd3eb841f282",
}


def build_fixture(root: Path) -> bytes:
    """Deterministic fixture tree with a sealed-holdout trap inside it."""
    (root / "autonomous_agent/state").mkdir(parents=True, exist_ok=True)
    (root / "study_files/outputs/study_v1/development").mkdir(parents=True, exist_ok=True)
    (root / "study_files/outputs/study_v1/prospective").mkdir(parents=True, exist_ok=True)

    table = b"event,label\n1,0\n2,1\n3,0\n"
    (root / "study_files/outputs/study_v1/development/event_table.csv").write_bytes(table)
    secret = b"SECRET-HOLDOUT-DATA-DO-NOT-LEAK"
    (root / "study_files/outputs/study_v1/prospective/secret.csv").write_bytes(secret)

    champion = {
        "version": "V2.0.8",
        "parent_champion": "V2.0.7",
        "artifact_sha256": "5dbcb5f1aa68fc9c753c7178b4d9ea65e24dca48a9dc7bbe523598ed9dc3dcd2",
        "experiment_id": "exp-3bbc4266814d",
        "baseline_id": "BASELINE_RECONSTRUCTED_2026_10",
        "metrics": {"pooled_roc_auc_a": 0.660322, "pooled_roc_auc_b": 0.683633,
                    "delta_auc": 0.023312},
        "holdout_policy": {"status": "SEALED", "uses": 0,
                           "policy": "Do not access for research tuning."},
        "dataset_sha256": sha_bytes(table),
        "pipeline_fingerprint": "d103e4c94a5f8fb7287c1617b956b45a939c86f8372a77f02f81555ee4aeccf1",
        "validation_status": "SELF_REPRODUCED",
        "created_at": "2026-10-04T21:04:49+00:00",
        "research_test_period": "none (final holdout SEALED, uses=0)",
        # Deliberate trap: a holdout PATH embedded in an allowlisted source.
        "evil_debug_path": "study_files/outputs/study_v1/prospective/secret.csv",
    }
    (root / "CHAMPION.json").write_text(json.dumps(champion, indent=1),
                                        encoding="utf-8")

    agent_state = {
        "research_exhausted": False,
        "last_cycle_status": "RESEARCH_EXHAUSTED",
        "direction_stats": {
            "feature_engineering": {"attempts": 21, "accepted": 3, "rejected": 18},
            "calibration": {"attempts": 19, "accepted": 2, "rejected": 17},
            "model_architecture": {"attempts": 21, "accepted": 3, "rejected": 18},
            "validation": {"attempts": 18, "accepted": 0, "rejected": 18},
            "error_analysis": {"attempts": 17, "accepted": 0, "rejected": 17},
            "data_quality": {"attempts": 18, "accepted": 0, "rejected": 18},
            "model_complexity": {"attempts": 17, "accepted": 0, "rejected": 17},
            "target_design": {"attempts": 18, "accepted": 0, "rejected": 18},
        },
        "experiments": [
            {"id": "exp-853a0b9e2520", "direction": "calibration",
             "status": "ACCEPTED", "created_at": "2026-10-04T18:00:14+00:00",
             "finished_at": "2026-10-04T18:16:51+00:00",
             "accepted_version": "V2.0.1"},
            {"id": "exp-41b8ce05bda2", "direction": "feature_engineering",
             "status": "ACCEPTED", "created_at": "2026-10-04T18:31:35+00:00",
             "finished_at": "2026-10-04T18:41:35+00:00",
             "accepted_version": "V2.0.2"},
            {"id": "exp-12b1f60fef45", "direction": "feature_engineering",
             "status": "REJECTED", "created_at": "2026-10-04T17:54:17+00:00",
             "finished_at": "2026-10-04T17:54:17+00:00",
             "accepted_version": None},
            {"id": "exp-evil", "direction": "calibration", "status": "REJECTED",
             "note": "leak attempt: study_files/outputs/study_v1/prospective/secret.csv"},
        ],
    }
    (root / "autonomous_agent/state/agent_state.json").write_text(
        json.dumps(agent_state, indent=1), encoding="utf-8")

    (root / "autonomous_agent/state/spec_attempts.json").write_text(
        json.dumps({"schema_version": 1, "attempts": CAMPAIGN1_ATTEMPTS},
                   indent=1), encoding="utf-8")
    (root / "autonomous_agent/state/experiment_registry.json").write_text(
        json.dumps({"schema_version": 1, "attempts": []}), encoding="utf-8")
    (root / "autonomous_agent/state/baseline_registry.json").write_text(
        json.dumps({"schema_version": 1,
                    "records": [{"baseline_id": "BASELINE_RECONSTRUCTED_2026_10",
                                 "status": "ESTABLISHED"}]}), encoding="utf-8")
    (root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json").write_text(
        json.dumps({"folds": [2023, 2024, 2025]}), encoding="utf-8")
    (root / "versions/V2.0.8").mkdir(parents=True, exist_ok=True)
    (root / "versions/V2.0.8/version.json").write_text(
        json.dumps({"version": "V2.0.8"}), encoding="utf-8")
    return secret


def base_policy(**overrides):
    policy = {
        "min_falsification_share": 0.0,
        "max_replication_share": 1.0,
        "max_per_direction": 4,
        "max_total_proposals": 20,
        "max_signature_count": 2,
        "max_proposals_per_cycle": 3,
        "require_human_approval": False,
        "allow_future_primitives": False,
    }
    policy.update(overrides)
    return bias_governor.merge_policy(policy)


class ProposalLayerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="proposal_layer_test_"))
        self.root = self.tmp / "ws"
        self.root.mkdir(parents=True)
        self.secret = build_fixture(self.root)
        self.view = evidence_view.build(self.root, clock=FIXED_CLOCK)
        self.ledger = ledger.ProposalLedger(
            self.root / "autonomous_agent/state/proposal_ledger.jsonl",
            clock=FIXED_CLOCK)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # helpers ---------------------------------------------------------------
    def make_payload(self, primitive_id="feature_arm_comparison",
                     params=None, proposal_class="confirmatory"):
        params = params or {"arm_pair": "A->B", "estimator": "LogisticRegression",
                            "n_boot": 500}
        return generator.payload_for(self.view, primitive_id, params,
                                     proposal_class)

    def validate(self, payload, *, policy=None, history=None, proposal_id=None):
        policy = policy or base_policy()
        if history is None:
            history = self.ledger.all_proposals()
        return validator.validate_proposal(
            payload, root=self.root, view=self.view, merged_history=history,
            policy=policy, proposal_id=proposal_id)

    def approve(self, proposal_id, *, policy=None, approver="test-suite",
                led=None):
        """Legal ACCEPTED_FOR_EXECUTION transition carrying the approval
        provenance required by revalidate_at_approval@1.0.0 (OBS-3)."""
        led = led or self.ledger
        governor = bias_governor.BiasGovernor(policy or base_policy())
        return led.transition(
            proposal_id, schema.STATUS_ACCEPTED_FOR_EXECUTION,
            reason_code="HUMAN_APPROVAL",
            detail={"approval_policy": cycle.APPROVAL_POLICY,
                    "approved_by": approver,
                    "quota_state": governor.quota_state(led.all_proposals()),
                    "revalidated_at_approval": True})

    # T1 --------------------------------------------------------------------
    def test_t1_deterministic_regeneration(self):
        view2 = evidence_view.build(self.root, clock=lambda: "OTHER-TIME")
        self.assertEqual(self.view["evidence_view_sha256"],
                         view2["evidence_view_sha256"])
        policy = base_policy()
        a = generator.generate_proposals(self.view, policy, seed=7, limit=5)
        b = generator.generate_proposals(self.view, policy, seed=7, limit=5)
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(b, sort_keys=True))
        c = generator.generate_proposals(self.view, policy, seed=8, limit=5)
        self.assertNotEqual([p["proposal_fingerprint"] for p in a],
                            [p["proposal_fingerprint"] for p in c])

    # T2 --------------------------------------------------------------------
    def test_t2_holdout_never_readable_through_evidence_view(self):
        serialized = json.dumps(self.view, sort_keys=True)
        self.assertNotIn("prospective", serialized)
        self.assertNotIn(self.secret.decode(), serialized)
        self.assertTrue(self.view["holdout_reference_stripped"])
        with self.assertRaises(evidence_view.EvidenceViewError):
            evidence_view._read_bytes(
                self.root, "study_files/outputs/study_v1/prospective/secret.csv")
        with self.assertRaises(evidence_view.EvidenceViewError):
            evidence_view.assert_source_allowed(
                "study_files/outputs/study_v1/prospective/secret.csv")
        # Policy status text (\"SEALED, uses=0\") survives without a path.
        self.assertEqual(self.view["holdout_policy"].get("status"), "SEALED")
        # No file under prospective/ is ever opened during a build.
        opened: list[str] = []
        real_open = io.open

        def tracking_open(file, *args, **kwargs):
            opened.append(str(file))
            return real_open(file, *args, **kwargs)

        with mock.patch("io.open", side_effect=tracking_open):
            evidence_view.build(self.root, clock=FIXED_CLOCK)
        self.assertFalse(any("prospective" in path for path in opened))

    def test_t2b_proposal_referenceing_holdout_is_refused(self):
        payload = self.make_payload()
        payload["hypothesis"] = ("[validation] probe "
                                 "study_files/outputs/study_v1/prospective/x.csv")
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_HOLDOUT)
        self.assertEqual(report.reason_code, schema.RC_HOLDOUT_REFERENCE)
        self.assertEqual(report.status_target, "FAILED_VALIDATION")

    # T3 --------------------------------------------------------------------
    def test_t3_evidence_hash_mismatch_refused(self):
        payload = self.make_payload()
        payload["evidence_citations"][0]["sha256"] = "0" * 64
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_UNRECALLED_EVIDENCE)
        # Non-allowlisted citation path is also refused.
        payload2 = self.make_payload()
        payload2["evidence_citations"][0]["artifact_path"] = "etc/passwd"
        payload2["proposal_fingerprint"] = schema.proposal_fingerprint(payload2)
        report2 = self.validate(payload2)
        self.assertFalse(report2.passed)
        self.assertEqual(report2.reason_code, schema.RC_UNRECALLED_EVIDENCE)
        # File mutated after the view was built -> stale view hash refused.
        protocol = self.root / "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"
        original = protocol.read_bytes()
        try:
            protocol.write_text('{"folds": [2023, 2024, 2025], "tampered": 1}',
                                encoding="utf-8")
            payload3 = self.make_payload()
            payload3["evidence_citations"].append({
                "artifact_path": "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json",
                "sha256": sha_bytes(protocol.read_bytes()),
                "what_it_shows": "protocol"})
            payload3["proposal_fingerprint"] = schema.proposal_fingerprint(payload3)
            report3 = self.validate(payload3)
            self.assertFalse(report3.passed)
            self.assertEqual(report3.reason_code, schema.RC_UNRECALLED_EVIDENCE)
        finally:
            protocol.write_bytes(original)

    # T4 --------------------------------------------------------------------
    def test_t4_schema_and_not_falsifiable_refusals(self):
        payload = self.make_payload()
        del payload["direction"]
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertEqual(report.failed_gate, schema.GATE_SCHEMA)

        payload = self.make_payload()
        payload["hypothesis"] = 42
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertEqual(report.failed_gate, schema.GATE_SCHEMA)

        payload = self.make_payload()
        payload["falsification_rule"] = {"metric": "made_up_metric",
                                         "comparator": "<", "threshold": 0.0,
                                         "scope": "pooled"}
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_NOT_FALSIFIABLE)
        self.assertEqual(report.status_target, "FAILED_VALIDATION")

    # T5 --------------------------------------------------------------------
    def test_t5_surface_escape_refusals(self):
        payload = self.make_payload()
        payload["design"]["primitives"][0]["params"]["arm_pair"] = "study_files/x.py"
        payload["parameters"]["arm_pair"] = "study_files/x.py"
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_SURFACE)
        self.assertEqual(report.reason_code, schema.RC_SURFACE_ESCAPE)

        payload = self.make_payload()
        payload["design"]["primitives"][0]["primitive_id"] = "not_a_primitive"
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertEqual(report.reason_code, schema.RC_UNSUPPORTED_PRIMITIVE)

        payload = self.make_payload()
        payload["design"]["primitives"][0]["params"]["smuggle"] = 1
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertEqual(report.reason_code, schema.RC_INVALID_PARAMETER)

    # T6 --------------------------------------------------------------------
    def test_t6_duplicate_and_near_duplicate_refusals(self):
        policy = base_policy()
        # C->D + LogisticRegression + 1500 was never run in Campaign 1, so
        # these designs exercise proposal-vs-proposal controls only.
        params = {"arm_pair": "C->D", "estimator": "LogisticRegression",
                  "n_boot": 1500}
        # (a) exact fingerprint duplicate: first recorded, identical second
        # must be refused.
        first = self.make_payload(params=params)
        first_id = self.ledger.create_proposal(first)
        self.ledger.transition(first_id, schema.STATUS_VALIDATING)
        report_first = self.validate(first, policy=policy, proposal_id=first_id)
        self.assertTrue(report_first.passed, report_first.to_dict())
        self.approve(first_id, policy=policy)

        duplicate = dict(first)
        dup_id = self.ledger.create_proposal(duplicate)
        self.ledger.transition(dup_id, schema.STATUS_VALIDATING)
        report = self.validate(duplicate, policy=policy, proposal_id=dup_id)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_DUPLICATE)
        self.assertEqual(report.status_target, "REFUSED")

        # (b) same design signature, different framing, no justification.
        near = self.make_payload(params=params, proposal_class="falsification")
        near["hypothesis"] = ("Totally distinct phrasing for the signature-only "
                              "near duplicate check between two framings.")
        near["proposal_fingerprint"] = schema.proposal_fingerprint(near)
        near_id = self.ledger.create_proposal(near)
        self.ledger.transition(near_id, schema.STATUS_VALIDATING)
        report = self.validate(near, policy=policy, proposal_id=near_id)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_NEAR_DUPLICATE)

        # (c) justified repeat passes the duplicate gate (raised cap).
        policy_cap3 = base_policy(max_signature_count=3)
        justified = self.make_payload(params=params,
                                      proposal_class="falsification")
        justified["hypothesis"] = ("Distinct justified reframe for signature two "
                                  "with explicit delta declared below.")
        justified["delta_from_prior"] = "estimator held fixed; class framing differs"
        justified["proposal_fingerprint"] = schema.proposal_fingerprint(justified)
        jid = self.ledger.create_proposal(justified)
        self.ledger.transition(jid, schema.STATUS_VALIDATING)
        report = self.validate(justified, policy=policy_cap3, proposal_id=jid)
        self.assertTrue(report.passed, report.to_dict())
        self.approve(jid, policy=policy_cap3)

        # (d) cross-signature templated wording is no longer a refusal
        # (OBS-1 resolution, Task 2 case C): the hypothesis text is highly
        # similar to `first` (same templated primitive purpose), but the
        # design signature is scientifically distinct (LightGBM/500 vs
        # LogisticRegression/1500). Wording alone may not refuse a distinct
        # design; layers 1 (fingerprint) and 2 (signature) are unchanged.
        text_dup = self.make_payload(params={"arm_pair": "C->D",
                                             "estimator": "LightGBM",
                                             "n_boot": 500})
        text_dup["proposal_fingerprint"] = schema.proposal_fingerprint(text_dup)
        tdid = self.ledger.create_proposal(text_dup)
        self.ledger.transition(tdid, schema.STATUS_VALIDATING)
        report = self.validate(text_dup, policy=policy, proposal_id=tdid)
        self.assertTrue(report.passed, report.to_dict())

    def test_t6b_signature_cap_enforced(self):
        params = {"arm_pair": "C->D", "estimator": "LogisticRegression",
                  "n_boot": 1500}
        texts = [
            "Alpha frame: does the C to D arm comparison hold under the frozen protocol.",
            "Beta frame: separate prose about resampling stability of the C-D pair.",
            "Gamma frame: third wording covering subgroup drift for C versus D.",
        ]
        for index, text in enumerate(texts):
            payload = self.make_payload(params=params)
            payload["hypothesis"] = text
            payload["delta_from_prior"] = f"distinct framing {index}"
            payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
            pid = self.ledger.create_proposal(payload)
            self.ledger.transition(pid, schema.STATUS_VALIDATING)
            report = self.validate(payload, proposal_id=pid)
            if index < 2:
                self.assertTrue(report.passed, report.to_dict())
                self.approve(pid)
            else:
                self.assertFalse(report.passed, report.to_dict())
                self.assertEqual(report.reason_code, schema.RC_SIGNATURE_CAP)
                self.assertEqual(report.status_target, "REFUSED")


    # T7 --------------------------------------------------------------------
    def test_t7_campaign1_replays_are_duplicates(self):
        mapping = {
            "feature_arm_nested_ablation": "feature_arm_comparison",
            "model_class_matched_comparison": "model_class_comparison",
            "calibration_stability_check": "calibration_stability_check",
        }
        for attempt in CAMPAIGN1_ATTEMPTS:
            primitive_id = mapping[attempt["recipe_id"]]
            payload = generator.payload_for(
                self.view, primitive_id, attempt["selected_parameters"],
                "replication")
            report = self.validate(payload, proposal_id="none")
            self.assertFalse(report.passed, attempt["experiment_id"])
            self.assertEqual(report.reason_code, schema.RC_DUPLICATE,
                             attempt["experiment_id"])
            self.assertEqual(report.failed_gate, schema.GATE_DUPLICATE,
                             attempt["experiment_id"])

    # T8 --------------------------------------------------------------------
    def test_t8_selection_blind_to_expected_outcomes(self):
        governor = bias_governor.BiasGovernor(base_policy())
        candidate = {
            "direction": "validation", "proposal_class": "falsification",
            "novelty_score": 1.0, "evidence_gap_score": 0.5,
            "quota_pressure": 1.0, "priority": 0.99,
            "attempts_in_direction": 0,
        }
        perturbed = dict(candidate)
        perturbed["preregistered_expectation"] = {"expected_direction": "huge win"}
        perturbed["predicted_delta"] = 0.42
        self.assertEqual(governor.score(candidate), governor.score(perturbed))
        inputs = governor.selection_inputs(candidate)
        self.assertEqual(set(inputs), set(bias_governor.SELECTION_INPUT_FIELDS))
        self.assertFalse(any("expect" in key or "predict" in key or "delta" in key
                             for key in inputs))
        # The closed input set itself documents the ban.
        self.assertNotIn("preregistered_expectation",
                         bias_governor.SELECTION_INPUT_FIELDS)

    # T9 --------------------------------------------------------------------
    def test_t9_quota_steering_and_enforcement(self):
        policy = base_policy(min_falsification_share=0.6)
        payloads = generator.generate_proposals(self.view, policy, seed=1, limit=4)
        self.assertTrue(payloads)
        self.assertTrue(all(p["proposal_class"] == "falsification"
                            for p in payloads[:3]),
                        [p["proposal_class"] for p in payloads])
        governor = bias_governor.BiasGovernor(policy)
        state = {"total": 1,
                 "by_class": {"confirmatory": 1, "falsification": 0},
                 "by_direction": {"feature_engineering": 1},
                 "by_signature": {"sig": 1}}
        payload = {"proposal_class": "confirmatory",
                   "direction": "calibration", "design_signature": "sig2"}
        ok, reason, _ = governor.check_accept(payload, state)
        self.assertFalse(ok)
        self.assertEqual(reason, schema.RC_BIAS_QUOTA)

    # Extra: flag OFF must write nothing ------------------------------------
    def test_flag_off_cycle_refuses_and_writes_nothing(self):
        self.assertFalse(proposals_enabled(self.root))  # fixture has no flag file
        before = sorted(p for p in self.root.rglob("*"))
        with self.assertRaises(cycle.DisabledError):
            cycle.run_proposal_cycle(self.root, seed=1)
        after = sorted(p for p in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertFalse((self.root / "autonomous_agent/state"
                          / "proposal_ledger.jsonl").exists())

    def test_real_repository_flag_matches_reviewed_file(self):
        # Campaign 2 Stage 1 (2026-10-04) explicitly authorized setting
        # allow_generated_proposals = true in the reviewed flag file; the old
        # "flag is off" assertion encoded the Phase-2 invariant and is
        # superseded here transparently (documented in the Stage 1 audit).
        # Durable invariants kept: the flag is a strict boolean, the reader
        # mirrors the file fail-closed, and the flag stays SEPARATE from
        # Campaign 1's autonomy_config.json (which must remain untouched).
        data = json.loads((REPO_ROOT / "autonomous_agent/proposal_config.json")
                          .read_text(encoding="utf-8"))
        self.assertIn(data.get("allow_generated_proposals"), (True, False))
        self.assertIs(proposals_enabled(REPO_ROOT),
                      data.get("allow_generated_proposals") is True)
        autonomy = json.loads((REPO_ROOT / "autonomous_agent/autonomy_config.json")
                              .read_text(encoding="utf-8"))
        self.assertIs(autonomy.get("allow_autonomous_specs"), True)  # C1 setting
        # Fail-closed: missing/malformed flag => OFF.
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(proposals_enabled(tmp))
            (Path(tmp) / "autonomous_agent").mkdir()
            (Path(tmp) / "autonomous_agent/proposal_config.json").write_text(
                "{not json", encoding="utf-8")
            self.assertFalse(proposals_enabled(tmp))

    # T10 -------------------------------------------------------------------
    def test_t10_lifecycle_state_machine(self):
        payload = self.make_payload()
        pid = self.ledger.create_proposal(payload)
        self.assertEqual(self.ledger.status(pid), schema.STATUS_PROPOSED)
        # Illegal transitions bypassing validation are impossible.
        for illegal in (schema.STATUS_COMPILED, schema.STATUS_EXECUTED,
                        schema.STATUS_ACCEPTED_FOR_EXECUTION,
                        schema.STATUS_PROMOTED, schema.STATUS_REFUSED):
            with self.assertRaises(ledger.LedgerError):
                self.ledger.transition(pid, illegal)
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition("prop-nonexistent-1", schema.STATUS_VALIDATING)
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition(pid, "NOT_A_STATUS")
        # Legal chain, end to end.
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        self.approve(pid)
        self.ledger.transition(pid, schema.STATUS_COMPILED)
        self.ledger.transition(pid, schema.STATUS_EXECUTED,
                               detail={"result": "REJECTED"})
        self.ledger.transition(pid, schema.STATUS_ADJUDICATED,
                               reason_code="GATES_FAILED")
        # Terminal states stay terminal (rejected outcomes are preserved).
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition(pid, schema.STATUS_PROMOTED)
        # FAILED_* terminal paths also exist.
        pid2 = self.ledger.create_proposal(self.make_payload(
            params={"arm_pair": "B->C", "estimator": "LightGBM",
                    "n_boot": 500}))
        self.ledger.transition(pid2, schema.STATUS_VALIDATING)
        self.ledger.transition(pid2, schema.STATUS_FAILED_VALIDATION,
                               reason_code=schema.RC_NOT_FALSIFIABLE)
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition(pid2, schema.STATUS_VALIDATING)

    # T11 -------------------------------------------------------------------
    def test_t11_no_dynamic_code_anywhere_in_layer(self):
        banned_calls = {"eval", "exec", "compile", "__import__"}
        banned_modules = {"subprocess", "pickle", "joblib", "ctypes",
                          "importlib", "shutil", "pty"}
        layer_dir = REPO_ROOT / "autonomous_agent/proposal_layer"
        for path in sorted(layer_dir.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    name = None
                    if isinstance(func, ast.Name):
                        name = func.id
                    elif isinstance(func, ast.Attribute):
                        # re.compile() compiles a regex pattern, not code.
                        if (func.attr == "compile"
                                and isinstance(func.value, ast.Name)
                                and func.value.id == "re"):
                            name = None
                        else:
                            name = func.attr
                    self.assertNotIn(name, banned_calls,
                                     f"{path.name}:{node.lineno} calls {name}")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split(".")[0], banned_modules,
                                         f"{path.name} imports {alias.name}")
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], banned_modules,
                                     f"{path.name} imports {node.module}")
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("os.system", source)
            self.assertNotIn("os.popen", source)

    # T12 -------------------------------------------------------------------
    @staticmethod
    def _imports_of(path: Path) -> set[str]:
        """Every module/imported name referenced by an import statement."""
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module)
                names.update(alias.name for alias in node.names)
        return names

    def test_t12_import_boundaries(self):
        layer_dir = REPO_ROOT / "autonomous_agent/proposal_layer"
        # (a) generator side never imports the execution path (H.T12: an
        # IMPORT boundary — docstrings may *name* the boundary, imports may
        # not cross it).
        banned_modules = ("experiment_adapter", "recipe_harness",
                          "spec_recipes", "run_experiment")
        for name in ("schema.py", "evidence_view.py", "primitives.py",
                     "ledger.py", "bias_governor.py", "generator.py",
                     "__init__.py"):
            imports = self._imports_of(layer_dir / name)
            for token in banned_modules:
                self.assertFalse(any(token in item for item in imports),
                                 f"{name} imports {token}: {sorted(imports)}")
            self.assertFalse(
                any(item.rsplit(".", 1)[-1] in ("compiler", "cycle")
                    for item in imports),
                f"{name} imports compiler/cycle: {sorted(imports)}")
        # generator specifically (Phase 1 H.T12).
        gen_imports = self._imports_of(layer_dir / "generator.py")
        self.assertFalse(any("compiler" in item for item in gen_imports),
                         sorted(gen_imports))
        self.assertFalse(any(item.rsplit(".", 1)[-1] == "cycle"
                              for item in gen_imports), sorted(gen_imports))
        # (b) the execution path never imports the proposal layer.
        for name in ("experiment_adapter.py", "core.py",
                     "recipe_harness.py", "hardening.py"):
            path = REPO_ROOT / "autonomous_agent" / name
            imports = self._imports_of(path)
            self.assertFalse(any("proposal_layer" in item for item in imports),
                             f"{name}: {sorted(imports)}")
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("proposal_layer", source, name)

    # T13 -------------------------------------------------------------------
    def test_t13_ledger_corrupt_tail_preserves_prior_rows(self):
        pid = self.ledger.create_proposal(self.make_payload())
        intact = self.ledger.path.read_bytes()
        with open(self.ledger.path, "a", encoding="utf-8") as stream:
            stream.write('{"row_type": "partial')  # simulated crash mid-write
        with self.assertRaises(ledger.LedgerCorrupt):
            self.ledger.read_rows(strict=True)
        tolerant = self.ledger.read_rows(strict=False)
        self.assertEqual(tolerant[-1]["__corrupt_lines__"], 1)
        self.assertTrue(any(row.get("proposal_id") == pid
                            for row in tolerant if isinstance(row, dict)))
        self.assertTrue(self.ledger.path.read_bytes().startswith(intact))

    # T14 -------------------------------------------------------------------
    def test_t14_generator_performs_no_io_and_no_execution(self):
        policy = base_policy()
        with mock.patch.object(builtins, "open",
                               side_effect=AssertionError("generator I/O")):
            payloads = generator.generate_proposals(self.view, policy,
                                                    seed=3, limit=3)
        self.assertEqual(len(payloads), 3)
        # Full generate -> validate -> approve -> compile with execution
        # primitives armed: none may be touched.
        def boom(*args, **kwargs):
            raise AssertionError("execution attempted")
        with mock.patch.object(subprocess, "Popen", side_effect=boom), \
                mock.patch.object(subprocess, "run", side_effect=boom), \
                mock.patch.object(subprocess, "call", side_effect=boom), \
                mock.patch("os.system", side_effect=boom):
            payload = payloads[0]
            pid = self.ledger.create_proposal(payload)
            self.ledger.transition(pid, schema.STATUS_VALIDATING)
            report = self.validate(payload, policy=policy, proposal_id=pid)
            self.assertTrue(report.passed, report.to_dict())
            self.approve(pid, policy=policy)
            spec, spec_sha = compiler.compile_proposal(
                payload, root=self.root,
                status=schema.STATUS_ACCEPTED_FOR_EXECUTION)
            self.assertEqual(len(spec_sha), 64)
        # No candidate workspace or other execution artifact was created.
        self.assertFalse((self.root / "autonomous_agent/candidates").exists())
        registry = json.loads((self.root / "autonomous_agent/state"
                               / "experiment_registry.json").read_text())
        self.assertEqual(registry["attempts"], [])  # adapter records, not compiler

    # T15 -------------------------------------------------------------------
    def test_t15_budget_permanence_across_restart(self):
        policy = base_policy(max_per_direction=2)
        p1 = self.make_payload()
        id1 = self.ledger.create_proposal(p1)
        self.ledger.transition(id1, schema.STATUS_VALIDATING)
        p2 = self.make_payload(params={"arm_pair": "A->B",
                                       "estimator": "LightGBM",
                                       "n_boot": 500})
        id2 = self.ledger.create_proposal(p2)
        self.ledger.transition(id2, schema.STATUS_VALIDATING)
        # Simulate restart: brand-new ledger instance re-reads from disk.
        fresh = ledger.ProposalLedger(self.ledger.path, clock=FIXED_CLOCK)
        p3 = self.make_payload(params={"arm_pair": "B->C",
                                       "estimator": "LightGBM",
                                       "n_boot": 500})
        # Distinct hypothesis so the text gate cannot mask the budget gate.
        p3["hypothesis"] = ("Budget probe: unique wording for the direction-cap "
                            "enforcement check across a ledger restart.")
        p3["proposal_fingerprint"] = schema.proposal_fingerprint(p3)
        id3 = fresh.create_proposal(p3)
        fresh.transition(id3, schema.STATUS_VALIDATING)
        report = validator.validate_proposal(
            p3, root=self.root, view=self.view,
            merged_history=fresh.all_proposals(), policy=policy,
            proposal_id=id3)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_BUDGET_EXHAUSTED)
        self.assertEqual(report.status_target, "REFUSED")

    # T16 -------------------------------------------------------------------
    def test_t16_compiler_boundary_and_spec_validation_after_compilation(self):
        # C->D + LogisticRegression + 1500 was never run in Campaign 1, so
        # the DUPLICATE gate cannot mask the boundary checks below.
        payload = self.make_payload(params={"arm_pair": "C->D",
                                            "estimator": "LogisticRegression",
                                            "n_boot": 1500})
        # Not ACCEPTED_FOR_EXECUTION -> boundary refusal.
        with self.assertRaises(compiler.BoundaryViolation):
            compiler.compile_proposal(payload, root=self.root,
                                      status=schema.STATUS_PROPOSED)
        with self.assertRaises(compiler.BoundaryViolation):
            compiler.compile_proposal(payload, root=self.root,
                                      status=schema.STATUS_VALIDATING)
        # After validation + approval the single crossing works, and the
        # existing mechanical contract runs AFTER compilation.
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        report = self.validate(payload, proposal_id=pid)
        self.assertTrue(report.passed, report.to_dict())
        self.approve(pid)
        spec, spec_sha = compiler.compile_proposal(
            payload, root=self.root,
            status=self.ledger.status(pid))
        spec.validate()  # must not raise
        self.assertEqual(hardening_fingerprint(spec), spec_sha)
        self.assertTrue(spec.experiment_id.startswith("exp-proposal-"))
        self.assertFalse(spec.allow_repeat)
        self.assertEqual(spec.parent_version, "V2.0.8")
        self.assertIn("proposal_fingerprint", spec.provenance)
        self.assertIs(spec.provenance["llm_involved"], False)
        # The rendered experiment config satisfies the reviewed harness schema.
        from autonomous_agent.recipe_harness import validate_experiment_config
        config_entry = spec.changes()[-1]
        self.assertEqual(config_entry.path,
                         "autonomous_agent/experiments/experiment_config.json")
        config = json.loads(config_entry.content)
        self.assertEqual(validate_experiment_config(config), [])
        # SpecRegistry duplicate protection still applies at this boundary.
        from autonomous_agent import hardening
        hardening.SpecRegistry(self.root / "autonomous_agent/state").record(
            spec.to_dict(), spec.experiment_id, FIXED_CLOCK())
        with self.assertRaises(compiler.CompileError) as ctx:
            compiler.compile_proposal(payload, root=self.root,
                                      status=schema.STATUS_ACCEPTED_FOR_EXECUTION)
        self.assertEqual(ctx.exception.code, schema.RC_DUPLICATE)

    # T17 -------------------------------------------------------------------
    def test_t17_invalid_parent_fails_closed(self):
        champion_path = self.root / "CHAMPION.json"
        original = champion_path.read_text(encoding="utf-8")
        try:
            champion = json.loads(original)
            champion["version"] = "banana"
            champion_path.write_text(json.dumps(champion), encoding="utf-8")
            payload = self.make_payload()
            with self.assertRaises(compiler.CompileError) as ctx:
                compiler.preview_spec(payload, root=self.root)
            self.assertEqual(ctx.exception.code, schema.RC_INVALID_PARENT)
            # Rebuild view + payload AFTER the mutation so every evidence
            # hash matches: the only gate that can refuse is the fail-closed
            # parent resolution (INVALID_PARENT) — never a guess.
            view2 = evidence_view.build(self.root, clock=FIXED_CLOCK)
            payload2 = generator.payload_for(
                view2, "feature_arm_comparison",
                {"arm_pair": "C->D", "estimator": "LogisticRegression",
                 "n_boot": 1500}, "confirmatory")
            report = validator.validate_proposal(
                payload2, root=self.root, view=view2,
                merged_history=self.ledger.all_proposals(),
                policy=base_policy())
            self.assertFalse(report.passed)
            self.assertEqual(report.failed_gate, schema.GATE_MECHANICAL)
            self.assertEqual(report.reason_code, schema.RC_INVALID_PARENT)
        finally:
            champion_path.write_text(original, encoding="utf-8")

    # T18 -------------------------------------------------------------------
    def test_t18_generator_truthfulness_no_llm(self):
        payloads = generator.generate_proposals(self.view, base_policy(),
                                                seed=5, limit=5)
        for payload in payloads:
            self.assertEqual(payload["generator_type"],
                             schema.GENERATOR_TYPE_DETERMINISTIC)
            self.assertIs(payload.get("llm_involved", False), False)
        payload = self.make_payload()
        payload["generator_type"] = "llm_assisted"
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        report = self.validate(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code,
                         schema.RC_GENERATOR_NOT_PERMITTED)
        layer_dir = REPO_ROOT / "autonomous_agent/proposal_layer"
        for path in layer_dir.glob("*.py"):
            source = path.read_text(encoding="utf-8").lower()
            for token in ("openai", "anthropic", "litellm", "gpt-"):
                self.assertNotIn(token, source, path.name)
        self.assertEqual(schema.ALLOWED_GENERATOR_TYPES,
                         frozenset({"deterministic_compositional", "human"}))

    # Extras required by Phase 2 -------------------------------------------
    def test_campaign1_evidence_unchanged(self):
        for relative, expected in CAMPAIGN1_FROZEN_HASHES.items():
            path = REPO_ROOT / relative
            self.assertTrue(path.is_file(), f"missing: {relative}")
            self.assertEqual(sha_file(path), expected, relative)

    def test_refused_proposals_are_permanently_preserved(self):
        payload = self.make_payload()
        payload["falsification_rule"] = {"metric": "nope"}
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        report = self.validate(payload, proposal_id=pid)
        self.ledger.transition(pid, schema.STATUS_FAILED_VALIDATION,
                               reason_code=report.reason_code,
                               detail=report.to_dict())
        # Restart: fresh ledger instance sees the refusal forever.
        fresh = ledger.ProposalLedger(self.ledger.path, clock=FIXED_CLOCK)
        merged = fresh.all_proposals()
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["status"], schema.STATUS_FAILED_VALIDATION)
        self.assertEqual(merged[0]["last_reason_code"], schema.RC_NOT_FALSIFIABLE)
        # It also feeds back as permanent already-asked memory.
        view2 = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                    ledger_rows=fresh.read_rows())
        self.assertEqual(len(view2["already_asked"]), 1)
        self.assertEqual(view2["already_asked"][0]["status"],
                         schema.STATUS_FAILED_VALIDATION)

    def test_full_cycle_with_flag_on_records_everything(self):
        # The flag is enabled ONLY inside this temporary fixture root.
        (self.root / "autonomous_agent").mkdir(exist_ok=True)
        (self.root / "autonomous_agent/proposal_config.json").write_text(
            json.dumps({"schema_version": 1,
                        "allow_generated_proposals": True}), encoding="utf-8")
        summary = cycle.run_proposal_cycle(self.root, seed=11,
                                           clock=FIXED_CLOCK,
                                           approver="phase2-test")
        self.assertEqual(len(summary["created"]), 3)
        self.assertEqual(len(summary["compiled"]), 3, summary)
        rows = self.ledger.read_rows()
        statuses = [row for row in rows if row.get("row_type") == "transition"]
        self.assertTrue(all(row["to"] in (schema.STATUS_VALIDATING,
                                          schema.STATUS_ACCEPTED_FOR_EXECUTION,
                                          schema.STATUS_COMPILED)
                            for row in statuses))
        self.assertTrue(any(row["to"] == schema.STATUS_COMPILED
                            for row in statuses))
        # Approved by recorded approver, compiled with spec hash recorded.
        compiled = [row for row in statuses if row["to"] == schema.STATUS_COMPILED]
        self.assertTrue(all(row["detail"].get("spec_sha256")
                            for row in compiled))
        # Nothing beyond the ledger + flag file was written: no candidates,
        # no experiments, no registry entries.
        self.assertFalse((self.root / "autonomous_agent/candidates").exists())
        registry = json.loads((self.root / "autonomous_agent/state"
                               / "experiment_registry.json").read_text())
        self.assertEqual(registry["attempts"], [])
        self.assertFalse((self.root / "study_files/outputs/study_v1/prospective/"
                          "secret.csv").read_bytes() in
                         self.ledger.path.read_bytes())

    def test_direction_priorities_mirror_research_planner(self):
        from autonomous_agent.core import ResearchPlanner
        policy = json.loads((REPO_ROOT / "autonomous_agent/proposal_layer"
                             / "bias_policy.json").read_text(encoding="utf-8"))
        planner = {h.direction: h.priority
                   for h in ResearchPlanner.BASE_DIRECTIONS}
        self.assertEqual(set(policy["directions"]), set(planner))
        self.assertEqual(policy["direction_priorities"], planner)

    def test_future_primitives_are_refused_by_compiler(self):
        payload = generator.payload_for(
            self.view, "purge_sensitivity_probe",
            {"arm_pair": "A->B", "n_boot": 500}, "falsification")
        with self.assertRaises(compiler.CompileError) as ctx:
            compiler.preview_spec(payload, root=self.root)
        self.assertEqual(ctx.exception.code,
                         schema.RC_PRIMITIVE_NOT_EXECUTABLE)
        # And the default policy never generates them.
        payloads = generator.generate_proposals(self.view, base_policy(),
                                                seed=2, limit=20)
        self.assertFalse(any(
            p["design"]["primitives"][0]["primitive_id"]
            == "purge_sensitivity_probe" for p in payloads))


# ---------------------------------------------------------------------------
# Campaign 2 Stage 1 RESOLUTION regression tests (2026-10-04)
#
# Task 1 / OBS-3: revalidate_at_approval@1.0.0 — a proposal valid at T1 may
#   become REFUSED/BUDGET_EXHAUSTED at approval T2 after state change.
# Task 2 / OBS-1: duplicate layers — fingerprint/signature refuse, cross-
#   signature templated wording does not; semantic equivalence limitation
#   documented, no heuristic.
# Task 3 / OBS-2: fail-closed scheduler — exhausted directions/signatures/
#   classes excluded, refusals permanent, research exhaustion reported.
# ---------------------------------------------------------------------------
    def _enable_flag_and_policy(self, **overrides):
        """Fixture flag ON + written bias policy (approve_pending loads it)."""
        (self.root / "autonomous_agent").mkdir(exist_ok=True)
        (self.root / "autonomous_agent/proposal_config.json").write_text(
            json.dumps({"schema_version": 1,
                        "allow_generated_proposals": True}),
            encoding="utf-8")
        policy_dir = self.root / "autonomous_agent/proposal_layer"
        policy_dir.mkdir(parents=True, exist_ok=True)
        file_policy = {"schema_version": 1,
                       "min_falsification_share": 0.0,
                       "max_replication_share": 1.0}
        file_policy.update(overrides)
        (policy_dir / "bias_policy.json").write_text(
            json.dumps(file_policy), encoding="utf-8")
        return cycle._load_policy(self.root)

    def _record(self, payload):
        """Create + VALIDATING in the ledger (an accounting record)."""
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        return pid

    def _rebuild_view(self):
        return evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=self.ledger.read_rows())

    # Task 1 — OBS-3: revalidation at approval ------------------------------
    def test_t19_obs3_state_change_between_validation_and_approval(self):
        # T1: proposal passes every gate while its direction is within cap.
        policy = self._enable_flag_and_policy(max_per_direction=1)
        params = {"arm_pair": "C->D", "estimator": "LogisticRegression",
                  "n_boot": 1500}
        payload = self.make_payload(params=params)
        pid = self._record(payload)
        report_t1 = self.validate(payload, policy=policy, proposal_id=pid)
        self.assertTrue(report_t1.passed, report_t1.to_dict())  # valid at T1

        # T2: a new record in the SAME direction pushes it over the cap.
        # The new record itself is refused (post-creation accounting) and
        # that refusal is permanent.
        other = self.make_payload(params={"arm_pair": "C->D",
                                          "estimator": "LightGBM",
                                          "n_boot": 500})
        oid = self._record(other)
        report_t2 = self.validate(other, policy=policy, proposal_id=oid)
        self.assertFalse(report_t2.passed)
        self.assertEqual(report_t2.reason_code, schema.RC_BUDGET_EXHAUSTED)
        self.assertEqual(report_t2.status_target, "REFUSED")
        self.ledger.transition(oid, schema.STATUS_REFUSED,
                               reason_code=report_t2.reason_code,
                               detail=report_t2.to_dict())

        # Approval at T2 re-evaluates CURRENT state: the T1-valid proposal
        # must become REFUSED/BUDGET_EXHAUSTED — never silently accepted.
        summary = cycle.approve_pending(self.root, approver="obs3-test",
                                        clock=FIXED_CLOCK)
        self.assertEqual(summary["approved"], [])
        self.assertEqual(len(summary["refused_at_approval"]), 1,
                         summary)
        entry = summary["refused_at_approval"][0]
        self.assertEqual(entry["proposal_id"], pid)
        self.assertEqual(entry["reason_code"], schema.RC_BUDGET_EXHAUSTED)

        # Expected final lifecycle state: REFUSED with the exact reason.
        self.assertEqual(self.ledger.status(pid), schema.STATUS_REFUSED)
        merged = self.ledger.get(pid)
        self.assertEqual(merged["last_reason_code"],
                         schema.RC_BUDGET_EXHAUSTED)

        # Approval provenance persisted: policy/version, who attempted, and
        # the exact quota_state snapshot the decision used.
        attempts = [row for row in merged["transitions"]
                    if (row.get("detail") or {}).get(
                        "revalidated_at_approval")]
        self.assertEqual(len(attempts), 1, merged["transitions"])
        detail = attempts[0]["detail"]
        self.assertEqual(detail["approval_policy"],
                         cycle.APPROVAL_POLICY)
        self.assertEqual(detail["approval_policy"],
                         "revalidate_at_approval@1.0.0")
        self.assertEqual(detail["approval_attempted_by"], "obs3-test")
        self.assertEqual(detail["reason_code"],
                         schema.RC_BUDGET_EXHAUSTED)
        self.assertEqual(detail["quota_state"]["by_direction"]
                         ["feature_engineering"], 2)
        self.assertEqual(detail["quota_state"]["total"], 2)

        # Never silently convert: no ACCEPTED_FOR_EXECUTION row exists.
        all_rows = self.ledger.read_rows()
        self.assertFalse(any(row.get("to") ==
                             schema.STATUS_ACCEPTED_FOR_EXECUTION
                             for row in all_rows))
        # The T2 refusal record itself was not deleted.
        self.assertEqual(self.ledger.status(oid), schema.STATUS_REFUSED)
        self.assertEqual(self.ledger.get(oid)["last_reason_code"],
                         schema.RC_BUDGET_EXHAUSTED)

    def test_t19b_obs3_restart_between_validation_and_approval(self):
        # T1 in process A.
        policy = self._enable_flag_and_policy(max_per_direction=1)
        payload = self.make_payload(params={"arm_pair": "C->D",
                                            "estimator": "LogisticRegression",
                                            "n_boot": 1500})
        pid = self._record(payload)
        report = self.validate(payload, policy=policy, proposal_id=pid)
        self.assertTrue(report.passed, report.to_dict())

        # RESTART between T1 and T2: brand-new ledger instance re-reads the
        # append-only file; the state change happens after the restart.
        fresh = ledger.ProposalLedger(self.ledger.path, clock=FIXED_CLOCK)
        other = self.make_payload(params={"arm_pair": "C->D",
                                          "estimator": "LightGBM",
                                          "n_boot": 500})
        oid = fresh.create_proposal(other)
        fresh.transition(oid, schema.STATUS_VALIDATING)
        report2 = validator.validate_proposal(
            other, root=self.root, view=self._rebuild_view(),
            merged_history=fresh.all_proposals(), policy=policy,
            proposal_id=oid)
        self.assertFalse(report2.passed)
        fresh.transition(oid, schema.STATUS_REFUSED,
                         reason_code=report2.reason_code,
                         detail=report2.to_dict())

        # Approval after the restart reads state from disk only.
        summary = cycle.approve_pending(self.root, approver="obs3-restart",
                                        clock=FIXED_CLOCK)
        self.assertEqual(summary["approved"], [])
        self.assertEqual([e["proposal_id"]
                          for e in summary["refused_at_approval"]], [pid])
        self.assertEqual(self.ledger.status(pid), schema.STATUS_REFUSED)
        attempts = [row for row in self.ledger.read_rows()
                    if row.get("row_type") == "transition"
                    and row.get("proposal_id") == pid
                    and (row.get("detail") or {}).get(
                        "revalidated_at_approval")]
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["detail"]["approval_policy"],
                         "revalidate_at_approval@1.0.0")

        # Idempotent: a second approval attempt records nothing new (the
        # proposal is no longer pending; no duplicate/contradictory rows).
        rows_before = len(self.ledger.read_rows())
        again = cycle.approve_pending(self.root, approver="obs3-restart",
                                      clock=FIXED_CLOCK)
        self.assertEqual(again, {"approved": [], "refused_at_approval": [],
                                 "failed_at_approval": [],
                                 "already_decided": []})
        self.assertEqual(len(self.ledger.read_rows()), rows_before)

    def test_t19c_obs3_sequential_approvals_persist_provenance(self):
        # Both proposals remain within budget: sequential approval at T2
        # must succeed and persist full approval provenance for each.
        self._enable_flag_and_policy()
        p1 = self.make_payload(params={"arm_pair": "C->D",
                                       "estimator": "LogisticRegression",
                                       "n_boot": 1500})
        p2 = self.make_payload(params={"arm_pair": "B->C",
                                       "estimator": "LogisticRegression",
                                       "n_boot": 500})
        pid1, pid2 = self._record(p1), self._record(p2)
        for payload, pid in ((p1, pid1), (p2, pid2)):
            report = self.validate(
                payload, policy=cycle._load_policy(self.root),
                proposal_id=pid)
            self.assertTrue(report.passed, report.to_dict())

        summary = cycle.approve_pending(self.root, approver="obs3-seq",
                                        clock=FIXED_CLOCK)
        self.assertEqual(summary["approved"], [pid1, pid2], summary)
        self.assertEqual(summary["refused_at_approval"], [])
        for pid in (pid1, pid2):
            self.assertEqual(self.ledger.status(pid),
                             schema.STATUS_ACCEPTED_FOR_EXECUTION)
            accepted = [row for row in self.ledger.get(pid)["transitions"]
                        if row["to"] == schema.STATUS_ACCEPTED_FOR_EXECUTION]
            self.assertEqual(len(accepted), 1)
            detail = accepted[0]["detail"]
            self.assertEqual(detail["approval_policy"],
                             "revalidate_at_approval@1.0.0")
            self.assertEqual(detail["approved_by"], "obs3-seq")
            self.assertTrue(detail["revalidated_at_approval"])
            self.assertEqual(detail["quota_state"]["total"], 2)
            self.assertIn("feature_engineering",
                          detail["quota_state"]["by_direction"])
        # Approval never compiles or executes anything.
        self.assertFalse(any(row.get("to") == schema.STATUS_COMPILED
                             for row in self.ledger.read_rows()))
        self.assertFalse((self.root / "autonomous_agent/candidates").exists())

    def test_t19d_obs3_ledger_requires_approval_provenance(self):
        payload = self.make_payload(params={"arm_pair": "C->D",
                                            "estimator": "LogisticRegression",
                                            "n_boot": 1500})
        pid = self._record(payload)
        # Missing entirely.
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition(pid, schema.STATUS_ACCEPTED_FOR_EXECUTION)
        # Partial provenance is still refused (fail-closed).
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition(pid, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                                   detail={"approved_by": "x"})
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition(pid, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                                   detail={"approval_policy":
                                           "revalidate_at_approval@1.0.0",
                                           "approved_by": "x"})
        # Only complete provenance crosses the boundary.
        self.approve(pid)
        self.assertEqual(self.ledger.status(pid),
                         schema.STATUS_ACCEPTED_FOR_EXECUTION)

    # Task 2 — OBS-1: duplicate layers -------------------------------------
    def test_t20a_duplicate_layer_exact_fingerprint_refused(self):
        payload = self.make_payload(params={"arm_pair": "C->D",
                                            "estimator": "LogisticRegression",
                                            "n_boot": 1500})
        pid = self._record(payload)
        first = self.validate(payload, proposal_id=pid)
        self.assertTrue(first.passed, first.to_dict())
        duplicate = dict(payload)          # byte-identical re-ask
        did = self._record(duplicate)
        report = self.validate(duplicate, proposal_id=did)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_DUPLICATE)
        self.assertEqual(report.reason_code, schema.RC_DUPLICATE)
        self.assertEqual(report.status_target, "REFUSED")

    def test_t20b_duplicate_layer_same_signature_high_text_refused(self):
        params = {"arm_pair": "C->D", "estimator": "LogisticRegression",
                  "n_boot": 1500}
        prior = self.make_payload(params=params)
        self._record(prior)
        # Same signature, delta declared, but near-identical wording: the
        # text layer still refuses within a signature (layer 2 + layer 3).
        repeat = self.make_payload(params=params,
                                   proposal_class="falsification")
        repeat["hypothesis"] = prior["hypothesis"] + " (re-ask)"
        repeat["delta_from_prior"] = "declared but wording unchanged"
        repeat["proposal_fingerprint"] = schema.proposal_fingerprint(repeat)
        self.assertGreaterEqual(
            schema.text_similarity(repeat["hypothesis"],
                                   prior["hypothesis"]),
            schema.NEAR_DUPLICATE_TEXT_THRESHOLD)
        rid = self._record(repeat)
        report = self.validate(repeat, proposal_id=rid)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_DUPLICATE)
        self.assertEqual(report.reason_code, schema.RC_NEAR_DUPLICATE)
        # Without delta_from_prior the signature layer refuses first.
        plain = self.make_payload(params=params,
                                  proposal_class="falsification")
        plain["hypothesis"] = ("Entirely different prose for a signature "
                               "already asked in this ledger fixture.")
        plain["proposal_fingerprint"] = schema.proposal_fingerprint(plain)
        pid = self._record(plain)
        report2 = self.validate(plain, proposal_id=pid)
        self.assertFalse(report2.passed)
        self.assertEqual(report2.reason_code, schema.RC_NEAR_DUPLICATE)

    def test_t20c_cross_signature_templated_text_allowed(self):
        # Templated hypotheses from the same primitive reach >= 0.90 text
        # similarity across DISTINCT design signatures (the OBS-1 trigger).
        p1 = self.make_payload(params={"arm_pair": "C->D",
                                       "estimator": "LogisticRegression",
                                       "n_boot": 1500})
        p2 = self.make_payload(params={"arm_pair": "C->D",
                                       "estimator": "LightGBM",
                                       "n_boot": 500})
        self.assertNotEqual(p1["design_signature"], p2["design_signature"])
        self.assertGreaterEqual(
            schema.text_similarity(p1["hypothesis"], p2["hypothesis"]),
            schema.NEAR_DUPLICATE_TEXT_THRESHOLD)
        self._record(p1)
        pid2 = self._record(p2)
        report = self.validate(p2, proposal_id=pid2)
        # Scientifically distinct designs are NOT refused on wording alone.
        self.assertTrue(report.passed, report.to_dict())
        # No DUPLICATE-layer failure was recorded (passing gates are not
        # individually appended; only failures are).
        self.assertFalse([g for g in report.gates
                          if g.gate == schema.GATE_DUPLICATE
                          and not g.passed], report.to_dict())

    def test_t20d_semantic_equivalence_is_a_documented_limitation(self):
        # Deterministic establishment of "same question" works whenever a
        # record exists: prior-campaign recipe replay is refused exactly.
        replay = generator.payload_for(
            self.view, "feature_arm_comparison",
            {"arm_pair": "A->B", "estimator": "LogisticRegression",
             "n_boot": 500}, "replication")
        report = self.validate(replay, proposal_id="none")
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_DUPLICATE)
        # Same signature (parameter-identical re-ask) is also refused: see
        # T20a (fingerprint) and T20b (signature/text).
        #
        # LIMITATION (documented, not heuristically "solved"): semantic
        # equivalence across DIFFERENT design signatures cannot be decided
        # deterministically without an LLM or arbitrary semantic code. The
        # system therefore distinguishes parameterized variants only via
        # signature-level accounting; wording may not refuse them. This test
        # pins that behavior deliberately — see
        # CAMPAIGN_2_STAGE_1_RESOLUTION_AUDIT_2026_10_04.md section G.
        p1 = self.make_payload(params={"arm_pair": "C->D",
                                       "estimator": "LogisticRegression",
                                       "n_boot": 1500})
        p2 = self.make_payload(params={"arm_pair": "C->D",
                                       "estimator": "LogisticRegression",
                                       "n_boot": 1000})
        p2["hypothesis"] = p1["hypothesis"]     # identical wording
        p2["proposal_fingerprint"] = schema.proposal_fingerprint(p2)
        self.assertNotEqual(p1["design_signature"], p2["design_signature"])
        self.assertGreaterEqual(
            schema.text_similarity(p1["hypothesis"], p2["hypothesis"]),
            schema.NEAR_DUPLICATE_TEXT_THRESHOLD)
        self._record(p1)
        pid2 = self._record(p2)
        report2 = self.validate(p2, proposal_id=pid2)
        self.assertTrue(report2.passed, report2.to_dict())
        # The signature cap still bounds how often one design may be asked.
        self.assertLessEqual(
            generator.capacity(self._rebuild_view(), base_policy())
            ["state"]["by_signature"][p1["design_signature"]],
            base_policy()["max_signature_count"])

    # Task 3 — OBS-2: fail-closed scheduler --------------------------------
    def test_t21a_exhausted_direction_excluded_from_ranking(self):
        policy = base_policy(max_per_direction=2)
        self._record(self.make_payload(
            params={"arm_pair": "C->D", "estimator": "LogisticRegression",
                    "n_boot": 1500}))
        self._record(self.make_payload(
            params={"arm_pair": "B->C", "estimator": "LogisticRegression",
                    "n_boot": 500}))        # both = feature_engineering
        view2 = self._rebuild_view()
        cap = generator.capacity(view2, policy)
        self.assertEqual(cap["remaining_by_direction"]
                         ["feature_engineering"], 0)
        payloads = generator.generate_proposals(view2, policy,
                                                seed=1, limit=10)
        self.assertTrue(payloads)             # other directions still have room
        self.assertTrue(all(p["direction"] != "feature_engineering"
                            for p in payloads),
                        [p["direction"] for p in payloads])
        report = generator.scheduler_report(view2, policy)
        self.assertIn("feature_engineering",
                      report["excluded_exhausted_directions"])
        self.assertEqual(report["remaining_by_direction"]
                         ["feature_engineering"], 0)
        self.assertFalse(report["exhausted"])

    def test_t21b_exhausted_signature_excluded_from_generation(self):
        policy = base_policy()
        # n_boot=500 is inside the generator grid, so this signature IS a
        # rankable candidate until it is recorded twice.
        params = {"arm_pair": "C->D", "estimator": "LogisticRegression",
                  "n_boot": 500}
        p1 = self.make_payload(params=params)
        p2 = self.make_payload(params=params, proposal_class="falsification")
        p2["hypothesis"] = ("Second distinct framing for the very same "
                            "design signature in this fixture ledger.")
        p2["proposal_fingerprint"] = schema.proposal_fingerprint(p2)
        self.assertEqual(p1["design_signature"], p2["design_signature"])
        self._record(p1)
        self._record(p2)                      # signature now at its cap
        view2 = self._rebuild_view()
        signature = p1["design_signature"]
        payloads = generator.generate_proposals(view2, policy,
                                                seed=1, limit=10)
        self.assertTrue(payloads)
        self.assertTrue(all(p["design_signature"] != signature
                            for p in payloads),
                        [p["design_signature"] for p in payloads])
        report = generator.scheduler_report(view2, policy)
        self.assertGreaterEqual(report["excluded_asked_signatures"], 1)
        self.assertGreaterEqual(
            generator.capacity(view2, policy)["state"]["by_signature"]
            [signature],
            policy["max_signature_count"])

    def test_t21c_refusal_remains_in_ledger_and_is_never_regenerated(self):
        policy = base_policy()
        # In-grid signature (n_boot=500) so regeneration would be possible
        # without the asked-signature exclusion.
        payload = self.make_payload(params={"arm_pair": "C->D",
                                            "estimator": "LogisticRegression",
                                            "n_boot": 500})
        payload["falsification_rule"] = {"metric": "nope"}
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        pid = self._record(payload)
        report = self.validate(payload, proposal_id=pid)
        self.assertFalse(report.passed)
        self.ledger.transition(pid, schema.STATUS_FAILED_VALIDATION,
                               reason_code=report.reason_code,
                               detail=report.to_dict())
        signature = payload["design_signature"]
        fingerprint = payload["proposal_fingerprint"]

        # Restart: fresh ledger; refusal record is permanent and visible.
        fresh = ledger.ProposalLedger(self.ledger.path, clock=FIXED_CLOCK)
        rows = fresh.read_rows(strict=True)
        refusals = [row for row in rows
                    if row.get("row_type") == "transition"
                    and row.get("proposal_id") == pid
                    and row.get("to") == schema.STATUS_FAILED_VALIDATION]
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0]["reason_code"],
                         report.reason_code)
        view2 = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                    ledger_rows=rows)
        asked = {item["proposal_id"]: item for item in
                 view2["already_asked"]}
        self.assertEqual(asked[pid]["status"],
                         schema.STATUS_FAILED_VALIDATION)

        # The scheduler never regenerates the refused proposal (any seed).
        for seed in range(1, 6):
            for p in generator.generate_proposals(view2, policy,
                                                  seed=seed, limit=10):
                self.assertNotEqual(p["design_signature"], signature)
                self.assertNotEqual(p["proposal_fingerprint"], fingerprint)
        rep = generator.scheduler_report(view2, policy)
        self.assertGreaterEqual(rep["excluded_asked_signatures"], 1)
        # And the refusal row is still there after all that generation.
        self.assertIn(refusals[0], fresh.read_rows(strict=True))

    def test_t21d_restart_preserves_exhaustion(self):
        policy = base_policy(max_per_direction=1)
        self._record(self.make_payload(
            params={"arm_pair": "C->D", "estimator": "LogisticRegression",
                    "n_boot": 1500}))
        view2 = self._rebuild_view()
        self.assertEqual(generator.capacity(view2, policy)
                         ["remaining_by_direction"]["feature_engineering"], 0)
        # Restart: brand-new ledger + view rebuilt from disk.
        fresh = ledger.ProposalLedger(self.ledger.path, clock=FIXED_CLOCK)
        view3 = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                    ledger_rows=fresh.read_rows(strict=True))
        cap = generator.capacity(view3, policy)
        self.assertEqual(cap["remaining_by_direction"]
                         ["feature_engineering"], 0)
        report = generator.scheduler_report(view3, policy)
        self.assertIn("feature_engineering",
                      report["excluded_exhausted_directions"])
        payloads = generator.generate_proposals(view3, policy,
                                                seed=3, limit=10)
        self.assertTrue(all(p["direction"] != "feature_engineering"
                            for p in payloads))

    def test_t21e_all_exhausted_reports_research_exhaustion(self):
        policy = base_policy(max_per_direction=1)
        # One record in every executable direction => all capacities zero.
        self._record(self.make_payload(                       # feature_engineering
            params={"arm_pair": "C->D", "estimator": "LogisticRegression",
                    "n_boot": 1500}))
        self._record(generator.payload_for(
            self.view, "model_class_comparison",
            {"arm": "C", "n_boot": 1000}, "confirmatory"))
        self._record(generator.payload_for(
            self.view, "calibration_stability_check",
            {"arm_pair": "C->D", "estimator": "LightGBM",
             "calibration_bins": 5, "n_boot": 500}, "confirmatory"))
        self._record(generator.payload_for(
            self.view, "year_stability_falsifier",
            {"arm_pair": "C->D", "estimator": "LogisticRegression",
             "n_boot": 1500}, "falsification"))
        view2 = self._rebuild_view()
        report = generator.scheduler_report(view2, policy)
        self.assertEqual(report["candidates_remaining"], 0)
        self.assertTrue(report["exhausted"])       # research exhaustion flag
        self.assertEqual(sorted(report["excluded_exhausted_directions"]),
                         sorted({"feature_engineering", "model_architecture",
                                 "calibration", "validation"}))
        # No pointless proposals are generated.
        self.assertEqual(generator.generate_proposals(view2, policy,
                                                      seed=1, limit=5), [])
        # Total-budget exhaustion is also fail-closed.
        total_policy = base_policy(max_total_proposals=4)     # 4 records exist
        cap = generator.capacity(view2, total_policy)
        self.assertEqual(cap["remaining_total"], 0)
        rep2 = generator.scheduler_report(view2, total_policy)
        self.assertTrue(rep2["excluded_total_budget"])
        self.assertTrue(rep2["exhausted"])
        self.assertEqual(generator.generate_proposals(view2, total_policy,
                                                      seed=1, limit=5), [])

    def test_t21f_exhausted_class_budget_excluded_from_ranking(self):
        # Class budgets bind exactly like direction caps: a class at its
        # cap can never admit a proposal, so ranking it would only create
        # guaranteed BUDGET refusals (churn).
        policy = base_policy(class_budgets={"confirmatory": 1,
                                            "falsification": 8,
                                            "replication": 2,
                                            "exploration": 2})
        self._record(self.make_payload(
            params={"arm_pair": "C->D", "estimator": "LogisticRegression",
                    "n_boot": 1500}))          # confirmatory now at cap
        view2 = self._rebuild_view()
        cap = generator.capacity(view2, policy)
        self.assertEqual(cap["remaining_by_class"]["confirmatory"], 0)
        payloads = generator.generate_proposals(view2, policy,
                                                seed=1, limit=10)
        self.assertTrue(payloads)
        self.assertTrue(all(p["proposal_class"] == "falsification"
                            for p in payloads),
                        [p["proposal_class"] for p in payloads])
        report = generator.scheduler_report(view2, policy)
        self.assertIn("confirmatory", report["excluded_exhausted_classes"])
        # And every generated payload still passes validation end-to-end:
        # no doomed proposal was created only to be refused.
        for p in payloads[:2]:
            pid = self._record(p)
            result = self.validate(p, policy=policy, proposal_id=pid)
            self.assertTrue(result.passed, result.to_dict())


def hardening_fingerprint(spec) -> str:
    from autonomous_agent import hardening
    return hardening.spec_fingerprint(spec.to_dict())


if __name__ == "__main__":
    unittest.main()
