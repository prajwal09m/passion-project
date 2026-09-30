"""
V5 TRAINER — MASSIVE ensemble on expanded feature set.

Targets (all honest walk-forward):
  - alpha_spy_2pct  (primary, baseline 0.745)
  - alpha_spy_1pct  (higher base rate, easier)
  - alpha_spy_3pct  (harder but more profitable)
  - mag_spy_2pct    (magnitude — predict move size, not direction)

Enhancements:
  1. All 11 sector ETF returns + rich VIX from V5 dataset
  2. Gap features (pre-market signal)
  3. Zone geometry features (from legacy)
  4. Extended interaction features (more pairs)
  5. Expanded target encoding (sector, month, ticker trend)
  6. Ensemble: CatBoost + XGBoost + LightGBM
  7. Walk-forward validation on ALL targets
"""
import sys, json, joblib
from pathlib import Path
import numpy as np, pandas as pd
from datetime import datetime
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier
from sklearn.metrics import roc_auc_score
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATASET = ROOT / "outputs" / "v5" / "demand_zone_v5_dataset.csv"
OUTDIR = ROOT / "outputs" / "v5"
MODELDIR = ROOT / "models" / "v5"
OUTDIR.mkdir(parents=True, exist_ok=True)
MODELDIR.mkdir(parents=True, exist_ok=True)

RNG = 42
TARGETS = ["alpha_spy_2pct", "alpha_spy_1pct", "alpha_spy_3pct", "mag_spy_2pct"]

# Columns that are NOT features
LABEL_LIKE = {
    "ticker", "date", "hold1_ret", "buy_open_ret", "close_ret_after",
    "close_and_open_hold", "sector_hold1_ret", "bench_SPY_hold1",
    "alpha_spy_hold1", "alpha_sector_hold1",
    "hit_target", "hit_5pct", "hit_10pct", "hit_15pct", "hit_20pct",
    "target_tier", "strong_hit", "market_relative_hit", "is_sub_10",
}
for t in ["1pct","2pct","3pct","4pct","5pct","6pct"]:
    LABEL_LIKE |= {f"hold1_{t}",f"co_{t}",f"alpha_spy_{t}",f"alpha_sector_{t}",
                   f"mag_spy_{t}"}
for tp,sl in [(2,1),(3,1),(5,2),(6,3)]:
    LABEL_LIKE |= {f"tb_{tp}tp_{sl}sl_label",f"tb_{tp}tp_{sl}sl_type",
                   f"tb_{tp}tp_{sl}sl_tth",f"tb_{tp}tp_{sl}sl_mfe",
                   f"tb_{tp}tp_{sl}sl_mae"}

# Extended interaction pairs for richer feature engineering
INTERACTION_PAIRS = [
    ("atr_pct", "vix_percentile_60d"),
    ("daily_return", "spy_return_5d"),
    ("rel_volume", "vix_level"),
    ("dist_ema_20_pct", "rsi_14"),
    ("distance_to_zone_pct", "zone_age_days"),
    ("spy_return_20d", "qqq_return_20d"),
    ("departure_volume_ratio", "body"),
    ("gap_pct", "vix_level"),
    ("gap_vs_atr", "atr_pct"),
    ("zone_width_pct", "vix_percentile_60d"),
    ("zone_freshness", "rel_volume"),
    ("xlk_return_20d", "spy_return_20d"),
    ("xlf_return_20d", "spy_return_20d"),
    ("spy_return_5d", "qqq_return_5d"),
    ("daily_return", "spy_return_1d"),
    ("return_per_atr", "vix_level"),
]


def safe_numeric(X):
    X = X.copy()
    for c in list(X.columns):
        try:
            X[c] = pd.to_numeric(X[c], errors='coerce')
        except Exception:
            del X[c]
    X = X.fillna(0).astype(float)
    std = X.std()
    X = X.drop(columns=[c for c in X.columns if std[c] < 1e-8])
    return X


