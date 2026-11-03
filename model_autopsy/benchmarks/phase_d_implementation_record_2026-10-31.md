# Phase 2 implementation record — R1–R6 (2026-10-31, offline, no provider contact)

## Starting state
Phase 2 core work already existed on disk (`bench_persistence.py` with
incremental JSONL + fsync, investigation-id linkage, redaction, fail-closed
finalize, `delete_dir_after_verify`, `recover_incomplete_runs`; both harnesses
with per-run sandboxes, interrupted-path finalize, no-overwrite campaign
guards). Verification against R1–R6 + the 8 task requirements found it
substantially complete but with 7 genuine gaps; all are closed below.
No network calls were made; no commits or pushes.

## Gaps found and fixed
1. **Usage rows lacked provider-response linkage (req 2).** Meta ledger
   success entries and Groq `per_request` entries carried no response id.
   Fixed: both entries now record `response_id` (`resp.get("id")` /
   body id), so every `usage.jsonl` row joins to `responses.jsonl`.
2. **`delete_dir_after_verify` checked presence, not bytes (req 5).** Added
   `verify_manifest_hashes()` — every manifest-recorded SHA-256 is
   recomputed against disk; any mismatch keeps the sandbox with a
   `hash mismatch ...` reason. New regression test corrupts post-finalize
   bytes and proves the sandbox survives.
3. **Recovery status/name/scope (req 6).** `recover_incomplete_runs` marked
   `crashed_or_interrupted` and scanned only `phase_d_meta_live_*`; now
   marks `interrupted` and covers both `phase_d_meta_live_*` and
   `phase_d_groq_live_*`. Recovery still only ADDS a manifest, never deletes.
4. **Repairs were never a required artifact (req 5).** `finalize()` now
   requires non-empty `repairs.jsonl` when
   `outcome["repair_attempted"]` is true (both harnesses populate it:
   Meta from `result*.repairs`, Groq from `summary_repair_attempts > 0`),
   and ignores it otherwise. Late-arriving repairs promote
   `incomplete_preservation` → `finalized`.
5. **Harness call sites vs recorder signatures.** Threaded
   `investigation_id` as keyword through all Meta/Groq
   `record_response/assistant/usage/repair` calls (a positional mismatch
   would have misbound turn ids); removed a non-existent `run_label`
   kwarg; set `ledger.current_inv_id` per investigation.
6. **`final_message_head` [:400] and engine/loop [:600] caps confirmed
   display-only / production event-log behavior.** The durable recorder
   path stores complete text verbatim (2000+ char test + 5000-char
   payload test); no production code was changed.
7. **Status vocabulary documented (req 6).** `finalized` is defined as the
   completed state (finished + all required evidence verified);
   `interrupted` is never overwritten; module docstring maps R1–R7.

## Files changed (4)
- `model_autopsy/benchmarks/bench_persistence.py` — docstring, conditional
   repairs rule, `verify_manifest_hashes`, hash-enforced delete guard,
   `interrupted` recovery + Groq prefix coverage.
- `model_autopsy/benchmarks/meta_paired_continuation_benchmark.py` —
   response-id usage linkage, keyword investigation ids, repair_attempted.
- `model_autopsy/benchmarks/groq_paired_continuation_benchmark.py` — same
   threading + response-id per-request entries + repair_attempted.
- `model_autopsy/tests/test_phase_d_persistence.py` — keyword-form call
   updates + 11 new regression tests (RC1–RC6, linkage, redaction,
   hash-mismatch, no-overwrite, kill -9 subprocess recovery, end-to-end
   usage→response id join over a simulated live run).

## Test results
- `test_phase_d_persistence.py`: 29/29 pass (18 pre-existing + 11 new).
- Full suite `model_autopsy/tests`: **202 passed, 0 failed** (includes the
  7 Groq offline-persistence tests and all simulated-live scenarios).
- Kill-simulation: subprocess `os._exit(137)` mid-run → recovery marks
  `interrupted`, evidence byte-identical.
- Credential scan: no `sk-proj-`/`gsk_` bearer material written; only
  `[REDACTED]` markers; `.env` git-ignored.
- Historical integrity: all **65 manifest-recorded artifact hashes**
  across every historical campaign re-verified, 0 mismatches — no
  historical artifact modified.
- Manifest hashes for all newly finalized (simulated) runs verify.

## Blockers / notes
- None for Phase 2/3. Production loop change from prior work (repairs
  returned by `run_meta_turn`) is consumed, not modified, here.
- Next step per instructions requires provider contact (Groq validation),
  which was explicitly out of scope for this task — STOPPING here.
