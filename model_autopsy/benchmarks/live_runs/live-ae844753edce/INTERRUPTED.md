# INTERRUPTED — not finalized (read this first)

Run `live-ae844753edce` (M6, project `eval_claim`) was interrupted by an
operator tool timeout (60 s) during round 2 — not by the model, the
governor, or a budget cap. No manifest exists in this directory, which
means the run is NOT finalized (per M5 limitation #4: no manifest = not
finalized). Nothing here has been repaired, resumed, or re-run.

Preserved as-is:
- `live.sqlite3` — 1 investigation, 24 events, 4 actions (3 ran), 3 hypotheses.
- Recorded provider usage at interruption: 2 attempts, 8,687 input tokens
  (4,081 cached), 837 output tokens — approx $0.0099, far below all caps.

Do not treat this directory as a completed evaluation. See
`benchmarks/milestone_6_results.md` for the full honest record.
No second run was launched (M6 §8: a failed run is recorded and stops).
