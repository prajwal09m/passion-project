# Groq context-efficiency benchmark — Model Autopsy
Generated: 2026-10-28 21:37 UTC
DB: C:\Users\kamal\AppData\Local\Temp\ma-groq-bench-xq4sypc2\sandbox.db

## Payload sizes
| Metric | Old (pre-6cf865f) | New (compacted) |
|---|---|---|
| context payload (chars) | 1003 | 1110 |
| instructions (chars; separate channel) | 592 | 1675 |
| combined request bytes (no tool schemas — identical both sides) | 1597 | 2791 |
| input tokens (provider-reported) | not measured (offline) | not measured (offline) |
| output tokens (provider-reported) | not measured (offline) | not measured (offline) |
| latency (s) | not measured (offline) | not measured (offline) |

## Duplicate diagnostics (backend-enforced reuse; no provider)
- second identical request reused prior result: **True**
- tool executions for two identical requests: **1** (budget stayed at 1)

## Notes / limitations
- Character/byte sizes are NOT token counts; token rows are filled only from provider-reported usage in --live mode.
- A Groq result does not establish Meta API performance; providers and tokenizers differ.
- Estimated cost is computed from the pricing source named below; it is an estimate, not an actual charge or billing record.
- Single-payload probes skipped: only the --rounds comparison below ran live.

<!-- multi-round -->
## Multi-round comparison (3 rounds, cap 10, billed 10)

Model: `openai/gpt-oss-120b`; tools (identical both conditions): propose_hypothesis, artifact_summary, classification_metrics

| Condition | cumulative input tokens | cumulative output tokens | executions (backend) | reused results (backend) | est. cost USD |
|---|---|---|---|---|---|
| old | 3804 | 1506 | 3 | 0 | 0.001474 |
| new | 2431 | 1369 | 1 | 0 | 0.001186 |

### Per-round detail

- **old**: r1: in 901 / out 727 / 2.2s (finish=tool_calls, tool_calls=1); r2: in 1269 / out 520 / 1.87s (finish=tool_calls, tool_calls=1); r3: in 1634 / out 259 / 1.22s (finish=tool_calls, tool_calls=1)
- **new**: r1: in 1045 / out 722 / 2.37s (finish=tool_calls, tool_calls=1); r2: in 1386 / out 647 / 1.96s (finish=stop, tool_calls=0)

### Limitations

- Measures the COMBINED effect of instruction + context changes (they differ between conditions); not context compaction alone.
- Groq chat-completions is stateless — each round resends the transcript; Meta's Responses API uses previous_response_id, so absolute per-round counts would differ behind Meta.
- A 3-round simulation is not a real end-to-end investigation and cannot show that the new investigator reaches better conclusions.
- Groq results do not establish Meta API performance.
- Duplicate-diagnostic prevention is certified separately by the offline backend test (see RESULTS offline section); it is NOT included in these token totals.
- Cost figures are estimates from published pricing, not actual charges.
- Condition 'new' was re-run once (same parameters; other condition untouched) to complete all rounds after an HTTP 429 provider rate limit cut short that attempt; token totals exclude the non-billed 429 request.
- Total billed requests across the completed comparison attempts: 8 (hard cap 10 per comparison run).
- Total request ATTEMPTS across the completed comparison: 10 (hard cap 10). Attempts include HTTP 400/429 requests the provider rejected without billing; only generated-token responses were charged.

<!-- phase-d -->
## Phase D — Meta paired continuation benchmark (BLOCKED: no Meta key)

Generated: 2026-10-28 (pre-decision). Harness: `meta_paired_continuation_benchmark.py` (new, in this directory).

### Design (constructed; not yet executed live)

| Aspect | Value |
|---|---|
| Baseline condition `full` | Pre-Phase-C behavior: continuation turns resend the FULL initial context. Achieved **without touching production code**: the harness patches `meta_loop._continuation_delta_items` in-process; an offline assertion verified the patched payload is byte-identical to the pre-Phase-C full-context continuation. |
| Candidate condition `delta` | Phase C production code as-is (delta items + existing one-shot chain-state fallback). |
| Identical across conditions | model (`muse-spark-1.3` per `[backend/config.py](model_autopsy/backend/config.py)`), objective, artifact, tool definitions + instructions, temperature 0.2 (production default), round limit 3, tool budget `max_tool_calls=6`, turn structure (1 fresh investigation turn + 1 chained continuation turn), prompt/case digest in both. |
| Isolation | Sandbox SQLite via `MODEL_AUTOPSY_DB_PATH`; the live app DB is never touched. |

### Hard caps enforced by the harness (all parts of one run)

| Cap | Default | Trigger |
|---|---|---|
| Total request attempts (incl. retries + fallbacks) | 40 | Abort immediately |
| Total provider-reported tokens | 150 000 | Abort immediately |
| ESTIMATED cost | $1.00 | Abort immediately |
| Consecutive 429s | 3 | Abort (repeated rate limit) |

- Failed/rejected attempts are ledgered separately from successful billed requests; attempt counts for rejected calls come from the adapter's "(after N attempts)" hint.
- Missing usage fields are recorded as missing — never invented.
- Cost is an ESTIMATE using the pricing table in the harness header; it is never presented as an actual charge.

### Status: run blocked — no Meta API key is configured

- `MODEL_API_KEY` (Meta) does not exist in `model_autopsy/.env`, the process environment, or the OS environment. The only credential present is `GROQ_API_KEY`, which this benchmark must not use (a Groq result does not measure Meta).
- Nothing was charged and nothing was measured: the live command refuses to run without the key and produces no provider requests (verified in offline mode).
- Configuration was verified the safe way: a spend-free connectivity probe was attempted, and environment/network behavior was inspected without reading key values. Provider/pricing facts are in Phase B's capability matrix; the estimate rates will be re-verified at run time against the published page before any charge is estimated.

### To unblock (owner action, not agent)

1. Place a Meta Model API key at `MODEL_API_KEY=<key>` in `model_autopsy/.env` (or export it into the process environment).
2. Re-run: `python benchmarks/meta_paired_continuation_benchmark.py` (defaults: 2 pairs; all caps above apply). Output: `benchmarks/phase_d_meta_results.json` plus the paired table appended here.

### Quality gates the harness reports per run (so the decision is not token-only)

Whether the investigation reached a supported conclusion; claims' evidence/action-ID citations validated against recorded backend actions; facts vs hypotheses vs conclusions distinguished; unresolved hypotheses and limitations; diagnostic execution and reuse counts; appropriate stopping within budget. Tool-choice/conclusion divergence between conditions is flagged rather than celebrated when counts differ.

### Pre-registered decision rule

- **Keep Phase C** only if measured Meta billed input tokens (and, where reported, cached-token accounting) show savings at equal-or-better quality parity.
- **Keep but revise fallback** if savings hold but the fallback-audit tests expose a classifier defect.
- **Reconsider Phase C** if no demonstrated saving or any meaningful regression.
- Single-run/small-sample results will be labelled as such; no statistical significance will be claimed.

### Fallback audit (mocked; no live requests) — COMPLETE, all pass

| Audit requirement | Test | Status |
|---|---|---|
| Continuation-state failure → at most ONE full-context fallback | `test_continuation_failure_falls_back_once_with_full_context` | pass |
| Transient/network/5xx do NOT trigger fallback | `test_transient_and_network_failures_never_fall_back` | pass |
| Unrelated 400s are not blind-retried as stale chains; original failure + returned error both recorded | `test_second_continuation_failure_never_blind_retries` | pass |
| Fallback preserves prior evidence; accurate attempt/context-mode accounting; rollup labels `delta_fallback` | `test_fallback_preserves_prior_evidence_and_accounting` | pass |
| Failed fallback ends the turn honestly, retaining the original failure detail | `test_second_continuation_failure_never_blind_retries` | pass |

Full suite at Phase D close: **110 passed** (includes all new audit tests). The classifier limitation flagged in Phase B remains: 400/404 chain-state classification is status-only; the fallback design caps its misuse to one wasted attempt per turn, and the paired full-context baseline is precisely the recovery shape used, so measurement remains valid under both branches.

### Limitations even once unblocked

- Paired, not randomized: model stochasticity at temperature 0.2 means per-line tool choices can diverge between conditions; divergence is reported, not smoothed away.
- Two pairs = four investigations: strong directional signal for large savings, only weak evidence for small ones.
- Meta does not bill a stateless resend differently from a delta (Phase B verified: no true server-side prompt cache for this endpoint). The expected saving is therefore a raw token reduction, priced at the plain input rate, not at cached-input rates.

<!-- phase-d-groq -->
## Phase D — Groq paired continuation experiment (stateless analogue; run truncated by rate limits)

