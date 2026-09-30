# Part I — Development, Audit, and Recovery Status for the Demand Zone AI Study

## How Demand Zone AI Evolved—and Why Its Scores Needed an Audit

### An iterative study of short-horizon equity prediction

> **Companion documents:** [`MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json`](MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json) is the frozen v1.0.2 protocol; [`MARKET_STRUCTURE_ABLATION_PROTOCOL.md`](MARKET_STRUCTURE_ABLATION_PROTOCOL.md) explains its contract and closeout status; [`outputs/study_v1_archive_audit_closeout.md`](outputs/study_v1_archive_audit_closeout.md) records the bounded archive audit. The immutable `outputs/study_v1/` results are a distinct v1.0.1 archive. The exact Python source for that archive has not been recovered, and the current reconstruction has not matched its event features. Pooled/fold point metrics and the two primary point deltas below were recalculated from retained OOF predictions and checked against the archive; this does not reproduce the historic features or prediction generation. Bootstrap intervals remain archived report/manifest values only. No prospective performance results are reported.

**Author:** [Student name]  
**Affiliation:** Independent project, [school or organization]  
**Draft date:** September 29, 2026  
**Status:** Working research draft; finite Plan B archive-only closeout complete. The v1.0.2 protocol is frozen; exact v1.0.1 source/feature parity remains unavailable; prospective evaluation is not locked or started.  

> **Research-integrity note.** This draft reconstructs project history from available source code, model metadata, reports, and recovery audits. The Plan B read-only closeout verified the immutable v1.0.1 archive's 153 source CSV hashes, two result-table hashes, eight model hashes, OOF/event-table identity, and pooled/fold point metrics recalculated from saved OOF scores. This is output-integrity and saved-score validation—not historical source, feature-generation, or model-training reproduction. The exact source matching the manifest is unavailable; source-prefix comparison matched counts and ordered event IDs but failed feature parity, including a scoped AAL check with 480/480 rows differing on `rsi14`, `atr_pct`, and `zone_width_pct`. The two primary point AUC deltas recalculate from saved scores, but the archive's bootstrap interval bounds remain report/manifest values: the current helper failed to reproduce all seven bounds in a prior full check. A Python 3.13 bytecode file used in a separate bounded replay was explicitly unreviewed and overwritten during later syntax validation; its old recorded hash is not the current file, and no matching copy was found. Under the approved finite Plan B, source recovery is closed as unavailable; no further search/replay, canonical rerun, new study, or prospective artifact was made. The machine-readable v1.0.2 protocol remains frozen; it is distinct from the v1.0.1 archive. There is no prospective lock, prediction, or outcome. This is an educational research project, not investment advice.

## Abstract

Demand Zone AI evolved from a rule-based demand-zone detector into a multi-version short-horizon equity-prediction pipeline. This development record asks what each iteration changed, what its reported metrics appeared to show, and what methodological limitations remain. The available artifacts document plausible forward-information leakage, full-sample outcome-derived features, validation reuse, and label-handling concerns in some older pipelines. Because the historic experiments differ in target, rows, features, folds, and selection process, the repository does not support a reliable numerical estimate of how much past performance was caused by leakage. The recovered V2 table has 44,854 rows across 149 tickers from August 2021 through June 2026; the associated local OHLCV cache audited for the study contains all 149 roster files plus SPY, QQQ, IWM, and VIX, with coverage through August 3, 2026. The frozen v1.0.2 protocol specifies same-event A/B/C/D Logistic Regression-versus-LightGBM comparisons, chronological development folds, fold-local preprocessing, label-maturity purging, and a hash-chained prospective logging plan. The separate immutable v1.0.1 archive report records 61,045 candidate events, 61,045 valid labels, and 41,221 out-of-fold scores across the 2023–2025 folds. The closeout recalculated the pooled and per-fold point metrics from saved OOF scores and matched the manifest/report; this does not reproduce how the historical features or predictions were generated. The exact source is unavailable, and the current reconstruction has not matched archived feature values. The archive's reported bootstrap intervals were not reproduced by the current helper. Thus all values remain retrospective v1.0.1 archive results—not v1.0.2 results or an untouched confirmation. There are no prospective predictions or outcomes. The archive does not establish prospective market-structure value, generalization, or profitability.

