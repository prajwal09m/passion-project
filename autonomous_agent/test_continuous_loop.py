"""Stage 5 infrastructure tests: persistent loop, recovery, stops (mock only).

Every test runs on a disposable fixture with an injected mock executor —
NO real experiment execution, NO real production state, NO supervisor.
Covers: one cycle, multiple cycles, crash recovery, restart, budget
exhaustion, proposal/direction/class exhaustion, STOP, stale locks,
duplicate prevention, state corruption, invalid lifecycle, repeated
crashes, campaign-config tampering, and promotion of a mock-accepted
result.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from autonomous_agent.continuous_loop import (LAUNCH_GATES_REL,
                                              LoopStop, ResearchLoop,
                                              REQUIRED_LAUNCH_GATES)
from autonomous_agent.proposal_layer import cycle, schema
from autonomous_agent.test_proposal_layer import FIXED_CLOCK, build_fixture
from autonomous_agent.test_stage2_campaign import write_campaign

CAMPAIGN = "campaign-loop-test"


def write_launch_gates(root, *, decided: bool = True) -> Path:
    """Write a fail-closed-satisfying launch-gate record into a fixture root.

    The loop refuses to start without ``launch_gates.json`` (F-5 fix). Tests
    that exercise OTHER stop paths need a gates file that passes, so the
    shared fixture defines all required gates as decided with durable
    evidence. Tests for the gate check itself overwrite this file
    deliberately. Evidence is a fixture-local file, NOT any production
    decision record: a test never asserts any real-world human approval.
    """
    evidence_rel = "autonomous_agent/launch_gates_evidence.md"
    (root / evidence_rel).write_text(
        "fixture launch-gate evidence: substituted for a real decision "
        "record in loop tests only\n", encoding="utf-8")
    gates = {name: {"decided": decided,
                    "decided_by": "fixture (synthetic, no real approval)",
                    "date": "2026-10-04",
                    "evidence_path": evidence_rel}
             for name in REQUIRED_LAUNCH_GATES}
    path = root / LAUNCH_GATES_REL
    path.write_text(json.dumps(gates, indent=1), encoding="utf-8")
    return path


def _rejected_outcome(experiment_id: str) -> dict:
    return {
        "status": "REJECTED",
        "checks": {"unit": "PASS", "data_integrity": "PASS",
                   "leakage": "PASS", "walk_forward": "PASS",
                   "robustness": "PASS", "evaluation": "FAIL"},
        "results": {"primary_metric": {"name": "pooled_roc_auc_delta",
                                       "delta": -0.004},
                    "decision_criteria_passed": False},
        "candidate_path": None,
        "holdout_touched": False,
        "rejection_reason": "mock: predeclared acceptance criteria not met",
        "blockers": [],
        "leakage_status": "PASS",
        "robustness_status": "PASS",
    }


def _accepted_outcome(root: Path, experiment_id: str) -> dict:
    """Full acceptance evidence + candidate workspace (mock artifacts)."""
    from autonomous_agent.core import tree_sha256
    candidate = root / "autonomous_agent/candidates" / experiment_id
    candidate.mkdir(parents=True, exist_ok=True)
    (candidate / "evaluation.json").write_text(
        json.dumps({"mock": True, "experiment_id": experiment_id}),
        encoding="utf-8")
    artifact = tree_sha256(candidate)
    metadata = {
        "dataset_id": "study_v1_development_event_table",
        "dataset_sha256": "d" * 64,
        "feature_set": ["f1"],
        "model": "mock",
        "target_definition": "mock target",
        "training_period": "2022-2025",
        "validation_period": "folds 2023/2024/2025",
        "research_test_period": "none (holdout SEALED)",
        "metrics": {"pooled_roc_auc_a": 0.5, "pooled_roc_auc_b": 0.51,
                    "delta_auc": 0.01},
        "backtest": {"status": "NOT_RUN", "reason": "mock"},
        "known_limitations": ["mock fixture evidence"],
        "reproduction_command": "py -3 -m autonomous_agent.experiments.run_experiment",
    }
    return {
        "experiment_id": experiment_id,
        "status": "ACCEPTED",
        "checks": {"unit": "PASS", "data_integrity": "PASS",
                   "leakage": "PASS", "walk_forward": "PASS",
                   "robustness": "PASS", "evaluation": "PASS"},
        "results": {
            "primary_metric": {"name": "pooled_roc_auc_delta", "delta": 0.01},
            "uncertainty_interval": {"lower": -0.001, "upper": 0.02},
            "practical_effect": {"delta_auc": 0.01},
            "decision_criteria_passed": True,
            "calibration": {"brier_delta": 0.0},
            "subgroup_stability": {"min_year_delta": 0.0},
            "per_seed_metrics": {"42": {}, "43": {}, "44": {}},
            "complexity_delta": {"delta": 0},
            "runtime_delta": {"delta_seconds": 0.0},
            "backtest": {"status": "NOT_RUN", "reason": "mock"},
        },
        "candidate_path": str(candidate),
        "holdout_touched": False,
        "artifact_sha256": artifact,
        "release_metadata": metadata,
        "reproduction_command": metadata["reproduction_command"],
        "blockers": [],
        "leakage_status": "PASS",
        "robustness_status": "PASS",
    }


class MockExecutor:
    def __init__(self, root: Path, accept_first: bool = False) -> None:
        self.root = root
        self.calls: list[str] = []
        self.accept_first = accept_first

    def __call__(self, spec) -> dict:
        self.calls.append(spec.experiment_id)
        if self.accept_first and len(self.calls) == 1:
            return _accepted_outcome(self.root, spec.experiment_id)
        return _rejected_outcome(spec.experiment_id)


class LoopTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="loop_test_"))
        self.root = self.tmp / "ws"
        self.root.mkdir(parents=True)
        build_fixture(self.root)
        # Complete the fixture champion so the reviewed promotion path
        # (parse_champion) accepts it in mock-acceptance tests.
        champion_path = self.root / "CHAMPION.json"
        champion = json.loads(champion_path.read_text("utf-8"))
        champion.setdefault("code_revision", "a" * 40)
        champion.setdefault("dataset_id", "fixture_dataset")
        champion.setdefault("feature_set", ["f1"])
        champion.setdefault("model", ["LogisticRegression"])
        champion.setdefault("target_definition", "fixture target")
        champion.setdefault("training_period", "2022-2025")
        champion.setdefault("validation_period", "folds 2023/2024/2025")
        champion.setdefault("backtest", {"status": "NOT_RUN"})
        champion.setdefault("leakage_status", "PASS")
        champion.setdefault("known_limitations", ["fixture"])
        champion.setdefault("reproduction_command",
                            "py -3 -m autonomous_agent.experiments.run_experiment")
        champion.setdefault("baseline_kind", "reconstructed_baseline")
        champion["lineage"] = {"relation": "reconstruction",
                               "parent": "V2.0.7"}
        champion.setdefault("v1_0_1_status", "FAILED")
        champion.setdefault("historical_v1_0_1_sha256", "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b")
        champion.setdefault("reconstructed_source_sha256", "b" * 40)
        champion.setdefault("self_reproduction", {"byte_identical": True})
        champion.setdefault("validation_scope",
                            "fixture: NOT a reproduction of V1.0.1")
        champion.setdefault("dataset_sha256", "c" * 64)
        champion.setdefault("created_at", "2026-10-04T00:00:00+00:00")
        champion_path.write_text(json.dumps(champion, indent=1),
                                 encoding="utf-8")
        (self.root / "autonomous_agent/proposal_config.json").write_text(
            json.dumps({"schema_version": 1,
                        "allow_generated_proposals": True}),
            encoding="utf-8")
        self.campaign = write_campaign(self.root)
        write_launch_gates(self.root)
        self.ledger_path = (self.root /
                            "autonomous_agent/state/proposal_ledger.jsonl")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_loop(self, max_cycles=4, executor=None, **kwargs) -> ResearchLoop:
        return ResearchLoop(self.root, max_cycles=max_cycles,
                            executor=executor or MockExecutor(self.root),
                            clock=FIXED_CLOCK, **kwargs)

    # -- one cycle / multiple cycles ----------------------------------------
    def test_one_cycle_generates_approves_and_executes(self):
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["cycles"], 1)
        self.assertEqual(summary["stop_reason"], "MAX_CYCLES")
        self.assertEqual(len(executor.calls), 1, executor.calls)
        rows = [json.loads(line) for line in
                self.ledger_path.read_text("utf-8").splitlines() if line.strip()]
        created = [r for r in rows if r.get("row_type") == "proposal"]
        self.assertTrue(created)
        transitions = [r["to"] for r in rows
                       if r.get("row_type") == "transition"]
        self.assertIn(schema.STATUS_ACCEPTED_FOR_EXECUTION, transitions)
        self.assertIn(schema.STATUS_COMPILED, transitions)
        self.assertIn(schema.STATUS_ADJUDICATED, transitions)
        state = json.loads((self.root / "autonomous_agent/state"
                            / "loop_state.json").read_text("utf-8"))
        self.assertEqual(state["executions_done"], 1)
        self.assertFalse((self.root / "autonomous_agent/state"
                          / "loop.lock").exists())

    def test_multiple_cycles_stop_at_execution_budget(self):
        self.campaign  # budget = 4 from write_campaign
        # shrink budget to 2 by rewriting the campaign config
        path = self.root / "autonomous_agent/state/campaign_config.json"
        config = json.loads(path.read_text("utf-8"))
        config["execution"]["max_total_executions"] = 2
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        (self.root / "autonomous_agent/state/campaign_config.sha256").write_text(
            hashlib.sha256(path.read_bytes()).hexdigest() + "\n",
            encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=10, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "EXECUTION_BUDGET")
        self.assertEqual(len(executor.calls), 2, executor.calls)
        # exactly one execution per experiment: no duplicates
        self.assertEqual(len(set(executor.calls)), len(executor.calls))
        state = json.loads((self.root / "autonomous_agent/state"
                            / "loop_state.json").read_text("utf-8"))
        self.assertEqual(state["executions_done"], 2)

    # -- STOP / locks --------------------------------------------------------
    def test_stop_file_halts_cleanly(self):
        stop = self.root / "autonomous_agent/state/STOP"
        stop.write_text("stop\n", encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=3, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "STOP_FILE")
        self.assertEqual(executor.calls, [])
        stop.unlink()
        # and the loop runs again after the STOP file is removed
        summary2 = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary2["stop_reason"], "MAX_CYCLES")

    def test_live_lock_blocks_and_stale_lock_recovers(self):
        lock = self.root / "autonomous_agent/state/loop.lock"
        # A live owner (this very process) must block acquisition.
        lock.write_text(f"pid={subprocess.os.getpid()} started=now\n",
                        encoding="utf-8")
        loop = self.make_loop(max_cycles=1)
        self.assertFalse(loop.acquire_lock())
        loop.release_lock()
        self.assertTrue(lock.exists())   # not ours: left alone
        # A provably dead owner must be recovered. The Popen object must
        # be dropped first: while it lives it holds an open handle to the
        # exited process, and Windows then still reports the pid as alive
        # to os.kill(pid, 0).
        # Windows recycles PIDs, so a previously exited pid is not
        # automatically "provably dead": a recycled (live or inaccessible)
        # pid makes the recovery path correctly refuse, which was the
        # captured 2026-10-11 flake (1 failure in 10 full-suite runs).
        # Verify the precondition instead of assuming it: obtain an exited
        # pid whose death os.kill confirms, retrying if it was recycled.
        dead_pid = None
        for _ in range(10):
            dead = subprocess.Popen(["cmd", "/c", "exit", "0"])
            candidate = dead.pid
            dead.wait()
            del dead
            try:
                os.kill(candidate, 0)
            except ProcessLookupError:
                dead_pid = candidate
                break
            except OSError as error:
                # Windows: nonexistent PID surfaces as generic OSError.
                if getattr(error, "errno", None) == getattr(os, "ESRCH", 3) \
                        or getattr(error, "winerror", None) in (87, 1168):
                    dead_pid = candidate
                    break
            # candidate was recycled by a live/inaccessible process: retry.
        self.assertIsNotNone(dead_pid,
                             "could not obtain a provably dead pid")
        lock.write_text(f"pid={dead_pid} started=now\n", encoding="utf-8")
        loop2 = self.make_loop(max_cycles=1)
        self.assertTrue(loop2.acquire_lock())
        loop2.release_lock()
        self.assertFalse(lock.exists())

    # -- corruption / invalid lifecycle / repeated crashes -------------------
    def test_corrupted_ledger_stops_loop(self):
        with open(self.ledger_path, "a", encoding="utf-8") as stream:
            stream.write('{"row_type": "partial')
        summary = self.make_loop(max_cycles=3).run()
        self.assertEqual(summary["stop_reason"], "INVALID_LEDGER_STATE")

    def test_invalid_lifecycle_stops_loop(self):
        from autonomous_agent.proposal_layer.ledger import LedgerError
        loop = self.make_loop(max_cycles=3)
        original = ResearchLoop.phase_generate_and_approve

        def boom(self_):
            raise LedgerError("forced illegal lifecycle move")

        ResearchLoop.phase_generate_and_approve = boom
        try:
            summary = loop.run()
        finally:
            ResearchLoop.phase_generate_and_approve = original
        self.assertEqual(summary["stop_reason"], "INVALID_LEDGER_STATE")
        self.assertIn("forced illegal", summary.get("stop_detail", ""))

    def test_repeated_crashes_stop_loop(self):
        loop = self.make_loop(max_cycles=10)
        original = ResearchLoop.phase_generate_and_approve

        def boom(self_):
            raise RuntimeError("synthetic crash")

        ResearchLoop.phase_generate_and_approve = boom
        try:
            summary = loop.run()
        finally:
            ResearchLoop.phase_generate_and_approve = original
        self.assertEqual(summary["stop_reason"], "REPEATED_CRASHES")
        state = json.loads((self.root / "autonomous_agent/state"
                            / "loop_state.json").read_text("utf-8"))
        self.assertEqual(state["consecutive_failures"], 3)

    # -- campaign config tampering ------------------------------------------
    def test_campaign_config_tamper_stops_loop(self):
        path = self.root / "autonomous_agent/state/campaign_config.json"
        config = json.loads(path.read_text("utf-8"))
        config["execution"]["max_total_executions"] = 999
        path.write_text(json.dumps(config, indent=2, sort_keys=True),
                        encoding="utf-8")
        summary = self.make_loop(max_cycles=3).run()
        self.assertEqual(summary["stop_reason"],
                         "CAMPAIGN_CONFIG_HASH_MISMATCH")

    # -- exhaustion ----------------------------------------------------------
    def test_proposal_budget_exhaustion_reports_research_exhaustion(self):
        path = self.root / "autonomous_agent/state/campaign_config.json"
        config = json.loads(path.read_text("utf-8"))
        config["policy_overrides"]["max_total_proposals"] = 0
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        (self.root / "autonomous_agent/state/campaign_config.sha256").write_text(
            hashlib.sha256(path.read_bytes()).hexdigest() + "\n",
            encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=3, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "PROPOSAL_EXHAUSTED")
        self.assertEqual(executor.calls, [])

    def test_direction_exhaustion_reports_research_exhaustion(self):
        path = self.root / "autonomous_agent/state/campaign_config.json"
        config = json.loads(path.read_text("utf-8"))
        config["policy_overrides"]["max_per_direction"] = 0
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        (self.root / "autonomous_agent/state/campaign_config.sha256").write_text(
            hashlib.sha256(path.read_bytes()).hexdigest() + "\n",
            encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=3, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "PROPOSAL_EXHAUSTED")
        self.assertEqual(executor.calls, [])
        report = ResearchLoop(self.root, max_cycles=1,
                              executor=executor).exhaustion_report()
        self.assertTrue(report["scheduler_exhausted"])
        self.assertTrue(report["excluded_exhausted_directions"])

    def test_class_exhaustion_reports_research_exhaustion(self):
        path = self.root / "autonomous_agent/state/campaign_config.json"
        config = json.loads(path.read_text("utf-8"))
        config["policy_overrides"]["class_budgets"] = {
            "confirmatory": 0, "falsification": 0,
            "replication": 0, "exploration": 0}
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        (self.root / "autonomous_agent/state/campaign_config.sha256").write_text(
            hashlib.sha256(path.read_bytes()).hexdigest() + "\n",
            encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=3, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "PROPOSAL_EXHAUSTED")
        self.assertEqual(executor.calls, [])
        report = ResearchLoop(self.root, max_cycles=1,
                              executor=executor).exhaustion_report()
        self.assertTrue(report["excluded_exhausted_classes"])

    # -- restart -------------------------------------------------------------
    def test_restart_resumes_from_durable_state(self):
        first = self.make_loop(max_cycles=1)
        first.run()
        state_after = json.loads((self.root / "autonomous_agent/state"
                                  / "loop_state.json").read_text("utf-8"))
        self.assertEqual(state_after["cycle"], 1)
        # brand-new instance: state reloaded from disk, lock acquirable
        executor = MockExecutor(self.root)
        second = self.make_loop(max_cycles=2, executor=executor)
        summary = second.run()
        self.assertEqual(summary["stop_reason"], "MAX_CYCLES")
        state_final = json.loads((self.root / "autonomous_agent/state"
                                  / "loop_state.json").read_text("utf-8"))
        self.assertEqual(state_final["cycle"], 2)
        self.assertEqual(len(executor.calls), 1)

    # -- crash recovery: never re-run ---------------------------------------
    def test_crash_recovery_adjudicates_durable_result_without_rerun(self):
        # Craft a crash window: a proposal marked EXECUTED/started whose
        # executor actually finished (durable result.json exists).
        loop = self.make_loop(max_cycles=1)
        policy = loop._policy()
        from autonomous_agent.proposal_layer import generator as gen_mod
        from autonomous_agent.proposal_layer import evidence_view
        ledger_obj = loop._ledger()
        view = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=ledger_obj.read_rows())
        payloads = gen_mod.generate_proposals(view, policy, seed=7, limit=1)
        payload = payloads[0]
        pid = ledger_obj.create_proposal(payload)
        ledger_obj.transition(pid, schema.STATUS_VALIDATING)
        ledger_obj.transition(
            pid, schema.STATUS_ACCEPTED_FOR_EXECUTION,
            reason_code="HUMAN_APPROVAL",
            detail={"approval_policy": "revalidate_at_approval@1.0.0",
                    "approved_by": "policy:test",
                    "quota_state": {"total": 1}})
        ledger_obj.transition(pid, schema.STATUS_COMPILED,
                              reason_code="COMPILED",
                              detail={"spec_sha256": "s" * 64,
                                      "experiment_id": "exp-proposal-crash01"})
        ledger_obj.transition(
            pid, schema.STATUS_EXECUTED, reason_code="EXECUTION_STARTED",
            detail={"phase": "started",
                    "experiment_id": "exp-proposal-crash01",
                    "spec_sha256": "s" * 64})
        result_dir = (self.root / "autonomous_agent/candidates"
                      / "exp-proposal-crash01")
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / "result.json").write_text(json.dumps({
            "experiment_id": "exp-proposal-crash01",
            "status": "REJECTED",
            "acceptance_recommendation": "REJECT",
            "metrics": {"primary_metric": {"delta": -0.002},
                        "decision_criteria_passed": False},
            "checks": {"unit": "PASS", "walk_forward": "PASS"},
            "error": {"message": "durable mock result"},
        }), encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        # recovered from result.json: adjudicated, executor never called
        # for that experiment (it may run a NEW proposal in the same cycle).
        merged = ledger_obj.get(pid)
        self.assertEqual(merged["status"], schema.STATUS_ADJUDICATED)
        self.assertEqual(merged["transitions"][-1]["detail"]["result"],
                         "REJECTED")
        self.assertNotIn("exp-proposal-crash01", executor.calls)
        self.assertLessEqual(len(executor.calls), 1)

    # -- promotion (mock-accepted) ------------------------------------------
    def test_accepted_result_is_promoted_with_full_provenance(self):
        executor = MockExecutor(self.root, accept_first=True)
        summary = self.make_loop(max_cycles=2, executor=executor).run()
        champion = json.loads((self.root / "CHAMPION.json").read_text("utf-8"))
        self.assertEqual(champion["version"], "V2.0.9")
        rows = [json.loads(line) for line in
                self.ledger_path.read_text("utf-8").splitlines() if line.strip()]
        promoted = [r for r in rows if r.get("to") == schema.STATUS_PROMOTED]
        self.assertEqual(len(promoted), 1)
        detail = promoted[0]["detail"]
        self.assertEqual(detail["version"], "V2.0.9")
        self.assertTrue(detail["artifact_sha256"])
        adjudicated = [r for r in rows
                       if r.get("to") == schema.STATUS_ADJUDICATED]
        accepted_rows = [r for r in adjudicated
                         if (r.get("detail") or {}).get("result") == "ACCEPTED"]
        self.assertEqual(len(accepted_rows), 1)
        # research memory + agent state updated (append-only)
        memory = json.loads((self.root / "autonomous_agent/state"
                             / "research_memory.json").read_text("utf-8"))
        self.assertTrue(any(d.get("accepted_version") == "V2.0.9"
                            for d in memory.get("discoveries", [])))
        agent = json.loads((self.root / "autonomous_agent/state"
                            / "agent_state.json").read_text("utf-8"))
        self.assertTrue(any(e.get("accepted_version") == "V2.0.9"
                            for e in agent.get("experiments", [])))
        human = (self.root / "RESEARCH_MEMORY.md").read_text("utf-8")
        self.assertIn("V2.0.9", human)
        # never re-execute the promoted experiment
        self.assertEqual(len(executor.calls), len(set(executor.calls)))

    # -- reconcile-refusal wiring: promotion continues, refusal journaled ----
    def test_promotion_survives_refused_reconcile_and_journals_refusal(self):
        """The _promote wiring is best-effort: when champion-state reconciliation
        refuses (here: the fixture snapshot tree carries no verifiable
        artifact anchor, so canonical verification fails deterministically),
        the promotion must still complete and the refusal must be recorded as
        evidence — never silently dropped."""
        executor = MockExecutor(self.root, accept_first=True)
        state_path = (self.root / "autonomous_agent/state"
                      / "agent_state.json")
        loop = self.make_loop(max_cycles=2, executor=executor)
        summary = loop.run()
        # The promotion itself succeeded despite the refused reconcile.
        champion = json.loads((self.root / "CHAMPION.json").read_text("utf-8"))
        self.assertEqual(champion["version"], "V2.0.9")
        rows = [json.loads(line) for line in
                self.ledger_path.read_text("utf-8").splitlines() if line.strip()]
        promoted = [r for r in rows if r.get("to") == schema.STATUS_PROMOTED]
        self.assertEqual(len(promoted), 1)
        self.assertEqual(promoted[0]["detail"]["version"], "V2.0.9")
        # And the refusal is on the durable journal, not swallowed.
        journal = [json.loads(line) for line in
                   loop.journal_path.read_text("utf-8").splitlines()
                   if line.strip()]
        refused = [r for r in journal
                   if r.get("event") == "champion_state_reconcile_refused"]
        self.assertEqual(len(refused), 1, journal[-5:])
        self.assertIn("could not be verified", str(refused[0].get("detail", "")))
        # Fail-closed: the refused reconcile must not have installed a
        # champion projection in agent_state (the loop's own bookkeeping may
        # legitimately rewrite other parts of the file).
        state_after = json.loads(state_path.read_text("utf-8"))
        self.assertNotIn("champion", state_after,
                         "refused reconcile must not modify the projection")
        self.assertNotIn("champion_projection_history", state_after,
                         "refused reconcile must not retire history")


# -- frozen diagnostic-promotion rule (2026-10-25 regression fix) ----------

def _make_diagnostic_payload(base_payload: dict) -> dict:
    """Rebrand a generated payload as an owner-predeclared error-cluster
    diagnostic (direction + primitive + axis), matching the frozen C5
    predeclaration vocabulary. Only identity fields are rewritten; no
    gate, threshold, floor, budget, or multiplicity value changes."""
    payload = json.loads(json.dumps(base_payload))  # deep copy
    payload["direction"] = "error_analysis"
    payload["hypothesis"] = (
        "[error_analysis] diagnostic axis regression fixture: does the "
        "predeclared non-degradation condition hold? (fixture only)")
    payload["design"] = {
        "primitives": [{"params": {"error_cluster_axis": "volume_confirmation"},
                        "primitive_id": "error_clustering_analysis"}],
        "protocol": {"folds": [2023, 2024, 2025], "seeds": [42, 43, 44]},
    }
    payload["parent_version"] = "V2.0.74"
    return payload


class DiagnosticPropagationClassificationTest(unittest.TestCase):
    """Unit tests for diagnostic_promotion_outcome classification.

    Read-only against the real frozen record; the fail-closed refusal
    statuses are exercised by monkeypatching the module map — no production
    artifact is ever touched or renamed.
    """

    def test_normal_payload_is_not_diagnostic(self):
        from autonomous_agent.continuous_loop import (diagnostic_promotion_outcome)
        payload = {"design": {"primitives": [
            {"params": {"arm": "C"}, "primitive_id": "model_class_comparison"}]}}
        self.assertIsNone(diagnostic_promotion_outcome(payload))

    def test_error_cluster_payload_reads_frozen_rule(self):
        from autonomous_agent.continuous_loop import (diagnostic_promotion_outcome)
        payload = {"design": {"primitives": [
            {"params": {"error_cluster_axis": "vix_regime"},
             "primitive_id": "error_clustering_analysis"}]}}
        result = diagnostic_promotion_outcome(payload)
        self.assertEqual(result[1], "frozen")
        self.assertIn("diagnostics, not promotions", str(result[0]))
        self.assertIn("V2.0.74", str(result[0]))

    def test_missing_predeclaration_refuses_promotion_fail_closed(self):
        from autonomous_agent import continuous_loop as cl
        payload = {"design": {"primitives": [
            {"params": {}, "primitive_id": "error_clustering_analysis"}]}}
        original = dict(cl._FROZEN_DIAGNOSTIC_PREDECLARATIONS)
        try:
            cl._FROZEN_DIAGNOSTIC_PREDECLARATIONS.update({
                "error_clustering_analysis": (
                    "NOT_A_REAL_PATH/predecl.json", "FROZEN_2026_10_25")})
            rule, status = cl.diagnostic_promotion_outcome(payload)
        finally:
            cl._FROZEN_DIAGNOSTIC_PREDECLARATIONS = original
        self.assertIsNone(rule)
        self.assertEqual(status, "record_missing")

    def test_unfrozen_predeclaration_refuses_promotion_fail_closed(self):
        from autonomous_agent import continuous_loop as cl
        import tempfile as _tempfile
        payload = {"design": {"primitives": [
            {"params": {}, "primitive_id": "error_clustering_analysis"}]}}
        tmp = _tempfile.mkdtemp()
        marker = Path(tmp) / "thawed.json"
        marker.write_text(json.dumps({"_status": "DRAFT"}), encoding="utf-8")
        original = dict(cl._FROZEN_DIAGNOSTIC_PREDECLARATIONS)
        try:
            cl._FROZEN_DIAGNOSTIC_PREDECLARATIONS.update({
                "error_clustering_analysis": (
                    str(marker), "FROZEN_2026_10_25")})
            rule, status = cl.diagnostic_promotion_outcome(payload)
        finally:
            cl._FROZEN_DIAGNOSTIC_PREDECLARATIONS = original
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertIsNone(rule)
        self.assertEqual(status, "record_not_frozen")


class DiagnosticRetentionLoopTest(LoopTestCase):
    """2026-10-25 promotion defect regression: an ACCEPTED diagnostic run
    under a frozen champion_rule predeclaration must be RETAINED as a
    diagnostic — no version directory, no CHAMPION.json change, and a
    ledger adjudication that permanently refuses PROMOTED.
    """

    def _stage_executed_diagnostic(self, ledger_obj, payload,
                                   experiment_id="exp-proposal-diag01"):
        from autonomous_agent.proposal_layer import compiler
        pid = ledger_obj.create_proposal(payload)
        ledger_obj.transition(pid, schema.STATUS_VALIDATING)
        ledger_obj.transition(
            pid, schema.STATUS_ACCEPTED_FOR_EXECUTION,
            reason_code="POLICY_AUTO_APPROVAL",
            detail={"approval_policy": "revalidate_at_approval@1.0.0",
                    "approved_by": "fixture (synthetic)",
                    "quota_state": {"total": 1}})
        ledger_obj.transition(pid, schema.STATUS_COMPILED,
                              reason_code="COMPILED",
                              detail={"spec_sha256": "s" * 64,
                                      "experiment_id": experiment_id})
        ledger_obj.transition(
            pid, schema.STATUS_EXECUTED, reason_code="EXECUTION_STARTED",
            detail={"phase": "started", "experiment_id": experiment_id,
                    "spec_sha256": "s" * 64})
        assert compiler.preview_spec(payload, root=self.root)  # compilable
        accepted = _accepted_outcome(self.root, experiment_id)
        # Durable adapter-shaped result (ExperimentResult.from_dict reads
        # ``metrics``, not ``results``): same evidence, same gates.
        durable = {
            "experiment_id": experiment_id,
            "status": "ACCEPTED",
            "acceptance_recommendation": "PROMOTE",
            "checks": accepted["checks"],
            "metrics": accepted["results"],
            "artifacts": {"tree_sha256": accepted["artifact_sha256"]},
            "release_metadata": accepted["release_metadata"],
            "reproduction_command": accepted["reproduction_command"],
            "candidate_path": accepted["candidate_path"],
            "error": accepted.get("error") or {},
            "blockers": accepted["blockers"],
        }
        result_dir = (self.root / "autonomous_agent/candidates" / experiment_id)
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / "result.json").write_text(
            json.dumps(durable), encoding="utf-8")
        return pid

    def test_accepted_diagnostic_is_retained_and_never_promoted(self):
        executor = MockExecutor(self.root)
        loop = self.make_loop(max_cycles=1, executor=executor)
        policy = loop._policy()
        from autonomous_agent.proposal_layer import (compiler, generator as gen_mod,
                                                     evidence_view)
        ledger_obj = loop._ledger()
        view = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=ledger_obj.read_rows())
        base_payload = gen_mod.generate_proposals(
            view, policy, seed=11, limit=1)[0]
        payload = _make_diagnostic_payload(base_payload)
        champion_before = json.loads(
            (self.root / "CHAMPION.json").read_text("utf-8"))
        preexisting_versions = sorted((self.root / "versions").iterdir())
        pid = self._stage_executed_diagnostic(ledger_obj, payload)
        summary = loop.run()
        # Adjudicated from the durable result: never re-executed.
        self.assertNotIn("exp-proposal-diag01", executor.calls)
        rows = [json.loads(line) for line in
                self.ledger_path.read_text("utf-8").splitlines() if line.strip()]
        promoted = [r for r in rows if r.get("to") == schema.STATUS_PROMOTED]
        self.assertEqual(promoted, [])
        retained = [r for r in rows
                    if r.get("reason_code") == "DIAGNOSTIC_RETAINED"
                    and r.get("row_type") == "transition"]
        self.assertEqual(len(retained), 1)
        detail = retained[0]["detail"]
        self.assertEqual(detail["result"], "ACCEPTED")
        self.assertEqual(detail["promotion_outcome"], "DIAGNOSTIC_RETAINED")
        self.assertEqual(detail["rule_record_status"], "frozen")
        self.assertIn("diagnostics, not promotions", detail["diagnostic_rule"])
        self.assertTrue(detail["champion_unchanged"])
        # No version directory was created and the champion is untouched.
        versions_after = (self.root / "versions")
        self.assertEqual(sorted(versions_after.iterdir()),
                         preexisting_versions,
                         "a diagnostic run must not create any version")
        champion_after = json.loads(
            (self.root / "CHAMPION.json").read_text("utf-8"))
        self.assertEqual(champion_after["version"], champion_before["version"])
        # The proposal ends at ADJUDICATED; and the ledger now refuses any
        # later PROMOTED repair-of-state attempt (fail-closed).
        with self.assertRaises(Exception) as ctx:
            ledger_obj.transition(pid, schema.STATUS_PROMOTED,
                                  reason_code="PROMOTED",
                                  detail={"version": "fixture-attempt"})
        self.assertIn("DIAGNOSTIC_RETAINED", str(ctx.exception))

    def test_ledger_refuses_promotion_after_diagnostic_adjudication(self):
        executor = MockExecutor(self.root)
        loop = self.make_loop(max_cycles=1, executor=executor)
        from autonomous_agent.proposal_layer import (compiler, generator as gen_mod,
                                                     evidence_view)
        from autonomous_agent.proposal_layer.ledger import LedgerError
        ledger_obj = loop._ledger()
        view = evidence_view.build(self.root, clock=FIXED_CLOCK,
                                   ledger_rows=ledger_obj.read_rows())
        base_payload = gen_mod.generate_proposals(
            view, loop._policy(), seed=13, limit=1)[0]
        payload = _make_diagnostic_payload(base_payload)
        pid = self._stage_executed_diagnostic(
            ledger_obj, payload, experiment_id="exp-proposal-diag02")
        loop.run()
        # Direct fail-closed check at the ledger layer (mirrors the loop
        # guard: no manual status surgery can promote a diagnostic
        # adjudication).
        merged = ledger_obj.get(pid)
        adjudications = [t for t in (merged.get("transitions") or [])
                         if t.get("to") == schema.STATUS_ADJUDICATED
                         and (t.get("detail") or {}).get("result") == "ACCEPTED"
                         and (t.get("detail") or {}).get("promotion_outcome")
                         == "DIAGNOSTIC_RETAINED"]
        self.assertEqual(len(adjudications), 1)
        with self.assertRaises(LedgerError) as ctx:
            ledger_obj.transition(pid, schema.STATUS_PROMOTED)
        self.assertIn("diagnostic", str(ctx.exception))



if __name__ == "__main__":
    unittest.main()