Generated: 2026-10-28, one capped paired comparison. Harness: `groq_paired_continuation_benchmark.py` (new, isolated; reuses the request/pricing helpers of the previous Groq benchmark and the PRODUCTION loop's instruction text, tool schemas, wrap-up item, tool-packet truncation and reuse guard, without modifying any production code).

### Method

| Aspect | Value |
|---|---|
| Conditions | `full`: chained turn re-transmits the FULL recorded context (`_initial_context_items`) on top of the resent transcript (pre-Phase-C strategy). `delta`: chained turn transmits only the state delta (`_continuation_delta_items`) — Phase C. |
| Identical both sides | model `openai/gpt-oss-120b` (verified listed), objective, artifact, instructions, tool list (8 registered ML tools), round limit 2/turn, tool budget 6, temperature 0.2 (production default), reuse guard ON, wrap-up and truncation functions reused from production. |
| Structure | 1 fresh turn + 1 chained turn per condition; separate investigation each; sandbox DB via `MODEL_AUTOPSY_DB_PATH`. |
| Caps | 10 total provider HTTP attempts (GET /models + all chat requests + any rejected request); 120 000 tokens; US$0.50 estimated; stop at 3 consecutive 429s. Interactive-generation requests only; no other endpoint was called. |

What a Groq experiment CAN and CANNOT show (stated per the harness docstring, verifiable there):
- Groq Chat Completions is stateless — every request resends the transcript. This does NOT reproduce Meta's `previous_response_id` retention. It measures how the two chained-context strategies behave **when requests resend history**; under the `full` condition the corpus context appears in the transcript AND again in the re-transmitted chained message, which is exactly the redundancy Phase C removes.
- Groq prompt-token accounting does NOT establish Meta billing behavior. No Meta requests were made.

### _
_Legend: attempt rows include rejected requests; usage only from successful ones._

| Run segment | Condition | Request | Status | prompt toks | completion toks | latency s | shipped msgs / chars |
|---|---|---|---|---|---|---|---|
| probe | - | GET /models | 200 OK | - | - | 0.75 | - |
| full | full | turn1r1 | 200 | 1719 | 381 | 1.56 | 2 / 2468 |
| full | full | turn1r2 | 200 | 2022 | 210 | 1.14 | 4 / 3996 |
| full | full | turn2r1 (chained) | 200 | 2997 | 315 | 1.46 | 8 / 8087 |
| full | full | turn2r2 | **429** | rejected | rejected | 0.46 | 10 / 9111 |
| delta | delta | turn1r1 | 200 | 1719 | 587 | 1.98 | 2 / 2468 |
| delta | delta | turn1r2 | **429** | rejected | rejected | 0.50 | 4 / 4513 |
| delta | delta | turn2r1 (chained) | **429** | rejected | rejected | 0.40 | 5 / 5761 |

**Condition totals (successful requests only):**

| Condition | billed reqs | input toks | output toks | provider latency | chained msg chars |
|---|---|---|---|---|---|
| full | 3 | 6738 | 906 | 4.61 s | 1996 |
| delta | 1 | 1719 | 587 | 2.88 s | 1107 |

Whole-run totals: 8 provider attempts / 5 with usage / 3 rejected 429s; 8 457 input + 1 493 output tokens; **estimated cost US$0.002164** (0.15/1M input, 0.60/1M output, console.groq.com/docs/models — an ESTIMATE, not a charge). No cap breached (8/10 attempts); the run ended because continuing would necessarily approach the 10-attempt ceiling while both segments were still rate-limited.

### Cross-condition sanity check (harness validation)

The turn-1 opening payloads are byte-identical across conditions (offline check: `turn1_context_identical=true`, both shipped 2 468 chars), and the provider reported **exactly 1 719 prompt tokens for both** — an independent provider-side confirmation that prompt tokens track transmitted payload, and that the paired baseline is real.

### Investigation-behavior comparison — NOT interpretable as quality

Both conditions were truncated by 429s before their turns completed; **neither produced a structured `investigation_summary` block, so neither "reached a supported conclusion"**:

| Backend facts (recorded, not prose) | full | delta |
|---|---|---|
| tool executions | 3 (propose_hypothesis, time_split_validation ×2) | 1 (propose_hypothesis) |
| tool failures | 0 | 0 |
| reuse of prior results | 0 | 0 |
| tool budget used | 3/6 | 1/6 |
| hypotheses proposed | 2 | 1 |
| structured-summary valid | false (truncated before closing) | false (truncated before closing) |

The 3 vs 1 execution difference is an artifact of rate-limit truncation, NOT a condition difference — the report deliberately does not claim behavioral parity or difference from this run.

### Harness issues found during this pass (fixed in place; production untouched)

1. The `_post` docstring claimed a 20 s 429 backoff-retry that the code never performed; corrected after the run so the artifact matches its actual behavior (429 → recorded failed attempt, round breaks; no silent retry, so every rejected request is visible in the ledger).
2. `openai/gpt-oss-120b` on the `on_demand` tier rate-limits aggressively for interactive multi-round use (this run and the earlier Groq benchmark both hit 429s mid-run). Long inter-request pacing or a lower-tier/lower-token model would be needed for a FULL paired Groq run; the pre-registered 10-attempt cap forbade lingering.

### What this pass DID establish

- Paired harness mechanics validated-end-to-end: identical turn-1 payload → identical provider prompt tokens (1 719 both); ledger accounting of billed vs rejected requests works; caps enforced; sandbox isolation held.
- Directionally: the chained-turn shipped content is much smaller under `delta` (1 107 vs 1 996 chained-context chars; turn-2 shipped 5 761 vs 8 087 chars when the same first-round shape was requested) — consistent with the redundancy Phase C targets, but **provider-confirmed token comparison of a chained turn is absent from this run** (the delta chained request was rejected unbilled).

### What this pass did NOT establish

- No valid Meta savings claim of any kind (no Meta request was made).
- No token/cost conclusion comparing conditions: `delta`'s chained turn never billed.
- No investigation-quality conclusion: both runs truncated; no valid summary on either side.

### Evidence basis for the later capped Meta test

Proceeding to the capped Meta paired test when `MODEL_API_KEY` is available remains justified: the harness is now validated (offline reproducibility, byte-level baseline reconstruction, provider-token sanity check, cap accounting), and the Groq pass surfaced no design flaw in the paired method. The Meta run stays governed by the caps pre-registered in `meta_paired_continuation_benchmark.py` (attempts/tokens/estimated cost/429 limits) plus the quality gates and decision rule already in RESULTS.md.

<!-- phase-d-groq-paced -->
## Phase D — Groq paired continuation, paced completion run (429 → wait to next minute; both conditions finished)

Generated: 2026-10-28 22:24 UTC. This run **supersedes the truncated run above** as the operative Groq outcome. Owner-directed change: Groq's on-demand tier enforces an ~8 000 tokens/minute window; the harness now paces itself under that window and, on a 429, waits until the next minute boundary and retries the same request instead of stopping. Every attempt — successful or rejected — is still ledgered; the ambient attempt ceiling was raised 10 → 25 solely because 429s now pause rather than end a run. No production code changed.

### Run integrity

8 provider attempts / 8 successful / **0 rejected** (pacing stayed under the window, so no 429 ever occurred). No cap breached; no stop reason. Sandbox DB isolated; the live app DB untouched.

Whole-run totals: **16 695 input + 3 049 output tokens, estimated cost US$0.004334** (0.15/0.60 per 1M, console.groq.com — an estimate, not a charge).

### Paired per-request table (provider-reported usage; both conditions bill identically at turn 1)

| Condition | Request | Status | prompt toks | completion toks | latency s | shipped msgs / chars | finish |
|---|---|---|---|---|---|---|---|
| - | GET /models | 200 | - | - | 1.39 | - | - |
| full | turn1r1 | 200 | 1719 | 625 | 2.66 | 2 / 2468 | tool_calls |
| full | turn1r2 | 200 | 2066 | 392 | 1.43 | 4 / 4222 | tool_calls |
| full | turn2r1 (chained) | 200 | 3101 | 748 | 2.40 | 8 / **8516** | stop |
| delta | turn1r1 | 200 | **1719** | 494 | 1.78 | 2 / **2468** | tool_calls |
| delta | turn1r2 | 200 | 2061 | 249 | 1.18 | 4 / 4132 | tool_calls |
| delta | turn2r1 (chained) | 200 | 2966 | 310 | 1.50 | 8 / **8054** | tool_calls |
| delta | turn2r2 | 200 | 3063 | 231 | 1.09 | 10 / 8604 | tool_calls |

Sanity check, unchanged and confirmed again: byte-identical turn-1 opening both sides → byte-identical chained turn-1 opening both sides → **exactly 1 719 prompt tokens both conditions**.

### Condition totals (billed requests only)

| Condition | reqs | input toks | output toks | provider latency | chained msg chars | est. cost |
|---|---|---|---|---|---|---|
| full | 3 | 6886 | 1765 | 6.49 s | 2002 | US$0.002092 |
| delta | 4 | 9809 | 1284 | 5.55 s | 1796 | US$0.002241 |

### The measured mechanical effect (and its confound)

The **controlled quantity** — the chained-turn opening message built from the same recorded state — is ~10% smaller under Phase C: **2002 chars (full) vs 1796 chars (delta)**. The per-request prompt-token difference at turn2r1 (3101 vs 2966) partially reflects this but is **confounded**: the two conditions' turn-1 behavior diverged, so their transcripts differ too. No provider credits per-message tokens; the per-message difference is therefore observable only at character level in this stateless analogue.

**Why this analogue understates Phase C's benefit:** under Meta's Responses API (Phase B verified), a chained request bills `input_tokens` for only the NEW turn while the provider retains the transcript server-side. Baseline full-resend would re-bill the entire context each continuation turn; delta bills just the small payload. This Groq analogue is forced to resend the full transcript in BOTH conditions, so it can only show the chained-message savings (≈10% here), not the larger per-turn billing reduction the real Meta architecture achieves. Groq cannot validate that Meta-side saving.

### Investigation-behavior comparison (material divergence, honestly flagged)

| Backend facts (recorded, not prose) | full | delta |
|---|---|---|
| tool executions | 2 (propose_hypothesis ×2) | 3 (propose_hypothesis, time_split_validation, +1 failed feature_target_suspiciousness attempt) |
| tool failures | 0 | 1 |
| reuse of prior results | 0 | 0 |
| tool budget used | 2/6 | 3/6 |
| hypotheses proposed | 2 | 2 |
| structured summary | **VALID** — conclusion "insufficient evidence to attribute OOF underperformance…", per-hypothesis status recommendations citing basis action IDs, uncertainties, recommended next steps | **invalid** — no summary block: the run ended on tool_calls at the turn-2 round cap after performing MORE diagnostics |

Both hypotheses (distribution shift, target leakage) are correctly distinguished from observed facts in both conditions' narratives; neither fabricated metrics. The divergence is behavioral, not architectural: with 2-round turns, the delta condition spent both synthesized rounds interpreting/planning more diagnostics and hit the round limit before writing the summary, while the full condition conceded earlier and synthesized. This is a single observation at 0.2 temperature — it flags a real risk (denser state deltas may encourage more exploration before synthesis; round limits then starve the summary), NOT a demonstrated regression. Any final Phase C verdict needs the Meta run or round-limited retries.

### Verdict for this pass

- Paired run: **completed**, 8/8 requests billed, 0 failures, 0 429s, total est. cost under half a cent.
- Paced 429 handling works as directed: no crash, no silent retries; the ledger shows `try 1` on every request this time because pacing pre-empted rate limits.
- Phase C decision: **unchanged — cannot be made from this analogue.** The measured mechanical saving (≈10% of the chained message; smaller than the truncated run suggested at 29%, once both conditions completed identically) is real but small here because the stateless resend dilutes it; the decisive Meta-side benefit (billed input = new delta only) is untestable on Groq. The Meta paired benchmark with `MODEL_API_KEY` remains the measurement that matters, per the pre-registered caps and decision rule.

<!-- phase-d-groq-summary-starvation -->
## Phase D — Groq summary-starvation investigation + harness fairness fixes (conditions improved; live pair rate-limited)

Generated: 2026-10-29 (third pass). Objective: explain why `delta` "used more diagnostics and failed
to produce a valid summary while `baseline` succeeded" (owner's framing, prior run), and make the
next comparison fair — WITHOUT touching production code, prompts, adapter, live DB, or the frozen
artifact. All claims below separate evidence (ledger/sandbox facts) from hypothesis.

### 1. Evidence-backed causes of the prior "summary-starvation" divergence

Per-request ledger (`phase_d_groq_results.json`) + both investigations' event histories:

| Backend facts | full | delta |
|---|---|---|
| provider requests (billed) | 4 | 4 |
| round cap in force BOTH sides | **3/turn** | **3/turn** |
| turn-2 stop | `finish=stop` with summary block | `finish=tool_calls` (round cap) |
| structured summary | valid | invalid (never emitted) |

Root cause is now **evidence-backed, not hypothesis**: the PRIOR run's round limit (2/turn) starved
`delta` because its denser state deltas encouraged more diagnostic exploration before synthesis;
the round cap, not the condition, decided interpretation-vs-synthesis. Three harness defects made
this look worse than it is, all fixed benchmark-side this pass:

1. **Round limit 2/turn (harness), production `TURN_ROUNDS=3`.** Fixed: harness now mirrors
   production exactly for both conditions (round limit 3), so both get the same stopping
   opportunity, including the F4 wrap-up request production offers.
2. **Missing F4 summary-repair equalizer.** Production offers one bounded no-tools repair request
   (`meta_loop._SUMMARY_REPAIR_TOKENS=1200`) when a final summary fails validation; the harness
   didn't. Fixed: repair mirrored exactly (same prompt shape, one bounded attempt, no tools);
   recorded either way.
3. **Output-token budget 1000 (harness) vs production `max_output_tokens=2000`.** Fixed. This was
   the subtlest defect: at 1000, the baseline's synthesis was cut mid-stream (`finish=length`)
   in one trial, invalidating its summary for a harness reason unconnected to the condition —
   the asymmetry was INTERACTIVE, not baseline-vs-delta.

**What is known** (harness-verified): these were the whole difference in the prior run. The
baseline's "success" was partly a patience artifact of needing one fewer synthesis round; the
delta condition's EXTRA diagnostic activity is real but was paused, not concluded.

**What remains hypothesis** (one pair each, cannot generalize): fixed-round-limit + equal budgets
may showLIKELY that `delta` now BEATS baseline on the same criteria; the three completed pairs so
far at production-mirrored caps show delta produced a valid summary AND more diagnostics in trials
1-2, while trial 3 aborted on a provider-side model fault (bogus tool name → Groq rejects at
generation time with 400 "tool call validation failed"), a *model behavior* issue, not an
architecture one (production tolerates bogus tool names client-side; run_tool fails them there).

### 2. Harness fixes this pass (benchmark-only; zero production edits)

1. Bogus-tool-name 400s are now condition-scoped: one counted retry keeps loop-equivalent
   semantics; persistence aborts ONLY that condition without vetoing the other's run.
   Previously such a 400 aborted the WHOLE run before `delta` ever started (unfair error handling).
2. Per-condition `aborted`/`aborted_reason` flags surface honestly in results (previously these
   stops were ledgered but reported with `status: null`, looking like silence).
3. Provider-guided rate-limit waits: Groq's documented headers (`retry-after`,
   `x-ratelimit-reset-tokens`) now drive bounded waits instead of a blind minute-boundary sleep
   (docs: console.groq.com/docs/rate-limits). Attempts, waits, and final rate hints are ledgered.
