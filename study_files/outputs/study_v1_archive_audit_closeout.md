# v1.0.1 Archive-Only Audit Closeout

**Status:** Plan B closeout complete. This is a read-only audit of retained outputs, not a new study, historical source replay, or prospective evaluation.  
**Protocol boundary:** [`MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json`](../MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json) remains frozen v1.0.2 (decision date 2026-09-28; exclusive signal-date cutoff 2026-01-01). The immutable [`outputs/study_v1/`](study_v1/) directory is a distinct historical v1.0.1 archive.  
**Scope:** Saved-output identity, OOF/event/label consistency, and metrics recalculated from retained OOF scores. No features/events were regenerated and no models were fit.

## Outcome

The v1.0.1 archive is internally consistent at the saved-output and point-metric level. It is **not independently reproduced from its original source or feature generation**, and it does not constitute a v1.0.2 run. The historical source is unavailable; source/feature comparison failed. Accordingly, the historical metrics are retained archive results—not prospective or confirmatory evidence.

## Checks completed

- **Artifact integrity:** 153/153 cached source CSVs, both primary result tables, and all 8/8 model artifacts match the v1.0.1 run manifest hashes. The primary table SHA-256 values are `event_table.csv` `232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0` and `oof_predictions.csv` `011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829`.
- **Archive counts:** 61,045 event rows and labels; 41,221 unique OOF rows, with 19,824 non-OOF event rows. OOF fold counts are 2023: 13,924; 2024: 13,180; 2025: 14,117. Signal dates run from 2023-01-03 through 2025-12-31, strictly before the exclusive 2026-01-01 cutoff.
- **OOF consistency:** Scores are finite; OOF event IDs, labels, returns, and entry/exit dates align with the archived event table. Saved labels match the inclusive `hold1_ret >= 0.02` target and the saved forward dates mature after the signal date.
- **Metrics from saved predictions:** Recomputed pooled and fold metrics match the run manifest; pooled values match the archived report to its stated precision. Recomputed paired point AUC contrasts match the manifest:

| Saved-score contrast | Recomputed Δ AUC | Archive-reported 95% interval |
|---|---:|---:|
| LightGBM A − Logistic Regression A | +0.081757 | [0.065751, 0.099027] |
| LightGBM C − LightGBM B | +0.005688 | [0.002179, 0.009191] |

The point deltas above are independently calculated from the retained OOF score columns. The intervals are copied from the archived manifest/report and are **not independently reproduced** by the current reconstruction.

## Source and interval limitations

The v1.0.1 manifest records original source-code SHA-256 `29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b` and protocol SHA-256 `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`. No intact `.py` matching the source hash was recovered. The partial source is damaged. A prior source-prefix comparison matched event counts and ordered event IDs but not many feature values. In a scoped AAL comparison, all 480 aligned rows differed on each of `rsi14`, `atr_pct`, and `zone_width_pct`. Therefore the editable code is only a reconstruction and does not establish historical feature or source parity.

The previously used Python 3.13 bytecode was an older v1.0.1 implementation, not a substitute for the source and not v1.0.2. Its old recorded hash was `c7d23b68e66d76f1f851887bc755b84b6bb1c8c424c24cccc8bf94de59d8f585`; a later `py_compile` overwrote the cache path, whose current hash is `ee9017b7cf354931d638cb83bdc276c341bad9e90278addcdeec9ba60b4a7ed6`. No trusted matching copy was found. This error is disclosed; recovery is closed as unavailable under Plan B. The earlier replay remains explicitly unreviewed and is not source-reproduction evidence.

A prior full recomputation using the current reconstructed weekly block-bootstrap helper did **not** reproduce any of the seven archived interval bounds, although point deltas and valid-resample counts matched. The root cause is unknown. The closeout did not rerun those bootstraps. Keep all archive intervals as reported values; do not replace them with the current helper's bounds or claim independent confidence-interval reproduction.

## Interpretation and endpoint

The archive reports a positive LightGBM C−B point delta of about **+0.0057 AUC**. Because exact source and feature parity are unavailable, it cannot be confidently attributed to the intended market-structure features. Both primary comparisons are historical development results on dates already available to prior project work. AUC differences do not establish profitability, causal market support, broad-universe performance, or prospective stability.

There is no prospective lock or ledger, and there are **zero prospective predictions and zero prospective outcomes**. Historical data cannot be backfilled into prospective evidence. The finite archive-only closeout is complete; trusted source recovery is not a remaining task in Plan B.

## Safety boundary

No canonical development was rerun; no prospective command, lock, prediction, or new study artifact was created; and no immutable v1.0.1 result/model/source file was modified. The machine-readable v1.0.2 protocol was not changed. The current 22-test suite tests reconstructed behavior and selected archive hashes; it does not prove historical feature parity. A distinct future v1.0.2 study or prospective trial would require separate review and explicit authorization.

Audit utility: [read-only saved-output audit](../.freebuff/recovery_tools/audit_saved_v1_0_1_outputs.py). Its default run checks archive hashes and saved-score metrics; it does not rerun the bootstrap, replay events, regenerate features, or fit models.
