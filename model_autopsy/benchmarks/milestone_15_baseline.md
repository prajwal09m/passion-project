# M15 Baseline (Phase 0) — 2026-11-01

## System state
- Backend: 439 passed, 0 failed (full suite, exit 0). Frontend: tsc
  clean, vite build ok. M9–M14 artifacts, live runs, sealed truths
  intact (live-c0cae8776976, live-d8b174527ca5, live-ecdd47fafd9d).
- Offline discovery (evidence-required): M13 flagship b_unit_shift
  single 0.688 / team 0.773; M14 flagship c_robustness single
  0.688 / team 0.773, mechanism candidate found (m2 ratio 614.19),
  verification honestly not-reproduced via independent tool.
- Live (heuristic scorer): M13 eval_credit inconclusive 0.63,
  M14 eval_music inconclusive 0.63, both discovery 0.0, no FP.

## Target model (primary project: demand-zone)
- V7 Honest Ensemble (LightGBM+CatBoost+XGBoost, walk-forward,
  leakage-cleaned): OOF AUC alpha_spy_2pct 0.7049 (fold
  0.6993±0.0116), mag_spy_2pct 0.6989, hold1_2pct 0.7084.
- Data: study_files/outputs/v2/demand_zone_v2_dataset.csv, 44,854
  rows, 444 cols, 2021-08-03→2026-06-24, binary targets
  (alpha_spy_2pct base rate 0.1957). tb_* columns are pure future
  and excluded from features (per train_v7.py).
- Missing before M15: no in-repo AUC lab re-establishing
  baseline-vs-candidate on identical observations with
  uncertainty; V7 numbers are historical metadata, not a live
  baseline. M15 must measure its own baseline, not quote metadata
  as its result.

## Failure analysis: why live ends inconclusive
Traced through live-ecdd47fafd9d (eval_music; truth: cold-start
collapse of new-item slice P@K under healthy pooled mean):
1. Recognition ok: H1 named the true mechanism ("cold-start
   ranking failure, new-catalog slice").
2. Execution failure (infrastructure): artifact_summary FAILED
   (required column 'label' missing; file uses relevance/score
   naming) → lost recon opportunity. Responsible: tool argument
   defaults/column-alias handling in the live path.
3. Experiment thinness (experiment design): only 2 diagnostics
   ran (classification_metrics, segment_quality_screen); no
   calibration/reliability, no residual, no ranking/P@K view.
4. Interpretation failure (reasoning): classification_metrics
   pooled/grouped AUC CONTRADICTED the true H1 while SUPPORTING
   H3 ("globally uninformative") — AUC cannot see P@K slice
   collapse under a healthy pooled mean. Metric inadequacy, not
   noise. Responsible: metric coverage (no slice-P@K diagnostic)
   + attribution accepting the contradiction at face value.
5. Stopping (orchestration): loop ended after 2 rounds with all
   hypotheses investigating; no discriminating follow-up, no
   skeptic demand for a slice-aware ranking probe, no judge,
   no verification. Live path lacks M11/M12 review passes.
6. Offline would have run 4–6 experiments plus team probes and
   skeptic challenges — capability exists offline but is not
   wired into the live loop. Gap appears in live traces; offline
   simulations do not reproduce it (different driver).

## Dependency map (where fixes belong)
- Column-alias robustness → engine/tools_registry + live context
  (Phase 1 recon, Phase 5 parity test).
- Slice-aware ranking/P@K diagnostic → new diagnostic method
  (Phase 8) + invention catalog (Phase 3).
- Contradiction handling (true hypothesis contradicted by wrong
  metric) → resolution engine (Phase 2: diagnose reason,
  design discriminating experiment, skeptic challenge).
- Live review passes → live loop携带 skeptic/judge-lite under
  budget (Phase 5; offline-testable via replay).
- AUC breakthrough → Phase 1 lab on demand-zone chronological
  sample with strict measurement and promotion gates.
