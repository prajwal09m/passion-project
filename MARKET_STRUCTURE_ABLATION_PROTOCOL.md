# Part II — Frozen Experiment Protocol v1.0.2 and Recovery Status

## Machine Learning and Market-Structure Features for Short-Horizon Equity Prediction: A Leakage-Audited Study

**Status:** The machine-readable v1.0.2 protocol is frozen and authoritative as a protocol, not as a source-verified run. Plan B archive-only closeout is complete: the immutable v1.0.1 saved outputs and point metrics were audited directly; the historical source remains unavailable, feature parity failed, and the current bootstrap helper does not reproduce the archive-reported interval bounds. The bytecode used for an earlier exploratory replay was overwritten during a later syntax check; no matching copy has been found. Do not treat the editable reconstruction as historical source or lock-ready. No prospective lock, predictions, or outcomes exist.  
**Protocol ID:** `DZAI-MARKET-STRUCTURE-ABLATION-V1`  
**Protocol version:** `1.0.2`  
**Decision lock date:** September 28, 2026  
**Machine-readable authority:** [`MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json`](MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json)  
**Companion record:** [`DEMAND_ZONE_AI_RESEARCH_DRAFT.md`](DEMAND_ZONE_AI_RESEARCH_DRAFT.md)

> **Evidence boundary.** The immutable directory `outputs/study_v1/` is a v1.0.1 historical development archive, not an execution of the current v1.0.2 protocol/code pair. Its manifest records code SHA-256 `29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b`, protocol SHA-256 `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`, and 61,045 labeled events / 41,221 OOF predictions. A read-only closeout audit verified all 153 source CSV hashes, both primary-table hashes, all eight model hashes, OOF/event-table row identity, and pooled/fold point metrics recomputed from the saved OOF scores. This is an output-integrity and saved-score calculation, not a historical source, feature-generation, or model-training reproduction. The archived primary point contrasts recalculate to +0.081757 (LightGBM A − Logistic A) and +0.005688 (LightGBM C − LightGBM B). The archive reports 95% intervals [0.065751, 0.099027] and [0.002179, 0.009191], respectively; the current reconstructed bootstrap helper did not reproduce any of the seven archived interval bounds in an earlier full check. Preserve those intervals as **archive-reported only**; do not substitute current bounds or claim independent interval reproduction. The exact source associated with the archive code hash is not present as an intact Python file, and the partial source is damaged. A previously recorded older Python 3.13 bytecode file with SHA-256 `c7d23b68e66d76f1f851887bc755b84b6bb1c8c424c24cccc8bf94de59d8f585` was previously used for a bounded replay; it was an older v1.0.1 implementation, was explicitly unreviewed, and is not a source restoration. During later validation, `py_compile` overwrote the bytecode cache with a newly compiled file (current SHA-256 `ee9017b7cf354931d638cb83bdc276c341bad9e90278addcdeec9ba60b4a7ed6`). No copy with the former hash was found. Source-prefix comparisons matched event count and ordered IDs but not numerous feature values, including `rsi14`, `atr_pct`, and `zone_width_pct`; the scoped AAL check found all 480 aligned rows differed on those three values. Therefore no source/feature parity or end-to-end metric reproduction is claimed. There are no prospective predictions or outcomes.

## 1. Frozen v1.0.2 objective and estimands (protocol specification; no v1.0.2 run)

This section records the frozen historical-development protocol in JSON. It does not document an executed v1.0.2 run; historical values belong to the separate v1.0.1 archive discussed below.

The protocol specifies one fixed Logistic Regression classifier and one fixed LightGBM classifier across the same candidate demand-zone retest events, target, chronological folds, and nested feature sets. The population is conditional on a candidate retest emitted by the frozen event generator for the recovered fixed roster of 149 symbols. This is not an all-stock/all-date scan, a causal estimate, a profitability study, or evidence about a representative market-wide universe.

Feature sets are nested:

