"""Autonomous investigation workflow (M6 Part 3).

Fourteen logical stages mapped onto the existing engine FSM (no FSM
redefinition — the engine remains the single source of truth):

  reconnaissance → understanding → anomaly → hypotheses → competition →
  planning → selection → execution → interpretation → update →
  targeted → review → diagnosis → validation.

Guards: no stage skip (each requires its predecessor's evidence), no
redundant experiment (exact-arg dedup + qualitative redundancy note),
no premature completion (diagnosis + validation gates), bounded loops
(max 3 targeted re-entries, then inconclusive with stated limits).
Every transition is auditable via events; illegal engine transitions
are never attempted (use engine.ensure_finalizable for the tail).
"""
from __future__ import annotations

STAGES = ("reconnaissance", "understanding", "anomaly", "hypotheses",
          "competition", "planning", "selection", "execution",
          "interpretation", "update", "targeted", "review",
          "diagnosis", "validation")

# Maps each stage to the engine status that must hold while in it.
STAGE_ENGINE_STATUS = {
    "reconnaissance": ("created", "context_ready"),
    "understanding": ("context_ready", "hypotheses_proposed"),
    "anomaly": ("context_ready", "hypotheses_proposed", "investigating"),
    "hypotheses": ("hypotheses_proposed", "investigating"),
    "competition": ("hypotheses_proposed", "investigating"),
    "planning": ("investigating",),
    "selection": ("investigating",),
    "execution": ("investigating",),
    "interpretation": ("investigating", "revising"),
    "update": ("investigating", "revising"),
    "targeted": ("revising", "investigating"),
    "review": ("revising", "finalizing"),
    "diagnosis": ("finalizing",),
    "validation": ("finalizing", "complete"),
}


def check_stage(stage: str, engine_status: str) -> bool:
    return engine_status in STAGE_ENGINE_STATUS.get(stage, ())


def next_stage(current: str, evidence: dict) -> tuple[str, str]:
    """Advance or loop back with a stated reason. Never skips stages."""
    order = list(STAGES)
    i = order.index(current)
    if current == "execution" and evidence.get("failed_tool"):
        return "selection", "failed tool recorded; reselect with corrected args"
    if current == "update" and evidence.get("contradiction") \
            and (evidence.get("targeted_rounds", 0) < 3):
        return "targeted", "contradiction needs a discriminating follow-up"
    if current == "update" and evidence.get("targeted_rounds", 0) >= 3:
        return "review", "targeted budget used; proceed to review as inconclusive if unresolved"
    if current == "targeted":
        return "selection", "targeted question framed; select the discriminating test"
    if i + 1 < len(order):
        return order[i + 1], "predecessor evidence recorded"
    return current, "terminal stage"


def completion_allowed(hypotheses: list[dict], validation: dict) -> tuple[bool, str]:
    open_h = [h for h in hypotheses
              if h.get("status") in ("proposed", "investigating")]
    if open_h and not validation.get("inconclusive_declared"):
        return False, f"{len(open_h)} hypotheses still open; declare inconclusive with reasons first"
    if not validation.get("report_ok"):
        return False, "report validation must pass (or invalid original preserved with errors)"
    return True, "diagnosis + validation gates satisfied"
