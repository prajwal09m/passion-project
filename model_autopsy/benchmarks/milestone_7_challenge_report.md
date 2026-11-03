# Milestone 7 — Closed-loop challenge report (offline)

Harness: `backend/eval/m7_challenge.py`, scripted top-pick policy driving
the REAL engine + tools + linker + planner on 6 concealed M6 scenarios
(drift, competing regression, interacting pipeline, no-failure control,
distractor, correlation-vs-causation). Seeds are generic structural
hypotheses per task family — identical for every scenario in the
family, never answers. Truth lives in `m6_challenge._TRUTH`, read only
by assertions about concealment, never by the loop. No paid traffic.

## Results (reproducible via `evaluate_all`)

| Scenario | Steps | Tool calls | Statuses reached | Transitions | Stop rationale |
|---|---|---|---|---|---|
| m6_drift_forecast | 6 | 5 | proposed/rejected/supported | 2 | open hyp, budget continues |
| m6_competing_regression | 5 | 4 | investigating | 3 | no applicable experiments remain |
| m6_interacting_pipeline | 5 | 4 | investigating | 3 | no applicable experiments remain |
| m6_no_failure | 5 | 4 | investigating | 3 | no applicable experiments remain |
| m6_distractor | 6 | 5 | proposed/rejected/supported | 2 | open hyp, budget continues |
| m6_correlation_causation | 6 | 5 | proposed/rejected/supported | 2 | open hyp, budget continues |

Behavioral checks: `transitions_occur: true`, `refs_valid: true`
(every evidence ref cites a ran action), `no_duplicates: true`,
`budget_ok: true` (≤6), `rationales: true` (every stop justified).

## What this demonstrates

- The closed loop moves hypotheses for evidence reasons on every
  scenario (rejected + supported on forecasting; investigating with
  recorded refs on regression).
- Failed tools (`artifact_summary` on non-case-study CSVs) are recorded
  once, then excluded from future picks — no failure loops.
- Tools needing absent columns are skipped as inapplicable and reported
  (`skipped_inapplicable`), never forced.
- Stopping always carries a rationale; inconclusive-with-reasons is a
  reachable, honest terminal state.

## Limitations (binding)

- 6/12 M6 scenarios (generic-args subset); classification-only tools
  (`grouped_auc_comparison`, `classification_metrics` paths needing
  score columns) are not exercised here.
- The scripted policy always follows the brief, so adherence is 100% by
  construction — deviation handling is tested in `test_m7_closed_loop`
  (live-turn test) instead.
- This exercises loop machinery, not investigator quality. No
  generalization claim follows; live evidence comes only from Part 8.
- Sample size is small by design; the report is reproducible evidence,
  not a benchmark leaderboard.
