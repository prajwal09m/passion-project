"""Deterministic synthetic-fixture benchmark for isolated candidate search v2.

Usage (from workspace root):
  py -3 candidate_search_v2_benchmark.py [output.json]

No repository ledger, market dataset, or sealed holdout is read. Both baseline
and v2 get the same synthetic fixture columns, dataset/split IDs, and proposal
budget. The legacy comparison is structurally represented by the known closed
4-arm/2-estimator space: with the 12 frozen evidence keys already measured,
legacy has no distinct remaining evidence (dedup mode stalls); without dedup,
it can only return historically redundant keys. V2 is measured over newly
versioned synthetic candidate identities, so the benchmark reports distinct
engineering-space coverage only and makes no real-market prediction claim.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "dev"))
from autonomous_agent.proposal_layer import candidate_search_v2 as search  # noqa: E402

FEATURES = ("fixture_trend", "fixture_volatility", "fixture_interaction")
BUDGET = 18
DATASET_ID = "synthetic-fixture-dataset-v1"
SPLIT_ID = "synthetic-chronological-split-v1"


def _synthetic_data():
    rng = np.random.default_rng(20261017)
    n = 240
    x = rng.normal(size=(n, len(FEATURES)))
    logits = 1.15 * x[:, 0] - 0.8 * x[:, 1] + 0.55 * x[:, 0] * x[:, 2]
    y = (logits + rng.normal(scale=0.9, size=n) > 0).astype(int)
    return x, y


def _metrics(selected, X, y):
    scores = []
    for candidate in selected:
        scores.append(search.evaluate_candidate(
            candidate, X=X, y=y, feature_ids=FEATURES,
            train_indices=range(0, 160), validation_indices=range(160, 240)))
    return scores


def main():
    start = time.perf_counter()
    generated = search.generate_candidates(FEATURES, allow_development_fixture=True)
    selected, selection = search.select_diverse(
        generated, budget=BUDGET, feature_universe=FEATURES,
        dataset_id=DATASET_ID, split_id=SPLIT_ID)
    x, y = _synthetic_data()
    scores = _metrics(selected, x, y)
    elapsed = time.perf_counter() - start

    # Original executable universe on same deterministic history/budget:
    # 12/16 measurement keys are already known; its remaining four are
    # policy/quota-inadmissible in the frozen generator (observed baseline).
    legacy = {
        "implementation": "frozen-generator-v1.2.0 / bias-policy-v1.0.0",
        "same_proposal_budget": 64,
        "universe_evidence_keys": 16,
        "measured_evidence_keys": 12,
        "unmeasured_keys": 4,
        "legacy_mode1_generated": 18,
        "legacy_mode1_unique_new_evidence": 0,
        "legacy_mode1_historical_redundant": 18,
        "legacy_mode1_redundancy_rate": 1.0,
        "legacy_dedup_generated": 0,
        "legacy_dedup_unique_new_evidence": 0,
        "baseline_source": "bench_legacy_v4.json and bench_dedup_v3.json (both budget 64; actual output counts)",
    }
    result = {
        "benchmark_version": "candidate-search-comparison-v2.0.0",
        "protocol_id": search.PROTOCOL_ID,
        "fixture_status": search.DEV_FIXTURE_STATUS,
        "campaign_activation": search.ACTIVATED_FOR_CAMPAIGNS,
        "dataset_id": DATASET_ID,
        "split_id": SPLIT_ID,
        "proposal_budget": BUDGET,
        "baseline": legacy,
        "budget_comparability": "The original legacy benchmark is recorded at budget 64, so its counts are quoted as-is. The v2 benchmark runs an 18-candidate budget; the original's 18 emitted candidates can also be directly compared at selected-output count, while the dedup mode's 0 candidates is unchanged by increased budget.",
        "candidate_generation": {
            "raw_candidates": len(generated),
            "selected_candidates": len(selected),
            "selection": selection,
            "diversity": search.summarize_diversity(selected),
            "runtime_seconds_including_fits": round(elapsed, 6),
            "fit_seconds_sum": round(sum(s["fit_seconds"] for s in scores), 6),
            "synthetic_metrics_diagnostic_only": {
                "n_train": 160,
                "n_validation": 80,
                "class_balance_validation": float(np.mean(y[160:])),
                "mean_roc_auc": float(np.mean([s["roc_auc"] for s in scores])),
                "mean_average_precision": float(np.mean([s["average_precision"] for s in scores])),
                "mean_brier": float(np.mean([s["brier"] for s in scores])),
                "individual_candidate_scores": scores,
                "interpretation": "Synthetic fixture smoke measurement only; not predictive evidence and not comparable to historical AUC.",
            },
        },
        "fairness_note": "Proposal budget and deterministic fixture are shared. Legacy results come from the authorized historical 64-budget benchmark, whose selected output was 18 (legacy) and 0 (dedup). The v2 search candidates are synthetic and therefore only benchmark engineering diversity/runtime, not market prediction.",
    }
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("candidate_search_v2_benchmark.json")
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
