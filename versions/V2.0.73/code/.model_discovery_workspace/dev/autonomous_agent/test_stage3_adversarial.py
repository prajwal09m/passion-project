"""Campaign 2 Stage 3 — 26 adversarial attacks on the proposal/loop boundary.

Every test runs on a disposable fixture with an injected mock executor:
NO real experiment execution, NO real production state, NO supervisor,
NO LLM. The real repository and the frozen campaign config are never touched.

Attack categories (26 total, numbered to match the Stage 3 audit):

  Outcome blindness  (3)  A1-A3
  Quota/budget/duplicate bypasses (6)  B4-B9
  Lifecycle / config integrity (3)  C10-C12
  Holdout / prospective injection (3)  D13-D15
  Code / eval / exec injection (3)  E16-E18
  Path access (2)  F19-F20
  Executor / compiler bypass (3)  G21-G23
  Crash recovery / streaks (3)  H24-H26

Findings (Stage 3): C12 and D15 are written against the REMEDIATED behavior;
they fail against the pre-fix loop and document the two Stage 3 findings
(see CAMPAIGN_2_STAGE_3_ADVERSARIAL_AUDIT_2026_10_04.md).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from autonomous_agent.continuous_loop import LoopStop, ResearchLoop
from autonomous_agent.proposal_layer import (
    bias_governor, compiler, cycle, evidence_view, generator, ledger, schema,
    validator,
)
from autonomous_agent.test_continuous_loop import (
    MockExecutor, _accepted_outcome,
)
from autonomous_agent.test_proposal_layer import (
    FIXED_CLOCK, base_policy, build_fixture,
)
from autonomous_agent.test_stage2_campaign import CAMPAIGN, write_campaign

# Four param sets for feature_arm_comparison that were NEVER part of a
# Campaign 1 recipe replay (C1 only ran arm_pair A->B for this family), so
# the recipe-replay duplicate layer can never mask the gate under test.
P1 = {"arm_pair": "C->D", "estimator": "LogisticRegression", "n_boot": 1500}
P2 = {"arm_pair": "C->D", "estimator": "LightGBM", "n_boot": 500}
P3 = {"arm_pair": "B->C", "estimator": "LightGBM", "n_boot": 1200}
P4 = {"arm_pair": "B->C", "estimator": "LogisticRegression", "n_boot": 700}

H1 = ("First framing: does the C to D arm comparison hold when the estimator "
      "is frozen under purged folds.")
H2 = ("Second framing: resampling stability probe for the C versus D nesting "
      "under a moving block bootstrap.")
H3 = ("Third framing: subgroup drift across calendar years for the nested "
      "C to D arm hierarchy under identical seeds.")


def _refingerprint(payload: dict) -> dict:
    payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AlwaysAcceptExecutor:
    """Mock: every execution returns full acceptance evidence.

    The release metadata carries the TRUE dataset hash of the fixture
    (the shared mock's placeholder would make the promoted champion declare
    a wrong dataset_sha256, and the fail-closed EVIDENCE gate would then
    refuse every later proposal citing the dataset — which is exactly the
    correct behavior, so the mock must stay evidence-consistent).
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[str] = []

    def __call__(self, spec) -> dict:
        self.calls.append(spec.experiment_id)
        outcome = _accepted_outcome(self.root, spec.experiment_id)
        outcome["release_metadata"]["dataset_sha256"] = _sha256(
            self.root / "study_files/outputs/study_v1/development/event_table.csv")
        return outcome


class HoldoutTouchExecutor:
    """Mock: claims full acceptance BUT reports the sealed holdout touched."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[str] = []

    def __call__(self, spec) -> dict:
        self.calls.append(spec.experiment_id)
        outcome = _accepted_outcome(self.root, spec.experiment_id)
        outcome["holdout_touched"] = True
        return outcome


class TamperedArtifactExecutor:
    """Mock: acceptance evidence whose artifact hash does not match the tree."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[str] = []

    def __call__(self, spec) -> dict:
        self.calls.append(spec.experiment_id)
        outcome = _accepted_outcome(self.root, spec.experiment_id)
        outcome["artifact_sha256"] = "0" * 64
        return outcome


