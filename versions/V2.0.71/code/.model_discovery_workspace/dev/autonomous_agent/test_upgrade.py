"""Dev-only upgrade tests (not wired into production).

Covers: temporal leakage guard for outcome priors, replication cold-start cap
flag (default-off = legacy), and that the new generator options are inert when
disabled and reorder (never add) candidates when enabled.
"""
import json
import unittest
from pathlib import Path

from autonomous_agent.proposal_layer import evidence_view, generator
from autonomous_agent.proposal_layer import outcome_ranking as ork
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = json.loads((REPO_ROOT / "autonomous_agent/proposal_layer/bias_policy.json")
                    .read_text(encoding="utf-8"))


def obs(at, passed, direction="validation", primitive="g1"):
    return ork.Observation(at=at, direction=direction, proposal_class="experiment",
                           primitive_id=primitive, passed=passed)


class OutcomeRankingTests(unittest.TestCase):
    def test_future_observation_is_refused(self):
        history = [obs("2026-01-02", True), obs("2026-01-05", False)]
        with self.assertRaises(ork.LeakageError):
            ork.estimate(history, cutoff="2026-01-03", direction="validation",
                         primitive_id="g1")

    def test_known_before_excludes_cutoff_and_later(self):
        history = [obs("2026-01-01", True), obs("2026-01-03", False), obs("2026-01-04", True)]
        known = ork.known_before(history, "2026-01-03")
        self.assertEqual([o.at for o in known], ["2026-01-01"])

    def test_empty_history_returns_base_rate(self):
        est = ork.estimate([], cutoff="2026-01-01", direction="validation",
                           primitive_id="g1", base_rate=0.3)
        self.assertAlmostEqual(est.mean, 0.3)
        self.assertEqual(est.n_total, 0)

    def test_future_outcome_cannot_change_earlier_estimate(self):
        past = [obs("2026-01-01", True), obs("2026-01-02", True)]
        cutoff = "2026-01-03"
        before = ork.estimate(ork.known_before(past, cutoff), cutoff=cutoff,
                              direction="validation", primitive_id="g1")
        future = past + [obs("2026-01-09", False)]  # strictly after cutoff
        after = ork.estimate(ork.known_before(future, cutoff), cutoff=cutoff,
                             direction="validation", primitive_id="g1")
        self.assertEqual(before, after)

    def test_base_rate_must_be_interior(self):
        with self.assertRaises(ValueError):
            ork.estimate([], cutoff="2026-01-01", direction="d", primitive_id="g",
                         base_rate=1.0)

    def test_brier_validates_inputs(self):
        with self.assertRaises(ValueError):
            ork.brier([0.5], [True, False])
        self.assertAlmostEqual(ork.brier([1.0, 0.0], [True, False]), 0.0)


def _state(total, by_class, direction="validation", signature="s"):
    return {"total": total, "by_class": by_class,
            "by_direction": {direction: total},
            "by_signature": {signature: total}}


PROPOSAL = {"proposal_class": "replication", "direction": "validation",
            "design_signature": "s"}


class ReplicationColdStartTests(unittest.TestCase):
    def _gov(self, **extra):
        return BiasGovernor(dict(min_falsification_share=0.0, **extra))

    def test_legacy_default_refuses_first_replication(self):
        ok, reason, _ = self._gov().check_accept(PROPOSAL, _state(1, {"replication": 1}))
        self.assertFalse(ok)
        self.assertEqual(reason, "BIAS_QUOTA")

    def test_min_portfolio_flag_admits_cold_start(self):
        ok, _, _ = self._gov(replication_cap_min_portfolio=3).check_accept(
            PROPOSAL, _state(1, {"replication": 1}))
        self.assertTrue(ok)

    def test_min_portfolio_flag_still_enforces_cap_when_portfolio_grows(self):
        # Lift the budget caps so the replication share cap is the binding rule.
        gov = self._gov(replication_cap_min_portfolio=3, max_total_proposals=50,
                        max_per_direction=50, max_signature_count=50,
                        class_budgets={"replication": 50})
        ok, reason, _ = gov.check_accept(PROPOSAL, _state(5, {"replication": 5}))
        self.assertFalse(ok)
        self.assertEqual(reason, "BIAS_QUOTA")


class GeneratorOptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.view = evidence_view.build(REPO_ROOT, clock=lambda: "2026-10-17T00:00:00+00:00")

    def _policy(self, **extra):
        policy = dict(POLICY)
        policy.update({"campaign_id": "upgrade-test-2026-10-17"})
        policy.update(extra)
        return policy

    def _fps(self, policy, **kwargs):
        out = generator.generate_proposals(self.view, policy, seed=0, **kwargs)
        return [p["proposal_fingerprint"] for p in out]

    def test_disabled_options_match_legacy_output(self):
        legacy = self._fps(self._policy())
        same = self._fps(self._policy(outcome_ranking_weight=0.0,
                                      falsification_floor_vacuous_when_no_novel=False))
        self.assertEqual(legacy, same)

    def test_zero_weight_ignores_outcome_scores(self):
        legacy = self._fps(self._policy())
        scored = self._fps(self._policy(outcome_ranking_weight=0.0),
                           outcome_scores={"any_primitive": 1.0})
        self.assertEqual(legacy, scored)

    def test_outcome_bonus_reorders_but_only_within_admissible_set(self):
        policy = self._policy()
        legacy = generator.generate_proposals(self.view, policy, seed=0)
        self.assertTrue(legacy, "legacy generator returned no proposals on the real view")
        first = legacy[0]["design"]["primitives"][0]["primitive_id"]
        others = {p["design"]["primitives"][0]["primitive_id"] for p in legacy} - {first}
        self.assertTrue(others, "need a second primitive to test reordering")
        boosted = sorted(others)[0]
        boosted_policy = self._policy(outcome_ranking_weight=1000.0)
        scored = generator.generate_proposals(
            self.view, boosted_policy, seed=0,
            outcome_scores={boosted: 1.0, first: 0.0})
        self.assertEqual(scored[0]["design"]["primitives"][0]["primitive_id"], boosted)
        # Reordering never invents a candidate: every scored design signature
        # must belong to the legacy admissible set on the same view.
        admissible = {c["design_signature"] for c in generator._build_candidates(
            self.view, policy, BiasGovernor(policy))}
        for payload in scored:
            self.assertIn(payload["design_signature"], admissible)


if __name__ == "__main__":
    unittest.main()
