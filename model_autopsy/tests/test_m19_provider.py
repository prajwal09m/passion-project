"""M19 Phase 7a: provider request resilience (mocked provider, no spend).

Proves the M18 round-2 failure shape is recovered: validation refuses
known-bad chained requests locally, one full-context fallback re-sends
without the chain, budgets are rechecked, completed tools are never
re-executed, and non-eligible failures never trigger fallback.
"""
import json

import pytest

from model_autopsy.backend.db import SessionLocal, init_db
from model_autopsy.backend.meta_api import client as C

MUSIC = "model_autopsy/tests/fixture_eval/investigator/music_rank.csv"
TURBINE = "model_autopsy/tests/fixture_eval/investigator/turbine_output.csv"

SLICE_ARGS = {"predictions_path": MUSIC, "slice_column": "slice",
              "score_column": "score", "labels": "relevance"}


def _inv(s, artifact=MUSIC, **cfg):
    from model_autopsy.backend import engine
    base = {"max_iterations": 3, "predictions_path": artifact,
            "m16_skeptic": False}
    base.update(cfg)
    return engine.create_investigation(s, "ml", "m19p", "m19 probe", base)


def _calls(*specs, rid="r"):
    out = []
    for call_id, name, args in specs:
        out.append({"type": "function_call", "call_id": call_id,
                    "name": name, "arguments": json.dumps(args)})
    return {"id": rid, "status": "completed", "output": out,
            "usage": {"input_tokens": 100, "output_tokens": 50}}


def _msg(text, rid="r"):
    return {"id": rid, "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50}}


def _unavailable(status):
    return C.MetaUnavailable(f"HTTP {status}: simulated", status_code=status)


# ---- requests.validate_request --------------------------------------------

def test_m19_valid_full_request_passes():
    from model_autopsy.backend.meta_api import requests as R
    items = [{"role": "user", "content": "context"},
             {"role": "user", "content": "{\"selection_brief\": {}}"}]
    out = R.validate_request(items, None, [{"name": "t"}])
    assert out == {"mode": "full", "problems": []}


def test_m19_valid_chained_outputs_pass():
    """The M18 round-2 shape (outputs + chain) is sendable, not refused."""
    from model_autopsy.backend.meta_api import requests as R
    items = [{"type": "function_call_output", "call_id": "c1",
              "output": json.dumps({"tool": "propose_hypothesis",
                                    "ok": True})}]
    out = R.validate_request(items, "resp_abc", [{"name": "t"}])
    assert out == {"mode": "chained", "problems": []}


def test_m19_empty_input_refused():
    from model_autopsy.backend.meta_api import requests as R
    out = R.validate_request([], "resp_abc", [{"name": "t"}])
    assert out["mode"] == "chained"
    assert any("non-empty" in p for p in out["problems"])


def test_m19_blank_chain_id_refused():
    from model_autopsy.backend.meta_api import requests as R
    items = [{"type": "function_call_output", "call_id": "c1",
              "output": "{\"ok\": true}"}]
    out = R.validate_request(items, "   ", [{"name": "t"}])
    assert any("continuation" in p for p in out["problems"])


def test_m19_empty_tools_refused():
    from model_autopsy.backend.meta_api import requests as R
    out = R.validate_request([{"role": "user", "content": "hi"}], None, [])
    assert any("tool definitions" in p for p in out["problems"])


def test_m19_unknown_good_shapes_pass():
    from model_autopsy.backend.meta_api import requests as R
    # Unknown TYPED shapes pass (validate known-bad, not unknown-good);
    # a dict with neither role nor type is known-bad and is refused.
    out = R.validate_request([{"role": "user", "content": "x"},
                              {"type": "future_thing", "v": 1}], None,
                             [{"name": "t"}])
    assert out["problems"] == []
    bad = R.validate_request([{"kind": "future-item"}], None,
                             [{"name": "t"}])
    assert any("missing type" in p for p in bad["problems"])


# ---- requests.failure_category / fallback_eligible --------------------------

def test_m19_400_with_chain_is_continuation_state():
    from model_autopsy.backend.meta_api import requests as R
    assert R.failure_category(400, True) == "continuation-state"
    assert R.failure_category(400, False) == "request-shape"
    assert R.failure_category(401, True) == "authentication"
    assert R.failure_category(500, True) == "transient-or-server"
    assert R.failure_category(None, True) == "transport-or-network"


def test_m19_eligibility_policy():
    from model_autopsy.backend.meta_api import requests as R
    ok, _ = R.fallback_eligible(400, True, False)
    assert ok is True
    for status in (401, 403, 429, 500, None, 422):
        ok, why = R.fallback_eligible(status, True, False)
        assert ok is False, (status, why)
    ok, why = R.fallback_eligible(400, True, True)
    assert ok is False and "already" in why
    ok, _ = R.fallback_eligible(400, False, False)
    assert ok is False


# ---- loop: M18-shape recovery -------------------------------------------------

def _propose_calls(n=3, rid="resp_1"):
    return _calls(*[
        (f"c{i}", "propose_hypothesis",
         {"text": f"Hypothesis number {i} about slice quality effects xxxx"})
        for i in range(1, n + 1)], rid=rid)


def test_m19_m18_shape_chained_400_recovers(monkeypatch):
    """Exact M18 failure: chained round-2 400 → one full-context fallback."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action, Event
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    sent = []

    def fake(**kw):
        sent.append(kw)
        if len(sent) == 1:
            return _propose_calls(3, rid="resp_1")
        if len(sent) == 2:
            raise _unavailable(400)
        return _msg("```investigation_summary\n"
                      "{\"conclusion\": \"open\", "
                      "\"status_recommendations\": [], "
                      "\"uncertainties\": [\"more data\"], "
                      "\"recommended_next\": \"run slice probe\"}" "\n```",
                      rid="resp_3")

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=b)
    assert out["status"] == "ok", out
    assert len(sent) == 3  # initial + failed chained + one fallback
    assert sent[1].get("previous_response_id") == "resp_1"
    assert sent[2].get("previous_response_id") in (None, "")
    # The 3 proposes survived; nothing executed twice. The end-of-turn
    # reservation fires normally after recovery (1 experiment slot).
    acts = s.query(Action).filter(
        Action.investigation_id == inv.id).all()
    assert len(acts) == 4, [a.tool_name for a in acts]
    assert sum(1 for a in acts
               if a.tool_name == "propose_hypothesis") == 3
    assert b.experiments_used == 1
    kinds = [e.kind for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()]
    assert "investigator_decision" in kinds
    assert any("allback" in (e.title or "")
               for e in s.query(Event).filter(
                   Event.investigation_id == inv.id).all())


def test_m19_fallback_then_diagnostic_executes(monkeypatch):
    """Recovery preserves state AND the investigation moves forward."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    sent = []

    def fake(**kw):
        sent.append(kw)
        if len(sent) == 1:
            return _propose_calls(2, rid="resp_1")
        if len(sent) == 2:
            raise _unavailable(404)
        if len(sent) == 3:
            return _calls(("c9", "ranking_slice_diagnostics", SLICE_ARGS),
                          rid="resp_3")
        return _msg("done.", rid="resp_4")

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    out = L.run_meta_turn(s, inv, max_rounds=3, budget=b)
    assert out["status"] == "ok", out
    # Model diagnostic (1) + end-of-turn reservation probe (1); the two
    # proposes cost nothing under M18 accounting.
    assert b.experiments_used == 2, b.ledger()
    ran = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").all()
    assert {a.tool_name for a in ran} >= {
        "propose_hypothesis", "ranking_slice_diagnostics"}, \
        [a.tool_name for a in ran]


def test_m19_fallback_failure_stops_honestly(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    sent = []

    def fake(**kw):
        sent.append(kw)
        if len(sent) == 1:
            return _propose_calls(2, rid="resp_1")
        raise _unavailable(400)

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget())
    assert out["status"] == "meta_unavailable", out
    assert len(sent) == 3  # initial + failed + one failed fallback, then stop
    # Prior proposes preserved, nothing duplicated or lost.
    from model_autopsy.backend.db import Hypothesis
    assert s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).count() == 2


