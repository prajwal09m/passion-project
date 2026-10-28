# Model Autopsy — Demo-Readiness Audit Report (2026-10-28)

Branch: `study/demand-zone-ai-autonomy-audit` · Scope: `model_autopsy/` only.
Every claim below states what was **verified** (actually executed) vs merely inspected.

## 1. Tests actually run and their results

| Check | Result |
|---|---|
| Backend pytest (full suite, live code) | **86 passed** in 28.3s (0 failures) |
| `test_isolation_and_report.py` incl. new dedupe test | 8 passed |
| `test_tools_software_and_engine.py` + `test_api.py` (post-fix rerun) | 19 passed |
| Frontend `npm run build` (Vite production build) | **passes** (built in 3.4s) |
| Sandbox API smoke (`GET /api/investigations` on :8002) | HTTP 200 |
| Live-DB read-only smoke (`GET` on :8000) | HTTP 200, 57 investigations listed |
| Full workspace workflow in browser (sandbox UI on :5175) | covered in §3 |

Not run: nothing blocked; no check was skipped.

## 2. Bugs discovered and fixed

1. **Duplicate findings rendered twice in the final report** (verified by
   recording an identical finding twice in the sandbox: `confirmed` section
   listed the same summary twice). Unlike `link_evidence` (which already had a
   dedupe guard), `engine.record_finding` accepted exact duplicates and
   `engine.build_report` rendered each copy.
   **Fix** (both layers):
   - `engine.record_finding` now returns `{"unchanged": True}` for an exact
     duplicate (same summary + status) without appending or logging a second
     event.
   - `engine.build_report` additionally de-dupes `(summary, evidence_action_id)`
     when assembling sections.
   - New regression test `test_duplicate_finding_is_idempotent_and_report_renders_once`.
   - **Fix verified**: re-generated the sandbox report via API → exactly 2
     distinct confirmed entries; UI renders the entry once (`reportSectionCount: 1`).
   Note: the timeline/raw findings log intentionally keeps one record for the
   original double submission (immutable history); only new writes are guarded.

   No other defects observed: navigation, charts, budgets, status transitions,
   validation, isolation flags and empty states all behaved correctly in
   browser testing.

## 3. Verified status of the complete investigation workflow

Executed end-to-end in the browser on the **sandboxed temp DB** (:8002/:5175),
using the **real** Demand Zone artifact
(`study_files/outputs/study_v1/development/oof_predictions.csv`, 41,221 rows):

1. **Landing** — live counters, 4 pooled-AUC figures recomputed from the
   artifact; honest labeling of the conceptual leakage illustration. ✅
2. **Case study open** — "Demand Zone AI — error-cluster investigation"
   (sandbox copy), tool budget 5/12. ✅
3. **Diagnostics** — `classification_metrics`, `calibration_and_error_analysis`
   (twice, different arms), `time_split_validation`, `grouped_auc_comparison`
   all ran against the real CSV, recorded as actions #4–#12 with full JSON.
   ✅
4. **Hypotheses** — registered a falsifiable hypothesis, ran diagnostics,
   **rejected** it when the data contradicted it (LightGBM_C turned out to be
   the strongest arm, AUC 0.6835 — the honest "diagnose → reject" arc),
   registered and **supported** a second (LR_A deficit; ΔAUC +0.0818,
   CI 0.0637–0.1010, ticker-cluster bootstrap, seed 42). Status transitions
   and evidence linking (`supports`/`contradicts`) recorded correctly. ✅
5. **Independent recomputation** — pandas recomputation from the raw artifact
   matches every recorded metric to 6 decimals (pooled AUCs, Brier 0.130634,
   precision/recall@0.5, fold sizes). ✅
6. **Evidence traceability** — every finding cites action hashes; the JSON of
   each action includes the absolute artifact path. ✅
7. **Final report** — deterministic, rendered from recorded evidence only;
   confirmed/likely/rejected/unresolved sections + limitations + budget.
   Verified in the UI after the dedupe fix. ✅
8. **Honest failure path** — with no `MODEL_API_KEY`, "Run bounded Meta turn"
   surfaces a truthful, actionable unavailability message and records no fake
   data. ✅

