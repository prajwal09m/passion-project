# Milestone 4 — Results and Limitations (offline, 2026-11-01)

Official run: `benchmarks/eval_runs/eval-6247993ca658/`
(manifest present; reruns mint new IDs; supersedes the pre-fix run
`eval-169efa3d3c00`, retained for audit). 8 projects, deterministic
investigator, zero provider calls.

## Per-project results

| Project | Verdict | Overall | Evidence |
|---|---|---|---|
| eval_credit | correct | 1.00 | subgroup named; group_gap 0.46; delinq distractor NOT claimed |
| eval_rent | correct | 1.00 | segment bias; group MAE spread ~6x |
| eval_turbine | correct | 1.00 | level-shift drift 7.0→24.3, overlap correctly False |
| eval_docs | correct | 1.00 | instability; silhouette 0.334 < 0.4 bar |
| eval_music | correct | 1.00 | cold-start collapse; slice P@K gap 0.60 |
| eval_claim | partial | 0.62 | bias + featcorr(−0.97) present but mechanism only symptom-named |
| eval_wellness | correct-null | 1.00 | nothing confirmed on clean project |
| eval_pilot | inconclusive | 0.94 | nothing fabricated at n=120 (correct handling) |

Aggregate mean overall: **0.945**. Verdicts: 5 correct, 1 correct-null,
1 partial (by design), 1 inconclusive (correct handling).

## Diagnostic corrections made during M4 (root-caused, tested)

1. **`forecast_diagnostics` split-overlap check was wrong**: sorted-key
   string comparison (`max(test) >= min(train)`) reported overlap for
   any chronological train/test split. Fixed to proper interval
   intersection. Consequence: M3's energy fixture has NO true date
   overlap (contiguous spans) — its "overlap detected" history was an
   artifact of this bug; its drift finding was and remains real. Two
   M3 unit assertions that encoded the buggy `True` were corrected
   with dated comments (fixture bytes, ground truth, M3 reports frozen;
   M3 suite still 26/26 green on the drift signal).
2. **Clustering instability bar unreachable**: k-means k=3 on
   unstructured data yields silhouette ≈0.34 (σ sweep 1.5–3.0), so the
   `<0.3` breach could never fire. Recalibrated to `<0.4` (weak
   structure) with measured rationale; M3 healthy control (0.72)
   unaffected.

## Limitations (what the numbers do NOT prove)

- The investigator is deterministic triage, not a live model: scores
  measure pipeline + threshold design, NOT independent ML reasoning.
- Co-design bias: fixtures and thresholds were built in the same
  milestone (some bars tuned to fixture values, disclosed above).
- n=1 scenario per family; synthetic, strong signals.
- No human reviews recorded yet (all runs report null reviews).
- Efficiency dimension is shallow (experiment counts only, no billed
  tokens — correctly, since nothing was billed).
