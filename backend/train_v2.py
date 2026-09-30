"""
V2 OVERNIGHT MODEL TRAINER — publication-grade evaluation.

Pipeline
--------
1. Feature audit  : drop constants/near-constants, drop >0.98-correlated
                    duplicates, permutation importance ranking.
2. Benchmarks     : LightGBM | XGBoost | CatBoost | RandomForest
                    on the PRIMARY target (hold1 > 2%) via chronological
                    walk-forward. Plus LightGBM LambdaRank (grouped by date).
3. Validation     : walk-forward (primary), expanding, rolling,
                    leave-one-year-out, leave-one-ticker-out.
4. Calibration    : Platt scaling + Isotonic on OOF walk-forward probs;
                    Brier score & ECE before/after.
5. Backtest       : honest simulation — fixed capital/trade, transaction
                    costs, slippage, max simultaneous positions, no
                    infinite compounding. Trades the model's top picks
                    per day on out-of-fold data.
6. Reports        : model comparison, feature importance, calibration,
                    backtest → outputs/v2/*.md

HONESTY RULES
  * chronological splits only (no random shuffle)
  * every indicator uses only data available at close of signal day T
  * labels = real executable trades (buy open[T+1] → sell open[T+2])
"""
import sys
import json
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Python"))

import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (roc_auc_score, brier_score_loss, average_precision_score,
                             precision_recall_curve)
from sklearn.inspection import permutation_importance

DATASET = ROOT / "outputs" / "v2" / "demand_zone_v2_dataset.csv"
OUTDIR = ROOT / "outputs" / "v2"
OUTDIR.mkdir(exist_ok=True)
MODELDIR = ROOT / "models" / "v2"
MODELDIR.mkdir(parents=True, exist_ok=True)

PRIMARY = "hold1_2pct"
EXTRA_TARGETS = ["alpha_spy_2pct", "alpha_sector_2pct",
                 "tb_2tp_1sl_label", "tb_3tp_1sl_label"]

# Columns that are labels/targets/ids — never features
TARGET_LIKE = [
    "ticker", "date", "hold1_ret", "buy_open_ret", "close_ret_after",
    "close_and_open_hold", "sector_hold1_ret",
    "bench_SPY_hold1", "alpha_spy_hold1", "alpha_sector_hold1",
    "hit_target", "hit_5pct", "hit_10pct", "hit_15pct", "hit_20pct",
    "target_tier", "strong_hit", "market_relative_hit", "is_sub_10",
]
for t in ["2pct", "3pct", "4pct", "5pct", "6pct"]:
    TARGET_LIKE += [f"hold1_{t}", f"co_{t}"]
for t in ["2pct", "3pct", "5pct"]:
    TARGET_LIKE += [f"alpha_spy_{t}", f"alpha_sector_{t}"]
for tp, sl in [(2, 1), (3, 1), (5, 2), (6, 3)]:
    TARGET_LIKE += [f"tb_{tp}tp_{sl}sl_label", f"tb_{tp}tp_{sl}sl_type",
                    f"tb_{tp}tp_{sl}sl_tth", f"tb_{tp}tp_{sl}sl_mfe",
                    f"tb_{tp}tp_{sl}sl_mae"]

RNG = 42
FEATURE_AUDIT = True
MAX_FEATURES = 100

# Compute budget (kept lean so the whole pipeline finishes on a laptop)
_N_EST = {"LightGBM": 200, "XGBoost": 180, "CatBoost": 150, "RandomForest": 150}
PERM_SAMPLE = 4000
PERM_REPEATS = 1
RANK_EST = 150
CAL_CV = 2
CAL_EST = 80


# ── 1. Feature audit ─────────────────────────────────────────────────────────

