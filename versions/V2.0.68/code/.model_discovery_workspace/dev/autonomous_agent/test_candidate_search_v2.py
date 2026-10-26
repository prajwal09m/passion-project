"""Tests for isolated proposal-v2 search and measurement primitives.

All data used here are deterministic synthetic fixtures. The module remains
unconnected to any production generator or campaign entrypoint.
"""
from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from autonomous_agent.proposal_layer import candidate_search_v2 as search  # noqa: E402
from autonomous_agent.proposal_layer import outcome_ranking as ranking  # noqa: E402

FEATURES = ("trend", "volatility", "interaction")
DATASET = "synthetic-fixture-v1"
SPLIT = "chronological-fixture-70-30-v1"


def _candidates():
    return search.generate_candidates(FEATURES, allow_development_fixture=True)


def test_generation_requires_explicit_development_only_opt_in():
    with pytest.raises(PermissionError):
        search.generate_candidates(FEATURES)


def test_generation_rejects_malformed_feature_id_containers_and_values():
    for malformed in ("trend,volatility,interaction", b"abc", None, 7):
        with pytest.raises(ValueError, match="sequence"):
            search.generate_candidates(malformed, allow_development_fixture=True)
    for malformed in (("trend", "", "interaction"),
                      ("trend", None, "interaction"),
                      ("trend", 4, "interaction")):
        with pytest.raises(ValueError, match="non-empty strings"):
            search.generate_candidates(malformed, allow_development_fixture=True)
    with pytest.raises(ValueError, match="unique"):
        search.generate_candidates(("trend", "trend", "interaction"),
                                   allow_development_fixture=True)


def test_catalog_contains_real_model_feature_transform_interactions():
    candidates = _candidates()
    assert len(candidates) == (2 + 4 + 4) * 4 * 3 * len(search.FEATURE_OPERATORS)
    assert {c["estimator_family"] for c in candidates} == set(search.FAMILIES)
    assert {c["transform"] for c in candidates} == set(search.TRANSFORMS)
    assert {c["feature_operator"] for c in candidates} == set(search.FEATURE_OPERATORS)
    assert len({tuple(c["feature_ids"]) for c in candidates}) == 4
    assert len({search.candidate_identity(c) for c in candidates}) == 264
    # Raw 360 configurations collapse tree-scaling equivalences, but keep
    # semantic feature maps distinct: pairwise products are not unary squares,
    # nor are operator-then-degree-2 expansions identified with direct degree-2.
    # Remaining identities are executable estimator/feature-map hypotheses.
    assert len({search.candidate_identity(c) for c in candidates}) < len(candidates)
    for candidate in candidates:
        assert search.validate_candidate(candidate, FEATURES) == []
        assert search.build_pipeline(candidate) is not None


def test_identity_ignores_presentation_fields_but_changes_for_evidence_settings():
    candidate = _candidates()[0]
    annotated = dict(candidate, rationale="different prose", title="display only")
    # The exact schema validator still rejects extra payload fields, while
    # identity itself correctly ignores presentation-only values.
    assert search.candidate_identity(annotated) == search.candidate_identity(candidate)
    changed = dict(candidate, transform="standardize")
    assert search.candidate_identity(changed) != search.candidate_identity(candidate)
    changed_operator = dict(candidate, feature_operator="pairwise_interactions")
    assert search.candidate_identity(changed_operator) != search.candidate_identity(candidate)
    assert search.candidate_evidence_key(candidate, dataset_id=DATASET,
                                         split_id=SPLIT) != search.candidate_evidence_key(
        candidate, dataset_id=DATASET, split_id="another-split")


