"""
Hold-1-Day Honest Trainer.

Trains XGBoost models on the HONEST hold-1-day targets built by
build_hold1_targets.py — NOT on intraday-touch labels.

Targets (per threshold t):
  hold1_t : buy open[T+1], sell open[T+2] -> return >= t    (user's real trade)
  co_t    : close[T+1] >= open[T+1]*(1+t) AND open[T+2] >= open[T+1]*(1+t)
            (the user's strict ask: closes at t AND next open holds at t)

Walk-forward chronological split. Feature set = same indicator-aligned
features used at inference time (features_from_row).
"""
import sys
from pathlib import Path
_PARENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PARENT)); sys.path.insert(0, str(_PARENT / "Python"))

import pandas as pd, numpy as np, joblib, json, warnings
from datetime import datetime
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.inspection import permutation_importance
import xgboost as xgb
from lightgbm import LGBMClassifier
warnings.filterwarnings("ignore")

from backend.utils import features_from_row

MODEL_DIR = _PARENT / "models"
MODEL_DIR.mkdir(exist_ok=True)

DATASET = _PARENT / "outputs" / "hold1" / "demand_zone_hold1_dataset_v1.csv"
KEEP_FEATURES = 50
TRAIN_FRAC = 0.80          # chronological: first 80% train, last 20% test
N_SPLITS = 4               # walk-forward folds within the train portion

THRESHOLDS = [0.02, 0.03, 0.04, 0.05, 0.06]

INDICATOR_COLS = {
    "Open", "High", "Low", "Close", "Volume",
    "daily_return", "5d_return", "20d_return",
    "ema_20", "ema_50", "ema_200",
    "dist_ema_20_pct", "dist_ema_50_pct", "dist_ema_200_pct",
    "ema_alignment", "trend_slope_20",
    "rsi_14", "macd", "macd_signal", "macd_hist",
    "atr_14", "atr_pct", "adx_14",
    "avg_volume_20", "rel_volume",
    "body", "upper_wick", "lower_wick", "is_bullish", "lower_wick_pct",
    "distance_from_52w_high_pct",
    "spy_return_5d", "spy_return_20d", "spy_return_50d", "spy_above_200ma",
    "vix_level", "vix_percentile_60d",
    "xlk_return_20d", "xlf_return_20d", "xle_return_20d", "xlv_return_20d",
    "xly_return_20d", "xlp_return_20d", "xli_return_20d", "xlb_return_20d",
    "xlu_return_20d", "xlre_return_20d", "xlc_return_20d",
    "iwm_return_20d", "qqq_return_20d", "spy_atr_pct",
    "entry_price", "zone_price", "zone_touches", "zone_age_days",
    "target_tier",
}


def walk_forward_auc(model_fn, Xt, yt, n_splits=4, kept=None):
    """Evaluate with expanding-window walk-forward inside the TRAIN set.
    Returns per-fold AUC list. Subsets to `kept` features if provided."""
    if kept is not None:
        Xt = Xt[kept]
    n = len(Xt)
    fold_size = n // (n_splits + 1)
    aucs = []
    for k in range(1, n_splits + 1):
        cut = k * fold_size
        if cut >= n or cut < 1000:
            continue
        m = model_fn(Xt.iloc[:cut], yt.iloc[:cut])
        val = Xt.iloc[cut:min(cut + fold_size, n)]
        yf = yt.iloc[cut:min(cut + fold_size, n)]
        if len(np.unique(yf)) > 1:
            probs = m.predict_proba(val)[:, 1]
            aucs.append(roc_auc_score(yf, probs))
    return aucs


