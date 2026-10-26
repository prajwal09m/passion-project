"""Campaign 2 — PART 12/13: loop safety-contract hard-stop verification.

The Stage-5 loop docstring promises a closed list of hard stops. This module
verifies EVERY stop reason that had no direct test before, each on a
disposable fixture with mock executors only (no real execution, no real
state). Stops already covered elsewhere are listed in the readiness audit's
coverage table:

  already tested: STOP_FILE, INVALID_LEDGER_STATE, REPEATED_CRASHES,
  CAMPAIGN_CONFIG_HASH_MISMATCH (test_continuous_loop);
  EXECUTION_BUDGET, PROPOSAL_EXHAUSTED (test_continuous_loop + Stage 3);
  CAMPAIGN_CONFIG_CHANGED, HOLDOUT_TOUCHED, PROMOTION_FAILED (Stage 3).

  verified here: STOP_REQUESTED, LOCKED, FLAG_OFF, CHAMPION_UNREADABLE,
  HOLDOUT_STATE, CAMPAIGN_CONFIG_MISSING, CAMPAIGN_CONFIG_UNREADABLE,
  CAMPAIGN_CONFIG_INVALID, BUDGET_INCONSISTENCY, PORTFOLIO_COMPLETE,
  PROMOTION_BLOCKED.

Fixture logic is reused from Stage3Case via unbound calls (setUp runs on
this TestCase directly) so the fixture definition stays single-sourced.
"""
from __future__ import annotations

import json
import unittest

from autonomous_agent.continuous_loop import LoopStop
from autonomous_agent.proposal_layer import generator, schema
from autonomous_agent.test_stage2_campaign import write_campaign
from autonomous_agent.test_stage3_adversarial import (
    CAMPAIGN, MockExecutor,
)