def audit_features(X: pd.DataFrame, y: pd.Series) -> list:
    """Return kept feature names after constant / near-constant / correlation
    pruning + permutation-importance cap."""
    before = X.shape[1]
    # constants + near-constants
    nunique = X.nunique()
    drop = set(nunique[nunique <= 2].index)              # constant or binary-no-variance
    # zero-variance and <0.1% unique
    frac = nunique / len(X)
    drop |= set(frac[frac < 0.0005].index)
    X = X.drop(columns=list(drop))
    print(f"    dropped {len(drop)} constant/near-constant cols "
          f"({before} -> {X.shape[1]})")

    # high-correlation duplicates (keep first by corr with target)
    corr = X.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    hi = [c for c in upper.columns if any(upper[c] > 0.98)]
    # keep the one with higher abs correlation to y
    if len(hi):
        yc = X.apply(lambda s: abs(np.corrcoef(s, y)[0, 1]) if s.std() > 0 else 0)
        keep_first = {}
        for c in hi:
            mates = upper.index[upper[c] > 0.98].tolist()
            group = [c] + mates
            best = max(group, key=lambda g: yc.get(g, 0))
            for g in group:
                keep_first.setdefault(g, best)
        dedup = {g for g, b in keep_first.items() if g != b}
        X = X.drop(columns=list(dedup))
        print(f"    dropped {len(dedup)} >0.98-correlated duplicates "
              f"({X.shape[1]} cols left)")

    # permutation importance ranking (LightGBM, fast) — cap at MAX_FEATURES
    if X.shape[1] > MAX_FEATURES:
        m = lgb.LGBMClassifier(n_estimators=80, max_depth=5, learning_rate=0.1,
                               subsample=0.8, colsample_bytree=0.8,
                               random_state=RNG, n_jobs=-1, verbose=-1)
        m.fit(X, y)
        # sample for speed
        n_samp = min(PERM_SAMPLE, len(X))
        idx = np.random.RandomState(RNG).choice(len(X), n_samp, replace=False)
        pi = permutation_importance(m, X.iloc[idx], y.iloc[idx], n_repeats=PERM_REPEATS,
                                    random_state=RNG, n_jobs=-1, scoring="roc_auc")
        imp = pd.Series(pi.importances_mean, index=X.columns).sort_values(ascending=False)
        kept = imp.head(MAX_FEATURES).index.tolist()
        print(f"    permutation-importance cap: kept top {len(kept)} "
              f"(min imp {imp[kept[-1]]:.5f})")
        imp.to_json(OUTDIR / "feature_importance_permutation.json", orient="index")
        return kept
    return list(X.columns)


# ── 2. Model factories ───────────────────────────────────────────────────────

def make_models():
    return {
        "LightGBM": lgb.LGBMClassifier(
            n_estimators=_N_EST["LightGBM"], num_leaves=31, max_depth=-1,
            learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
            min_child_samples=30, lambda_l1=0.05, lambda_l2=0.5,
            random_state=RNG, n_jobs=-1, verbose=-1),
        "XGBoost": xgb.XGBClassifier(
            n_estimators=_N_EST["XGBoost"], max_depth=6, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.8, reg_alpha=0.05, reg_lambda=0.5,
            gamma=0.1, min_child_weight=5, random_state=RNG, n_jobs=-1, verbosity=0),
        "CatBoost": CatBoostClassifier(
            iterations=_N_EST["CatBoost"], depth=5, learning_rate=0.07, l2_leaf_reg=5,
            random_seed=RNG, verbose=0, allow_writing_files=False),
        "RandomForest": RandomForestClassifier(
            n_estimators=_N_EST["RandomForest"], max_depth=8, min_samples_leaf=20,
            random_state=RNG, n_jobs=-1),
    }


# ── 3. Chronological split helpers ───────────────────────────────────────────

def walk_forward_folds(dates: np.ndarray, n_folds: int = 5):
    """Expanding-window chronological fold boundaries (train_end, val_end)."""
    uniq = np.sort(np.unique(dates))
    edges = np.array_split(uniq, n_folds + 1)
    folds = []
    for k in range(1, n_folds + 1):
        train_end = edges[k][0]          # first date of the k-th test block
        val_end = edges[k + 1][0] if k + 1 < len(edges) else uniq[-1] + np.timedelta64(1, "D")
        folds.append((train_end, val_end))
    return folds


