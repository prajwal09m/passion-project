# M16 Phase 2 — Readiness Report (Preparation Complete)

## Verdict: READY for authorized live evaluation, with the bounds below.

## What was verified (offline, no spend)
- 17/17 Phase 1 tests pass (reservation, budget, slice P@K, thin-slice
  guards, aliases, adequacy gates ×2, M14/M7 replays, denier handling,
  single-support non-promotion, skeptic challenge/probe/dissent,
  no-duplicate-spend, grounded summary).
- Full suite green required before authorization (475/475 at last full
  run + 1 new test since; §7 re-runs the suite and blocks on it).
- Corroboration, caps, scorer, M9/M10 grades, sealed separation, and
  historical artifacts all untouched (diff-clean per §1 of the protocol).
- One concrete defect found and fixed in prep: skeptic dropped all but
  the first blocking challenge and could charge budget for engine-dedup
  reuse. Fixed (per-challenge loop with refreshed snapshots;
  release-on-reuse) and covered by the no-duplicate-spend test.

## Must-fix before live: NONE open.

## Authorization requested (not assumed)
- Minimum campaign: arms B+C × 5 runs on eval_music (10 runs,
  est. $0.31–0.58).
- Preferred campaign: + arm A × 5 music + arms B+C × 5 credit
  (25 runs, est. $0.8–1.5).
- Per-run caps unchanged (3 rounds / 6 exps / 12 attempts / 50k tokens /
  $0.40); protocol pinned to its git hash at approval; any cap breach
  invalidates that run (disclosed, not hidden).

## Residual risks (accepted, monitored per-run)
- Ranking-claim vocabulary is narrow by design (regression-avoidance);
  paraphrased top-K claims may evade the gate — counted as
  attribution errors if observed live.
- Reservation fires first turn only; late-hypothesis revisions get no
  second reservation (recorded gap, not a silent behavior).
- n=5 per arm is variance-estimation scale, not proof scale; the only
  preregistered claimable test is a 5-vs-0 Fisher exact (or nothing).

STOP. Awaiting explicit authorization to spend anything live.
