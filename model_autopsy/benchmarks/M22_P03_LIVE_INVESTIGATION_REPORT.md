# M22 P0.3 — Controlled Live Investigation Report

**Stage:** 3 of 4 (ONE controlled live investigation, $0.65 total ceiling)
**Date (UTC):** 2026-11-02
**Run directory:** `model_autopsy/benchmarks/live_runs/m22-live-01/`
**Classification: PARTIAL PASS** (justified in §10 — the zero-action recovery
nudge was never triggered because the model acted from turn 1; inaction
*detection* and all evidence-floor paths were demonstrated live instead)

---

## 1. Preflight checks

| Check | Result |
|---|---|
| Stage 2 passed | YES — `M22_P02_INDEPENDENT_VERIFICATION.md`, PASS (1062 tests) |
| Provider/model available | YES — Meta API, `gpt-5.1` |
| Pricing known | YES — measured per-call ledger: investigator ≈ $0.012–0.041, repair ≈ $0.006, final ≈ $0.003 |
| Conservative max cost | 5 calls observed; worst single call $0.041 → even 10 retries ≈ $0.41 < $0.65 |
| Cumulative tracking | YES — `run_governor` ledger persisted per call to `usage.jsonl` |
| Retries cannot bypass budget | YES — fixed `max_rounds=3`, no auto-retry loops; governor consulted before spend |
| Stop-before-exceed | YES — single bounded run, no background tasks; measured total $0.072925 (11% of ceiling) |
| No background consumers | YES — only run consumed budget; ledger has exactly 5 entries |

Preflight verdict: GO. No blockers.

## 2. Provider / model / pricing

- Provider: Meta (existing `meta_api` integration, no new code).
- Model: `gpt-5.1`.
- Pricing: provider-metered; actuals from ledger (no estimation needed):
  investigator turn 1 $0.012452 → turn 2 $0.013824 → turn 3 $0.037642
  (empty-output turn cost most: 8087 completion tokens of retries/empties),
  repair $0.005986, final eval $0.003021. **Total $0.072925.**

## 3. Experiment scenario

- Frozen M25 scenario `m25-music-01` (music catalog slice-gap case).
- Ground truth sealed (severity 1.5/5, 2 slices, 6 metrics); scenario text only,
  truth never shown to model.
- Token cap 3500/turn, `max_rounds=3` — reproduces the M21 shape (bounded
  turns, prose-capable model, diagnostic toolbelt available).
- No artificial forcing: native investigator prompt, real toolbelt, real linker.

## 4. Turn-by-turn record (12 required transitions in §5 table)

**Turn 1** — model responded with prose + tool calls: proposed 3 hypotheses
(all `propose_hypothesis` ran) and 3 diagnostics; executed
`ranking_slice_diagnostics`, `classification_metrics`, `regression_metrics`
(all `ran`); linker recorded links; summary INVALID
(`prose_without_block`) → bounded JSON repair requested → **repair returned
empty → rejected, fallback composed** (`repair_attempted`, `repair_rejected`
both recorded with reasons). Investigation continued (no break: fallback turn).

**Turn 2** — model responded: ran `slice_gap_significance` + repeated
`ranking_slice_diagnostics`; linker linked to 3 open hypotheses; summary
invalid again → NO repair requested (repair budget already consumed:
`repair_skipped_budget_consumed`) → fallback composed.

**Turn 3** — **model went completely silent** (empty output, 0 tool calls,
0 text): parser → `empty_output` → turn ineligible → fallback; decision:
`total_inaction=TRUE`, `incomplete=TRUE`, pre-existing progress
`sufficient-evidence`; **no M22 recovery nudge** (by design — hypotheses
existed, so no `no_hypothesis` silence occurred and the verify tool gates any
deeper check); **no verify dispatch** (prior evidence already measured —
recorded reason, not an omission). Evidence floor `ran=8>0` → `completed`
(no `inconclusive_no_gain`: prior rounds produced gain).

## 5. Transition table (§C: 14 items)

