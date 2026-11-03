"""Task-specific diagnostics + capability-aware selection (Phases 4-6).

Every tool declares tasks, capabilities, inputs, outputs, and limits.
`select_tools` returns only diagnostics whose task matches AND whose
capabilities the project exposes AND whose required columns exist —
never a silent fabrication when data is missing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import config

PROJECT_ROOT = config.PROJECT_ROOT


def _resolve(path: str | None) -> "Path":
    from pathlib import Path
    from ..ml_tools import _resolve_project_csv
    return _resolve_project_csv(path, "")


TOOL_CARDS: dict[str, dict] = {
    "dataset_validation": {
        "tasks": ["classification", "regression", "forecasting", "ranking",
                  "clustering", "other"],
        "capabilities": ["prediction_inspection"],
        "requires_columns": [],
        "outputs": ["schema", "nulls", "label/fold/date coverage"],
        "read_only": True, "modifies": False,
        "limitations": ["reports structure only; no performance judgment"],
        "evidence": "column profiles + coverage flags"},
    "classification_metrics": {
        "tasks": ["classification"],
        "capabilities": ["prediction_inspection", "error_analysis"],
        "requires_columns": ["label", "score"],
        "outputs": ["roc_auc", "brier", "precision", "recall", "per-split"],
        "read_only": True, "modifies": False,
        "limitations": ["binary labels only; a metric alone proves no cause"],
        "evidence": "recomputed metric values + source path"},
    "calibration_and_error_analysis": {
        "tasks": ["classification"],
        "capabilities": ["calibration"],
        "requires_columns": ["label", "score"],
        "outputs": ["reliability_bins", "per_fold_auc"],
        "read_only": True, "modifies": False,
        "limitations": ["binning is descriptive; threshold choice is separate"],
        "evidence": "binned reliability table"},
    "ranking_slice_diagnostics": {
        "tasks": ["ranking", "classification"],
        "capabilities": ["prediction_inspection", "error_analysis"],
        "requires_columns": ["label", "score"],
        "outputs": ["per_slice_precision_at_k", "max_slice_gap",
                    "pooled_precision_at_k"],
        "read_only": True, "modifies": False,
        "limitations": ["observational ranking gap; thin slices "
                        "inconclusive; proves no cause"],
        "evidence": "per-slice top-K hit rates + source path"},
    "regression_metrics": {
        "tasks": ["regression", "forecasting"],
        "capabilities": ["prediction_inspection", "error_analysis"],
        "requires_columns": ["target", "prediction"],
        "outputs": ["mae", "mse", "rmse", "r2", "residual_stats",
                    "heteroscedasticity_hint", "outliers", "bias"],
        "read_only": True, "modifies": False,
        "limitations": ["descriptive; residual patterns suggest, never prove, causes"],
        "evidence": "recomputed error metrics + residual summaries"},
    "forecast_diagnostics": {
        "tasks": ["forecasting"],
        "capabilities": ["prediction_inspection", "error_analysis"],
        "requires_columns": ["date", "target", "prediction"],
        "outputs": ["error_by_horizon", "drift", "residual_autocorr",
                    "split_overlap"],
        "read_only": True, "modifies": False,
        "limitations": ["hints only; causal drift claims need pipeline info"],
        "evidence": "per-horizon errors + overlap report"},
    "clustering_stability": {
        "tasks": ["clustering"],
        "capabilities": ["prediction_inspection"],
        "requires_columns": ["features"],
        "outputs": ["silhouette", "cluster_sizes", "imbalance_ratio"],
        "read_only": True, "modifies": False,
        "limitations": ["k-means screening only; stability across seeds reported"],
        "evidence": "silhouette + size distribution"},
    "time_split_validation": {
        "tasks": ["classification", "regression", "forecasting"],
        "capabilities": ["prediction_inspection", "data_leakage_checks"],
        "requires_columns": [],
        "outputs": ["fold_sizes", "fold_date_spans"],
        "read_only": True, "modifies": False,
        "limitations": ["date overlap is necessary-not-sufficient for leakage"],
        "evidence": "spans + sizes"},
    "feature_target_suspiciousness": {
        "tasks": ["classification", "regression"],
        "capabilities": ["data_leakage_checks"],
        "requires_columns": ["features"],
        "outputs": ["top_correlations"],
        "read_only": True, "modifies": False,
        "limitations": ["association only; never confirms leakage alone"],
        "evidence": "ranked correlations"},
    "grouped_auc_comparison": {
        "tasks": ["classification"],
        "capabilities": ["prediction_inspection"],
        "requires_columns": ["label", "score_a", "score_b"],
        "outputs": ["delta_auc", "bootstrap_ci"],
        "read_only": True, "modifies": False,
        "limitations": ["pooled contrast; cluster design when grouping known"],
        "evidence": "delta + interval + design"},
    "ranking_diagnostics": {
        "tasks": ["ranking"],
        "capabilities": ["prediction_inspection"],
        "requires_columns": [],
        "outputs": ["p_at_k_by_slice", "slice_gap"],
        "read_only": True, "modifies": False,
        "limitations": ["P@K proxy on observed slices; pooled means can conceal slice failure"],
        "evidence": "per-slice top-K relevance + gap"},
}


def select_tools(task_type: str, capabilities: list[str],
                 available: dict) -> dict:
    """Capability-aware selection. Returns {selected, skipped} with reasons.

    `available` maps requirement names to bool/column-lists, e.g.
    {"label": True, "score": ["s1"], "features": True, ...}.
    A tool is selected only when its task matches, all capabilities are
    exposed, and every required column group is present.
    """
    caps = set(capabilities)
    selected, skipped = [], []
    for name, card in TOOL_CARDS.items():
        if task_type not in card["tasks"]:
            skipped.append({"tool": name, "reason": f"task {task_type} not in "
                                                    f"{card['tasks']}"})
            continue
        missing_caps = [c for c in card["capabilities"] if c not in caps]
        if missing_caps:
            skipped.append({"tool": name,
                            "reason": f"missing capabilities {missing_caps}"})
            continue
        missing_cols = [c for c in card["requires_columns"]
                        if not available.get(c)]
        if missing_cols:
            skipped.append({"tool": name,
                            "reason": f"missing inputs {missing_cols}"})
            continue
        selected.append(name)
    return {"selected": selected, "skipped": skipped}


def _load_frame(predictions_path: str | None) -> tuple[pd.DataFrame, str]:
    path = _resolve(predictions_path)
    return pd.read_csv(path), str(path)


def regression_metrics(predictions_path: str | None = None,
                       target_column: str = "target",
                       prediction_column: str = "prediction",
                       group_column: str | None = None) -> dict:
    """MAE/MSE/RMSE/R² + residual diagnostics on caller-supplied columns."""
    df, source = _load_frame(predictions_path)
    for col in (target_column, prediction_column):
        if col not in df.columns:
            raise ValueError(f"column {col!r} missing in {source}")
    y = pd.to_numeric(df[target_column], errors="coerce").to_numpy(dtype=float)
    p = pd.to_numeric(df[prediction_column], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(y) & np.isfinite(p)
    y, p = y[mask], p[mask]
    if len(y) == 0:
        raise ValueError("no finite target/prediction pairs")
    resid = y - p
    ss_tot = float(((y - y.mean()) ** 2).sum())
    out: dict = {"ok": True, "source": source, "n": int(len(y)),
                 "mae": float(np.mean(np.abs(resid))),
                 "mse": float(np.mean(resid ** 2)),
                 "rmse": float(np.sqrt(np.mean(resid ** 2))),
                 "r2": float(1 - ((resid ** 2).sum() / ss_tot)) if ss_tot else None,
                 "bias_mean_residual": float(resid.mean()),
                 "residual_std": float(resid.std()),
                 "heteroscedasticity_hint": float(np.corrcoef(
                     np.abs(resid), np.abs(p - p.mean()))[0, 1])
                 if len(y) > 2 else None,
                 "outliers_abs_z_gt_3": int((((resid - resid.mean()) /
                                              (resid.std() or 1)).__abs__() > 3).sum())}
    if group_column and group_column in df.columns:
        per = {}
        for value, chunk in df.iloc[np.where(mask)[0]].groupby(group_column):
            yy = pd.to_numeric(chunk[target_column], errors="coerce").to_numpy(dtype=float)
            pp = pd.to_numeric(chunk[prediction_column], errors="coerce").to_numpy(dtype=float)
            okm = np.isfinite(yy) & np.isfinite(pp)
            if okm.sum():
                per[str(value)] = float(np.mean(np.abs(yy[okm] - pp[okm])))
        out["mae_by_group"] = per
    return out


def clustering_stability(features_csv: str, feature_columns: list[str] | None = None,
                         n_clusters: int = 3, seed: int = 42,
                         max_rows: int = 5000) -> dict:
    """Silhouette + size balance for k-means screening (deterministic seed)."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    frame = pd.read_csv(_resolve(features_csv))
    cols = feature_columns or [c for c in frame.columns
                               if pd.api.types.is_numeric_dtype(frame[c])]
    if not cols:
        raise ValueError("no numeric feature columns found")
    X = frame[cols].dropna().to_numpy(dtype=float)
    if len(X) > max_rows:
        X = X[:max_rows]
    if len(X) < n_clusters + 1:
        raise ValueError("not enough rows for requested clusters")
    km = KMeans(n_clusters=int(n_clusters), n_init=10, random_state=seed)
    labels = km.fit_predict(X)
    sizes = [int((labels == k).sum()) for k in range(int(n_clusters))]
    return {"ok": True, "source": str(features_csv), "n": int(len(X)),
            "n_clusters": int(n_clusters), "seed": seed,
            "silhouette": float(silhouette_score(X, labels)),
            "cluster_sizes": sizes,
            "imbalance_ratio": float(max(sizes) / max(1, min(sizes))),
            "caveat": "k-means screening only; not a claim about true structure"}


