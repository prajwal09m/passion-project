# Milestone 4 — Scoring Methodology (rubric v2)

Implemented in `backend/eval/scorer.py`. Scored against concealed
ground truth using finding titles AND attached evidence numbers —
never title keywords alone.

## Dimensions A–F

| Dim | Weight | What is measured |
|---|---|---|
| Discovery (A) | 0.30 | mechanism named + numbers support, distractor discipline |
| Evidence (B) | 0.25 | linked experiments carry consistent numbers |
| Reasoning (C) | 0.15 | competing explanations considered, contradictions respected |
| Calibration (D) | 0.15 | null/inconclusive held where appropriate; no overclaim |
| Efficiency (E) | 0.05 | ≤4 experiments full marks, linear decay after |
| Reproducibility (F) | 0.10 | executive summary + experiment ids preserved |

`overall = Σ dim·weight` (weights sum to 1.0, asserted in tests).
Overall is reported WITH per-dimension values, never alone.

## Mechanism checks (bands, not exact values)

- subgroup: per-group AUC gap ≥ 0.10 on classification metrics.
- segment: group MAE spread ≥ 2x or |bias| > 100 or |resid feat corr| > 0.5.
- drift: late/early MAE ≥ 1.5x AND no split overlap.
- instability: silhouette < 0.4 or imbalance > 5.
- slice: per-slice P@K gap ≥ 0.20.
- input_dependence: residual–feature |corr| > 0.5 (or group/bias bands).

## Verdict taxonomy

- **correct**: mechanism named + numbers support, no false positive.
- **partial**: symptom found but mechanism unidentified (claim), or right
  mechanism plus a confirmed distractor.
- **incorrect**: wrong mechanism confirmed, or any confirmation on a
  no-failure project.
- **unsupported**: mechanism named without supporting numbers.
- **inconclusive**: failure missed entirely (with note on evidence
  sufficiency) — or the CORRECT handling of a weak-evidence case.
- **correct-null**: no confirmation where nothing was planted.

## Calibration incentives

False positives are penalized explicitly (`false_positive` flag +
discovery downgrade): claiming the delinq leak on credit or split
leakage on turbine costs the run. Confirming nothing on wellness/pilot
earns full calibration. Distractor markers: credit {leak, proxy},
turbine {leak, overlap}, pilot {leak, bias, drift, subgroup, proxy}.
