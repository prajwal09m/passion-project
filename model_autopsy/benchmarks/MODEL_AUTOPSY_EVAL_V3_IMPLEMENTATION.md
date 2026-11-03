# MODEL_AUTOPSY EVAL V3 — IMPLEMENTATION (Stages 2–6)

**Mode:** offline only. No provider calls, no live runs, no spend, no
commit/tag/push. Frozen artifacts (scorer v2, sealed truth, archived
scorecards/eval_reports/manifests/DBs, Phase-D files, Demand Zone AI)
untouched — verified in Stage 8 audit.

## 1. Files created (new, additive only)

| File | Purpose |
|---|---|
| `backend/eval/normalize.py` | Canonical `gap` metric; alias/conflict/invalid rules; input never mutated |
| `backend/eval/rubric_v3.py` | Versioned rubric: weights, slice `min_gap=0.15` + documented rationale, formula |
| `backend/eval/scorer_v3.py` | Separated dimensions: discovery/evidence/verification/confirmation/efficiency/reproducibility; `rubric_version: "v3"` on every scorecard |
| `backend/live/verification.py` | Plan → execute-or-explain workflow; 8 reason codes; read-only status rollup |
| `tests/test_eval_v3_{normalize,scorer,verification,regression}.py` | 32 tests |
| 6 reports (this project) | inventory, design, implementation, validation, comparison, audit |

## 2. Files modified (narrow, backward-compatible)

| File | Change | Compatibility |
|---|---|---|
| `backend/live/adapter.py` | `_numbers_only(tool, result)` applies canonical-gap alias at boundary; `verification` list filled read-only from events (was hardcoded `[]`) | key presence/provenance tests pass; non-mutation test passes (queries only, no writes) |
| `backend/live/driver.py` | one-line switch `maybe_verify` → `run_verification_phase` (same signature) | same skip/execute semantics; adds plan + reason-code events |
| `frontend/src/Eval.tsx` | optional `rubric_version`/`notes`/`unavailable`; verification trail (executed vs planned); "discovery ≠ confirmation" explainer | v2 scorecards render unchanged (fields optional; generic dimension renderer reused) |

**Not modified:** `backend/eval/scorer.py` (v2 byte-identical — pinned by
`test_v2_weights_and_bands_untouched` + archived-scorecard reproduction),
sealed truth, fixtures, any archived run, `engine.py` (no hook needed:
verification reuses `record_event`/existing replication machinery),
Demand Zone AI (zero diffs).

## 3. V3 scoring formula (implemented as specified)

`overall = Σ w·dim / Σ w` over available dims; `None` when truth missing or
>1 core dim unavailable. Weights: discovery .30 / evidence .20 /
verification .15 / confirmation .20 / efficiency .05 / reproducibility .10.
Discovery: token-overlap ≥0.25 + family word, status credit
confirmed/likely 1.0, supported 0.7, investigating/proposed 0.4,
rejected 0.0; duplicates single-counted; confirmed-distractor −0.3.
Evidence: 0.4 any moving ref + 0.3 support&contradict + 0.3 linked-ran
fraction; repeats noted not double-counted. Verification: executed 1.0 /
errored 0.4 / planned-only 0.2 / none 0.0. Confirmation: correct 1.0 /
honest partial-with-discovery 0.7 / honest stall 0.4 / unsupported 0.0.
Numbers gate (slice): `gap ≥ 0.15 AND (p<0.05 if a p-value is attached)`.

## 4. Calibration decision (implemented, not fitted)

`min_gap 0.15` per `rubric_v3.py` rationale: pre-existing test-suite floor
(`test_m15_resolution`, `test_m16_phase1` assert `>= 0.15`), ~12% margin
below deterministic effect 0.1695, far above noise (p=0.0005), null fixtures
structurally exempt (gap absent ⇒ gate cannot fire). Fixture and truth
unchanged — no v3 fixture needed.

## 5. Verification workflow (implemented)

`plan_verification` (records claim/probe/expected pro-con/budget, dispatches
nothing) → delegate to existing `maybe_verify` → skip paths mapped to
`record_non_verification` reason codes. ≤1 probe/hypothesis/phase; budgets,
timeouts, retries, stopping rules inherited unchanged. M22-shape outcome now
records `already_measured` instead of a bare skip.

## 6. Known limitations

Older archived shapes (m16/m17/m21) embed no moving evidence refs, so v3
evidence scores 0.0 there with an explanatory note (honest, not a bug);
`verification==[]` on v2 archives reads as 0.0/"no verification recorded";
UI explainer shows only when discovery>0 and confirmation<1.
