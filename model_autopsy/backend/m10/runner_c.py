"""M14 third corpus runner (offline, investigator-safe)."""
from __future__ import annotations


def run_scenario_c(scenario_id: str, session, max_steps: int = 6) -> dict:
    from ..research import autonomous as AU
    from .scenarios_c import SCENARIOS
    scen = next(s for s in SCENARIOS if s["id"] == scenario_id)
    behavior = AU.run_autonomous(
        session, scen["artifact"], scen["task"], scen["brief"],
        max_steps=max_steps,
        investigation_title=f"M14 corpus-C: {scenario_id}")
    return {"scenario": scenario_id, "task": scen["task"],
            "brief": scen["brief"], **behavior}


def load_truth_c() -> dict:
    import json
    from pathlib import Path
    return json.loads(Path(
        "model_autopsy/tests/fixture_m10c/_sealed/truth.json"
    ).read_text(encoding="utf-8"))
