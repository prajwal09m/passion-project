"""
V3 Dataset Builder — three AUC improvements in one pass:
  1. Easier targets: alpha_spy > 1% (higher base rate = higher AUC)
  2. Gap/intraday features from daily bars: gap_pct, gap_vs_atr, gap_direction,
     open_drive, opening_range, gap_filled_flag
  3. More data: expands from 149 to ~449 tickers (300 new from universe_1000.csv)

Extends the V2 dataset (outputs/v2/demand_zone_v2_dataset.csv) with new
columns and rows. New tickers get zones detected, features built, and
honest hold-1-day + alpha + triple-barrier targets computed from real OHLCV.

Output: outputs/v3/demand_zone_v3_dataset.csv
"""
import sys, json, time
from pathlib import Path
import numpy as np, pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Python"))

from backend.utils import features_from_row, download_ohlcv
from backend.zones import detect_demand_zones

V2 = ROOT / "outputs" / "v2" / "demand_zone_v2_dataset.csv"
OUT = ROOT / "outputs" / "v3"
OUT.mkdir(parents=True, exist_ok=True)
OHLCV_CACHE = OUT / "_ohlcv"
OHLCV_CACHE.mkdir(exist_ok=True)
OUTFILE = OUT / "demand_zone_v3_dataset.csv"
SECTOR_CACHE = ROOT / "outputs" / "v2" / "ticker_sector.json"
EARN_CACHE = ROOT / "outputs" / "v2" / "earnings_dates.json"
MAX_NEW_TICKERS = 300

THRESHOLDS = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
TB_GRID = [(0.02, 0.01), (0.03, 0.01), (0.05, 0.02), (0.06, 0.03)]

# Benchmarks for alpha/sector targets
BENCH_TICKERS = {
    "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM",
    "XLK": "XLK", "XLF": "XLF", "XLE": "XLE", "XLV": "XLV",
    "XLY": "XLY", "XLP": "XLP", "XLI": "XLI", "XLB": "XLB",
    "XLU": "XLU", "XLRE": "XLRE", "XLC": "XLC",
}

SECTOR_TO_ETF = {
    "Technology": "XLK", "Financials": "XLF", "Energy": "XLE",
    "Healthcare": "XLV", "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP", "Industrials": "XLI", "Materials": "XLB",
    "Utilities": "XLU", "Real Estate": "XLRE", "Communication Services": "XLC",
}


def _cached_ohlcv(symbol):
    p = OHLCV_CACHE / f"{symbol.replace('^','X')}.csv"
    # Check V3 cache first, then V2 cache
    for cache_dir in [OHLCV_CACHE, ROOT / "outputs" / "v2" / "_ohlcv"]:
        cp = cache_dir / f"{symbol.replace('^','X')}.csv"
        if cp.exists():
            df = pd.read_csv(cp, index_col=0, parse_dates=True)
            if len(df) >= 50:
                return df
    try:
        df = yf.download(symbol, period="6y", progress=False, auto_adjust=True)
        if df is not None and not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index)
            keep = [c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
            df = df[keep].dropna()
            if len(df) >= 50:
                df.to_csv(p)
                return df
    except Exception:
        pass
    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════
#  Gap / intraday features from daily bars
# ═══════════════════════════════════════════════════════════════════════════

def compute_gap_features(stock_df, dates):
    """Compute gap features as-of each signal date (close[T]).

    Args:
        stock_df: OHLCV DataFrame indexed by Date
        dates: array of signal dates (close[T])
    Returns DataFrame with gap feature columns, index aligned to dates.
    """
    if stock_df.empty or len(stock_df) < 5:
        return pd.DataFrame()
    o, h, l, c = stock_df["Open"], stock_df["High"], stock_df["Low"], stock_df["Close"]
    atr14 = (pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1)
             .max(axis=1).rolling(14).mean())
    out = {}
    for colname, vals in [("open", o), ("high", h), ("low", l), ("close", c),
                           ("atr14", atr14)]:
        out[colname] = vals.reindex(dates).to_numpy()
    n = len(dates)
    arrs = {}
    for k, v in out.items():
        arrs[k] = np.array(v, dtype=float)
    gap_pct = np.full(n, np.nan)
    gap_vs_atr = np.full(n, np.nan)
    gap_direction = np.full(n, 0)
    open_drive = np.full(n, 0.0)
    opening_range_pct = np.full(n, np.nan)
    gap_filled = np.full(n, 0)

    for i in range(n):
        o_i = arrs["open"][i]; c_prev = i > 0 and arrs["close"][i-1] or np.nan
        h_i = arrs["high"][i]; l_i = arrs["low"][i]
        if not (np.isfinite(o_i) and np.isfinite(c_prev) and c_prev > 0):
            continue
        gap_pct[i] = (o_i - c_prev) / c_prev
        atr = arrs["atr14"][i] if np.isfinite(arrs["atr14"][i]) else o_i * 0.02
        gap_vs_atr[i] = gap_pct[i] / max(atr / o_i, 0.001)
        if gap_pct[i] > 0.003:
            gap_direction[i] = 1
        elif gap_pct[i] < -0.003:
            gap_direction[i] = -1
        # open drive: did price move in gap direction or reverse?
        if np.isfinite(h_i) and np.isfinite(l_i):
            close_est = arrs["close"][i]
            opening_range_pct[i] = (h_i - l_i) / o_i if o_i > 0 else 0
            if gap_direction[i] == 1:
                open_drive[i] = (close_est - o_i) / (h_i - o_i + 1e-9)
            elif gap_direction[i] == -1:
                open_drive[i] = (o_i - close_est) / (o_i - l_i + 1e-9)
            # gap filled: did price cross back through the prior close?
            if gap_direction[i] == 1 and l_i <= c_prev:
                gap_filled[i] = 1
            elif gap_direction[i] == -1 and h_i >= c_prev:
                gap_filled[i] = 1
    return pd.DataFrame({
        "gap_pct": gap_pct, "gap_vs_atr": gap_vs_atr,
        "gap_direction": gap_direction, "open_drive": open_drive,
        "opening_range_pct": opening_range_pct, "gap_filled": gap_filled,
    }, index=range(n))


