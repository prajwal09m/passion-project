"""Isolated candidate-search proposal v2 (not wired to campaigns).

The current campaign generator's executable universe is closed to four
feature arms and two estimators. This module exercises a proposed, genuinely
executable extension using caller-supplied development feature IDs only. Its
catalog is deliberately campaign-ineligible; feature IDs in the benchmark
are synthetic fixture columns, not claims about production data.

Every candidate is a closed, versioned config. Candidate identity contains
only effective model/evaluation settings (not display text), and evidence
identity additionally binds the dataset and split. Generation requires an
explicit development-only opt-in; no production entrypoint imports this file.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

PROTOCOL_ID = "demand-zone-ai-search-proposal-v2.0.2"
CANDIDATE_VERSION = "candidate-search-v2.0.2"
ACTIVATED_FOR_CAMPAIGNS = False
DEV_FIXTURE_STATUS = "DEVELOPMENT_FIXTURE_ONLY"
TRANSFORMS = ("identity", "standardize", "polynomial2")
FAMILIES = ("logistic_regression", "random_forest", "hist_gradient_boosting")
FEATURE_OPERATORS = ("original", "pairwise_interactions", "nonlinear_marginals")
NOVELTY_DIMENSIONS = ("estimator_family", "transform", "features", "feature_operator",
                      "hyperparameters")

_MODEL_GRID: dict[str, tuple[dict[str, Any], ...]] = {
    "logistic_regression": ({"C": 0.1}, {"C": 1.0}),
    "random_forest": (
        {"max_depth": 3, "n_estimators": 64},
        {"max_depth": 6, "n_estimators": 64},
        {"max_depth": 3, "n_estimators": 128},
        {"max_depth": 6, "n_estimators": 128},
    ),
    "hist_gradient_boosting": (
        {"learning_rate": 0.05, "max_leaf_nodes": 7},
        {"learning_rate": 0.05, "max_leaf_nodes": 15},
        {"learning_rate": 0.1, "max_leaf_nodes": 7},
        {"learning_rate": 0.1, "max_leaf_nodes": 15},
    ),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _semantic_feature_map(candidate: Mapping[str, Any]) -> tuple[tuple[int, ...], ...]:
    """Canonical monomial columns produced by the composed feature operators.

    This represents the actual feature matrix, rather than treating an
    operator/transform label pair as automatically novel. A square-only
    ``nonlinear_marginals + identity`` map omits cross-feature products, while
    ``original + polynomial2`` includes them; these are distinct hypotheses.
    """
    features = candidate.get("feature_ids")
    if not isinstance(features, list) or not features:
        return ()
    ordered = sorted(features)
    width = len(ordered)
    operator = candidate.get("feature_operator", "original")
    base = []
    for i in range(width):
        exponent = [0] * width
        exponent[i] = 1
        base.append(tuple(exponent))
    if operator == "original":
        terms = set(base)
    elif operator == "pairwise_interactions":
        terms = set(base)
        for i in range(width):
            for j in range(i + 1, width):
                exponent = [0] * width
                exponent[i] = exponent[j] = 1
                terms.add(tuple(exponent))
    elif operator == "nonlinear_marginals":
        terms = set(base)
        for i in range(width):
            exponent = [0] * width
            exponent[i] = 2
            terms.add(tuple(exponent))
    else:
        return ()
    if candidate.get("transform") == "polynomial2":
        expanded = set(terms)
        ordered_terms = sorted(terms)
        for i, left in enumerate(ordered_terms):
            for right in ordered_terms[i:]:
                expanded.add(tuple(a + b for a, b in zip(left, right)))
        terms = expanded
    return tuple(sorted(terms))


def _identity_fields(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Identity of executable estimator + actual feature map + scaling behavior."""
    family = candidate.get("estimator_family")
    transform = candidate.get("transform")
    # StandardScaler preserves tree partition representability (up to ties and
    # floating-point effects), but polynomial2 changes the feature map itself.
    # Do not collapse polynomial expansion for tree estimators: the composed
    # monomial map below includes it and remains identity-bearing.
    scaled = transform == "standardize"
    if family in {"random_forest", "hist_gradient_boosting"}:
        scaled = False  # positive axis-wise scaling preserves tree thresholds
    return {
        "protocol_id": candidate.get("protocol_id"),
        "estimator_family": family,
        "hyperparameters": candidate.get("hyperparameters"),
        "feature_ids": sorted(candidate.get("feature_ids", [])),
        "feature_map_exponents": _semantic_feature_map(candidate),
        "scaled": scaled,
        "split_protocol_id": candidate.get("split_protocol_id"),
    }


