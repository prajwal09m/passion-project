"""Reconstructed demand-zone / market-structure ablation study (protocol v1.0.2).

This editable reconstruction is based on the preserved source prefix and protocol,
not an exact restoration of the historical implementation. Its replay has not
matched the immutable v1.0.1 event-table features; do not use it to attribute or
reproduce the archived model metrics until that mismatch is resolved.

Run from the repository root:
    py backend/demand_zone_study_v1.py audit
    py backend/demand_zone_study_v1.py development [--artifact-dir PATH]
    py backend/demand_zone_study_v1.py freeze-prospective --confirm
    py backend/demand_zone_study_v1.py log-prospective --date YYYY-MM-DD
    py backend/demand_zone_study_v1.py mature-prospective
    py backend/demand_zone_study_v1.py verify-ledger

The machine-readable protocol is the analysis-plan authority. Historical
results are retrospective development evidence only; prospective evaluation
requires a separately reviewed, hash-consistent lock and post-lock predictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import lightgbm
import numpy as np
import pandas as pd
import sklearn
from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"
ROSTER_SOURCE = ROOT / "outputs" / "v2" / "demand_zone_v2_dataset.csv"
DATA_DIR = ROOT / "outputs" / "v2" / "_ohlcv"
ARTIFACT_DIR = ROOT / "outputs" / "study_v1"
DEVELOPMENT_DIR = ARTIFACT_DIR / "development"
MODEL_DIR = ARTIFACT_DIR / "models"
PROSPECTIVE_DIR = ARTIFACT_DIR / "prospective"
PROSPECTIVE_LOG = PROSPECTIVE_DIR / "events.jsonl"
PROSPECTIVE_STATUS = PROSPECTIVE_DIR / "status.json"
PROSPECTIVE_LOCK = PROSPECTIVE_DIR / "lock.json"
REPLAY_CUTOFF_KEY = "historical_replay_signal_date_cutoff_exclusive"

A_FEATURES = [
    "daily_return", "return_5d", "return_20d", "dist_ema20", "dist_ema50",
    "dist_ema200", "ema_alignment", "ema20_slope_5d", "rsi14", "macd_pct",
    "macd_signal_pct", "macd_hist_pct", "roc14", "relative_volume20",
    "volume_trend20", "accumulation_days10", "volume_flow_5d_norm",
    "volume_consistency20", "close_strength", "bullish_candle",
]
B_INCREMENT = [
    "atr_pct", "realized_vol_5d", "realized_vol_10d", "realized_vol_20d",
    "spy_return_5d", "spy_return_20d", "qqq_return_5d", "qqq_return_20d",
    "iwm_return_5d", "iwm_return_20d", "spy_dist_sma200", "spy_above_sma200",
    "vix_level", "vix_change_1d", "vix_percentile_60d",
    "relative_strength_spy_20d", "relative_strength_qqq_20d",
    "relative_strength_iwm_20d",
]
C_INCREMENT = [
    "zone_distance_pct", "zone_width_pct", "zone_touch_count", "zone_strength",
    "zone_age_sessions", "zone_freshness", "zone_prior_retest_count",
    "zone_retest_number", "zone_is_first_retest", "zone_base_candles",
    "zone_base_volume_ratio", "zone_departure_move_pct", "zone_departure_volume_ratio",
    "zone_base_range_pct", "zone_volatility_contraction", "zone_departure_atr_multiple",
    "zone_base_body_ratio", "zone_base_average_body_pct",
    "zone_base_average_wick_ratio", "zone_base_range_to_prior_mean_ratio",
    "zone_inside_bar_count", "zone_compression_score",
    "zone_largest_departure_candle_pct", "zone_departure_gap_pct",
    "zone_departure_volume_percentile", "zone_consecutive_bullish_departure",
    "zone_departure_close_near_high",
]
D_INCREMENT = [
    "ob_bull_exists", "ob_bear_exists", "ob_unmitigated_bull_count",
    "ob_unmitigated_bear_count", "ob_bull_distance_signed_pct", "ob_bull_width_pct",
    "ob_bull_age_calendar_days", "ob_bull_age_sessions", "ob_bull_impulse_return_pct",
    "ob_bull_impulse_atr_multiple", "ob_bull_impulse_volume_ratio",
    "ob_bull_impulse_candles", "ob_bull_candles_until_impulse",
    "ob_bull_displacement_rank", "ob_bull_volume_ratio", "ob_bull_candle_count",
    "ob_bull_body_pct", "ob_bull_wick_pct", "ob_bull_touch_count",
    "ob_bear_distance_signed_pct", "ob_bear_width_pct", "ob_bear_age_calendar_days",
    "ob_bear_age_sessions", "ob_bear_impulse_return_pct", "ob_bear_impulse_atr_multiple",
    "ob_bear_impulse_volume_ratio", "ob_bear_impulse_candles",
    "ob_bear_candles_until_impulse", "ob_bear_displacement_rank",
    "ob_bear_volume_ratio", "ob_bear_candle_count", "ob_bear_body_pct",
    "ob_bear_wick_pct", "ob_bear_touch_count",
]
FEATURE_ARMS = {
    "A": A_FEATURES,
    "B": A_FEATURES + B_INCREMENT,
    "C": A_FEATURES + B_INCREMENT + C_INCREMENT,
    "D": A_FEATURES + B_INCREMENT + C_INCREMENT + D_INCREMENT,
}
ZONE_SOURCE_FIELDS = {
    "zone_strength": "strength",
    "zone_base_candles": "base_candles",
    "zone_base_volume_ratio": "base_volume_ratio",
    "zone_departure_move_pct": "departure_move_pct",
    "zone_departure_volume_ratio": "departure_volume_ratio",
    "zone_base_range_pct": "base_range_pct",
    "zone_volatility_contraction": "volatility_contraction",
    "zone_departure_atr_multiple": "departure_atr_multiple",
    "zone_base_body_ratio": "base_body_ratio",
    "zone_base_average_body_pct": "base_average_body_pct",
    "zone_base_average_wick_ratio": "base_average_wick_ratio",
    "zone_base_tightness_score": "base_tightness_score",
    "zone_base_range_to_prior_mean_ratio": "base_range_to_prior_mean_ratio",
    "zone_inside_bar_count": "inside_bar_count",
    "zone_compression_score": "compression_score",
    "zone_largest_departure_candle_pct": "largest_departure_candle_pct",
    "zone_departure_gap_pct": "departure_gap_pct",
    "zone_departure_volume_percentile": "departure_volume_percentile",
    "zone_consecutive_bullish_departure": "consecutive_bullish_departure",
    "zone_departure_close_near_high": "departure_close_near_high",
}
BANNED_FEATURE_PATTERNS = (
    "target", "label", "outcome", "future", "forward", "hold1", "alpha_",
    "bench_", "tb_", "mfe", "mae", "realized_return", "return_proxy",
    "expected_return", "hit_", "strong_hit", "market_relative_hit", "success", "failure",
)
ESTIMATORS = ("LogisticRegression", "LightGBM")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=_json_default)


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, pd.Period)):
        return str(value)
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot JSON-serialize {type(value).__name__}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(*parts: Any) -> str:
    return sha256_bytes("|".join(map(str, parts)).encode("utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_protocol() -> dict[str, Any]:
    with PROTOCOL_PATH.open("r", encoding="utf-8") as stream:
        protocol = json.load(stream)
    if protocol.get("protocol_id") != "DZAI-MARKET-STRUCTURE-ABLATION-V1":
        raise ValueError("Unexpected protocol ID")
    if protocol.get("status") != "frozen_v1.0.2" or protocol.get("protocol_version") != "1.0.2":
        raise ValueError("Protocol status/version mismatch; v1.0.2 must be explicitly frozen before running")
    return protocol


def _historical_replay_cutoff(protocol: dict[str, Any]) -> str:
    """Exclusive signal-date cutoff derived from the final frozen validation fold."""
    folds = protocol["historical_development_evaluation"]["folds"]
    if not folds or any(not fold.get("validation_end_exclusive") for fold in folds):
        raise ValueError("Every historical validation fold must define validation_end_exclusive")
    return max(str(fold["validation_end_exclusive"]) for fold in folds)


def validate_feature_whitelist(protocol: dict[str, Any] | None = None) -> None:
    protocol = protocol or load_protocol()
    for arm, features in FEATURE_ARMS.items():
        if len(features) != len(set(features)):
            raise AssertionError(f"Duplicate feature in arm {arm}")
        forbidden = [name for name in features if any(p in name.lower() for p in BANNED_FEATURE_PATTERNS)]
        if forbidden:
            raise AssertionError(f"Banned feature(s) in arm {arm}: {forbidden}")
    assert set(FEATURE_ARMS["A"]).issubset(FEATURE_ARMS["B"])
    assert set(FEATURE_ARMS["B"]).issubset(FEATURE_ARMS["C"])
    assert set(FEATURE_ARMS["C"]).issubset(FEATURE_ARMS["D"])
    expected = protocol.get("feature_groups", {})
    for group, values in [("A", A_FEATURES), ("B_increment", B_INCREMENT), ("C_increment", C_INCREMENT), ("D_increment", D_INCREMENT)]:
        if expected.get(group) != values:
            raise AssertionError(f"Protocol/code whitelist mismatch in {group}")
    estimator_configs = protocol.get("estimators", {})
    for estimator in ESTIMATORS:
        config = estimator_configs.get(estimator)
        if not isinstance(config, dict):
            raise AssertionError(f"Frozen estimator config missing for {estimator}")
        actual = make_model(estimator).get_params()
        for key, value in config.items():
            if key in {"pipeline", "penalty", "selection"}:
                continue
            if key not in actual or actual[key] != value:
                raise AssertionError(f"Protocol/code estimator mismatch for {estimator}.{key}: {actual.get(key)!r} != {value!r}")


def load_roster(source: Path = ROSTER_SOURCE) -> list[str]:
    frame = pd.read_csv(source, usecols=["ticker"])
    roster = sorted(frame.ticker.dropna().astype(str).str.strip().unique())
    if len(roster) != 149:
        raise AssertionError(f"Expected recovered 149-ticker project roster; got {len(roster)}")
    return roster


def _universe_sha256(roster: Iterable[str]) -> str:
    return sha256_bytes(("\n".join(sorted(roster)) + "\n").encode("utf-8"))


def read_ohlcv(symbol: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    path = data_dir / f"{symbol.replace('^', 'X')}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing local OHLCV file: {path}")
    frame = pd.read_csv(path)
    if "Date" not in frame.columns:
        raise ValueError(f"Missing Date column in {path}")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.tz_localize(None)
    frame = frame.dropna(subset=["Date"]).drop_duplicates("Date", keep="last").sort_values("Date").set_index("Date")
    frame = frame.rename(columns={column: column.capitalize() for column in frame.columns})
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing OHLCV columns in {path}: {sorted(required - set(frame.columns))}")
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _input_hashes(roster: list[str], data_dir: Path) -> dict[str, str]:
    hashes = {}
    for symbol in roster + ["SPY", "QQQ", "IWM", "XVIX"]:
        path = data_dir / f"{symbol}.csv"
        if path.exists():
            hashes[symbol] = sha256_file(path)
    return hashes


def _prefix_hash(frame: pd.DataFrame, as_of: pd.Timestamp) -> str:
    prefix = frame.loc[frame.index <= pd.Timestamp(as_of)]
    payload = prefix.to_csv(index=True, float_format="%.12g", lineterminator="\n").encode("utf-8")
    return sha256_bytes(payload)


def _event_features_from_cache(bars: pd.DataFrame, markets: dict[str, pd.DataFrame], as_of: pd.Timestamp) -> dict[str, pd.DataFrame]:
    return {}


def calculate_stock_indicators(bars: pd.DataFrame) -> pd.DataFrame:
    """Causal rolling predictors recovered from the intact source prefix."""
    frame = bars.copy()
    close, high, low, open_, volume = frame.Close, frame.High, frame.Low, frame.Open, frame.Volume
    returns = close.pct_change(fill_method=None)
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    change = close.diff()
    gain = change.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-change.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)
    true_range = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    atr = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    average_volume = volume.rolling(20, min_periods=20).mean()
    candle_range = (high - low).replace(0, np.nan)

    frame["daily_return"] = returns
    frame["return_5d"] = close.pct_change(5, fill_method=None)
    frame["return_20d"] = close.pct_change(20, fill_method=None)
    frame["dist_ema20"] = close / ema20 - 1
    frame["dist_ema50"] = close / ema50 - 1
    frame["dist_ema200"] = close / ema200 - 1
    frame["ema_alignment"] = ((ema20 > ema50) & (ema50 > ema200)).where(ema200.notna(), np.nan).astype(float)
    frame["ema20_slope_5d"] = ema20.pct_change(5, fill_method=None)
    frame["rsi14"] = rsi
    frame["macd_pct"] = macd / close
    frame["macd_signal_pct"] = macd_signal / close
    frame["macd_hist_pct"] = (macd - macd_signal) / close
    frame["roc14"] = close.pct_change(14)
    frame["relative_volume20"] = volume / average_volume.replace(0, np.nan)
    frame["volume_trend20"] = average_volume.pct_change(20, fill_method=None)
    frame["accumulation_days10"] = ((close > open_) & (volume > average_volume)).astype(float).rolling(10, min_periods=10).sum()
    frame["volume_flow_5d_norm"] = (volume * np.sign(change).fillna(0)).rolling(5, min_periods=5).sum() / average_volume.replace(0, np.nan)
    frame["volume_consistency20"] = volume.rolling(20, min_periods=20).std() / average_volume.replace(0, np.nan)
    frame["close_strength"] = (close - low) / candle_range
    frame["bullish_candle"] = (close > open_).astype(float)
    frame["atr_pct"] = atr / close
    frame["realized_vol_5d"] = returns.rolling(5, min_periods=5).std() * np.sqrt(252)
    frame["realized_vol_10d"] = returns.rolling(10, min_periods=10).std() * np.sqrt(252)
    frame["realized_vol_20d"] = returns.rolling(20, min_periods=20).std() * np.sqrt(252)
    frame["_atr14"] = atr
    return frame


def calculate_market_indicators(bars: pd.DataFrame, prefix: str, *, vix: bool = False) -> pd.DataFrame:
    close = bars["Close"]
    result = pd.DataFrame(index=bars.index)
    if vix:
        result["vix_level"] = close
        result["vix_change_1d"] = close.pct_change(1, fill_method=None)
        result["vix_percentile_60d"] = close.rolling(60, min_periods=60).rank(pct=True)
        return result
    result[f"{prefix}_return_5d"] = close.pct_change(5, fill_method=None)
    result[f"{prefix}_return_20d"] = close.pct_change(20, fill_method=None)
    if prefix == "spy":
        sma200 = close.rolling(200, min_periods=200).mean()
        result["spy_dist_sma200"] = close / sma200 - 1
        result["spy_above_sma200"] = (close > sma200).where(sma200.notna(), np.nan).astype(float)
    return result


def _zone_formation(bars: pd.DataFrame, indicators: pd.DataFrame, pivot: int) -> dict[str, Any]:
    low, high = bars.Low.to_numpy(dtype=float), bars.High.to_numpy(dtype=float)
    close, open_, volume = bars.Close.to_numpy(dtype=float), bars.Open.to_numpy(dtype=float), bars.Volume.to_numpy(dtype=float)
    confirm = pivot + 2
    price = float(low[pivot])
    width = finite_or_nan(indicators["atr_pct"].iloc[pivot])
    if not np.isfinite(width) or price <= 0 or pivot < 1:
        return {}
    base_start = pivot
    tolerance = max(0.03, width * 2)
    while base_start > max(0, pivot - 10):
        previous_close = close[base_start - 1]
        if not np.isfinite(previous_close) or abs(previous_close - price) / price > tolerance:
            break
        base_start -= 1
    base = slice(base_start, pivot + 1)
    departure = slice(pivot, confirm + 1)
    pre_start = max(0, base_start - 10)
    pre_ranges = high[pre_start:base_start] - low[pre_start:base_start]
    base_ranges = high[base] - low[base]
    base_bodies = np.abs(close[base] - open_[base])
    base_wicks = (high[base] - np.maximum(open_[base], close[base])) + (np.minimum(open_[base], close[base]) - low[base])
    departure_bodies = np.abs(close[departure] - open_[departure])
    base_mean = float(np.nanmean(base_ranges))
    pre_mean = float(np.nanmean(pre_ranges)) if len(pre_ranges) else np.nan
    prior_volume = float(np.nanmean(volume[max(0, pivot - 20):pivot])) if pivot > 0 else np.nan
    base_volume = float(np.nanmean(volume[base]))
    departure_high = float(np.nanmax(high[departure]))
    departure_volume = float(np.nanmean(volume[departure]))
    max_departure = pivot + int(np.nanargmax(departure_bodies))
    previous_close = close[pivot - 1]
    prior_ranges = high[max(0, pivot - 60):pivot] - low[max(0, pivot - 60):pivot]
    denominator = float(np.nanmean(prior_ranges)) if len(prior_ranges) else np.nan
    return {
        "price": price,
        "confirmation_idx": confirm,
        "initial_touches": int(np.count_nonzero(np.abs(low[:confirm + 1] - price) / price <= 0.03)),
        "strength": (close[confirm] - price) / price,
        "width_pct": width,
        "base_candles": int(pivot - base_start + 1),
        "base_volume_ratio": base_volume / prior_volume if np.isfinite(prior_volume) and prior_volume != 0 else np.nan,
        "departure_move_pct": (departure_high - price) / price,
        "departure_volume_ratio": departure_volume / prior_volume if np.isfinite(prior_volume) and prior_volume != 0 else np.nan,
        "base_range_pct": (float(np.nanmax(high[base])) - float(np.nanmin(low[base]))) / price,
        "volatility_contraction": base_mean / pre_mean if np.isfinite(pre_mean) and pre_mean != 0 else np.nan,
        "departure_atr_multiple": ((departure_high - price) / price) / width if width != 0 else np.nan,
        "base_body_ratio": float(np.nanmean(np.divide(base_bodies, base_ranges, out=np.full_like(base_bodies, np.nan), where=base_ranges != 0))),
        "base_average_body_pct": float(np.nanmean(base_bodies)) / price,
        "base_average_wick_ratio": float(np.nanmean(np.divide(base_wicks, base_ranges, out=np.full_like(base_wicks, np.nan), where=base_ranges != 0))),
        "base_range_to_prior_mean_ratio": base_mean / denominator if np.isfinite(denominator) and denominator != 0 else np.nan,
        "base_tightness_score": float(np.mean(base_ranges <= np.nanmedian(pre_ranges))) if len(pre_ranges) and np.isfinite(np.nanmedian(pre_ranges)) else np.nan,
        "inside_bar_count": int(np.sum((high[base_start + 1:pivot + 1] <= high[base_start:pivot]) & (low[base_start + 1:pivot + 1] >= low[base_start:pivot]))) if pivot > base_start else 0,
        "compression_score": pre_mean / base_mean if np.isfinite(pre_mean) and base_mean != 0 else np.nan,
        "largest_departure_candle_pct": float(np.nanmax(departure_bodies)) / price,
        "departure_gap_pct": (open_[pivot] - previous_close) / previous_close if previous_close else np.nan,
        "departure_volume_percentile": float(pd.Series(volume[departure]).rank(pct=True).iloc[-1]),
        "consecutive_bullish_departure": int(np.cumprod((close[departure] > open_[departure]).astype(int)).sum()),
        "departure_close_near_high": (high[max_departure] - close[max_departure]) / (high[max_departure] - low[max_departure] + 1e-9),
    }


def finite_or_nan(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan
    return number if np.isfinite(number) else np.nan


def _target_for_index(bars: pd.DataFrame, idx: int) -> dict[str, Any]:
    invalid = {"label_valid": False, "entry_date": None, "exit_date": None, "entry_open": None, "exit_open": None, "hold1_ret": None, "label": None}
    if idx < 0 or idx + 2 >= len(bars):
        return invalid
    entry_open = finite_or_nan(bars.Open.iloc[idx + 1])
    exit_open = finite_or_nan(bars.Open.iloc[idx + 2])
    if not np.isfinite(entry_open) or entry_open <= 0 or not np.isfinite(exit_open) or exit_open <= 0:
        return invalid
    ret = exit_open / entry_open - 1
    if not np.isfinite(ret):
        return invalid
    return {
        "label_valid": True,
        "entry_date": pd.Timestamp(bars.index[idx + 1]),
        "exit_date": pd.Timestamp(bars.index[idx + 2]),
        "entry_open": entry_open,
        "exit_open": exit_open,
        "hold1_ret": ret,
        "label": int(ret >= 0.02),
    }


def _market_row(features: pd.DataFrame, bars: pd.DataFrame, date: pd.Timestamp) -> tuple[pd.Series | None, int]:
    idx = bars.index.searchsorted(date, side="right") - 1
    return (None, -1) if idx < 0 else (features.iloc[idx], idx)


def _make_event_features(
    ticker: str, bars: pd.DataFrame, indicators: pd.DataFrame,
    market_bars: dict[str, pd.DataFrame], market_features: dict[str, pd.DataFrame],
    tracker: "CausalOrderBlockTracker", idx: int, zone: dict[str, Any], retest_number: int,
) -> dict[str, Any]:
    date = pd.Timestamp(bars.index[idx])
    close = finite_or_nan(bars.Close.iloc[idx])
    low = finite_or_nan(bars.Low.iloc[idx])
    zone_price = float(zone["price"])
    age = idx - int(zone["confirmation_idx"])
    features = {name: finite_or_nan(indicators[name].iloc[idx]) for name in A_FEATURES + B_INCREMENT[:4]}
    for symbol, prefix in (("SPY", "spy"), ("QQQ", "qqq"), ("IWM", "iwm")):
        market_row, _ = _market_row(market_features[prefix.upper()], market_bars[symbol], date)
        for column in (f"{prefix}_return_5d", f"{prefix}_return_20d"):
            features[column] = finite_or_nan(market_row[column]) if market_row is not None else np.nan
        stock_return = finite_or_nan(indicators.return_20d.iloc[idx])
        features[f"relative_strength_{prefix}_20d"] = stock_return - features[f"{prefix}_return_20d"] if np.isfinite(stock_return) and np.isfinite(features[f"{prefix}_return_20d"]) else np.nan
    spy_row, _ = _market_row(market_features["SPY"], market_bars["SPY"], date)
    vix_row, _ = _market_row(market_features["VIX"], market_bars["^VIX"], date)
    for column in ("spy_dist_sma200", "spy_above_sma200"):
        features[column] = finite_or_nan(spy_row[column]) if spy_row is not None else np.nan
    for column in ("vix_level", "vix_change_1d", "vix_percentile_60d"):
        features[column] = finite_or_nan(vix_row[column]) if vix_row is not None else np.nan
    features.update({
        "zone_distance_pct": (close - zone_price) / zone_price,
        "zone_width_pct": float(zone["width_pct"]),
        "zone_touch_count": float(zone["initial_touches"] + retest_number),
        "zone_strength": float(zone["strength"]),
        "zone_age_sessions": float(age),
        "zone_freshness": math.exp(-age / 60) * (1 + (zone["initial_touches"] + retest_number) / 10),
        "zone_prior_retest_count": float(max(0, retest_number - 1)),
        "zone_retest_number": float(retest_number),
        "zone_is_first_retest": float(retest_number == 1),
    })
    features.update({name: float(zone[source]) if np.isfinite(zone.get(source, np.nan)) else np.nan for name, source in ZONE_SOURCE_FIELDS.items()})
    features.update(tracker.features(close, date, idx))
    return features


@dataclass
class _OrderBlock:
    direction: str
    idx: int
    date: pd.Timestamp
    low: float
    high: float
    impulse_return_pct: float
    impulse_atr_multiple: float
    impulse_volume_ratio: float
    impulse_candles: int
    candles_until_impulse: int
    displacement_rank: float
    volume_ratio: float
    candle_count: int
    body_pct: float
    wick_pct: float
    touch_count: int = 0


class CausalOrderBlockTracker:
    """Deterministic streaming tracker; caller advances once per closed session."""

    def __init__(self, bars: pd.DataFrame, indicators: pd.DataFrame, *, min_bars: int = 100, max_age_days: int = 90):
        self.bars = bars
        self.indicators = indicators
        self.min_bars = min_bars
        self.max_age_days = max_age_days
        self.blocks: list[_OrderBlock] = []
        self.last_advanced = -1

    def advance(self, idx: int) -> None:
        if idx != self.last_advanced + 1:
            raise AssertionError(f"Order-block tracker must advance sequentially: {self.last_advanced} -> {idx}")
        self.last_advanced = idx
        if idx < self.min_bars:
            return
        date = pd.Timestamp(self.bars.index[idx])
        close = float(self.bars.Close.iloc[idx])
        prior_close = float(self.bars.Close.iloc[idx - 1])
        atr = finite_or_nan(self.indicators._atr14.iloc[idx - 1])
        volume = finite_or_nan(self.bars.Volume.iloc[idx])
        prior_volume = finite_or_nan(self.bars.Volume.iloc[max(0, idx - 20):idx].mean())
        if np.isfinite(atr) and atr > 0 and np.isfinite(prior_close) and prior_close > 0:
            displacement = (close - prior_close) / atr
            volume_ratio = volume / prior_volume if np.isfinite(volume) and np.isfinite(prior_volume) and prior_volume > 0 else np.nan
            if displacement >= 0.6 and np.isfinite(volume_ratio) and volume_ratio >= 0.5:
                self._create_block(idx, "bull", displacement, volume_ratio)
            elif displacement <= -0.6 and np.isfinite(volume_ratio) and volume_ratio >= 0.5:
                self._create_block(idx, "bear", displacement, volume_ratio)
        low = float(self.bars.Low.iloc[idx])
        high = float(self.bars.High.iloc[idx])
        active = []
        for block in self.blocks:
            if (date - block.date).days > self.max_age_days:
                continue
            if block.direction == "bull" and low <= block.low:
                continue
            if block.direction == "bear" and high >= block.high:
                continue
            if block.low <= close <= block.high:
                block.touch_count += 1
            active.append(block)
        self.blocks = active

    def _create_block(self, idx: int, direction: str, displacement: float, volume_ratio: float) -> None:
        start = max(0, idx - 5)
        opposite = (self.bars.Close.iloc[start:idx] < self.bars.Open.iloc[start:idx]) if direction == "bull" else (self.bars.Close.iloc[start:idx] > self.bars.Open.iloc[start:idx])
        candidates = np.flatnonzero(opposite.to_numpy())
        if not len(candidates):
            return
        selected = candidates[-3:]
        positions = start + selected
        lows = self.bars.Low.to_numpy(dtype=float)[positions]
        highs = self.bars.High.to_numpy(dtype=float)[positions]
        first, last = int(positions[0]), int(positions[-1])
        date = pd.Timestamp(self.bars.index[idx])
        window_dates = pd.to_datetime(self.bars.index[max(0, idx - 20):idx])
        window_volume = self.bars.Volume.iloc[max(0, idx - 20):idx].to_numpy(dtype=float)
        volume_percentile = float(pd.Series(window_volume).rank(pct=True).iloc[-1]) if len(window_volume) and np.isfinite(window_volume[-1]) else 0.0
        ranges = self.bars.High.iloc[max(0, idx - 5):idx].to_numpy(dtype=float) - self.bars.Low.iloc[max(0, idx - 5):idx].to_numpy(dtype=float)
        body = abs(float(self.bars.Close.iloc[first]) - float(self.bars.Open.iloc[first]))
        candle_range = float(self.bars.High.iloc[first] - self.bars.Low.iloc[first])
        upper = float(self.bars.High.iloc[first] - max(self.bars.Open.iloc[first], self.bars.Close.iloc[first]))
        lower = float(min(self.bars.Open.iloc[first], self.bars.Close.iloc[first]) - self.bars.Low.iloc[first])
        self.blocks.append(_OrderBlock(
            direction=direction, idx=first, date=pd.Timestamp(self.bars.index[first]),
            low=float(np.nanmin(lows)), high=float(np.nanmax(highs)),
            impulse_return_pct=float(displacement * finite_or_nan(self.indicators.atr_pct.iloc[idx - 1])),
            impulse_atr_multiple=abs(float(displacement)), impulse_volume_ratio=float(volume_ratio),
            impulse_candles=max(1, idx - first), candles_until_impulse=max(1, idx - last),
            displacement_rank=volume_percentile,
            volume_ratio=float(self.bars.Volume.iloc[first] / np.nanmean(window_volume)) if np.nanmean(window_volume) > 0 else np.nan,
            candle_count=int(len(positions)), body_pct=body / float(self.bars.Close.iloc[first]),
            wick_pct=(upper + lower) / candle_range if candle_range > 0 else np.nan,
        ))

    def features(self, close: float, date: pd.Timestamp, idx: int) -> dict[str, float]:
        bull = [block for block in self.blocks if block.direction == "bull"]
        bear = [block for block in self.blocks if block.direction == "bear"]
        bull_block = min(bull, key=lambda block: abs(close - (block.low + block.high) / 2)) if bull else None
        bear_block = min(bear, key=lambda block: abs(close - (block.low + block.high) / 2)) if bear else None
        result = {"ob_bull_exists": float(bull_block is not None), "ob_bear_exists": float(bear_block is not None), "ob_unmitigated_bull_count": float(len(bull)), "ob_unmitigated_bear_count": float(len(bear))}
        for direction, block in (("bull", bull_block), ("bear", bear_block)):
            prefix = f"ob_{direction}"
            if block is None:
                values = {"distance_signed_pct": np.nan, "width_pct": np.nan, "age_calendar_days": np.nan, "age_sessions": np.nan, "impulse_return_pct": np.nan, "impulse_atr_multiple": np.nan, "impulse_volume_ratio": np.nan, "impulse_candles": np.nan, "candles_until_impulse": np.nan, "displacement_rank": np.nan, "volume_ratio": np.nan, "candle_count": np.nan, "body_pct": np.nan, "wick_pct": np.nan, "touch_count": np.nan}
            else:
                midpoint = (block.low + block.high) / 2
                values = {
                    "distance_signed_pct": (close - midpoint) / midpoint,
                    "width_pct": (block.high - block.low) / midpoint,
                    "age_calendar_days": float((date - block.date).days),
                    "age_sessions": float(idx - block.idx),
                    "impulse_return_pct": block.impulse_return_pct,
                    "impulse_atr_multiple": block.impulse_atr_multiple,
                    "impulse_volume_ratio": block.impulse_volume_ratio,
                    "impulse_candles": float(block.impulse_candles),
                    "candles_until_impulse": float(block.candles_until_impulse),
                    "displacement_rank": block.displacement_rank,
                    "volume_ratio": block.volume_ratio,
                    "candle_count": float(block.candle_count),
                    "body_pct": block.body_pct,
                    "wick_pct": block.wick_pct,
                    "touch_count": float(block.touch_count),
                }
            result.update({f"{prefix}_{name}": float(value) for name, value in values.items()})
        return result


def _market_row(features: pd.DataFrame, bars: pd.DataFrame, date: pd.Timestamp) -> tuple[pd.Series | None, int]:
    idx = bars.index.searchsorted(date, side="right") - 1
    return (None, -1) if idx < 0 else (features.iloc[idx], idx)


def generate_symbol_events(
    ticker: str, bars: pd.DataFrame, market_bars: dict[str, pd.DataFrame],
    market_features: dict[str, pd.DataFrame], *, min_date: pd.Timestamp,
    max_date_exclusive: pd.Timestamp | str | None = None, include_labels: bool = True,
) -> list[dict[str, Any]]:
    if len(bars) < 260:
        return []
    end = pd.Timestamp(max_date_exclusive).normalize() if max_date_exclusive is not None else None
    indicators = calculate_stock_indicators(bars)
    tracker = CausalOrderBlockTracker(bars, indicators, min_bars=100, max_age_days=90)
    low, close = bars.Low.to_numpy(dtype=float), bars.Close.to_numpy(dtype=float)
    zones: list[dict[str, Any]] = []
    retests: dict[int, int] = {}
    was_at_zone: dict[int, bool] = {}
    events = []
    for idx, date_value in enumerate(bars.index):
        date = pd.Timestamp(date_value)
        if end is not None and date >= end:
            break
        if idx >= 4:
            pivot = idx - 2
            if low[pivot] <= low[pivot - 1] and low[pivot] <= low[pivot - 2] and low[pivot] <= low[pivot + 1] and low[pivot] <= low[pivot + 2]:
                zone = _zone_formation(bars, indicators, pivot)
                if zone:
                    zone["zone_id"] = int(pivot)
                    zones.append(zone)
                    retests[pivot] = 0
                    was_at_zone[pivot] = False
        active = []
        for zone in zones:
            zone_id = int(zone["zone_id"])
            if idx <= int(zone["confirmation_idx"]):
                continue
            price = float(zone["price"])
            in_zone = abs(float(low[idx]) - price) / price <= 0.03
            is_start = in_zone and not was_at_zone[zone_id]
            was_at_zone[zone_id] = bool(in_zone)
            if retests[zone_id] < 5 and is_start:
                retests[zone_id] += 1
                active.append((zone, retests[zone_id]))
        if not active or date < pd.Timestamp(min_date):
            tracker.advance(idx)
            continue
        candidates = []
        for zone, number in active:
            price = float(zone["price"])
            distance = abs((float(close[idx]) - price) / price)
            candidates.append((int(zone["initial_touches"] + number), -distance, -int(zone["zone_id"]), zone, number))
        _, _, _, selected_zone, retest_number = max(candidates, key=lambda item: item[:3])
        tracker.advance(idx)
        features = _make_event_features(ticker, bars, indicators, market_bars, market_features, tracker, idx, selected_zone, retest_number)
        event = {
            **features,
            "ticker": ticker,
            "date": date,
            "event_id": stable_id(ticker, date.date().isoformat()),
            "zone_id": int(selected_zone["zone_id"]),
            "signal_close": float(close[idx]),
            "signal_timestamp": date.tz_localize("America/New_York").replace(hour=16).isoformat(),
            "feature_asof_date": date.date().isoformat(),
        }
        event.update(_target_for_index(bars, idx) if include_labels else {
            "label_valid": False, "entry_date": None, "exit_date": None, "entry_open": None,
            "exit_open": None, "hold1_ret": None, "label": None,
        })
        events.append(event)
    return events


def _assert_event_table(frame: pd.DataFrame) -> None:
    validate_feature_whitelist()
    if frame.empty:
        raise AssertionError("No candidate events")
    if not frame.event_id.is_unique or frame.duplicated(["ticker", "date"]).any():
        raise AssertionError("Duplicate candidate ticker-date event")
    if not frame.feature_asof_date.eq(pd.to_datetime(frame.date).dt.date.astype(str)).all():
        raise AssertionError("Feature as-of timestamp does not equal signal date")
    for arm, features in FEATURE_ARMS.items():
        missing = set(features) - set(frame.columns)
        if missing:
            raise AssertionError(f"Missing feature values in {arm}: {sorted(missing)}")
        if any(any(pattern in feature.lower() for pattern in BANNED_FEATURE_PATTERNS) for feature in features):
            raise AssertionError(f"Leakage-name exclusion failed for arm {arm}")
    valid = frame.label_valid.fillna(False).astype(bool)
    for column in ("entry_open", "exit_open", "hold1_ret"):
        values = pd.to_numeric(frame.loc[valid, column], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise AssertionError(f"Non-finite valid label field {column}")
    if valid.any():
        entry = frame.loc[valid, "entry_open"].astype(float)
        exit_ = frame.loc[valid, "exit_open"].astype(float)
        returns = frame.loc[valid, "hold1_ret"].astype(float)
        if (entry <= 0).any() or (exit_ <= 0).any() or not np.allclose(exit_ / entry - 1, returns, rtol=1e-12, atol=1e-12):
            raise AssertionError("Target return does not match forward opens")
        if not np.array_equal(frame.loc[valid, "label"].astype(int), (returns >= 0.02).astype(int)):
            raise AssertionError("Target label does not match the inclusive 2% threshold")
        if not (pd.to_datetime(frame.loc[valid, "exit_date"]) > pd.to_datetime(frame.loc[valid, "date"])).all():
            raise AssertionError("Target horizon did not mature after signal date")
    if frame.loc[~valid, "label"].notna().any():
        raise AssertionError("Missing outcomes were incorrectly converted to negative labels")


def build_event_table(
    roster: list[str], *, data_dir: Path = DATA_DIR, include_labels: bool = True,
    min_date: str = "2021-08-03", max_date_exclusive: str | None = None,
    as_of: str | pd.Timestamp | None = None, allow_empty: bool = False,
    ticker_limit: int | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    as_of_date = pd.Timestamp(as_of).normalize() if as_of is not None else None
    market_bars = {symbol: read_ohlcv(symbol, data_dir) for symbol in ("SPY", "QQQ", "IWM", "^VIX")}
    if as_of_date is not None:
        market_bars = {symbol: bars.loc[bars.index <= as_of_date].copy() for symbol, bars in market_bars.items()}
    market_features = {
        "SPY": calculate_market_indicators(market_bars["SPY"], "spy"),
        "QQQ": calculate_market_indicators(market_bars["QQQ"], "qqq"),
        "IWM": calculate_market_indicators(market_bars["IWM"], "iwm"),
        "VIX": calculate_market_indicators(market_bars["^VIX"], "vix", vix=True),
    }
    start = pd.Timestamp(min_date)
    end = pd.Timestamp(max_date_exclusive) if max_date_exclusive else None
    events: list[dict[str, Any]] = []
    missing = []
    chosen_roster = roster[:ticker_limit] if ticker_limit else roster
    for position, ticker in enumerate(chosen_roster, start=1):
        try:
            bars = read_ohlcv(ticker, data_dir)
        except FileNotFoundError:
            missing.append(ticker)
            continue
        if as_of_date is not None:
            bars = bars.loc[bars.index <= as_of_date].copy()
        if len(bars) < 260:
            continue
        events.extend(generate_symbol_events(
            ticker, bars, market_bars, market_features,
            min_date=start, max_date_exclusive=end, include_labels=include_labels,
        ))
        print(f"[events] {position}/{len(chosen_roster)} {ticker}: {len(events):,} cumulative", flush=True)
    if not events:
        if not allow_empty:
            raise ValueError("No events generated for the selected date range")
        columns = list(dict.fromkeys(sum(FEATURE_ARMS.values(), []) + [
            "ticker", "date", "event_id", "zone_id", "signal_close", "signal_timestamp",
            "feature_asof_date", "label_valid", "entry_date", "exit_date", "entry_open",
            "exit_open", "hold1_ret", "label",
        ]))
        return pd.DataFrame(columns=columns), missing
    result = pd.DataFrame(events).sort_values(["date", "ticker"], kind="stable").reset_index(drop=True)
    _assert_event_table(result)
    return result, missing


def make_model(estimator: str):
    if estimator == "LogisticRegression":
        return LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000, random_state=42)
    if estimator == "LightGBM":
        return LGBMClassifier(
            n_estimators=300, max_depth=6, num_leaves=31, learning_rate=0.03,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
            min_child_samples=30, reg_alpha=0.1, reg_lambda=0.5,
            random_state=42, n_jobs=1, verbosity=-1,
            deterministic=True, force_col_wise=True,
        )
    raise ValueError(estimator)


def fit_pipeline(estimator: str, features: list[str], rows: pd.DataFrame, labels: np.ndarray) -> dict[str, Any]:
    matrix = rows[features].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).to_numpy(dtype=float)
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    transformed = imputer.fit_transform(matrix)
    scaler = None
    if estimator == "LogisticRegression":
        scaler = StandardScaler()
        transformed = scaler.fit_transform(transformed)
    model = make_model(estimator)
    model.fit(transformed, labels)
    return {"estimator": estimator, "features": list(features), "imputer": imputer, "scaler": scaler, "model": model, "protocol_id": load_protocol()["protocol_id"]}


def predict_pipeline(pipeline: dict[str, Any], rows: pd.DataFrame) -> np.ndarray:
    matrix = rows[pipeline["features"]].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).to_numpy(dtype=float)
    transformed = pipeline["imputer"].transform(matrix)
    if pipeline["scaler"] is not None:
        transformed = pipeline["scaler"].transform(transformed)
    return pipeline["model"].predict_proba(transformed)[:, 1]


def make_folds(frame: pd.DataFrame, years: Iterable[int] = (2023, 2024, 2025)) -> list[dict[str, Any]]:
    dates, exits = pd.to_datetime(frame.date), pd.to_datetime(frame.exit_date)
    folds = []
    expected = [str(year) for year in years]
    for year in map(int, expected):
        start, end = pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year + 1}-01-01")
        train = (dates < start) & (exits < start)
        valid = (dates >= start) & (dates < end)
        if train.any() and valid.any():
            folds.append({"name": str(year), "start": start, "end": end, "train_mask": train.to_numpy(), "valid_mask": valid.to_numpy()})
    if [fold["name"] for fold in folds] != expected:
        raise RuntimeError(f"Expected chronological folds {expected}, got {[fold['name'] for fold in folds]}")
    return folds


def block_bootstrap_delta(frame: pd.DataFrame, score_a: str, score_b: str, *, n_boot: int = 1000, block_weeks: int = 4, seed: int = 42) -> dict[str, Any]:
    valid = frame[[score_a, score_b, "label"]].notna().all(axis=1)
    data = frame.loc[valid].copy()
    if data.label.nunique() < 2:
        raise ValueError("AUC comparison requires two label classes")
    base = roc_auc_score(data.label, data[score_a]) - roc_auc_score(data.label, data[score_b])
    weeks = pd.to_datetime(data.date).dt.to_period("W-SUN")
    week_values = sorted(weeks.unique())
    if len(week_values) < block_weeks:
        raise ValueError("Insufficient calendar weeks for moving-block bootstrap")
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(n_boot):
        indices = []
        while len(indices) < len(data):
            start = int(rng.integers(0, len(week_values)))
            block = [week_values[(start + offset) % len(week_values)] for offset in range(block_weeks)]
            for week in block:
                indices.extend(np.flatnonzero((weeks == week).to_numpy()).tolist())
        sample = data.iloc[indices[:len(data)]]
        if sample.label.nunique() == 2:
            deltas.append(roc_auc_score(sample.label, sample[score_a]) - roc_auc_score(sample.label, sample[score_b]))
    if not deltas:
        raise RuntimeError("No valid moving-block bootstrap resamples")
    low, high = np.quantile(deltas, [0.025, 0.975])
    return {"score_a": score_a, "score_b": score_b, "delta_auc": float(base), "ci_95": [float(low), float(high)], "n_boot_valid": len(deltas), "block_weeks": block_weeks, "seed": seed}


def summarize_predictions(frame: pd.DataFrame, score_col: str) -> dict[str, Any]:
    labels = frame.label.astype(int).to_numpy()
    scores = frame[score_col].to_numpy(dtype=float)
    valid = np.isfinite(scores) & np.isfinite(labels)
    data = frame.loc[valid].copy()
    labels, scores = labels[valid], scores[valid]
    auc = float(roc_auc_score(labels, scores)) if len(np.unique(labels)) == 2 else None
    ap = float(average_precision_score(labels, scores)) if len(np.unique(labels)) == 2 else None
    data["date"] = pd.to_datetime(data.date)
    daily_auc, top5, prevalences = [], [], []
    for _, group in data.groupby("date", sort=True):
        if group.label.nunique() > 1:
            daily_auc.append(float(roc_auc_score(group.label.astype(int), group[score_col])))
        n = max(1, int(np.ceil(len(group) * 0.05)))
        selected = group.nlargest(n, score_col)
        top5.append(float(selected.label.mean()))
        prevalences.append(float(group.label.mean()))
    return {
        "events": int(len(data)), "positive_rate": float(np.mean(labels)) if len(labels) else None,
        "pooled_auc": auc, "average_precision": ap,
        "daily_auc_mean_two_class_dates": float(np.mean(daily_auc)) if daily_auc else None,
        "daily_auc_eligible_dates": len(daily_auc),
        "top5pct_precision_mean_per_date": float(np.mean(top5)) if top5 else None,
        "same_date_base_rate_mean": float(np.mean(prevalences)) if prevalences else None,
    }


def _hash_model_files(paths: Iterable[Path]) -> dict[str, str]:
    return {path.name: sha256_file(path) for path in sorted(paths)}


def _fit_final_models(eligible: pd.DataFrame, *, model_dir: Path) -> tuple[list[Path], dict[str, Any]]:
    import joblib
    ensure_dir(model_dir)
    paths, metadata = [], {}
    labels = eligible.label.astype(int).to_numpy()
    if len(np.unique(labels)) != 2:
        raise RuntimeError("Final prospective models require both label classes")
    for estimator in ESTIMATORS:
        for arm, features in FEATURE_ARMS.items():
            key = f"{estimator}_{arm}"
            model = fit_pipeline(estimator, features, eligible, labels)
            target = model_dir / f"{key}.joblib"
            joblib.dump(model, target, compress=3)
            paths.append(target)
            metadata[key] = {
                "file": target.name, "features": features, "training_events": int(len(eligible)),
                "training_start": str(pd.to_datetime(eligible.date).min().date()),
                "training_end_signal": str(pd.to_datetime(eligible.date).max().date()),
                "last_label_exit": str(pd.to_datetime(eligible.exit_date).max().date()),
                "positive_rate": float(eligible.label.mean()), "sha256": sha256_file(target),
            }
            print(f"[final fit] {key}: {len(eligible):,} matured training rows", flush=True)
    return paths, metadata


def run_development(*, data_dir: Path = DATA_DIR, ticker_limit: int | None = None, artifact_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    import joblib  # verifies serialization support
    protocol = load_protocol()
    validate_feature_whitelist(protocol)
    cutoff = _historical_replay_cutoff(protocol)
    roster = load_roster()
    input_hashes = _input_hashes(roster, data_dir)
    protocol_hash = sha256_file(PROTOCOL_PATH)
    code_path = Path(__file__).resolve()
    code_hash = sha256_file(code_path)
    test_path = ROOT / "backend" / "tests" / "test_demand_zone_study_v1.py"
    test_hash = sha256_file(test_path)
    roster_source_hash = sha256_file(ROSTER_SOURCE)
    dev_dir, model_dir = artifact_dir / "development", artifact_dir / "models"
    if artifact_dir.resolve() == ARTIFACT_DIR.resolve():
        if PROSPECTIVE_LOCK.exists() or (PROSPECTIVE_LOG.exists() and PROSPECTIVE_LOG.stat().st_size):
            raise FileExistsError("Prospective artifacts already exist; refusing to replace the canonical development archive")
        if DEVELOPMENT_DIR.exists() and any(DEVELOPMENT_DIR.iterdir()):
            raise FileExistsError("Canonical development artifacts exist; refusing overwrite")
        if MODEL_DIR.exists() and list(MODEL_DIR.glob("*.joblib")):
            raise FileExistsError("Canonical fitted models exist; refusing overwrite")
    if dev_dir.exists() and any(dev_dir.iterdir()):
        raise FileExistsError(f"Development output exists; refusing overwrite: {dev_dir}")
    if model_dir.exists() and any(model_dir.iterdir()):
        raise FileExistsError(f"Model output exists; refusing overwrite: {model_dir}")
    if ticker_limit:
        raise RuntimeError("Capped runs are disabled for this frozen development command")

    print(f"Historical signal-date cutoff (exclusive): {cutoff}", flush=True)
    events, missing = build_event_table(
        roster, data_dir=data_dir, include_labels=True,
        min_date=protocol["population"]["study_start_date"],
        max_date_exclusive=cutoff, ticker_limit=None,
    )
    if pd.to_datetime(events.date).isna().any() or (pd.to_datetime(events.date) >= pd.Timestamp(cutoff)).any():
        raise AssertionError("Historical replay emitted an invalid or post-cutoff signal date")
    ensure_dir(dev_dir)
    events.to_csv(dev_dir / "event_table.csv", index=False)
    valid = events.loc[events.label_valid.fillna(False).astype(bool) & events.label.notna()].copy()
    valid["date"], valid["exit_date"] = pd.to_datetime(valid.date), pd.to_datetime(valid.exit_date)
    if valid.label.nunique() != 2:
        raise RuntimeError("Historical eligible events do not contain both classes")
    folds = make_folds(valid)
    prediction_frames, fold_results = [], []
    for fold in folds:
        train, test = valid.loc[fold["train_mask"]].copy(), valid.loc[fold["valid_mask"]].copy()
        if not (train.exit_date < fold["start"]).all():
            raise AssertionError(f"Target-maturity purge failed for {fold['name']}")
        if train.label.nunique() != 2 or test.label.nunique() != 2:
            raise RuntimeError(f"Fold {fold['name']} requires both label classes")
        oof = test[["ticker", "date", "event_id", "label", "hold1_ret", "entry_date", "exit_date"]].copy()
        oof["fold"] = fold["name"]
        oof["fold_validation_key"] = oof.event_id.map(lambda event_id: stable_id(event_id, fold["name"]))
        expected = tuple(zip(oof.event_id, oof.label.astype(int)))
        for arm, features in FEATURE_ARMS.items():
            for estimator in ESTIMATORS:
                score = f"{estimator}_{arm}"
                fitted = fit_pipeline(estimator, features, train, train.label.astype(int).to_numpy())
                oof[score] = predict_pipeline(fitted, test)
                if tuple(zip(oof.event_id, oof.label.astype(int))) != expected:
                    raise AssertionError(f"Validation event/label set changed for {score}/{fold['name']}")
        score_cols = [f"{name}_{arm}" for name in ESTIMATORS for arm in "ABCD"]
        if oof[score_cols].isna().any().any():
            raise AssertionError(f"Missing OOF scores in {fold['name']}")
        prediction_frames.append(oof)
        fold_results.append({
            "fold": fold["name"], "train_events": len(train),
            "train_positive_rate": float(train.label.mean()),
            "train_signal_start": str(train.date.min().date()),
            "train_signal_end": str(train.date.max().date()),
            "train_label_exit_max": str(train.exit_date.max().date()),
            "validation_events": len(test), "validation_positive_rate": float(test.label.mean()),
            "validation_signal_start": str(test.date.min().date()),
            "validation_signal_end": str(test.date.max().date()),
            "all_eight_scores_same_validation_keys": True,
            "metrics": {f"{estimator}_{arm}": summarize_predictions(oof, f"{estimator}_{arm}") for estimator in ESTIMATORS for arm in "ABCD"},
        })
        print(f"[fold {fold['name']}] train={len(train):,} valid={len(test):,}", flush=True)
    predictions = pd.concat(prediction_frames, ignore_index=True)
    predictions.to_csv(dev_dir / "oof_predictions.csv", index=False)
    metrics = {f"{estimator}_{arm}": summarize_predictions(predictions, f"{estimator}_{arm}") for estimator in ESTIMATORS for arm in "ABCD"}
    contrasts = {
        "primary_LightGBM_A_minus_LogisticRegression_A": block_bootstrap_delta(predictions, "LightGBM_A", "LogisticRegression_A"),
        "primary_LightGBM_C_minus_LightGBM_B": block_bootstrap_delta(predictions, "LightGBM_C", "LightGBM_B"),
        "secondary_LogisticRegression_B_minus_A": block_bootstrap_delta(predictions, "LogisticRegression_B", "LogisticRegression_A"),
        "secondary_LightGBM_B_minus_A": block_bootstrap_delta(predictions, "LightGBM_B", "LightGBM_A"),
        "secondary_LogisticRegression_C_minus_B": block_bootstrap_delta(predictions, "LogisticRegression_C", "LogisticRegression_B"),
        "secondary_LogisticRegression_D_minus_C": block_bootstrap_delta(predictions, "LogisticRegression_D", "LogisticRegression_C"),
        "secondary_LightGBM_D_minus_C": block_bootstrap_delta(predictions, "LightGBM_D", "LightGBM_C"),
    }
    if len(predictions) != sum(fold["validation_events"] for fold in fold_results) or predictions.event_id.duplicated().any():
        raise AssertionError("OOF rows are missing or duplicated")
    final_fit = valid.loc[(valid.date < pd.Timestamp(cutoff)) & (valid.exit_date < pd.Timestamp(cutoff))].copy()
    if final_fit.empty or final_fit.label.nunique() != 2:
        raise RuntimeError("Pre-cutoff fully matured rows must contain both labels")
    final_paths, final_models = _fit_final_models(final_fit, model_dir=model_dir)
    source_coverage, prefix_hashes = {}, {}
    for symbol in roster + ["SPY", "QQQ", "IWM", "XVIX"]:
        source = read_ohlcv(symbol, data_dir)
        latest = pd.Timestamp(source.index.max())
        source_coverage[symbol] = {"first_date": str(source.index.min().date()), "last_date": str(latest.date()), "rows": len(source)}
        prefix_hashes[symbol] = _prefix_hash(source, latest)
    if _input_hashes(roster, data_dir) != input_hashes:
        raise RuntimeError("Source OHLCV changed during the development run")
    if sha256_file(code_path) != code_hash or sha256_file(PROTOCOL_PATH) != protocol_hash:
        raise RuntimeError("Study code or protocol changed during the development run")
    if sha256_file(test_path) != test_hash or sha256_file(ROSTER_SOURCE) != roster_source_hash:
        raise RuntimeError("Test suite or roster source changed during the development run")
    artifact_hashes = {
        "event_table.csv": sha256_file(dev_dir / "event_table.csv"),
        "oof_predictions.csv": sha256_file(dev_dir / "oof_predictions.csv"),
    }
    manifest = {
        "protocol_id": protocol["protocol_id"], "protocol_version": protocol["protocol_version"],
        "protocol_sha256": protocol_hash, "model_settings": protocol["estimators"],
        "code_sha256": code_hash, "test_suite_sha256": test_hash,
        "roster_source_sha256": roster_source_hash, "artifact_sha256": artifact_hashes,
        "final_model_training_cutoff": f"signal_date < {cutoff} AND exit_date < {cutoff}; later cache bars were not used for final model fitting",
        REPLAY_CUTOFF_KEY: cutoff,
        "universe_sha256": _universe_sha256(roster), "universe_tickers": roster,
        "universe_size": len(roster),
        "universe_caveat": "Recovered fixed project roster. Historical constituent membership, delisted issuers, and original selection date are unknown; no all-market inference.",
        "source_data_sha256": input_hashes, "source_data_prefix_sha256": prefix_hashes,
        "source_data_max_date_by_symbol": {symbol: row["last_date"] for symbol, row in source_coverage.items()},
        "source_data_coverage": source_coverage, "data_directory": str(data_dir.resolve()),
        "data_sha256_after_replay": _input_hashes(roster, data_dir),
        "runtime": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__, "lightgbm": lightgbm.__version__, "joblib": joblib.__version__},
        "feature_arms": FEATURE_ARMS, "feature_arms_sha256": sha256_bytes(canonical_json(FEATURE_ARMS).encode()),
        "event_generation": {
            "candidate_events": int(len(events)), "labeled_events": int(len(valid)),
            "invalid_or_unmatured_events": int(len(events) - len(valid)), "oof_events": int(len(predictions)),
            "development_only_unscored_rows": int(len(valid) - len(predictions)),
            "ticker_count_with_events": int(events.ticker.nunique()),
            "date_min": str(pd.to_datetime(events.date).min().date()),
            "date_max": str(pd.to_datetime(events.date).max().date()), "missing_roster_sources": missing,
        },
        "label": {"definition": "Open[T+2]/Open[T+1]-1 >= 0.02", "positive_rate_all_matured": float(valid.label.mean()), "label_horizon_exit_latest": str(final_fit.exit_date.max().date())},
        "chronological_development_folds": fold_results, "pooled_oof_metrics": metrics,
        "paired_week_block_bootstrap_1000": contrasts,
        "model_fit_data_scope": f"Final eight models use only labeled rows with signal_date < {cutoff} and exit_date < {cutoff}.",
        "model_artifacts": final_models, "model_artifacts_sha256": _hash_model_files(final_paths),
        "artifact_directory": str(artifact_dir.resolve()),
        "historical_interpretation": "Retrospective fixed-fold development only, not prospective evidence.",
        "limitations": [
            "Local adjusted Yahoo-derived OHLCV is not a verified point-in-time data vintage.",
            "Fixed roster membership and survivorship are unresolved; no broad-market claim.",
            "Demand-zone and order-block events are heuristic conditional samples.",
            "Ranking metrics do not establish profitability.",
            "No prospective prediction exists until a post-lock event is logged before outcomes mature.",
        ],
    }
    (dev_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, default=_json_default) + "\n", encoding="utf-8")
    _write_development_report(manifest, development_dir=dev_dir)
    print(f"Historical development finished: {len(valid):,} labels, {len(predictions):,} OOF events.", flush=True)
    return manifest


def _write_development_report(manifest: dict[str, Any], *, development_dir: Path = DEVELOPMENT_DIR) -> None:
    out = [
        "# Frozen v1 historical development run (not prospective)", "",
        f"Protocol: `{manifest['protocol_id']}` · SHA-256 `{manifest['protocol_sha256']}`  ",
        f"Code SHA-256: `{manifest['code_sha256']}`  ",
        f"Replay signal-date cutoff (exclusive): `{manifest[REPLAY_CUTOFF_KEY]}`; no candidates on or after this date.  ",
        f"Data: {manifest['event_generation']['candidate_events']:,} candidate events; {manifest['event_generation']['labeled_events']:,} mature labels; {manifest['event_generation']['oof_events']:,} OOF-scored events; {manifest['universe_size']} roster symbols; {manifest['event_generation']['date_min']}–{manifest['event_generation']['date_max']}", "",
        f"Unscored historical development rows: {manifest['event_generation']['development_only_unscored_rows']:,}.", "",
        f"Target: next-session open entry, following-session open exit; positive iff return ≥2%. Positive rate: {manifest['label']['positive_rate_all_matured']:.4f}.", "",
        "> **Retrospective development only.** No result is a profitability claim or prospective evidence.", "",
        "## Pooled out-of-fold metrics (2023–2025 chronological validation)", "",
        "| Estimator | Arm | Events | Positive rate | Pooled ROC-AUC | PR-AUC | Mean daily ROC-AUC | Top-5% precision | Same-date base rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, stats in manifest["pooled_oof_metrics"].items():
        estimator, arm = key.rsplit("_", 1)
        fmt = lambda value: "—" if value is None else f"{value:.4f}"
        out.append(f"| {estimator} | {arm} | {stats['events']:,} | {fmt(stats['positive_rate'])} | {fmt(stats['pooled_auc'])} | {fmt(stats['average_precision'])} | {fmt(stats['daily_auc_mean_two_class_dates'])} ({stats['daily_auc_eligible_dates']:,}) | {fmt(stats['top5pct_precision_mean_per_date'])} | {fmt(stats['same_date_base_rate_mean'])} |")
    out += ["", "## Paired AUC contrasts (four-week circular block bootstrap)", "", "| Contrast | Δ pooled AUC | 95% interval |", "|---|---:|---:|"]
    for name, result in manifest["paired_week_block_bootstrap_1000"].items():
        ci, delta = result.get("ci_95"), result.get("delta_auc")
        out.append(f"| {name} | {'—' if delta is None else f'{delta:+.4f}'} | {'—' if not ci else f'[{ci[0]:.4f}, {ci[1]:.4f}]'} |")
    out += ["", "## Fold-level AUC", "", "| Fold | Train n | Validation n | Logistic A/B/C/D | LightGBM A/B/C/D |", "|---|---:|---:|---|---|"]
    for fold in manifest["chronological_development_folds"]:
        metrics = fold["metrics"]
        logistic = ", ".join("—" if metrics[f"LogisticRegression_{arm}"]["pooled_auc"] is None else f"{metrics[f'LogisticRegression_{arm}']['pooled_auc']:.4f}" for arm in "ABCD")
        boosting = ", ".join("—" if metrics[f"LightGBM_{arm}"]["pooled_auc"] is None else f"{metrics[f'LightGBM_{arm}']['pooled_auc']:.4f}" for arm in "ABCD")
        out.append(f"| {fold['fold']} | {fold['train_events']:,} | {fold['validation_events']:,} | {logistic} | {boosting} |")
    out += ["", "## Limits and prospective status", ""]
    out.extend(f"- {item}" for item in manifest["limitations"])
    out += ["", "No confirmatory or prospective conclusion is available.", ""]
    (development_dir / "development_report.md").write_text("\n".join(out), encoding="utf-8")


def _model_paths(model_dir: Path = MODEL_DIR) -> list[Path]:
    return sorted(model_dir.glob("*.joblib")) if model_dir.exists() else []


def _ensure_models_match_ready(ready: dict[str, Any], model_dir: Path = MODEL_DIR) -> None:
    paths = _model_paths(model_dir)
    if _hash_model_files(paths) != ready.get("model_artifacts_sha256"):
        raise ValueError("Model files differ from the development manifest")
    if len(paths) != 8:
        raise ValueError(f"Expected eight model files, found {len(paths)}")


def freeze_prospective(*, confirm: bool, artifact_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    """Create a prospective lock only after an explicit operator confirmation."""
    if not confirm:
        raise ValueError("Explicit --confirm is required")
    prospective = artifact_dir / "prospective"
    ledger, status_path, lock_path = prospective / "events.jsonl", prospective / "status.json", prospective / "lock.json"
    if lock_path.exists() or status_path.exists() or ledger.exists() and ledger.stat().st_size:
        raise FileExistsError("Prospective artifacts exist; inspect rather than overwrite")
    ready_path = artifact_dir / "development" / "run_manifest.json"
    if not ready_path.exists():
        raise FileNotFoundError("Run and review development before prospective freeze")
    ready = json.loads(ready_path.read_text(encoding="utf-8"))
    if ready.get("code_sha256") != sha256_file(Path(__file__).resolve()):
        raise ValueError("Study code hash differs from development manifest")
    if ready.get("protocol_sha256") != sha256_file(PROTOCOL_PATH):
        raise ValueError("Protocol hash differs from development manifest")
    test_path = ROOT / "backend" / "tests" / "test_demand_zone_study_v1.py"
    if ready.get("test_suite_sha256") != sha256_file(test_path):
        raise ValueError("Test suite hash differs from development manifest")
    if ready.get(REPLAY_CUTOFF_KEY) != _historical_replay_cutoff(load_protocol()):
        raise ValueError("Development replay cutoff differs from the frozen protocol")
    if ready.get("model_artifacts_sha256") != _hash_model_files(_model_paths(artifact_dir / "models")):
        raise ValueError("Model artifact hashes differ from development manifest")
    roster = load_roster()
    if ready.get("roster_source_sha256") != sha256_file(ROSTER_SOURCE):
        raise ValueError("Roster-source hash differs from development manifest")
    if ready.get("source_data_sha256") != _input_hashes(roster, Path(ready["data_directory"])):
        raise ValueError("OHLCV source hashes differ from development manifest")
    latest_source = max(pd.Timestamp(row["last_date"]) for row in ready["source_data_coverage"].values())
    if pd.Timestamp(ready["label"]["label_horizon_exit_latest"]) >= pd.Timestamp.now(tz="UTC").tz_localize(None).normalize():
        raise ValueError("Training labels must be matured before prospective lock")
    ensure_dir(prospective)
    with ledger.open("x", encoding="utf-8") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    protocol = load_protocol()
    now = pd.Timestamp.now(tz="UTC")
    lock = {
        "protocol_id": ready["protocol_id"], "lock_timestamp_utc": now.isoformat(),
        "protocol_sha256": ready["protocol_sha256"], "code_sha256": ready["code_sha256"],
        "test_suite_sha256": ready["test_suite_sha256"], "universe_sha256": ready["universe_sha256"],
        "source_data_sha256": ready["source_data_sha256"], "source_data_prefix_sha256": ready["source_data_prefix_sha256"],
        "source_data_max_date_by_symbol": ready["source_data_max_date_by_symbol"],
        "roster_source_sha256": ready["roster_source_sha256"], "source_data_coverage": ready["source_data_coverage"],
        "source_data_latest_bar_date": str(latest_source.date()),
        "feature_arms_sha256": ready["feature_arms_sha256"], "model_artifacts_sha256": ready["model_artifacts_sha256"],
        "model_artifacts": ready["model_artifacts"], "model_fit_data_scope": ready["model_fit_data_scope"],
        "model_training_cutoff": ready["final_model_training_cutoff"], "estimators": protocol["estimators"],
        "minimum_prospective_events": protocol["prospective_evaluation"]["minimum_events"],
        "maximum_prospective_events": protocol["reproducibility"]["maximum_prospective_events"],
        "minimum_prediction_window_months": protocol["prospective_evaluation"]["minimum_duration_months"],
        "maximum_prediction_window_months": protocol["prospective_evaluation"]["maximum_duration_months"],
        "prospective_start_rule": "First successfully logged eligible close strictly after lock timestamp and latest locked source date; no backfill.",
    }
    status = {
        "protocol_id": ready["protocol_id"], "status": "locked_waiting_for_first_post_lock_prediction_and_fresh_data",
        "lock_timestamp_utc": now.isoformat(), "source_snapshot_last_bar": str(latest_source.date()),
        "first_prospective_prediction_date": None, "first_prediction_timestamp_utc": None,
        "eligible_prediction_events": 0, "matured_outcome_events": 0,
        "minimum_months": protocol["prospective_evaluation"]["minimum_duration_months"],
        "minimum_events": protocol["prospective_evaluation"]["minimum_events"],
        "maximum_months": protocol["prospective_evaluation"]["maximum_duration_months"],
        "maximum_events": protocol["reproducibility"]["maximum_prospective_events"],
        "ledger": str(ledger.resolve()), "ledger_sha256": sha256_file(ledger), "analysis_ready": False,
    }
    with status_path.open("x", encoding="utf-8") as stream:
        json.dump(status, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    with lock_path.open("x", encoding="utf-8") as stream:
        json.dump(lock, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return lock


def _prospective_maturity_state(first_prediction_timestamp_utc: str | None, prediction_count: int, matured_count: int, *, now: str | pd.Timestamp | None = None) -> dict[str, Any]:
    if not first_prediction_timestamp_utc:
        return {"analysis_ready": False, "prediction_window_closed": False, "months_elapsed": 0.0, "minimum_events_met": False, "status": "locked_waiting_for_first_eligible_prediction_event"}
    start = pd.Timestamp(first_prediction_timestamp_utc).tz_convert("UTC")
    current = pd.Timestamp(now or pd.Timestamp.now(tz="UTC")).tz_convert("UTC")
    twelve, eighteen = start + pd.DateOffset(months=12), start + pd.DateOffset(months=18)
    months_elapsed = max(0.0, (current - start).total_seconds() / (365.2425 / 12 * 86400))
    window_closed = current >= eighteen or prediction_count >= 2000
    events_met = matured_count >= 2000
    time_met = current >= twelve
    ready = time_met and events_met
    if ready:
        status = "analysis_ready"
    elif current >= eighteen and not events_met:
        status = "maximum_window_closed_event_shortfall"
    elif prediction_count >= 2000 and not time_met:
        status = "event_cap_reached_waiting_for_12_month_minimum"
    elif prediction_count >= 2000 and time_met and not events_met:
        status = "event_cap_reached_below_matured_minimum_after_12_months"
    else:
        status = "prospective_collection_in_progress"
    return {"analysis_ready": ready, "prediction_window_closed": window_closed, "months_elapsed": months_elapsed, "minimum_events_met": events_met, "status": status}


def append_hash_chained_record(path: Path, record: dict[str, Any]) -> str:
    previous = "0" * 64
    if path.exists() and path.stat().st_size:
        with path.open("rb") as stream:
            for line in stream:
                previous = json.loads(line)["record_hash"]
    payload = {key: value for key, value in record.items() if key not in {"record_hash", "previous_hash"}}
    payload["previous_hash"] = previous
    payload["record_hash"] = sha256_bytes(canonical_json(payload).encode("utf-8"))
    with path.open("a", encoding="utf-8") as stream:
        stream.write(canonical_json(payload) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return payload["record_hash"]


def verify_ledger(path: Path = PROSPECTIVE_LOG) -> dict[str, Any]:
    previous = "0" * 64
    records, prediction_runs, predictions, outcomes, seen_events, seen_outcomes = [], {}, [], {}, set(), set()
    record_count = 0
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            record = json.loads(line)
            supplied = record.get("record_hash")
            if record.get("previous_hash") != previous:
                raise AssertionError(f"Ledger previous hash mismatch at line {line_number}")
            payload = {key: value for key, value in record.items() if key not in {"record_hash", "previous_hash"}}
            calculated = sha256_bytes(canonical_json({**payload, "previous_hash": previous}).encode("utf-8"))
            if supplied != calculated:
                raise AssertionError(f"Ledger record hash mismatch at line {line_number}")
            previous = supplied
            record_count += 1
            kind = record.get("record_type")
            if kind == "prediction_run":
                run_date = record.get("requested_signal_date")
                if run_date in prediction_runs:
                    raise AssertionError(f"Duplicate prediction-run date: {run_date}")
                prediction_runs[run_date] = {"record": record, "events": 0}
                records.append(record)
            elif kind == "prediction":
                event = record.get("event_id")
                if event in seen_events:
                    raise AssertionError(f"Duplicate prospective event: {event}")
                seen_events.add(event)
                run_id = record.get("prediction_run_id")
                run = next((item for item in prediction_runs.values() if item["record"].get("run_id") == run_id), None)
                if run is None or run["record"].get("record_hash") != record.get("prediction_run_hash"):
                    raise AssertionError(f"Prediction lacks its matching run record: {event}")
                run["events"] += 1
                predictions.append(record)
            elif kind == "outcome":
                event = record.get("event_id")
                if event not in seen_events:
                    raise AssertionError(f"Orphan outcome: {event}")
                if event in seen_outcomes:
                    raise AssertionError(f"Duplicate outcome: {event}")
                prediction = next(item for item in predictions if item.get("event_id") == event)
                if record.get("prediction_hash") != prediction.get("record_hash"):
                    raise AssertionError(f"Outcome hash does not match its prediction: {event}")
                if pd.Timestamp(record["matured_at_utc"]) < pd.Timestamp(prediction["prediction_timestamp_utc"]):
                    raise AssertionError(f"Outcome predates its prediction: {event}")
                seen_outcomes.add(event)
                outcomes[event] = record
            else:
                raise AssertionError(f"Unknown ledger record type at line {line_number}: {kind}")
    incomplete = {date: {"expected": item["record"].get("eligible_events"), "logged": item["events"]} for date, item in prediction_runs.items() if item["record"].get("status") == "success" and item["events"] != item["record"].get("eligible_events")}
    return {
        "valid": True, "records": record_count,
        "prediction_events": len(predictions), "matured_outcomes": len(outcomes),
        "prediction_runs": len(prediction_runs), "incomplete_runs": incomplete,
        "last_record_hash": previous,
    }


def _refresh_status_from_ledger(
    status: dict[str, Any],
    lock: dict[str, Any],
    *,
    ledger_path: Path = PROSPECTIVE_LOG,
    now: str | pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Derive prospective counters and maturity status from the verified ledger."""
    refreshed = dict(status)
    if ledger_path.exists() and ledger_path.stat().st_size:
        ledger = verify_ledger(ledger_path)
        records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines()]
    else:
        ledger = {"valid": True, "prediction_events": 0, "matured_outcomes": 0, "prediction_runs": 0, "incomplete_runs": {}}
        records = []
    predictions = [record for record in records if record.get("record_type") == "prediction" and record.get("eligible_event", True)]
    first = predictions[0] if predictions else None
    first_timestamp = (first or {}).get("prediction_timestamp_utc")
    if first_timestamp is None and first is not None:
        signal_date = first.get("signal_date", first.get("event_date"))
        if signal_date is not None:
            first_timestamp = pd.Timestamp(signal_date).tz_localize("America/New_York").replace(hour=16).tz_convert("UTC").isoformat()
    state = _prospective_maturity_state(
        first_timestamp,
        len(predictions),
        ledger["matured_outcomes"],
        now=now,
    )
    successful_runs = [record for record in records if record.get("record_type") == "prediction_run" and record.get("status") in {"success", "no_candidate_events"}]
    refreshed.update({
        "status": state["status"],
        "first_prediction_timestamp_utc": first_timestamp,
        "first_prospective_prediction_date": (first or {}).get("signal_date", (first or {}).get("event_date")),
        "eligible_prediction_events": len(predictions),
        "matured_outcome_events": ledger["matured_outcomes"],
        "analysis_ready": state["analysis_ready"],
        "prediction_window_closed": state["prediction_window_closed"],
        "months_elapsed": state["months_elapsed"],
        "ledger_sha256": sha256_file(ledger_path) if ledger_path.exists() else None,
        "ledger_verification": ledger,
    })
    if not predictions and successful_runs:
        refreshed["status"] = "successful_no_candidate_run"
    if lock.get("lock_timestamp_utc") and not refreshed.get("lock_timestamp_utc"):
        refreshed["lock_timestamp_utc"] = lock["lock_timestamp_utc"]
    return refreshed


