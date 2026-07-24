"""
Stock Demand Zone ML Dataset Generator
Feature engineering pipeline for ML-ready demand zone signal detection
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import warnings
from typing import Dict, List, Tuple, Optional
warnings.filterwarnings('ignore')

# Configuration
CONFIG = {
    'min_price': 1.0,            # Minimum price per share ($1+)
    'max_price': 10.0,           # Maximum price per share (under $10)
    'min_volume': 1000000,       # Min average daily volume (1M+ shares)
    'target_universe_size': 100, # Target number of stocks
    'history_years': 5,          # Years of historical data
    'trailing_days': 90,        # Trailing days for zone detection
    'zone_touch_threshold': 0.03,  # 3% tolerance for zone touches
    'zone_break_threshold': 0.05,  # 5% tolerance for zone breaks
    'min_zone_touches': 2,       # Minimum touches to qualify as zone
    'signal_lookahead': 2,       # Days after signal to check for confirmation
    'min_green_candles': 2,      # Minimum consecutive green candles for confirmation
    'min_absolute_threshold': 0.15,  # Minimum absolute threshold for stocks under $2
    'trade_horizon_days': 20,     # Days to simulate trade outcomes
    'target_gain_pct': 0.15,      # 15% profit target (updated from 10%)
    'stop_loss_pct': 0.07,       # 7% stop loss (updated from 5%)
    'market_tickers': ['SPY', 'QQQ', 'IWM', '^VIX'],  # Market context tickers
}


def select_universe() -> List[str]:
    """
    Select US-listed stocks with:
    - Price between $1-$10
    - Average daily volume > 1M shares
    - At least 5 years of historical data
    
    NOTE: This function has survivorship bias - it only selects stocks that exist today.
    Stocks that were delisted, went bankrupt, or merged in the past are excluded.
    This inflates backtest performance. For production use, use historical constituent data.
    
    Returns:
        List of ticker symbols
    """
    print(f"Selecting universe of stocks (price: ${CONFIG['min_price']}-${CONFIG['max_price']}, volume: {CONFIG['min_volume']:,}+)...")
    
    # Focus on small/mid-cap tickers more likely to trade under $10
    tickers = [
        'SNDL', 'GME', 'AMC', 'BB', 'NOK', 'PLTR', 'RIVN', 'LCID', 'HOOD',
        'COIN', 'ROKU', 'Z', 'PLUG', 'FCEL', 'BLNK', 'QS', 'SPCE', 'HYLN',
        'CRSP', 'EDIT', 'NTLA', 'BEAM', 'PACB', 'NTRA', 'GH', 'TXG', 'RGEN',
        'DNA', 'BMEA', 'ARVN', 'ICLR', 'MRVI', 'INCY', 'ALXO', 'QGEN',
        'ETSY', 'SHOP', 'SQ', 'JD', 'BABA', 'PDD', 'NTES', 'TME',
        'WKHS', 'RIDE', 'CANO', 'GOEV', 'NKLA', 'EXAS', 'ARCT', 'IMGO',
        'SAGE', 'NLOK', 'AGTC',
        'UBER', 'LYFT', 'SNAP', 'PINS', 'DOCU', 'ZM', 'OKTA', 'DDOG',
        'TWLO', 'NET', 'MDB', 'ESTC', 'FSLY', 'TEAM', 'CRWD',
        'RUN', 'SPWR', 'CSIQ', 'JKS', 'BBBY',
    ]
    
    tickers = sorted(list(set(tickers)))  # Sort for deterministic behavior
    valid_tickers = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            avg_volume = info.get('averageVolume') or info.get('regularMarketVolume')
            
            if avg_volume and avg_volume > CONFIG['min_volume']:
                valid_tickers.append(ticker)
                print(f"  Added {ticker}: Vol: {avg_volume:,.0f}")
            
            time.sleep(0.1)
        except Exception as e:
            print(f"  Skipping {ticker}: {str(e)[:50]}")
            continue
    
    print(f"\nSelected {len(valid_tickers)} stocks meeting volume criteria")
    return valid_tickers[:CONFIG['target_universe_size']]


def download_data(tickers: List[str]) -> Dict[str, pd.DataFrame]:
    """
    Download historical OHLCV data for each ticker plus SPY and VIX for market context
    
    Args:
        tickers: List of stock ticker symbols
        
    Returns:
        Dictionary mapping ticker symbols to DataFrames
    """
    print(f"\nDownloading {CONFIG['history_years']} years of historical data...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=CONFIG['history_years'] * 365)
    
    data = {}
    skipped = []
    
    # Download stock data
    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if len(df) >= 252 * 2:
                data[ticker] = df
                print(f"  {ticker}: {len(df)} days downloaded")
            else:
                skipped.append((ticker, len(df)))
                print(f"  {ticker}: Insufficient data ({len(df)} days), skipping")
            
            time.sleep(0.1)
        except Exception as e:
            skipped.append((ticker, 0))
            print(f"  {ticker}: Error - {str(e)[:50]}")
    
    # Download market context tickers (SPY, QQQ, IWM, VIX)
    for market_ticker in CONFIG['market_tickers']:
        try:
            print(f"  Downloading {market_ticker} for market context...")
            market_df = yf.download(market_ticker, start=start_date, end=end_date, progress=False)
            if isinstance(market_df.columns, pd.MultiIndex):
                market_df.columns = market_df.columns.get_level_values(0)
            data[market_ticker] = market_df
            print(f"  {market_ticker}: {len(market_df)} days downloaded")
        except Exception as e:
            print(f"  {market_ticker} download failed: {str(e)[:50]}")
    
    print(f"\nSuccessfully downloaded data for {len(data)} tickers")
    if skipped:
        print(f"Skipped {len(skipped)} tickers: {[t[0] for t in skipped]}")
    
    return data


def calculate_indicators(df: pd.DataFrame, spy_df: Optional[pd.DataFrame] = None, 
                         qqq_df: Optional[pd.DataFrame] = None,
                         iwm_df: Optional[pd.DataFrame] = None,
                         vix_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Calculate all technical indicators for feature engineering
    
    Args:
        df: Stock OHLCV DataFrame
        spy_df: SPY DataFrame for market context (optional)
        vix_df: VIX DataFrame for volatility context (optional)
        
    Returns:
        DataFrame with all indicators added as columns
    """
    df = df.copy()
    
    # ===== Trend Features =====
    # EMAs
    df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # Distance from EMAs (%)
    df['dist_ema_20_pct'] = (df['Close'] - df['ema_20']) / df['ema_20']
    df['dist_ema_50_pct'] = (df['Close'] - df['ema_50']) / df['ema_50']
    df['dist_ema_200_pct'] = (df['Close'] - df['ema_200']) / df['ema_200']
    
    # EMA alignment (bullish if EMA20 > EMA50 > EMA200)
    df['ema_alignment'] = ((df['ema_20'] > df['ema_50']) & 
                          (df['ema_50'] > df['ema_200'])).astype(int)
    
    # Trend slope (linear regression of last 20 closes, normalized by log-price)
    def calculate_slope(series, window=20):
        slopes = np.full(len(series), np.nan)
        for i in range(window - 1, len(series)):
            y = np.log(series.iloc[i - window + 1:i + 1].values)  # Log-price for stability
            x = np.arange(window)
            slope = np.polyfit(x, y, 1)[0]
            slopes[i] = slope
        return slopes
    
    df['trend_slope_20'] = calculate_slope(df['Close'], 20)
    
    # ===== Momentum Features =====
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Stochastic RSI (handle divide-by-zero)
    rsi_min = df['rsi_14'].rolling(window=14).min()
    rsi_max = df['rsi_14'].rolling(window=14).max()
    rsi_range = rsi_max - rsi_min
    rsi_range = rsi_range.replace(0, np.nan)  # Handle divide-by-zero
    df['stoch_rsi_k'] = ((df['rsi_14'] - rsi_min) / rsi_range) * 100
    df['stoch_rsi_d'] = df['stoch_rsi_k'].rolling(window=3).mean()
    
    # Rate of Change (ROC)
    df['roc_14'] = df['Close'].pct_change(14) * 100
    
    # ===== Volume Features =====
    # Relative Volume (current / 20-day average, shifted to avoid leakage)
    df['vol_avg_20'] = df['Volume'].shift(1).rolling(window=20).mean()
    df['rel_volume'] = df['Volume'] / df['vol_avg_20']
    
    # Cap relative volume to handle holidays/halts/IPO noise
    df['rel_volume'] = df['rel_volume'].clip(upper=10.0)
    
    # On-Balance Volume (replace raw OBV with derived features)
    obv = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
    df['obv_ema'] = obv.ewm(span=20, adjust=False).mean()
    df['obv_slope'] = obv.diff(5)  # 5-day slope
    df['obv_roc'] = obv.pct_change(14) * 100  # 14-day rate of change
    df['obv_norm'] = obv / df['vol_avg_20']  # Normalized by volume average
    
    # Volume spike % (capped)
    df['vol_spike_pct'] = ((df['Volume'] - df['vol_avg_20']) / df['vol_avg_20']) * 100
    df['vol_spike_pct'] = df['vol_spike_pct'].clip(upper=500)  # Cap at 500%
    
    # ===== Volatility Features =====
    # ATR (14)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(window=14).mean()
    
    # ATR as % of price
    df['atr_pct'] = df['atr_14'] / df['Close']
    
    # Average candle range
    df['candle_range'] = (df['High'] - df['Low']) / df['Close']
    df['avg_candle_range_14'] = df['candle_range'].rolling(window=14).mean()
    
    # ===== Candlestick Features =====
    df['candle_color'] = np.where(df['Close'] > df['Open'], 1, 0)  # 1=green, 0=red
    df['body'] = abs(df['Close'] - df['Open'])
    df['upper_wick'] = df['High'] - np.maximum(df['Open'], df['Close'])
    df['lower_wick'] = np.minimum(df['Open'], df['Close']) - df['Low']
    df['range'] = df['High'] - df['Low']
    df['range'] = df['range'].replace(0, np.nan)
    
    # Candlestick patterns
    df['is_hammer'] = ((df['lower_wick'] >= 2 * df['body']) &
                      (df['upper_wick'] <= 0.5 * df['body']) &
                      (df['candle_color'] == 1)).astype(int)
    
    df['is_bullish_engulfing'] = ((df['candle_color'] == 1) & 
                                   (df['candle_color'].shift(1) == 0) & 
                                   (df['Open'] < df['Close'].shift(1)) & 
                                   (df['Close'] > df['Open'].shift(1))).astype(int)
    
    df['is_doji'] = (df['body'] / df['range'] < 0.1).astype(int)
    df['is_long_lower_wick'] = (df['lower_wick'] >= 2 * df['body']).astype(int)
    df['is_long_upper_wick'] = (df['upper_wick'] >= 2 * df['body']).astype(int)
    
    # Consecutive green candles
    df['consecutive_greens'] = (df['candle_color'].groupby(
        (df['candle_color'] != df['candle_color'].shift()).cumsum()
    ).cumsum() * df['candle_color'])
    
    # ===== Market Context Features =====
    if spy_df is not None:
        # Align SPY data with stock data
        spy_aligned = spy_df.reindex(df.index, method='ffill')
        
        # SPY EMAs
        spy_aligned['spy_ema_20'] = spy_aligned['Close'].ewm(span=20, adjust=False).mean()
        spy_aligned['spy_ema_50'] = spy_aligned['Close'].ewm(span=50, adjust=False).mean()
        spy_aligned['spy_ema_200'] = spy_aligned['Close'].ewm(span=200, adjust=False).mean()
        
        # SPY trend alignment
        df['spy_ema_alignment'] = ((spy_aligned['spy_ema_20'] > spy_aligned['spy_ema_50']) &
                                   (spy_aligned['spy_ema_50'] > spy_aligned['spy_ema_200'])).astype(int)
        
        # SPY 20-day return
        df['spy_20d_return'] = spy_aligned['Close'].pct_change(20) * 100
        
        # Relative performance vs SPY
        stock_20d_return = df['Close'].pct_change(20) * 100
        df['rel_performance_spy'] = stock_20d_return - df['spy_20d_return']
    
    # Add QQQ market context if available
    if qqq_df is not None:
        qqq_aligned = qqq_df.reindex(df.index, method='ffill')
        df['qqq_close'] = qqq_aligned['Close']
        df['qqq_20d_return'] = qqq_aligned['Close'].pct_change(20) * 100
        df['rel_performance_qqq'] = stock_20d_return - df['qqq_20d_return']
    
    # Add IWM market context if available
    if iwm_df is not None:
        iwm_aligned = iwm_df.reindex(df.index, method='ffill')
        df['iwm_close'] = iwm_aligned['Close']
        df['iwm_20d_return'] = iwm_aligned['Close'].pct_change(20) * 100
        df['rel_performance_iwm'] = stock_20d_return - df['iwm_20d_return']
    
    if vix_df is not None:
        # Align VIX data with stock data
        vix_aligned = vix_df.reindex(df.index, method='ffill')
        df['vix_level'] = vix_aligned['Close']
        
        # VIX percentile (relative to 1-year history)
        df['vix_percentile'] = vix_aligned['Close'].rolling(window=252).apply(
            lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() != x.min() else 0.5
        )
    
    return df


