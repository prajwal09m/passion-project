"""
Model training and serialization script.
Trains a model on the existing ML dataset and saves it for API serving.

Usage: python backend/train_model.py
"""

import sys
import os
from pathlib import Path

_PARENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARENT / "Python"))

import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")


MODEL_DIR = _PARENT / "models"
MODEL_DIR.mkdir(exist_ok=True)

# Possible dataset paths (tried in order)
DATASET_PATHS = [
    _PARENT / "outputs" / "v10" / "demand_zone_ml_dataset_v10.csv",
    _PARENT / "Other" / "demand_zone_ml_dataset.csv",
    _PARENT / "outputs" / "v10" / "demand_zone_ml_dataset_v10.csv",
]


def find_dataset() -> Path | None:
    """Find the dataset CSV file."""
    for p in DATASET_PATHS:
        if p.exists():
            return p
    return None


def train_model():
    """Train a LightGBM model and save it."""
    dataset_path = find_dataset()

    if dataset_path is None:
        print("[train] No dataset found. Creating a minimal model from synthetic data.")
        return create_minimal_model()

    print(f"[train] Loading dataset from {dataset_path}")
    df = pd.read_csv(dataset_path)
    print(f"[train] Loaded {len(df)} rows, {len(df.columns)} columns")

    # Identify target column
    if "hit_target" in df.columns:
        target_col = "hit_target"
    elif "target" in df.columns:
        target_col = "target"
    else:
        print("[train] No target column found, creating minimal model.")
        return create_minimal_model()

    # Exclude non-feature columns
    exclude = ["ticker", "Ticker", "date", "Date", "exit_reason", "exit_date",
               "hit_target", "hit_stop", "final_return_pct", "forward_return_5d",
               "forward_return_20d", "max_return_20d", "days_until_target",
               "hit_target_10_5", "risk_adjusted_success", "mfe_pct", "mae_pct",
               "entry_price", "zone_price", "realized_return_pct", "trade_duration_days",
               "is_sub_10", "target"]

    feature_cols = [c for c in df.columns if c not in exclude]
    feature_cols = [c for c in feature_cols if df[c].dtype in ("float64", "int64", "float32", "int32")]

    if len(feature_cols) < 5:
        print(f"[train] Only {len(feature_cols)} numeric features. Creating minimal model.")
        return create_minimal_model()

    X = df[feature_cols].copy()
    y = df[target_col].copy()

    # Handle missing values
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median())

    # Handle class imbalance
    pos_count = int(y.sum())
    neg_count = int(len(y) - pos_count)
    scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0
    print(f"[train] Target distribution: {neg_count} negative, {pos_count} positive")
    print(f"[train] Scale pos weight: {scale_pos_weight:.2f}")

    # Train LightGBM
    try:
        import lightgbm as lgb
        model = lgb.LGBMClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )

        # Chronological split: last 15% for test
        split = int(len(X) * 0.85)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        model.fit(X_train, y_train)
        print("[train] LightGBM model trained successfully")

        # Evaluate
        from sklearn.metrics import roc_auc_score, precision_score, recall_score
        if len(X_test) > 0:
            proba = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, proba)
            pred = (proba >= 0.5).astype(int)
            prec = precision_score(y_test, pred, zero_division=0)
            rec = recall_score(y_test, pred, zero_division=0)
            print(f"[train] Test AUC: {auc:.4f}, Precision: {prec:.4f}, Recall: {rec:.4f}")

        # Permutation importance
        try:
            from sklearn.inspection import permutation_importance
            pi = permutation_importance(model, X_test, y_test, n_repeats=5,
                                        random_state=42, n_jobs=-1, scoring="roc_auc")
            importance_df = pd.DataFrame({
                "feature": feature_cols,
                "importance": pi.importances_mean,
            }).sort_values("importance", ascending=False)

            # Normalize to 0..1
            max_imp = importance_df["importance"].max() or 1.0
            importance_df["contribution"] = importance_df["importance"] / max_imp
            top = importance_df.head(10)
            print("[train] Top 5 features:")
            for _, row in top.head(5).iterrows():
                print(f"  {row['feature']}: {row['importance']:.4f}")
        except Exception as e:
            print(f"[train] Permutation importance failed: {e}")
            top = pd.DataFrame({"feature": feature_cols[:10], "contribution": [0.1] * 10})

        label = "LightGBM v8"
    except ImportError:
        # Fallback to Random Forest
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(
            n_estimators=100, max_depth=10, min_samples_split=20,
            min_samples_leaf=10, class_weight="balanced", random_state=42, n_jobs=-1,
        )
        model.fit(X, y)
        print("[train] Random Forest model trained (LightGBM not available)")

        top = pd.DataFrame({"feature": feature_cols[:10], "contribution": [0.1] * 10})
        label = "Random Forest v8"

    # Save model
    model_path = MODEL_DIR / "lightgbm.joblib"
    joblib.dump(model, model_path)
    print(f"[train] Model saved to {model_path}")

    # Save feature importance
    fi_data = []
    for _, row in top.iterrows():
        fi_data.append({
            "name": str(row["feature"]).replace("_", " ").title(),
            "contribution": float(row["contribution"]),
            "description": f"Feature: {row['feature']}",
        })

    with open(MODEL_DIR / "feature_importance.json", "w") as f:
        json.dump(fi_data, f, indent=2)

    # Save metadata
    metadata = {
        "model_name": label,
        "trained_at": datetime.now().isoformat(),
        "features_count": len(feature_cols),
        "dataset_rows": len(df),
        "features": feature_cols,
        "target_distribution": {"negative": int(neg_count), "positive": int(pos_count)},
    }
    with open(MODEL_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("[train] Training complete!")
    return True


def create_minimal_model():
    """Create a minimal sklearn model for fallback serving."""
    from sklearn.ensemble import RandomForestClassifier
    import numpy as np

    # Train on synthetic data
    X = np.random.randn(1000, 10)
    y = (X[:, 0] + X[:, 1] - X[:, 2] + np.random.randn(1000) * 0.5 > 0).astype(int)

    model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X, y)

    model_path = MODEL_DIR / "lightgbm.joblib"
    joblib.dump(model, model_path)
    print(f"[train] Minimal fallback model saved to {model_path}")

    metadata = {
        "model_name": "Random Forest (minimal fallback)",
        "trained_at": datetime.now().isoformat(),
        "features_count": 10,
        "note": "Trained on synthetic data. Retrain with real dataset for production use.",
    }
    with open(MODEL_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return True


if __name__ == "__main__":
    train_model()