def test_m19_auth_failure_never_fallbacks(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    sent = []

    def fake(**kw):
        sent.append(kw)
        raise _unavailable(401)

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget())
    assert out["status"] == "meta_unavailable"
    assert len(sent) == 1  # no fallback on auth errors


def test_m19_server_error_never_fallbacks(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    sent = []

    def fake(**kw):
        sent.append(kw)
        raise _unavailable(500)

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget())
    assert out["status"] == "meta_unavailable"
    assert len(sent) == 1


def test_m19_fallback_rechecks_budget_before_resend(monkeypatch):
    """The fallback performs its own headroom attempt check: a refusal
    stops the recovery with budget_exceeded and sends nothing further."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    sent = []

    def fake(**kw):
        sent.append(kw)
        if len(sent) == 1:
            return _propose_calls(2, rid="resp_1")
        raise _unavailable(400)

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    real_check = b.check_dispatch
    calls = {"n": 0}

    def _spy(est=0):
        calls["n"] += 1
        if calls["n"] >= 3:
            # Round-1 and round-2 checks pass; the fallback recheck fails.
            from model_autopsy.backend.live.governor import BudgetExceeded
            raise BudgetExceeded("simulated fallback headroom refusal")
        return real_check(est)

    monkeypatch.setattr(b, "check_dispatch", _spy)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=b)
    assert out["status"] == "budget_exceeded", out
    assert len(sent) == 2  # initial + failed chained; fallback never sent
    assert b.experiments_used == 0


def test_m19_fallback_attempt_budget_refusal(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    sent = []

    def fake(**kw):
        sent.append(kw)
        if len(sent) == 1:
            return _propose_calls(2, rid="resp_1")
        raise _unavailable(410)

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    b.attempts_used = 11  # round uses 1 (→12); fallback has none left
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=b)
    assert out["status"] in ("meta_unavailable", "budget_exceeded"), out
    assert len(sent) <= 2
    assert b.attempts_used <= 12


def test_m19_no_duplicate_execution_after_recovery(monkeypatch):
    """Fallback model re-requests the ran tool → recorded reuse, no spend."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action, Event
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    sent = []

    def fake(**kw):
        sent.append(kw)
        if len(sent) == 1:
            return _calls(("c1", "ranking_slice_diagnostics", SLICE_ARGS),
                          rid="resp_1")
        if len(sent) == 2:
            raise _unavailable(400)
        # Recovered model redundantly re-requests the SAME diagnostic.
        return _calls(("c2", "ranking_slice_diagnostics", SLICE_ARGS),
                      rid="resp_3")

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    out = L.run_meta_turn(s, inv, max_rounds=3, budget=b)
    assert b.experiments_used == 1, b.ledger()
    ran = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").all()
    assert len(ran) == 1  # no duplicate execution
    reuse = [e for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()
        if "reused" in (e.title or "").lower()
        or "reuse" in (e.title or "").lower()]
    assert reuse, "dedup reuse must be on the record"
