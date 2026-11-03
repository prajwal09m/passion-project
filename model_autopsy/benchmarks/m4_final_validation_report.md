# Milestone 4 — Final Validation Report (2026-11-01, offline)

## 1. What was implemented

Independent evaluation system (`backend/eval/`, 6 modules) + 8
unfamiliar benchmark projects + sealed ground truth + trust-boundary
audit + rubric-v2 scorer + repeatable CLI runner + blind human-review
workflow + 9 `/api/eval/*` endpoints + **Independent Evaluation**
dashboard section with drill-down and in-UI blind review.

## 2. Files created / changed

- Created: `backend/eval/{__init__,projects,separation,scorer,runner,
  review}.py`; `tests/fixture_eval/{generate.py,investigator/
  (8 CSVs+briefs),ground_truth_eval.json}`; `tests/
  test_eval_independence.py` (25 tests); `frontend/Eval.tsx`;
  `benchmarks/eval_runs/eval-*/` (2 runs); 9 M4 docs (recon +
  architecture, design, separation, scoring, security, instructions,
  human-review, results, this report).
- Changed (additive unless noted): `backend/api.py` (+9 routes),
  `frontend/src/{api.ts,App.tsx}` (+nav/section), `backend/research/
  lab.py` (0.4 silhouette bar), `backend/task_diagnostics/__init__.py`
  (interval-intersection overlap fix), `tests/
  test_universal_projects.py` (2 assertions corrected w/ dated
  comments), `README.md` (eval instructions).
- Frozen/untouched: M3 fixtures bytes + ground truth + reports,
  Demand Zone endpoints/charts/reports, `phase_d_*`/`.sealed/`
  artifacts, engine/db schemas, existing tests unweakened.

## 3. Benchmark projects: 8 (6 families + clean + weak-evidence)

Tabular classification, regression, forecasting, clustering,
recommendation/ranking, multi-stage pipeline, clean control,
weak-evidence pilot — each with concealed mechanism, distractors, and
expected verdict.

## 4–5. Test results

- New: 25/25 eval tests pass (separation incl. planted-token catch,
  isolation, reproducibility, all verdict classes, blind-before-reveal,
  API, credentials, preservation).
- Full suite: 260/260 pass (235 pre-existing + 25 new), exit 0.
- TypeScript `tsc --noEmit` clean; `vite build` succeeds.

## 6. Benchmark investigations

Official run `eval-6247993ca658`: 8/8 investigations completed,
all <1 s each. Verdicts: 5 correct, 1 correct-null, 1 partial
(claim, by design), 1 inconclusive (pilot, correct handling).
Mean overall 0.945.

## 7. Results by dimension (mean over 8 projects)

Discovery ~0.90, evidence ~0.94, reasoning ~0.89, calibration ~0.94,
efficiency 1.0 (all ≤4 experiments), reproducibility 1.0.
Full per-project table: `m4_results_and_limitations.md`.

## 8. Ground-truth separation tested

Lexical audit green (9 files, 17 tokens); planted-token test proves
the audit bites; truth file outside investigator tree (tested);
runner source references no ground truth (tested).

## 9. Security / isolation limits

Data-only fixtures (no benchmark code executes); run-scoped DBs;
credential-set refusal; append-only runs/reviews; live-dir count
pinned. In-process diagnostics are NOT a sandbox (documented).

## 10. Paid API activity

None. Runner refuses credentials; suites assert keys unset; no new
live-campaign artifacts (live-dir count 7, unchanged).

## 11. Incomplete / honest gaps

- Scores measure the deterministic pipeline, not live-model reasoning
  (a build success here is a measurement success, not proof Model
  Autopsy investigates unfamiliar systems in general).
- Co-design bias (same-team fixtures + thresholds); n=1 per family;
  synthetic strong signals; no human reviews recorded yet.

## Status separation

- Implemented + tested: all evaluation infrastructure, offline runs,
  dashboard, API, docs.
- Synthetic/offline results: 0.945 mean, verdict table above.
- Live-model reasoning: NOT validated (requires authorized paid run).
- Human-reviewed findings: none (null reviews reported as null).