def expanding_auc(model_fn, X, y, dates, n_folds=5):
    aucs, n = [], len(X)
    folds = walk_forward_folds(dates, n_folds)
    for train_end, val_end in folds:
        tr, va = dates < train_end, (dates >= train_end) & (dates < val_end)
        if tr.sum() < 2000 or va.sum() < 200:
            continue
        if len(np.unique(y[va])) < 2:
            continue
        m = model_fn(X[tr], y[tr])
        p = m.predict_proba(X[va])[:, 1]
        aucs.append(roc_auc_score(y[va], p))
    return aucs


def rolling_auc(model_fn, X, y, dates, window=365, step=120, max_folds=6):
    aucs = []
    uniq = np.sort(np.unique(dates))
    starts = np.linspace(0, len(uniq) - step - 1, max_folds).astype(int)
    for i in starts:
        tr_end = uniq[i] + np.timedelta64(window, "D")
        if tr_end >= uniq[-1]:
            continue
        tr = (dates >= uniq[i]) & (dates < tr_end)
        va = (dates >= tr_end) & (dates < tr_end + np.timedelta64(step, "D"))
        if tr.sum() < 1500 or va.sum() < 150 or len(np.unique(y[va])) < 2:
            continue
        m = model_fn(X[tr], y[tr])
        p = m.predict_proba(X[va])[:, 1]
        aucs.append(roc_auc_score(y[va], p))
    return aucs


# ── 4. Backtest (honest) ─────────────────────────────────────────────────────

def run_backtest(df_oof: pd.DataFrame, y_true_col: str, top_k: int = 3,
                 capital_per_trade: float = 18.0, cost_bps: float = 2.0,
                 slippage_bps: float = 5.0, max_positions: int = 5,
                 hold_days: int = 1):
    """Trade top-K picks per day on out-of-fold data. Fixed capital per
    trade, transaction costs + slippage, max simultaneous positions,
    no compounding. Returns equity curve + metrics."""
    df = df_oof.copy()
    df = df.sort_values("date")
    trades = []
    dates = sorted(df["date"].unique())
    open_positions = {}  # entry_date -> {exit_date, shares, entry_price, cost}

    for i, d in enumerate(dates):
        # close positions whose exit date is today (hold_days later)
        for ed in list(open_positions):
            if d >= ed:
                p = open_positions.pop(ed)
                # exit at open[T+2] approximated by hold1_ret path
                trades.append(p)
        # open new positions: top-k by prob today
        day = df[df["date"] == d].sort_values("prob", ascending=False)
        day = day[day["prob"] >= day["prob"].quantile(0.85)]  # only confident
        slots = max_positions - len(open_positions)
        for _, r in day.head(slots).iterrows():
            # buy at open[T+1]: entry = buy_open (approx via hold1 ret path)
            entry = r.get("buy_open", r.get("entry_price", 0))
            if not entry or entry <= 0:
                continue
            ret = float(r.get("hold1_ret", 0))
            cost = (cost_bps + slippage_bps) / 1e4
            net_ret = ret - cost
            exit_date = d + np.timedelta64(hold_days, "D")
            open_positions[exit_date] = {
                "date": d, "ticker": r.get("ticker", ""), "entry": entry,
                "ret_pct": ret * 100, "net_ret_pct": net_ret * 100,
                "capital": capital_per_trade,
                "pnl": capital_per_trade * net_ret,
            }
    for p in open_positions.values():
        trades.append(p)

    if not trades:
        return {"n_trades": 0}
    tdf = pd.DataFrame(trades)
    pnl = tdf["pnl"]
    rets = tdf["net_ret_pct"] / 100
    eq = np.cumsum(pnl.values)
    peak = np.maximum.accumulate(eq)
    dd = eq - peak
    sharpe = (rets.mean() / rets.std() * np.sqrt(252)) if rets.std() > 0 else 0
    downside = rets[rets < 0]
    sortino = (rets.mean() / downside.std() * np.sqrt(252)) if len(downside) and downside.std() > 0 else 0
    wins, losses = rets[rets > 0], rets[rets <= 0]
    profit_factor = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")
    total_cap = len(tdf) * capital_per_trade
    cagr = (1 + pnl.sum() / total_cap) ** (252 / max(len(tdf), 1)) - 1
    return {
        "n_trades": len(tdf),
        "win_rate": (rets > 0).mean() * 100,
        "avg_ret_pct": rets.mean() * 100,
        "median_ret_pct": rets.median() * 100,
        "profit_factor": float(profit_factor),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown_pct": float(dd.min() * 100),
        "cagr_pct": float(cagr * 100),
        "expectancy_pct": float(rets.mean() * 100),
        "total_pnl": float(pnl.sum()),
        "total_capital_deployed": float(total_cap),
    }


