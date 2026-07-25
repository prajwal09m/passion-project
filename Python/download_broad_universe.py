"""Download a liquid broad-market OHLCV universe for demand-zone research.

The files written here are consumed by generate_ml_dataset.py.  This is a
research universe, not point-in-time index membership; use an institutional
historical constituent dataset before making production/backtest claims.
"""

import argparse
import os
from datetime import date

import pandas as pd
import yfinance as yf


# Diversified, liquid U.S. sample.  Keep the list versioned for reproducibility.
BROAD_UNIVERSE = """
AAPL MSFT NVDA AMZN GOOGL META AVGO TSLA BRK-B JPM V UNH XOM LLY MA HD PG COST
JNJ ABBV WMT BAC KO NFLX CRM ORCL AMD CSCO ACN MCD DIS LIN ABT DHR WFC GE
CAT PM IBM QCOM TXN AMGN ISRG TMO NOW INTU AMAT BKNG PEP SPGI GS BLK SBUX
LOW DE BA GILD ADP MDLZ CVS C CI SCHW MO SO DUK NEE COP SLB FDX UPS GM F
PYPL SQ UBER PLTR COIN HOOD ROKU SNAP PINS DOCU ZM NET DDOG TWLO OKTA
CRWD TEAM MDB SHOP MELI TTD PANW SNOW CFLT AFRM RIVN LCID NIO BABA JD PDD
TME NKE LULU CROX TGT KHC GIS KDP XEL AEP OXY MAR HLT DAL UAL AAL
""".split()

MARKET_SERIES = [
    'SPY', 'QQQ', 'IWM', '^VIX', 'XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP',
    'XLI', 'XLB', 'XLU', 'XLRE', 'XLC'
]


def normalise_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.reset_index()
    if 'Date' not in frame.columns and 'Datetime' in frame.columns:
        frame = frame.rename(columns={'Datetime': 'Date'})
    return frame[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--years', type=int, default=8)
    parser.add_argument('--batch-size', type=int, default=20)
    parser.add_argument('--output-dir', default='data')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    end = pd.Timestamp(date.today())
    start = end - pd.DateOffset(years=args.years)
    symbols = sorted(set(BROAD_UNIVERSE + MARKET_SERIES))
    saved, failed = 0, []

    for first in range(0, len(symbols), args.batch_size):
        batch = symbols[first:first + args.batch_size]
        print(f'Downloading {first + 1}-{first + len(batch)} of {len(symbols)}...')
        raw = yf.download(batch, start=start, end=end, auto_adjust=False,
                          group_by='ticker', progress=False, threads=True)
        for symbol in batch:
            try:
                frame = raw[symbol] if isinstance(raw.columns, pd.MultiIndex) else raw
                clean = normalise_frame(frame)
                if len(clean) < 252:
                    failed.append(symbol)
                    continue
                filename = 'VIX_data.csv' if symbol == '^VIX' else f'{symbol}_data.csv'
                clean.to_csv(os.path.join(args.output_dir, filename), index=False)
                saved += 1
            except (KeyError, ValueError):
                failed.append(symbol)

    print(f'Saved {saved} OHLCV files to {args.output_dir}.')
    if failed:
        print(f'No usable data for: {", ".join(failed)}')


if __name__ == '__main__':
    main()
