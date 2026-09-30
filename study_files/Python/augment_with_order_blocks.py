"""
Augment existing ML dataset with Order Block features.
Reads a demand_zone_ml_dataset CSV, runs the order block detector for each signal,
and appends ~55 OB features. Outputs a new versioned file.

Usage:
    python augment_with_order_blocks.py --input ../outputs/v12/demand_zone_ml_dataset_v12.csv --output ../outputs/v13/demand_zone_ml_dataset_v13.csv
"""

import argparse
import os
import sys
import warnings
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

# Add parent to path for order_block_detector import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from order_block_detector import OrderBlockDetector, OrderBlockConfig, extract_ob_features_for_signal

warnings.filterwarnings("ignore")


def load_dataset(path: str) -> pd.DataFrame:
    """Load the ML dataset CSV."""
    print(f"Loading dataset from {path}...")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
    return df


def download_stock_data(ticker: str, period: str = "4y") -> Optional[pd.DataFrame]:
    """
    Download historical OHLCV data for a ticker.
    Returns None if download fails.
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Compute ATR and avg volume for OB detector
        high_low = df["High"] - df["Low"]
        high_close = np.abs(df["High"] - df["Close"].shift())
        low_close = np.abs(df["Low"] - df["Close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr_14"] = tr.rolling(14).mean()
        df["avg_volume_20"] = df["Volume"].rolling(20).mean()
        return df
    except Exception:
        return None


def process_ticker(
    ticker: str,
    ticker_df: pd.DataFrame,
    detector: OrderBlockDetector,
    data_cache: Dict[str, pd.DataFrame],
) -> Optional[pd.DataFrame]:
    """
    Process all signals for one ticker: download data, detect OBs, augment features.

    Args:
        ticker: Stock ticker symbol
        ticker_df: Subset of dataset for this ticker
        detector: Configured OrderBlockDetector
        data_cache: Cache of downloaded data to avoid re-downloading

    Returns:
        Augmented DataFrame with OB features, or None on failure
    """
    print(f"  Processing {ticker} ({len(ticker_df)} signals)...")

    # Get stock data (from cache or download)
    if ticker in data_cache:
        df = data_cache[ticker]
    else:
        df = download_stock_data(ticker)
        if df is not None:
            data_cache[ticker] = df

    if df is None or len(df) < detector.config.min_data_length:
        print(f"    {ticker}: insufficient data, filling OB features with zeros")
        return _fill_zero_ob_features(ticker_df)

    # For each signal row, extract OB features using data up to that date
    ob_features_list = []
    for _, row in ticker_df.iterrows():
        signal_date = row["date"]
        signal_price = row.get("entry_price", row.get("price", row.get("Close", 0)))
        features = extract_ob_features_for_signal(
            detector, df, signal_date, signal_price
        )
        ob_features_list.append(features)

    ob_df = pd.DataFrame(ob_features_list)
    result = pd.concat([ticker_df.reset_index(drop=True), ob_df], axis=1)
    return result


def _fill_zero_ob_features(ticker_df: pd.DataFrame) -> pd.DataFrame:
    """Fill OB features with zeros when data is unavailable."""
    from order_block_detector import _empty_ob_features
    empty = _empty_ob_features()
    for col, val in empty.items():
        ticker_df[col] = val if col not in ticker_df.columns else ticker_df[col]
    return ticker_df


def main():
    parser = argparse.ArgumentParser(
        description="Augment ML dataset with Order Block features"
    )
    parser.add_argument(
        "--input",
        default="../outputs/v12/demand_zone_ml_dataset_v12.csv",
        help="Input CSV path",
    )
    parser.add_argument(
        "--output",
        default="../outputs/v13/demand_zone_ml_dataset_v13.csv",
        help="Output CSV path",
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="Number of parallel workers for downloading",
    )
    parser.add_argument(
        "--use-cache", action="store_true",
        help="Cache downloaded stock data to speed up re-runs",
    )
    parser.add_argument(
        "--tickers", type=str, default=None,
        help="Comma-separated list of tickers to process (default: all)",
    )
    args = parser.parse_args()

    # Load dataset
    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    dataset = load_dataset(args.input)

    # Determine tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        tickers = sorted(dataset["ticker"].unique())
    print(f"Processing {len(tickers)} tickers: {tickers}")

    # Configure detector with balanced settings for batch processing
    config = OrderBlockConfig(
        min_displacement_pct=0.01,
        min_displacement_atr_mult=0.6,
        min_impulse_volume_ratio=0.5,
        require_bos=False,
        max_block_age_days=90,
    )
    detector = OrderBlockDetector(config)

    # Process each ticker
    data_cache: Dict[str, pd.DataFrame] = {}
    augmented_dfs = []

    for ticker in tickers:
        ticker_df = dataset[dataset["ticker"] == ticker].copy()
        if len(ticker_df) == 0:
            continue

        try:
            result = process_ticker(ticker, ticker_df, detector, data_cache)
            if result is not None:
                augmented_dfs.append(result)
        except Exception as e:
            print(f"    {ticker}: ERROR — {e}")
            # Fill with zeros and continue
            result = _fill_zero_ob_features(ticker_df)
            augmented_dfs.append(result)

    if not augmented_dfs:
        print("ERROR: No data processed. Check input file.")
        sys.exit(1)

    # Combine all augmented data
    final_dataset = pd.concat(augmented_dfs, ignore_index=True)

    # Sort by date (original order)
    if "date" in final_dataset.columns:
        final_dataset = final_dataset.sort_values(["ticker", "date"])

    # Remove any duplicate columns that got added
    final_dataset = final_dataset.loc[:, ~final_dataset.columns.duplicated()]

    # Save
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    final_dataset.to_csv(args.output, index=False)

    print(f"\n{'=' * 60}")
    print(f"Augmentation complete!")
    print(f"  Input:  {args.input} ({len(dataset):,} rows, {len(dataset.columns)} cols)")
    print(f"  Output: {args.output} ({len(final_dataset):,} rows, {len(final_dataset.columns)} cols)")
    print(f"  New OB features: {len(final_dataset.columns) - len(dataset.columns)} columns")

    # Summary statistics on OB features
    ob_cols = [c for c in final_dataset.columns if c.startswith("ob_")]
    if ob_cols:
        print(f"\n  OB feature summary:")
        for col in sorted(ob_cols)[:10]:
            vals = final_dataset[col].dropna()
            if len(vals) > 0:
                print(f"    {col}: mean={vals.mean():.4f}, non-zero={(vals != 0).mean()*100:.1f}%")


if __name__ == "__main__":
    main()
