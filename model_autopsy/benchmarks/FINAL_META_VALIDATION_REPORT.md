# FINAL Meta validation report — Stage B (2026-10-31, authorized by Stage A GO)

- Model: `muse-spark-1.3`, endpoint `https://api.meta.ai/v1/responses` (from frozen code config; no overrides).
- Design: frozen 2 pairs × (full→delta), 2 turns, 3 rounds/turn, shared 6-call tool budget, temp 0.2, output 2000, repair cap 1200.
- Hard caps enforced in code: 40 attempts / 150,000 tokens / $1.00 / 3×429. Actual: **30 attempts, 104,350 provider tokens, $0.15056, 0 stops.**
- Exactly one campaign: `phase_d_meta_live_20261031T215509Z` → `phase_d_meta_final_validation_2026-10-31.json` (`1edc12797451db30`). Exit `META_EXIT=0`.

## Execution record (all 4 runs finalized, nothing deleted)
| Run dir | Condition | Billed/incomplete/failed | Summary |
|---|---|---|---|
| run-zfxpvt8j | p1-full | 6 resp (2 incomplete), 2× HTTP 400 preserved | INVALID (empty final; repair spent 1198/1200 output tokens on reasoning, empty text) |
| run-n8gzenu9 | p1-delta | 6 resp (2 incomplete) | VALID post-repair |
| run-eamlugzy | p2-full | 6 resp (3 incomplete) | INVALID (truncated 339-char final; repair invalid) |
| run-4ia6ynjt | p2-delta | 6 resp (1 incomplete) | VALID (first attempt; only turn-1 repair) |

All failures are provider-side (max-output truncation, reasoning-budget exhaustion, transient 400s) with verbatim durable records. No cap hit, no 429 stops, no missing evidence.

## Preservation verification (all 4 runs)
- Manifests `finalized`; every recorded SHA-256 re-verifies; 0 mismatches.
- 100% rows carry investigation_id; usage→response-id join 0 misses (24/24).
- Credential scan: zero secret-pattern hits.
- Continuation used validated latest response IDs (`chain_used_for_turn2` = recorded latest in all runs).

## Blind scoring (frozen rubric v1; packets `phase_d_meta_final_validation_packets_2026-10-31/`)
- Sealed index written before scoring (seed 20261031); scores frozen in `RUN-0X.scores.json`; unblinded after freeze.
- RUN-01 = p2-delta: **12/12** (valid). RUN-04 = p1-delta: **10/12** (valid).
- RUN-03 = p2-full: **5/12** (invalid summary, truncated final; scored as found).
- RUN-02 = p1-full: **not_scorable** (empty final; protocol §0, no dimension scores assigned).
- Numeric-grounding figures (0.683495, per-split AUCs) verified present in recorded event evidence for RUN-01/03/04.

## Paired comparison (established decision rule: quality first, then tokens)
- Pair 1: delta 10 vs full unscorable. Pair 2: delta 12 vs full 5.
- Uncached input tokens (new tokens actually processed): p1 4027 vs 7667 (**−47.2%**); p2 4419 vs 4486 (**−1.5%**). Delta lower in both pairs.
- Total input confounded by session-order cache warming (last run warmest: 20,006 cached); cached/uncached reported separately, never conflated.
- Decision: **Delta retained.** Quality strictly better-observed (valid 2/2 vs 0/2) with lower uncached input in both pairs. No significance claimed (n=2).

## Limitations
- n=2 pairs; provider-side incomplete stops (8/24) hit fulls harder — plausibly systematic (larger contexts → longer outputs) but not proven.
- 2 transient HTTP 400s (p1-full); preserved, run completed honestly; cause attributed to provider, not proven.
- Reasoning-budget exhaustion on one repair (frozen 1200-token cap) — reuse risk for reasoning-heavy models.
