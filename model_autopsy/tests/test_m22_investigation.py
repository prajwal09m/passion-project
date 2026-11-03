"""M22: evidence-floor completion + total-inaction handling (offline only).

No live calls, no spend: every provider interaction is a queued fake.
Covers the M21 failure (silent model certified as complete) and the
M22 protections: evidence floor, inaction flag, bounded recovery,
progress tracking, honest inconclusive status.
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


def _inv(s, **cfg):
    from model_autopsy.backend import engine
    base = {"max_iterations": 3, "predictions_path": MUSIC,
            "m16_skeptic": False}
    base.update(cfg)
    return engine.create_investigation(s, "ml", "m22", "m22 probe", base)


def _mk(s, n_hyps=2):
    """Fixture with hypotheses + one ran diagnostic + linked refs."""
    from model_autopsy.backend import engine
    inv = _inv(s)
    for i in range(n_hyps):
        engine.propose_hypothesis(s, inv, text=f"candidate mechanism {i}",
                                  predicted_observation="probe decides")
    hyps = _hyps(s, inv)
    out = engine.run_tool(s, inv, "ranking_slice_diagnostics",
                          dict(SLICE_ARGS), source_meta=True)
    assert out.get("ok"), out
    from model_autopsy.backend.db import Action
    act = s.get(Action, out["action_id"])
    hyps[0].evidence_refs = [{"action_id": act.id,
                              "tool": act.tool_name,
                              "relation": "supports"}]
    if len(hyps) > 1:
        hyps[1].evidence_refs = [{"action_id": act.id,
                                  "tool": act.tool_name,
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


def _calls_msg(text, *specs, rid="r"):
    items = [{"type": "message", "content": [
        {"type": "output_text", "text": text}]}]
    for cid, name, args in specs:
        items.append({"type": "function_call", "call_id": cid,
                      "name": name,
                      "arguments": json.dumps(args, sort_keys=True)})
    return {"id": rid, "status": "completed",
            "output": items,
            "usage": {"input_tokens": 100, "output_tokens": 50}}


def _turn(monkeypatch, s, inv, script, max_rounds=1):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.live import governor as G
    sent = []
    queue = list(script)

    def fake(**kw):
        sent.append(kw)
        assert queue, "provider called more times than scripted"
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=max_rounds, budget=G.Budget())
    return out, sent


def _evs(s, inv, kind=None):
    from model_autopsy.backend.db import Event
    q = s.query(Event).filter(Event.investigation_id == inv.id)
    if kind:
        q = q.filter(Event.kind == kind)
    return q.order_by(Event.seq.asc()).all()


def _empty_block():
    return _block("No diagnostic evidence recorded; inconclusive.",
                  [], unc=("cause unmeasured",), nxt="")


def _honest_block(hyps, act):
    return _block("mixed evidence with contradicting slice result noted",
                  [{"hypothesis_id": h.id, "status": "investigating",
                    "basis": [act.id]} for h in hyps],
                  unc=("cause unmeasured; slice gap contradicts uniformity",))


# ---- P0: total-inaction flag + progress --------------------------------------

def test_m22_silent_turn_flagged_total_inaction(monkeypatch):
    """M21 replay at turn level: zero hyps + zero calls is flagged."""
    init_db(); s = _session(); inv = _inv(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("deviating note with no action, substantive prose", rid="r1"),
        _msg("still no action, substantive prose here", rid="r2"),
        _msg(_empty_block(), rid="r3")], max_rounds=2)
    assert out["status"] == "ok", out
    d = out["decision"]
    assert d["total_inaction"] is True
    assert d["progress"] == "no-activity"
    assert d["incomplete_progression"] is True
    assert d["next_action"] == "no-diagnostic-no-reason"


def test_m22_zero_action_recovery_sent_once(monkeypatch):
    """Recovery fires exactly once per turn, then the loop stops."""
    init_db(); s = _session(); inv = _inv(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("deviating note with no action, substantive prose", rid="r1"),
        _msg("still no action, substantive prose here", rid="r2"),
        _msg(_empty_block(), rid="r3")], max_rounds=3)
    # round1 prose, round2 recovery response, repair = 3 provider calls
    assert out["usage_rollup"]["api_calls"] == 3
    prompts = [e for e in _evs(s, inv, "decision_prompt")
               if "Zero-action recovery" in (e.title or "")]
    assert len(prompts) == 1
    assert out["summary"]["valid"] is True  # repair accepted honest empty


def test_m22_recovery_resumes_investigation(monkeypatch):
    """A model that answers the nudge performs real diagnostics."""
    init_db(); s = _session(); inv = _inv(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("deviating note with no action, substantive prose", rid="r1"),
        _calls_msg("proposing and measuring now",
                   ("c1", "propose_hypothesis",
                    {"text": "selective slice mechanism causes the gap"}),
                   ("c2", "ranking_slice_diagnostics", SLICE_ARGS),
                   rid="r2"),
        _msg(_empty_block(), rid="r3")], max_rounds=2)
    assert out["status"] == "ok", out
    d = out["decision"]
    assert d["total_inaction"] is False
    assert d["progress"] in ("diagnostic-progress", "sufficient-evidence")
    assert d["incomplete_progression"] is False
    from model_autopsy.backend.db import Action
    ran = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    # model diagnostic + end-of-turn reservation probe
    assert ran >= 1


def test_m22_recovery_not_sent_when_hyps_exist(monkeypatch):
    """M20 repair path unchanged: hyps on record means no recovery round."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("prose without any block, but substantive", rid="r1"),
        _msg(_honest_block(hyps, act), rid="r2")], max_rounds=2)
    assert out["status"] == "ok", out
    assert out["usage_rollup"]["api_calls"] == 2  # round + repair only
    prompts = [e for e in _evs(s, inv, "decision_prompt")
               if "Zero-action recovery" in (e.title or "")]
    assert prompts == []
    assert out["summary"].get("repaired_via") == "summary_repair"