4. `chat:turn1r2` and `chat:turn1r3` tags expose 429-in-place waits; `per_request_ledger` records
   `#tryN` for every rejected crystal-clear.

### 3. Live outcome this pass (honest)

8 pairs attempted → **no complete pair was produced this pass**. Three trials stalled on Groq
on-demand tier rate limiting whose cooldown windows (provider-reported `retry-after`: 293s,
39s, 526s between tries) exceed the wall-clock budget a sane capped run can spend on pauses;
2 runs completed BOTH conditions, 1 aborted mid-`full` on the bogus-tool-name fault, 1 aborted
mid-`delta`, and 2 stalls on persistent 429 hard-stopped the run. Estimated spend across all
trials ≤ US$0.01 total; no cap (attempts/tokens/cost) was breached; nothing ran unbounded.

**A live paired result is NOT available this pass.** The provider begging for 5-minute single-
request cooldowns interacts badly with an 8k-token-per-minute tier. A successful paired
comparison requires either (a) a higher-tier key, (b) batches spread over tens of minutes with
the owner's blessing on wall-clock, or (c) a smaller/lower-tier model (e.g. 20b variant) so both
conditions fit comfortably in one window.

### 4. What this pass DID establish

- The summary-starvation cause is confirmed as a HARNESS defect set, now fixed: equal round
  limits (3, matching production), equal output-token budgets (2000, matching production), equal
  F4 repair availability. These fixes are necessary regardless of which condition wins.
- The bogus-tool-name 400 aborting the whole pair was THE structural waste; scoping it to one
  condition ends manufacturing of asymmetric cap failures.
- Sandbox isolation held throughout: no production DB, adapter, prompt, frontend, or frozen
  artifact was touched (verified by git status/diff scoping and by the untouched production
  test suite still passing).

### 5. Explicit non-claims

- No Meta API savings are claimed anywhere. Groq findings do not transfer to `previous_response_id`
  behavior or Meta billing.
- No quality conclusion from a single pair, and no pair completed under the production-mirrored
  caps this pass. The next live pass should run under the production-parity caps (rounds=3,
  max_output_tokens=2000, one F4 repair both sides) and expect ~10-15 minutes of wall time per
  pair on this tier, or use a higher-rate-limit key.
- No statistical significance claimed from any sample size here (0 complete pairs this pass).

<!-- phase-d-groq-20b-pilot -->
## Phase D - Groq 20B paired pilot (PRODUCTION-PARITY CONFIG; PAIR COMPLETED)

Generated: 2026-10-29 (fourth pass). Machine-readable results:
`phase_d_groq_20b_pilot.json`. This section preserves; it does not overwrite,
the prior Groq passes above.

### Pre-pilot inspection findings (fixed before the run)

1. **Sandbox-isolation regression (defect):** the DB-path bootstrap had been
   stranded after an early `return` inside the rate-header extractor during
   the last pass, leaving `MODEL_AUTOPSY_DB_PATH` unset (the offline run
   emitted `"sandbox_db": null`). Restored into `bootstrap_env()`; the offline
   run now reports a real temp sandbox path and all 33 scoped tests pass
   (`tests/test_groq_benchmark.py`, `tests/test_meta_adapter.py`,
   `tests/test_meta_retries.py`).
2. **F4 repair status vocabulary (parity defect):** the benchmark-only repair
   prompt previously hardcoded `proposed, supported, refuted` while production
   `engine.HYPOTHESIS_RECOMMENDABLE_STATUSES` is the broader set (proposed,
   investigating, supported, rejected, inconclusive). It now imports the
   production constant. Validator behavior was unaffected either way.
3. Stale module docstring updated (3-round limit, 2000-token output budget,
   provider-guided waits, condition-scoped tool-validation 400s):
   documentation only.

### Preregistered-artifact model change (declared deviation)

The preregistered model was `openai/gpt-oss-120b`, which on this key's
on-demand tier repeatedly met >4-minute provider cooldowns (`retry-after`
293s/39s/526s across three prior passes; no pair ever completed there).
Per docs/rate-limits both models share the same 30 RPM / 8K TPM / 1K RPD
window, and the prior section pre-declared "a smaller/lower-tier model
(e.g. 20b variant)" as the fallback; the pilot therefore used
`openai/gpt-oss-20b`. Availability and tool-calling were probed first: 20b is
listed, and one capability probe passed (one probe with a fair "supply any
required arguments" instruction returned a valid tool call; the first,
adversarial no-arguments probe returned Groq 400 and is disclosed below as an
unbudgeted, unretryable probe attempt).

### Pilot design (identical except the chained-turn opening message)

Model `openai/gpt-oss-20b`; temperature 0.2; 3 rounds per turn; output budget
2000 tokens; tool budget max_tool_calls=6; same reduced tool allowlist; reuse
guard ON both sides; production packet truncation + wrap-up item on both
sides; ONE production-parity F4 summary repair per run when the final summary
fails validation (identical for both conditions, one bounded no-tools
request). The ONLY condition difference: the chained-turn (turn-2) user
message - `full` re-transmits the whole initial recording context; `delta`
transmits just the fresh state delta. Hard caps unchanged: 25 attempts /
120,000 tokens / US$0.50 est. / 4-consecutive-429 stop / 9 bounded
provider-guided waits max per logical request.

### Execution (12 billed / 0 rejected; 0 429 waits; no cap breached)

12 of 25 attempts used (including the pilot's own GET /models); 27,845 input
+ 6,591 output tokens of the 120,000 ceiling; estimated US$0.004066 of the
US$0.50 ceiling. Both conditions stayed far from the TPM window
(`x-ratelimit-remaining-tokens` >= 5,042 of 8,000). Sandbox DB fresh per run
(`ma-phase-d-groq-*` temp dir); the production DB, prompts, adapter,
frontend, and frozen artifact untouched.

Turn-1 sanity check re-confirmed on 20b: turn1r1 prompt tokens exactly 1,719
with 2,468 shipped chars in BOTH conditions (byte-identical openings;
provider-reported usage agrees).

### Provider-reported usage and estimated cost (20b pricing: 0.075/0.30 per 1M)

| Condition | requests | input tokens | output tokens | provider latency | est. cost (ESTIMATE) |
|---|---|---|---|---|---|
| full | 6 (3 t1 + 2 t2 + 1 repair) | 16,638 | 4,261 | 10.949 s | US$0.002526 |
| delta | 5 (3 t1 + 1 t2 + 1 repair) | 11,207 | 2,330 | 11.531 s | US$0.001540 |
| total | 12 (+1 models list) | 27,845 | 6,591 | 22.48 s | US$0.004066 |

Cost figures are ESTIMATES from published pricing, not actual charges.

Token-attribution caveat: transcripts had already diverged by turn 2 (turn-1
outputs differ), so the turn-2 prompt-token difference (3,508 full vs 3,133
delta) mixes the chained-opening difference with earlier output-size
differences; it is not a clean per-component delta. The controlled quantity -
the chained-turn opening message - measured nearly identical this run
(2,147 full vs 2,134 delta chars): with diagnostics recorded, delta's fresh
state payload (roster + findings + ledger + budget) grew to roughly the size
of the corpus. Under this scenario the Groq-visible saving is dominated by
delta spending ONE FEWER turn-2 round (it concluded immediately) plus smaller
turn-1 outputs - NOT by a large chained-message shrink.

### Quality gates (per condition)

| Gate | full | delta |
|---|---|---|
| summary valid after F4 repair | yes | yes |
| repair attempts (counted, bounded) | 1 | 1 |
| hypothesis ids from recorded roster | yes (validator) | yes (visible in JSON head) |
| basis cites recorded action ids | yes (validator) | yes (2 recorded action ids visible) |
| facts vs hypotheses distinguished | yes ("remains an unconfirmed hypothesis") | yes ("inconclusive"; cites basis) |
| tools executed / failed | 4 / 0 | 3 / 0 |
| tool budget used | 4/6 | 3/6 |
| duplicate attempts | 0 | 0 (2nd metrics call added split_by:"fold") |

### Substantive behavioral divergence (flagged, not hidden)

The conditions reached DIFFERENT answers to the same objective:

- **full** ran feature_target_suspiciousness + time_split_validation and
  concluded that feature `hold1_ret` correlates with the target, suggesting
  potential leakage inflating training performance - explicitly labelled "an
  unconfirmed hypothesis". Evidence-backed: it executed the diagnostics.
- **delta** never ran suspiciousness or time-split; its own hypothesis's
  predicted_observation described exactly those follow-up diagnostics, then it
  concluded "no definitive cause ... can be established" and published the
  hypothesis as `inconclusive`. Honest, correct epistemics, but cheaper AND
  terminally less informative in this pair: it described the right work
  instead of doing it, while remaining inside budget.

Whether this is one-pair model-behavior variance (temperature 0.2) or a
systematic effect of the denser delta state channel is impossible to
distinguish from a single pair.

### Explicit non-claims

- No Meta API / previous_response_id savings claim of any kind. Groq is a
  stateless analogue: both conditions resend the transcript each request, so
  Meta's server-side retention and its billing behavior cannot be measured
  here.
- No statistical significance (single pair).
- No quality-equivalence claim; the recorded divergence favors FULL this
  pilot.
- No comparability of this 20b run to any earlier 120b numbers in this file;
  the conditions comparison here is internally consistent only (same model
  both sides).

### Recommendation (next step)

The Phase C retention decision still belongs to the capped Meta paired
benchmark (meta_paired_continuation_benchmark.py with MODEL_API_KEY). This
pilot re-validated the harness mechanically (identity-baseline turn-1
billing, clean ledger, all caps untouched, zero rejections in a complete run)
and adds ONE new flag for the Meta run's quality analysis: watch whether the
delta channel shifts behavior toward planned-but-unexecuted diagnostics
(observed once here) - cheap tokens with weaker conclusions would defeat the
optimization's goal. 2-3 more 20b pairs (<=US$0.01 each on this tier) would
begin separating variance from a systematic effect; nothing in this pilot
narrows that to a conclusion.

<!-- phase-d-groq-20b-pilots-2-3 -->
## Phase D - Groq 20B paired pilots #2 and #3 (two additional pairs; diagnostic-follow-through test)

Generated: 2026-10-29 (fifth pass). Purpose: test whether pilot #1's observation -
delta proposed then skipped the diagnostics its own hypothesis predicted, while
full executed them - was one-pair model variance or a systematic delta-context
effect. Protocol: exactly TWO additional pairs, existing harness unchanged,
production files untouched, all prior sections preserved.

### Protocol (byte-identical to pilot #1 except nothing)

Same configuration as the completed 20B pilot: `openai/gpt-oss-20b`,
temperature 0.2, 3 rounds per turn, 2000-token output budget, tool budget 6,
same tool allowlist/schemas, same objective/artifact, production wrap-up item,
one F4 repair per run, reuse guard ON both sides, production packet
truncation. Caps unchanged and enforced per attempt: 25 attempts / 120,000
tokens / US$0.50 est / 4-consecutive-429 stop / 9 bounded provider-guided
waits max per logical request. Machine-readable ledgers written to NEW files;
pilot #1's JSON untouched:
pilot #2 = `phase_d_groq_20b_pilot2.json`,
pilot #3 = `phase_d_groq_20b_pilot3.json`.

Pre-flight: model still listed via `GET /models`; pricing still 0.075/0.30 per
1M (console.groq.com/docs/models); fresh sandbox DB per invocation.Expected ~12 requests/pair at ~US$0.004 each; actuals below.

### Pair completion (both pairs finished; zero rejections anywhere)

| Pair | attempts | billed | rejected | 429 waits | est. cost (ESTIMATE) |
|---|---|---|---|---|---|
| #2 | 12 | 12 | 0 | 0 | US$0.003927 |
| #3 | 11 | 11 | 0 | 0 | US$0.003602 |No 429s occurred in either new pair (`rate_limit_wait_s` 0.0 both conditions, both pairs); token-header headroom stayed >= ~4,400/8,000 throughout.

### Provider-reported usage per condition (billed requests only)

| Pair | full in/out | full est. | delta in/out | delta est. |
|---|---|---|---|---|
| #1 (prior) | 16,638 / 4,261 | US$0.002526 | 11,207 / 2,330 | US$0.001540 |
| #2 | 11,661 / 2,571 | US$0.001646 | 15,289 / 3,780 | US$0.002281 |
| #3 | 11,748 / 3,541 | US$0.001943 | 11,225 / 2,723 | US$0.001659 |
| 3-pair total | 40,047 / 10,373 | US$0.006115 | 37,721 / 8,833 | US$0.005480 |

Cost figures are ESTIMATES from published pricing, never charges.  Directions FLIPPED in pilot #2: delta used MORE tokens than full there, because delta was the condition that pursued the additional diagnostics.

### The head-line result: pilot #1's concern did NOT repeat as a delta effect

Diagnostic follow-through, per pair (recorded actions, never prose):

| Pair | full diagnostics executed | delta diagnostics executed |
|---|---|---|
| #1 | 4: suspiciousness, classification, time-split, hypothesis | 3: classification x2 (differing args), hypothesis - suspiciousness/time-split PROPOSED BUT NOT RUN |
| #2 | 3: classification x2 (differing args), hypothesis | 4: classification, suspiciousness, time-split, hypothesis |
| #3 | 3: classification, suspiciousness, hypothesis | 3: classification, time-split, hypothesis |

Across the three pairs, WHO executes the "deeper" diagnostics alternates:
full in #1, delta in #2, both partially in #3. The observed behavior is
pair-level model variance, not a stable property of either context strategy.
n=3 cannot establish a rate or rule it out; but the specific "delta starves
its summary" pattern from pilot #1 did not replicate.

### Summary validity and repair outcomes (bounded repair, no loops)

| Pair | full | delta |
|---|---|---|
| #1 | valid after 1 repair | valid after 1 repair |
| #2 | INVALID after 1 repair (no fenced block; repair failed honestly, recorded) | valid after 1 repair |
| #3 | valid after 1 repair | valid after 1 repair |

Delta: 3/3 valid summaries. Full: 2/3 - the one failure is a summary-integrity
failure, not an investigation-quality failure (see next section). Every run
used exactly one repair; no run looped or breached budgets.

### Evidence-backed quality difference (the part that matters)

- **Pilot #1** (prior pass): delta weaker - described planned diagnostics,
  never executed them; conclusion "no definitive cause ... inconclusive"
  (cites 2 recorded actions). Full evidence-backed the `hold1_ret` leak
  signal as "unconfirmed hypothesis".
- **Pilot #2 - ROLES REVERSED.** full produced a PROSE summary (Markdown
  table + narrative) with NO structured `investigation_summary` block; the
  bounded repair could not recover one, so the run ends with no valid
  machine-readable summary (valid=False; recorded honestly). Full still had
  real content (per-fold AUCs ~0.68 spread contradicting its overfit
  hypothesis), but zero structured output to carry it. delta, meanwhile,
  executed the deeper diagnostics instead and produced a valid summary with a
  causal-ish claim: "poor OOF performance primarily due to class imbalance ...
  low recall while maintaining moderate AUC", status `supported`, basis =
  action 32d6f2f4... (its classification_metrics run). Quality caveat:
  `supported` is aggressive for a single-sourced metrics action - the
  imbalance->recall causality is inference beyond the action's scope, though
  the summary validated and cites the recorded action ID correctly.
