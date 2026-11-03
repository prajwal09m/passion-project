"""M13 second corpus runner (offline, investigator-safe).

Uses scenarios_b (briefs + artifacts only). Sealed truth is read
only by the grader, never by the investigator path.
"""
from __future__ import annotations


def run_scenario_b(scenario_id: str, session, max_steps: int = 6) -> dict:
    from ..research import autonomous as AU
    from .scenarios_b import SCENARIOS
    scen = next(s for s in SCENARIOS if s["id"] == scenario_id)
    behavior = AU.run_autonomous(
        session, scen["artifact"], scen["task"], scen["brief"],
        max_steps=max_steps,
        investigation_title=f"M13 corpus-B: {scenario_id}")
    return {"scenario": scenario_id, "task": scen["task"],
            "brief": scen["brief"], **behavior}


def run_all_b(session_factory, max_steps: int = 6) -> dict:
    from .scenarios_b import SCENARIOS
    rows = []
    for scen in SCENARIOS:
        s = session_factory()
        try:
            rows.append(run_scenario_b(scen["id"], s, max_steps))
        finally:
            s.close()
    return {"scenarios": rows}


def load_truth_b() -> dict:
    import json
    from pathlib import Path
    p = Path("model_autopsy/tests/fixture_m10b/_sealed/truth.json")
    return json.loads(p.read_text(encoding="utf-8"))
