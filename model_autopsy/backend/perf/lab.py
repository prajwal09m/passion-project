"""M15 Phase 1.1/1.2: performance reconnaissance + AUC lab (offline).

Chronological demand-zone lab: no shuffling across time, leakage
columns excluded by the V7 protocol, untouched final test period.
Every candidate carries hypothesis, explanation, expected effect,
experiment, baseline comparison, and reproducible artifact.
"""
from __future__ import annotations

EXCLUDE_PATTERNS = (
    'ticker', 'date', 'hold1_', 'co_', 'alpha_spy_', 'alpha_sector_',
    'mag_spy_', 'mag_sector_', 'bench_', 'tb_', 'departure_',
    'expected_return_proxy', 'risk_adjusted_return_proxy',
    'buy_open_ret', 'close_ret_after', 'close_and_open_hold',
    'sector_hold1_ret', 'close_strength',
)

TARGET = "alpha_spy_2pct"


def load(cache_cols: list[str] | None = None, nrows: int | None = None):
    import pandas as pd
    df = pd.read_csv("study_files/outputs/v2/demand_zone_v2_dataset.csv",
                     nrows=nrows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "ticker"]).reset_index(drop=True)


def features(df, target: str = TARGET) -> list[str]:
    excl = {c for c in df.columns
            for pat in EXCLUDE_PATTERNS if pat in c}
    excl.add(target)
    num = [c for c in df.columns
           if c not in excl and str(df[c].dtype) in (
               "float64", "int64", "float32", "int32")]
    nulls = df[num].isna().mean()
    return [c for c in num if float(nulls[c]) < 0.3]


def chrono_splits(df, train_end="2024-01-01", val_end="2025-01-01"):
    import pandas as pd
    d = pd.to_datetime(df["date"])
    tr = d < pd.Timestamp(train_end)
    va = (d >= pd.Timestamp(train_end)) & (d < pd.Timestamp(val_end))
    te = d >= pd.Timestamp(val_end)
    return {"train": tr, "val": va, "test": te}


def train_lgbm(X_train, y_train, params: dict | None = None,
               seed: int = 7):
    import lightgbm as lgb
    p = {"n_estimators": 200, "learning_rate": 0.05,
         "num_leaves": 63, "min_child_samples": 100,
         "subsample": 0.8, "subsample_freq": 1,
         "colsample_bytree": 0.7, "reg_lambda": 5.0,
         "random_state": seed, "verbosity": -1}
    if params:
        p.update(params)
    m = lgb.LGBMClassifier(**p)
    m.fit(X_train, y_train)
    return m


CANDIDATES = {
    "class_balance": {
        "hypothesis": "Base rate 0.196 under-weights positives; "
                      "balanced weighting recovers minority signal.",
        "params": {"class_weight": "balanced"},
        "expected": "small val AUC gain without calibration collapse"},
    "capacity": {
        "hypothesis": "63 leaves under-fit 120+ feature interactions; "
                      "more capacity with stronger regularization helps.",
        "params": {"num_leaves": 127, "reg_lambda": 10.0,
                   "min_child_samples": 150},
        "expected": "val AUC gain if capacity is the bottleneck"},
    "slower_learn": {
        "hypothesis": "lr 0.05 with 200 trees stops short; slower "
                      "learning with more trees generalizes better.",
        "params": {"learning_rate": 0.02, "n_estimators": 600},
        "expected": "val AUC gain if optimization is the bottleneck"},
}


def run_candidate(name: str, X_train, y_train, X_val, seed: int = 7):
    spec = CANDIDATES[name]
    model = train_lgbm(X_train, y_train, spec["params"], seed)
    return {"name": name, "hypothesis": spec["hypothesis"],
            "expected": spec["expected"], "model": model,
            "params": spec["params"]}
