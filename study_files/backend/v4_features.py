"""
V4 Feature Computer — extends the base feature dict with V4-specific engineered
features (interaction terms, target encoding) so the V4 CatBoost model receives
the same 407 features at inference as it did at training.
"""
import json
import numpy as np
from pathlib import Path

_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "v4"

# Interaction pairs (same as train_v4.py)
_INTERACTION_PAIRS = [
    ("atr_pct", "vix_percentile_60d"),
    ("daily_return", "spy_return_5d"),
    ("rel_volume", "vix_level"),
    ("dist_ema_20_pct", "rsi_14"),
    ("distance_to_zone_pct", "zone_age_days"),
    ("spy_return_20d", "qqq_return_20d"),
    ("departure_volume_ratio", "body"),
]

# Fallback if rs_spy_5d not available
_ALT_PAIR = ("relative_strength_spy_20d", "spy_return_20d")

# Global target encoding (pre-computed during training, loaded on demand)
_target_encoding = None


def _load_target_encoding():
    """Load pre-computed ticker hit rates from training metadata."""
    global _target_encoding
    if _target_encoding is not None:
        return _target_encoding
    try:
        meta = json.load(open(_MODEL_DIR / "v4_metadata.json"))
        _target_encoding = meta.get("target_encoding", {})
    except Exception:
        _target_encoding = {}
    return _target_encoding


def extend_features(features: dict, symbol: str = "",
                    month_hitrate: float = None) -> dict:
    """Add V4 engineered features to an existing features dict.

    Args:
        features: Base feature dict from features_from_row() or v2_features
        symbol: Ticker symbol for target encoding lookup
        month_hitrate: Monthly average hit rate (optional, uses 0.196 default)

    Returns extended dict (mutates and returns input).
    """
    base_rate = month_hitrate if month_hitrate is not None else 0.196

    # ── Interaction features ──
    pairs = list(_INTERACTION_PAIRS)
    # Add the alt pair if rs_spy_5d is available, otherwise use the fallback
    if "rs_spy_5d" in features:
        pairs.append(("rs_spy_5d", "gap_pct" if "gap_pct" in features else "spy_return_5d"))
    else:
        pairs.append(_ALT_PAIR)

    for a, b in pairs:
        va = float(features.get(a, 0))
        vb = float(features.get(b, 0))
        features[f"inter_{a}__{b}"] = va * vb
        features[f"rat_{a}__{b}"] = va / (abs(vb) + 0.001)
        features[f"sum_{a}__{b}"] = va + vb

    # ── Target encoding ──
    enc = _load_target_encoding()
    features["ticker_hist_hitrate"] = float(enc.get(symbol, base_rate))
    features["month_hitrate"] = float(base_rate)
    features["ticker_hitrate_trend"] = features["ticker_hist_hitrate"] - features["month_hitrate"]

    return features
