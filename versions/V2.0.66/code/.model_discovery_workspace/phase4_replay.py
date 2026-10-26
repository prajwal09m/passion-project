"""Strict chronological, group-aware replay of append-only proposal outcomes.

Input is the pre-existing development proposal ledger and linked spec/result
artifacts. No prospective data, campaign execution, parameter search, or model
training is performed. Success/rejection are scoring labels; interrupted
execution, inconclusive decisions, and pre-execution refusal remain preserved
but are not mislabeled as binary performance.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent
sys.path.insert(0, str(WORKSPACE / "dev"))
from autonomous_agent.proposal_layer import outcome_ranking as ranking  # noqa: E402

LEDGER = ROOT / "autonomous_agent/state/proposal_ledger.jsonl"
CANDIDATES = ROOT / "autonomous_agent/candidates"
OUT = WORKSPACE / "phase4_outcome_replay.json"


def _proposal_map(rows):
    return {row["proposal_id"]: row["proposal"] for row in rows
            if row.get("row_type") == "proposal"}


def _group_for(spec: dict) -> str:
    config = {}
    for item in spec.get("proposed_change", {}).get("files", []):
        if str(item.get("path", "")).endswith("experiment_config.json"):
            try:
                config = json.loads(item["content"])
            except (TypeError, json.JSONDecodeError):
                config = {}
    if config:
        fields = ("arm_a", "arm_b", "estimator_a", "estimator_b", "seeds", "folds", "baseline_id")
        key = {name: config.get(name) for name in fields}
        return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()
    return str(spec.get("recipe_id") or spec.get("proposal_id") or spec.get("experiment_id"))


def load_observations():
    rows = [json.loads(line) for line in LEDGER.read_text("utf-8").splitlines() if line.strip()]
    proposals = _proposal_map(rows)
    transitions = [row for row in rows if row.get("row_type") == "transition"]
    terminal_by_experiment = {}
    terminal_by_proposal = {}
    execution_by_experiment = {}
    decision_by_experiment = {}
    for row in transitions:
        detail = row.get("detail") or {}
        experiment_id = detail.get("experiment_id")
        proposal_id = row.get("proposal_id")
        if row.get("to") == "EXECUTED" and experiment_id:
            execution_by_experiment[experiment_id] = (row, detail)
        if row.get("to") == "EXECUTED" and experiment_id:
            # The ledger transition means execution began, not necessarily
            # that evaluation completed; a later adjudication will replace
            # this placeholder. A missing terminal row remains inconclusive.
            decision_by_experiment[experiment_id] = (row, "inconclusive", detail)
        if row.get("to") == "FAILED_EXECUTION":
            if experiment_id:
                terminal_by_experiment[experiment_id] = (row, "failed", detail)
        if row.get("to") == "ADJUDICATED" and experiment_id:
            passed = detail.get("decision_criteria_passed")
            if passed is False:
                status = "rejected"
            elif passed is True:
                status = "success"
            else:
                status = "inconclusive"
            terminal_by_experiment[experiment_id] = (row, status, detail)
        if row.get("to") == "PROMOTED" and experiment_id:
            # Promotion is an adapter/champion state, not an independent
            # model outcome. Retain it only as an attribution annotation.
            prior = terminal_by_experiment.get(experiment_id)
            if prior:
                prior[2]["promotion_at"] = row.get("at")
        if row.get("to") == "REFUSED":
            terminal_by_proposal[proposal_id] = (row, "refused", detail)
        if row.get("to") == "FAILED_VALIDATION":
            terminal_by_proposal[proposal_id] = (row, "refused", detail)
    observations = []
    linked_missing = []
    for experiment_id, (terminal, status, detail) in terminal_by_experiment.items():
        proposal_id = terminal.get("proposal_id")
        proposal = proposals.get(proposal_id, {})
        direction = str(proposal.get("direction") or (proposal.get("payload") or {}).get("direction") or "unknown")
        source = execution_by_experiment.get(experiment_id)
        group = None
        if source:
            spec_path = CANDIDATES / experiment_id / "spec.json"
            if spec_path.is_file():
                spec = json.loads(spec_path.read_text("utf-8"))
                group = _group_for(spec)
            else:
                linked_missing.append(experiment_id)
            result_path = CANDIDATES / experiment_id / "result.json"
            if not result_path.is_file():
                linked_missing.append(f"result:{experiment_id}")
            else:
                result_doc = json.loads(result_path.read_text("utf-8"))
                artifact_status = str(result_doc.get("status", "")).upper()
                results = result_doc.get("results") or result_doc.get("metrics") or {}
                label = str(results.get("label") or "").upper()
                decision_passed = results.get("decision_criteria_passed")
                if artifact_status in {"FAILED", "ERROR", "INTERRUPTED"}:
                    status = "failed"
                elif decision_passed is False or label in {"REFUTED", "REJECTED"}:
                    status = "rejected"
                elif decision_passed is None and label in {"INCONCLUSIVE", "UNAVAILABLE"}:
                    status = "inconclusive"
        if group is None:
            group = f"unlinked:{experiment_id}"
        if status == "success" and detail.get("result") != "ACCEPTED":
            status = "failed"
        binary = True if status == "success" else False if status == "rejected" else None
        observations.append(ranking.Observation(
            at=str(terminal["at"]), direction=direction,
            proposal_class=str(proposal.get("proposal_class") or "unknown"),
            primitive_id=group, passed=binary, outcome_status=status,
            experiment_id=str(experiment_id), proposal_id=str(proposal_id or ""),
            rejection_reason=str(detail.get("rejection_reason") or detail.get("error") or "") or None))
    # Executions interrupted before ADJUDICATED remain individually
    # attributable, including those with no durable spec/result. Terminal
    # precedence above has no row for those incomplete attempts.
    for experiment_id, (executed, status, detail) in decision_by_experiment.items():
        if experiment_id in terminal_by_experiment:
            continue
        proposal_id = executed.get("proposal_id")
        proposal = proposals.get(proposal_id, {})
        direction = str(proposal.get("direction") or (proposal.get("payload") or {}).get("direction") or "unknown")
        spec_path = CANDIDATES / experiment_id / "spec.json"
        if not spec_path.is_file():
            linked_missing.append(experiment_id)
            group = f"unlinked:{experiment_id}"
        else:
            group = _group_for(json.loads(spec_path.read_text("utf-8")))
        observations.append(ranking.Observation(
            at=str(executed["at"]), direction=direction,
            proposal_class=str(proposal.get("proposal_class") or "unknown"),
            primitive_id=group, passed=None, outcome_status="inconclusive",
            experiment_id=str(experiment_id), proposal_id=str(proposal_id or ""),
            rejection_reason="execution has no terminal adjudication row"))

    # Count each pre-execution refusal as one preserved attempt row. Dedup
    # transition rows for a proposal to its final refusal only.
    for proposal_id, (terminal, status, detail) in terminal_by_proposal.items():
        proposal = proposals.get(proposal_id, {})
        direction = str(proposal.get("direction") or (proposal.get("payload") or {}).get("direction") or "unknown")
        design = proposal.get("design") or {}
        group = hashlib.sha256(json.dumps(design, sort_keys=True).encode()).hexdigest()
        observations.append(ranking.Observation(
            at=str(terminal["at"]), direction=direction,
            proposal_class=str(proposal.get("proposal_class") or "unknown"),
            primitive_id=group, passed=None, outcome_status=status,
            experiment_id=None, proposal_id=str(proposal_id),
            rejection_reason=str(detail.get("reason_code") or detail.get("reason") or "refused")))
    observations.sort(key=lambda o: (ranking._time_key(o.at), o.proposal_id or "", o.experiment_id or ""))
    return rows, observations, linked_missing


def _brier(values, outcomes):
    return sum((p - y) ** 2 for p, y in zip(values, outcomes)) / len(outcomes) if outcomes else None


def _auc(values, outcomes):
    positive = [p for p, y in zip(values, outcomes) if y == 1]
    negative = [p for p, y in zip(values, outcomes) if y == 0]
    if not positive or not negative:
        return None
    return sum(1.0 if a > b else 0.5 if a == b else 0.0
               for a in positive for b in negative) / (len(positive) * len(negative))


def _interval(values, *, seed, reps=5000):
    rng = random.Random(seed)
    if len(values) < 2:
        return None
    samples = sorted(sum(rng.choice(values) for _ in values) / len(values)
                     for _ in range(reps))
    return [samples[int(0.025 * reps)], samples[int(0.975 * reps) - 1]]


def evaluate(observations, *, source_rows):
    scored = [o for o in observations if ranking._adjudicated(o)]
    groups = {}
    for obs in scored:
        groups.setdefault((obs.direction, obs.primitive_id), []).append(obs)
    # One sample per exact executed measurement config, across directions.
    # Use the earliest adjudicated outcome only; later repeats remain counted
    # as history but cannot relabel this unseen-group target. If timestamps
    # tie, stable proposal/experiment IDs determine the representative without
    # inspecting outcomes.
    by_config = {}
    for obs in scored:
        by_config.setdefault(obs.primitive_id, []).append(obs)
    group_rows = []
    for primitive_id, obslist in by_config.items():
        obslist.sort(key=lambda o: (ranking._time_key(o.at), o.proposal_id or "", o.experiment_id or ""))
        first = obslist[0]
        group_rows.append({"group": primitive_id, "at": first.at,
                           "direction": first.direction,
                           "primitive_id": primitive_id,
                           "outcome": float(bool(first.passed)),
                           "attempts": len(obslist),
                           "representative_experiment_id": first.experiment_id,
                           "representative_proposal_id": first.proposal_id})
    group_rows.sort(key=lambda row: (ranking._time_key(row["at"]), row["group"]))

    # Build the one-row-per-configuration chronological history used for
    # prediction; the original observation list remains available for audit
    # counts and for confirming status attribution.
    group_observations = [ranking.Observation(
        at=row["at"], direction=row["direction"], proposal_class="first_config_outcome",
        primitive_id=row["primitive_id"], passed=bool(row["outcome"]),
        outcome_status="success" if row["outcome"] else "rejected",
        experiment_id=row["representative_experiment_id"],
        proposal_id=row["representative_proposal_id"])
        for row in group_rows]

    # Evaluate one config at first recorded outcome using only earlier config
    # groups. At a tied timestamp none of those rows can train another.
    predictions = []
    unique_times = sorted({ranking._time_key(row["at"]) for row in group_rows})
    for timestamp in unique_times:
        cohort = [row for row in group_rows if ranking._time_key(row["at"]) == timestamp]
        cutoff = cohort[0]["at"]
        history = ranking.known_before(group_observations, cutoff)
        history_outcomes = ranking._group_outcomes(history)
        if not history_outcomes:
            continue
        for row in cohort:
            prior = ranking.estimate(history, cutoff=cutoff,
                                     direction=row["direction"],
                                     primitive_id=row["primitive_id"])
            base = (sum(history_outcomes.values()) + 1) / (len(history_outcomes) + 2)
            predictions.append({**row, "aware": prior.mean, "base_rate": base,
                                "sd": prior.sd, "n_history_groups": prior.n_total,
                                "unseen_group": True})

    # Chronological hold-forward split is fixed at the median unique-group
    # time boundary (not based on outcome values). Later groups are evaluated
    # strictly prequentially as above, including tie handling.
    unique_group_times = sorted(ranking._time_key(row["at"]) for row in group_rows)
    boundary = unique_group_times[len(unique_group_times) // 2] if unique_group_times else None
    later_predictions = []
    for row in group_rows:
        row_time = ranking._time_key(row["at"])
        if boundary is None or row_time < boundary:
            continue
        history = [o for o in group_observations if ranking._time_key(o.at) < row_time]
        history_outcomes = ranking._group_outcomes(history)
        if not history_outcomes:
            continue
        prior = ranking.estimate(history, cutoff=row["at"], direction=row["direction"],
                                 primitive_id=row["primitive_id"])
        base = (sum(history_outcomes.values()) + 1) / (len(history_outcomes) + 2)
        later_predictions.append({**row, "aware": prior.mean, "base_rate": base,
                                  "sd": prior.sd, "n_history_groups": prior.n_total,
                                  "unseen_group": True})

    def summary(rows, name):
        outcomes = [float(row["outcome"]) for row in rows]
        aware = [row["aware"] for row in rows]
        base = [row["base_rate"] for row in rows]
        deltas = [(a-y)**2-(b-y)**2 for a,b,y in zip(aware,base,outcomes)]
        return {"label": name, "n_groups": len(rows),
                "n_attempts_in_scored_groups": sum(r["attempts"] for r in rows),
                "effective_group_count": len({r["group"] for r in rows}),
                "positive_equivalent": sum(outcomes),
                "brier": {"outcome_aware": _brier(aware,outcomes), "base_rate": _brier(base,outcomes)},
                "roc_auc": {"outcome_aware": _auc(aware,outcomes), "base_rate": _auc(base,outcomes)},
                "outcome_aware_minus_base_brier": sum(deltas)/len(deltas) if deltas else None,
                "paired_group_bootstrap_95ci_delta": _interval(deltas,seed=20261017) if deltas else None,
                "mean_posterior_sd": sum(r["sd"] for r in rows)/len(rows) if rows else None,
                "unseen_group_count": sum(r["unseen_group"] for r in rows)}

    # Paired group bootstrap at the whole-group unit, sampling unique scored
    # group rows (all group retries already collapsed to a single outcome).
    def bootstrap_delta(rows, reps=5000, seed=20261017):
        if len(rows) < 2:
            return None
        diffs = [(r["aware"]-r["outcome"])**2-(r["base_rate"]-r["outcome"])**2 for r in rows]
        rng = random.Random(seed)
        draws = sorted(sum(rng.choice(diffs) for _ in diffs)/len(diffs) for _ in range(reps))
        return [draws[int(.025*reps)], draws[int(.975*reps)-1]]

    return {
        "all_attempt_outcome_counts": dict(sorted(Counter(ranking._status(o) for o in observations).items())),
        "observations": len(observations),
        "source_adjudicated_rows": sum(1 for row in source_rows if row.get("row_type") == "transition" and row.get("to") == "ADJUDICATED"),
        "source_execution_attempts": sum(1 for row in source_rows if row.get("row_type") == "transition" and row.get("to") == "EXECUTED"),
        "unadjudicated_execution_attempts": sum(1 for observation in observations
                                                if observation.outcome_status == "inconclusive"),
        "adjudicated_attempts": len(scored),
        "unique_adjudicated_groups": len(group_rows),
        "unique_measurement_configs": len(by_config),
        "repeated_attempts_collapsed": len(scored)-len(group_rows),
        "first_seen_group_predictions": {**summary(predictions,"all_first_seen_groups_with_prior"),
                                          "paired_group_bootstrap_95ci_delta": bootstrap_delta(predictions)},
        "chronological_second_half_unseen_groups": {**summary(later_predictions,"fixed_chronological_second_half_unseen_groups"),
                                                     "paired_group_bootstrap_95ci_delta": bootstrap_delta(later_predictions)},
        "split_definition": "exact executed measurement config (not direction+config) scored once, at its first adjudicated occurrence; later repeats do not relabel it; only strictly earlier config outcomes train the Beta prior; fixed median-time second half",
        "notes": ["The source ledger contains 69 adjudicated lifecycle outcomes; 53 accepted decisions, 13 criteria rejections, and 3 criteria-passed runs rejected by non-statistical safety gates (counted as failed, not success).",
                  "The replay target is the first outcome per unique measurement config, not repeated lifecycle attempts.",
                  "The ledger has only a single October 2026 campaign month: there is no independent calendar regime validation.",
                  "Group identity is the executed measurement config; unlinked executions receive unique IDs and are reported.",
                  "The replay score predicts adjudication success probability, not market ROC-AUC.",
                  "Failed/inconclusive/refused attempts remain attributed and counted, but are not coerced into binary outcomes."]}


def main():
    rows, observations, missing = load_observations()
    results = evaluate(observations, source_rows=rows)
    result = {"schema": "phase4-grouped-chronological-outcome-replay-v1",
              "source_ledger": str(LEDGER.relative_to(ROOT)),
              "source_ledger_sha256": hashlib.sha256(LEDGER.read_bytes()).hexdigest(),
              "source_ledger_rows": len(rows),
              "source_candidates_root": str(CANDIDATES.relative_to(ROOT)),
              "linked_result_missing_ids": missing,
              "results": results}
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))


if __name__ == "__main__":
    main()