def test_identity_distinguishes_operator_compositions_and_collapses_tree_scaling():
    candidates = _candidates()
    rf_identity = next(c for c in candidates
                       if c["estimator_family"] == "random_forest"
                       and c["transform"] == "identity")
    rf_scaled = dict(rf_identity, transform="standardize")
    rf_scaled["candidate_id"] = search.candidate_identity(rf_scaled)
    rf_reordered = dict(rf_identity, feature_ids=list(reversed(rf_identity["feature_ids"])))
    rf_reordered["candidate_id"] = search.candidate_identity(rf_reordered)
    assert search.candidate_identity(rf_scaled) == rf_identity["candidate_id"]
    assert search.candidate_identity(rf_reordered) == rf_identity["candidate_id"]
    rf_interactions = dict(rf_identity, feature_operator="pairwise_interactions")
    assert search.candidate_identity(rf_interactions) != rf_identity["candidate_id"]
    rf_nonlinear = dict(rf_identity, feature_operator="nonlinear_marginals")
    assert search.candidate_identity(rf_nonlinear) != rf_identity["candidate_id"]
    rf_poly = dict(rf_identity, transform="polynomial2")
    assert search.candidate_identity(rf_poly) != rf_identity["candidate_id"]
    # Pairwise interactions and marginal squares are different maps; the
    # pipeline produces cross-products in one and only squares in the other.
    assert search.candidate_identity(rf_interactions) != search.candidate_identity(rf_nonlinear)
    lr_identity = next(c for c in candidates
                       if c["estimator_family"] == "logistic_regression"
                       and c["transform"] == "identity")
    lr_scaled = dict(lr_identity, transform="standardize")
    lr_scaled["candidate_id"] = search.candidate_identity(lr_scaled)
    assert search.candidate_identity(lr_scaled) != lr_identity["candidate_id"]

    # PolynomialFeatures is applied after the selected operator. Thus
    # original+polynomial2, interactions+polynomial2, and squares+polynomial2
    # remain distinct, and equivalent feature ordering remains canonical.
    lr_poly = dict(lr_identity, transform="polynomial2")
    lr_interactions = dict(lr_identity, feature_operator="pairwise_interactions",
                           transform="polynomial2")
    lr_nonlinear = dict(lr_identity, feature_operator="nonlinear_marginals",
                        transform="polynomial2")
    identities = {search.candidate_identity(row)
                  for row in (lr_identity, lr_scaled, lr_poly,
                              lr_interactions, lr_nonlinear)}
    assert len(identities) == 5


def test_selection_deduplicates_tree_scaling_aliases_but_keeps_distinct_maps():
    candidates = _candidates()
    rf_identity = next(c for c in candidates
                       if c["estimator_family"] == "random_forest"
                       and c["transform"] == "identity")
    rf_scaled = dict(rf_identity, transform="standardize")
    rf_scaled["candidate_id"] = search.candidate_identity(rf_scaled)
    rf_reordered = dict(rf_identity, feature_ids=list(reversed(rf_identity["feature_ids"])))
    rf_reordered["candidate_id"] = search.candidate_identity(rf_reordered)
    rf_interactions = dict(rf_identity, feature_operator="pairwise_interactions")
    rf_interactions["candidate_id"] = search.candidate_identity(rf_interactions)
    rf_nonlinear = dict(rf_identity, feature_operator="nonlinear_marginals")
    rf_nonlinear["candidate_id"] = search.candidate_identity(rf_nonlinear)
    selected, stats = search.select_diverse(
        [rf_identity, rf_scaled, rf_reordered, rf_interactions, rf_nonlinear],
        budget=10, feature_universe=FEATURES, dataset_id=DATASET, split_id=SPLIT)
    assert stats["duplicate_configs_removed"] == 2
    assert stats["selected"] == stats["unique_evidence_keys_selected"] == 3
    assert selected[0]["transform"] == "identity"
    assert {c["feature_operator"] for c in selected} == {
        "original", "pairwise_interactions", "nonlinear_marginals"}


def test_validation_refuses_malformed_feature_universes():
    candidate = _candidates()[0]
    assert any("feature_universe" in error for error in
               search.validate_candidate(candidate, [[], "trend", "volatility"]))
    assert any("outside" in error for error in
               search.validate_candidate(candidate, ["trend", "volatility"]))


