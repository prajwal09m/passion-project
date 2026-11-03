# Milestone 6 — Postmortem of the Milestone 5 live pilot

Status: reconnaissance only. No paid API calls were made for this document.
Sources: `benchmarks/live_runs/live-140167117ef5/*` (completed run),
`benchmarks/live_runs/live-206dd3c2a288/*` (failed attempt 1),
`benchmarks/milestone_5_{results,cost_and_safety,limitations,architecture,reconnaissance}.md`,
`backend/{engine,db,tools_registry,ml_tools,task_diagnostics}.py`,
`backend/{live/{driver,adapter,governor,recorder},meta_api/loop.py,eval/{scorer,projects}}.py`.

Ground truth (for analysis only, never shown to the investigator):
`eval_turbine` = "missed level shift at day 500; splits are clean and
chronological (no leakage)". Forbidden tokens include "level shift",
"day 500", "no leakage". Expect verdict `correct`.

Live result (frozen): overall 0.55, verdict `partial`
(discovery 0.4, evidence 0.5, reasoning 0.6, calibration 0.5,
efficiency 0.8, reproducibility 1.0).
All three hypotheses stayed `proposed` at freeze.
`structured_summary_valid == false` (preserved as-is).

## 1. What the investigator did well (demonstrated, with evidence)

1. **Correct direction, no false positive.** H1 names "a level shift/drift
   in the recent/test period" — the right family. H2 (split-hygiene /
   leakage artifact) was entertained but never asserted, so the scorer's
   distractor check (`leak`/`overlap` in confirmed text) did not fire.
   `scorecard.json`: `false_positive == false`.
