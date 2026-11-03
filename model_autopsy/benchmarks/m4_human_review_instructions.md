# Milestone 4 — Human-Review Instructions

## Principle

Automated scores are not enough. A reviewer must be able to judge
whether the conclusion is scientifically defensible — WITHOUT seeing
ground truth first (otherwise the review is biased by the answer).

## Workflow (enforced blind-then-reveal)

1. Open the run in **Evaluation**, drill into a project. Read ONLY:
   the brief, hypotheses, experiments + numbers, conclusions,
   limitations. Do NOT open `ground_truth_eval.json`.
2. Record a blind verdict (`defensible` / `questionable` /
   `not_defensible` / `cannot_tell`) with notes, attesting no prior
   exposure to ground truth. The store requires this BEFORE reveal
   (reveal without a blind verdict is refused and tested).
3. Reveal: the ground-truth mechanism summary is shown; record a
   post-reveal assessment. The blind verdict is preserved alongside,
   never replaced.
4. Reviews live in `{pid}.review.json` beside results, separate from
   automated scorecards. Absence of review is reported as absent.

## What to judge

- Does the evidence actually support the mechanism (numbers, not prose)?
- Was a plausible alternative (e.g. the documented distractor) ruled
  out for a reason, or merely not mentioned?
- Is a `correct-null`/`inconclusive` outcome justified, or is it a
  missed detection?
- Would another researcher reproduce this from the preserved artifacts?

## Status honesty

No human reviews have been fabricated: every completed M4 run to date
reports `human_review: null` until a real reviewer acts. Do not invent
reviewer identities, verdicts, or timestamps.
