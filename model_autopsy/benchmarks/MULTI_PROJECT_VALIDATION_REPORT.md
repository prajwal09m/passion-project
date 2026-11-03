# Multi-Project Validation Report (2026-10-31, fully offline)

Suite: `tests/test_universal_projects.py` — 26 tests, all passing, no network,
no keys, no LLM calls. Fixtures: seeded generator (`tests/fixture_universal/
generate.py`, seed 7); ground truth sealed in `ground_truth.json`, read only
for assertions — triage code never sees it.

## Per-scenario results (deterministic triage over capability-selected tools)
1. **Clinic readmission (non-finance classification):** leakage column correctly
   identified as top correlation; AUC > 0.8 recomputed. PASS.
2. **House prices (regression):** |bias| ≈ 7951 (> 5000 threshold for the ~8k
   blended shift); urban MAE > 2× rural. PASS.
3. **Energy demand (forecasting):** 30-day split overlap detected; late MAE >
   2× early (missed drift). PASS.
4. **Customers (clustering control):** silhouette > 0.5, imbalance < 2. PASS.
5. **Black-box (predictions+labels only):** capability report correctly allows
   error_analysis/calibration and refuses leakage confirmation; AUC > 0.8. PASS.

## Coverage honesty
- LLM reasoning across projects was NOT tested here (would need paid calls);
  it was validated on Demand Zone by the frozen live campaigns
  (`FINAL_GROQ/META_VALIDATION_REPORT.md`). This suite validates specs,
  adapters, selection, diagnostics, ingestion, providers (fake transports),
  and context packages.
- Ranking metrics: not implemented (declared gap). Forecasting/clustering rest
  on single scenarios each. Six-example success is not a universality proof;
  the table in SUPPORTED_TASK_TYPES.md is the actual tested coverage.