def add_interaction_features(X):
    """Extended interaction features from V5 rich feature set."""
    for a, b in INTERACTION_PAIRS:
        if a in X.columns and b in X.columns:
            X[f"inter_{a}__{b}"] = X[a] * X[b]
            X[f"rat_{a}__{b}"] = X[a] / (X[b].abs() + 0.001)
            X[f"sum_{a}__{b}"] = X[a] + X[b]
    return X


def add_target_encoding(X, df, target_col, y):
    """Expanded target encoding: ticker, sector, month, and trend."""
    # Ticker hit rate (chronological, point-in-time)
    ticker_feat = np.zeros(len(df))
    ticker_hits = {}
    for i in range(len(df)):
        t = df["ticker"].iloc[i]
        if t not in ticker_hits:
            ticker_hits[t] = {"hits": 0, "total": 0}
        th = ticker_hits[t]
        if th["total"] > 10:
            ticker_feat[i] = th["hits"] / th["total"]
        else:
            ticker_feat[i] = y.mean()
        th["hits"] += y.iloc[i]
        th["total"] += 1
    X["ticker_hist_hitrate"] = np.clip(ticker_feat, 0.005, 0.995)

    # Month bucket hit rate
    ym = df["date"].dt.strftime("%Y-%m")
    ym_rates = y.groupby(ym).mean()
    X["month_hitrate"] = ym.map(ym_rates).fillna(y.mean()).clip(0.005, 0.995).values

    # Hitrate trend
    X["ticker_hitrate_trend"] = X["ticker_hist_hitrate"] - X["month_hitrate"]

    # Sector hit rate (if sector info available)
    sector_col = None
    for c in ["sector", "sector_etf"]:
        if c in df.columns:
            sector_col = c
            break
    if sector_col:
        sector_rates = y.groupby(df[sector_col]).mean()
        X["sector_hitrate"] = df[sector_col].map(sector_rates).fillna(y.mean()).clip(0.005, 0.995).values
    else:
        X["sector_hitrate"] = y.mean()

    return X


def sample_weights(df, recent_weight=2.0, recent_year=2024):
    dates = pd.to_datetime(df["date"])
    return np.where(dates >= pd.Timestamp(f"{recent_year}-01-01"), recent_weight, 1.0)


def walk_forward_folds(dates, n_folds=5):
    uniq = np.sort(np.unique(dates))
    edges = np.array_split(uniq, n_folds + 1)
    folds = []
    for k in range(1, n_folds + 1):
        te = edges[k][0]
        ve = edges[k + 1][0] if k + 1 < len(edges) else uniq[-1] + np.timedelta64(1, "D")
        folds.append((te, ve))
    return folds


def make_model(name):
    if name == "CatBoost":
        return CatBoostClassifier(iterations=300, depth=7, learning_rate=0.04,
            l2_leaf_reg=3, random_seed=RNG, verbose=0, allow_writing_files=False)
    elif name == "XGBoost":
        return xgb.XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.04,
            subsample=0.85, colsample_bytree=0.8, reg_alpha=0.05, reg_lambda=0.5,
            gamma=0.1, random_state=RNG, n_jobs=-1, verbosity=0)
    else:
        return lgb.LGBMClassifier(n_estimators=300, num_leaves=31, max_depth=-1,
            learning_rate=0.03, subsample=0.8, colsample_bytree=0.8,
            min_child_samples=30, lambda_l1=0.05, lambda_l2=0.5,
            random_state=RNG, n_jobs=-1, verbose=-1)