def get_thresholds(price: float, atr: Optional[float] = None) -> Tuple[float, float]:
    """
    Get appropriate thresholds based on price level and ATR
    Uses ATR-based thresholds when available for volatility-adjusted zones
    
    Args:
        price: Current price level
        atr: ATR value for volatility-adjusted thresholds (optional)
        
    Returns:
        Tuple of (touch_threshold, break_threshold)
    """
    # Use ATR-based thresholds when available (more robust across volatility regimes)
    if atr is not None and atr > 0:
        # ATR-based: 0.5 ATR for touch, 1.0 ATR for break
        touch_threshold = 0.5 * atr / price
        break_threshold = 1.0 * atr / price
    elif price < 2:
        # For very cheap stocks, use absolute minimum threshold
        touch_threshold = max(CONFIG['zone_touch_threshold'], CONFIG['min_absolute_threshold'] / price)
        break_threshold = max(CONFIG['zone_break_threshold'], CONFIG['min_absolute_threshold'] / price)
    else:
        # Default fixed percentage thresholds
        touch_threshold = CONFIG['zone_touch_threshold']
        break_threshold = CONFIG['zone_break_threshold']
    
    return touch_threshold, break_threshold


def detect_demand_zones(df: pd.DataFrame, end_date: Optional[pd.Timestamp] = None) -> List[Dict]:
    """
    Identify demand zones in the trailing 90 days up to end_date
    Uses 5-bar pivot (fractal) for more robust swing low detection
    
    Args:
        df: Full historical dataframe with OHLCV data
        end_date: Calculate zones using data up to this date (default: most recent)
        
    Returns:
        List of zone dictionaries with metadata
    """
    if end_date is None:
        trailing_df = df.tail(CONFIG['trailing_days']).copy()
    else:
        df_before = df[df.index <= end_date]
        trailing_df = df_before.tail(CONFIG['trailing_days']).copy()
    
    if len(trailing_df) < CONFIG['min_zone_touches'] + 4:  # Need at least 5 bars for pivot
        return []
    
    zones = []
    lows = trailing_df['Low'].values
    
    # 5-bar pivot: low is lower than 2 bars on each side
    for i in range(2, len(lows) - 2):
        if (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and 
            lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
            zone_price = lows[i]
            
            # Get ATR at this point for volatility-adjusted thresholds
            atr_at_pivot = trailing_df['atr_14'].iloc[i] if 'atr_14' in trailing_df.columns else None
            touch_threshold, break_threshold = get_thresholds(zone_price, atr_at_pivot)
            
            touches = 0
            touch_dates = []
            
            for j, low in enumerate(lows):
                if abs(low - zone_price) / zone_price <= touch_threshold:
                    touches += 1
                    touch_dates.append(trailing_df.index[j])
            
            # Check if zone was broken (only after zone formed, using close instead of intraday low)
            broken = False
            zone_formed_idx = i  # Zone forms at this local minimum
            closes = trailing_df['Close'].values
            for j in range(zone_formed_idx, len(closes)):
                if closes[j] < zone_price * (1 - break_threshold):
                    broken = True
                    break
            
            if touches >= CONFIG['min_zone_touches'] and not broken:
                zone_age = 0
                if touch_dates:
                    zone_age = (trailing_df.index[i] - touch_dates[0]).days
                
                zone = {
                    'price': zone_price,
                    'touches': touches,
                    'touch_dates': touch_dates,
                    'upper_bound': zone_price * (1 + touch_threshold),
                    'lower_bound': zone_price * (1 - touch_threshold),
                    'first_touch_date': touch_dates[0] if touch_dates else None,
                    'age_days': zone_age,
                    'pivot_idx': i
                }
                zones.append(zone)
    
    # Sort zones by quality (more touches, fresher, lower price)
    zones.sort(key=lambda z: (-z['touches'], z['age_days'], z['price']))
    
    # Merge overlapping zones (keep higher quality)
    merged_zones = []
    for zone in zones:
        is_duplicate = False
        for existing in merged_zones:
            # Check if zones overlap significantly
            if abs(zone['price'] - existing['price']) / existing['price'] < touch_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            merged_zones.append(zone)
    
    return merged_zones


def detect_signals(ticker: str, df: pd.DataFrame) -> List[Dict]:
    """
    Detect buy signals when price enters demand zone (no confirmation required)
    Entry occurs at close of signal day - no future candle leakage
    Prevents multiple entries in same zone - only first touch counts
    
    Args:
        ticker: Stock symbol
        df: DataFrame with OHLCV and indicators
        
    Returns:
        List of signal dictionaries with basic info
    """
    signals = []
    start_idx = CONFIG['trailing_days']
    in_zone = False
    current_zone = None
    last_signal_date = None
    cooldown_days = 10  # Prevent overlapping signals
    
    for i in range(start_idx, len(df) - CONFIG['trade_horizon_days']):
        current_date = df.index[i]
        close_price = df.iloc[i]['Close']
        low = df.iloc[i]['Low']
        high = df.iloc[i]['High']
        
        # Apply price filter at signal time
        if close_price >= CONFIG['max_price']:
            continue
        
        # Check cooldown (prevent overlapping signals)
        if last_signal_date is not None:
            days_since_signal = (current_date - last_signal_date).days
            if days_since_signal < cooldown_days:
                continue
        
        # Calculate demand zones using rolling window up to current date
        zones = detect_demand_zones(df, end_date=current_date)
        
        if not zones:
            in_zone = False
            current_zone = None
            continue
        
        # Check if we're in any zone
        in_any_zone = False
        for zone in zones:
            if zone['lower_bound'] <= low <= zone['upper_bound']:
                in_any_zone = True
                if not in_zone:
                    # First touch of this zone - generate signal
                    signal = {
                        'ticker': ticker,
                        'date': current_date,
                        'price': df.iloc[i]['Close'],  # Entry at close of signal day
                        'zone_price': zone['price'],
                        'zone_touches': zone['touches'] - 1,
                        'zone': zone,
                        'row_idx': i
                    }
                    signals.append(signal)
                    in_zone = True
                    current_zone = zone
                    last_signal_date = current_date
                break
        
        # Check if we exited the zone (price above upper bound)
        if in_zone and current_zone:
            if high > current_zone['upper_bound']:
                in_zone = False
                current_zone = None
    
    return signals


def engineer_features(df: pd.DataFrame, signals: List[Dict]) -> pd.DataFrame:
    """
    Extract signal-specific features for each detected signal
    
    Args:
        df: DataFrame with all indicators calculated
        signals: List of signal dictionaries from detect_signals
        
    Returns:
        DataFrame with one row per signal and all engineered features
    """
    feature_rows = []
    
    for signal in signals:
        row_idx = signal['row_idx']
        row = df.iloc[row_idx]
        zone = signal['zone']
        signal_date = signal['date']
        
        # ===== Basic Signal Info =====
        features = {
            'ticker': signal['ticker'],
            'date': signal['date'],
            'entry_price': signal['price'],
        }
        
        # ===== Trend Features =====
        features['ema_20'] = row['ema_20']
        features['ema_50'] = row['ema_50']
        features['ema_200'] = row['ema_200']
        features['dist_ema_20_pct'] = row['dist_ema_20_pct']
        features['dist_ema_50_pct'] = row['dist_ema_50_pct']
        features['dist_ema_200_pct'] = row['dist_ema_200_pct']
        features['ema_alignment'] = row['ema_alignment']
        features['trend_slope_20'] = row['trend_slope_20']
        
        # Binary trend features (above/below EMAs)
        features['above_ema20'] = 1 if row['Close'] > row['ema_20'] else 0
        features['above_ema50'] = 1 if row['Close'] > row['ema_50'] else 0
        features['above_ema200'] = 1 if row['Close'] > row['ema_200'] else 0
        features['ema20_above_ema50'] = 1 if row['ema_20'] > row['ema_50'] else 0
        features['ema50_above_ema200'] = 1 if row['ema_50'] > row['ema_200'] else 0
        
        # ===== Momentum Features =====
        features['rsi_14'] = row['rsi_14']
        features['macd'] = row['macd']
        features['macd_signal'] = row['macd_signal']
        features['macd_hist'] = row['macd_hist']
        features['stoch_rsi_k'] = row['stoch_rsi_k']
        features['stoch_rsi_d'] = row['stoch_rsi_d']
        features['roc_14'] = row['roc_14']
        
        # ===== Volume Features =====
        features['rel_volume'] = row['rel_volume']
        features['obv_ema'] = row['obv_ema']
        features['obv_slope'] = row['obv_slope']
        features['obv_roc'] = row['obv_roc']
        features['obv_norm'] = row['obv_norm']
        features['vol_spike_pct'] = row['vol_spike_pct']
        
        # ===== Volatility Features =====
        features['atr_14'] = row['atr_14']
        features['atr_pct'] = row['atr_pct']
        features['avg_candle_range_14'] = row['avg_candle_range_14']
        
        # ATR percentile (relative to 60-day history)
        if 'atr_14' in df.columns:
            atr_history = df['atr_14'].iloc[max(0, row_idx-60):row_idx]
            if len(atr_history) > 0:
                atr_percentile = (atr_history.iloc[-1] - atr_history.min()) / (atr_history.max() - atr_history.min()) if atr_history.max() != atr_history.min() else 0.5
            else:
                atr_percentile = 0.5
        else:
            atr_percentile = 0.5
        features['atr_percentile'] = atr_percentile
        
        # ===== Demand Zone Features =====
        features['zone_price'] = zone['price']
        features['zone_distance_pct'] = (signal['price'] - zone['price']) / zone['price']
        features['zone_width_pct'] = (zone['upper_bound'] - zone['lower_bound']) / zone['lower_bound']
        features['zone_touches'] = signal['zone_touches']
        
        # Zone age (days since first touch)
        if zone['first_touch_date'] is not None:
            zone_age = (signal['date'] - zone['first_touch_date']).days
        else:
            zone_age = 0
        features['zone_age_days'] = zone_age
        
        # Fresh zone (less than 30 days old)
        features['is_fresh_zone'] = 1 if zone_age < 30 else 0
        
        # Zone strength score (composite of touches, freshness, and quality)
        zone_strength = zone['touches'] * (1 - min(zone_age / 180, 1))  # Decay over 180 days
        features['zone_strength'] = zone_strength
        
        # Store raw zone features (let ML model determine importance)
        # Removed arbitrary strength score - let XGBoost discover feature importance
        
        # Calculate zone quality metrics using main df
        # Bounce strength: how much price moved away after last touch
        if len(zone['touch_dates']) > 1:
            last_touch_date = zone['touch_dates'][-1]
            if last_touch_date in df.index:
                last_touch_idx = df.index.get_loc(last_touch_date)
                if last_touch_idx < len(df) - 1:
                    next_high = df['High'].iloc[last_touch_idx + 1]
                    bounce_strength = (next_high - zone['price']) / zone['price'] if zone['price'] > 0 else 0
                else:
                    bounce_strength = 0
            else:
                bounce_strength = 0
        else:
            bounce_strength = 0
        
        # Rejection wick: average lower wick at zone touches
        touch_wicks = []
        for touch_date in zone['touch_dates']:
            if touch_date in df.index:
                touch_idx = df.index.get_loc(touch_date)
                lower_wick = df['lower_wick'].iloc[touch_idx]
                touch_wicks.append(lower_wick)
        avg_rejection_wick = np.mean(touch_wicks) if touch_wicks else 0
        
        # Departure velocity: how fast price left the zone after last touch
        if len(zone['touch_dates']) > 0:
            last_touch_date = zone['touch_dates'][-1]
            if last_touch_date in df.index:
                last_touch_idx = df.index.get_loc(last_touch_date)
                if last_touch_idx < len(df) - 5:
                    price_5d_later = df['Close'].iloc[last_touch_idx + 5]
                    departure_velocity = (price_5d_later - zone['price']) / zone['price'] if zone['price'] > 0 else 0
                else:
                    departure_velocity = 0
            else:
                departure_velocity = 0
        else:
            departure_velocity = 0
        
        features['zone_bounce_strength'] = bounce_strength
        features['zone_avg_rejection_wick'] = avg_rejection_wick
        features['zone_departure_velocity'] = departure_velocity
        
        # ===== Candlestick Features =====
        features['is_hammer'] = row['is_hammer']
        features['is_bullish_engulfing'] = row['is_bullish_engulfing']
        features['is_doji'] = row['is_doji']
        features['is_long_lower_wick'] = row['is_long_lower_wick']
        features['is_long_upper_wick'] = row['is_long_upper_wick']
        # Removed consecutive_greens (predetermined by signal logic, adds no information)
        features['body_size_pct'] = row['body'] / signal['price']
        
        # ===== Market Context Features =====
        if 'spy_ema_alignment' in row:
            features['spy_ema_alignment'] = row['spy_ema_alignment']
            features['spy_20d_return'] = row['spy_20d_return']
            features['rel_performance_spy'] = row['rel_performance_spy']
            
            # SPY trend binary features
            if 'spy_close' in df.columns and 'spy_ema200' in df.columns:
                spy_close = df['spy_close'].iloc[row_idx]
                spy_ema200 = df['spy_ema200'].iloc[row_idx]
                features['spy_above_ema200'] = 1 if spy_close > spy_ema200 else 0
        
        if 'vix_level' in row:
            features['vix_level'] = row['vix_level']
            features['vix_percentile'] = row['vix_percentile']
            
            # VIX regime classification
            vix = row['vix_level']
            features['vix_regime_low'] = 1 if vix < 15 else 0  # Low volatility
            features['vix_regime_normal'] = 1 if 15 <= vix < 25 else 0  # Normal volatility
            features['vix_regime_high'] = 1 if vix >= 25 else 0  # High volatility
        
        feature_rows.append(features)
    
    return pd.DataFrame(feature_rows)


def label_trade_outcomes(df: pd.DataFrame, signals: List[Dict]) -> pd.DataFrame:
    """
    Simulate trade outcomes for each signal and calculate performance metrics
    
    Args:
        df: DataFrame with OHLCV data
        signals: List of signal dictionaries with row_idx
        
    Returns:
        DataFrame with trade outcome labels added
    """
    outcomes = []
    
    for signal in signals:
        row_idx = signal['row_idx']
        entry_price = signal['price']
        
        # Get future data for trade simulation
        future_data = df.iloc[row_idx + 1:row_idx + CONFIG['trade_horizon_days'] + 1]
        
        if len(future_data) == 0:
            continue
        
        # Calculate targets
        target_price = entry_price * (1 + CONFIG['target_gain_pct'])
        stop_loss_price = entry_price * (1 - CONFIG['stop_loss_pct'])
        
        # Track MFE and MAE
        mfe = 0  # Maximum favorable excursion
        mae = 0  # Maximum adverse excursion
        max_gain_pct = 0
        max_drawdown_pct = 0
        
        days_to_target = None
        days_to_stop = None
        exit_reason = 'timeout'
        final_price = future_data.iloc[-1]['Close']
        
        for day_idx, (_, row) in enumerate(future_data.iterrows(), 1):
            high = row['High']
            low = row['Low']
            
            # Update MFE (best price achieved)
            if high > entry_price:
                current_gain = (high - entry_price) / entry_price
                if current_gain > mfe:
                    mfe = current_gain
                if current_gain > max_gain_pct:
                    max_gain_pct = current_gain
            
            # Update MAE (worst price experienced)
            if low < entry_price:
                current_loss = (entry_price - low) / entry_price
                if current_loss > mae:
                    mae = current_loss
                if current_loss > max_drawdown_pct:
                    max_drawdown_pct = current_loss
            
            # Check for ambiguous bar (both stop and target hit)
            hit_stop = low <= stop_loss_price
            hit_target = high >= target_price
            
            if hit_stop and hit_target:
                # Ambiguous bar - skip this trade (cannot determine order)
                exit_reason = 'ambiguous'
                final_price = entry_price  # No profit/loss
                break
            
            # Check exit conditions (stop checked before target for conservative estimate)
            if hit_stop and days_to_stop is None:
                days_to_stop = day_idx
                exit_reason = 'stop'
                final_price = stop_loss_price
                break
            
            if hit_target and days_to_target is None:
                days_to_target = day_idx
                exit_reason = 'target'
                final_price = target_price
                break
        
        # Calculate final outcome
        final_return_pct = (final_price - entry_price) / entry_price
        
        outcome = {
            'mfe_pct': mfe,
            'mae_pct': mae,
            'max_gain_pct': max_gain_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'days_to_max_gain': days_to_target if days_to_target else CONFIG['trade_horizon_days'],
            'days_to_stop': days_to_stop,
            'days_to_target': days_to_target,
            'exit_reason': exit_reason,
            'final_return_pct': final_return_pct,
            'hit_target': 1 if exit_reason == 'target' else 0,
            'hit_stop': 1 if exit_reason == 'stop' else 0,
            '20_day_return': final_return_pct,
            'max_return': max_gain_pct,
            'max_drawdown': max_drawdown_pct
        }
        
        outcomes.append(outcome)
    
    return pd.DataFrame(outcomes)


def export_dataset(features_df: pd.DataFrame, outcomes_df: pd.DataFrame) -> pd.DataFrame:
    """
    Combine features and outcomes into final ML dataset
    Filter out rows with NaN values from early indicator warmup periods
    Use merge on ticker/date for robustness
    
    Args:
        features_df: DataFrame with engineered features
        outcomes_df: DataFrame with trade outcome labels
        
    Returns:
        Combined DataFrame ready for ML training
    """
    # Add temporary index for merging
    features_df = features_df.reset_index(drop=True)
    outcomes_df = outcomes_df.reset_index(drop=True)
    
    # Combine features and outcomes using concat (same row order guaranteed by pipeline)
    dataset = pd.concat([features_df, outcomes_df], axis=1)
    
    # Sort by date
    dataset['date'] = pd.to_datetime(dataset['date'])
    dataset = dataset.sort_values('date')
    
    # Remove rows with NaN values (from indicator warmup periods)
    initial_rows = len(dataset)
    dataset = dataset.dropna()
    removed_rows = initial_rows - len(dataset)
    
    if removed_rows > 0:
        print(f"  Removed {removed_rows} rows with NaN values (indicator warmup)")
    
    # Remove duplicate signals
    initial_rows = len(dataset)
    dataset = dataset.drop_duplicates(subset=['ticker', 'date'])
    removed_rows = initial_rows - len(dataset)
    
    if removed_rows > 0:
        print(f"  Removed {removed_rows} duplicate signals")
    
    # Remove duplicate metric columns
    duplicate_cols = ['max_gain_pct', 'max_drawdown_pct']  # These duplicate max_return and max_drawdown
    cols_to_drop = [col for col in duplicate_cols if col in dataset.columns]
    if cols_to_drop:
        dataset = dataset.drop(columns=cols_to_drop)
        print(f"  Removed duplicate columns: {cols_to_drop}")
    
    # Dataset validation
    print("\n  Dataset validation:")
    print(f"    No NaN values: {not dataset.isna().any().any()}")
    print(f"    No infinite values: {not np.isinf(dataset.select_dtypes(include=[np.number])).any().any()}")
    print(f"    Unique (ticker, date) pairs: {len(dataset.groupby(['ticker', 'date']))}")
    print(f"    Total rows: {len(dataset)}")
    
    return dataset


def main():
    """
    Main execution flow for ML dataset generation
    """
    print("=" * 60)
    print("Stock Demand Zone ML Dataset Generator")
    print("=" * 60)
    print(f"Configuration: {CONFIG}")
    print("=" * 60)
    
    # Step 1: Universe Selection
    tickers = select_universe()
    
    if not tickers:
        print("No stocks found matching criteria. Exiting.")
        return
    
    # Save ticker list
    ticker_df = pd.DataFrame({'Ticker': tickers})
    ticker_df.to_csv('selected_tickers.csv', index=False)
    print(f"\nTicker list saved to selected_tickers.csv")
    
    # Step 2: Data Download (stocks + SPY + VIX)
    data = download_data(tickers)
    
    if not data:
        print("No historical data downloaded. Exiting.")
        return
    
    # Extract SPY and VIX for market context
    spy_df = data.pop('SPY', None)
    vix_df = data.pop('VIX', None)
    
    # Step 3: Calculate indicators for all stocks
    print("\nCalculating technical indicators...")
    indicators_data = {}
    for ticker, df in data.items():
        if ticker in ['SPY', 'VIX']:
            continue
        indicators_data[ticker] = calculate_indicators(df, spy_df, vix_df)
        print(f"  {ticker}: Indicators calculated")
    
    # Step 4: Detect signals
    print("\nDetecting demand zone signals...")
    all_signals = []
    for ticker, df in indicators_data.items():
        signals = detect_signals(ticker, df)
        if signals:
            all_signals.extend(signals)
            print(f"  {ticker}: {len(signals)} signals detected")
        else:
            print(f"  {ticker}: No signals detected")
    
    if not all_signals:
        print("\nNo signals detected. Exiting.")
        return
    
    # Step 5: Engineer features
    print("\nEngineering features...")
    all_features = []
    for ticker, df in indicators_data.items():
        ticker_signals = [s for s in all_signals if s['ticker'] == ticker]
        if ticker_signals:
            features_df = engineer_features(df, ticker_signals)
            all_features.append(features_df)
    
    features_df = pd.concat(all_features, ignore_index=True)
    print(f"  Total features: {len(features_df)} rows, {len(features_df.columns)} columns")
    
    # Step 6: Label trade outcomes
    print("\nLabeling trade outcomes...")
    all_outcomes = []
    for ticker, df in data.items():
        if ticker in ['SPY', 'VIX']:
            continue
        ticker_signals = [s for s in all_signals if s['ticker'] == ticker]
        if ticker_signals:
            outcomes_df = label_trade_outcomes(df, ticker_signals)
            all_outcomes.append(outcomes_df)
    
    outcomes_df = pd.concat(all_outcomes, ignore_index=True)
    print(f"  Total outcomes: {len(outcomes_df)} rows")
    
    # Step 7: Export dataset
    print("\nExporting ML dataset...")
    dataset = export_dataset(features_df, outcomes_df)
    
    # Save to CSV
    dataset.to_csv('demand_zone_ml_dataset.csv', index=False)
    print(f"  Dataset saved to demand_zone_ml_dataset.csv")
    print(f"  Shape: {dataset.shape}")
    
    # Print summary statistics
    print(f"\n{'=' * 60}")
    print("Dataset Summary")
    print(f"{'=' * 60}")
    print(f"Total signals: {len(dataset)}")
    print(f"Unique tickers: {dataset['ticker'].nunique()}")
    print(f"Date range: {dataset['date'].min()} to {dataset['date'].max()}")
    print(f"\nTarget hit rate: {dataset['hit_target'].mean():.2%}")
    print(f"Stop hit rate: {dataset['hit_stop'].mean():.2%}")
    print(f"Average return: {dataset['final_return_pct'].mean():.2%}")
    print(f"\nExit reasons:")
    print(dataset['exit_reason'].value_counts())
    print(f"\nSignals per ticker:")
    print(dataset.groupby('ticker').size().sort_values(ascending=False))
    
    # Feature statistics
    print(f"\n{'=' * 60}")
    print("Feature Statistics (Sample)")
    print(f"{'=' * 60}")
    print(dataset[['entry_price', 'zone_distance_pct', 'rsi_14', 'rel_volume', 
                   'atr_pct', 'max_gain_pct', 'final_return_pct']].describe())
    
    print(f"\n{'=' * 60}")
    print("ML Dataset Generation Complete")
    print(f"{'=' * 60}")
    print(f"Dataset saved to: demand_zone_ml_dataset.csv")
    print(f"Ready for ML model training (Random Forest, XGBoost, LightGBM)")


if __name__ == "__main__":
    main()
