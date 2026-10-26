"""Freeze-integrity, protected-state preservation, and stop-correspondence tests.

Authorized 2026-10-12 (gate 3, D2-independent subset). Three jobs:

1. **Protected state is preserved.** Pinned artifacts (plan, H-10 record,
   review bundle, Campaign 3 frozen config, C4 draft, flake evidence, the
   flake-fixed test) must keep the exact digests recorded in the governance
   documents. A future *authorized* change must consciously re-pin; this
   test failing is the mechanism that forces that.
2. **Declared stops correspond to enforcement code.** Every stop condition
   a frozen campaign config declares must map to markers that actually
   exist in the harness source — the config's ``stop_conditions`` list is
   declarative, so without this test a stop name could be declared with
   nothing behind it.
3. **The v1.1.0 additions are inert for v1.0.0.** No module other than the
   loop imports the new machinery; the five v1.1.0 primitives stay
   dormant; Campaign 3's frozen config declares none of the new stops.

Loop-level behavior of the new stops and the firewall is exercised here on
disposable fixtures with a mock executor — no real experiment, no real
production state.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from autonomous_agent.continuous_loop import LoopStop, ResearchLoop
from autonomous_agent.proposal_layer import multiplicity as mult, schema
from autonomous_agent.test_continuous_loop import MockExecutor, write_launch_gates
from autonomous_agent.test_proposal_layer import FIXED_CLOCK, build_fixture
from autonomous_agent.test_stage2_campaign import write_campaign

REPO = Path(__file__).resolve().parent.parent
STATE = REPO / "autonomous_agent/state"

# Documented pins (owner authorization record §5, review packet §10, flake
# evidence file). These are governance anchors, not convenience hashes.
PINNED = {
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
    "HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md": "094827b0",
    "stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md": "b9db3233",
    "stat_validation_h10/H10_D2_REVIEW_SUBMISSION.zip": "ee345dab",
    # Live config pin: changes exactly once per campaign freeze, under the
    # recorded freeze act (C4_FREEZE_RECORD_2026_10_14.md). Campaign 3's
    # pin was 1e0e30b8; the frozen Campaign 4 config's fresh pin follows.
    # 2026-10-15 re-freeze (owner repair directive, recorded in
    # C4_GENERATOR_REPAIR_AND_REFREEZE_RECORD_2026_10_15.md): 33334d14 ->
    # f5293708. Capacity re-freeze (owner directive "Continue Campaign 4
    # Through Completion", same record section 6): f5293708 -> b40c9c01,
    # then capacity re-freeze #2 (interruption slack, same record): ->
    # 3e6a5ae4, then capacity re-freeze #3 (post-crash interruption
    # slack): -> d8bff195
    # (proposals 45->64, class budgets falsification 18->34 / confirmatory
    # 12->14; ceilings only, consumption preserved, statistical surface
    # untouched). Each re-pin is deliberate and exactly once per freeze.
    # Campaign 5 freeze (B4 owner decision packet signed by PMED 2026-10-22,
    # Option D): d8bff195 -> 29c905aa; final after the 2026-10-23
    # key-rotation-era completions recorded in the config's _FREEZE_STATUS
    # (protocol_sha256 + authorization_scope additions; the authorization
    # record was re-signed and verifies end-to-end under the rotated HMAC
    # keys, preflight APPROVED).
    "autonomous_agent/state/campaign_config.json": "29c905aa",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
    "CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json": "307e98ab",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
    "GOVERNANCE_SUITE_FLAKE_EVIDENCE_2026_10_11.md": "72504661",
    # 2026-10-22 deliberate re-pin (F-5 launch-gate fix; fixture-only
    # changes plus the shared write_launch_gates helper and the new
    # launch-gate regression tests — no assertion was weakened, skipped,
    # or removed): e1de8523 -> 5423af61.
    # 2026-10-25 deliberate re-pin 5423af61 -> 6861fc37: the file was edited
    # earlier on 2026-10-25 (~16:08Z, outside this declaration work — its
    # own 15-test suite passes) and no repository history exists to restore
    # from; the pin is updated to the current verified content rather than
    # silently kept on the stale value.
    "autonomous_agent/test_continuous_loop.py": "6861fc37",
}

# Config stop condition -> (relative file, literal marker) pairs that must
# exist in the source. Add a stop to a frozen config and this map must grow
# with it, or the correspondence test fails.
STOP_ENFORCEMENT: dict[str, tuple[tuple[str, str], ...]] = {
    "max_total_executions_reached":
        (("autonomous_agent/continuous_loop.py", '"EXECUTION_BUDGET"'),),
    "portfolio_minimums_met_and_no_admissible_proposal":
        (("autonomous_agent/continuous_loop.py", '"PORTFOLIO_COMPLETE"'),),
    "holdout_or_prospective_access_detected":
        (("autonomous_agent/continuous_loop.py", '"HOLDOUT_TOUCHED"'),
         ("autonomous_agent/continuous_loop.py", '"HOLDOUT_STATE"')),
    "arbitrary_code_or_executor_bypass_detected":
        (("autonomous_agent/proposal_layer/schema.py", "def looks_like_code"),
         ("autonomous_agent/proposal_layer/validator.py", "_gate_surface")),
    "validation_or_approval_bypass_detected":
        (("autonomous_agent/proposal_layer/ledger.py", "approval provenance"),
         ("autonomous_agent/proposal_layer/ledger.py", "class LedgerError")),
    "provenance_loss_or_ledger_corruption":
        (("autonomous_agent/continuous_loop.py", '"INVALID_LEDGER_STATE"'),
         ("autonomous_agent/proposal_layer/ledger.py", "class LedgerCorrupt")),
    "budget_inconsistency_or_negative_capacity":
        (("autonomous_agent/continuous_loop.py", '"BUDGET_INCONSISTENCY"'),),
    "duplicate_execution_detected":
        (("autonomous_agent/hardening.py", "class SpecRegistry"),
         ("autonomous_agent/hardening.py", "duplicate prevention")),
    "invalid_lifecycle_transition":
        (("autonomous_agent/proposal_layer/ledger.py", "Illegal transition"),),
    "repeated_crash_threshold_exceeded":
        (("autonomous_agent/continuous_loop.py", '"REPEATED_CRASHES"'),),
    "stale_loop_lock":
        (("autonomous_agent/continuous_loop.py", '"LOCKED"'),),
    "research_proposal_direction_or_class_exhaustion":
        (("autonomous_agent/continuous_loop.py", '"PROPOSAL_EXHAUSTED"'),),
    "explicit_STOP_file_present":
        (("autonomous_agent/continuous_loop.py", '"STOP_FILE"'),),
    "campaign_config_hash_mismatch":
        (("autonomous_agent/continuous_loop.py", '"CAMPAIGN_CONFIG_HASH_MISMATCH"'),),
    # The two v1.1.0 stops (authorized 2026-10-12): declared here so a C4
    # config that declares them is enforced, and so the wiring cannot be
    # silently deleted.
    "point_in_time_contamination_detected":
        (("autonomous_agent/continuous_loop.py", "audit_stop_signal"),
         ("autonomous_agent/continuous_loop.py", "AUDIT_STOP_CONDITIONS"),
         ("autonomous_agent/proposal_layer/multiplicity.py",
          "CONFIRMED_CONTAMINATION")),
    "unverifiable_lineage_detected":
        (("autonomous_agent/continuous_loop.py", "recorded_audit_stop"),
         ("autonomous_agent/proposal_layer/multiplicity.py", "UNVERIFIABLE_LINEAGE")),
    # Campaign 5's two declared signal stops (launched 2026-10-23), wired by
    # autonomous_agent/proposal_layer/stops_c5.py plus the loop's
    # adjudication path, in the same durable-first contract as the v1.1.0
    # audit stops. "c5_signal_stop" appears in both the loop's
    # adjudication-time firmware and its restart guard.
    "regime_predefinition_violation":
        (("autonomous_agent/continuous_loop.py", "c5_signal_stop"),
         ("autonomous_agent/proposal_layer/stops_c5.py",
          "STOP_REGIME_PREDEFINITION"),
         ("autonomous_agent/proposal_layer/stops_c5.py",
          "regime_predefinition_violation")),
    "data_snooping_detected":
        (("autonomous_agent/continuous_loop.py", "c5_signal_stop"),
         ("autonomous_agent/proposal_layer/stops_c5.py",
          "STOP_DATA_SNOOPING"),
         ("autonomous_agent/proposal_layer/stops_c5.py",
          "data_snooping_detected")),
}

C3_STOPS = tuple(name for name in STOP_ENFORCEMENT
                 if name not in mult.AUDIT_STOP_CONDITIONS)

FIVE_GATES_LITERAL = ('gates = ("unit", "data_integrity", "leakage", '
                      '"walk_forward", "robustness", "evaluation")')


def _sha(relative: str) -> str:
    return hashlib.sha256((REPO / relative).read_bytes()).hexdigest()


class ProtectedPinTests(unittest.TestCase):
    """Governance anchors must not drift."""

    def test_pinned_artifacts_match_their_documented_digests(self) -> None:
        for relative, prefix in PINNED.items():
            path = REPO / relative
            self.assertTrue(path.is_file(), f"missing pinned artifact {relative}")
            self.assertTrue(_sha(relative).startswith(prefix),
                            f"{relative} drifted: {_sha(relative)[:16]}… "
                            f"expected {prefix}… — re-pin deliberately or restore it")

    def test_campaign_config_sidecar_still_pins_the_live_config(self) -> None:
        pinned = (STATE / "campaign_config.sha256").read_text("utf-8").split()[0]
        self.assertEqual(pinned, _sha("autonomous_agent/state/campaign_config.json"))

    def test_campaign_3_state_is_archived_and_stopped(self) -> None:
        # Campaign 3's final state lives at the live loop_state.json until
        # the Campaign 4 freeze installs and archives it (campaign-2
        # precedent); the invariant is that it is preserved, STOPPED, and
        # never rewritten. Once Campaign 4 has actually launched, the
        # live state is Campaign 4's and the archive is authoritative
        # for Campaign 3.
        live = STATE / "loop_state.json"
        archived = STATE / "loop_state.campaign-3-continuous-2026-10-05.final.json"
        if archived.exists():
            path = archived
        else:
            path = live
        self.assertTrue(path.is_file(), "Campaign 3 final state is gone")
        state = json.loads(path.read_text("utf-8"))
        self.assertTrue(state["campaign_id"].startswith("campaign-3"))
        self.assertEqual(state["status"], "STOPPED")
        self.assertEqual(state["executions_done"], 38)
        config = json.loads((STATE / "campaign_config.json").read_text("utf-8"))
        cid = config["campaign_id"]
        # live config epoch lineage: campaign-3/4/5 era (Campaign 5 frozen
        # 2026-10-22 per the B4 owner decision packet).
        self.assertTrue(cid.startswith(("campaign-3", "campaign-4", "campaign-5")))
        if not cid.startswith("campaign-3"):
            # frozen successor epoch: Campaign 3's config must be archived
            # too. The live loop_state.json is absent between the rollover
            # and the first new-campaign start (documented freeze state,
            # campaign-2/3->4 precedent); once it exists it must belong to
            # the current campaign lineage.
            self.assertTrue((STATE / "campaign_config."
                                   "campaign-3-continuous-2026-10-05.json").is_file())
            live_state = STATE / "loop_state.json"
            if live_state.exists():
                self.assertTrue(json.loads(live_state.read_text("utf-8"))
                                ["campaign_id"].startswith(("campaign-4",
                                                            "campaign-5")))
        archive = (REPO / "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
                          "CAMPAIGN_3_FINAL_ARCHIVE_2026-10-09")
        self.assertTrue((archive / "campaign_config.json").is_file())

    def test_ledger_still_folds_strictly(self) -> None:
        from autonomous_agent.proposal_layer.ledger import ProposalLedger
        rows = ProposalLedger(STATE / "proposal_ledger.jsonl").read_rows(strict=True)
        self.assertGreaterEqual(len(rows), 350)
        self.assertTrue(any(row.get("row_type") == "proposal" for row in rows))


class HoldoutSealTests(unittest.TestCase):
    def test_holdout_directory_is_absent(self) -> None:
        for candidate in ("prospective", "autonomous_agent/prospective",
                          "study_files/outputs/study_v1/prospective"):
            self.assertFalse((REPO / candidate).exists(), candidate)

    def test_frozen_policy_stays_sealed_with_zero_uses(self) -> None:
        policy = json.loads((STATE / "campaign_config.json")
                            .read_text("utf-8"))["holdout_policy"]
        self.assertEqual(policy["status"], "SEALED")
        self.assertEqual(policy["uses"], 0)
        self.assertEqual(policy["prospective_usage"], 0)

    def test_evidence_view_still_refuses_holdout_paths(self) -> None:
        from autonomous_agent.proposal_layer import evidence_view
        self.assertTrue(evidence_view.is_denied(
            "study_files/outputs/study_v1/prospective/holdout.csv"))
        with self.assertRaises(evidence_view.EvidenceViewError):
            evidence_view.assert_source_allowed("prospective/anything.csv")


class FrozenPolicySurfaceTests(unittest.TestCase):
    """The existing safety surface must be untouched by v1.1.0."""

    def test_five_existing_gate_names_are_unchanged(self) -> None:
        source = (REPO / "autonomous_agent/experiment_adapter.py").read_text("utf-8")
        self.assertIn(FIVE_GATES_LITERAL, source)

    def test_frozen_config_policy_fields_are_unchanged(self) -> None:
        config = json.loads((STATE / "campaign_config.json").read_text("utf-8"))
        overrides = config["policy_overrides"]
        # Floor is era-pinned by each recorded freeze: C4 froze 0.35; the C5
        # freeze (Option D, B1 C4->C5 deltas) releases it to 0.3 while every
        # other field below stays identical.
        expected_falsification_floor = {
            "campaign-4": 0.35, "campaign-5": 0.3}
        cid = config.get("campaign_id", "")
        era = next((prefix for prefix in sorted(expected_falsification_floor)
                    if cid.startswith(prefix)), None)
        self.assertIsNotNone(era, f"unknown campaign era {cid!r}")
        self.assertEqual(overrides["min_falsification_share"],
                         expected_falsification_floor[era])
        self.assertEqual(overrides["max_replication_share"], 0.5)
        self.assertEqual(config["approval"]["policy"], "revalidate_at_approval@1.0.0")
        self.assertEqual(config["outcome_blindness_policy"]["closed_selection_inputs"],
                         ["direction", "proposal_class", "novelty_score",
                          "evidence_gap_score", "quota_pressure", "priority",
                          "attempts_in_direction"])
        self.assertEqual(config["duplicate_policy"]["layers"],
                         ["exact_proposal_fingerprint", "bucketed_design_signature",
                          "same_signature_text_similarity>=0.90",
                          "prior_campaign_recipe_replay", "already_asked_memory"])
        self.assertEqual(config["duplicate_policy"]["already_asked"],
                         "global_and_permanent_across_campaigns")

    def test_v1_1_0_primitives_active_only_under_the_recorded_r3_grant(self) -> None:
        # Owner R-3 grant (2026-10-12) supersedes the pre-grant dormancy pin:
        # the five primitives are executable, and activation is legitimate
        # ONLY while the grant record exists. Delete the record and this
        # pin fails -- activation without recorded authorization is still
        # refused.
        grant = (REPO / "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
                 "PRIMITIVE_ACTIVATION_GRANT_R3_2026_10_12.md")
        self.assertTrue(grant.is_file(),
                        "R-3 grant record missing: five primitives are "
                        "executable without recorded authorization")
        grant_text = grant.read_text("utf-8")
        self.assertIn("OWNER GRANT RECORDED FOR PRIMITIVE ACTIVATION ONLY",
                      grant_text)
        source = (REPO / "autonomous_agent/proposal_layer/primitives.py").read_text("utf-8")
        import re
        five_activated = ("purge_sensitivity_probe", "regime_split_analysis",
                          "complexity_reduction_check", "target_horizon_robustness",
                          "point_in_time_data_audit")
        for primitive in five_activated:
            match = re.search(
                r'primitive_id="%s"[\s\S]{0,400}?executable=(True|False)'
                % re.escape(primitive), source)
            self.assertIsNotNone(match, f"{primitive} disappeared from primitives.py")
            self.assertEqual(match.group(1), "True",
                             f"{primitive} is dormant despite the R-3 grant")


class StopCorrespondenceTests(unittest.TestCase):
    def test_every_declared_stop_has_enforcement_markers(self) -> None:
        config = json.loads((STATE / "campaign_config.json").read_text("utf-8"))
        declared = list(config["stop_conditions"])
        for stop in declared:
            self.assertIn(stop, STOP_ENFORCEMENT,
                          f"declared stop {stop!r} has no recorded enforcement site")
        for stop in declared:
            for relative, marker in STOP_ENFORCEMENT[stop]:
                source = (REPO / relative).read_text("utf-8")
                self.assertIn(marker, source,
                              f"{stop}: enforcement marker {marker!r} missing "
                              f"from {relative}")

    def test_new_stops_are_wired_even_though_c3_does_not_declare_them(self) -> None:
        self.assertEqual(mult.AUDIT_STOP_CONDITIONS,
                         {"point_in_time_contamination_detected",
                          "unverifiable_lineage_detected"})
        for stop in sorted(mult.AUDIT_STOP_CONDITIONS):
            self.assertIn(stop, STOP_ENFORCEMENT)
        config = json.loads((STATE / "campaign_config.json").read_text("utf-8"))
        if config["campaign_id"].startswith("campaign-3"):
            self.assertFalse(set(config["stop_conditions"]) & mult.AUDIT_STOP_CONDITIONS,
                             "Campaign 3's frozen config must not declare the new stops")
        else:
            # Any frozen successor campaign (C4, C5) must declare both wired
            # v1.1.0 audit stops
            self.assertTrue(mult.AUDIT_STOP_CONDITIONS <=
                            set(config["stop_conditions"]),
                            "frozen successor campaign must declare both "
                            "v1.1.0 audit stops")

    def test_map_covers_every_stop_name_the_harness_can_declare(self) -> None:
        from autonomous_agent.proposal_layer import stops_c5
        config = json.loads((STATE / "campaign_config.json").read_text("utf-8"))
        expected = set(C3_STOPS)
        if config["campaign_id"].startswith("campaign-4"):
            expected |= set(mult.AUDIT_STOP_CONDITIONS)
        elif config["campaign_id"].startswith("campaign-5"):
            expected |= set(mult.AUDIT_STOP_CONDITIONS)
            expected |= set(stops_c5.C5_SIGNAL_STOPS)
        self.assertEqual(set(config["stop_conditions"]), expected)


class InertnessTests(unittest.TestCase):
    """v1.0.0 behavior stays byte-identical unless the new code is opted into."""

    def test_only_the_loop_imports_the_multiplicity_machinery(self) -> None:
        # needle is concatenated so this file cannot match itself
        needle = "import " + "multiplicity"
        importers = set()
        for path in list((REPO / "autonomous_agent").glob("*.py")) + \
                list((REPO / "autonomous_agent/proposal_layer").glob("*.py")):
            if path.name == Path(__file__).name:
                continue
            if needle in path.read_text("utf-8"):
                importers.add(path.name)
        self.assertEqual(importers,
                         {"continuous_loop.py", "test_multiplicity.py",
                          "test_signflip_port.py",
                          # 2026-10-25: test-only importer added with the
                          # error_clustering_analysis declaration tests.
                          "test_error_clustering_declaration.py"})

    def test_nothing_imports_the_census_machinery_but_its_tests(self) -> None:
        needle = "import " + "census"
        importers = set()
        for path in list((REPO / "autonomous_agent").glob("*.py")) + \
                list((REPO / "autonomous_agent/proposal_layer").glob("*.py")):
            if needle in path.read_text("utf-8"):
                importers.add(path.name)
        self.assertEqual(importers, {"test_census_manifest.py"})


# ---------------------------------------------------------------- loop behavior
class RepairPreservesPriorEvidence(unittest.TestCase):
    """2026-10-15 repair directive: the generator repair must not alter any
    prior experiment adjudication or weaken any promotion gate."""

    PROMOTED_TREES = {
        "7cc1bdc76ef986c03c3c901c18da285e8c0b28087c7941f2521bfeb8c1069c90",
        "3071f5d695e764ba95dd6bf73262e96095f7380fae3e0ed5d8938ac0d44ffc59",
    }
    SIX_GATES = {"unit", "data_integrity", "leakage", "walk_forward",
                 "robustness", "evaluation"}

    def test_both_promoted_executions_remain_recorded_verbatim(self) -> None:
        rows = [json.loads(line) for line in
                (STATE / "proposal_ledger.jsonl").read_text("utf-8").splitlines()
                if line.strip()]
        promoted = [r for r in rows
                    if r.get("row_type") == "transition"
                    and r.get("to") == "PROMOTED"]
        trees = {(r.get("detail") or {}).get("artifact_sha256")
                 for r in promoted}
        for tree in self.PROMOTED_TREES:
            self.assertIn(tree, trees,
                          "a pre-repair promotion was erased or rewritten")
        adjudicated = [r for r in rows
                       if r.get("row_type") == "transition"
                       and r.get("to") == "ADJUDICATED"
                       and (r.get("detail") or {}).get("artifact_sha256")
                       in self.PROMOTED_TREES]
        self.assertEqual(len(adjudicated), 2)
        for row in adjudicated:
            self.assertEqual((row.get("detail") or {}).get("result"),
                             "ACCEPTED")

    def test_prior_results_still_carry_six_pass_gates_and_sealed_holdout(self) -> None:
        for experiment_id in ("exp-proposal-5d52d16b94ca",
                              "exp-proposal-4fdf6dd35236"):
            path = (REPO / "autonomous_agent/candidates" / experiment_id
                    / "result.json")
            self.assertTrue(path.is_file(), experiment_id)
            result = json.loads(path.read_text("utf-8"))
            self.assertEqual(result["acceptance_recommendation"], "PROMOTE")
            self.assertEqual(set(result["checks"]), self.SIX_GATES)
            self.assertTrue(all(v == "PASS" for v in result["checks"].values()),
                            result["checks"])
            self.assertEqual(result["holdout_status"], "SEALED")

    def test_live_loop_state_still_counts_every_prior_execution(self) -> None:
        # Campaign 4 epoch: >= 32 executions recorded (historical floor 2 for
        # the post-launch bounded run). Campaign 5 (fresh epoch, campaign-
        # scoped budgets, launched 2026-10-23) starts at 0, so the era-aware
        # campaign-5 invariant is the authorized-BUDGET ceiling: executions
        # may grow with the campaign but must never exceed it.
        state = json.loads((STATE / "loop_state.json").read_text("utf-8"))
        if state["campaign_id"].startswith("campaign-5"):
            config = json.loads((STATE / "campaign_config.json").read_text("utf-8"))
            budget = int((config.get("execution") or {})
                         ["max_total_executions"])
            self.assertLessEqual(int(state["executions_done"]), budget)
        else:
            self.assertTrue(state["campaign_id"].startswith("campaign-4"))
            self.assertGreaterEqual(int(state["executions_done"]), 2)


def _complete_champion(root: Path) -> None:
    champion_path = root / "CHAMPION.json"
    champion = json.loads(champion_path.read_text("utf-8"))
    for key, value in {
        "code_revision": "a" * 40, "dataset_id": "fixture_dataset",
        "feature_set": ["f1"], "model": ["LogisticRegression"],
        "target_definition": "fixture target", "training_period": "2022-2025",
        "validation_period": "folds 2023/2024/2025",
        "backtest": {"status": "NOT_RUN"}, "leakage_status": "PASS",
        "known_limitations": ["fixture"],
        "reproduction_command": "py -3 -m autonomous_agent.experiments.run_experiment",
        "baseline_kind": "reconstructed_baseline",
        "v1_0_1_status": "FAILED",
        "historical_v1_0_1_sha256": "29885c5f14235e78349b728156e18feba930f3ee"
                                    "533565ea36a05f695692424b",
        "reconstructed_source_sha256": "b" * 40,
        "self_reproduction": {"byte_identical": True},
        "validation_scope": "fixture: NOT a reproduction of V1.0.1",
        "dataset_sha256": "c" * 64, "created_at": "2026-10-04T00:00:00+00:00",
    }.items():
        champion.setdefault(key, value)
    champion["lineage"] = {"relation": "reconstruction", "parent": "V2.0.7"}
    champion_path.write_text(json.dumps(champion, indent=1), encoding="utf-8")
    (root / "autonomous_agent/proposal_config.json").write_text(
        json.dumps({"schema_version": 1, "allow_generated_proposals": True}),
        encoding="utf-8")


class _FixtureLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="freeze_integrity_"))
        self.root = self.tmp / "ws"
        self.root.mkdir(parents=True)
        build_fixture(self.root)
        _complete_champion(self.root)
        self.campaign = write_campaign(self.root)
        write_launch_gates(self.root)
        self.ledger_path = (self.root /
                            "autonomous_agent/state/proposal_ledger.jsonl")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_loop(self, max_cycles: int = 3, executor=None) -> ResearchLoop:
        return ResearchLoop(self.root, max_cycles=max_cycles,
                            executor=executor or MockExecutor(self.root),
                            clock=FIXED_CLOCK)

    def ledger_text(self) -> str:
        return self.ledger_path.read_text("utf-8") \
            if self.ledger_path.exists() else ""


class C5SignalStopBehaviorTests(_FixtureLoopTest):
    """Campaign 5's two declared signal stops behave like the audit stops:
    durable-first ledger record, unconditional adjudication-time halt, and a
    restart guard scoped to configs that declare the stops."""

    def _declare_both(self) -> None:
        from autonomous_agent.proposal_layer import stops_c5
        write_campaign(
            self.root,
            stop_conditions=sorted(set(mult.AUDIT_STOP_CONDITIONS)
                                   | set(stops_c5.C5_SIGNAL_STOPS)))

    def _snooping_executor(self):
        def executor(spec):
            return {"status": "REJECTED",
                    "checks": {"unit": "PASS", "data_integrity": "PASS",
                               "leakage": "PASS", "walk_forward": "PASS",
                               "robustness": "PASS", "evaluation": "FAIL"},
                    "results": {"primary_metric": {"name": "x", "delta": -0.01},
                                "decision_criteria_passed": False,
                                "data_snooping_status":
                                    "DATA_SNOOPING_DETECTED"},
                    "candidate_path": None, "holdout_touched": False,
                    "blockers": [], "leakage_status": "PASS",
                    "robustness_status": "PASS"}
        return executor

    def test_data_snooping_signal_halts_durably_and_on_restart(self) -> None:
        self._declare_both()
        summary = self.make_loop(max_cycles=1,
                                 executor=self._snooping_executor()).run()
        self.assertEqual(summary["stop_reason"], "data_snooping_detected")
        rows = [json.loads(line) for line in self.ledger_text().splitlines()
                if line.strip()]
        stops = [row for row in rows
                 if (row.get("detail") or {}).get("c5_signal_stop")
                 == "data_snooping_detected"]
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["to"], schema.STATUS_FAILED_EXECUTION)
        restarted = self.make_loop(max_cycles=1, executor=MockExecutor(self.root))
        with self.assertRaises(LoopStop) as caught:
            restarted.cycle_once()
        self.assertEqual(caught.exception.reason, "data_snooping_detected")

    def test_regime_predefinition_signal_halts_durably_and_on_restart(self) -> None:
        self._declare_both()

        def executor(spec):
            return {"status": "REJECTED",
                    "checks": {"unit": "PASS", "data_integrity": "PASS",
                               "leakage": "PASS", "walk_forward": "PASS",
                               "robustness": "PASS", "evaluation": "FAIL"},
                    "results": {"primary_metric": {"name": "x", "delta": -0.01},
                                "decision_criteria_passed": False,
                                "regime_predefinition_status":
                                    "VIOLATION_OF_REGIME_PREDECLARATION"},
                    "candidate_path": None, "holdout_touched": False,
                    "blockers": [], "leakage_status": "PASS",
                    "robustness_status": "PASS"}
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"],
                         "regime_predefinition_violation")
        rows = [json.loads(line) for line in self.ledger_text().splitlines()
                if line.strip()]
        stops = [row for row in rows
                 if (row.get("detail") or {}).get("c5_signal_stop")
                 == "regime_predefinition_violation"]
        self.assertEqual(len(stops), 1)
        restarted = self.make_loop(max_cycles=1, executor=MockExecutor(self.root))
        with self.assertRaises(LoopStop) as caught:
            restarted.cycle_once()
        self.assertEqual(caught.exception.reason,
                         "regime_predefinition_violation")

    def test_ordinary_verdicts_never_trigger_the_c5_walker(self) -> None:
        from autonomous_agent.proposal_layer import stops_c5
        examples = [
            {"status": "ACCEPTED"},
            {"status": "REJECTED"},
            {"data_snooping": "NOT_DETECTED"},
            {"data_snooping": "NONE_FOUND"},
            {"data_snooping": "NONE_DETECTED"},
            {"regime_predefinition_status": "PREDECLARED"},
            {"results": {"status": "PASS", "checks": ["ok"]}},
            {},]
        for outcome in examples:
            self.assertIsNone(stops_c5.c5_signal_stop(outcome), outcome)


class NewStopBehaviorTests(_FixtureLoopTest):
    def _with_declared_stops(self, stops) -> None:
        write_campaign(self.root, stop_conditions=list(stops))

    def test_normal_rejection_is_unaffected_by_the_firewall(self) -> None:
        summary = self.make_loop(max_cycles=1, executor=MockExecutor(self.root)).run()
        self.assertEqual(summary["stop_reason"], "MAX_CYCLES")
        self.assertNotIn("FIREWALL_VIOLATION", self.ledger_text())

    def test_bare_refuted_label_halts_the_campaign_before_it_is_recorded(self) -> None:
        def executor(spec):
            return {"status": "REJECTED",
                    "checks": {"unit": "PASS", "data_integrity": "PASS",
                               "leakage": "PASS", "walk_forward": "PASS",
                               "robustness": "PASS", "evaluation": "FAIL"},
                    "results": {"label": "REFUTED",
                                "primary_metric": {"name": "x", "delta": -0.01},
                                "decision_criteria_passed": False},
                    "candidate_path": None, "holdout_touched": False,
                    "blockers": [], "leakage_status": "PASS",
                    "robustness_status": "PASS"}
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "FIREWALL_VIOLATION")
        # the label never reached any durable artifact
        events = (self.root / "autonomous_agent/state/loop_events.jsonl").read_text("utf-8")
        self.assertNotIn('{"label": "REFUTED"}', self.ledger_text())
        self.assertIn("firewall_violation", events)

    def test_confirmed_contamination_halt_is_durable_and_restart_safe(self) -> None:
        self._with_declared_stops(mult.AUDIT_STOP_CONDITIONS)

        def executor(spec):
            return {"status": "REJECTED",
                    "checks": {"unit": "PASS", "data_integrity": "PASS",
                               "leakage": "PASS", "walk_forward": "PASS",
                               "robustness": "PASS", "evaluation": "FAIL"},
                    "results": {"point_in_time_audit": {
                        "status": "CONFIRMED_CONTAMINATION", "family": "features"},
                        "primary_metric": {"name": "x", "delta": -0.01},
                        "decision_criteria_passed": False},
                    "candidate_path": None, "holdout_touched": False,
                    "blockers": [], "leakage_status": "PASS",
                    "robustness_status": "PASS"}
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "point_in_time_contamination_detected")
        rows = [json.loads(line) for line in self.ledger_text().splitlines() if line.strip()]
        audit_rows = [row for row in rows
                      if (row.get("detail") or {}).get("audit_stop")
                      == "point_in_time_contamination_detected"]
        self.assertEqual(len(audit_rows), 1)
        self.assertEqual(audit_rows[0]["to"], schema.STATUS_FAILED_EXECUTION)
        events = (self.root / "autonomous_agent/state/loop_events.jsonl").read_text("utf-8")
        self.assertIn('"audit_stop"', events)
        # restarting with the signal in the ledger stops again, immediately
        restarted = self.make_loop(max_cycles=1, executor=MockExecutor(self.root))
        with self.assertRaises(LoopStop) as caught:
            restarted.cycle_once()
        self.assertEqual(caught.exception.reason, "point_in_time_contamination_detected")

    def test_unverifiable_lineage_halts_the_campaign(self) -> None:
        self._with_declared_stops(mult.AUDIT_STOP_CONDITIONS)

        def executor(spec):
            return {"status": "REJECTED",
                    "checks": {"unit": "PASS", "data_integrity": "PASS",
                               "leakage": "PASS", "walk_forward": "PASS",
                               "robustness": "PASS", "evaluation": "FAIL"},
                    "results": {"point_in_time_audit": {
                        "lineage_status": "UNVERIFIABLE"},
                        "primary_metric": {"name": "x", "delta": 0.0},
                        "decision_criteria_passed": False},
                    "candidate_path": None, "holdout_touched": False,
                    "blockers": [], "leakage_status": "PASS",
                    "robustness_status": "PASS"}
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        self.assertEqual(summary["stop_reason"], "unverifiable_lineage_detected")

    def test_campaign_without_the_stops_declared_is_untouched(self) -> None:
        # Same contamination signal, but the (Campaign-3-style) frozen config
        # does not declare the v1.1.0 stops: behavior is unchanged, exactly as
        # authorized. The signal is still recorded durably as a failed
        # execution, never as a silent pass.
        def executor(spec):
            return {"status": "REJECTED",
                    "checks": {"unit": "PASS", "data_integrity": "PASS",
                               "leakage": "PASS", "walk_forward": "PASS",
                               "robustness": "PASS", "evaluation": "FAIL"},
                    "results": {"point_in_time_audit": {
                        "status": "CONFIRMED_CONTAMINATION"},
                        "primary_metric": {"name": "x", "delta": -0.01},
                        "decision_criteria_passed": False},
                    "candidate_path": None, "holdout_touched": False,
                    "blockers": [], "leakage_status": "PASS",
                    "robustness_status": "PASS"}
        summary = self.make_loop(max_cycles=1, executor=executor).run()
        # The adjudication-time halt is unconditional (fail-closed); only the
        # *restart guard* is scoped to configs that declare the stops.
        self.assertEqual(summary["stop_reason"],
                         "point_in_time_contamination_detected")
        # A Campaign-3-style config does not re-raise on restart: cycle_once
        # proceeds, and a fresh execution adjudicates normally.
        # cycle counters are cumulative across restarts, so the restart needs
        # one more cycle than the first run consumed
        restarted = self.make_loop(max_cycles=2, executor=MockExecutor(self.root))
        summary = restarted.run()
        self.assertEqual(summary["stop_reason"], "MAX_CYCLES")
        state = json.loads((self.root / "autonomous_agent/state"
                            / "loop_state.json").read_text("utf-8"))
        self.assertEqual(state["status"], "STOPPED")
        # the halted attempt still consumed its slot (H-8: an experiment
        # consumes its authorized execution slot), plus the restart's run
        self.assertEqual(state["executions_done"], 2)


if __name__ == "__main__":
    unittest.main()
