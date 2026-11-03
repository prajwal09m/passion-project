# M22 Independent Validation Report — Offline, No Prod Edits

Stage 2 of M22. No production code was modified during validation; no
live calls; no spend. Evidence: `tests/test_m22_validation.py`
(10 scenarios) + full-suite regression counts.

## Scenario results (expected vs actual)

| # | Scenario | Expected | Actual | Result |
|---|---|---|---|---|
| V1 | Zero hyps + zero calls | flagged `total_inaction`, `no-activity` | decision carries both; `incomplete_progression` true | PASS |
| V2 | Zero-action + valid report | run cannot complete | driver status `inconclusive`, 0 experiments | PASS |
| V3 | Recovery produces evidence | resume → ran measurement, progress advances | `total_inaction` false, progress diagnostic+ | PASS |
| V4 | Failed recovery | exactly 1 nudge, honest stop | 3 api calls (2 rounds + repair), 1 prompt, incomplete true | PASS |
| V5 | Calls without evidence | activity, not progress | `activity-without-evidence`, `total_inaction` false | PASS |
| V6 | Meaningful evidence | conclusion-capable, complete turn | progress diagnostic+/sufficient, incomplete false | PASS |
| V7 | Genuinely inconclusive | contract stays `unresolved` | `resolve.contract` → `unresolved`, note intact | PASS |
| V8 | M19 decline | incomplete preserved, no M22 recovery | incomplete true; zero-action prompts absent | PASS |
| V9 | M20 repair | 2 calls, `repaired_via` | api_calls == 2, repair accepted | PASS |
| V10 | M21 empty fallback | direct deterministic fallback | no repair, fallback kind correct | PASS |

## Regression results

Full suite **656 passed, 0 failed** (635 pre-M22 + 11 M22 impl + 10
validation). M19 35/35, M20 53/53, adapter 25/25, M7 stopping updated
for honesty (old text pinned for the truly-resolved case), M9/M10/API
green. `tsc` clean, Vite build succeeds.

## Completion-state agreement

Empty runs report `inconclusive` at manifest + run level while the
resolution contract reports `unresolved` — statuses agree (no false
completion). Evidence runs report `completed` with fallback or native
provenance intact.

## Boundedness / safety

Recovery: one nudge per turn (event-counted), normal budget/headroom
gates on re-dispatch, stall + stopping + caps terminate. No infinite
loops observed (all runs return). No crashes, no inconsistent states.

## Limitations

Mocks script provider text; live-model compliance with the nudge is
unverified (needs authorized run). Single fixture family. The
`sufficient-evidence` proxy is turn-level; the resolution contract
remains authoritative.

## Verdict: PASS

All 10 scenarios behave as required; regressions green; no bypass of
the evidence floor found offline. This judges the offline
implementation only — not whole-project readiness, and not live
reliability.
