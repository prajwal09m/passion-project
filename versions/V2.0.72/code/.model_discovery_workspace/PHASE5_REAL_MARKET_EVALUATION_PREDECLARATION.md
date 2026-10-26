# Phase 5 Real-Market Predictive Comparison — Predeclaration Draft

**Status: DRAFT — NOT AUTHORIZED; DO NOT EXECUTE.** Prepared 2026-10-18 for owner and independent statistical reviewer. This document is a proposal only. It does not authorize a market-data evaluation, model fitting, candidate selection, campaign run, holdout read, or change to any frozen policy.

**Version reconciliation required before approval:** this draft names frozen protocol `DZAI-MARKET-STRUCTURE-ABLATION-V1` v1.0.1, while the working tree contains [MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json](../study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json) v1.0.2. The development run manifest identifies v1.0.1 and pins outputs to it. No protocol file/hash was read as evaluation data and no market comparison was run. Owner and reviewer must determine whether this proposed comparison is explicitly an extension under frozen v1.0.2 or a v1.0.1 reconstruction, pin its exact protocol bytes/digest, and resolve the conflict; this draft must not be executed against either version until the pin is unambiguous.

**Predeclaration detail gap:** the older version listed in the pinned manifest is `DZAI-MARKET-STRUCTURE-ABLATION-V1` v1.0.1. The exact A/B contrast permitted below is *not* silently treated as a result-ready study plan: protocol v1.0.2's historical primary contrasts list LightGBM-A minus LogisticRegression-A and LightGBM-C minus LightGBM-B, while its secondary list includes B-A within each estimator. A→B with LogisticRegression is only a conditional fixed ablation proposed here, and must be explicitly approved as such or replaced in a new reviewed predeclaration. No selection can be made from already seen OOF scores.

**Boundary non-claim:** the protocol artifact itself includes the text `prospective_evaluation` (a design section); this does not prove what filesystem path is the sealed holdout or that the run-manifest-pinned event table and OOF rows are disjoint from it. The owner must establish the precise protected path/boundary from the design record without opening, listing, hashing, or querying its contents. This remains a hard blocker.

**Uncertainty method reconciliation:** frozen protocol v1.0.2 specifies a 1,000-replicate, seed-42, four-consecutive-calendar-week circular moving-block bootstrap over pooled OOF rows. A 5,000-replicate alternate is not authorized by this document. The default proposal is to retain exact frozen `n_boot=1000`, circular wrapping/truncation and paired row indices. Any alternative statistic, replicate count, event-cluster bootstrap, or resampling unit requires reviewer approval and owner authorization recorded before running. The v1.0.0 executable harness's bootstrap implementation and the v1.0.2 written protocol must be verified to match this exact procedure before execution; discrepancy blocks the run.

**ECE detail:** the local development harness defines 10 equal-width bins `[0,0.1), …, [0.9,1]`, skips empty bins, and weights each non-empty-bin absolute confidence–frequency gap by bin row share. This is inspected code, not proof of the v1.0.2 producer/metric pin. Freeze exactly this convention only if the owner/reviewer confirms it matches the pinned protocol; otherwise the comparison remains blocked until ECE is fully specified and independently reviewed.

**No campaign path:** this draft authorizes no candidate generation, statistical-method adoption, campaign execution, launch, model promotion, or sealed-holdout access, including if a later comparison appears favorable.

## 0. Supersession and exact decision register

**Version 1.1 readiness-preparation update (2026-10-18):** This revision adds an explicit closure checklist below. No protocol choice was made; all earlier unresolved statements remain controlling. This file is not an owner decision, reviewer sign-off, or authorization. No evaluation data or OOF prediction artifact was opened or analyzed while making this update.

### 0.1 Required pre-execution fields (all unresolved unless expressly marked otherwise)

