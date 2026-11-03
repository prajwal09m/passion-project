# Supported Models and Frameworks (verified 2026-10-31)

Distinction: **implemented** (works now) vs **tested** (exercised by the suite)
vs **planned** (interface only). Nothing below is claimed from an interface alone.

| Framework | Status | Tested | Capabilities when usable |
|---|---|---|---|
| black_box (predictions file) | implemented | yes (5 scenarios) | prediction_inspection, error_analysis, calibration, data_leakage_checks, reproducibility |
| sklearn | implemented | yes (LogReg fit/predict/importance) | + feature_importance when estimator exposes it |
| xgboost | implemented | yes (fit/predict) | same as sklearn |
| lightgbm | implemented | yes (fit/predict) | same as sklearn |
| catboost | implemented | yes (fit/predict) | same as sklearn |
| pytorch | partial (predict-only) | yes (forward pass) | prediction_inspection, error_analysis; gradients/activations honestly absent |
| api (remote) | implemented | yes (fake transport) | prediction_inspection, error_analysis |
| tensorflow | planned (guarded stub) | no (not installed) | use black-box predictions adapter instead |
| huggingface | planned (guarded stub) | no (not installed) | use black-box predictions adapter instead |

Environment at verification: sklearn 1.9, xgboost/lightgbm/catboost/torch
importable; tensorflow/transformers absent. Black-box investigation needs only
a predictions CSV — no weights, no framework, no API access.
