"""M13 second held-out corpus registry (investigator-safe side).

Different structures from fixture_m10: unfamiliar segment names
(zone), date/split aliases (day/fold), target/pred naming. Only
briefs + artifact paths travel with the investigator.
"""
from __future__ import annotations

BASE = "model_autopsy/tests/fixture_m10b"

SCENARIOS: list[dict] = [
    {"id": "b_region_gap", "task": "classification",
     "brief": "Conversion looks uneven across regions.",
     "artifact": BASE + "/b_region_gap.csv"},
    {"id": "b_score_inflate", "task": "classification",
     "brief": "Scores run hot; is the ranking still sound?",
     "artifact": BASE + "/b_score_inflate.csv"},
    {"id": "b_gradual_drift", "task": "forecasting",
     "brief": "Forecasts sag as the level climbs all year.",
     "artifact": BASE + "/b_gradual_drift.csv"},
    {"id": "b_unit_shift", "task": "regression",
     "brief": "Southern estimates look wrong after a vendor change.",
     "artifact": BASE + "/b_unit_shift.csv"},
    {"id": "b_steady", "task": "classification",
     "brief": "Routine check: is this classifier healthy?",
     "artifact": BASE + "/b_steady.csv"},
    {"id": "b_thin", "task": "classification",
     "brief": "Tiny pilot: signal or noise?",
     "artifact": BASE + "/b_thin.csv"},
]
