# Milestone 5 — Architecture

Roles are separated by construction, not by convention.

## Meta AI = investigator

Entry point: `backend/live/driver.py::run_live_investigation`.
Recon builds a neutral context (brief + real schema + tool names +
column guidance; no mechanism words, verified by test). Investigation
proceeds through ≤3 chained `meta_api.loop.run_meta_turn` calls
(max 2 tool-rounds each, `previous_response_id` chaining, one
full-context fallback on chain-state errors only). Meta proposes
hypotheses via `propose_hypothesis`, runs diagnostics via the existing
allowlist, and must close with a fenced `investigation_summary`
(one bounded repair attempt if invalid). The backend never writes
hypotheses, conclusions, or scores on Meta's behalf.

## Model Autopsy = research environment

Provides the project, validates every tool call against the mode
allowlist, executes diagnostics read-only, records all evidence
(Actions/Events), preserves the full run (`live/recorder.py`:
events, assistant texts, usage, hypotheses, actions, run DB copy,
manifest with sha256 map + required-evidence checklist, atomic
manifest-last write). Run dirs: `benchmarks/live_runs/{run_id}/`
with run-scoped `live.sqlite3` (never the app or test DB).

## Evaluator = judge (post-freeze only)

`live/adapter.py` converts the frozen engine report + frozen final
message into the M4 scorer input (titles from recorded findings,
numbers from recorded action results — nothing introduced). M4
`scorer.score` runs after finalization; human review follows the M4
blind-then-reveal path against the preserved run.

## Budget governor (`live/governor.py`)

Hard caps — 3 rounds / 6 experiments / 12 attempts / 50k provider
tokens / $0.40 (authorized; raised from $0.25) — enforced pre-request; retries and repairs count as
attempts; cost computed from provider-reported usage only
(uncached = input − cached; $1.25/$0.15/$4.25 per 1M). 429s are
respected, not retried blindly. Any cap stops the run as
`inconclusive`, never as a forced discovery.

## New vs. reused

- Reused untouched: `meta_api` client/loop, engine FSM + report
  builder, tools registry + allowlists, M4 projects/separation/scorer/
  review, `eval.runner.session_for`.
- New: `backend/live/` (driver, governor, recorder, adapter, CLI),
  `GET /api/live/runs[/{id}]` (read-only; no spend endpoint by design),
  dashboard live section, `tests/test_live_investigator.py` (15 mocked
  tests covering all 20 required behaviors).
