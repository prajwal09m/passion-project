# Milestone 10 Unseen Projects

Generator: `tests/fixture_m10/generate.py` (seed 20261101, frozen
outputs). All families differ from M9's eight.

| id | family | mechanism | artifact rows |
|---|---|---|---|
| m10_ward_gap | classification | east-ward subgroup degradation, pooled AUC hides it | 1500 |
| m10_proxy_signal | classification | `derived_flag` ≈ label (non-score near-duplicate) | 1500 |
| m10_threshold_skew | classification | scores +0.18 (systematic over-scoring) | 1500 |
| m10_stale_lag | forecasting | predictions lag target 3 steps | 300 |
| m10_district_scale | regression | district c logged in different units | 1200 |
| m10_combo | forecasting | drift + weak district-z gap together | 300 |
| m10_steady | regression | healthy (correct-null) | 1200 |
| m10_sparse | classification | n=60 (inconclusive required) | 60 |

The investigator receives only the one-line brief + artifact path
(see `scenarios.py`). Nothing names the mechanism, the key tool, or
the expected grade.
