"""Tests for measurement-key deduplication (dev copy; not activated).

Covers: drift against the real config renderer, parameter invariance of the
key, exclusion of already-measured evidence, one-measurement-per-cycle, the
default (disabled) path, and fail-closed handling of malformed arm pairs.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from autonomous_agent.proposal_layer import compiler, generator, schema
from autonomous_agent.proposal_layer.evidence_key import measurement_key
from autonomous_agent.proposal_layer.primitives import LIBRARY, get

REPO_POLICY = Path(__file__).resolve().parent / "proposal_layer" / "bias_policy.json"
KEY_FIELDS = ("arm_a", "arm_b", "estimator_a", "estimator_b", "seeds", "folds", "baseline_id")


def _policy() -> dict:
    policy = json.loads(REPO_POLICY.read_text(encoding="utf-8"))
    policy["campaign_id"] = "test-campaign"
    policy["max_total_proposals"] = 64
    return policy


def _view(already_asked=None) -> dict:
    return {
        "champion": {"version": "V-test"},
        "baseline": {"baseline_id": "BASE-TEST"},
        "already_asked": list(already_asked or []),
        "recipe_attempts": [],
        "direction_stats": {},
        "sources": [],
    }


def _grid():
    for primitive in LIBRARY:
        if not primitive.executable:
            continue
        for params in generator._param_grid(primitive):
            yield primitive, params


def _key_from_config(cfg: dict) -> tuple:
    return (cfg["arm_a"], cfg["arm_b"], cfg["estimator_a"], cfg["estimator_b"],
            tuple(cfg["seeds"]), tuple(cfg["folds"]), cfg["baseline_id"])


class DriftAgainstRealRenderer(unittest.TestCase):
    """The mirror key must equal the key of the config the compiler renders."""

    def test_every_executable_grid_candidate_matches_the_renderer(self) -> None:
        compared = 0
        for primitive, params in _grid():
            payload = {"research_question_id": "rq-test", "hypothesis": "h",
                       "baseline_id": "BASE-TEST"}
            try:
                cfg = compiler._render_config(payload, primitive, dict(params))
            except compiler.CompileError:
                continue          # the renderer refuses it; nothing to match
            self.assertEqual(
                measurement_key(primitive, params, "BASE-TEST"),
                _key_from_config(cfg),
                f"{primitive.primitive_id} {params}")
            compared += 1
        self.assertGreater(compared, 0, "no candidate was compared with the renderer")


class KeyInvariance(unittest.TestCase):
    def test_threshold_and_bootstrap_variants_share_one_key(self) -> None:
        primitive = get("complexity_premium_check")
        keys = {measurement_key(primitive, {"arm": "A", "n_boot": n, "premium": p}, "B")
                for n in (500, 1000, 2000) for p in ("standard", "high")}
        self.assertEqual(len(keys), 1)

    def test_different_arms_give_different_keys(self) -> None:
        primitive = get("complexity_premium_check")
        a = measurement_key(primitive, {"arm": "A", "n_boot": 500, "premium": "high"}, "B")
        b = measurement_key(primitive, {"arm": "B", "n_boot": 500, "premium": "high"}, "B")
        self.assertNotEqual(a, b)


class DeduplicationBehaviour(unittest.TestCase):
    def test_measured_evidence_is_never_reproposed(self) -> None:
        primitive_keys = set()
        for primitive, params in _grid():
            primitive_keys.add(measurement_key(primitive, params, "BASE-TEST"))
        measured = set(list(primitive_keys)[: len(primitive_keys) // 2])
        payloads = generator.generate_proposals(
            _view(), _policy(), seed=0, limit=50, measured_keys=measured)
        for payload in payloads:
            primitive = get(payload["design"]["primitives"][0]["primitive_id"])
            key = measurement_key(primitive, payload["parameters"], "BASE-TEST")
            self.assertNotIn(key, measured)

    def test_one_measurement_per_cycle(self) -> None:
        payloads = generator.generate_proposals(
            _view(), _policy(), seed=0, limit=50, measured_keys=set())
        keys = []
        for payload in payloads:
            primitive = get(payload["design"]["primitives"][0]["primitive_id"])
            keys.append(measurement_key(primitive, payload["parameters"], "BASE-TEST"))
        self.assertEqual(len(keys), len(set(keys)))

    def test_disabled_path_is_unchanged_by_the_key(self) -> None:
        # measured_keys=None must not filter anything beyond the legacy rules.
        legacy = generator.generate_proposals(_view(), _policy(), seed=3, limit=3)
        again = generator.generate_proposals(_view(), _policy(), seed=3, limit=3,
                                             measured_keys=None)
        self.assertEqual(
            [p["proposal_fingerprint"] for p in legacy],
            [p["proposal_fingerprint"] for p in again])
        for payload in legacy:
            self.assertEqual(payload["proposal_fingerprint"],
                             schema.proposal_fingerprint(payload))


class FailClosed(unittest.TestCase):
    def test_malformed_arm_pair_is_rejected(self) -> None:
        primitive = get("model_class_comparison")
        with self.assertRaises(ValueError):
            measurement_key(primitive, {"arm_pair": "B-C", "n_boot": 1000}, "B")


if __name__ == "__main__":
    unittest.main()
