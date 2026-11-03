"""Milestone 5 offline tests — mocked provider, zero credits.

All Meta traffic is monkeypatched; no key, no network. Covers request
construction, credentials, persistence, linkage, tool validation,
hypotheses, experiments, delivery, report validation, isolation,
budgets, 429s, incomplete responses, recovery, finalization,
evaluator separation, and dashboard integration.
"""
from __future__ import annotations

import json

import pytest

TURBINE = "model_autopsy/tests/fixture_eval/investigator/turbine_output.csv"


def _resp(text="", calls=(), rid="resp_1", status="completed",
          usage=None):
    out = []
    if text:
        out.append({"type": "message", "content": [
            {"type": "output_text", "text": text}]})
    for call_id, name, args in calls:
        out.append({"type": "function_call", "call_id": call_id,
                    "name": name, "arguments": json.dumps(args)})
    return {"id": rid, "status": status, "output": out,
            "usage": usage or {"input_tokens": 100, "output_tokens": 50,
                               "total_tokens": 150}}


def _inv(session, context=None):
    from model_autopsy.backend import engine
    inv = engine.create_investigation(
        session, "ml", "Live test", "Is the forecaster off?",
        {"max_iterations": 3, "predictions_path": TURBINE})
    if context is not None:
        inv.config = {**(inv.config or {}), "context": context}
        session.commit()
    return inv


def _ctx():
    return {"project": "T", "task": "forecasting",
            "columns": ["date", "target", "prediction", "split"]}


# 1. request construction
def test_request_body_shape(monkeypatch):
    from model_autopsy.backend.meta_api import client as C
    seen = {}
    import httpx

    class FakeResp:
        status_code = 200
        headers = {}
        def json(self):
            return _resp("hi")

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, body=json,
                    auth=("Bearer " in (headers or {}).get(
                        "Authorization", "")))
        return FakeResp()

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setenv("MODEL_API_KEY", "dummy-test-key")
    out = C.create_response(model="muse-spark-1.3", input_items=[],
                            tools=[])
    assert out["id"] == "resp_1"
    assert seen["url"].endswith("/responses")
    assert seen["auth"] is True
    assert seen["body"]["model"] == "muse-spark-1.3"


# 2. credential loading
def test_missing_key_raises_without_network(monkeypatch):
    from model_autopsy.backend.meta_api import client as C
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    with pytest.raises(C.MetaUnavailable):
        C.create_response(model="m", input_items=[], tools=[])
    assert C.test_connection()["ok"] is False


# 3. request/response persistence
def test_turn_persists_request_and_response(monkeypatch):
    from model_autopsy.backend import db
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    db.init_db()
    s = db.SessionLocal()
    try:
        inv = _inv(s, _ctx())
        monkeypatch.setattr(
            C, "create_response",
            lambda **kw: _resp("nothing to add", rid="resp_a"))
        out = L.run_meta_turn(s, inv, max_rounds=1)
        assert out["status"] == "ok"
        kinds = [e.kind for e in s.query(db.Event).filter(
            db.Event.investigation_id == inv.id).all()]
        assert "meta_request" in kinds and "meta_response" in kinds
    finally:
        s.close()


# 4. response-id linkage
def test_continuation_chains_ids(monkeypatch):
    from model_autopsy.backend import db
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    db.init_db()
    s = db.SessionLocal()
    try:
        inv = _inv(s, _ctx())
        seen = []
        valid = ("```investigation_summary\n"
                 "{\"conclusion\": \"nothing to add\", "
                 "\"uncertainties\": []}\n```")
        def fake(**kw):
            seen.append(kw.get("previous_response_id"))
            return _resp(valid, rid=f"resp_{len(seen)}")
        monkeypatch.setattr(C, "create_response", fake)
        # Valid summaries: no repair request interleaves between turns.
        L.run_meta_turn(s, inv, max_rounds=1)
        L.run_meta_turn(s, inv, max_rounds=1,
                        previous_response_id="resp_1")
        assert seen[1] == "resp_1"
    finally:
        s.close()


# 5. tool-call validation
def test_unknown_tool_refused_and_recorded(monkeypatch):
    from model_autopsy.backend import db
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    db.init_db()
    s = db.SessionLocal()
    try:
        inv = _inv(s, _ctx())
        monkeypatch.setattr(
            C, "create_response",
            lambda **kw: _resp("", calls=[("c1", "hack_the_planet", {})],
                               rid="resp_x"))
        out = L.run_meta_turn(s, inv, max_rounds=1)
        assert out["tool_calls"][0]["outcome"]["ok"] is False
    finally:
        s.close()


