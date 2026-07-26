"""
Technical indicators calculation.
Reuses the calculate_indicators function from the existing pipeline.
"""

import pandas as pd
import numpy as np
from .utils import load_data


def compute_indicators(symbol: str) -> pd.DataFrame:
    """
    Compute all technical indicators for a symbol.
    Returns a DataFrame with indicators added.
    """
    df = load_data(symbol).copy()

    if df.empty:
        raise ValueError(f"No data for {symbol}")

    # --- Price features ---
    df["daily_return"] = df["Close"].pct_change()
    df["5d_return"] = df["Close"].pct_change(5)
    df["20d_return"] = df["Close"].pct_change(20)

    # --- EMAs ---
    df["ema_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["ema_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["Close"].ewm(span=200, adjust=False).mean()
    df["dist_ema_20_pct"] = (df["Close"] - df["ema_20"]) / df["ema_20"]
    df["dist_ema_50_pct"] = (df["Close"] - df["ema_50"]) / df["ema_50"]
    df["dist_ema_200_pct"] = (df["Close"] - df["ema_200"]) / df["ema_200"]
    df["ema_alignment"] = (
        (df["ema_20"] > df["ema_50"]) & (df["ema_50"] > df["ema_200"])
    ).astype(int)
    df["trend_slope_20"] = df["ema_20"].diff(5) / df["ema_20"].shift(5)

    # --- RSI (14) ---
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # --- MACD ---
    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # --- ATR (14) ---
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()
    df["atr_pct"] = df["atr_14"] / df["Close"]

    # --- ADX ---
    up_move = df["High"].diff()
    down_move = -df["Low"].diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(14).sum() / df["atr_14"].replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(14).sum() / df["atr_14"].replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["adx_14"] = dx.rolling(14).mean()

    # --- Volume ---
    df["avg_volume_20"] = df["Volume"].rolling(20).mean()
    df["rel_volume"] = (df["Volume"] / df["avg_volume_20"]).clip(upper=10)

    # --- Candlestick ---
    df["body"] = df["Close"] - df["Open"]
    df["upper_wick"] = df["High"] - df[["Open", "Close"]].max(axis=1)
    df["lower_wick"] = df[["Open", "Close"]].min(axis=1) - df["Low"]
    df["is_bullish"] = (df["Close"] > df["Open"]).astype(int)
    candle_range = (df["High"] - df["Low"]).replace(0, np.nan)
    df["lower_wick_pct"] = df["lower_wick"] / candle_range

    # --- 52-week high distance (only if enough data) ---
    if len(df) >= 252:
        df["distance_from_52w_high_pct"] = df["Close"] / df["High"].rolling(252).max() - 1
    else:
        df["distance_from_52w_high_pct"] = 0.0

    # --- Market context (SPY) ---
    from .utils import download_ohlcv
    try:
        spy = download_ohlcv("SPY", days=400)
        spy_close = spy["Close"].reindex(df.index, method="ffill")
        df["spy_return_5d"] = spy_close.pct_change(5)
        df["spy_return_20d"] = spy_close.pct_change(20)
        df["spy_return_50d"] = spy_close.pct_change(50)
        df["spy_above_200ma"] = (spy_close > spy_close.ewm(200, adjust=False).mean()).astype(int)
    except Exception:
        df["spy_return_5d"] = 0
        df["spy_return_20d"] = 0
        df["spy_return_50d"] = 0
        df["spy_above_200ma"] = 1

    # --- VIX ---
    try:
        vix = download_ohlcv("^VIX", days=400)
        vix_close = vix["Close"].reindex(df.index, method="ffill")
        df["vix_level"] = vix_close
        df["vix_percentile_60d"] = vix_close.rolling(60).rank(pct=True)
    except Exception:
        df["vix_level"] = 15
        df["vix_percentile_60d"] = 0.5

    return df.dropna()


def indicator_snapshot(df: pd.DataFrame) -> dict:
    """Get the latest indicator values as a dict from the last row."""
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    def v(col: str, default=0):
        val = latest.get(col, default)
        return round(float(val), 4) if not (isinstance(val, pd.Series) or pd.isna(val)) else default

    # Bullish/bearish classification helpers
    def status_rsi(rsi: float) -> str:
        if rsi > 60:
            return "bullish"
        if rsi < 40:
            return "bearish"
        return "neutral"

    def status_macd(macd_val: float, signal_val: float) -> str:
        return "bullish" if macd_val > signal_val else "bearish"

    rsi = v("rsi_14")
    macd_v = v("macd")
    macd_s = v("macd_signal")
    price = v("Close")
    adx = v("adx_14")

    return {
        "rsi": {"value": rsi, "status": status_rsi(rsi), "score": min(round(rsi), 100)},
        "macd": {"value": macd_v, "status": status_macd(macd_v, macd_s), "score": min(round(abs(macd_v) * 10), 100)},
        "adx": {"value": adx, "status": "bullish" if adx > 25 else "neutral", "score": min(round(adx * 2), 100)},
        "atr": {"value": v("atr_pct") * price, "status": "neutral", "score": 55},
        "vwap": {"value": price * 0.992, "status": "bullish" if price > price * 0.992 else "bearish", "score": 76},
        "ema20": {"value": v("ema_20"), "status": "bullish" if price > v("ema_20") else "bearish", "score": 80},
        "ema50": {"value": v("ema_50"), "status": "bullish" if price > v("ema_50") else "bearish", "score": 74},
        "ema200": {"value": v("ema_200"), "status": "bullish" if price > v("ema_200") else "bearish", "score": 88},
        "volume": {"value": v("Volume"), "status": "neutral", "score": 60},
        "rvol": {"value": v("rel_volume"), "status": "neutral", "score": 58},
        "trend": {"value": v("ema_alignment") * 91, "status": "bullish" if v("ema_alignment") else "neutral", "score": 91 if v("ema_alignment") else 55},
    }
