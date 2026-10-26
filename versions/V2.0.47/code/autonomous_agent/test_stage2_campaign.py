"""Campaign 2 Stage 2 regression tests: campaign-scoped budgets.

Campaign budgets are scoped to one campaign while duplicate/already-asked
memory stays global and permanent. Approval carries full provenance
(revalidate_at_approval@1.0.0). Everything runs in disposable fixtures.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from autonomous_agent.proposal_layer import (
    bias_governor, cycle, evidence_view, generator, ledger, schema, validator,
)
from autonomous_agent.test_proposal_layer import (
    FIXED_CLOCK, base_policy, build_fixture,
)

CAMPAIGN = "campaign-unit-test"


def write_campaign(root: Path, **overrides) -> dict:
    config = {
        "schema_version": 1,
        "campaign_id": CAMPAIGN,
        "stage_id": "stage-2",
        "execution": {"max_total_executions": 4},
        "portfolio": {"falsification_minimum": {"count": 1},
                      "confirmatory_minimum": {"count": 1}},
        "approval": {"approver": "policy:unit-test"},
        "policy_overrides": {
            "campaign_id": CAMPAIGN,
            "max_total_proposals": 8,
            "max_per_direction": 2,
            "max_signature_count": 2,
            "min_falsification_share": 0.35,
            "max_replication_share": 0.5,
            "class_budgets": {"confirmatory": 4, "falsification": 4,
                              "replication": 1, "exploration": 1},
            "max_proposals_per_cycle": 3,
            "require_human_approval": False,
        },
        "seed_base": 7,
        "immutable": True,
    }
    for key, value in overrides.items():
        config[key] = value
    state = root / "autonomous_agent/state"
    state.mkdir(parents=True, exist_ok=True)
    path = state / "campaign_config.json"
    path.write_text(json.dumps(config, indent=2, sort_keys=True),
                    encoding="utf-8", newline="\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (state / "campaign_config.sha256").write_text(digest + "\n",
                                                  encoding="utf-8")
    return config


class CampaignScopedBudgetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="stage2_test_"))
        self.root = self.tmp / "ws"
        self.root.mkdir(parents=True)
        build_fixture(self.root)
        (self.root / "autonomous_agent/proposal_config.json").write_text(
            json.dumps({"schema_version": 1,
                        "allow_generated_proposals": True}),
            encoding="utf-8")
        write_campaign(self.root)
        self.ledger = ledger.ProposalLedger(
            self.root / "autonomous_agent/state/proposal_ledger.jsonl",
            clock=FIXED_CLOCK)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- policy overlay ------------------------------------------------------
    def test_policy_overlay_loads_campaign_budgets(self):
        policy = cycle._load_policy(self.root)
        self.assertEqual(policy["campaign_id"], CAMPAIGN)
        self.assertEqual(policy["max_total_proposals"], 8)
        self.assertEqual(policy["max_per_direction"], 2)
        self.assertIs(policy["require_human_approval"], False)
        # Stage 1 bias_policy.json itself is never modified: the fixture's
        # absence of a bias_policy file proves the overlay alone supplies
        # these values on the real repository too.
        self.assertFalse((self.root / "autonomous_agent/proposal_layer"
                          / "bias_policy.json").exists())

    # -- scoped quota accounting --------------------------------------------
    def test_quota_state_counts_only_active_campaign(self):
        governor = bias_governor.BiasGovernor(base_policy())
        prior = [{"proposal": {"proposal_class": "confirmatory",
                               "direction": "feature_engineering",
                               "design_signature": "sig-old",
                               "proposal_fingerprint": f"fp-old-{index}"}}
                 for index in range(5)]
        current = [{"proposal": {"proposal_class": "confirmatory",
                                 "direction": "feature_engineering",
                                 "design_signature": "sig-new",
                                 "proposal_fingerprint": f"fp-{index}",
                                 "campaign_id": CAMPAIGN}}
                   for index in range(3)]
        scoped = governor.quota_state(prior + current, campaign_id=CAMPAIGN)
        self.assertEqual(scoped["total"], 3)
        legacy = governor.quota_state(prior + current)
        self.assertEqual(legacy["total"], 8)
        # Scoped counts can never exceed the scoped caps here.
        self.assertLessEqual(scoped["by_direction"]["feature_engineering"], 8)

    # -- generation stamps the campaign --------------------------------------
    def test_generated_payloads_carry_campaign_id_and_stable_fingerprint(self):
        policy = cycle._load_policy(self.root)
        rows = self.ledger.read_rows()
        view = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=rows)
        payloads = generator.generate_proposals(view, policy, seed=7, limit=3)
        self.assertTrue(payloads)
        for payload in payloads:
            self.assertEqual(payload["campaign_id"], CAMPAIGN)
        # campaign_id is NOT part of scientific identity: the fingerprint
        # equals the fingerprint of the same payload without the stamp.
        stripped = dict(payloads[0])
        self.assertEqual(stripped.pop("campaign_id"), CAMPAIGN)
        self.assertNotIn("campaign_id", stripped)
        self.assertEqual(schema.proposal_fingerprint(stripped),
                         payloads[0]["proposal_fingerprint"])

    # -- campaign mismatch is refused (fail-closed) --------------------------
    def test_foreign_proposal_refused_under_active_campaign(self):
        policy = cycle._load_policy(self.root)
        view = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=self.ledger.read_rows())
        payload = generator.payload_for(
            view, "feature_arm_comparison",
            {"arm_pair": "C->D", "estimator": "LogisticRegression",
             "n_boot": 1500}, "confirmatory")
        payload["campaign_id"] = "some-other-campaign"
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        report = validator.validate_proposal(
            payload, root=self.root, view=view,
            merged_history=self.ledger.all_proposals(), policy=policy,
            proposal_id=pid)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_BUDGET)
        self.assertEqual(report.reason_code, schema.RC_CAMPAIGN_MISMATCH)
        self.assertEqual(report.status_target, "REFUSED")

    def test_unstamped_proposal_refused_under_active_campaign(self):
        # A proposal from before the campaign (no campaign_id) can never be
        # approved under the campaign's budget.
        policy = cycle._load_policy(self.root)
        view = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=self.ledger.read_rows())
        payload = generator.payload_for(
            view, "feature_arm_comparison",
            {"arm_pair": "C->D", "estimator": "LogisticRegression",
             "n_boot": 1500}, "confirmatory")
        payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        report = validator.validate_proposal(
            payload, root=self.root, view=view,
            merged_history=self.ledger.all_proposals(), policy=policy,
            proposal_id=pid)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_CAMPAIGN_MISMATCH)

    # -- duplicate memory remains GLOBAL across campaigns --------------------
    def test_global_duplicate_memory_survives_budget_scoping(self):
        policy = cycle._load_policy(self.root)
        view = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=self.ledger.read_rows())
        # A prior-campaign recipe replay is still refused although its
        # records do not count against this campaign's budget.
        replay = generator.payload_for(
            view, "feature_arm_comparison",
            {"arm_pair": "A->B", "estimator": "LogisticRegression",
             "n_boot": 500}, "replication")
        replay["campaign_id"] = CAMPAIGN
        replay["proposal_fingerprint"] = schema.proposal_fingerprint(replay)
        pid = self.ledger.create_proposal(replay)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        report = validator.validate_proposal(
            replay, root=self.root, view=view,
            merged_history=self.ledger.all_proposals(), policy=policy,
            proposal_id=pid)
        self.assertFalse(report.passed)
        self.assertEqual(report.reason_code, schema.RC_DUPLICATE)

    # -- approval provenance carries Stage 2 fields --------------------------
    def test_approval_records_full_provenance(self):
        (self.root / "autonomous_agent").mkdir(exist_ok=True)
        policy = cycle._load_policy(self.root)
        view = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=self.ledger.read_rows())
        payloads = generator.generate_proposals(view, policy, seed=7, limit=1)
        payload = payloads[0]
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        summary = cycle.approve_pending(self.root, approver="policy:unit-test",
                                        clock=FIXED_CLOCK)
        # Fresh campaign budget: the first proposal must APPROVE.
        self.assertEqual(summary["approved"], [pid], summary)
        self.assertEqual(summary["refused_at_approval"], [])
        merged = self.ledger.get(pid)
        rows = [row for row in merged["transitions"]
                if (row.get("detail") or {}).get("revalidated_at_approval")]
        self.assertEqual(len(rows), 1)
        detail = rows[0]["detail"]
        self.assertEqual(detail["approval_policy"],
                         "revalidate_at_approval@1.0.0")
        self.assertEqual(detail["approved_by"], "policy:unit-test")
        self.assertEqual(detail["proposal_fingerprint"],
                         payload["proposal_fingerprint"])
        self.assertEqual(detail["design_signature"],
                         payload["design_signature"])
        self.assertTrue(detail["evidence_hashes"])
        self.assertEqual(detail["parent_version"],
                         payload["parent_version"])
        self.assertEqual(detail["baseline_id"], payload["baseline_id"])
        self.assertTrue(detail["protocol_sha256"])
        self.assertIn("quota_state", detail)


if __name__ == "__main__":
    unittest.main()
