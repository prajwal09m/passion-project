# M18 Phase 8 — Offline Validation Report

No paid calls made. All gates evaluated offline from deterministic tests
and recorded state.

## 1. Gate summary

| Gate | Result |
|---|---|
| Full backend test suite | **520 passed, 0 failed** (~121s) — 495 pre-existing + 25 new M18 |
| New M18 tests (`tests/test_m18_integration.py`) | 25/25 |
| TypeScript `tsc --noEmit` | clean (exit 0) |
| Vite production build | succeeds (~2s) |
| API tests (`test_api.py`) | green (in full suite) |
| Budget enforcement (`test_m8_budget.py`, `test_live_investigator.py`) | green |
| M9/M10 grades (`test_m9_challenge.py`, `test_m10_validation.py`) | unchanged, green |
| Sealed-truth separation audit | ok — no `sealed`/`ground_truth` refs in `live/` or `meta_api/` |
| Credential exposure scan | clean (only dummy/test values) |
| Historical `benchmarks/` artifacts | unmodified (3 files added, none edited) |
| Scorer / M10 evaluators | untouched (read-only) |
| Demand Zone AI | untouched (no files under its paths) |
| **Readiness verdict** | **GO — see `M18_LIVE_READINESS.md`** |

Exact commands: `py -m pytest model_autopsy/tests -q` (520 passed);
`npx tsc --noEmit` (exit 0); `npm run build` (✓ built); grep audits above.

## 2. Files changed (session scope)

- `backend/live/accounting.py` (NEW) — authoritative experiment taxonomy,
  single reserve/settle/release choke point, verification hold, purpose
  ledger (`experiment_ledger` events).
- `backend/meta_api/loop.py` — hypothesis ops bypass the experiment budget;
  call-list slicing governed only by tool-call budget; per-dispatch
  allocator enforcement with recorded refusals.
- `backend/live/reserve.py`, `backend/live/skeptic.py`,
  `backend/live/verify.py` — all experiment spend routed through
  `accounting` (purpose + hypothesis link recorded); dedup reuses release
  instead of charging; skeptic/reservation honor the verification hold;
  verification consumes the held slot.
- `backend/research/resolve.py` — ADD `collect_transitions()` (real
  from→to events from revisions + hypothesis events); `contract()` reports
  `partially-resolved` only on genuine advancement to supported/rejected;
  evidence-without-advancement is `unresolved`.
- `backend/live/verify.py` — contract fed by `collect_transitions`;
  hypotheses re-read post-probe so the contract sees final state.
- `backend/live/governor.py` — `CAPS["cost_usd"]` 0.40 → **0.65** (the
  M18-authorized single-run ceiling; all other caps unchanged).
- `backend/api.py` — NEW read-only `GET /closure` (hypotheses, real
  transitions, ledger, allocation, skeptic/verification/resolution, spend).
- `frontend/src/api.ts`, `frontend/src/Workspace.tsx` — scientific-closure
  panel reading recorded backend data (no fabricated state).
- `tests/test_live_investigator.py` — cost-cap boundary test updated to the
  authorized $0.65 ceiling (required by the requested behavior; old
  0.40 values no longer the cap).
- `tests/test_m18_integration.py` (NEW, 25 tests) + this doc.

## 3. Failures found during development (all fixed at cause)

1. Verification-hold v1 ("always hold 1 slot") deadlocked evidence
   gathering and broke two pre-existing tests (`test_m7_closed_loop`,
   `test_m8_budget` dry run): with a 1-experiment cap nothing could run.
   Root cause: hold must not precede the candidate it protects. Fixed at
   cause — hold activates only when an eligible candidate exists on
   record; no test was weakened (the two old tests pass unmodified).
2. Call-list slicing still counted hypothesis ops against
   `experiments_left`, starving diagnostics when the caller budget was 1.
   Fixed at cause — slicing governed only by tool-call budget, experiment
   cap enforced per-dispatch by the allocator.
3. `api.py` closure endpoint written with a 1-space indent (IndentationError
   caught by the closure-endpoint test). Fixed; test green.
4. Over-strict hold test asserted the 6th slot is held with no candidate
   on record; corrected to link evidence first (candidate → hold on).
5. `resolve.contract` initially kept snapshot-shaped test inputs working
   by accident; added explicit snapshot-vs-transition regression tests.

No test was skipped, weakened, or adjusted to pass; no lint/type
suppression added. The single updated test (0.40 → 0.65 boundary) tracks
the explicitly authorized cap change.

## 4. End-to-end offline closure tests

- `test_m18_e2e_closure_success_confirms`: hypothesize (free) → reserve →
  model diagnostic (allocator) → skeptic challenge/response → verify
  (independent `slice_gap_significance` probe) → checklist → confirmed;
  event chain reservation/experiment_ledger/skeptic/replication/
  verification/resolution all present; spend ≤ 6.
- `test_m18_e2e_contradiction_never_confirms`: corroboration runs; a later
  contradicting ref keeps fresh candidates unconfirmable; no false
  confirmation.
- `test_m18_e2e_budget_starvation_keeps_unresolved`: budget filled, 6th
  non-verification spend refused with the hold reason, verification
  declined honestly, status unresolved, nothing confirmed.

## 5. Limitations and known risks for the live run

- The model writes its own hypotheses and chooses its own diagnostics;
  if it never produces a verifiable candidate, verification declines
  honestly and the milestone verdict is incomplete, not failed.
- If the candidate only emerges on the 6th experiment, verification
  starves (hold cannot precede the candidate) — honest skip, disclosed.
- Frozen scorer music band (`gap` ≥ 0.20 vs measured 0.1695) still caps
  discovery scoring; untouched per constraints.
- Single scenario (`eval_music`), single model, one run: no
  generalization claims.
