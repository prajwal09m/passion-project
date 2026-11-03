# M16 Evaluation Plan — Offline + Live Protocols

## 1. Offline evaluation (no authorization needed; run first)

Corpora (frozen, sealed truth untouched): A (8, `tests/fixture_m10/`),
B (6, `fixture_m10b/`, novel columns zone/day/fold), C (6,
`fixture_m10c/`, county/machine/sensor), D (4, `fixture_m10d`,
null/thin/combined/confounded). Plus planted slice-collapse cases
(music_rank shape) and column-alias variants (relevance/score naming).

- Correct-null: d_null + steady controls must stay unclaimed (target: 4/4, Wilson CI reported).
- Thin-evidence: d_thin + sparse must stay inconclusive-correct (target: 2/2).
- Confounded: d_confounded + schema-vs-district cases must preserve uncertainty, never false-confirm (target: 0 false confirmations).
- Families: ≥5 model families; unfamiliar columns required in ≥50% of planted cases.
- Regression gates: M9 means byte-identical, M10 grades unchanged, 459 tests green, tsc + build green.
- Metrics per scenario (eval2/eval3 + new localization): discovery (strict),
  localization (new, P2), precision, correct-null, FP/FN, hypothesis quality,
  attribution accuracy (denier cases), confounder handling, reproducibility,
  efficiency. Per-scenario rows preserved; means with bootstrap CIs.

## 2. Live evaluation — feasibility and design

**Feasibility**: yes. Each live run costs $0.03–0.06 and 28k–45k tokens
(verified range over 7 runs); 5 repetitions × 2 scenarios ≈ 10 runs ≈
$0.31–0.58 total, ~300k–450k tokens. Well within the historical $0.40/run
authorization shape (one authorization per run or a 10-run campaign cap).

**Statistical usefulness**: n=5 per scenario does not power a McNemar or a
small-effect t-test (and this plan refuses to pretend otherwise). What n=5
does buy: (a) variance estimates where today there are none; (b) Wilson
CIs on discovery/localization rates (e.g. 3/5 → [0.23, 0.88] — wide but
honest, vs today's [0.00, 0.39] on 0/6); (c) paired within-scenario
comparison of P0/P1 changes against the frozen M13/M14 baselines
(descriptive deltas + CIs, significance only if effects are huge and
consistent); (d) falsification of "never localizes" (one replicated
localization breaks the 0/6 streak descriptively).

**Design** (frozen before first run; preregister rubric + P2 localization):
- Scenarios: eval_music (slice collapse; baseline: 0.63 inconclusive, H1-named-but-contradicted) and eval_credit (regional gap; baseline: 0.63/0.61 inconclusive, per-region unmeasured).
- Arms (within-scenario, same budgets 3 rounds / 6 exps / 12 attempts / 50k tokens / $0.40): (i) single investigator (status quo), (ii) investigator + skeptic-lite, (iii) full team pass where budget allows. Minimum: arms (i)+(ii) × 5 each per scenario = 20 runs (~$0.62–1.17). If authorization is tighter: (i)+(ii) × 5 on eval_music only = 10 runs.
- Primary outcomes: localization rate (adequate-granularity evidence measured), discovery rate (strict, independent second probe).
- Secondary: status-motion rate, skeptic-challenge count + resolution, summary-valid rate, attribution-error rate (denier-supports count, must be 0), tokens/cost per run, FP count (must be 0).
- Analysis: Wilson CIs per arm; paired descriptives vs frozen baselines; no p-values unless preregistered effect sizes hit with consistency (5/5 vs 0/5 → Fisher exact p≈0.008, the only claimable test at this n — preregister it or don't claim it).
- Failure handling: failed tool calls, invalid summaries, cap stops all preserved and counted (M7-breach rule: any cap breach invalidates that run's comparability, disclosed not hidden).
- Cost reporting: per-run provider ledger (input/cached/output, $), campaign totals, cost per localized/confirmed finding.

## 3. What "M16 succeeded" means (decision rule, preregistered)
- Must: ≥3/5 music runs measure the slice localization live with moving evidence + zero denier-supports + zero FPs, and credit runs measure per-region AUC ≥3/5.
- Should: ≥1 confirmed finding surviving the independent second probe (replication.py) across the campaign.
- Must not: weaken the scorer, relabel inconclusives, or compare new-dimension scores against old-dimension history.
- If the must-bar fails, M16 reports which bottleneck survived (C/D/E/F/G) with the new variance data — a null result with narrower CIs is still progress over n=1 ignorance.