- **A — conventional baseline:** price, momentum, volume (20 columns).
- **B — context:** A + volatility and market context (38 total).
- **C — demand structure:** B + demand-zone geometry and retest state (65 total).
- **D — order blocks:** C + point-in-time order-block features (99 total).

For a conformant v1.0.2 study, both estimator families would be run for all A/B/C/D combinations on identical event identifiers, labels, and validation folds; this remains protocol design, not a historical-source conformance finding. A constant-score model has AUC 0.5 and is the chance reference; it is not a third fitted model.

The two primary historical-development contrasts frozen in v1.0.2 (not v1.0.2 run results) are:

1. `LightGBM-A ROC-AUC − LogisticRegression-A ROC-AUC`.
2. `LightGBM-C ROC-AUC − LightGBM-B ROC-AUC`.

Secondary contrasts are B−A within each estimator, C−B within Logistic Regression, and D−C within each estimator. They are descriptive and do not trigger model or feature selection. The estimates concern ranking conditional on candidate retest events only.

## 2. Frozen v1.0.2 population, source data, and event protocol (not archive-generation proof)

### 2.1 Fixed roster and source

Frozen protocol roster requirement: use the sorted distinct `ticker` column from `outputs/v2/demand_zone_v2_dataset.csv` (44,854 legacy rows; 149 unique tickers) for roster membership only. The legacy events, features, and labels are excluded from study-table construction. The frozen data specification names the corresponding 149 OHLCV files plus SPY, QQQ, IWM, and VIX (`XVIX.csv`) under `outputs/v2/_ohlcv/`. The read-only archive audit verified all 153 cached source-file hashes against the historical v1.0.1 manifest; cached dates begin in 2020 and latest bars through **2026-08-03**. This hash check does not establish point-in-time vendor vintages or v1.0.2 feature-generation conformance.

The universe is a fixed historical project roster, not a point-in-time constituent universe. Its original selection date, historical index membership, delisted issuer coverage, and survivorship properties are unresolved. Claims must remain conditional on this roster and may not generalize to all US equities. Local prices are Yahoo-derived, adjusted snapshots; historical vendor vintages, corrections, and corporate-action adjustment timing are not verifiable. The exact source files and per-event as-of prefixes are SHA-256 recorded for reproducibility, not proof that the data are historically point-in-time vintages.

### 2.2 Frozen v1.0.2 event definition (not a source-verified replay)

- Signal time is after the close of daily session T.
- A pivot is a swing low at index i when `Low[i]` is no greater than lows at i−1, i−2, i+1, and i+2. It is confirmed only after session i+2 closes.
- The zone price is `Low[i]`; width is `ATR(14)[i] / Close[i]`. Formation/departure features freeze at confirmation and use no bar after i+2.
- A retest is the first bar in a contiguous run where `abs(Low[T] − zone_price) / zone_price <= 0.03`, strictly after zone confirmation. Each zone emits up to five retest starts; zones do not expire. Zone in/out state is replayed from the beginning of the available cache, including before the study start, so the start boundary does not reset retest state.
- If multiple confirmed zones trigger on one ticker-date, retain one by highest known touch count, smallest absolute close-to-zone distance, then lowest chronological zone ID. The event ID is a stable SHA-256 of ticker and signal date, so there is at most one candidate event per ticker-session.
- All signal-row features use only bars dated no later than T. Prospective histories are physically truncated at explicit `as_of` before any feature construction.

**Frozen v1.0.2 protocol contract (design only):** the planned protocol-conformant implementation would emit candidate signals from **2021-08-03** up to (but excluding) **2026-01-01**. No 2026 signal event is allowed. Bars after the cutoff may be read only to mature T+1/T+2 labels for signals through 2025-12-31; final model-training rows must also have `exit_date < 2026-01-01`. The 2023–2025 folds are historical development evaluation, not prospective evidence. This contract does not establish that the v1.0.1 archive or the reconstructed source conforms to v1.0.2. In the separate exploratory prefix comparison, event counts and ID/order matched the archive, but feature values did not; the bytecode replay is also unreviewed. These outputs cannot validate v1.0.2 metrics.

