# Milestone 4 — Reconnaissance (read-only, no code modified)

Date: 2026-11-01. No paid API activity. All paths relative to repo root.

## 1. Existing capabilities (reusable directly)

- **Orchestration**: `backend/research/lab.py` — 11-stage driver
  (`run_autonomous_investigation`), deterministic offline triage,
  provider-independent (no LLM import in driver).
- **Hypotheses**: `backend/research/hypotheses.py` — structured cards
  (mechanism, observables, support/refute criteria, priority), validated
  transitions incl. `blocked`; evidence required for
  supported/rejected; deepcopy-on-write persistence fix in place.
- **Experiments**: `backend/research/experiments.py` — heuristic design
  (explicitly labeled, not Bayesian) + copy-on-read workspaces under
  `backend/data/research_runs/{inv}/{exp}/` with plan/seed/log/provenance.
- **Verification**: `backend/research/verification.py` — checklist review,
  disagreements preserved.
- **Challenge suite**: `backend/research/challenge.py` — 9 scenarios, 8
  families; fixtures in `tests/fixture_universal/` +
  `tests/fixture_challenge/`; ground truth sealed in
  `ground_truth*.json` (tests-only); 9/9 hits offline.
- **Scoring**: `backend/research/evaluate.py` — 6 dimensions + aggregate
  (never alone); verdict classes deterministic/heuristic.
- **Contexts**: `backend/research/rcontexts.py` + `backend/contexts.py` —
  reference-based summaries, 74.8% char-proxy reduction measured.
- **API**: 27 routes in `backend/api.py`, incl. 4 research routes
  (`research/run`, `research` GET, `research/hypotheses` POST,
  `research/hypotheses/{id}/transition` POST). Additive-only pattern.
- **DB**: `backend/db.py` — investigations/hypotheses/actions/events/settings;
  test isolation via `tests/conftest.py` temp-DB guard (refuses to run
  against the app DB). Additive config-JSON pattern avoids migrations.
- **Dashboard**: `frontend/src/ResearchLab.tsx` — 8 sections, embedded in
  ML Workspace; `tsc` + `vite build` clean.
- **Flagship**: `demo/flagship_research_lab.py` + `flagship_report.json`
  (insurance regression, end-to-end offline).
- **Docs**: 10 Milestone-3 docs + Milestone-2 universal architecture docs;
  frozen paid-campaign artifacts under `benchmarks/phase_d_*`,
  `benchmarks/.sealed/` (must not be touched).
- **Suite**: 235 tests green; credential handling env-only
  (`MODEL_API_KEY` never stored/logged/returned).

## 2. Missing evaluation capabilities (the Milestone 4 gap)

1. **No unfamiliarity guarantee.** M3 fixtures were generated in-repo
   alongside the triage rules; triage keyword-matches the same columns
   the fixtures plant (`leak_flag`, `segment`, `split`, `slice`). A green
   suite cannot distinguish investigation from pattern memorization.
2. **No leakage audit.** Nothing verifies the investigator environment is
   free of ground-truth hints via filenames, comments, variable names,
   API responses, logs, or the `expect`/`kind` fields sitting next to
   specs in `challenge.py`.
3. **Superficial scoring.** `evaluate.score_run` keyword-matches finding
   titles (`"leak" in text`). It does not test symptom-vs-cause
   distinction, competing explanations, experiment discrimination power,
   calibration, or knowing-when-not-to-know.
4. **No verdict taxonomy.** Outcomes correct/partial/incorrect/
   unsupported/inconclusive/correct-null are not distinguished.
5. **No eval runner.** No CLI with run IDs, version pinning
   (benchmark/investigator/config), artifact preservation, or
   no-overwrite history.
6. **No human-review workflow.** No blind-then-reveal review path; no
   reviewer-feedback store separate from automated scores.
7. **No dashboard eval section.** ResearchLab shows one investigation;
   no benchmark projects / runs / scorecards / drill-down views.
8. **No untrusted-code boundary.** Copy-on-read workspaces are not
   sandboxing; project code must be treated as untrusted.