| Requirement | Current value/status | Required evidence before any evaluation |
|---|---|---|
| Dataset/run identifier | Existing manifest metadata names `DZAI-MARKET-STRUCTURE-ABLATION-V1` v1.0.1; proposed approved dataset/use **UNRESOLVED** | Owner/data steward specifies eligible dataset/run ID, exact allowed paths and digests, permitted operation and one-use scope |
| Protocol version and digest | v1.0.1 manifest digest conflicts with v1.0.2 protocol artifact; **UNRESOLVED** | Owner chooses exactly one immutable protocol; recaptured SHA-256; reviewer accepts that same version |
| Target definition | Draft proposal: `hold1_2pct`, `Open[T+2]/Open[T+1]-1 >= 0.02`; **NOT APPROVED** | Owner/reviewer confirm it is the selected protocol target, exact maturity/exclusions and sign convention |
| Split rules | Draft proposal: chronological folds 2023/2024/2025 with `date < year_start` and `exit_date < year_start` training purge; 2025 is previously exposed/retrospective; **BOUNDARY UNRESOLVED** | Owner/data steward confirms eligible temporal boundary from governance records; reviewer accepts purge, embargo, exposure, and grouping; never inspect sealed data to verify |
| Baseline | Draft proposal: fixed Arm A LogisticRegression matched to Arm B; **CONTRAST NOT APPROVED** | Owner selects exact comparator only after protocol reconciliation; pin estimator, features, preprocessing, folds and seeds |
| Primary contrast | A→B LogisticRegression is not listed as v1.0.2 primary; **UNRESOLVED** | Owner explicitly approves as a reviewed extension or replaces with a new independently reviewed declaration before any further score access |
| Metrics and acceptance criteria | Draft AUC delta and Brier/ECE margins; **UNRESOLVED** pending protocol/reviewer reconciliation | Freeze metric definitions, thresholds, direction, all required strata, and multiplicity family |
| Uncertainty method | Draft says four-week circular moving-block paired bootstrap, seed 42, 1,000 replicates; harness equivalence **UNVERIFIED** | Reviewer accepts group/time unit and uncertainty procedure; code-to-protocol equivalence test plus independent recalculation |
| ECE | Local harness convention is 10 equal-width bins, skip empty bins, occupancy weights; **PROTOCOL MATCH UNVERIFIED** | Owner/reviewer confirm exact edges, inclusive upper-edge convention, empty-bin behavior, weighting and uncertainty |
| Candidate selection/multiplicity | No new candidate search authorized; one fixed contrast proposed; multiplicity/selection treatment **UNRESOLVED** | Define all comparisons and family, one-use rule, retries, no post-hoc selection, and adjustment/claim scope |
| Stopping and missingness | Draft says stop on any missing/invalid/mismatched input and unresolved boundary; **PROPOSAL ONLY** | Owner/reviewer approve explicit stop, invalid-resample, inconclusive, failure and deviation rules |
| Protected final-evaluation boundary | Exact governed boundary and development disjointness **UNRESOLVED** | Owner/data steward attests from authoritative metadata without opening/listing/hashing/querying protected contents; if impossible, do not evaluate |
| Independent review | No independent C5 reviewer/sign-off; **PENDING** | Non-implementing independent statistician provides written report against exact final document digest |
| Owner authorization | **NOT GRANTED** | Authentic explicit owner decision names final protocol, dataset IDs/digests, contrast, allowed outputs and prohibited operations |
| Campaign integration / launch | **NOT AUTHORIZED** | Separate later owner decision after prerequisites; cannot be inferred from this predeclaration or test results |

If any row remains unresolved, the status remains **NOT AUTHORIZED; DO NOT RUN**. Unknowns are not defaults and silence is not consent.

### 0.2 Decision and evidence links

- Owner decisions: [CAMPAIGN5_OWNER_DECISION_PACKET.md](CAMPAIGN5_OWNER_DECISION_PACKET.md) — pending; no completed decision asserted.
- Independent review: [CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md](CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md) — template only; reviewer identity and answers intentionally blank.
- Blocker statuses and exact closure artifacts: [CAMPAIGN5_BLOCKER_REGISTER.md](CAMPAIGN5_BLOCKER_REGISTER.md) and [CAMPAIGN5_BLOCKER_REGISTER.json](CAMPAIGN5_BLOCKER_REGISTER.json).

No market evaluation, model fit, score, metric computation, candidate selection, or campaign execution is authorized by these linked documents.

## 0.3 Supersession and exact decision register


This file is a preparation draft only; it does not supersede a frozen protocol or earlier C4 predeclaration. The exact one-run decision fields that remain unresolved are:

| Field | Proposed fixed value | Approval status |
|---|---|---|
| Dataset/run ID | `DZAI-MARKET-STRUCTURE-ABLATION-V1`, manifest v1.0.1 rows | owner/reviewer must reconcile with v1.0.2 protocol |
| Frozen protocol | v1.0.1 manifest digest `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07` OR exact v1.0.2 file hash | unresolved; exactly one must be selected and rehashed before review/authorization |
| Contrast | Arm A LogisticRegression vs Arm B LogisticRegression | not listed as a primary v1.0.2 contrast; explicit fixed-extension approval or new predeclaration required |
| Primary target | `hold1_2pct`, `Open[T+2]/Open[T+1]-1 >= 0.02` | protocol-defined, subject to selected version confirmation |
| Primary metric | pooled paired chronological OOF ROC-AUC difference B−A | protocol-compatible secondary comparison only if expressly authorized |
| Bootstrap | frozen four-week circular moving-block paired AUC; seed 42; `n_boot=1000` | default; verify implementation/code match and reviewer acceptance |
| ECE | 10 equal-width probability bins with empty bins skipped and occupancy weights | matches local harness, still reviewer must verify pinned version |
| Holdout boundary | exact protected path, kept sealed; development-only allowlist | owner confirmation absent |
| Independent review | non-implementing external statistical reviewer, written sign-off | absent |
| Owner authorization | explicit written Phase 5 scope + exact digests + outputs | absent |

No market fit, score, metric calculation, or comparison is permitted until all fields are resolved and approval is recorded. If the owner wants the v1.0.2 primary contrast instead, create a new predeclaration and review it before inspecting any additional OOF results.

## 1. Exact decision and authorization gate

The proposed sole question is: **does adding the already-frozen market-structure feature block in Arm B to Arm A improve chronological out-of-sample ROC-AUC for the frozen binary event target, under the frozen protocol, beyond a predeclared practical threshold, without degrading calibration beyond its existing margins?** This is a fixed ablation, not a search over new estimators, features, operators, targets, or thresholds.

Before any new fit, scoring, metric calculation, or comparison on the retained market files, all of the following must be recorded in durable, append-only owner/statistical records:

1. **Explicit written owner authorization** naming the exact protocol version/digest, permitted dataset files/digests, one comparator and feature contrast, permitted outputs, and prohibition on holdout access. Existing C4/Phase 4 records explicitly say real-data integration is NOT AUTHORIZED; the Oct 11 H-10 owner authorization explicitly does not authorize statistical-method adoption, D2 closure, implementation, freeze, or launch. It is not authorization for this Phase 5 study.
2. **Independent external statistical review** of this predeclaration and its data/split/selection/uncertainty plan, returned in writing and recorded. The existing D2 AI review discloses the reviewer was the implementing AI and states the independent reviewer requirement is unresolved. Do not count that substitute as personnel-independent review.
3. **Owner confirmation of the holdout boundary** from the frozen design record: confirm that the exact development event table and OOF file listed below contain development rows only, that no row is from the sealed prospective set, and identify the protected prospective path/record without opening, hashing, listing, or querying its contents. The Phase 4 predeclaration says the boundary is unresolved.
4. Independent reviewer acceptance of the statistical unit, paired uncertainty method, and choice of final untouched calendar years. No execution until the reviewer has no unresolved blocking comments and the owner records approval after review.

**Currently recorded status:** owner authorization NOT GRANTED; external statistical review pending; development-vs-sealed boundary unverified. Therefore no Phase 5 market-data comparison is run. This draft does not satisfy these gates.

## 2. Frozen source inputs and fingerprints (re-capture only after approval)

Current byte hashes captured read-only on 2026-10-18:

| Role | Exact path | SHA-256 |
|---|---|---|
| Event rows, candidate-development scope | `study_files/outputs/study_v1/development/event_table.csv` | `232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0` |
| Existing out-of-fold predictions | `study_files/outputs/study_v1/development/oof_predictions.csv` | `011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829` |
| Dataset/run manifest | `study_files/outputs/study_v1/development/run_manifest.json` | `dab3ee5f6b07078f44d1c6bb2a76163e02619c301bc83b67bb49e9f2dab469c9` |
| Frozen study producer | `study_files/backend/demand_zone_study_v1.py` | `cea2440425e1f2f56a95b576481ae2ef603fe1f6a9816078e0a998781e0cef2a` |
| Frozen protocol | `study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json` | v1.0.2 file exists but exact byte digest is not recorded here; run manifest instead identifies v1.0.1 with digest `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`; owner/reviewer must resolve version and recapture a digest before approval |