def candidate_identity(candidate: Mapping[str, Any]) -> str:
    return _sha256(_identity_fields(candidate))


def candidate_evidence_key(candidate: Mapping[str, Any], *,
                           dataset_id: str, split_id: str) -> str:
    """Bind a model definition to exact authorized data/split identifiers."""
    if not dataset_id or not split_id:
        raise ValueError("dataset_id and split_id must be non-empty")
    return _sha256({"candidate_identity": candidate_identity(candidate),
                    "dataset_id": dataset_id, "split_id": split_id})


def _make_candidate(family: str, params: Mapping[str, Any], features: Sequence[str],
                    transform: str, feature_operator: str = "original") -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "schema_version": 1,
        "candidate_version": CANDIDATE_VERSION,
        "protocol_id": PROTOCOL_ID,
        "activation_status": DEV_FIXTURE_STATUS,
        "estimator_family": family,
        "hyperparameters": dict(params),
        "feature_ids": list(features),
        "feature_operator": feature_operator,
        "transform": transform,
        "split_protocol_id": "chronological_holdout_v1",
    }
    candidate["candidate_id"] = candidate_identity(candidate)
    return candidate


def validate_candidate(candidate: Mapping[str, Any],
                       feature_universe: Iterable[str]) -> list[str]:
    """Validate a candidate against the closed development-only catalog."""
    errors: list[str] = []
    required = {"schema_version", "candidate_version", "protocol_id",
                "activation_status", "estimator_family", "hyperparameters",
                "feature_ids", "feature_operator", "transform", "split_protocol_id", "candidate_id"}
    if set(candidate) != required:
        errors.append(f"candidate keys must exactly match the v2 schema; extra={sorted(set(candidate)-required)} missing={sorted(required-set(candidate))}")
        return errors
    if candidate["schema_version"] != 1 or candidate["candidate_version"] != CANDIDATE_VERSION:
        errors.append("unsupported candidate schema/version")
    if not isinstance(candidate["hyperparameters"], dict):
        errors.append("hyperparameters must be a mapping")
    if not isinstance(candidate["feature_ids"], list):
        errors.append("feature_ids must be a list")
    if not isinstance(candidate["transform"], str):
        errors.append("transform must be a string")
    if not isinstance(candidate["feature_operator"], str):
        errors.append("feature_operator must be a string")
    if not isinstance(candidate["estimator_family"], str):
        errors.append("estimator_family must be a string")
    if errors:
        return errors
    if candidate["protocol_id"] != PROTOCOL_ID:
        errors.append("unknown protocol_id")
    if candidate["activation_status"] != DEV_FIXTURE_STATUS or ACTIVATED_FOR_CAMPAIGNS:
        errors.append("candidate search is disabled for campaigns; development fixture only")
    family = candidate["estimator_family"]
    if family not in _MODEL_GRID:
        errors.append(f"unsupported estimator_family: {family!r}")
    elif candidate["hyperparameters"] not in _MODEL_GRID[family]:
        errors.append(f"hyperparameters are outside the reviewed dev grid for {family}")
    if candidate["transform"] not in TRANSFORMS:
        errors.append(f"unsupported transform: {candidate['transform']!r}")
    if candidate["feature_operator"] not in FEATURE_OPERATORS:
        errors.append(f"unsupported feature_operator: {candidate['feature_operator']!r}")
    if candidate["split_protocol_id"] != "chronological_holdout_v1":
        errors.append("unsupported split protocol")
    features = candidate["feature_ids"]
    try:
        known = set(feature_universe)
    except TypeError:
        errors.append("feature_universe must contain hashable feature IDs")
        return errors
    if (not isinstance(features, list) or len(features) < 2
            or any(not isinstance(feature, str) or not feature for feature in features)
            or len(set(features)) != len(features)):
        errors.append("feature_ids must be a list of at least two distinct non-empty strings")
    elif not set(features) <= known:
        errors.append("feature_ids contain columns outside the supplied development fixture")
    try:
        actual_id = candidate_identity(candidate)
    except (TypeError, ValueError):
        actual_id = ""
    if candidate["candidate_id"] != actual_id:
        errors.append("candidate_id does not match canonical executable identity")
    return errors