def test_validation_refuses_unknown_features_families_and_tampered_ids():
    candidate = _candidates()[0]
    unknown = dict(candidate, feature_ids=["not-in-fixture", "trend"])
    unknown["candidate_id"] = search.candidate_identity(unknown)
    assert any("outside" in e for e in search.validate_candidate(unknown, FEATURES))
    altered = dict(candidate, estimator_family="xgboost")
    altered["candidate_id"] = search.candidate_identity(altered)
    assert any("unsupported estimator_family" in e
               for e in search.validate_candidate(altered, FEATURES))
    tampered = dict(candidate)
    tampered["hyperparameters"] = {"C": 999}
    assert any("candidate_id" in e or "outside" in e
               for e in search.validate_candidate(tampered, FEATURES))
    extra = dict(candidate, python_code="__import__('os')")
    assert search.validate_candidate(extra, FEATURES)


def test_selection_removes_duplicate_configs_duplicate_evidence_and_history():
    candidates = _candidates()
    same = candidates[0]
    duplicates = candidates + [dict(same), dict(same)]
    existing = search.candidate_evidence_key(same, dataset_id=DATASET,
                                             split_id=SPLIT)
    selected, stats = search.select_diverse(
        duplicates, budget=30, feature_universe=FEATURES,
        dataset_id=DATASET, split_id=SPLIT,
        existing_evidence_keys=[existing])
    # v2 canonicalization also merges tree-only scaling variants generated
    # by the raw product grid, in addition to the two explicit duplicates.
    assert stats["duplicate_configs_removed"] == 98
    assert stats["redundant_evidence_removed"] == 1
    assert stats["selected"] == 30
    assert stats["unique_evidence_keys_selected"] == 30
    assert all(c["evidence_key"] != existing for c in selected)
    assert len({c["candidate_id"] for c in selected}) == len(selected)
    assert len(stats["dimension_coverage"]["estimator_family"]) == 3
    assert len(stats["dimension_coverage"]["transform"]) == 3
    assert len(stats["dimension_coverage"]["feature_operator"]) == 3


def test_selection_materializes_one_shot_feature_universe_once():
    candidates = _candidates()[:2]

    def feature_universe_once():
        yield from FEATURES

    universe = feature_universe_once()
    selected, stats = search.select_diverse(
        candidates, budget=2, feature_universe=universe,
        dataset_id=DATASET, split_id=SPLIT)
    assert stats["invalid_count"] == 0
    assert {c["candidate_id"] for c in selected} == {
        c["candidate_id"] for c in candidates}

    with pytest.raises(ValueError, match="hashable"):
        search.select_diverse(
            candidates, budget=1, feature_universe=[[], "trend"],
            dataset_id=DATASET, split_id=SPLIT)


def test_selection_requires_nonnegative_integer_budget():
    candidate = _candidates()[0]
    for invalid_budget in (-1, 1.5, True):
        with pytest.raises(ValueError, match="non-negative integer"):
            search.select_diverse(
                [candidate], budget=invalid_budget, feature_universe=FEATURES,
                dataset_id=DATASET, split_id=SPLIT)


def test_selection_quarantines_invalid_candidates_instead_of_scoring_them():
    candidates = _candidates()
    invalid = dict(candidates[0], estimator_family="unknown")
    invalid["candidate_id"] = search.candidate_identity(invalid)
    selected, stats = search.select_diverse(
        [invalid, *candidates], budget=5, feature_universe=FEATURES,
        dataset_id=DATASET, split_id=SPLIT)
    assert stats["invalid_count"] == 1
    assert selected
    assert all("unknown" != c["estimator_family"] for c in selected)


