"""Outcome-aware candidate priors (development only; not wired into production).

The estimate for a candidate is a Beta-smoothed pass rate. It is shrunk toward
its direction's rate, which is shrunk toward the overall rate, so sparse
groups fall back to broader evidence. Every estimate reports its effective
sample size and posterior standard deviation, so callers can see how little
evidence supports it.

Temporal discipline: ``known_before(history, cutoff)`` is the only way to
select history, and ``estimate`` refuses any observation at or after its
cutoff. A future outcome therefore cannot influence an earlier priority.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping, Sequence

OUTCOME_STATUSES = frozenset({"success", "rejected", "inconclusive", "failed", "refused", "unverifiable"})
ADJUDICATED_STATUSES = frozenset({"success", "rejected"})


def _time_key(value: str) -> datetime:
    """Parse an ISO-8601 instant; treat naive timestamps as UTC."""
    if not isinstance(value, str) or not value:
        raise ValueError("timestamps must be non-empty ISO-8601 strings")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _status(observation: "Observation") -> str:
    """Normalize legacy boolean-only rows and validate explicit outcomes."""
    status = observation.outcome_status
    if status is None:
        if not isinstance(observation.passed, bool):
            raise ValueError("only adjudicated boolean outcomes may inform the ranker")
        status = "success" if observation.passed else "rejected"
    if status not in OUTCOME_STATUSES:
        raise ValueError(f"unknown outcome status {status!r}")
    if status == "success" and observation.passed is not True:
        raise ValueError("success outcome must carry passed=True")
    if status == "rejected" and observation.passed is not False:
        raise ValueError("rejected outcome must carry passed=False")
    if status in {"inconclusive", "failed", "refused", "unverifiable"} and observation.passed is not None:
        raise ValueError(f"{status} outcomes must not be coerced to a boolean label")
    return status


def _adjudicated(observation: "Observation") -> bool:
    return _status(observation) in ADJUDICATED_STATUSES


def _label(observation: "Observation") -> float:
    if not _adjudicated(observation):
        raise ValueError("only success/rejected outcomes have a binary label")
    return 1.0 if observation.passed else 0.0


def _eligible(observations: Sequence["Observation"]) -> list["Observation"]:
    return [observation for observation in observations if _adjudicated(observation)]


def _group_votes(observations: Sequence["Observation"]) -> list[float]:
    """One bounded vote per measurement group, independent of proposal direction."""
    grouped: dict[str, list[float]] = {}
    for observation in _eligible(observations):
        grouped.setdefault(observation.primitive_id, []).append(_label(observation))
    return [sum(values) / len(values) for _, values in sorted(grouped.items())]


def _group_outcomes(observations: Sequence["Observation"]) -> dict[str, float]:
    """One equal-weight outcome per exact measurement group across directions."""
    grouped: dict[str, list[float]] = {}
    for observation in _eligible(observations):
        grouped.setdefault(observation.primitive_id, []).append(_label(observation))
    return {key: sum(values) / len(values) for key, values in grouped.items()}


def _grouped_measurement_votes(observations: Sequence["Observation"], *,
                               direction: str | None = None,
                               selection_key: str | None = None
                               ) -> dict[str, float]:
    """Average repeated adjudications within each exact config to one vote."""
    grouped: dict[str, list[float]] = {}
    for observation in _eligible(observations):
        if direction is not None and observation.direction != direction:
            continue
        if selection_key is not None and (observation.selection_key or observation.primitive_id) != selection_key:
            continue
        grouped.setdefault(observation.primitive_id, []).append(_label(observation))
    return {measurement_id: sum(votes) / len(votes)
            for measurement_id, votes in grouped.items()}


def _direction_group_outcomes(observations: Sequence["Observation"],
                              direction: str) -> dict[str, float]:
    """One bounded mean vote per independent config in a direction."""
    return _grouped_measurement_votes(observations, direction=direction)


def _candidate_group_outcomes(observations: Sequence["Observation"], *,
                              direction: str, primitive_id: str,
                              candidate_key: str | None = None) -> dict[str, float]:
    key = candidate_key or primitive_id
    if candidate_key is not None:
        return _grouped_measurement_votes(observations, direction=direction,
                                          selection_key=key)
    exact_group = {primitive_id: value for primitive_id, value in
                   _grouped_measurement_votes(observations, direction=direction).items()
                   if primitive_id == key}
    return exact_group


def _mean(values: Iterable[float], fallback: float) -> float:
    values = list(values)
    return sum(values) / len(values) if values else fallback


def _shrunk_probability(values: Sequence[float], parent_mean: float,
                        strength: float) -> float:
    return (sum(values) + strength * parent_mean) / (len(values) + strength)


def _probability_sd(mean: float, effective_n: float, strength: float) -> float:
    """Approximate Beta posterior SD with parent probability as prior mean."""
    a = mean * (effective_n + strength)
    b = (1.0 - mean) * (effective_n + strength)
    return math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1.0)))


def _percentile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _effective_adjudicated_groups(observations: Sequence["Observation"]) -> dict[str, float]:
    """Resolve each group's label as of the last adjudicated attempt before cutoff.

    Failed, refused, inconclusive, and missing outcomes do not become zeroes.
    Keeping one current adjudication per exact config avoids both repeat-count
    inflation and the first-attempt label's inability to learn later known
    outcomes.
    """
    return _grouped_measurement_votes(observations)


def _calibrated_beta_probability(values: Sequence[float], prior_mean: float,
                                 strength: float) -> tuple[float, float]:
    """Posterior beta mean/SD; fractional config votes retain one trial weight."""
    if not 0.0 < prior_mean < 1.0 or strength <= 0.0:
        raise ValueError("prior_mean must be inside (0,1) and strength positive")
    successes = sum(values)
    trials = float(len(values))
    alpha = prior_mean * strength + successes
    beta = (1.0 - prior_mean) * strength + trials - successes
    total = alpha + beta
    return alpha / total, math.sqrt(alpha * beta / (total * total * (total + 1.0)))


def _apply_hybrid(base: float, learned: float, n_groups: int, *, min_groups: int,
                  full_groups: int) -> tuple[float, float]:
    """Conservative shrinkage weight, exactly zero below minimum evidence."""
    if n_groups < min_groups:
        return base, 0.0
    weight = min(1.0, (n_groups - min_groups + 1) / (full_groups - min_groups + 1))
    return base + weight * (learned - base), weight


def unseen_group_estimates(history: Sequence["Observation"], *, cutoff: str,
                           direction: str, candidate_ids: Iterable[str]
                           ) -> list[tuple[str, "Estimate"]]:
    """Return calibrated priors only for groups absent from eligible history.

    This is the safe explore/exploit primitive for candidate selection: known
    evidence keys are not re-scored as novel; caller can use the posterior
    mean for exploitation and sd for uncertainty-aware exploration.
    """
    eligible_ids = set(_direction_group_outcomes(history, direction))
    result = []
    for candidate_id in sorted(set(candidate_ids) - eligible_ids):
        result.append((candidate_id, estimate(
            history, cutoff=cutoff, direction=direction,
            primitive_id=candidate_id)))
    return result


def _beta_mean_sd(successes: float, trials: float, prior_mean: float,
                  strength: float) -> tuple[float, float]:
    a = prior_mean * strength + successes
    b = (1.0 - prior_mean) * strength + (trials - successes)
    total = a + b
    mean = a / total
    sd = math.sqrt(a * b / (total * total * (total + 1.0)))
    return mean, sd


def _independent_group_outcomes(observations: Sequence["Observation"]) -> list[float]:
    """Compatibility alias for one bounded vote per eligible measurement group."""
    return _group_votes(observations)


class LeakageError(ValueError):
    """An observation at or after the decision cutoff was supplied."""


@dataclass(frozen=True)
class Observation:
    at: str                 # ISO-8601 time the outcome became known
    direction: str
    proposal_class: str
    primitive_id: str
    passed: bool | None
    outcome_status: str | None = None
    experiment_id: str | None = None
    proposal_id: str | None = None
    rejection_reason: str | None = None
    selection_key: str | None = None  # reusable candidate-family/context identity


@dataclass(frozen=True)
class Estimate:
    mean: float             # shrunk pass probability
    sd: float               # posterior standard deviation
    n_primitive: int
    n_direction: int
    n_total: int


def known_before(history: Iterable[Observation], cutoff: str) -> list[Observation]:
    """Keep all attempts known strictly before cutoff, comparing UTC instants."""
    cutoff_time = _time_key(cutoff)
    return [o for o in history if _time_key(o.at) < cutoff_time]


def _independent_group_outcomes(observations: Sequence[Observation]) -> list[float]:
    """Collapse valid adjudications per group; unscored attempts are not labels.

    Repeated ledger rows for the same primitive/configuration are not treated
    as independent trials. If adjudicated labels differ, the group has one
    fractional vote, but contributes only one effective trial. Inconclusive,
    interrupted, and refused attempts remain recorded but never become false.
    """
    return _group_votes(observations)


def estimate(history: Sequence[Observation], *, cutoff: str, direction: str,
             primitive_id: str, strength: float = 2.0,
             base_rate: float = 0.5,
             candidate_key: str | None = None) -> Estimate:
    """Shrunk pass estimate using only pre-cutoff, independent config groups.

    ``primitive_id`` is the canonical evidence-group identity in replay data.
    Repeated rows for one group contribute at most one trial to both the
    direction prior and the candidate estimate, preventing repeated campaigns
    from manufacturing posterior confidence.
    """
    cutoff_time = _time_key(cutoff)
    if any(_time_key(o.at) >= cutoff_time for o in history):
        raise LeakageError(f"observation at or after cutoff {cutoff} supplied to estimate()")
    for observation in history:
        _status(observation)
    if strength <= 0.0:
        raise ValueError("strength must be positive")
    if not 0.0 < base_rate < 1.0:
        raise ValueError("base_rate must lie strictly between 0 and 1")
    scored_history = _eligible(history)
    # All estimates use equal-weight config outcomes, never proposal direction
    # as an independent replicate. The direction estimate is a regularized
    # secondary term; it cannot manufacture global effective sample size.
    global_groups = _effective_adjudicated_groups(scored_history)
    global_mean = _mean(global_groups.values(), base_rate)
    direction_groups = _direction_group_outcomes(scored_history, direction)
    direction_mean = _mean(direction_groups.values(), global_mean)
    candidate_groups = _candidate_group_outcomes(
        scored_history, direction=direction, primitive_id=primitive_id,
        candidate_key=candidate_key)
    candidate_values = list(candidate_groups.values())
    mean = _shrunk_probability(candidate_values, direction_mean, strength)
    sd = _probability_sd(mean, len(candidate_values), strength)
    return Estimate(mean=mean, sd=sd, n_primitive=len(candidate_values),
                    n_direction=len(direction_groups), n_total=len(global_groups))


def rank_candidates(history: Sequence[Observation], *, cutoff: str,
                    direction: str, candidate_ids: Iterable[str],
                    exploration_weight: float = 0.0,
                    strength: float = 2.0,
                    base_rate: float = 0.5,
                    candidate_keys: Mapping[str, str] | None = None
                    ) -> list[dict[str, float | int | str | bool]]:
    """Rank development candidates with an explicit uncertainty exploration bonus.

    ``mean`` is a shrunk probability of prior adjudication success, not a
    forecast of market AUC. ``acquisition_value = mean + weight * sd`` is an
    optimism heuristic; it is not a calibrated probability and is not wired
    to a campaign. Ties are stable by candidate id. A positive weight makes
    unfamiliar groups with broader posterior uncertainty worth exploring,
    while zero weight ranks purely by historical mean.
    """
    if exploration_weight < 0.0 or not math.isfinite(exploration_weight):
        raise ValueError("exploration_weight must be finite and non-negative")
    if not math.isfinite(strength) or not 0.0 < base_rate < 1.0:
        raise ValueError("strength and base_rate must be finite valid priors")
    groups = _effective_adjudicated_groups(history)
    direction_groups = _direction_group_outcomes(history, direction)
    base_rate = _mean(groups.values(), base_rate)
    direction_rate = _mean(direction_groups.values(), base_rate)
    scored = []
    for candidate_id in sorted(set(candidate_ids)):
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("candidate_ids must be non-empty strings")
        candidate_key = (candidate_keys or {}).get(candidate_id, candidate_id)
        # This also validates strict as-of cutoff discipline before exposing a score.
        posterior = estimate(history, cutoff=cutoff, direction=direction,
                             primitive_id=candidate_id, strength=strength,
                             base_rate=base_rate, candidate_key=candidate_key)
        # Candidate prior: calibrated global rate + a small direction-specific
        # adjustment (one quarter of its deviation). Only repeated evidence
        # for the exact candidate family can move the estimate further.
        prior = min(0.95, max(0.05, base_rate + 0.25 * (direction_rate - base_rate)))
        candidate_groups = _candidate_group_outcomes(
            history, direction=direction, primitive_id=candidate_id,
            candidate_key=candidate_key)
        learned_values = list(candidate_groups.values())
        learned, learned_sd = _calibrated_beta_probability(
            learned_values, prior, strength)
        n_evidence = len(groups)
        # Exploration is UCB-style but capped and intentionally zero with a
        # single-digit independent evidence history (default capped weight is
        # not selected from evaluation outcomes).
        warmup = max(0.0, min(1.0, (n_evidence - 3) / 9.0))
        bonus = min(exploration_weight * learned_sd * warmup, 0.10)
        acquisition = learned + bonus
        observed = bool(candidate_groups)
        scored.append({
            "candidate_id": candidate_id,
            "mean": learned,
            "sd": learned_sd,
            "exploration_bonus": bonus,
            "acquisition_value": acquisition,
            "observed_before": observed,
            "n_primitive": len(learned_values),
            "n_direction": len(direction_groups),
            "n_total": n_evidence,
            "fallback_base_rate": base_rate,
        })
    return sorted(scored, key=lambda item: (-float(item["acquisition_value"]),
                                             str(item["candidate_id"])))


def regularized_candidate_probability(history: Sequence[Observation], *, cutoff: str,
                                      direction: str, primitive_id: str,
                                      strength: float = 4.0,
                                      base_rate: float = 0.5,
                                      candidate_key: str | None = None
                                      ) -> dict[str, float | int]:
    """Regularized beta-binomial estimate with pooled-group fallback.

    Each measurement config contributes exactly one current adjudicated vote.
    Direction rates are partially pooled toward the global mean. Failed and
    non-adjudicated rows remain audit observations but are not binary labels.
    """
    estimate(history, cutoff=cutoff, direction=direction,
             primitive_id=primitive_id, strength=strength,
             base_rate=base_rate)

    eligible = _effective_adjudicated_groups(_eligible(history))
    global_rate = _mean(eligible.values(), base_rate)
    direction_groups = _direction_group_outcomes(history, direction)
    direction_rate = _mean(direction_groups.values(), global_rate)
    candidate = _candidate_group_outcomes(history, direction=direction,
                                          primitive_id=primitive_id,
                                          candidate_key=candidate_key)
    prior = min(0.95, max(0.05,
                          global_rate + 0.25 * (direction_rate - global_rate)))
    mean, sd = _calibrated_beta_probability(list(candidate.values()), prior,
                                            strength)
    return {"mean": mean, "sd": sd, "n_candidate_groups": len(candidate),
            "n_direction_groups": len(direction_groups),
            "n_global_groups": len(eligible), "prior_mean": prior}


def conservative_hybrid_probability(history: Sequence[Observation], *, cutoff: str,
                                    direction: str, primitive_id: str,
                                    min_groups: int = 12, full_groups: int = 30,
                                    strength: float = 4.0,
                                    base_rate: float = 0.5,
                                    candidate_key: str | None = None
                                    ) -> dict[str, float | int]:
    """Keep pooled base rate until enough independent groups; then shrink in.

    The thresholds are explicit development defaults, not optimized on replay.
    The method is an evaluation candidate only; it is not campaign integrated.
    """
    if min_groups < 1 or full_groups < min_groups:
        raise ValueError("require 1 <= min_groups <= full_groups")
    eligible = _effective_adjudicated_groups(_eligible(history))
    direction_groups = _direction_group_outcomes(history, direction)
    pooled = _mean(eligible.values(), base_rate)
    regularized = regularized_candidate_probability(
        history, cutoff=cutoff, direction=direction, primitive_id=primitive_id,
        strength=strength, base_rate=base_rate, candidate_key=candidate_key)
    # The learned term is direction-specific. Unrelated directions must not
    # satisfy its evidence threshold; otherwise a large global ledger could
    # activate a preference supported by only one or two same-family groups.
    blend_groups = len(direction_groups)
    hybrid, weight = _apply_hybrid(
        pooled, float(regularized["mean"]), blend_groups,
        min_groups=min_groups, full_groups=full_groups)
    return {"mean": hybrid, "weight": weight,
            "n_global_groups": len(eligible),
            "n_direction_groups": blend_groups,
            "n_blend_groups": blend_groups,
            "regularized_mean": float(regularized["mean"]),
            "pooled_base_rate": pooled,
            "sd": float(regularized["sd"])}


def outcome_group_counts(history: Sequence[Observation]) -> dict[str, int]:
    """Count all preserved statuses separately from eligible evidence groups."""
    statuses = {status: 0 for status in sorted(OUTCOME_STATUSES)}
    for observation in history:
        statuses[_status(observation)] += 1
    return {"rows": len(history),
            "adjudicated_rows": sum(statuses[s] for s in ADJUDICATED_STATUSES),
            "independent_groups": len(_effective_adjudicated_groups(history)),
            "status_counts": statuses}


def brier(predictions: Sequence[float], outcomes: Sequence[bool]) -> float:
    if len(predictions) != len(outcomes) or not predictions:
        raise ValueError("predictions and outcomes must be non-empty and equal length")
    return sum((p - (1.0 if y else 0.0)) ** 2 for p, y in zip(predictions, outcomes)) / len(predictions)