def test_m22_failed_diagnostic_is_activity_without_evidence(monkeypatch):
    """A tool call alone is not progress: failed run != evidence."""
    init_db(); s = _session(); inv = _inv(s)
    bad = dict(SLICE_ARGS, slice_column="no_such_column")
    out, sent = _turn(monkeypatch, s, inv, [
        _calls_msg("running the diagnostic",
                   ("c1", "ranking_slice_diagnostics", bad), rid="r1"),
        _msg(_empty_block(), rid="r2")], max_rounds=1)
    assert out["status"] == "ok", out
    d = out["decision"]
    assert d["total_inaction"] is False  # work was attempted
    assert d["progress"] == "activity-without-evidence"
    from model_autopsy.backend.db import Action
    ran = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    assert ran == 0


def test_m22_progress_classifier_unit():
    from model_autopsy.backend.meta_api.loop import _classify_turn_progress as f
    assert f(new_hypotheses=0, executed_any=False,
             ran_new=0, verify_ready=False) == "no-activity"
    assert f(new_hypotheses=1, executed_any=False,
             ran_new=0, verify_ready=False) == "activity-without-evidence"
    assert f(new_hypotheses=0, executed_any=True,
             ran_new=0, verify_ready=False) == "activity-without-evidence"
    assert f(new_hypotheses=1, executed_any=True,
             ran_new=1, verify_ready=False) == "diagnostic-progress"
    assert f(new_hypotheses=0, executed_any=True,
             ran_new=1, verify_ready=True) == "sufficient-evidence"


# ---- P0: evidence floor at driver level ---------------------------------------

def _driver_script(*items):
    return list(items)


def _run_driver(monkeypatch, tmp_path, script, max_rounds=1):
    from model_autopsy.backend.meta_api import client as C
    seen = []
    queue = list(script)

    def fake(**kw):
        seen.append(kw)
        assert queue, "provider called more times than scripted"
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(C, "create_response", fake)
    from model_autopsy.backend.live import driver as D
    rec = D.run_live_investigation("eval_music", tmp_path,
                                   max_rounds=max_rounds,
                                   run_id="m22-" + tmp_path.name)
    return rec, seen


def test_m22_empty_run_never_completed(monkeypatch, tmp_path):
    """Evidence floor: silent model cannot earn a completed run."""
    init_db()
    rec, seen = _run_driver(monkeypatch, tmp_path, [
        _msg("deviating note with no action, substantive prose", rid="r1"),
        _msg("still silent, substantive prose continues", rid="r2"),
        _msg(_empty_block(), rid="r3")], max_rounds=1)
    assert rec["status"] == "inconclusive"
    assert rec["budget"]["experiments"] == [0, 6]
    import json as _json
    manifest = _json.loads(
        (tmp_path / rec["run_id"] / "manifest.json").read_text())
    assert manifest["status"] == "inconclusive"


def test_m22_persistent_silence_bounded_and_honest(monkeypatch, tmp_path):
    """Two silent turns hit the stall rule: bounded, recorded, inconclusive."""
    init_db()
    rec, seen = _run_driver(monkeypatch, tmp_path, [
        _msg("silent one, substantive prose here", rid="r1"),
        _msg("silent two, substantive prose here", rid="r2"),
        _msg(_empty_block(), rid="r3"),
        _msg("silent three, substantive prose here", rid="r4"),
        _msg("silent four, substantive prose here", rid="r5"),
        _msg(_empty_block(), rid="r6")], max_rounds=2)
    assert rec["status"] == "inconclusive"
    # turn 1: 2 rounds + repair = 3 attempts; turn 2 never dispatches:
    # the stopping rule fires honestly with zero hypotheses on record
    assert rec["budget"]["attempts"][0] == 3, rec["budget"]
    # the driver writes its own live.sqlite3; read the durable dump
    import json as _json
    evs = _json.loads(
        (tmp_path / rec["run_id"] / "events_dump.json").read_text())
    stops = [e for e in evs if e.get("kind") == "stopping"]
    assert len(stops) == 1
    assert "no hypotheses on record" in ((stops[0].get("payload") or {})
                                               .get("rationale", ""))
    recoveries = [e for e in evs if e.get("kind") == "decision_prompt"
                  and "Zero-action recovery" in (e.get("title") or "")]
    assert len(recoveries) == 1  # strictly one bounded nudge


