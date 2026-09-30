"""
V5 DATASET BUILDER — MASSIVE upgrade.
Extends V2 dataset with:
  1. ALL 11 sector ETF returns at 1d/5d/10d/20d horizons (PROPERLY LAGGED)
  2. Rich VIX features (percentile, z-score, level, changes at multiple horizons)
  3. Zone geometry from legacy model
  4. Pre-market gap features (gap%, gap_vs_atr, gap_direction)
  5. Magnitude targets (abs(alpha) > 2%, abs(alpha) > 3%)
  6. More interaction-ready base features

Output: outputs/v5/demand_zone_v5_dataset.csv
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

V2_DATASET = ROOT / "outputs" / "v2" / "demand_zone_v2_dataset.csv"
OUTDIR = ROOT / "outputs" / "v5"
OUTDIR.mkdir(parents=True, exist_ok=True)
OHLCV_CACHE = ROOT / "outputs" / "v2" / "_ohlcv"
OUTFILE = OUTDIR / "demand_zone_v5_dataset.csv"

# ── All 11 sector ETFs + major benchmarks ──
SECTOR_ETFS = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Healthcare", "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples", "XLI": "Industrials", "XLB": "Materials",
    "XLU": "Utilities", "XLRE": "Real Estate", "XLC": "Communication Services",
}
BENCHMARKS = {"SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "VIX": "^VIX"}
ALL_ETFS = {**SECTOR_ETFS, **BENCHMARKS}

MAGNITUDE_THRESHOLDS = [0.02, 0.03]  # abs(alpha) > 2%, > 3%


def load_benchmark_ohlcv():
    """Load all benchmark/sector OHLCV from V2 cache."""
    bench = {}
    for ticker in ALL_ETFS:
        p = OHLCV_CACHE / f"{ticker.replace('^','X')}.csv"
        if p.exists():
            df = pd.read_csv(p, index_col=0, parse_dates=True)
            if len(df) >= 200:
                bench[ticker] = df
    return bench


def compute_etf_features(bench: dict, dates: pd.DatetimeIndex, ticker_idx_map: dict = None):
    """Compute properly-lagged ETF features as-of each signal date.

    For each ETF and each date, compute returns and MAs using ONLY data
    available at close[T]. pct_change(N) at close[T] = (close[T]-close[T-N])/close[T-N]
    which is point-in-time safe since we're predicting open[T+2]-open[T+1].

    Returns DataFrame indexed same as dates with all ETF feature columns.
    """
    out = {}
    horizons = [1, 5, 10, 20, 50]
    for ticker, df in bench.items():
        if df is None or df.empty or "Close" not in df.columns:
            continue
        c = df["Close"]
        v = df["Volume"] if "Volume" in df.columns else pd.Series(1.0, index=df.index)
        # Returns at each horizon
        for h in horizons:
            ret = c.pct_change(h)
            out[f"{ticker}_ret_{h}d"] = ret.reindex(dates).values
        # Distance from EMAs/SMAs
        ema20 = c.ewm(span=20, adjust=False).mean()
        sma50 = c.rolling(50).mean()
        sma200 = c.rolling(200).mean()
        out[f"{ticker}_dist_ema20"] = ((c / ema20) - 1).reindex(dates).values
        out[f"{ticker}_dist_sma50"] = ((c / sma50) - 1).reindex(dates).values
        out[f"{ticker}_dist_sma200"] = ((c / sma200) - 1).reindex(dates).values
        # Volatility
        realvol = c.pct_change().rolling(20).std() * np.sqrt(252)
        out[f"{ticker}_realvol_20d"] = realvol.reindex(dates).values
        # Volume trend
        vol20 = v.rolling(20).mean()
        out[f"{ticker}_vol_ratio"] = (v / vol20).reindex(dates).values

    # ── VIX-specific features ──
    for vix_key in ["^VIX", "VIX"]:
        vdf = bench.get(vix_key)
        if vdf is not None and not vdf.empty:
            vc = vdf["Close"]
            out["vix_level"] = vc.reindex(dates).values
            out["vix_1d_chg"] = vc.pct_change(1).reindex(dates).values
            out["vix_5d_chg"] = vc.pct_change(5).reindex(dates).values
            out["vix_20d_chg"] = vc.pct_change(20).reindex(dates).values
            # Percentile in 60-day window
            vix_pctile = vc.rolling(60).rank(pct=True)
            out["vix_percentile_60d"] = vix_pctile.reindex(dates).values
            # Z-score in 60-day window
            vix_z = (vc - vc.rolling(60).mean()) / vc.rolling(60).std()
            out["vix_zscore_60d"] = vix_z.reindex(dates).values
            # VIX term structure proxy: VIX level vs 20-day MA
            out["vix_vs_ma20"] = (vc / vc.rolling(20).mean()).reindex(dates).values
            break

    n = len(dates)
    df_out = pd.DataFrame(index=range(n))
    for col, vals in out.items():
        arr = np.array(vals if not isinstance(vals, np.ndarray) else vals, dtype=float)
        # Fill NaN with 0 (no data available for that date)
        arr = np.where(np.isfinite(arr), arr, 0.0)
        if len(arr) == n:
            df_out[col] = arr
    return df_out


def compute_zone_geometry(row_dict: dict, stock_df: pd.DataFrame, symbol: str) -> dict:
    """Add zone geometry features from the legacy model that V4 might be missing."""
    out = {}
    # These should already be in the features dict, but ensure they're present
    eps = float(row_dict.get("entry_price", 0))
    zp = float(row_dict.get("zone_price", 0))
    if eps > 0 and zp > 0:
        out["zone_width_pct"] = abs(eps - zp) / eps
    out["zone_touches"] = float(row_dict.get("zone_touches", 0))
    out["zone_age_days"] = float(row_dict.get("zone_age_days", 0))
    # Zone freshness: 1 / (1 + age) — newer zones are fresher
    age = out["zone_age_days"]
    out["zone_freshness"] = 1.0 / (1.0 + age) if age > 0 else 1.0
    # Rejection strength proxy
    out["rejection_strength"] = float(row_dict.get("rejection_strength", 0))
    out["zone_strength"] = float(row_dict.get("zone_strength", 0))
    # Weekly/monthly zone distance (if available)
    out["base_range_pct"] = float(row_dict.get("base_range_pct", 0))
    out["departure_atr_multiple"] = float(row_dict.get("departure_atr_multiple", 0))
    return out


def compute_gap_features(stock_df: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute pre-market gap features from daily bars.

    Gap = (today's open - yesterday's close) / yesterday's close
    gap_vs_atr = gap_pct / (ATR / close)
    gap_direction = +1 (gap up), -1 (gap down), 0 (flat)
    """
    if stock_df.empty or len(stock_df) < 5:
        return pd.DataFrame({"gap_pct": np.zeros(len(dates)),
                            "gap_vs_atr": np.zeros(len(dates)),
                            "gap_direction": np.zeros(len(dates))})

    o, c = stock_df["Open"], stock_df["Close"]
    hl = stock_df["High"] - stock_df["Low"]
    hc = (stock_df["High"] - c.shift()).abs()
    lc = (stock_df["Low"] - c.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    # Reindex to signal dates
    o_aligned = o.reindex(dates)
    c_prev = c.shift(1).reindex(dates)
    atr_aligned = atr.reindex(dates)

    n = len(dates)
    gap_pct = np.zeros(n); gap_vs_atr = np.zeros(n); gap_direction = np.zeros(n, dtype=int)

    for i in range(n):
        oi = o_aligned.iloc[i] if i < len(o_aligned) else np.nan
        ci = c_prev.iloc[i] if i < len(c_prev) else np.nan
        ai = atr_aligned.iloc[i] if i < len(atr_aligned) else np.nan
        if not (np.isfinite(oi) and np.isfinite(ci) and ci > 0):
            continue
        gp = (oi - ci) / ci
        gap_pct[i] = gp
        if np.isfinite(ai) and ai > 0:
            gap_vs_atr[i] = gp / max(ai / oi, 0.001)
        if gp > 0.003:
            gap_direction[i] = 1
        elif gp < -0.003:
            gap_direction[i] = -1

    return pd.DataFrame({"gap_pct": gap_pct, "gap_vs_atr": gap_vs_atr,
                         "gap_direction": gap_direction})


def add_magnitude_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Add magnitude targets: abs(alpha_spy_hold1) > X%"""
    if "alpha_spy_hold1" not in df.columns:
        return df
    for t in MAGNITUDE_THRESHOLDS:
        tag = f"{int(t*100)}pct"
        df[f"mag_spy_{tag}"] = (df["alpha_spy_hold1"].abs() >= t).astype(int)
        print(f"  mag_spy_{tag}: base rate = {df[f'mag_spy_{tag}'].mean()*100:.1f}%")
    return df


def main():
    print("=" * 70)
    print("V5 DATASET BUILDER — ETF Armada + VIX + Zone + Gap + Magnitude")
    print("=" * 70)

    # ── Load V2 dataset ──
    df = pd.read_csv(V2_DATASET)
    df["date"] = pd.to_datetime(df["date"])
    print(f"V2: {len(df):,} rows, {df['ticker'].nunique()} tickers, "
          f"{len(df.columns)} cols, {df['date'].min().date()} -> {df['date'].max().date()}")

    # ── Load benchmarks ──
    print("\nLoading benchmark OHLCV...")
    bench = load_benchmark_ohlcv()
    print(f"  Loaded {len(bench)} benchmarks: {list(bench.keys())}")

    if not bench:
        print("ERROR: No benchmark data found in V2 cache. Aborting.")
        return

    # ── 1. Add ETF features (per-ticker, per-date) ──
    print("\nComputing ETF features (per-ticker)...")
    tickers = sorted(df["ticker"].unique())
    etf_parts = []
    for sym in tickers:
        sub = df[df["ticker"] == sym].copy()
        dates = pd.DatetimeIndex(sub["date"].values)
        etf_feats = compute_etf_features(bench, dates)
        etf_feats.index = sub.index  # align to original rows
        etf_parts.append(etf_feats)
    if etf_parts:
        etf_df = pd.concat(etf_parts)
        # Add new columns to df
        for col in etf_df.columns:
            if col not in df.columns:
                df[col] = etf_df[col].values
        print(f"  Added {len(etf_df.columns)} ETF columns: {list(etf_df.columns)[:10]}...")
    else:
        print("  WARNING: No ETF features computed")

    # ── 2. Add zone geometry features ──
    print("\nAdding zone geometry features...")
    for col, default in [("zone_width_pct", 0), ("zone_freshness", 0),
                          ("rejection_strength", 0), ("zone_strength", 0),
                          ("base_range_pct", 0), ("departure_atr_multiple", 0)]:
        if col not in df.columns:
            df[col] = default
    if "zone_width_pct" in df.columns or df["entry_price"].notna().any():
        mask = (df["entry_price"] > 0) & (df["zone_price"] > 0)
        df["zone_width_pct"] = np.where(mask, abs(df["entry_price"] - df["zone_price"]) / df["entry_price"], 0)
    df["zone_freshness"] = 1.0 / (1.0 + df["zone_age_days"].fillna(30).clip(lower=1))
    print(f"  Zone features: zone_width_pct, zone_freshness, zone_strength, etc.")

    # ── 3. Add gap features ──
    print("\nComputing gap features...")
    gap_parts = []
    for sym in tickers:
        p = OHLCV_CACHE / f"{sym}.csv"
        if not p.exists():
            continue
        stock_df = pd.read_csv(p, index_col=0, parse_dates=True)
        if stock_df.empty or len(stock_df) < 5:
            continue
        sub = df[df["ticker"] == sym].copy()
        dates = pd.DatetimeIndex(sub["date"].values)
        gf = compute_gap_features(stock_df, dates)
        gf.index = sub.index
        gap_parts.append(gf)
    if gap_parts:
        gap_df = pd.concat(gap_parts)
        for col in gap_df.columns:
            if col not in df.columns:
                df[col] = gap_df[col].values
        print(f"  Added gap features: {list(gap_df.columns)}")
    else:
        print("  WARNING: No gap features computed")

    # ── 4. Add magnitude targets ──
    print("\nAdding magnitude targets...")
    df = add_magnitude_targets(df)

    # ── 5. Fill NaN in all new columns ──
    print("\nFinal cleanup...")
    for col in df.columns:
        if df[col].dtype == float:
            df[col] = df[col].fillna(0.0)
        elif df[col].dtype == object:
            # String columns: leave as-is
            pass
    df = df.reset_index(drop=True)

    # ── Save ──
    df.to_csv(OUTFILE, index=False)
    new_cols = [c for c in df.columns if c not in 
                pd.read_csv(V2_DATASET, nrows=0).columns and c != "date"]
    print(f"\n{'='*70}")
    print(f"V5 DATASET SAVED: {OUTFILE}")
    print(f"  {len(df):,} rows, {df['ticker'].nunique()} tickers, {len(df.columns)} cols")
    print(f"  NEW columns ({len(new_cols)}): {new_cols[:15]}...")
    print(f"  Total new feature cols: {len(new_cols)}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
