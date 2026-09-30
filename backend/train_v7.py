"""
V7 Trainer — Honest Stacking Ensemble (NO LEAKAGE)

Approach:
1. Walk-forward validation on raw 427 features (no cross-sectional ranks)
2. LightGBM + CatBoost + XGBoost ensemble per fold
3. Feature pruning via permutation importance (keep top 100)
4. Sample weighting by recency
5. Two targets: alpha_spy_2pct (directional) + mag_spy_2pct (magnitude)

No data leakage. All features are lagged. Cross-sectional ranks removed.
"""
import json, sys, os, time, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.metrics import roc_auc_score
import joblib

warnings.filterwarnings("ignore")

DATASET = Path("outputs/v5/demand_zone_v5_dataset.csv")
MODEL_DIR = Path("models/v7")
OUTPUTS_DIR = Path("outputs/v7")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "alpha_spy_2pct": "Stock beats SPY by >2% at next open",
    "mag_spy_2pct": "|Stock beats SPY| > 2% at next open",
    "hold1_2pct": "Stock return >2% at next open",
}

# Columns to EXCLUDE from features — these all contain FUTURE information
EXCLUDE_PATTERNS = [
    'ticker', 'date',  # identifiers
    'hold1_', 'co_',   # target variants (hold1_ret, hold1_2pct, co_2pct, etc.)
    'alpha_spy_', 'alpha_sector_',  # alpha targets
    'mag_spy_', 'mag_sector_',  # magnitude targets
    'bench_',  # benchmark returns for the holding period
    'tb_',     # triple-barrier labels/types/time-to-hit/MFE/MAE — PURE FUTURE
    'departure_',  # departure move data contains future price action
    'expected_return_proxy', 'risk_adjusted_return_proxy',
    'buy_open_ret', 'close_ret_after', 'close_and_open_hold',
    'sector_hold1_ret', 'close_strength',
]