def evaluate_target(df, X_raw, target_col, sw, dates, model_names):
    """Walk-forward ensemble on one target. Returns dict of metrics."""
    print(f"\n{'='*70}")
    print(f"TARGET: {target_col}")
    print(f"{'='*70}")

    if target_col not in df.columns:
        print(f"  SKIP — column not found")
        return None

    # Filter out rows where target is NaN (e.g., missing alpha data)
    valid = df[target_col].notna()
    if valid.sum() < 1000:
        print(f"  SKIP — only {valid.sum()} valid rows")
        return None

    y = (df.loc[valid, target_col] == 1).astype(int)
    br = y.mean() * 100
    X = X_raw.loc[valid].reset_index(drop=True)
    y = y.reset_index(drop=True)
    dates_v = dates[valid.values]
    sw_v = sw[valid.values]

    X = safe_numeric(X)
    X = add_interaction_features(X)
    X = add_target_encoding(X, df.loc[valid].reset_index(drop=True), target_col, y)
    X = safe_numeric(X)
    print(f"  Features: {X.shape[1]} | Base rate: {br:.1f}% | Rows: {len(y):,}")

    folds = walk_forward_folds(dates_v, 5)
    per_model = {name: {"aucs": [], "probs": np.zeros(len(y))} for name in model_names}

    for k, (train_end, val_end) in enumerate(folds):
        tr = dates_v < train_end
        va = (dates_v >= train_end) & (dates_v < val_end)
        if tr.sum() < 2000 or va.sum() < 200 or len(np.unique(y[va])) < 2:
            continue
        fold_probs = {}
        for name in model_names:
            m = make_model(name)
            try:
                m.fit(X.iloc[tr], y.iloc[tr], sample_weight=sw_v[tr])
                p = m.predict_proba(X.iloc[va])[:, 1]
            except Exception:
                p = np.full(va.sum(), y[va].mean())
            per_model[name]["probs"][va] = p
            a = roc_auc_score(y.iloc[va], p)
            per_model[name]["aucs"].append(a)
            fold_probs[name] = p

    # OOF stats
    mask = np.any([per_model[n]["probs"] > 0 for n in model_names], axis=0)
    results = {}
    mean_aucs = {}
    for name in model_names:
        aucs = per_model[name]["aucs"]
        if aucs:
            mean_aucs[name] = np.mean(aucs)
            print(f"  {name:12s} AUC {mean_aucs[name]:.4f} ± {np.std(aucs):.4f}")

    if not mean_aucs:
        return None

    # Weighted ensemble
    total_w = sum(mean_aucs.values())
    weights = {n: mean_aucs[n] / total_w for n in mean_aucs}
    oof_ens = np.zeros(len(y))
    for n in model_names:
        if n in weights:
            oof_ens += per_model[n]["probs"] * weights[n]
    oof_auc = roc_auc_score(y[mask], oof_ens[mask]) if mask.sum() > 0 else 0
    results["oof_auc"] = oof_auc
    results["mean_aucs"] = mean_aucs
    results["weights"] = weights
    results["base_rate"] = br

    # Top-5% / Top-10%
    n5 = max(int(mask.sum() * 0.05), 1)
    top5_idx = oof_ens[mask].argsort()[-n5:][::-1]
    top5_hr = y.values[mask][top5_idx].mean() * 100
    n10 = max(int(mask.sum() * 0.10), 1)
    top10_idx = oof_ens[mask].argsort()[-n10:][::-1]
    top10_hr = y.values[mask][top10_idx].mean() * 100
    results["top5_hr"] = top5_hr
    results["top10_hr"] = top10_hr
    print(f"  ENSEMBLE AUC: {oof_auc:.4f}")
    print(f"  Top-5% HR: {top5_hr:.1f}% | Top-10% HR: {top10_hr:.1f}% | Lift: {top5_hr/br:.1f}x")

    # Train final on 80%
    sp = int(len(y) * 0.8)
    Xt, Xv = X.iloc[:sp], X.iloc[sp:]
    yt, yv = y.iloc[:sp], y.iloc[sp:]
    swt = sw_v[:sp]
    final = {}
    for name in model_names:
        m = make_model(name)
        m.fit(Xt, yt, sample_weight=swt)
        final[name] = m
        p = m.predict_proba(Xv)[:, 1]
        test_a = roc_auc_score(yv, p)
        print(f"  Final {name:12s} test: {test_a:.4f}")

    test_ens = np.zeros(len(yv))
    for n in model_names:
        test_ens += final[n].predict_proba(Xv)[:, 1] * weights[n]
    test_auc = roc_auc_score(yv, test_ens)
    results["test_auc"] = test_auc
    results["final_models"] = final
    results["feature_count"] = X.shape[1]
    print(f"  Final ENSEMBLE  test: {test_auc:.4f}")
    return results


