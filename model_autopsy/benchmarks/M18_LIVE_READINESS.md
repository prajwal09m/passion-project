# M18 Phase 9 — Live Readiness Review

Separate assessment before any spend, proven from code and tests.

## 1. Readiness checklist (each proven, not asserted)

1. **Hypothesis registration no longer counted as an experiment.**
   Proven by `test_m18_hypothesis_registration_consumes_zero_experiment_slots`
   (real `run_meta_turn` with a mocked provider: propose + diagnostic →
   `experiments_used == 1`) and `test_m18_is_experiment_taxonomy`.
   Callers: `loop.py` kind-checks every dispatch; `accounting.is_experiment`
   is the single taxonomy.
2. **All actual probes use the shared allocator.** Proven by
   `test_m18_actual_experiments_consume_exactly_one_slot`,
   `test_m18_every_experiment_has_purpose_record`, and the e2e chain test
   asserting `experiment_ledger` events. Callers: loop (`model-diagnostic`),
   `reserve.run_reserved` (`reservation`), `skeptic.review` (`skeptic`),
   `verify.maybe_verify` (`verification`) — all via
   `accounting.reserve_experiment` / settle / release.
3. **Verification capacity survives reservation and skeptic activity.**
   Proven by `test_m18_hold_blocks_starvation_but_allows_verification`
   (candidate on record → 6th non-verification spend refused with the hold
   reason; verification consumes the held slot) and
   `test_m18_skeptic_probe_shares_allocator_and_hold`.
4. **An eligible hypothesis can reach an independent verification dispatch.**
   Proven by `test_m18_verification_executes_when_eligible_and_independent`
   (dispatched, corroborated, confirmed) through the real `maybe_verify` →
   `replication.replicate` path.
5. **The verification tool is genuinely independent.** `replication.replicate`
   refuses same-tool reruns; `verify` counts distinct supporting tools
   post-probe (bar 2+/0); cached results release the hold and never verify
   (proven by `test_m18_cached_probe_cannot_count_as_independent_verification`
   and `test_m18_cached_results_not_newly_executed`).
6. **The resolution contract consumes actual transitions.**
   Proven by `test_m18_investigating_with_evidence_is_unresolved_not_partial`
   (M17 snapshot-shape repro → `unresolved`) and
   `test_m18_supported_transition_is_partially_resolved`, via
   `resolve.collect_transitions` fed into `verify`'s contract on every path.
7. **The live path invokes every required component.** Driver →
   `run_meta_turn` (selection, reservation, provider rounds, linker,
   skeptic, grounded summary) → `verify.maybe_verify` (replication,
   checklist, record_finding, contract). Asserted structurally in the audit
   and exercised by `test_m18_e2e_closure_success_confirms` through the
   actual live callers (loop/reserve/skeptic/verify), plus the pre-existing
   dry-run test `test_driver_dry_run_respects_experiment_cap` (live driver,
   scripted provider, cap honored).
8. **Token and financial governors protect every provider request.**
   `check_dispatch` headroom before every dispatch (proven by
   `test_m18_token_headroom_blocks_unsafe_dispatch` + M17 headroom tests);
   attempt/financial caps proven by `test_m18_financial_and_attempt_caps_hold`
   and the full M8/M17 budget suites.
9. **All offline gates pass.** 520/520 suite, tsc clean, Vite build,
   API/M9/M10 green, separation + credential scans clean, history and
   scorer untouched — see `M18_OFFLINE_VALIDATION.md`.

## 2. Allocation simulation (real allocator, offline, no spend)

Planned worst-case live spend through `accounting.reserve/settle`:

- 3 × `propose_hypothesis` (hypothesis ops): **0 slots**, used = 0/6
- model diagnostic: +1 → 1/6
- reserved probe: +1 → 2/6
- skeptic probe: +1 → 3/6
- verification probe: +1 → 4/6

Worst case fits in 4 of 6 with **2 slots margin** for model follow-ups.
Even with 2 extra model diagnostics, spend is 6/6 with verification
holding the final slot (hold activates once the candidate emerges, which
the first moving diagnostic creates). Starvation is possible only if the
candidate first emerges on the 6th experiment — an honest-skip edge,
disclosed, never manufactured.

Pre-run cost check: worst-case projection ≤ $0.1172 typical (M17-measured
$0.0226 for a full run) against the $0.65 ceiling — headroom > 5×.

## 3. Verdict

**GO — one authorized live run is safe to attempt.**

- Scenario `eval_music` only, exactly one investigation, max 3 rounds /
  6 actual experiments / 12 attempts / 50,000 tokens / **$0.65**.
- Stop after the single investigation whatever the outcome; no retries,
  no second runs, no additional scenarios.
