"""Development-only expanded predictive search space and novelty classifier.

Why atoms, not keys.  A measurement key (``evidence_key.measurement_key``)
names one *comparison*: two arms, two estimators, seeds, folds, baseline.
The harness computes each side of a comparison from that arm's own features
and estimator only (``recipe_harness._run_pooled``: ``score_a`` depends on
``features_a``/``estimator_a`` and the folds; the fits are deterministic and
seeds only resample out-of-fold rows). So the predictive evidence atom is
one arm under one estimator::

    atom = (arm, estimator, seeds, folds, baseline_id)

A comparison's AUC pair is fully determined by its two atoms. Consequently:

* ``B->A`` is the same evidence as ``A->B`` with the sign of the delta flipped
  (``delta_auc = auc_b - auc_a``), so the two must share one identity.
* A skip pair such as ``A->C`` adds no AUC evidence when both of its atoms
  were already measured. It is a new *decision question* on old evidence.
* Only a new atom (for example a new seed set) produces new predictive
  evidence within the frozen feature arms, estimators and folds.

Novelty is therefore classified as one of:

``MEASURED``            the exact key has been measured.
``REVERSED_DUPLICATE``  same evidence as a measured key, opposite direction.
``RECOMBINATION_ONLY``  new key, but every atom is already measured.
``NEW_EVIDENCE``        at least one atom has never been measured.

Nothing here reads outcomes, and nothing here is wired into production.
"""
from __future__ import annotations

from typing import Iterable, Mapping

from autonomous_agent.recipe_harness import ALLOWED_ARMS, ALLOWED_ESTIMATORS

FOLDS: tuple[int, ...] = (2023, 2024, 2025)
DEFAULT_SEEDS: tuple[int, ...] = (42, 43, 44)
# Replication seed set used by the seed_set_replication primitive; the only
# seed set whose atoms are not already measured in the frozen history.
REPLICATION_SEEDS: tuple[int, ...] = (7, 17, 29)

MEASURED = "MEASURED"
REVERSED_DUPLICATE = "REVERSED_DUPLICATE"
RECOMBINATION_ONLY = "RECOMBINATION_ONLY"
NEW_EVIDENCE = "NEW_EVIDENCE"

Key = tuple  # (arm_a, arm_b, est_a, est_b, seeds, folds, baseline_id)


def _validate_key(key: Key) -> None:
    if not isinstance(key, tuple) or len(key) != 7:
        raise ValueError(f"measurement key must be a 7-tuple, got {key!r}")
    arm_a, arm_b, est_a, est_b = key[:4]
    if arm_a not in ALLOWED_ARMS or arm_b not in ALLOWED_ARMS:
        raise ValueError(f"unknown arm in key: {arm_a!r}, {arm_b!r}")
    if est_a not in ALLOWED_ESTIMATORS or est_b not in ALLOWED_ESTIMATORS:
        raise ValueError(f"unknown estimator in key: {est_a!r}, {est_b!r}")


def atoms(key: Key) -> frozenset:
    """The arm-level evidence atoms a comparison depends on."""
    _validate_key(key)
    arm_a, arm_b, est_a, est_b, seeds, folds, baseline = key
    return frozenset({(arm_a, est_a, seeds, folds, baseline),
                      (arm_b, est_b, seeds, folds, baseline)})


def canonical_key(key: Key) -> Key:
    """Direction-free evidence identity: ``B->A`` and ``A->B`` coincide."""
    _validate_key(key)
    arm_a, arm_b, est_a, est_b, seeds, folds, baseline = key
    if (arm_b, est_b) < (arm_a, est_a):
        arm_a, arm_b, est_a, est_b = arm_b, arm_a, est_b, est_a
    return (arm_a, arm_b, est_a, est_b, seeds, folds, baseline)


def classify(key: Key, measured: Iterable[Key]) -> tuple[str, tuple]:
    """Return ``(status, new_atoms)`` for ``key`` against measured keys."""
    measured = [tuple(m) for m in measured]
    if tuple(key) in measured:
        return MEASURED, ()
    canon = canonical_key(key)
    if any(canonical_key(m) == canon for m in measured):
        return REVERSED_DUPLICATE, ()
    measured_atoms: set = set()
    for m in measured:
        measured_atoms |= atoms(m)
    new = tuple(sorted(atoms(key) - measured_atoms))
    if not new:
        return RECOMBINATION_ONLY, ()
    return NEW_EVIDENCE, new


def expanded_pairs() -> list[tuple[str, str]]:
    """All ordered arm pairs over the harness's closed arm set.

    The production library admits only the three adjacent forward pairs
    (A->B, B->C, C->D); this development list lifts that restriction.
    """
    return [(a, b) for a in ALLOWED_ARMS for b in ALLOWED_ARMS if a != b]


def expanded_keys(baseline_id: str,
                  seed_sets: Iterable[tuple[int, ...]] = (DEFAULT_SEEDS, REPLICATION_SEEDS)
                  ) -> list[Key]:
    """Every expanded comparison key (raw, before direction dedup).

    Pair keys share one estimator on both sides, as the production renderer
    does for ``arm_pair``. Arm-only keys compare one arm under both estimators,
    as the production renderer does for ``arm``.
    """
    keys: list[Key] = []
    for seeds in seed_sets:
        seeds = tuple(seeds)
        for arm_a, arm_b in expanded_pairs():
            for estimator in ALLOWED_ESTIMATORS:
                keys.append((arm_a, arm_b, estimator, estimator, seeds, FOLDS,
                             baseline_id))
        for arm in ALLOWED_ARMS:
            keys.append((arm, arm, "LogisticRegression", "LightGBM", seeds, FOLDS,
                         baseline_id))
    return keys


def distinct_evidence(keys: Iterable[Key]) -> list[Key]:
    """Collapse keys to their direction-free evidence identity, in order."""
    seen: dict[Key, None] = {}
    for key in keys:
        seen.setdefault(canonical_key(key), None)
    return list(seen)


def arm_pair_enum_problems(pair: str, enum: Iterable[str]) -> list[str]:
    """Explain why a pair is outside a frozen enum (for audit output)."""
    if pair in set(enum):
        return []
    return [f"arm_pair {pair!r} is outside the frozen library enum"]


def harness_contract_problems(base_config: Mapping, arm_a: str, arm_b: str,
                              estimator: str) -> list[str]:
    """Validate an expanded comparison against the real harness contract.

    ``base_config`` must be a config rendered by the production compiler for a
    legal candidate. Only the comparison fields are substituted, so the result
    tests the expanded pair against ``validate_experiment_config`` itself.
    """
    from autonomous_agent.recipe_harness import validate_experiment_config

    config = dict(base_config)
    config.update({"arm_a": arm_a, "arm_b": arm_b,
                   "estimator_a": estimator, "estimator_b": estimator})
    return list(validate_experiment_config(config))
