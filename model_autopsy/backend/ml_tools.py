"""ML diagnostics tools — real pandas/sklearn computations on real artifacts.

No tool here invents a metric: everything recomputes from the configured
prediction/artifact files and reports provenance (row counts + source path).
Leakage is never claimed by suspiciousness alone; conclusions live with
Meta's hypothesis status after real evidence is recorded.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (brier_score_loss, precision_score, recall_score,
                             roc_auc_score)

from . import config
from .db import to_json_blob

PROJECT_ROOT = config.PROJECT_ROOT


def fast_auc(y: np.ndarray, score: np.ndarray) -> float:
    """Vectorized ROC-AUC (Mann–Whitney U, tie-aware group counting).

    Numerically identical to sklearn.metrics.roc_auc_score for binary y
    (ties get 0.5 via within-equal-group counting), but ~100x cheaper so
    delta-AUC bootstrap replication is practical.

    Per replicate: one argsort, then numerator summed over the maximal
    equal-score groups — positives receive every earlier-group negative
    (pos > neg ⇒ 1) plus half of same-group negatives. Returns NaN when a
    replicate has a single class.
    """
    y = np.asarray(y)
    s = np.asarray(score, dtype=float)
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(s)   # stable not required: equal values are the tie groups
    sv = s[order]
    yv = y[order]
    neq = sv[1:] != sv[:-1]
    group_id = np.concatenate(([0], np.cumsum(neq)))
    n_groups = int(group_id[-1]) + 1
    neg_g = np.bincount(group_id, weights=(yv == 0).astype(np.float64),
                        minlength=n_groups)
    pos_g = np.bincount(group_id, weights=(yv == 1).astype(np.float64),
                        minlength=n_groups)
    neg_before = np.concatenate(([0.0], np.cumsum(neg_g)))[:-1]
    numerator = float((pos_g * (neg_before + 0.5 * neg_g)).sum())
    return numerator / (n_pos * n_neg)


def clustered_bootstrap_delta(y: np.ndarray, score_a: np.ndarray,
                              score_b: np.ndarray,
                              cluster_values: np.ndarray | None,
                              n_boot: int, seed: int = 42) -> dict:
    """Delta-AUC (B − A) bootstrap with an honest resampling design.

    When `cluster_values` identifies a grouping (e.g. ticker), whole units
    are re-drawn so events of one unit stay together (within-unit event
    dependence is preserved); otherwise rows are resampled and the
    limitation is stated. Uses fast_auc per replicate; seed and unit are
    reported for reproducibility.
    """
    y = np.asarray(y)
    sa = np.asarray(score_a)
    sb = np.asarray(score_b)
    rng = np.random.default_rng(seed)
    deltas: list[float] = []
    use_cluster = cluster_values is not None
    if use_cluster:
        units = np.unique(cluster_values)
        if len(units) >= 5:
            # Vectorized ragged-gather: precompute each unit's slice inside
            # the cluster-sorted ordering, then assemble replicate indices
            # with the repeat/cumsum idiom (no Python-level concatenation
            # per replicate).
            order = np.argsort(cluster_values, kind="mergesort")
            cl_sorted = cluster_values[order]
            uniq, first_pos, counts = np.unique(
                cl_sorted, return_index=True, return_counts=True)
            n_units = len(uniq)
            for _ in range(int(n_boot)):
                picked = rng.integers(0, n_units, size=n_units)
                starts = first_pos[picked]
                sizes = counts[picked]
                total = int(sizes.sum())
                # standard ragged-range vectorization (no per-replicate
                # Python concatenation):
                cumstarts = np.concatenate(([0], np.cumsum(sizes)[:-1]))
                offsets = np.arange(total) - np.repeat(cumstarts, sizes)
                idx = order[np.repeat(starts, sizes) + offsets]
                ya = y[idx]
                if ya.min() != 0 or ya.max() != 1:      # degenerate replicate
                    continue
                deltas.append(fast_auc(ya, sb[idx]) - fast_auc(ya, sa[idx]))
        else:
            use_cluster = False
    if not use_cluster:
        n = len(y)
        idx_all = np.arange(n)
        for _ in range(int(n_boot)):
            s = rng.choice(idx_all, size=n, replace=True)
            ya = y[s]
            if ya.min() != 0 or ya.max() != 1:          # degenerate replicate
                continue
            deltas.append(fast_auc(ya, sb[s]) - fast_auc(ya, sa[s]))
    arr = np.asarray(deltas, dtype=float)
    # Guard: all replicates degenerate would mean no interval can exist.
    if not arr.size:
        return {"ci_low": None, "ci_high": None, "n_boot": 0,
                "design": "no usable bootstrap replicates (degenerate classes)",
                "sampling_unit": "ticker" if use_cluster else "row",
                "reproducibility": f"seed={seed} (numpy default_rng)"}
    lo, hi = np.percentile(arr[np.isfinite(arr)], [2.5, 97.5])
    design = ("ticker-cluster bootstrap (re-draws whole tickers; events of "
              "one ticker treated as dependent)"
              if use_cluster else
              "row-level bootstrap (LIMITATION: ignores within-ticker "
              "event dependence; usable cross-sectional approximation)")
    return {"ci_low": round(float(lo), 6), "ci_high": round(float(hi), 6),
            "n_boot": int(arr.size), "design": design,
            "sampling_unit": ("ticker" if use_cluster else "row"),
            "reproducibility": f"seed={seed} (numpy default_rng)"}

CASE_STUDY_CONFIG = {
    "name": "Demand Zone AI (v1.0.2 frozen protocol)",
    "oof_csv": str(PROJECT_ROOT / "study_files" / "outputs" / "study_v1"
                   / "development" / "oof_predictions.csv"),
    "event_csv": str(PROJECT_ROOT / "study_files" / "outputs" / "study_v1"
                     / "development" / "event_table.csv"),
    "models_dir": str(PROJECT_ROOT / "study_files" / "outputs" / "study_v1" / "models"),
    "label_col": "label",
    "fold_col": "fold",
    "model_cols": ["LogisticRegression_A", "LightGBM_A", "LogisticRegression_B",
                   "LightGBM_B", "LogisticRegression_C", "LightGBM_C",
                   "LogisticRegression_D", "LightGBM_D"],
}


def _resolve_project_csv(path: str | None, fallback: str) -> Path:
    """Resolve a caller-supplied CSV path inside the wrapped ProjectRoot."""
    if path and str(path).strip():
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        candidate = candidate.resolve()
    else:
        candidate = Path(fallback)
    if not candidate.exists():
        raise FileNotFoundError(f"artifact not found: {candidate}")
    try:
        candidate.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        raise PermissionError(f"artifact {candidate} outside the project root "
                              "(read-only mode; supply a project-relative path)")
    return candidate


def load_predictions_csv(predictions_path: str | None) -> tuple[pd.DataFrame, Path]:
    """Load a real prediction CSV, validating Case Study required columns."""
    csv_path = _resolve_project_csv(predictions_path, CASE_STUDY_CONFIG["oof_csv"])
    df = pd.read_csv(csv_path)
    for col in ("label", "fold"):
        if col not in df.columns:
            raise ValueError(f"{csv_path.name}: required column '{col}' missing")
    labels = df["label"].astype(int)
    if set(labels.unique()) != {0, 1}:
        raise ValueError(f"{csv_path.name}: 'label' is not binary (values "
                         f"{sorted(labels.unique().tolist())[:5]}...)")
    return df, csv_path


def artifact_summary(predictions_path: str | None = None,
                     labels: str | None = None) -> dict:
    """Schema/quality overview of the configured prediction artifact."""
    df, csv_path = load_predictions_csv(predictions_path)
    label_col = labels or "label"
    out = {"ok": True, "path": str(csv_path), "filename": csv_path.name,
           "n_rows": int(df.shape[0]), "n_columns": int(df.shape[1]),
           "columns": list(df.columns),
           "label_counts": to_json_blob(df[label_col].value_counts().to_dict()),
           "unique_labels": int(df[label_col].nunique()),
           "n_folds": int(df["fold"].nunique()) if "fold" in df.columns else None,
           "folds_present": [int(f) for f in sorted(df["fold"].unique())]
                            if "fold" in df.columns else None,
           "not_a_model_column": [c for c in df.columns
                                  if c not in set(CASE_STUDY_CONFIG["model_cols"])]}
    return out


def classification_metrics(predictions_path: str | None = None,
                           labels: str | None = None,
                           score_column: str = "LightGBM_C",
                           threshold: float = 0.5,
                           split_by: str | None = None) -> dict:
    """Real ROC-AUC (OOF), Brier, precision, recall — overall, optionally
    recomputed per split (e.g. per fold or per year)."""
    label_col = labels or "label"
    df, csv_path = load_predictions_csv(predictions_path)
    if score_column not in df.columns:
        raise ValueError(f"score_column {score_column!r} not in {csv_path.name}")
    y = df[label_col].to_numpy()
    p = df[score_column].to_numpy()
    pred = (p >= float(threshold)).astype(int)
    out = {"ok": True, "source": str(csv_path), "score_column": score_column,
           "n": int(len(y)),
           "roc_auc": (float(roc_auc_score(y, p))
                       if len(set(y.tolist())) > 1 else None),
           "brier": float(brier_score_loss(y, p)),
           "brier_convention": "lower is better; probability of positive class",
           "precision_at_threshold": float(precision_score(y, pred, zero_division=0)),
           "recall_at_threshold": float(recall_score(y, pred, zero_division=0)),
           "threshold": float(threshold)}
    if split_by and split_by in df.columns:
        per = {}
        for value, chunk in df.groupby(split_by):
            yy = chunk[label_col].to_numpy()
            if len(set(yy.tolist())) > 1:
                per[str(value)] = float(roc_auc_score(yy, chunk[score_column].to_numpy()))
        out["per_split_auc"] = per
    return out


def time_split_validation(predictions_path: str | None = None,
                          labels: str | None = None,
                          date_column: str | None = None) -> dict:
    """Chronology checks of the fold/date columns (fold date spans, sizes).
    """
    label_col = labels or "label"
    df, csv_path = load_predictions_csv(predictions_path)
    if date_column is None:
        date_column = next((c for c in ("date", "entry_date", "exit_date")
                            if c in df.columns), None)
    out: dict = {"ok": True, "source": str(csv_path), "n_rows": int(len(df))}
    date_parsed = None
    if date_column and date_column in df.columns:
        date_parsed = pd.to_datetime(df[date_column], errors="coerce")
        out["date_column"] = date_column
        out["n_valid_dates"] = int(date_parsed.notna().sum())
        out["date_min"] = str(date_parsed.min())
        out["date_max"] = str(date_parsed.max())
    if "fold" in df.columns:
        spans: dict[str, list] = {}
        if date_parsed is not None:
            for fold, chunk in df.assign(_d=date_parsed).groupby("fold"):
                dd = chunk["_d"].dropna()
                if len(dd):
                    spans[str(int(fold))] = [str(dd.min().date()),
                                             str(dd.max().date())]
            out["fold_date_spans"] = spans
        out["fold_sizes"] = {str(int(f)): int(c)
                             for f, c in df["fold"].value_counts().sort_index().items()}
    return out


def feature_target_suspiciousness(feature_csv: str, label_csv: str | None = None,
                                  feature_col: str | None = None,
                                  n_top: int = 12) -> dict:
    """Correlation-style suspiciousness scan of features vs labels.

    Returns the strongest |point-biserial|-style correlations. This is
    screening evidence only — it can NEVER alone confirm leakage.
    """
    from scipy import stats as sps
    feat_path = _resolve_project_csv(feature_csv, "")
    frame = pd.read_csv(feat_path)
    if label_csv:
        label_frame = pd.read_csv(_resolve_project_csv(label_csv, ""))["label"]
        merged = frame.assign(_label=label_frame.values)
        y = merged["_label"]
        frame = merged
    else:
        y = frame["label"]
    n_features = int(frame.shape[1])
    rows = []
    for col in frame.columns:
        if col == "_label" or not pd.api.types.is_numeric_dtype(frame[col]):
            continue
        series = frame[col].dropna()
        if series.nunique() <= 1:
            continue
        r, p = sps.pointbiserialr(frame["_label"][series.index], series)
        rows.append({"feature": col, "r": float(r), "abs_r": abs(float(r)),
                     "n": int(series.shape[0])})
    rows.sort(key=lambda row: -row["abs_r"])
    return {"ok": True, "source": str(feat_path), "n_features": n_features,
            "top_correlations": rows[: max(1, int(n_top))],
            "caveat": "statistical association only; leakage claims require "
                      "feature provenance and re-evaluation evidence"}


def calibration_and_error_analysis(predictions_path: str | None = None,
                                   labels: str | None = None,
                                   score_column: str = "LightGBM_C",
                                   bins: int = 10) -> dict:
    """Calibration curve (binned reliability) plus per-fold AUC."""
    label_col = labels or "label"
    df, csv_path = load_predictions_csv(predictions_path)
    if score_column not in df.columns:
        raise ValueError(f"score_column {score_column!r} not in {csv_path.name}")
    y = df[label_col].to_numpy()
    p = df[score_column].to_numpy()
    edges = np.linspace(0.0, 1.0, int(bins) + 1)
    bucket = np.digitize(p, edges) - 1
    rel: list[dict] = []
    for i in range(int(bins)):
        mask = bucket == i
        if mask.sum() == 0:
            continue
        rel.append({"bin_low": float(edges[i]), "bin_high": float(edges[i + 1]),
                    "n": int(mask.sum()),
                    "mean_score": float(p[mask].mean()),
                    "fraction_positive": float(y[mask].mean())})
    per_fold: dict[str, float] = {}
    if "fold" in df.columns:
        for fold, chunk in df.groupby("fold"):
            yy = chunk[label_col].to_numpy()
            if len(set(yy.tolist())) > 1:
                per_fold[str(int(fold))] = float(
                    roc_auc_score(yy, chunk[score_column].to_numpy()))
    return {"ok": True, "source": str(csv_path), "score_column": score_column,
            "brier": float(brier_score_loss(y, p)),
            "reliability_bins": rel, "per_fold_auc": per_fold}


def dataset_validation(predictions_path: str, score_columns: list[str] | None = None,
                       label_column: str | None = None,
                       date_column: str | None = None,
                       fold_column: str | None = None) -> dict:
    """Generic project input validation (not Demand-Zone-specific).

    Reports schema preview, null counts, label-binarity, fold coverage and
    date coverage for an arbitrary project-root-relative CSV. Never
    infers the target silently — missing required fields are reported as
    factual gaps with clear failures, not guessed."""
    from .db import to_json_blob as _jsonsafe
    csv_path = _resolve_project_csv(predictions_path, "")
    df = pd.read_csv(csv_path)
    label = label_column or "label"
    fold = fold_column or "fold"
    out: dict = {"ok": True, "source": str(csv_path),
                 "filename": csv_path.name,
                 "n_rows": int(df.shape[0]),
                 "n_columns": int(df.shape[1]),
                 "columns": [
                     {"name": c, "dtype": str(df[c].dtype),
                      "n_missing": int(df[c].isna().sum()),
                      "n_unique": int(df[c].nunique(dropna=True))}
                     for c in df.columns],
                 "n_duplicate_rows": int(df.duplicated().sum())}
    checks: dict = {}
    if label in df.columns:
        y = df[label]
        checks["label_column"] = {"name": label,
                                  "present": True,
                                  "binary_01": set(y.dropna().unique().tolist()) <= {0, 1},
                                  "values": _jsonsafe(y.value_counts(dropna=False).to_dict())}
    else:
        checks["label_column"] = {"name": label, "present": False,
                                  "note": "required by all metric tools; "
                                          "supply label_column or add the column"}
    if fold in df.columns:
        checks["fold_column"] = {"name": fold, "present": True,
                                  "n_folds": int(df[fold].nunique()),
                                  "sizes": {str(int(f)): int(c) for f, c in
                                            df[fold].value_counts().sort_index().items()}}
    else:
        checks["fold_column"] = {"name": fold, "present": False,
                                  "note": "optional; needed for per-fold and "
                                          "chronology tools"}
    date_col = date_column or next((c for c in ("date", "entry_date", "signal_date")
                                    if c in df.columns), None)
    if date_col and date_col in df.columns:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        checks["date_column"] = {"name": date_col, "present": True,
                                 "n_valid": int(parsed.notna().sum()),
                                 "min": str(parsed.min()), "max": str(parsed.max())}
    else:
        checks["date_column"] = {"name": date_column, "present": False,
                                  "note": "optional; needed for chronology analysis"}
    if score_columns:
        missing_sc = [c for c in score_columns if c not in df.columns]
        checks["score_columns"] = {"present": [c for c in score_columns
                                                if c in df.columns],
                                    "missing": missing_sc}
    out["checks"] = checks
    return out


def grouped_auc_comparison(predictions_path: str | None = None,
                           labels: str | None = None,
                           score_a: str = "LogisticRegression_A",
                           score_b: str = "LightGBM_A",
                           n_boot: int = 2000) -> dict:
    """Pooled Delta AUC between two real score columns (pooled OOF) with a
    bootstrap interval — the real Demand Zone contrast simplified."""
    label_col = labels or "label"
    df, csv_path = load_predictions_csv(predictions_path)
    missing = [c for c in (score_a, score_b) if c not in df.columns]
    if missing:
        raise ValueError(f"score columns missing: {missing}")
    y = df[label_col].to_numpy()
    pa = df[score_a].to_numpy()
    pb = df[score_b].to_numpy()
    y = y.astype(int)
    auc_a = fast_auc(y, pa)
    auc_b = fast_auc(y, pb)
    # Cluster-aware design when a ticker-like grouping column exists.
    cluster = next((c for c in ("ticker", "symbol", "Ticker")
                    if c in df.columns), None)
    cluster_values = df[cluster].to_numpy() if cluster else None
    boot = clustered_bootstrap_delta(y, pa, pb, cluster_values, n_boot)
    return {"ok": True, "source": str(csv_path), "score_a": score_a,
            "score_b": score_b, "n": int(len(y)), "auc_a": float(auc_a),
            "auc_b": float(auc_b),
            "delta": float(auc_b - auc_a),
            "bootstrap_ci": [boot["ci_low"], boot["ci_high"]],
            "n_boot": boot["n_boot"],
            "sampling_unit": boot["sampling_unit"],
            "design": boot["design"]}