| # | Transition | Observed |
|---|---|---|
| 1 | Initial model response | Prose + 6 tool calls (3 hyps + 3 diagnostics) |
| 2 | Hypotheses generated | YES — 3 (turn 1) |
| 3 | Diagnostic actions proposed | YES — 3 (turn 1), +2 more (turn 2) |
| 4 | Zero-action detection triggers | Turn 3: `total_inaction=TRUE` recorded live |
| 5 | Recovery nudge issued | NO — never triggered (hyps existed all run) |
| 6 | Model responds to nudge | N/A — no nudge issued |
| 7 | Diagnostic actions executed | YES — 8 `ran` (5 propose-hyp filtered: 3 propose + 5 diagnostics) |
| 8 | Useful moving evidence | YES — `useful_evidence=true`, refs on all 3 hyps (4/5/5 refs) |
| 9 | Evidence supports/contradicts | YES — 1 supported, 1 rejected, 1 investigating |
| 10 | Supported conclusion established | PARTIAL — resolution `partially-resolved`, no confirmation |
| 11 | Final resolution contract | `partially-resolved` (honest, unresolved per P0.1 semantics) |
| 12 | Final run status | `completed` (evidence floor met: 8 ran) |
| 13 | Final `useful_evidence` | `true` (manifest line 1 AND provenance line 2 agree) |
| 14 | Total cumulative cost | **$0.072925 / $0.65 (11.2%)** |

## 6. Diagnostic actions actually executed

`propose_hypothesis`×3, `ranking_slice_diagnostics`×2,
`classification_metrics`×1, `regression_metrics`×1,
`slice_gap_significance`×1 — all status `ran`, 0 failed.

## 7. Evidence produced

- 3 hypotheses with 4/5/5 evidence refs; statuses supported/rejected/investigating.
- Linker events: 5 recorded link decisions (turns 1–2).
- Scorecard (sealed truth, deterministic): label `inconclusive`, discovery F1
  **0.0** — the model discriminated slices but **missed the true failing
  mechanism entirely**. Reported as-is; no inflation.

## 8. Resolution / status / signal

- Resolution contract: `partially-resolved`. Run status: `completed`.
  `useful_evidence`: `true`. All three layers agree and are mutually
  consistent (execution ≠ usefulness ≠ resolution — the P0 distinction holds live).

## 9. Spending ledger (exact)

`usage.jsonl` (5 entries): 0.012452 + 0.013824 + 0.037642 + 0.005986 +
0.003021 = **$0.072925**. Ceiling $0.65 respected with 8.9× headroom.
No further provider calls will be made (investigation closed; Stage 4 is
strictly read-only/offline).

## 10. Classification: PARTIAL PASS

- The M21-from-scratch shape did **not** recur: the model acted from turn 1
  (3 hyps + 3 diagnostics), so the **recovery-nudge response question is
  untested live** — no qualifying total-silence-from-scratch event occurred.
- What WAS demonstrated live: real diagnostic activity, moving evidence
  (`useful_evidence=true`), status discrimination (supported/rejected/open),
  silent-turn detection (`total_inaction=TRUE`, empty-output fallback),
  bounded-repair rejection, repair-budget gating, evidence-floor completion,
  and honest non-confirmation (scorecard 0.0 discovery, partially-resolved).
- Not a PASS (recovery response unmeasured). Not a FAIL (no zero-action
  failure, no safeguard failure, budget respected). **PARTIAL PASS.**

## 11. Remaining limitations

1. Recovery-nudge response still UNVERIFIED live (only offline-validated, 10/10).
2. Repair path fragile: the one live repair returned empty (model-side), correctly rejected.
3. Discovery quality low on this scenario (0.0 F1) — investigation activity ≠ diagnostic accuracy.
4. Turn-3 silence shows live models can stall mid-run; only the evidence floor
   (prior gain) distinguished this `completed` from an inconclusive stall.
5. No second experiment authorized — findings rest on n=1 by design.
