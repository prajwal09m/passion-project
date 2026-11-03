# MODEL AUTOPSY — FULL-SYSTEM TECHNICAL AUDIT (Stage 4, READ-ONLY)

**Date (UTC):** 2026-11-02 · **Mode:** strictly read-only (no code/test/prod
changes, no provider calls) · **Scope:** entire Model Autopsy application,
not only M22 · **Evidence:** source inspection + `m22-live-01` live artifacts
+ P02 verification results (1062 tests, tsc, production build — all passing
at Stage 2; no app code changed after Stage 2 except nothing: Stages 3–4
added only reports + one untracked live-run directory).

**Final classification: READY WITH LIMITATIONS** (justified in §13).

---

## 1. Executive summary

Model Autopsy is a genuinely investigating system, not a report generator
wearing a lab coat: hypotheses, tool executions, evidence links, status
transitions, repairs, fallbacks and scorecards are all recorded state
transitions, and the final report is deterministically composed from recorded
state only. The P0 distinction (execution ≠ usefulness ≠ resolution) was
demonstrated live. The dominant residual risk is **diagnostic accuracy, not
machinery**: the one live run produced real evidence yet missed the sealed
mechanism entirely (discovery F1 0.0), and the recovery-nudge response path
remains live-unverified. A second structural risk: the git HEAD is far older
than the working tree (core dirs `backend/live|causal|eval|ingestion` and all
benchmarks are untracked), so reproducibility rests on the workspace snapshot,
not version control.

## 2. Architecture assessment

Layered CLI/API → engine (FSM + report) → tools_registry → providers
(Meta/Groq/Ollama behind `InferenceProvider`); persistence in SQLite via
SQLAlchemy; eval/scorer + sealed truths kept separate (`backend/eval`,
`m10/sealed`). Strengths: single legal FSM walk (`ensure_finalizable`,
engine.py:287) shared by driver/API/tests; record-not-reject validation
contract (M20 frozen, M21 advisory-only); offline eval runner **refuses to run
with credentials present** (eval/runner.py:25). Weakness: no API auth layer
sighted — the API assumes trusted local/operator use (see §9).

## 3. Investigation-engine assessment

Honest machinery throughout: summary validation records invalid output, never
silently trusts or discards it (engine.py:304); model cannot change
hypothesis statuses (recommendations only); repair is bounded (1/turn,
rejection recorded — exercised live: repair returned empty → rejected);
stopping/progress is 4-state with total-inaction detection (seen live:
turn-3 `total_inaction=TRUE`). Gap: verify-dispatch is skipped when prior
evidence was already measured — the skip reason is recorded, but a late stall
is then never independently re-checked (Medium, §11-F4).

## 4. Provider integration assessment

Clean adapter separation; bearer keys from env/`.env` only, never logged
(config.py, meta_api/client.py:44); retryable limited to 429/500/502/503;
Groq transport injectable so tests never touch network; Ollama fully local.
Provider failures cannot corrupt state: Groq errors → `ProviderError`,
empty/invalid model output → recorded fallbacks, never fabricated content.
Caveats: Groq advertises `structured_outputs: False` (strict-summary paths
are provider-dependent); per-call ledger exists but **no pre-call
dollar-budget gate** — the $0.65 ceiling was enforced procedurally
(max_rounds=3, no retries), not by code (Medium, §11-F5).

## 5. Backend assessment

Lifecycle create→investigate→finalize→score is single-pathed; resume restores
manifest/provenance incl. `useful_evidence` (P0.1 tests); run-scoped DBs for
eval (never app DB); `resolve_restricted` confines model/API paths to allowed
roots (config.py:113). Not audited deeply (read-only time-box): concurrent
investigations against one SQLite file (locking behavior untested) — Low.

## 6. Model and dataset analysis assessment

Implemented: ingestion boundaries (`ingestion/`), project specs + synthetic
fixtures, slice/leakage-style diagnostics (`ranking_slice_diagnostics`,
`slice_gap_significance`, classification/regression metrics), coverage maps
per hypothesis. Do NOT claim: universal model/dataset compatibility —
diagnostics are tabular/slice-shaped; temporal-leakage and training-pipeline
analysis are partial at best (Medium, demo-risk §11-F2).