## 3. Target and eligibility

For an eligible event on date T:

\[
R_T = \frac{Open[T+2]}{Open[T+1]} - 1,
\qquad
Y_T = \mathbb{1}[R_T \ge 0.02].
\]

Entry is the next ticker trading-session open T+1; exit is the following ticker trading-session open T+2. A label is valid only when both opens and the return are finite and strictly positive. Apply that validity mask before binarization. Missing or invalid future opens are excluded; they are never negative labels. No alpha, barrier-touch, 20-day, proxy, magnitude, or alternate-threshold label enters the primary experiment.

## 4. Frozen v1.0.2 feature dictionary (protocol whitelist, not a run record)

The lists below define the **v1.0.2 protocol whitelist**, not proof that the recovered implementation generated those historical values. Only the exact names listed here may enter each model matrix. Identifiers, outcomes, forward benchmarks, and unlisted columns are excluded. Infinite values become missing. Median imputation is fit on the training rows only and applied unchanged to validation rows. Logistic Regression additionally uses training-fold `StandardScaler`; LightGBM does not scale. No outcome-driven feature selection, missingness indicators, target encoding, threshold selection, or tuning is allowed. The present reconstructed source has not been shown feature-equivalent to the immutable v1.0.1 archive.

### A — Price, momentum, volume (20)

`daily_return`, `return_5d`, `return_20d`, `dist_ema20`, `dist_ema50`, `dist_ema200`, `ema_alignment`, `ema20_slope_5d`, `rsi14`, `macd_pct`, `macd_signal_pct`, `macd_hist_pct`, `roc14`, `relative_volume20`, `volume_trend20`, `accumulation_days10`, `volume_flow_5d_norm`, `volume_consistency20`, `close_strength`, `bullish_candle`.

Protocol requirement: every A-arm value is derived from stock OHLCV at or before close T. Price features are normalized ratios or summaries; absolute price levels and identifiers are excluded. This does not certify historical feature generation.

### B increment — Volatility and market context (18; 38 total)

`atr_pct`, `realized_vol_5d`, `realized_vol_10d`, `realized_vol_20d`, `spy_return_5d`, `spy_return_20d`, `qqq_return_5d`, `qqq_return_20d`, `iwm_return_5d`, `iwm_return_20d`, `spy_dist_sma200`, `spy_above_sma200`, `vix_level`, `vix_change_1d`, `vix_percentile_60d`, `relative_strength_spy_20d`, `relative_strength_qqq_20d`, `relative_strength_iwm_20d`.

Trailing windows end at T. Reference-market rows are the latest bars dated no later than T. Relative strength is stock trailing 20-session return minus the corresponding benchmark trailing 20-session return. There is no sector mapping or forward benchmark holding-period return.

### C increment — Demand-zone structure (27; 65 total)

`zone_distance_pct`, `zone_width_pct`, `zone_touch_count`, `zone_strength`, `zone_age_sessions`, `zone_freshness`, `zone_prior_retest_count`, `zone_retest_number`, `zone_is_first_retest`, `zone_base_candles`, `zone_base_volume_ratio`, `zone_departure_move_pct`, `zone_departure_volume_ratio`, `zone_base_range_pct`, `zone_volatility_contraction`, `zone_departure_atr_multiple`, `zone_base_body_ratio`, `zone_base_average_body_pct`, `zone_base_average_wick_ratio`, `zone_base_range_to_prior_mean_ratio`, `zone_inside_bar_count`, `zone_compression_score`, `zone_largest_departure_candle_pct`, `zone_departure_gap_pct`, `zone_departure_volume_percentile`, `zone_consecutive_bullish_departure`, `zone_departure_close_near_high`.

The v1.0.2 protocol requires the selected zone to be confirmed by T. Formation geometry is to be computed from pivot through confirmation only; retest count, touch, age, distance, and freshness are sequential through T. This is a protocol rule, not an archive-parity result. Neither `zone_base_range_to_prior_mean_ratio` nor `zone_compression_score` is a true historical percentile; those names describe the frozen ratio calculations. No prior retest success/failure or outcome statistic is used.