## 1. Introduction

Short-horizon equity prediction is difficult. Daily returns are noisy, relationships change across market conditions, and a model can appear successful when its training pipeline exposes information that would not have been known at prediction time. These difficulties matter for technical and market-structure features: a signal might contain useful information, but complex historical features and repeated searches also create opportunities for look-ahead, target contamination, and data snooping.

Demand Zone AI began as software to identify potential demand zones—historical price areas treated by the system as possible support—and display related indicators and trade simulations. The project expanded into dataset-generation scripts, forward targets, feature pipelines, multiple model versions, and a web application. Version numbers are not a single linear chain: dataset-generation versions (including V10–V13), training-model versions (V1–V7), and product releases describe different components.

This paper treats the work as an evolving research pipeline rather than a validated prediction product. Its purpose is to distinguish code-level observations from saved metrics, comments, and unverified claims; reconstruct what can be established from available artifacts; and explain why each result needs a reproducible target, point-in-time features, and a locked evaluation process. The narrative is not “each version predicted better,” but “each version changed the question and the evidence needed to assess it.”

### 1.1 Research questions

The overarching question is:

> **Can machine-learning models provide reliable predictive information about short-horizon equity movements under strict, leakage-aware temporal validation?**

The market-structure question is:

> **Do demand-zone and related market-structure features add predictive ranking information beyond conventional price, momentum, volume, volatility, and market-context features?**

Part I also asks what the development iterations changed and which application-specific limitations are supported by code or retained artifacts. A broader motivation is how much apparent financial-ML success may reflect model complexity, experimental choices, or leakage. That last question is not a measured fraction here. Old versions were not reproduced on one matched target, event set, fold schedule, and model-selection budget, so an overall “leakage share” cannot be inferred.

The frozen machine-readable v1.0.2 protocol specifies one target and event-generation contract, compares a simple linear classifier with a fixed nonlinear classifier, and incrementally adds volatility/context and market-structure features on identical events. Section 5 transcribes the results reported in the separate v1.0.1 archive; it does not present a verified v1.0.2 replay. The archived dates and related data were available to earlier project development, so those values are retrospective in any case. The exact archived source is missing, and the current reconstruction has not matched archived features. No source-verified v1.0.2 result, prospective lock, or prospective conclusion is available.

### 1.2 Scope and contribution

This is a project-specific account of limitations that become visible in a financial-prediction pipeline: future information can enter predictors, labels can be mishandled, repeated model selection can compromise validation, prices and market relationships may change over time, historical universe membership may be biased, and ranking metrics are not returns. Some risks are directly visible in inspected code; others remain unresolved because the necessary source vintages, point-in-time membership, or original run artifacts are missing.

The paper contributes a qualified development chronology, an application-specific source audit, and a controlled experiment specification with archived retrospective results. It does not establish that those results generalize beyond the development period, that demand-zone features add stable prospective value, that a displayed score is calibrated, or that a strategy is profitable.

## 2. Related work

Machine learning has been applied to empirical asset pricing using large predictor sets and nonlinear methods. Gu, Kelly, and Xiu compare machine-learning approaches to measuring risk premia [1]. Their work provides context for fixed model comparison, but Demand Zone AI is narrower: it concerns selected short-horizon labels conditional on candidate demand-zone retests.

Financial research also faces data-snooping and multiple-testing risks. Sullivan, Timmermann, and White evaluate technical rules while accounting for a search across candidate strategies [2]. Harvey, Liu, and Zhu discuss multiple testing in the search for return predictors [3]. Bailey and coauthors propose a framework for estimating backtest overfitting [4]. These concerns motivate this project’s versioned protocol, fixed feature whitelist, explicit chronology, and restraint about results chosen after many experiments.