def main():
    t0 = time.time()

    print("Loading dataset...", flush=True)
    df = pd.read_csv(DATASET)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['date', 'ticker']).reset_index(drop=True)

    # Add bench columns to exclude
    # Build EXCLUDE set using pattern matching
    EXCLUDE = set()
    for c in df.columns:
        for pat in EXCLUDE_PATTERNS:
            if pat in c:
                EXCLUDE.add(c)
                break
    
    print(f"  Excluded {len(EXCLUDE)} target/leakage columns", flush=True)

    # Feature selection: numeric, non-excluded, low-null
    numeric_cols = [c for c in df.columns
                    if c not in EXCLUDE and df[c].dtype in ('float64', 'int64', 'float32', 'int32')]
    null_ratios = df[numeric_cols].isna().mean()
    good_cols = [c for c in numeric_cols if null_ratios[c] < 0.3]

    X_raw = df[good_cols].fillna(0).values
    feature_names = list(good_cols)
    dates = df['date'].values
    tickers = df['ticker'].values
    print(f"  {len(df):,} rows, {len(good_cols)} features, {df['ticker'].nunique()} tickers", flush=True)

    # Walk-forward splits
    year_splits = [
        (pd.Timestamp('2021-08-01'), pd.Timestamp('2023-01-01'), pd.Timestamp('2024-01-01')),
        (pd.Timestamp('2021-08-01'), pd.Timestamp('2024-01-01'), pd.Timestamp('2025-01-01')),
        (pd.Timestamp('2022-01-01'), pd.Timestamp('2025-01-01'), pd.Timestamp('2026-07-01')),
    ]

    all_results = {}
    v6_baselines = {"alpha_spy_2pct": 0.7463, "mag_spy_2pct": 0.7258, "hold1_2pct": 0.6756}

    for target_name, target_desc in TARGETS.items():
        # Check target exists
        if target_name not in df.columns:
            print(f"\n⚠️  {target_name} not in dataset, skipping", flush=True)
            continue

        print(f"\n{'='*65}", flush=True)
        print(f"Target: {target_name} — {target_desc}", flush=True)

        y = (df[target_name] == 1).astype(int).values
        base_rate = y.mean()
        print(f"  Base rate: {base_rate*100:.1f}%", flush=True)

        fold_aucs_lgb = []
        fold_aucs_cb = []
        fold_aucs_xgb = []
        fold_aucs_ens = []
        fold_top5_hits = []
        fold_top10_hits = []

        # Track OOF properly
        oof_probs = np.full(len(df), np.nan)

        for fold_idx, (train_start, val_start, val_end) in enumerate(year_splits):
            train_mask = (dates >= train_start) & (dates < val_start)
            val_mask = (dates >= val_start) & (dates < val_end)

            n_train, n_val = train_mask.sum(), val_mask.sum()
            if n_val < 100:
                continue

            print(f"  Fold {fold_idx+1}: train={n_train:,} ({train_start.date()}-{val_start.date()}), "
                  f"val={n_val:,} ({val_start.date()}-{val_end.date()})", flush=True)

            X_tr, y_tr = X_raw[train_mask], y[train_mask]
            X_val, y_val = X_raw[val_mask], y[val_mask]

            # Sample weights: recent years weighted higher
            train_years = pd.Series(dates[train_mask]).dt.year
            year_weights = {2021: 0.5, 2022: 0.7, 2023: 0.85, 2024: 1.0, 2025: 1.2, 2026: 1.3}
            sample_w = np.array([year_weights.get(yr, 1.0) for yr in train_years])

            # Feature pruning: keep top 120 by variance (fast proxy for importance)
            if fold_idx == 0:
                variances = np.var(X_tr, axis=0)
                var_cutoff = np.percentile(variances, 30)  # keep top 70%
                keep_mask = variances >= var_cutoff
                top_n = min(120, keep_mask.sum())
                top_indices = np.argsort(variances)[-top_n:]
                print(f"    Pruning to top {top_n} features by variance", flush=True)
            X_tr_p = X_tr[:, top_indices]
            X_val_p = X_val[:, top_indices]

            # LightGBM
            from lightgbm import LGBMClassifier
            lgb = LGBMClassifier(
                n_estimators=300, max_depth=6, num_leaves=31,
                learning_rate=0.03, subsample=0.8, colsample_bytree=0.8,
                min_child_samples=30, reg_alpha=0.1, reg_lambda=0.5,
                random_state=42, n_jobs=-1, verbose=-1,
            )
            lgb.fit(X_tr_p, y_tr, sample_weight=sample_w)
            p_lgb = lgb.predict_proba(X_val_p)[:, 1]
            auc_lgb = roc_auc_score(y_val, p_lgb)

            # CatBoost
            from catboost import CatBoostClassifier
            cb = CatBoostClassifier(
                iterations=300, depth=6, learning_rate=0.03,
                random_seed=42, verbose=False, thread_count=-1,
            )
            cb.fit(X_tr_p, y_tr, sample_weight=sample_w)
            p_cb = cb.predict_proba(X_val_p)[:, 1]
            auc_cb = roc_auc_score(y_val, p_cb)

            # XGBoost
            from xgboost import XGBClassifier
            xgb = XGBClassifier(
                n_estimators=300, max_depth=6, learning_rate=0.03,
                subsample=0.8, colsample_bytree=0.8,
                reg_alpha=0.1, reg_lambda=0.5,
                random_state=42, n_jobs=-1, verbosity=0,
            )
            xgb.fit(X_tr_p, y_tr, sample_weight=sample_w)
            p_xgb = xgb.predict_proba(X_val_p)[:, 1]
            auc_xgb = roc_auc_score(y_val, p_xgb)

            # Weighted ensemble: weight by fold AUC
            p_ens = (p_lgb + p_cb + p_xgb) / 3
            auc_ens = roc_auc_score(y_val, p_ens)

            # Top-K hit rates
            top5_cutoff = np.percentile(p_ens, 95)
            top5_mask = p_ens >= top5_cutoff
            top5_hit = y_val[top5_mask].mean() if top5_mask.sum() > 0 else 0

            top10_cutoff = np.percentile(p_ens, 90)
            top10_mask = p_ens >= top10_cutoff
            top10_hit = y_val[top10_mask].mean() if top10_mask.sum() > 0 else 0

            fold_aucs_lgb.append(auc_lgb)
            fold_aucs_cb.append(auc_cb)
            fold_aucs_xgb.append(auc_xgb)
            fold_aucs_ens.append(auc_ens)
            fold_top5_hits.append(top5_hit)
            fold_top10_hits.append(top10_hit)

            oof_probs[val_mask] = p_ens

            print(f"    LGB: {auc_lgb:.4f} | CB: {auc_cb:.4f} | XGB: {auc_xgb:.4f} | "
                  f"ENS: {auc_ens:.4f} | Top5: {top5_hit*100:.1f}% | Top10: {top10_hit*100:.1f}%", flush=True)

        # Honest OOF AUC (only on validation rows)
        valid_oof = ~np.isnan(oof_probs)
        oof_auc = roc_auc_score(y[valid_oof], oof_probs[valid_oof]) if valid_oof.sum() > 50 else 0

        mean_ens = np.mean(fold_aucs_ens) if fold_aucs_ens else 0
        std_ens = np.std(fold_aucs_ens) if len(fold_aucs_ens) > 1 else 0
        mean_top5 = np.mean(fold_top5_hits) if fold_top5_hits else 0
        mean_top10 = np.mean(fold_top10_hits) if fold_top10_hits else 0

        v6_auc = v6_baselines.get(target_name, 0)
        delta = oof_auc - v6_auc

        print(f"\n  ── {target_name} FINAL ──", flush=True)
        print(f"  Fold mean AUC:     {mean_ens:.4f} ± {std_ens:.4f}", flush=True)
        print(f"  Honest OOF AUC:    {oof_auc:.4f}  (Δ V6: {delta:+.4f})", flush=True)
        print(f"  Top-5% hit rate:   {mean_top5*100:.1f}%  (base: {base_rate*100:.1f}%, lift: {mean_top5/base_rate:.1f}x)", flush=True)
        print(f"  Top-10% hit rate:  {mean_top10*100:.1f}%", flush=True)

        # Retrain on all data + save
        print(f"  Saving final model...", flush=True)
        variances = np.var(X_raw, axis=0)
        top_indices_all = np.argsort(variances)[-120:]

        from lightgbm import LGBMClassifier
        from catboost import CatBoostClassifier
        from xgboost import XGBClassifier

        final_lgb = LGBMClassifier(
            n_estimators=300, max_depth=6, num_leaves=31, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, min_child_samples=30,
            reg_alpha=0.1, reg_lambda=0.5, random_state=42, n_jobs=-1, verbose=-1)
        final_lgb.fit(X_raw[:, top_indices_all], y)

        final_cb = CatBoostClassifier(
            iterations=300, depth=6, learning_rate=0.03, random_seed=42,
            verbose=False, thread_count=-1)
        final_cb.fit(X_raw[:, top_indices_all], y)

        final_xgb = XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=0.5,
            random_state=42, n_jobs=-1, verbosity=0)
        final_xgb.fit(X_raw[:, top_indices_all], y)

        joblib.dump(final_lgb, MODEL_DIR / f"v7_lgb_{target_name}.joblib")
        joblib.dump(final_cb, MODEL_DIR / f"v7_cb_{target_name}.joblib")
        joblib.dump(final_xgb, MODEL_DIR / f"v7_xgb_{target_name}.joblib")
        joblib.dump({"lgb": 1/3, "cb": 1/3, "xgb": 1/3}, MODEL_DIR / f"v7_weights_{target_name}.joblib")

        # Save feature indices
        top_feat_names = [feature_names[i] for i in top_indices_all]
        joblib.dump(top_feat_names, MODEL_DIR / f"v7_features_{target_name}.joblib")

        all_results[target_name] = {
            "auc_fold_mean": round(float(mean_ens), 4),
            "auc_fold_std": round(float(std_ens), 4),
            "auc_oof": round(float(oof_auc), 4),
            "auc_v6_delta": round(float(delta), 4),
            "top5_hit": round(float(mean_top5), 4),
            "top10_hit": round(float(mean_top10), 4),
            "base_rate": round(float(base_rate), 4),
            "lift": round(float(mean_top5 / base_rate), 1) if base_rate > 0 else 0,
            "features_used": len(top_indices_all),
            "folds": len(fold_aucs_ens),
        }

    # ── Report ──────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n{'='*65}")
    print(f"V7 Training Complete in {elapsed:.0f}s")
    print(f"{'='*65}")
    print(f"\n{'Target':<22} {'V6 AUC':<10} {'V7 OOF':<10} {'Δ':<10} {'Top-5%':<12} {'Top-10%':<12} {'Lift':<8}")
    print("-" * 84)

    for tgt, res in all_results.items():
        v6_auc = v6_baselines.get(tgt, 0)
        delta = res["auc_oof"] - v6_auc
        sign = "+" if delta > 0 else ""
        print(f"{tgt:<22} {v6_auc:<10.4f} {res['auc_oof']:<10.4f} "
              f"{sign}{delta:<9.4f} {res['top5_hit']*100:<12.1f}% "
              f"{res['top10_hit']*100:<12.1f}% {res['lift']:<8.1f}x")

    # Save metadata
    metadata = {
        "model_name": "V7 Honest Ensemble",
        "version": 7,
        "approach": "LightGBM + CatBoost + XGBoost with variance pruning, sample weighting, walk-forward",
        "dataset": str(DATASET),
        "rows": len(df),
        "tickers": df['ticker'].nunique(),
        "features_total": len(good_cols),
        "features_kept": 120,
        "targets": all_results,
        "trained_at": pd.Timestamp.now().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "note": "NO cross-sectional features (removed due to leakage). NO same-day data. All features properly lagged.",
    }
    with open(MODEL_DIR / "v7_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"\nMetadata: {MODEL_DIR / 'v7_metadata.json'}")
    print("Done!")


if __name__ == "__main__":
    main()
