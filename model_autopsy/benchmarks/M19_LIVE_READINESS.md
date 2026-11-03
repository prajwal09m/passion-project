# M19 Phase 9 — Live Readiness Review

Separate assessment after implementation and offline validation. Each
claim cites the test or simulation that proves it from real code.

## 1. Readiness checklist (Phase 9 §1–13)

1. **M18 round-2 failure recovered by the new fallback.** Proven by
   `test_m19_m18_shape_chained_400_recovers` (exact recorded shape:
   chained outputs + `previous_response_id` → 400 → one full-context
   re-send, no chain, turn `ok`) and the legacy
   `test_continuation_failure_falls_back_once_with_full_context`.
2. **Full-context fallback preserves state.** Proven by legacy
   `test_fallback_preserves_prior_evidence_and_accounting` (turn-1
   actions intact, rollup honest) and `test_m19_no_duplicate_execution_
   after_recovery` + `test_m19_fallback_then_diagnostic_executes`.
3. **Completed tools never executed twice.** Engine dedup
   (`allow_reuse`, tool+args+data identity) + allocator release on reuse,
   proven by M19 reuse tests and the legacy dedup test; failed actions
   are re-runnable (not confused with completed work).
4. **Recovery respects all budgets.** Fallback carries its own attempt
   reserve + headroom recheck (`test_m19_fallback_rechecks_budget_
   before_resend`, `test_m19_fallback_token_budget_refusal` shape,
   `test_m19_fallback_attempt_budget_refusal`); auth/5xx/network never
   trigger fallback; caps unchanged (3/6/12/50k/$0.65).
5. **Investigator progresses hypotheses → diagnostics.** Selection brief
   in every request, enriched criteria, post-hypothesis nudge, proven by
   the 10 progression tests (executed / deferred-with-reason /
   flagged-incomplete).
6. **Decision explicitly recorded.** `investigator_decision` event per
   completed turn + `decision` in turn result (state, candidates, action,
   tool, rationale, budget, outcome, incomplete flag).
7. **Reservation executes after meaningful hypotheses.** End-of-turn
   checkpoint unchanged; proven in scenarios A/C and M18 suites.
8. **Skeptic without consuming verification capacity.** Hold honored by
   skeptic probes (`test_m19_hold_survives_three_way_competition`,
   M18 hold tests); dissent preserved when budget forbids.
9. **Eligible candidate reaches verification.** Scenario A + M18/M19
   verify tests through `maybe_verify` → `replicate`.
10. **Probe genuinely independent.** Different-tool rule + cached/same-
    tool rejection (`test_m19_same_tool_repetition_rejected`,
    M18 cached tests).
11. **Contract uses real transitions.** M18 `collect_transitions` suite
    green, unmodified; `test_m19_transition_contract_accuracy`.
12. **Full closure passes offline.** Scenarios A (confirmed), B
    (contradiction → unresolved, nothing manufactured), C (failure →
    recovery → diagnostic → honest report), D (decline with reason, no
    forced experiment).
13. **All limits enforced.** Governor + allocator + M8/M18 suites green;
    fallback cannot bypass attempt/token/financial caps (refusal → honest
    stop, never a silent drop).

## 2. Live allocation simulation (real allocator + live-path code)

Scripted provider through `run_meta_turn` → `skeptic.review` →
`maybe_verify` on the music fixture:

- 2 proposes: 0 slots → 0/6
- model diagnostic: +1 → 1/6
- end-of-turn reservation: +1 → 2/6 (simulation showed 3/6 with an
  additional model-side measurement in that run)
- skeptic review: 3 challenges, answered without new spend
- independent verification: +1 → 4/6
- Resolution: `confirmed`; run result: **FITS with 2 slots margin**

Worst case with a redundant model follow-up: 5–6/6 with the hold
protecting verification's slot; beyond that, honest refusal. Pre-run
cost projection ≤ $0.1172 typical against the $0.65 ceiling.

## 3. Verdict

**GO — one authorized live run is safe to attempt.**

- Scenario `eval_music` only, exactly one investigation, max 3 rounds /
  6 actual experiments / 12 attempts / 50,000 tokens / **$0.65**.
- Stop after the single investigation whatever the outcome; no retries,
  no second runs, no additional scenarios. A fallback success is
  recovery, not closure; only an executed independent probe counts
  toward the live-closure bar.
