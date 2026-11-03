# M22 Implementation Report — Investigation Inaction & Completion Gating

## Root cause addressed

M21 (`m21-music-01`): the model returned text with zero hypotheses and
zero tool calls; the loop ended the round, the repair produced a valid
summary, and the driver mistook that valid report for a completed
investigation (`driver.py:235`). Total inaction was recorded as
`completed-turn` with `incomplete_progression:false`.

## Exact files changed

- `backend/meta_api/loop.py` — P0 total-inaction flag + progress in the
  turn decision; P0 zero-action recovery (one bounded resume round);
  P1 `_classify_turn_progress` (no-activity / activity-without-evidence
  / diagnostic-progress / sufficient-evidence); `_ran_new_turn`
  counter. No validation, repair, consistency, or budget logic touched.
- `backend/live/driver.py` — P0 evidence floor on the valid-summary
  break; run status `inconclusive` (not `completed`) when zero ran
  actions exist, with a recorded event.
- `backend/live/resume.py` — same two changes (mirrored).
- `backend/causal/planning.py` — `stopping()` distinguishes "no
  hypotheses on record" from "all resolved" (decision unchanged, only
  the recorded rationale is now honest).
- `tests/test_m7_closed_loop.py` — one assertion updated to the honest
  rationale (see below) + old text pinned for the truly-resolved case.
- `tests/test_m22_investigation.py` (NEW, 11 tests).
- P1 brief reorder deliberately NOT implemented: `plan_next` takes no
  task/mode signal, so task-targeted ranking would need signature
  changes and ripple through callers/tests for speculative gain; the
  recovery nudge already surfaces the brief's top pick dynamically.

## Design decisions

- Evidence, not counts: the floor requires ≥1 `ran` action, the only
  recorded proof of measurement. No arbitrary minimums.
- Recovery is gated to the exact M21 shape (prose-only round, zero
  hyps on record, rounds remaining, once per turn) so M8/M19/M20 flows
  (valid-summary turns, prose-with-hyps repairs, empty-output
  fallbacks) behave byte-identically — verified by their suites
  passing unmodified.
- `incomplete_progression` flips only where no deferral reason exists,
  preserving the M19 decline-with-reason contract.
- Failure modes terminate through existing honest paths (stall rule,
  stopping rule, caps); no new loops were created.

## Completion-state changes

- Driver/resume: valid summary + zero ran actions → continue, not
  break; run with zero ran actions → status `inconclusive`, never
  `completed`. Runs with any ran action are unaffected (M8 budget test
  still completes).
- Turn decision now carries `total_inaction` and `progress`; total
  inaction without a recorded next step marks `incomplete_progression`
  true.

## Tests added (11, all mocked-provider, zero live calls)

M21 replay flagged; recovery sent once; recovery resumes to real
diagnostics; no recovery when hyps exist (M20 path intact); failed
diagnostic = activity-without-evidence; classifier unit (4 states);
empty run never completes; persistent silence bounded + honest stop;
stall bound with reservation evidence; evidence run still completes;
floor break with evidence + valid summary.

## Test results

Full suite **646 passed, 0 failed** (635 pre-existing + 11 new).
`tsc --noEmit` clean; Vite build succeeds; separation/credential/
network scans clean; no live calls; frozen artifacts untouched.

Two development failures fixed at cause: (1) four legacy adapter
tests broke because recovery fired on valid-summary-only turns —
fixed by narrowing recovery to prose-only rounds (production cause,
tests untouched); (2) M7's stopping test asserted the old misleading
"resolved" text for an empty roster — the M22-mandated honest rationale
required updating that assertion (explained here), with the old text
re-pinned for the genuinely-resolved case. No test weakened: every
updated expectation is stricter or equally strict about honesty.

## Known limitations

- Recovery fires only for prose-only silence; a model emitting empty
  blocks or bare JSON with zero hyps takes the repair/fallback path
  (unchanged M20 behavior).
- `_verify_ready` proxy for sufficient-evidence is turn-level and
  heuristic; the resolution contract remains authoritative.
- Silent-model recurrence live is untested by design (no live calls).

## Remaining risks

A model that proposes hypotheses but never runs diagnostics across
all rounds still burns attempts until stalls/caps stop it (honest but
wasteful); first-turn brief quality is unchanged; live-model
compliance with the nudge is unverified and needs an authorized run.
