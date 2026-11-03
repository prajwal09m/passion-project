# Blinded scoring packet RUN-02

- Campaign: Meta final validation 2026-10-31; condition withheld
- Rubric: phase_d_blind_scoring_rubric_v1.md (frozen 2026-10-29)

## 1. Turn-2 final assistant message (verbatim)

(EMPTY - no final message text)

## 2. Parsed structured summary block (from turn-2 text, if any)

(none)

## 3. Structured-summary validity (kept separate from quality)
- First-attempt valid: see campaign record; post-repair valid: False
- Note: a valid block earns no quality points by itself.

## 4. Recorded actions (seq, tool, status)
- 4: propose_hypothesis [ran]
- 7: propose_hypothesis [ran]
- 10: propose_hypothesis [ran]
- 15: calibration_and_error_analysis [ran]

## 5. Recorded hypotheses (id, status, text-head)
- 8ad8ceed07ef4f71b906a6f4544e25e5 [proposed]: Model underperforms OOF because of weak overall discrimination — scores do not rank positives above negatives in any fold.
- 315e4e5db323446a981e5d57f5914ea6 [proposed]: Model underperforms OOF because of fold instability / distribution shift — pooled performance is dragged down by one or more bad folds, not uniformly weak ranking.
- c0d0b3a65230497a85711fd275adea79 [proposed]: Model underperforms OOF because of miscalibration / threshold mismatch — ranking is intact but predicted probabilities are systematically off, hurting thresholded metrics.

## 6. Budget and completion
- Tool calls executed: 4 (budget shared: 6 calls)
- Incomplete provider responses observed in run: 2
- Failed requests preserved: yes
