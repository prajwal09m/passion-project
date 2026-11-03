"""M15 Phase 1.1: performance reconnaissance (offline, read-only)."""
from __future__ import annotations


def recon(df, target: str, feature_cols: list[str]) -> dict:
    import pandas as pd
    y = df[target]
    return {
        "n": int(len(df)),
        "period": [str(df["date"].min()), str(df["date"].max())],
        "base_rate": round(float(y.mean()), 4),
        "n_features": len(feature_cols),
        "null_share": round(float(
            df[feature_cols].isna().mean().mean()), 4),
        "class_balance": {
            "neg": int((y == 0).sum()), "pos": int((y == 1).sum())},
        "bottleneck_notes": [
            "base rate ~0.2: imbalance handling is a live hypothesis",
            "444 raw columns reduced by leakage exclusion + null "
            "filter; representation quality untested",
            "capacity/regularization/optimization unknown until "
            "candidates are measured",
        ],
    }