**Live DB (read-only, GET only — no writes this session):**
- 2 real investigations: `cf2b4a41` (context_ready, 0 actions), `25bb7732`
  (context_ready, 1 action: context load; 1 proposed hypothesis, 0 evidence
  refs, no report). Their full workflow has **not** been executed live (by
  design — audit ran sandboxed); the live DB's real records are pristine.
- 55 legacy practice records all flagged `is_test_record=True` — intact,
  untouched, never read as case data by the UI. ✅

## 4. Meta integration — exact status

**Implemented (code + unit tests, no mocks or stubs found anywhere in
`model_autopsy/backend`):**
- `meta_api/client.py` — real HTTP adapter to `https://api.meta.ai/v1`
  Responses API (verified endpoint facts): bearer auth, `create_response`
  with tools + `previous_response_id`, bounded retries (429/5xx/408 with
  backoff, honors `retry-after`), no key → `MetaUnavailable`, errors are
  sanitized and never contain the key.
- `meta_api/loop.py` — bounded multi-round tool-calling loop with honest
  context injection, tool allowlist, `function_call_output` round-trips,
  budget enforcement, verbatim recording of Meta's message; hypotheses from
  Meta are flagged uncalibrated and must trace to recorded evidence.
- Unit tests cover: no-key behavior, malformed responses, loop execution and
  evidence recording, retry exhaustion, fail-fast on non-retryable, key-leak
  prevention, schema/allowlist consistency (part of the 86).

**Mocked: nothing.** There is no fake-response path; without a key the loop
honestly reports unavailable.

**Unverified: live traffic.** zero real Meta API calls have ever been made
(no `MODEL_API_KEY` configured; authorization required before any live call).
All parsing/orchestration is proven only against unit-test doubles of the
HTTP layer. **Remaining steps for a controlled live test:**
1. Provide a valid `MODEL_API_KEY` (never pasted in chat; backend env only).
2. Integrations page → connection test (GET /models — free, no spend).
3. Run one bounded Meta turn (≤3 rounds) on a **sandbox** investigation
   (temp DB) and confirm recorded events (meta_request/meta_response/usage).
4. Only then a live-DB investigation, watching budget consumption.

**Readiness verdict:** adapter is code-complete and test-covered; real-API
behavior (auth, actual response shape, rate limits) remains single-point
unverified until the first authorized call.

## 5. Anything that could stop a judge from using the demo

- ⚠️ **Two backends can confuse selectors**: the live backend sits on :8000
  and a stale uvicorn (PID 23812) may still hold :8001; the sandbox runs on
  **:8002** (UI on :5175). Demo scripts must pin ports exactly as in
  `DEMO_SCRIPT.md` — the Vite proxy targets 8000 by default, so always use
  the documented sandbox launch or the default pair, never mixed.
- ⚠️ **The full E2E workflow was verified in a sandbox**, not against the
  live DB (deliberately read-only). A judge doing live-DB writes is safe —
  the same engine code ran under test — but the live DB has no finished
  investigation yet, so [step 6 of the script] shows a completed case only
  in the sandbox (or after running the flow once in sandbox/live mode).
  Running the 6-step sequence once *before* the judge (in either mode)
  guarantees a presentable state; the sandbox path leaves the live DB pristine.
- ⚠️ **Meta demo needs a key** for the AI-path; without it, show the honest
  unavailable message (scripted as a 10-second "honesty" beat).
- ✅ No console errors observed during the walkthrough; charts, budgets,
  responsive layout, empty/loading states all behaved.
- ✅ No dependence on the archived 0.97/0.98 AUC result; explicitly and
  visibly disclaimed in the UI.

## 6. Single highest-priority next action

**Run the documented 6-step demo sequence once against the live :8000/:5173
pair with the real DB (writes OK), then leave that completed investigation
open in a browser tab before the judge session.** This converts the one
remaining caveat (completed case exists only in sandbox) into a guaranteed
presentable state, without touching the 55 test records or any research
artifacts. It also quietly becomes the first live-DB exercise of the exact
path a judge will click.
