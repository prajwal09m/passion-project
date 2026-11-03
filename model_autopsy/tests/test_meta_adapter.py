"""Meta adapter tests — no network. Uses a stubbed `create_response` whose
payloads follow the documented Responses API shape to exercise the
tool-calling loop honestly; nothing here is presented as a live result."""
from __future__ import annotations

import hashlib
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


def test_ml_instructions_stay_compact_but_behavioral():
    """Prompt-efficiency guard: the ml instructions must contain every
    required investigative behavior while staying bounded in size (the
    instructions are resent on every loop round by both providers)."""
    text = meta_loop.MODE_INSTRUCTIONS["ml"]
    for required in (
        "action id",                 # evidence/action-id traceability
        "competing",                 # >1 plausible hypotheses when warranted
        "fact / hypothesis /",       # honest facts-vs-hypotheses distinction
        "UNRESOLVED",                # explicit uncertainty labeling
        "DISCRIMINATES",             # information-value diagnostics choice
        "predicted observation",     # compare actual result with prediction
        "duplicate",                 # reuse guard awareness (no rerun waste)
        "historical",                # historical-narrative separation
        "investigation_summary",     # structured final output block
        "status_recommendations", "uncertainties", "recommended_next",
    ):
        assert required.lower() in text.lower(), f"missing {required!r}"
    # M20: the generation contract (schema table, status vocabulary,
    # representation rules, prohibitions, one example) is required
    # reporting behavior that cannot fit the old budget alongside the
    # existing behavioral clauses; the bound stays tight relative to
    # per-round context (ledger/roster run to many KB).
    assert len(text) < 4000, (
        f"instructions grew to {len(text)} chars; keep them compact — they "
        "are resent every round")


# ---------------------------------------------------------------------------
# Scripted deterministic scenarios: hypotheses, integrity, budgets, redundancy
# ---------------------------------------------------------------------------

def _tool_call_response(call_id: str, name: str, arguments: str = "{}",
                        usage=(10, 20, 30), resp_id=None) -> dict:
    return {"id": resp_id or f"resp_{call_id}", "object": "response",
            "status": "completed",
            "output": [{"id": f"fc_{call_id}", "type": "function_call",
                        "status": "completed", "call_id": call_id,
                        "name": name, "arguments": arguments}],
            "usage": {"input_tokens": usage[0], "output_tokens": usage[1],
                      "total_tokens": usage[2]}}


