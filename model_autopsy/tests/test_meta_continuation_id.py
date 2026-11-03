"""Regression tests: continuation ID after a summary repair (protocol v2).

The defect: `run_meta_turn` returned the PRE-repair response id even when the
one bounded summary repair succeeded, so the next continuation chained from the
response that carried the invalid summary and silently dropped the repair.

Every test uses a mocked `create_response` (no network, dummy ids only). Both
experimental conditions are exercised through the real loop entry point:
  - "full":  no previous_response_id (fresh turn re-sends the initial context)
  - "delta": previous_response_id set (chained turn sends only the state delta)
"""
from __future__ import annotations

import json

import pytest

from model_autopsy.backend import engine
from model_autopsy.backend.db import SessionLocal, init_db
from model_autopsy.backend.meta_api import client as meta_client
from model_autopsy.backend.meta_api import loop as meta_loop

VALID_SUMMARY = (
    "```investigation_summary\n"
    '{"conclusion": "repaired conclusion", '
    '"uncertainties": ["none recorded"], '
    '"recommended_next": "run a metric"}\n'
    "```")
INVALID_TEXT = "no structured summary block here"


def _message_response(resp_id="resp_original", text=VALID_SUMMARY, *,
                      include_id=True) -> dict:
    payload = {
        "object": "response", "status": "completed",
        "output": [{"type": "message", "role": "assistant",
                    "content": [{"type": "output_text", "text": text}]}],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    if include_id:
        payload["id"] = resp_id
    return payload


class _ScriptedAPI:
    """Deterministic Responses stub: yields scripted payloads in order."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.bodies: list[dict] = []

    def create_response(self, **kwargs):
        self.bodies.append(dict(kwargs))
        if not self._payloads:
            raise AssertionError("script exhausted before a final message")
        item = self._payloads.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture()
def session(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "dummy-offline-placeholder")
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _investigation(session):
    inv = engine.create_investigation(session, "ml", "continuation-id case",
                                      "why?", {"max_tool_calls": 6})
    engine.build_context(session, inv)
    return inv


def _run(monkeypatch, api, session, inv, condition, max_rounds=1,
         previous_response_id=None):
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    if condition == "delta":
        previous_response_id = previous_response_id or "resp_prev"
    return meta_loop.run_meta_turn(
        session, inv, max_rounds=max_rounds,
        previous_response_id=previous_response_id)


def _first_payload(body: dict) -> dict:
    return json.loads(body["input_items"][0]["content"])


@pytest.mark.parametrize("condition", ["full", "delta"])
def test_no_repair_retains_original_response_id(monkeypatch, session,
                                                condition):
    api = _ScriptedAPI([_message_response("resp_original")])
    inv = _investigation(session)

    result = _run(monkeypatch, api, session, inv, condition)

    assert result["summary"]["valid"] is True
    assert result["response_id"] == "resp_original"
    assert result["continuation_state"] == {
        "attempted": False, "valid": None, "response_id_source": "original"}
    assert len(api.bodies) == 1
    # The condition's payload shape is untouched by the id fix:
    payload = _first_payload(api.bodies[0])
    if condition == "delta":
        assert api.bodies[0].get("previous_response_id") == "resp_prev"
        assert "recorded_context" not in payload
    else:
        assert not api.bodies[0].get("previous_response_id")
        assert "recorded_context" in payload


@pytest.mark.parametrize("condition", ["full", "delta"])
def test_successful_repair_returns_repaired_response_id(monkeypatch, session,
                                                        condition):
    api = _ScriptedAPI([
        _message_response("resp_original", INVALID_TEXT),
        _message_response("resp_repaired", VALID_SUMMARY),
    ])
    inv = _investigation(session)

    result = _run(monkeypatch, api, session, inv, condition)

    assert result["summary"]["valid"] is True
    assert result["message_text"].startswith("```investigation_summary")
    # THE FIX: the next continuation must chain from the repaired response.
    assert result["response_id"] == "resp_repaired"
    assert result["continuation_state"] == {
        "attempted": True, "valid": True, "response_id_source": "repair"}
    # M8 redesign (see milestone_8_audit §repair): the repair is a FRESH
    # full-context request, tools-free. Chaining from the original response
    # fails provider-side whenever that response's tool calls were never
    # answered (HTTP 400 "No tool output found" — see live 400 records).
    assert api.bodies[1].get("previous_response_id") is None
    assert api.bodies[1]["tools"] == []
    assert "allowed_hypothesis_ids" in json.dumps(
        api.bodies[1].get("input_items"))


@pytest.mark.parametrize("condition", ["full", "delta"])
def test_failed_repair_keeps_original_state_and_id(monkeypatch, session,
                                                   condition):
    api = _ScriptedAPI([
        _message_response("resp_original", INVALID_TEXT),
        _message_response("resp_repair", INVALID_TEXT),
    ])
    inv = _investigation(session)

    result = _run(monkeypatch, api, session, inv, condition)

    # No invalid repaired state is accepted: original verdict and text stand,
    # and the original response id remains the honest continuation handle.
    assert result["summary"]["valid"] is False
    assert result["message_text"] == INVALID_TEXT
    assert result["response_id"] == "resp_original"
    assert result["continuation_state"] == {
        "attempted": True, "valid": False, "response_id_source": "original"}


@pytest.mark.parametrize("condition", ["full", "delta"])
def test_unavailable_repair_keeps_original_state_and_id(monkeypatch, session,
                                                        condition):
    exc = meta_client.MetaUnavailable("HTTP 503: unavailable", status_code=503)
    api = _ScriptedAPI([_message_response("resp_original", INVALID_TEXT), exc])
    inv = _investigation(session)

    result = _run(monkeypatch, api, session, inv, condition)

    assert result["summary"]["valid"] is False
    assert result["response_id"] == "resp_original"
    assert result["continuation_state"] == {
        "attempted": True, "valid": None, "response_id_source": "original"}


def test_missing_original_response_id_is_never_used(monkeypatch, session):
    api = _ScriptedAPI([_message_response(include_id=False)])
    inv = _investigation(session)

    result = _run(monkeypatch, api, session, inv, "full")

    assert result["response_id"] is None
    assert result["continuation_state"]["response_id_source"] == "original"


def test_missing_original_id_still_allows_repair_chain(monkeypatch, session):
    """A malformed/missing original id must never be sent as a chain reference,
    in the repair request or afterwards; a successful repair still yields a
    usable continuation id."""
    api = _ScriptedAPI([
        _message_response(include_id=False, text=INVALID_TEXT),
        _message_response("resp_repaired", VALID_SUMMARY),
    ])
    inv = _investigation(session)

    result = _run(monkeypatch, api, session, inv, "delta")

    assert len(api.bodies) == 2
    assert api.bodies[0].get("previous_response_id") == "resp_prev"
    # The missing original id is dropped, not forwarded to the repair request.
    assert api.bodies[1].get("previous_response_id") is None
    assert result["response_id"] == "resp_repaired"
    assert result["continuation_state"]["response_id_source"] == "repair"


@pytest.mark.parametrize("bad_id", [None, 12345, "", "   "])
def test_missing_or_malformed_repair_id_establishes_no_continuation(
        monkeypatch, session, bad_id):
    repair = _message_response("resp_repaired", VALID_SUMMARY)
    if bad_id is None:
        repair.pop("id")
    else:
        repair["id"] = bad_id
    api = _ScriptedAPI([_message_response("resp_original", INVALID_TEXT), repair])
    inv = _investigation(session)

    result = _run(monkeypatch, api, session, inv, "full")

    # The repair won, but without a usable id there is no continuation state;
    # silently falling back to the invalid-summary response is not allowed.
    assert result["summary"]["valid"] is True
    assert result["response_id"] is None
    assert result["continuation_state"] == {
        "attempted": True, "valid": True, "response_id_source": "unavailable"}


def test_subsequent_continuation_uses_repaired_id(monkeypatch, session):
    api = _ScriptedAPI([
        _message_response("resp_original", INVALID_TEXT),
        _message_response("resp_repaired", VALID_SUMMARY),
        _message_response("resp_turn2", VALID_SUMMARY),
    ])
    inv = _investigation(session)
    monkeypatch.setattr(meta_client, "create_response", api.create_response)

    turn1 = meta_loop.run_meta_turn(session, inv, max_rounds=1)
    assert turn1["response_id"] == "resp_repaired"
    turn2 = meta_loop.run_meta_turn(
        session, inv, max_rounds=1,
        previous_response_id=turn1["response_id"])

    # The second turn chained from the repaired response, not the original.
    assert api.bodies[2]["previous_response_id"] == "resp_repaired"
    assert api.bodies[2]["previous_response_id"] != "resp_original"
    assert turn2["response_id"] == "resp_turn2"
    assert turn2["continuation_state"]["response_id_source"] == "original"
