"""M10 runner: autonomous investigation of unseen projects.

Truth never enters this module. Each scenario gets the same offline
machinery as M9 (questions, invention, attribution, confounders).
"""
from __future__ import annotations


def run_scenario(scenario_id: str, session, max_steps: int = 6) -> dict:
    from ..research import autonomous as AU
    from .scenarios import SCENARIOS
    scen = next(s for s in SCENARIOS if s["id"] == scenario_id)
    behavior = AU.run_autonomous(
        session, scen["artifact"], scen["task"], scen["brief"],
        max_steps=max_steps,
        investigation_title=f"M10 unseen: {scenario_id}")
    return {"scenario": scenario_id, "task": scen["task"],
            "brief": scen["brief"], **behavior}


def run_all(session_factory, max_steps: int = 6) -> dict:
    from .scenarios import SCENARIOS
    from ..db import init_db
    init_db()
    rows = []
    for scen in SCENARIOS:
        s = session_factory()
        try:
            rows.append(run_scenario(scen["id"], s, max_steps))
        finally:
            s.close()
    return {"scenarios": rows}
