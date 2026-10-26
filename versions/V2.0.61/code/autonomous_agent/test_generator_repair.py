"""Regression tests for the 2026-10-15 Campaign 4 generator repair.

Owner directive: "Campaign 4 - Repair Proposal Exhaustion and Resume
Execution". Three coordinated defects were repaired:

1. **Doomed creations.** The generator ranked and created candidates the
   BiasGovernor would certainly refuse at validation (BIAS_QUOTA: while the
   falsification share is below the floor, only falsification-class
   proposals may be accepted). Refusals consume permanent direction/class
   budget by design, so doomed creations destroyed campaign capacity -
   Campaign 4 lost 24 of 26 proposal slots to refusals that were provable
   at creation time. The generator now projects the post-creation quota
   state and runs the governor's own ``check_accept`` before a candidate is
   ever ranked (in ``_build_candidates``) and again cumulatively during
   cycle selection (in ``generate_proposals``), mirroring exactly what
   validation will do.

2. **Unreachable falsification framing.** ``regime_split_analysis`` and
   ``target_horizon_robustness`` declared ``falsification_capable=True``
   but shipped with ``default_class="exploration"``, and
   ``_OPPOSITE_CLASS`` maps exploration->exploration, so the falsification
   framing was structurally unreachable - contradicting the reviewed
   ``HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`` table, which
   assigns both primitives class ``falsification``. Their semantics
   support the framing (frozen IUT ladders whose failing cell refutes;
   regime/horizon families feed the campaign-end Holm refutation test).

3. **Exhausted signature space.** The ``n_boot`` grid only ever emitted
   the reviewed s (500) and m (1000) buckets; the schema's own
   ``bucket_n_boot`` defines l (2000) as design-identity-significant.
   Adding that one in-bounds grid point completes the reviewed bucket
   vocabulary and restores legitimate never-asked signatures without any
   new config key, code path, gate, or threshold.

The tests below pin each repair AND prove the surrounding invariants are
unchanged: asked-signature memory, permanent refusal accounting, budget
limits, recipe exclusions, the honest PROPOSAL_EXHAUSTED stop, and the
frozen policy/gates. Live-state preservation of prior adjudications is
pinned in ``test_freeze_integrity.py``.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from autonomous_agent.continuous_loop import ResearchLoop
from autonomous_agent.proposal_layer import generator, schema
from autonomous_agent.proposal_layer.primitives import get as get_primitive
from autonomous_agent.test_continuous_loop import MockExecutor
from autonomous_agent.test_freeze_integrity import _complete_champion
from autonomous_agent.test_proposal_layer import FIXED_CLOCK, base_policy, build_fixture
from autonomous_agent.test_stage2_campaign import write_campaign


def _view(asked=(), recipe_attempts=(), direction_stats=None):
    """Minimal evidence view consumed by the generator's scheduler."""
    return {
        "already_asked": [
            {"proposal_class": cls, "direction": direction,
             "design_signature": signature, "fingerprint": "fp-" + signature[:16],
             "campaign_id": None, "hypothesis": hypothesis}
            for (signature, cls, direction, hypothesis) in asked
        ],
        "recipe_attempts": list(recipe_attempts),
        "direction_stats": dict(direction_stats or {}),
    }


def _build(view, policy):
    stats: dict = {}
    candidates = generator._build_candidates(
        view, policy, generator.BiasGovernor(policy), stats=stats)
    return candidates, stats


