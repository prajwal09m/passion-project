"""Phase 5 chronological evaluation of proposal-selection scoring rules.

Uses only the retained append-only proposal ledger and linked result/spec files.
It predicts adjudication status from information known strictly before each
execution; it never scores real-market model AUC, reads the sealed holdout, or
writes campaign state. Candidate-family identity is proposal direction; each
exact experiment configuration is an independent evaluation unit.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from collections import defaultdict

import numpy as np

WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent
sys.path.insert(0, str(WORKSPACE / "dev"))
sys.path.insert(0, str(WORKSPACE))
from autonomous_agent.proposal_layer import outcome_ranking as ranking  # noqa: E402
import phase4_replay  # noqa: E402

OUT = WORKSPACE / "phase5_selector_replay.json"


def _hash_json(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _config_group(experiment_id: str) -> tuple[str, str, dict[str, Any]]:
    """Return exact execution-config identity and its parsed config, fail-closed."""
    path = ROOT / "autonomous_agent" / "candidates" / experiment_id / "spec.json"
    if not path.is_file():
        return f"unlinked:{experiment_id}", "missing_spec", {}
    spec = json.loads(path.read_text(encoding="utf-8"))
    configs = []
    for item in spec.get("proposed_change", {}).get("files", []):
        if str(item.get("path", "")).endswith("experiment_config.json"):
            try:
                configs.append(json.loads(item["content"]))
            except (TypeError, json.JSONDecodeError):
                continue
    if not configs:
        return f"unlinked:{experiment_id}", "no_experiment_config", {}
    config = configs[0]
    return _hash_json(config), "linked", config


def _treatment_identity(config: dict[str, Any], *, include_calibration_bins: bool
                        ) -> str | None:
    """Identify the model treatment apart from its prose/decision gate metadata."""
    fields = ["arm_a", "arm_b", "estimator_a", "estimator_b",
              "baseline_id", "folds"]
    if include_calibration_bins:
        fields.append("calibration_bins")
    if not all(field in config for field in fields):
        return None
    return _hash_json({field: config[field] for field in fields})


def _decision_profile(config: dict[str, Any]) -> str | None:
    """Identity of criteria and uncertainty settings that define gate success."""
    criteria = config.get("evaluation_criteria")
    if not isinstance(criteria, dict):
        return None
    # Notes/hypothesis prose do not change the numeric decision rule.
    numeric_rule = {key: criteria.get(key) for key in (
        "primary_metric_min_delta", "ci_lower_min", "min_folds",
        "max_brier_degradation", "max_ece_degradation")}
    return _hash_json({"criteria": numeric_rule,
                       "n_boot": config.get("n_boot"),
                       "seeds": config.get("seeds"),
                       "calibration_bins": config.get("calibration_bins")})


def _direction_summary(rows: list[dict]) -> dict[str, dict[str, int | float]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row["direction"])].append(row)
    return {
        direction: {
            "n_config_groups": len(items),
            "positive": sum(int(item["outcome"]) for item in items),
            "negative": len(items) - sum(int(item["outcome"]) for item in items),
            "mean_predicted_base_rate": sum(float(item["base_rate"]) for item in items) / len(items),
        }
        for direction, items in sorted(grouped.items())
    }


def _week_cluster_ci(rows: list[dict], method: str, *, seed: int,
                     repetitions: int = 10000) -> dict[str, Any]:
    """Paired Brier delta bootstrap by actual W-SUN calendar week clusters."""
    by_week: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in rows:
        week = ranking._time_key(row["execute_at"]).date().isocalendar()
        delta = ((float(row[method]) - int(row["outcome"])) ** 2
                 - (float(row["base_rate"]) - int(row["outcome"])) ** 2)
        by_week[(week.year, week.week)].append(delta)
    weeks = sorted(by_week)
    if len(weeks) < 2:
        return {"ci": None, "calendar_week_clusters": len(weeks),
                "valid_replicates": 0,
                "note": "At least two calendar-week clusters are needed even for a descriptive cluster bootstrap."}
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(repetitions):
        picked = rng.integers(0, len(weeks), size=len(weeks))
        deltas = [delta for index in picked for delta in by_week[weeks[index]]]
        samples.append(float(np.mean(deltas)))
    samples.sort()
    return {"ci": [samples[int(.025 * repetitions)],
                   samples[int(.975 * repetitions) - 1]],
            "calendar_week_clusters": len(weeks),
            "valid_replicates": repetitions,
            "note": "Only a few weeks within one month; this is descriptive, not a reliable regime-generalization interval."}


def _target_identity_diagnostics(records: list[dict]) -> dict[str, Any]:
    treatment = {row["treatment_key"] for row in records if row["treatment_key"]}
    treatment_with_bins = {row["treatment_with_bins_key"] for row in records
                           if row["treatment_with_bins_key"]}
    decision_profiles = {row["decision_profile"] for row in records
                         if row["decision_profile"]}
    return {
        "full_recipe_config_attempts": len(records),
        "distinct_model_treatments_arms_estimators_baseline_folds": len(treatment),
        "distinct_treatments_including_calibration_bins": len(treatment_with_bins),
        "distinct_gate_protocols_criteria_bootstrap_and_calibration": len(decision_profiles),
        "warning": ("The scored outcome is gate/adjudication success, while configurations "
                    "vary in treatment and numeric success criteria. Exact full-config "
                    "grouping avoids mixing gate specifications but creates pseudo-diversity; "
                    "collapsing to model treatment yields too few groups and still leaves "
                    "criterion-dependent labels. Neither validates candidate market quality."),
    }


def _execution_times(rows: list[dict]) -> dict[str, str]:
    result = {}
    for row in rows:
        if row.get("row_type") != "transition" or row.get("to") != "EXECUTED":
            continue
        experiment_id = (row.get("detail") or {}).get("experiment_id")
        if experiment_id:
            result[experiment_id] = row["at"]
    return result


def _beta_base(history: list[ranking.Observation], prior: float = 0.5) -> float:
    groups = ranking._effective_adjudicated_groups(history)
    return (sum(groups.values()) + 2.0 * prior) / (len(groups) + 2.0)


def _logloss(probabilities: list[float], outcomes: list[int]) -> float:
    eps = 1e-12
    return -sum(y * math.log(max(eps, min(1.0 - eps, p))) +
                (1 - y) * math.log(max(eps, min(1.0 - eps, 1.0 - p)))
                for p, y in zip(probabilities, outcomes)) / len(outcomes)


def _auc(scores: list[float], outcomes: list[int]) -> float | None:
    positive = [s for s, y in zip(scores, outcomes) if y == 1]
    negative = [s for s, y in zip(scores, outcomes) if y == 0]
    if not positive or not negative:
        return None
    return sum(1.0 if p > n else 0.5 if p == n else 0.0
               for p in positive for n in negative) / (len(positive) * len(negative))


def _bootstrap_ci(values: list[float], *, seed: int = 20261018,
                  repetitions: int = 10000) -> list[float] | None:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values)
                   for _ in range(repetitions))
    return [means[int(0.025 * repetitions)], means[int(0.975 * repetitions) - 1]]


def _score(rows: list[dict], method: str, *, seed: int = 20261018) -> dict:
    if not rows:
        return {"n_groups": 0, "positive_groups": 0, "brier": None,
                "log_loss": None, "roc_auc_of_probability_ranking": None,
                "mean_probability": None,
                "brier_delta_vs_pooled_beta_baseline": None,
                "paired_config_bootstrap_95ci_brier_delta": None,
                "paired_wsun_week_cluster_bootstrap_95ci_brier_delta": None,
                "week_cluster_bootstrap_calendar_weeks": 0,
                "week_cluster_bootstrap_valid_replicates": 0}
    if method not in rows[0]:
        raise ValueError(f"prediction rows have no probability for method {method!r}")
    if any(not math.isfinite(float(row[method])) or not 0.0 <= float(row[method]) <= 1.0
           for row in rows):
        raise ValueError(f"method {method!r} emitted an invalid probability")
    ys = [int(row["outcome"]) for row in rows]
    ps = [float(row[method]) for row in rows]
    deltas = [(p-y)**2 - (float(row["base_rate"])-y)**2
              for p, y, row in zip(ps, ys, rows)]
    week_ci = _week_cluster_ci(rows, method, seed=seed + 1)
    return {
        "n_groups": len(rows),
        "positive_groups": sum(ys),
        "brier": sum((p-y)**2 for p, y in zip(ps, ys)) / len(ys),
        "log_loss": _logloss(ps, ys),
        "roc_auc_of_probability_ranking": _auc(ps, ys),
        "mean_probability": sum(ps) / len(ps),
        "brier_delta_vs_pooled_beta_baseline": sum(deltas) / len(deltas),
        "paired_config_bootstrap_95ci_brier_delta": _bootstrap_ci(deltas, seed=seed),
        "paired_wsun_week_cluster_bootstrap_95ci_brier_delta": week_ci["ci"],
        "week_cluster_bootstrap_calendar_weeks": week_ci["calendar_week_clusters"],
        "week_cluster_bootstrap_valid_replicates": week_ci["valid_replicates"],
        "uncertainty_note": (
            "Configuration resampling assumes IID configs; calendar-week cluster "
            "resampling uses only a few weeks in one month. Neither interval can "
            "establish regime generalization."
        ),
    }


def run() -> dict:
    source_rows, observations, _phase4_missing = phase4_replay.load_observations()
    execution_at = _execution_times(source_rows)
    # Full experiment_config is the measured-treatment identity. Phase 4's
    # short field projection collapsed scientifically different ablations,
    # estimators, thresholds, and calibration settings into just 12 keys.
    grouped: dict[str, list[dict]] = {}
    no_execution_time = 0
    missing_result_ids = []
    missing_spec_ids = []
    attempt_records: list[dict] = []
    for observation in observations:
        if not observation.experiment_id:
            continue  # pre-execution refusals remain counted, not model labels
        experiment_id = observation.experiment_id
        execute = execution_at.get(experiment_id)
        if execute is None:
            no_execution_time += 1
            continue
        config_id, link_status, config = _config_group(experiment_id)
        result_path = ROOT / "autonomous_agent" / "candidates" / experiment_id / "result.json"
        status = observation.outcome_status or ranking._status(observation)
        if link_status != "linked":
            missing_spec_ids.append(experiment_id)
        if not result_path.is_file():
            missing_result_ids.append(experiment_id)
            if status in ranking.ADJUDICATED_STATUSES:
                status = "unverifiable"
        record = {
            "config_id": config_id,
            "experiment_id": experiment_id,
            "execute_at": execute,
            "known_at": observation.at,
            "direction": observation.direction,
            "status": status,
            "passed": observation.passed if status in ranking.ADJUDICATED_STATUSES else None,
            "proposal_id": observation.proposal_id,
            "link_status": link_status,
            "treatment_key": _treatment_identity(config, include_calibration_bins=False),
            "treatment_with_bins_key": _treatment_identity(config, include_calibration_bins=True),
            "decision_profile": _decision_profile(config),
        }
        attempt_records.append(record)
        grouped.setdefault(config_id, []).append(record)

    # One target per full config: the earliest adjudicated result with a linked
    # result artifact. Missing/failed/refused outcomes are retained in counts,
    # but cannot be coerced to candidate-quality failures.
    targets = []
    for config_id, attempts in grouped.items():
        adjudicated = [row for row in attempts
                       if row["status"] in ranking.ADJUDICATED_STATUSES
                       and row["passed"] is not None]
        if not adjudicated:
            continue
        # A group contributes once at its first execution. If that execution
        # fails/is inconclusive or loses its result link, do not replace it
        # with a later successful run as though the first had never happened.
        attempts.sort(key=lambda row: (ranking._time_key(row["execute_at"]),
                                       row["experiment_id"]))
        first_execution_at = attempts[0]["execute_at"]
        first_cohort = [row for row in attempts
                        if ranking._time_key(row["execute_at"])
                        == ranking._time_key(first_execution_at)]
        first_cohort.sort(key=lambda row: row["experiment_id"])
        earliest_execution = first_cohort[0]
        target = next((row for row in adjudicated
                       if row["experiment_id"] == earliest_execution["experiment_id"]), None)
        if target is None:
            continue
        target["repeated_attempts_in_config"] = len(attempts)
        targets.append(target)
    targets.sort(key=lambda row: (ranking._time_key(row["execute_at"]),
                                  row["config_id"], row["experiment_id"]))

    # History is reveal-time based: the model sees outcomes only after their
    # terminal adjudication timestamp, and never sees any same-time cohort.
    # An adjudication after the next execution cannot be back-propagated to
    # the historical decision; use only labels already known as-of that time.
    execution_instants = sorted({ranking._time_key(value)
                                  for value in execution_at.values()})
    next_execution_by_time = {
        instant: execution_instants[index + 1]
        for index, instant in enumerate(execution_instants[:-1])
    }
    usable_history: list[ranking.Observation] = []
    predictions = []
    for target in targets:
        decision = target["execute_at"]
        decision_time = ranking._time_key(decision)
        next_decision = next_execution_by_time.get(decision_time)
        # The target contributes to future history only if it became known
        # before the next decision boundary. Delayed evidence remains target
        # information but does not enter any earlier subsequent score.
        known = [obs for obs in usable_history
                 if ranking._time_key(obs.at) < decision_time]
        base = _beta_base(known)
        candidate_id = target["direction"] or "unknown"
        family_key = candidate_id
        reg = ranking.regularized_candidate_probability(
            known, cutoff=decision, direction=candidate_id,
            primitive_id=target["config_id"], candidate_key=family_key,
            strength=4.0, base_rate=0.5)
        hybrid = ranking.conservative_hybrid_probability(
            known, cutoff=decision, direction=candidate_id,
            primitive_id=target["config_id"], candidate_key=family_key,
            min_groups=12, full_groups=30, strength=4.0, base_rate=0.5)
        n_groups = len(ranking._effective_adjudicated_groups(known))
        # UCB is an acquisition/ranking value, not a probability. Its AUC is
        # reported only as a ranking diagnostic; it is never scored with Brier.
        warmup = max(0.0, min(1.0, (n_groups - 3) / 9.0))
        ucb = min(float(reg["mean"]) + 0.25 * float(reg["sd"]) * warmup, 1.0)
        predictions.append({
            "config_id": target["config_id"],
            "treatment_key": target["treatment_key"],
            "treatment_with_bins_key": target["treatment_with_bins_key"],
            "decision_profile": target["decision_profile"],
            "experiment_id": target["experiment_id"],
            "execute_at": decision,
            "known_at": target["known_at"],
            "direction": candidate_id,
            "outcome": int(bool(target["passed"])),
            "base_rate": base,
            "regularized": float(reg["mean"]),
            "hybrid": float(hybrid["mean"]),
            "hybrid_weight": float(hybrid["weight"]),
            "ucb_acquisition": ucb,
            "regularized_sd": float(reg["sd"]),
            "history_groups": n_groups,
            "history_same_direction_configs": int(reg["n_direction_groups"]),
            "repeated_attempts_in_config": target["repeated_attempts_in_config"],
        })
        # Reveal this group only at the first adjudication terminal time.
        known_at = ranking._time_key(target["known_at"])
        reveal_before_next = next_decision is None or known_at < next_decision
        target["revealed_before_next_decision"] = reveal_before_next
        target["decision_to_adjudication_hours"] = (
            known_at - decision_time).total_seconds() / 3600.0
        prediction = next(row for row in predictions
                          if row["experiment_id"] == target["experiment_id"])
        prediction["revealed_before_next_decision"] = reveal_before_next
        prediction["decision_to_adjudication_hours"] = target["decision_to_adjudication_hours"]
        # Store the outcome timestamp, not a pre-filtered reveal event. At each
        # later execution the strict as-of filter can then include a delayed
        # result only once it has actually become known.
        usable_history.append(ranking.Observation(
            at=target["known_at"], direction=candidate_id,
            proposal_class="historical-proposal", primitive_id=target["config_id"],
            passed=bool(target["passed"]), outcome_status=target["status"],
            experiment_id=target["experiment_id"], proposal_id=target["proposal_id"],
            selection_key=family_key))

    if not predictions:
        raise RuntimeError("no fully-linked first-config adjudications available")
    # The test-time predictions are strictly prequential. The median-time
    # boundary is fixed from execution times, without using outcomes.
    ordered_times = sorted(ranking._time_key(value) for value in execution_at.values())
    boundary = ordered_times[len(ordered_times) // 2]
    later = [row for row in predictions
             if ranking._time_key(row["execute_at"]) >= boundary]

    from collections import Counter

    status_counts: dict[str, int] = defaultdict(int)
    for record in attempt_records:
        status_counts[record["status"]] += 1
    # Report operation lifecycle statuses separately from labels: no forced
    # collapse of missing-result, failed, refused, or inconclusive attempts.
    attempt_rows_with_refusals = [*attempt_records]
    attempt_rows_with_refusals.extend(
        {"status": ranking._status(obs), "experiment_id": None,
         "config_id": None, "direction": obs.direction}
        for obs in observations if obs.experiment_id is None)
    all_status_counts: dict[str, int] = defaultdict(int)
    for record in attempt_rows_with_refusals:
        all_status_counts[record["status"]] += 1
    for status in ranking.OUTCOME_STATUSES:
        all_status_counts.setdefault(status, 0)
    grouped_status_counts: dict[str, int] = defaultdict(int)
    for record in attempt_records:
        grouped_status_counts[record["status"]] += 1
    result = {
        "schema": "phase5-asof-experiment-selector-replay-v1",
        "source_ledger_sha256": hashlib.sha256(
            phase4_replay.LEDGER.read_bytes()).hexdigest(),
        "source_ledger_rows": len(source_rows),
        "source_execution_attempts": sum(1 for row in source_rows
                                          if row.get("row_type") == "transition"
                                          and row.get("to") == "EXECUTED"),
        "source_adjudication_rows": sum(1 for row in source_rows
                                         if row.get("row_type") == "transition"
                                         and row.get("to") == "ADJUDICATED"),
        "lifecycle_status_counts_including_refusals": dict(sorted(all_status_counts.items())),
        "execution_lifecycle_count_reconciliation": {
            "ledger_executed": sum(1 for row in source_rows
                                    if row.get("row_type") == "transition"
                                    and row.get("to") == "EXECUTED"),
            "execution_attempt_rows_with_ids": len(attempt_records),
            "execution_attempt_rows_without_spec_config": sum(
                1 for row in attempt_records if row["link_status"] != "linked"),
            "pre_execution_refusals": sum(1 for obs in observations if obs.experiment_id is None),
            "note": "Per-attempt records are exact. Missing spec/result is an artifact-link dimension, not a new outcome label; missing-result attempts retain their ledger status and are excluded from binary prediction targets.",
        },
        "grouped_linked_attempt_status_counts": dict(sorted(status_counts.items())),
        "status_counts_by_link_status": {
            link: dict(sorted(Counter(
                row["status"] for row in attempt_records
                if row["link_status"] == link).items()))
            for link in sorted({row["link_status"] for row in attempt_records})
        },
        "status_counts_by_spec_result_link": {
            f"spec_{spec}_result_{result}": dict(sorted(Counter(
                row["status"] for row in attempt_records
                if (row["link_status"] == "linked")
                and ((ROOT / "autonomous_agent" / "candidates" /
                      row["experiment_id"] / "spec.json").is_file() == spec)
                and ((ROOT / "autonomous_agent" / "candidates" /
                      row["experiment_id"] / "result.json").is_file() == result)
            ).items()))
            for spec, result in ((True, True), (True, False),
                                 (False, True), (False, False))
        },
        "refused_proposals_preserved_but_not_scored": sum(
            1 for obs in observations if obs.experiment_id is None),
        "inconclusive_execution_count": all_status_counts["inconclusive"],
        "failed_execution_count": all_status_counts["failed"],
        "missing_result_unverifiable_count": all_status_counts["unverifiable"],
        "linked_spec_missing_ids": sorted(set(missing_spec_ids)),
        "linked_result_missing_ids": sorted(set(missing_result_ids)),
        "no_execution_timestamp_count": no_execution_time,
        "measurement_groups_total": len(grouped),
        "measurement_groups_scored": len(predictions),
        "eligible_first_execution_groups": len(targets),
        "excluded_groups_without_binary_first_linked_execution": len(grouped) - len(targets),
        "target_identity_diagnostics": _target_identity_diagnostics(attempt_records),
        "candidate_family_diagnostics_all_rows": _direction_summary(predictions),
        "candidate_family_prior_only_diagnostics": {
            direction: {"prior_scored_groups": sum(
                            1 for row in predictions
                            if row["direction"] == direction and row["history_same_direction_configs"] > 0),
                        "status": "descriptive only; no predictive-quality target"}
            for direction in sorted({row["direction"] for row in predictions})
        },
        "candidate_family_diagnostics_later_period": _direction_summary(later),
        "scoring_target": "first fully linked binary adjudication (ACCEPTED/criteria-passed success vs criteria rejection) per exact full experiment_config; not market AUC, return, or profitability",
        "replay_artifact_sha256": "computed after canonical JSON serialization without this field",
        "candidate_identity": "proposal direction as the reusable selection family; full experiment_config hash as the independent measurement group",
        "fixed_first_time_second_half": {
            "boundary_from_all_execution_times": sorted(execution_at.values())[len(execution_at) // 2],
            "assignment": "predictions at or after fixed median execution-time boundary; used descriptively, without outcome-based boundary choice",
        },
        "as_of_cutoff_rule": "execution timestamp strictly less than outcome-known-at timestamp, and only outcome-known-at timestamps strictly earlier than the next execution; rows with adjudication known after the decision are not replay-trainable",
        "decision_time": "EXECUTED transition timestamp; history contains only previous group adjudications with known_at strictly before decision_time; simultaneous decisions are batched",
        "history_months": sorted({row["known_at"][:7] for row in predictions}),
        "timeline": {
            "first_execution": min(execution_at.values()),
            "last_execution": max(execution_at.values()),
            "distinct_execution_days": len({value[:10] for value in execution_at.values()}),
            "distinct_execution_weeks": len({
                ranking._time_key(value).date().isocalendar()[:2]
                for value in execution_at.values()}),
            "maximum_gap_between_execution_days": max((
                (ranking._time_key(day) - ranking._time_key(previous)).days
                for previous, day in zip(sorted({value[:10] for value in execution_at.values()}),
                                         sorted({value[:10] for value in execution_at.values()})[1:])
            ), default=0),
        },
        "unique_wsun_blocks": len({ranking._time_key(row["execute_at"]).date().isocalendar()[:2]
                                    for row in predictions}),
        "attempt_outcome_semantics": {
            "success": "ledger adjudication says criteria passed and recorded result ACCEPTED; process-gate success only",
            "rejected": "criteria evaluation rejected; process-gate label only",
            "failed": "execution/runtime or non-statistical safety/integrity failure, never coerced to predictive negative",
            "inconclusive": "executed but no binary adjudication, never coerced to either class",
            "unverifiable": "binary-looking adjudication without required linked spec/result artifact, not scored",
            "refused": "pre-execution refusal, preserved outside executed config outcomes",
        },
        "methods": {
            "calibrated_pooled_beta": "Beta(1,1) pooled group pass-rate; no learned candidate preference.",
            "regularized_direction_beta": "Beta(4) candidate-family preference, pooled 25% toward the direction rate and 75% global rate; equal-weight config votes.",
            "conservative_hybrid": "pooled Beta baseline until 12 prior independent groups within the candidate direction, then linearly blend through 30; thresholds fixed before replay, not optimized here.",
            "ucb_acquisition": "regularized mean + 0.25 posterior SD with a 3-to-12-group warm-up, clipped at 1; ranking-only, not a calibrated probability.",
        },
        "all_first_config_predictions": {
            method: _score(predictions, method)
            for method in ("base_rate", "regularized", "hybrid")
        },
        "experimental_candidate_family_quality_unidentified": {
            "identified": False,
            "reason": "Historical gate pass/reject outcomes are not counterfactual candidate predictive quality. Only a small, policy-selected set of configurations was executed; candidate direction, execution time, numeric success thresholds, and proposal difficulty are confounded. No off-policy ranking comparison is estimable from the observed ledger.",
            "retention_decision": "Keep the pooled prior as default; retain direction regularization and hybrid as quarantined development-only experiments, not a winning learner.",
        },
        "asof_rate_baseline": _score(predictions, "base_rate"),
        "asof_learned_direction_regularization": _score(predictions, "regularized"),
        "asof_conservative_hybrid": _score(predictions, "hybrid"),
        "as_of_reveal_diagnostics": {
            "scored_targets_revealed_before_next_decision": sum(
                bool(row["revealed_before_next_decision"]) for row in predictions),
            "scored_targets_revealed_after_next_decision": sum(
                not bool(row["revealed_before_next_decision"]) for row in predictions),
            "max_delay_hours": max(float(row["decision_to_adjudication_hours"])
                                    for row in predictions),
            "note": "Later adjudications are excluded from history before intervening execution points; history is only appended when known by the next decision time.",
        },
        "fixed_chronological_second_half": {
            "split_definition": "boundary is the execution-time median over all executed attempts (including those excluded from binary scoring); target config predictions on/after it are reported as chronological later-period outcomes",
            "time_boundary": boundary.isoformat(),
            "predictions": len(later),
            "methods": {method: _score(later, method, seed=20261019)
                        for method in ("base_rate", "regularized", "hybrid")},
            "ucb_roc_auc_ranking_only": _auc(
                [row["ucb_acquisition"] for row in later],
                [int(row["outcome"]) for row in later]),
            "pooled_baseline_roc_auc_ranking_only": _auc(
                [row["base_rate"] for row in later],
                [int(row["outcome"]) for row in later]),
        },
        "all_prediction_rows": predictions,
        "limitations": [
            "Acceptance/adjudication is a process-gate target, not candidate predictive quality or market performance.",
            "Only one short campaign month and two W-SUN weeks are represented; chronological CIs are weak.",
            "The realized policy chose which proposals were executed; rejected/unselected alternatives have no observed counterfactual outcomes, so off-policy utility cannot be identified.",
            "The logged primary metric is success under variable statistical/gating criteria, not market predictive quality. First full-config grouping leaves 66 groups but many have only one point; scientific treatment-equivalent config collapsing leaves only about a dozen groups and mixes repeated trials with time-varying exposure, so neither gives a causal policy comparison.",
            "The direction-level learner cannot estimate candidate quality: direction labels pool heterogeneous arms, estimators, thresholds, seed sets, and campaign phases; the apparent high pass rate in later days is confounded by changing direction mix and rising global prevalence.",
            "Direction is strongly confounded with proposal difficulty, criteria, generation policy, and campaign batch.",
            "Missing result artifacts are labeled unverifiable and excluded from binary scores; failed runs and pre-execution refusals are not false candidate labels.",
        ],
    }
    result.pop("replay_artifact_sha256", None)
    result["replay_artifact_sha256"] = _hash_json(result)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
