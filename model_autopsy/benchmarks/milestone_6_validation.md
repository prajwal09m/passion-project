# Milestone 6 — Offline validation (Part 7)

No paid API calls were made for any check below except where explicitly
noted (§8). All commands were run from the repository root.

## 1. Backend tests (all + new M6)

- `py -3 -m pytest model_autopsy/tests -q` → **287 passed** (277 pre-existing
  + 10 new `test_m6_causal.py`), exit 0, ~115 s. No tests weakened, none
  skipped; failure paths are tested (invalid summary, contradictory
  recommendations, workflow guards, failed-tool reselect).

## 2. New M6 tests

- `py -3 -m pytest model_autopsy/tests/test_m6_causal.py -q` → **10 passed**.
  Covers: duplicate/contradict/compatible detection, confidence steps,
  selection ranking + predicted-vs-actual, diagnosis gate, extended report
  validation, workflow guards, changepoint scan on the real turbine
  fixture (shift_size > 5, changepoint in 2024, recent-shift pattern,
  train/test gap confirmed), M4-wrap scorer (M4 dims unchanged),
  challenge separation (12 scenarios, 0 truth leaks in public briefs),
  evidence-graph build + trace.

## 3. Frontend checks

- `npx tsc --noEmit` (in `model_autopsy/frontend`) → exit 0.
- `npm run build` → success (`dist/` written, 780 kB JS chunk warning only).

## 4. API / workflow / state-machine tests

- Existing `test_live_investigator.py` FSM-walk regression still passes
  (single shared `engine.ensure_finalizable` now used by both the report
  endpoint and the live driver — one path, tested).
- `PATCH /api/hypotheses` accepts the new `blocked` status; invalid
  statuses still rejected.
- Causal endpoint: `GET /api/investigations/{id}/causal` → 200, returns
  competition / evidence_graph / selection / diagnosis_grades (verified
  with TestClient against a live SQLite investigation).

## 5. Evidence-graph / report-validation tests

- `test_m6_causal.py` covers graph build, `trace_conclusion`
  (why-believed / contradicts / alternatives / what-would-establish),
  and `report_validation.validate` (required fields, unknown hypothesis
  refs, unknown experiment refs, contradictory recommendations,
  supported-without-evidence). Invalid summaries are preserved, never
  rewritten; transformations are explicitly labeled.

## 6. Ground-truth separation audit

- `eval.separation.audit_investigator_env()` → `ok: True`.
- M6 challenge: `public_brief()` output for all 12 scenarios contains
  zero forbidden truth tokens (`day 500`, `level shift`, `near-random W`
  absent); truth lives only in harness-side `_TRUTH`, never passed to
  the investigator path.
- M4 `load_truth()` is still read post-freeze only (driver + scorer).

## 7. Credential safety audit

- New files (`backend/causal/*.py`, `backend/eval/m6_*.py`,
  `tests/test_m6_causal.py`, frontend `CausalPanel.tsx`) contain no key
  material (regex scan for `sk-…` / key assignments: none).
- Live tests remain keyless with mocked transport; the pilot check reads
  only key presence (value never leaves the process except as auth header).
- `model`/endpoint unchanged: `muse-spark-1.3`,
  `https://api.meta.ai/v1/responses`.

## 8. Historical artifact integrity

- M5 run dirs (`live-140167117ef5`, `live-206dd3c2a288`) untouched —
  reads only. M5 manifest still reports `completed` / `failed`
  respectively; SHA-256 entries intact.
- M4 official run `eval-6247993ca658` (mean 0.945) untouched.
- No destructive DB migrations: new Hypothesis columns are additive +
  nullable (`expected_consequences`, `missing_evidence`,
  `status_justification`); `init_db` migrates existing DBs via
  `PRAGMA table_info` + `ALTER TABLE`.

## 9. Dashboard integration checks

- New `CausalPanel` (competition table, selection rationale, diagnosis
  grades, evidence-graph counts) renders from the read-only causal
  endpoint; existing design language and routes preserved; `tsc` + build
  green (§3). Backend serves the page; no new spend path exists
  (no `POST /api/live/runs`).

## 10. End-to-end challenge suite (offline)

- 12-scenario M6 harness (`m6_challenge.evaluate`) runs fully offline:
  12/12 evaluated, mean overall 0.53 on minimal-evidence synthetic
  reports (min 0.433, max 0.711), truth-leak count 0.
- M6 scorer (`m6_scorer.score_m6`) wraps frozen M4: M4 dims/overall
  unchanged and comparable to M5; three new dims reported alongside,
  never averaged into M4.

## 11. Preconditions for the authorized live run (all met before launch)

| Gate | Result |
|---|---|
| Full backend suite green | 287 passed |
| Frontend checks + build | tsc 0, build ok |
| Ground-truth separation clean | ok True, 0 leaks |
| Credential safety clean | none found |
| Project suitable, truth sealed | `eval_claim` (new for M6; input-dependence, partial-verdict family) |
| Secure credential path | key configured (presence only) |
| Model/endpoint unchanged | muse-spark-1.3, Meta responses endpoint |

A single live invocation on `eval_claim` was started under the M6 §8
authorization, interrupted at ~2 rounds by an operator-side 60-second
tool timeout (~$0.01 spend), and subsequently RESUMED IN PLACE under a
fresh continuation authorization (same run ID/DB/investigation, no
replay, cumulative caps honored). See `milestone_6_recovery_assessment.md`
(resume plan, classified "resumable with documented limitations"),
`live_runs/live-ae844753edce/resumption.json` (pre-resume snapshot),
and `milestone_6_results.md` (completed: `completed`, M4 inconclusive
0.62, $0.054/$0.40 cumulative). `INTERRUPTED.md` is retained as
interruption history alongside the final manifest.

## 12. Known limitations

- The offline challenge mean (0.53) uses synthetic minimal reports; it
  exercises the harness, not investigator quality — no generalization
  claim is made.
- New diagnostics are validated on the real turbine + claim fixtures,
  but day-500 localization on live traffic remains unproven (the live
  run did not reach diagnosis).
- `CausalPanel` shows counts + tables; richer graph visualization is
  future work (responsiveness preserved by keeping it lightweight).
