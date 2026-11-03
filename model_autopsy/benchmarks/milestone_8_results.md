# Milestone 8 — Live Results (`live-dbf6a5b3fbff`)

Exactly one authorized Meta AI evaluation, launched only after every
offline gate passed. No second campaign, no retry, no further live calls.

## Run information

- Run ID: `live-dbf6a5b3fbff`, status `completed`, error `None`.
- Project: **eval_rent** (rent estimates off in one district after a
  schema update; never used live in M5/M6/M7).
- Model/endpoint: `muse-spark-1.3` via `https://api.meta.ai/v1/responses`
  (identifiers only; credentials never displayed, logged, or stored in
  artifacts).
- Investigation rounds: 2/3 (stopped by experiment cap, rationale recorded).
- Experiment executions: **6/6 — at the cap, never over.**
- API request attempts: 7/12. Provider tokens: 24,255 in (17,077 cached)
  + 5,272 out = **29,527/50,000**. Spend: **$0.03394/$0.40**.
- Structured summaries: INVALID in both turns (model emitted no summary
  block; bounded repair also yielded none); deterministic fallback
  composed from records in both turns and preserved.

## Budget compliance — all ceilings respected

| Ceiling | Used | Verdict |
|---|---|---|
| 1 live run / 1 project | 1 / eval_rent | compliant |
| 3 rounds | 2 | compliant |
| 6 experiments | 6 | compliant (at cap, stopped by it) |
| 12 attempts | 7 | compliant |
| 50,000 tokens | 29,527 | compliant |
| $0.40 | $0.03394 | compliant |

The M7 breach shape is gone: one shared Budget flows driver → loop →
resume, reservations precede every dispatch, and the run stopped exactly
when the experiment cap was reached (`Stopping early: budget exhausted:
experiment cap 6 reached`). No limit was breached.

## Research performance (independent scorer, post-freeze truth)

M4 scorecard: discovery **0.0**, evidence 1.0 (honest-inconclusive
convention), reasoning 0.6, calibration 1.0, efficiency 0.6,
reproducibility 1.0, overall **0.62**, verdict **inconclusive**.
No false positive.

M8 dimension read (same evidence, honest extension): diagnostic
coverage partial (district concentration measured, schema-change and
calibration families unrun at cap); experiment selection good
(discriminating tools, no duplicates, adherence recorded);
evidence quality high (refs valid, failures never cited); hypothesis
management active (5 evidence-driven revisions across 3 hypotheses);
causal reasoning restrained (no single-evidence promotion — corroboration
bar held everywhere); calibration bounded; reporting validity holds via
the labeled fallback, not via a valid model summary.

## What the system did (evidence, not adjectives)

- Proposed 3 genuinely competing hypotheses (district-specific bias from
  schema mishandling; mis-scaled numeric feature, not district; global
  miscalibration with no district failure).
- Ran the discriminating diagnostics: `regression_metrics`
  (MAE 191, bias +114) **with `group_column=district` — district C MAE
  584 vs ~95 elsewhere (ratio 6.2)**; `residual_feature_dependence`
  (max |r| 0.18, no input tracking); `calibration_snapshot`.
  The per-district measurement M7 never obtained WAS obtained live.
- Linker connected evidence to hypotheses (5 revisions): district
  concentration supports the district-bias hypothesis; weak feature
  tracking contradicts the mis-scaling hypothesis. Statuses moved for
  recorded reasons, none promoted without corroboration.
- Stopped exactly at the experiment cap with a recorded rationale; the
  fallback conclusion is inconclusive with cited limits — the justified
  outcome, since schema-update vs district-bias mechanisms remain
  confounded with 3 diagnostics run.

## What was NOT discovered, and why

- Discovery 0.0: nothing entered confirmed findings. The district-C
  concentration (ratio 6.2) is measured and linked, but no hypothesis
  reached `supported` — correctly, under the corroboration bar.
- Both structured summaries were missing entirely (not malformed —
  absent), so report_validity rests on the fallback, as in M7. The M8
  repair path behaved as designed (bounded, fresh-context, preserved),
  but the model did not comply with the summary instruction twice.
- `distribution_shift_profile` never ran (rent has no split column —
  honestly inapplicable) and calibration-by-district was unrun at cap.

## Comparison with earlier milestones (not a ranking)

M5 turbine 0.55 / M6 claim 0.62 / M7 credit 0.61 / M8 rent 0.62: different
projects, families, and scorer inputs — the numbers are not comparable
and no improvement is claimed from them. The comparable deltas are
engineering facts: budget compliance restored (8/6 breach → 6/6 exact
stop), per-segment measurement obtained live for the first time
(district ratio 6.2 recorded with evidence links), statuses moved for
recorded reasons in every hypothesis (5 revisions), and invalid summaries
now degrade to a labeled records-only fallback instead of silent prose.

## Limitations (no success claims beyond evidence)

- **Over-attribution in text matching.** The district-concentration
  evidence linked `supports` to all three hypotheses because each
  mentions "district" — including H3, which explicitly denies a
  district-specific failure. Substring family matching cannot tell
  mention from endorsement. Evidence itself is correct; attribution is
  muddy. Top next-milestone fix (offline only; no live re-run to test
  it under this authorization).
- Single live sample (n=1); live model behavior (summary non-compliance)
  differs from offline harnesses; offline scores are not comparable
  with live scores.
- Unresolved: schema-vs-district confounding, calibration-by-district,
  shift-profile inapplicability on split-less artifacts.
