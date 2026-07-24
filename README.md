# ML Demand Zone Trading System

A fully automated machine learning pipeline for demand zone trading on US stocks priced between $1-$10.

## Overview

This system automatically:
1. Scans stock CSV files for demand zones
2. Generates trading signals with technical features
3. Simulates trade outcomes (MFE/MAE calculation)
4. Trains ML models (Random Forest, XGBoost, LightGBM)
5. Selects the best model and evaluates performance
6. Runs realistic backtesting with transaction costs

## Features

- **Automated Data Pipeline**: One command runs everything from data to model evaluation
- **Demand Zone Detection**: 5-bar pivot swing low detection with touch counting
- **Feature Engineering**: 30+ technical indicators (price, trend, momentum, volume, volatility)
- **Trade Simulation**: Realistic trade outcomes with MFE/MAE tracking
- **Model Comparison**: Automatic selection of best model (RF/XGBoost/LightGBM)
- **Risk-Adjusted Targets**: MFE/MAE ratio for better trade quality assessment
- **Realistic Backtesting**: Transaction costs, position sizing, overlapping trade prevention
- **Sharpe Ratio Optimization**: Trading-focused threshold optimization

## Installation

```bash
pip install pandas numpy scikit-learn xgboost lightgbm matplotlib yfinance
```

## Folder Structure

```
/Prajwal MIT/Passion/
├── data/                          # Folder for stock CSV files
│   ├── AMC_data.csv
│   ├── ARVN_data.csv
│   └── ... (more stock CSV files)
├── generate_ml_dataset.py         # Dataset generator
├── ml_demand_zone_trainer.py      # ML model trainer
├── run_pipeline.py                # Main pipeline orchestrator
├── stock_demand_zone_signals.py   # Legacy signal detector
└── README.md
```

## Setup

1. **Create data folder**:
```bash
mkdir data
```

2. **Add stock CSV files** to the `data/` folder:
   - Format: `{TICKER}_data.csv`
   - Required columns: `Date`, `Open`, `High`, `Low`, `Close`, `Volume`
   - Example: `AMC_data.csv`, `ARVN_data.csv`, `GNL_data.csv`

3. **Configure parameters** in `generate_ml_dataset.py`:
```python
CONFIG = {
    'data_folder': './data',
    'output_file': 'demand_zone_ml_dataset.csv',
    'min_price': 1.0,              # $1 minimum price
    'max_price': 10.0,             # $10 maximum price
    'min_volume': 1000000,         # 1M+ shares daily volume
    'stop_loss_pct': 0.05,         # 5% stop loss
    'target_gain_pct': 0.15,       # 15% profit target
    'holding_period_days': 20,     # 20-day holding period
}
```

## Usage

Run the complete pipeline with one command:

```bash
python run_pipeline.py
```

This executes:
1. **Step 1**: Generate ML dataset from stock CSV files
2. **Step 2**: Train and compare ML models
3. **Step 3**: Evaluate performance metrics
4. **Step 4**: Save results to file

## Output Files

- `demand_zone_ml_dataset.csv` - Generated ML dataset with features and labels
- `pipeline_results.txt` - Summary of pipeline results and performance metrics
- `feature_importance.png` - Feature importance plot
- `model_comparison.csv` - Model comparison results (if using compare_models)

## Pipeline Details

### Step 1: Dataset Generation

The `generate_ml_dataset.py` script:
- Scans `data/` folder for `*_data.csv` files
- Extracts ticker name from filename
- Loads OHLCV data and filters by price ($1-$10) and volume (1M+)
- Calculates 30+ technical indicators
- Detects demand zones using 5-bar pivot swing lows
- Generates trading signals at zone touches
- Simulates trades with +15% target / -7% stop over 20 days
- Calculates MFE/MAE for risk/reward assessment
- Saves dataset with features and labels

### Step 2: Model Training

The `ml_demand_zone_trainer.py` script:
- Loads the generated dataset
- Prepares features (removes raw prices, handles missing values)
- Creates risk-adjusted target (MFE/MAE ratio > 3)
- Splits data chronologically (70/15/15 train/val/test)
- Trains Random Forest, XGBoost, and LightGBM
- Compares models and selects best based on AUC
- Optimizes probability threshold using Sharpe ratio
- Evaluates on test set with optimized threshold

### Step 3: Performance Evaluation

Metrics tracked:
- Precision (primary trading metric)
- Recall
- F1 Score
- ROC-AUC
- Sharpe Ratio
- Profit Factor
- Maximum Drawdown
- Win Rate

### Step 4: Results