def train_target(name: str, y_raw, X, y, sw):
    """Train XGBoost on a hold-1-day target. Chronological 80/20 split."""
    sp = int(len(X) * TRAIN_FRAC)
    Xt, Xv = X.iloc[:sp], X.iloc[sp:]
    yt, yv = y.iloc[:sp], y.iloc[sp:]
    pos = int(y_raw.sum())
    base_rate = pos / len(y) * 100

    # LightGBM baseline for pruning
    base = LGBMClassifier(n_estimators=100, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8, scale_pos_weight=sw,
        random_state=42, n_jobs=-1, verbose=-1)
    base.fit(Xt, yt)
    base_auc = roc_auc_score(yv, base.predict_proba(Xv)[:, 1])

    n_samp = min(3000, len(Xt))
    idx = np.random.RandomState(42).choice(len(Xt), n_samp, replace=False)
    pi = permutation_importance(base, Xt.iloc[idx], yt.iloc[idx],
        n_repeats=3, random_state=42, n_jobs=-1, scoring="roc_auc")
    imp = (pd.DataFrame({"feature": X.columns, "importance": pi.importances_mean})
           .sort_values("importance", ascending=False))
    kept = imp.head(KEEP_FEATURES)["feature"].tolist()
    Xtp, Xvp = Xt[kept], Xv[kept]

    m = xgb.XGBClassifier(n_estimators=200, max_depth=7, learning_rate=0.05,
        subsample=0.85, colsample_bytree=0.8, reg_alpha=0.05, reg_lambda=0.05,
        gamma=0.1, scale_pos_weight=sw, random_state=42, n_jobs=-1, verbosity=0)
    m.fit(Xtp, yt)
    probs = m.predict_proba(Xvp)[:, 1]
    auc = roc_auc_score(yv, probs)

    # Walk-forward within train (subset to kept features)
    wf_aucs = walk_forward_auc(
        lambda a, b: xgb.XGBClassifier(n_estimators=150, max_depth=6, learning_rate=0.06,
            subsample=0.85, colsample_bytree=0.8, scale_pos_weight=sw,
            random_state=42, n_jobs=-1, verbosity=0).fit(a, b),
        Xt, yt, kept=kept)

    # Deciles on honest labels
    dec_df = pd.DataFrame({"y": yv.values, "p": probs})
    dec_df["decile"] = pd.qcut(dec_df["p"], q=10, labels=False, duplicates="drop")
    top_dec = dec_df[dec_df["decile"] == dec_df["decile"].max()]
    top_hr = float(top_dec["y"].mean() * 100) if len(top_dec) > 0 else 0
    # Top 5% / Top 20 rows by probability
    n_top5 = max(int(len(yv) * 0.05), 1)
    top5 = probs.argsort()[-n_top5:][::-1]
    top5_hr = float(yv.iloc[top5].mean() * 100)
    top20 = probs.argsort()[-20:][::-1]
    top20_hr = float(yv.iloc[top20].mean() * 100)
    brier = float(brier_score_loss(yv, probs))
    percs = {f"p{p}": float(np.percentile(probs, p)) for p in [50, 75, 90, 95, 99]}

    print(f"\n  {'-'*55}")
    print(f"  {name}")
    print(f"  Base rate (honest): {base_rate:.1f}% | Pos: {pos:,}")
    print(f"  AUC: {auc:.4f} (base LGBM {base_auc:.4f}) | WF folds: "
          f"{[f'{a:.4f}' for a in wf_aucs]}")
    print(f"  Top-5% hit: {top5_hr:.1f}% | Top-decile: {top_hr:.1f}% | Top-20: {top20_hr:.1f}%")
    print(f"  Brier: {brier:.4f} | prob range [{probs.min():.3f},{probs.max():.3f}] "
          f"mean={probs.mean():.4f}")
    print(f"  p50={percs['p50']:.3f} p75={percs['p75']:.3f} p90={percs['p90']:.3f} "
          f"p95={percs['p95']:.3f} p99={percs['p99']:.3f}")

    meta = {"auc": auc, "base_auc": base_auc, "wf_aucs": wf_aucs,
            "pos": pos, "base_rate": base_rate, "top5_hit_rate": top5_hr,
            "top_decile_hit_rate": top_hr, "top20_hit_rate": top20_hr,
            "brier": brier, "percentiles": percs}
    return m, kept, meta