class SafetyContractCase(unittest.TestCase):
    # Stage3Case is imported LOCALLY inside these helpers: a module-level
    # import would make unittest collect its 26 tests twice.
    def setUp(self) -> None:
        from autonomous_agent.test_stage3_adversarial import Stage3Case
        Stage3Case.setUp(self)          # single-sourced fixture

    def tearDown(self) -> None:
        from autonomous_agent.test_stage3_adversarial import Stage3Case
        Stage3Case.tearDown(self)

    def make_loop(self, *args, **kwargs):
        from autonomous_agent.test_stage3_adversarial import Stage3Case
        return Stage3Case.make_loop(self, *args, **kwargs)

    def loop_state(self):
        from autonomous_agent.test_stage3_adversarial import Stage3Case
        return Stage3Case.loop_state(self)

    # -- in-process / lock stops --------------------------------------------
    def test_stop_requested_halts_cycle(self):
        loop = self.make_loop(max_cycles=1)
        loop.request_stop()
        with self.assertRaises(LoopStop) as ctx:
            loop.cycle_once()
        self.assertEqual(ctx.exception.reason, "STOP_REQUESTED")

    def test_second_loop_run_raises_locked(self):
        holder = self.make_loop(max_cycles=1)
        self.assertTrue(holder.acquire_lock())
        try:
            intruder = self.make_loop(max_cycles=1,
                                      executor=MockExecutor(self.root))
            with self.assertRaises(LoopStop) as ctx:
                intruder.run()          # raises before entering the cycle
            self.assertEqual(ctx.exception.reason, "LOCKED")
        finally:
            holder.release_lock()
        self.assertFalse((self.root / "autonomous_agent/state"
                          / "loop.lock").exists())

    # -- feature-flag stop ---------------------------------------------------
    def test_flag_off_stops_loop(self):
        (self.root / "autonomous_agent/proposal_config.json").write_text(
            json.dumps({"schema_version": 1,
                        "allow_generated_proposals": False}),
            encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "FLAG_OFF")
        self.assertEqual(executor.calls, [])
        self.assertEqual(summary["status"], "STOPPED")

    # -- champion stops ------------------------------------------------------
    def test_champion_unreadable_stops_loop(self):
        (self.root / "CHAMPION.json").write_text("{not json",
                                                 encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "CHAMPION_UNREADABLE")
        self.assertEqual(executor.calls, [])

    def test_holdout_not_sealed_stops_loop(self):
        champion_path = self.root / "CHAMPION.json"
        champion = json.loads(champion_path.read_text("utf-8"))
        champion["holdout_policy"] = {"status": "OPENED", "uses": 1,
                                      "policy": "attack: use the holdout"}
        champion_path.write_text(json.dumps(champion, indent=1),
                                 encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "HOLDOUT_STATE")
        self.assertEqual(executor.calls, [])

    # -- campaign-config stops ----------------------------------------------
    def test_missing_sidecar_stops_loop(self):
        (self.root / "autonomous_agent/state"
         / "campaign_config.sha256").unlink()
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "CAMPAIGN_CONFIG_MISSING")
        self.assertEqual(executor.calls, [])

    def test_unreadable_campaign_config_stops_loop(self):
        import hashlib
        path = self.root / "autonomous_agent/state/campaign_config.json"
        path.write_text("{corrupt", encoding="utf-8")
        (self.root / "autonomous_agent/state"
         / "campaign_config.sha256").write_text(
            hashlib.sha256(path.read_bytes()).hexdigest() + "\n",
            encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"],
                         "CAMPAIGN_CONFIG_UNREADABLE")
        self.assertEqual(executor.calls, [])

    def test_invalid_campaign_config_stops_loop(self):
        import hashlib
        path = self.root / "autonomous_agent/state/campaign_config.json"
        config = json.loads(path.read_text("utf-8"))
        del config["campaign_id"]          # valid JSON, invalid contract
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        (self.root / "autonomous_agent/state"
         / "campaign_config.sha256").write_text(
            hashlib.sha256(path.read_bytes()).hexdigest() + "\n",
            encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "CAMPAIGN_CONFIG_INVALID")
        self.assertEqual(executor.calls, [])

    def test_negative_budget_stops_loop(self):
        # A (hypothetically tampered) negative proposal budget is
        # inconsistent state, not permission: the precheck refuses it.
        write_campaign(
            self.root,
            policy_overrides={"campaign_id": CAMPAIGN,
                              "max_total_proposals": -5,
                              "max_per_direction": 2,
                              "max_signature_count": 2,
                              "min_falsification_share": 0.35,
                              "max_replication_share": 0.5,
                              "class_budgets": {"confirmatory": 4,
                                                "falsification": 4,
                                                "replication": 1,
                                                "exploration": 1},
                              "max_proposals_per_cycle": 3,
                              "require_human_approval": False})
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "BUDGET_INCONSISTENCY")
        self.assertEqual(executor.calls, [])

    # -- portfolio-complete stop --------------------------------------------
    def test_portfolio_complete_stops_loop(self):
        write_campaign(
            self.root,
            policy_overrides={"campaign_id": CAMPAIGN,
                              "max_total_proposals": 2,
                              "max_per_direction": 2,
                              "max_signature_count": 2,
                              "min_falsification_share": 0.0,
                              "max_replication_share": 0.5,
                              "class_budgets": {"confirmatory": 2,
                                                "falsification": 2,
                                                "replication": 1,
                                                "exploration": 1},
                              "max_proposals_per_cycle": 3,
                              "require_human_approval": False})
        # Craft both portfolio classes adjudicated (2 records = budget 2,
        # so remaining proposal capacity is exactly 0) with nothing waiting.
        approval = {"approval_policy": "revalidate_at_approval@1.0.0",
                    "approved_by": "policy:readiness",
                    "quota_state": {"total": 1}}
        for proposal_class, params in (
                ("falsification",
                 {"arm_pair": "C->D", "estimator": "LogisticRegression",
                  "n_boot": 1500}),
                ("confirmatory",
                 {"arm_pair": "C->D", "estimator": "LightGBM",
                  "n_boot": 500})):
            payload = generator.payload_for(
                self.view, "feature_arm_comparison", params, proposal_class)
            payload["campaign_id"] = CAMPAIGN
            payload["proposal_fingerprint"] = schema.proposal_fingerprint(
                payload)
            pid = self.ledger.create_proposal(payload)
            self.ledger.transition(pid, schema.STATUS_VALIDATING)
            self.ledger.transition(pid, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                                   reason_code="HUMAN_APPROVAL",
                                   detail=approval)
            self.ledger.transition(pid, schema.STATUS_COMPILED,
                                   reason_code="COMPILED",
                                   detail={"spec_sha256": "s" * 64})
            self.ledger.transition(pid, schema.STATUS_EXECUTED,
                                   reason_code="EXECUTION_STARTED",
                                   detail={"phase": "finished"})
            self.ledger.transition(pid, schema.STATUS_ADJUDICATED,
                                   reason_code="GATES_FAILED",
                                   detail={"result": "REJECTED"})
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=3, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "PORTFOLIO_COMPLETE")
        self.assertEqual(executor.calls, [])
        state = self.loop_state()
        self.assertEqual(state["status"], "STOPPED")

    # -- promotion-blocked stop (defense in depth) --------------------------
    def test_promotion_blocked_when_champion_invalid(self):
        # Champion parses to nothing (defense in depth behind the
        # CHAMPION_UNREADABLE precheck): promotion refuses, never promotes.
        (self.root / "CHAMPION.json").write_text(
            json.dumps({"version": "banana",
                        "holdout_policy": {"status": "SEALED",
                                           "uses": 0}}),
            encoding="utf-8")
        loop = self.make_loop(max_cycles=1)
        with self.assertRaises(LoopStop) as ctx:
            loop._promote({"id": "exp-probe"}, {"status": "ACCEPTED"})
        self.assertEqual(ctx.exception.reason, "PROMOTION_BLOCKED")


if __name__ == "__main__":
    unittest.main()
