# V2.0.29

## Hypothesis

[feature_engineering] Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LightGBM, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

## Changes and results

See `version.json` and `evaluation.json` for the immutable code/config, data fingerprints, metrics, robustness gates, and reproduction command.

## Decision

ACCEPTED relative to V2.0.28; all required checks passed.
