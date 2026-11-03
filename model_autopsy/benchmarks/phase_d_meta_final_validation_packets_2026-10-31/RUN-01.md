# Blinded scoring packet RUN-01

- Campaign: Meta final validation 2026-10-31; condition withheld
- Rubric: phase_d_blind_scoring_rubric_v1.md (frozen 2026-10-29)

## 1. Turn-2 final assistant message (verbatim)

Fact: recorded `classification_metrics` [action b8624fed472b4737bd6225d795018431] reports pooled ROC-AUC 0.683495 with per-split AUCs 2023 0.690708, 2024 0.680062, 2025 0.689827, precision 0.51497 and recall 0.012662 at 0.5, Brier 0.130634.
Fact: recorded `calibration_and_error_analysis` shows reliability bins tracking mean_score vs fraction_positive (e.g. 0.0-0.1: 0.055 vs 0.076, n=16997; 0.1-0.2: 0.147 vs 0.183, n=12663; 0.4-0.5: 0.440 vs 0.374, n=559) with only 130+32+5 samples above 0.5, and same per-fold AUCs ~0.68-0.69.

Hypothesis c8f0e4b1f1c646af944d1f1d08798e24 predicted uniformly weak AUC — supports: pooled 0.683 and uniform folds match prediction.
Hypothesis 5097b0b5c55545a39e1db181824ec295 predicted large fold divergence — contradicts: spread ~0.01, so demote to rejected.
Hypothesis 7f5fe5faa59943118b4ea88a59cd45e5 predicted decent AUC with systematic miscalibration driving threshold failure — contradicts: AUC is modest-low not decent, and bins are broadly aligned not grossly miscalibrated; low recall reflects few high scores plus weak separation, so demote to rejected as primary cause.

Conclusion: OOF underperformance is best explained by weak global discrimination uniform across folds, not by single-fold shift or pure miscalibration.

```investigation_summary
{"conclusion":"OOF underperformance explained by weak uniform discrimination (pooled AUC 0.683, per-fold 0.68-0.69); fold-shift and pure-miscalibration hypotheses rejected.","status_recommendations":[{"hypothesis_id":"c8f0e4b1f1c646af944d1f1d08798e24","status":"supported","basis":"b8624fed472b4737bd6225d795018431 pooled roc_auc 0.683495 uniform per-split AUCs"},{"hypothesis_id":"5097b0b5c55545a39e1db181824ec295","status":"rejected","basis":"b8624fed472b4737bd6225d795018431 per_split_auc 2023 0.690708 2024 0.680062 2025 0.689827 spread ~0.01"},{"hypothesis_id":"7f5fe5faa59943118b4ea88a59cd45e5","status":"rejected","basis":"b8624fed472b4737bd6225d795018431 AUC 0.683 not decent plus calibration bins broadly aligned"}],"uncertainties":["Exact operating-threshold tradeoff without threshold sweep UNRESOLVED"],"recommended_next":"Tune threshold / address class imbalance and improve ranking power rather than fixing fold split or recalibration alone."}
```

## 2. Parsed structured summary block (from turn-2 text, if any)

{"conclusion":"OOF underperformance explained by weak uniform discrimination (pooled AUC 0.683, per-fold 0.68-0.69); fold-shift and pure-miscalibration hypotheses rejected.","status_recommendations":[{"hypothesis_id":"c8f0e4b1f1c646af944d1f1d08798e24","status":"supported","basis":"b8624fed472b4737bd6225d795018431 pooled roc_auc 0.683495 uniform per-split AUCs"},{"hypothesis_id":"5097b0b5c55545a39e1db181824ec295","status":"rejected","basis":"b8624fed472b4737bd6225d795018431 per_split_auc 2023 0.690708 2024 0.680062 2025 0.689827 spread ~0.01"},{"hypothesis_id":"7f5fe5faa59943118b4ea88a59cd45e5","status":"rejected","basis":"b8624fed472b4737bd6225d795018431 AUC 0.683 not decent plus calibration bins broadly aligned"}],"uncertainties":["Exact operating-threshold tradeoff without threshold sweep UNRESOLVED"],"recommended_next":"Tune threshold / address class imbalance and improve ranking power rather than fixing fold split or recalibration alone."}

## 3. Structured-summary validity (kept separate from quality)
- First-attempt valid: see campaign record; post-repair valid: True
- Note: a valid block earns no quality points by itself.

## 4. Recorded actions (seq, tool, status)
- 4: propose_hypothesis [ran]
- 6: propose_hypothesis [ran]
- 8: propose_hypothesis [ran]
- 10: classification_metrics [ran]
- 16: calibration_and_error_analysis [ran]

## 5. Recorded hypotheses (id, status, text-head)
- c8f0e4b1f1c646af944d1f1d08798e24 [proposed]: Model has weak global out-of-fold discrimination: scores fail to rank positives above negatives across all data.
- 5097b0b5c55545a39e1db181824ec295 [proposed]: Performance is driven by fold heterogeneity / distribution shift: one fold or time period generalizes poorly and drags pooled OOF down.
- 7f5fe5faa59943118b4ea88a59cd45e5 [proposed]: Model ranking is okay but probabilities are miscalibrated at the operating threshold, causing poor precision/recall despite decent AUC.

## 6. Budget and completion
- Tool calls executed: 5 (budget shared: 6 calls)
- Incomplete provider responses observed in run: 1
- Failed requests preserved: no
