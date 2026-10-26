# V2.0.30

## Hypothesis

[calibration] Measure Brier/ECE stability across chronological folds and years. (arm_pair=C->D, calibration_bins=5, estimator=LightGBM, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

## Changes and results

See `version.json` and `evaluation.json` for the immutable code/config, data fingerprints, metrics, robustness gates, and reproduction command.

## Decision

ACCEPTED relative to V2.0.29; all required checks passed.
