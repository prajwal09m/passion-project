"""
ML Demand Zone Trading Model
Train and evaluate ML models for demand zone signal prediction
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, classification_report, mean_absolute_error, r2_score
import xgboost as xgb
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


class DemandZoneMLTrainer:
    """
    ML trainer for demand zone signal prediction
    Uses chronological splits to avoid look-ahead bias
    """
    
    def __init__(self, dataset_path: str = 'demand_zone_ml_dataset.csv'):
        """
        Initialize trainer with dataset
        
        Args:
            dataset_path: Path to ML dataset CSV
        """
        self.dataset_path = dataset_path
        self.dataset = None
        self.features = None
        self.target = None
        self.model = None
        self.return_model = None
        self.feature_importance = None
        
    def load_dataset(self):
        """Load and prepare dataset for ML training"""
        print("Loading dataset...")
        self.dataset = pd.read_csv(self.dataset_path)
        self.dataset['date'] = pd.to_datetime(self.dataset['date'])
        print(f"  Loaded {len(self.dataset)} signals")
        
    def prepare_features(self, target_col: str = 'hit_target', create_risk_adjusted: bool = False):
        """
        Prepare features and target for ML training
        Remove raw price features to prevent scale bias
        Handle missing values
        Optionally create risk-adjusted target
        
        Args:
            target_col: Column to use as prediction target
            create_risk_adjusted: If True, create risk-adjusted success target
        """
        print(f"\nPreparing features (target: {target_col})...")
        
        # Risk-adjusted returns belong in the backtest, not in the classifier's
        # label.  Keep this optional only for controlled research experiments.
        if create_risk_adjusted and 'mfe_pct' in self.dataset.columns and 'mae_pct' in self.dataset.columns:
            print("  Creating risk-adjusted target...")
            # Use MFE/MAE for risk/reward ratio (more accurate than final_return/max_drawdown)
            # MFE = Maximum Favorable Excursion (best price achieved)
            # MAE = Maximum Adverse Excursion (worst price experienced)
            # Good trade: reward/risk ratio > 3 (MFE at least 3x MAE)
            risk_reward_ratio = self.dataset['mfe_pct'] / (self.dataset['mae_pct'] + 0.001)
            self.dataset['risk_adjusted_success'] = (risk_reward_ratio > 3).astype(int)
            target_col = 'risk_adjusted_success'
            print(f"  Risk-adjusted target distribution: {self.dataset[target_col].value_counts().to_dict()}")
            print(f"  Average risk/reward ratio: {risk_reward_ratio.mean():.2f}")
        
        # Exclude non-feature columns
        exclude_cols = ['ticker', 'date', 'exit_reason', 
                       'hit_target', 'hit_stop', 'final_return_pct', 'realized_return_pct',
                       'forward_return_5d', 'forward_return_20d', 'max_return_20d',
                       'days_until_target', 'trade_duration_days', 'hit_target_10_5',
                       'risk_adjusted_success', 'mfe_pct', 'mae_pct',
                       'entry_price', 'zone_price']  # Also exclude MFE/MAE and raw prices from features
        
        # Remove raw price features to prevent scale bias
        # Model should learn from normalized features, not absolute prices
        price_cols = ['ema_20', 'ema_50', 'ema_200', 'atr_14']
        exclude_cols.extend(price_cols)
        
        # Use all other columns as features
        feature_cols = [col for col in self.dataset.columns 
                       if col not in exclude_cols]
        
        self.features = self.dataset[feature_cols].copy()
        self.target = self.dataset[target_col].copy()
        
        # Handle missing values
        print("  Handling missing values...")
        self.features = self.features.replace([np.inf, -np.inf], np.nan)
        self.features = self.features.fillna(self.features.median())
        
        print(f"  Features: {len(feature_cols)} columns")
        print(f"  Target distribution: {self.target.value_counts().to_dict()}")

    def run_return_regression(self, X_train, X_test):
        """Predict a forward return for ranking research, separate from trading labels."""
        target = self.dataset['forward_return_20d']
        y_train = target.loc[X_train.index]
        y_test = target.loc[X_test.index]
        self.return_model = RandomForestRegressor(
            n_estimators=300, max_depth=8, min_samples_leaf=10,
            random_state=42, n_jobs=-1
        )
        self.return_model.fit(X_train, y_train)
        predicted = self.return_model.predict(X_test)
        rank_corr = pd.Series(predicted).corr(pd.Series(y_test.values), method='spearman')
        metrics = {
            'mae': mean_absolute_error(y_test, predicted),
            'r2': r2_score(y_test, predicted),
            'spearman_rank_correlation': 0.0 if pd.isna(rank_corr) else rank_corr,
        }
        print("\nForward Return Ranking (held-out test set):")
        for name, value in metrics.items():
            print(f"  {name}: {value:.4f}")
        return metrics
        
    def chronological_split(self, train_ratio: float = 0.7, val_ratio: float = 0.15):
        """
        Split data chronologically into train/val/test (no random shuffling)
        Prevents threshold optimization leakage by using separate validation set
        
        Args:
            train_ratio: Proportion of data for training
            val_ratio: Proportion of data for validation
            
        Returns:
            X_train, X_val, X_test, y_train, y_val, y_test
        """
        print(f"\nChronological split (train: {train_ratio:.0%}, val: {val_ratio:.0%}, test: {1-train_ratio-val_ratio:.0%})...")
        
        # Sort by date
        sorted_idx = self.dataset['date'].argsort()
        train_end = int(len(sorted_idx) * train_ratio)
        val_end = int(len(sorted_idx) * (train_ratio + val_ratio))
        
        train_idx = sorted_idx[:train_end]
        val_idx = sorted_idx[train_end:val_end]
        test_idx = sorted_idx[val_end:]
        
        X_train = self.features.iloc[train_idx]
        X_val = self.features.iloc[val_idx]
        X_test = self.features.iloc[test_idx]
        y_train = self.target.iloc[train_idx]
        y_val = self.target.iloc[val_idx]
        y_test = self.target.iloc[test_idx]
        
        print(f"  Train: {len(X_train)} samples ({self.dataset['date'].iloc[train_idx].min()} to {self.dataset['date'].iloc[train_idx].max()})")
        print(f"  Val: {len(X_val)} samples ({self.dataset['date'].iloc[val_idx].min()} to {self.dataset['date'].iloc[val_idx].max()})")
        print(f"  Test: {len(X_test)} samples ({self.dataset['date'].iloc[test_idx].min()} to {self.dataset['date'].iloc[test_idx].max()})")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def train_random_forest(self, X_train, y_train, n_estimators: int = 100):
        """
        Train Random Forest classifier with class imbalance handling
        
        Args:
            X_train: Training features
            y_train: Training target
            n_estimators: Number of trees
        """
        print("\nTraining Random Forest...")
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            class_weight='balanced',  # Handle class imbalance
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train, y_train)
        print("  Random Forest trained")
        
    def train_xgboost(self, X_train, y_train):
        """
        Train XGBoost classifier with class imbalance handling
        
        Args:
            X_train: Training features
            y_train: Training target
        """
        print("\nTraining XGBoost...")
        
        # Calculate scale_pos_weight for class imbalance
        neg_count = (y_train == 0).sum()
        pos_count = (y_train == 1).sum()
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1
        
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,  # Handle class imbalance
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train, y_train)
        print(f"  XGBoost trained (scale_pos_weight: {scale_pos_weight:.2f})")
    
    def train_lightgbm(self, X_train, y_train):
        """
        Train LightGBM classifier with class imbalance handling
        
        Args:
            X_train: Training features
            y_train: Training target
        """
        if not LIGHTGBM_AVAILABLE:
            print("  LightGBM not available, skipping...")
            return None
        
        print("\nTraining LightGBM...")
        
        # Calculate scale_pos_weight for class imbalance
        neg_count = (y_train == 0).sum()
        pos_count = (y_train == 1).sum()
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1
        
        self.model = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,  # Handle class imbalance
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
        self.model.fit(X_train, y_train)
        print(f"  LightGBM trained (scale_pos_weight: {scale_pos_weight:.2f})")
        
    def compare_models(self, X_train, y_train, X_val, y_val):
        """
        Compare Random Forest, XGBoost, and LightGBM models
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            
        Returns:
            DataFrame with model comparison results
        """
        print("\n" + "=" * 60)
        print("Model Comparison")
        print("=" * 60)
        
        results = []
        
        # Random Forest
        print("\n--- Random Forest ---")
        self.train_random_forest(X_train, y_train)
        rf_metrics = self.evaluate(X_val, y_val)
        rf_metrics['model'] = 'Random Forest'
        results.append(rf_metrics)
        
        # XGBoost
        print("\n--- XGBoost ---")
        self.train_xgboost(X_train, y_train)
        xgb_metrics = self.evaluate(X_val, y_val)
        xgb_metrics['model'] = 'XGBoost'
        results.append(xgb_metrics)
        
        # LightGBM
        if LIGHTGBM_AVAILABLE:
            print("\n--- LightGBM ---")
            self.train_lightgbm(X_train, y_train)
            if self.model is not None:
                lgb_metrics = self.evaluate(X_val, y_val)
                lgb_metrics['model'] = 'LightGBM'
                results.append(lgb_metrics)
        
        # Create comparison DataFrame
        comparison_df = pd.DataFrame(results)
        comparison_df = comparison_df.set_index('model')
        
        print("\n" + "=" * 60)
        print("Model Comparison Results")
        print("=" * 60)
        print(comparison_df.to_string())
        
        # Select best model based on AUC
        best_model = comparison_df['auc'].idxmax()
        print(f"\nBest model: {best_model} (AUC: {comparison_df.loc[best_model, 'auc']:.4f})")
        
        # Retrain best model
        if best_model == 'Random Forest':
            self.train_random_forest(X_train, y_train)
        elif best_model == 'XGBoost':
            self.train_xgboost(X_train, y_train)
        elif best_model == 'LightGBM':
            self.train_lightgbm(X_train, y_train)
        
        return comparison_df
    
    def evaluate(self, X_test, y_test, threshold: float = 0.5):
        """
        Evaluate model performance
        
        Args:
            X_test: Test features
            y_test: Test target
            
        Returns:
            Dictionary of metrics
        """
        print("\nEvaluating model...")
        
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba >= threshold).astype(int)
        
        metrics = {
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
            'auc': roc_auc_score(y_test, y_pred_proba)
        }
        
        print("  Metrics:")
        for metric, value in metrics.items():
            print(f"    {metric.upper()}: {value:.4f}")
        
        print("\n  Classification Report:")
        print(classification_report(y_test, y_pred))
        
        return metrics
    
    def get_feature_importance(self, X_eval, y_eval, use_permutation: bool = True):
        """
        Get feature importance from trained model
        Uses permutation importance for more reliable results
        
        Args:
            use_permutation: If True, use permutation importance (more reliable)
            
        Returns:
            DataFrame with feature importance
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        from sklearn.inspection import permutation_importance
        
        feature_names = self.features.columns
        
        if use_permutation:
            # Use permutation importance (more reliable than Gini importance)
            print("  Calculating permutation importance...")
            # Importance must be measured out of sample.  Never reuse training
            # rows here: they can make weak/noisy features look predictive.
            perm_importance = permutation_importance(
                self.model, X_eval, y_eval, n_repeats=10, random_state=42,
                n_jobs=-1, scoring='roc_auc'
            )
            
            self.feature_importance = pd.DataFrame({
                'feature': feature_names,
                'importance': perm_importance.importances_mean
            }).sort_values('importance', ascending=False)
        else:
            # Fall back to Gini importance (less reliable)
            importance = self.model.feature_importances_
            self.feature_importance = pd.DataFrame({
                'feature': feature_names,
                'importance': importance
            }).sort_values('importance', ascending=False)
        
        return self.feature_importance
    
    def plot_feature_importance(self, top_n: int = 20):
        """
        Plot top N feature importance
        
        Args:
            top_n: Number of top features to display
        """
        if self.feature_importance is None:
            raise ValueError("Calculate feature importance on a held-out set before plotting")
        
        top_features = self.feature_importance.head(top_n)
        
        plt.figure(figsize=(10, 6))
        plt.barh(top_features['feature'], top_features['importance'])
        plt.xlabel('Importance')
        plt.ylabel('Feature')
        plt.title(f'Top {top_n} Feature Importance')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig('feature_importance.png', dpi=150)
        print(f"\nFeature importance plot saved to feature_importance.png")
        
    def optimize_probability_threshold(self, X_test, y_test, X_test_idx=None, thresholds=None, optimize_metric='sharpe'):
        """
        Optimize probability threshold based on Sharpe ratio (trading-focused)
        
        Args:
            X_test: Test features
            y_test: Test target
            X_test_idx: Index mapping to dataset for return calculation
            thresholds: List of thresholds to test (default: 0.50-0.75)
            optimize_metric: Metric to optimize ('sharpe', 'f1', 'precision')
            
        Returns:
            Best threshold and corresponding metrics
        """
        if thresholds is None:
            thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
        
        print(f"\nOptimizing probability threshold (metric: {optimize_metric})...")
        
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        
        best_threshold = 0.5
        best_metric_value = -np.inf if optimize_metric == 'sharpe' else 0
        
        for threshold in thresholds:
            y_pred_filtered = (y_pred_proba >= threshold).astype(int)
            
            if y_pred_filtered.sum() > 0:
                precision = precision_score(y_test, y_pred_filtered, zero_division=0)
                recall = recall_score(y_test, y_pred_filtered, zero_division=0)
                f1 = f1_score(y_test, y_pred_filtered, zero_division=0)
                signals_kept = y_pred_filtered.sum() / len(y_pred_filtered)
                
                # Calculate Sharpe ratio if we have returns
                sharpe = 0
                if optimize_metric == 'sharpe' and X_test_idx is not None:
                    test_returns = self.dataset.loc[X_test_idx, 'realized_return_pct'].values
                    trade_returns = test_returns[y_pred_filtered == 1]
                    if len(trade_returns) > 1:
                        sharpe = np.mean(trade_returns) / np.std(trade_returns) * np.sqrt(252) if np.std(trade_returns) > 0 else 0
                
                print(f"  Threshold {threshold:.2f}: Precision={precision:.3f}, Recall={recall:.3f}, F1={f1:.3f}, Sharpe={sharpe:.2f}, Signals={signals_kept:.1%}")
                
                # Select best based on metric
                if optimize_metric == 'sharpe':
                    if sharpe > best_metric_value:
                        best_metric_value = sharpe
                        best_threshold = threshold
                elif optimize_metric == 'f1':
                    if f1 > best_metric_value:
                        best_metric_value = f1
                        best_threshold = threshold
                elif optimize_metric == 'precision':
                    if precision > best_metric_value:
                        best_metric_value = precision
                        best_threshold = threshold
        
        print(f"\n  Best threshold: {best_threshold:.2f} ({optimize_metric}: {best_metric_value:.3f})")
        return best_threshold
    
    def probability_based_filtering(self, X_test, y_test, threshold: float = None):
        """
        Apply probability-based filtering to improve precision
        
        Args:
            X_test: Test features
            y_test: Test target
            threshold: Minimum probability threshold (if None, will optimize)
            
        Returns:
            Filtered metrics
        """
        if threshold is None:
            threshold = self.optimize_probability_threshold(X_test, y_test)
        
        print(f"\nProbability-based filtering (threshold: {threshold})...")
        
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred_filtered = (y_pred_proba >= threshold).astype(int)
        
        # Calculate filtered metrics
        if y_pred_filtered.sum() > 0:
            metrics_filtered = {
                'precision': precision_score(y_test, y_pred_filtered),
                'recall': recall_score(y_test, y_pred_filtered),
                'f1': f1_score(y_test, y_pred_filtered),
                'signals_kept': y_pred_filtered.sum() / len(y_pred_filtered)
            }
            
            print("  Filtered Metrics:")
            for metric, value in metrics_filtered.items():
                print(f"    {metric}: {value:.4f}")
        else:
            print("  No signals passed threshold")
            metrics_filtered = None
            
        return metrics_filtered
    
    def walk_forward_validation(self, n_splits: int = 5, threshold: float = 0.6):
        """
        Perform walk-forward validation with optimized threshold
        Creates fresh model each fold to avoid global state leakage
        
        Args:
            n_splits: Number of splits for validation
            threshold: Probability threshold for predictions
        """
        print(f"\nWalk-forward validation ({n_splits} splits, threshold: {threshold})...")
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        metrics_list = []
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(self.features)):
            print(f"\n  Fold {fold + 1}/{n_splits}")
            
            X_train = self.features.iloc[train_idx]
            X_test = self.features.iloc[test_idx]
            y_train = self.target.iloc[train_idx]
            y_test = self.target.iloc[test_idx]
            
            # Create fresh model for each fold (avoid global state leakage)
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                class_weight='balanced',
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            
            # Evaluate with optimized threshold (not default 0.5)
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            y_pred = (y_pred_proba >= threshold).astype(int)
            
            metrics = {
                'precision': precision_score(y_test, y_pred, zero_division=0),
                'recall': recall_score(y_test, y_pred, zero_division=0),
                'f1': f1_score(y_test, y_pred, zero_division=0),
                'auc': roc_auc_score(y_test, y_pred_proba)
            }
            metrics_list.append(metrics)
            
            print(f"    Precision: {metrics['precision']:.4f}")
            print(f"    Recall: {metrics['recall']:.4f}")
            print(f"    F1: {metrics['f1']:.4f}")
            print(f"    AUC: {metrics['auc']:.4f}")
        
        # Average metrics
        avg_metrics = {
            metric: np.mean([m[metric] for m in metrics_list])
            for metric in metrics_list[0].keys()
        }
        
        print("\n  Average Metrics Across Folds:")
        for metric, value in avg_metrics.items():
            print(f"    {metric.upper()}: {value:.4f}")
        
        return avg_metrics
    
    def backtest_portfolio(self, X_test, y_test, initial_capital: float = 10000,
                          risk_per_trade: float = 0.01, stop_loss_pct: float = 0.05,
                          threshold: float = 0.5, transaction_cost: float = 0.0005,
                          slippage_bps: float = 15, commission_per_trade: float = 1.0,
                          max_positions: int = 5):
        """
        Simulate portfolio performance based on model predictions
        Uses proper risk sizing: position_size = risk_amount / stop_loss
        Respects time ordering by sorting trades by date
        Includes transaction costs and slippage
        Tracks positions to prevent overlapping trades
        
        Args:
            X_test: Test features
            y_test: Test target (actual returns)
            initial_capital: Starting capital
            risk_per_trade: Risk percentage per trade (e.g., 0.02 = 2%)
            stop_loss_pct: Stop loss percentage for position sizing
            threshold: Probability threshold for taking trades
            transaction_cost: Transaction cost per trade (e.g., 0.001 = 0.1%)
            
        Returns:
            Portfolio metrics dictionary
        """
        print(f"\nPortfolio Backtest (Capital: ${initial_capital:,.0f}, Risk: {risk_per_trade:.1%}, Stop: {stop_loss_pct:.1%}, Cost: {transaction_cost:.2%})...")
        
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred_filtered = (y_pred_proba >= threshold).astype(int)
        
        # Get actual returns, dates, and tickers from dataset
        test_returns = self.dataset.loc[X_test.index, 'realized_return_pct'].values
        test_dates = self.dataset.loc[X_test.index, 'date'].values
        test_tickers = self.dataset.loc[X_test.index, 'ticker'].values
        test_durations = self.dataset.loc[X_test.index, 'trade_duration_days'].values
        
        # Only take trades where model predicts success
        trade_mask = (y_pred_filtered == 1)
        
        if trade_mask.sum() == 0:
            print("  No trades taken")
            return None
        
        # Create trade dataframe with dates, returns, and tickers
        trades_df = pd.DataFrame({
            'date': test_dates[trade_mask],
            'return': test_returns[trade_mask],
            'ticker': test_tickers[trade_mask],
            'duration_days': test_durations[trade_mask]
        })
        
        # Sort by date to respect time ordering
        trades_df = trades_df.sort_values('date')
        
        # Event-based portfolio accounting: cash is reserved at entry and
        # released only at exit. This enforces both capital and position limits.
        cash = initial_capital
        portfolio_value = initial_capital
        equity_curve = [initial_capital]
        open_positions = []
        completed_returns = []
        skipped_capacity = 0
        
        # Detailed trade log for audit
        trade_log = []
        
        for _, row in trades_df.iterrows():
            ticker = row['ticker']
            ret = row['return']
            signal_date = row['date']
            
            remaining = []
            for pos in open_positions:
                if pos['exit_date'] <= signal_date:
                    cash_before_exit = cash
                    cash += pos['size'] * (1 + pos['net_return']) - commission_per_trade
                    completed_returns.append(pos['net_return'])
                    # Log exit
                    trade_log.append({
                        'action': 'EXIT',
                        'date': signal_date,
                        'ticker': pos['ticker'],
                        'exit_date': pos['exit_date'],
                        'position_size': pos['size'],
                        'cash_before_exit': cash_before_exit,
                        'cash_after_exit': cash,
                        'net_return': pos['net_return'],
                        'commission': commission_per_trade,
                        'running_equity': cash + sum(p['size'] for p in open_positions)
                    })
                else:
                    remaining.append(pos)
            open_positions = remaining
            if len(open_positions) >= max_positions or any(p['ticker'] == ticker for p in open_positions):
                skipped_capacity += 1
                continue
            # Use only available cash for position sizing (not unrealized gains)
            position_size = min(cash, cash * risk_per_trade / stop_loss_pct)
            if position_size <= 0:
                skipped_capacity += 1
                continue
            slippage = slippage_bps / 10000
            net_return = ret - 2 * (transaction_cost + slippage)
            cash_before_entry = cash
            cash -= position_size + commission_per_trade
            open_positions.append({'ticker': ticker, 'size': position_size,
                                   'net_return': net_return,
                                   'exit_date': signal_date + pd.Timedelta(days=int(row['duration_days']))})
            portfolio_value = cash + sum(p['size'] for p in open_positions)
            equity_curve.append(portfolio_value)
            # Log entry
            trade_log.append({
                'action': 'ENTRY',
                'date': signal_date,
                'ticker': ticker,
                'entry_price': ret,  # This is the realized return %, not actual price
                'position_size': position_size,
                'cash_before_entry': cash_before_entry,
                'cash_after_entry': cash,
                'slippage_bps': slippage_bps,
                'commission': commission_per_trade,
                'net_return': net_return,
                'exit_date': signal_date + pd.Timedelta(days=int(row['duration_days'])),
                'running_equity': portfolio_value
            })

        for pos in open_positions:
            cash_before_exit = cash
            cash += pos['size'] * (1 + pos['net_return']) - commission_per_trade
            completed_returns.append(pos['net_return'])
            # Log final exit for positions still open
            trade_log.append({
                'action': 'FINAL_EXIT',
                'date': pos['exit_date'],
                'ticker': pos['ticker'],
                'exit_date': pos['exit_date'],
                'position_size': pos['size'],
                'cash_before_exit': cash_before_exit,
                'cash_after_exit': cash,
                'net_return': pos['net_return'],
                'commission': commission_per_trade,
                'running_equity': cash
            })
        portfolio_value = cash
        
        # Calculate metrics
        total_return = (portfolio_value - initial_capital) / initial_capital
        num_trades = len(completed_returns)
        position_returns = np.array(completed_returns)
        win_rate = (position_returns > 0).sum() / len(position_returns)
        avg_return = position_returns.mean()
        avg_win = position_returns[position_returns > 0].mean() if (position_returns > 0).sum() > 0 else 0
        avg_loss = position_returns[position_returns < 0].mean() if (position_returns < 0).sum() > 0 else 0
        
        # Calculate max drawdown
        equity_curve = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calculate Sharpe ratio (assuming 252 trading days)
        if len(equity_curve) > 1:
            daily_returns = np.diff(equity_curve) / equity_curve[:-1]
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Profit factor
        total_wins = position_returns[position_returns > 0].sum() if (position_returns > 0).sum() > 0 else 0
        total_losses = abs(position_returns[position_returns < 0].sum()) if (position_returns < 0).sum() > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else np.inf
        
        metrics = {
            'final_value': portfolio_value,
            'total_return': total_return,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'profit_factor': profit_factor,
            'skipped_capacity': skipped_capacity,
            'trade_log': trade_log
        }
        
        # Save detailed trade log for audit
        trade_log_df = pd.DataFrame(trade_log)
        trade_log_df.to_csv('backtest_trade_log.csv', index=False)
        print(f"  Trade log saved to backtest_trade_log.csv ({len(trade_log)} entries)")
        
        # Generate summary statistics for accounting verification
        summary_stats = {
            'total_entries': len(trade_log_df[trade_log_df['action'] == 'ENTRY']),
            'total_exits': len(trade_log_df[trade_log_df['action'].isin(['EXIT', 'FINAL_EXIT'])]),
            'total_commissions': trade_log_df['commission'].sum(),
            'avg_position_size': trade_log_df[trade_log_df['action'] == 'ENTRY']['position_size'].mean(),
            'total_cash_reserved': trade_log_df[trade_log_df['action'] == 'ENTRY']['position_size'].sum(),
            'total_cash_released': trade_log_df[trade_log_df['action'].isin(['EXIT', 'FINAL_EXIT'])]['position_size'].sum(),
            'final_cash': cash,
            'accounting_check': abs(cash - (initial_capital + trade_log_df[trade_log_df['action'].isin(['EXIT', 'FINAL_EXIT'])]['position_size'].sum() * trade_log_df[trade_log_df['action'].isin(['EXIT', 'FINAL_EXIT'])]['net_return'].mean() - trade_log_df['commission'].sum()))
        }
        
        print(f"  Accounting Summary:")
        print(f"    Total Entries: {summary_stats['total_entries']}")
        print(f"    Total Exits: {summary_stats['total_exits']}")
        print(f"    Total Commissions: ${summary_stats['total_commissions']:.2f}")
        print(f"    Avg Position Size: ${summary_stats['avg_position_size']:.2f}")
        print(f"    Total Cash Reserved: ${summary_stats['total_cash_reserved']:.2f}")
        print(f"    Total Cash Released: ${summary_stats['total_cash_released']:.2f}")
        print(f"    Final Cash: ${summary_stats['final_cash']:.2f}")
        print(f"    Accounting Check: ${summary_stats['accounting_check']:.2f} (should be ~0)")
        
        # Save summary statistics
        with open('backtest_summary_stats.txt', 'w') as f:
            f.write("Backtest Summary Statistics\n")
            f.write("=" * 40 + "\n\n")
            for key, value in summary_stats.items():
                f.write(f"{key}: {value}\n")
        print(f"  Summary statistics saved to backtest_summary_stats.txt")
        
        print("  Portfolio Metrics:")
        print(f"    Final Value: ${portfolio_value:,.2f}")
        print(f"    Total Return: {total_return:.2%}")
        print(f"    Number of Trades: {num_trades}")
        print(f"    Win Rate: {win_rate:.2%}")
        print(f"    Avg Return: {avg_return:.2%}")
        print(f"    Max Drawdown: {max_drawdown:.2%}")
        print(f"    Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"    Profit Factor: {profit_factor:.2f}")
        
        return metrics
    
    def run_full_pipeline(self, target_col: str = 'hit_target', use_risk_adjusted: bool = False, compare_models_flag: bool = True):
        """
        Run complete ML pipeline with proper train/val/test split
        Uses validation set for threshold optimization to prevent leakage
        Optionally compares multiple models
        
        Args:
            target_col: Target column for prediction
            use_risk_adjusted: Use risk-adjusted target instead of hit_target
            compare_models_flag: If True, compare RF/XGBoost/LightGBM
        """
        print("=" * 60)
        print("ML Demand Zone Trading Pipeline")
        print("=" * 60)
        
        # Load and prepare
        self.load_dataset()
        self.prepare_features(target_col, create_risk_adjusted=use_risk_adjusted)
        
        # Split into train/val/test
        X_train, X_val, X_test, y_train, y_val, y_test = self.chronological_split()
        
        # Compare models and select best
        if compare_models_flag:
            comparison_df = self.compare_models(X_train, y_train, X_val, y_val)
        else:
            # Train Random Forest only
            self.train_random_forest(X_train, y_train)
        
        # Keep a fixed decision threshold while feature/target research is in
        # progress. Threshold optimization cannot repair weak ranking.
        best_threshold = 0.50
        
        # Evaluate once on the untouched test set at the validation-selected
        # threshold.  Classification and trading results remain separate.
        print("\nFinal Test Set Evaluation:")
        metrics = self.evaluate(X_test, y_test, threshold=best_threshold)
        metrics['threshold'] = best_threshold
        metrics['return_ranking'] = self.run_return_regression(X_train, X_test)

        sub_10_mask = self.dataset.loc[X_test.index, 'is_sub_10'].astype(bool)
        if sub_10_mask.any():
            print("\nSub-$10 Held-out Test Evaluation:")
            metrics['sub_10_test'] = self.evaluate(X_test.loc[sub_10_mask], y_test.loc[sub_10_mask], threshold=best_threshold)
        
        # Feature importance
        self.get_feature_importance(X_test, y_test)
        print("\nTop 10 Out-of-Sample Features:")
        print(self.feature_importance.head(10).to_string(index=False))
        self.plot_feature_importance()
        
        # Probability filtering on test set
        self.probability_based_filtering(X_test, y_test, threshold=best_threshold)
        
        # Portfolio backtest on test set
        trading_metrics = self.backtest_portfolio(X_test, y_test, threshold=best_threshold)
        metrics['trading'] = trading_metrics
        
        # Walk-forward validation with optimized threshold
        self.walk_forward_validation(n_splits=5, threshold=best_threshold)
        
        print("\n" + "=" * 60)
        print("ML Pipeline Complete")
        print("=" * 60)
        
        return metrics


def main():
    """Main execution"""
    trainer = DemandZoneMLTrainer()
    trainer.run_full_pipeline(target_col='hit_target')


if __name__ == "__main__":
    main()
