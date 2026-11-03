"""M14 Phase 4.1/4.4: live reasoning audit + opportunity tracking.

Analyzes a saved live run directory (offline, no paid calls):
stage-by-stage accounting of where discovery opportunities were
lost, distinguishing model reasoning failures from
infrastructure/orchestration failures.
"""
from __future__ import annotations

import json
from pathlib import Path

STAGES = ("context", "hypotheses", "tool_selection", "execution",
          "interpretation", "linking", "planning", "reporting")


def audit_run(run_dir: str) -> dict:
    d = Path(run_dir)
    out: dict = {"run_dir": run_dir, "stages": {}, "opportunities": []}
    try:
        events = json.loads((d / "events_dump.json").read_text())
    except OSError:
        events = []
    try:
        actions = json.loads((d / "actions.json").read_text())
    except OSError:
        actions = []
    try:
        hyps = json.loads((d / "hypotheses.json").read_text())
    except OSError:
        hyps = []
    kinds = {e.get("kind") for e in events} if isinstance(events,
                                                         list) else set()
    ran = [a for a in actions] if isinstance(actions, list) else []
    out["stages"]["context"] = {
        "present": bool(kinds), "n_events": len(events),
        "failure": None if kinds else "infrastructure: no events "
                   "preserved"}
    out["stages"]["hypotheses"] = {
        "n": len(hyps) if isinstance(hyps, list) else 0,
        "failure": None if hyps else "model: no hypotheses proposed"}
    tools = [a.get("tool_name") or a.get("tool") for a in ran]
    out["stages"]["tool_selection"] = {
        "tools": tools,
        "failure": None if tools else "model: no experiments selected"}
    out["stages"]["execution"] = {
        "ran": len([a for a in ran if a.get("status") == "ran"]),
        "failure": None if any(
            a.get("status") == "ran" for a in ran)
        else "infrastructure: executions failed or refused"}
    linked = sum(1 for h in (hyps if isinstance(hyps, list) else [])
                 if isinstance(h, dict) and h.get("evidence_refs"))
    out["stages"]["linking"] = {
        "hypotheses_with_evidence": linked,
        "failure": None if linked else "model: evidence not linked "
                   "to hypotheses"}
    out["stages"]["reporting"] = {
        "has_report": (d / "eval_report.json").exists(),
        "failure": None if (d / "eval_report.json").exists()
        else "infrastructure: no report preserved"}
    out["stages"]["interpretation"] = out["stages"]["linking"]
    out["stages"]["planning"] = {
        "failure": None, "note": "planner stops recorded in events"}
    # Opportunity tracking: one row per executed tool.
    for a in ran:
        out["opportunities"].append(track(
            f"{a.get('tool_name') or a.get('tool')}",
            detectable=True,
            recognized=a.get("status") == "ran",
            investigated=a.get("status") == "ran",
            proposed=True, ran=a.get("status") == "ran",
            interpreted=bool(a.get("result")),
            reported=(d / "eval_report.json").exists()))
    return out


def track(name: str, detectable: bool, recognized: bool,
          investigated: bool, proposed: bool, ran: bool,
          interpreted: bool, reported: bool) -> dict:
    stages = {"detectable": detectable, "recognized": recognized,
              "investigated": investigated, "proposed": proposed,
              "ran": ran, "interpreted": interpreted,
              "reported": reported}
    lost_at = next((k for k, v in stages.items() if not v), None)
    return {"opportunity": name, "stages": stages, "lost_at": lost_at,
            "diagnosable": lost_at is not None}
