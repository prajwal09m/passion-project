"""
Automated ML Dataset Generator for Demand Zone Trading
Scans stock CSV files, detects demand zones, generates features, and simulates trades
"""

import pandas as pd
import numpy as np
import os
import glob
import re
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Configuration
CONFIG = {
    'data_folder': './data',  # Folder containing stock CSV files
    'output_file': 'demand_zone_ml_dataset.csv',
    # Use broad-market history for training.  The trainer separately reports
    # the sub-$10 test subset rather than throwing away higher-priced examples.
    'min_price': None,
    'max_price': None,
    'min_volume': None,
    'stop_loss_pct': 0.05,  # 5% stop loss
    'target_gain_pct': 0.15,  # 15% profit target
    'holding_period_days': 20,  # Maximum holding period
    'zone_detection_window': 90,  # Days to look back for zone detection
    'min_zone_touches': 2,  # Minimum touches to qualify as zone
    'zone_touch_threshold': 0.03,  # 3% tolerance for zone touches
    'max_retests_per_zone': 3,  # first/second/third test; bounds dataset growth
    'market_tickers': [
        'SPY', 'QQQ', 'IWM', 'VIX', 'XLK', 'XLF', 'XLE', 'XLV', 'XLY',
        'XLP', 'XLI', 'XLB', 'XLU', 'XLRE', 'XLC'
    ],
    'sector_map_file': './data/ticker_sectors.csv',
}