class PreCreationGovernorGuardTests(unittest.TestCase):
    """(1) Provably inadmissible candidates are rejected before creation."""

    FLOOR = 0.35

    def _floor_policy(self, **overrides):
        return base_policy(min_falsification_share=self.FLOOR, **overrides)

    def test_share_floor_blocks_every_non_falsification_candidate(self) -> None:
        policy = self._floor_policy()
        candidates, stats = _build(_view(), policy)
        self.assertTrue(candidates)                 # admissible ones exist
        self.assertTrue(all(c["proposal_class"] == "falsification"
                            for c in candidates),
                        sorted({c["proposal_class"] for c in candidates}))
        # The blocked framings are accounted for, with the governor's own
        # reason code - nothing is silently dropped.
        self.assertGreater(stats["excluded_governor_inadmissible"], 0)
        self.assertEqual(stats["excluded_governor_reasons"], ["BIAS_QUOTA"])

    def test_generate_proposals_never_returns_a_doomed_class(self) -> None:
        policy = self._floor_policy()
        payloads = generator.generate_proposals(_view(), policy, seed=1, limit=10)
        self.assertTrue(payloads)
        self.assertTrue(all(p["proposal_class"] == "falsification"
                            for p in payloads),
                        sorted({p["proposal_class"] for p in payloads}))

    def test_guard_refuses_exactly_what_validation_refuses(self) -> None:
        # Build the payload the OLD generator would have created and prove
        # the governor refuses it at validation with the same reason code
        # the guard now uses - the guard is not stricter or looser than the
        # gate it mirrors.
        view = _view()
        policy = self._floor_policy()
        payload = generator.payload_for(
            view, "feature_arm_comparison",
            {"arm_pair": "A->B", "estimator": "LightGBM", "n_boot": 500},
            "confirmatory")
        state = generator._project_quota_state(
            {"total": 0, "by_direction": {}, "by_class": {}, "by_signature": {}},
            direction=payload["direction"], proposal_class=payload["proposal_class"],
            signature=payload["design_signature"])
        ok, reason, detail = generator.BiasGovernor(policy).check_accept(payload, state)
        self.assertFalse(ok)
        self.assertEqual(reason, schema.RC_BIAS_QUOTA)
        self.assertIn("falsification share", detail)
        # ...and the generator never emitted that class under this policy.
        emitted = {p["proposal_class"] for p in
                   generator.generate_proposals(view, policy, seed=7, limit=10)}
        self.assertNotIn("confirmatory", emitted)

    def test_replication_share_cap_is_guarded_too(self) -> None:
        # A second hard governor constraint: replication over its share cap
        # is refused pre-creation as well (floor relaxed to isolate it).
        policy = base_policy(min_falsification_share=0.0,
                             max_replication_share=0.0)
        payloads = generator.generate_proposals(_view(), policy, seed=1, limit=10)
        self.assertTrue(payloads)
        self.assertNotIn("replication",
                         {p["proposal_class"] for p in payloads})
        _, stats = _build(_view(), policy)
        self.assertIn("BIAS_QUOTA", stats["excluded_governor_reasons"])

    def test_selection_projects_cumulatively_within_one_cycle(self) -> None:
        # Base state: 11 falsification / 30 total = 0.3667. Without any
        # falsification candidate left to refill the share, the FIRST
        # non-falsification record (11/31 = 0.3548) is admissible and every
        # subsequent one would be refused (11/32 = 0.3438 < 0.35). The old
        # generator would have created up to 10 doomed records here; the
        # cumulative running-state mirror must select at most ONE.
        asked = [(f"fake-fals-{i:02d}" * 4, "falsification",
                  "calibration", f"prior fals {i}") for i in range(11)] + \
                [(f"fake-conf-{i:02d}" * 4, "confirmatory",
                  "calibration", f"prior conf {i}") for i in range(19)]
        policy = base_policy(
            min_falsification_share=0.35, max_total_proposals=60,
            max_per_direction=40,
            class_budgets={"confirmatory": 25, "falsification": 11,
                           "replication": 2, "exploration": 2})
        payloads = generator.generate_proposals(_view(asked=asked), policy,
                                                seed=1, limit=10)
        self.assertLessEqual(len(payloads), 1, [p["proposal_class"]
                                                for p in payloads])

    def test_every_emitted_sequence_replays_as_validation_pass(self) -> None:
        # The mirror invariant, on a mixed sequence where falsification
        # refill keeps the share afloat: replaying creation exactly as
        # validation will see it (base + each record in order) must pass
        # check_accept at every step. If generation and validation ever
        # disagree, this fails.
        asked = [(f"fake-fals-{i:02d}" * 4, "falsification",
                  "calibration", f"prior fals {i}") for i in range(11)] + \
                [(f"fake-conf-{i:02d}" * 4, "confirmatory",
                  "calibration", f"prior conf {i}") for i in range(19)]
        policy = base_policy(
            min_falsification_share=0.35, max_total_proposals=60,
            max_per_direction=40,
            class_budgets={"confirmatory": 25, "falsification": 40,
                           "replication": 2, "exploration": 2})
        view = _view(asked=asked)
        payloads = generator.generate_proposals(view, policy, seed=1, limit=10)
        self.assertTrue(payloads)
        governor = generator.BiasGovernor(policy)
        state = generator.capacity(view, policy)["state"]
        for payload in payloads:
            projected = generator._project_quota_state(
                state, direction=payload["direction"],
                proposal_class=payload["proposal_class"],
                signature=payload["design_signature"])
            ok, reason, detail = governor.check_accept(payload, projected)
            self.assertTrue(ok, (payload["proposal_class"], reason, detail))
            state = projected


