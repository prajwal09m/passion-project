# Milestone 10 Challenge Report (measured, deterministic)

Full-corpus autonomous runs, max 6 steps each, graded by the
independent evaluator (evidence-required):

| scenario | grade | score | key evidence |
|---|---|---|---|
| m10_ward_gap | discovered | 1.0 | per-ward AUC spread, moving |
| m10_proxy_signal | discovered | 1.0 | non-score \|r|≈1, moving |
| m10_threshold_skew | relevant-only | 0.25 | named, never measured |
| m10_stale_lag | discovered | 1.0 | persistent-error pattern, moving |
| m10_district_scale | discovered | 1.0 | group MAE ratio, moving |
| m10_combo | discovered | 1.0 | changepoint + residual pattern |
| m10_steady | inconclusive-correct | 1.0 | no supports |
| m10_sparse | inconclusive-correct | 1.0 | thin evidence, uncommitted |

Mean discovery: 0.906. Every discovered case carries ≥1 naming
hypothesis with moving evidence from a real executed action; the
key discriminating tool was measured in all five.
