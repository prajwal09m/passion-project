"""Model adapter architecture (Phase 3).

Each adapter declares what it CAN do via capabilities; diagnostics that
need an unsupported capability explain why and suggest alternatives
instead of fabricating results. Availability is probed honestly:
framework adapters whose libraries are not installed report
`available=False` with the missing dependency named.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


CAPABILITIES = (
    "prediction_inspection",   # inputs + outputs observable
    "feature_importance",      # only when the model exposes it
    "gradient_analysis",       # only with differentiable access
    "internal_activations",    # only with white-box access
    "error_analysis",          # predictions + ground truth
    "calibration",             # appropriate prediction scores
    "data_leakage_checks",     # dataset + pipeline information
    "reproducibility",         # training/environment metadata
)


class CapabilityError(Exception):
    """Raised when a diagnostic needs a capability the adapter lacks."""


class ModelAdapter:
    """Base class for model adapters."""
    framework = "unknown"
    availability = "black_box"

    def __init__(self, config: dict | None = None):
        self.config = dict(config or {})

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        """(available, reason). Honest probe — no import side effects."""
        return True, "generic adapter"

    def capabilities(self) -> list[str]:
        raise NotImplementedError

    def require(self, capability: str, alternative: str = "") -> None:
        if capability not in self.capabilities():
            hint = f" Alternative: {alternative}" if alternative else ""
            raise CapabilityError(
                f"{self.framework} adapter lacks capability "
                f"{capability!r}.{hint}")

    def describe(self) -> dict:
        ok, reason = self.is_available()
        return {"framework": self.framework, "availability": self.availability,
                "capabilities": self.capabilities(), "usable": ok,
                "reason": reason}


class BlackBoxPredictionsAdapter(ModelAdapter):
    """Black-box via a predictions artifact (CSV with label + score cols).

    The honest default: investigates through observable inputs/outputs only,
    never pretending at internal access.
    """
    framework = "black_box"
    availability = "black_box"

    def capabilities(self) -> list[str]:
        return ["prediction_inspection", "error_analysis", "calibration",
                "data_leakage_checks", "reproducibility"]


class SklearnAdapter(ModelAdapter):
    """Scikit-learn estimator adapter (local inference + importances)."""
    framework = "sklearn"
    availability = "local"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._estimator = (config or {}).get("estimator")

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        if importlib.util.find_spec("sklearn") is None:
            return False, "scikit-learn is not installed"
        return True, "scikit-learn importable"

    def capabilities(self) -> list[str]:
        caps = ["prediction_inspection", "error_analysis", "calibration",
                "data_leakage_checks", "reproducibility"]
        est = self._estimator
        if est is not None and (hasattr(est, "feature_importances_") or
                                hasattr(est, "coef_")):
            caps.append("feature_importance")
        return caps

    def predict(self, X):
        ok, reason = self.is_available()
        if not ok:
            raise CapabilityError(reason)
        if self._estimator is None:
            raise CapabilityError("no estimator configured; supply "
                                  "config['estimator']")
        return self._estimator.predict(X)

    def feature_importance(self) -> dict:
        self.require("feature_importance",
                     "use permutation-based screening on predictions instead")
        est = self._estimator
        if hasattr(est, "feature_importances_"):
            vals = est.feature_importances_
            method = "feature_importances_"
        else:
            vals = est.coef_
            method = "coef_"
        flat = list(vals.ravel()) if hasattr(vals, "ravel") else list(vals)
        return {"method": method, "values": [float(v) for v in flat]}


class SklearnCompatAdapter(ModelAdapter):
    """Real adapter for sklearn-API-compatible estimators
    (XGBoost, LightGBM, CatBoost): fit/predict + importances."""
    framework = "sklearn_compat"
    availability = "local"
    package = ""

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._estimator = (config or {}).get("estimator")

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        if importlib.util.find_spec(cls.package) is None:
            return False, f"{cls.package} is not installed"
        return True, f"{cls.package} importable"

    def capabilities(self) -> list[str]:
        caps = ["prediction_inspection", "error_analysis", "calibration",
                "data_leakage_checks", "reproducibility"]
        if self._estimator is not None and (
                hasattr(self._estimator, "feature_importances_") or
                hasattr(self._estimator, "coef_")):
            caps.append("feature_importance")
        return caps

    def predict(self, X):
        ok, reason = self.is_available()
        if not ok:
            raise CapabilityError(reason)
        if self._estimator is None:
            raise CapabilityError("no estimator configured; supply "
                                  "config['estimator']")
        return self._estimator.predict(X)


class XGBoostAdapter(SklearnCompatAdapter):
    framework = "xgboost"
    package = "xgboost"


class LightGBMAdapter(SklearnCompatAdapter):
    framework = "lightgbm"
    package = "lightgbm"


class CatBoostAdapter(SklearnCompatAdapter):
    framework = "catboost"
    package = "catboost"


class PyTorchAdapter(ModelAdapter):
    """Predict-only adapter for torch modules (no gradient/activation
    analysis in this build — those capabilities are honestly absent,
    with permutation-screening suggested as the alternative)."""
    framework = "pytorch"
    availability = "local"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._module = (config or {}).get("module")

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        if importlib.util.find_spec("torch") is None:
            return False, "torch is not installed"
        return True, "torch importable"

    def capabilities(self) -> list[str]:
        return ["prediction_inspection", "error_analysis"]

    def predict(self, X):
        import torch
        ok, reason = self.is_available()
        if not ok:
            raise CapabilityError(reason)
        if self._module is None:
            raise CapabilityError("no module configured; supply "
                                  "config['module']")
        import numpy as np
        self._module.eval()
        with torch.no_grad():
            out = self._module(torch.as_tensor(np.asarray(X, dtype=float),
                                               dtype=torch.float32))
        return np.asarray(out).reshape(len(np.asarray(X)))


def _guarded_framework_adapter(framework: str, package: str):
    class _Guarded(ModelAdapter):
        availability = "local"

        @classmethod
        def is_available(cls) -> tuple[bool, str]:
            if importlib.util.find_spec(package) is None:
                return False, f"{package} is not installed"
            return True, f"{package} importable"

        def capabilities(self) -> list[str]:
            raise CapabilityError(
                f"{framework} adapter is declared but not implemented in "
                f"this build; use BlackBoxPredictionsAdapter on its saved "
                f"predictions instead")
    _Guarded.framework = framework
    _Guarded.__name__ = framework.capitalize() + "Adapter"
    return _Guarded


TensorFlowAdapter = _guarded_framework_adapter("tensorflow", "tensorflow")
HuggingFaceAdapter = _guarded_framework_adapter("huggingface", "transformers")


class ApiModelAdapter(ModelAdapter):
    """Remote/API model: predictions only, no internals. No credentials here —
    endpoint configuration lives with the caller, never in this module."""
    framework = "api"
    availability = "api"

    def capabilities(self) -> list[str]:
        return ["prediction_inspection", "error_analysis"]


_ADAPTERS = {"black_box": BlackBoxPredictionsAdapter,
             "sklearn": SklearnAdapter,
             "xgboost": XGBoostAdapter, "lightgbm": LightGBMAdapter,
             "catboost": CatBoostAdapter, "pytorch": PyTorchAdapter,
             "tensorflow": TensorFlowAdapter, "huggingface": HuggingFaceAdapter,
             "api": ApiModelAdapter}


def get_adapter(framework: str, config: dict | None = None) -> ModelAdapter:
    try:
        cls = _ADAPTERS[framework]
    except KeyError:
        raise LookupError(f"unknown model framework {framework!r}; "
                          f"supported: {sorted(_ADAPTERS)}") from None
    return cls(config)


def supported_frameworks() -> list[dict]:
    out = []
    for name, cls in _ADAPTERS.items():
        ok, reason = cls.is_available()
        try:
            caps = cls({}).capabilities()
        except CapabilityError as exc:
            caps = []
            reason = str(exc)
        out.append({"framework": name, "usable": ok, "reason": reason,
                    "capabilities": caps})
    return out
