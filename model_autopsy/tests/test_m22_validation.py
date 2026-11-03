"""M22 independent validation: 10 required scenarios, offline only.

Written against the M22 requirements (not the implementation): each
test asserts observable behavior through public paths with queued
fakes. No production code is modified here. No live calls.
"""
import json

import pytest

from model_autopsy.backend.db import SessionLocal as _SessionLocal
from model_autopsy.backend.db import init_db

_open_sessions: list = []


def _session():
    s = _SessionLocal()
    _open_sessions.append(s)
    return s


@pytest.fixture(autouse=True)
def _close_test_sessions():
    yield
    while _open_sessions:
        s = _open_sessions.pop()
        try:
            s.close()
        except Exception:
            pass


MUSIC = "model_autopsy/tests/fixture_eval/investigator/music_rank.csv"
SLICE_ARGS = {"predictions_path": MUSIC, "slice_column": "slice",
              "score_column": "score", "labels": "relevance"}


def _inv(s):
    from model_autopsy.backend import engine
    return engine.create_investigation(
        s, "ml", "m22v", "m22 validation probe",
        {"max_iterations": 3, "predictions_path": MUSIC,
         "m16_skeptic": False})


def _mk(s):
    from model_autopsy.backend import engine
    inv = _inv(s)
    for i in range(2):
        engine.propose_hypothesis(s, inv, text=f"mechanism {i}",
                                  predicted_observation="probe decides")
    hyps = _hyps(s, inv)
    out = engine.run_tool(s, inv, "ranking_slice_diagnostics",
                          dict(SLICE_ARGS), source_meta=True)
    assert out.get("ok"), out
    from model_autopsy.backend.db import Action
    act = s.get(Action, out["action_id"])
    hyps[0].evidence_refs = [{"action_id": act.id, "tool": act.tool_name,
                              "relation": "supports"}]
    hyps[1].evidence_refs = [{"action_id": act.id, "tool": act.tool_name,
                              "relation": "contradicts"}]
    s.commit()
    return inv, hyps, act


def _hyps(s, inv):
    from model_autopsy.backend.db import Hypothesis
    return s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).order_by(
        Hypothesis.id).all()


def _block(conclusion, recs, unc=("open q",), nxt="next step"):
    body = {"conclusion": conclusion, "status_recommendations": recs,
            "uncertainties": list(unc), "recommended_next": nxt}
    return ("```investigation_summary\n" + json.dumps(body) + "\n```")


def _msg(text, rid="r"):
    return {"id": rid, "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50}}


def _run_turn(monkeypatch, s, inv, script, max_rounds=1):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.live import governor as G
    queue = list(script)

    def fake(**kw):
        assert queue, "provider called more times than scripted"
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(C, "create_response", fake)
    return L.run_meta_turn(s, inv, max_rounds=max_rounds, budget=G.Budget())


def _dynamic_repair_block(kw):
    """Valid repair block citing the repair prompt's allowed ids."""
    for item in kw.get("input_items") or []:
        try:
            body = json.loads(item.get("content") or "{}")
        except (ValueError, AttributeError):
            continue
        if isinstance(body, dict) and body.get("allowed_hypothesis_ids"):
            ids = list(body["allowed_hypothesis_ids"])
            recs = [{"hypothesis_id": i, "status": "investigating"}
                    for i in ids]
            return _msg(_block("deferred", recs,
                               unc=("missing measurement",), nxt=""),
                        rid="rep")
    raise AssertionError("no allowed ids in repair prompt")


def test_v1_silent_turn_flagged(monkeypatch):
    init_db(); s = _session(); inv = _inv(s)
    out = _run_turn(monkeypatch, s, inv, [
        _msg("deviating note with no action, substantive prose", rid="r1"),
        _msg("still silent, substantive prose continues", rid="r2"),
        _msg(_block("nothing recorded.", [], unc=("cause unmeasured",),
                    nxt=""), rid="r3")], max_rounds=2)
    assert out["status"] == "ok"
    assert out["decision"]["total_inaction"] is True
    assert out["decision"]["progress"] == "no-activity"


def test_v2_valid_report_cannot_complete_empty(monkeypatch, tmp_path):
    init_db()
    from model_autopsy.backend.meta_api import client as C
    queue = [
        _msg("deviating note with no action, substantive prose", rid="r1"),
        _msg("still silent, substantive prose continues", rid="r2"),
        _msg(_block("nothing recorded.", [], unc=("cause unmeasured",),
                    nxt=""), rid="r3")]

    def fake(**kw):
        assert queue
        return queue.pop(0)

    monkeypatch.setattr(C, "create_response", fake)
    from model_autopsy.backend.live import driver as D
    rec = D.run_live_investigation("eval_music", tmp_path, max_rounds=1,
                                   run_id="m22v-" + tmp_path.name)
    assert rec["status"] == "inconclusive"
    assert rec["budget"]["experiments"] == [0, 6]


def test_v3_recovery_produces_evidence(monkeypatch):
    init_db(); s = _session(); inv = _inv(s)
    seen = []

    def fake(**kw):
        seen.append(kw)
        if len(seen) == 1:
            return _msg("deviating note, substantive prose here", rid="r1")
        if len(seen) == 2:
            return {"id": "r2", "status": "completed",
                    "output": [
                        {"type": "message", "content": [
                            {"type": "output_text",
                             "text": "proposing and measuring now"}]},
                        {"type": "function_call", "call_id": "c1",
                         "name": "propose_hypothesis",
                         "arguments": json.dumps(
                             {"text": "slice mechanism causes the gap"})},
                        {"type": "function_call", "call_id": "c2",
                         "name": "ranking_slice_diagnostics",
                         "arguments": json.dumps(SLICE_ARGS)}],
                    "usage": {"input_tokens": 1, "output_tokens": 1}}
        return _msg(_block("nothing recorded.", [],
                           unc=("cause unmeasured",), nxt=""), rid="r3")

    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget())
    assert out["status"] == "ok"
    assert out["decision"]["total_inaction"] is False
    assert out["decision"]["progress"] in ("diagnostic-progress",
                                           "sufficient-evidence")