Chronological splits better match the intended forecasting task than random row splits, but chronology alone is not sufficient. Every input must be available at the signal timestamp, learned transforms must be restricted to training rows, forward labels must be mature before validation, and repeated inspection can still turn development folds into development data.

## 3. Data and target definitions

### 3.1 Legacy dataset and local cache

The saved V2 report and local CSV identify **44,854 rows**, **149 tickers**, and dates from **August 3, 2021 through June 24, 2026**. A current source audit confirms the expected **153 OHLCV files** for the sorted 149-symbol roster plus SPY, QQQ, IWM, and VIX (`XVIX.csv`); the latest cached date is **August 3, 2026**. This confirms file presence and reported coverage, not point-in-time vendor vintages.

For the new study, the legacy V2 table is used only to recover the fixed 149-symbol roster. Its old event rows, labels, and features are excluded from the controlled study’s feature matrix and target construction. This avoids inheriting old forward-return predictors and label conversions, but it does not solve historical roster survivorship or price-vintage concerns.

The fixed roster’s selection procedure, historical constituent membership, and delisted-security coverage are unresolved. The OHLCV files are Yahoo-derived adjusted snapshots; historical vendor revisions and point-in-time adjustment information cannot be independently verified. The historical development findings are restricted to this roster and data snapshot; they do not generalize to all US equities.

### 3.2 Frozen executable target

For signal date T, the frozen outcome is the return from the next ticker trading session’s open to the following session’s open:

\[
R_T = \frac{O_{T+2}}{O_{T+1}} - 1,
\qquad
Y_T = \mathbb{1}[R_T \ge 0.02].
\]

A label is eligible only when both forward opens and the computed return are finite and strictly positive. The validity filter is applied before class conversion. This is intentionally distinct from earlier 20-day +15%/-5% barrier simulations, SPY-relative outcomes, magnitude labels, and heuristic “success” proxies.

The historical hold-1 target builder filters some rows by `hold1_ret`, but its threshold comparisons can convert missing future returns to apparent zero labels if missing rows are retained. The v1.0.2 protocol requires rebuilding the target from local OHLCV with an explicit valid-outcome mask. The current reconstructed module implements that rule, and its tests cover missing/nonpositive future opens and the inclusive 2% threshold; neither fact establishes that the missing v1.0.1 source used identical code.

### 3.3 Point-in-time candidate events

The v1.0.2 protocol defines a local swing-low pivot as confirmed only after two subsequent bars close, then permits a candidate at the start of a later retest run. It requires at most one event per ticker-session and signal features restricted to bars through T. The protocol also requires a streaming order-block tracker and prefix-invariance checks. The present editable module is a reconstruction: synthetic prefix tests cover its current behavior but do not establish historical source parity. The archive has matching event count and ID/order in the prior prefix comparison, but many feature values differ. The model population is a heuristic candidate-event sample, not every stock on every date; its historical archived implementation remains unverified.

## 4. Project and model evolution

“V1,” “V2,” etc. occur in different project subsystems. Dataset versions, training-model versions, and product releases should not be treated as one controlled experiment. The following table summarizes currently retained historical evidence; reported values are not independently validated by the new protocol.

