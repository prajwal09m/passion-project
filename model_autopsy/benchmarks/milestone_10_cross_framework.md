# Milestone 10 Cross-Framework Validation

Measured by `backend/m10/cross_framework.py` (`test_cross_framework_reports_honestly`).

- scikit-learn 1.x: LogisticRegression + RandomForestClassifier fit
  on synthetic tabular (600×8), predict_proba → real
  `classification_metrics` (AUC reported per model). Supported:
  fit, predict_proba, classification_metrics.
- PyTorch: 4→16→1 MLP regressor (60 Adam steps), predictions →
  real `regression_metrics` (R² reported). Supported: fit-mlp,
  predict, regression_metrics. Sequence models not exercised.
- TensorFlow: not installed — NO validation claimed.
- Hugging Face: not installed — NO validation claimed.

Framework generality beyond (sklearn classification, torch
regression) is unproven and not claimed.