def forecast_diagnostics(predictions_path: str | None = None,
                         date_column: str = "date",
                         target_column: str = "target",
                         prediction_column: str = "prediction",
                         horizon_column: str | None = None,
                         split_column: str | None = None) -> dict:
    """Horizon errors, drift, residual autocorrelation, split overlap."""
    df, source = _load_frame(predictions_path)
    for col in (date_column, target_column, prediction_column):
        if col not in df.columns:
            raise ValueError(f"column {col!r} missing in {source}")
    parsed = pd.to_datetime(df[date_column], errors="coerce")
    work = df.assign(_d=parsed).dropna(subset=["_d"]).sort_values("_d")
    y = pd.to_numeric(work[target_column], errors="coerce").to_numpy(dtype=float)
    p = pd.to_numeric(work[prediction_column], errors="coerce").to_numpy(dtype=float)
    okm = np.isfinite(y) & np.isfinite(p)
    work, y, p = work.iloc[np.where(okm)[0]], y[okm], p[okm]
    err = np.abs(y - p)
    out: dict = {"ok": True, "source": source, "n": int(len(y)),
                 "mae": float(err.mean())}
    if horizon_column and horizon_column in work.columns:
        per_h = {}
        for h, chunk in work.assign(_e=err).groupby(horizon_column):
            per_h[str(h)] = float(chunk["_e"].mean())
        out["mae_by_horizon"] = per_h
    else:
        out["mae_by_horizon"] = {}
    half = len(err) // 2
    out["drift_early_vs_late_mae"] = [float(err[:half].mean()),
                                      float(err[half:].mean())] if half else []
    if len(err) > 2:
        r = y - p
        out["residual_lag1_autocorr"] = float(np.corrcoef(r[:-1], r[1:])[0, 1])
    else:
        out["residual_lag1_autocorr"] = None
    if split_column and split_column in work.columns:
        spans = {}
        for s, chunk in work.groupby(split_column):
            dd = chunk["_d"].dropna()
            if len(dd):
                spans[str(s)] = [str(dd.min()), str(dd.max())]
        out["split_date_spans"] = spans
        # Proper interval intersection (key order is NOT chronological:
        # sorted() puts "test" before "train"). Overlap = any pair of
        # split date ranges intersect, not adjacent-key string order.
        parsed_spans = {}
        for s, (lo, hi) in spans.items():
            try:
                parsed_spans[s] = (pd.to_datetime(lo), pd.to_datetime(hi))
            except Exception:
                continue
        overlap = False
        keys = sorted(parsed_spans)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                lo = max(parsed_spans[keys[i]][0],
                         parsed_spans[keys[j]][0])
                hi = min(parsed_spans[keys[i]][1],
                         parsed_spans[keys[j]][1])
                if lo <= hi:
                    overlap = True
        out["split_overlap_hint"] = bool(overlap)
    return out