| Stage | Documented development | Reported result / evidence | Current interpretation |
|---|---|---|---|
| Demand-zone prototype / dataset lineage | A daily-OHLCV pipeline detects swing-low zones, records retests, computes technical/zone features, and simulates future barrier outcomes. Current generator configuration includes a 20-day horizon, +15% target, and -5% stop. | Source scripts document design; a complete immutable sequence of early datasets/results is not available. | Engineering origin, not a fully reproducible model laboratory notebook. Future barrier fields belong to labels/backtests, never predictors. |
| V1 baseline (as quoted by V2 report) | The V2 report calls this a hold-1 XGBoost baseline with 50 features. | AUC 0.619 and top-5% hit rate 29.0% are quoted in the later report; the exact original run artifacts were not recovered in the inspected paths. | Attribute only to the later report until original splits, code, and predictions are recovered. |
| V2 | Adds market regimes, relative strength, liquidity, volume, volatility, event features, and comparisons across several estimators/targets. | Saved report/CSV: CatBoost mean AUC 0.67595 (SD 0.02284); report also gives a negative simulated trading result. | Source review found probable forward benchmark-return columns surviving the predictor filter; targets and backtest also need matched reproduction. Not leakage-free evidence. |
| V3 | Expands target menu with SPY-relative labels, adds gaps/open-drive features, and aims for a larger universe. | Metadata reports `alpha_spy_2pct` mean AUC 0.72811 across five folds. | Different target and likely retained forward benchmark columns. Do not compare as an apples-to-apples gain over V2. |
| V4 | Adds ensemble, interactions, recency weights, and ticker/month outcome-derived encodings. | Metadata reports `alpha_spy_2pct` OOF AUC 0.74464, temporal test AUC 0.72799, top-5 hit 53.49%. | Full-sample encoding and forward benchmark concerns require a corrected matched replay. |
| V5 | Adds sector ETF/VIX context, gaps, zone geometry, magnitude targets, interactions, and an ensemble. | Metadata selects `alpha_spy_3pct`: OOF AUC 0.78408, test AUC 0.75295, top-5 hit 43.13%. | Different, rarer target; full-sample outcome encoding and forward benchmark risks remain. This is not a controlled improvement estimate. |
| V6 | Adds magnitude and same-day-close experiments on V5 data. | Metadata reports magnitude AUC 0.72583 and same-day absolute-move AUC 0.76056. | Different outcomes and inherited upstream concerns; not directly comparable to hold-1 prediction. |
| V7 | Uses a fixed equal-weight tree ensemble, chronological folds, and explicit future-column exclusions. | Metadata reports OOF AUC 0.7084 for `hold1_2pct`, 0.7049 for `alpha_spy_2pct`, and 0.6989 for a magnitude target. | Broader exclusions are useful but comments do not prove point-in-time construction. Still historical, unmatched, and non-prospective. |
| V10–V13 dataset augmentation | Adds engineered features, market-context proxies, higher-timeframe structure, and order blocks. | Scripts exist; not all corresponding datasets or comparable model tables were found. | Feature-engineering intent, not verified performance progression. Some targets are heuristics rather than realized threshold outcomes. |

### 4.1 Historical target and feature differences

The project contains at least two different target families: the next-open-to-next-open `hold1_2pct` target and a 20-day barrier-touch target. Later datasets also include benchmark-relative, same-day, magnitude, and proxy labels. AUC values across these targets do not estimate the same question. The frozen v1.0.2 protocol specifies only the explicit hold-1 target; the archived baseline described below is v1.0.1.

V2’s data builder creates benchmark columns such as `bench_{symbol}_hold1` from a future open relative to the signal-date close. Those values are unavailable at close T and are a clear source-level look-ahead concern if included as predictors. Other old feature screens, target encodings, whole-sample feature auditing, and validation reuse are also risks documented in the project audit. Their impact on old metrics has not been measured through matched reproduction, so this record does not attribute a numeric fraction of performance to them.

## 5. Immutable v1.0.1 archive values and recovery limits