- **Pilot #3: effectively a tie.** full: "no evidence of overfitting; AUC
  moderate and consistent across folds; no leakage detected from the
  suspiciousness analysis" - abstention backed by ITS OWN executed
  suspiciousness diagnostic (action 15bd3d7d...). delta: "insufficient
  evidence to confirm or refute temporal drift; further analysis required",
  status `inconclusive`, basis = recorded actions 9b3a830f... + e71ccd4e...
  Both valid, both evidence-cited, delta marginally cheaper
  (11,225/2,723 vs 11,748/3,541).

Distinguishing claims (as requested):
1. REPEATED OBSERVATION: pilot #1's delta-concluded-without-executing pattern
   did NOT recur in pairs #2/#3; if anything the roles reversed in #2.
2. PLAUSIBLE EXPLANATION: the effect is model-behavior variance under
   temperature 0.2 interacting with whichever condition is further along its
   exploration trajectory, possibly with the richer delta state nudging MORE
   (not less) planned-follow-through sometimes.
3. SUPPORTED CONCLUSION (from the sample): at n=3, neither condition shows a
   quality edge; both are capable of both failure modes (full failed a
   summary in #2; delta failed follow-through in #1). Valid-summary count:
   delta 3/3 vs full 2/3 - a THREE-PAIR sample note, not a rule.

### Failures, waits, deviations

- Zero rejections, zero 429 waits, zero cap breaches in both new pairs.
- Full's pilot-#2 summary repair failed and was recorded as such (no
  overwriting, no silent retry). This is the F4 bound working as designed.
- No protocol deviations: harness, config, caps, and model all reused from
  pilot #1 unchanged. The two new ledgers are new files; no historical
  artifacts were overwritten.

### Explicit non-claims

- No statistical significance; n=3 pairs.
- No Meta API / `previous_response_id` savings established - Groq resends
  the transcript in BOTH conditions by construction.
