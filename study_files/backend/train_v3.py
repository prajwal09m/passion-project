"""
V3 MODEL TRAINER — measures AUC gains from three improvements:
  1. Easier target: alpha_spy > 1% (32.3% base rate vs 16.4% hold1>2%)
  2. Gap/intraday features: open drive, gap direction, gap filled, etc.
  3. More data: 418 tickers (up from 149)

Lean CatBoost benchmark — walk-forward, compare V2→V3 AUC.
"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
from datetime import datetime
import lightgbm as lgb
from catboost import CatBoostClassifier
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATASET = ROOT / "outputs" / "v3" / "demand_zone_v3_dataset.csv"
OUTDIR = ROOT / "outputs" / "v3"
MODELDIR = ROOT / "models" / "v3"
MODELDIR.mkdir(parents=True, exist_ok=True)

RNG = 42
N_EST = 200
MAX_FEAT = 100

TARGET_LIKE = [
    "ticker", "date", "hold1_ret", "buy_open_ret", "close_ret_after",
    "close_and_open_hold", "sector_hold1_ret", "bench_SPY_hold1",
    "alpha_spy_ret", "alpha_sector_ret", "alpha_spy_hold1", "alpha_sector_hold1",
    "hit_target", "hit_5pct", "hit_10pct", "hit_15pct", "hit_20pct",
    "target_tier", "strong_hit", "market_relative_hit", "is_sub_10",
]
for t in ["1pct", "2pct", "3pct", "4pct", "5pct", "6pct"]:
    TARGET_LIKE += [f"hold1_{t}", f"co_{t}", f"alpha_spy_{t}", f"alpha_sector_{t}"]
for tp, sl in [(2, 1), (3, 1), (5, 2), (6, 3)]:
    TARGET_LIKE += [f"tb_{tp}tp_{sl}sl_label", f"tb_{tp}tp_{sl}sl_type",
                    f"tb_{tp}tp_{sl}sl_tth", f"tb_{tp}tp_{sl}sl_mfe",
                    f"tb_{tp}tp_{sl}sl_mae"]

TARGETS = {
    "hold1_2pct": "Hold1 > 2% (open-open, baseline)",
    "alpha_spy_1pct": "Alpha SPY > 1% (stock beats SPY by 1%, easier target)",
    "alpha_spy_2pct": "Alpha SPY > 2%",
    "alpha_sector_1pct": "Alpha Sector > 1%",
}


def walk_forward_auc(model_fn, X, y, dates, n_folds=5):
    aucs = []; n = len(X)
    uniq = np.sort(np.unique(dates))
    edges = np.array_split(uniq, n_folds + 1)
    for k in range(1, n_folds + 1):
        train_end = edges[k][0]
        val_end = edges[k + 1][0] if k + 1 < len(edges) else uniq[-1] + np.timedelta64(1, "D")
        tr, va = dates < train_end, (dates >= train_end) & (dates < val_end)
        if tr.sum() < 2000 or va.sum() < 200 or len(np.unique(y[va])) < 2:
            continue
        m = model_fn(X.iloc[tr], y.iloc[tr])
        p = m.predict_proba(X.iloc[va])[:, 1]
        aucs.append(roc_auc_score(y.iloc[va], p))
    return aucs


def main():
    print("=" * 70)
    print("V3 MODEL BENCHMARK — Alpha targets + Gap features + 418 tickers")
    print("=" * 70)
    df = pd.read_csv(DATASET)
    df["date"] = pd.to_datetime(df["date"], format='mixed')
    df = df.sort_values(["date"]).reset_index(drop=True)
    print(f"Dataset: {len(df):,} rows, {df['ticker'].nunique()} tickers, "
          f"{len(df.columns)} cols")
    print(f"Date range: {df['date'].min().date()} → {df['date'].max().date()}")

    # Features — only numeric columns
    feats = [c for c in df.columns if c not in TARGET_LIKE]
    X = df[feats].fillna(0)
    # Force all columns to numeric, dropping those that can't convert
    for c in X.columns:
        try:
            X[c] = pd.to_numeric(X[c], errors='coerce').fillna(0)
        except Exception:
            X[c] = 0.0
    # Drop any non-finite or string columns
    numeric_cols = [c for c in X.columns if np.issubdtype(X[c].dtype, np.number)]
    X = X[numeric_cols]
    dates = df["date"].values

    # Feature audit (light): remove constants + >0.99 corr plus cap at MAX_FEAT
    nunique = X.nunique()
    drop = set(nunique[nunique <= 2].index)
    X = X.drop(columns=list(drop))
    # Correlation on numeric only (sample for speed if too many cols)
    corr_cols = X.columns[:500]  # cap at 500 cols for correlation matrix
    corr = X[corr_cols].corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    dup_rules = {}
    for c in upper.columns:
        mates = upper.index[upper[c] > 0.99].tolist()
        if mates:
            group = [c] + mates
            yc = X[group].apply(lambda s: abs(np.corrcoef(s, df["hold1_2pct"])[0, 1]) if s.std() > 0 else 0)
            best = max(group, key=lambda g: yc.get(g, 0))
            for g in group:
                dup_rules.setdefault(g, best)
    dedup = {g for g, b in dup_rules.items() if g != b}
    X = X.drop(columns=list(dedup))
    print(f"Feature audit: {len(feats)} → {X.shape[1]} (dropped {len(drop)} const + "
          f"{len(dedup)} corr duplicates)")

    # Benchmark
    print("\n--- Walk-forward AUC (CatBoost, 5 folds) ---")
    results = []
    for tgt, label in TARGETS.items():
        if tgt not in df.columns:
            continue
        y = (df[tgt] == 1).astype(int)
        pos = int(y.sum())
        base_rate = pos / len(y) * 100
        m = CatBoostClassifier(iterations=N_EST, depth=6, learning_rate=0.06,
                               l2_leaf_reg=5, random_seed=RNG, verbose=0,
                               allow_writing_files=False)
        def fn(X_, y_):
            cat = CatBoostClassifier(iterations=N_EST, depth=6, learning_rate=0.06,
                                     l2_leaf_reg=5, random_seed=RNG, verbose=0,
                                     allow_writing_files=False)
            return cat.fit(X_, y_)
        aucs = walk_forward_auc(fn, X, y, dates)
        if aucs:
            print(f"  {tgt:22s} AUC {np.mean(aucs):.4f} ± {np.std(aucs):.4f} "
                  f" (base {base_rate:.1f}%) folds: {[round(a,4) for a in aucs]}")
            results.append({"target": tgt, "label": label, "mean_auc": np.mean(aucs),
                            "std_auc": np.std(aucs), "base_rate": base_rate,
                            "folds": len(aucs), "aucs": [round(a,4) for a in aucs],
                            "features": X.shape[1]})

    # ── Comparison to V2 ──
    print("\n--- V2 → V3 Comparison ---")
    v2_baseline = {"hold1_2pct": 0.6756, "alpha_spy_2pct": 0.7368}
    for r in results:
        t = r["target"]
        v3 = r["mean_auc"]
        v2 = v2_baseline.get(t, None)
        if v2:
            delta = v3 - v2
            print(f"  {t:22s} V2={v2:.4f}  V3={v3:.4f}  Δ={delta:+.4f}  "
                  f"({'+' if delta>0 else ''}{delta/v2*100:+.1f}%)")
        else:
            print(f"  {t:22s} V3={v3:.4f} (new target, base {r['base_rate']:.1f}%)")

    # Save best model
    best = max(results, key=lambda r: r["mean_auc"])
    print(f"\nBest: {best['target']} AUC {best['mean_auc']:.4f}")
    tgt = best["target"]
    y = (df[tgt] == 1).astype(int)
    sp = int(len(df) * 0.8)
    final = CatBoostClassifier(iterations=N_EST, depth=6, learning_rate=0.06,
                               l2_leaf_reg=5, random_seed=RNG, verbose=0,
                               allow_writing_files=False)
    final.fit(X.iloc[:sp], y.iloc[:sp])
    import joblib
    joblib.dump(final, MODELDIR / f"v3_{tgt}.joblib")
    json.dump({"best_target": tgt, "base_rate": best["base_rate"],
               "auc": best["mean_auc"], "features": list(X.columns),
               "trained_at": datetime.now().isoformat(),
               "comparison": results},
              open(MODELDIR / "v3_metadata.json", "w"), indent=2, default=str)

    # Report
    print(f"Model: {MODELDIR}/v3_{tgt}.joblib")
    print(f"Done — V3 AUC gains in report above.")


if __name__ == "__main__":
    main()
