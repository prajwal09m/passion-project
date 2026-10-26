# V2.0.63

## Hypothesis

[validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=C->D, estimator=LightGBM, n_boot=500) reproduce deterministically under an independently parameterized re-run?

## Changes and results

See `version.json` and `evaluation.json` for the immutable code/config, data fingerprints, metrics, robustness gates, and reproduction command.

## Decision

ACCEPTED relative to V2.0.62; all required checks passed.