## 3. Proposed architecture (`backend/eval/`, new package)

- `projects.py` — NEW benchmark project registry, separate from
  `research/challenge.py` (which stays frozen). New fixtures under
  `tests/fixture_eval/` with neutral filenames/columns; generators
  seeded and committed; reference solutions in sealed files the
  investigator path can never resolve.
- `separation.py` — trust boundary: investigation-env builder (sanitized
  project dir: data + brief + declarative spec only) vs. evaluation env
  (ground truth, reference experiments, scoring rules). Includes a
  leakage-audit test that scans the investigation env for ground-truth
  tokens (failure names, mechanism keywords, reference-solution strings).
- `scorer.py` — rubric v2 with dimensions A–F (discovery, evidence,
  experimental reasoning, calibration, efficiency, reproducibility) +
  verdict taxonomy (correct / partial / incorrect / unsupported /
  inconclusive / correct-null) + explicitly-weighted overall score.
  Scores mechanism identification, not title keywords: checks numbers
  (e.g. per-group gaps, correlations) and evidence links.
- `runner.py` — CLI (`py -3 -m model_autopsy.backend.eval.runner`)
  with run IDs, version records, artifact preservation under
  `benchmarks/eval_runs/{run_id}/` (never overwritten; reruns get new IDs).
- `review.py` — human-review workflow: blind report view → verdict →
  ground-truth reveal → reviewer feedback stored separately from scores.
- API: additive routes only (`/api/eval/...`); dashboard: new
  **Independent Evaluation** section in ResearchLab style.
- Data-only fixtures preferred (CSV + declarative spec, no project code
  execution). Any code execution stays in-process ONLY for registered
  deterministic diagnostics; benchmark-supplied code is never imported.

## 4. Files likely to change

- NEW: `backend/eval/__init__.py, projects.py, separation.py, scorer.py,
  runner.py, review.py`; `tests/fixture_eval/generate.py` + fixtures +
  `ground_truth_eval.json` (sealed); `tests/test_eval_independence.py`;
  `benchmarks/eval_runs/` (results); M4 docs.
- ADDITIVE: `backend/api.py` (new `/api/eval/*` routes),
  `frontend/src/api.ts` + eval dashboard section, `README.md`.
- FROZEN (do not touch): `research/challenge.py`, M3 fixtures,
  `benchmarks/phase_d_*`, `.sealed/`, historical campaign results,
  `engine.py`/`db.py` schemas, existing tests (no weakening).

## 5. Compatibility risks

- DB: no migrations; eval state in `config` JSON with deepcopy-on-write
  (M3 lesson). Registry `project_id` collisions avoided via `eval_`
  prefix + separate registry module (no shared mutable registry).
- Test isolation: conftest temp-DB guard covers new tests automatically;
  eval runner must refuse the app DB path explicitly.
- Frontend: follow ResearchLab patterns; keep `tsc`+build green.
- Full suite must stay 235+ green; new tests must not depend on network,
  keys, or wall-clock nondeterminism (fixed seeds).

## 6. Security and execution-isolation concerns

- Ground-truth files live OUTSIDE the investigator-resolvable tree;
  path resolution for the investigator is restricted to the sanitized
  env dir; leakage-audit test enforces token absence.
- `.env`/credentials never copied into eval workspaces; subprocess-free
  design (no benchmark code execution at all in v1).
- Historical results append-only (new run IDs); eval code cannot modify
  `benchmarks/phase_d_*` (tests assert pre-existing files unchanged —
  add a manifest check if cheap).
- Honest limitation to document: in-process diagnostics are NOT a
  sandbox boundary; v1 avoids the problem by executing zero
  benchmark-supplied code.

## 7. Reproducibility plan

Fixed generator seeds; committed fixtures; run records pin benchmark
version, project version, investigator version (triage rules hash),
config, hypothesis/experiment/evidence histories, final report,
scorecard, execution metadata; unique run IDs; never overwrite.
Human reviews stored separately with reviewer id + timestamp; no
fabricated reviews — absence of review is reported as absent.
