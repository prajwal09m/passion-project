# Phase D infrastructure defect audit — harness lifecycle (2026-10-29)

Offline, source-inspection only. No provider request, no credential access.

## What happened in the 2026-10-29 campaign

Four paired investigations ran under frozen caps. The report is internally
consistent (24 billed attempts, 121,455 provider tokens, $0.18237 estimated),
but the preserved evidence is not: only 1/4 runs had a complete final
assistant message; 3/4 final summaries invalid; 10/24 responses incomplete
(6 regular at 2,000 tokens, 4 repairs at 1,200). The scoring-readiness audit
concluded the four-run quality comparison is unsupported.

## Root causes (source-verified)

RC1 — **No durable per-run storage before cleanup.**
[meta_paired_continuation_benchmark.py](meta_paired_continuation_benchmark.py)
`run_live()` creates a per-run temp dir + sandbox SQLite; at the end of each
run `finally: … shutil.rmtree(run_dir, ignore_errors=True)`. Before deletion,
the harness persists only table counts, ledger entries, and a 400-char
`final_message_head` (`_quality()` line: `((final or {}).get("message_text")
or "")[:400]`). The complete final text (in-memory `result2["message_text"]`)
is never written anywhere durable. Once the temp dir is gone, so is the
complete message/summary/repair evidence.

RC2 — **In-loop event-detail truncation caps the preserved assistant text.**
[backend/meta_api/loop.py](../backend/meta_api/loop.py) line 394 records the
assistant round response as `detail=text_out[:600] or "(tool call only)"`.
Even a perfectly preserved DB therefore caps any message longer than 600
characters. The one surviving complete message (546 chars) fit only because
it happened to be under the cap.

RC3 — **Provider raw response bodies are never persisted.** The Responses-API
payload (full output items, stop reasons, usage, ids) lives only in process
memory; `client.py` returns it and the loop never writes it to disk. Status/
usage survive in the ledger, but raw output does not.

RC4 — **External snapshots raced the harness.** Snapshots in
`phase_d_meta_raw_2026-10-29/sandbox_snapshots/` captured the temp DB mid-run;
the harness commits final events and deletes the temp dir before any snapshot
could reach the last state. The snapshot note in `RUN_MANIFEST.json`
discloses exactly this.

RC5 — **Deletion happens even when preservation failed.** `shutil.rmtree(...,
ignore_errors=True)` runs unconditionally, so a verification failure or an
exception could not block cleanup and could not mark a run incomplete for
preservation reasons.

RC6 — **Crash/windup leaves no repair-partial evidence.** If the process dies
during summary repair, the repair response exists only in that process; the
sandbox holds at most the 600-char detail and nothing marks the turn
mid-repair on disk.

## Failure modes traced to causes

| Failure mode | Cause |
|---|---|
| Missing final assistant messages | RC1, RC2 |
| Missing/truncated summaries | RC1, RC2 |
| Lost repair responses | RC1, RC6 |
| Lost raw response payloads | RC3 |
| Missing usage records | RC3 (usage only in ledger, not tied to a durable response record) |
| Incorrect snapshot-dependent preservation | RC4 |
| Incorrect run status after lost evidence | RC5 (no preservation gate on `finalize`) |
| Lost evidence after termination mid-run | RC6 |

Not causes: the continuation-ID defect (already fixed, v2, regression-tested),
the caps (they held: 24/40 attempts, 121,455/150,000 tokens, $0.18237/$1.00),
and tool execution (18 actions, 0 failed, no fallbacks).

## Required repairs (Phase 2 targets)

- R1: per-run durable recorder written before and during cleanup:
  `responses.jsonl` (raw provider responses), `assistant_messages.json`
  (complete text per turn/round with response ids), `repairs.jsonl`
  (each repair attempt in full), `usage.jsonl`, `events.jsonl` (dump before
  deletion), `sandbox_final.db` (SQLite backup copy), `run_manifest.json`
  (SHA-256 of every artifact).
- R2: remove the 600-char cap from the persisted event for benchmark runs
  (detail stored verbatim; display truncation stays presentation-only).
- R3: `run_meta_turn` returns the complete message text (it already does) and
  the recorder persists it with the response id and continuation state.
- R4: finalization becomes atomic: persist → verify hashes → then
  `rmtree`; on verification failure keep the temp dir and mark the run
  `incomplete_preservation` with an explicit reason.
- R5: a mid-run crash leaves `respond_*` files on disk plus a
  `run_manifest.json` with `status: interrupted` and missing-evidence IDs.
- R6: dry-run simulation suite covering the 20 required scenarios offline.

## Security

No credential, `.env`, authorization header, or environment value appears in
this report; recorder artifacts must also exclude them (redaction gate in the
recorder test). This report modifies nothing.