def generate_candidates(feature_ids: Sequence[str], *,
                        allow_development_fixture: bool = False) -> list[dict[str, Any]]:
    """Generate bounded model/feature/transform interactions; never campaign-active."""
    if not allow_development_fixture:
        raise PermissionError("pass allow_development_fixture=True to use the isolated fixture catalog")
    if (not isinstance(feature_ids, Sequence)
            or isinstance(feature_ids, (str, bytes))):
        raise ValueError("feature IDs must be a sequence of at least three unique strings")
    if any(not isinstance(feature, str) or not feature for feature in feature_ids):
        raise ValueError("feature IDs must be non-empty strings")
    if len(feature_ids) < 3 or len(set(feature_ids)) != len(feature_ids):
        raise ValueError("provide at least three unique fixture feature IDs")
    feature_patterns = [tuple(feature_ids)]
    feature_patterns.extend(tuple(f for f in feature_ids if f != omitted)
                            for omitted in feature_ids)
    candidates = [
        _make_candidate(family, params, features, transform, operator)
        for family in FAMILIES
        for params in _MODEL_GRID[family]
        for features in feature_patterns
        for transform in TRANSFORMS
        for operator in FEATURE_OPERATORS
    ]
    errors = [(c["candidate_id"], validate_candidate(c, feature_ids))
              for c in candidates]
    invalid = [(cid, problems) for cid, problems in errors if problems]
    if invalid:
        raise ValueError(f"internal candidate catalog contains invalid config: {invalid[0]}")
    return candidates


def _dimension_value(candidate: Mapping[str, Any], dimension: str) -> str:
    if dimension == "features":
        return _canonical_json(candidate["feature_ids"])
    if dimension == "hyperparameters":
        return _canonical_json(candidate["hyperparameters"])
    if dimension == "feature_operator":
        return str(candidate.get("feature_operator", "original"))
    return str(candidate[dimension])


