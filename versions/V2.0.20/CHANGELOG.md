# V2.0.20

## Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=B, n_boot=500, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

## Changes and results

See `version.json` and `evaluation.json` for the immutable code/config, data fingerprints, metrics, robustness gates, and reproduction command.

## Decision

ACCEPTED relative to V2.0.19; all required checks passed.
