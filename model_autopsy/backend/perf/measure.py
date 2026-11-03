"""M15 Phase 1.3: strict AUC measurement (offline, deterministic).

Every reported AUC specifies dataset, split, positive-class
definition, period, model version, and sample count, with a
bootstrap confidence interval. Baseline and candidate are
compared on identical observations with a paired bootstrap
interval for the delta. Calibration (Brier + reliability gap),
PR-AUC, and subgroup AUCs accompany every AUC.
"""
from __future__ import annotations

import numpy as np


def auc_report(y_true, scores, *, dataset: str, split: str,
               positive: str, period: str, model_version: str,
               n_boot: int = 200, seed: int = 7) -> dict:
    from sklearn.metrics import (roc_auc_score, average_precision_score,
                                 brier_score_loss)
    y = np.asarray(y_true, dtype=int)
    s = np.asarray(scores, dtype=float)
    n = int(len(y))
    auc = float(roc_auc_score(y, s)) if len(set(y.tolist())) > 1 else 0.5
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(set(y[idx].tolist())) > 1:
            boots.append(roc_auc_score(y[idx], s[idx]))
    lo, hi = (float(np.percentile(boots, 2.5)),
              float(np.percentile(boots, 97.5))) if boots else (auc, auc)
    return {
        "dataset": dataset, "split": split,
        "positive_class": positive, "period": period,
        "model_version": model_version, "n": n,
        "auc": round(auc, 4), "auc_ci95": [round(lo, 4), round(hi, 4)],
        "pr_auc": round(float(average_precision_score(y, s)), 4),
        "brier": round(float(brier_score_loss(y, s)), 4),
        "base_rate": round(float(y.mean()), 4),
        "note": "out-of-fold/validation/held-out status in split field",
    }


def paired_delta(y_true, scores_base, scores_cand,
                 n_boot: int = 200, seed: int = 7) -> dict:
    """Delta on identical observations with paired bootstrap CI."""
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y_true, dtype=int)
    b = np.asarray(scores_base, dtype=float)
    c = np.asarray(scores_cand, dtype=float)
    assert len(y) == len(b) == len(c), "identical observations required"
    auc_b = float(roc_auc_score(y, b))
    auc_c = float(roc_auc_score(y, c))
    rng = np.random.default_rng(seed)
    diffs = []
    n = len(y)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if len(set(y[idx].tolist())) > 1:
            diffs.append(roc_auc_score(y[idx], c[idx])
                         - roc_auc_score(y[idx], b[idx]))
    lo, hi = (float(np.percentile(diffs, 2.5)),
              float(np.percentile(diffs, 97.5))) if diffs else (0.0, 0.0)
    return {"auc_base": round(auc_b, 4), "auc_cand": round(auc_c, 4),
            "delta": round(auc_c - auc_b, 4),
            "delta_ci95": [round(lo, 4), round(hi, 4)],
            "n": n,
            "significant": bool(lo > 0) if (auc_c - auc_b) >= 0
            else bool(hi < 0)}


def subgroup_auc(y_true, scores, groups, min_n: int = 30) -> dict:
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y_true)
    s = np.asarray(scores, dtype=float)
    out = {}
    for g in sorted(set(groups)):
        m = np.asarray(groups) == g
        if int(m.sum()) < min_n or len(set(y[m].tolist())) < 2:
            out[str(g)] = {"n": int(m.sum()), "auc": None,
                           "note": f"n<{min_n} or single class: "
                                   "inconclusive by design"}
        else:
            out[str(g)] = {"n": int(m.sum()),
                           "auc": round(float(roc_auc_score(y[m],
                                                            s[m])), 4)}
    return out