def select_diverse(candidates: Sequence[Mapping[str, Any]], *, budget: int,
                   feature_universe: Iterable[str], dataset_id: str,
                   split_id: str, existing_evidence_keys: Iterable[str] = ()) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fail-closed canonical dedup, then deterministic marginal diversity selection."""
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
        raise ValueError("budget must be a non-negative integer")
    try:
        known_features = set(feature_universe)
    except TypeError as exc:
        raise ValueError("feature_universe must contain hashable feature IDs") from exc
    existing = set(existing_evidence_keys)
    seen_identity: set[str] = set()
    seen_evidence_keys: set[str] = set(existing)
    pool: list[dict[str, Any]] = []
    duplicate_evidence_in_input = 0
    duplicate_configs = 0
    redundant_evidence = 0
    invalid: list[dict[str, Any]] = []
    for raw in candidates:
        candidate = dict(raw)
        problems = validate_candidate(candidate, known_features)
        if problems:
            invalid.append({"candidate_id": candidate.get("candidate_id"),
                            "reasons": problems})
            continue
        identity = candidate_identity(candidate)
        if identity in seen_identity:
            duplicate_configs += 1
            continue
        seen_identity.add(identity)
        evidence = candidate_evidence_key(candidate, dataset_id=dataset_id,
                                          split_id=split_id)
        if evidence in seen_evidence_keys:
            if evidence in existing:
                redundant_evidence += 1
            else:
                duplicate_evidence_in_input += 1
            continue
        seen_evidence_keys.add(evidence)
        candidate["evidence_key"] = evidence
        pool.append(candidate)

    selected: list[dict[str, Any]] = []
    counts: dict[str, Counter[str]] = {
        dimension: Counter() for dimension in NOVELTY_DIMENSIONS}
    while pool and len(selected) < budget:
        def diversity_score(candidate: Mapping[str, Any]) -> tuple[float, str]:
            score = sum(1.0 / (1.0 + counts[d][_dimension_value(candidate, d)])
                        for d in counts)
            return score, candidate_identity(candidate)
        best = min(pool, key=lambda c: (-diversity_score(c)[0], diversity_score(c)[1]))
        pool.remove(best)
        selected.append(best)
        for dimension in counts:
            counts[dimension][_dimension_value(best, dimension)] += 1

    dim_coverage = {dimension: dict(sorted(Counter(
        _dimension_value(c, dimension) for c in selected).items()))
        for dimension in counts}
    stats = {
        "input_count": len(candidates),
        "valid_unique_candidates": len(seen_identity),
        "unique_evidence_candidates": len(seen_evidence_keys) - len(existing),
        "selected": len(selected),
        "duplicate_configs_removed": duplicate_configs,
        "redundant_evidence_removed": redundant_evidence,
        "duplicate_evidence_in_input_removed": duplicate_evidence_in_input,
        "invalid_count": len(invalid),
        "invalid_reasons": invalid,
        "remaining_after_budget": len(pool),
        "unique_evidence_keys_selected": len({c["evidence_key"] for c in selected}),
        "dimension_coverage": dim_coverage,
    }
    return selected, stats


def _append_marginal_squares(matrix: Any):
    """Add x_j^2 columns without silently adding cross-feature products."""
    import numpy as np
    values = np.asarray(matrix, dtype=float)
    return np.concatenate((values, np.square(values)), axis=1)


def _estimator(family: str, params: Mapping[str, Any]):
    if family == "logistic_regression":
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(C=float(params["C"]), max_iter=1000,
                                  solver="lbfgs", random_state=0)
    if family == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(n_estimators=int(params["n_estimators"]),
                                      max_depth=int(params["max_depth"]),
                                      random_state=0, n_jobs=1)
    if family == "hist_gradient_boosting":
        from sklearn.ensemble import HistGradientBoostingClassifier
        return HistGradientBoostingClassifier(
            learning_rate=float(params["learning_rate"]),
            max_leaf_nodes=int(params["max_leaf_nodes"]),
            random_state=0, early_stopping=False)
    raise ValueError(f"unsupported estimator family {family!r}")


def build_pipeline(candidate: Mapping[str, Any]):
    """Build a real sklearn preprocessing+estimator pipeline from a validated spec."""
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import FunctionTransformer, PolynomialFeatures, StandardScaler

    transform = candidate["transform"]
    operator = candidate.get("feature_operator", "original")
    if operator == "original":
        feature_steps = []
    elif operator == "pairwise_interactions":
        feature_steps = [("interactions", PolynomialFeatures(
            degree=2, interaction_only=True, include_bias=False))]
    elif operator == "nonlinear_marginals":
        feature_steps = [("nonlinear", FunctionTransformer(
            _append_marginal_squares, validate=True, feature_names_out="one-to-one"))]
    else:
        raise ValueError(f"unsupported feature operator {operator!r}")
    if transform == "identity":
        steps = list(feature_steps)
    elif transform == "standardize":
        steps = list(feature_steps) + [("scale", StandardScaler())]
    elif transform == "polynomial2":
        steps = list(feature_steps) + [("polynomial", PolynomialFeatures(degree=2, include_bias=False)),
                                      ("scale", StandardScaler())]
    else:
        raise ValueError(f"unsupported transform {transform!r}")
    steps.append(("model", _estimator(candidate["estimator_family"],
                                      candidate["hyperparameters"])))
    return Pipeline(steps)


def evaluate_candidate(candidate: Mapping[str, Any], *, X: Any, y: Any,
                        feature_ids: Sequence[str], train_indices: Sequence[int],
                        validation_indices: Sequence[int],
                        include_predictions: bool = False) -> dict[str, Any]:
    """Fit on a strictly earlier training slice and score an untouched later slice."""
    import numpy as np
    from sklearn.metrics import (average_precision_score, brier_score_loss,
                                 roc_auc_score)

    # Selection annotates candidates with an evidence_key; this derived
    # selection field is not part of the signed candidate schema.
    model_config = {key: value for key, value in candidate.items()
                    if key != "evidence_key"}
    if (not isinstance(feature_ids, Sequence)
            or isinstance(feature_ids, (str, bytes))
            or any(not isinstance(feature, str) or not feature for feature in feature_ids)
            or len(set(feature_ids)) != len(feature_ids)):
        raise ValueError("feature_ids must be unique non-empty strings")
    errors = validate_candidate(model_config, feature_ids)
    if errors:
        raise ValueError(f"candidate is invalid: {errors}")
    x = np.asarray(X, dtype=float)
    labels = np.asarray(y)
    if x.ndim != 2 or labels.ndim != 1 or len(x) != len(labels):
        raise ValueError("X must be 2D and y must be a matching 1D vector")
    if x.shape[1] != len(feature_ids) or not np.isfinite(x).all():
        raise ValueError("X columns must match feature_ids and contain only finite values")
    raw_train = np.asarray(train_indices)
    raw_valid = np.asarray(validation_indices)
    if raw_train.ndim != 1 or raw_valid.ndim != 1:
        raise ValueError("split indices must be one-dimensional")
    if (not np.issubdtype(raw_train.dtype, np.integer)
            or not np.issubdtype(raw_valid.dtype, np.integer)):
        raise ValueError("split indices must be integers")
    train = raw_train.astype(int, copy=False)
    valid = raw_valid.astype(int, copy=False)
    if not len(train) or not len(valid) or np.intersect1d(train, valid).size:
        raise ValueError("train and validation indices must be non-empty and disjoint")
    if len(np.unique(train)) != len(train) or len(np.unique(valid)) != len(valid):
        raise ValueError("train and validation indices must be unique")
    if train.min() < 0 or valid.min() < 0 or train.max() >= len(x) or valid.max() >= len(x):
        raise ValueError("split index outside the supplied fixture")
    if train.max() >= valid.min():
        raise ValueError("training rows must be strictly earlier than validation rows")
    if (not np.issubdtype(labels.dtype, np.number)
            or not np.isfinite(labels).all()
            or not np.isin(labels, [0, 1]).all()):
        raise ValueError("y must contain finite binary labels 0/1")
    y_train, y_valid = labels[train], labels[valid]
    if len(np.unique(y_train)) != 2 or len(np.unique(y_valid)) != 2:
        raise ValueError("both temporal partitions must contain both classes")
    col = {name: i for i, name in enumerate(feature_ids)}
    selected_cols = [col[name] for name in model_config["feature_ids"]]
    pipeline = build_pipeline(model_config)
    started = time.perf_counter()
    pipeline.fit(x[train][:, selected_cols], y_train)
    fit_seconds = time.perf_counter() - started
    probabilities = pipeline.predict_proba(x[valid][:, selected_cols])[:, 1]
    result = {
        "candidate_id": model_config["candidate_id"],
        "n_train": int(len(train)), "n_validation": int(len(valid)),
        "positive_rate_validation": float(np.mean(y_valid)),
        "roc_auc": float(roc_auc_score(y_valid, probabilities)),
        "average_precision": float(average_precision_score(y_valid, probabilities)),
        "brier": float(brier_score_loss(y_valid, probabilities)),
        "fit_seconds": float(fit_seconds),
    }
    if include_predictions:
        result["predicted_probabilities"] = probabilities.tolist()
        result["validation_labels"] = y_valid.astype(int).tolist()
    return result


def summarize_diversity(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Coverage and repeated-group frequency for selected candidate evidence."""
    groups = Counter(str(c.get("evidence_key") or candidate_identity(c))
                     for c in candidates)
    return {
        "proposals": len(candidates),
        "unique_evidence_keys": len(groups),
        "repeated_evidence_groups": sum(count > 1 for count in groups.values()),
        "proposals_in_repeated_groups": sum(count for count in groups.values() if count > 1),
        "family_counts": dict(sorted(Counter(str(c["estimator_family"])
                                                 for c in candidates).items())),            "transform_counts": dict(sorted(Counter(str(c["transform"])
                                                    for c in candidates).items())),
        "feature_operator_counts": dict(sorted(Counter(str(c.get("feature_operator", "original"))
                                                    for c in candidates).items())),
        "unique_feature_sets": len({_canonical_json(c["feature_ids"]) for c in candidates}),
    }
