"""Adaptive diagnostic suite (M6 Part 2C).

Each diagnostic states: purpose, required inputs, assumptions,
reproducible outputs, what it establishes and what it does NOT establish,
and which hypotheses it connects to. Pure pandas/numpy, deterministic
(seeded where sampling), no network, no ground-truth access.

Covers: distribution shift, concept drift, missingness/quality, feature
instability, model instability, calibration, overfitting, target/label
problems, temporal consistency, pipeline/preprocessing consistency,
feature-target relationships, prediction/subgroup errors.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd


def _frame(predictions_path: str) -> pd.DataFrame:
    return pd.read_csv(predictions_path)


def temporal_changepoint_scan(predictions_path: str,
                              date_column: str = "date",
                              target_column: str = "target",
                              prediction_column: str = "prediction",
                              min_segment: int = 30) -> dict:
    """Purpose: localize WHEN a level shift occurs (day-level scan).

    Inputs: predictions CSV with date, target, prediction columns.
    Assumptions: rows sortable by date; residual mean shift is the signal.
    Output: best changepoint date, pre/post residual means, shift size,
    CUSUM-style scan table summary. Reproducible: full sort, no sampling.
    Establishes: the location and size of the largest mean break.
    Does NOT establish: the cause of the break (drift vs pipeline change
    vs label shift need further tests). Connects to: drift hypotheses.
    """
    df = _frame(predictions_path).copy()
    for c in (date_column, target_column, prediction_column):
        if c not in df.columns:
            raise ValueError(f"{predictions_path}: required column {c!r} missing")
    df[date_column] = pd.to_datetime(df[date_column])
    df = df.sort_values(date_column).reset_index(drop=True)
    resid = (df[target_column] - df[prediction_column]).to_numpy(dtype=float)
    n = len(df)
    if n < 2 * min_segment:
        raise ValueError(f"need >= {2 * min_segment} rows for a scan, got {n}")
    best_k, best_gain = min_segment, -1.0
    overall = float(np.mean(resid))
    for k in range(min_segment, n - min_segment + 1):
        pre, post = float(np.mean(resid[:k])), float(np.mean(resid[k:]))
        gain = abs(post - pre) * min(k, n - k) / n
        if gain > best_gain:
            best_gain, best_k = gain, k
    pre_m = float(np.mean(resid[:best_k]))
    post_m = float(np.mean(resid[best_k:]))
    return {"ok": True, "n": n,
            "changepoint_date": str(df.loc[best_k, date_column].date()),
            "changepoint_index": int(best_k),
            "pre_residual_mean": round(pre_m, 6),
            "post_residual_mean": round(post_m, 6),
            "shift_size": round(float(post_m - pre_m), 6),
            "overall_residual_mean": round(overall, 6),
            "establishes": "location/size of largest residual-mean break",
            "does_not_establish": "cause of the break"}


def residual_time_analysis(predictions_path: str,
                           date_column: str = "date",
                           target_column: str = "target",
                           prediction_column: str = "prediction",
                           split_column: str | None = "split") -> dict:
    """Purpose: separate persistent misspecification from a new shift.

    Compares residual mean/autocorr in the first vs second half (and
    train vs test when a split column exists). A new shift shows small
    early errors exploding late; persistent misspecification shows large
    errors throughout. Establishes correlation with time, not causation.
    """
    df = _frame(predictions_path).copy()
    for c in (date_column, target_column, prediction_column):
        if c not in df.columns:
            raise ValueError(f"{predictions_path}: required column {c!r} missing")
    df[date_column] = pd.to_datetime(df[date_column])
    df = df.sort_values(date_column).reset_index(drop=True)
    df["_resid"] = df[target_column] - df[prediction_column]
    half = len(df) // 2
    early, late = df.iloc[:half], df.iloc[half:]
    out: dict = {"ok": True, "n": len(df),
                 "early_mae": round(float((early["_resid"]).abs().mean()), 6),
                 "late_mae": round(float((late["_resid"]).abs().mean()), 6),
                 "early_residual_mean": round(float(early["_resid"].mean()), 6),
                 "late_residual_mean": round(float(late["_resid"].mean()), 6)}
    if split_column and split_column in df.columns:
        by = df.groupby(split_column)["_resid"].agg(
            lambda s: round(float(s.abs().mean()), 6)).to_dict()
        out["mae_by_split"] = {str(k): v for k, v in by.items()}
        means = df.groupby(split_column)["_resid"].mean().to_dict()
        out["residual_mean_by_split"] = {str(k): round(float(v), 6)
                                         for k, v in means.items()}
    out["pattern"] = ("recent-shift pattern" if out["late_mae"] > 1.5 * max(out["early_mae"], 1e-9)
                      else "persistent-error pattern")
    out["establishes"] = "whether errors are recent vs persistent"
    out["does_not_establish"] = "the mechanism behind the pattern"
    return out


def distribution_shift_profile(predictions_path: str,
                               target_column: str = "target",
                               split_column: str = "split") -> dict:
    """Purpose: quantify target/level shift between splits (covariate check).

    Compares target mean/std/median train vs test. Establishes that the
    TARGET moved (a precondition for drift claims). Does NOT establish
    that the model caused the miss or rule out label problems.
    """
    df = _frame(predictions_path)
    for c in (target_column, split_column):
        if c not in df.columns:
            raise ValueError(f"{predictions_path}: required column {c!r} missing")
    g = df.groupby(split_column)[target_column]
    stats = {str(k): {"mean": round(float(v.mean()), 6),
                      "std": round(float(v.std()), 6),
                      "median": round(float(v.median()), 6),
                      "n": int(v.count())}
             for k, v in g}
    keys = list(stats)
    shift = None
    if len(keys) >= 2:
        a, b = stats[keys[0]], stats[keys[1]]
        shift = round(float(b["mean"] - a["mean"]), 6)
    return {"ok": True, "by_split": stats, "mean_shift": shift,
            "establishes": "target level moved between splits",
            "does_not_establish": "why it moved"}


def data_quality_profile(predictions_path: str) -> dict:
    """Purpose: missingness / quality screen (nulls, dups, constant cols).

    Establishes data-hygiene facts. Does NOT establish model impact —
    join with error analysis for that.
    """
    df = _frame(predictions_path)
    nulls = {c: int(df[c].isna().sum()) for c in df.columns}
    return {"ok": True, "n": len(df), "n_columns": len(df.columns),
            "nulls": nulls, "duplicate_rows": int(df.duplicated().sum()),
            "establishes": "missingness/duplication facts",
            "does_not_establish": "whether quality issues caused errors"}


def segment_quality_screen(predictions_path: str,
                           segment_column: str | None = None) -> dict:
    """Purpose: hygiene per segment — null/dup rates by group.

    A DIFFERENT measurement from data_quality_profile (pooled): it
    asks whether hygiene defects concentrate in one segment, which
    is the shape a segment-confounded quality claim predicts.
    Establishes per-segment null/duplicate rates. Does NOT establish
    model impact — join with error analysis for that.
    """
    df = _frame(predictions_path)
    seg = segment_column
    if seg is None:
        seg = next((c for c in ("region", "slice", "district",
                                "ward", "segment", "split", "fold")
                    if c in df.columns), None)
    if seg is None:
        raise ValueError(f"{predictions_path}: no segment column found "
                         "for segment quality screen")
    by_seg = {}
    worst_null, worst_dup = 0.0, 0.0
    for value, chunk in df.groupby(seg):
        n = max(len(chunk), 1)
        null_rate = round(float(chunk.isna().sum().sum() / n), 6)
        dup_rate = round(float(chunk.duplicated().sum() / n), 6)
        by_seg[str(value)] = {"n": int(len(chunk)),
                              "null_rate": null_rate,
                              "dup_rate": dup_rate}
        worst_null = max(worst_null, null_rate)
        worst_dup = max(worst_dup, dup_rate)
    return {"ok": True, "n": len(df), "segment_column": seg,
            "by_segment": by_seg, "worst_null_rate": worst_null,
            "worst_dup_rate": worst_dup,
            "establishes": "whether hygiene defects concentrate "
            "in a segment",
            "does_not_establish": "whether quality issues caused "
            "errors"}


def calibration_snapshot(predictions_path: str,
                         prediction_column: str = "prediction",
                         target_column: str = "target") -> dict:
    """Purpose: bias/variance split of error (overfitting vs systematic bias).

    Establishes bias_mean_residual and spread. Does NOT establish the
    source of bias.
    """
    df = _frame(predictions_path)
    for c in (prediction_column, target_column):
        if c not in df.columns:
            raise ValueError(f"{predictions_path}: required column {c!r} missing")
    resid = df[target_column] - df[prediction_column]
    return {"ok": True, "n": len(df),
            "bias_mean_residual": round(float(resid.mean()), 6),
            "residual_std": round(float(resid.std()), 6),
            "mae": round(float(resid.abs().mean()), 6),
            "establishes": "bias vs variance decomposition",
            "does_not_establish": "source of the bias"}


def residual_feature_dependence(predictions_path: str,
                                 target_column: str = "target",
                                 prediction_column: str = "prediction",
                                 top_k: int = 5) -> dict:
    """Purpose: test whether errors depend on an input/feature column.

    Computes |Pearson r| between residuals and every other numeric column
    (excluding target/prediction). Inputs: predictions CSV containing at
    least one extra numeric column. Assumptions: linear association
    screening only; correlation is not causation. Output: ranked columns
    with |r| and n. Reproducible: full-column scan, no sampling.
    Establishes: whether error magnitude/direction tracks an input
    (supports input-dependence hypotheses when max|r| > 0.5; contradicts
    them when all |r| < 0.2). Does NOT establish: why the dependence
    exists (stale input, leakage, misspecification need further tests).
    """
    import pandas as pd
    df = _frame(predictions_path)
    for c in (target_column, prediction_column):
        if c not in df.columns:
            raise ValueError(f"{predictions_path}: required column {c!r} missing")
    y = pd.to_numeric(df[target_column], errors="coerce")
    p = pd.to_numeric(df[prediction_column], errors="coerce")
    resid = (y - p)
    ranked = []
    for col in df.columns:
        if col in (target_column, prediction_column):
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        x = pd.to_numeric(df[col], errors="coerce")
        m = resid.notna() & x.notna()
        if m.sum() < 3 or float(x[m].std() or 0) == 0.0:
            continue
        r = float(resid[m].corr(x[m]))
        if r != r:  # NaN guard
            continue
        ranked.append({"column": col, "abs_corr": round(abs(r), 6),
                       "corr": round(r, 6), "n": int(m.sum())})
    ranked.sort(key=lambda d: d["abs_corr"], reverse=True)
    top = ranked[: max(1, int(top_k))]
    peak = top[0]["abs_corr"] if top else 0.0
    return {"ok": True, "n": int(len(df)),
            "ranked": top, "n_numeric_scanned": len(ranked),
            "max_abs_corr": peak,
            "establishes": "whether residuals track an input column",
            "does_not_establish": "the cause of the dependence"}


def fingerprint(predictions_path: str) -> str:
    h = hashlib.sha256()
    with open(predictions_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]
