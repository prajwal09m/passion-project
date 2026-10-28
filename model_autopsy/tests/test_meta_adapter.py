"""Meta adapter tests — no network. Uses a stubbed `create_response` whose
payloads follow the documented Responses API shape to exercise the
tool-calling loop honestly; nothing here is presented as a live result."""
from __future__ import annotations

import json

import httpx
import pytest

from model_autopsy.backend import engine
from model_autopsy.backend.db import Event, SessionLocal, init_db
from model_autopsy.backend.meta_api import client as meta_client
from model_autopsy.backend.meta_api import loop as meta_loop


class FakeClosedLoopAPI:
    """Stub Responses API honoring the documented request/response shape."""

    def __init__(self):
        self.counter = 0
        self.bodies = []

    def create_response(self, **kwargs):
        body = kwargs
        self.bodies.append(body)
        self.counter += 1
        if self.counter == 1:
            return {"id": "resp_1", "object": "response", "status": "completed",
                    "output": [{"id": "fc1", "type": "function_call",
                                "status": "completed", "call_id": "c1",
                                "name": "artifact_summary", "arguments": "{}"}],
                    "usage": {"input_tokens": 10, "output_tokens": 20,
                              "total_tokens": 30}}
        return {"id": "resp_2", "object": "response", "status": "completed",
                "output": [{"type": "message", "role": "assistant",
                            "content": [{"type": "output_text",
                                         "text": "H1: cross-fold variability check."}]}],
                "usage": {"input_tokens": 40, "output_tokens": 15,
                          "total_tokens": 55}}


def test_no_key_raises_meta_unavailable(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    with pytest.raises(meta_client.MetaUnavailable):
        meta_client._headers()


def test_extract_function_calls_and_message():
    calls = meta_client.extract_function_calls({"output": [
        {"type": "function_call", "call_id": "c1", "name": "run_tests",
         "arguments": '{"root": "."}'}]})
    assert calls == [{"call_id": "c1", "name": "run_tests",
                      "arguments": {"root": "."}}]
    broken = meta_client.extract_function_calls({"output": [
        {"type": "function_call", "call_id": "c2", "name": "t",
         "arguments": "not json"}]})
    assert broken[0]["arguments"] == {"_invalid_json": "not json"}
    assert meta_client.extract_message_text(
        {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": "hi"}]}]}) == "hi"


def test_loop_executes_tool_and_records_evidence(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = FakeClosedLoopAPI()
    monkeypatch.setattr(meta_client, "create_response", api.create_response)

    init_db()
    session = SessionLocal()
    try:
        inv = engine.create_investigation(session, "ml", "fake case", "why?",
                                          {"max_tool_calls": 5})
        engine.build_context(session, inv)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=3)
        assert result["status"] == "ok"
        assert result["message_text"].startswith("H1")
        assert len(result["tool_calls"]) == 1 and result["tool_calls"][0]["outcome"]["ok"]
        # The reported metric came from a genuine run on the real artifact:
        assert result["tool_calls"][0]["outcome"]["result"]["n_rows"] > 0
        # Second request carried the function_call_output round-trip:
        second = api.bodies[1]
        assert any(isinstance(i, dict)
                   and i.get("type") == "function_call_output"
                   for i in second["input_items"])
        assert second.get("previous_response_id") == "resp_1"
        # Timeline: honest record of both sides and the tool result
        kinds = [e.kind for e in session.query(Event)
                 .filter_by(investigation_id=inv.id).all()]
        assert {"meta_request", "meta_response", "tool_request",
                "tool_result"}.issubset(set(kinds))
    finally:
        session.close()


def test_loop_reports_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    init_db()
    session = SessionLocal()
    try:
        inv = engine.create_investigation(session, "ml", "t", "q")
        result = meta_loop.run_meta_turn(session, inv, max_rounds=1)
        assert result["status"] == "meta_unavailable"
        assert "MODEL_API_KEY" in result["error"]
    finally:
        session.close()


def test_connection_test_without_key(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    out = meta_client.test_connection()
    assert out["ok"] is False and "MODEL_API_KEY" in out["detail"]
