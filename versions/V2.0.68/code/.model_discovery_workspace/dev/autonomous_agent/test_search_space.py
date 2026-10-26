"""Development tests for proposal_layer.search_space (no production changes)."""
from __future__ import annotations

import pytest

from autonomous_agent.proposal_layer import compiler, evidence_key, generator
from autonomous_agent.proposal_layer import search_space as ss
from autonomous_agent.proposal_layer.primitives import LIBRARY, validate_params

BASELINE = "BASELINE_RECONSTRUCTED_2026_10"
LR, LGBM = "LogisticRegression", "LightGBM"
DEFAULT = ss.DEFAULT_SEEDS
REPL = ss.REPLICATION_SEEDS


def _key(a, b, est, seeds=DEFAULT):
    return (a, b, est, est, tuple(seeds), ss.FOLDS, BASELINE)


def _measured_adjacent():
    """The frozen adjacent-pair keys (A->B, B->C, C->D) under both estimators.

    Their atoms cover every (arm, estimator) under the default seeds.
    """
    return [_key(a, b, e) for a, b in (("A", "B"), ("B", "C"), ("C", "D"))
            for e in (LR, LGBM)]


def _base_config():
    """A real production-rendered config for a legal legacy candidate."""
    for primitive in LIBRARY:
        if not primitive.executable:
            continue
        for params in generator._param_grid(primitive):
            if "arm_pair" in params:
                payload = {"research_question_id": "rq", "hypothesis": "h",
                           "baseline_id": BASELINE}
                return compiler._render_config(payload, primitive, dict(params))
    raise AssertionError("no arm_pair candidate in the production grid")


def test_reversed_pair_shares_evidence_identity():
    forward, reverse = _key("A", "B", LR), _key("B", "A", LR)
    assert ss.canonical_key(forward) == ss.canonical_key(reverse)
    assert ss.atoms(forward) == ss.atoms(reverse)
    status, new = ss.classify(reverse, [forward])
    assert status == ss.REVERSED_DUPLICATE and new == ()


def test_reversed_key_is_distinct_as_a_key_but_not_as_evidence():
    assert _key("A", "B", LR) != _key("B", "A", LR)
    assert len(ss.distinct_evidence([_key("A", "B", LR), _key("B", "A", LR)])) == 1


def test_measured_key_is_reported_as_measured():
    status, new = ss.classify(_key("B", "C", LR), _measured_adjacent())
    assert status == ss.MEASURED and new == ()


def test_skip_pairs_are_recombination_only_when_atoms_are_measured():
    for pair in (("A", "C"), ("A", "D"), ("B", "D")):
        for est in (LR, LGBM):
            status, new = ss.classify(_key(*pair, est), _measured_adjacent())
            assert status == ss.RECOMBINATION_ONLY, (pair, est)
            assert new == ()


def test_replication_seed_atoms_are_new_evidence():
    status, new = ss.classify(_key("B", "C", LR, REPL), _measured_adjacent())
    assert status == ss.NEW_EVIDENCE
    assert {atom[0] for atom in new} == {"B", "C"}
    assert all(atom[2] == REPL for atom in new)


def test_expanded_space_collapses_to_distinct_evidence():
    keys = ss.expanded_keys(BASELINE)
    # 12 ordered pairs x 2 estimators x 2 seed sets, plus 4 arm-only x 2 seed sets.
    assert len(keys) == 12 * 2 * 2 + 4 * 2
    # Direction collapses 12 ordered pairs to 6 unordered ones:
    # 6 x 2 estimators x 2 seed sets + 4 arm-only x 2 seed sets = 32.
    assert len(ss.distinct_evidence(keys)) == 6 * 2 * 2 + 4 * 2


def test_every_expanded_pair_passes_the_harness_contract():
    base = _base_config()
    for arm_a, arm_b in ss.expanded_pairs():
        for est in (LR, LGBM):
            problems = ss.harness_contract_problems(base, arm_a, arm_b, est)
            assert problems == [], (arm_a, arm_b, est, problems)


def test_unknown_arm_or_estimator_fails_the_harness_contract():
    base = _base_config()
    assert ss.harness_contract_problems(base, "E", "B", LGBM)
    assert ss.harness_contract_problems(base, "A", "B", "XGBoost")


def test_production_enum_still_refuses_skip_pairs():
    # Development expansion must not leak into production validation.
    primitive = next(p for p in LIBRARY if p.executable and any(
        "arm_pair" in params for params in generator._param_grid(p)))
    base = next(dict(x) for x in generator._param_grid(primitive) if "arm_pair" in x)
    assert validate_params(primitive.primitive_id, dict(base)) == []
    for pair in ("A->C", "A->D", "B->D", "B->A"):
        params = dict(base, arm_pair=pair)
        assert validate_params(primitive.primitive_id, params), pair


def test_canonical_identity_matches_real_renderer_for_grid_candidates():
    payload_base = {"research_question_id": "rq", "hypothesis": "h",
                    "baseline_id": BASELINE}
    checked = 0
    for primitive in LIBRARY:
        if not primitive.executable:
            continue
        for params in generator._param_grid(primitive):
            if "arm_pair" not in params:
                continue
            cfg = compiler._render_config(payload_base, primitive, dict(params))
            rendered = (cfg["arm_a"], cfg["arm_b"], cfg["estimator_a"],
                        cfg["estimator_b"], tuple(cfg["seeds"]),
                        tuple(cfg["folds"]), cfg["baseline_id"])
            mirrored = evidence_key.measurement_key(primitive, params, BASELINE)
            assert ss.canonical_key(mirrored) == ss.canonical_key(rendered)
            checked += 1
    assert checked > 0


@pytest.mark.parametrize("bad", [("A", "B"), ("A", "B", LR, LR, DEFAULT, ss.FOLDS)])
def test_malformed_keys_are_rejected(bad):
    with pytest.raises(ValueError):
        ss.atoms(bad)
    with pytest.raises(ValueError):
        ss.canonical_key(bad)


def test_unknown_arm_key_is_rejected():
    with pytest.raises(ValueError):
        ss.canonical_key(_key("A", "E", LR))
