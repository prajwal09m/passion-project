# Milestone 6 — Results (resumed run, independently scored)

## A. Evaluation details

- Project evaluated: **eval_claim** (severity estimator; input-dependence
  family, `expect_verdict: partial`). Chosen because M5 used eval_turbine;
  this tests a different mechanism family.
- Model / configuration: `muse-spark-1.3` via
  `https://api.meta.ai/v1/responses`; secure `.env` credential path;
  endpoint, model id, temperature, and prompts unchanged throughout.
- Run ID: `live-ae844753edce` — the SAME run, resumed in place (same run
  directory, same `live.sqlite3`, same investigation `28473f0c…`). No
  restart, no new investigation, no replacement project. See
  `milestone_6_recovery_assessment.md` for the resume plan and
  `resumption.json` in the run dir for the pre-resume snapshot.
- Investigation rounds: 3/3 (1 completed pre-interruption + 2 resumed).
- Experiments executed: 6/6 — 3× `propose_hypothesis` (pre-interruption),
  `calibration_snapshot` (pre-interruption, executed once, never
  re-executed), `data_quality_profile` + `regression_metrics` (resumed
  portion). No duplicate requests, no replayed tools.
- Request attempts: 8/12 cumulative (4 pre-interruption incl. the refused
  chained call counted conservatively, + 4 resumed).
- Provider-reported token usage (cumulative ledger): 30,920 input
  (11,219 cached), 6,509 output (incl. reasoning), 37,429/50,000 total.
- Actual cumulative cost: **$0.053972 / $0.40** (provider-reported usage
  at Standard rates; cached tokens at the provider's cached rate only).
- Pre-interruption spend was ~$0.0169; resumed spend ~$0.0370.

## B. Research performance

Independent M4-compatible scoring (frozen definitions, post-freeze
truth `lagged input: error grows with device_age`, truth revealed only
for scoring):

- Discovery: **0.0** — nothing entered `confirmed_findings`; the exact
  input-dependence mechanism (error growing with `device_age`,
  `residual_feature_corr`) was never named with supporting numbers.
- Evidence: **1.0** — scorer rule for an honest inconclusive with no
  confirmed claims (not a quality claim; see §C for what was recorded).
- Reasoning: **0.6** — competing hypotheses maintained, one rival
  (data quality) contradicted by recorded evidence, but the surviving
  explanation stayed at symptom level.
- Calibration: **1.0** — correctly inconclusive rather than confirmed
  beyond the evidence.
- Experiment selection (M6): **0.4** — one discriminating diagnostic
  (`regression_metrics`) plus a hygiene check (`data_quality_profile`);
  competitors untested, no changepoint-style localization attempted.
- Causal diagnosis (M6): **0.5** — honestly inconclusive; bias named as
  best explanation in prose but never promoted with cited-action
  discipline, and the `device_age` dependence untested.
- Efficiency: **0.6** (6 experiments, at the cap).
- Reproducibility: **1.0** — full evidence trail, manifest-last SHA-256s.
- Report validity (M6): **1.0** — structured summary VALID with
  traceable hypothesis references (fixes the M5 `invalid` outcome).
- Overall M4: **0.62**, verdict **`inconclusive`**.
  M6 9-dimension figure: **0.678** (reported alongside, never averaged
  into M4).

## C. Detailed findings

- What the investigator discovered: a massive systematic overprediction
  (FACT in its own conclusion: `calibration_snapshot` residual mean
  −131.77, MAE 132.51, n=1500; `regression_metrics` R² −0.99, MAE spread
  across groups modest vs. the bias scale). Directionally correct and
  real.
- Hypotheses: all 3 remained `proposed` in the DB (statuses move only
  via recorded updates; the valid summary carries recommendations).
  H1 uniform bias — best-supported prose conclusion, unconfirmed.
  H2 feature-dependent miscalibration — neither supported nor rejected
  (the discriminating `residual_feature_corr` number was never produced).
  H3 data-quality artifact — contradicted (`duplicate_rows: 0`, no
  missingness signal) yet never formally rejected.
- Useful experiments: `calibration_snapshot` (established the bias
  scale), `data_quality_profile` (ruled out the hygiene rival),
  `regression_metrics` (confirmed error scale, but the adapter's
  numbers lacked the feature-correlation field the scorer needs).
- Where reasoning improved vs M5: a VALID structured summary with real
  hypothesis ids and cited action ids; explicit FACT vs CONCLUSION
  separation in the final message; a rival eliminated with evidence.
- Where it still struggled: stopped at "systematic bias" without
  testing `device_age` dependence; never computed a
  residual-vs-feature correlation; left a contradicted rival formally
  open. The M6 diagnosis gate (supported/rejected with cited actions)
  was available in the backend but the live loop never invoked the
  update path — statuses stayed frozen, as in M5.
- Cause established? No. Accurate inconclusive, correctly scored.

## D. Comparison with Milestone 5

M5: 0.55 `partial` on eval_turbine (drift direction found, mechanism
not pinned). M6: 0.62 `inconclusive` on eval_claim (bias scale found,
input-dependence not pinned). **These are not comparable as
better/worse**: different projects, different mechanism families,
different verdict semantics (`partial` credits a named-but-unproven
mechanism; `inconclusive` with discovery 0.0 reflects an empty
confirmed set). No improvement claim is made on scores.

Genuine deltas, stated separately:
- Architecture (offline-proven): hypothesis competition analysis,
  selection rationale, changepoint/residual-time/shift diagnostics
  (which localize the M5 turbine break on frozen fixtures), evidence
  graph, diagnosis gate, extended validation, 14-stage workflow, single
  FSM helper, 12-scenario concealed suite, causal dashboard view.
- Live process: report validity 0→1 (valid summary vs M5's missing
  block), clean resume with zero duplicate work, conservative
  cumulative accounting.
- Live science: not yet demonstrated — the exact-dependence question
  (M5: day-500 changepoint; M6: `device_age` correlation) beat the
  investigator twice. The pattern is consistent: direction found,
  mechanism unpinned, honestly inconclusive.

## E. Limitations and next steps

- One run proves nothing general; the M6 challenge-suite mean is a
  harness exercise, not investigator evidence.
- Only 2 experiment executions remained after the interruption under
  the original caps — resumed depth was constrained by design.
- The unused-diagnostics list is long (notably `temporal_changepoint_scan`
  and `distribution_shift_profile` never ran on claim); selection policy
  is advisory, not yet wired into the live loop's prompts.
- The hypothesis-status update path (`link_evidence` → confidence →
  supported/rejected) still never fires during live runs; closing that
  loop is the highest-value next step.
- Preserved failures: M5 `live-206dd3c2a288` (driver FSM bug),
  M6 interruption (operator timeout, `INTERRUPTED.md` retained
  alongside the now-complete manifest — history, not contradiction).
  Nothing concealed, nothing rewritten.
