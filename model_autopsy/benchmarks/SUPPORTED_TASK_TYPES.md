# Supported Task Types (verified 2026-10-31)

| Task | Diagnostics (real) | Tested | Notes |
|---|---|---|---|
| classification | artifact_summary, dataset_validation, classification_metrics, calibration_and_error_analysis, time_split, leakage screening, grouped AUC | yes (Demand Zone live campaigns + clinic/black-box fixtures) | binary labels; fold optional since universalization |
| regression | regression_metrics (MAE/MSE/RMSE/R², residuals, heteroscedasticity, outliers, bias, per-group) | yes (house-price bias scenario) | any numeric target/prediction columns |
| forecasting | forecast_diagnostics (horizon error, drift, residual autocorr, split overlap) + time_split | yes (energy overlap+drift scenario) | needs date column; horizon/split optional |
| clustering | clustering_stability (silhouette, sizes, imbalance) | yes (separated-blobs control) | k-means screening; descriptive, not a structure claim |
| ranking | interface + selection ready | no (no metrics yet) | planned: NDCG/MAP/P@K — honest gap |
| other | dataset_validation, capability_report | partial | schema/quality only |

Selection is capability-aware (`select_tools`): wrong-task tools are excluded
with reasons; missing inputs/capabilities are reported, never faked.