The immutable archive manifest under `outputs/study_v1/development/` identifies `DZAI-MARKET-STRUCTURE-ABLATION-V1` version **1.0.1** and records code SHA-256 `29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b`, protocol SHA-256 `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`, plus hashes for its event table, OOF predictions, source data, and eight models. Its report records the `hold1_2pct` target, nested A/B/C/D feature sets, Logistic Regression and LightGBM, 2023–2025 folds, and the following counts/metrics. The exact source file associated with the recorded code hash is not present as an intact Python source file. The preserved source prefix matched event counts and event-ID order but not numerous feature values, including `rsi14`, `atr_pct`, and `zone_width_pct`. A scoped AAL check found 480 aligned IDs, with all 480 rows differing on each of those three indicators; this was a single-symbol feature audit, not a full replay. The older bytecode used for a separate bounded replay is explicitly unreviewed, and its cache file was subsequently overwritten during syntax validation; no copy matching the execution hash was found in the workspace. Consequently, the tables below transcribe the immutable v1.0.1 archive report. A closeout check recomputed pooled and per-fold summary metrics from saved OOF scores and matched the manifest/report, but did not regenerate events/features, refit models, or reproduce predictions from the historical source. These are archived v1.0.1 values—not a source/feature reproduction or v1.0.2 results. Do not treat the bytecode replay as confirmation.

According to that archived report/manifest, the fixed-roster run contains **61,045 candidate events**, **61,045 valid labels**, from **149 tickers**, dated **2021-08-03 through 2025-12-31**. It reports **41,221 pooled OOF events** across the 2023, 2024, and 2025 validation folds, with 19,824 matured rows outside those OOF score sets. The reported positive rate is **17.58%** across all eligible archive rows and **16.48%** in pooled OOF rows. The source cache extended to August 3, 2026; the v1.0.2 protocol now explicitly specifies an exclusive 2026-01-01 signal-date cutoff, but that protocol contract does not retroactively prove the archived code or features conform to v1.0.2.

**Important interpretation:** these archive values are **retrospective historical development only**, not a confirmatory test or untouched holdout. The dates and fixed roster were available to earlier project development. The current protocol is frozen as v1.0.2 but has no source-verified replay; the archive itself is v1.0.1, and the reconstructed source has not established feature parity. The protocol has not been externally preregistered.

### 5.1 Pooled OOF values reported by the v1.0.1 archive (saved-score point-metric check passed; source/prediction generation not reproduced)

| Estimator | Arm | OOF events | Positive rate | Pooled ROC-AUC | Average precision | Mean daily AUC (two-class dates) |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | A | 41,221 | 16.48% | 0.5901 | 0.2324 | 0.5883 |
| Logistic Regression | B | 41,221 | 16.48% | 0.6608 | 0.2688 | 0.6815 |
| Logistic Regression | C | 41,221 | 16.48% | 0.6603 | 0.2663 | 0.6752 |
| Logistic Regression | D | 41,221 | 16.48% | 0.6596 | 0.2655 | 0.6732 |
| LightGBM | A | 41,221 | 16.48% | 0.6718 | 0.2610 | 0.6692 |
| LightGBM | B | 41,221 | 16.48% | 0.6778 | 0.2739 | 0.6931 |
| LightGBM | C | 41,221 | 16.48% | 0.6835 | 0.2768 | 0.6940 |
| LightGBM | D | 41,221 | 16.48% | 0.6848 | 0.2748 | 0.6944 |

The archived report/manifest states that the eight combinations used common validation rows/labels, fold-local imputation/scaling, and training labels matured strictly before each validation start. The report gives Logistic Regression pooled fold AUCs for A/B/C/D of 0.6093/0.6655/0.6755/0.6707 in 2023; 0.5840/0.6750/0.6759/0.6769 in 2024; and 0.5742/0.6803/0.6708/0.6726 in 2025. It gives LightGBM A/B/C/D fold AUCs of 0.6696/0.6881/0.6907/0.6920 in 2023; 0.6798/0.6685/0.6801/0.6806 in 2024; and 0.6670/0.6876/0.6898/0.6904 in 2025. These are values retained in the archived report, not an independent rerun from recovered historical source; they do not demonstrate future stability.

### 5.2 Prespecified paired development contrasts

