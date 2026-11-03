# M16 Failure Analysis — Every Live Run M5–M15, Traced From Artifacts

Read-only. All claims reference preserved run artifacts under
`model_autopsy/benchmarks/live_runs/` or milestone reports. Nothing was
re-run; no paid APIs were called. "Verified fact" = artifact text quoted
or byte-counted. "Observation" = my reading of artifacts. "Hypothesis" =
inference labeled as such.

## Master table

| Milestone | Run | Initial observations | Hypotheses | Experiments (ran) | Confirmed discoveries | Final verdict | Main limitation |
|---|---|---|---|---|---|---|---|
| M5 | live-140167117ef5 (turbine) | Lag-1 autocorr 0.776, train≪test error; drift direction visible | 3: level-shift/drift; split-hygiene artifact; persistent misspecification | 5 ran (forecast_diagnostics, regression_metrics, 3× propose_hypothesis) + 1 failed (time_split_validation bad args) | 0 (day-500 changepoint never isolated) | partial 0.55 | Scientific: mechanism unpinned; technical: driver FSM crash on attempt 1 |
| M6 | live-ae844753edce (claim) | Residual mean −131.77, MAE 132.51, R² −0.99 (calibration_snapshot) | 3: uniform bias; feature-dependent miscalibration; data-quality artifact | 6 ran (3× propose_hypothesis, calibration_snapshot, data_quality_profile, regression_metrics) | 0 (device_age dependence never computed) | inconclusive 0.62 | Scientific: stopped at symptom (bias scale) |
| M7 | live-1e19b2cdedfe (credit) | Pooled AUC 0.97 (classification_metrics) | 3: regional-AUC gap; regional miscalibration; base-rate/quality artifact | 8 executions vs 6-cap (breach): 3× propose_hypothesis, pooled classification_metrics ×2 (1 failed first), shift profile, calibration/error, data_quality | 0 (per-region AUC never computed) | inconclusive 0.61 | Architectural: cap unenforced; scientific: pooled metric only |
| M8 | live-dbf6a5b3fbff (rent) | District C MAE 584 vs ~95 (ratio 6.2, regression_metrics group_column=district) | 3: district bias from schema; mis-scaled feature; global miscalibration | 6/6 exact: 3× propose_hypothesis, regression_metrics, residual_feature_dependence, calibration_snapshot | 0 (correctly unconfirmed — corroboration bar held) | inconclusive 0.62 | Evaluative: right outcome, scored 0.0; attribution mud (supports on denying H3) |
| M9int | live-c0cae8776976 (turbine) | Changepoint + residual-time + shift probes all fired supports | 3: level shift; persistent bias; data-quality artifact | 6/6: 3× propose_hypothesis + 3 drift probes | 0 (confirmed_findings empty despite 3× supported statuses) | inconclusive 0.62 | Technical: negation-blind attribution (deniers got supports) |
| M13 | live-d8b174527ca5 (credit) | Pooled AUC + Brier 0.13 recorded | 2: region-specific failure; data-artifact rival | 6/6: 2× propose_hypothesis, calibration/error, artifact_summary ×2, classification_metrics ×1 failed | 0 (failure missed entirely) | inconclusive 0.63 | Scientific: only 2 real diagnostics; per-region measurement never attempted |
| M14 | live-ecdd47fafd9d (music) | H1 named cold-start new-slice collapse; pooled P@K >0.9 healthy | 3: slice-specific failure; sparsity/hygiene artifact; globally uninformative | 6/6: 3× propose_hypothesis, artifact_summary FAILED, classification_metrics (pooled/grouped AUC), segment_quality_screen | 0 (pooled AUC contradicted true H1; no slice-P@K probe existed in path) | inconclusive 0.63 | Architectural: metric inadequacy + missing slice-aware diagnostic in live path |
| M15 | none | — | — | — | — | — | Offline-first authorization; no live runs |

Statistic-audit cross-check (verified): offline discovery M9 0.938 / M10
0.906 (challenge-report table recomputed: [1,1,0.25,1,1,1,1,1] → 0.906);
live discovery 0.0 in all six strict runs (M6–M14; M5 0.4 under older
partial-credit rule); reasoning 0.6 in all seven scorecards
(byte-identical across `scorecard.json` files); team-vs-single +0.085 on
n=1 each. All confirmed.

## Per-run answers (the 10 questions)

### M5 turbine (live-140167117ef5)
1. Detected: drift direction (H1 named level shift/drift — verified fact,
   hypotheses.json). 2. Three competing hypotheses, all proposed. 3. All
   investigated implicitly. 4. forecast_diagnostics + regression_metrics +
   failed split validation. 5. Established lag-1 autocorr 0.776 and
   train≪test error (verified fact, milestone_5_results.md §14). 6. No —
   all statuses stayed `proposed` (verified fact). 7./8. No skeptic/judge
   in live path (verified fact: zero challenge/judge events in
   events_dump.json). 9. Partial: direction without day-500 isolation.
   10. Scientific (mechanism pinning) + technical (attempt-1 FSM crash).

