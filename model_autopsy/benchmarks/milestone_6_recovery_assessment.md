# Milestone 6 — Recovery assessment of `live-ae844753edce`

No API requests were made for this assessment (DB + code reads only).
Run ID is read from the directory, not guessed: `live-ae844753edce`,
project `eval_claim` (from `config.live.eval_project` in `live.sqlite3`).

## 1. What completed (durable, committed)

- Investigation `28473f0c…` (mode ml): status `hypotheses_proposed`,
  `tool_call_count` 4/12, `iteration_count` 0/3.
- Driver iteration 1 finished a full turn: 2 Meta rounds
  (`resp_6ae756d90a…`, `resp_6ae756e20a…`), 3× `propose_hypothesis`
  (all `ran`), structured summary INVALID → one repair attempt →
  repair unavailable (HTTP 400) → continuation `original`.
  `meta_usage` rollup recorded: 2 attempts, 8,687 in / 4,081 cached /
  837 out (9,524 total).
- Driver iteration 2 started a second turn chained from
  `resp_6ae756e20a…`: provider refused continuation state (HTTP 400
  "No tool output found for function call call_4bbd…") → the loop's
  designed one-time full-context fallback fired → fresh response
  `resp_6ae756f51ad…` (4,756 in / 0 cached / 499 out) requesting
  `calibration_snapshot`, which executed and committed (`ran`,
  action seq 14, `tool_result` seq 15).
- 3 hypotheses, all `proposed`, all with recorded `propose_hypothesis`
  actions. `INTERRUPTED.md` present; **no manifest** (not finalized).

## 2. In-flight ambiguity: NONE

The last durable event is `tool_result` seq 15 (committed). No
`meta_request` exists without a matching `meta_response` or a recorded
refused-fallback pair after it. The kill occurred after the tool commit
and before the next round's `meta_request` was recorded — so no provider
request has an unknown outcome. Nothing needs replay; nothing will be
re-executed (all 4 tool results are committed and appear in the
experiments ledger the next turn sends).

## 3. Resume point and conversation continuity

- Resume handle: `resp_6ae756f51ad6c5fd67514fc2` (last `meta_response`,
  a complete recorded response whose single tool call was executed).
- `run_meta_turn(previous_response_id=…)` is the loop's normal chained
  path — same methodology, model, endpoint, prompts, temperature.
- Known hazard (documented, handled): the `calibration_snapshot` result
  was never delivered as `function_call_output` (turn died first), and
  the delta-continuation payload carries roster/ledger/budget rather than
  pending outputs — so the provider may again refuse continuation state
  ("No tool output…"). The loop's built-in one-time full-context
  fallback covers exactly this case, and the ledger already carries the
  result digest, so no evidence is lost either way. No methodology change
  is needed; no manual replay will occur.

## 4. Rebuilt cumulative budget (from events, conservative)

| Counter | Completed | Turn-2 partial | Resume baseline | Cap | Remaining |
|---|---:|---:|---:|---:|---:|
| Driver rounds | 1 | 0 | 1 | 3 | 2 |
| Experiments | 3 | 1 | 4 | 6 | 2 |
| Attempts | 2 | 2 (1 refused + 1 fallback) | 4 | 12 | 8 |
| Input tokens | 8,687 | 4,756 | 13,443 | — | — |
| Cached tokens | 4,081 | 0 | 4,081 | — | — |
| Output tokens | 837 | 499 | 1,336 | — | — |
| Cost (Standard rates) | $0.0099 | ~$0.0070 | ~$0.0169 | $0.40 | ~$0.383 |

The refused chained call returned no usage (HTTP 400, presumably
unbilled) but is counted as an attempt — an upper bound, never an
under-count. The in-memory `Budget` object was lost with the killed
process; the rebuild above is derived from durable events, not assumed.

## 5. Infrastructure check (timeout handling)

- Durable checkpoints: YES — every turn commits responses, tool
  results, repairs, and usage rollups to `live.sqlite3` before the next
  request; the kill lost nothing unrecorded.
- Idempotent transitions: status moves only forward via
  `engine.ensure_finalizable` at the very end; the investigation row is
  still `hypotheses_proposed`, so no transition was half-applied.
- Request accounting: per-request `_request_perf.attempts` + per-turn
  `meta_usage` rollups + per-response `usage` payloads — sufficient to
  rebuild the ledger (see §4).
- Background execution: supported — resume will run detached with a log
  file while polling reads only the DB/log (a polling timeout can never
  be mistaken for run failure; the run's own manifest is the sole
  completion signal).
- No infra change to methodology is required. One small additive module
  (`backend/live/resume.py`) reuses `run_meta_turn`, `ensure_finalizable`,
  `finalize_run`, and the scorer path unchanged.

## 6. Ground-truth separation

`config.live` holds only `eval_project: eval_claim`; no truth material
is in the DB or context. Truth is loaded post-freeze by the driver only
(`P.load_truth()` at scoring). Preflight (incl. separation audit) will
be re-run before any request in the resume path.

## Classification: RESUMABLE WITH EXPLICITLY DOCUMENTED LIMITATIONS

1. Pending tool output undelivered — covered by the loop's designed
   fallback (§3).
2. Budget rebuilt from events with conservative attempt counting (§4).
3. Only 2 experiment executions remain under the original caps — depth
   is constrained by design, not by the resume.

Stop conditions are clear: if reconcile finds a manifest, a dangling
request, a second investigation row, or a completed/failed status, it
refuses and no request is sent.
