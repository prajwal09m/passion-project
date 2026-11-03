# Model Adapter Development Guide

## Interface (`backend/model_adapters/`)
Subclass `ModelAdapter` and set `framework`:
- `is_available()` (classmethod) — honest probe: library importable AND adapter implemented.
- `capabilities()` — subset of the 8 declared capabilities; raise `CapabilityError` only if the adapter cannot function at all.
- `require(capability, alternative)` — guard diagnostics; always name an alternative.
- `describe()` — free status report (used by `/api/model-frameworks`).

## Capability contract
`prediction_inspection`, `error_analysis`, `calibration`, `data_leakage_checks`,
`reproducibility`, `feature_importance`, `gradient_analysis`, `internal_activations`.
Claim only what the adapter truly supports. Black-box adapters must never
claim internals; diagnostics that need an absent capability must explain why
and suggest the alternative (the registry enforces this via `select_tools`).

## Patterns in this repo
- `BlackBoxPredictionsAdapter`: predictions-file only (the universal fallback).
- `SklearnAdapter` / `SklearnCompatAdapter` (xgboost, lightgbm, catboost): local estimator + optional importances.
- `PyTorchAdapter`: predict-only; gradients/activations honestly absent.
- `ApiModelAdapter`: remote predictions only; credentials live with the caller, never here.
- Guarded stubs (tensorflow, huggingface): report unusable with the exact missing piece.

## Rules
- Never fabricate unsupported internals (no fake importances/gradients).
- `predict()` must work offline in tests via injected estimator/module objects.
- Register in `_ADAPTERS` under the framework key.