| Contrast | Δ pooled ROC-AUC (recalculated from saved OOF scores) | 95% four-week interval (archive-reported) |
|---|---:|---:|
| LightGBM A − Logistic Regression A | +0.0818 | [0.0658, 0.0990] |
| LightGBM C − LightGBM B | +0.0057 | [0.0022, 0.0092] |

The archive manifest reports 1,000 paired circular moving-block bootstrap resamples of four consecutive calendar weeks, seed 42. In the closeout, the point deltas above were recalculated directly from the saved OOF predictions and matched the manifest. The archived interval bounds were not recalculated in this closeout; a previous full run of the current reconstructed helper did not reproduce any of the seven manifest intervals, with the root cause unknown. Preserve the displayed bounds as archive-reported only—do not substitute the current helper's bounds or claim independent interval reproduction. These descriptive intervals are not formal confirmatory p-values, and no correction for project-wide model/feature search can make the previously inspected dates untouched. Secondary archive-reported deltas include LightGBM B−A +0.0060 (interval [−0.0086, 0.0217]), Logistic Regression B−A +0.0707 ([0.0503, 0.0947]), Logistic Regression C−B −0.0004 ([−0.0044, 0.0035]), Logistic Regression D−C −0.0007 ([−0.0034, 0.0019]), and LightGBM D−C +0.0013 ([−0.0019, 0.0051]). The D−C archive interval spans zero; do not claim an order-block improvement from these results.

The v1.0.1 report's model/feature comparisons describe saved scores for its historical event sample. This closeout recalculated point metrics from retained OOF scores but did not regenerate features, refit models, or reproduce the historical pipeline from source. AUC does not mean calibrated probability or profitable trading; top-5 event precision, when summarized, is conditional on the emitted candidate universe. No causal market-support claim is made. The 2026 tail was recorded for source coverage only and was not used as a holdout or diagnostic score period.

The current automated suite covers missing/invalid outcome handling, threshold alignment, historical-cutoff behavior, immutable archive artifact hashes, purge logic, nested whitelist, banned feature names, training-fold-only transforms, identical event/label rows across the eight model/arm combinations, synthetic order-block and event prefix-invariance, ledger hash-chain/tamper/orphan/incomplete-run checks, canonical universe hashing, outcome maturation, no-candidate clock behavior, and prospective 12/18-month plus 2,000-event maturity semantics. These tests exercise the current reconstructed code and verify selected preserved artifacts; they do not establish feature parity or independently reproduce the archived folds.

The v1.0.1 run manifest records that its eight prospective-intended model pipelines were fit on **60,961** eligible events with signal dates and label exits before 2026, then saved under `outputs/study_v1/models/`. The archived event table, OOF predictions, run manifest, and report remain under `outputs/study_v1/development/`. The Plan B read-only audit verified the 153 source CSV hashes, both primary result-table hashes, and all eight model hashes against the manifest; it also verified OOF/event-table identity and recalculated pooled/fold point metrics from retained OOF scores. This confirms retained-file integrity and arithmetic on saved predictions, not code-to-feature/model reproduction. The current study implementation and frozen v1.0.2 protocol do not match the v1.0.1 code/protocol hashes, and feature parity failed. No prospective lock or ledger exists; these historical models are not lock-eligible under the current reconstruction, and their existence does not mean a prediction was made prospectively. See the [archive-only closeout report](outputs/study_v1_archive_audit_closeout.md) for the bounded checks and limitations.

## 6. Legacy reported metrics and limits of interpretation

The prior V2 report quotes CatBoost mean AUC 0.67595. Metadata for other versions quotes values including 0.72811 (V3 alpha-SPY 2% target), 0.74464/0.72799 (V4 OOF/test on alpha-SPY 2%), 0.78408/0.75295 (V5 OOF/test on alpha-SPY 3%), and V7 OOF 0.7084 for hold1 2%. These are different pipeline records on different targets and feature sets, with unresolved source-timing, validation, and reproducibility issues. They remain development claims, not controlled v1 results.

