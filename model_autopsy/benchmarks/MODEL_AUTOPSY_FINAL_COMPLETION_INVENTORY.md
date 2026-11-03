# FINAL COMPLETION — INVENTORY (Stage 1)

**Date (UTC):** 2026-11-02 · Offline only. No reset/revert/stash; HEAD is stale
by design (working tree is the validated state — see EVAL V3 inventory).

## 1. Architecture (actual, inspected)

- **Entry points:** `backend/api.py` (FastAPI, ~60+ routes: investigations,
  hypotheses, findings, report, eval runs, live runs, lab, research),
  `backend/live/cli.py` (live pilot), `backend/live/resume.py` (resume CLI +
  reconcile), `backend/eval/runner.py` (offline runner, `--project/--all`).
- **Live lifecycle:** `driver.preflight` → `run_live_investigation` (recon →
  ≤3 meta turns → stall/stop rules → `verify.maybe_verify` →
  `ensure_finalizable` → `build_report` → `finalize` → adapter → v2 `score`
  → evidence floor → `recorder.finalize_run`); `resume.py` duplicates the
  tail (finalize→score) WITHOUT the verification call (gap → Stage 3).
- **Evaluation:** v2 `eval/scorer.py` (frozen); v3 `eval/scorer_v3.py` +
  `rubric_v3.py` + `normalize.py` (offline-validated, NOT in live path);
  offline runner `eval/runner.py` hardcodes v2 (`SC.score`) and stamps
  framework `eval_version: "m4-v1"` (distinct from rubric version).
- **Verification:** `live/verify.py::maybe_verify` (eligibility/independence/
  budget/contract) + `live/verification.py` (plan → delegate → reason codes);
  wired in driver only; resume path missing it.
- **Persistence:** SQLite/SQLAlchemy (`db.py`); `inv.config` JSON (version fits
  here — no schema migration needed); run-scoped DBs for eval/live;
  `finalize_run` writes hashed artifacts + manifest LAST (recovery-safe).
- **Providers:** `providers/` (meta/groq/ollama) behind `InferenceProvider`;
  keys env-only; eval runner refuses credentials; dashboard never spends.
- **Frontend:** `Eval.tsx` renders scorecards generically + v3 fields;
  `CausalPanel.tsx` shows competition/coverage/validation with honest labels.

## 2. Implemented / missing

Implemented: investigation/hypothesis/evidence lifecycles, linking with
indecision bands, bounded repair, fallback reports, resolution contracts,
budget governor, resume-with-reconcile, offline eval + blind review, v3
scorer + normalization + verification workflow (tested, 694 green).
Missing (this project): (a) central versioned eval selection + persistence
+ resume preservation + rollback; (b) verification in resume path;
(c) efficiency duplicate-discount (data supports it — recorded digests);
(d) safe stop endpoint; (e) API/frontend contract doc; (f) versioned
scorecards in live manifests.

## 3. Risks

- Tracked-file edits (`config.py`, `api.py`, `engine.py` untouched so far)
  must stay additive; full suite re-run after each.
- Runner manifest key `eval_version` ("m4-v1") collides conceptually with
  rubric selection → use distinct `eval_rubric_version` in manifests/config
  and `rubric_version` in scorecards; env name stays `MODEL_AUTOPSY_EVAL_VERSION`
  per spec (values strictly v2|v3, disjoint from m4-v1 namespace).
- Resume reconcile reads raw sqlite3 — version read must tolerate missing/
  corrupt values (fail safe, never switch silently).
- No live runs to exercise the new path → prove with offline harness +
  version-pinning tests + isolated-DB rollback test.

## 4. Files expected to change

NEW: `backend/eval/pipeline.py`, `tests/test_eval_v3_pipeline.py`
(+ rollback test inside), `MODEL_AUTOPSY_{FRONTEND_HANDOFF,
V3_INTEGRATION_AND_ROLLBACK,FINAL_SYSTEM_AUDIT,FINAL_COMPLETION_REPORT}.md`.
MODIFY (additive): `backend/config.py` (version resolution),
`backend/eval/scorer_v3.py` (efficiency duplicate-discount),
`backend/eval/runner.py` (version param + manifest key),
`backend/live/driver.py` + `resume.py` (pipeline scoring + version),
`backend/live/recorder.py` (manifest key), `backend/live/adapter.py`
(revert numbers alias → pipeline boundary), `backend/api.py`
(version endpoints + stop endpoint).

## 5. Must remain untouched

`backend/eval/scorer.py` · `tests/fixture_eval/ground_truth_eval.json` ·
fixture CSVs · all `live_runs/*` artifacts/DBs · `benchmarks/eval_runs/*` ·
Phase-D freeze files · Demand Zone AI (all paths) · provider credentials.
