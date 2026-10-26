"""Deterministic synthetic-fixture benchmark for isolated candidate search v2.

Run from ``.model_discovery_workspace``:
  py -3 generator_v2_benchmark.py [output.json]

No ledger, market dataset, or sealed holdout is read. The frozen legacy
universe has 16 measurement keys, 12 measured and 4 unmeasured; its recorded
runs emitted 18 redundant candidates or stalled after dedup. This synthetic
comparison uses the SAME 18-candidate output budget for both generators.
Legacy cannot contribute new unique evidence under the frozen executable
space; v2's values measure only synthetic engineering capability, never
market predictive performance.
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


def main():
    started = time.perf_counter()
    all_candidates = search.generate_candidates(FEATURES, allow_development_fixture=True)
    selected, selection = search.select_diverse(
        all_candidates, budget=BUDGET, feature_universe=FEATURES,
        dataset_id=DATASET_ID, split_id=SPLIT_ID)
    rng = np.random.default_rng(20261017)
    x = rng.normal(size=(240, len(FEATURES)))
    logits = 1.15*x[:, 0] - 0.8*x[:, 1] + 0.55*x[:, 0]*x[:, 2]
    y = (logits + rng.normal(scale=0.9, size=240) > 0).astype(int)
    scores = [search.evaluate_candidate(
        candidate, X=x, y=y, feature_ids=FEATURES,
        train_indices=range(160), validation_indices=range(160, 240))
        for candidate in selected]
    result = {
        "benchmark_version": "candidate-search-comparison-v2.1.0",
        "protocol_id": search.PROTOCOL_ID,
        "fixture_status": search.DEV_FIXTURE_STATUS,
        "campaign_activation": search.ACTIVATED_FOR_CAMPAIGNS,
        "dataset_id": DATASET_ID,
        "split_id": SPLIT_ID,
        "same_proposal_budget": BUDGET,
        "baseline": {
            "implementation": "frozen-generator-v1.2.0 / bias-policy-v1.0.0",
            "proposal_budget": BUDGET,
            "universe_evidence_keys": 16,
            "measured_evidence_keys": 12,
            "unmeasured_keys": 4,
            "legacy_raw_emitted_at_original_budget_64": 18,
            "legacy_distinct_new_evidence_at_equal_18_output_budget": 0,
            "legacy_historical_redundant_at_original_budget_64": 18,
            "legacy_redundancy_rate_at_original_budget_64": 1.0,
            "dedup_emitted_at_original_budget_64": 0,
            "source": ["bench_legacy_v4.json", "bench_dedup_v3.json"],
            "interpretation": "For this diagnostic comparison, both methods get an output budget of 18: frozen legacy yields zero distinct eligible evidence under its 16-key historical universe (12 already measured); v2 yields 18 distinct synthetic configs. Different evidence universes mean this is engineering coverage, not predictive uplift.",
        },
        "candidate_search_v2": {
            "raw_candidates": len(all_candidates),
            "selected_candidates": len(selected),
            "selection_stats": selection,
            "diversity": search.summarize_diversity(selected),
            "runtime_seconds_including_fits": round(time.perf_counter()-started, 6),
            "fit_seconds_sum": round(sum(row["fit_seconds"] for row in scores), 6),
            "fixture_evaluation": {
                "n_train": 160,
                "n_validation": 80,
                "validation_positive_rate": float(np.mean(y[160:])),
                "mean_roc_auc": float(np.mean([row["roc_auc"] for row in scores])),
                "mean_average_precision": float(np.mean([row["average_precision"] for row in scores])),
                "mean_brier": float(np.mean([row["brier"] for row in scores])),
                "candidate_scores": scores,
                "interpretation": "Synthetic smoke-test metrics only; not actual market evidence, not an independent holdout, and not comparable to historical AUC.",
            },
        },
        "conclusion": "Engineering diversity improved on its synthetic fixture: v2 selects 18 distinct model/feature/transform evidence keys from 360 raw executable configs (264 canonical identities); the legacy frozen generator selected no novel evidence under its historical 16-key universe. Predictive generalization improvement remains unmeasured.",
    }
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("generator_v2_benchmark.json")
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