class FramingCorrectionTests(unittest.TestCase):
    """(2) falsification_capable primitives can frame falsification - only
    where the reviewed plan and the semantics support it."""

    def test_reviewed_plan_classes_are_reachable(self) -> None:
        for primitive_id in ("regime_split_analysis", "target_horizon_robustness"):
            primitive = get_primitive(primitive_id)
            # The reviewed plan table (HARNESS_V1_1_0_IMPLEMENTATION_PLAN,
            # pinned 094827b0) assigns these the falsification class.
            self.assertEqual(primitive.default_class, "falsification",
                             primitive_id)
            self.assertTrue(primitive.falsification_capable, primitive_id)
            self.assertEqual(
                generator._framed_classes(primitive),
                ("falsification", "confirmatory"), primitive_id)

    def test_no_blind_relabel_of_non_capable_or_neutral_classes(self) -> None:
        # The repair must not relabel exploration as falsification wholesale.
        point_in_time = get_primitive("point_in_time_data_audit")
        self.assertFalse(point_in_time.falsification_capable)
        self.assertEqual(generator._framed_classes(point_in_time),
                         ("exploration",))
        replication = get_primitive("seed_set_replication")
        self.assertFalse(replication.falsification_capable)
        self.assertEqual(generator._framed_classes(replication), ("replication",))
        # The opposite-class table itself is untouched.
        self.assertEqual(generator._OPPOSITE_CLASS, {
            "confirmatory": "falsification",
            "falsification": "confirmatory",
            "replication": "replication",
            "exploration": "exploration",
        })

    def test_admissible_falsification_candidate_exists_when_space_allows(self) -> None:
        policy = base_policy(min_falsification_share=0.35)
        candidates, _ = _build(_view(), policy)
        regime = [c for c in candidates
                  if c["primitive_id"] == "regime_split_analysis"
                  and c["proposal_class"] == "falsification"]
        horizon = [c for c in candidates
                   if c["primitive_id"] == "target_horizon_robustness"
                   and c["proposal_class"] == "falsification"]
        self.assertTrue(regime, "regime-split must offer a falsification candidate")
        self.assertTrue(horizon, "horizon must offer a falsification candidate")

    def test_falsification_rule_payload_is_constructed_for_framing(self) -> None:
        view = _view()
        payload = generator.payload_for(
            view, "regime_split_analysis", {"arm": "B", "n_boot": 1000},
            "falsification")
        rule = payload["falsification_rule"]
        self.assertEqual(rule["metric"], "pooled_roc_auc_delta")
        self.assertEqual(rule["comparator"], "<")
        self.assertEqual(rule["threshold"], 0.0)
        self.assertIn(rule["metric"], schema.FALSIFICATION_METRICS)
        self.assertIn("Falsifier", payload["hypothesis"])