def test_v4_recovery_bounded(monkeypatch):
    init_db(); s = _session(); inv = _inv(s)
    out = _run_turn(monkeypatch, s, inv, [
        _msg("silent one, substantive prose here", rid="r1"),
        _msg("silent two, substantive prose here", rid="r2"),
        _msg(_block("nothing recorded.", [], unc=("cause unmeasured",),
                    nxt=""), rid="r3")], max_rounds=3)
    assert out["usage_rollup"]["api_calls"] == 3
    from model_autopsy.backend.db import Event
    prompts = [e for e in s.query(Event).filter(
        Event.investigation_id == inv.id,
        Event.kind == "decision_prompt").all()
        if "Zero-action recovery" in (e.title or "")]
    assert len(prompts) == 1
    assert out["decision"]["incomplete_progression"] is True


def test_v5_calls_without_evidence(monkeypatch):
    init_db(); s = _session(); inv = _inv(s)
    bad = dict(SLICE_ARGS, slice_column="no_such_column")
    out = _run_turn(monkeypatch, s, inv, [
        {"id": "r1", "status": "completed",
         "output": [
             {"type": "message", "content": [
                 {"type": "output_text", "text": "running it"}]},
             {"type": "function_call", "call_id": "c1",
              "name": "ranking_slice_diagnostics",
              "arguments": json.dumps(bad)}],
         "usage": {"input_tokens": 1, "output_tokens": 1}},
        _msg(_block("nothing recorded.", [], unc=("cause unmeasured",),
                    nxt=""), rid="r2")], max_rounds=1)
    assert out["decision"]["progress"] == "activity-without-evidence"
    assert out["decision"]["total_inaction"] is False


def test_v6_evidence_supports_conclusion(monkeypatch):
    # A turn producing a fresh ran measurement is conclusion-capable.
    # (V3 covers the recovery path itself; this covers evidence value.)
    init_db(); s = _session(); inv = _inv(s)
    out = _run_turn(monkeypatch, s, inv, [
        {"id": "r1", "status": "completed",
         "output": [
             {"type": "message", "content": [
                 {"type": "output_text", "text": "proposing"}]},
             {"type": "function_call", "call_id": "c1",
              "name": "propose_hypothesis",
              "arguments": json.dumps(
                  {"text": "selective slice mechanism causes the gap"})},
             {"type": "function_call", "call_id": "c2",
              "name": "ranking_slice_diagnostics",
              "arguments": json.dumps(SLICE_ARGS)}],
         "usage": {"input_tokens": 1, "output_tokens": 1}},
        _msg(_block("nothing recorded.", [], unc=("cause unmeasured",),
                    nxt=""), rid="r2")], max_rounds=1)
    assert out["status"] == "ok"
    assert out["decision"]["total_inaction"] is False
    assert out["decision"]["progress"] in ("diagnostic-progress",
                                               "sufficient-evidence")
    assert out["decision"]["incomplete_progression"] is False


def test_v7_inconclusive_contract_preserved():
    from model_autopsy.backend.research import resolve as R
    c = R.contract("q", [], [], [], [], [], [], "Unresolved: nothing met",
                   {"level": "recorded"}, {}, "u", "limit")
    assert c["status"] == "unresolved"
    assert "unresolved" in c["note"]


def test_v8_m19_decline_preserved(monkeypatch):
    init_db(); s = _session(); inv = _inv(s)
    queue = [
        {"id": "r1", "status": "completed",
         "output": [
             {"type": "message", "content": [
                 {"type": "output_text", "text": "proposing"}]},
             {"type": "function_call", "call_id": "c1",
              "name": "propose_hypothesis",
              "arguments": json.dumps(
                  {"text": "selective slice mechanism causes the gap"})}]},
        _msg("no suitable diagnostic for this claim", rid="r2"),
    ]

    def fake(**kw):
        blob = json.dumps(kw, sort_keys=True, default=str)
        if "allowed_hypothesis_ids" in blob:
            return _dynamic_repair_block(kw)
        assert queue
        return queue.pop(0)

    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget())
    assert out["decision"]["incomplete_progression"] is True
    from model_autopsy.backend.db import Event
    prompts = [e for e in s.query(Event).filter(
        Event.investigation_id == inv.id,
        Event.kind == "decision_prompt").all()
        if "Zero-action recovery" in (e.title or "")]
    assert prompts == []


def test_v9_m20_repair_preserved(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    recs = [{"hypothesis_id": h.id, "status": "investigating",
             "basis": [act.id]} for h in hyps]
    out = _run_turn(monkeypatch, s, inv, [
        _msg("prose without any block, but substantive", rid="r1"),
        _msg(_block("mixed evidence, still open", recs,
                    unc=("cause unmeasured; slice gap contradicts uniformity",)),
             rid="r2")], max_rounds=2)
    assert out["usage_rollup"]["api_calls"] == 2
    assert out["summary"].get("repaired_via") == "summary_repair"


def test_v10_m21_empty_fallback_preserved(monkeypatch):
    init_db(); s = _session(); inv = _inv(s)
    out = _run_turn(monkeypatch, s, inv, [_msg("   ", rid="r1")],
                     max_rounds=2)
    assert out["repairs"] == []
    assert out["fallback"] is not None
    assert out["fallback"]["kind"] == "deterministic-fallback"