2. **Real discriminating numbers were recorded.** `actions.json`:
   `forecast_diagnostics` → `drift_early_vs_late_mae=[7.00, 24.32]`,
   `split_overlap_hint=false`, chronological spans
   (train 2023-01-01→2024-05-14, test 2024-05-15→2024-12-30);
   `regression_metrics` → `mae_by_group={train: 6.90, test: 34.70}`,
   `bias_mean_residual=10.66`. The scorer's `drift_no_overlap` branch
   fired on exactly these numbers (hence discovery 0.4 "supporting
   numbers exist but mechanism not identified", not 0.0).
3. **Calibration discipline held.** With the exact changepoint unproven,
   nothing was confirmed. `eval_report.json`: `confirmed_findings==[]`,
   all three hypotheses in `inconclusive`. An accurate inconclusive beats
   an unsupported confirmation; calibration 0.5 / reasoning 0.6 reflect that.
4. **Evidence handling was honest.** The failed `time_split_validation`
   call (`required column 'label' missing`) was recorded as `failed` with
   the error returned to Meta, listed in `limitations`, never repaired away.
   The invalid structured summary was preserved (`structured_summary_valid
   false`, `structured_summary_note` in the manifest) — the right call.
5. **Reproducibility is real.** Manifest-last with SHA-256s, all eight
   required artifacts present, deterministic `build_report` + frozen
   message → scorer input via `live/adapter.py` (titles from recorded
   findings, numbers from recorded action results only).

## 2. Where reasoning was insufficient (demonstrated gaps)

1. **Symptom level, never mechanism level.** H1 says "recent level
   shift/drift" but never localizes it (day 500), quantifies the shift
   magnitude, or tests a changepoint. The scorer note is explicit:
   "supporting numbers exist but mechanism not identified".
2. **No hypothesis ever moved.** All three hypotheses are `status ==
   proposed`, `evidence_refs == null`, `revisions == null` at freeze.
   No transition to investigating / supported / rejected / inconclusive,
   no confidence update, no `link_evidence` call — even though the
   recorded numbers already contradict H2 (overlap false, chronological
   spans) and weaken H3 (train MAE 6.9 vs test 34.7 contradicts
   "present in all periods").
3. **Final message never concluded.** `assistant_messages.jsonl` contains
   only short status texts ("Missing your recent level shift — I'll test
   competing causes…"); every `summary` event in `events_dump.json` is
   `valid == false` with "no structured summary found in the final
   message". The loop treated the last status text as the final message,
   so `executive_summary` fell back to `message_text[:800]` and
   `structured_summary_valid` stayed false. This is a workflow/loop
   weakness (no enforced final-summary turn), not a model-mystery.
4. **One failed diagnostic was never retried with correct args.**
   `time_split_validation` failed on a schema error and the investigation
   moved on; its absence is listed in `limitations` but no alternative
   temporal check replaced it.
5. **Attempt 1 crashed on a driver FSM bug** (`hypotheses_proposed →
   complete` via `engine.finalize`), preserved as `live-206dd3c2a288`
   (status `failed`, $0.0613). Root cause: the driver never walked the
   engine FSM; fixed with a legal `investigating → finalizing` walk
   mirroring the report endpoint, plus a regression test. History preserved.

## 3. Why competing hypotheses were not distinguished

- H1 (recent drift) vs H2 (split-hygiene artifact) vs H3 (persistent
  misspecification) are genuinely competing, but the system had **no
  machinery to resolve competition**: no expected-vs-observed comparison,
  no contradiction detector, no confidence revision, no evidence graph.
  `update_hypothesis` and `link_evidence` exist in the engine but the
  live loop never calls them — Meta can only *recommend* statuses in the
  final summary, and no valid summary was ever produced.
- The numbers that *could* have decided the contest were never connected
  back: overlap=false + chronological spans contradict H2; train≪test
  error contradicts H3's "all periods" clause; drift ratio 24.3/7.0 ≈ 3.5
  supports H1's direction but not its exact mechanism. Without a
  hypothesis→evidence linkage step, all three stayed open and the report
  degenerated to `inconclusive × 3`.

## 4. Was experiment selection informative enough? No.

- Only two distinct diagnostics ran (`forecast_diagnostics`,
  `regression_metrics`); the other three "experiments" were
  `propose_hypothesis` records. The two diagnostics largely re-measure
  the same aggregate error (MAE 15.66 twice) rather than discriminating
  H1 vs H2 vs H3.
- No temporal-localization test ran (residual-vs-time, changepoint scan,
  pre/post-day-500 split, train-only residual check). Nothing tests H1's
  *exact* prediction (a step at a specific date) or H3's *exact*
  prediction (high train error / autocorrelated residuals even
  pre-shift).
- Selection rationale was never recorded: no predicted observation vs
  actual comparison, no information-value estimate, no "why this tool over
  alternatives", no redundancy check (dedup is only exact-arg reuse).
  Three `propose_hypothesis` calls consumed half the experiment budget
  without producing evidence.

## 5. Were available diagnostics appropriate? Partially.

- `forecast_diagnostics` was the right first tool (drift + split hygiene
  in one call) and `regression_metrics` confirmed the train/test gap. But
  `forecast_diagnostics` reports only an early-vs-late MAE pair — it
  cannot localize a step, estimate shift magnitude, or rule out gradual
  drift vs abrupt level shift vs variance change.
- `time_split_validation` (the natural follow-up for H2) was called with
  wrong arguments and abandoned. Eight other ML diagnostics
  (`artifact_summary`, `dataset_validation`, `classification_metrics`,
  `feature_target_suspiciousness`, `calibration_and_error_analysis`,
  `grouped_auc_comparison`, `clustering_stability`, plus ranking tools)
  were never tried — correctly, since most are off-task, but no temporal
  diagnostic existed to try.
- **Gap (architectural):** no changepoint / residual-vs-time / shift-size
  diagnostic exists. This is the single biggest capability gap for the
  turbine family.

## 6. Did evidence justify the final confidence levels?

- Yes — and the system correctly refused to overclaim. With mechanism
  unidentified and all hypotheses `proposed`, the scorer's `partial`
  (discovery 0.4 / evidence 0.5 / calibration 0.5) is the honest grade.
  The failure is not overconfidence but **under-resolution**: the
  investigation stopped at "drift direction + clean splits" instead of
  driving to "step at day ≈500 of size ≈X, H2/H3 rejected with cited
  action ids".

## 7. Why structured-output validation failed

- The loop's contract requires a fenced `investigation_summary` JSON block
  with `conclusion` + `status_recommendations[]` referencing real
  hypothesis ids. Meta's final turn contained none — only a short status
  sentence. Possible contributors: (a) the loop ends when Meta stops
  calling tools, with no dedicated "now write your summary" turn; (b) the
  3-round / 6-experiment budget left no explicit repair budget for a
  missing summary beyond the 2 counted summary repairs; (c) short status
  texts at every turn trained the pattern that a status sentence suffices.
- The backend behaved correctly: invalid output preserved, errors
  recorded, `structured_summary_valid false`, no fabrication. The fix is
  workflow-level (explicit final-summary turn + validation retry within
  the attempt cap), not silently rewriting the response.

## 8. Architectural vs prompt-related weaknesses

Architectural (need code, not just prompting):

1. No hypothesis lifecycle enforcement — statuses never move without a
   valid summary, and nothing else can move them.
2. No evidence→hypothesis linkage in the live path (`link_evidence`
   never called; `evidence_refs` always null).
3. No experiment-selection policy (no predicted-vs-actual, no
   discrimination scoring, no redundancy beyond exact-arg dedup).
4. No temporal/changepoint diagnostics.
5. No evidence graph / conclusion traceability beyond flat lists.
6. No causal-discipline gate (anomaly vs correlation vs supported vs
   established is conventional, not enforced).
7. FSM walk lived in two places (API endpoint vs driver) until the fix;
   needs a single `ensure_finalizable` helper with tests.
8. Single-summary-attempt workflow; missing-summary is terminal.

Prompt-related (cheaper to fix, still real):

9. The ML system prompt asks for competing hypotheses and predicted
   observations (good — Meta complied) but does not require a
   residual-vs-time check, a changepoint estimate, or an explicit
   H2-rejection step once overlap=false is observed.
10. Tool descriptions do not guide discrimination ("use X to separate
    drift from misspecification"); `time_split_validation` arg docs did
    not prevent the schema error.
11. No instruction to end with the summary block even when budget is low.

## 9. Which improvements could move the M4/M6 dimensions?

Distinguished from speculation. Each maps to a frozen dimension family:

- **Discovery (0.4 → higher):** changepoint-scan + residual-vs-time
  diagnostics aimed at day-level localization; predicted-observation
  checking that forces H2/H3 rejection when contradicted. *Demonstrated
  gap → high leverage.*
- **Evidence (0.5):** mandatory `link_evidence` on every diagnostic
  (supports/contradicts per hypothesis); failed-tool retry with corrected
  args within the attempt cap. *Demonstrated gap → high leverage.*
- **Reasoning (0.6):** competing-hypothesis analysis (duplicate /
  contradict / compatible detection), confidence updates with stated
  reasons, confounder checklist. *Demonstrated gap → medium-high.*
- **Calibration (0.5):** causal-discipline gate (only `supported` with
  cited action ids can enter confirmed; otherwise inconclusive with
  stated next test). Preserves the current honesty while making
  `partial`→`correct` reachable. *Medium.*
- **Experiment selection (new M6 dimension):** pre-execution rationale
  (which hypotheses, what would support/contradict, expected value, cost,
  simpler alternative) + post-execution predicted-vs-actual. *New
  measurement; directly addresses §4.*
- **Causal diagnosis (new):** step-response / ablation / counterfactual
  checks where the adapter allows; explicit "established vs supported vs
  plausible" labeling. *Medium; depends on new diagnostics.*
- **Efficiency (0.8):** selection policy should hold or improve this
  (fewer redundant calls); not a primary target.
- **Reproducibility (1.0) / Report validity (new):** explicit
  final-summary turn + validation retry preserves 1.0 while fixing the
  `structured_summary_valid false` outcome. *Demonstrated gap → must fix.*

Speculative (not claimed until offline + live evidence exists): exact
score deltas, cross-project generalization, any claim that prompt tweaks
alone would have found day 500.

## 10. Binding constraints for Milestone 6 (from M5)

- M5 history (both run dirs, scorecards, manifests) is frozen — reads
  only, never rewritten.
- M4 scorer definitions stay unchanged; M6 adds new dimensions alongside
  (experiment selection, causal diagnosis, report validity) without
  redefining old ones. Old and new scores are never averaged or compared
  as if identical.
- Deterministic 0.945 vs live 0.55 are never ranked against each other.
- The single M5 retry (infra bug + transparent retry) is the precedent:
  one authorized live run for M6, no auto-retry, failures preserved.