class EnforcementPreservedTests(unittest.TestCase):
    """(3) Asked memory, refusal accounting, budgets, recipe exclusions."""

    ASKED_SIG = schema.design_signature(
        primitive_ids=("feature_arm_comparison",),
        params={"arm_pair": "A->B", "estimator": "LogisticRegression",
                "n_boot": 500})

    RECIPE_ROW = {"recipe_id": "feature_arm_nested_ablation",
                  "selected_parameters": {"arm_pair": "C->D",
                                          "estimator": "LightGBM",
                                          "n_boot": 1000}}
    RECIPE_SIG = schema.signature_from_recipe_attempt(
        RECIPE_ROW["recipe_id"], RECIPE_ROW["selected_parameters"])

    def test_asked_signatures_are_never_regenerated(self) -> None:
        # The asked entry is exactly what a (refused or executed) ledger
        # record produces in the evidence view: permanent memory.
        view = _view(asked=[(self.ASKED_SIG, "confirmatory",
                             "feature_engineering", "prior hypothesis")])
        policy = base_policy(min_falsification_share=0.35)
        candidates, stats = _build(view, policy)
        self.assertNotIn(self.ASKED_SIG,
                         {c["design_signature"] for c in candidates})
        self.assertGreaterEqual(stats["excluded_asked_signatures"], 1)
        payloads = generator.generate_proposals(view, policy, seed=3, limit=10)
        self.assertNotIn(self.ASKED_SIG,
                         {p["design_signature"] for p in payloads})

    def test_recipe_exclusions_are_preserved(self) -> None:
        view = _view(recipe_attempts=[self.RECIPE_ROW])
        policy = base_policy(min_falsification_share=0.35)
        candidates, stats = _build(view, policy)
        self.assertNotIn(self.RECIPE_SIG,
                         {c["design_signature"] for c in candidates})
        self.assertGreaterEqual(stats["excluded_recipe_signatures"], 1)

    def test_exhausted_direction_budget_still_excludes(self) -> None:
        # Four asked records in feature_engineering == max_per_direction:
        # the direction is excluded even though its grid has free cells.
        asked = [
            (schema.design_signature(
                primitive_ids=("feature_arm_comparison",), params=params),
             "falsification", "feature_engineering", f"prior {i}")
            for i, params in enumerate([
                {"arm_pair": "A->B", "estimator": "LogisticRegression", "n_boot": 500},
                {"arm_pair": "A->B", "estimator": "LogisticRegression", "n_boot": 1000},
                {"arm_pair": "B->C", "estimator": "LightGBM", "n_boot": 500},
                {"arm_pair": "B->C", "estimator": "LightGBM", "n_boot": 1000},
            ])
        ]
        view = _view(asked=asked)
        policy = base_policy(min_falsification_share=0.35, max_per_direction=4)
        cap = generator.capacity(view, policy)
        self.assertEqual(cap["remaining_by_direction"]["feature_engineering"], 0)
        candidates, stats = _build(view, policy)
        self.assertIn("feature_engineering", stats["excluded_exhausted_directions"])
        self.assertTrue(all(c["direction"] != "feature_engineering"
                            for c in candidates))

    def test_total_budget_and_signature_cap_still_enforce(self) -> None:
        policy = base_policy(min_falsification_share=0.35,
                             max_total_proposals=0)
        candidates, stats = _build(_view(), policy)
        self.assertEqual(candidates, [])
        self.assertTrue(stats["excluded_total_budget"])
        # Signature cap accounting still counts asked uses.
        policy2 = base_policy(min_falsification_share=0.35, max_signature_count=2)
        cap = generator.capacity(
            _view(asked=[(self.ASKED_SIG, "confirmatory",
                          "feature_engineering", "prior")]), policy2)
        self.assertEqual(cap["state"]["by_signature"][self.ASKED_SIG], 1)

    def test_class_budget_exclusion_still_applies_before_the_guard(self) -> None:
        policy = base_policy(min_falsification_share=0.35,
                             class_budgets={"confirmatory": 0, "falsification": 8,
                                            "replication": 1, "exploration": 0})
        candidates, stats = _build(_view(), policy)
        # Exploration cannot frame falsification (not relabelled), and its
        # budget is zero -> excluded by the budget rule, not the guard.
        self.assertTrue(candidates)
        self.assertTrue(all(c["proposal_class"] == "falsification"
                            for c in candidates))
        self.assertIn("exploration", stats["excluded_exhausted_classes"])
        self.assertIn("confirmatory", stats["excluded_exhausted_classes"])


