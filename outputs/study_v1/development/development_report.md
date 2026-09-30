# Frozen v1 historical development run (not prospective)

Protocol: `DZAI-MARKET-STRUCTURE-ABLATION-V1` · SHA-256 `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`  
Code SHA-256: `29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b`  
Data: 61,045 candidate events; 61,045 mature labels; 41,221 OOF-scored events; 149 roster symbols; 2021-08-03–2025-12-31

Unscored historical development rows: 19,824. They are excluded from all eight validation score sets.

Target: next-session open entry, following-session open exit; positive iff return ≥2%. Positive rate: 0.1758.

> **Retrospective development only.** These rows were already historical and cannot substitute for the 12-month/2,000-event prospective evaluation. No result is a profitability claim.

## Pooled out-of-fold metrics (2023–2025 chronological validation)

| Estimator | Arm | Events | Positive rate | Pooled ROC-AUC | PR-AUC | Mean daily ROC-AUC (2-class days) | Top-5% per-date precision | Same-date base rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LogisticRegression | A | 41,221 | 0.1648 | 0.5901 | 0.2324 | 0.5883 (728) | 0.2835 | 0.1612 |
| LogisticRegression | B | 41,221 | 0.1648 | 0.6608 | 0.2688 | 0.6815 (728) | 0.3257 | 0.1612 |
| LogisticRegression | C | 41,221 | 0.1648 | 0.6603 | 0.2663 | 0.6752 (728) | 0.3252 | 0.1612 |
| LogisticRegression | D | 41,221 | 0.1648 | 0.6596 | 0.2655 | 0.6732 (728) | 0.3168 | 0.1612 |
| LightGBM | A | 41,221 | 0.1648 | 0.6718 | 0.2610 | 0.6692 (728) | 0.3010 | 0.1612 |
| LightGBM | B | 41,221 | 0.1648 | 0.6778 | 0.2739 | 0.6931 (728) | 0.3070 | 0.1612 |
| LightGBM | C | 41,221 | 0.1648 | 0.6835 | 0.2768 | 0.6940 (728) | 0.3095 | 0.1612 |
| LightGBM | D | 41,221 | 0.1648 | 0.6848 | 0.2748 | 0.6944 (728) | 0.3090 | 0.1612 |

## Paired AUC contrasts (weekly block bootstrap)

| Contrast | Δ pooled ROC-AUC | 95% block-bootstrap interval |
|---|---:|---:|
| primary_LightGBM_A_minus_LogisticRegression_A | +0.0818 | [0.0658, 0.0990] |
| primary_LightGBM_C_minus_LightGBM_B | +0.0057 | [0.0022, 0.0092] |
| secondary_LogisticRegression_B_minus_A | +0.0707 | [0.0503, 0.0947] |
| secondary_LightGBM_B_minus_A | +0.0060 | [-0.0086, 0.0217] |
| secondary_LogisticRegression_C_minus_B | -0.0004 | [-0.0044, 0.0035] |
| secondary_LogisticRegression_D_minus_C | -0.0007 | [-0.0034, 0.0019] |
| secondary_LightGBM_D_minus_C | +0.0013 | [-0.0019, 0.0051] |

## Fold-level AUC

| Fold | Train n | Validation n | Logistic A/B/C/D | LightGBM A/B/C/D |
|---|---:|---:|---|---|
| 2023 | 19,765 | 13,924 | 0.6093, 0.6655, 0.6755, 0.6707 | 0.6696, 0.6881, 0.6907, 0.6920 |
| 2024 | 33,680 | 13,180 | 0.5840, 0.6750, 0.6759, 0.6769 | 0.6798, 0.6685, 0.6801, 0.6806 |
| 2025 | 46,827 | 14,117 | 0.5742, 0.6803, 0.6708, 0.6726 | 0.6670, 0.6876, 0.6898, 0.6904 |

## Limits and prospective status

- Local Yahoo-derived, auto-adjusted historical snapshots are not point-in-time data vintages; vendor back-adjustments/corrections are unverified.
- The fixed 149-ticker roster may be selected/survivorship-biased; point-in-time universe membership is unavailable.
- Demand-zone and order-block events are heuristic, conditional samples, not all-stock/all-date opportunities.
- No returns/profitability claim follows from AUC, PR-AUC, or top-k event precision.
- No prospective prediction exists until a post-lock date with fresh finalized OHLCV has been logged before its outcomes.

No confirmatory or prospective conclusion is available from this report.
