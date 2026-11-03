"""M10 unseen-project registry (investigator-safe side).

Only plain-language briefs + artifact paths. Mechanism descriptions,
grades, and key tools live in _sealed/truth.json, readable solely by
the evaluator. The investigator path must never import `sealed`.
"""
from __future__ import annotations

BASE = "model_autopsy/tests/fixture_m10"

SCENARIOS: list[dict] = [
    {"id": "m10_ward_gap", "task": "classification",
     "brief": "Tag accuracy looks uneven across wards; pooled AUC is 0.91.",
     "artifact": BASE + "/m10_ward_gap.csv"},
    {"id": "m10_proxy_signal", "task": "classification",
     "brief": "Default predictions look strong; is the skill real?",
     "artifact": BASE + "/m10_proxy_signal.csv"},
    {"id": "m10_threshold_skew", "task": "classification",
     "brief": "Operators complain the scores run hot at threshold 0.5.",
     "artifact": BASE + "/m10_threshold_skew.csv"},
    {"id": "m10_stale_lag", "task": "forecasting",
     "brief": "Forecasts trail sudden moves; misses persist for days.",
     "artifact": BASE + "/m10_stale_lag.csv"},
    {"id": "m10_district_scale", "task": "regression",
     "brief": "Estimates for one district look off after a logging change.",
     "artifact": BASE + "/m10_district_scale.csv"},
    {"id": "m10_combo", "task": "forecasting",
     "brief": "Recent misses coincide with growth; one district looks odd.",
     "artifact": BASE + "/m10_combo.csv"},
    {"id": "m10_steady", "task": "regression",
     "brief": "Routine check: is this estimator healthy?",
     "artifact": BASE + "/m10_steady.csv"},
    {"id": "m10_sparse", "task": "classification",
     "brief": "Tiny pilot: real signal or more evidence needed?",
     "artifact": BASE + "/m10_sparse.csv"},
]