class HonestExhaustionTests(unittest.TestCase):
    """(4) With no admissible candidate the loop still stops honestly."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="generator_repair_"))
        self.root = self.tmp / "ws"
        self.root.mkdir(parents=True)
        build_fixture(self.root)
        _complete_champion(self.root)
        # Direction restricted to data_quality: its only primitive
        # (point_in_time_data_audit) is not falsification_capable, so under
        # the real 0.35 share floor no admissible candidate can exist - the
        # exact Campaign-4 production failure mode, hermetically.
        overrides = {
            "campaign_id": "stage-2-unit",
            "max_total_proposals": 8,
            "max_per_direction": 2,
            "max_signature_count": 2,
            "min_falsification_share": 0.35,
            "max_replication_share": 0.5,
            "class_budgets": {"confirmatory": 4, "falsification": 4,
                              "replication": 1, "exploration": 1},
            "max_proposals_per_cycle": 3,
            "require_human_approval": False,
            "directions": ["data_quality"],
        }
        write_campaign(self.root, policy_overrides=overrides)
        self.ledger_path = (self.root /
                            "autonomous_agent/state/proposal_ledger.jsonl")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_share_floor_with_no_falsification_option_stops_honestly(self) -> None:
        executor = MockExecutor(self.root)
        summary = ResearchLoop(
            self.root, max_cycles=3, executor=executor, clock=FIXED_CLOCK).run()
        self.assertEqual(summary["stop_reason"], "PROPOSAL_EXHAUSTED")
        self.assertEqual(summary["executions_done"], 0)
        self.assertEqual(executor.calls, [])       # nothing executed
        # No proposal record was ever created (the guard starved generation,
        # the loop reported exhaustion instead of churning doomed records).
        if self.ledger_path.exists():
            rows = [json.loads(line) for line in
                    self.ledger_path.read_text("utf-8").splitlines() if line.strip()]
            self.assertEqual(
                [r for r in rows if r.get("row_type") == "proposal"], [])
        # And the scheduler agrees the pool is empty.
        loop = ResearchLoop(self.root, max_cycles=1, executor=executor,
                            clock=FIXED_CLOCK)
        report = loop.exhaustion_report()
        self.assertTrue(report["scheduler_exhausted"])
        self.assertEqual(report["candidates_remaining"], 0)

    def test_budget_only_exhaustion_is_still_reported_as_exhausted(self) -> None:
        # Guards must not swallow the other honest stop: total budget at
        # zero still yields PROPOSAL_EXHAUSTED with no executions.
        overrides = {
            "campaign_id": "stage-2-unit",
            "max_total_proposals": 0,
            "max_per_direction": 2,
            "max_signature_count": 2,
            "min_falsification_share": 0.35,
            "max_replication_share": 0.5,
            "class_budgets": {"confirmatory": 4, "falsification": 4,
                              "replication": 1, "exploration": 1},
            "max_proposals_per_cycle": 3,
            "require_human_approval": False,
        }
        write_campaign(self.root, policy_overrides=overrides)
        executor = MockExecutor(self.root)
        summary = ResearchLoop(
            self.root, max_cycles=2, executor=executor, clock=FIXED_CLOCK).run()
        self.assertEqual(summary["stop_reason"], "PROPOSAL_EXHAUSTED")
        self.assertEqual(executor.calls, [])


class CandidateSpaceExpansionTests(unittest.TestCase):
    """(3b) The one grid addition stays inside every declared bound."""

    def test_grid_point_is_inside_every_declared_paramspec(self) -> None:
        # The grid intersects each primitive's declared bounds, so every
        # value it can actually emit must satisfy that primitive's spec
        # (a global candidate outside one primitive's floor, e.g. 500 for
        # the H-10b n_boot >= 1000 primitives, is filtered by _param_grid).
        for primitive in generator.LIBRARY:
            for combo in generator._param_grid(primitive):
                for key, value in combo.items():
                    spec = primitive.params[key]
                    self.assertTrue(
                        spec.check(value),
                        f"{primitive.primitive_id} grid emits {key}={value} "
                        f"outside its declared spec")
        # And the new point itself is inside every n_boot bound that could
        # receive it (in-range filter yields at least the declared low).
        for primitive in generator.LIBRARY:
            spec = primitive.params.get("n_boot")
            if spec is None or spec.kind != "int":
                continue
            emitted = [combo["n_boot"] for combo in generator._param_grid(primitive)]
            self.assertTrue(emitted, primitive.primitive_id)
            if spec.low <= 2000 <= spec.high:
                self.assertIn(2000, emitted, primitive.primitive_id)

    def test_n_boot_buckets_remain_distinct_signatures(self) -> None:
        # 500=s, 1000=m, 2000=l: three distinct design identities, no
        # silent in-bucket duplication inside the grid.
        buckets = [schema.bucket_n_boot(v)
                   for v in generator.GRID_INT_CANDIDATES["n_boot"]]
        self.assertEqual(len(buckets), len(set(buckets)))

    def test_family_floor_still_holds_for_the_new_grid_point(self) -> None:
        # H-10b: family-feeding primitives require n_boot >= 1000; the new
        # point (2000) satisfies it and the ParamSpec floor still rejects
        # 500 for those primitives at the spec level.
        from autonomous_agent.proposal_layer import primitives as prims
        for primitive in prims.LIBRARY:
            spec = primitive.params.get("n_boot")
            if spec is None:
                continue
            if spec.low >= 1000:
                self.assertFalse(spec.check(500), primitive.primitive_id)
                self.assertTrue(spec.check(2000), primitive.primitive_id)


if __name__ == "__main__":
    unittest.main()