def test_m22_stall_break_after_evidence_less_turns(monkeypatch, tmp_path):
    """Stall rule still bounds runs: model adds nothing after turn 1.

    The end-of-turn reservation still records its own probe, so this run
    honestly completes WITH evidence; the stall event proves the bound."""
    init_db()
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.db import SessionLocal as _SL
    seen = []
    queue = [
        _calls_msg("proposing now",
                   ("c1", "propose_hypothesis",
                    {"text": "selective slice mechanism causes the gap A"}),
                   ("c2", "propose_hypothesis",
                    {"text": "uniform exposure mechanism causes the gap B"}),
                   rid="r1"),
        _msg("round two prose, no block here", rid="r2"),
        _msg("round three prose, no block here", rid="r3"),
        _msg("round four prose, no block here", rid="r4"),
    ]

    def fake(**kw):
        seen.append(kw)
        blob = json.dumps(kw, sort_keys=True, default=str)
        if "allowed_hypothesis_ids" in blob:
            # dynamic repair: cite the ids the repair prompt allows
            ids = []
            for item in kw.get("input_items") or []:
                try:
                    body = json.loads(item.get("content") or "{}")
                except (ValueError, AttributeError):
                    continue
                if isinstance(body, dict) and body.get(
                        "allowed_hypothesis_ids"):
                    ids = list(body["allowed_hypothesis_ids"])
                    break
            assert ids, "repair prompt carries no hypothesis ids"
            return _msg(_block("open verdict, nothing measured yet",
                               [{"hypothesis_id": i,
                                 "status": "investigating"} for i in ids],
                               unc=("cause unmeasured",)), rid="rep")
        assert queue, "provider called more times than scripted"
        return queue.pop(0)

    monkeypatch.setattr(C, "create_response", fake)
    from model_autopsy.backend.live import driver as D
    rec = D.run_live_investigation("eval_music", tmp_path, max_rounds=3,
                                   run_id="m22-" + tmp_path.name)
    import json as _json
    rundir = tmp_path / rec["run_id"]
    evs = _json.loads((rundir / "events_dump.json").read_text())
    stalls = [e for e in evs if e.get("kind") == "stopping"
              and "two consecutive turns" in (e.get("title") or "")]
    assert len(stalls) == 1
    actions = _json.loads((rundir / "actions.json").read_text())
    assert any(a.get("status") == "ran" for a in actions)
    assert rec["status"] == "completed"  # evidence exists: honest


def test_m22_evidence_run_still_completes(monkeypatch, tmp_path):
    """Legitimate work still earns completion: floor is evidence, not counts."""
    init_db()
    rec, seen = _run_driver(monkeypatch, tmp_path, [
        _calls_msg("proposing and measuring",
                   ("c1", "propose_hypothesis",
                    {"text": "selective slice mechanism causes the gap"}),
                   ("c2", "ranking_slice_diagnostics", SLICE_ARGS),
                   rid="r1"),
        _msg("round two prose, no block here", rid="r2"),
        _msg("repair also broken, no block", rid="r3")], max_rounds=1)
    assert rec["status"] == "completed", rec
    assert rec["budget"]["experiments"][0] >= 1
    import json as _json
    eval_report = _json.loads(
        (tmp_path / rec["run_id"] / "eval_report.json").read_text())
    assert eval_report["fallback_used"] is True  # honest fallback path
    assert eval_report["report_generation_status"] == \
        "deterministic_fallback"


def test_m22_floor_break_with_evidence_and_valid_summary(monkeypatch):
    """Valid summary + ran evidence keeps the historic break behavior."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("prose without any block, but substantive", rid="r1"),
        _msg(_honest_block(hyps, act), rid="r2")], max_rounds=1)
    assert out["status"] == "ok", out
    assert out["summary"]["valid"] is True
    assert out["summary"].get("repaired_via") == "summary_repair"
    assert out["tool_calls"] == []
    # evidence floor met: the driver break condition still fires
    from model_autopsy.backend.db import Action
    ran = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    assert ran >= 1
    assert not (out["tool_calls"] == [] and out["summary"]["valid"]
                and ran == 0)
    d = out["decision"]
    # the turn itself contributed nothing new (fixture predates it), so
    # total_inaction is honestly True — but the deferral text keeps the
    # M19 decline contract (recorded reason => not incomplete).
    assert d["total_inaction"] is True
    assert d["incomplete_progression"] is False
