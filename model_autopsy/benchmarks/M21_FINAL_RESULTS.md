# M21 Final Results — Reporting Reliability & Scientific Integrity Validation

## 1. Executive summary

M21 asked whether M20's reporting guarantees survive real live-model
behavior — valid, malformed, incomplete, contradictory, or missing
structured output. Offline answer: the lifecycle is fully traced, the
ten scientific-integrity failure modes are pinned by tests, the
live-boundary harness recording is verified end to end, and the one
real gap found (native-report consistency findings were recorded where
no human looks) is fixed by surfacing, not by silent enforcement.
Full suite: **635 passed, 0 failed**. Zero live calls, zero spend,
M19/M20/Demand-Zone untouched. The live question itself remains
unrun by mandate — the proposal is ready for review.

## 2. Implemented

- M21 evaluation protocol (10 definitions + 13-scenario matrix S1–S13).
- End-to-end architecture audit with per-stage contracts and the
  recorded-not-rejected verdict (§3 of the audit).
- Read-only native consistency advisory: `engine` attaches
  `consistency_passed/failures/warnings` to valid results and summary
  events; `api` causal view exposes them; `CausalPanel` renders one
  muted line for native reports with findings. Additive only.
- `tests/test_m21_reporting.py`: 27 tests, mocked provider only.

## 3. Offline tested

635/635 full suite (608 pre-existing + 27 new). M19 35/35, M20 53/53,
adapter 25/25, M9/M10/API 60/60. tsc clean, Vite build succeeds,
separation/credential/network scans clean. Four development failures
fixed at cause (validation doc §3); no test weakened, no existing
test modified.

## 4. Live tested

One authorized investigation, `live_runs/m21-music-01` (`eval_music`):
S2→S8 demonstrated live (prose → valid consistency-gated repair,
`model_repaired`), honest `inconclusive` on zero evidence, no §2.10
violation, $0.020448 of $0.65. Full account:
`M21_LIVE_VALIDATION_RESULTS.md`. S1/S3–S7/S9 stay live-unverified.

## 5. Not yet demonstrated

- Whether the live model complies with the reporting contract.
- Whether organic S2–S9 classes resolve as the fixtures predict.
- Verification-then-confirmation under a live budget.
- Advisory signal-to-noise on free live prose.
These are exactly what the proposal's single investigation measures.

## 6. Known limitations

- Advisory regexes conservative by M20 design (substring `confirm`,
  decimal/percentage numbers, traceability-not-NLU contradictions).
- Validation-time advisory predates the resolution contract; the
  adapter-time check over final state is authoritative.
- Single fixture family, mocked provider; one scenario proposed live.
- Native record-not-reject stands: a human can still ignore the
  advisory line. Enforcement is deferred to a later milestone with
  explicit authorization — deliberately NOT smuggled into M21.

## 7. Acceptance checklist (§10 of the milestone)

- [x] Lifecycle audited end to end (audit doc §§1–2, 4–5).
- [x] Protocol + scenario matrix documented.
- [x] Integrity failure modes covered by tests (13 tests, §4 modes).
- [x] Native/repaired/fallback provenance distinguishable (pinned).
- [x] M19/M20 preserved (frozen paths clean; suites green unmodified).
- [x] All offline gates pass (validation doc §1).
- [x] Live-validation proposal ready for review.
- [x] No paid calls or live investigations made.
- [x] No M22 work started.
