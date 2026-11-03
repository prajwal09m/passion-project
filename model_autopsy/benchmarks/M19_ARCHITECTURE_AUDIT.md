# M19 Phase 0 — Forensic Architecture Audit (read-only; no behavior changed)

Scope: establish the exact root causes of the M18 live failure and the
progression gap, from recorded artifacts and current code. No M9/M10
artifacts touched. Demand Zone AI untouched.

## 1. The M18 HTTP 400 — exact reconstruction

Run `m18-music-01`, turn 1, round 1 → 3 × `propose_hypothesis` (all ran,
0 experiment slots — the M18 fix working). Round 2 request:

- Endpoint: `POST {MODEL_API_BASE_URL}/responses` (`backend/meta_api/
  client.py::create_response`, body `{model, input, tools, tool_choice,
  temperature, max_output_tokens, previous_response_id?}`).
- `previous_response_id` WAS used: round 1 returned
  `resp_6ae7fbf19b6354bdb0f7493c` (recorded in the meta_response payload),
  and `loop.py` sets `last_id` from every response, passing it as
  `previous_response_id` for round 2. (The `meta_request` event's
  `context_mode: "full"` label is stale — the variable is initialized per
  turn and never updated for in-turn chaining; the chaining itself did
  happen. Label-only defect, noted for cleanup.)
- `input` = 3 × `function_call_output` items (one per round-1 propose),
  no user/assistant message item, no wrapup (not last round, budget fine).
- Provider answered `HTTP 400: {"error":{"code":null,"message":"`input`
  must be non-empty",...}}`. `create_response` fails fast on 400 (not in
  `_RETRYABLE_STATUS`), raising `MetaUnavailable(message, status_code=400)`.

Why the provider received "empty" input is NOT determinable from the
record: the sent input was a non-empty list of well-formed
`function_call_output` items referencing round-1 `call_id`s — byte-shape
identical to M17's successful round 2 (`m17-music-01`: round 1 also
`n_tool_calls: 3` proposes; round 2 chained outputs accepted, model
continued with a diagnostic). Same construction, two outcomes → the 400
is a provider-side chain-state rejection (stale/unusable continuation,
transient validation), not a client serialization bug. `400` is already
classified in `CHAIN_STATE_ERROR_STATUSES` — the codebase half-knows this
class of failure.

## 2. Why the fallback did not fire