Saves comprehensive results to `pipeline_results.txt` including:
- Dataset statistics
- Model performance metrics
- Best model selection
- Trading metrics

## Configuration Options

### Dataset Generator (`generate_ml_dataset.py`)

- `data_folder`: Path to stock CSV files
- `min_price`: Minimum stock price ($1)
- `max_price`: Maximum stock price ($10)
- `min_volume`: Minimum daily volume (1M shares)
- `stop_loss_pct`: Stop loss percentage (5%)
- `target_gain_pct`: Profit target percentage (15%)
- `holding_period_days`: Maximum holding period (20 days)
- `zone_detection_window`: Lookback window for zones (90 days)
- `min_zone_touches`: Minimum touches for zone (2)

### ML Trainer (`ml_demand_zone_trainer.py`)

- `target_col`: Target column for prediction
- `use_risk_adjusted`: Use MFE/MAE risk-adjusted target
- `compare_models_flag`: Compare RF/XGBoost/LightGBM
- `optimize_metric`: Threshold optimization metric ('sharpe', 'f1', 'precision')

## Key Features

### Demand Zone Detection
- 5-bar pivot swing low detection
- Touch counting with configurable tolerance
- Zone strength calculation based on touches
- Automatic zone expiration after holding period

### Feature Engineering
**Price Features**: daily_return, 5d_return, 20d_return, distance_to_zone
**Trend Features**: EMA20/50/200, EMA distances, trend alignment, slope
**Momentum Features**: RSI, MACD, MACD histogram, ROC
**Volume Features**: Relative volume, volume spike percentage
**Volatility Features**: ATR, ATR percentage
**Zone Features**: Zone touches, zone strength, distance to zone
**Candlestick Features**: Bullish/bearish, body size

### Trade Simulation
- Entry at demand zone price
- Stop loss: -7%
- Take profit: +15%
- Maximum holding period: 20 days
- MFE (Maximum Favorable Excursion) tracking
- MAE (Maximum Adverse Excursion) tracking
- Exit reasons: target, stop, timeout

### Model Training
- Chronological train/val/test split (no look-ahead bias)
- Class imbalance handling (scale_pos_weight)
- Permutation importance for feature interpretation
- Sharpe ratio-based threshold optimization
- Walk-forward validation

### Backtesting
- Risk-based position sizing (2% risk per trade)
- Transaction costs (0.1% per trade)
- Overlapping trade prevention
- Position tracking with entry/exit dates
- Daily equity curve for drawdown calculation

## Example Output

```
============================================================
DEMAND ZONE ML TRADING PIPELINE
============================================================
Started at: 2024-01-15 10:30:00

============================================================
STEP 1: Generate ML Dataset
============================================================
Found 50 CSV files
  Loaded AMC: 1256 days
  Loaded ARVN: 892 days
  ...
Total signals generated: 3420
Total zones found: 1256
✓ Dataset generated successfully: 3420 signals

============================================================
STEP 2: Train ML Models
============================================================
Model Comparison
------------------------------------------------------------
--- Random Forest ---
  Precision: 0.6234
  Recall: 0.4512
  F1: 0.5234
  AUC: 0.7123

--- XGBoost ---
  Precision: 0.6543
  Retry: 0.4789
  F1: 0.5512
  AUC: 0.7456

Best model: XGBoost (AUC: 0.7456)
✓ Model training completed

============================================================
STEP 3: Evaluate Performance
============================================================
Model Performance Metrics:
  Precision: 0.6543
  Recall: 0.4789
  F1 Score: 0.5512
  ROC-AUC: 0.7456
✓ Performance evaluation completed

============================================================
STEP 4: Save Results
============================================================
✓ Results saved to pipeline_results.txt

============================================================
PIPELINE COMPLETED SUCCESSFULLY
============================================================
Duration: 0:15:32
```

## Notes

- **Survivorship Bias**: The system uses current stock universe, which may overestimate performance
- **Look-Ahead Bias**: All splits are chronological to prevent future data leakage
- **Transaction Costs**: Backtesting includes realistic costs and slippage
- **Position Sizing**: Risk-based sizing (2% account risk per trade)
- **Model Selection**: Automatic selection based on validation AUC
- **Threshold Optimization**: Sharpe ratio optimization for trading-focused results

## Troubleshooting

**No CSV files found**: Ensure stock CSV files are in the `data/` folder with format `{TICKER}_data.csv`

**Insufficient data**: Stocks need at least 252 days (1 year) of historical data

**No signals generated**: Check if stocks meet price/volume filters and have valid demand zones

**LightGBM not available**: Install with `pip install lightgbm` (optional, system will use RF/XGBoost)