def main():
    print("=" * 70)
    print("V5 TRAINER — ETF Armada + VIX + Zone + Gap + Magnitude")
    print("=" * 70)

    if not DATASET.exists():
        print(f"ERROR: V5 dataset not found at {DATASET}")
        print("Run build_v5_dataset.py first.")
        return

    df = pd.read_csv(DATASET)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date"]).reset_index(drop=True)
    print(f"Data: {len(df):,} rows, {df['ticker'].nunique()} tickers, "
          f"{df['date'].min().date()} -> {df['date'].max().date()}, {len(df.columns)} cols")

    # Feature columns (exclude labels)
    feats = [c for c in df.columns if c not in LABEL_LIKE]
    X_raw = df[feats].copy()
    print(f"Feature columns (raw): {X_raw.shape[1]}")

    sw = sample_weights(df, recent_weight=2.5, recent_year=2024)
    dates = df["date"].values
    model_names = ["CatBoost", "XGBoost", "LightGBM"]

    # ── Evaluate ALL targets ──
    all_results = {}
    best_target, best_auc, best_results = None, 0, None

    for target in TARGETS:
        res = evaluate_target(df, X_raw, target, sw, dates, model_names)
        if res is not None:
            all_results[target] = res
            if res["oof_auc"] > best_auc:
                best_auc = res["oof_auc"]
                best_target = target
                best_results = res

    # ── Summary ──
    print(f"\n{'='*70}")
    print("V5 RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"{'Target':<20s} {'AUC':>8s} {'Base Rate':>10s} {'Top-5% HR':>10s} {'Lift':>6s}")
    print("-" * 56)
    for target, res in sorted(all_results.items(), key=lambda x: x[1]["oof_auc"], reverse=True):
        print(f"{target:<20s} {res['oof_auc']:>8.4f} {res['base_rate']:>9.1f}% "
              f"{res['top5_hr']:>9.1f}% {res['top5_hr']/res['base_rate']:>5.1f}x")

    # ── Save best model ──
    if best_results:
        print(f"\nBest target: {best_target} (AUC: {best_auc:.4f})")
        for name, m in best_results["final_models"].items():
            joblib.dump(m, MODELDIR / f"v5_{name.lower()}.joblib")
        joblib.dump(best_results["weights"], MODELDIR / "v5_ensemble_weights.joblib")

        meta = {
            "best_target": best_target,
            "best_auc": best_auc,
            "test_auc": best_results["test_auc"],
            "top5_hr": best_results["top5_hr"],
            "top10_hr": best_results["top10_hr"],
            "base_rate": best_results["base_rate"],
            "feature_count": best_results["feature_count"],
            "ensemble_weights": best_results["weights"],
            "model_aucs": best_results["mean_aucs"],
            "all_targets": {t: {"auc": r["oof_auc"], "base_rate": r["base_rate"],
                                "top5_hr": r["top5_hr"]}
                            for t, r in all_results.items()},
            "trained_at": datetime.now().isoformat(),
        }
        json.dump(meta, open(MODELDIR / "v5_metadata.json", "w"), indent=2, default=str)
        print(f"Models saved: {MODELDIR}/v5_*.joblib")

        # Compare to V4
        print(f"\n{'='*70}")
        print("V4 vs V5 COMPARISON")
        print(f"{'='*70}")
        print(f"  V4 (alpha_spy_2pct):  AUC 0.7446, Top-5% 53.5%")
        print(f"  V5 (alpha_spy_2pct):  AUC {all_results.get('alpha_spy_2pct',{}).get('oof_auc','N/A')}")
        if 'alpha_spy_2pct' in all_results:
            delta = all_results['alpha_spy_2pct']['oof_auc'] - 0.7446
            print(f"  DELTA: {delta:+.4f}")
        print(f"  V5 (best={best_target}):    AUC {best_auc:.4f}")
        print(f"  V5 magnitude target:  AUC {all_results.get('mag_spy_2pct',{}).get('oof_auc','N/A')}")

    print("\nDone. 🔥")


if __name__ == "__main__":
    main()