### M6 claim (live-ae844753edce)
1. Detected: massive systematic overprediction (residual mean −131.77 —
   verified fact, milestone_6_results.md §C). 2.–3. Three hypotheses,
   uniform-bias lead. 4. calibration_snapshot, data_quality_profile
   (ruled out hygiene rival — genuine elimination), regression_metrics.
   5. Bias scale + no-duplicates evidence. 6. No — statuses frozen
   `proposed` (verified fact); summary carried recommendations but the DB
   never moved. 7./8. None live. 9. Inconclusive: device_age
   residual correlation never produced. 10. Scientific (stopped at
   symptom) + architectural (status-update path unfired live).

### M7 credit (live-1e19b2cdedfe)
1. Detected: pooled AUC 0.97 with prose-noted regional gap (verified
   fact). 2.–3. Three hypotheses; data_quality auto-contradicted H1/H3 via
   linker (first live status transitions: 2, verified fact). 4. Only
   pooled classification_metrics (group gap never measured) + shift +
   calibration + quality probes. 5. Clean quality evidence; regional gap
   unmeasured. 6. Partially (2 evidence-driven revisions). 7./8. None
   live. 9. Inconclusive + disclosed 8/6 cap breach. 10. Architectural
   (cap unenforced; brief ranked subgroup family "low") + scientific
   (wrong metric granularity).

### M8 rent (live-dbf6a5b3fbff)
1. Detected AND localized: district C ratio 6.2 with group_column
   (verified fact — the M7 miss, fixed). 2.–5. Three hypotheses, 5
   evidence-linked revisions; weak feature tracking (|r| 0.18)
   contradicted the mis-scaling rival. 6. Yes — statuses moved for
   recorded reasons (verified fact). 7./8. None live. 9. Inconclusive:
   corroboration bar correctly held (single concentration ≠ confirmed
   schema-vs-district mechanism). 10. Evaluative (right restraint scored
   0.0) + attribution defect (supports on denying H3 — verified fact,
   milestone_8_results.md Limitations).

### M9int turbine (live-c0cae8776976)
1. Detected: all three drift probes fired supports. 2.–5. Three
   hypotheses; every probe linked supports to every hypothesis —
   including two that explicitly deny a level change (verified fact,
   evidence_refs above + integrated_m9_m12_live_results.md). 6. Yes but
   wrongly: all three → `supported` (verified fact, hypotheses.json)
   while confirmed_findings stayed empty. 7./8. None live. 9.
   Inconclusive 0.62. 10. Technical (negation-blind `_family_of`;
   fixed offline same session, M9 means byte-identical).

### M13 credit (live-d8b174527ca5)
1. Detected: pooled numbers only (Brier 0.13). 2. Only 2 hypotheses.
   3.–5. calibration_and_error_analysis + artifact_summary ×2 + one failed
   classification_metrics; per-region AUC never attempted (verified fact,
   actions.json). 6. No (both stayed proposed). 7./8. None live
   (skeptic/judge are offline-team strengths — stated in report).
   9. Inconclusive 0.63, "failure missed entirely". 10. Scientific
   (thin probing: 2 real diagnostics) + architectural (team passes not
   wired into live loop).

### M14 music (live-ecdd47fafd9d)
1. Detected AND correctly named: H1 cold-start new-slice collapse
   (verified fact) — the only live run naming the exact truth. 2.–5.
   classification_metrics pooled/grouped AUC *contradicted* H1 and
   *supported* H3-globally-uninformative (verified fact, evidence_refs);
   artifact_summary FAILED (missing label column); segment_quality_screen
   ran but no P@K view. 6. Statuses moved (investigating) on the wrong
   signal. 7./8. None live. 9. Inconclusive 0.63. 10. Architectural
   (metric coverage: AUC cannot see P@K slice collapse; no slice-aware
   ranking probe in the live tool path) + technical (column-alias
   brittleness). See milestone_15_baseline.md failure analysis — confirmed
   against artifacts.

## Offline vs live vs demo vs regression (disambiguation)
- Offline evaluations (M9/M10/M13-eval2/M14-eval3/corpus D): deterministic
  autonomous loop (`research/autonomous.py`) + evidence-required grader
  (`m10/evaluator.py`, `eval2.py`, `eval3.py`). Discovery 0.906–0.938.
- Live evaluations (7 runs above): model-driven tool selection
  (`meta_api/loop.py::run_meta_turn`) + heuristic M4-family scorecards.
  Discovery 0.4 once + 0.0 ×6.
- Deterministic demonstrations (flagships m13/m14/m15): scripted stage
  walkthroughs, not investigator evidence (aggregate 0.709 M14 is a demo
  roll-up, not comparable to live 0.63).
- Regression tests (459): engineering contracts; they do not measure
  discovery. Test-count growth (260→459) is reliability evidence only.
