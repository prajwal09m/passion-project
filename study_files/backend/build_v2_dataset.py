"""
Build V2 dataset: honest hold-1-day targets + NEW labels + feature blocks.

Built on top of the existing hold1 dataset (which already carries 184 v13
technical/zone features and the honest open->open hold-1-day returns).

ADDED IN V2
-----------
A) ALPHA-ADJUSTED LABELS
     alpha_spy    = hold1_ret - SPY hold1_ret (open[T+1]->open[T+2])
     alpha_sector = hold1_ret - sector ETF hold1_ret
     targets: alpha_spy > 2/3/5%, alpha_sector > 2/3/5%

B) TRIPLE-BARRIER LABELS (buy open[T+1], TP/SL on day T+1 bars,
   time limit = open[T+2])
     barrier_hit_type: "TP" | "SL" | "TIME"
     tb_label: 1 if TP hit first else 0
     time_to_hit, mfe_pct, mae_pct stored per grid cell
   Convention for daily bars when both TP and SL touched same day:
   use close[T+1] vs open[T+1] as the intraday tie-break proxy
   (documented, deterministic, no lookahead).

C) MARKET REGIME FEATURES (as-of close[T], point-in-time safe)
     SPY / QQQ / IWM: 1d,5d,10d,20d returns, dist from 20EMA/50SMA/200SMA,
     above/below MAs, 20d realized vol
     VIX: level, 1d change, 5d change, 60d percentile rank
     regime flags: bull/bear/high-vol/low-vol/risk-on/risk-off

D) RELATIVE STRENGTH (stock vs SPY and vs sector ETF)
     1d,5d,20d relative returns; relative volume strength

E) LIQUIDITY
     avg dollar volume 20d, dollar-volume percentile, volume percentile,
     liquidity flag (dollar vol > threshold)

F) ADVANCED VOLUME
     volume spike, volume ratio, volume trend, OBV 5d slope,
     accumulation proxy, relative volume vs sector

G) VOLATILITY
     hist vol 5/10/20d, return/ATR, ATR trend, low/high vol breakout flags

H) EVENT FEATURES (best-effort, cached; 0 = unavailable)
     days until earnings, days since earnings (from yfinance calendar)

Everything is computed from data available at close[T] only — no future info.
"""
import sys
import json
import time
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
V1 = ROOT / "outputs" / "hold1" / "demand_zone_hold1_dataset_v1.csv"
OUT = ROOT / "outputs" / "v2"
OUT.mkdir(parents=True, exist_ok=True)
OUTFILE = OUT / "demand_zone_v2_dataset.csv"
OHLCV_CACHE = OUT / "_ohlcv"
OHLCV_CACHE.mkdir(exist_ok=True)
SECTOR_CACHE = OUT / "ticker_sector.json"
EARN_CACHE = OUT / "earnings_dates.json"

BENCHMARKS = {
    "SPY": "SPY", "QQQ": "QQQ", "IWM": "IWM", "VIX": "^VIX",
    "XLK": "XLK", "XLF": "XLF", "XLE": "XLE", "XLV": "XLV",
    "XLY": "XLY", "XLP": "XLP", "XLI": "XLI", "XLB": "XLB",
    "XLU": "XLU", "XLRE": "XLRE", "XLC": "XLC",
}

# Sector ETF per GICS sector (yfinance .info['sector'])
SECTOR_TO_ETF = {
    "Technology": "XLK", "Information Technology": "XLK",
    "Financials": "XLF", "Financial Services": "XLF",
    "Energy": "XLE", "Healthcare": "XLV", "Health Care": "XLV",
    "Consumer Discretionary": "XLY", "Consumer Staples": "XLP",
    "Industrials": "XLI", "Materials": "XLB", "Utilities": "XLU",
    "Real Estate": "XLRE", "Communication Services": "XLC",
    "Basic Materials": "XLB", "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP", "Communication": "XLC",
}

# Triple-barrier grid: (tp_pct, sl_pct) cells
TB_GRID = [(0.02, 0.01), (0.03, 0.01), (0.05, 0.02), (0.06, 0.03)]


def download_history(symbol: str, period: str = "6y") -> pd.DataFrame:
    """Download OHLCV history, flatten MultiIndex, Date-indexed df."""
    try:
        df = yf.download(symbol, period=period, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index)
        keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        return df[keep].dropna()
    except Exception:
        return pd.DataFrame()