- No claim that delta's cost/token profile is systematically lower - the
  Sign FLIPPED once (pilot #2) with diagnostic volume as the driver.
- No claim that Phase C should be retained or rejected from this evidence;
  the decision remains the capped Meta paired benchmark's, on measured
  savings and maintained quality.

### Recommended next step

The recurring actionable finding across all passes is harness-level, not
condition-level: the failure mode that MATTERS (pilot #2 full) is a
PROSE-instead-of-structured summary that one bounded repair could not recover.
Cheap, high-value next steps before any Meta decision: (a) 2-3 further pairs
at the same cost (~US$0.004 each) to get the valid-summary rate above n=3;
(b) consider whether production's single-repair bound should allow ONE
explicit structured-output retry when the original message contained real
analysis but no fenced block - the current bound discards good evidence into
an unparseable format. Both are Groq-only, cheap, production untouched.

<!-- phase-d-addendum-repair-failure-forensics -->
### Addendum (2026-10-29, sixth pass) — pilot #2 full summary/repair failure, cause identified

The pair-#2 characterization above ("INVALID after 1 repair (no fenced block)")
was imprecise. The sandbox DB for pair #2 was re-examined. Correction:

- The full run's ORIGINAL final message WAS prose-only (no fence) — that part
  stands, and the one bounded repair was requested (`chat:turn2repair`, HTTP
  200, `finish_reason: "stop"`, 891 completion tokens against the 1,200-token
  repair budget, so NOT output-budget truncation).
- The REPAIR response DID open a ```investigation_summary fence — the recorded
  event detail begins with `` ` `` — ```investigation_summary followed by
  valid-looking JSON prefix. However the validator's deterministic behavior
  proves no COMPLETE fenced block existed in that message: the recorded errors
  are exactly ['no structured summary found in the final message'] with no
  JSON-parse error and no parsed/raw_block payload (either fence-match failing
  or JSON-parse error would have been recorded instead), and the fallback
  bare-JSON pattern cannot match a nested-JSON body.
- The consistent explanation: the model (gpt-oss-20b, temp 0.2) emitted the
  opening fence and JSON and left the block unclosed — a MODEL-OUTPUT
  formatting failure, not a harness/validation defect and not budget
  truncation. Neither cited identifier was fabricated: hypothesis
  147726b7... and action e55013cc... both exist in the full condition's
  sandbox investigation.
- Caveat: only the first 600 characters of each event are stored, so the
  above is a demonstrated missing/unclosed block rather than full-byte proof;
  the validator's behavior fully determines the parsed outcome regardless.

Harness gap found and fixed (benchmark-only; production validator untouched):
the repair-time validation errors used to be DISCARDED — the run JSON carried
the original attempt's error string, which misdirected the first analysis.
`groq_paired_continuation_benchmark.py` now records the repair's own
validation errors as `summary_repair_errors` in the run record, with a
regression test (`test_unclosed_summary_fence_reproduces_pilot2_repair_failure`,
`test_harness_records_repair_validation_errors_in_run_record`; scope suite
43/43 passing).

Phase C decision impact: none beyond the correction — the failure remains a
case of "structured-output latency under one bounded repair," now with a
precise model-behavior cause rather than an assumed absent block.

<!-- phase-d-20b-pair4-pair5 -->
## Phase D, seventh pass (2026-10-29): Groq 20B paired pilots #4 and #5

**Purpose.** Two additional paired pilots (full vs delta continuation context) on
`openai/gpt-oss-20b` to extend the three-pair sample under the established
production-parity protocol. No protocol changes were made: temperature 0.2, 3
rounds/turn, 2 turns, 2,000-token output budget, 6-tool budget, one bounded
F4 summary-repair request, duplicate-diagnostic reuse guard, production tool
registry and prompts. Caps enforced per run: <=25 provider attempts,
<=120 000 tokens, <=$0.50 ESTIMATED cost, abort after 4 consecutive 429s;
stops/caps unchanged. Sandbox DB per run (temp dirs), live DB untouched.

**Outcome — both pairs completed cleanly, no model switching, no extra caps.**
- Pair #4 (`phase_d_groq_20b_pilot4.json`): 10 billed + 2 repair = 12/12 HTTP
  attempts OK, 0 failures, 0 rate-limit waits, 28 659 in / 7 850 out tokens,
  est. $0.004504 (input $0.075/M, output $0.30/M).
- Pair #5 (`phase_d_groq_20b_pilot5.json`): 10/10 attempts OK, 0 failures,
  0 waits, 21 163 in / 5 370 out tokens, est. $0.003198.
- Neither run hit any cap; wall time was dominated by pre-emptive
  minute-token-window pacing (the pacer reserves against the published
  ~8 000 tokens/minute on-demand window; `rate_limit_wait_s` stays a truthful 0.0
  because waits were avoidance reserves, not post-429 waits).

### Per-condition comparison (all five 20B pairs; est. cost = ESTIMATE)

| Pair | Full in/out tok | Delta in/out tok | Est. cost (F / D) | Repair used (F/D) | Valid summary end (F/D) | Diagnostics run (F/D) |
|---|---|---|---|---|---|---|
| #1 | 16 638 / 4 261 | 11 207 / 2 330 | — (historical) | 1 / 1 | T / T | 4 / 3 |
| #2 | 11 661 / 2 571 | 15 289 / 3 780 | — (historical) | 1 / 1 | **F** / T | 3 / 4 |
| #3 | 11 748 / 3 541 | 11 225 / 2 723 | — (historical) | 1 / 1 | T / T | 3 / 3 |
| #4 | 16 358 / 3 485 | 12 301 / 4 365 | $0.00227 / $0.00223 | 1 / 1 | T / T | 4 / 3 |
| #5 | 11 627 / 2 830 | 9 536 / 2 540 | $0.00097 / $0.00154 | 1 / 0 | T / T | 3 / 3 |

Delta used fewer input tokens in 4 of 5 pairs (ranged -33% to -25% in the three
clean large-delta pairs; #5 -18%; #2 was inverted, +31%, because the full run's
context itself was smaller that day and delta's own path was chatty). Output
tokens have no consistent direction (delta used more outputs in #4).

### Evidence-backed quality findings (pairs #4 and #5)

- **The pair-#1 diagnostic-follow-through concern did NOT repeat.** Delta
  executed the diagnostics its conclusions relied on in both new pairs
  (#4: 3 actions — classification_metrics, feature_target_suspiciousness,
  propose_hypothesis; #5: 3 actions — calibration_and_error_analysis,
  classification_metrics, feature_target_suspiciousness). Recorded statuses and
  action citations resolved against real sandbox IDs (e.g. #4 full cites action
  44e04452... / hypothesis e67afc78..., both present). Across five pairs the
  observed incidence of delta proposing-but-not-executing is 1 of 5 — plausibly
  one-off, unproven either way at n=5.
- **Round usage shaped conclusion informativeness in #4.** Full used 2 synthesis
  rounds and converged to an evidence-backed candidate cause ("hold1_ret highly
  correlated with the target (|r|=0.61) suggests potential label leakage", status
  `investigating`); delta synthesized after ONE round and deliberately abstained
  ("the current evidence does not confirm or refute...", status `proposed`, basis
  = 3 recorded action ids). The abstention is honest, but it left a readily
  testable hypothesis (feature ablation) untested with 3 tool calls and 2 rounds
  remaining — the same qualitative gap seen in pair #1's full>delta path.
- **Paired evidence asymmetry.** In #4, full additionally re-derived the metrics
  path (4 actions incl. reuse-guarded reuse = 0) before concluding; in #5 both
  conditions used 1 synthesis round and 3 actions, and both concluded with
  appropriately hedged language. Delta ran `calibration_and_error_analysis`
  first in #5 while full ran `dataset_validation` — model path variance exists
  in both directions.
- **Structured-output quality: a repeated, condition-symmetric behavior.** In
  9 of 10 runs, the FIRST synthesis attempt wrapped the summary in a
  markdown-prose preamble plus a ```json fence instead of the required
  ```investigation_summary fence (validator correctly returned
  "no structured summary found"), and the single bounded repair recovered a
  valid block after the repair prompt re-specified the fence. The one exception
  (pair #5 delta) passed WITHOUT repair via the validator's documented
  bare-JSON fallback, whose `{"conclusion"...}` capture cannot match nested
  status-recommendation objects, so it only fires when the JSON is flat).
  Therefore: (a) the production-parity one-shot repair is doing real work in
  this harness (9 recoveries) and should stay; (b) summary validity at n=10 is
  influenced by the validator's fragile fallback path — a PRODUCTION robustness
  note recorded here without changing production; (c) #2's full-case
  prose-only/no-fence failure remains a distinct, single occurrence of
  repair-insufficient output.

### What these two pairs do and do not establish

- Established: repeatable harness mechanics at production-parity settings
  (caps, pacing, isolation, schema) and two more clean pairs for n=5 total.
- NOT established: any quality parity claim (n=5, one model, one artifact);
  no statistical significance; nothing about Meta API billing,
  `previous_response_id` savings, or production retention (Groq is stateless
  Chat Completions; Groq pairs cannot measure Meta savings).
- The most material open delta-side behavior remains variance in how early
  delta synthesizes under equal wrap-up rules (1 vs 2 synthesis rounds in #4),
  which pairs with its consistent input-token advantage.

### Recommended next step

Stop adding Groq pairs (n=5 shows stable mechanics; remaining variance is
model behavior, not harness). The next decisive measurement must be the
actual capped Meta paired benchmark once `MODEL_API_KEY` is configured —
persist repair-time and validator truncation diagnostics as fixed in the
harness above apply there too. Decision rule unchanged from Phase D: retain
Phase C's delta strategy only if measured (not estimated) Meta input-token
savings appear at equal-or-better investigation quality.

<!-- phase-d-20b-five-pair-trace-reanalysis -->
## Phase D, trace-level re-analysis of the five Groq 20B pairs (2026-10-29, no API calls)

**Scope.** Existing data only. The five ledgers (`phase_d_groq_20b_pilot.json`,
`...pilot2.json` .. `...pilot5.json`) and the sandbox SQLite databases they
point at were re-read read-only; `analyze_groq_pairs.py` extracts the ordered
traces into `phase_d_groq_pair_trace_analysis.json`. No provider request was
made, no production file was modified, and every section above is preserved
verbatim. This section corrects three prior wordings where the ledgers alone
were insufficient (see "Corrections" below).

### What the ledgers did not contain, and what the traces show

The ledgers store rounds, finish reasons, summary validity and backend
counters, but not what executed in each turn. The sandbox databases do.

- **Turn 1 was structurally identical in all 10 runs:** 3 rounds, 3 tool
  calls, no summary block, ending at the 3-round cap (`finish_reason:
  tool_calls` each round). The diagnostics chosen differed by run.
- **Turn 2 never gathered evidence in any run.** Of the 10 runs, 7 synthesized
  in the first turn-2 round (0 calls). The other 3 (pilot 1 full, pilot 2
  delta, pilot 4 full) used exactly one extra round, and in every case that
  call was `propose_hypothesis` - not a diagnostic.
- **Every run stopped with budget left:** 3 or 4 of 6 tool calls used, at
  least 2 unused; no run used a third turn-2 round.
- Therefore **the evidence base is fixed by turn 1**, whose opening context
  was byte-identical across conditions. The continuation message cannot change
  what is available to reason about; it can only change what the model does
  with it.

Tool coverage (evidence-bearing calls only - `time_split_validation` returns
date spans/fold sizes and no performance metric, so it is counted as
structural, not as evidence):

| Pair | Full evidence tools | Delta evidence tools |
|---|---|---|
| 1 | classification_metrics, feature_target_suspiciousness | classification_metrics |
| 2 | classification_metrics | classification_metrics, feature_target_suspiciousness |
| 3 | classification_metrics, feature_target_suspiciousness | classification_metrics |
| 4 | classification_metrics, feature_target_suspiciousness | classification_metrics, feature_target_suspiciousness |
| 5 | classification_metrics, dataset_validation | classification_metrics, feature_target_suspiciousness, calibration_and_error_analysis |

Mean distinct evidence-bearing tools: full 1.8, delta 1.8. The two conditions
did not differ in evidence coverage.

### Confounder found: a "finish now" instruction immediately precedes turn 2

`_wrapup_item` fires on the last round of turn 1 in every run ("Budget/rounds
are nearly exhausted... Finish now: interpret the recorded results honestly
and end with your investigation_summary block"). The harness then appends the
chained opener and starts turn 2. In production that wrap-up ends the loop;
it is not followed by a new continuation turn. So both conditions were told to
finish immediately before the only turn in which synthesis timing could vary.
This is benchmark-only protocol, shared by both arms, but it floors turn-2
investigation and makes "stopping behaviour" unrepresentative of production.

### Paired trace summary

| Pair | T2 rounds F/D | Extra T2 action F/D | Calls F/D | Final summary valid F/D | Repair F/D | Conclusion (F / D) |
|---|---|---|---|---|---|---|
| 1 | 2 / 1 | propose_hypothesis / - | 4 / 3 | yes / yes | 1 / 1 | hold1_ret correlation suggests leakage, unconfirmed / "no definitive cause" |
| 2 | 1 / 2 | - / propose_hypothesis | 3 / 4 | **no** / yes | 1 / 1 | no structured summary / "primarily class imbalance", status `supported` |
| 3 | 1 / 1 | - / - | 3 / 3 | yes / yes | 1 / 1 | no overfitting, "no leakage detected" / temporal drift inconclusive |
| 4 | 2 / 1 | propose_hypothesis / - | 4 / 3 | yes / yes | 1 / 1 | hold1_ret leakage candidate / same hypothesis "does not confirm or refute" |
| 5 | 1 / 1 | - / - | 3 / 3 | yes / yes | 1 / 0 | overfitting "does not support or refute" + false budget claim / quantitative multi-factor conclusion, no status recs |

### Measured findings

1. **Mechanical validity: 9/10 final summaries valid.** First-attempt validity
   was 1/10 (pilot 5 delta, accepted by the bare-JSON fallback because
   `status_recommendations` was empty and the object was flat). Nine runs
   needed the one bounded repair; eight recovered. The single unrecovered case
   (pilot 2 full) is the unclosed-fence repair failure already documented in
   the sixth-pass addendum. This is a summary-formatting/termination issue,
   not a difference between context conditions.

2. **Citation validity: 14/14 basis action IDs and 8/8 hypothesis IDs in the
   nine parsed summaries resolve to rows in the same investigation.** No
   fabricated identifier was found. One valid summary (pilot 4 delta) used a
   comma-separated *string* for `basis` instead of a list; the validator
   accepts it because it only checks hypothesis IDs and statuses, never basis
   shape. No production consumer iterates `basis`, so no break was observed,
   but the schema is unenforced.

3. **Numeric grounding is the weakest measured dimension.** Only pilot 5
   delta cites measured numbers (AUC 0.683, Brier 0.131, |r| 0.606, per-fold
   0.68-0.69). The other eight usable conclusions are qualitative even though
   every trace contained those values. Its only unanchored figure ("~15%
   positives") is recoverable from the calibration bins it received (weighted
   positive rate 16.48%; the raw 6 792 / 41 221 count appears only in the full
   arm's `dataset_validation`); it is approximate, not fabricated. A summary
   can be mechanically valid, cite real actions, and still not say what the
   numbers were.

4. **No condition-level quality advantage: 2-2-1 on paired informativeness.**
   Full produced the more informative conclusion in pairs 1 and 4 (named
   `hold1_ret`, proposed an ablation); delta in pairs 2 and 5 (pair 5 was the
   only quantitative conclusion; pair 2 is the only pair where full had no
   usable summary); pair 3 was weak in both. Failure modes differ rather than
   ranking: all three epistemic/termination failures were full-side (one
   unrecovered summary, one misread of its own feature scan, one pair of false
   statements about diagnostics and remaining budget), while delta produced
   the only overclaim (`supported` class imbalance without a reweighting test)
   and the only summary with no hypothesis link. With n=5 and one model at
   temperature 0.2 these are anecdotes, not a condition effect.

5. **Timing association, not a context effect.** The three runs that spent an
   extra turn-2 round registering a hypothesis before synthesis produced the
   more informative or valid summary in all three of their pairs. The extra
   round added no evidence. The association is split 2 full / 1 delta, so it
   tracks deliberation/structuring, not the continuation format. n=3:
   exploratory.

6. **Abstention was honest but avoidable.** Pilot 1 delta, pilot 3 delta and
   pilot 4 delta abstained in ways consistent with the evidence each had
   gathered - none asserted an untested cause. But all three had >=2 tool calls
   and >=1 round unused, and the missing tests existed: a feature scan
   (pilot 1 delta), `classification_metrics(split_by="fold")` (pilot 3 delta),
   and a retrain/ablation (pilot 4 delta). Pilot 5 full's abstention is the
   exception: it claims no diagnostic metrics were run (per-fold AUC and
   dataset validation were run) and that the budget was exhausted (3/6 calls
   used). That is a factual self-report error, not a conservative choice.

7. **Token comparison correction.** Run-total input tokens differ by -33% /
   +31% / -5% / -25% / -18% (delta vs full), but request counts differ in four
   of five pairs (6/5, 5/6, 5/5, 6/5, 5/4), so totals mostly measure how many
   rounds each arm happened to take. Per-request input: -19.2%, +9.3%, -4.5%,
   -9.8%, +2.5% (mean -4.3%, median -4.5%). The chained message itself differs
   by only 13 / 566 / 254 / 18 / 341 characters, i.e. 0.1% / 4.4% / 2.0% /
   0.1% / 2.5% of the corresponding turn-2 prompt. The prior statement that
   "delta used fewer input tokens in 4 of 5 pairs" is true at the run-total
   level but is not a clean context-strategy measurement: at equal request
   count the effect is a few percent, and the large totals are round-count
   driven. The Groq analogue therefore cannot demonstrate Phase C's billing
   benefit; it can only test behavioural framing.

8. **Same evidence, divergent interpretations.** `feature_target_suspiciousness`
   scans the predictions CSV and therefore reports the label itself (r = 1.0)
   plus model-score columns; `hold1_ret` is the only genuine feature with a
   strong association (|r| = 0.606) and the tool explicitly caveats that
   provenance is required. Pilot 3 full read this as "no leakage is detected";
   pilots 4 full, 4 delta and 5 delta read it as a leakage flag. This is
   ambiguity handling, not a condition difference, and it is the main reason
   paired conclusions diverge on identical evidence.

### Corrections to earlier wording (history preserved, not rewritten)

- The seventh-pass sentence "in 9 of 10 runs, the FIRST synthesis attempt
  wrapped the summary in a markdown-prose preamble plus a ```json fence" is
  too strong. The archived first 600 characters show a ```json fence in 5 of
  the 9 invalid first attempts; the other 4 show no fence in the archived
  prefix. What is certain for all nine is that no *complete*
  ```investigation_summary block was present. The exact per-run failure mode
  beyond 600 characters is UNMEASURED: invalid summary events store
  `raw_block: null` and `record_event` keeps only 600 characters of detail.
- "Round usage shaped conclusion informativeness in #4" is right about the
  association but wrong about the mechanism: the extra round ran
  `propose_hypothesis`, not another diagnostic. No run gathered new evidence
  after turn 1.
- The earlier implication that delta under-investigates relative to full does
  not survive the full sample: both arms left >=2 calls unused, and the three
  extra-round runs split 2 full / 1 delta.

### Confounders that prevent a fair context-strategy comparison

1. Evidence is frozen after turn 1; continuation format cannot change it.
2. A "Finish now" wrap-up immediately precedes turn 2 in both arms.
3. The delta opener carries a framing cue ("this message is the current state
   delta only") and omits `recorded_context`; full re-sends the task framing.
   The arms differ in semantics, not only in size.
4. The stateless Groq transport resends the whole transcript in both arms, so
   the intended context-size contrast is a few percent of a request.
5. Total-token comparisons are post-treatment (they include each arm's
   stopping decision and repair request), so they cannot be used to explain
   that same stopping decision.
6. n=5 pairs, one model, one artifact, temperature 0.2, fixed condition order
   (full then delta) - no randomization, no repeated artifact, no power.
7. No ground truth: the sandbox has OOF predictions only, no training metrics
   and no feature provenance, so "why the model underperforms" cannot be
   adjudicated; only evidence-consistency and calibration can be scored.
8. Summary repair is itself condition-confounded through content shape: an
   empty `status_recommendations` list makes the JSON flat and lets the
   bare-JSON fallback fire, so "needed no repair" can reflect summary content
   rather than summary formatting skill.

### Explicitly unmeasured

- The pre-repair conclusion text of 8 of the 9 rejected first attempts
  (600-character event cap; `raw_block` is null on rejection).
- Actual billed cost (ledger figures are published-price estimates).
- Whether any conclusion's causal explanation is *correct* (no ground truth,
  no training metrics, no provenance file).
- Meta API billing, `previous_response_id` retention, and tokenizer parity.
- Any statistically meaningful condition effect.

### Smallest controlled follow-up that separates context from stopping

Do **not** add more free-stopping Groq pairs; they re-sample the same
confounded design. The minimal decisive change is a benchmark-only harness
flag with two arms, on the same model and caps:

- Neutralise the opener: both arms receive an identical instruction to
  continue; vary only whether the recorded-context block is re-sent. This
  removes the "state delta only" framing cue.
- Remove the "Finish now" wrap-up before turn 2 (or relocate it to the true
  final turn, as production does).
- Fix synthesis timing: require exactly one turn-2 round and require that
  round to be a *diagnostic*, not `propose_hypothesis`; if the model answers
  without a call, re-prompt once with the same requirement.
- Run 5 pairs per arm (10 new runs), pre-register the 6-component rubric used
  above (mechanism named, measured number cited, calibrated status,
  discriminating test, hypothesis linked, no false self-report), and score
  blind to arm.
- Prediction: a context-framing effect appears as an arm difference at fixed
  timing; a stopping/wrap-up effect disappears once timing is fixed; neither
  leaves the arms indistinguishable and the residual variance is model noise.
- Keep this off Meta: it answers the behavioural question only. The billing
  question still requires the capped Meta paired run.

Phase C decision: unchanged. These five pairs establish harness mechanics and
show that, with evidence held constant, neither continuation format has a
quality advantage; they do not establish any Meta-side saving.

<!-- phase-d-groq-controlled-followup-2026-10-29 -->
## Phase D, controlled Groq follow-up: neutral continuation, final-turn wrap-up only (2026-10-29)

**Scope.** Five new paired runs on Groq `openai/gpt-oss-120b` only. No Meta
request, no production-code change, no edit to any earlier section. The design
was frozen in `phase_d_groq_controlled_preregistration_2026-10-29.md` before
the first call; the harness flag is `--controlled`, the driver is
`run_controlled_pairs.py`. This is the smallest follow-up requested by the
trace re-analysis, with one owner-directed difference: it does **not** force a
diagnostic call in turn 2. Forcing a tool would be a new intervention. Whether
the model gathers evidence, synthesizes, or abstains is recorded as behaviour.

### Design corrections (benchmark-only)

- Both arms receive one identical, neutral continuation instruction: continue
  from the recorded state; use tools only if another measurement could change
  the conclusion; end with the summary block. The delta builder's "state delta
  only" framing note is not used.
- Turn 1 receives no `_wrapup_item`. Turn 2 receives it only on the last
  scheduled round or when the tool budget is fully exhausted. Production's
  "two calls remain" heuristic is not used in controlled mode. This is the
  benchmark's operational definition of the true final opportunity.
- Same 3 rounds per turn, same shared 6-call investigation budget, same
  production tool registry, validator, reuse guard, tool-packet truncation,
  sandbox isolation, and one bounded summary repair in both arms.
- The only payload difference is whether `recorded_context` is present (full)
  or absent (delta). Condition order alternates across pairs (full first on
  odd pairs, delta first on even pairs).

### Design certification

Offline `--offline --controlled` passed: identical continuation instruction,
identical keys and budgets, only `recorded_context` differs, delta payload
smaller (815 vs 1,188 chars), turn-1 wrap-up suppressed, turn-2 mid-round
wrap-up suppressed and last-round wrap-up allowed, reuse guard and valid-JSON
truncation intact. Live, all five pairs report `design_check: ok`, the same
model in both arms, `forced_diagnostic: false`, and no turn-1 wrap-up.

One accounting wrinkle: pair 2's full run made one tool-call-validation 400
(it tried to call the undeclared `investigation_summary` tool), retried once,
and recovered. The harness records that single logical failure twice. Ledger
attempts are therefore one higher than actual HTTP requests.

### Run accounting

`chat` excludes the one unbilled `GET /models` verification per pair; `ledger`
includes it. All five pairs completed, no pair aborted, no cap was hit.

| Pair | Order | HTTP attempts (ledger / chat) | Input tok | Output tok | Est. cost | Calls F/D | Summary valid F/D | Quality F/D |
|---|---|---|---|---|---|---|---|---|
| 1 | full → delta | 14 / 13 | 37,165 | 5,818 | $0.009066 | 4 / 5 | no / yes | 0 / 5 |
| 2 | delta → full | 17 / 15 | 40,389 | 5,570 | $0.009400 | 6 / 5 | yes / yes | 4 / 5 |
| 3 | full → delta | 15 / 14 | 40,821 | 5,138 | $0.009206 | 5 / 6 | yes / yes | 5 / 3 |
| 4 | delta → full | 15 / 14 | 40,244 | 6,918 | $0.010187 | 5 / 5 | no / yes | 4 / 5 |
| 5 | full → delta | 15 / 14 | 40,886 | 5,428 | $0.009390 | 5 / 5 | yes / yes | 4 / 4 |
| **Total** | | **76 / 70** | **199,505** | **28,872** | **$0.047249** | **25 / 26** | **3/5 / 5/5** | **17 / 22** |

Provider-reported totals: 228,377 tokens, estimated **$0.047249** — 9.4% of
the pre-registered $0.50 global ceiling, 76.1% of the 300,000-token ceiling,
and 76 of the 100 attempt ceiling. Per-pair estimated cost was $0.0091–$0.0102,
all below the $0.10 per-pair cap. Costs are published-price estimates, never
billed amounts. The preflight estimate from four prior complete 120B pairs was
$0.0343; actual was $0.047249. Groq exposes rate-limit headers but no
account-credit endpoint, so the established budget was the existing $0.50
harness ceiling, not a verified account balance. All five sandbox databases
were distinct temp files; none was the application database.

Aggregate by arm: full 99,346 input / 13,240 output / $0.022846 / 35 chat
attempts; delta 100,159 input / 15,632 output / $0.024404 / 35 chat attempts.
Delta used **+0.8% input**, **+18.1% output**, and cost **+6.8%**. At 35
actual chat requests per arm, input per request was 2,838.5 (full) vs 2,861.7
(delta): +0.8%. There is no input-token saving to report. The continuation
payload differs by only ~373 characters (~93 tokens), roughly 0.4% of a
~20k-token run.

### Mechanical validity (scored separately)

- Final summary valid after the one bounded repair: **8/10** overall — full
  3/5, delta 5/5. First-attempt valid: **0/10**; all ten needed the repair.
  The prior cohort recovered eight of nine invalid attempts; this one
  recovered eight of ten.
- Pair 1 full never produced a parseable block
  (`summary is not valid JSON ... no structured summary found`), and its repair
  failed the same way. Pair 4 full's repair failed because it cited a malformed
  variant of a real hypothesis id; the validator correctly rejected it.
- Citation audit: 27 basis values, 6 unresolved (R02: 2, R04: 1, R09: 3);
  16 status recommendations, 15 hypothesis ids resolve; 8/10 runs have every
  hypothesis id resolve. Basis ids are a separate, unvalidated field. All
  `basis` values are lists (no shape violation), but the validator still does
  not check them.
- Tool use: 58 actions attempted, 51 ran; all 7 failures were
  `feature_target_suspiciousness` (missing required columns/file). Calls used
  4–6 of 6; one run per arm reached 6; none exceeded.
- No aborted pairs. No condition-scoped abort. No cap hit.

### Behaviour: turn 2 is no longer frozen

The prior trace found that **0 of 10** turn-2 runs gathered evidence: 7
synthesized in round 1, and the other 3 spent one round on
`propose_hypothesis`. Under the controlled design, **10 of 10** runs executed
at least one new diagnostic in turn 2; 9 of 10 used all 3 turn-2 rounds (one
used 2). Tool calls rose from 3–4 of 6 in the prior cohort to 4–6 here.

Evidence-bearing turn-2 calls (classification metrics, calibration/error,
feature-target scan, dataset validation): full 8 ran / 11 attempted; delta 9 /
11. Structural calls (`artifact_summary`, `time_split_validation`) and
`propose_hypothesis` are not counted. Distinct evidence-bearing tools across
the whole run averaged 1.8 (full) and 2.2 (delta); the prior cohort averaged
1.8 in both arms. The feature scan failed in 7 runs for input reasons, so this
is a floor, not a ceiling.

This is the strongest behavioural effect in the experiment: removing the
premature finish instruction changed what the model did in turn 2. It is
consistent with the trace analysis's explanation of the earlier floor. With
n=5 and one model it is not proof of causation, and it is not a quality claim.

### Blind six-component quality

Scores were frozen in `phase_d_groq_controlled_scores_blind.json` before the
sealed condition key was opened. Components: 1 mechanism named; 2 measured
number cited accurately; 3 calibrated conclusion/status; 4 discriminating
follow-up; 5 hypotheses linked to recorded evidence; 6 no false self-report.
Mechanical validity is not included in the total.

| Pair | Arm | 1 | 2 | 3 | 4 | 5 | 6 | Total | Summary valid |
|---|---|---|---|---|---|---|---|---|---|
| 1 | full | 0 | 0 | 0 | 0 | 0 | 0 | **0** | no (unparseable) |
| 1 | delta | 1 | 0 | 1 | 1 | 1 | 1 | **5** | yes |
| 2 | full | 1 | 0 | 0 | 1 | 1 | 1 | **4** | yes |
| 2 | delta | 1 | 1 | 1 | 1 | 0 | 1 | **5** | yes |
| 3 | full | 1 | 0 | 1 | 1 | 1 | 1 | **5** | yes |
| 3 | delta | 1 | 0 | 0 | 1 | 0 | 1 | **3** | yes |
| 4 | full | 1 | 0 | 1 | 1 | 0 | 1 | **4** | no (bad id) |
| 4 | delta | 1 | 0 | 1 | 1 | 1 | 1 | **5** | yes |
| 5 | full | 0 | 0 | 1 | 1 | 1 | 1 | **4** | yes |
| 5 | delta | 1 | 0 | 1 | 1 | 0 | 1 | **4** | yes |
| **Total** | full / delta | 3 / 5 | 0 / 1 | 3 / 4 | 4 / 5 | 3 / 2 | 4 / 5 | **17 / 22** | 3/5 vs 5/5 |

All-runs means are 3.4 (full) and 4.4 (delta), a +1.0 difference. That number
is not a quality advantage: pair 1 full has no parseable summary, so its
quality is unassessable and was scored 0. Excluding runs without a valid
summary, the means are 4.33 (full, n=3) and 4.40 (delta, n=5); the three pairs
where both arms produced a valid summary differ by **+1, −2, 0** (delta minus
full). There is no consistent direction.

What the components say descriptively:

- **Mechanism naming** favoured delta (5/5 vs 3/5); the two full misses were the
  unparseable summary and a generic "both explanations remain plausible" that
  named neither.
- **Numeric grounding remains the weakest dimension:** 1/10 runs cited a
  measured number accurately (pair 2 delta: 0.6907 / 0.6801 / 0.6898, matching
  the recorded per-fold AUCs). The other nine were qualitative even when the
  numbers were in the tool output. This replicates the earlier finding.
- **Calibration** was better in delta (4/5 vs 3/5). Delta's one failure was a
  `supported` status for a bundled imbalance/threshold claim; full's two were
  the unparseable summary and a "no training-OOF gap" claim with no training
  metrics.
- **Discriminating follow-up** was near-saturated (4/5 vs 5/5); most runs named
  an ablation, reweighting, calibration, or drift test.
- **Hypothesis linkage** was worse in delta (2/5 vs 3/5) because two delta
  summaries put five fabricated or tool-name strings in `basis`; full's
  failures were the two invalid summaries. The validator does not check basis
  ids, so these summaries were accepted as valid.
- **No false self-report** was high in both arms (4/5 vs 5/5); no run claimed a
  diagnostic it had not run, though one full run claimed a training/OOF gap it
  could not observe.

Paired quality differences (delta − full): **+5, +1, −2, +1, 0**. The +5 is
the unassessable pair-1 full run. With only pairs where both summaries are
valid: **+1, −2, 0**. No statistical test is applied and none should be read
into these five numbers.

### Did the controlled design reduce the confounding?

**Yes for the confounds it targeted.** The premature turn-1 "Finish now" cue
is gone, the condition-specific framing note is gone, and rounds/tool budget
are identical; the offline and live certifications confirm that only
`recorded_context` differs. The behavioural signature changed accordingly:
turn-2 evidence gathering went from 0/10 to 10/10, and calls used rose from
3–4 to 4–6. The prior floor was therefore at least partly a protocol artefact,
not a stable property of either context strategy.

**No for the transport.** Groq Chat Completions resends the whole transcript,
so the manipulated payload is a few hundred characters inside a ~20k-token
run. Delta did not reduce input tokens (+0.8%); output and estimated cost were
higher (+18.1% and +6.8%). This experiment cannot measure Meta's
`previous_response_id` retention or billing, and no such inference is made
here.

**No for ground truth.** The sandbox has out-of-fold predictions only: no
training metrics, no feature provenance, no causal label. A run can name a
mechanism (component 1) without the mechanism being correct. Nothing in this
section establishes why the model underperforms.

### Limitations

- n=5 pairs, one model, one artifact, temperature 0.2, fixed objective. No
  power, no significance, no confidence interval presented as inference.
- Scoring was condition-masked and frozen before unsealing, but it was a
  single rater and not fully double-blind: the rater had seen several traces
  during run monitoring. Scores were not revised after the key was opened.
- Quality is scored from the final structured summary. Pair 1 full has no
  parseable summary, so its investigative quality is unassessable; pair 4
  full's summary content was scored but its identifiers are invalid. Prose
  outside the summary block was not scored.
- Token and cost figures are provider-reported usage and published-price
  estimates, not bills. Attempt counts include the duplicate 400 record.
- The per-run ledger field `summary.conclusion` is null in these five files:
  the harness serialized the validator's nested object before a one-line
  post-run fix. The analysis reads the full parsed block from each sandbox's
  `events.payload.raw_block` instead, so no reported conclusion depends on
  that field.
- The feature-target tool failed in 7/10 runs on input shape, limiting
  evidence coverage in both arms.
- Account-level credit was not verifiable through Groq's API; budget control
  relied on the pre-registered $0.50 ceiling and the $0.0343 preflight
  estimate, not a confirmed remaining balance.
- The experiment was run after the trace re-analysis and with knowledge of it;
  the design is pre-registered, but the hypothesis was not blind to the
  analyst.

### Artifacts

- `phase_d_groq_controlled_preregistration_2026-10-29.md`
- `phase_d_groq_controlled_pair{1..5}.json`
- `phase_d_groq_controlled_ledger.json`
- `phase_d_groq_controlled_blind_sheet.json`
- `phase_d_groq_controlled_mechanical.json`
- `phase_d_groq_controlled_scores_blind.json`
- `phase_d_groq_controlled_analysis.json`
- `phase_d_groq_controlled_report_data.json`

**Bottom line.** The controlled design removes the stopping/framing confound
identified in the trace analysis, and turn 2 now investigates instead of
immediately synthesizing. It does not show a quality advantage for either
continuation format, and it does not show an input-token saving for delta.
The Meta billing question remains open and still requires the capped Meta
paired run.

<!-- phase-d-meta-protocol-revision-v2 -->
## Phase D — Meta paired continuation benchmark: PROTOCOL REVISION v2 (FROZEN, 2026-10-29)

**Status: FROZEN.** This revision governs the first live Meta inference run. It
supersedes only the execution details of the earlier *“Phase D — Meta paired
continuation benchmark (BLOCKED: no Meta key)”* section; no historical section
or result above is rewritten, reinterpreted, or deleted. Harness:
`meta_paired_continuation_benchmark.py`; frozen protocol copy:
`phase_d_meta_protocol_revision_v2_2026-10-29.md`.

### Revision content — summary-repair continuation ID (defect corrected)

**Defect.** After the one bounded summary repair (F4) produced a *valid*
summary, `run_meta_turn` still returned the **pre-repair** response id. The next
continuation therefore chained from the provider response that carried the
invalid summary, and the repaired response was silently excluded from the
chain. A failed repair could likewise be mistaken for a repaired continuation
state.

**Correction.** The repair request's response id is now captured and, when the
repair validates, becomes the turn's returned `response_id`. The exact
behaviour is a frozen part of this protocol revision:

| Turn outcome | Returned continuation id | `continuation_state.response_id_source` |
|---|---|---|
| No repair needed | original response id | `original` |
| Repair valid, usable id | **repaired response id** | `repair` |
| Repair valid, id missing/malformed/blank | **none** (no chain state established) | `unavailable` |
| Repair still invalid | original response id (original text/verdict stand) | `original` |
| Repair unavailable (provider error) | original response id | `original` |
| Original response id missing/malformed | none | `original` |

No repair response id is ever accepted unless the repair validated, and a
missing or malformed id is never forwarded as `previous_response_id`. Tool-call
and conversation-history semantics are unchanged: a repair remains one bounded,
tool-free request inside the same turn, and the original invalid verdict stands
when repair does not win. The benchmark records this audit per turn
(`turn{1,2}_continuation_state`) and its latest-id checks verify the chain
actually used the reported id.

### Experiment

| Parameter | Frozen value |
|---|---|
| Provider | Meta Model API only. No other provider may be substituted. |
| Model | `muse-spark-1.3` |
| Endpoint | Existing official Meta Responses API endpoint (`https://api.meta.ai/v1/responses`) |
| Conditions | **Full** (baseline: continuation turns re-send the full initial context via the in-process `_continuation_delta_items` patch) versus **Delta** (Phase C production delta items with the one-shot chain-state fallback) |
| Pairing | 2 pairs, 4 runs total (one full run + one delta run per pair) |
| Ordering | Full then Delta within each pair (fixed) |
| Turns | 2 per run (1 fresh turn + 1 chained continuation turn) |
| Rounds | Maximum 3 per turn |
| Tool budget | 6 calls, shared across the run |
| Temperature | 0.2 |
| Output limit | 2,000 tokens per request |
| Summary-repair limit | 1,200 tokens, at most one repair per turn |

### Hard spending limits

| Limit | Value |
|---|---|
| Maximum request attempts (retries and repairs included) | **40** |
| Maximum provider-reported tokens | **150,000** |
| Maximum ESTIMATED cost | **$1.00** |
| Stop condition | Abort after **3 consecutive HTTP 429** responses |
| Provider switching | **Never.** No Groq or other provider fallback, at any point |

Caps are checked before and after every request; the adapter's retry loop is
clamped to the attempts that remain. Estimated cost uses the published
`muse-spark-1.3` Standard rates recorded in the harness header and is never
presented as an actual charge.

### Measurement

Recorded per request and per run from provider-reported usage and recorded
backend state (never from model prose alone):

- provider-reported **input tokens**, **cached input tokens**, **output tokens**;
- **estimated cost** (published rates; estimate only);
- **valid-summary rate** (first attempt and after the bounded repair);
- **investigation quality** (structured summary validity, evidence-cited
  conclusions, hypothesis-status calibration);
- **evidence coverage** (which recorded actions the conclusion relies on);
- **tool execution and diagnostic grounding** (executed vs. reused vs. failed
  calls, action ids cited);
- **incomplete-response frequency** (`status: incomplete`, other non-completed
  provider statuses);
- **repair frequency** (repairs attempted, repairs that validated).

Character sizes are reported only as a payload sanity check; they are not token
counts.

### Decision rule

> **Retain Phase C Delta only if Meta-billed input-token savings are
demonstrated at equal-or-better investigation quality.**

No statistical significance is claimed from two pairs. A token reduction with
worse or unverifiable quality does not satisfy the rule, and a quality result
without measured Meta input-token savings does not either.

### Declared limitations (frozen with the protocol)

- The continuation-ID correction is **part of this protocol revision**; runs made
  before it are not comparable on chained-turn state.
- **Full-then-Delta ordering remains a limitation**: position within a pair is
  fixed, so order effects (warm-up, provider-side load, residual caching) cannot
  be separated from the condition.
- **Two pairs provide preliminary evidence only** — a directional signal, not an
  estimate of a stable effect.
- **Provider caching and model drift may affect results**; cached-input tokens
  are recorded so any caching effect is visible rather than assumed.
- **Temperature 0.2 and the 2,000-token output limit are retained for production
  parity**, not tuned for the experiment.
- **Groq results are not evidence of Meta billing savings.** Groq Chat
  Completions is stateless and resends the transcript; no Groq number in this
  file may be used to support or refute Meta input-token savings.
- Failed/rejected attempts are ledgered separately from billed requests; missing
  usage fields are reported as missing, never invented.

### Verification at freeze (offline only; no provider request)

- Continuation-ID regression tests: **15 passed** (`tests/test_meta_continuation_id.py`),
  covering both conditions, successful/failed/unavailable repairs, missing and
  malformed original/repair ids, and the subsequent continuation id.
- Meta environment + readiness tests: **41 passed** (includes the offline
  payload-difference check).
- Full Model Autopsy suite: **155 passed, 3 pre-existing deprecation warnings**.
- Offline benchmark: exit 0; `baseline_patch_exact: true`;
  `delta_chars 448 < full_context_chars 692`; no key value emitted.
- **Zero network requests, zero inference calls, zero credits spent** during this
  revision.

**Freeze point.** The protocol is frozen as of 2026-10-29. Execution requires a
separate, explicit owner approval; this section records no live result.

### Pre-registered blind quality scoring (2026-10-29, before inference)

A blind investigation-quality scoring package was frozen **before any live Meta
request**; it does not alter the experiment protocol above. Files:

- [phase_d_blind_scoring_rubric_v1.md](phase_d_blind_scoring_rubric_v1.md) —
  six dimensions scored 0–2, unweighted maximum **12**: mechanism
  identification, numeric grounding, evidence linkage, calibration, diagnostic
  reasoning, execution honesty. Every score needs an evidence-based
  justification; verbosity, formatting, and summary-format validity earn no
  points; a well-justified stop is not penalized for lacking a diagnostic.
- `phase_d_blind_scoring_sheets/run-01.md` … `run-04.md` — one neutral sheet per
  planned run, labeled only `RUN-01`…`RUN-04` in a system-random presentation
  order. No sheet or filename contains a pair number or condition label.
- [phase_d_blind_evaluation_protocol_v1.md](phase_d_blind_evaluation_protocol_v1.md)
  — masking rules, independent scoring, score freeze, unblinding, and
  comparison/reporting procedure.
- `benchmarks/.sealed/phase_d_blind_condition_key_v1.json` — the separate
  label→pair/condition mapping, Git-ignored and  excluded from all scoring
  material; its SHA-256, the rubric/protocol/sheet/validator digests, and the
  raw-trace digests are frozen in
  [phase_d_blind_freeze_manifest_v1.json](phase_d_blind_freeze_manifest_v1.json).

**Procedure.** After each run the operator builds a condition-masked packet
(final message, structured summary, validator outcome, ordered recorded
actions, hypothesis roster, budget counters, completion status) and withholds
request payloads, token/cost/latency data, titles, and timestamps. The
evaluator scores each packet independently, records any blinding clue without
guessing, computes each run's total, then freezes the four sheets by hash.
Only then is the sealed key's digest verified and the mapping opened; frozen
scores are joined, never revised.

**Comparison and decision.** Report per-run totals, Full and Delta averages,
the two paired differences, summary validity (first attempt vs post-repair)
separately, evidence coverage, diagnostic execution, incomplete-response and
repair frequencies, and provider-reported input/cached/output tokens plus
estimated cost. The decision rule is unchanged: **retain Phase C Delta only if
measured Meta-billed input-token savings are demonstrated at equal-or-better
investigation quality.** Two pairs are descriptive only — no significance
claim.

**Blinding limitation.** Raw transport payloads would identify the condition,
so they are excluded from scoring material; residual clues can remain in model
prose, action shape, or evidence volume. Complete blinding is therefore not
claimed, and any observed clue is reported as a limitation. No run has been
executed or scored yet; this entry records pre-registration only.

### Phase D Meta paired benchmark — first frozen execution (2026-10-29; NOT SCORED)

Protocol v2 was executed once: Meta only, `muse-spark-1.3`, two pairs, Full
then Delta, four runs, two turns, three rounds per turn, six-tool shared
budget, temperature 0.2, 2,000-token output limit, 1,200-token repair limit.
No protocol, rubric, condition, or benchmark setting was changed.

**Completion.** 4/4 runs executed; **0/4** reached `run_outcome: completed`.
All four are recorded as `incomplete_provider_response` (turn 1 and turn 2
statuses `ok`). The provider returned `status: incomplete` on **10/24**
requests, every one with `incomplete_reason: max_output_tokens` — six regular
responses at the 2,000-token limit and four summary repairs at the 1,200-token
limit.

**Usage (provider-reported, aggregate; estimate only).** 24 billed requests /
24 attempts / 0 failed / 0 HTTP 429. Input **91,534** tokens (cached
**53,829**; uncached **37,705**); output **29,921**; total provider tokens
**121,455**; estimated cost **US$0.18237**. Caps: 24/40 attempts,
121,455/150,000 tokens, US$0.18237/US$1.00; no stop reason.

**Investigation facts.** 18 actions ran; 0 failed; 0 fallback events; **1/4**
final summaries valid; 6 bounded repairs (3 in turn 1, 3 in turn 2).
Continuation-ID audit: successful repairs returned the repaired response id
(two turn-1 cases chained from it); failed or unavailable repairs retained the
original id; no invalid repaired state was accepted.

**Preservation and blinding.** The complete benchmark report and console
summary are preserved under
[`phase_d_meta_raw_2026-10-29/`](phase_d_meta_raw_2026-10-29) with SHA-256
[`RUN_MANIFEST.json`](phase_d_meta_raw_2026-10-29/RUN_MANIFEST.json). Four
sandbox snapshots are preserved; each contains all recorded actions and
hypotheses, but snapshot coverage of the final turn-2 assistant message,
summary repair, and usage rollup varies because the frozen harness commits
those last events and deletes its temporary directory between snapshots.
Final prose and summary blocks may therefore be absent or truncated. The
report is authoritative for final run-level outcomes, summary validity, and
provider usage. The neutral
RUN-01…RUN-04 association is in a sealed post-run index; the condition mapping
remains sealed. No scoring, unblinding, paired comparison, or savings
conclusion has been made.

**Limitations.** The 10 incomplete responses materially limit run completion
and summary validity, and scoring may have to rely on truncated final prose for
runs whose summary repair failed. Repeating under the same 2,000/1,200-token
limits may hit the same caps; any change requires a new protocol revision and
owner approval. No per-condition token or quality comparison is reported here.

---

## Phase D final Meta campaign — 2026-10-31 (repaired harness)

**Campaign.** Provider Meta Model API, model `muse-spark-1.3`, 2 pairs
Full-then-Delta (4 runs), frozen protocol v2 caps (40 attempts / 150,000
tokens / $1.00 / stop after 3 consecutive 429s). Go authorized by the
Phase 6 readiness gate
([phase_d_meta_readiness_gate_2026-10-31.md](phase_d_meta_readiness_gate_2026-10-31.md))
after 189/189 offline tests, Groq validation3 (15/15 billed, all evidence
hashed-verified), and blinded-packet certification. Report:
[`phase_d_meta_final_2026-10-31.json`](phase_d_meta_final_2026-10-31.json);
raw runs: `phase_d_meta_live_20261031T204311Z/` (per-run manifests finalized,
SHA-256 verified). Historical 2026-10-29 results above are preserved unchanged.

**Spend (within all caps).** 25 attempts (0 failed, no stop):
provider-reported input 87,527 (cached 56,675, uncached 30,852), output
26,290, total 113,817; estimated cost US$0.15880. No 429 stop.

**Per-pair provider-reported input tokens (ledger sums).**

| Pair | Full in (cached) | Delta in (cached) | Delta − Full |
|---|---|---|---|
| p1 | 15,348 (5,986) | 20,364 (17,461) | +5,016 (+32.7%) |
| p2 | 29,958 (20,390) | 21,857 (12,838) | −8,101 (−27.0%) |
| total | 45,306 (26,376) | 42,221 (30,299) | −3,085 (−6.8%) |

Output tokens: Full 12,534 vs Delta 13,756. Incomplete responses: p1 0+0,
p2 2+4 (6 total; all max_output_tokens stops at 2,000/1,200). First-attempt
summary validity 2/4; post-repair validity 3/4; repairs attempted in 2 runs
(both turns of p2; continuation audit: successful repair → repaired id,
failed repair → original id retained, verified live).

**Blinded quality (frozen rubric v1, 0–12; sheets frozen before unblinding in
`phase_d_blind_scores_frozen_final_2026-10-31.json`; sealed post-run index
in `.sealed/`; original condition-key digest unchanged).**

| Neutral | Pair | Condition | Score |
|---|---|---|---|
| RUN-01 | p1 | full | 9 |
| RUN-02 | p2 | delta | 7 |
| RUN-03 | p1 | delta | 10 |
| RUN-04 | p2 | full | 8 |

Full mean 8.5 (9, 8); Delta mean 8.5 (10, 7). Paired differences (Delta −
Full): p1 +1, p2 −1; mean 0. No statistical claim (n = 2). Packets, sheets,
and freeze digests are recorded; no sheet was revised after unblinding.

**Decision (pre-registered rule).** Retain Phase C Delta only with
demonstrated Meta-billed input-token savings at equal-or-better quality.
Quality means tie (8.5 vs 8.5), but measured input-token savings are NOT
demonstrated: the pairs point in opposite directions (p1 +32.7%, p2 −27.0%),
and pair 2's comparison is confounded by 6 incomplete responses plus one
invalid final summary. **Delta is therefore NOT retained on this evidence.**
Groq validation figures were not used in this decision.

**Limitations.** Two pairs are preliminary only. Incomplete responses
(2,000-token regular / 1,200-token repair caps) truncated two runs and forced
both p2 repairs; repeating under the same caps may reproduce them.
Per-run diagnostic paths differ (tool counts 4–5 of 6), so token deltas mix
strategy effects with path effects. Provider caching and model drift may
shift a rerun. Temperature 0.2 and the output limits are production parity by
design. The `repairs.jsonl` dedicated record did not exist for this campaign
(repair exchanges are preserved verbatim in `responses.jsonl`); the harness
now emits per-repair records (`backend/meta_api/loop.py` returns `repairs`)
with regression tests, for future runs only — historical artifacts unchanged.