class DemandZoneDatasetGenerator:
    """
    Automated dataset generator for demand zone ML trading
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize generator with configuration
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or CONFIG
        self.all_signals = []
        self.total_zones_found = 0
        
    def load_stock_csvs(self) -> Dict[str, pd.DataFrame]:
        """
        Load all stock CSV files from data folder
        
        Returns:
            Dictionary of ticker -> DataFrame
        """
        print("=" * 60)
        print("Loading Stock Data")
        print("=" * 60)
        
        # Find all CSV files in data folder
        csv_pattern = os.path.join(self.config['data_folder'], '*_data.csv')
        csv_files = glob.glob(csv_pattern)
        
        if not csv_files:
            print(f"No CSV files found in {self.config['data_folder']}")
            return {}
        
        print(f"Found {len(csv_files)} CSV files")
        
        stock_data = {}
        for csv_file in csv_files:
            # Extract ticker from filename
            filename = os.path.basename(csv_file)
            ticker_match = re.match(r'(.+)_data\.csv', filename)
            
            if not ticker_match:
                print(f"  Skipping {filename}: invalid filename format")
                continue
            
            ticker = ticker_match.group(1)
            
            try:
                df = pd.read_csv(csv_file)
                
                # Validate required columns
                required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
                if not all(col in df.columns for col in required_cols):
                    print(f"  Skipping {ticker}: missing required columns")
                    continue
                
                # Clean and prepare data
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.sort_values('Date')
                df = df.dropna()
                
                if self.config['min_price'] is not None:
                    df = df[df['Close'] >= self.config['min_price']]
                if self.config['max_price'] is not None:
                    df = df[df['Close'] <= self.config['max_price']]
                if self.config['min_volume'] is not None:
                    df = df[df['Volume'] >= self.config['min_volume']]

                # All zone and signal timestamps must use actual trading dates.
                # The previous integer index made chronological validation invalid.
                df = df.set_index('Date', drop=False)
                
                if len(df) < 252:  # Need at least 1 year of data
                    print(f"  Skipping {ticker}: insufficient data ({len(df)} days)")
                    continue
                
                if ticker not in self.config['market_tickers']:
                    stock_data[ticker] = df
                print(f"  Loaded {ticker}: {len(df)} days")
                
            except Exception as e:
                print(f"  Error loading {ticker}: {str(e)[:50]}")
        
        print(f"\nSuccessfully loaded {len(stock_data)} stocks")
        return stock_data

    def load_market_context(self) -> Dict[str, pd.DataFrame]:
        """Load locally cached benchmark OHLCV files and align them by date."""
        context = {}
        for ticker in self.config['market_tickers']:
            path = os.path.join(self.config['data_folder'], f'{ticker}_data.csv')
            if not os.path.exists(path):
                continue
            df = pd.read_csv(path)
            if not {'Date', 'Close'}.issubset(df.columns):
                continue
            df['Date'] = pd.to_datetime(df['Date'])
            context[ticker] = df.sort_values('Date').set_index('Date')
        return context

    def load_sector_map(self) -> Dict[str, str]:
        path = self.config['sector_map_file']
        if not os.path.exists(path):
            return {}
        mapping = pd.read_csv(path)
        required = {'ticker', 'sector_etf'}
        if not required.issubset(mapping.columns):
            return {}
        return dict(zip(mapping['ticker'].str.upper(), mapping['sector_etf'].str.upper()))
    
    def calculate_indicators(self, df: pd.DataFrame, market_context: Dict[str, pd.DataFrame] = None,
                             sector_etf: str = None) -> pd.DataFrame:
        """
        Calculate technical indicators for feature engineering
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with indicators added
        """
        df = df.copy()
        
        # Price features
        df['daily_return'] = df['Close'].pct_change()
        df['5d_return'] = df['Close'].pct_change(5)
        df['20d_return'] = df['Close'].pct_change(20)
        
        # EMAs
        df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # EMA distances
        df['dist_ema_20_pct'] = (df['Close'] - df['ema_20']) / df['ema_20']
        df['dist_ema_50_pct'] = (df['Close'] - df['ema_50']) / df['ema_50']
        df['dist_ema_200_pct'] = (df['Close'] - df['ema_200']) / df['ema_200']
        
        # Trend alignment
        df['ema_alignment'] = ((df['ema_20'] > df['ema_50']) & 
                              (df['ema_50'] > df['ema_200'])).astype(int)
        
        # Trend slope
        df['trend_slope_20'] = df['ema_20'].diff(5) / df['ema_20'].shift(5)
        df['ema_20_slope_20'] = df['ema_20'].pct_change(20)
        df['ema_50_slope_20'] = df['ema_50'].pct_change(20)
        df['ema_200_slope_20'] = df['ema_200'].pct_change(20)
        df['price_vs_50ma_pct'] = (df['Close'] - df['ema_50']) / df['ema_50']
        df['price_vs_200ma_pct'] = (df['Close'] - df['ema_200']) / df['ema_200']
        df['ma_50_slope_20'] = df['ema_50'].pct_change(20)
        df['distance_from_52w_high_pct'] = (df['Close'] / df['High'].rolling(252).max()) - 1
        
        # Momentum - RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # Momentum - MACD
        df['ema_12'] = df['Close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['Close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Momentum - ROC
        df['roc_14'] = df['Close'].pct_change(14)
        
        # ATR (Average True Range)
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()
        df['atr_pct'] = df['atr_14'] / df['Close']
        up_move = df['High'].diff()
        down_move = -df['Low'].diff()
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(14).sum() / df['atr_14']
        minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(14).sum() / df['atr_14']
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        df['adx_14'] = dx.rolling(14).mean()
        
        # Volume features
        df['avg_volume_20'] = df['Volume'].rolling(window=20).mean()
        df['rel_volume'] = df['Volume'] / df['avg_volume_20']
        df['vol_spike_pct'] = (df['Volume'] - df['avg_volume_20']) / df['avg_volume_20']
        df['volume_ratio'] = df['rel_volume']
        df['volume_trend_20'] = df['avg_volume_20'].pct_change(20)
        df['avg_dollar_volume_20'] = (df['Close'] * df['Volume']).rolling(20).mean()
        df['volume_consistency_20'] = df['Volume'].rolling(20).std() / df['avg_volume_20']
        df['daily_volatility_20'] = df['daily_return'].rolling(20).std()
        gap_pct = (df['Open'] - df['Close'].shift()).abs() / df['Close'].shift()
        df['gap_frequency_20'] = (gap_pct > 0.03).rolling(20).mean()

        # Volume-flow features. All windows end on the signal candle.
        signed_volume = np.sign(df['Close'].diff()).fillna(0) * df['Volume']
        obv = signed_volume.cumsum()
        df['obv_slope_20'] = obv.pct_change(20)
        money_flow_multiplier = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']).replace(0, np.nan)
        df['chaikin_money_flow_20'] = (money_flow_multiplier * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum()
        rolling_vwap = (df['Close'] * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum()
        df['distance_vwap_20_pct'] = (df['Close'] - rolling_vwap) / rolling_vwap
        df['dollar_volume_percentile_60'] = df['avg_dollar_volume_20'].rolling(60).rank(pct=True)
        
        # Phase 3: Institutional Activity Features
        # Volume patterns
        df['volume_percentile_60'] = df['Volume'].rolling(60).rank(pct=True)
        df['volume_acceleration'] = df['rel_volume'].diff(5)
        high_volume_up_days = ((df['Close'] > df['Open']) & (df['Volume'] > df['avg_volume_20'])).rolling(20).sum()
        df['high_volume_up_days'] = high_volume_up_days
        low_volume_pullback = ((df['Close'] < df['Open']) & (df['Volume'] < df['avg_volume_20'])).rolling(20).sum()
        df['low_volume_pullback'] = low_volume_pullback
        
        # Price patterns
        df['close_near_high_pct'] = (df['Close'] - df['Low']) / (df['High'] - df['Low']).replace(0, 0.5)
        df['gap_frequency_20'] = (gap_pct > 0.02).rolling(20).mean()
        
        # ATR expansion/contraction
        df['atr_expansion_20'] = df['atr_14'].rolling(20).mean() / df['atr_14'].rolling(60).mean()
        df['atr_contraction_20'] = df['atr_14'].rolling(20).std() / df['atr_14'].rolling(20).mean()
        
        # Anchored VWAP (from zone pivot - simplified as 20-day VWAP)
        df['anchored_vwap_distance'] = (df['Close'] - rolling_vwap) / rolling_vwap

        # Completed prior-week data only: shift prevents access to Friday's
        # close while generating a signal earlier in that same week.
        weekly_close = df['Close'].resample('W-FRI').last().shift(1)
        weekly_lows = df['Low'].resample('W-FRI').min()
        weekly_ema_20 = weekly_close.ewm(span=20, adjust=False).mean()
        weekly_delta = weekly_close.diff()
        weekly_gain = weekly_delta.clip(lower=0).rolling(14).mean()
        weekly_loss = (-weekly_delta.clip(upper=0)).rolling(14).mean()
        weekly_rsi = 100 - (100 / (1 + weekly_gain / weekly_loss))
        weekly_macd = weekly_close.ewm(span=12, adjust=False).mean() - weekly_close.ewm(span=26, adjust=False).mean()
        weekly_features = pd.DataFrame({
            'weekly_price_vs_ema20': (weekly_close - weekly_ema_20) / weekly_ema_20,
            'weekly_ema_slope_10': weekly_ema_20.pct_change(10),
            'weekly_rsi_14': weekly_rsi,
            'weekly_macd': weekly_macd,
            'weekly_above_ema50': (weekly_close > weekly_close.ewm(span=50, adjust=False).mean()).astype(int),
            'weekly_higher_high': (df['High'].resample('W-FRI').max().shift(1) > df['High'].resample('W-FRI').max().shift(2)).astype(int),
            'weekly_higher_low': (weekly_lows.shift(1) > weekly_lows.shift(2)).astype(int),
            # Phase 4: Multi-Timeframe Confirmation
            'weekly_above_50ema': (weekly_close > weekly_close.ewm(span=50, adjust=False).mean()).astype(int),
            'weekly_higher_highs': (weekly_close > weekly_close.shift(1)).rolling(4).sum(),
            'weekly_higher_lows': (weekly_close.rolling(2).min() > weekly_close.rolling(2).min().shift(2)).rolling(4).sum(),
            'weekly_demand_freshness': (weekly_close.diff().rolling(4).apply(lambda x: (x > 0).sum())),
        })
        df = df.join(weekly_features.reindex(df.index, method='ffill'))

        weekly_zone = pd.Series(index=weekly_lows.index, dtype=float)
        active_zone = np.nan
        for i in range(4, len(weekly_lows)):
            pivot = weekly_lows.iloc[i - 2]
            if pivot <= weekly_lows.iloc[i - 4:i - 2].min() and pivot <= weekly_lows.iloc[i - 1:i + 1].min():
                active_zone = pivot  # confirmed only after two completed weeks
            weekly_zone.iloc[i] = active_zone
        df['weekly_demand_zone_price'] = weekly_zone.reindex(df.index, method='ffill')

        prior_resistance = df['High'].rolling(60).max().shift(1)
        df['distance_to_resistance_pct'] = (prior_resistance - df['Close']) / df['Close']
        
        # Volatility - ATR
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()
        df['atr_pct'] = df['atr_14'] / df['Close']
        
        # Candlestick features
        df['body'] = df['Close'] - df['Open']
        df['upper_wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
        df['lower_wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
        df['is_bullish'] = (df['Close'] > df['Open']).astype(int)
        candle_range = (df['High'] - df['Low']).replace(0, np.nan)
        df['lower_wick_pct'] = df['lower_wick'] / candle_range
        df['rejection_strength'] = (df['lower_wick'] / candle_range) * df['is_bullish']
        accumulation = ((df['Close'] > df['Open']) & (df['Volume'] > df['avg_volume_20'])).astype(int)
        df['accumulation_days_10'] = accumulation.rolling(10).sum()

        # Market-regime features are joined from files dated no later than the
        # signal candle.  Missing context is left NaN and handled downstream.
        market_context = market_context or {}
        for ticker, prefix in [('SPY', 'spy'), ('QQQ', 'qqq'), ('IWM', 'iwm')]:
            market = market_context.get(ticker)
            if market is None:
                continue
            aligned = market.reindex(df.index, method='ffill')
            close = aligned['Close']
            df[f'{prefix}_return_5d'] = close.pct_change(5)
            df[f'{prefix}_return_20d'] = close.pct_change(20)
            df[f'{prefix}_return_50d'] = close.pct_change(50)
            df[f'{prefix}_above_200ma'] = (close > close.ewm(span=200, adjust=False).mean()).astype(int)
            if prefix == 'spy':
                market_tr = pd.concat([aligned['High'] - aligned['Low'],
                                       (aligned['High'] - close.shift()).abs(),
                                       (aligned['Low'] - close.shift()).abs()], axis=1).max(axis=1)
                df['spy_atr_pct'] = market_tr.rolling(14).mean() / close
                df['relative_strength_spy_20d'] = df['20d_return'] - df['spy_return_20d']
        for ticker in ['XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP', 'XLI', 'XLB', 'XLU', 'XLRE', 'XLC']:
            sector = market_context.get(ticker)
            if sector is not None:
                sector_close = sector.reindex(df.index, method='ffill')['Close']
                df[f'{ticker.lower()}_return_20d'] = sector_close.pct_change(20)
        if sector_etf in market_context:
            sector_close = market_context[sector_etf].reindex(df.index, method='ffill')['Close']
            df['sector_return_20d'] = sector_close.pct_change(20)
            df['sector_slope_20'] = sector_close.ewm(span=20, adjust=False).mean().pct_change(20)
            df['relative_strength_sector_20d'] = df['20d_return'] - df['sector_return_20d']
        vix = market_context.get('VIX')
        if vix is not None:
            vix_close = vix.reindex(df.index, method='ffill')['Close']
            df['vix_level'] = vix_close
            df['vix_percentile_60d'] = vix_close.rolling(60).rank(pct=True)
            
            # Phase 2: SPY Regime Features
            spy = market_context.get('SPY')
            if spy is not None:
                spy_close = spy.reindex(df.index, method='ffill')['Close']
                spy_ema200 = spy_close.ewm(span=200, adjust=False).mean()
                spy_ema50 = spy_close.ewm(span=50, adjust=False).mean()
                
                # SPY regime classification
                df['spy_above_200ma'] = (spy_close > spy_ema200).astype(int)
                df['spy_ema_alignment'] = ((spy_ema50 > spy_ema200)).astype(int)
                
                # SPY ADX (trend strength)
                spy_tr = pd.concat([
                    (spy['High'] - spy['Low']).reindex(df.index, method='ffill'),
                    (spy['High'] - spy_close.shift()).abs().reindex(df.index, method='ffill'),
                    (spy['Low'] - spy_close.shift()).abs().reindex(df.index, method='ffill')
                ], axis=1).max(axis=1)
                df['spy_adx'] = spy_tr.rolling(14).mean()
                
                # SPY ATR
                df['spy_atr_pct'] = spy_tr.rolling(14).mean() / spy_close
                
                # SPY regime classification based on VIX and trend
                df['spy_regime_bull'] = ((spy_close > spy_ema200) & (vix_close < 20)).astype(int)
                df['spy_regime_bear'] = ((spy_close < spy_ema200) & (vix_close > 25)).astype(int)
                df['spy_regime_correction'] = ((spy_close < spy_ema200) & (vix_close < 20)).astype(int)
                df['spy_regime_recovery'] = ((spy_close > spy_ema200) & (vix_close > 20)).astype(int)
                df['spy_regime_high_vol'] = (vix_close > 25).astype(int)
                df['spy_regime_low_vol'] = (vix_close < 15).astype(int)
        
        # Phase 2: Sector Context Features (per stock)
        for sector_ticker in ['XLK', 'XLF', 'XLE', 'XLV', 'XLY', 'XLP', 'XLI', 'XLB', 'XLU', 'XLRE', 'XLC']:
            sector = market_context.get(sector_ticker)
            if sector is not None:
                sector_close = sector.reindex(df.index, method='ffill')['Close']
                sector_ema200 = sector_close.ewm(span=200, adjust=False).mean()
                
                # Sector relative strength
                df[f'{sector_ticker.lower()}_relative_strength'] = df['20d_return'] - sector_close.pct_change(20)
                df[f'{sector_ticker.lower()}_above_200ema'] = (sector_close > sector_ema200).astype(int)
                df[f'{sector_ticker.lower()}_trend'] = sector_close.ewm(span=20, adjust=False).mean().pct_change(5)
                df[f'{sector_ticker.lower()}_momentum'] = sector_close.pct_change(20)
                df[f'{sector_ticker.lower()}_drawdown'] = (sector_close.rolling(252).max() - sector_close) / sector_close.rolling(252).max()
                df[f'{sector_ticker.lower()}_volatility'] = sector_close.pct_change().rolling(20).std()
        
        return df
    
    def detect_demand_zones(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect demand zones using swing low detection
        
        Args:
            df: DataFrame with OHLCV data and indicators
            
        Returns:
            List of zone dictionaries
        """
        zones = []
        lows = df['Low'].values
        dates = df.index
        
        # A pivot is only known after two following bars have closed.  The zone
        # therefore becomes tradable on the confirmation bar, never on the pivot.
        for i in range(2, len(lows) - 2):
            # Check if this is a swing low (lower than 2 bars on each side)
            if (lows[i] <= lows[i-1] and lows[i] <= lows[i-2] and 
                lows[i] <= lows[i+1] and lows[i] <= lows[i+2]):
                
                zone_price = lows[i]
                confirmation_idx = i + 2
                zone_date = dates[confirmation_idx]

                # Only information available at confirmation may define a zone.
                known_lows = lows[:confirmation_idx + 1]
                touches = int(np.count_nonzero(
                    np.abs(known_lows - zone_price) / zone_price <= self.config['zone_touch_threshold']
                ))

                departure_strength = (df['Close'].iloc[confirmation_idx] - zone_price) / zone_price
                zone_width_pct = df['atr_pct'].iloc[i]
                # Zone-formation quality, calculated only from the pivot and
                # its confirmation candles (all known before a later retest).
                base_start = i
                base_tolerance = max(self.config['zone_touch_threshold'], zone_width_pct * 2)
                while base_start > max(0, i - 10):
                    prior_close = df['Close'].iloc[base_start - 1]
                    if abs(prior_close - zone_price) / zone_price > base_tolerance:
                        break
                    base_start -= 1
                base_candles = i - base_start + 1
                baseline_volume = df['Volume'].iloc[max(0, i - 20):i].mean()
                base_volume = df['Volume'].iloc[base_start:i + 1].mean()
                departure_volume = df['Volume'].iloc[i:confirmation_idx + 1].mean()
                departure_high = df['High'].iloc[i:confirmation_idx + 1].max()
                base_high = df['High'].iloc[base_start:i + 1].max()
                base_low = df['Low'].iloc[base_start:i + 1].min()
                pre_base_ranges = (df['High'].iloc[max(0, base_start - 10):base_start] -
                                   df['Low'].iloc[max(0, base_start - 10):base_start])
                base_ranges = df['High'].iloc[base_start:i + 1] - df['Low'].iloc[base_start:i + 1]
                base_body = (df['Close'].iloc[base_start:i + 1] - df['Open'].iloc[base_start:i + 1]).abs()
                base_wicks = (df['High'].iloc[base_start:i + 1] - df[['Open', 'Close']].iloc[base_start:i + 1].max(axis=1) +
                              df[['Open', 'Close']].iloc[base_start:i + 1].min(axis=1) - df['Low'].iloc[base_start:i + 1])
                base_inside = ((df['High'].iloc[base_start + 1:i + 1].values <= df['High'].iloc[base_start:i].values) &
                               (df['Low'].iloc[base_start + 1:i + 1].values >= df['Low'].iloc[base_start:i].values)).sum()
                departure = df.iloc[i:confirmation_idx + 1]
                departure_body = (departure['Close'] - departure['Open']).abs()
                departure_ranges = (departure['High'] - departure['Low']).replace(0, np.nan)
                departure_bullish = (departure['Close'] > departure['Open']).astype(int)
                max_departure_idx = departure_body.idxmax()
                prior_close = df['Close'].iloc[i - 1]
                
                zones.append({
                    'price': zone_price,
                    'date': zone_date,
                    'confirmation_idx': confirmation_idx,
                    'initial_touches': touches,
                    'strength': departure_strength,
                    'width_pct': zone_width_pct,
                    'base_candles': base_candles,
                    'base_volume_ratio': base_volume / baseline_volume if baseline_volume else np.nan,
                    'departure_move_pct': (departure_high - zone_price) / zone_price,
                    'departure_volume_ratio': departure_volume / baseline_volume if baseline_volume else np.nan,
                    'base_range_pct': (base_high - base_low) / zone_price,
                    'volatility_contraction': base_ranges.mean() / pre_base_ranges.mean() if len(pre_base_ranges) and pre_base_ranges.mean() else np.nan,
                    'departure_atr_multiple': ((departure_high - zone_price) / zone_price) / zone_width_pct if zone_width_pct else np.nan,
                    'base_body_ratio': (base_body / base_ranges.replace(0, np.nan)).mean(),
                    'base_average_body_pct': base_body.mean() / zone_price,
                    'base_average_wick_ratio': (base_wicks / base_ranges.replace(0, np.nan)).mean(),
                    'base_tightness_score': zone_width_pct / (df['atr_pct'].iloc[i] + 1e-9),
                    'base_range_percentile': (base_ranges.mean() / (df['High'].iloc[max(0, i-60):i] - df['Low'].iloc[max(0, i-60):i]).mean()),
                    'inside_bar_count': int(base_inside),
                    'compression_score': (pre_base_ranges.mean() / base_ranges.mean()) if base_ranges.mean() else np.nan,
                    'largest_departure_candle_pct': departure_body.max() / zone_price,
                    'departure_gap_pct': (departure['Open'].iloc[0] - prior_close) / prior_close,
                    'departure_volume_percentile': df['Volume'].iloc[i:confirmation_idx + 1].rank(pct=True).iloc[-1],
                    'consecutive_bullish_departure': int(departure_bullish.cumprod().sum()),
                    'departure_close_near_high': ((df.loc[max_departure_idx, 'High'] - df.loc[max_departure_idx, 'Close']) / (df.loc[max_departure_idx, 'High'] - df.loc[max_departure_idx, 'Low'] + 1e-9)),
                })
        
        return zones
    
    def generate_signals(self, df: pd.DataFrame, zones: List[Dict], ticker: str) -> List[Dict]:
        """
        Generate trading signals from demand zones
        
        Args:
            df: DataFrame with indicators
            zones: List of detected zones
            ticker: Stock ticker
            
        Returns:
            List of signal dictionaries
        """
        signals = []
        
        for zone_id, zone in enumerate(zones):
            zone_price = zone['price']
            confirmation_idx = zone['confirmation_idx']
            # Vectorized retest detection: starts of contiguous at-zone runs.
            # This replaces millions of slow Pandas scalar accesses.
            start = confirmation_idx + 1
            end = len(df) - self.config['holding_period_days']
            future_lows = df['Low'].to_numpy()[start:end]
            at_zone = np.abs(future_lows - zone_price) / zone_price <= self.config['zone_touch_threshold']
            retest_starts = np.flatnonzero(at_zone & np.r_[True, ~at_zone[:-1]])
            retest_starts = retest_starts[:self.config['max_retests_per_zone']]
            for test_number, relative_idx in enumerate(retest_starts, start=1):
                row_idx = start + relative_idx
                previous_tests = test_number - 1
                
                signals.append({
                    'ticker': ticker,
                    'zone_id': zone_id,
                    'date': df.index[row_idx],
                    'row_idx': row_idx,
                    'price': df['Close'].iloc[row_idx],
                    'zone_price': zone_price,
                    'zone_touches': zone['initial_touches'] + previous_tests,
                    'zone_strength': zone['strength'],
                    'zone_age_days': row_idx - confirmation_idx,
                    'zone_width_pct': zone['width_pct'],
                    'previous_zone_tests': previous_tests,
                    'departure_strength': zone['strength'],
                    'base_candles': zone['base_candles'],
                    'base_volume_ratio': zone['base_volume_ratio'],
                    'departure_move_pct': zone['departure_move_pct'],
                    'departure_volume_ratio': zone['departure_volume_ratio'],
                    'base_range_pct': zone['base_range_pct'],
                    'volatility_contraction': zone['volatility_contraction'],
                    'departure_atr_multiple': zone['departure_atr_multiple'],
                    **{key: zone[key] for key in ['base_body_ratio','base_average_body_pct','base_average_wick_ratio','base_tightness_score','base_range_percentile','inside_bar_count','compression_score','largest_departure_candle_pct','departure_gap_pct','departure_volume_percentile','consecutive_bullish_departure','departure_close_near_high']},
                    'retest_number': test_number,
                    'is_first_retest': int(test_number == 1),
                })
        
        return signals
    
    def simulate_trades(self, df: pd.DataFrame, signals: List[Dict]) -> List[Dict]:
        """
        Simulate trade outcomes for signals
        
        Args:
            df: DataFrame with OHLCV data
            signals: List of signal dictionaries
            
        Returns:
            List of signals with trade outcomes added
        """
        for signal in signals:
            row_idx = signal['row_idx']
            entry_price = signal['price']
            
            # Get future data
            future_data = df.iloc[row_idx + 1:row_idx + self.config['holding_period_days'] + 1]
            
            if len(future_data) == 0:
                signal['hit_target'] = 0
                signal['hit_stop'] = 0
                signal['final_return_pct'] = 0
                signal['mfe_pct'] = 0
                signal['mae_pct'] = 0
                signal['max_return_20d'] = 0
                signal['days_until_target'] = self.config['holding_period_days']
                signal['trade_duration_days'] = self.config['holding_period_days']
                signal['exit_reason'] = 'no_data'
                continue
            
            # Calculate target and stop prices
            target_price = entry_price * (1 + self.config['target_gain_pct'])
            stop_loss_price = entry_price * (1 - self.config['stop_loss_pct'])
            
            # Track MFE and MAE
            mfe_pct = 0  # Maximum favorable excursion
            mae_pct = 0  # Maximum adverse excursion
            hit_target = 0
            hit_stop = 0
            exit_reason = 'timeout'
            days_until_target = self.config['holding_period_days']
            trade_duration_days = self.config['holding_period_days']
            target_10_price = entry_price * 1.10
            hit_target_10_5 = 0
            
            for day_number, (_, row) in enumerate(future_data.iterrows(), start=1):
                high = row['High']
                low = row['Low']
                current_mfe = (high - entry_price) / entry_price
                current_mae = (entry_price - low) / entry_price
                mfe_pct = max(mfe_pct, current_mfe)
                mae_pct = max(mae_pct, current_mae)
                
                # Check target hit
                if high >= target_price:
                    hit_target = 1
                    hit_target_10_5 = 1
                    exit_reason = 'target'
                    days_until_target = day_number
                    trade_duration_days = day_number
                    break
                
                # Check stop loss hit
                if low <= stop_loss_price:
                    hit_stop = 1
                    exit_reason = 'stop'
                    trade_duration_days = day_number
                    break
                if high >= target_10_price:
                    hit_target_10_5 = 1
            
            # Calculate final return
            final_price = future_data.iloc[-1]['Close']
            final_return_pct = (final_price - entry_price) / entry_price
            forward_return_5d = (future_data.iloc[min(4, len(future_data) - 1)]['Close'] - entry_price) / entry_price
            realized_return_pct = (
                self.config['target_gain_pct'] if hit_target else
                -self.config['stop_loss_pct'] if hit_stop else
                final_return_pct
            )
            
            # Update signal with outcomes
            signal['hit_target'] = hit_target
            signal['hit_stop'] = hit_stop
            signal['final_return_pct'] = final_return_pct
            signal['forward_return_5d'] = forward_return_5d
            signal['forward_return_20d'] = final_return_pct
            signal['realized_return_pct'] = realized_return_pct
            signal['mfe_pct'] = mfe_pct
            signal['mae_pct'] = mae_pct
            signal['max_return_20d'] = mfe_pct
            signal['days_until_target'] = days_until_target
            signal['trade_duration_days'] = trade_duration_days
            signal['hit_target_10_5'] = hit_target_10_5
            signal['exit_reason'] = exit_reason
        
        return signals
    
    def create_features(self, df: pd.DataFrame, signals: List[Dict]) -> pd.DataFrame:
        """
        Create feature matrix for ML training
        
        Args:
            df: DataFrame with indicators
            signals: List of signal dictionaries
            
        Returns:
            DataFrame with features
        """
        feature_rows = []
        # Outcomes from a prior retest become usable only after its complete
        # holding window. This avoids leaking a prior retest's future outcome.
        history = {}
        history_features = {}
        for signal in sorted(signals, key=lambda item: (item['zone_id'], item['row_idx'])):
            prior = [p for p in history.get(signal['zone_id'], [])
                     if p['row_idx'] + self.config['holding_period_days'] <= signal['row_idx']]
            history_features[id(signal)] = {
                'successful_previous_retests': sum(p['hit_target'] for p in prior),
                'failed_previous_retests': sum(1 - p['hit_target'] for p in prior),
                'time_since_last_touch': signal['row_idx'] - prior[-1]['row_idx'] if prior else np.nan,
                'previous_bounce_size': prior[-1]['mfe_pct'] if prior else np.nan,
            }
            history.setdefault(signal['zone_id'], []).append(signal)
        
        for signal in signals:
            row_idx = signal['row_idx']
            row = df.iloc[row_idx]
            zone_history = history_features[id(signal)]
            
            features = {
                'ticker': signal['ticker'],
                'date': signal['date'],
                'entry_price': signal['price'],
                'is_sub_10': int(signal['price'] < 10),
                
                # Price features
                'daily_return': row['daily_return'],
                '5d_return': row['5d_return'],
                '20d_return': row['20d_return'],
                
                # Trend features
                'ema_20': row['ema_20'],
                'ema_50': row['ema_50'],
                'ema_200': row['ema_200'],
                'dist_ema_20_pct': row['dist_ema_20_pct'],
                'dist_ema_50_pct': row['dist_ema_50_pct'],
                'dist_ema_200_pct': row['dist_ema_200_pct'],
                'ema_alignment': row['ema_alignment'],
                'trend_slope_20': row['trend_slope_20'],
                'price_vs_50ma_pct': row['price_vs_50ma_pct'],
                'price_vs_200ma_pct': row['price_vs_200ma_pct'],
                'ma_50_slope_20': row['ma_50_slope_20'],
                'distance_from_52w_high_pct': row['distance_from_52w_high_pct'],
                
                # Momentum features
                'rsi_14': row['rsi_14'],
                'macd': row['macd'],
                'macd_signal': row['macd_signal'],
                'macd_hist': row['macd_hist'],
                'roc_14': row['roc_14'],
                
                # Volume features
                'rel_volume': row['rel_volume'],
                'vol_spike_pct': row['vol_spike_pct'],
                'volume_ratio': row['volume_ratio'],
                'volume_trend_20': row['volume_trend_20'],
                'accumulation_days_10': row['accumulation_days_10'],
                
                # Volatility features
                'atr_14': row['atr_14'],
                'atr_pct': row['atr_pct'],
                
                # Zone features
                'zone_price': signal['zone_price'],
                'zone_touches': signal['zone_touches'],
                'zone_strength': signal['zone_strength'],
                'distance_to_zone_pct': (signal['price'] - signal['zone_price']) / signal['zone_price'],
                'zone_age_days': signal['zone_age_days'],
                'previous_zone_tests': signal['previous_zone_tests'],
                'zone_width_pct': signal['zone_width_pct'],
                'departure_strength': signal['departure_strength'],
                'base_candles': signal['base_candles'],
                'base_volume_ratio': signal['base_volume_ratio'],
                'departure_move_pct': signal['departure_move_pct'],
                'departure_volume_ratio': signal['departure_volume_ratio'],
                'base_range_pct': signal['base_range_pct'],
                'volatility_contraction': signal['volatility_contraction'],
                'departure_atr_multiple': signal['departure_atr_multiple'],
                'retest_number': signal['retest_number'],
                'is_first_retest': signal['is_first_retest'],
                **{key: signal[key] for key in ['base_body_ratio','base_average_body_pct','base_average_wick_ratio','base_tightness_score','base_range_percentile','inside_bar_count','compression_score','largest_departure_candle_pct','departure_gap_pct','departure_volume_percentile','consecutive_bullish_departure','departure_close_near_high']},
                **zone_history,
                
                # Candlestick features
                'is_bullish': row['is_bullish'],
                'lower_wick_pct': row['lower_wick_pct'],
                'rejection_strength': row['rejection_strength'],
                'avg_dollar_volume_20': row['avg_dollar_volume_20'],
                'volume_consistency_20': row['volume_consistency_20'],
                'daily_volatility_20': row['daily_volatility_20'],
                'gap_frequency_20': row['gap_frequency_20'],
                'obv_slope_20': row['obv_slope_20'],
                'chaikin_money_flow_20': row['chaikin_money_flow_20'],
                'distance_vwap_20_pct': row['distance_vwap_20_pct'],
                'dollar_volume_percentile_60': row['dollar_volume_percentile_60'],
                'weekly_price_vs_ema20': row['weekly_price_vs_ema20'],
                'weekly_ema_slope_10': row['weekly_ema_slope_10'],
                'weekly_rsi_14': row['weekly_rsi_14'],
                'weekly_macd': row['weekly_macd'],
                'distance_to_resistance_pct': row['distance_to_resistance_pct'],
                'weekly_demand_overlap': int(
                    pd.notna(row['weekly_demand_zone_price']) and
                    abs(signal['zone_price'] - row['weekly_demand_zone_price']) / row['weekly_demand_zone_price'] <= 0.05
                ),
                'ema_20_slope_20': row['ema_20_slope_20'],
                'ema_50_slope_20': row['ema_50_slope_20'],
                'ema_200_slope_20': row['ema_200_slope_20'],
                'adx_14': row['adx_14'],
                'weekly_above_ema50': row['weekly_above_ema50'],
                'weekly_higher_high': row['weekly_higher_high'],
                'weekly_higher_low': row['weekly_higher_low'],

                # Optional market-regime features.
                **{column: row[column] for column in [
                    'spy_return_5d', 'spy_return_20d', 'spy_above_200ma',
                    'spy_return_50d', 'spy_atr_pct', 'relative_strength_spy_20d',
                    'qqq_return_5d', 'qqq_return_20d', 'qqq_above_200ma',
                    'iwm_return_5d', 'iwm_return_20d', 'iwm_above_200ma',
                    'vix_level', 'vix_percentile_60d', 'xlk_return_20d', 'xlf_return_20d',
                    'xle_return_20d', 'xlv_return_20d', 'xly_return_20d', 'xlp_return_20d',
                    'xli_return_20d', 'xlb_return_20d', 'xlu_return_20d', 'xlre_return_20d',
                    'xlc_return_20d'
                ] if column in row.index},
                
                # Trade outcomes (targets)
                'hit_target': signal['hit_target'],
                'hit_stop': signal['hit_stop'],
                'final_return_pct': signal['final_return_pct'],
                'forward_return_5d': signal['forward_return_5d'],
                'forward_return_20d': signal['forward_return_20d'],
                'realized_return_pct': signal['realized_return_pct'],
                'mfe_pct': signal['mfe_pct'],
                'max_return_20d': signal['max_return_20d'],
                'days_until_target': signal['days_until_target'],
                'trade_duration_days': signal['trade_duration_days'],
                'hit_target_10_5': signal['hit_target_10_5'],
                'mae_pct': signal['mae_pct'],
                'exit_reason': signal['exit_reason'],
            }
            
            feature_rows.append(features)
        
        return pd.DataFrame(feature_rows)
    
    def process_stock(self, ticker: str, df: pd.DataFrame, market_context: Dict[str, pd.DataFrame] = None,
                      sector_map: Dict[str, str] = None) -> pd.DataFrame:
        """
        Process a single stock: detect zones, generate signals, simulate trades
        
        Args:
            ticker: Stock ticker
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with features for this stock
        """
        print(f"  Processing {ticker}...")
        
        # Calculate indicators
        sector_etf = (sector_map or {}).get(ticker)
        df = self.calculate_indicators(df, market_context, sector_etf)
        df = df.dropna()
        
        # Detect demand zones
        zones = self.detect_demand_zones(df)
        print(f"    Found {len(zones)} demand zones")
        self.total_zones_found += len(zones)
        
        if len(zones) == 0:
            return pd.DataFrame()
        
        # Generate signals
        signals = self.generate_signals(df, zones, ticker)
        
        # Simulate trades
        signals = self.simulate_trades(df, signals)
        
        # Create features
        features_df = self.create_features(df, signals)
        
        return features_df
    
    def generate_dataset(self) -> pd.DataFrame:
        """
        Generate complete ML dataset from all stocks
        
        Returns:
            DataFrame with all features and labels
        """
        print("=" * 60)
        print("Generating ML Dataset")
        print("=" * 60)
        
        # Load stock data
        stock_data = self.load_stock_csvs()
        market_context = self.load_market_context()
        sector_map = self.load_sector_map()
        
        if not stock_data:
            print("No stock data loaded. Exiting.")
            return pd.DataFrame()
        
        # Process each stock
        all_features = []
        
        for ticker, df in stock_data.items():
            try:
                features_df = self.process_stock(ticker, df, market_context, sector_map)
                if len(features_df) > 0:
                    all_features.append(features_df)
                    self.all_signals.extend(features_df.to_dict('records'))
            except Exception as e:
                print(f"  Error processing {ticker}: {str(e)[:50]}")
        
        # Combine all features
        if all_features:
            final_dataset = pd.concat(all_features, ignore_index=True)
            # Different overlapping zones can fire on the same stock/day. Keep
            # the closest zone only: one ticker may produce at most one trade
            # candidate per date. Later retests after an exit remain valid.
            final_dataset = final_dataset.sort_values(
                ['ticker', 'date', 'distance_to_zone_pct'],
                key=lambda series: series.abs() if series.name == 'distance_to_zone_pct' else series
            ).drop_duplicates(subset=['ticker', 'date'], keep='first').reset_index(drop=True)
            print(f"\nTotal signals generated: {len(final_dataset)}")
            print(f"Total zones found: {self.total_zones_found}")
            return final_dataset
        else:
            print("No signals generated. Exiting.")
            return pd.DataFrame()
    
    def save_dataset(self, dataset: pd.DataFrame):
        """
        Save dataset to CSV
        
        Args:
            dataset: DataFrame to save
        """
        if len(dataset) == 0:
            print("No data to save.")
            return
        
        output_path = self.config['output_file']
        dataset.to_csv(output_path, index=False)
        print(f"\nDataset saved to {output_path}")
        print(f"Shape: {dataset.shape}")
        print(f"Columns: {list(dataset.columns)}")


def main():
    """Main execution function"""
    print("\n" + "=" * 60)
    print("Demand Zone ML Dataset Generator")
    print("=" * 60 + "\n")
    
    # Initialize generator
    generator = DemandZoneDatasetGenerator()
    
    # Generate dataset
    dataset = generator.generate_dataset()
    
    # Save dataset
    generator.save_dataset(dataset)
    
    print("\n" + "=" * 60)
    print("Dataset Generation Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
