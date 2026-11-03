"""M10 statistics: small, documented, honestly limited.

Each helper returns the estimate PLUS its interpretation and limits.
No p-values are reported: with benchmark-sized samples, effect sizes
with uncertainty intervals are more honest than significance flags.

Limits: normal-approximation intervals; independence assumed (not
verified for time series — see residual autocorrelation tools for
lag checks); subgroup comparisons are observational, not causal.
"""
from __future__ import annotations


def mean_ci(values: list[float], conf: float = 0.95) -> dict:
    """Mean with a normal-approximation interval."""
    import math
    n = len(values)
    if n < 3:
        return {"ok": False, "reason": "n < 3: no interval computed",
                "n": n}
    m = sum(values) / n
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    se = math.sqrt(var / n)
    z = 1.96 if conf == 0.95 else 1.645
    return {"ok": True, "n": n, "mean": m,
            "interval": [m - z * se, m + z * se],
            "interpretation": f"mean {m:.3f} ± {z * se:.3f} "
                              f"(~{int(conf * 100)}% interval, "
                              "independent-sample approximation)",
            "limits": "assumes independent draws; invalid under "
                      "unmodeled autocorrelation or selection"}


def subgroup_gap(a: list[float], b: list[float], name_a: str = "A",
                 name_b: str = "B") -> dict:
    """Difference in means with uncertainty + standardized effect."""
    import math
    ca, cb = mean_ci(a), mean_ci(b)
    if not (ca.get("ok") and cb.get("ok")):
        return {"ok": False, "reason": "insufficient data in a subgroup"}
    diff = ca["mean"] - cb["mean"]
    se = math.sqrt(((ca["interval"][1] - ca["mean"]) / 1.96) ** 2
                   + ((cb["interval"][1] - cb["mean"]) / 1.96) ** 2)
    pooled = math.sqrt(
        (sum((v - ca["mean"]) ** 2 for v in a)
         + sum((v - cb["mean"]) ** 2 for v in b))
        / max(len(a) + len(b) - 2, 1))
    d = diff / pooled if pooled else 0.0
    mag = ("negligible" if abs(d) < 0.2 else "small" if abs(d) < 0.5
           else "medium" if abs(d) < 0.8 else "large")
    return {"ok": True, "diff": diff,
            "interval": [diff - 1.96 * se, diff + 1.96 * se],
            "cohens_d": d, "magnitude": mag,
            "interpretation": f"{name_a} minus {name_b} = {diff:.3f} "
                              f"(d={d:.2f}, {mag}); observational gap, "
                              "not a causal effect",
            "limits": "confounders (e.g. prevalence, segment mix) not "
                      "adjusted; see confounder analysis"}
