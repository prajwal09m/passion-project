"""Phase 5 factorial synthetic model-search evaluation (development only).

Uses a fixed, time-ordered train/validation/final-test design and identical
rows across every candidate. The final block is used once for descriptive
generalization only; it is never used to select the winner. Output metrics are
synthetic validation artifacts, not market-data or profitability evidence.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE / "dev"))
from autonomous_agent.proposal_layer import candidate_search_v2 as search  # noqa: E402

OUT = WORKSPACE / "phase5_search_benchmark.json"
FEATURES = ("trend", "volatility", "interaction")
DATASET_ID = "phase5-synthetic-interaction-regime-v1"
SPLIT_ID = "fixed-chronological-60-20-20-v1"


def fixture():
    """Independent held-out regimes, drift, and known nonlinear interactions."""
    rng = np.random.default_rng(20261018)
    n = 600
    x = rng.normal(size=(n, 3))
    regime = np.zeros(n, dtype=float)
    regime[200:400] = 1.0
    regime[400:] = -0.7
    logit = (1.0 * x[:, 0] - 0.72 * x[:, 1] + 0.48 * x[:, 0] * x[:, 2]
             + 0.22 * x[:, 2] ** 2 + 0.45 * regime * x[:, 1])
    # Mild label noise makes perfect synthetic memorization unhelpful.
    y = (logit + rng.normal(scale=1.15, size=n) > 0.12).astype(int)
    return x, y


def _paired_block_bootstrap_delta(y, score_a, score_b, *, seed=42,
                                  reps=2000, block_size=10):
    """Paired consecutive-block AUC delta; identical sampled rows for both models."""
    from sklearn.metrics import roc_auc_score

    y = np.asarray(y, dtype=int)
    score_a, score_b = np.asarray(score_a), np.asarray(score_b)
    if not (len(y) == len(score_a) == len(score_b)) or not len(y):
        raise ValueError("labels and paired scores must be non-empty and equal length")
    blocks = [np.arange(start, min(start + block_size, len(y)))
              for start in range(0, len(y), block_size)]
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(reps):
        selected = rng.integers(0, len(blocks), size=len(blocks))
        indices = np.concatenate([blocks[i] for i in selected])[:len(y)]
        sampled_y = y[indices]
        if np.unique(sampled_y).size < 2:
            continue
        deltas.append(float(roc_auc_score(sampled_y, score_b[indices])
                            - roc_auc_score(sampled_y, score_a[indices])))
    if len(deltas) < 2:
        return {"ci": None, "valid_replicates": len(deltas),
                "requested_replicates": reps, "block_size_rows": block_size,
                "block_count": len(blocks)}
    deltas.sort()
    return {"ci": [deltas[int(.025 * len(deltas))],
                    deltas[min(len(deltas)-1, int(.975 * len(deltas))-1)]],
            "valid_replicates": len(deltas), "requested_replicates": reps,
            "block_size_rows": block_size, "block_count": len(blocks)}


def _metric_summary(y, probabilities):
    from sklearn.metrics import (average_precision_score, brier_score_loss,
                                 roc_auc_score)
    y = np.asarray(y, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    return {"roc_auc": float(roc_auc_score(y, p)),
            "average_precision": float(average_precision_score(y, p)),
            "brier": float(brier_score_loss(y, p)),
            "n_rows": len(y), "positive_rate": float(np.mean(y))}


def _ece(y, probabilities, bins=10):
    """Equal-width ECE matching the frozen local harness bin convention."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(y)
    error = 0.0
    for index in range(bins):
        mask = ((probabilities >= edges[index])
                & (probabilities < edges[index + 1]
                   if index + 1 < bins else probabilities <= edges[index + 1]))
        if np.any(mask):
            error += abs(float(np.mean(probabilities[mask])) - float(np.mean(y[mask]))) * (
                int(np.sum(mask)) / total)
    return float(error)