Dataset/run identity currently recorded in the output manifest: `DZAI-MARKET-STRUCTURE-ABLATION-V1`, version `1.0.1`; manifest protocol digest `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`. The v1.0.2 protocol file exists separately; no claim that this manifest reproduces it. Event universe is a recovered fixed 149-ticker roster; its historical point-in-time constituent membership/delistings are unknown. Do not claim broad-market or survivorship-free coverage.

No prospective/holdout path is an input. The sealed boundary must be attested from governance/design documentation by the owner and reviewer, not “checked” by opening the holdout.

## 3. Population, prediction time, target, and eligible rows

- Population: eligible rows already recorded in the pinned retained development event table; no new bars, external data, universe refresh, row reconstruction, or unpinned feature derivation.
- Prediction time: event `date` (signal date). Keep only features available at that signal time under the frozen producer and its point-in-time assertions.
- Binary target exactly as frozen: `Open[T+2] / Open[T+1] - 1 >= 0.02`; use `label_valid` and the frozen event row. Do not retune the 2% threshold or substitute profitability.
- Purge: for each validation year, train rows require both signal `date < year_start` **and** outcome `exit_date < year_start`; validate only `year_start <= date < next_year_start`. Preserve the frozen W-1/2 open timing, event identity, and label maturity logic.
- The retained table has 61,045 matured event rows (2021-08-03 through 2025-12-31); existing OOF has 41,221 scored rows across 2023–2025, 157 W-SUN weeks, overall OOF positive prevalence 0.16477. These are provenance metadata, not a newly computed contrast result.
- The 19,824 earlier mature rows are training-only for the frozen walk-forward folds. Do not report in-sample training metrics as prediction evidence.

## 4. Fixed comparator and treatment (no search)

- Baseline: frozen Arm A feature set, same LogisticRegression estimator/settings, folds, seeds, event keys, preprocessing fit only on each training fold, and all frozen feature-availability checks.
- Treatment: frozen Arm B = Arm A plus the exact B-increment already defined by the frozen study; same estimator/settings and every other input and split held fixed.
- The feature arrays/config and implementation are pinned by the protocol and study source. No Arm C/D, LightGBM, random forest, generated interactions, new transformations, feature selection, hyperparameter tuning, post-hoc subgroups, or changes to training prevalence are permitted in this one contrast.
- Existing OOF values are only baseline-reproduction/provenance aids; do not select a different challenger based on previously observed OOF metrics. The exact preregistered contrast remains A→B and must be run once after approvals. The estimand is fixed before producing new comparison output.

## 5. Splits and one-use evaluation boundary

- Reproduce the frozen walk-forward folds for 2023, 2024, and 2025 with the purging rule above. Keep event keys paired exactly between A and B within each fold. Do not random-shuffle rows.
- Primary model-development/evaluation output: pooled chronological OOF across the three frozen years, with scores assembled on identical event keys.
- Year-wise AUC differences are predeclared diagnostics (2023, 2024, 2025), not additional hypotheses for selecting variants.
- The 2025 fold is the final temporal report stratum; no further tuning, rerun, feature decision, or threshold change may use it. The existing validation file and prior experiments mean this is a predeclared *fixed retrospective development* test, not a virgin holdout. If the independent reviewer says prior exposure invalidates confirmatory interpretation, report only descriptive reproduction and acquire a separately authorized future period for confirmation; never relabel 2025 or the sealed prospective data as available tuning data.
- No test/holdout file or campaign registry is needed or allowed. Output path is a new disposable directory under `.model_discovery_workspace/phase5_market_run/`; never write the persistent campaign state or alter source inputs.

## 6. Metrics, baseline, decision rule, and multiplicity

Primary outcome: paired pooled OOF ROC-AUC delta, `AUC(Arm B) - AUC(Arm A)`, on the identical eligible OOF event keys. Also report the two arms' separate AUC, event count, prevalence, average precision and Brier score. Calibration deltas are treatment minus baseline (negative favors Arm B). No trading/backtest/return claim is in scope.