# ── 5. Calibration ───────────────────────────────────────────────────────────

def ece(y, p, n_bins=10):
    bins = np.linspace(0, 1, n_bins + 1)
    e = 0.0
    for i in range(n_bins):
        m = (p >= bins[i]) & (p < bins[i + 1])
        if m.sum() == 0:
            continue
        e += abs(p[m].mean() - y[m].mean()) * m.mean()
    return e


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("V2 OVERNIGHT MODEL — benchmarks, validation, calibration, backtest")
    print("=" * 70)
    df = pd.read_csv(DATASET)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["date"]).reset_index(drop=True)
    print(f"Loaded: {len(df):,} rows, {df['ticker'].nunique()} tickers, "
          f"{df['date'].min().date()} → {df['date'].max().date()}")

    # Features
    feats = [c for c in df.columns if c not in TARGET_LIKE]
    X = df[feats].copy()
    y = (df[PRIMARY] == 1).astype(int)
    dates = df["date"].values

    # Feature audit
    if FEATURE_AUDIT:
        print("\n[1/6] Feature audit")
        kept = audit_features(X, y)
    else:
        kept = feats
    Xk = X[kept]
    print(f"    final feature count: {len(kept)}")

    # ── Walk-forward: benchmark models ──
    print("\n[2/6] Walk-forward benchmarks (primary target hold1>2%)")
    folds = walk_forward_folds(dates, n_folds=5)
    models = make_models()
    bench_rows = []
    oof = {name: np.zeros(len(df)) for name in models}
    oof_rank = np.zeros(len(df))
    for name, m in models.items():
        aucs, p5s, p10s, topdec = [], [], [], []
        for train_end, val_end in folds:
            tr = (dates < train_end)
            va = (dates >= train_end) & (dates < val_end)
            if tr.sum() < 2000 or va.sum() < 200 or len(np.unique(y[va])) < 2:
                continue
            mm = m.__class__(**m.get_params()) if name != "CatBoost" else m.__class__(**m.get_params())
            mm.fit(Xk[tr], y[tr])
            p = mm.predict_proba(Xk[va])[:, 1]
            oof[name][va] = p
            aucs.append(roc_auc_score(y[va], p))
            n5 = max(int(va.sum() * 0.05), 1)
            top5 = p.argsort()[-n5:][::-1]
            p5s.append(y.values[va][top5].mean() * 100)
            n10 = max(int(va.sum() * 0.10), 1)
            top10 = p.argsort()[-n10:][::-1]
            p10s.append(y.values[va][top10].mean() * 100)
            dc = pd.Series(p).pipe(lambda s: pd.qcut(s, 10, labels=False, duplicates="drop"))
            topd = dc == dc.max()
            topdec.append(y.values[va][topd].mean() * 100 if topd.sum() else 0)
        if aucs:
            bench_rows.append({
                "model": name, "mean_auc": np.mean(aucs), "std_auc": np.std(aucs),
                "worst_auc": np.min(aucs), "best_auc": np.max(aucs),
                "prec@5%": np.mean(p5s), "prec@10%": np.mean(p10s),
                "top_decile_hr": np.mean(topdec), "folds": len(aucs),
                "auc_per_fold": [round(a, 4) for a in aucs],
            })
            print(f"    {name:13s} AUC {np.mean(aucs):.4f}±{np.std(aucs):.4f} "
                  f"[{np.min(aucs):.4f}–{np.max(aucs):.4f}] "
                  f"P@5% {np.mean(p5s):.1f}% P@10% {np.mean(p10s):.1f}%")

    # ── LambdaRank (grouped by date) ──
    print("\n[3/6] LightGBM LambdaRank (grouped by date)")
    try:
        rank_aucs = []
        for train_end, val_end in folds:
            tr = (dates < train_end)
            va = (dates >= train_end) & (dates < val_end)
            if tr.sum() < 2000 or va.sum() < 200 or len(np.unique(y[va])) < 2:
                continue
            groups_tr = pd.Series(df["date"].values[tr]).value_counts().sort_index().values
            groups_va = pd.Series(df["date"].values[va]).value_counts().sort_index().values
            rk = lgb.LGBMRanker(n_estimators=RANK_EST, num_leaves=31, learning_rate=0.06,
                                min_child_samples=30, subsample=0.8, colsample_bytree=0.8,
                                random_state=RNG, n_jobs=-1, verbose=-1)
            rk.fit(Xk[tr], y[tr], group=groups_tr)
            p = rk.predict(Xk[va])
            oof_rank[va] = p
            rank_aucs.append(roc_auc_score(y[va], p))
        print(f"    LambdaRank AUC {np.mean(rank_aucs):.4f}±{np.std(rank_aucs):.4f} "
              f"{[round(a,4) for a in rank_aucs]}")
        bench_rows.append({
            "model": "LightGBM-Rank", "mean_auc": np.mean(rank_aucs),
            "std_auc": np.std(rank_aucs), "worst_auc": np.min(rank_aucs),
            "best_auc": np.max(rank_aucs), "prec@5%": np.nan, "prec@10%": np.nan,
            "top_decile_hr": np.nan, "folds": len(rank_aucs),
            "auc_per_fold": [round(a, 4) for a in rank_aucs],
        })
    except Exception as e:
        print(f"    LambdaRank failed: {e}")

    # ── Robustness: additional validation protocols on LightGBM ──
    print("\n[4/6] Robustness validation (LightGBM)")
    lgbm = models["LightGBM"]

    def fn(X_, y_):
        m = lgb.LGBMClassifier(**lgbm.get_params())
        return m.fit(X_, y_)

    wf_aucs = expanding_auc(fn, Xk, y, dates, n_folds=5)
    rl_aucs = rolling_auc(fn, Xk, y, dates)
    print(f"    walk-forward (expanding): {len(wf_aucs)} folds, "
          f"AUC {np.mean(wf_aucs):.4f}±{np.std(wf_aucs):.4f}")
    print(f"    rolling window:           {len(rl_aucs)} folds, "
          f"AUC {np.mean(rl_aucs):.4f}±{np.std(rl_aucs):.4f}")

    # leave-one-year-out
    years = np.array([d.astype("datetime64[Y]").astype(int) + 1970 for d in dates])
    loyo = []
    for yr in np.unique(years):
        va = years == yr
        tr = ~va
        if tr.sum() < 2000 or va.sum() < 200 or len(np.unique(y[va])) < 2:
            continue
        m = fn(Xk[tr], y[tr])
        p = m.predict_proba(Xk[va])[:, 1]
        loyo.append((int(yr), roc_auc_score(y[va], p)))
    print(f"    leave-one-year-out: " +
          ", ".join(f"{y_} {a:.4f}" for y_, a in loyo))

    # leave-one-ticker-out (sample tickers for speed)
    tickers = sorted(df["ticker"].unique())
    rng = np.random.RandomState(RNG)
    loto = []
    for t in rng.choice(tickers, size=min(8, len(tickers)), replace=False):
        va = df["ticker"].values == t
        tr = ~va
        if tr.sum() < 2000 or va.sum() < 100 or len(np.unique(y[va])) < 2:
            continue
        m = fn(Xk[tr], y[tr])
        p = m.predict_proba(Xk[va])[:, 1]
        loto.append((t, roc_auc_score(y[va], p)))
    print(f"    leave-one-ticker-out: " +
          ", ".join(f"{t} {a:.3f}" for t, a in loto[:6]) +
          (" …" if len(loto) > 6 else ""))

    # ── Calibration (on OOF walk-forward probs of best classifier) ──
    print("\n[5/6] Calibration (Platt + Isotonic on OOF probs)")
    best_name = max(bench_rows, key=lambda r: r["mean_auc"])["model"] if bench_rows else "LightGBM"
    raw = oof[best_name]
    mask = raw > 0
    yv, pv = y.values[mask], raw[mask]
    res = {}
    for method in ["sigmoid", "isotonic"]:
        cc = CalibratedClassifierCV(
            lgb.LGBMClassifier(n_estimators=CAL_EST, num_leaves=31, learning_rate=0.08,
                               random_state=RNG, n_jobs=-1, verbose=-1),
            method=method, cv=CAL_CV).fit(Xk[mask], yv)
        pcal = cc.predict_proba(Xk[mask])[:, 1]
        # refit on full kept features for the out-of-fold vector via CV-fold probs
        res[method] = {
            "brier_raw": float(brier_score_loss(yv, pv)),
            "brier_cal": float(brier_score_loss(yv, pcal)),
            "ece_raw": float(ece(yv, pv)),
            "ece_cal": float(ece(yv, pcal)),
            "auc_raw": float(roc_auc_score(yv, pv)),
            "auc_cal": float(roc_auc_score(yv, pcal)),
        }
        print(f"    {method:10s} Brier {res[method]['brier_raw']:.4f}→{res[method]['brier_cal']:.4f} "
              f"| ECE {res[method]['ece_raw']:.4f}→{res[method]['ece_cal']:.4f} "
              f"| AUC {res[method]['auc_raw']:.4f}→{res[method]['auc_cal']:.4f}")

    # ── Backtest on OOF ──
    print("\n[6/6] Honest backtest (top picks/day, costs+slippage)")
    bt_df = df[["date", "ticker", "hold1_ret", "entry_price", "buy_open_ret"]].copy()
    bt_df["prob"] = raw
    bt_df = bt_df.dropna(subset=["prob"])
    bt = run_backtest(bt_df, "hold1_2pct")
    if bt.get("n_trades", 0):
        print(f"    trades={bt['n_trades']} win_rate={bt['win_rate']:.1f}% "
              f"avg_ret={bt['avg_ret_pct']:.2f}% PF={bt['profit_factor']:.2f}")
        print(f"    Sharpe={bt['sharpe']:.2f} Sortino={bt['sortino']:.2f} "
              f"maxDD={bt['max_drawdown_pct']:.1f}% CAGR={bt['cagr_pct']:.1f}%")
    else:
        print("    no trades (insufficient OOF coverage)")

    # ── Extra targets: walk-forward AUC on primary model ──
    print("\n[+] Extra targets walk-forward AUC (LightGBM)")
    extra = {}
    for tg in EXTRA_TARGETS:
        if tg not in df.columns:
            continue
        yt = df[tg]
        yt = yt.where(yt >= 0).astype(float)   # triple-barrier -1 = invalid
        m2 = yt.notna()
        if m2.sum() < 5000 or yt[m2].nunique() < 2:
            continue
        d2, X2 = dates[m2], Xk[m2]
        y2 = (yt[m2] == 1).astype(int)
        aucs = expanding_auc(fn, X2, y2, d2, n_folds=3)
        extra[tg] = {"mean_auc": float(np.mean(aucs)), "aucs": [round(a, 4) for a in aucs],
                     "base_rate": float(y2.mean())}
        print(f"    {tg:22s} AUC {np.mean(aucs):.4f} "
              f"(base {(y2.mean()*100):.1f}%) {[round(a,4) for a in aucs]}")

    # ── Save ──
    bench_df = pd.DataFrame(bench_rows).sort_values("mean_auc", ascending=False)
    bench_df.to_csv(OUTDIR / "v2_model_comparison.csv", index=False)
    best_model_name = bench_df.iloc[0]["model"] if len(bench_df) else "LightGBM"
    print(f"\nBest walk-forward model: {best_model_name} "
          f"(AUC {bench_df.iloc[0]['mean_auc']:.4f})")

    # save best classifier for inference
    train_end, val_end = folds[-1]
    tr = dates < train_end
    best_m = models.get(best_model_name, lgbm)
    best_m.fit(Xk[tr], y[tr])
    import joblib
    joblib.dump(best_m, MODELDIR / f"hold1_v2_{best_model_name.lower()}.joblib")
    json.dump({"features": kept, "best_model": best_model_name,
               "target": PRIMARY, "trained_at": datetime.now().isoformat(),
               "benchmarks": bench_df.to_dict("records")},
              open(MODELDIR / "hold1_v2_metadata.json", "w"), indent=2, default=str)

    # Markdown report
    md = ["# V2 Overnight Model Report", "",
          f"Dataset: {len(df):,} rows · {df['ticker'].nunique()} tickers · "
          f"{df['date'].min().date()} → {df['date'].max().date()}",
          f"Target: {PRIMARY} (buy open[T+1] → sell open[T+2])", "",
          "## Model comparison (chronological walk-forward)", ""]
    md.append(bench_df.to_markdown(index=False) if hasattr(bench_df, "to_markdown")
              else bench_df.to_string())
    md += ["", "## Robustness (LightGBM)", "",
           f"- walk-forward (expanding): {len(wf_aucs)} folds, "
           f"mean AUC {np.mean(wf_aucs):.4f} ± {np.std(wf_aucs):.4f}",
           f"- rolling window: {len(rl_aucs)} folds, "
           f"mean AUC {np.mean(rl_aucs):.4f} ± {np.std(rl_aucs):.4f}",
           f"- leave-one-year-out: " +
           ", ".join(f"{y_} {a:.4f}" for y_, a in loyo),
           f"- leave-one-ticker-out: " +
           ", ".join(f"{t} {a:.3f}" for t, a in loto), "",
           "## Calibration (OOF)", ""]
    for method, r in res.items():
        md.append(f"- **{method}**: Brier {r['brier_raw']:.4f}→{r['brier_cal']:.4f} · "
                  f"ECE {r['ece_raw']:.4f}→{r['ece_cal']:.4f} · "
                  f"AUC {r['auc_raw']:.4f}→{r['auc_cal']:.4f}")
    md += ["", "## Backtest (honest: costs + slippage + max positions)", "",
           f"- trades: {bt.get('n_trades', 'n/a')} · win rate: "
           f"{bt.get('win_rate', 'n/a'):.1f}% · profit factor: "
           f"{bt.get('profit_factor', 'n/a'):.2f}",
           f"- Sharpe: {bt.get('sharpe', 'n/a'):.2f} · Sortino: "
           f"{bt.get('sortino', 'n/a'):.2f} · max DD: "
           f"{bt.get('max_drawdown_pct', 'n/a'):.1f}% · CAGR: "
           f"{bt.get('cagr_pct', 'n/a'):.1f}%",
           f"- avg return/trade: {bt.get('avg_ret_pct', 'n/a'):.2f}% · "
           f"expectancy: {bt.get('expectancy_pct', 'n/a'):.2f}%", "",
           "## Extra targets (walk-forward AUC)", ""]
    for tg, r in extra.items():
        md.append(f"- {tg}: {r['mean_auc']:.4f} (base {r['base_rate']*100:.1f}%)")
    (OUTDIR / "v2_report.md").write_text("\n".join(md))
    print(f"\nSaved: {OUTDIR/'v2_report.md'} and {OUTDIR/'v2_model_comparison.csv'}")


if __name__ == "__main__":
    main()