def mature_prospective_outcomes(
    *,
    data_dir: Path = DATA_DIR,
    artifact_dir: Path = ARTIFACT_DIR,
    as_of: str | pd.Timestamp | None = None,
) -> dict[str, Any]:
    """Append newly matured outcomes for already-logged prospective predictions."""
    ledger = artifact_dir / "prospective" / "events.jsonl"
    lock_path = artifact_dir / "prospective" / "lock.json"
    status_path = artifact_dir / "prospective" / "status.json"
    if not lock_path.exists() or not ledger.exists() or not status_path.exists():
        raise FileNotFoundError("No complete prospective lock/ledger/status exists")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    status = json.loads(status_path.read_text(encoding="utf-8"))
    expected_universe = _universe_sha256(load_roster())
    if lock.get("universe_sha256") != expected_universe:
        raise ValueError("Prospective lock universe hash is not the canonical recovered roster hash")
    verified = verify_ledger(ledger)
    records = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    predictions = [record for record in records if record.get("record_type") == "prediction" and record.get("eligible_event", True)]
    already_matured = {record["event_id"] for record in records if record.get("record_type") == "outcome"}
    maturity_date = pd.Timestamp(as_of or pd.Timestamp.now(tz="UTC")).tz_localize(None).normalize()
    bars_by_ticker: dict[str, pd.DataFrame] = {}
    appended = 0
    lock_time = pd.Timestamp(lock["lock_timestamp_utc"]).tz_convert("UTC") if lock.get("lock_timestamp_utc") else None
    latest_source = pd.Timestamp(lock.get("source_data_latest_bar_date", "1900-01-01"))
    for prediction in predictions:
        event_id = prediction.get("event_id")
        if event_id in already_matured:
            continue
        ticker = prediction.get("ticker")
        date_value = prediction.get("signal_date", prediction.get("event_date"))
        prediction_timestamp = prediction.get("prediction_timestamp_utc")
        if not ticker or not date_value or not prediction_timestamp:
            continue
        signal_date = pd.Timestamp(date_value).normalize()
        predicted_at = pd.Timestamp(prediction_timestamp).tz_convert("UTC")
        if lock_time is not None and predicted_at <= lock_time:
            raise AssertionError(f"Prospective prediction predates its lock: {event_id}")
        if signal_date <= latest_source:
            raise AssertionError(f"Prospective signal date is not after its locked source snapshot: {event_id}")
        if ticker not in bars_by_ticker:
            path = data_dir / f"{ticker.replace('^', 'X')}.csv"
            if not path.exists():
                continue
            bars_by_ticker[ticker] = read_ohlcv(ticker, data_dir)
        bars = bars_by_ticker[ticker]
        idx = bars.index.searchsorted(signal_date, side="left")
        if idx >= len(bars) or pd.Timestamp(bars.index[idx]).normalize() != signal_date or idx + 2 >= len(bars):
            continue
        entry_date, exit_date = pd.Timestamp(bars.index[idx + 1]), pd.Timestamp(bars.index[idx + 2])
        if exit_date.normalize() > maturity_date:
            continue
        entry_open, exit_open = finite_or_nan(bars.Open.iloc[idx + 1]), finite_or_nan(bars.Open.iloc[idx + 2])
        if not np.isfinite(entry_open) or entry_open <= 0 or not np.isfinite(exit_open) or exit_open <= 0:
            continue
        hold_return = exit_open / entry_open - 1
        if not np.isfinite(hold_return):
            continue
        outcome = {
            "record_type": "outcome",
            "event_id": event_id,
            "prediction_hash": prediction["record_hash"],
            "entry_date": str(entry_date.date()),
            "exit_date": str(exit_date.date()),
            "entry_open": entry_open,
            "exit_open": exit_open,
            "hold1_ret": hold_return,
            "label": int(hold_return >= 0.02),
            "matured_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        }
        append_hash_chained_record(ledger, outcome)
        already_matured.add(event_id)
        appended += 1
    verified = verify_ledger(ledger)
    status = _refresh_status_from_ledger(status, lock, ledger_path=ledger)
    status["outcomes_appended_this_run"] = appended
    status["ledger_sha256"] = sha256_file(ledger)
    status["last_maturement_check_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return {"matured_now": appended, "ledger": verified, "status": status}


def mature_prospective(*, artifact_dir: Path = ARTIFACT_DIR, as_of: str | None = None) -> dict[str, Any]:
    """CLI-compatible alias for the audited outcome maturer."""
    result = mature_prospective_outcomes(artifact_dir=artifact_dir, as_of=as_of)
    return {**result["status"], "matured_now": result["matured_now"], "ledger": result["ledger"]}


def audit(*, data_dir: Path = DATA_DIR) -> dict[str, Any]:
    protocol = load_protocol()
    cutoff = _historical_replay_cutoff(protocol)
    roster = load_roster()
    sources = _input_hashes(roster, data_dir)
    if len(sources) != len(roster) + 4:
        raise AssertionError(f"Expected 153 roster/reference sources; found {len(sources)}")
    coverage = {}
    for symbol in roster + ["SPY", "QQQ", "IWM", "XVIX"]:
        frame = read_ohlcv(symbol, data_dir)
        coverage[symbol] = {"first_date": str(frame.index.min().date()), "last_date": str(frame.index.max().date()), "rows": len(frame)}
    print(f"Audit passed: {len(roster)} roster symbols, {len(sources)} OHLCV sources, replay cutoff < {cutoff}.")
    return {"roster_size": len(roster), "source_count": len(sources), "replay_cutoff_exclusive": cutoff, "source_coverage": coverage, "source_sha256": sources}


def audit(*, data_dir: Path = DATA_DIR) -> dict[str, Any]:
    protocol = load_protocol()
    cutoff = _historical_replay_cutoff(protocol)
    roster = load_roster()
    sources = _input_hashes(roster, data_dir)
    if len(sources) != len(roster) + 4:
        raise AssertionError(f"Expected 153 roster/reference sources; found {len(sources)}")
    coverage = {}
    for symbol in roster + ["SPY", "QQQ", "IWM", "XVIX"]:
        frame = read_ohlcv(symbol, data_dir)
        coverage[symbol] = {"first_date": str(frame.index.min().date()), "last_date": str(frame.index.max().date()), "rows": len(frame)}
    print(f"Audit passed: {len(roster)} roster symbols, {len(sources)} OHLCV sources, replay cutoff < {cutoff}.")
    return {"roster_size": len(roster), "source_count": len(sources), "replay_cutoff_exclusive": cutoff, "source_coverage": coverage, "source_sha256": sources}


def log_prospective(*, signal_date: str, artifact_dir: Path = ARTIFACT_DIR) -> dict[str, Any]:
    protocol = load_protocol()
    prospective = artifact_dir / "prospective"
    lock_path, status_path, ledger = prospective / "lock.json", prospective / "status.json", prospective / "events.jsonl"
    if not lock_path.exists() or not status_path.exists() or not ledger.exists():
        raise FileNotFoundError("Prospective lock, status, and ledger must exist before predictions")
    lock, status = json.loads(lock_path.read_text(encoding="utf-8")), json.loads(status_path.read_text(encoding="utf-8"))
    signal_day = pd.Timestamp(signal_date).normalize()
    lock_time = pd.Timestamp(lock["lock_timestamp_utc"]).tz_convert("UTC")
    latest_locked = pd.Timestamp(lock["source_data_latest_bar_date"])
    if signal_day <= latest_locked or pd.Timestamp.now(tz="UTC").tz_localize(None).normalize() < signal_day:
        raise ValueError("Signal date must be fresh and strictly later than the locked source snapshot")
    if signal_day.tz_localize("America/New_York").tz_convert("UTC") <= lock_time:
        raise ValueError("Prediction close must occur after the prospective lock timestamp")
    current_hashes = _input_hashes(load_roster(), DATA_DIR)
    if current_hashes == lock["source_data_sha256"]:
        raise ValueError("No fresh OHLCV data after the lock; refusing to start/backfill prospective evaluation")
    frame, missing = build_event_table(
        load_roster(), data_dir=DATA_DIR, include_labels=False,
        min_date=str(signal_day.date()), max_date_exclusive=str((signal_day + pd.Timedelta(days=1)).date()),
        as_of=signal_day, allow_empty=True,
    )
    frame = frame.loc[pd.to_datetime(frame.date).dt.normalize() == signal_day].copy()
    if len(frame) > int(lock["maximum_prospective_events"]):
        raise ValueError("Per-date events exceed the protocol cap and must be handled by a reviewed stable truncation")
    run_id = stable_id(signal_day.date().isoformat(), lock["lock_timestamp_utc"])
    run = {
        "record_type": "prediction_run", "requested_signal_date": str(signal_day.date()),
        "run_id": run_id, "eligible_events": int(len(frame)), "status": "success",
        "missing_symbols": missing, "created_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
    }
    existing = verify_ledger(ledger)
    if existing["prediction_runs"] and signal_day.date().isoformat() <= max(pd.Timestamp(date).date() for date in [r["requested_signal_date"] for r in [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()] if r.get("record_type") == "prediction_run"]).isoformat():
        raise ValueError("Prospective signal dates must be logged strictly in chronological order")
    run_hash = append_hash_chained_record(ledger, run)
    model_dir = artifact_dir / "models"
    _ensure_models_match_ready({**lock, "model_artifacts_sha256": lock["model_artifacts_sha256"]}, model_dir)
    import joblib
    models = {path.stem: joblib.load(path) for path in _model_paths(model_dir)}
    if len(frame):
        for name, model in models.items():
            frame[name] = predict_pipeline(model, frame)
        for _, row in frame.sort_values(["date", "ticker"], kind="stable").iterrows():
            record = {
                "record_type": "prediction", "event_id": row.event_id, "ticker": row.ticker,
                "signal_date": str(pd.Timestamp(row.date).date()), "signal_timestamp": row.signal_timestamp,
                "feature_asof_date": row.feature_asof_date,
                "feature_values": {feature: finite_or_nan(row[feature]) for feature in FEATURE_ARMS["D"]},
                "scores": {name: float(row[name]) for name in models},
                "source_prefix_sha256": {symbol: _prefix_hash(read_ohlcv(symbol), pd.Timestamp(row.date)) for symbol in load_roster() + ["SPY", "QQQ", "IWM", "XVIX"]},
                "model_hashes": lock["model_artifacts_sha256"],
                "protocol_sha256": lock["protocol_sha256"], "code_sha256": lock["code_sha256"],
                "prediction_timestamp_utc": pd.Timestamp.now(tz="UTC").isoformat(),
                "prediction_run_id": run_id, "prediction_run_hash": run_hash,
            }
            append_hash_chained_record(ledger, record)
    verified = verify_ledger(ledger)
    if verified["incomplete_runs"]:
        raise AssertionError(f"Prospective run was incompletely recorded: {verified['incomplete_runs']}")
    if len(frame) and not status.get("first_prediction_timestamp_utc"):
        first = min(pd.Timestamp(value).tz_localize("America/New_York").tz_convert("UTC") for value in pd.to_datetime(frame.date).unique())
        status["first_prediction_timestamp_utc"] = first.isoformat()
        status["first_prospective_prediction_date"] = str(frame.date.min().date())
    status["eligible_prediction_events"] = verified["prediction_events"]
    status["ledger_sha256"] = sha256_file(ledger)
    status["last_prediction_run_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
    status["status"] = "prospective_collection_in_progress" if len(frame) else "successful_no_candidate_run"
    status_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return {"run": run, "predictions": len(frame), "ledger": str(ledger), "ledger_verification": verified}


def main() -> None:
    parser = argparse.ArgumentParser(description="Frozen v1.0.2 historical market-structure ablation study")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit", help="verify frozen source roster and local OHLCV coverage")
    development = subparsers.add_parser("development", help="run the bounded retrospective 2023-2025 walk-forward study")
    development.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    freeze = subparsers.add_parser("freeze-prospective", help="explicitly hash-lock reviewed models for future prospective evaluation")
    freeze.add_argument("--confirm", action="store_true", help="required confirmation before creating an immutable prospective lock")
    freeze.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    log = subparsers.add_parser("log-prospective", help="score and append a fresh post-lock session")
    log.add_argument("--date", required=True)
    log.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    mature = subparsers.add_parser("mature-prospective", help="append newly matured prospective outcomes")
    mature.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    mature.add_argument("--as-of")
    verify = subparsers.add_parser("verify-ledger", help="verify prospective append-only hash chain")
    verify.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    args = parser.parse_args()
    if args.command == "audit":
        audit()
    elif args.command == "development":
        run_development(artifact_dir=args.artifact_dir)
    elif args.command == "freeze-prospective":
        lock = freeze_prospective(confirm=args.confirm, artifact_dir=args.artifact_dir)
        print(f"Prospective lock created at {args.artifact_dir / 'prospective' / 'lock.json'}: {lock['lock_timestamp_utc']}")
    elif args.command == "log-prospective":
        print(json.dumps(log_prospective(signal_date=args.date, artifact_dir=args.artifact_dir), indent=2))
    elif args.command == "mature-prospective":
        print(json.dumps(mature_prospective(artifact_dir=args.artifact_dir, as_of=args.as_of), indent=2))
    elif args.command == "verify-ledger":
        print(json.dumps(verify_ledger(args.artifact_dir / "prospective" / "events.jsonl"), indent=2))


if __name__ == "__main__":
    main()
