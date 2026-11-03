"""M14 third held-out corpus registry (investigator-safe side)."""
from __future__ import annotations

BASE = "model_autopsy/tests/fixture_m10c"

SCENARIOS: list[dict] = [
    {"id": "c_interaction", "task": "regression",
     "brief": "Southern equipment fails under joint stress; pooled fit looks okay.",
     "artifact": BASE + "/c_interaction.csv"},
    {"id": "c_robustness", "task": "regression",
     "brief": "One machine family reads far off; is it a scale fault?",
     "artifact": BASE + "/c_robustness.csv"},
    {"id": "c_saturation", "task": "classification",
     "brief": "High-end scores plateau; ranking still looks sound?",
     "artifact": BASE + "/c_saturation.csv"},
    {"id": "c_combined", "task": "classification",
     "brief": "Eastern conversions look inflated.",
     "artifact": BASE + "/c_combined.csv"},
    {"id": "c_steady", "task": "classification",
     "brief": "Routine check: is this classifier healthy?",
     "artifact": BASE + "/c_steady.csv"},
    {"id": "c_thin", "task": "classification",
     "brief": "Tiny pilot: signal or noise?",
     "artifact": BASE + "/c_thin.csv"},
]