def _summary(rows):
    import statistics
    def summarize(key):
        values = [float(row[key]) for row in rows]
        return {"mean": statistics.mean(values),
                "median": statistics.median(values),
                "min": min(values), "max": max(values)}
    return {"n": len(rows), "roc_auc": summarize("roc_auc"),
            "average_precision": summarize("average_precision"),
            "brier": summarize("brier"),
            "fit_seconds_sum": sum(float(row["fit_seconds"]) for row in rows)}


def main():
    started = time.perf_counter()
    x, y = fixture()
    # The selector may see the first 60% only. Validation chooses one config
    # within each family for descriptive family selection; test is not used to
    # alter the selected candidate or report a learned tuned winner.
    train = range(0, 360)
    validation = range(360, 480)
    test = range(480, 600)
    catalog = search.generate_candidates(FEATURES, allow_development_fixture=True)
    selected, stats = search.select_diverse(
        catalog, budget=18, feature_universe=FEATURES,
        dataset_id=DATASET_ID, split_id=SPLIT_ID)
    validation_rows = []
    elapsed_fit = 0.0
    for candidate in selected:
        valid = search.evaluate_candidate(candidate, X=x, y=y,
                                          feature_ids=FEATURES,
                                          train_indices=train,
                                          validation_indices=validation)
        validation_rows.append({**candidate, **valid})
        elapsed_fit += valid["fit_seconds"]

    # Freeze one reference estimator/hyperparameter tuple and four matched
    # single-factor changes before viewing final-test predictions.
    lr_params = {"C": 1.0}
    ablation_specs = {
        "reference_original_identity": ("original", "identity"),
        "pairwise_interactions_vs_original": ("pairwise_interactions", "identity"),
        "nonlinear_marginals_vs_original": ("nonlinear_marginals", "identity"),
        "polynomial2_vs_identity": ("original", "polynomial2"),
        "standardize_vs_identity_logistic": ("original", "standardize"),
    }
    catalog_by_identity = {search.candidate_identity(c): c for c in catalog}
    ablation_candidates = {}
    for name, (operator, transform) in ablation_specs.items():
        probe = search._make_candidate("logistic_regression", lr_params,
                                       FEATURES, transform, operator)
        ablation_candidates[name] = catalog_by_identity[search.candidate_identity(probe)]

    # The final-test block is not swept over every searched config. It is used
    # for one validation-selected config and this small preregistered matched
    # ablation panel only; none of these results changes the search winner.
    validation_winner = sorted(validation_rows,
                               key=lambda r: (-r["roc_auc"], r["candidate_id"]))[0]
    final_configs = {validation_winner["candidate_id"]: {
        key: value for key, value in validation_winner.items()
        if key in {"schema_version", "candidate_version", "protocol_id",
                   "activation_status", "estimator_family", "hyperparameters",
                   "feature_ids", "feature_operator", "transform",
                   "split_protocol_id", "candidate_id"}}}
    for candidate in ablation_candidates.values():
        final_configs[candidate["candidate_id"]] = candidate
    final_test_rows = {}
    for candidate_id, candidate in final_configs.items():
        result = search.evaluate_candidate(
            candidate, X=x, y=y, feature_ids=FEATURES,
            train_indices=range(0, 480), validation_indices=test,
            include_predictions=True)
        elapsed_fit += result["fit_seconds"]
        final_test_rows[candidate_id] = {**candidate, **result}

    # Same-model, same-data, paired contrasts; use fixed consecutive
    # blocks of 10 observations. All arms share every resampled index.
    reference = ablation_candidates["reference_original_identity"]
    reference_result = final_test_rows[reference["candidate_id"]]
    test_labels = np.asarray(y[480:600], dtype=int)
    blocks = [np.arange(start, min(start + 10, len(test_labels)))
              for start in range(0, len(test_labels), 10)]
    ablation_results = {}
    for name, candidate in ablation_candidates.items():
        if name == "reference_original_identity":
            continue
        treated = final_test_rows[candidate["candidate_id"]]
        control_scores = np.asarray(reference_result["predicted_probabilities"])
        treated_scores = np.asarray(treated["predicted_probabilities"])
        delta = treated["roc_auc"] - reference_result["roc_auc"]
        bootstrap = _paired_block_bootstrap_delta(
            test_labels, control_scores, treated_scores,
            seed=42, reps=2000, block_size=10)
        ablation_results[name] = {
            "reference_candidate_id": reference["candidate_id"],
            "candidate_id": candidate["candidate_id"],
            "test_auc_reference": reference_result["roc_auc"],
            "test_auc_candidate": treated["roc_auc"],
            "test_auc_delta": delta,
            "block_bootstrap_95ci_delta": bootstrap["ci"],
            "bootstrap_valid_replicates": bootstrap["valid_replicates"],
            "bootstrap_requested_replicates": bootstrap["requested_replicates"],
            "n_test_rows": len(test_labels),
            "block_length_rows": 10,
            "n_blocks": bootstrap["block_count"],
        }
    # Hyperparameter/candidate selection uses only validation. Report the top
    # validation candidate and its one final-test score; ablations are the
    # small, separately predeclared comparison panel above.
    final_top = final_test_rows[validation_winner["candidate_id"]]

    fixed_model_score_columns = {}
    fixed_model_set = sorted({
        (str(row["estimator_family"]),
         json.dumps(row["hyperparameters"], sort_keys=True),
         str(row["feature_operator"]), str(row["transform"]))
        for row in validation_rows
    })
    selected_feature_set = tuple(FEATURES)
    candidate_lookup = {}
    for candidate in catalog:
        effective_features = tuple(sorted(candidate["feature_ids"]))
        if len(effective_features) == len(selected_feature_set) and effective_features == tuple(sorted(selected_feature_set)):
            key = (str(candidate["estimator_family"]),
                   json.dumps(candidate["hyperparameters"], sort_keys=True),
                   str(candidate["feature_operator"]), str(candidate["transform"]))
            candidate_lookup[key] = candidate
    for candidate_id in final_test_rows:
        fixed_model_score_columns[candidate_id] = final_test_rows[candidate_id]
    for family, params_json, operator, transform in fixed_model_set:
        candidate = candidate_lookup[(family, params_json, operator, transform)]
        evaluated = search.evaluate_candidate(
            candidate, X=x, y=y, feature_ids=FEATURES,
            train_indices=range(0, 480), validation_indices=test,
            include_predictions=True)
        elapsed_fit += evaluated["fit_seconds"]
        fixed_model_score_columns[candidate["candidate_id"]] = evaluated
    selected_feature_candidates = [
        candidate for candidate in selected
        if tuple(sorted(candidate["feature_ids"])) == tuple(sorted(FEATURES))
    ]
    fixed_selected_test_results = [
        fixed_model_score_columns[candidate["candidate_id"]]
        for candidate in selected_feature_candidates
        if candidate["candidate_id"] in fixed_model_score_columns
    ]
    fixed_all_test_ids = list(fixed_model_score_columns)
    fixed_all_test_scores = {
        cid: _metric_summary(test_labels, result["predicted_probabilities"])
        for cid, result in fixed_model_score_columns.items()
    }
    baseline_fixed = ablation_candidates["reference_original_identity"]
    baseline_fixed_scores = np.asarray(
        fixed_model_score_columns[baseline_fixed["candidate_id"]]["predicted_probabilities"])
    fixed_family_deltas = {}
    for family in sorted({key[0] for key in fixed_model_set}):
        family_scores = [
            fixed_model_score_columns[candidate_lookup[key]["candidate_id"]]
            for key in fixed_model_set if key[0] == family
        ]
        family_test = [row for row in family_scores]
        fixed_family_deltas[family] = {
            "n_configurations": len(family_test),
            "mean_auc": float(np.mean([row["roc_auc"] for row in family_test])),
            "max_auc": float(max(row["roc_auc"] for row in family_test)),
        }

    # Before-after diversity comparisons use same budget and evidence space:
    # old legacy generator provides 18 outputs but all repeat 12 prior keys;
    # dedup correctly yields no eligible candidates. v2 produces a deduped
    # executable pool; no predictive comparison is inferred from these counts.
    runtime = time.perf_counter() - started
    result = {
        "schema": "phase5-synthetic-search-factorial-v1",
        "campaign_activation": False,
        "fixture_status": "DEVELOPMENT_FIXTURE_ONLY",
        "dataset_id": DATASET_ID,
        "split_id": SPLIT_ID,
        "n_rows": len(y),
        "split_sizes": {"train": len(list(train)), "validation": len(list(validation)),
                        "final_test": len(list(test))},
        "train_validation_test_ordered": True,
        "label_prevalence": {"train": float(np.mean(y[:360])),
                              "validation": float(np.mean(y[360:480])),
                              "final_test": float(np.mean(y[480:]))},
        "raw_configs": len(catalog),
        "genuinely_distinct_configs_after_semantic_dedup": stats["valid_unique_candidates"],
        "redundancy_removed": stats["duplicate_configs_removed"],
        "invalid_configs": stats["invalid_count"],
        "pool_after_dedup": stats["unique_evidence_candidates"],
        "selection_coverage": search.summarize_diversity(selected),
        "dimension_coverage": stats["dimension_coverage"],
        "selected_diverse_configs_validation_summary": _summary(validation_rows),
        "legacy_metric_comparison": {
            "legacy_outputs": 18,
            "legacy_distinct_config_keys": 12,
            "legacy_redundant_outputs": 18,
            "legacy_redundancy_rate": 1.0,
            "v2_raw_catalog_candidates": len(catalog),
            "v2_distinct_semantic_candidates": stats["valid_unique_candidates"],
            "v2_candidates_selected_for_validation": len(validation_rows),
            "comparison_limit": "The legacy key space is a different search universe and old outputs have no matched synthetic X/y evaluation; only catalog redundancy is comparable, not predictive metrics.",
        },
        "selected_candidates_validation": [
            {"candidate_id": row["candidate_id"],
             "estimator_family": row["estimator_family"],
             "feature_ids": row["feature_ids"],
             "feature_operator": row["feature_operator"],
             "transform": row["transform"],
             "hyperparameters": row["hyperparameters"],
             "roc_auc": row["roc_auc"],
             "average_precision": row["average_precision"],
             "brier": row["brier"]}
            for row in validation_rows
        ],
        "final_test_evaluation_count": len(final_test_rows),
        "final_test_evaluation_ids": sorted(final_test_rows),
        "validation_selected_config": {
            "candidate_id": validation_winner["candidate_id"],
            "family": validation_winner["estimator_family"],
            "operator": validation_winner["feature_operator"],
            "transform": validation_winner["transform"],
            "feature_ids": validation_winner["feature_ids"],
            "validation_metrics": {k: validation_winner[k] for k in
                                   ("roc_auc", "average_precision", "brier")},
            "final_test_metrics_once": {k: final_top[k] for k in
                                         ("roc_auc", "average_precision", "brier")},
            "warning": "Selected on the 20% validation block; reported once on the synthetic final-test block. Synthetic only; no promotion.",
        },
        "fixed_logistic_feature_ablation_final_test": ablation_results,
        "final_test_metric_method": "frozen pipeline fit on chronological train+validation indices 0:480, scored exactly once on indices 480:600; AUC/AP/Brier are descriptive synthetic results",
        "feature_operator_ablation_design": {
            "fixed_estimator": "LogisticRegression(C=1.0,max_iter=1000,solver=lbfgs)",
            "fixed_features": list(FEATURES),
            "reference": "original feature operator + identity transform",
            "single_factor_changes": ["pairwise interactions", "nonlinear marginals", "polynomial2", "standardize"],
            "same_training_rows": 480,
            "same_test_rows": 120,
            "same_random_seed": 0,
            "auc_interval": "paired bootstrap over 12 contiguous 10-row blocks, same indices both arms, NumPy seed 42, 2000 replicates; synthetic diagnostic only",
        },
        "selected_catalog_fixed_feature_subset_final_test": {
            "n_configurations": len(fixed_all_test_ids),
            "n_feature_maps": len({(key[2], key[3]) for key in fixed_model_set}),
            "metric_summary_by_candidate_id": fixed_all_test_scores,
            "family_summary": fixed_family_deltas,
            "fixed_feature_subset_ablation_vs_original_identity": {
                key[2] + "__" + key[3]: {
                    "n_configurations": len([k for k in fixed_model_set
                                               if (k[2], k[3]) == (key[2], key[3])]),
                    "mean_auc": float(np.mean([
                        fixed_model_score_columns[candidate_lookup[k]["candidate_id"]]["roc_auc"]
                        for k in fixed_model_set if (k[2], k[3]) == (key[2], key[3])
                    ])),
                }
                for key in fixed_model_set
                if (key[2], key[3]) != ("original", "identity")
            },
            "note": "All canonical estimator/hyperparameter/operator/transform combinations in the catalogue evaluated on the single fixed fixture feature subset; descriptive diagnostic only and never used to change the selected winner.",
        },
        "fit_runtime_seconds_validation_18_plus_final_test_panel": elapsed_fit,
        "wall_runtime_seconds": runtime,
        "measured_fit_count": len(validation_rows) + len(fixed_model_score_columns),
        "median_fit_seconds_validation": float(np.median(
            [row["fit_seconds"] for row in validation_rows])),
        "median_fit_seconds_fixed_final_test_candidates": float(np.median(
            [row["fit_seconds"] for row in fixed_model_score_columns.values()])),
        "search_coverage_diagnostics": {
            "distinct_estimator_families": len({c["estimator_family"] for c in catalog}),
            "distinct_raw_feature_subsets": len({tuple(sorted(c["feature_ids"])) for c in catalog}),
            "distinct_semantic_feature_maps": len({
                search._semantic_feature_map(c) for c in catalog}),
            "distinct_parameterized_transform_families": len({
                (c["estimator_family"], json.dumps(c["hyperparameters"], sort_keys=True),
                 search._semantic_feature_map(c),
                 search._identity_fields(c)["scaled"], c["split_protocol_id"])
                for c in catalog}),
            "feature_operator_transform_combinations": len({
                (c["feature_operator"], c["transform"]) for c in catalog}),
            "selection_coverage": stats["dimension_coverage"],
        },
        "legacy_comparison": {
            "same_proposal_budget": 18,
            "legacy_raw_emitted": 18,
            "legacy_unique_new_evidence": 0,
            "legacy_redundancy_rate": 1.0,
            "new_search_distinct_evidence_configs": stats["unique_evidence_candidates"],
            "comparison_limitation": "Legacy and proposal v2 change evidence universe as well as code; distinct-search count is engineering coverage, not predictive lift.",
        },
        "limitations": [
            "All outcomes are synthetic; no real-market prediction claims.",
            "The synthetic data-generating equation is intentionally known and contains nonlinear effects; matched ablations are a software/diagnostic check, not an unbiased estimate of live-market effect.",
            "The final-test descriptive sweep is not used to select a winner; hyperparameter selection remains validation-only.",
            "Matched ablation pairs share one held-out block and require independent datasets/regimes for inferential conclusions.",
        ],
    }
    result.pop("benchmark_sha256", None)
    result["benchmark_sha256"] = hashlib.sha256(json.dumps(
        result, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "raw_configs", "genuinely_distinct_configs_after_semantic_dedup",
        "redundancy_removed", "selected_diverse_configs_validation_summary",
        "fixed_logistic_feature_ablation_final_test",
        "validation_selected_config",
        "fit_runtime_seconds_validation_18_plus_final_test_panel",
        "wall_runtime_seconds")}, indent=2))


if __name__ == "__main__":
    main()
