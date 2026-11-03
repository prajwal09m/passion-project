# M21 Live Validation Proposal — Reporting Reliability (Preparation Only)

No authorization is requested by writing this document. No paid calls
or live investigations have been made. This proposal awaits explicit
approval; M21 implementation stops here.

## 1. Recommended scenario

`eval_music` (music_rank artifact) — the same scenario as M19. Rationale:
only scenario with a recorded baseline for the exact failure being
validated (model returned prose twice, repair returned prose, fallback
carried the report); fixture-backed offline coverage already encodes
its shapes (S2/S6/S9); scorer, truth, and budget envelopes are known.

## 2. Run envelope (hard caps, shared budget)

- Investigations: exactly **1**. Rounds: max **3**. Actual experiments:
  max **6** (verification hold honored). Provider attempts: max **12**.
- Tokens: **50,000** ceiling. Spend: **$0.65** ceiling (same as M19).
- Retry policy: at most one full-context fallback per turn; at most
  one summary repair per turn; no recursion, no manual retries.
- These caps are enforced by the live governor/allocator, not by
  operator discipline.

## 3. Stop conditions (stop after the single investigation regardless)

- Budget headroom refusal, `meta_unavailable` honest stop, or two
  consecutive evidence-less turns (existing stopping rules).
- Any provider-side incident: record, fall back or stop, never retry
  outside the envelope.
- No second runs, no additional scenarios, no chasing a cleaner story.

## 4. Expected outputs and artifacts

- `live_runs/m21-music-01/`: launch log, manifest (budget ledger,
  token usage, financials), `events_dump.json` (summary class,
  eligibility, repair attempts with raw text, consistency results,
  fallback selection, verification/resolution events),
  `assistant_messages.jsonl` (raw provider text), scorecard.
- No new benchmark campaigns; no scorer/fixture/sealed changes.

## 5. Objective success criteria (read from recorded artifacts)

1. Provenance unambiguous: exactly one of `model_native` /
   `model_repaired` / `deterministic_fallback` in `report_provenance`.
2. Every scientific claim traces to a ran action or recorded event;
   zero §2.10 protocol violations at final state.
3. Native consistency advisory (if any) visible in the causal view;
   final-state adapter consistency recorded.
4. Budgets respected; any refusal recorded with `attempt_spent:false`
   where pre-dispatch.
5. Verification handled honestly: confirmed only under a `confirmed`
   contract, else preserved unresolved with reason.

## 6. Inconclusive conditions (not failures)

- Verification budget refused → finding preserved unresolved (honest,
  per §2.8 of the protocol).
- Transport failures force fallback with no model content to
  evaluate → reporting pipeline validated only through S6/S7.
- Model returns valid-but-unverifiable prose → advisory recorded,
  report inconclusive, never upgraded.

## 7. Failure conditions

- Any unsupported confirmation/verification/measurement reaching the
  final report; silently dropped evidence; ambiguous provenance; spend
  or attempt overrun; any write to frozen artifacts, scorers, sealed
  truth, or Demand Zone AI.

## 8. Cost projection

M19's allocation simulation projected ≤ $0.1172 typical against the
$0.65 ceiling for this envelope; M21 adds ~440 tokens/round of
reporting contract plus at most one repair dispatch (~1200-token cap).
Expected actual: at or below the M19 run. The ceiling, not the
projection, is the binding constraint.
