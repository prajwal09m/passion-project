# Phase D — Meta paired continuation benchmark: Protocol Revision v2 (FROZEN)

**Frozen: 2026-10-29.** Status: FROZEN; supersedes only the execution details of
the earlier "Phase D — Meta paired continuation benchmark (BLOCKED: no Meta
key)" section in [RESULTS.md](RESULTS.md). No historical result is rewritten or
deleted. Harness: [meta_paired_continuation_benchmark.py](meta_paired_continuation_benchmark.py).

## What this revision changes

The summary-repair continuation-ID defect is corrected and becomes part of the
frozen protocol:

- **Defect:** when the one bounded summary repair (F4) produced a valid summary,
  `run_meta_turn` returned the PRE-repair response id, so the next continuation
  chained from the response carrying the invalid summary and excluded the
  repair.
- **Correction:** the repair response's own id is captured; on a valid repair it
  is the returned `response_id`. Without a repair, or after a repair that did not
  win, the original id is returned unchanged. A repair that wins but has no
  usable id yields no continuation id and is labelled `unavailable`.

| Turn outcome | Returned continuation id | `continuation_state.response_id_source` |
|---|---|---|
| No repair needed | original response id | `original` |
| Repair valid, usable id | **repaired response id** | `repair` |
| Repair valid, id missing/malformed/blank | **none** (no chain established) | `unavailable` |
| Repair still invalid | original id (original verdict/text stand) | `original` |
| Repair unavailable (provider error) | original id | `original` |
| Original response id missing/malformed | none | `original` |

A repair is still exactly one bounded, tool-free request inside the same turn;
the tool budget and conversation-history semantics are unchanged.

## Experiment

| Parameter | Frozen value |
|---|---|
| Provider | Meta Model API only; no other provider may be substituted |
| Model | `muse-spark-1.3` |
| Endpoint | Existing official Meta Responses API endpoint (`https://api.meta.ai/v1/responses`) |
| Conditions | **Full** (continuation re-sends the full initial context via the in-process patch) vs **Delta** (Phase C production delta items + one-shot chain-state fallback) |
| Pairing | 2 pairs, 4 runs total |
| Ordering | Full then Delta within each pair (fixed) |
| Turns | 2 per run (1 fresh + 1 chained) |
| Rounds | Maximum 3 per turn |
| Tool budget | 6 calls, shared across the run |
| Temperature | 0.2 |
| Output limit | 2,000 tokens per request |
| Summary-repair limit | 1,200 tokens, at most one repair per turn |

Identical on both sides: model, objective, artifact, tool definitions,
instructions, limits, and the shared tool budget.

## Hard spending limits

| Limit | Value |
|---|---|
| Maximum request attempts (retries and repairs included) | **40** |
| Maximum provider-reported tokens | **150,000** |
| Maximum ESTIMATED cost | **$1.00** |
| Stop condition | Abort after **3 consecutive HTTP 429** responses |
| Provider switching | **Never** — no Groq or other provider fallback |

Caps are enforced before and after every request; the adapter's retry loop is
clamped to the attempts that remain. Cost is an estimate from the published
`muse-spark-1.3` Standard rates in the harness header, never an actual charge.

## Measurement

- Provider-reported input tokens, cached input tokens, output tokens.
- Estimated cost (published rates; estimate only).
- Valid-summary rate (first attempt and after repair).
- Investigation quality (summary validity, evidence-cited conclusions,
  hypothesis-status calibration).
- Evidence coverage (recorded actions the conclusion relies on).
- Tool execution and diagnostic grounding (executed/reused/failed, cited ids).
- Incomplete-response frequency (provider `incomplete` / non-completed statuses).
- Repair frequency (attempted, validated).

## Decision rule

> **Retain Phase C Delta only if Meta-billed input-token savings are demonstrated
> at equal-or-better investigation quality.**

No statistical significance is claimed from two pairs.

## Declared limitations

- The continuation-ID correction is part of this revision; pre-revision runs are
  not comparable on chained-turn state.
- Full-then-Delta ordering is fixed, so order effects cannot be separated.
- Two pairs provide preliminary evidence only.
- Provider caching and model drift may affect results.
- Temperature 0.2 and the 2,000-token output limit are retained for production
  parity.
- Groq results are not evidence of Meta billing savings.
- Failed attempts are ledgered separately from billed requests; missing usage is
  reported as missing, never invented.

## Verification at freeze (offline; no provider request)

- Continuation-ID regression tests: 15 passed (both conditions, successful /
  failed / unavailable repairs, missing and malformed ids, subsequent chain id).
- Meta environment + readiness tests: 41 passed (incl. payload-difference check).
- Full Model Autopsy suite: 155 passed, 3 pre-existing deprecation warnings.
- Offline benchmark: exit 0; `baseline_patch_exact: true`;
  `delta_chars 448 < full_context_chars 692`; no key value emitted.

**Freeze point.** Execution requires separate, explicit owner approval. This
document records no live result.
