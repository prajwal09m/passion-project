# M17 Phase 7 — Offline Validation Report

No paid calls made. All gates evaluated offline from recorded state and
deterministic tests.

## 1. Gate summary

| Gate | Result |
|---|---|
| Full test suite | **495 passed, 0 failed** (306s) |
| New M17 regression tests | 18/18 in `tests/test_m17_integration.py` |
| TypeScript `tsc --noEmit` | clean (exit 0) |
| Vite production build | succeeds (4.28s) |
| API smoke tests | pass (in suite: `test_api.py`) |
| Budget enforcement tests | pass (`test_m8_budget.py`, `test_live_investigator.py`) |
| Sealed-truth separation audit | ok, 11 files scanned, 0 violations |
| Credential exposure scan | clean (only dummy test values) |
| M9/M10 grades | unchanged (`test_m9_challenge.py`, `test_m10_validation.py` green) |
| Historical artifacts | unmodified (one file added, none edited) |
| Scorer / M10 evaluators | untouched (read-only inspection) |
| Demand Zone AI | untouched (no files under its paths) |
| **Readiness verdict** | **GO for the single authorized live run** |

## 2. Files changed (session scope)

- `backend/meta_api/loop.py` — reservation checkpoint moved to
  `maybe_reserve_end_of_turn` (end of turn); per-dispatch token
  headroom gates; driver calls `live/verify.maybe_verify`.
- `backend/live/verify.py` (new) — budgeted verification caller +
  resolution contract on every path.
- `backend/live/reserve.py` — unchanged (called later; behavior same).
- `backend/live/skeptic.py` — open/answered challenge persistence,
  gate helpers, probe/dissent resolution marking.
- `backend/live/governor.py` — `EST_OUTPUT_TOKENS` + `check_dispatch`.
- `backend/live/driver.py` — verification hook (never throws).
- `backend/m11/roles.py` — missing-falsification + contradictory-evidence
  block (once-per-hypothesis dedupe in review).
- `backend/causal/attribution.py` — stemmed segment matching,
  euphemistic-denial symmetry, insufficiency bar.
- `backend/causal/hypotheses.py` — skeptic gate on `supported`,
  auto-answer on falsification.
- `backend/causal/linker.py` — `slice_gap_significance` rule.
- `backend/causal/selection.py` — new tool registered as discriminator.
- `backend/m10/replication.py` — `ranking` second probe; arg mapping
  fixed per family (ranking tools take `score_column`, not
  `prediction_column`).
- `backend/ml_tools.py`, `backend/tools_registry.py` — new
  `slice_gap_significance` diagnostic (permutation null, seeded).
- `tests/test_m17_integration.py` (new, 18 tests).
- Docs: `benchmarks/M17_ARCHITECTURE_AUDIT.md` (Phase 0), this file.

## 3. Failures found during development (all fixed at cause)

1. Phase 1 test asserted the wrong event-title casing — test corrected,
   code untouched.
2. Phase 2 `replicate()` added `prediction_column` for the ranking
   family, which the new tool does not accept — fixed arg mapping per
   family; regression covered by the confirmation test.
3. `record_review` called without the investigation argument — fixed
   call site.
4. Attribution test helper omitted `slice_column`, tripping the (correct)
   adequacy gate — helper fixed to act like the live model.
5. `verify.py` first draft written with literal escape sequences —
   rewritten cleanly; full-suite green after.
6. Roles change initially risked re-blocking answered challenges —
   resolved with once-per-(type, hypothesis) dedupe + persisted state.

No test was skipped, weakened, or adjusted to pass; no lint/type
suppression added.

## 4. End-to-end offline integration test

`test_m17_end_to_end_scientific_closure` drives one offline
investigation through the actual live callers: round-1 hypotheses →
`maybe_reserve_end_of_turn` (reserved + executed, 1 experiment) →
slice diagnostic + link → `skeptic.review` (blocking challenge →
probe/dissent, gate released) → `maybe_verify` (independent
permutation probe, checklist upheld, `record_finding("confirmed")`,
`resolve.contract` status confirmed). Event chain verified:
reservation, experiment, skeptic, replication, verification,
resolution. Budget: ≤3 experiments of the shared 6-cap.

## 5. Integration paths (live callers)

- Reservation: `run_meta_turn` → `maybe_reserve_end_of_turn` →
  `reserve.run_reserved` → `invention.execute` → `linker`.
- Skeptic: `run_meta_turn` → `skeptic.review` → `roles.skeptic` +
  granularity → `invention` probe → `linker`; gate in
  `hypotheses.update_with_evidence`.
- Verification: `driver.run_live_investigation` →
  `verify.maybe_verify` → `replication.replicate` →
  `verification.review_claim/record_review` → `record_finding` →
  `resolve.contract`.
- Headroom: `run_meta_turn` (per dispatch) + `_attempt_summary_repair`.

## 6. Limitations and known risks for the live run

- Budget is tight by design: reservation (1) + model diagnostics +
  possible skeptic probe (≤1) + verification (1) share 6 experiments.
  Decline paths are honest but consume the run's one shot at
  confirmation if the model is spendthrift.
- The frozen scorer's music band (`gap` ≥ 0.20) exceeds the measured
  0.1695: even a fully confirmed finding scores discovery ≤ 0.2 there.
  Scorer untouched per constraints; reported, not gamed.
- The model writes its own hypotheses: euphemistic uniformity wordings
  are now contradicted correctly, but novel paraphrases outside the
  phrase list fall back to neutral (visible, non-moving) — safe
  direction.
- Single scenario (`eval_music`), single model, one run: no
  generalization claims will be made.

## 7. Readiness verdict

All offline gates pass. The scientific workflow is integrated into the
actual live path and proven end-to-end offline. **GO for exactly ONE
live `eval_music` investigation under the $0.65 aggregate ceiling.**
