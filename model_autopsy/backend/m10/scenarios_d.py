"""M15 fourth corpus registry (investigator-safe side)."""
from __future__ import annotations

BASE = "model_autopsy/tests/fixture_m10d"

SCENARIOS: list[dict] = [
    {"id": "d_null", "task": "classification",
     "brief": "Routine check: is this classifier healthy?",
     "artifact": BASE + "/d_null.csv"},
    {"id": "d_thin", "task": "classification",
     "brief": "Tiny pilot: signal or noise?",
     "artifact": BASE + "/d_thin.csv"},
    {"id": "d_combined", "task": "classification",
     "brief": "Site B conversions look inflated.",
     "artifact": BASE + "/d_combined.csv"},
    {"id": "d_confounded", "task": "regression",
     "brief": "Southern estimates look wrong; sizes differ by zone.",
     "artifact": BASE + "/d_confounded.csv"},
]