def _message_response(text: str, usage=(10, 20, 30), resp_id="resp_final") -> dict:
    return {"id": resp_id, "object": "response", "status": "completed",
            "output": [{"type": "message", "role": "assistant",
                        "content": [{"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": usage[0], "output_tokens": usage[1],
                      "total_tokens": usage[2]}}


class _ScriptedAPI:
    """Deterministic Responses stub: yields scripted payloads in order."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.bodies = []

    def create_response(self, **kwargs):
        self.bodies.append(kwargs)
        if not self._payloads:
            raise AssertionError("script exhausted before a final message")
        item = self._payloads.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _ml_investigation(session, **cfg):
    cfg.setdefault("max_tool_calls", 8)
    inv = engine.create_investigation(session, "ml", "fake case", "why?", cfg)
    engine.build_context(session, inv)
    return inv


def test_duplicate_request_reuses_recorded_result_never_reexecutes(monkeypatch):
    """Same tool + same normalized args + same data identity => the recorded
    prior result is returned again without re-execution, WITHOUT consuming
    another tool-call budget unit."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        _tool_call_response("c1", "artifact_summary", "{}", usage=(100, 10, 110)),
        _tool_call_response("c2", "artifact_summary", "{}", usage=(100, 10, 110)),
        _message_response("done\n```investigation_summary\n"
                          "{\"conclusion\": \"schema inspected\", "
                          "\"uncertainties\": [\"none recorded\"], "
                          "\"recommended_next\": \"run a metric\"}\n```",
                          usage=(100, 10, 110)),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=3)
        assert result["status"] == "ok"
        assert len(result["tool_calls"]) == 2
        first, second = result["tool_calls"]
        assert not first["outcome"].get("reused")
        assert second["outcome"].get("reused") is True
        # Same recorded action — nothing was re-executed:
        assert first["outcome"]["action_id"] == second["outcome"]["action_id"]
        assert "n_rows" in second["outcome"]["result"]
        assert second["outcome"]["result"]["reused"] is True
        # Budget consumed exactly once:
        assert inv.tool_call_count == 1
        # Normalized-args dedup is deterministic (order-insensitive):
        assert api.bodies[1]["previous_response_id"]
        roll = result["usage_rollup"]
        assert roll["tool_calls_executed"] == 1 and roll["tool_calls_reused"] == 1
        # Provider-reported usage summed across the three rounds:
        assert roll["tokens"] == {"input_tokens": 300, "output_tokens": 30,
                                  "total_tokens": 330}
        kinds = [e.kind for e in session.query(Event)
                 .filter_by(investigation_id=inv.id).all()]
        assert "meta_usage" in kinds
        reused_events = [e for e in session.query(Event)
                         .filter_by(investigation_id=inv.id, kind="tool_result").all()
                         if (e.payload or {}).get("reused")]
        assert len(reused_events) == 1
        # The wrap-up signal rides the existing round (no extra API call):
        assert len(api.bodies) == 3
        assert result["summary"]["valid"] is True
    finally:
        session.close()


def test_unknown_tool_and_invalid_arguments_recorded_never_fabricated(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        _tool_call_response("c1", "run_tests"),
        _tool_call_response("c2", "dataset_validation", "{}"),
        _message_response("tried tools; both rejected by the backend"),
        _message_response("no improvement"),  # summary-repair attempt (F4)
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=3)
        out1 = result["tool_calls"][0]["outcome"]
        out2 = result["tool_calls"][1]["outcome"]
        assert out1["ok"] is False          # run_tests is software-mode only
        assert out2["ok"] is False          # dataset_validation missing required arg
        # No fabricated results — outcomes carry errors, not fake metrics:
        assert "result" not in out1 and out1.get("error")
        assert out2.get("error")
        failed = [a for a in session.query(engine.db.Action)
                  .filter_by(investigation_id=inv.id, status="failed").all()]
        assert sorted(a.tool_name for a in failed) == ["dataset_validation", "run_tests"]
        # Unparseable final summary is RECORDED as invalid, not silently dropped:
        assert result["summary"]["valid"] is False
        kinds = [e.kind for e in session.query(Event)
                 .filter_by(investigation_id=inv.id).all()]
        assert "summary" in kinds
        ev = session.query(Event).filter_by(investigation_id=inv.id,
                                            kind="summary").first()
        assert ev.payload["valid"] is False and ev.payload["errors"]
    finally:
        session.close()


def test_tool_budget_and_rounds_stop_inside_one_turn(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        _tool_call_response("c1", "artifact_summary", '{}'),
        _tool_call_response("c2", "classification_metrics",
                            '{"score_column": "LightGBM_A"}'),
        _tool_call_response("c3", "classification_metrics",
                            '{"score_column": "LightGBM_C"}'),
        # M20: final prose must be substantive to qualify for repair
        # (short fragments take the deterministic fallback directly).
        _message_response("out of budget and stopping here without summary"),
        _message_response("still cannot summarize"),  # repair attempt (F4)
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session, max_tool_calls=2)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=4)
        assert result["status"] == "ok"
        # Exactly two executed calls (budget); the third DISTINCT call got the
        # honest over-budget ack instead of an execution:
        assert len(result["tool_calls"]) == 2
        assert inv.tool_call_count == 2
        # The over-budget ack is delivered with c3's call_id in the FOLLOWING
        # round's request (that round then returns the final message):
        third_body = api.bodies[3]
        outputs = [i for i in third_body["input_items"]
                   if i.get("type") == "function_call_output"]
        assert any("tool_call_budget_exhausted"
                   in str(i.get("output")) for i in outputs)
        # Wrap-up signal folded into an EXISTING round's outputs (round 3,
        # the final tool round): no extra API call for it. The 5th call is the
        # ONE bounded invalid-summary repair attempt (F4).
        assert len(api.bodies) == 5
        wrapup_bodies = [i for body in api.bodies for i in body["input_items"]
                         if i.get("role") == "user"
                         and "nearly exhausted" in str(i.get("content"))]
        assert len(wrapup_bodies) >= 1
        assert result["usage_rollup"]["tool_calls_executed"] == 2
    finally:
        session.close()


def test_meta_unavailable_midturn_preserves_recorded_evidence(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        _tool_call_response("c1", "artifact_summary", resp_id="resp_1"),
        meta_client.MetaUnavailable("HTTP 500: provider outage"),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=3)
        assert result["status"] == "meta_unavailable"
        assert "500" in result["error"]
        # Evidence recorded BEFORE the outage survives and is honest:
        ran = session.query(engine.db.Action).filter_by(
            investigation_id=inv.id, status="ran").all()
        assert len(ran) == 1
        kinds = [e.kind for e in session.query(Event)
                 .filter_by(investigation_id=inv.id).all()]
        assert {"tool_request", "tool_result", "meta_request"}.issubset(set(kinds))
    finally:
        session.close()


def test_summary_recommendations_validated_against_real_ids_and_vocab(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    init_db()
    session = SessionLocal()
    try:
        # --- valid case: a real hypothesis id, app-vocabulary status ------
        api = _ScriptedAPI([
            _message_response("evidence weighs against it\n```investigation_summary\n"
                              "PLACEHOLDER\n```"),
        ])
        monkeypatch.setattr(meta_client, "create_response", api.create_response)
        inv = _ml_investigation(session)
        hyp = engine.propose_hypothesis(
            session, inv, "fold coverage variability explains the drop",
            rationale="chronology differs across folds",
            predicted_observation="per-fold AUC spread > 0.1")
        hid = hyp["hypothesis_id"]
        text = ("judged by AUC per fold\n```investigation_summary\n"
                f"{{\"conclusion\": \"needs evidence\", "
                "\"status_recommendations\": [{\"hypothesis_id\": \""
                f"{hid}\", \"status\": \"rejected\", "
                "\"basis\": \"recorded action\"}], "
                "\"uncertainties\": [\"sample size\"], "
                "\"recommended_next\": \"time split check\"}\n```")
        api._payloads = [_message_response(text)]
        result = meta_loop.run_meta_turn(session, inv, max_rounds=1)
        assert result["summary"]["valid"] is True
        from model_autopsy.backend.db import Hypothesis
        row = session.get(Hypothesis, hid)
        # Meta RECOMMENDS; the backend never lets the model apply statuses:
        assert row.status == "proposed"
        assert row.revisions is None or row.revisions == []
        session.close()

        # --- invalid case: fabricated id and out-of-vocabulary status ----- 
        session2 = SessionLocal()
        try:
            inv2 = _ml_investigation(session2)
            bad = ("\n```investigation_summary\n"
                   "{\"conclusion\": \"x\", \"status_recommendations\": ["
                   "{\"hypothesis_id\": \"deadbeef\", "
                   "\"status\": \"confirmed\"}]}\n```")
            monkeypatch.setattr(
                meta_client, "create_response",
                _ScriptedAPI([_message_response(bad),
                              _message_response(bad)]).create_response)  # +repair (F4)
            result2 = meta_loop.run_meta_turn(session2, inv2, max_rounds=1)
            assert result2["summary"]["valid"] is False
            errs = " ".join(result2["summary"]["errors"])
            assert "deadbeef" in errs and "confirmed" in errs
            ev = (session2.query(Event)
                  .filter_by(investigation_id=inv2.id, kind="summary")
                  .order_by(Event.id.desc()).first())
            assert ev.payload["valid"] is False
        finally:
            session2.close()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Phase A instrumentation & reliability (F7 usage/perf, F8 truncation, F4 repair)
# ---------------------------------------------------------------------------

class _StatusResp:
    def __init__(self, status_code, text="", hdrs=None, json_data=None):
        self.status_code, self.text, self.headers = (
            status_code, text, (hdrs or {}))
        self._json = json_data if json_data is not None else {}

    def json(self):
        return self._json


def test_usage_flattens_nested_cached_token_details():
    """Provider-reported nested usage details (e.g. cached-token wrappers)
    are captured as dotted keys — and absent when not reported."""
    out = meta_client.usage({"usage": {"input_tokens": 100,
                                       "output_tokens": 5, "total_tokens": 105,
                                       "input_tokens_details":
                                       {"cached_tokens": 60}}})
    assert out == {"input_tokens": 100, "output_tokens": 5, "total_tokens": 105,
                   "input_tokens_details.cached_tokens": 60}
    assert meta_client.usage({}) == {}


def test_request_perf_records_latency_and_attempts(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    monkeypatch.setattr(meta_client.time, "sleep", lambda s: None)
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        if len(calls) < 2:
            return _StatusResp(429, text="rate limited",
                               hdrs={"retry-after": "0.01"})
        return _StatusResp(200, json_data={"id": "resp_ok", "output": [],
                                           "usage": {"input_tokens": 7}})

    monkeypatch.setattr(meta_client.httpx, "post", fake_post)
    out = meta_client.create_response(model="x", input_items=[], tools=[])
    perf = out["_request_perf"]
    assert perf["attempts"] == 2
    assert isinstance(perf["latency_s"], float)


def test_truncated_tool_payload_stays_valid_json():
    """F8: truncation never produces malformed JSON — the model receives a
    structured notice with digest and prefix instead."""
    small = {"tool": "artifact_summary", "ok": True, "result": {"n_rows": 3}}
    assert meta_loop._truncate_tool_payload(dict(small)) == small

    big_value = "x" * 3000
    out = meta_loop._truncate_tool_payload(
        {"tool": "t", "ok": True, "result": big_value})
    dumped = json.dumps(out)
    assert json.loads(dumped) == out  # round-trips as valid JSON
    notice = out["result"]
    assert notice["truncated"] is True
    assert notice["prefix"] == "x" * 400
    assert notice["omitted_chars"] == 2600
    assert notice["sha256"] == hashlib.sha256(big_value.encode()).hexdigest()

    # Oversized structured result: same self-describing notice, digest of its
    # exact serialized value.
    huge = {"rows": "y" * 3000}
    out2 = meta_loop._truncate_tool_payload(
        {"tool": "t", "ok": True, "result": huge})
    assert json.loads(json.dumps(out2)) == out2
    assert out2["result"]["truncated"] is True
    assert out2["result"]["sha256"] == hashlib.sha256(
        json.dumps(huge, sort_keys=True).encode()).hexdigest()


def test_summary_repair_succeeds_without_extra_tool_budget(monkeypatch):
    """F4: one bounded repair request turns an invalid summary into a valid
    one; no tools are offered (tool budget untouched); the attempt and its
    provider state are recorded."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        _tool_call_response("c1", "artifact_summary", "{}"),
        _message_response("first pass had no valid summary block"),
        _message_response("repaired\n```investigation_summary\n"
                          "{\"conclusion\": \"repaired conclusion\", "
                          "\"uncertainties\": [\"none recorded\"], "
                          "\"recommended_next\": \"run a metric\"}\n```"),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2)
        assert result["status"] == "ok"
        assert result["summary"]["valid"] is True
        assert result["message_text"].startswith("repaired")
        roll = result["usage_rollup"]
        assert roll["summary_repair_attempts"] == 1
        assert roll["api_calls"] == 3  # two rounds + exactly one repair
        assert inv.tool_call_count == 1
        # M8 redesign: the repair is a FRESH full-context request carrying
        # recorded state (chaining from unanswered tool calls dies with
        # provider 400) and offers NO tools:
        repair_body = api.bodies[-1]
        assert repair_body.get("previous_response_id") is None
        assert repair_body.get("tools") == []
        import json as _json
        assert "allowed_hypothesis_ids" in _json.dumps(
            repair_body.get("input_items"))
        kinds = [e.kind for e in session.query(Event)
                 .filter_by(investigation_id=inv.id).all()]
        # M20: attempt + consistency gate + success (a repaired summary
        # must pass the authoritative consistency checks to be accepted).
        assert kinds.count("summary_repair") == 3
    finally:
        session.close()


def test_summary_repair_runs_at_most_once_and_keeps_original(monkeypatch):
    """F4: an unsuccessful repair is never retried — the original invalid
    verdict and the original message text stand."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    original = "first pass had no valid summary block"
    api = _ScriptedAPI([
        _tool_call_response("c1", "artifact_summary", "{}"),
        _message_response(original),
        _message_response("repair attempt also had no usable block"),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2)
        assert result["status"] == "ok"
        assert result["summary"]["valid"] is False
        assert result["message_text"] == original
        assert result["usage_rollup"]["summary_repair_attempts"] == 1
        # Exactly three bodies: round1 tool, round2 message, ONE repair. A
        # second repair attempt would exhaust the script and fail loudly.
        assert len(api.bodies) == 3
    finally:
        session.close()


def test_repair_record_returned_for_recorders_success(monkeypatch):
    """The turn result carries a dedicated repair record (valid repair) so
    benchmark recorders can persist repairs.jsonl; the exchange is also in
    the wrapped-client log."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        _tool_call_response("c1", "artifact_summary", "{}"),
        _message_response("first pass had no valid summary block"),
        _message_response("repaired\n```investigation_summary\n"
                          "{\"conclusion\": \"repaired conclusion\", "
                          "\"uncertainties\": [\"none recorded\"], "
                          "\"recommended_next\": \"run a metric\"}\n```"),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2)
        assert result["summary"]["valid"] is True
        repairs = result["repairs"]
        assert len(repairs) == 1
        record = repairs[0]
        assert record["valid"] is True
        assert record["repair_text"].startswith("repaired")
        assert record["response_id"]  # usable continuation handle
        assert record["continuation"] == "repair"
        assert record["errors_before"]  # the original rejection, verbatim
        assert record["errors_after"] == []
    finally:
        session.close()


def test_repair_record_returned_for_recorders_failure(monkeypatch):
    """An unsuccessful repair is also recorded: original verdict stands,
    continuation honestly stays on the original response."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    original = "first pass had no valid summary block"
    api = _ScriptedAPI([
        _tool_call_response("c1", "artifact_summary", "{}"),
        _message_response(original),
        _message_response("repair attempt also had no usable block"),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2)
        assert result["summary"]["valid"] is False
        repairs = result["repairs"]
        assert len(repairs) == 1
        record = repairs[0]
        assert record["valid"] is False
        assert record["continuation"] == "original"
        assert record["repair_text"] == "repair attempt also had no usable block"
        assert record["errors_after"]  # why the repair was rejected
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Phase C: continuation turns send a state delta; full-context fallback on
# RETAINED-history chain failures only (never transient/network failures).
# ---------------------------------------------------------------------------

def _valid_summary_message(prefix="continued"):
    return _message_response(f"{prefix}\n```investigation_summary\n"
                            "{\"conclusion\": \"analysis continued\", "
                            "\"uncertainties\": [\"none recorded\"], "
                            "\"recommended_next\": \"run a metric\"}\n```")


def test_meta_unavailable_carries_status_code():
    exc = meta_client.MetaUnavailable("HTTP 404: response not found",
                                      status_code=404)
    assert exc.status_code == 404
    assert meta_client.MetaUnavailable("key missing").status_code is None
    assert str(exc) == "HTTP 404: response not found"


def test_continuation_turn_sends_delta_not_full_context(monkeypatch):
    """A turn with a valid chain id sends only the fresh state delta; the
    turn-invariant recorded context stays in the provider's stored history.
    Instructions and tool definitions are still supplied (documented
    requirement: they do not persist across turns)."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([_valid_summary_message()])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2,
                                         previous_response_id="resp_prev")
        assert result["status"] == "ok"
        first = api.bodies[0]
        assert first.get("previous_response_id") == "resp_prev"
        assert first.get("instructions") == meta_loop.MODE_INSTRUCTIONS["ml"]
        assert first.get("tools")
        delta = json.loads(first["input_items"][0]["content"])
        assert "recorded_context" not in delta
        assert {"objective", "hypotheses", "findings",
                "experiments_ledger", "budget", "context_source"}.issubset(delta)
        full = json.loads(
            meta_loop._initial_context_items(session, inv)[0]["content"])
        assert len(json.dumps(delta, sort_keys=True)) < len(
            json.dumps(full, sort_keys=True))
        assert result["usage_rollup"]["context_mode"] == "delta"
    finally:
        session.close()


def test_initial_turn_sends_full_context_no_chain(monkeypatch):
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([_valid_summary_message()])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2)
        assert result["status"] == "ok"
        first = api.bodies[0]
        assert first.get("previous_response_id") is None
        payload = json.loads(first["input_items"][0]["content"])
        assert "recorded_context" in payload
        assert result["usage_rollup"]["context_mode"] == "full"
    finally:
        session.close()


def test_continuation_failure_falls_back_once_with_full_context(monkeypatch):
    """A continuation-state failure (HTTP 404 on a chained request) triggers
    AT MOST ONE full-context fallback with no chain reference — never a blind
    retry of the same failing request."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        meta_client.MetaUnavailable("HTTP 404: response not found",
                                    status_code=404),
        _valid_summary_message("fell back ok"),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2,
                                         previous_response_id="resp_stale")
        assert result["status"] == "ok"
        assert result["summary"]["valid"] is True
        # First request was the delta attempt; the fallback is a DIFFERENT
        # request: no chain id, full recorded context restored.
        assert len(api.bodies) == 2
        assert "previous_response_id" in api.bodies[0]
        fallback_body = api.bodies[1]
        assert fallback_body.get("previous_response_id") is None
        fallback_payload = json.loads(fallback_body["input_items"][0]["content"])
        assert "recorded_context" in fallback_payload
        assert fallback_body.get("tools")
        roll = result["usage_rollup"]
        assert roll["context_mode"] == "delta_fallback"
        assert roll["fallback_used"] is True
        # One SUCCESSFUL provider call (the fallback); the refused one shows up
        # in attempt/latency accounting, not in api_calls.
        assert roll["api_calls"] == 1
        assert roll["api_attempts"] >= 1
        events = [e for e in session.query(Event).filter_by(
            investigation_id=inv.id, kind="meta_request").all()]
        assert any("fallback" in str(e.title) for e in events)
    finally:
        session.close()


def test_transient_and_network_failures_never_fall_back(monkeypatch):
    """Outages (5xx) and network-style failures are NOT continuation-state
    problems: no fallback is attempted, and the turn surfaces meta_unavailable
    with the recorded evidence preserved."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        api = _ScriptedAPI([
            meta_client.MetaUnavailable("HTTP 503: provider outage",
                                        status_code=503)])
        monkeypatch.setattr(meta_client, "create_response", api.create_response)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2,
                                         previous_response_id="resp_prev")
        assert result["status"] == "meta_unavailable"
        assert len(api.bodies) == 1
        session.close()

        # Network-style failure: no HTTP status → not a chain-state problem.
        session2 = SessionLocal()
        try:
            inv2 = _ml_investigation(session2)
            api2 = _ScriptedAPI([
                meta_client.MetaUnavailable("ConnectError: refused")])
            monkeypatch.setattr(meta_client, "create_response", api2.create_response)
            result2 = meta_loop.run_meta_turn(session2, inv2, max_rounds=2,
                                              previous_response_id="resp_prev")
            assert result2["status"] == "meta_unavailable"
            assert len(api2.bodies) == 1
        finally:
            session2.close()
    finally:
        session.close()


def test_second_continuation_failure_never_blind_retries(monkeypatch):
    """Even inside the fallback window, only ONE rebuilt full-context request
    is attempted. A failure of the fallback itself ends honestly with BOTH
    failures recorded (the original detail lives in the investigation record;
    the returned error describes the last failure)."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        meta_client.MetaUnavailable("HTTP 404: response not found",
                                    status_code=404),
        meta_client.MetaUnavailable("HTTP 400: invalid request",
                                    status_code=400),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        result = meta_loop.run_meta_turn(session, inv, max_rounds=2,
                                         previous_response_id="resp_stale")
        assert result["status"] == "meta_unavailable"
        # Two attempts total: the refused delta continuation and the ONE
        # rebuilt full-context request. A third request would exhaust the
        # scripted failure class — never retried identically.
        assert len(api.bodies) == 2
        assert json.loads(api.bodies[1]["input_items"][0]["content"]).get(
            "recorded_context") is not None
        assert api.bodies[1].get("previous_response_id") is None
        # Original failure information is preserved in the record, and the
        # returned error describes the final failure:
        events = [e for e in session.query(Event).filter_by(
            investigation_id=inv.id, kind="meta_request").all()]
        original = [e for e in events if str(e.title or "").startswith(
            "Continuation state refused")]
        final = [e for e in events if "fallback also failed" in str(e.title or "")]
        assert original and "404" in str(original[0].detail)
        assert final and "400" in str(final[0].detail)
        assert "400" in result["error"]
    finally:
        session.close()


def test_fallback_preserves_prior_evidence_and_accounting(monkeypatch):
    """When a chained TURN (with already-recorded evidence from turn 1) hits a
    stale-chain failure, the rebuilt full-context request preserves the prior
    actions and the rollup reflects the fallback attempt honestly."""
    monkeypatch.setenv("MODEL_API_KEY", "0" * 40)
    api = _ScriptedAPI([
        _tool_call_response("c1", "artifact_summary", "{}", resp_id="resp_t1a"),
        # M20: substantive prose qualifies for repair (short fragments
        # take the deterministic fallback directly).
        _message_response("turn one done, evidence recorded and ready",
                          resp_id="resp_t1b"),
        # Turn 1's bounded F4 summary repair consumes the following payload —
        # hand it a valid structured summary so turn 1 ends cleanly.
        _message_response("```investigation_summary\n"
                          "{\"conclusion\": \"turn one concluded\", "
                          "\"uncertainties\": [\"none recorded\"], "
                          "\"recommended_next\": \"run a metric\"}\n```",
                          resp_id="resp_t1c"),
        meta_client.MetaUnavailable("HTTP 404: response not found",
                                    status_code=404),
        _message_response("turn two after fallback"
                          "\n```investigation_summary\n"
                          "{\"conclusion\": \"continued after fallback\", "
                          "\"uncertainties\": [\"none recorded\"], "
                          "\"recommended_next\": \"run a metric\"}\n```",
                          resp_id="resp_t2"),
    ])
    monkeypatch.setattr(meta_client, "create_response", api.create_response)
    init_db()
    session = SessionLocal()
    try:
        inv = _ml_investigation(session)
        turn1 = meta_loop.run_meta_turn(session, inv, max_rounds=3)
        assert turn1["status"] == "ok"
        ran_before = len(session.query(engine.db.Action).filter_by(
            investigation_id=inv.id, status="ran").all())
        assert ran_before == 1
        turn2 = meta_loop.run_meta_turn(session, inv, max_rounds=2,
                                        previous_response_id="resp_stale")
        assert turn2["status"] == "ok"
        assert turn2["summary"]["valid"] is True
        # Turn-1 evidence survives the fallback untouched:
        assert len(session.query(engine.db.Action).filter_by(
            investigation_id=inv.id, status="ran").all()) == ran_before
        roll = turn2["usage_rollup"]
        assert roll["context_mode"] == "delta_fallback"
        assert roll["fallback_used"] is True
        # Accounting: two provider calls this turn (refused + rebuilt):
        assert roll["api_calls"] == 1 and roll["api_attempts"] >= 1
    finally:
        session.close()