## 7. Evidence and reporting integrity assessment

Strongest area. Conclusions cite recorded action ids; failed experiments
appear with errors; unverified hypotheses stay in `unresolved`; confidence is
model-note-flagged; manifest/provenance/`useful_evidence` agreed live;
dashboard labels fallbacks "records only… not a valid model summary" and
advisories "not enforced" (CausalPanel.tsx). No integrity finding.

## 8. Dashboard assessment

`CausalPanel` faithfully renders competition (explicitly "qualitative — no
fabricated scores"), selection rationale, grades, evidence for/against counts,
transitions, confidence trail, coverage gaps, validation/repairs/fallbacks,
stopping rationale, with loading/error/empty states. tsc + production build
pass (P02). Gap: **`useful_evidence` is not surfaced in the UI** — the
headline P0.1 signal exists only in manifest/provenance JSON (Low, §11-F6).

## 9. Security assessment

Secrets env-only, `.env` loader never echoes values, providers take
caller-supplied keys, eval refuses credentials, secret scan of live-run
artifacts clean, file access restricted to workspace roots, Model Autopsy /
Demand Zone separation intact (no demand-zone paths in any diff or edit this
session; Demand Zone files: `demand-zone-webapp/`,
`backend/demand_zone_study_v1.py`, dataset zips — untouched). Concerns: no
API authentication (trusts operator network — High if ever exposed beyond
localhost, Low as a local tool); no destructive tests performed.

## 10. Testing and reproducibility assessment

59 test files; Stage 2: **1062 passed, 0 failed** incl. M19/M20/M21/M22/P0.1
suites; mocked transports for providers; frozen phase-D protocol/rubric/manifest
present and unmodified (Oct 29 timestamps; this session issued no edits to
them — only 3 new `M22_P*` reports created); live run fully persisted
(assistant_messages, hypotheses, actions, events, usage, scorecards).
Reproducibility caveat (High, §11-F1): git HEAD predates the working tree —
`backend/live|causal|eval|ingestion`, `tests/test_m22_p01.py` and all of
`benchmarks/` are **untracked** (`git ls-files` returns empty for them).
The tree is reproducible only as a snapshot, not as a checkout.

## 11. Critical findings (ranked)

- **F1 [High] Reproducibility rests on snapshot, not VCS.** Core dirs +
  benchmarks untracked; HEAD diffs (+3932 lines across 14 tracked files)
  predate this session. Action: commit or tag the working tree before any
  hackathon submission.
- **F2 [High] Diagnostic accuracy unproven.** Live n=1: real evidence, 1
  supported / 1 rejected, yet discovery F1 0.0 — missed sealed mechanism.
  Activity ≠ accuracy. Action: score-gated demo (show scorecard, not just
  activity) + more offline eval runs.
- **F3 [High] Recovery-nudge response live-unverified.** The exact M21
  question (silent model → nudge → genuine recovery) never occurred live
  (model acted from turn 1). Offline 10/10 stands. Action: state as limitation
  in demo; do not claim live recovery.
- **F4 [Medium] Late-stall verify skip.** Prior-measured evidence suppresses
  verify dispatch with a recorded reason — correct frugality, but a late
  stall gets no independent re-check. Action: cap the suppression (e.g. only
  within N turns).
- **F5 [Medium] No coded spend gate.** Governor tracks/ledgers; nothing
  refuses a call on projected dollars. The $0.65 ceiling was procedural.
  Action: add `max_spend_usd` to governor with pre-call refusal.
- **F6 [Low] `useful_evidence` invisible in UI.** Manifest/provenance only.
  Action: one-line status chip in CausalPanel + Workspace.

## 12. Noncritical improvements

Commit workspace (F1); spend gate (F5); UI chip (F6); SQLite concurrency test;
Groq structured-output fallback note in docs; second live run only if a new
question (e.g. forced-silence recovery) justifies fresh spend — NOT authorized
by this audit.

## 13. Hackathon readiness: READY WITH LIMITATIONS

Demo the honest loop (hypothesize → execute → link → discriminate →
partially-resolve with scorecard), disclose F2/F3 verbally, keep spend
capped, submit from a tagged commit. Do not claim: live recovery, universal
compatibility, confirmed root causes beyond the resolution contract.
