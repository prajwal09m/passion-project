# FINAL Groq validation report — Stage A (2026-10-31)

- Model: `openai/gpt-oss-120b`, endpoint `https://api.groq.com/openai/v1/chat/completions`
- Design: frozen controlled Full-vs-Delta, 1 pair, full→delta, temp 0.2, 3 rounds/turn, caps 25 attempts / 120k tokens / $0.50 / 4×429.
- Attempts used: 2 of max 2. Total measured spend: **$0.01940** ($0.009881 + $0.009515).

## Campaigns (both preserved, nothing overwritten)
- Attempt 1: `phase_d_groq_live_20261031T212749Z` → `phase_d_groq_final_validation_results.json`
- Attempt 2: `phase_d_groq_live_20261031T213842Z` → `phase_d_groq_final_validation_results_attempt2.json`
- Stdout logs: `phase_d_groq_final_validation_stdout.log` (+ `_attempt2.log`), both end `GROQ_EXIT=0`.

## 12 pass criteria
1. **Runs execute / failures documented: PASS.** 4 runs, 30 billed requests, 0 failed, no cap hit, no 429 waits. Two invalid summaries (att1-delta, att2-full) root-caused to provider-side flakes (tool-only rounds → empty final; repair length-stopped at frozen 1200-token cap), evidence preserved verbatim.
2. **Every request durable: PASS.** 7 responses + 7 usage rows per run (+1 unbilled config probe), all manifests `finalized`.
3. **Identifiers/linkage: PASS.** 100% rows carry investigation_id; 0 usage→response join misses across all 4 runs.
4. **Messages/summaries survive: PASS.** Verbatim rows incl. empty pre-repair finals + post-repair finals (1052/1094 chars); invalid summaries reported honestly, never fabricated.
5. **Raw payloads + redaction: PASS.** Full provider bodies preserved; zero `sk-proj-`/`gsk_` pattern hits in any artifact.
6. **Repairs preserved: PASS.** `repairs.jsonl` in all runs incl. the 28-char length-stopped stub.
7. **Usage reconciles: PASS.** Per-condition sums from provider-reported usage; joins 100%.
8. **No overwrites: PASS.** Fresh timestamped campaign dirs; all 65 historical manifest hashes re-verified, 0 mismatches.
9. **No unexplained gaps: PASS.** Every empty/invalid field traced to a preserved provider response.
10. **Quality not worse under Delta: PASS.** Blinded frozen-rubric scoring: valid-full 8/12, valid-delta 11/12; same conclusion direction (both inconclusive, further diagnostics). Completion flaked equally (1/2 each) — condition-independent.
11. **Interpretable tokens: PASS.** Identical 7-request structure, no stops/waits. Provider-reported input: att1 −1.7%, att2 −4.4% Delta-vs-Full. Infrastructure signal only — NOT Meta billing evidence.
12. **Tests: PASS.** 202/202 full suite on current implementation; 36/36 persistence+Groq (exit 0).

## Blinding record
Packets built from valid finals only; labels randomized (seed 20261031); key sealed to `.sealed/phase_d_groq_final_packet_key.json` BEFORE scoring; scores frozen in `PACKET-*.scores.json`; unblinded after freeze: A=att1-full (8), B=att2-delta (11).

## Artifact hashes (SHA-256, prefix)
- `80aef646f2f4c96c` final_validation_results.json
- `9ccf56c64bed8a2e` final_validation_results_attempt2.json
- `365e2a58f4dbdbc9` PACKET-A.md / `a0eebb73ed3f0ebd` PACKET-B.md
- `88a70492a4af1eb9` PACKET-A.scores.json / `e4939f760d5c54a9` PACKET-B.scores.json

## Limitations
- Completion flake: gpt-oss-120b produced tool-only trajectories (no prose) in 2/4 runs; repair then length-stopped once. Equal across conditions; not a Delta defect, but a reuse risk for fully autonomous runs.
- Quality comparison is cross-attempt (n=1 valid each), not paired within one campaign.
- Groq token deltas say nothing about Meta billed tokens.

## Decision: **GO for Stage B.**
All 12 criteria pass. Both Groq attempts are exhausted (2/2) — no further Groq spend authorized. Exactly one frozen 4-run Meta campaign is authorized next.
