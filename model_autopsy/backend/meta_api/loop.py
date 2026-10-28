"""Tool-calling investigation loop for Meta (Muse Spark).

Bounded orchestration that drives one investigation segment:
  1. Build honest investigation context (engine-recorded evidence only).
  2. Ask Meta to act, with the mode's tool schemas.
  3. Validate every requested tool call against the allowlist.
  4. Execute approved tools with real inputs; record evidence.
  5. Return results to Meta with `function_call_output` items.
  6. Repeat while Meta keeps calling tools and budgets remain.
  7. Record Meta's final message verbatim as the interpretation.

Meta is never a source of truth by confidence alone — every hypothesis,
finding and metric must trace to a recorded action or be absent.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from .. import config, engine, tools_registry
from ..db import Investigation, record_event, to_json_blob
from . import client as meta_client

MODE_INSTRUCTIONS = {
    "software": (
        "You are the runtime investigator of Model Autopsy, a software autopsy. "
        "Review the supplied git change set against the stated objective. Use the "
        "provided tools to inspect files or run the automated test suite (read-only "
        "operations; you cannot choose the command). Report concrete defects with "
        "file/line references, and register them using the propose_hypothesis tool "
        "(one call per hypothesis, with a falsifiable statement and predicted "
        "observation). When a fix is warranted, record a propose_revision_instructions "
        "bundle for a HUMAN reviewer — applying changes is never automatic. Be "
        "explicit when evidence is missing. Never claim a test passed unless you "
        "requested the test tool and saw its recorded result."),
    "ml": (
        "You are the runtime investigator of Model Autopsy, an ML model autopsy. "
        "Given the recorded evaluation context, propose competing explanations about "
        "why the model performs as observed by calling the propose_hypothesis tool "
        "(each with a falsifiable statement, a predicted observation, and a note "
        "that its confidence is uncalibrated). Select diagnostic tools that can "
        "DISCRIMINATE between competing hypotheses — do not run every tool. "
        "Interpret only recorded tool results; distinguish confirmed findings from "
        "hypotheses. Never claim leakage from suspiciousness alone without "
        "evaluation evidence."),
}


def _initial_context_items(inv: Investigation) -> list[dict]:
    context = (inv.config or {}).get("context") or {}
    items = [
        {"role": "user", "content": json.dumps({
            "mode": inv.mode, "objective": inv.question,
            "recorded_context": to_json_blob(context),
            "evidence_so_far": [f for f in (inv.latest_findings or [])],
            "budget": {"iterations_used": inv.iteration_count,
                       "max_iterations": inv.max_iterations}}, sort_keys=True)}]
    return items


def run_meta_turn(session: Session, inv: Investigation,
                  max_rounds: int = 3,
                  previous_response_id: str | None = None) -> dict:
    """One bounded Meta turn: tool calls loop up to `max_rounds` rounds."""
    if inv.tool_call_count >= inv.max_tool_calls:
        return {"status": "tool_budget_exhausted", "message_text": "",
                "tool_calls": []}
    tools = tools_registry.meta_tool_schemas(inv.mode)
    input_items = _initial_context_items(inv)
    last_id = previous_response_id
    round_no = 0
    executed: list[dict] = []
    text_out = ""
    usage: dict | None = None

    while round_no < max_rounds:
        round_no += 1
        record_event(session, inv.id, "meta_request",
                     f"Meta round {round_no} (mode={inv.mode})",
                     payload={"round": round_no, "tools_offered": [t["name"] for t in tools]})
        try:
            response = meta_client.create_response(
                model=config.meta_model_id(), input_items=input_items,
                tools=tools, previous_response_id=last_id,
                instructions=MODE_INSTRUCTIONS[inv.mode])
        except meta_client.MetaUnavailable as exc:
            record_event(session, inv.id, "meta_request",
                         "Meta unavailable", detail=str(exc)[:300])
            session.commit()
            return {"status": "meta_unavailable", "message_text": "",
                    "tool_calls": executed, "error": str(exc)}
        last_id = meta_client.response_id(response)
        usage = meta_client.usage(response)
        text_out = meta_client.extract_message_text(response)
        calls = meta_client.extract_function_calls(response)
        record_event(session, inv.id, "meta_response",
                     f"Meta round {round_no} response",
                     detail=text_out[:600] or "(tool call only)",
                     payload={"response_id": last_id, "n_tool_calls": len(calls),
                              "usage": usage})
        if not calls:
            break
        call_outputs = []
        remaining = inv.max_tool_calls - inv.tool_call_count
        for call in calls[: max(0, remaining)]:
            outcome = engine.run_tool(session, inv, call["name"],
                                      dict(call.get("arguments") or {}),
                                      source_meta=True)
            executed.append({"call_id": call["call_id"], "name": call["name"],
                             "outcome": outcome})
            call_outputs.append({
                "type": "function_call_output", "call_id": call["call_id"],
                "output": json.dumps({"tool": call["name"],
                                      "result": outcome.get("result"),
                                      "ok": outcome.get("ok", False),
                                      "error": outcome.get("error")})[:2000]})
        if len(calls) > remaining:
            for call in calls[remaining:]:
                call_outputs.append({
                    "type": "function_call_output", "call_id": call["call_id"],
                    "output": json.dumps({"error": "tool_call_budget_exhausted"})})
        if inv.tool_call_count >= inv.max_tool_calls:
            record_event(session, inv.id, "status_change",
                         f"Tool-call budget exhausted ({inv.max_tool_calls})")
        input_items = call_outputs
        session.commit()
    session.commit()
    return {"status": "ok", "message_text": text_out, "tool_calls": executed,
            "response_id": last_id, "usage": usage}