def main():
    print("=" * 65)
    print("HOLD-1-DAY HONEST TRAINER")
    print("Targets: buy open -> sell next open (NOT intraday touches)")
    print("=" * 65)

    df = pd.read_csv(DATASET)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date"]).reset_index(drop=True)
    print(f"Loaded: {len(df):,} rows, {df['ticker'].nunique()} tickers, "
          f"{len(df.columns)} cols")

    available = [c for c in INDICATOR_COLS if c in df.columns]

    # Build features once (indicator-aligned, identical to inference path)
    print("\nBuilding features...")
    feature_rows = []
    for idx, row in df.iterrows():
        if idx % 15000 == 0 and idx > 0:
            print(f"  {idx}/{len(df)}")
        try:
            sparse_row = {c: row.get(c, 0) if c in row.index else 0 for c in available}
            feats = features_from_row(pd.Series(sparse_row),
                entry_price=float(row.get("entry_price", row.get("Close", 100))),
                zone_price=float(row.get("zone_price", row.get("Close", 100) * 0.95)),
                zone_touches=int(row.get("zone_touches", 1)),
                zone_age_days=int(row.get("zone_age_days", 0)))
            feature_rows.append(feats)
        except Exception:
            if feature_rows:
                feature_rows.append({k: 0.0 for k in feature_rows[0]})
            else:
                feature_rows.append({})
    X = pd.DataFrame(feature_rows).fillna(0)
    print(f"  Features: {X.shape[1]} cols from {len(X):,} rows")

    # ── Train per target ──
    models_hold1 = {}
    models_co = {}
    meta_hold1 = {}
    meta_co = {}
    all_meta = {}

    for thresh in THRESHOLDS:
        tag = f"{int(thresh*100)}pct"
        # Target A: the user's real trade
        y_raw_h = df[f"hold1_{tag}"]
        y_h = pd.Series(y_raw_h.astype(int))
        sw_h = (len(y_h) - int(y_h.sum())) / max(int(y_h.sum()), 1)
        m_h, kept, meta_h = train_target(
            f"hold1 > {int(thresh*100)}% (buy open -> next open)", y_raw_h, X, y_h, sw_h)
        models_hold1[thresh] = m_h
        meta_hold1[thresh] = meta_h

        # Target B: strict close + next-open hold
        y_raw_c = df[f"co_{tag}"]
        y_c = pd.Series(y_raw_c.astype(int))
        sw_c = (len(y_c) - int(y_c.sum())) / max(int(y_c.sum()), 1)
        m_c, _, meta_c = train_target(
            f"close AND next-open >= {int(thresh*100)}%", y_raw_c, X, y_c, sw_c)
        models_co[thresh] = m_c
        meta_co[thresh] = meta_c

        all_meta[tag] = {
            "hold1_auc": meta_h["auc"], "hold1_top5": meta_h["top5_hit_rate"],
            "hold1_base": meta_h["base_rate"], "hold1_wf": meta_h["wf_aucs"],
            "co_auc": meta_c["auc"], "co_top5": meta_c["top5_hit_rate"],
            "co_base": meta_c["base_rate"], "co_wf": meta_c["wf_aucs"],
        }

    # ── Save ──
    for thresh in THRESHOLDS:
        joblib.dump(models_hold1[thresh], MODEL_DIR / f"hold1_{int(thresh*100)}pct.joblib")
        joblib.dump(models_co[thresh], MODEL_DIR / f"hold1_co_{int(thresh*100)}pct.joblib")
    json.dump({"features": kept, "count": len(kept)},
              open(MODEL_DIR / "hold1_feature_names.json", "w"), indent=2)
    meta = {
        "model_name": "Hold-1-Day Honest (open->open + close-hold)",
        "trained_at": datetime.now().isoformat(),
        "features_count": KEEP_FEATURES,
        "dataset_rows": len(df),
        "dataset": str(DATASET),
        "target_def": ("hold1: buy open[T+1] sell open[T+2]; "
                       "co: close[T+1] AND open[T+2] >= entry*(1+t)"),
        "thresholds": all_meta,
        "feature_names": kept,
    }
    json.dump(meta, open(MODEL_DIR / "hold1_metadata.json", "w"), indent=2, default=str)

    print("\n" + "=" * 65)
    print("HOLD-1-DAY TRAINING COMPLETE")
    print("=" * 65)
    for tag, m in all_meta.items():
        print(f"  >{tag}: hold1 AUC={m['hold1_auc']:.4f} top5={m['hold1_top5']:.1f}% "
              f"(base {m['hold1_base']:.1f}%) | co AUC={m['co_auc']:.4f} top5={m['co_top5']:.1f}% "
              f"(base {m['co_base']:.1f}%)")
    print(f"  Models: {MODEL_DIR}/hold1_*.joblib")


if __name__ == "__main__":
    main()