### D increment — Causal order blocks (34; 99 total)

`ob_bull_exists`, `ob_bear_exists`, `ob_unmitigated_bull_count`, `ob_unmitigated_bear_count`, `ob_bull_distance_signed_pct`, `ob_bull_width_pct`, `ob_bull_age_calendar_days`, `ob_bull_age_sessions`, `ob_bull_impulse_return_pct`, `ob_bull_impulse_atr_multiple`, `ob_bull_impulse_volume_ratio`, `ob_bull_impulse_candles`, `ob_bull_candles_until_impulse`, `ob_bull_displacement_rank`, `ob_bull_volume_ratio`, `ob_bull_candle_count`, `ob_bull_body_pct`, `ob_bull_wick_pct`, `ob_bull_touch_count`, `ob_bear_distance_signed_pct`, `ob_bear_width_pct`, `ob_bear_age_calendar_days`, `ob_bear_age_sessions`, `ob_bear_impulse_return_pct`, `ob_bear_impulse_atr_multiple`, `ob_bear_impulse_volume_ratio`, `ob_bear_impulse_candles`, `ob_bear_candles_until_impulse`, `ob_bear_displacement_rank`, `ob_bear_volume_ratio`, `ob_bear_candle_count`, `ob_bear_body_pct`, `ob_bear_wick_pct`, `ob_bear_touch_count`.

**Protocol requirement, not verified source provenance:** v1.0.2 specifies a streaming `CausalOrderBlockTracker` with 1% displacement, 0.6 ATR, 0.5 volume, an up-to-three-bar opposing block, five-bar lookback, 90-calendar-day age, 100-session warmup, and the nearest unmitigated bullish/bearish block. It must advance once per closed bar. Higher-timeframe alignment, structure-break flags, future mitigation/outcome fields, and absolute prices are excluded. The editable [`backend/demand_zone_study_v1.py`](backend/demand_zone_study_v1.py) is a reconstruction, not an exact restoration. Synthetic prefix-invariance tests exercise its current behavior, but do not establish feature parity with the archive; the preserved bytecode tracker is older and the prior feature comparison failed. This paragraph states the protocol contract, not a claim that the historical tracker has been recovered.

## 5. Frozen v1.0.2 estimators, folds, and planned model fit

The model settings below are frozen v1.0.2 requirements. They are not evidence of an executed v1.0.2 run or of historical v1.0.1 source conformance. The fixed estimator definitions are listed here as protocol configuration only; they do not certify how archived artifacts were trained.

### Logistic Regression

`C=1.0`, `solver="lbfgs"`, `max_iter=2000`, `random_state=42`, no class weighting; estimator default L2 penalty. Pipeline: `SimpleImputer(strategy="median", keep_empty_features=True)` → `StandardScaler` → Logistic Regression. Every step is fit only on that fold’s training rows.

### LightGBM

`n_estimators=300`, `max_depth=6`, `num_leaves=31`, `learning_rate=0.03`, `subsample=0.8`, `subsample_freq=1`, `colsample_bytree=0.8`, `min_child_samples=30`, `reg_alpha=0.1`, `reg_lambda=0.5`, `random_state=42`, `n_jobs=1`, `verbosity=-1`, `deterministic=True`, `force_col_wise=True`, no class weighting. Pipeline: fold-local median imputation → `LGBMClassifier`.

For a conformant v1.0.2 run, no hyperparameter search, ensemble, feature ranking, calibration, result-dependent model changes, or model/feature selection is permitted. Package/runtime versions and hashes must be retained. These controls are protocol requirements, not verified v1.0.1 provenance.

### Frozen v1.0.2 development folds and final-fit rule (protocol design, not execution evidence)

| Frozen v1.0.2 protocol fold | Training-row requirement | Validation signal dates |
|---|---|---|
| 2023 | Signal date before 2023-01-01 and label exit strictly before 2023-01-01 | 2023-01-01 through 2023-12-31 |
| 2024 | Signal date before 2024-01-01 and label exit strictly before 2024-01-01 | 2024-01-01 through 2024-12-31 |
| 2025 | Signal date before 2025-01-01 and label exit strictly before 2025-01-01 | 2025-01-01 through 2025-12-31 |

