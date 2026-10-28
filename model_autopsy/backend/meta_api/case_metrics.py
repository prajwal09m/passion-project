"""Case-study chart metrics — REAL numbers recomputed live from the frozen
Demand Zone OOF artifact.

Nothing in this module hardcodes a metric: every figure comes from
pandas/sklearn over study_files/outputs/study_v1/development/oof_predictions.csv
(and reports the file it used). Used by the dashboard's ML visualizations;
identical math to the diagnostic tools.

Bootstrap honesty: when a ticker-like column exists in the artifact, the
delta-AUC interval is computed with ticker-CLUSTER resampling (events of the
same ticker are dependent) and the sampling unit is reported; otherwise it
falls back to row-level resampling and the limitation is stated.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (brier_score_loss, log_loss)

from .. import ml_tools

TICKER_CANDIDATES = ("ticker", "symbol", "Ticker")
# noqa comment: bootstrap replicates use ml_tools.fast_auc (vectorized
# Mann-Whitney ranks) — previously one sklearn roc_auc_score call per
# replicate made each request take 25-60 s over the 41k-row artifact.
PAIRS = [
    ("LogisticRegression_A", "LightGBM_A"),
    ("LogisticRegression_C", "LightGBM_C"),
    ("LightGBM_A", "LightGBM_C"),
    ("LogisticRegression_B", "LightGBM_B"),
]


def _load() -> tuple[pd.DataFrame, Path]:
    path = Path(ml_tools.CASE_STUDY_CONFIG["oof_csv"])
    if not path.exists():
        raise FileNotFoundError(f"case-study artifact missing: {path}")
    return pd.read_csv(path), path


def _cluster_bootstrap_delta(y: np.ndarray, pa: np.ndarray, pb: np.ndarray,
                             clusters: np.ndarray | None, n_boot: int,
                             seed: int = 42) -> dict:
    """Delta AUC with a justified resampling design (vectorized fast_auc;
    identical sampling logic to the shared helper in ml_tools)."""
    return ml_tools.clustered_bootstrap_delta(y, pa, pb, clusters, n_boot, seed)


_CACHE: dict[tuple, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 3600.0


def build_case_metrics(n_boot: int = 500) -> dict:
    """Caching wrapper over the (now vectorized) full recomputation.

    The frozen artifact cannot change, so the result is memoized per
    (artifact mtime, n_boot) for the process lifetime with a 1-hour TTL.
    Cache hits are flagged so the UI can be honest about compute age.
    """
    path = Path(ml_tools.CASE_STUDY_CONFIG["oof_csv"])
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        mtime_ns = 0
    key = (str(path), mtime_ns, int(n_boot))
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit is not None and (now - hit[0]) < _CACHE_TTL_SECONDS:
        out = dict(hit[1])
        out["cache_hit"] = True
        out["cache_age_seconds"] = round(now - hit[0], 1)
        return out
    result = _build_case_metrics_uncached(n_boot)
    result["cache_hit"] = False
    result["computed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _CACHE[key] = (now, result)
    return result


def _build_case_metrics_uncached(n_boot: int = 500) -> dict:
    df, path = _load()
    cfg = ml_tools.CASE_STUDY_CONFIG
    y = df["label"].to_numpy()
    arms = [c for c in cfg["model_cols"] if c in df.columns]
    cluster_col = next((c for c in TICKER_CANDIDATES if c in df.columns), None)
    clusters = df[cluster_col].to_numpy() if cluster_col else None

    pooled = {arm: float(ml_tools.fast_auc(y, df[arm].to_numpy()))
              for arm in arms}
    per_fold: dict[str, dict[str, float]] = {}
    fold_sizes: dict[str, int] = {}
    if "fold" in df.columns:
        for fold, chunk in df.groupby("fold"):
            yy = chunk["label"].to_numpy()
            if len(set(yy.tolist())) < 2:
                continue
            fold_sizes[str(int(fold))] = int(len(chunk))
            per_fold[str(int(fold))] = {
                arm: float(ml_tools.fast_auc(yy, chunk[arm].to_numpy()))
                for arm in arms if len(set(chunk[arm].tolist()))}

    # The four bootstrap comparisons run in parallel threads: every numpy
    # call releases the GIL, so wall time ≈ the slowest single pair instead
    # of the sum of four. Each pair owns its rng, so determinism is kept.
    from concurrent.futures import ThreadPoolExecutor
    active = [(a, b) for a, b in PAIRS if a in pooled and b in pooled]
    with ThreadPoolExecutor(max_workers=min(4, max(1, len(active)))) as ex:
        boots = list(ex.map(
            lambda ab: _cluster_bootstrap_delta(
                y, df[ab[0]].to_numpy(), df[ab[1]].to_numpy(), clusters, n_boot),
            active))
    pairs = []
    for (a, b), boot in zip(active, boots):
        pairs.append({"score_a": a, "score_b": b,
                      "auc_a": pooled[a], "auc_b": pooled[b],
                      "delta": round(pooled[b] - pooled[a], 6), **boot})

    # Calibration + error profile for the configured champion arm.
    champion = "LightGBM_C" if "LightGBM_C" in df.columns else arms[-1]
    p = df[champion].to_numpy()
    edges = np.linspace(0.0, 1.0, 11)
    bucket = np.digitize(p, edges) - 1
    reliability = []
    for i in range(10):
        mask = bucket == i
        if not mask.any():
            continue
        reliability.append({"bin_low": round(float(edges[i]), 2),
                            "bin_high": round(float(edges[i + 1]), 2),
                            "n": int(mask.sum()),
                            "mean_score": round(float(p[mask].mean()), 4),
                            "fraction_positive":
                                round(float(y[mask].mean()), 4)})
    calibration = {
        "arm": champion, "reliability_bins": reliability,
        "brier": round(float(brier_score_loss(y, p)), 6),
        "log_loss": round(float(log_loss(y, p)), 6),
        "brier_note": "lower is better; probability of positive class"}

    # Label balance + chronology.
    label_balance = {"counts": {"negative_0": int((y == 0).sum()),
                                "positive_1": int((y == 1).sum())},
                     "positive_share":
                         round(float(y.mean()), 6),
                     "n_rows": int(len(y))}
    chronology: dict = {}
    date_col = next((c for c in ("date", "entry_date", "exit_date")
                     if c in df.columns), None)
    if "fold" in df.columns and date_col:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        spans = {}
        for fold, chunk in df.assign(_d=parsed).groupby("fold"):
            dd = chunk["_d"].dropna()
            if len(dd):
                spans[str(int(fold))] = [str(dd.min().date()),
                                         str(dd.max().date())]
        non_overlapping = all(
            spans[k][1] < spans[next_k][0]
            for k, next_k in zip(sorted(spans), sorted(spans)[1:]))
        chronology = {"date_column": date_col, "fold_date_spans": spans,
                      "non_overlapping_adjacent_folds": bool(non_overlapping),
                      "oscope_note": "non-overlapping dates in this "
                                     "prediction artifact do NOT by "
                                     "themselves prove the underlying "
                                     "training procedure was leak-free"}

    return {"ok": True, "source": str(path), "n_rows": int(len(y)),
            "cluster_column_used": cluster_col,
            "pooled_auc": pooled,
            "per_fold_auc": per_fold, "fold_sizes": fold_sizes,
            "delta_auc_pairs": pairs, "calibration": calibration,
            "label_balance": label_balance, "chronology": chronology,
            "recomputed_live": True,
            "historical_claim_note":
                "the archived 0.97 -> 0.676 suspicious-AUC narrative is a "
                "stored project claim over a dataset that is NOT present in "
                "this repository; it cannot be recomputed here and is "
                "presented as recorded history only"}