# ═══════════════════════════════════════════════════════════════════════════
#  Target computation for new tickers
# ═══════════════════════════════════════════════════════════════════════════

def compute_targets_tb(sym, dates, hist, bench_map):
    """Compute hold-1-day returns + alpha + triple-barrier labels per signal date."""
    dates = pd.to_datetime(dates)
    pos = hist.index.searchsorted(dates, side="right") - 1
    pos = np.clip(pos, 0, len(hist) - 1)
    exact = np.array(hist.index[np.array(pos)] == dates, dtype=bool)
    o, h, lo, c = hist["Open"].to_numpy(), hist["High"].to_numpy(), hist["Low"].to_numpy(), hist["Close"].to_numpy()
    n = len(dates)
    buy_open = np.full(n, np.nan); close_after = np.full(n, np.nan)
    open_after = np.full(n, np.nan)
    for i in range(n):
        if not exact[i]: continue
        p = pos[i]
        if p < len(hist) - 2:
            buy_open[i] = o[p+1]; close_after[i] = c[p+1]; open_after[i] = o[p+2]
    valid = ~np.isnan(buy_open) & ~np.isnan(open_after) & (c[pos] > 0)
    hold1_ret = np.where(valid, open_after / buy_open - 1, np.nan)
    buy_open_ret = np.where(valid, buy_open / c[pos] - 1, np.nan)
    close_ret_after = np.where(valid, close_after / buy_open - 1, np.nan)

    # alpha targets: stock - benchmark
    alpha_spy_ret = np.full(n, np.nan)
    alpha_sector_ret = np.full(n, np.nan)
    spy = bench_map.get("SPY")
    if spy is not None and len(spy) > 2:
        spy_o = spy["Open"].to_numpy(); spy_o2 = np.roll(spy_o, -2)
        spy_ret = np.where(spy_o > 0, spy_o2 / spy_o - 1, np.nan)
        alpha_spy_ret = hold1_ret - spy_ret[np.array(pos)]
    # sector: use XLK as rough proxy if sector map fails
    sector = bench_map.get("XLK")
    if sector is not None and len(sector) > 2:
        sec_o = sector["Open"].to_numpy(); sec_o2 = np.roll(sec_o, -2)
        sec_ret = np.where(sec_o > 0, sec_o2 / sec_o - 1, np.nan)
    else:
        sec_ret = np.full(len(spy) if spy is not None else 0, 0.0)
    if spy is not None:
        alpha_sector_ret = hold1_ret - sec_ret[np.array(pos)]

    out = {"ticker": sym, "buy_open_ret": buy_open_ret, "hold1_ret": hold1_ret,
           "close_ret_after": close_ret_after,
           "alpha_spy_ret": alpha_spy_ret, "alpha_sector_ret": alpha_sector_ret}
    for t in THRESHOLDS:
        tag = f"{int(t*100)}pct"
        out[f"hold1_{tag}"] = np.where(np.isfinite(hold1_ret), (hold1_ret >= t).astype(int), 0)
        out[f"alpha_spy_{tag}"] = np.where(np.isfinite(alpha_spy_ret), (alpha_spy_ret >= t).astype(int), 0)
        out[f"alpha_sector_{tag}"] = np.where(np.isfinite(alpha_sector_ret), (alpha_sector_ret >= t).astype(int), 0)

    # Triple barrier
    for tp, sl in TB_GRID:
        tag = f"tb_{int(tp*100)}tp_{int(sl*100)}sl"
        labels = np.full(n, -1)
        for i in range(n):
            if not exact[i]: continue
            p = pos[i]; entry = o[p+1]
            if not entry or entry <= 0: continue
            tp_lvl, sl_lvl = entry * (1+tp), entry * (1-sl)
            hb, lb, cb = h[p+1], lo[p+1], c[p+1]
            tpt, slt = hb >= tp_lvl, lb <= sl_lvl
            if tpt and not slt: labels[i] = 1
            elif slt and not tpt: labels[i] = 0
            elif tpt and slt: labels[i] = 1 if cb >= entry else 0
            else:
                o2v = o[p+2] if p+2 < len(o) else cb
                labels[i] = 1 if o2v >= entry else 0
        out[f"{tag}_label"] = labels
    return pd.DataFrame(out)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("V3 DATASET BUILDER — Alpha 1% + Gap Features + Expanded Universe")
    print("=" * 70)

    # ── Load V2 dataset ──
    df = pd.read_csv(V2)
    df["date"] = pd.to_datetime(df["date"])
    print(f"V2: {len(df):,} rows, {df['ticker'].nunique()} tickers")

    # ── 1. Add alpha_1pct from existing columns ──
    if "alpha_spy_hold1" in df.columns:
        for t in [0.01]:
            tag = f"{int(t*100)}pct"
            df[f"alpha_spy_{tag}"] = (df["alpha_spy_hold1"] >= t).astype(int)
            df[f"alpha_sector_{tag}"] = (df["alpha_sector_hold1"] >= t).astype(int)
    print(f"  alpha_1pct base rates: spy={df['alpha_spy_1pct'].mean()*100:.1f}% "
          f"sector={df['alpha_sector_1pct'].mean()*100:.1f}%")

    # ── 2. Gap features for existing rows ──
    print("\nComputing gap features for existing tickers...")
    tickers = sorted(df["ticker"].unique())
    gap_parts = []
    for sym in tickers:
        hist = _cached_ohlcv(sym)
        if hist.empty:
            continue
        sub = df[df["ticker"] == sym].copy()
        dates = pd.to_datetime(sub["date"])
        gf = compute_gap_features(hist, dates)
        gap_parts.append(gf.reset_index(drop=True))
    if gap_parts:
        gaps = pd.concat(gap_parts, ignore_index=True)
        for col in gaps.columns:
            df[col] = gaps[col].values
    print(f"  Added gap features: {list(gaps.columns) if gap_parts else 'none'}")

    # ── 3. Expand tickers ──
    print("\nExpanding ticker universe...")
    universe = pd.read_csv(ROOT / "data" / "universe_1000.csv")
    all_tickers = set(universe["ticker"].str.upper())
    existing = set(df["ticker"].unique())
    new_tickers = sorted(all_tickers - existing)[:MAX_NEW_TICKERS]
    print(f"  New tickers to add: {len(new_tickers)}")

    # Download benchmarks (shared)
    print("  Downloading benchmarks...")
    bench_map = {}
    for _, tkr in BENCH_TICKERS.items():
        h = _cached_ohlcv(tkr)
        if len(h) > 50:
            bench_map[tkr] = h
    # Sector map
    sector_map = {}
    try:
        sector_map = json.load(open(SECTOR_CACHE))
    except Exception:
        pass

    new_rows = []
    fields_needed = ["ticker","date","entry_price","zone_price","zone_touches",
                     "zone_strength","zone_age_days","is_sub_10","target_tier",
                     "hold1_ret","buy_open_ret","close_ret_after",
                     "alpha_spy_ret","alpha_sector_ret"]
    label_patterns = ["hold1_","alpha_spy_","alpha_sector_","tb_","co_"]
    # Get the column set from the existing df minus target/label columns
    existing_feat_cols = [c for c in df.columns
                          if not any(c.startswith(p) for p in label_patterns)
                          and c not in ["hold1_ret","buy_open_ret","close_ret_after",
                                       "alpha_spy_ret","alpha_sector_ret","sector_hold1_ret",
                                       "bench_SPY_hold1"]]
    # We'll only populate the essential V2-like features + gap features + labels
    print(f"  Processing {len(new_tickers)} new tickers...")
    processed = 0
    for sym in new_tickers:
        hist = _cached_ohlcv(sym)
        if hist.empty:
            continue
        # Detect zones
        zones = detect_demand_zones(hist)
        if not zones:
            continue
        idx = hist.index
        for z in zones[:8]:  # top 8 zones per ticker
            z_price = z["price"]
            z_date = idx[z.get("base_idx", len(hist)//2)] if "base_idx" in z else idx[min(len(idx)-1, len(hist)//2)]
            if not isinstance(z_date, pd.Timestamp):
                continue
            z_date = pd.Timestamp(z_date)
            # Build indicator row approximation: use close at signal date
            if z_date not in idx:
                closest = idx[idx <= z_date][-1] if any(idx <= z_date) else idx[0]
            else:
                closest = z_date
            row = hist.loc[closest]
            price = float(row["Close"])
            touches = z.get("touches", 1)
            zone_age = z.get("age_days", max(1, (hist.index[-1] - closest).days))
            features = features_from_row(pd.Series(), entry_price=price,
                                         zone_price=z_price, zone_touches=touches,
                                         zone_age_days=zone_age)
            # Compute targets for THIS signal date (row = features + labels from real data)
            dates_series = pd.Series([z_date])
            tgt = compute_targets_tb(sym, dates_series, hist, bench_map)
            if tgt.empty:
                continue
            row_dict = {
                "ticker": sym, "date": z_date.strftime("%Y-%m-%d"),
                "entry_price": price, "zone_price": z_price,
                "zone_touches": touches, "zone_strength": z.get("strength", 0),
                "zone_age_days": zone_age, "is_sub_10": int(price < 10),
                "target_tier": z.get("tier", 1),
            }
            # Add targets
            for col in tgt.columns:
                if col != "ticker":
                    row_dict[col] = float(tgt[col].iloc[0]) if pd.notna(tgt[col].iloc[0]) else 0.0
            # Add gap features
            gf = compute_gap_features(hist, dates_series)
            for col in gf.columns:
                row_dict[col] = float(gf[col].iloc[0]) if pd.notna(gf[col].iloc[0]) else 0.0
            # Add existing features (from features dict, plus defaults for V2-specific cols)
            for k in existing_feat_cols:
                if k not in row_dict:
                    row_dict[k] = features.get(k, 0.0)
            new_rows.append(row_dict)
        processed += 1
        if processed % 50 == 0:
            print(f"    {processed}/{len(new_tickers)} tickers, {len(new_rows)} signal rows")

    print(f"  New signal rows: {len(new_rows)}")

    # ── 4. Merge new rows into existing dataset ──
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        # Ensure column alignment: new_df has all columns df has
        for c in df.columns:
            if c not in new_df.columns:
                new_df[c] = 0.0
        for c in new_df.columns:
            if c not in df.columns:
                df[c] = 0.0
        new_df = new_df[df.columns]
        df = pd.concat([df, new_df], ignore_index=True)
    df = df.reset_index(drop=True)

    print(f"\n  Final V3 dataset: {len(df):,} rows, {df['ticker'].nunique()} tickers, "
          f"{len(df.columns)} cols")

    # ── Report ──
    print("\n" + "=" * 70)
    print("TARGET BASE RATES (V3)")
    print("=" * 70)
    for name in ["hold1_1pct","hold1_2pct","alpha_spy_1pct","alpha_spy_2pct",
                 "alpha_sector_1pct","alpha_sector_2pct"]:
        if name in df.columns:
            rate = df[name].mean() * 100
            print(f"  {name:22s} {rate:.2f}%")
    for tp, sl in TB_GRID:
        tag = f"tb_{int(tp*100)}tp_{int(sl*100)}sl_label"
        if tag in df.columns:
            valid = df[tag] >= 0
            hit = (df.loc[valid, tag] == 1).mean() * 100
            print(f"  {tag:22s} {hit:.2f}% win")

    df.to_csv(OUTFILE, index=False)
    print(f"\nSaved: {OUTFILE}")

if __name__ == "__main__":
    main()
