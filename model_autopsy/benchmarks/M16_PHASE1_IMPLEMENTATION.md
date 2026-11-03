# M16 Phase 1 — Core Live Discovery Integration (Implementation Record)

Offline-first. No paid calls, no live investigations, no campaign
launches. All behavior below is proven by the 16 new offline tests in
`model_autopsy/tests/test_m16_phase1.py` plus the full 475-test suite.

## 1. What changed (files)

- `backend/live/reserve.py` (new) — P0-1: `select()` picks the top valid
  discriminating spec via `invention.propose/validate` (decisive/
  supporting only, never exploratory filler); `run_reserved()` enforces
  it pre-dispatch through the shared `Budget` (refused without budget,
  declines when <2 experiments remain so the model keeps control).
- `backend/meta_api/loop.py` — wires reservation once per investigation
  (guarded by existing `reservation` events); adds post-round
  skeptic-lite review (`live/skeptic.py`) that never breaks the turn;
  records `grounded` facts and grounds the summary-repair prompt.
- `backend/live/skeptic.py` (new) — P1-3: `review()` runs
  `m11.roles.skeptic` + granularity challenges (segment claim without
  segment-broken measurement; ranking claim without slice P@K),
  one budgeted probe via the invention engine, dissent preserved when
  budget/inventability fails.
- `backend/causal/selection.py` — registers `ranking_slice_diagnostics`
  and `segment_quality_screen` in costs + discrimination map.
- `backend/causal/planning.py` — both tools added to plan candidates.
- `backend/causal/attribution.py` — P1-1 adequacy gates in `classify()`:
  pooled-vs-segment (`relevant_to`, M14 shape) and AUC-vs-ranking-claim
  (`relevant_to`, narrowed to explicit top-K language after the m8-linker
  regression caught an over-broad trigger); `_SEGMENT_ARGS` extended
  with `slice_column`/`segment_column`.
- `backend/causal/linker.py` — P1-2: records `linker` no-bearing notes
  for hypotheses an action did not move (why-nothing-changed audit).
- `backend/research/invention.py` — P0-2: `artifact_facts()` now records
  `column_mapping` (label/score/segments + confidence high/medium/low)
  and `mapping_notes` (ambiguity → clarify; missing label → explicit
  limitation). Additive; existing keys unchanged.
- `backend/engine.py` — P1-2: `grounded_summary()` (record-only facts
  the model must explain, not regenerate).
- `backend/api.py` — `GET /api/investigations/{id}/m16` (reservation,
  skeptic, grounded, linker notes, status justifications; read-only).
- `frontend/src/api.ts`, `frontend/src/Workspace.tsx` — M16 section
  (reserved probe, skeptic-lite, grounded facts, status justifications;
  empty states when no live turn has run; no fabricated content).
- `tests/test_m16_phase1.py` (new, 16 tests).

## 2. Architecture delta (vs M16_PIPELINE_MAP.md)

- The live path now has three deterministic callers that previously
  existed offline-only: reservation (invention engine), skeptic-lite
  (team skeptic + granularity rules), adequacy-gated attribution.
- The model still picks its own tools; the reservation is 1 of 6 and
  the skeptic at most 1 of the remainder (shared Budget, pre-dispatch
  reservation — overrun impossible by construction).
- `info_value` remains a heuristic proxy (unchanged); the reservation
  prefers decisive/supporting specs and records the rationale instead
  of claiming information gain numbers.

## 3. Test results and regression comparison

- New: 16/16 pass (`test_m16_phase1.py`).
- Full suite: **475 passed** (459 pre-existing + 16 new), 0 failed.
- Regression incident during development: the first ranking-gate draft
  matched generic "ranking performance" prose and broke
  `test_per_region_auc_gap_links_subgroup_hypothesis` (supports became
  relevant_to). Fixed by narrowing the trigger to explicit top-K
  language (cause fix, not a weakened assertion); the M14 shape
  ("top results … cold-start") is still caught. Full suite re-run green.
- Gates: M9/M10 grades unchanged (challenge/validation tests green);
  `tsc --noEmit` clean; `vite build` succeeds; separation/truth-leakage
  tests green (suite); no credential handling touched; historical
  artifacts byte-identical (`benchmarks/` unmodified — git shows no
  tracked modifications there).

## 4. Old vs new metrics (reported separately, never merged)

- Old (unchanged): M9 means 1.0/1.0/1.0/0.938/0.75/0.625; M10 mean
  0.906; live scorecards frozen in run dirs.
- New (offline only): reservation selects a discriminating probe on
  music/ward fixtures; pooled-vs-slice misattribution blocked
  (M14 replay: zero moving links from pooled AUC to the slice H);
  skeptic fires granularity challenges and runs the slice probe with
  budget / dissents without; no live claims — live validation awaits
  authorization (see `m16_phase0/M16_EVALUATION_PLAN.md`).

## 5. Budget accounting

Reservation and skeptic probes both `budget.reserve("experiments", 1)`
before dispatch and `settle` after, inside the existing 6-experiment
cap and 12-attempt ceiling. Decline paths (no valid spec, <2 remaining,
budget refused, duplicate) record `reservation`/`skeptic` events with
reasons and spend nothing. Dedupe: exact-args duplicates are refused at
`invention.validate`; skeptic reuses the reservation spec shape when it
matches (recorded as reuse, no second spend).

## 6. Known limitations and unresolved issues

- The reservation fires once per investigation (first turn); later-turn
  re-reservation after hypothesis revision is future work.
- Skeptic-lite impact magnitude is unmeasured (offline probes only).
- Ranking-gate vocabulary is deliberately narrow; novel paraphrases of
  top-K claims may slip through as supports (audit, don't assume).
- No live evidence yet: all P0/P1 effects are offline-demonstrated.
- Demand-Zone target-model work untouched per constraints.