The V2 report also records a negative historical backtest under its stated assumptions. Because the backtest implementation and potentially its model inputs require audit, it should not be used as a validated estimate of net strategy performance. More generally, ROC-AUC measures ranking, not calibrated probabilities or expected portfolio return. Top-k event precision is conditional on event candidates; it does not show all-market opportunity or tradability.

The saved v1.0.1 OOF scores yield a LightGBM C−B point AUC difference of +0.005688, matching the archived manifest; the report rounds this to +0.0057. Its 95% interval [0.002179, 0.009191] is archive-reported only because the current bootstrap helper failed to reproduce the manifest bounds. More importantly, the original source is unavailable and reconstructed features do not match the archive. Therefore the small historical point difference cannot be attributed confidently to the intended demand-zone features, and neither it nor the other archived scores establishes generalization beyond the previously inspected period, stable prospective structure value, or profitability. The outcome of any separately authorized future prospective test may be positive, null, or negative; null results are scientifically acceptable.

## 7. Prospective test status and limitations

The prospective protocol requires predictions logged after the code/model/data/protocol lock, with an append-only hash-chained record written before outcomes. No historical prediction can be backfilled. The first successfully logged eligible event starts the duration clock; successful no-candidate runs and failures are retained but do not start it. Predictions stop at 2,000 events or 18 months, whichever comes first. The single final analysis is allowed only after both 12 calendar months and at least 2,000 eligible outcomes mature. If fewer than 2,000 events mature by month 18, the shortfall must be reported; no extension or result-dependent early stop is allowed.

At the time of this audit, there is no prospective lock or ledger and there are **zero prospective predictions and zero prospective outcomes**. The immutable v1.0.1 archive exists, but its exact source is missing; the v1.0.2 reconstruction does not match the archived feature table, and the separate bytecode replay is explicitly unreviewed. A reviewed, source-verified v1.0.2 implementation and separately archived, hash-consistent development run are required before an explicit prospective freeze can be considered. Existing OHLCV is historical development data even where its latest bar is August 2026; it cannot stand in for a fresh, pre-outcome prediction. No prospective conclusion is claimed.

Other limitations include the fixed 149-symbol roster’s unresolved survivorship and selection, Yahoo-derived historical snapshot revisions, heuristic event definition, no verified all-market coverage, and absence of independently reproduced legacy runs. A public dashboard or model artifact is not a forecasting trial unless dated predictions are retained before the outcomes occur.

## 8. Discussion and conclusion

Demand Zone AI’s history illustrates that predictive performance is a property of the full experiment—not just its classifier. Target definitions, information timing, universe construction, preprocessing, fold boundaries, model search, and repeated validation use determine whether a reported score has a forecasting interpretation. A chronological split cannot fix a future return already embedded in a feature; a claimed holdout ceases to be untouched once it guides later choices.

The machine-readable v1.0.2 JSON protocol is frozen and authoritative as a protocol; it is not an execution record. The separate v1.0.1 archive passed output-hash and saved-OOF point-metric checks, but its exact source is unavailable, the reconstruction fails feature parity, and archived bootstrap intervals remain unverified by the current helper. The Plan B closeout found the archived LightGBM C−B point delta is only +0.0057; source/feature mismatch prevents a defensible claim that the intended demand-zone features caused that difference. This is retrospective development evidence, not an untouched confirmation. There are zero prospective predictions and zero outcomes, so reliable prospective predictive information, incremental structure value, calibration, and profitability remain unestablished.

The finite archive-only closeout is complete; no further source/bytecode hunt, canonical development rerun, new study, or prospective lock was authorized or performed. Do not rescue the record by selecting a favorable metric or changing the target. Preserve the archived values and caveats as documented; the exact source/feature run is unreproduced and the intervals remain archive-reported only. Any distinct future v1.0.2 implementation/run or prospective test requires its own review and explicit authorization. A historical replay can be reconsidered only if trusted exact artifacts become independently available; it cannot produce a universal “leakage share” or make used dates prospective.

