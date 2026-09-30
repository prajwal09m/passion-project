"""
Build HOLD-1-DAY honest targets on top of the v13 dataset.

THE BUG BEING FIXED
-------------------
v13's `hit_target` is labeled a WIN when the intraday HIGH touches +15%
(generate_ml_dataset.py: `if high >= target_price: hit_target = 1`).
A stock that wicks +6% and closes +2.8% (e.g. DV on Aug 3) is counted as a win,
but the user's real trade (buy next open, sell the day-after open) would NOT
have captured that wick.

THIS FILE
---------
For every v13 signal row, download real OHLCV history for its ticker and compute
honest forward targets from actual market data:

  signal day T  ->  close (v13 entry_price)
  buy at open[T+1]                       (user's real entry)
  sell at open[T+2]                      (user's real 1-day exit)
  also sell at close[T+1]                (alternative same-day exit)

Targets appended:
  buy_open_ret        gap the user pays: open[T+1]/close[T] - 1
  hold1_ret           the ACTUAL 1-day hold: open[T+2]/open[T+1] - 1
  close_ret_after     close[T+1]/open[T+1] - 1
  close_and_open_hold min(close_ret_after, hold1_ret)   <- user's strict ask
  labels: hold1_2pct..hold1_6pct, co_2pct..co_6pct at each threshold
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
V13 = ROOT / "outputs" / "v13" / "demand_zone_ml_dataset_v13.csv"
OUT = ROOT / "outputs" / "hold1"
OUT.mkdir(parents=True, exist_ok=True)
OUTFILE = OUT / "demand_zone_hold1_dataset_v1.csv"

THRESHOLDS = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]


def download_history(symbol: str, period: str = "5y") -> pd.DataFrame:
    """Download OHLCV history, flatten MultiIndex, return Date-indexed df."""
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


def compute_targets(sym: str, dates: pd.Series, hist: pd.DataFrame) -> pd.DataFrame:
    """Compute honest forward targets for each signal date of a ticker.

    Signal date T: v13 entry = close[T]. User buys at open[T+1], sells at
    open[T+2] (1-day hold). We look up each signal date's position in the
    history by exact index match and read the NEXT two trading bars.
    """
    dates = pd.to_datetime(dates)
    o = hist["Open"]
    c = hist["Close"]

    # Position of each signal date within hist (exact match; NaN if absent)
    pos = hist.index.searchsorted(dates, side="right") - 1
    pos = np.clip(pos, 0, len(hist) - 1)
    exact = np.array([hist.index[i] == d for i, d in zip(pos, dates)])

    n = len(dates)
    o_arr = o.to_numpy()
    c_arr = c.to_numpy()

    buy_open = np.full(n, np.nan)
    close_after = np.full(n, np.nan)
    open_after = np.full(n, np.nan)
    buy_open_ret = np.full(n, np.nan)
    hold1_ret = np.full(n, np.nan)
    close_ret_after = np.full(n, np.nan)

    for i in range(n):
        if not exact[i]:
            continue
        p = pos[i]
        if p < len(hist) - 2:      # need T+1 and T+2 bars
            buy_open[i] = o_arr[p + 1]
            close_after[i] = c_arr[p + 1]
            open_after[i] = o_arr[p + 2]
    valid = ~np.isnan(buy_open) & ~np.isnan(open_after) & (c_arr[pos] > 0)
    buy_open_ret[valid] = buy_open[valid] / c_arr[pos[valid]] - 1.0
    hold1_ret[valid] = open_after[valid] / buy_open[valid] - 1.0
    close_ret_after[valid] = close_after[valid] / buy_open[valid] - 1.0

    out = pd.DataFrame(index=range(n))
    out["ticker"] = sym
    out["buy_open_ret"] = buy_open_ret
    out["hold1_ret"] = hold1_ret
    out["close_ret_after"] = close_ret_after
    out["close_and_open_hold"] = np.minimum(close_ret_after, hold1_ret)

    for t in THRESHOLDS:
        tag = f"{int(t*100)}pct"
        out[f"hold1_{tag}"] = (hold1_ret >= t).astype(int)
        out[f"co_{tag}"] = (out["close_and_open_hold"] >= t).astype(int)
    return out


def main():
    print("=" * 65)
    print("HOLD-1-DAY honest target builder")
    print("=" * 65)
    df = pd.read_csv(V13)
    print(f"v13 rows: {len(df):,}, tickers: {df['ticker'].nunique()}, cols: {len(df.columns)}")

    df["date"] = pd.to_datetime(df["date"])
    tickers = sorted(df["ticker"].unique())
    print(f"\nDownloading OHLCV history for {len(tickers)} tickers...")

    hist_map = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(download_history, t): t for t in tickers}
        for i, fut in enumerate(as_completed(futs), 1):
            t = futs[fut]
            h = fut.result()
            if len(h) >= 100:
                hist_map[t] = h
            if i % 25 == 0 or i == len(futs):
                print(f"  {i}/{len(futs)} downloaded ({len(hist_map)} usable)")
            elif i < len(futs):
                continue

    print(f"\nUsable histories: {len(hist_map)}/{len(tickers)}")

    # Compute targets per ticker
    print("\nComputing honest targets per signal date...")
    target_parts = []
    for sym, hist in hist_map.items():
        sub = df[df["ticker"] == sym].copy()
        tgt = compute_targets(sym, sub["date"].reset_index(drop=True), hist)
        target_parts.append(tgt)
    targets = pd.concat(target_parts, ignore_index=True)

    # Merge back onto v13 by position (same order within each ticker)
    result = df.copy()
    for col in targets.columns:
        result[col] = np.nan
    idx = 0
    for sym, hist in hist_map.items():
        n = int((df["ticker"] == sym).sum())
        tgt = targets.iloc[idx:idx + n]
        for col in tgt.columns:
            result.loc[df["ticker"] == sym, col] = tgt[col].values
        idx += n

    # Rows without targets (delisted / no data / too recent)
    nan_rows = result["hold1_ret"].isna().sum()
    print(f"\nRows with targets: {len(result) - nan_rows:,} / {len(result):,} "
          f"(skipped {nan_rows:,} due to missing history)")

    result = result.dropna(subset=["hold1_ret"]).reset_index(drop=True)
    print(f"Final rows: {len(result):,}")

    # ── Report: touch-vs-close discrepancy ──
    print("\n" + "=" * 65)
    print("HONEST TARGET DISTRIBUTION (buy open -> sell next open)")
    print("=" * 65)
    print(f"  mean buy_open_ret (gap paid):     {result['buy_open_ret'].mean()*100:+.3f}%")
    print(f"  mean hold1_ret (1-day hold):      {result['hold1_ret'].mean()*100:+.3f}%")
    print(f"  mean close_ret_after:             {result['close_ret_after'].mean()*100:+.3f}%")
    print(f"  % hold1_ret > 0:                  {(result['hold1_ret'] > 0).mean()*100:.2f}%")
    for t in THRESHOLDS:
        tag = f"{int(t*100)}pct"
        print(f"  hold1 > {int(t*100)}%: {result[f'hold1_{tag}'].mean()*100:6.2f}%  "
              f"| close AND next-open hold: {result[f'co_{tag}'].mean()*100:6.2f}%")

    result.to_csv(OUTFILE, index=False)
    print(f"\nSaved: {OUTFILE}")
    print(f"Shape: {result.shape}")


if __name__ == "__main__":
    main()