def test_temporal_evaluation_fits_only_earlier_rows_and_reports_metrics():
    rng = np.random.default_rng(20261017)
    n = 240
    x = rng.normal(size=(n, 3))
    logits = 0.9 * x[:, 0] - 0.7 * x[:, 1] + 0.5 * x[:, 0] * x[:, 2]
    y = (logits + rng.normal(scale=0.8, size=n) > 0.0).astype(int)
    candidate = next(c for c in _candidates()
                     if c["estimator_family"] == "logistic_regression"
                     and c["transform"] == "standardize")
    result = search.evaluate_candidate(
        candidate, X=x, y=y, feature_ids=FEATURES,
        train_indices=range(0, 160), validation_indices=range(160, n))
    assert result["n_train"] == 160
    assert result["n_validation"] == 80
    assert 0.0 <= result["roc_auc"] <= 1.0
    assert 0.0 <= result["average_precision"] <= 1.0
    assert 0.0 <= result["brier"] <= 1.0
    assert result["fit_seconds"] >= 0.0


def test_evaluation_refuses_leaking_or_invalid_splits():
    rng = np.random.default_rng(12)
    x = rng.normal(size=(60, 3))
    y = np.tile([0, 1], 30)
    candidate = _candidates()[0]
    with pytest.raises(ValueError, match="unique non-empty strings"):
        search.evaluate_candidate(candidate, X=x, y=y,
                                  feature_ids=("trend", "trend", "interaction"),
                                  train_indices=range(0, 30),
                                  validation_indices=range(30, 60))
    with pytest.raises(ValueError, match="one-dimensional"):
        search.evaluate_candidate(candidate, X=x, y=y, feature_ids=FEATURES,
                                  train_indices=[[0, 1], [2, 3]],
                                  validation_indices=range(30, 60))
    with pytest.raises(ValueError, match="strictly earlier"):
        search.evaluate_candidate(candidate, X=x, y=y, feature_ids=FEATURES,
                                  train_indices=[0, 40],
                                  validation_indices=[10, 30, 50])
    with pytest.raises(ValueError, match="disjoint"):
        search.evaluate_candidate(candidate, X=x, y=y, feature_ids=FEATURES,
                                  train_indices=range(0, 32),
                                  validation_indices=range(30, 60))
    with pytest.raises(ValueError, match="unique"):
        search.evaluate_candidate(candidate, X=x, y=y, feature_ids=FEATURES,
                                  train_indices=[0, 1, 1, 2],
                                  validation_indices=range(30, 60))
    with pytest.raises(ValueError, match="unique"):
        search.evaluate_candidate(candidate, X=x, y=y, feature_ids=FEATURES,
                                  train_indices=range(0, 30),
                                  validation_indices=[30, 31, 31, 32])
    with pytest.raises(ValueError, match="finite"):
        x[1, 0] = np.nan
        search.evaluate_candidate(candidate, X=x, y=y, feature_ids=FEATURES,
                                  train_indices=range(0, 30),
                                  validation_indices=range(30, 60))


def test_failed_and_inconclusive_attempts_remain_in_log_but_not_false_labels():
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
    ]
    estimate = ranking.estimate(observations[:3], cutoff="2026-01-04T00:00:00Z",
                                 direction="calibration", primitive_id="candidate-new")
    counts = ranking.outcome_group_counts(observations)
    assert estimate.n_total == estimate.n_direction == 1
    assert estimate.n_primitive == 0  # unseen candidate inherits the global/direction prior
    assert estimate.mean == 0.5  # conflicting adjudications yield one bounded prior vote
    assert counts["rows"] == 5
    assert counts["adjudicated_rows"] == 2
    assert counts["independent_groups"] == 1
    assert counts["status_counts"] == {
        "failed": 1, "inconclusive": 1, "refused": 1, "rejected": 1,
        "success": 1, "unverifiable": 0}


