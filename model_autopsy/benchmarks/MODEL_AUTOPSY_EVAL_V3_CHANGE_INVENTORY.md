# MODEL_AUTOPSY EVAL V3 — CHANGE INVENTORY (Stage 1 checkpoint)

**Date (UTC):** 2026-11-02 · **Mode:** offline only (no provider calls, no live runs, no spend).
No reset/clean/revert/stash performed. No commit/tag/push/deploy.

## 1. Repository state

- Branch work newer than HEAD. **Tracked-modified (14 files):** `.gitignore`,
  `model_autopsy/README.md`, `backend/{api,config,db,engine}.py`,
  `backend/meta_api/{client,loop}.py`, `backend/ml_tools.py`,
  `backend/tools_registry.py`, `frontend/src/{App,Workspace,api}.{tsx,tsx,ts}`,
  `tests/test_meta_adapter.py`. Ownership ambiguous → **preserved untouched**.
- **Untracked (new vs HEAD):** `backend/{causal,eval,ingestion,live,m10,m11,m12,
  model_adapters,perf,projects,providers,task_diagnostics}/`,
  `backend/contexts.py`, `meta_api/requests.py`, `benchmarks/`,
  `tests/fixture_eval/` + others, `frontend/src/{CausalPanel,Eval,Lab,Projects,
  ResearchLab}.{tsx}`, demo flagships, `.lab*` joblibs, `.pytest_groq_debug/`.
- Demand Zone AI paths (`demand-zone-webapp/`, `backend/demand_zone_study_v1.py`,
  dataset zips): **zero diffs, zero edits** — untouched, will remain so.
- Credentials: env-only (`MODEL_API_KEY`); none in repo; no provider calls in
  this project (offline mandate).

## 2. Validated application state (baseline)

- Full backend suite: **662 passed, 0 failed** (154s, this checkpoint).
- Frontend tsc + production build: passing per Stage-2 P02 verification; no
  app-code edits since (only reports added). Will re-run in Stage 7.
- Latest completed reports: `M22_P01/P02/P03`, `MODEL_AUTOPSY_FULL_SYSTEM_AUDIT`,
  `MODEL_AUTOPSY_LIVE_F1_ROOT_CAUSE_REPORT` (all in `model_autopsy/benchmarks/`).

## 3. Scorer + benchmark files (exact)

- Authoritative scorer: `model_autopsy/backend/eval/scorer.py` (**v2, FROZEN** —
  never edit in place; historical scorecards depend on it).
- v2 weights: discovery .30 / evidence .25 / reasoning .15 / calibration .15 /
  efficiency .05 / reproducibility .10. `eval_music` gate: `{tool:
  ranking_diagnostics, min_gap: 0.20}` on numbers key `gap`.
- Sealed truth: `model_autopsy/tests/fixture_eval/ground_truth_eval.json`
  (**FROZEN**). Fixture generator:
  `model_autopsy/tests/fixture_eval/generate.py` (`music()`, deterministic,
  gap always 0.1695). Fixture CSV: `tests/fixture_eval/investigator/music_rank.csv`.
- Score adapter: `model_autopsy/backend/live/adapter.py`
  (`meta_report_to_eval`, `_numbers_only`). Normalization target (Stage 4).
- Live record: `model_autopsy/benchmarks/live_runs/m22-live-01/` (manifest,
  hypotheses, actions, events, usage, eval_report, scorecard — all FROZEN).
- Frozen Phase-D protocol/rubric/manifest: Oct-29 files in `benchmarks/` —
  out of scope, untouched.
- M16b/c, m17, m19, m21, m22 music runs in `benchmarks/live_runs/` (v2/v3
  comparison corpus, Stage 7; scorecards never overwritten).

## 4. Artifacts frozen for this project

scorer.py (v2) · ground_truth_eval.json · all `live_runs/*/scorecard.json` +
`eval_report.json` + manifests + DBs · Phase-D freeze files · Demand Zone AI
(any path) · provider credentials/config semantics.

## 5. Files this project MAY create/modify

- NEW: `backend/eval/scorer_v3.py`, `backend/eval/rubric_v3.py`,
  `backend/eval/normalize.py`, `backend/causal/verification.py` (or
  `backend/eval/verification.py`), `tests/test_eval_v3_*.py`, 6 reports.
- MODIFY (narrow, additive): `backend/live/adapter.py` (normalize at boundary),
  `backend/live/driver.py` + `backend/engine.py` (bounded verification phase),
  `frontend/src/Eval.tsx` (v3 breakdown display). All backward-compatible;
  v2 code paths untouched.
