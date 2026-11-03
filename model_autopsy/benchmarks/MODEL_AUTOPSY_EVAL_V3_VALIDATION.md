# MODEL_AUTOPSY EVAL V3 — VALIDATION (Stage 7)

**Mode:** offline only. No provider calls, no live runs, no spend.
Archived scorecards/eval_reports never rewritten (comparison computed
in-memory; regression tests assert values, never write files).

## 1. Test totals

- Full backend suite: **694 passed, 0 failed** (baseline before this project:
  662 passed; +32 new v3 tests, zero regressions).
  - `test_eval_v3_normalize.py`: 9 (gap-only, alias, equal, conflict,
    absent-never-zero, invalid→dropped+flag, None-means-absent,
    input-immutability, single-read-path).
  - `test_eval_v3_scorer.py`: 11 (supported/confirmed/wrong/duplicate/
    rejected-only discovery, evidence linkage, 3 verification states,
    unsupported-confirmation penalty, missing-truth unavailable,
    correct-null, 2× v2-preservation pins).
  - `test_eval_v3_verification.py`: 7 (plan records expectations without
    spending, unknown-hypothesis, all 8 reason codes + invalid default,
    status rollup, no-eligible explains itself, real independent probe
    executes offline, already-measured refuses without spending).
  - `test_eval_v3_regression.py`: 5 (v2 reproduces all 4 archived music
    scorecards exactly; M22 v3 expectations; M19 v3 full-credit;
    version/unavailable honesty).
- One real bug found by the new tests and fixed (cause, not symptom):
  v2 list entries without refs shadowed ref-rich fallback records in
  `_collect_hypotheses` (M22 evidence read 0.64, "only supports"); fixed by
  ref-preferring dedupe → evidence 1.0 with both relations. Full suite
  re-run green after the fix.
- Intermediate failure also fixed at cause: `_numbers_only` called without
  the new `tool` parameter (NameError) — signature + call site corrected,
  affected suites re-run green, then full suite green.

## 2. M22 regression (offline re-evaluation, persisted artifacts only)

v3 on `m22-live-01`: discovery **0.7** (supported cold-start, overlap 0.67),
evidence **1.0** (5/5 linked, both relations), verification **0.0** (nothing
recorded), confirmation **0.7** (honest partial), efficiency 0.18 (base 0.2
× duplicate-discount 0.9 for the repeated ranking diagnostic; 8 exps),
reproducibility 1.0 → overall **0.66**, verdict `honest_partial`.
Correct per spec: discovery credited, no fabricated verification/
confirmation, partial not treated as total failure, M22 confirmed-hypothesis
counterfactual still resolves to the documented 0.2→(v3: confirmation gated
by numbers, which now pass).

## 3. Sensitivity analysis (weight ±0.10, M22 dims)

Base 0.660. discovery ±: 0.656/0.664. evidence ±: 0.622/0.691.
verification ±: 0.733/0.600. confirmation ±: 0.656/0.664.
Range 0.60–0.73: the qualitative reading (found with evidence, unverified,
honestly partial) never flips to "confirmed" or "total failure". Weights are
documented as judgment, not fitted — no weight was chosen to make M22 pass.

## 4. Remaining gates

- Frontend `tsc --noEmit`: exit 0. Production build: exit 0 (chunk-size
  warning pre-existing, unrelated).
- Secret scan over all new/changed files: clean (no keys, no bearer tokens).
  Network scan: no new outbound URLs (only pre-existing provider/docs URLs
  in untouched code paths). Demand Zone AI: zero diffs.
- Calibration rationale: threshold chosen by documented method (test-suite
  floor 0.15), NOT fitted to 0.1695; fixture + truth + v2 band preserved.
- No external AI calls, no spend, no live investigation replayed.

## 5. Limitations

v3 evidence on pre-fallback archive shapes (m16/m17/m21) is 0.0 with notes
(records lack embedded refs — honest, not a bug); efficiency punishes the
8-experiment M22 run (0.2) by inherited v2 design; verification dimension on
v2 archives reads `[]` as 0.0/"no verification recorded" (cannot distinguish
"unrecorded" from "absent" historically).
