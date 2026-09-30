"""
V2 Feature Computer — inference-time mirror of build_v2_dataset's feature blocks.

Computes the 100 V2-specific features (regime, relative strength, volume,
volatility, events) that the CatBoost V2 model expects at inference time.

Designed to be called from top_signals.py with pre-loaded benchmark data
(SPY, QQQ, IWM, VIX, sector ETFs) shared across all tickers in a scan.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
_V2_OUT = Path(__file__).resolve().parent.parent / "outputs" / "v2"
BENCHMARKS = {
    "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "VIX": "^VIX",
    "XLK": "XLK", "XLF": "XLF", "XLE": "XLE", "XLV": "XLV",
    "XLY": "XLY", "XLP": "XLP", "XLI": "XLI", "XLB": "XLB",
    "XLU": "XLU", "XLRE": "XLRE", "XLC": "XLC",
}
# Feature names expected by the V2 CatBoost model (from metadata)
_V2_FEATURES = None


def _load_v2_features():
    global _V2_FEATURES
    if _V2_FEATURES is not None:
        return _V2_FEATURES
    try:
        m = json.load(open(_MODEL_DIR / "v2" / "hold1_v2_metadata.json"))
        _V2_FEATURES = m.get("features", [])
    except Exception:
        pass
    return _V2_FEATURES or []


def compute_v2_features(stock_df: pd.DataFrame, benchmark_data: dict,
                        symbol: str = "", target_date=None) -> dict:
    """Compute all V2-specific features from raw OHLCV data.

    Args:
        stock_df: OHLCV DataFrame for the stock (Date index, Open/High/Low/Close/Volume cols)
        benchmark_data: dict of benchmark_name -> OHLCV DataFrame (e.g. {"SPY": df, ...})
        symbol: ticker symbol for earnings lookup
        target_date: the signal date (close[T]) — defaults to last row

    Returns dict of V2 feature values (single row, latest available). Keys
    match the V2 CatBoost model's expected column names. Returns empty dict
    if data insufficient.
    """
    if stock_df is None or stock_df.empty or "Close" not in stock_df.columns:
        return {}
    need = _load_v2_features()
    if not need:
        return {}
    result = {}

    c = stock_df["Close"]
    v = stock_df["Volume"]
    idx = -1 if target_date is None else stock_df.index.searchsorted(target_date, side="right") - 1
    if idx < 0 or idx >= len(stock_df):
        idx = len(stock_df) - 1

    # ── Volatility features ──
    hl = stock_df["High"] - stock_df["Low"]
    hc = (stock_df["High"] - c.shift()).abs()
    lc = (stock_df["Low"] - c.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    ret = c.pct_change()
    result["hist_vol_5d"] = _safe(ret.rolling(5).std().iloc[idx] * np.sqrt(252))
    result["hist_vol_10d"] = _safe(ret.rolling(10).std().iloc[idx] * np.sqrt(252))
    result["hist_vol_20d"] = _safe(ret.rolling(20).std().iloc[idx] * np.sqrt(252))
    rpatr = _safe((ret / (atr / c).replace(0, np.nan)).iloc[idx])
    result["return_per_atr"] = rpatr
    result["atr_trend_10"] = _safe(atr.rolling(10).mean().iloc[idx] / max(atr.rolling(40).mean().iloc[idx], 1e-9))
    result["atr_expansion_5"] = _safe(atr.iloc[idx] / max(atr.rolling(5).mean().iloc[idx], 1e-9))
    atr_pct_s = atr.rolling(60).apply(lambda x: x.iloc[-1] / max(c.iloc[-1], 1e-9))
    result["low_vol_breakout"] = int(_safe(atr_pct_s.iloc[idx]) < _safe(atr_pct_s.rolling(60).quantile(0.25).iloc[idx]))
    result["high_vol_regime"] = int(_safe(atr_pct_s.iloc[idx]) > _safe(atr_pct_s.rolling(60).quantile(0.75).iloc[idx]))

    # ── Volume features ──
    dv = v * c
    result["avg_dollar_vol_20"] = _safe(dv.rolling(20).mean().iloc[idx])
    result["dollar_vol_pctile_60"] = _safe(dv.rolling(60).rank(pct=True).iloc[idx])
    result["vol_pctile_60"] = _safe(v.rolling(60).rank(pct=True).iloc[idx])
    result["volume_spike"] = _safe(v.iloc[idx] / max(v.rolling(20).mean().iloc[idx], 1e-9))
    result["volume_trend_10"] = _safe(v.rolling(10).mean().iloc[idx] / max(v.rolling(50).mean().iloc[idx], 1e-9))
    result["obv_5d_slope"] = _safe((v * np.sign(c.diff())).fillna(0).rolling(5).sum().iloc[idx])
    result["accumulation_proxy"] = _safe(
        ((c - c.rolling(20).mean()) / (c.rolling(20).std() + 1e-9) * (v / v.rolling(20).mean())).iloc[idx])
    result["liquid_flag"] = int(_safe(dv.rolling(20).mean().iloc[idx]) >= 5e6)

    # ── Benchmark regime features (SPY, QQQ, IWM) ──
    if benchmark_data is None:
        benchmark_data = _load_benchmark_data()
    for name, bdf in list(benchmark_data.items()):
        if bdf is None or bdf.empty or "Close" not in bdf.columns:
            continue
        bc = bdf["Close"]
        # returns
        for span, tag in [(1, "1d"), (5, "5d"), (10, "10d"), (20, "20d")]:
            key = f"{name}_ret_{tag}"
            if key in need:
                # Get the value at the closest date (reindex or loc)
                bidx = min(idx, len(bc) - 1)
                result[key] = _safe(bc.pct_change(span).iloc[bidx])
        # dist from MAs
        ema20 = bc.ewm(span=20, adjust=False).mean()
        sma50 = bc.rolling(50).mean()
        sma200 = bc.rolling(200).mean()
        bidx = min(idx, len(bc) - 1)
        result[f"{name}_dist_ema20"] = _safe((bc.iloc[bidx] / max(ema20.iloc[bidx], 1e-9)) - 1)
        result[f"{name}_dist_sma50"] = _safe((bc.iloc[bidx] / max(sma50.iloc[bidx], 1e-9)) - 1)
        result[f"{name}_dist_sma200"] = _safe((bc.iloc[bidx] / max(sma200.iloc[bidx], 1e-9)) - 1)
        result[f"{name}_above_ema20"] = int(_safe(bc.iloc[bidx]) > _safe(ema20.iloc[bidx]))
        result[f"{name}_above_sma50"] = int(_safe(bc.iloc[bidx]) > _safe(sma50.iloc[bidx]))
        result[f"{name}_above_sma200"] = int(_safe(bc.iloc[bidx]) > _safe(sma200.iloc[bidx]))
        result[f"{name}_realvol_20d"] = _safe(bc.pct_change().rolling(20).std().iloc[bidx] * np.sqrt(252))

    # ── VIX-specific features ──
    vix = benchmark_data.get("VIX")
    if vix is not None and not vix.empty:
        vc = vix["Close"]
        vidx = min(idx, len(vc) - 1)
        result["vix_1d_change"] = _safe(vc.pct_change(1).iloc[vidx])
        result["vix_5d_change"] = _safe(vc.pct_change(5).iloc[vidx])
        result["vix_20d_change"] = _safe(vc.pct_change(20).iloc[vidx])
        result["vix_z_20d"] = _safe((vc - vc.rolling(20).mean()).iloc[vidx] / max(vc.rolling(20).std().iloc[vidx], 1e-9))

    # ── Relative strength (stock vs SPY and vs sector) ──
    spy = benchmark_data.get("SPY")
    if spy is not None and not spy.empty:
        sc = c.iloc[idx]
        spc = spy["Close"]
        sidx = min(idx, len(spc) - 1)
        for span, tag in [(1, "1d"), (5, "5d"), (20, "20d")]:
            key = f"rs_spy_{tag}"
            if key in need:
                sr = _safe(c.pct_change(span).iloc[idx])
                mr = _safe(spc.pct_change(span).iloc[sidx])
                result[key] = sr - mr
        # relative volume
        svr = _safe(v.iloc[idx] / max(v.rolling(20).mean().iloc[idx], 1e-9))
        spv = spy["Volume"] if "Volume" in spy.columns else pd.Series(1, index=spy.index)
        mvr = _safe(spv.iloc[sidx] / max(spv.rolling(20).mean().iloc[sidx], 1e-9))
        result["rel_vol_vs_spy"] = svr / max(mvr, 1e-9)

    # ── Sector ETF specific features (XLK_hold1 etc. won't exist at inference
    #    since those are forward returns; set to 0 as they're not tradable) ──

    # ── Earnings features ──
    try:
        earn = json.load(open(_V2_OUT / "earnings_dates.json"))
        dates = earn.get(symbol, [])
        if dates:
            dts = pd.to_datetime(dates)
            today = target_date if target_date is not None else stock_df.index[idx]
            future = dts[dts >= today]
            past = dts[dts < today]
            result["days_until_earnings"] = (future[0] - today).days if len(future) else 999
            result["days_since_earnings"] = (today - past[-1]).days if len(past) else 999
    except Exception:
        pass

    # Fill 0 for any requested feature not yet computed
    for k in need:
        if k not in result:
            result[k] = 0.0
    return {k: float(result.get(k, 0.0)) for k in need}


def _safe(val) -> float:
    try:
        v = float(val)
        return v if np.isfinite(v) else 0.0
    except Exception:
        return 0.0


# Thread-safe cache for benchmark DataFrames (avoids re-downloading per ticker)
_benchmark_cache = {}

def _load_benchmark_data() -> dict:
    """Download/cache SPY, QQQ, IWM, VIX and sector ETF OHLCV data.
    Returns dict of name -> DataFrame. First call downloads; subsequent
    calls return cached (shared across ThreadPoolExecutor workers)."""
    if _benchmark_cache:
        return _benchmark_cache
    try:
        from .utils import download_ohlcv
    except Exception:
        return {}
    for name, ticker in BENCHMARKS.items():
        try:
            df = download_ohlcv(ticker, days=400)
            if len(df) >= 50:
                _benchmark_cache[name] = df
        except Exception:
            pass
    return _benchmark_cache