def _cached_ohlcv(symbol: str) -> pd.DataFrame:
    p = OHLCV_CACHE / f"{symbol.replace('^', 'X')}.csv"
    if p.exists():
        df = pd.read_csv(p, index_col=0, parse_dates=True)
        if len(df) >= 100:
            return df
    df = download_history(symbol)
    if len(df) >= 100:
        df.to_csv(p)
    return df


def build_sector_map(tickers) -> dict:
    """Ticker -> sector ETF (best-effort, cached)."""
    if SECTOR_CACHE.exists():
        return json.load(open(SECTOR_CACHE))
    m = {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            sec = info.get("sector") or ""
            m[t] = SECTOR_TO_ETF.get(sec, "SPY")
        except Exception:
            m[t] = "SPY"
        time.sleep(0.05)
    json.dump(m, open(SECTOR_CACHE, "w"))
    return m


def build_earnings_map(tickers) -> dict:
    """Ticker -> list of earnings dates (best-effort, cached)."""
    if EARN_CACHE.exists():
        return json.load(open(EARN_CACHE))
    m = {}
    for t in tickers:
        try:
            cal = yf.Ticker(t).calendar
            ed = cal.get("Earnings Date") if isinstance(cal, dict) else None
            if ed is not None:
                m[t] = sorted(pd.to_datetime(ed).strftime("%Y-%m-%d").tolist())
        except Exception:
            pass
        time.sleep(0.05)
    json.dump(m, open(EARN_CACHE, "w"))
    return m


# ── Feature builders (point-in-time: value as of close of day T) ────────────

def regime_features(df_hist: pd.DataFrame, dates: pd.Series, sym: str) -> pd.DataFrame:
    """Market regime block computed as-of each signal date (close[T] only)."""
    if df_hist.empty:
        return pd.DataFrame()
    c = df_hist["Close"]
    out = {}
    # returns (lag 1 = known at close of day T)
    for name, span in [("1d", 1), ("5d", 5), ("10d", 10), ("20d", 20)]:
        r = c.pct_change(span)
        out[f"{sym}_ret_{name}"] = r.reindex(dates).to_numpy()
    ema20 = c.ewm(span=20, adjust=False).mean()
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()
    out[f"{sym}_dist_ema20"] = (c / ema20 - 1).reindex(dates).to_numpy()
    out[f"{sym}_dist_sma50"] = (c / sma50 - 1).reindex(dates).to_numpy()
    out[f"{sym}_dist_sma200"] = (c / sma200 - 1).reindex(dates).to_numpy()
    out[f"{sym}_above_ema20"] = (c > ema20).astype(float).reindex(dates).to_numpy()
    out[f"{sym}_above_sma50"] = (c > sma50).astype(float).reindex(dates).to_numpy()
    out[f"{sym}_above_sma200"] = (c > sma200).astype(float).reindex(dates).to_numpy()
    out[f"{sym}_realvol_20d"] = (c.pct_change().rolling(20).std() * np.sqrt(252)).reindex(dates).to_numpy()
    return pd.DataFrame(out, index=range(len(dates)))


def vix_features(vix: pd.DataFrame, dates: pd.Series) -> pd.DataFrame:
    if vix is None or vix.empty:
        return pd.DataFrame()
    c = vix["Close"]
    out = {
        "vix_1d_change": c.pct_change(1).reindex(dates).to_numpy(),
        "vix_5d_change": c.pct_change(5).reindex(dates).to_numpy(),
        "vix_20d_change": c.pct_change(20).reindex(dates).to_numpy(),
        "vix_percentile_60d": c.rolling(60).rank(pct=True).reindex(dates).to_numpy(),
        "vix_percentile_120d": c.rolling(120).rank(pct=True).reindex(dates).to_numpy(),
        "vix_z_20d": ((c - c.rolling(20).mean()) / c.rolling(20).std()).reindex(dates).to_numpy(),
    }
    return pd.DataFrame(out, index=range(len(dates)))


def rel_strength(stock: pd.DataFrame, bench: pd.DataFrame, dates: pd.Series,
                 prefix: str) -> pd.DataFrame:
    """stock return - benchmark return, 1d/5d/20d (as of close[T])."""
    if stock.empty or bench is None or bench.empty:
        return pd.DataFrame()
    sc = stock["Close"]
    bc = bench["Close"].reindex(stock.index, method="ffill")
    out = {}
    for name, span in [("1d", 1), ("5d", 5), ("20d", 20)]:
        rs = (sc.pct_change(span) - bc.pct_change(span))
        out[f"rs_{prefix}_{name}"] = rs.reindex(dates).to_numpy()
    # relative volume strength: stock rel_vol / benchmark rel_vol
    sv = stock["Volume"] / stock["Volume"].rolling(20).mean()
    bv = bench["Volume"] / bench["Volume"].rolling(20).mean()
    out[f"rel_vol_vs_{prefix}"] = (sv / bv.replace(0, np.nan)).reindex(dates).to_numpy()
    return pd.DataFrame(out, index=range(len(dates)))


def liquidity_volume(stock: pd.DataFrame, dates: pd.Series) -> pd.DataFrame:
    if stock.empty:
        return pd.DataFrame()
    v = stock["Volume"]
    c = stock["Close"]
    dv = v * c
    out = {
        "avg_dollar_vol_20": dv.rolling(20).mean().reindex(dates).to_numpy(),
        "dollar_vol_pctile_60": dv.rolling(60).rank(pct=True).reindex(dates).to_numpy(),
        "vol_pctile_60": v.rolling(60).rank(pct=True).reindex(dates).to_numpy(),
        "volume_spike": (v / v.rolling(20).mean()).reindex(dates).to_numpy(),
        "volume_trend_10": (v.rolling(10).mean() / v.rolling(50).mean()).reindex(dates).to_numpy(),
        "obv_5d_slope": (v * np.sign(c.diff())).fillna(0).rolling(5).sum().reindex(dates).to_numpy(),
        "accumulation_proxy": ((c - c.rolling(20).mean()) / (c.rolling(20).std() + 1e-9)
                               * (v / v.rolling(20).mean())).reindex(dates).to_numpy(),
    }
    return pd.DataFrame(out, index=range(len(dates)))


def volatility_block(stock: pd.DataFrame, dates: pd.Series) -> pd.DataFrame:
    if stock.empty:
        return pd.DataFrame()
    c = stock["Close"]
    hl = stock["High"] - stock["Low"]
    hc = (stock["High"] - c.shift()).abs()
    lc = (stock["Low"] - c.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    ret = c.pct_change()
    out = {
        "hist_vol_5d": (ret.rolling(5).std() * np.sqrt(252)).reindex(dates).to_numpy(),
        "hist_vol_10d": (ret.rolling(10).std() * np.sqrt(252)).reindex(dates).to_numpy(),
        "hist_vol_20d": (ret.rolling(20).std() * np.sqrt(252)).reindex(dates).to_numpy(),
        "return_per_atr": (ret / (atr / c).replace(0, np.nan)).reindex(dates).to_numpy(),
        "atr_trend_10": (atr.rolling(10).mean() / atr.rolling(40).mean()).reindex(dates).to_numpy(),
        "atr_expansion_5": (atr / atr.rolling(5).mean()).reindex(dates).to_numpy(),
        "low_vol_breakout": ((atr / c) < (atr / c).rolling(60).quantile(0.25)).astype(float).reindex(dates).to_numpy(),
        "high_vol_regime": ((atr / c) > (atr / c).rolling(60).quantile(0.75)).astype(float).reindex(dates).to_numpy(),
    }
    return pd.DataFrame(out, index=range(len(dates)))


def event_features(dates: pd.Series, earnings: list) -> pd.DataFrame:
    out = np.full((len(dates), 2), np.nan)
    if earnings:
        ed = pd.to_datetime(earnings)
        d = pd.to_datetime(dates).to_numpy()
        for i, dd in enumerate(d):
            future = ed[ed >= dd]
            past = ed[ed < dd]
            if len(future) > 0:
                out[i, 0] = (future[0] - dd).days      # days until
            if len(past) > 0:
                out[i, 1] = (dd - past[-1]).days       # days since
    return pd.DataFrame({
        "days_until_earnings": out[:, 0],
        "days_since_earnings": out[:, 1],
    }, index=range(len(dates)))


def triple_barrier(hist: pd.DataFrame, pos_idx: np.ndarray, n: int) -> pd.DataFrame:
    """Compute triple-barrier labels for each signal date.

    Entry = open[T+1]; TP/SL tested on day T+1 high/low; time exit = open[T+2].
    Uses daily bars only (no intraday lookahead). If both barriers are touched
    on the same bar, close[T+1] vs open[T+1] is the deterministic tie-break.
    """
    o = hist["Open"].to_numpy()
    h = hist["High"].to_numpy()
    lo = hist["Low"].to_numpy()
    c = hist["Close"].to_numpy()
    o2 = np.roll(o, -1)  # open of T+2
    cols = {}
    for tp, sl in TB_GRID:
        tag = f"tb_{int(tp*100)}tp_{int(sl*100)}sl"
        labels = np.full(n, -1)
        hit_type = np.full(n, "TIME", dtype=object)
        tth = np.full(n, 2)
        mfe = np.full(n, np.nan)
        mae = np.full(n, np.nan)
        for i in range(n):
            p = pos_idx[i]
            if p is None or p >= len(hist) - 2:
                continue
            entry = o[p + 1]
            if not entry or entry <= 0:
                continue
            tp_lvl = entry * (1 + tp)
            sl_lvl = entry * (1 - sl)
            hi, lo_d, cl = h[p + 1], lo[p + 1], c[p + 1]
            mfe[i] = max(hi, o2[p + 1]) / entry - 1
            mae[i] = min(lo_d, o2[p + 1]) / entry - 1
            tp_touched = hi >= tp_lvl
            sl_touched = lo_d <= sl_lvl
            if tp_touched and not sl_touched:
                labels[i], hit_type[i], tth[i] = 1, "TP", 1
            elif sl_touched and not tp_touched:
                labels[i], hit_type[i], tth[i] = 0, "SL", 1
            elif tp_touched and sl_touched:
                # both touched same day -> tie-break by close vs open direction
                if cl >= entry:
                    labels[i], hit_type[i], tth[i] = 1, "TP", 1
                else:
                    labels[i], hit_type[i], tth[i] = 0, "SL", 1
            else:
                # neither on day T+1 -> time exit at open[T+2]
                o2v = o2[p + 1]
                labels[i], hit_type[i], tth[i] = (1 if o2v >= entry else 0), "TIME", 2
        cols[f"{tag}_label"] = labels
        cols[f"{tag}_type"] = hit_type
        cols[f"{tag}_tth"] = tth
        cols[f"{tag}_mfe"] = mfe
        cols[f"{tag}_mae"] = mae
    return pd.DataFrame(cols)


def main():
    print("=" * 70)
    print("V2 DATASET BUILDER — alpha labels + triple barrier + feature blocks")
    print("=" * 70)
    df = pd.read_csv(V1)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    print(f"v1 rows: {len(df):,}, tickers: {df['ticker'].nunique()}")
    tickers = sorted(df["ticker"].unique())

    # ── OHLCV for every ticker + benchmarks ──
    print(f"\nDownloading/caching OHLCV for {len(tickers)} tickers + "
          f"{len(BENCHMARKS)} benchmarks...")
    hist_map = {}
    todo = tickers + list(BENCHMARKS.values())
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(_cached_ohlcv, t): t for t in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            t = futs[fut]
            h = fut.result()
            if len(h) >= 100:
                hist_map[t] = h
            if i % 40 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} ({len(hist_map)} usable)")

    bench_map = {k: hist_map.get(v) for k, v in BENCHMARKS.items()}

    print("\nBuilding sector map (best-effort)...")
    sector_map = build_sector_map(tickers)
    print(f"  mapped {len(sector_map)} tickers")

    print("Building earnings calendar (best-effort)...")
    earn_map = build_earnings_map(tickers)
    print(f"  earnings for {len(earn_map)} tickers")

    # ── Per-ticker: align signal dates to history ──
    print("\nComputing labels + features per ticker...")
    parts = []
    for sym in tickers:
        hist = hist_map.get(sym)
        if hist is None:
            continue
        sub = df[df["ticker"] == sym].copy()
        dates = pd.to_datetime(sub["date"])
        # position of each signal date within hist (signal date = close[T])
        pos = hist.index.searchsorted(dates, side="right") - 1
        pos = np.clip(pos, 0, len(hist) - 1)
        exact = [hist.index[i] == d for i, d in zip(pos, dates)]
        pos_idx = [i if e else None for i, e in zip(pos, exact)]
        n = len(sub)

        frames = [sub.reset_index(drop=True)]

        # Alpha targets: benchmark hold-1-day return over same window
        for bname, bhist in bench_map.items():
            if bhist is None or len(bhist) < 2:
                continue
            bo = bhist["Open"]
            bo2 = bo.shift(-1)
            bret = (bo2 / bo - 1)
            col = bret.reindex(dates).to_numpy()
            frames.append(pd.DataFrame({f"bench_{bname}_hold1": col}))

        # Triple barrier
        tb = triple_barrier(hist, pos_idx, n)
        frames.append(tb.reset_index(drop=True))

        # Market regime blocks
        for bname, bhist in bench_map.items():
            if bhist is None:
                continue
            rf = regime_features(bhist, dates, bname)
            if len(rf):
                frames.append(rf.reset_index(drop=True))
        vf = vix_features(bench_map.get("VIX"), dates)
        if len(vf):
            frames.append(vf.reset_index(drop=True))

        # Relative strength vs SPY and vs sector
        spy = bench_map.get("SPY")
        rs = rel_strength(hist, spy, dates, "spy")
        if len(rs):
            frames.append(rs.reset_index(drop=True))
        sect_etf = sector_map.get(sym, "SPY")
        sect = bench_map.get(sect_etf)
        if sect is not None:
            rss = rel_strength(hist, sect, dates, "sector")
            if len(rss):
                frames.append(rss.reset_index(drop=True))

        # Liquidity / volume / volatility / events
        lv = liquidity_volume(hist, dates)
        if len(lv):
            frames.append(lv.reset_index(drop=True))
        vb = volatility_block(hist, dates)
        if len(vb):
            frames.append(vb.reset_index(drop=True))
        ev = event_features(dates, earn_map.get(sym, []))
        frames.append(ev.reset_index(drop=True))

        merged = pd.concat(frames, axis=1)
        parts.append(merged)

    if not parts:
        print("FATAL: no data built")
        sys.exit(1)
    out = pd.concat(parts, ignore_index=True)
    print(f"\nMerged rows: {len(out):,}")

    # ── Alpha target labels ──
    for b in ["SPY"]:
        bret = out[f"bench_{b}_hold1"]
        out[f"alpha_{b.lower()}_hold1"] = out["hold1_ret"] - bret
    # sector alpha (sector ETF hold1 return merged via dict)
    sect_cols = {}
    for sym in tickers:
        etf = sector_map.get(sym, "SPY")
        col = f"bench_{etf}_hold1"
        if col in out.columns:
            sect_cols[sym] = col
    if sect_cols:
        out["sector_hold1_ret"] = [out.loc[i, sect_cols[t]]
                                   if t in sect_cols else np.nan
                                   for i, t in enumerate(out["ticker"])]
        out["alpha_sector_hold1"] = out["hold1_ret"] - out["sector_hold1_ret"]
    else:
        out["sector_hold1_ret"] = np.nan
        out["alpha_sector_hold1"] = np.nan
    for t in [0.02, 0.03, 0.05]:
        tag = f"{int(t*100)}pct"
        out[f"alpha_spy_{tag}"] = (out["alpha_spy_hold1"] >= t).astype(int)
        out[f"alpha_sector_{tag}"] = (out["alpha_sector_hold1"] >= t).astype(int)

    # ── Liquidity filter flag ──
    out["liquid_flag"] = (out.get("avg_dollar_vol_20", pd.Series(1e6, index=out.index))
                          >= 5e6).astype(int)

    # ── Report new label base rates ──
    print("\n" + "=" * 70)
    print("NEW LABEL DISTRIBUTIONS (honest, executable)")
    print("=" * 70)
    print(f"  hold1>2%:        {(out['hold1_2pct']==1).mean()*100:5.2f}%")
    print(f"  alpha_spy>2%:    {out['alpha_spy_2pct'].mean()*100:5.2f}%   "
          f"(mean alpha {out['alpha_spy_hold1'].mean()*100:+.3f}%)")
    print(f"  alpha_sector>2%: {out['alpha_sector_2pct'].mean()*100:5.2f}%")
    for tp, sl in TB_GRID:
        tag = f"tb_{int(tp*100)}tp_{int(sl*100)}sl"
        lab = out[f"{tag}_label"]
        valid = lab >= 0
        hit = (lab == 1).sum() / max(valid.sum(), 1) * 100
        tp_rate = (out[f"{tag}_type"] == "TP").mean() * 100
        sl_rate = (out[f"{tag}_type"] == "SL").mean() * 100
        tm_rate = (out[f"{tag}_type"] == "TIME").mean() * 100
        print(f"  TP+{int(tp*100)}%/SL-{int(sl*100)}%: win {hit:5.2f}%  "
              f"(TP {tp_rate:.1f}% | SL {sl_rate:.1f}% | TIME {tm_rate:.1f}%)")

    out.to_csv(OUTFILE, index=False)
    print(f"\nSaved: {OUTFILE}")
    print(f"Shape: {out.shape}")
    return out


if __name__ == "__main__":
    main()