Protocol requirement: all ticker rows on a date remain together. In a conformant v1.0.2 run, all eight combinations would be fit and scored on identical validation `event_id`/date/label rows. The target-maturity purge requires each training `exit_date` to precede the validation start. The archive-only closeout verified saved OOF row identity, not conformance of historical feature generation or training to this specification.

**Frozen v1.0.2 planned final-fit rule (not executed in this closeout):** in a separately reviewed and authorized run, the eight prospective model pipelines would be fit only on labeled rows with **signal_date < 2026-01-01 and exit_date < 2026-01-01**, then frozen without prospective retraining. This rule prevents use of 2026 cache-tail rows or labels maturing after the cutoff. It is protocol design, not evidence that a source-verified v1.0.2 fit occurred; no prospective lock or fit is claimed here.

## 6. Frozen v1.0.2 metrics and uncertainty requirements (protocol design, not executed results)

The frozen v1.0.2 protocol specifies pooled OOF ROC-AUC on common rows as the primary development summary. It also specifies per-fold pooled AUC, pooled average precision, sample count, positive rate, equal-weight mean daily AUC on dates with both classes, the eligible-date count, and mean per-date top-5% precision beside same-date prevalence. Top-5% is conditional on the candidate event universe; it is not an all-market rank or trading return. The audit recalculated available point metrics from saved v1.0.1 scores only; it did not execute a v1.0.2 evaluation.

The frozen protocol prescribes 95% percentile intervals for the primary paired contrasts using **1,000 circular moving-block bootstrap resamples of four consecutive calendar weeks**, retaining all event rows within each sampled week, seed 42. Sampled weeks are concatenated (including repeats) and pooled AUC recomputed on the paired sample. These are descriptive historical intervals, not a formal time-series inferential test or confirmatory p-value. AUC 0.5 is the constant-score chance reference. These are protocol requirements, not newly calculated v1.0.2 results; the separate v1.0.1 archive intervals remain report/manifest values only because the current helper did not reproduce them.

No profitability, calibration, or causal claim follows from these metrics. This protocol companion contains no v1.0.2 execution result. The separate v1.0.1 archive is retrospective; no prospective result table is populated because no prospective data exist.

## 7. Frozen v1.0.2 leakage and reproducibility gates (requirements, not verified historical evidence)

The following are requirements for a separately reviewed, protocol-conformant v1.0.2 implementation/run. They were not all re-executed as part of the Plan B saved-output audit and do not prove the historical v1.0.1 source satisfied them:

1. Valid finite positive forward opens/return are established before label conversion; unavailable labels are excluded.
2. Exact A/B/C/D feature names match this protocol, are nested, and contain no target/label/outcome/future/forward/hold1/alpha/benchmark-return/target-proxy columns or identifiers.
3. Each event’s feature as-of date equals its signal date, and event identity is ticker-session rather than zone.
4. Zone retest state and order-block tracker replay are unchanged when data after an as-of date are appended; histories are truncated before prospective construction.
5. Training imputation/scaling are fitted only on training rows.
6. Training labels mature strictly before each validation window.
7. All eight scores use identical validation event IDs and labels, with no dropped rows due to missing feature values.
8. All required ticker/reference data files are present and source/code/protocol/test/model hashes are recorded and checked for mutation.
9. The 2026 cache tail is excluded from historical folds and final model training.
10. The prospective JSONL ledger is append-only, hash chained, de-duplicates events/outcomes, detects incomplete runs, respects the 2,000-event maximum, and never backfills pre-lock predictions.