Frozen acceptance margins from the historical protocol: primary AUC point delta at least `0`; lower bound of the paired 95% interval at least `-0.01`; Brier degradation no more than `+0.005`; ECE degradation no more than `+0.02`; all three years present. The precise ECE bin edges and empty-bin convention must be copied verbatim from the pinned producer/protocol into the final signed/approved record before execution; do not infer or select them after seeing results. This is one predeclared contrast, not a family-wide claim, and no additional method can be selected from the test result.

For the primary paired AUC interval, proposed default is exactly the frozen protocol's 1,000 circular moving-block bootstrap replicates, seed 42, four consecutive W-SUN calendar weeks, circular concatenation and truncation to the paired-row count. Use identical sampled event indices for both arms; record valid two-class replicate count and both percentile endpoints. For Brier/ECE, use the exact same paired weekly indices and report paired deltas. Independently verify the implementation against the pinned producer before any evaluation. Do not substitute the weekly sign-flip/Holm procedure for a predictive confidence interval. No change of replicate count, block size, circular rule, or statistical unit is authorized in this draft.

This is a fixed retrospective evaluation with previous exposure to OOF artifacts, so intervals are uncertainty summaries conditional on this design; they do not erase selection/exposure bias or establish prospective generalization. No threshold-based “winner” will be declared if the interval spans zero or fails a predeclared margin.

## 7. Software/provenance, run isolation, and artifacts

The current production harness writes into each candidate's disposable workspace, and its result includes broad runtime evidence. Any future approved execution must use a separate fresh copy of the explicitly allowlisted development inputs and run the fixed protocol without invoking the persistent campaign adapter/loop. No source `experiment_config`, candidate result, ledger, or campaign state is to be modified. This draft has not validated that execution isolation or these pinned protocol versions are currently congruent.

Before approval: run only offline static review and synthetic tests. After all gates are recorded, execution—if approved—must:

1. Reverify and log the five source digests above and current code/test digests. Any mismatch voids this draft pending review.
2. Use a fresh disposable directory with byte-copied, allowlisted development input(s), no prospective directory, no persistent campaign state, network disabled, no GPU, and no campaign entry point.
3. Execute one exact frozen-protocol A/B comparison; record command, environment/dependency versions, stdout/stderr, real exit status, runtime, row counts/split boundaries, duplicate/excluded-row accounting, and output file hashes.
4. Independently recompute paired event IDs, fold masks/purge, primary metric, and uncertainty using separate code; reviewer must verify.
5. Verify after run that all source and protected hashes match and that the disposable directory contains only declared output. Do not create, update, reconcile, or delete experiment/campaign ledger records. Retain the reviewable output; delete no historical artifact.

Predeclared output set: `evaluation.json`, `run.log`, `input_hashes.json`, `independent_check.json`, and `environment.json` in the disposable run directory. Do not write into champion/version or launch-gate records.

## 8. Failure, missingness, and deviations

Missing/invalid features, label maturity, duplicate keys, non-matching arm event sets, invalid fold, nonzero command exit, inconsistent source pin, absent owner/reviewer authorization, or holdout-boundary uncertainty means **STOP / BLOCKED**, not a partial success. Do not impute missing results as model failures. Record failed execution, refusal, inconclusive statistical decision, and unlinked/missing artifact as distinct statuses. Any deviation, retry with changed parameters, new estimator, extra comparison, threshold/metric change, or exposure to final 2025 predictions requires a new predeclaration and approvals before repeating.

## 9. Explicit non-claims and signature record fields

Even a successful authorized execution would establish only the result of this fixed retrospective development comparison on this recovered roster and split. It would not establish profitability, point-in-time OHLCV integrity, survivorship-free universe validity, prospective generalization, sealed-holdout performance, independent validation of the sign-flip method, campaign approval, or deployment readiness.

Approval record must append: owner identity/time/scope; independent reviewer identity, affiliation/independence and written assessment; explicit reviewer/owner acceptance of the exact dataset/protocol pin, contrast and holdout boundary; code/data/config hashes; approved uncertainty algorithm and ECE bin definition; confirmation of no holdout access; dissent; and an explicit statement “no launch/campaign integration granted.” Until those records are present: **NOT AUTHORIZED; DO NOT RUN.**
