# Milestone 5 — Results

## Offline validation (final, post-pilot)

- `tests/test_live_investigator.py`: 17/17 pass (mocked transport,
  zero credits) — 15 original + $0.40 boundary test + FSM-walk
  regression test for the attempt-1 finalization crash.
- Full suite: 277 passed, exit 0 (after all code changes).
- `tsc --noEmit` clean (exit 0); `vite build` succeeds (exit 0).
- Separation audit green (9 files, 17 tokens, 0 violations);
  M4 official run `eval-6247993ca658` (mean 0.945) preserved
  untouched — only reads, no writes to historical artifacts.

## Live pilot (authorized single investigation + one transparent retry)

Cost authorization for this pilot: $0.40 (raised from $0.25);
all other caps unchanged (3 rounds / 6 experiments / 12 attempts /
50k tokens). Preflight passed fresh before any request.

### Attempt 1 — failed on a driver FSM bug (preserved, reported)

- Run `live-206dd3c2a288`: 3 rounds, 5 experiments ran (1 failed),
  7 attempts, 36,663 provider tokens, $0.0613 spent.
- Real Meta reasoning occurred (hypotheses + experiments recorded),
  but `driver` called `engine.finalize` from `hypotheses_proposed`
  → `ValueError: illegal transition hypotheses_proposed -> complete`.
- Failure artifacts preserved in the run dir (manifest status
  `failed`, events/assistant/usage/actions/DB intact). Root-caused
  (driver never walked the engine FSM) and fixed with a legal
  `investigating → finalizing` walk mirroring the report endpoint;
  fix proven offline (FSM-walk test) before any retry. No silent
  restart: this document records both attempts.

### Attempt 2 (the completed pilot) — `live-140167117ef5`

1. Launched: yes — single CLI invocation, exit 0.
2. Completed: yes — status `completed`, error none.
3. Project + rationale: **eval_turbine** (forecasting; missed clean
   level shift; tempting-but-wrong leakage explanation tests
   attribution; single-diagnostic evidence; neutral name; mechanism
   never discussed with Meta).
4. Meta request attempts: 7 of 12 (incl. 2 summary repairs).
5. Provider input tokens: 23,263 (17,446 cached).
6. Cached input tokens: 17,446, provider-reported.
7. Provider output tokens: 4,929 (incl. 382 reasoning).
8. Estimated actual cost: $0.0308 (this run) / $0.0921 combined
   with attempt 1 — within the $0.40 authorization.
9. Hypotheses generated: 3 (level-shift/drift; split-hygiene
   artifact; persistent misspecification).
10. Experiments proposed: 6 tool calls requested.
11. Experiments executed: 5 ran (`forecast_diagnostics`,
    `regression_metrics`, 3× `propose_hypothesis`); 1 failed
    (`time_split_validation`, bad args — error returned to Meta).
12. Hidden failure discovered: partially — H1 names a recent level
    shift/drift (correct direction); exact mechanism (level shift
    at day 500) not pinned.
13. Root cause correctly explained: no — scored as mechanism-not-
    identified; no false positive (leakage distractor entertained
    in H2 but not asserted).
14. Evidence: conclusions reference recorded tool results (lag-1
    autocorr 0.776, train≪test error); per-fold AUC spread ~0.01
    correctly argued against fold-shift, but day-500 changepoint
    never isolated.
15. Six dimensions (independent M4 scorer, deterministic +
    heuristic; LLM/human reserved): discovery 0.4, evidence 0.5,
    reasoning 0.6, calibration 0.5, efficiency 0.8,
    reproducibility 1.0 — overall 0.55, verdict `partial`
    ("supporting numbers exist but mechanism not identified").
16. Ground-truth separation: audit green at launch (9 files clean);
    truth revealed only post-freeze for scoring.
17. Artifact preservation: all required evidence true (events,
    assistant messages, usage, hypotheses, actions, sandbox DB,
    eval report, scorecard); manifest written last with SHA-256s.
    Structured summary invalid at freeze — preserved as-is, noted
    in manifest (`structured_summary_note`), never repaired away.
18. Human-review status: pending — blind package = run dir +
    `eval_report.json` + `scorecard.json` (truth in scorer only);
    no reviewer available; nothing fabricated.
19. Incomplete responses/errors: 2 summary repairs (1 with
    `delta_fallback`); 1 failed tool call; final message required
    no truncation repair beyond the counted attempts.
20. Final tests/builds: 277 pytest passed; tsc exit 0;
    vite build exit 0; separation green; manifests verified.

### Pilot totals vs hard caps

- Runs: 2 dirs (1 failed infra attempt + 1 completed pilot),
  1 project, 3 rounds max, 6/6 experiments, 7/12 attempts,
  28,192/50,000 tokens (completed run), $0.0308/$0.40 run cap
  ($0.0921 combined) — no cap breached; provider never refused;
  preservation healthy throughout.

### Four-way separation

1. Deterministic baseline (M4): 0.945, 8 projects, offline.
2. Live Meta result: 0.55 `partial` on eval_turbine (this pilot).
3. Automated ground-truth score: `scorecard.json` in the run dir.
4. Human review: pending unless a reviewer acts (never fabricated).

### Four-way separation

1. Deterministic baseline (M4): 0.945, 8 projects, offline.
2. Live Meta result: see pilot record (one project, one run).
3. Automated ground-truth score: see scorecard in run dir.
4. Human review: pending unless a reviewer acts (never fabricated).
