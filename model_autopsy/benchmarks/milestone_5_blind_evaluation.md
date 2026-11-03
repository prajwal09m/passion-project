# Milestone 5 — Blind Evaluation

## Freeze order (enforced by driver sequence)

Investigation → frozen final report → adapter → automated scoring →
human-review package. The scorer never runs before `engine.finalize`;
ground truth is loaded only inside `scorer.score`, after the report is
frozen. The driver imports truth solely to pass it to the scorer
post-freeze (source test pins this).

## Automated scoring (M4 rubric, unchanged weights)

Dimensions A–F (0.30/0.25/0.15/0.15/0.05/0.10): discovery, evidence,
experimental reasoning, calibration, efficiency, reproducibility.
Verdict taxonomy: correct / partial / incorrect / unsupported /
inconclusive / correct-null. Mechanism bands check attached numbers
(drift-without-overlap for turbine), false-positive markers penalize
leakage/overlap claims. Overall accompanies dimensions, never alone.

## Separation from the deterministic baseline

The M4 0.945 measures the deterministic pipeline on 8 projects. The
live pilot score measures one live model on one project. They are
reported side by side, never ranked against each other, never averaged.

## Human review

M4 blind-then-reveal workflow applies to the preserved live run
(`live_runs/{id}/` + scorecard): blind verdict on report + evidence
first, ground-truth reveal only after. No review is fabricated; status
`pending` until a real reviewer acts. Dashboard shows human-review
status from the same store shape as M4.
