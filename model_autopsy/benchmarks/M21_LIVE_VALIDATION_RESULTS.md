# M21 Live Validation Results — Single Authorized Investigation

Run: `live_runs/m21-music-01` (`eval_music`). One investigation, no
retries, no follow-ups. Launcher: `benchmarks/m21_live_run.py`
(preflight-first; runtime token-cap lift per authorization, cost cap
unchanged; no source files modified).

## 1. Configuration and execution summary

- Model `muse-spark-1.3` via `https://api.meta.ai/v1/responses`;
  key present (boolean-checked only, never exposed).
- Preflight: project known, separation audit ok (11 files), artifact
  readable, preservation writable, cost projection worst $0.1172 /
  typical $0.0342, within $0.65 cap → GO.
- Caps enforced: rounds 3, experiments 6, attempts 12, cost $0.65,
  tokens unlimited per authorization (runtime value only).
- Outcome: `completed`, 1 round, 0 experiments, 2 attempts,
  9,689 tokens, **$0.020448 (3.1% of cap)**.
- Scorecard: `inconclusive` ("failure missed entirely"), overall 0.64.

## 2. Rounds / experiments / attempts

- Round 1: model returned prose, zero tool calls, zero hypotheses.
  Summary invalid → one repair → repaired summary valid +
  consistency-passed → provenance `model_repaired`. Turn `ok`.
- Post-turn: reservation declined (0 open hypotheses), skeptic
  0 challenges, verification skipped (no eligible hypothesis),
  resolution contract `unresolved`. Driver stopped after round 1
  (no tool calls + valid summary break condition); no budget pressure.

## 3. Usage and estimated cost

Provider-reported only: input 6,910 (cached 0), output 2,779.
Cost = 6910 × 1.25e-6 + 2779 × 4.25e-6 = 0.0086375 + 0.01181075 =
**$0.020448**, matching the run ledger exactly (math verified
offline pre-run against M19 figures). Cap headroom remaining: $0.6296.

## 4. Evidence inventory and preservation verification

All 10 artifacts present, readable, sha256-manifested
(`required_evidence_present` all true): `events_dump.json` (19 events),
`assistant_messages.jsonl`, `usage.jsonl`, `hypotheses.json` (`[]`),
`actions.json` (`[]`), `eval_report.json`, `scorecard.json`,
`live.sqlite3` + `sandbox_final.db`, `manifest.json`, plus the launch
log. Secret scan of all artifacts clean. Reconstruction check: final
report rebuilds from `live.sqlite3` events/hypotheses/actions alone.

Preservation notes (honest): raw round-1 text verbatim in
`meta_response` payload; repair response 251 chars, complete inside
the 600-char persisted head (ends with closing fence); longer repairs
would truncate per the documented M20 design. Per-call repair usage
is folded into rollup/ledger totals, not a per-call event.

## 5. Scenario-by-scenario results (protocol S1–S13)

| Scenario | Live outcome |
|---|---|
| S1 valid native | Not observed — remains fixture-only |
| S2 prose without block | **Demonstrated** — final message prose, class `prose_without_block`, eligible |
| S3/S4/S5 malformed/schema/semantic | Not observed — fixture-only |
| S6 empty / S7 provider failure | Not observed — fixture-only |
| S8 repair succeeds | **Demonstrated** — valid repair, all 10 consistency gates passed, `repaired_via` marked |
| S9 repair fails | Not observed — fixture-only |
| S10 unsupported confirmation | **Pass** — no confirmation language anywhere; contract `unresolved`, conclusion honest |
| S11 missing verification | **Pass** — no verification claimed; skip recorded with reason |
| S12 contradiction | **Pass (vacuous)** — none existed; nothing hidden |
| S13 invented numbers | **Pass (vacuous)** — none claimed |

## 6. Malformed / incomplete / contradictory / missing behavior

- Malformed: none (prose, not malformed). Incomplete: the whole
  investigation — zero hypotheses, zero diagnostics. Contradictory:
  none. Missing output: none (both calls returned content).
- Unexpected model behavior (recorded, not concealed): the model
  wrote a one-line deviation note ("low-value generic checks ... don't
  measure P@K per slice") and then stopped — no hypotheses, no
  diagnostics, no decline reason. The pipeline recorded this exactly
  (`investigator_decision: no-diagnostic-no-reason`, scorecard
  discovery 0.0, `inconclusive`).

## 7. Reporting-contract compliance

Native invalid → eligibility true → exactly one repair (no tools, no
chain) → base validation + all consistency gates → accepted with
`repaired_via`; original verdict preserved in its own events;
provenance unambiguously `model_repaired` in both eval-report and
(prior) causal view shapes; final-state adapter consistency
`passed:true`, zero failures/warnings; assembly fingerprint unchanged
(`assembly_mutated_state:false`); M21 native-advisory keys present on
both summary events. No §2.10 violation at final state.

## 8. Failures and limitations

- Investigation yielded no science (model did no work) — an honest
  `inconclusive`, not a pipeline failure, but S1/S3–S7/S9 stay
  live-unverified.
- Single scenario / single model / one run: proves nothing about
  general reliability (per milestone rule).
- Preservation caveats in §4 (repair-head truncation design,
  per-call repair usage in totals only).
- `assistant_messages.jsonl` is a JSON-encoded string wrapping JSONL
  (pre-existing recorder convention, shared with M19).

## 9. What was demonstrated vs. what remains unverified

Demonstrated live: S2→S8 path end to end; eligibility gating;
single-attempt bound; consistency-gated acceptance; `model_repaired`
provenance; honest inconclusive on empty evidence; no false
confirmation/verification; budget + evidence preservation.
Unverified live: native-valid handling (S1), malformed/schema/
semantic classes (S3–S5), empty/provider-failure paths (S6–S7),
repair rejection (S9), verification-then-confirmation under budget.

## 10. Sufficiency

Evidence is sufficient to support exactly the conclusions in §9 —
and insufficient for any broader reliability claim. No criteria were
changed: the protocol's pass/fail/inconclusive definitions are
untouched, and this report marks the run `inconclusive` on science
while `pass` on reporting-pipeline behavior.
