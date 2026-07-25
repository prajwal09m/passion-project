"""Create a ticker-to-sector-ETF map used for sector-relative-strength features."""
import glob
import os
import re
import pandas as pd
import yfinance as yf

SECTOR_ETFS = {
    'Technology': 'XLK', 'Financial Services': 'XLF', 'Financial': 'XLF',
    'Energy': 'XLE', 'Healthcare': 'XLV', 'Consumer Cyclical': 'XLY',
    'Consumer Defensive': 'XLP', 'Industrials': 'XLI', 'Basic Materials': 'XLB',
    'Utilities': 'XLU', 'Real Estate': 'XLRE', 'Communication Services': 'XLC',
}
MARKET = {'SPY','QQQ','IWM','VIX','XLK','XLF','XLE','XLV','XLY','XLP','XLI','XLB','XLU','XLRE','XLC'}

def main():
    tickers = []
    for path in glob.glob('data/*_data.csv'):
        ticker = re.sub(r'_data\.csv$', '', os.path.basename(path)).upper()
        if ticker not in MARKET:
            tickers.append(ticker)
    rows = []
    for ticker in sorted(set(tickers)):
        try:
            sector = yf.Ticker(ticker).info.get('sector')
            etf = SECTOR_ETFS.get(sector)
            if etf:
                rows.append({'ticker': ticker, 'sector': sector, 'sector_etf': etf})
        except Exception:
            pass
    pd.DataFrame(rows).to_csv('data/ticker_sector_etf.csv', index=False)
    print(f'Mapped {len(rows)} of {len(tickers)} tickers.')

if __name__ == '__main__':
    main()
