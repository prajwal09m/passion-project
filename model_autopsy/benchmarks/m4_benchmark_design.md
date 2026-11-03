# Milestone 4 — Benchmark Design

Generator: `tests/fixture_eval/generate.py` (seed 23, committed outputs).
Eight projects, disjoint from M3 in story, domain, columns, mechanisms.

## Projects

| id | Family | Failure | Kind |
|---|---|---|---|
| eval_credit | tabular classification | conditional subgroup failure (region W near-random, pooled AUC 0.97) + legitimate strong distractor (delinq r≈0.55, below leak bar) | single + false-positive trap |
| eval_rent | regression | stale category code: district C silently falls back, missing rooms effect (group MAE spread ~6x) | single, conditional |
| eval_turbine | forecasting | missed level shift at day 500; splits clean/chronological (no leakage to find) | single + wrong-explanation trap |
| eval_docs | clustering | overlapping structure, silhouette ≈0.33 (weak, unstable) | single |
| eval_music | ranking | cold-start collapse: new-item P@K gap ≈0.60 under healthy pooled mean | single, conditional |
| eval_claim | multi-stage pipeline | input-dependent error growth (residual–device_age corr ≈-0.97) + documented-but-untestable threshold concern | partial-credit design |
| eval_wellness | clean control | none planted | correct-null test |
| eval_pilot | weak-evidence (n=120) | none planted; hints below every bar | inconclusive-handling test |

## Adversarial coverage (§6 mapping)

- Multiple interacting mechanisms: eval_claim (staleness + threshold).
- Harmless anomalies/distractors: delinq strength, turbine split column.
- Misleading correlations: delinq↔label (legitimate, must not be called leak).
- Weak evidence: eval_pilot (must not fabricate).
- Conditional failure: W region, district C, post-day-500, new slice.
- Plausible-but-false: leak claim on credit, leakage claim on turbine
  (both penalized as false positives via DISTRACTOR_MARKERS).
- No meaningful failure: eval_wellness.
- More-evidence-required: eval_pilot (inconclusive = correct handling).

## Reference solutions

`ground_truth_eval.json`: per project `{failure, mechanism,
expect_verdict, distractors, forbidden_tokens}`. Expected verdicts:
correct (credit/rent/turbine/docs/music), partial (claim),
correct-null (wellness), inconclusive-handled (pilot).

## Reproducibility

Fixed seed, committed CSVs + briefs, run records pin benchmark,
project, investigator, and config versions plus full histories;
unique run IDs; results append-only under `benchmarks/eval_runs/`.