The current automated suite tests label validity/threshold alignment, cutoff behavior, archive artifact hashes, target-maturity purge, exact feature-arm nesting and leakage-name exclusion, fold-local transforms, identical rows for all eight model/arm combinations, synthetic event/order-block prefix invariance, canonical universe hashing, hash-chained outcome maturation, ledger tamper/orphan/incomplete-run detection, no-candidate clock behavior, and prospective 12/18-month plus 2,000-event gates. All 22 tests passed for the current reconstruction. These are code-level and artifact-integrity checks; they do not prove historical source or feature parity, validate the unreviewed bytecode replay, convert archive metrics into prospective evidence, or substitute for hash agreement at a future freeze.

## 8. Prospective evaluation design (frozen v1.0.2 requirements; not initiated)

This section records future protocol gates only. No prospective test is ongoing or initiated. A prospective test may begin only after a separately reviewed v1.0.2 implementation and a new, separately archived development run have matching code, protocol, test-suite, source snapshot, universe, and all eight model-artifact hashes, followed by an explicitly authorized lock and an empty append-only ledger. The immutable v1.0.1 manifest records hashes for its 153 source CSVs, result tables, and eight models; those artifacts are not thereby validated as outputs of v1.0.2. The current reconstruction is not hash-identical to the archived code and has not matched the archive's feature values. The separate bytecode replay is unreviewed, created no final models, and is not lock-eligible. No prospective lock or ledger has been initialized. Resolve source/protocol conformance in a distinct reviewed run before considering any prospective lock. A lock by itself does not start the clock. The first event must be logged after the lock and after the latest frozen source date; no historical backfill is allowed. Successful dates with no candidates and same-session failures are retained, but neither starts the duration clock. The clock starts with the first successfully logged eligible prediction.

On each eligible session, save every event’s feature values, all eight probabilities, signal/prediction timestamp, per-symbol source-prefix hashes, protocol/code/model hashes, and run record before T+1/T+2 outcomes are known. Append target outcomes only after both future opens are available and finite. Keep the ledger sealed from result review while prospective predictions accrue. If a date has more candidates than the remaining event slots, keep the stable first events sorted by signal date and ticker and record omissions.

Stop issuing predictions at the first of (a) 2,000 unique eligible ticker-date predictions, or (b) 18 calendar months after the first eligible prediction. Conduct one final inferential analysis only when **both at least 12 calendar months have elapsed and at least 2,000 eligible event outcomes have matured**. If 2,000 predictions are reached early, stop new predictions but wait until month 12. If fewer than 2,000 events mature by month 18, report the observed count/precision limitation and do not extend the window. No result-dependent early stopping, retraining, tuning, or threshold changes. As of the current audit there are **zero logged prospective events and zero prospective outcomes**; the required prospective conclusion cannot yet exist.

## 9. Historical forensic replay boundary

Past project scores used different targets, features, splits, and model-selection processes; the available artifacts do not provide a matched basis for a numeric leakage attribution. Under the approved finite Plan B, exact v1.0.1 source recovery and source-verified replay are closed as unavailable after feature parity failed. Do not resume source/bytecode hunting or use the current reconstruction for historical attribution. Any genuinely new work based on trusted exact artifacts obtained independently would be a separate task requiring explicit authorization; it is not an open step in this closeout. Do not compare unrelated V5/V7 metrics as a leakage estimate or relabel historical validation as prospective.

## 10. Frozen v1.0.2 status and archive-only reporting checklist

**Protocol authority:** [`MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json`](MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json) is frozen as v1.0.2 (decision date 2026-09-28); its exclusive historical signal-date cutoff is 2026-01-01. **Immutable baseline:** `outputs/study_v1/development/` and `outputs/study_v1/models/` contain a v1.0.1 archive whose manifest records code SHA-256 `29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b`, protocol SHA-256 `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`, 61,045 labeled events, and 41,221 OOF predictions. The Plan B read-only audit verified 153/153 source CSV hashes, both primary result-table hashes, and all eight model hashes; it also verified OOF/event identity and recalculated pooled/fold point metrics from saved OOF predictions, matching manifest/report values. This verifies retained-output integrity and saved-score arithmetic, not historical code/feature reproduction. Details are in the [archive-only closeout report](outputs/study_v1_archive_audit_closeout.md).

