# V2.0.58

## Hypothesis

[feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

## Changes and results

See `version.json` and `evaluation.json` for the immutable code/config, data fingerprints, metrics, robustness gates, and reproduction command.

## Decision

ACCEPTED relative to V2.0.57; all required checks passed.