## References

[1] Gu, S., Kelly, B., & Xiu, D. (2020). Empirical Asset Pricing via Machine Learning. *The Review of Financial Studies, 33*(5), 2223–2273. https://doi.org/10.1093/rfs/hhaa009

[2] Sullivan, R., Timmermann, A., & White, H. (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *The Journal of Finance, 54*(5), 1647–1691. https://doi.org/10.1111/0022-1082.00163

[3] Harvey, C. R., Liu, Y., & Zhu, H. (2016). ...and the Cross-Section of Expected Returns. *The Review of Financial Studies, 29*(1), 5–68. https://doi.org/10.1093/rfs/hhv059

[4] Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2017). The Probability of Backtest Overfitting. *The Journal of Computational Finance, 20*(4), 39–69. https://doi.org/10.21314/JCF.2016.322

## Appendix A. Plan B closeout status

- [x] Keep the frozen machine-readable v1.0.2 protocol distinct from the immutable v1.0.1 archive.
- [x] Close exact historical source/bytecode recovery as unavailable; disclose the overwritten bytecode and stop recovery attempts under Plan B.
- [x] Record that available source-prefix events match counts and ordered IDs but fail feature parity; the scoped AAL check differed on all 480 aligned rows for `rsi14`, `atr_pct`, and `zone_width_pct`.
- [x] Verify all 153 source CSV hashes, both primary-table hashes, and all eight model hashes against the v1.0.1 manifest.
- [x] Verify OOF/event-table identity, signal-date cutoff and label rows; recalculate pooled and fold metrics from saved OOF scores, matching manifest/report values.
- [x] Retain confidence intervals as archive-reported only after the current helper failed to reproduce any of seven archived bounds in the prior full check; do not replace them.
- [x] Run the 22 current unit tests and safe syntax/XML checks without `py_compile`; tests do not establish historical feature parity.
- [x] Align this draft, protocol notes, Word companions, and the [archive-only audit closeout report](outputs/study_v1_archive_audit_closeout.md) to the evidence boundary.
- [x] Confirm no canonical development rerun, new study artifact, prospective lock, prediction, or outcome was created; archive remains unchanged.
- [x] Record that any new reviewed v1.0.2 run or prospective trial is a distinct future task requiring separate explicit authorization—not an open step in this closeout.

**Audit implementation:** [read-only saved-output audit utility](.freebuff/recovery_tools/audit_saved_v1_0_1_outputs.py). The utility recalculates saved-score metrics and checks retained file hashes; it does not regenerate events/features, fit models, or create prospective artifacts. Bootstrap recalculation is opt-in via `AUDIT_RECOMPUTE_BOOTSTRAP=1` and was not run again for this closeout.

## Appendix B. Repository artifacts

Primary historical artifacts include `README.md`; `Python/generate_ml_dataset.py`; `Python/augment_v10_to_v11.py`; `Python/augment_v11_to_v12.py`; `Python/augment_v12_to_v13.py`; `Python/order_block_detector.py`; `backend/build_hold1_targets.py`; `backend/build_v2_dataset.py`; `backend/build_v3_dataset.py`; `backend/build_v5_dataset.py`; `backend/train_hold1.py`; `backend/train_v2.py`; `backend/train_v3.py`; `backend/train_v4.py`; `backend/train_v5.py`; `backend/train_v7.py`; and saved reports/metadata under `outputs/v2` and `models/v2` through `models/v7`. The frozen protocol is `MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json`; `backend/demand_zone_study_v1.py` is a non-equivalent reconstruction under audit, and `backend/tests/test_demand_zone_study_v1.py` exercises its current behavior rather than proving historical source identity.