class ExplodingExecutor:
    """Mock: raises mid-execution (failure is evidence, never a crash)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, spec) -> dict:
        self.calls.append(spec.experiment_id)
        raise RuntimeError("synthetic executor explosion")


class Stage3Case(unittest.TestCase):
    """Disposable fixture, campaign config, completed champion, mock executors.

    Same fixture completion as test_continuous_loop.LoopTestCase (copied so
    this module's inherited test list stays exactly the 26 attacks below).
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="stage3_adv_"))
        self.root = self.tmp / "ws"
        self.root.mkdir(parents=True)
        build_fixture(self.root)
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
        champion.setdefault("historical_v1_0_1_sha256",
                            "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b")
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
        write_campaign(self.root)
        self.campaign = CAMPAIGN
        self.ledger_path = (self.root /
                            "autonomous_agent/state/proposal_ledger.jsonl")
        self.ledger = ledger.ProposalLedger(self.ledger_path, clock=FIXED_CLOCK)
        self.view = evidence_view.build(
            self.root, clock=FIXED_CLOCK,
            ledger_rows=self.ledger.read_rows())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers -------------------------------------------------------------
    def make_loop(self, max_cycles=1, executor=None, **kwargs) -> ResearchLoop:
        return ResearchLoop(self.root, max_cycles=max_cycles,
                            executor=executor or MockExecutor(self.root),
                            clock=FIXED_CLOCK, **kwargs)

    def policy(self, **overrides) -> dict:
        policy = cycle._load_policy(self.root)
        policy.update(overrides)
        return policy

    def make_payload(self, params=None, proposal_class="falsification",
                     hypothesis=None) -> dict:
        payload = generator.payload_for(
            self.view, "feature_arm_comparison", params or P1,
            proposal_class)
        payload["campaign_id"] = self.campaign
        if hypothesis is not None:
            payload["hypothesis"] = hypothesis
        return _refingerprint(payload)

    def record(self, payload: dict) -> str:
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        return pid

    def check(self, payload: dict, *, policy=None) -> tuple[str, validator.ValidationReport]:
        pid = self.record(payload)
        report = validator.validate_proposal(
            payload, root=self.root, view=self.view,
            merged_history=self.ledger.all_proposals(),
            policy=policy if policy is not None else self.policy(),
            proposal_id=pid)
        return pid, report

    def apply(self, pid: str, report) -> None:
        """Record the gate outcome exactly as phase_generate_and_approve does."""
        self.ledger.transition(pid, report.status_target,
                               reason_code=report.reason_code,
                               detail=report.to_dict())

    def approve(self, pid: str) -> None:
        self.ledger.transition(
            pid, schema.STATUS_ACCEPTED_FOR_EXECUTION,
            reason_code="HUMAN_APPROVAL",
            detail={"approval_policy": "revalidate_at_approval@1.0.0",
                    "approved_by": "policy:stage3",
                    "quota_state": {"total": 1}})

    def quota(self, policy=None) -> dict:
        governor = bias_governor.BiasGovernor(policy or self.policy())
        return governor.quota_state(
            self.ledger.all_proposals(),
            campaign_id=(policy or self.policy()).get("campaign_id"))

    def loop_state(self) -> dict:
        return json.loads((self.root / "autonomous_agent/state"
                           / "loop_state.json").read_text("utf-8"))

    def ledger_rows(self) -> list[dict]:
        return [json.loads(line) for line in
                self.ledger_path.read_text("utf-8").splitlines() if line.strip()]

    def assert_lifecycle_legal(self) -> None:
        """Fold every transition against the authoritative LEGAL_TRANSITIONS."""
        adjudication: dict[str, object] = {}
        for row in self.ledger_rows():
            if row.get("row_type") != "transition":
                continue
            pid = row.get("proposal_id")
            frm, to = row.get("from"), row.get("to")
            self.assertIn(to, schema.LEGAL_TRANSITIONS.get(frm, frozenset()),
                          msg=f"illegal transition {frm} -> {to} for {pid}")
            if to == schema.STATUS_ADJUDICATED:
                adjudication[pid] = (row.get("detail") or {}).get("result")
            if to == schema.STATUS_PROMOTED:
                self.assertEqual(
                    adjudication.get(pid), "ACCEPTED",
                    msg=f"PROMOTED without a latest ACCEPTED adjudication "
                        f"for {pid}")

    # A1 ---------------------------------------------------------------------
    def test_a1_loop_selection_blinds_to_preregistered_expectations(self):
        """Selection uses portfolio minimums + approval order — never the
        predicted outcome embedded in a payload (A1)."""
        loop = self.make_loop(max_cycles=1)
        fals = {"proposal_id": "p-fals", "proposal": {
            "proposal_class": "falsification", "direction": "calibration",
            "preregistered_expectation":
                "Pessimistic: I expect this to FAIL (predicted_delta -0.5).",
            "predicted_outcome": -0.5, "expected_result": "rejection"}}
        conf = {"proposal_id": "p-conf", "proposal": {
            "proposal_class": "confirmatory", "direction": "calibration",
            "preregistered_expectation":
                "Optimistic: predicted_delta +0.4, guaranteed win.",
            "predicted_outcome": 0.4, "expected_result": "acceptance"}}
        maximums = {"falsification": 1, "confirmatory": 1}
        # Unmet portfolio minimum: the falsification slot wins whatever the
        # expectation texts say.
        self.assertIs(loop._select_next([conf, fals], {}, maximums), fals)
        conf["proposal"]["preregistered_expectation"], \
            fals["proposal"]["preregistered_expectation"] = (
                fals["proposal"]["preregistered_expectation"],
                conf["proposal"]["preregistered_expectation"])
        self.assertIs(loop._select_next([conf, fals], {}, maximums), fals)
        # Minimums met: approval order decides; content is irrelevant.
        met = {"falsification": 1, "confirmatory": 1}
        self.assertIs(loop._select_next([conf, fals], met, maximums), conf)
        self.assertIs(loop._select_next([fals, conf], met, maximums), fals)

    # A2 ---------------------------------------------------------------------
    def test_a2_injected_outcome_weight_cannot_steer_score(self):
        """A hidden outcome weight smuggled into score_weights has no effect:
        score() only reads the reviewed weight keys (A2)."""
        candidate = {"direction": "validation", "proposal_class": "falsification",
                     "novelty_score": 0.7, "evidence_gap_score": 0.5,
                     "quota_pressure": 1.0, "priority": 0.9,
                     "attempts_in_direction": 2}
        baseline = bias_governor.BiasGovernor(base_policy())
        weights = dict(base_policy()["score_weights"])
        weights.update({"outcome": 1.0, "predicted_delta": 0.99,
                        "expected_delta": -1.0})
        injected = bias_governor.BiasGovernor(base_policy(score_weights=weights))
        self.assertEqual(baseline.score(candidate), injected.score(candidate))

    # A3 ---------------------------------------------------------------------
    def test_a3_missing_selection_input_fails_closed(self):
        """No silent fallback: a missing allowed input raises instead of
        defaulting — and outcome-like fields are not substitutes (A3)."""
        governor = bias_governor.BiasGovernor(base_policy())
        candidate = {"direction": "validation", "proposal_class": "falsification",
                     "novelty_score": 0.7, "evidence_gap_score": 0.5,
                     "quota_pressure": 1.0, "priority": 0.9,
                     "attempts_in_direction": 2}
        del candidate["novelty_score"]
        with self.assertRaises(KeyError) as ctx:
            governor.selection_inputs(candidate)
        self.assertIn("Selection input(s) missing", str(ctx.exception))
        with self.assertRaises(KeyError):
            governor.score(candidate)
        candidate["predicted_delta"] = 0.99   # outcome field is no substitute
        with self.assertRaises(KeyError):
            governor.score(candidate)

    # B4 ---------------------------------------------------------------------
    def test_b4_direction_cap_bypass_refused_and_recorded(self):
        """A manually injected third proposal in a direction at its cap is
        refused at BUDGET and permanently recorded (B4)."""
        policy = self.policy(max_per_direction=1, min_falsification_share=0.0)
        pid1, report1 = self.check(self.make_payload(P1, "confirmatory"),
                                   policy=policy)
        self.assertTrue(report1.passed, report1.to_dict())
        pid2, report2 = self.check(self.make_payload(P2, "confirmatory"),
                                   policy=policy)
        self.assertFalse(report2.passed)
        self.assertEqual(report2.failed_gate, schema.GATE_BUDGET)
        self.assertEqual(report2.reason_code, schema.RC_BUDGET_EXHAUSTED)
        self.assertEqual(report2.status_target, "REFUSED")
        self.apply(pid2, report2)
        self.assertEqual(self.ledger.status(pid2), schema.STATUS_REFUSED)

    # B5 ---------------------------------------------------------------------
    def test_b5_total_proposal_budget_bypass_refused(self):
        """Bypassing the generator (direct ledger injection) still cannot
        exceed the campaign's total proposal budget (B5)."""
        policy = self.policy(max_total_proposals=1, min_falsification_share=0.0)
        pid1, report1 = self.check(self.make_payload(P1, "falsification"),
                                   policy=policy)
        self.assertTrue(report1.passed, report1.to_dict())
        pid2, report2 = self.check(self.make_payload(P2, "falsification"),
                                   policy=policy)
        self.assertFalse(report2.passed)
        self.assertEqual(report2.failed_gate, schema.GATE_BUDGET)
        self.assertEqual(report2.reason_code, schema.RC_BUDGET_EXHAUSTED)
        self.assertIn("total", report2.gates[-1].detail)
        self.apply(pid2, report2)
        self.assertEqual(self.ledger.status(pid2), schema.STATUS_REFUSED)

    # B6 ---------------------------------------------------------------------
    def test_b6_class_budget_bypass_refused_at_bias_gate(self):
        """Second confirmatory record against a class budget of 1 is refused
        by the portfolio governor (B6)."""
        policy = self.policy(
            min_falsification_share=0.0,
            class_budgets={"confirmatory": 1, "falsification": 4,
                           "replication": 1, "exploration": 1})
        pid1, report1 = self.check(self.make_payload(P1, "confirmatory"),
                                   policy=policy)
        self.assertTrue(report1.passed, report1.to_dict())
        pid2, report2 = self.check(self.make_payload(P2, "confirmatory"),
                                   policy=policy)
        self.assertFalse(report2.passed)
        self.assertEqual(report2.failed_gate, schema.GATE_BIAS)
        self.assertEqual(report2.reason_code, schema.RC_BUDGET_EXHAUSTED)
        self.assertIn("class confirmatory", report2.gates[-1].detail)
        self.apply(pid2, report2)
        self.assertEqual(self.ledger.status(pid2), schema.STATUS_REFUSED)

    # B7 ---------------------------------------------------------------------
    def test_b7_replication_share_cap_holds_under_all_orderings(self):
        """The replication-share cap refuses regardless of insertion order;
        refused records are permanent and keep counting (B7)."""
        policy = self.policy(
            min_falsification_share=0.0, max_replication_share=0.4,
            max_per_direction=4,
            class_budgets={"confirmatory": 4, "falsification": 4,
                           "replication": 4, "exploration": 1})
        pid1, report1 = self.check(self.make_payload(P1, "confirmatory"),
                                   policy=policy)
        self.assertTrue(report1.passed, report1.to_dict())
        # Two replication records exist because refusals are permanent
        # records; each refusal reason must be the share cap.
        for params in (P2, P3):
            pid, report = self.check(self.make_payload(params, "replication"),
                                     policy=policy)
            self.assertFalse(report.passed)
            self.assertEqual(report.failed_gate, schema.GATE_BIAS)
            self.assertEqual(report.reason_code, schema.RC_BIAS_QUOTA)
            self.assertIn("replication share", report.gates[-1].detail)
            self.apply(pid, report)
        # Post-creation accounting: the two permanent refusals keep counting
        # (forgetting refusals would be the bias risk).
        state = self.quota(policy)
        self.assertAlmostEqual(state["replication_share"], 2 / 3)
        # A third replication attempt: post-creation share 3/4 = 0.75 > 0.4.
        pid4, report4 = self.check(self.make_payload(P4, "replication"),
                                   policy=policy)
        self.assertFalse(report4.passed)
        self.assertEqual(report4.reason_code, schema.RC_BIAS_QUOTA)
        self.assertIn("replication share 0.75", report4.gates[-1].detail)
        self.apply(pid4, report4)
        self.assertEqual(self.ledger.status(pid4), schema.STATUS_REFUSED)
        self.assertAlmostEqual(self.quota(policy)["replication_share"], 0.75)

    # B8 ---------------------------------------------------------------------
    def test_b8_identical_fingerprint_flood_neither_inflates_budget_nor_bypasses_duplicate(self):
        """Flooding identical re-asks: every copy is refused AND the copies
        collapse into one record — budget is not consumed by the flood (B8)."""
        policy = self.policy(min_falsification_share=0.0)
        original = self.make_payload(P1, "falsification")
        pid1, report1 = self.check(original, policy=policy)
        self.assertTrue(report1.passed, report1.to_dict())
        for _ in range(3):
            pid, report = self.check(dict(original), policy=policy)
            self.assertFalse(report.passed)
            self.assertEqual(report.failed_gate, schema.GATE_DUPLICATE)
            self.assertEqual(report.reason_code, schema.RC_DUPLICATE)
            self.apply(pid, report)
        # Quota counts DISTINCT designs: the 3 copies add nothing.
        state = self.quota(policy)
        self.assertEqual(state["total"], 1, state)
        self.assertEqual(
            state["by_signature"][original["design_signature"]], 1, state)
        # So a fresh distinct design still fits a cap of 2 — the flood
        # consumed zero budget.
        tight = self.policy(min_falsification_share=0.0,
                            max_total_proposals=2)
        pid2, report2 = self.check(self.make_payload(P2, "falsification"),
                                   policy=tight)
        self.assertTrue(report2.passed, report2.to_dict())

    # B9 ---------------------------------------------------------------------
    def test_b9_signature_budget_not_inflated_by_copies_and_cap_holds(self):
        """Identical copies do not consume signature budget; a genuine third
        same-signature design (with delta declared) hits the cap (B9)."""
        policy = self.policy(min_falsification_share=0.0,
                             max_per_direction=4, max_signature_count=2)
        sig = self.make_payload(P1, "falsification", hypothesis=H1)
        pid1, report1 = self.check(sig, policy=policy)
        self.assertTrue(report1.passed, report1.to_dict())
        # A byte-identical copy: refused as duplicate, counts nothing.
        pidc, reportc = self.check(dict(sig), policy=policy)
        self.assertFalse(reportc.passed)
        self.assertEqual(reportc.reason_code, schema.RC_DUPLICATE)
        self.apply(pidc, reportc)
        self.assertEqual(self.quota(policy)["by_signature"][sig["design_signature"]], 1)
        # Second justified same-signature design: at the cap, passes.
        second = self.make_payload(P1, "falsification", hypothesis=H2)
        second["delta_from_prior"] = "estimator grid fixed; framing differs"
        pid2, report2 = self.check(second, policy=policy)
        self.assertTrue(report2.passed, report2.to_dict())
        self.assertEqual(self.quota(policy)["by_signature"][sig["design_signature"]], 2)
        # Third: over the cap -> RC_SIGNATURE_CAP even with a declared delta.
        third = self.make_payload(P1, "falsification", hypothesis=H3)
        third["delta_from_prior"] = "third declared framing of the same design"
        pid3, report3 = self.check(third, policy=policy)
        self.assertFalse(report3.passed)
        self.assertEqual(report3.failed_gate, schema.GATE_BIAS)
        self.assertEqual(report3.reason_code, schema.RC_SIGNATURE_CAP)
        self.assertEqual(report3.status_target, "REFUSED")
        self.apply(pid3, report3)
        self.assertEqual(self.ledger.status(pid3), schema.STATUS_REFUSED)

    # C10 ----------------------------------------------------------------------
    def test_c10_exhaustive_illegal_transition_matrix_refused(self):
        """Every (from -> to) pair absent from LEGAL_TRANSITIONS raises —
        all 11 states swept, not just the ones an attacker would pick (C10)."""
        payload = {"proposal_fingerprint": "stage3sweep" * 6,
                   "design_signature": "stage3-sweep-signature"}
        pids = [self.ledger.create_proposal(dict(payload)) for _ in range(11)]
        (p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10) = pids
        approval = {"approval_policy": "revalidate_at_approval@1.0.0",
                    "approved_by": "policy:stage3",
                    "quota_state": {"total": 1}}
        states: dict[str, str] = {}
        # PROPOSED (p0 untouched)
        states[schema.STATUS_PROPOSED] = p0
        # VALIDATING
        self.ledger.transition(p1, schema.STATUS_VALIDATING)
        states[schema.STATUS_VALIDATING] = p1
        # ACCEPTED_FOR_EXECUTION
        self.ledger.transition(p2, schema.STATUS_VALIDATING)
        self.ledger.transition(p2, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        states[schema.STATUS_ACCEPTED_FOR_EXECUTION] = p2
        # COMPILED
        self.ledger.transition(p3, schema.STATUS_VALIDATING)
        self.ledger.transition(p3, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        self.ledger.transition(p3, schema.STATUS_COMPILED,
                               reason_code="COMPILED",
                               detail={"spec_sha256": "s" * 64})
        states[schema.STATUS_COMPILED] = p3
        # EXECUTED
        self.ledger.transition(p4, schema.STATUS_VALIDATING)
        self.ledger.transition(p4, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        self.ledger.transition(p4, schema.STATUS_COMPILED,
                               reason_code="COMPILED",
                               detail={"spec_sha256": "s" * 64})
        self.ledger.transition(p4, schema.STATUS_EXECUTED,
                               reason_code="EXECUTION_STARTED",
                               detail={"phase": "started"})
        states[schema.STATUS_EXECUTED] = p4
        # ADJUDICATED (accepted adjudication, so PROMOTED is legal here)
        self.ledger.transition(p5, schema.STATUS_VALIDATING)
        self.ledger.transition(p5, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        self.ledger.transition(p5, schema.STATUS_COMPILED,
                               reason_code="COMPILED",
                               detail={"spec_sha256": "s" * 64})
        self.ledger.transition(p5, schema.STATUS_EXECUTED,
                               reason_code="EXECUTION_STARTED",
                               detail={"phase": "started"})
        self.ledger.transition(p5, schema.STATUS_ADJUDICATED,
                               reason_code="GATES_PASSED",
                               detail={"result": "ACCEPTED"})
        states[schema.STATUS_ADJUDICATED] = p5
        # PROMOTED
        self.ledger.transition(p6, schema.STATUS_VALIDATING)
        self.ledger.transition(p6, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        self.ledger.transition(p6, schema.STATUS_COMPILED,
                               reason_code="COMPILED",
                               detail={"spec_sha256": "s" * 64})
        self.ledger.transition(p6, schema.STATUS_EXECUTED,
                               reason_code="EXECUTION_STARTED",
                               detail={"phase": "started"})
        self.ledger.transition(p6, schema.STATUS_ADJUDICATED,
                               reason_code="GATES_PASSED",
                               detail={"result": "ACCEPTED"})
        self.ledger.transition(p6, schema.STATUS_PROMOTED,
                               reason_code="PROMOTED",
                               detail={"version": "V2.0.9"})
        states[schema.STATUS_PROMOTED] = p6
        # REFUSED
        self.ledger.transition(p7, schema.STATUS_VALIDATING)
        self.ledger.transition(p7, schema.STATUS_REFUSED,
                               reason_code=schema.RC_DUPLICATE)
        states[schema.STATUS_REFUSED] = p7
        # FAILED_VALIDATION
        self.ledger.transition(p8, schema.STATUS_VALIDATING)
        self.ledger.transition(p8, schema.STATUS_FAILED_VALIDATION,
                               reason_code=schema.RC_NOT_FALSIFIABLE)
        states[schema.STATUS_FAILED_VALIDATION] = p8
        # FAILED_COMPILATION
        self.ledger.transition(p9, schema.STATUS_VALIDATING)
        self.ledger.transition(p9, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        self.ledger.transition(p9, schema.STATUS_FAILED_COMPILATION,
                               reason_code=schema.RC_SPEC_CONTRACT)
        states[schema.STATUS_FAILED_COMPILATION] = p9
        # FAILED_EXECUTION
        self.ledger.transition(p10, schema.STATUS_VALIDATING)
        self.ledger.transition(p10, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        self.ledger.transition(p10, schema.STATUS_COMPILED,
                               reason_code="COMPILED",
                               detail={"spec_sha256": "s" * 64})
        self.ledger.transition(p10, schema.STATUS_EXECUTED,
                               reason_code="EXECUTION_STARTED",
                               detail={"phase": "started"})
        self.ledger.transition(p10, schema.STATUS_FAILED_EXECUTION,
                               reason_code="EXECUTION_FAILED")
        states[schema.STATUS_FAILED_EXECUTION] = p10

        self.assertEqual(set(states), set(schema.ALL_STATUSES))
        checked = 0
        for state, pid in sorted(states.items()):
            for target in sorted(schema.ALL_STATUSES):
                if target in schema.LEGAL_TRANSITIONS[state]:
                    continue          # legal pairs are exercised elsewhere
                with self.assertRaises(
                        ledger.LedgerError,
                        msg=f"{state} -> {target} was NOT refused"):
                    self.ledger.transition(pid, target)
                checked += 1
        # 11 states x 11 targets - 10 legal pairs = 111 illegal pairs.
        self.assertEqual(checked, 111)
        for terminal in (schema.STATUS_REFUSED, schema.STATUS_FAILED_VALIDATION,
                         schema.STATUS_FAILED_COMPILATION,
                         schema.STATUS_FAILED_EXECUTION,
                         schema.STATUS_PROMOTED):
            self.assertEqual(schema.LEGAL_TRANSITIONS[terminal], frozenset())
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition(p0, "NOT_A_STATUS")
        with self.assertRaises(ledger.LedgerError):
            self.ledger.transition("prop-doesnotexist-1",
                                   schema.STATUS_VALIDATING)

    # C11 ----------------------------------------------------------------------
    def test_c11_promotion_refused_after_explicit_rejected_adjudication(self):
        """A recorded rejection is permanent: PROMOTED requires the LATEST
        adjudication to record result == ACCEPTED (C11)."""
        payload = {"proposal_fingerprint": "stage3rej" * 6,
                   "design_signature": "stage3-rejected-signature"}
        pid = self.ledger.create_proposal(payload)
        approval = {"approval_policy": "revalidate_at_approval@1.0.0",
                    "approved_by": "policy:stage3",
                    "quota_state": {"total": 1}}
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        self.ledger.transition(pid, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        self.ledger.transition(pid, schema.STATUS_COMPILED,
                               reason_code="COMPILED",
                               detail={"spec_sha256": "s" * 64})
        self.ledger.transition(pid, schema.STATUS_EXECUTED,
                               reason_code="EXECUTION_STARTED",
                               detail={"phase": "started"})
        self.ledger.transition(pid, schema.STATUS_ADJUDICATED,
                               reason_code="GATES_FAILED",
                               detail={"result": "REJECTED",
                                       "primary_delta": -0.02})
        with self.assertRaises(ledger.LedgerError) as ctx:
            self.ledger.transition(pid, schema.STATUS_PROMOTED)
        self.assertIn("requires the latest ADJUDICATED row",
                      str(ctx.exception))
        # Positive control: an ACCEPTED adjudication may promote (ledger-level).
        ok = self.ledger.create_proposal(
            {**payload, "design_signature": "stage3-accepted-signature"})
        self.ledger.transition(ok, schema.STATUS_VALIDATING)
        self.ledger.transition(ok, schema.STATUS_ACCEPTED_FOR_EXECUTION,
                               reason_code="HUMAN_APPROVAL", detail=approval)
        self.ledger.transition(ok, schema.STATUS_COMPILED,
                               reason_code="COMPILED",
                               detail={"spec_sha256": "s" * 64})
        self.ledger.transition(ok, schema.STATUS_EXECUTED,
                               reason_code="EXECUTION_STARTED",
                               detail={"phase": "started"})
        self.ledger.transition(ok, schema.STATUS_ADJUDICATED,
                               reason_code="GATES_PASSED",
                               detail={"result": "ACCEPTED"})
        self.ledger.transition(ok, schema.STATUS_PROMOTED,
                               reason_code="PROMOTED",
                               detail={"version": "V2.0.9"})
        self.assertEqual(self.ledger.status(ok), schema.STATUS_PROMOTED)

    # C12 ----------------------------------------------------------------------
    def test_c12_self_consistent_campaign_config_swap_is_pinned(self):
        """Attacker rewrites config AND its sidecar together (self-consistent,
        so the file-vs-sidecar check passes). The digest pinned in loop state
        at first start must still refuse the change (C12, Stage 3 finding)."""
        executor = MockExecutor(self.root)
        first = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(first["stop_reason"], "MAX_CYCLES")
        self.assertEqual(len(executor.calls), 1)
        pinned = self.loop_state()["campaign_config_sha256"]
        # Self-consistent swap: budget 999 + matching sidecar.
        path = self.root / "autonomous_agent/state/campaign_config.json"
        config = json.loads(path.read_text("utf-8"))
        config["execution"]["max_total_executions"] = 999
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
        (self.root / "autonomous_agent/state/campaign_config.sha256").write_text(
            _sha256(path) + "\n", encoding="utf-8")
        # The file-vs-sidecar comparison now passes — only the pin can stop it.
        executor2 = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=3, executor=executor2).run()
        self.assertEqual(summary["stop_reason"], "CAMPAIGN_CONFIG_CHANGED")
        self.assertEqual(executor2.calls, [])
        self.assertEqual(self.loop_state()["campaign_config_sha256"], pinned)

    # D13 ----------------------------------------------------------------------
    def test_d13_holdout_path_in_non_surface_fields_refused(self):
        """The HOLDOUT gate walks the WHOLE payload, not just the SURFACE
        gate's design/parameters: holdout paths hidden in rationale or in the
        falsification rule are refused (D13)."""
        payload = self.make_payload(P1, "falsification")
        payload["rationale"]["evidence_gap"] = (
            "feature_engineering: 0 accepted / 0 rejected; leak attempt via "
            "rationale at study_files/outputs/study_v1/prospective/secret.csv")
        _refingerprint(payload)
        pid, report = self.check(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_HOLDOUT)
        self.assertEqual(report.reason_code, schema.RC_HOLDOUT_REFERENCE)
        self.assertEqual(report.status_target, "FAILED_VALIDATION")

        payload2 = self.make_payload(P2, "falsification")
        payload2["falsification_rule"]["scope"] = (
            "study_files/outputs/study_v1/prospective/secret.csv")
        _refingerprint(payload2)
        pid2, report2 = self.check(payload2)
        self.assertFalse(report2.passed)
        self.assertEqual(report2.failed_gate, schema.GATE_HOLDOUT)
        self.assertEqual(report2.reason_code, schema.RC_HOLDOUT_REFERENCE)

    def test_d13b_holdout_alias_path_component_refused(self):
        """is_denied refuses any '/holdout/' path component; the payload-walking
        HOLDOUT gate must use the same marker set as the denylist, not
        'prospective' alone, so an alias spelling cannot survive in a
        proposal field that is never opened as a citation path."""
        # Policy/provenance text stays legitimate, exactly as before.
        self.assertFalse(schema.contains_holdout_path("holdout sealed, uses=0"))
        # The prospective spelling already refused. The aliased spelling of
        # the SAME sealed directory must refuse too. (Fails pre-fix.)
        self.assertTrue(schema.contains_holdout_path(
            "study_files/outputs/holdout/x.csv"))
        payload = self.make_payload(P1, "falsification")
        payload["hypothesis"] = ("[validation] probe study_files/outputs/"
                                 "holdout/x.csv")
        _refingerprint(payload)
        _, report = self.check(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_HOLDOUT)
        self.assertEqual(report.reason_code, schema.RC_HOLDOUT_REFERENCE)
        self.assertEqual(report.status_target, "FAILED_VALIDATION")

    # D14 ----------------------------------------------------------------------
    def test_d14_holdout_citation_denied_before_any_open(self):
        """A citation aimed at the sealed holdout is refused by the denylist
        BEFORE any read: the refusal message is the deny branch itself (D14)."""
        payload = self.make_payload(P1, "falsification")
        payload["evidence_citations"][0] = {
            "artifact_path": "study_files/outputs/study_v1/prospective/secret.csv",
            "sha256": "0" * 64,
            "what_it_shows": "try to read the sealed holdout"}
        _refingerprint(payload)
        pid, report = self.check(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_EVIDENCE)
        self.assertEqual(report.reason_code, schema.RC_UNRECALLED_EVIDENCE)
        failed = next(g for g in report.gates if not g.passed)
        self.assertIn("sealed-holdout", failed.detail)

    # D15 ----------------------------------------------------------------------
    def test_d15_holdout_touch_acceptance_cannot_promote(self):
        """Executor claims full acceptance but reports the holdout touched:
        no promotion, champion untouched, and the ledger records the outcome
        TRUTHFULLY as REJECTED (D15, Stage 3 finding)."""
        executor = HoldoutTouchExecutor(self.root)
        summary = self.make_loop(max_cycles=2, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "HOLDOUT_TOUCHED")
        self.assertEqual(len(executor.calls), 1)
        champion = json.loads((self.root / "CHAMPION.json").read_text("utf-8"))
        self.assertEqual(champion["version"], "V2.0.8")
        self.assertFalse((self.root / "versions/V2.0.9").exists())
        adjudicated = [r for r in self.ledger_rows()
                       if r.get("to") == schema.STATUS_ADJUDICATED]
        self.assertEqual(len(adjudicated), 1)
        detail = adjudicated[0]["detail"]
        self.assertEqual(detail["result"], "REJECTED")
        self.assertTrue(detail["holdout_touched"])
        self.assertTrue(detail.get("rejection_reason"))
        promoted = [r for r in self.ledger_rows()
                    if r.get("to") == schema.STATUS_PROMOTED]
        self.assertEqual(promoted, [])

    # E16 ----------------------------------------------------------------------
    def test_e16_code_injection_vectors_in_parameters_refused(self):
        """eval/exec/import/backtick/semicolon vectors anywhere in design or
        parameters die at SURFACE (E16)."""
        vectors = ["os.system('id')", "__import__('subprocess')",
                   "eval(1+1)", "`id`", "x; import os",
                   "open('/etc/passwd')"]
        for vector in vectors:
            payload = self.make_payload(P1, "falsification")
            payload["parameters"]["estimator"] = vector
            _refingerprint(payload)
            pid, report = self.check(payload)
            self.assertFalse(report.passed, vector)
            self.assertEqual(report.failed_gate, schema.GATE_SURFACE, vector)
            self.assertEqual(report.reason_code, schema.RC_SURFACE_ESCAPE,
                             vector)
            self.assertEqual(report.status_target, "FAILED_VALIDATION", vector)
        # Code smuggled into a design param escalates the same way.
        payload = self.make_payload(P1, "falsification")
        payload["design"]["primitives"][0]["params"]["arm_pair"] = \
            "__import__('os')"
        _refingerprint(payload)
        pid, report = self.check(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_SURFACE)
        self.assertEqual(report.reason_code, schema.RC_SURFACE_ESCAPE)

    # E17 ----------------------------------------------------------------------
    def test_e17_unknown_key_smuggling_refused(self):
        """Unknown payload keys (hook smuggling) die at SCHEMA; code in an
        unknown design key dies at SURFACE (E17)."""
        payload = self.make_payload(P1, "falsification")
        payload["eval_hook"] = "os.system('id')"
        _refingerprint(payload)
        pid, report = self.check(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_SCHEMA)
        self.assertEqual(report.reason_code, schema.RC_SCHEMA)
        self.assertIn("unknown keys are prohibited", report.gates[-1].detail)

        payload2 = self.make_payload(P2, "falsification")
        payload2["design"]["script"] = "import os"
        _refingerprint(payload2)
        pid2, report2 = self.check(payload2)
        self.assertFalse(report2.passed)
        self.assertEqual(report2.failed_gate, schema.GATE_SURFACE)
        self.assertEqual(report2.reason_code, schema.RC_SURFACE_ESCAPE)

    # E18 ----------------------------------------------------------------------
    def test_e18_free_text_code_never_reaches_executable_spec(self):
        """Code-like text in a free-text field (hypothesis) is allowed as
        DECLARED TEXT but can never reach the executable content of the
        compiled spec — the spec files come only from reviewed templates (E18)."""
        payload = self.make_payload(P1, "falsification")
        payload["hypothesis"] = (
            "[probe] import os; os.system('rm -rf /') and __import__('shutil')")
        _refingerprint(payload)
        pid, report = self.check(payload)
        # Free text passes the gates: it is inert, not executed.
        self.assertTrue(report.passed, report.to_dict())
        self.approve(pid)
        spec, _sha = compiler.compile_proposal(
            payload, root=self.root,
            status=schema.STATUS_ACCEPTED_FOR_EXECUTION)
        # Executable content (entrypoint, package init) comes only from the
        # reviewed templates — the injection never lands there.
        joined = "\n".join(entry.content for entry in spec.changes()[:-1])
        self.assertNotIn("os.system", joined)
        self.assertNotIn("__import__", joined)
        self.assertNotIn("rm -rf", joined)
        self.assertIn("os.system", spec.hypothesis)   # declared, inert
        # Inside the rendered config the injection may appear ONLY as the
        # declared hypothesis_text data field — never as executable content,
        # and the config still satisfies the reviewed harness schema.
        from autonomous_agent.recipe_harness import validate_experiment_config
        config = json.loads(spec.changes()[-1].content)
        carriers = [key for key, value in config.items()
                    if isinstance(value, str) and "os.system" in value]
        self.assertEqual(carriers, ["hypothesis_text"])
        self.assertEqual(validate_experiment_config(config), [])

    # F19 ----------------------------------------------------------------------
    def test_f19_path_traversal_citations_refused(self):
        """No citation can read outside the workspace root: traversal,
        Windows-drive, and mixed-separator paths all fail closed (F19)."""
        evil_paths = ["../../etc/passwd",
                      "..\\..\\etc\\passwd",
                      "study_files/outputs/../../secrets.txt",
                      "C:/Windows/win.ini",
                      "autonomous_agent/state/../../../etc/shadow",
                      "../../CHAMPION.json"]
        for path in evil_paths:
            payload = self.make_payload(P1, "falsification")
            payload["evidence_citations"][0] = {
                "artifact_path": path, "sha256": "0" * 64,
                "what_it_shows": "traversal probe"}
            _refingerprint(payload)
            pid, report = self.check(payload)
            self.assertFalse(report.passed, path)
            self.assertEqual(report.failed_gate, schema.GATE_EVIDENCE, path)
            self.assertEqual(report.reason_code,
                             schema.RC_UNRECALLED_EVIDENCE, path)
        # Traversal syntax is rejected before the allowlist can match a path.
        with self.assertRaises(evidence_view.EvidenceViewError):
            evidence_view.assert_source_allowed("../../CHAMPION.json")
        with self.assertRaises(evidence_view.EvidenceViewError):
            evidence_view.assert_source_allowed("versions/../../outside/version.json")
        with tempfile.TemporaryDirectory(prefix="evidence-traversal-") as temporary:
            base = Path(temporary)
            root = base / "workspace"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            sentinel = outside / "version.json"
            sentinel.write_text("synthetic-outside-root-sentinel", encoding="utf-8")
            with self.assertRaises(evidence_view.EvidenceViewError):
                evidence_view._read_bytes(
                    root, "versions/../../outside/version.json")
        with self.assertRaises(evidence_view.EvidenceViewError):
            evidence_view.assert_source_allowed("C:/workspace/CHAMPION.json")
        self.assertEqual(evidence_view.assert_source_allowed(
            "./CHAMPION.json"), "CHAMPION.json")

    def test_f19b_evidence_view_rejects_resolved_symlink_escape(self):
        """A path that resolves outside the root is denied before file access."""
        with tempfile.TemporaryDirectory(prefix="evidence-root-") as temporary:
            base = Path(temporary)
            root = base / "workspace"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            (outside / "version.json").write_text(
                "synthetic-outside-root-sentinel", encoding="utf-8")
            link = root / "versions/V2.0.9"
            link.mkdir(parents=True)
            (link / "version.json").write_text(
                "synthetic-in-root-decoy", encoding="utf-8")
            real_resolve = Path.resolve

            def resolve_external_target(path, *args, **kwargs):
                candidate = Path(path)
                try:
                    suffix = candidate.relative_to(link)
                except ValueError:
                    return real_resolve(path, *args, **kwargs)
                return outside / suffix

            with mock.patch.object(Path, "resolve", resolve_external_target):
                with self.assertRaises(evidence_view.EvidenceViewError):
                    evidence_view._read_bytes(root, "versions/V2.0.9/version.json")
                with self.assertRaises(evidence_view.EvidenceViewError):
                    list(evidence_view._iter_source_paths(root))

    def test_f19c_metadata_dataset_resolution_escape_refused(self):
        """Metadata-only dataset stat also must stay within the workspace."""
        with tempfile.TemporaryDirectory(prefix="evidence-dataset-") as temporary:
            base = Path(temporary)
            root = base / "workspace"
            dataset_parent = root / "study_files/outputs/study_v1/development"
            dataset_parent.mkdir(parents=True)
            outside = base / "outside.csv"
            outside.write_text("synthetic-only-not-market-data", encoding="utf-8")
            (root / "CHAMPION.json").write_text(
                json.dumps({"version": "V2.0.8"}), encoding="utf-8")
            target = dataset_parent / "event_table.csv"

            def escaped_resolve(path, *args, **kwargs):
                if Path(path) == target:
                    return outside
                return real_resolve(path, *args, **kwargs)

            real_resolve = Path.resolve
            with mock.patch.object(Path, "resolve", escaped_resolve):
                with self.assertRaises(evidence_view.EvidenceViewError):
                    evidence_view.build(root, clock=FIXED_CLOCK)

    def test_f19d_invalid_path_types_and_nul_fail_closed(self):
        for value in ("", None, 1, "CHAMPION.json\\x00suffix"):
            with self.assertRaises(evidence_view.EvidenceViewError):
                evidence_view.assert_source_allowed(value)

    # F20 ----------------------------------------------------------------------
    def test_f20_obfuscated_holdout_paths_denied(self):
        """./ prefixes, backslashes, ../ inside the path, and the generic
        holdout marker are all denied before any open (F20)."""
        obfuscated = [
            "./study_files/outputs/study_v1/prospective/secret.csv",
            "study_files\\outputs\\study_v1\\prospective\\secret.csv",
            "study_files/outputs/study_v1/prospective/../prospective/secret.csv",
            "study_files/outputs/holdout/secret.csv",
            "//study_files/outputs/study_v1/prospective/x.csv",
        ]
        for candidate in obfuscated:
            with self.assertRaises(evidence_view.EvidenceViewError,
                                   msg=f"{candidate!r} was NOT denied"):
                evidence_view.assert_source_allowed(candidate)
        # Positive control: allowlisted source still resolves.
        self.assertEqual(evidence_view.assert_source_allowed("CHAMPION.json"),
                         "CHAMPION.json")

    def test_f19e_citation_gate_rejects_resolved_workspace_escape(self):
        """Citation hashing must use the same resolved in-root read boundary."""
        with tempfile.TemporaryDirectory(prefix="evidence-citation-") as temporary:
            base = Path(temporary)
            root = base / "workspace"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            (outside / "version.json").write_text(
                "synthetic-outside-root-sentinel", encoding="utf-8")
            in_root = root / "versions/V2.0.9/version.json"
            in_root.parent.mkdir(parents=True)
            in_root.write_text("synthetic-in-root-decoy", encoding="utf-8")
            view = {"sources": [], "dataset": {}}
            payload = {"evidence_citations": [{
                "artifact_path": "versions/V2.0.9/version.json",
                "sha256": "0" * 64,
            }]}
            report = validator.ValidationReport(passed=True)
            real_resolve = Path.resolve

            def resolve_external_target(path, *args, **kwargs):
                candidate = Path(path)
                try:
                    suffix = candidate.relative_to(in_root.parent)
                except ValueError:
                    return real_resolve(path, *args, **kwargs)
                return outside / suffix

            with mock.patch.object(Path, "resolve", resolve_external_target):
                self.assertFalse(validator._gate_evidence(
                    payload, root, view, report))
            self.assertEqual(report.failed_gate, schema.GATE_EVIDENCE)
            self.assertEqual(report.reason_code, schema.RC_UNRECALLED_EVIDENCE)

    def test_f19f_proposal_with_outside_citation_is_refused(self):
        payload = self.make_payload(P1, "falsification")
        payload["evidence_citations"][0]["artifact_path"] = (
            "versions/../../outside/version.json")
        _refingerprint(payload)
        _, report = self.check(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_EVIDENCE)
        self.assertEqual(report.reason_code, schema.RC_UNRECALLED_EVIDENCE)

    def test_f19g_allowlist_wildcard_cannot_span_path_components(self):
        """fnmatch '*' spans '/' (versions/a/b/version.json matched
        versions/*/version.json), so a nested path inside the versions
        subtree was silently allowlisted by the coarser glob. Allowlist
        patterns match one path component at a time."""
        # One-deep paths stay allowlisted exactly as before.
        self.assertTrue(evidence_view.is_allowed_source(
            "versions/V2.0.9/version.json"))
        self.assertTrue(evidence_view.is_allowed_source(
            "versions/V2.0.9/evaluation.json"))
        # Deeper paths were never intended matches and are refused now.
        with self.assertRaises(evidence_view.EvidenceViewError):
            evidence_view.assert_source_allowed("versions/a/b/version.json")
        with self.assertRaises(evidence_view.EvidenceViewError):
            evidence_view.assert_source_allowed(
                "versions/V2.0.9/extra/version.json")

    def test_f19h_citation_of_file_created_after_the_view_fails_closed(self):
        """A cited artifact carrying no hash in the authorizing evidence view
        is refused, not silently accepted: previously the staleness check
        was skipped whenever lookup returned None, so a file that appeared
        after the view was built passed on its own current hash."""
        late = self.root / "versions/V2.0.9/version.json"
        late.parent.mkdir(parents=True)
        late.write_text("synthetic-late-arrival-slot", encoding="utf-8")
        payload = self.make_payload(P1, "falsification")
        payload["evidence_citations"] = [{
            "artifact_path": "versions/V2.0.9/version.json",
            "sha256": hashlib.sha256(late.read_bytes()).hexdigest(),
            "what_it_shows": "file created after the evidence view"}]
        _refingerprint(payload)
        _, report = self.check(payload)
        self.assertFalse(report.passed)
        self.assertEqual(report.failed_gate, schema.GATE_EVIDENCE)
        self.assertEqual(report.reason_code, schema.RC_UNRECALLED_EVIDENCE)

    def test_f19i_citation_case_alias_respects_view_staleness(self):
        """On a case-insensitive filesystem a case-variant citation path opens
        the SAME file; the recorded-hash lookup must fold case the same way
        the allowlist does, so content mutated after the view was built is
        still detected instead of the staleness check being skipped."""
        sys = __import__("sys")
        if not sys.platform.startswith("win"):
            self.skipTest("Windows-style case-insensitive citations only")
        champion_path = self.root / "CHAMPION.json"
        original = champion_path.read_text("utf-8")

        def citation_for(path_text: str) -> dict:
            return {"artifact_path": path_text,
                    "sha256": hashlib.sha256(
                        champion_path.read_bytes()).hexdigest(),
                    "what_it_shows": "champion"}

        try:
            # Positive control: unchanged content under a case alias stays
            # acceptable (the alias opens the real file, hashes match, and
            # the recorded hash resolves to the same source).
            payload = self.make_payload(P1, "falsification")
            payload["evidence_citations"] = [citation_for("cHaMpIoN.jSoN")]
            _refingerprint(payload)
            _, ok_report = self.check(payload)
            self.assertTrue(ok_report.passed, ok_report.to_dict())

            # Then: mutate AFTER the view was built; the case-aliased
            # citation must NOT bypass the stale-view check.
            mutated = json.loads(original)
            mutated["version"] = "V2.0.8"
            mutated["post_view_mutation_slot"] = "changed after evidence view"
            champion_path.write_text(json.dumps(mutated), encoding="utf-8")
            payload2 = self.make_payload(P1, "falsification")
            payload2["evidence_citations"] = [citation_for("cHaMpIoN.jSoN")]
            _refingerprint(payload2)
            _, report = self.check(payload2)
            self.assertFalse(report.passed)
            self.assertEqual(report.failed_gate, schema.GATE_EVIDENCE)
            self.assertEqual(report.reason_code, schema.RC_UNRECALLED_EVIDENCE)
        finally:
            champion_path.write_text(original, encoding="utf-8")

    def test_f19j_unreadable_cited_artifact_fails_closed_not_crash(self):
        """If the cited file becomes unreadable between the is-file check and
        the read (removed / permission), the gate records FAILED_VALIDATION
        instead of letting an OSError escape the gate chain."""
        with tempfile.TemporaryDirectory(prefix="evidence-unreadable-") as temporary:
            base = Path(temporary)
            root = base / "workspace"
            root.mkdir()
            (root / "CHAMPION.json").write_text(
                "{}", encoding="utf-8")  # exists at check time
            view = {"sources": [{"path": "CHAMPION.json", "sha256": "0" * 64}],
                    "dataset": {}}
            payload = {"evidence_citations": [{
                "artifact_path": "CHAMPION.json", "sha256": "0" * 64}]}
            report = validator.ValidationReport(passed=True)
            # The citation hash now flows through the race-hardened read gate
            # (evidence_view._read_bytes), so the failure is injected at the
            # open() it actually performs.
            import os as _os
            with mock.patch.object(evidence_view.os, "open",
                                   side_effect=PermissionError("denied")):
                self.assertFalse(validator._gate_evidence(
                    payload, root, view, report))
            self.assertEqual(report.failed_gate, schema.GATE_EVIDENCE)
            self.assertEqual(report.reason_code, schema.RC_UNRECALLED_EVIDENCE)

    def test_f19p_hardened_read_positive_control(self):
        """Normal reads still work through the hardened single read gate."""
        champion = self.root / "CHAMPION.json"
        data = evidence_view._read_bytes(self.root, "CHAMPION.json")
        self.assertEqual(hashlib.sha256(data).hexdigest(),
                         hashlib.sha256(champion.read_bytes()).hexdigest())
        version_file = self.root / "versions/V2.0.8/version.json"
        self.assertEqual(
            evidence_view._read_bytes(self.root,
                                      "versions/V2.0.8/version.json"),
            version_file.read_bytes())

    def test_f19q_windows_opened_file_identity_enforced(self):
        """Windows wiring: the OPENED descriptor's identity (st_dev/st_ino)
        must equal the pre-checked file's identity. A substitution between
        the check and the open — in or out of the root — is refused. This
        exercises the wiring with a mocked fstat; it documents the defense
        and is NOT a claim that a mocked test proves OS-level race
        resistance."""
        import sys as _sys
        if not _sys.platform.startswith("win"):
            self.skipTest("Windows identity verification only")

        class SubstitutedStat:
            st_mode = 0o100644
            st_dev = 123456
            st_ino = 654321

        real_fstat = evidence_view.os.fstat
        with mock.patch.object(evidence_view.os, "fstat",
                               return_value=SubstitutedStat()):
            with self.assertRaises(evidence_view.EvidenceViewError) as ctx:
                evidence_view._read_bytes(self.root, "CHAMPION.json")
        self.assertIn("substitution", str(ctx.exception))
        # Positive control after removing the mock: the same read succeeds.
        self.assertTrue(evidence_view._read_bytes(
            self.root, "CHAMPION.json"))
        self.assertEqual(real_fstat.__name__, "fstat")

    def test_f19r_windows_reparse_point_final_component_refused(self):
        """Windows wiring: a reparse point (symlink/junction) as the final
        component is refused before any open (mocked lstat attributes)."""
        import sys as _sys
        if not _sys.platform.startswith("win"):
            self.skipTest("Windows reparse-point attributes only")

        class FakeLstat:
            st_file_attributes = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT
            st_mode = 0o100644

        with mock.patch.object(evidence_view.os, "lstat",
                               return_value=FakeLstat()):
            with self.assertRaises(evidence_view.EvidenceViewError) as ctx:
                evidence_view._read_bytes(self.root, "CHAMPION.json")
        self.assertIn("reparse point", str(ctx.exception))

    def test_f19s_posix_nofollow_chain_refuses_final_symlink(self):
        """POSIX: even when the pre-check containment is DEFEATED, the
        descriptor-relative O_NOFOLLOW chain refuses a final-component
        symlink at open time. Deterministic (no race simulation)."""
        import os as _os
        import sys as _sys
        if not _sys.platform.startswith("linux") \
                and not hasattr(_os, "O_NOFOLLOW"):
            self.skipTest("POSIX O_NOFOLLOW only")
        if _sys.platform == "win32":
            self.skipTest("POSIX O_NOFOLLOW only")
        real_resolve = Path.resolve
        base = Path(tempfile.mkdtemp(prefix="evidence-nofollow-"))
        try:
            root = base / "workspace"
            root.mkdir()
            outside = base / "outside"
            outside.mkdir()
            (outside / "secret.txt").write_text("synthetic", encoding="utf-8")
            _os.symlink(outside / "secret.txt", root / "CHAMPION.json")

            def hide_symlink(path, *args, **kwargs):
                candidate = Path(path)
                if candidate.name == "CHAMPION.json":
                    return candidate  # pretend the containment check passed
                return real_resolve(path, *args, **kwargs)

            with mock.patch.object(Path, "resolve", hide_symlink):
                with self.assertRaises(evidence_view.EvidenceViewError):
                    evidence_view._read_bytes(root, "CHAMPION.json")
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_f19t_posix_intermediate_symlink_refused(self):
        """POSIX: a symlinked intermediate directory component cannot be
        followed even when the pre-check was defeated (O_NOFOLLOW at each
        level of the descriptor chain)."""
        import os as _os
        import sys as _sys
        if _sys.platform == "win32" or not hasattr(_os, "O_NOFOLLOW"):
            self.skipTest("POSIX O_NOFOLLOW only")
        real_resolve = Path.resolve
        base = Path(tempfile.mkdtemp(prefix="evidence-midlink-"))
        try:
            root = base / "workspace"
            outside_tree = base / "outside_tree/V2.0.9"
            outside_tree.mkdir(parents=True)
            (outside_tree / "version.json").write_text(
                "synthetic-outside", encoding="utf-8")
            _os.symlink(outside_tree, root / "versions")

            def hide_symlink(path, *args, **kwargs):
                candidate = Path(path)
                if candidate == root:
                    return real_resolve(path, *args, **kwargs)
                return candidate  # pre-checks see the un-resolved tree

            with mock.patch.object(Path, "resolve", hide_symlink):
                with self.assertRaises(evidence_view.EvidenceViewError):
                    evidence_view._read_bytes(root,
                                              "versions/V2.0.9/version.json")
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_f19u_posix_fifo_refused_not_regular_file(self):
        """POSIX: a FIFO (non-regular file) at an allowlisted path is
        refused by the post-open fstat identity check instead of being read
        or blocking."""
        import os as _os
        import sys as _sys
        if _sys.platform == "win32" or not hasattr(_os, "mkfifo"):
            self.skipTest("POSIX mkfifo only")
        base = Path(tempfile.mkdtemp(prefix="evidence-fifo-"))
        try:
            root = base / "workspace"
            root.mkdir()
            _os.mkfifo(root / "CHAMPION.json")
            with self.assertRaises(evidence_view.EvidenceViewError):
                evidence_view._read_bytes(root, "CHAMPION.json")
        finally:
            shutil.rmtree(base, ignore_errors=True)

    # G21 ----------------------------------------------------------------------
    def test_g21_executor_exception_becomes_recorded_failure_not_crash(self):
        """A raising executor produces a permanent FAILED_EXECUTION record
        and a clean cycle — failures are evidence, not crashes (G21)."""
        executor = ExplodingExecutor()
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "MAX_CYCLES")
        self.assertEqual(len(executor.calls), 1)
        state = self.loop_state()
        self.assertEqual(state["executions_done"], 1)
        self.assertEqual(state["consecutive_failures"], 0)
        failed = [r for r in self.ledger_rows()
                  if r.get("to") == schema.STATUS_FAILED_EXECUTION]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["reason_code"], "EXECUTION_FAILED")
        self.assertIn("synthetic executor explosion",
                      json.dumps(failed[0]["detail"]))
        champion = json.loads((self.root / "CHAMPION.json").read_text("utf-8"))
        self.assertEqual(champion["version"], "V2.0.8")
        memory = json.loads((self.root / "autonomous_agent/state"
                             / "research_memory.json").read_text("utf-8"))
        self.assertTrue(any(d.get("status") == "FAILED"
                            for d in memory.get("discoveries", [])))
        self.assert_lifecycle_legal()

    # G22 ----------------------------------------------------------------------
    def test_g22_executor_non_mapping_outcome_fails_closed(self):
        """An executor returning garbage (None / a string) is coerced into a
        FAILED outcome — never accepted, never promoted (G22)."""
        class NonMappingExecutor:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def __call__(self, spec):
                self.calls.append(spec.experiment_id)
                return None

        executor = NonMappingExecutor()
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "MAX_CYCLES")
        failed = [r for r in self.ledger_rows()
                  if r.get("to") == schema.STATUS_FAILED_EXECUTION]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["reason_code"], "EXECUTION_FAILED")
        self.assertEqual([r for r in self.ledger_rows()
                          if r.get("to") == schema.STATUS_PROMOTED], [])
        # Direct probe: a non-mapping return is coerced fail-closed too.
        loop = self.make_loop(max_cycles=1, executor=lambda spec: "ok")
        outcome = loop._invoke_executor(object(), "exp-probe-nonmapping")
        self.assertEqual(outcome["status"], "FAILED")
        self.assertIn("non-mapping", outcome["error"]["message"])

    # G23 ----------------------------------------------------------------------
    def test_g23_tampered_artifact_hash_cannot_promote(self):
        """Acceptance evidence whose artifact hash does not match the candidate
        tree is refused at promotion: champion untouched, no version (G23)."""
        executor = TamperedArtifactExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "PROMOTION_FAILED")
        self.assertEqual(len(executor.calls), 1)
        champion = json.loads((self.root / "CHAMPION.json").read_text("utf-8"))
        self.assertEqual(champion["version"], "V2.0.8")
        self.assertFalse((self.root / "versions/V2.0.9").exists())
        self.assertEqual([r for r in self.ledger_rows()
                          if r.get("to") == schema.STATUS_PROMOTED], [])
        self.assertEqual(self.loop_state()["status"], "STOPPED")

    # H24 ----------------------------------------------------------------------
    def _craft_interrupted(self, experiment_id: str) -> tuple[str, dict]:
        """Proposal at EXECUTED/started (crash window), no durable result."""
        policy = self.policy()
        payload = generator.generate_proposals(self.view, policy,
                                               seed=7, limit=1)[0]
        pid = self.ledger.create_proposal(payload)
        self.ledger.transition(pid, schema.STATUS_VALIDATING)
        self.approve(pid)
        self.ledger.transition(pid, schema.STATUS_COMPILED,
                               reason_code="COMPILED",
                               detail={"spec_sha256": "s" * 64,
                                       "experiment_id": experiment_id})
        self.ledger.transition(pid, schema.STATUS_EXECUTED,
                               reason_code="EXECUTION_STARTED",
                               detail={"phase": "started",
                                       "experiment_id": experiment_id,
                                       "spec_sha256": "s" * 64})
        return pid, payload

    def test_h24_interrupted_attempt_without_durable_result_recorded_never_retried(self):
        """Crash before any durable result: the attempt is recorded as
        EXECUTION_INTERRUPTED, counts against budget, and is NEVER re-run
        on this or any later start (H24)."""
        pid, _payload = self._craft_interrupted("exp-proposal-interrupt01")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "MAX_CYCLES")
        self.assertEqual(self.ledger.status(pid),
                         schema.STATUS_FAILED_EXECUTION)
        rows = self.ledger.transitions_of(pid)
        self.assertEqual(rows[-1]["reason_code"], "EXECUTION_INTERRUPTED")
        self.assertIn("never silently retried",
                      json.dumps(rows[-1]["detail"]))
        self.assertNotIn("exp-proposal-interrupt01", executor.calls)
        # Budget honesty: the interrupted attempt counts (1) plus one fresh
        # execution in the same cycle (2) — a consumed attempt is never
        # refunded.
        self.assertEqual(self.loop_state()["executions_done"], 2)
        self.assert_lifecycle_legal()
        # Restart: the attempt is terminal — never re-executed, never moved.
        before = len(self.ledger.transitions_of(pid))
        second = self.make_loop(max_cycles=2, executor=executor).run()
        self.assertEqual(second["stop_reason"], "MAX_CYCLES")
        self.assertEqual(self.ledger.status(pid),
                         schema.STATUS_FAILED_EXECUTION)
        self.assertEqual(len(self.ledger.transitions_of(pid)), before)
        self.assertNotIn("exp-proposal-interrupt01", executor.calls)

    # H25 ----------------------------------------------------------------------
    def test_h25_forged_durable_result_cannot_promote(self):
        """Crash-recovery path: a forged result.json claiming ACCEPTED with
        fabricated (empty) evidence cannot promote — no re-run, champion
        untouched, loop stops (H25)."""
        experiment_id = "exp-proposal-forged01"
        pid, _payload = self._craft_interrupted(experiment_id)
        result_dir = (self.root / "autonomous_agent/candidates"
                      / experiment_id)
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / "result.json").write_text(json.dumps({
            "experiment_id": experiment_id,
            "status": "ACCEPTED",
            "acceptance_recommendation": "ACCEPT",
            "metrics": {},
            "checks": {},
            "candidate_path": None,
        }), encoding="utf-8")
        executor = MockExecutor(self.root)
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "PROMOTION_FAILED")
        self.assertEqual(executor.calls, [])   # never re-run
        self.assertIn(self.ledger.status(pid),
                      (schema.STATUS_ADJUDICATED,))
        self.assertEqual([r for r in self.ledger_rows()
                          if r.get("to") == schema.STATUS_PROMOTED], [])
        champion = json.loads((self.root / "CHAMPION.json").read_text("utf-8"))
        self.assertEqual(champion["version"], "V2.0.8")
        self.assertFalse((self.root / "versions/V2.0.9").exists())
        self.assertEqual(self.loop_state()["status"], "STOPPED")

    # H26 ----------------------------------------------------------------------
    def test_h26_acceptance_streak_capped_by_budget_and_legal_lifecycle(self):
        """An always-accepting executor cannot exceed the frozen execution
        budget: exactly max_total_executions runs, sequential versions, every
        transition legal, portfolio minimums satisfied (H26)."""
        executor = AlwaysAcceptExecutor(self.root)
        summary = self.make_loop(max_cycles=8, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "EXECUTION_BUDGET")
        self.assertEqual(summary["status"], "STOPPED")
        self.assertEqual(len(executor.calls), 4, executor.calls)
        self.assertEqual(len(set(executor.calls)), 4)   # one run per experiment
        for version in ("V2.0.9", "V2.0.10", "V2.0.11", "V2.0.12"):
            self.assertTrue((self.root / "versions" / version
                             / "version.json").is_file(), version)
        champion = json.loads((self.root / "CHAMPION.json").read_text("utf-8"))
        self.assertEqual(champion["version"], "V2.0.12")
        state = self.loop_state()
        self.assertEqual(state["executions_done"], 4)
        self.assertEqual(state["consecutive_failures"], 0)
        self.assert_lifecycle_legal()
        report = self.make_loop(max_cycles=1, executor=executor).\
            exhaustion_report()
        self.assertTrue(report["portfolio_complete"], report)
        self.assertGreaterEqual(report["executed_by_class"].get(
            "falsification", 0), 1)
        self.assertGreaterEqual(report["executed_by_class"].get(
            "confirmatory", 0), 1)


if __name__ == "__main__":
    unittest.main()
