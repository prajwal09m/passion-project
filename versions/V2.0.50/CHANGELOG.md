# V2.0.50

## Hypothesis

[calibration] Measure Brier/ECE stability across chronological folds and years. (arm_pair=B->C, calibration_bins=10, estimator=LightGBM, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

## Changes and results

See `version.json` and `evaluation.json` for the immutable code/config, data fingerprints, metrics, robustness gates, and reproduction command.

## Decision

ACCEPTED relative to V2.0.49; all required checks passed.