# 6/7/8. hypothesis + experiment + delivery round-trip
def test_hypothesis_experiment_delivery(monkeypatch):
    from model_autopsy.backend import db
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    db.init_db()
    s = db.SessionLocal()
    try:
        inv = _inv(s, _ctx())
        script = [
            _resp("", calls=[
                ("c1", "propose_hypothesis",
                 {"text": "Missed level shift after day 500",
                  "rationale": "late error jump"})], rid="resp_1"),
            _resp("", calls=[
                ("c2", "forecast_diagnostics",
                 {"predictions_path": TURBINE,
                  "split_column": "split"})], rid="resp_2"),
        ]
        seen_inputs = []

        def fake(**kw):
            seen_inputs.append(kw.get("input_items"))
            if len(seen_inputs) <= 2:
                return script[len(seen_inputs) - 1]
            return _resp("Final. ```investigation_summary\n"
                         "{\"conclusion\": \"level shift missed\"}\n```",
                         rid="resp_3")

        monkeypatch.setattr(C, "create_response", fake)
        out = L.run_meta_turn(s, inv, max_rounds=3)
        hyps = s.query(db.Hypothesis).filter(
            db.Hypothesis.investigation_id == inv.id).all()
        assert len(hyps) == 1 and "level shift" in hyps[0].text
        tools = [t["name"] for t in out["tool_calls"]]
        assert "forecast_diagnostics" in tools
        # second request carried the first result back
        assert any(isinstance(items, list) and any(
            isinstance(i, dict) and i.get("type") == "function_call_output"
            for i in items) for items in seen_inputs[1:])
    finally:
        s.close()


# 9. final report validation + repair
def test_invalid_summary_triggers_one_repair(monkeypatch):
    from model_autopsy.backend import db
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    db.init_db()
    s = db.SessionLocal()
    try:
        inv = _inv(s, _ctx())
        calls = []

        def fake(**kw):
            calls.append(kw)
            if len(calls) == 1:
                return _resp("no structured block here", rid="resp_1")
            return _resp("```investigation_summary\n"
                         "{\"conclusion\": \"repaired\"}\n```", rid="resp_2")

        monkeypatch.setattr(C, "create_response", fake)
        out = L.run_meta_turn(s, inv, max_rounds=1)
        assert out["summary"]["valid"] is True
        assert out["usage_rollup"]["summary_repair_attempts"] == 1
    finally:
        s.close()


# 10. ground-truth isolation
def test_live_context_has_no_forbidden_tokens():
    from model_autopsy.backend import db
    from model_autopsy.backend.eval import projects as P
    from model_autopsy.backend.eval import separation as S
    from model_autopsy.backend.live import driver as D
    db.init_db()
    s = db.SessionLocal()
    try:
        proj = P.get_project("eval_turbine")
        truth = P.load_truth()
        inv = _inv(s)
        ctx = D.build_live_context(
            s, inv, proj, S.discovery_input(proj)["brief"])
        blob = json.dumps(ctx).lower()
        for tok in truth["eval_turbine"]["forbidden_tokens"]:
            assert tok.lower() not in blob
        import model_autopsy.backend.live.driver as _D
        import inspect
        assert "ground_truth" not in inspect.getsource(_D)
    finally:
        s.close()


# 11/13/14. budget enforcement incl. tokens and cost
def test_budget_caps_stop_before_request():
    from model_autopsy.backend.live.governor import Budget, BudgetExceeded
    b = Budget()
    b.attempts_used = 12
    with pytest.raises(BudgetExceeded):
        b.check()
    b2 = Budget()
    b2.input_tokens = 60_000
    with pytest.raises(BudgetExceeded):
        b2.check()
    b3 = Budget()
    b3.output_tokens = 100_000  # 100k > 50k token cap (also ~$0.425)
    with pytest.raises(BudgetExceeded):
        b3.check()


def test_budget_cost_cap_040_boundary():
    # M18 Phase 6: the authorized single-run ceiling is $0.65.
    from model_autopsy.backend.live.governor import Budget, BudgetExceeded, CAPS
    assert CAPS["cost_usd"] == 0.65
    wide = dict(CAPS, tokens=10_000_000)
    below = Budget(caps=dict(wide))
    below.output_tokens = 90_000
    assert below.cost_usd() < 0.65
    below.check()
    above = Budget(caps=dict(wide))
    above.output_tokens = 160_000
    assert above.cost_usd() >= 0.65
    with pytest.raises(BudgetExceeded):
        above.check()


def test_budget_records_provider_usage_only():
    from model_autopsy.backend.live.governor import Budget
    b = Budget()
    b.record_turn({"api_attempts": 2, "tool_calls_executed": 1,
                   "tokens": {"input_tokens": 1000,
                              "input_tokens_details.cached_tokens": 800,
                              "output_tokens": 200}})
    assert b.ledger()["cost_usd"]["spent"] == round(
        200 * 1.25e-6 + 800 * 0.15e-6 + 200 * 4.25e-6, 6)
    assert b.total_tokens() == 1200


