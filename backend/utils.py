"""
Data loading utilities shared across backend modules.
Reuses existing pipeline code from ../Python/ wherever possible.
"""

import sys
import os
from pathlib import Path

# Add parent Python directory to path so we can import existing pipeline modules
_PARENT = Path(__file__).resolve().parent.parent
_PYTHON_DIR = _PARENT / "Python"
if str(_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTHON_DIR))

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta


def download_ohlcv(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Download recent OHLCV data for a symbol using yfinance.
    Returns a DataFrame with Date index and OHLCV columns.
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)

    if df.empty:
        raise ValueError(f"No data returned for ticker {symbol}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    if "Datetime" in df.columns and "Date" not in df.columns:
        df = df.rename(columns={"Datetime": "Date"})
    if "Date" not in df.columns:
        df["Date"] = df.index
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").set_index("Date")
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def load_csv_if_exists(symbol: str) -> pd.DataFrame | None:
    """Try loading cached CSV data for a symbol."""
    data_dir = _PARENT / "data (v1)"
    csv_path = data_dir / f"{symbol}_data.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.sort_values("Date").set_index("Date")
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    return None


def load_data(symbol: str) -> pd.DataFrame:
    """Load OHLCV data: prefer cached CSV, fall back to yfinance download."""
    cached = load_csv_if_exists(symbol)
    if cached is not None and len(cached) >= 200:
        return cached
    return download_ohlcv(symbol, days=365)


def features_from_row(row: pd.Series, entry_price: float, zone_price: float,
                      zone_touches: int, zone_age_days: int) -> dict:
    """
    Build a feature dict matching the model's expected input columns.
    Extracts known important features from a single indicator row.
    Falls back to 0 for missing columns.
    """
    features = {}

    # Zone quality features (top-ranked)
    features["base_range_pct"] = float(row.get("base_range_pct", 0) if isinstance(row.get("base_range_pct"), (int, float)) else 0)
    features["zone_width_pct"] = float(row.get("atr_pct", 0.02))  # approximation
    features["rejection_strength"] = float(row.get("lower_wick_pct", 0) if isinstance(row.get("lower_wick_pct"), (int, float)) else 0)

    # Market context
    for col in ["spy_return_50d", "spy_return_20d", "spy_return_5d", "spy_above_200ma",
                "iwm_return_20d", "qqq_return_20d", "vix_level", "vix_percentile_60d"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Trend
    for col in ["ema_20", "ema_50", "ema_200", "dist_ema_20_pct", "dist_ema_50_pct",
                "dist_ema_200_pct", "ema_alignment", "trend_slope_20",
                "ema_50_slope_20", "ema_200_slope_20", "price_vs_200ma_pct",
                "distance_from_52w_high_pct", "trend_quality"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Momentum
    for col in ["rsi_14", "macd", "macd_signal", "macd_hist", "roc_14", "adx_14"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Volume
    for col in ["rel_volume", "volume_trend_20", "accumulation_days_10",
                "ofi_20", "liquidity_depth_score", "avg_dollar_volume_20",
                "volume_consistency_20", "obv_slope_20", "chaikin_money_flow_20",
                "distance_vwap_20_pct", "dollar_volume_percentile_60"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Volatility
    for col in ["atr_14", "atr_pct", "daily_volatility_20", "gap_frequency_20"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Candlestick
    for col in ["is_bullish", "lower_wick_pct", "body"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Zone-specific
    features["distance_to_zone_pct"] = (entry_price - zone_price) / zone_price if zone_price > 0 else 0
    features["zone_touches"] = float(zone_touches)
    features["zone_age_days"] = float(zone_age_days)
    features["zone_freshness"] = float(np.exp(-zone_age_days / 60) * (1 + zone_touches / 10))

    # Multi-timeframe (defaults)
    for col in ["weekly_zone_present", "monthly_zone_present", "weekly_zone_distance_pct",
                "monthly_zone_distance_pct", "nested_zone_score", "weekly_departure_strength",
                "monthly_departure_strength", "timeframe_alignment_score",
                "daily_weekly_zone_alignment", "daily_monthly_zone_alignment",
                "higher_tf_strength_score", "weekly_trend_aligned", "monthly_trend_aligned"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Sector ETF returns
    for etf in ["xlk", "xlf", "xle", "xlv", "xly", "xlp", "xli", "xlb", "xlu", "xlre", "xlc"]:
        col = f"{etf}_return_20d"
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Relative strength
    for col in ["relative_strength_spy_20d", "relative_strength_sector_20d",
                "sector_return_20d", "rs_momentum"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # SPY regime
    for col in ["spy_regime_bull", "spy_regime_bear", "spy_regime_correction",
                "spy_regime_recovery", "spy_regime_high_vol", "spy_regime_low_vol"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Additional zone quality
    for col in ["departure_volume_ratio", "departure_move_pct", "base_volume_ratio",
                "base_candles", "base_body_ratio", "base_average_body_pct",
                "base_average_wick_ratio", "base_tightness_score", "base_range_percentile",
                "inside_bar_count", "compression_score", "largest_departure_candle_pct",
                "departure_gap_pct", "departure_volume_percentile",
                "consecutive_bullish_departure", "departure_close_near_high",
                "departure_strength", "departure_atr_multiple", "volatility_contraction",
                "retest_number", "is_first_retest", "previous_zone_tests",
                "successful_previous_retests", "failed_previous_retests",
                "time_since_last_touch", "previous_bounce_size"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Weekly
    for col in ["weekly_price_vs_ema20", "weekly_ema_slope_10", "weekly_rsi_14",
                "weekly_macd", "weekly_above_ema50", "weekly_higher_high",
                "weekly_higher_low", "weekly_demand_overlap"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # SPY ADX / ATR
    for col in ["spy_adx", "spy_atr_pct", "spy_ema_alignment"]:
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Relative strength sector
    for etf in ["xlk", "xlf", "xle", "xlv", "xly", "xlp", "xli", "xlb", "xlu", "xlre", "xlc"]:
        col = f"{etf}_relative_strength"
        features[col] = float(row.get(col, 0) if not isinstance(row.get(col), pd.Series) else 0)

    # Entry price feature
    features["entry_price"] = float(entry_price)
    features["is_sub_10"] = int(entry_price < 10)

    return features


TOP_FEATURE_NAMES = [
    "base_range_pct", "zone_width_pct", "spy_return_50d", "ma_50_slope_20",
    "iwm_return_20d", "vix_percentile_60d", "xly_return_20d", "departure_volume_ratio",
    "vix_level", "rejection_strength"
]
