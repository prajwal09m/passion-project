# M15 Final Report — Autonomous Model Breakthrough & Scientific Resolution

Date: 2026-11-01. Offline-first; no Meta/Groq calls were made for M15.
All claims below are directly measured, deterministic simulations, or
explicitly labeled historical records.

## 1. What changed architecturally

Additive modules only (see `benchmarks/M15_ARCHITECTURE.md`):
perf recon/measure/lab/promote; resolve (13 classes, 6 statuses);
pipeline (observation→mechanism + diversity); intervene (8 kinds);
replay + parity; diaglab (versioned diagnostics); check_transfer guards;
workflow orchestrator; strategies.summarize; runner_d + corpus D;
flagship_m15 demo; 5 new API routes; Lab.tsx strategy-perf + flagship
sections.

## 2. What changed in the actual model

Demand-zone v2, target `alpha_spy_2pct`, chronological splits
train 2021-08-01/2023-12-31, val 2024, test 2025-01-01/2026-06-24
(HELD-OUT, n=15,871). Leakage columns excluded by the V7 protocol.
Baseline LightGBM vs regularized candidate
(leaves 31, reg 20, min_child 300, lr 0.02, 600 trees).

## 3. Baseline AUC vs candidate AUC (strict, held-out)

- Baseline val AUC: 0.7108; baseline test AUC: 0.7177.
- Candidate test AUC: 0.7226.
- Paired delta on identical held-out observations: +0.0048, 95% CI
  [0.0009, 0.0083], n=15,871, significant (CI excludes 0).
- Brier 0.1466 → 0.1449 (no calibration regression).
- Subgroups: no regression beyond −0.02 on adequate groups.
- Promotion: PROMOTED under the gate; baseline artifact retained for
  rollback. Val-rejected candidates recorded in the endpoint
  (`failed_candidates`), never hidden.

## 4. Evaluation methodology and uncertainty

Bootstrap CIs (200 resamples, seed 7) for AUC and paired deltas;
identical-observation pairing; chronological splits preserved; thin
subgroups (n<30 or single-class) reported inconclusive, never zeroed.
PR-AUC, Brier, base rate accompany every AUC.

## 5–6. Which experiments helped / failed

Helped: regularized-lgbm (capacity + regularization rebalancing).
Failed on validation (recorded, not discarded): class_balance,
capacity (+leaves), slower_learn — val deltas ~0 with CIs crossing 0.
Workflow notes the perf lab as the separate pointer; no random search.

## 7. Why previous investigations ended inconclusively

Replay + live-audit pin the dominant losses to tool_selection and
linking: pooled metrics contradicting slice-concentrated truth
(music_rank: pooled P@K >0.9 vs worst-slice gap ≥0.15), thin-data
over-claiming, and execution failures with no moving evidence. The
resolve module now names these (13 classes) instead of generic
"inconclusive", with the discriminating next tool or an explicit block.

## 8. Which failure mechanisms were fixed

- Generic inconclusive → evidence-derived diagnosis + contract.
- Re-running dead experiments → failed-signature memory in autonomous.
- Pooled-metric blindness → slice-aware probe + diaglab admission path.
- False-analogy transfer → check_transfer warnings.
- Untestable strategy claims → summarize tallies + held-out compare.

## 9–10. Resolved vs unresolved

Corpus D (offline, max_steps=2 smoke): all four tracks execute without
errors; d_null trends to verified-null/inconclusive rather than false
discovery; d_thin stays inconclusive by design; d_combined surfaces
slice evidence via ranking_slice_diagnostics. Full resolution-quality
grading runs through eval2/eval3 dimensions per scenario; per-scenario
rows are preserved, never averaged away.

## 11. Independent verification

Replication uses a DIFFERENT tool from the original measurement
(`m10/replication.py` SECOND_PROBE); diaglab requires reproduction on
another family before admission; flagship diagnostic slice-gap-screen
evaluated FP/FN on controlled cases + independent artifact.

## 12. Held-out evaluation

Corpora A (8), B, C, D (4) remain sealed from investigator imports;
evaluator grades discovery only with moving (supports/contradicts)
evidence. Novelty reported separately, never a score multiplier.

## 13. Live/offline parity

`research/replay.py` replays recorded investigations deterministically
(no model calls) and emits missed opportunities + the 7-question parity
report. `live/audit.py` separates model failures (no hypotheses,
no linking) from infrastructure failures (no events, refused runs).

## 14. Test counts and build results

- Backend: 459 tests (454 pre-existing + 5 new), all passing.
- Frontend: `tsc --noEmit` clean, `npm run build` succeeds.
- API smoke: strategy-performance, eval-d, corpus-d, workflow/run,
  flagship-m15 all 200 with real payloads.

## 15. Security and credential audit

No Meta/Groq calls; no `.env` contents logged or transmitted; tool
allow-lists unchanged; write tools remain absent; campaign isolation
unchanged. `git status` shows only intended M15 additions.

## 16. New limitations

- Demand-zone gain is small (+0.0048) and domain-specific; no claim
  it generalizes to other projects.
- Replay covers deterministic policy pieces, not model judgment.
- Diaglab admission demonstrated on one probe family; broader
  generalization needs more families.
- Strategy learning is tallies + frozen compare, not an auto-tuner
  (deliberate anti-reward-hacking boundary).

## 17. Remaining high-value opportunities

Slice-aware selection ranking by default; temporal walk-forward
promotion windows; confounded-regression discovery probes; auto
blind-spot mining from replay misses into diaglab proposals.
