"""Measurement identity of a candidate (structural; never reads outcomes).

Two candidates with the same measurement key evaluate the same arms with the
same estimators, seeds, folds and baseline, so they produce the same per-seed
pooled OOF AUCs. Running both spends two budget slots on one piece of evidence.

Excluded from the key, because they change only the *decision* on the
measured evidence, never the measured AUC:
  * ``n_boot``            (bootstrap confidence interval only),
  * ``calibration_bins``  (Brier / ECE only),
  * ``evaluation_criteria`` thresholds (acceptance decision only),
  * the hypothesis text.

The mirror of the rendered-config fields is pinned by a drift test that
compares this key with ``compiler._render_config`` for every grid candidate,
so the two can never silently diverge.

Validated 2026-10-17 against the 69 adjudicated Campaign 2-4 experiments: the
key partitions them exactly as the measured per-seed AUCs do (12 groups).
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from autonomous_agent.proposal_layer.primitives import Primitive

FOLDS: tuple[int, ...] = (2023, 2024, 2025)
DEFAULT_SEEDS: tuple[int, ...] = (42, 43, 44)


def measurement_key(primitive: Primitive, params: Mapping[str, Any],
                    baseline_id: str = "") -> tuple:
    """Return the measured-evidence identity of one candidate.

    Mirrors ``compiler._render_v110_config`` and ``compiler._render_config``:
    ``arm_pair`` unpacks into two arms with one shared estimator; ``arm``
    gives the same arm on both sides with LogisticRegression vs LightGBM.
    A candidate with neither parameter is never merged with another, so the
    key stays conservative (no false duplicate).
    """
    extra = dict(getattr(primitive, "extra", None) or {})
    seeds = tuple(int(seed) for seed in (extra.get("seeds") or DEFAULT_SEEDS))
    if "arm_pair" in params:
        arm_a, arm_b = str(params["arm_pair"]).split("->", 1)
        estimator_a = estimator_b = str(params.get("estimator", "LightGBM"))
    elif "arm" in params or primitive.harness_min_version == "1.1.0":
        arm_a = arm_b = str(params.get("arm", "A"))
        estimator_a, estimator_b = "LogisticRegression", "LightGBM"
    else:
        return ("unkeyed", primitive.primitive_id,
                json.dumps(dict(params), sort_keys=True))
    return (arm_a, arm_b, estimator_a, estimator_b, seeds, FOLDS,
            str(baseline_id))
