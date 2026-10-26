"""Development-only grouped outcome-ranking tests and as-of score helpers."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autonomous_agent.proposal_layer import outcome_ranking as ranking  # noqa: E402


def _obs(at, group, passed, direction="validation"):
    return ranking.Observation(at=at, direction=direction,
                               proposal_class="adjudicated",
                               primitive_id=group, passed=passed)


def test_duplicate_rows_for_one_group_do_not_inflate_effective_sample_size():
    single = [_obs("2026-01-01", "config-a", True)]
    repeated = [_obs(f"2026-01-{day:02d}", "config-a", True)
                for day in range(1, 10)]
    a = ranking.estimate(single, cutoff="2026-02-01", direction="validation",
                         primitive_id="config-a")
    b = ranking.estimate(repeated, cutoff="2026-02-01", direction="validation",
                         primitive_id="config-a")
    assert a == b
    assert (a.n_primitive, a.n_direction, a.n_total) == (1, 1, 1)


def test_group_vote_is_bounded_to_one_trial_even_when_labels_disagree():
    history = [_obs("2026-01-01", "config-a", True),
               _obs("2026-01-02", "config-a", False)]
    estimate = ranking.estimate(history, cutoff="2026-02-01", direction="validation",
                                primitive_id="config-a")
    assert estimate.n_primitive == estimate.n_direction == 1
    assert estimate.mean < 0.75


def test_non_boolean_missing_outcomes_fail_closed():
    with pytest.raises(ValueError, match="boolean"):
        ranking.estimate([_obs("2026-01-01", "missing", None)],
                         cutoff="2026-02-01", direction="validation",
                         primitive_id="missing")


def test_nonpositive_shrinkage_strength_fails_closed():
    with pytest.raises(ValueError, match="strength"):
        ranking.estimate([], cutoff="2026-02-01", direction="validation",
                         primitive_id="new", strength=0)


def test_uncertainty_bonus_explores_unseen_candidates_and_is_stable():
    history = [_obs("2026-01-01T00:00:00Z", "strong", True),
               _obs("2026-01-02T00:00:00Z", "strong", True),
               _obs("2026-01-03T00:00:00Z", "weak", False),
               _obs("2026-01-04T00:00:00Z", "weak", False)]
    cutoff = "2026-02-01T00:00:00Z"
    exploitation = ranking.rank_candidates(
        history, cutoff=cutoff, direction="validation",
        candidate_ids=["strong", "weak", "new"], exploration_weight=0.0)
    exploration = ranking.rank_candidates(
        history, cutoff=cutoff, direction="validation",
        candidate_ids=["strong", "weak", "new"], exploration_weight=1.0)
    assert exploitation[0]["candidate_id"] == "strong"
    assert exploration[-1]["candidate_id"] == "weak"
    unseen = next(row for row in exploration if row["candidate_id"] == "new")
    assert unseen["observed_before"] is False
    assert unseen["n_primitive"] == 0
    assert unseen["sd"] > next(row["sd"] for row in exploration
                                 if row["candidate_id"] == "strong")
    assert exploration == ranking.rank_candidates(
        history, cutoff=cutoff, direction="validation",
        candidate_ids=["weak", "new", "strong"], exploration_weight=1.0)


def test_negative_or_nonfinite_exploration_weight_refused():
    for weight in (-1.0, float("inf"), float("nan")):
        with pytest.raises(ValueError, match="exploration_weight"):
            ranking.rank_candidates([], cutoff="2026-02-01", direction="validation",
                                    candidate_ids=["new"], exploration_weight=weight)


def _brier(predictions, outcomes):
    return sum((p - int(y)) ** 2 for p, y in zip(predictions, outcomes)) / len(outcomes)


def evaluate_asof_group_holdout(observations, *, bootstrap_reps=2000, seed=8127):
    """First-seen one-group outcomes with cluster-bootstrap helper."""
    ordered = sorted(observations, key=lambda o: (ranking._time_key(o.at),
                                                   o.primitive_id))
    seen: set[tuple[str, str]] = set()
    rows = []
    rng = random.Random(seed)
    for target in ordered:
        group = (target.direction, target.primitive_id)
        if group in seen:
            continue
        seen.add(group)
        history = ranking.known_before(ordered, target.at)
        if not history:
            continue
        estimate = ranking.estimate(history, cutoff=target.at,
                                    direction=target.direction,
                                    primitive_id=target.primitive_id)
        base = (sum(o.passed for o in history) + 1) / (len(history) + 2)
        rows.append({"group": group, "y": target.passed,
                     "outcome_aware": estimate.mean,
                     "base_rate": base, "random": rng.random()})
    if not rows:
        raise ValueError("no first-seen group has prior history")
    groups = sorted({row["group"] for row in rows})
    result = {"n_rows": len(rows), "n_groups": len(groups),
              "n_positive": sum(row["y"] for row in rows), "metrics": {}}
    for method in ("outcome_aware", "base_rate", "random"):
        result["metrics"][method] = _brier([r[method] for r in rows],
                                            [r["y"] for r in rows])
    rng = random.Random(seed)
    differences = []
    for _ in range(bootstrap_reps):
        draw = [rng.choice(groups) for _ in groups]
        sample = [row for group in draw for row in rows if row["group"] == group]
        y = [row["y"] for row in sample]
        aware = [row["outcome_aware"] for row in sample]
        base = [row["base_rate"] for row in sample]
        differences.append(_brier(aware, y) - _brier(base, y))
    differences.sort()
    result["outcome_aware_minus_base_brier_cluster_bootstrap_95ci"] = [
        differences[int(.025 * bootstrap_reps)],
        differences[int(.975 * bootstrap_reps) - 1]]
    result["sample_design"] = "first-seen group outcomes with strict chronological as-of predictions"
    return result


def test_candidate_family_identity_pools_configs_without_counting_them_as_groups():
    history = [
        ranking.Observation("2026-01-01T00:00:00Z", "model_architecture", "model", "cfg-a", True,
                           selection_key="model_architecture"),
        ranking.Observation("2026-01-02T00:00:00Z", "model_architecture", "model", "cfg-b", True,
                           selection_key="model_architecture"),
        ranking.Observation("2026-01-03T00:00:00Z", "feature_engineering", "feature", "cfg-c", False,
                           selection_key="feature_engineering"),
    ]
    cutoff = "2026-02-01T00:00:00Z"
    estimate = ranking.regularized_candidate_probability(
        history, cutoff=cutoff, direction="model_architecture",
        primitive_id="new-model-config", candidate_key="model_architecture")
    assert estimate["n_global_groups"] == 3
    assert estimate["n_candidate_groups"] == 2
    assert estimate["mean"] > estimate["prior_mean"]
    exact = ranking.regularized_candidate_probability(
        history, cutoff=cutoff, direction="model_architecture",
        primitive_id="cfg-a")
    assert exact["n_candidate_groups"] == 1


def test_conservative_hybrid_does_not_learn_below_minimum_unique_groups():
    history = [_obs(f"2026-01-{day:02d}", f"config-{day}", day % 2 == 0)
               for day in range(1, 10)]
    row = ranking.conservative_hybrid_probability(
        history, cutoff="2026-02-01", direction="validation",
        primitive_id="new-config", min_groups=12, full_groups=30)
    assert row["n_global_groups"] == 9
    assert row["n_direction_groups"] == 9
    assert row["weight"] == 0.0
    assert row["mean"] == row["pooled_base_rate"]


def test_hybrid_cannot_unlock_direction_preferences_from_unrelated_groups():
    history = [
        ranking.Observation(f"2026-01-{day:02d}T00:00:00Z", "feature_engineering",
                            "feature", f"feature-{day}", day % 2 == 0)
        for day in range(1, 25)
    ]
    history.extend(
        ranking.Observation(f"2026-02-{day:02d}T00:00:00Z", "model_complexity",
                            "complexity", f"complexity-{day}", True)
        for day in range(1, 4)
    )
    row = ranking.conservative_hybrid_probability(
        history, cutoff="2026-03-01T00:00:00Z", direction="model_complexity",
        primitive_id="new-complexity", min_groups=12, full_groups=30)
    assert row["n_global_groups"] == 27
    assert row["n_direction_groups"] == 3
    assert row["n_blend_groups"] == 3
    assert row["weight"] == 0.0
    assert row["mean"] == row["pooled_base_rate"]


def test_hybrid_warmup_uses_candidate_family_group_count():
    history = [
        ranking.Observation(f"2026-01-{day:02d}T00:00:00Z", "feature_engineering",
                            "feature", f"feature-{day}", day % 2 == 0)
        for day in range(1, 10)
    ]
    history.extend(
        ranking.Observation(f"2026-02-{day:02d}T00:00:00Z", "model_complexity",
                            "complexity", f"complexity-{day}", True)
        for day in range(1, 7)
    )
    row = ranking.conservative_hybrid_probability(
        history, cutoff="2026-03-01T00:00:00Z", direction="model_complexity",
        primitive_id="new-complexity", min_groups=5, full_groups=10)
    assert row["n_global_groups"] == 15
    assert row["n_direction_groups"] == 6
    assert row["n_blend_groups"] == 6
    assert row["weight"] == pytest.approx(2 / 6)
    assert row["mean"] == pytest.approx(
        row["pooled_base_rate"] + row["weight"] *
        (row["regularized_mean"] - row["pooled_base_rate"]))


def test_failed_and_inconclusive_attempts_are_not_false_labels():
    observations = [
        ranking.Observation("2026-01-01T00:00:00Z", "calibration", "test", "candidate-a", True,
                           outcome_status="success", experiment_id="exp-1", proposal_id="prop-1"),
        ranking.Observation("2026-01-01T00:00:01Z", "calibration", "test", "candidate-a", False,
                           outcome_status="rejected", experiment_id="exp-1b", proposal_id="prop-1b"),
        ranking.Observation("2026-01-02T00:00:00Z", "calibration", "test", "candidate-b", None,
                           outcome_status="failed", experiment_id="exp-2", proposal_id="prop-2",
                           rejection_reason="timeout"),
        ranking.Observation("2026-01-03T00:00:00Z", "calibration", "test", "candidate-c", None,
                           outcome_status="inconclusive", experiment_id="exp-3", proposal_id="prop-3"),
        ranking.Observation("2026-01-04T00:00:00Z", "calibration", "test", "candidate-d", None,
                           outcome_status="refused", experiment_id="exp-4", proposal_id="prop-4",
                           rejection_reason="duplicate"),
        ranking.Observation("2026-01-05T00:00:00Z", "calibration", "test", "candidate-e", None,
                           outcome_status="unverifiable", experiment_id="exp-5", proposal_id="prop-5",
                           rejection_reason="missing linked result"),
    ]
    estimate = ranking.estimate(observations[:3], cutoff="2026-01-04T00:00:00Z",
                                direction="calibration", primitive_id="candidate-new")
    counts = ranking.outcome_group_counts(observations)
    assert estimate.n_total == estimate.n_direction == 1
    assert estimate.n_primitive == 0
    assert estimate.mean == 0.5
    assert counts["rows"] == 6
    assert counts["adjudicated_rows"] == 2
    assert counts["independent_groups"] == 1
    assert counts["status_counts"] == {
        "failed": 1, "inconclusive": 1, "refused": 1,
        "rejected": 1, "success": 1, "unverifiable": 1}


def test_iso8601_cutoff_compares_instants_not_lexical_offsets():
    earlier = ranking.Observation("2026-01-01T01:00:00+01:00", "d", "c", "a", True)
    later = ranking.Observation("2026-01-01T00:30:00Z", "d", "c", "b", False)
    assert ranking.known_before([earlier, later], "2026-01-01T00:15:00Z") == [earlier]
    assert ranking.known_before([earlier], "2026-01-01T00:30:00Z") == [earlier]
    assert ranking.known_before([earlier], "2026-01-01T00:30:00.001Z") == [earlier]


def test_no_holdout_or_campaign_activation_surface_exists():
    from autonomous_agent.proposal_layer import candidate_search_v2 as search
    assert search.ACTIVATED_FOR_CAMPAIGNS is False
    assert search.DEV_FIXTURE_STATUS == "DEVELOPMENT_FIXTURE_ONLY"
    assert not hasattr(search, "run_campaign")