**Plan B closeout finding:** the exact Python source associated with the archived code hash is unavailable. The partial source is damaged; the former `.pyc` was overwritten during syntax validation and its earlier SHA-256 (`c7d23b68e66d76f1f851887bc755b84b6bb1c8c424c24cccc8bf94de59d8f585`) does not match the current cache file (`ee9017b7cf354931d638cb83bdc276c341bad9e90278addcdeec9ba60b4a7ed6`). Its recorded hash is not a substitute for the missing artifact. Under the approved finite Plan B, source/bytecode recovery is closed as unavailable; do not continue hunting or replaying. The earlier unreviewed replay under `outputs/study_v1_recovered_bytecode_unreviewed_20260928/` is not v1.0.2 evidence. Source-prefix comparisons matched count and ordered event IDs but not feature values (including `rsi14`, `atr_pct`, `zone_width_pct`); the scoped AAL check found 480/480 aligned rows differed for each of those three columns. No historical feature/source or end-to-end metric reproduction is claimed.

**Saved-output audit:** the read-only audit verified 153/153 source hashes, both primary result-table hashes, and all 8/8 model hashes against the immutable manifest. It confirmed 61,045 event/label rows, 41,221 unique finite OOF predictions, matching OOF/event-table identities and outcomes, signal dates through 2025-12-31, and pooled and fold point metrics recalculated from saved OOF scores matching the manifest and report. This does not validate how the historical features or scores were generated. The +0.081757 LightGBM-A minus Logistic-A and +0.005688 LightGBM-C minus LightGBM-B point deltas are calculations from the retained OOF predictions. The manifest intervals [0.065751, 0.099027] and [0.002179, 0.009191] remain archive-reported values: a prior full recalculation with the current bootstrap helper failed to reproduce all seven archived intervals; exact root cause is unknown. No interval was replaced, and the closeout did not rerun the bootstrap.

The prospective directory, lock, and ledger have not been initialized; there are zero prospective events and outcomes. No canonical development was rerun, no new/prospective artifacts were created, and the immutable archive was not modified. Any v1.0.2 implementation/review and prospective trial are separate, gated future work—not remaining steps in this finite archive closeout.

- [x] Keep the v1.0.2 machine-readable protocol frozen and authoritative as a protocol; retain the distinct v1.0.1 archive unchanged.
- [x] Close exact source/bytecode recovery as unavailable under Plan B; document the missing original source and overwritten cache without treating the recorded bytecode hash as a recoverable artifact.
- [x] Compare available source-prefix events: counts and ordered IDs match, but feature values do not; no source-parity claim.
- [x] Verify the immutable archive's 153 source hashes, 2 primary result-table hashes, and 8 model hashes.
- [x] Audit saved event/OOF identity, labels, dates, finite scores, and recalculate pooled/fold point metrics from saved predictions.
- [x] Preserve bootstrap confidence intervals as manifest-reported only; document that the current helper failed to reproduce any of the seven bounds and do not substitute new values.
- [x] Align the Markdown and Word status/conclusion/checklist with the v1.0.2/v1.0.1 distinction and zero-prospective status.
- [x] Run safe tests and integrity/syntax checks without `py_compile`; preserve all immutable archive outputs.
Future only: a distinct, reviewed v1.0.2 implementation/run and any prospective lock require their own authorization; neither is part of this completed closeout.

**Safe checks used for this closeout:**

```bash
py -3.13 -B -m unittest backend.tests.test_demand_zone_study_v1 -v
py -3.13 -B .freebuff/recovery_tools/audit_saved_v1_0_1_outputs.py
```

The archive audit reads retained files and recalculates saved-score metrics; by default it does not rerun the bootstrap, regenerate events/features, fit models, or write prospective artifacts. Unit tests cover current reconstructed behavior and selected archive hashes, not original-source parity. Do **not** use `development`, `freeze-prospective`, or prospective logging commands to extend this closeout. The frozen JSON governs protocol requirements; the v1.0.1 archive remains immutable historical evidence only.