# 12/15. retries counted, 429 respected
def test_429_retry_counts_attempts(monkeypatch):
    from model_autopsy.backend.meta_api import client as C
    import httpx
    monkeypatch.setenv("MODEL_API_KEY", "dummy-test-key")
    calls = []

    class R429:
        status_code = 429
        headers = {"retry-after": "0"}
        text = "slow down"

    class R200:
        status_code = 200
        headers = {}
        def json(self):
            return _resp("ok")

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(1)
        return R429() if len(calls) == 1 else R200()

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr("time.sleep", lambda s: None)
    out = C.create_response(model="m", input_items=[], tools=[])
    assert out["id"] == "resp_1"
    assert out["_request_perf"]["attempts"] == 2


# 16. incomplete preservation
def test_incomplete_response_preserved_and_classified(monkeypatch):
    from model_autopsy.backend import db
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    db.init_db()
    s = db.SessionLocal()
    try:
        inv = _inv(s, _ctx())
        monkeypatch.setattr(
            C, "create_response",
            lambda **kw: _resp("cut off", rid="resp_i",
                               status="incomplete"))
        out = L.run_meta_turn(s, inv, max_rounds=1)
        assert out["status"] == "ok"
        payloads = [e.payload for e in s.query(db.Event).filter(
            db.Event.investigation_id == inv.id,
            db.Event.kind == "meta_response").all()]
        assert payloads and payloads[0]["text"] == "cut off"
    finally:
        s.close()


# 17/18. recovery + atomic finalization
def test_manifest_checklist_and_missing_manifest(tmp_path):
    from model_autopsy.backend.live import recorder as R
    from model_autopsy.backend.live.governor import Budget
    d = tmp_path / "live-x"
    d.mkdir()
    manifest = R.finalize_run(d, "live-x", "eval_turbine", None, None,
                              Budget(), "failed", None, None, "",
                              error="boom")
    assert manifest["status"] == "failed"
    assert manifest["required_evidence_present"]["usage"] is True
    assert manifest["required_evidence_present"]["sandbox_db"] is False
    assert manifest["required_evidence_present"]["scorecard"] == "n/a"
    assert (d / "manifest.json").exists()


# 19. evaluator separation (post-freeze only input shape)
def test_adapter_output_scores_without_truth():
    from model_autopsy.backend.eval import scorer as SC
    from model_autopsy.backend.eval import projects as P
    report = {"executive_summary": "level shift missed",
              "confirmed_findings": [
                  {"hypothesis_id": "a1",
                   "title": "Stale validation split hides drift"}],
              "rejected_hypotheses": [], "experiments": [
                  {"experiment_id": "a2", "tool": "forecast_diagnostics",
                   "summary": "drift",
                   "numbers": {"drift": [7.0, 24.3],
                               "overlap": False, "n": 730}}],
              "inconclusive": [], "verification": [], "limitations": []}
    sc = SC.score("eval_turbine", report, P.load_truth())
    assert sc["verdict"] == "correct", sc
    assert "ground_truth" not in json.dumps(report)


# 20. dashboard integration (read-only live endpoints)
def test_live_api_readonly(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from model_autopsy.backend import db
    db.init_db()
    import model_autopsy.backend.api as API
    monkeypatch.setattr(API, "_live_root",
                        lambda: tmp_path, raising=True)
    d = tmp_path / "live-demo"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps(
        {"run_id": "live-demo", "status": "completed"}))
    from model_autopsy.backend.api import app
    c = TestClient(app)
    assert c.get("/api/live/runs").json()["runs"][0]["run_id"] == \
        "live-demo"
    assert c.get("/api/live/runs/live-demo").json()["status"] == \
        "completed"
    assert c.get("/api/live/runs/nope").status_code == 404
    # No spend-triggering endpoint exists.
    assert not any(r.path == "/api/live/runs"
                   and "POST" in r.methods
                   for r in app.routes if hasattr(r, "path"))


# 21. live FSM walk: Meta turns leave hypotheses_proposed; the driver
# must reach finalizing before finalize (regression for the first
# pilot attempt's `hypotheses_proposed -> complete` crash). No network.
def test_live_finalize_walk_from_proposed(tmp_path, monkeypatch):
    import os
    monkeypatch.setenv("MODEL_AUTOPSY_DB_PATH",
                        str(tmp_path / "fsm.db"))
    from model_autopsy.backend.eval import runner as R
    from model_autopsy.backend import engine
    s = R.session_for(str(tmp_path / "fsm.db"))()
    inv = engine.create_investigation(
        s, "ml", "FSM walk", "Q?",
        {"max_iterations": 3, "predictions_path": TURBINE})
    engine.add_hypothesis(s, inv.id, "H1: guess")
    assert inv.status == "hypotheses_proposed"
    if inv.status in ("created", "context_ready",
                      "hypotheses_proposed", "revising",
                      "blocked", "failed"):
        engine.set_status(s, inv, "investigating")
    if inv.status == "investigating":
        engine.set_status(s, inv, "finalizing")
    s.commit()
    report = engine.build_report(s, inv)
    final = engine.finalize(s, inv, report)
    assert inv.status == "complete"
    assert "unresolved" in final
    s.close()