`loop.py` has exactly ONE continuation-fallback site, guarded by
`(round_no == 1 and previous_response_id and not fallback_used and
exc.status_code in CHAIN_STATE_ERROR_STATUSES)`. That covers CROSS-TURN
chaining (turn N+1 re-attaching to turn N's response). The M18 failure
was IN-TURN chaining (round 2 of turn 1 re-attaching to round 1's
response): `round_no == 2`, turn-level `previous_response_id is None` →
guard false → `fallback_response is None` → return `meta_unavailable`,
turn dies. No fallback was attempted, no budget was misspent, and the
driver preserved everything honestly — but the investigation lost two
remaining rounds and all downstream stages (reservation, skeptic probe,
verification) to a recoverable transport failure.

Pre-dispatch validation does not exist: nothing checks input
non-emptiness, chain-id usability, or chained-vs-full-context coherence
before sending. A request known to be invalid would be sent (and billed
an attempt) the same as a valid one.

## 3. Partial-state and duplicate-execution analysis

- A failed REQUEST cannot leave partially recorded tool calls: tool
  execution happens only after a successful response is parsed
  (`extract_function_calls` → per-call dispatch). Round-1 tools all
  completed and committed before round 2 was built.
- Fallback re-send carries no tool calls itself; if the recovered model
  re-requests an already-ran tool+args+data identity,
  `tools_registry.execute(allow_reuse=True)` returns the recorded prior
  result (`reused`, no budget, explicit event) — the dedup mechanism that
  already protects the loop (`budget.release` on reuse) and skeptic paths.
- Genuinely unexecuted operations (requested but never dispatched because
  the turn died) are re-dispatchable: they have no recorded Action, so
  dedup cannot confuse them with completed work. The four states in the
  spec map cleanly onto `{no Action} / {failed Action} / {ran Action}` +
  ledger events.
- `driver.run_live_investigation` after `meta_unavailable`: breaks the
  turn loop, still runs `verify.maybe_verify` (honest skip),
  `ensure_finalizable/build_report/finalize`, scoring, and
  `finalize_run`. State preserved; the m18 run dir is complete
  (manifest, sqlite, events, hypotheses, scorecard).

## 4. Progression gap — why 3 hypotheses and 0 diagnostics

- The selection brief WAS in the request (`selection` event:
  top=`artifact_summary`, alternatives included; brief items are appended
  to `input_items`). All 20 tools were offered with generated schemas.
  The model had artifact columns, sample rows, and the brief — and chose
  3 proposes, 0 diagnostics. Legal under current rules.
- `MODE_INSTRUCTIONS["ml"]` tells the model to run "one diagnostic at a
  time" and to "stop requesting tools when evidence suffices" — but
  nothing requires an explicit next-action DECISION when it stops with
  hypotheses and no measurements. `if not calls: break` treats silence
  as a clean turn end; the summary repair path only validates JSON shape,
  never decision completeness.
- No `investigator_decision` record exists: turns record selection,
  requests, results, skeptic, grounded facts — never "given state S with
  candidates H, I chose action A because R with budget B, executed E,
  outcome O". A propose-only turn is therefore indistinguishable from a
  deliberate deferral in the record. That is the gap Phase 2 closes.

## 5. Existing safeguards to preserve

- `accounting.py` taxonomy + single choke point + candidate-gated hold
  (M18, proven by 25 tests + full suite 520 green).
- `replication.replicate` different-tool rule; cached-result
  disqualification; `record_finding` only on corroboration.
- `resolve.collect_transitions` + tightened `contract()` (M18).
- `governor.check`/`check_dispatch` headroom; reserve-then-settle; dedup
  release; M8 started-counted rule.
- Caps: 3 / 6 / 12 / 50k / $0.65. Scope: Demand Zone AI, M9/M10, scorers,
  sealed truth, history — frozen.

## 6. Proposed minimal changes

1. NEW `backend/meta_api/requests.py` (stdlib-only, no session): request
   validation (`validate_request`), fallback eligibility
   (`fallback_eligible`: chain-status + chain-in-play + unused fallback +
   non-auth/non-budget failure), no credentials in diagnostics.
2. `loop.py`: pre-dispatch `validate_request` (invalid → local refusal,
   no attempt spent, straight to the single fallback); extend the
   fallback to in-turn chained failures (round ≥ 1, `last_id` in play,
   once per turn); reconstruction = `_initial_context_items` + compact
   recorded-results message (no chain id, no chain-referencing outputs);
   separate attempt reserve + headroom recheck; observability event with
   mode/failure/eligibility/reuse/cost fields. Keep the cross-turn
   fallback, routed through the same eligibility + observability.
3. `loop.py` Phase 2: per-turn `investigator_decision` event (state,
   candidates, action, tool?, rationale, budget, executed, outcome,
   incomplete-progression flag); post-hypothesis nudge (one explicit
   decision prompt when a round ends with new hypotheses, zero
   experiments, rounds remaining — decline-with-reason explicitly
   allowed); brief instruction enriched with discrimination +
   independence + affordability criteria (no signature changes).
4. Tests: `tests/test_m19_provider.py` (validation + eligibility +
   fallback + dedup, mocked provider) and `tests/test_m19_integration.py`
   (progression decisions + closure on the recovered path + scenarios
   A/B/C/D through real live callers). Full suite must stay green;
   M18 accounting/hold/contract behavior pinned by existing tests.
5. Docs: this audit, `M19_OFFLINE_VALIDATION.md`, `M19_LIVE_READINESS.md`
   (GO/NO-GO), `M19_FINAL_RESULTS.md`.

## 7. Risks

- Fallback re-send costs 1 attempt + tokens: bounded (once/turn,
  re-budgeted, else honest stop). Risk of masking a real outage is
  contained by eligibility (chain-status only) and the once-per-turn cap.
- The decision nudge could annoy into forced diagnostics: mitigated —
  decline-with-reason is a first-class, recorded, valid outcome; no rule
  requires a diagnostic per turn.
- Pre-dispatch validation could false-positive on a future valid shape:
  mitigated — validation failures route to the same fallback path, never
  to a silent drop; unknown shapes pass with a recorded note rather than
  a refusal (validate known-bad, not unknown-good).