def test_iso8601_cutoff_compares_instants_not_lexical_offsets():
    earlier = ranking.Observation("2026-01-01T01:00:00+01:00", "d", "c", "a", True)
    later = ranking.Observation("2026-01-01T00:30:00Z", "d", "c", "b", False)
    assert ranking.known_before([earlier, later], "2026-01-01T00:15:00Z") == [earlier]
    assert ranking.known_before([earlier], "2026-01-01T00:30:00Z") == [earlier]
    assert ranking.known_before([earlier], "2026-01-01T00:30:00.001Z") == [earlier]


def test_no_holdout_or_campaign_activation_surface_exists():
    assert search.ACTIVATED_FOR_CAMPAIGNS is False
    assert search.DEV_FIXTURE_STATUS == "DEVELOPMENT_FIXTURE_ONLY"
    assert not hasattr(search, "run_campaign")


def test_identity_matches_reproducible_synthetic_feature_matrices_and_subprocesses():
    from sklearn.preprocessing import FunctionTransformer, PolynomialFeatures, StandardScaler

    rng = np.random.default_rng(20261018)
    X = rng.normal(size=(31, len(FEATURES))) + np.arange(len(FEATURES))[None, :] * 0.37
    base = next(candidate for candidate in _candidates()
                if candidate["estimator_family"] == "random_forest"
                and candidate["hyperparameters"] == {"max_depth": 3, "n_estimators": 64}
                and candidate["feature_ids"] == list(FEATURES))
    matrix_by_identity = {}

    for operator in search.FEATURE_OPERATORS:
        for transform in search.TRANSFORMS:
            candidate = dict(base, feature_operator=operator, transform=transform)
            candidate["candidate_id"] = search.candidate_identity(candidate)
            matrix = X.copy()
            terms = [tuple(int(i == j) for i in range(len(FEATURES)))
                     for j in range(len(FEATURES))]
            for _, step in search.build_pipeline(candidate).steps[:-1]:
                if isinstance(step, StandardScaler):
                    continue
                if isinstance(step, FunctionTransformer):
                    matrix = step.transform(matrix)
                    terms = terms + [tuple(2 * power for power in term) for term in terms]
                elif isinstance(step, PolynomialFeatures):
                    input_terms = list(terms)
                    matrix = step.fit_transform(matrix)
                    terms = [tuple(sum(int(power) * exponent[k]
                                       for power, exponent in zip(powers, input_terms))
                                   for k in range(len(FEATURES)))
                             for powers in step.powers_]
            term_counts = Counter(terms)
            assert set(term_counts) == set(search._semantic_feature_map(candidate))

            expected = np.column_stack([
                np.prod(np.column_stack([X[:, i] ** exponent
                                         for i, exponent in enumerate(term)]), axis=1)
                for term in terms
            ])
            assert np.allclose(matrix, expected, rtol=1e-12, atol=1e-12)
            signature = tuple(sorted(term_counts.items()))
            prior = matrix_by_identity.setdefault(candidate["candidate_id"], signature)
            assert prior == signature

    assert len(matrix_by_identity) == 6
    code = (
        "from autonomous_agent.proposal_layer import candidate_search_v2 as s; "
        "c=next(x for x in s.generate_candidates(('trend','volatility','interaction'), "
        "allow_development_fixture=True) if x['estimator_family']=='random_forest' "
        "and x['hyperparameters']=={'max_depth':3,'n_estimators':64} "
        "and x['feature_operator']=='pairwise_interactions' and x['transform']=='polynomial2'); "
        "print(s.candidate_identity(c))"
    )
    cwd = Path(__file__).resolve().parents[1]
    first = subprocess.check_output([sys.executable, "-c", code], cwd=cwd, text=True).strip()
    second = subprocess.check_output([sys.executable, "-c", code], cwd=cwd, text=True).strip()
    candidate = dict(base, feature_operator="pairwise_interactions", transform="polynomial2")
    candidate["candidate_id"] = search.candidate_identity(candidate)
    assert first == second == candidate["candidate_id"]
