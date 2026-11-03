"""M21: live reporting reliability & scientific integrity (offline only).

No live calls, no spend: every provider interaction uses a queued fake.
Covers the M21 evaluation protocol scenarios S1-S13:
  scientific integrity (10 failure modes from milestone §4),
  live-boundary harness recording (milestone §5),
  provenance distinguishability + frozen M20 contract pins,
  API/dashboard surfacing of the native consistency advisory.
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
    return engine.create_investigation(s, "ml", "m21", "m21 probe", base)


def _mk(s, n_hyps=2, statuses=None):
    """Two hypotheses, one ran diagnostic, supports/contradicts refs."""
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
    if statuses:
        for h, st in zip(hyps, statuses):
            engine.update_hypothesis(s, h.id, st, rationale="m21 fixture")
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


def _block(conclusion, recs, unc=("open q",), nxt="next step", conf=None):
    body = {"conclusion": conclusion, "status_recommendations": recs,
            "uncertainties": list(unc), "recommended_next": nxt}
    if conf is not None:
        body["confidence"] = conf
    return ("```investigation_summary\n" + json.dumps(body) + "\n```")


def _msg(text, rid="r"):
    return {"id": rid, "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50}}


def _validate(s, inv, text):
    from model_autopsy.backend import engine
    return engine.validate_structured_summary(s, inv, text)


def _check(s, inv, summary):
    from model_autopsy.backend.causal import report_consistency as RC
    return RC.check(summary, RC.build_snapshot(s, inv))


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


def _recs(hyps, act, status="investigating"):
    return [{"hypothesis_id": h.id, "status": status, "basis": [act.id]}
            for h in hyps]


def _evs(s, inv, kind=None):
    from model_autopsy.backend.db import Event
    q = s.query(Event).filter(Event.investigation_id == inv.id)
    if kind:
        q = q.filter(Event.kind == kind)
    return q.order_by(Event.seq.asc()).all()


# ---- S10/scientific integrity: the 10 failure modes --------------------------

def test_m21_confirm_without_contract_fails():
    """Confirmation language with no confirmed contract is a FAIL."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "CONFIRMED: mechanism established",
            "status_recommendations": _recs(hyps, act),
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("confirmation" in f for f in res["failures"])


def test_m21_prose_status_confirmed_rejected():
    """'confirmed' is not recommendable prose; only the contract confirms."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    recs = _recs(hyps, act)
    recs[0] = dict(recs[0], status="confirmed")
    summ = {"conclusion": "looks confirmed", "status_recommendations": recs,
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("confirmed" in f for f in res["failures"])


def test_m21_terminal_move_rejected():
    """A repair/report must not move a terminal supported->rejected."""
    init_db(); s = _session()
    inv, hyps, act = _mk(s, statuses=["supported", "investigating"])
    recs = _recs(hyps, act)
    recs[0] = dict(recs[0], status="rejected")
    summ = {"conclusion": "revisiting the supported finding",
            "status_recommendations": recs,
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("terminal state" in f for f in res["failures"])


def test_m21_no_terminal_resurrection():
    """rejected->supported is likewise immobile."""
    init_db(); s = _session()
    inv, hyps, act = _mk(s, statuses=["rejected", "investigating"])
    recs = _recs(hyps, act)
    recs[0] = dict(recs[0], status="supported")
    summ = {"conclusion": "revisiting the rejected finding",
            "status_recommendations": recs,
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("terminal state" in f for f in res["failures"])


def test_m21_independent_verification_claim_needs_probe():
    """Verification claimed without a confirmed probe record fails."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "the finding was independently verified",
            "status_recommendations": _recs(hyps, act),
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "an independent probe confirms it"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("verification" in f for f in res["failures"])


def test_m21_unknown_evidence_ref_fails():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    recs = _recs(hyps, act)
    recs[0] = dict(recs[0], basis=["no-such-action"])
    summ = {"conclusion": "grounded verdict",
            "status_recommendations": recs,
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("unknown evidence" in f for f in res["failures"])


def test_m21_silent_hypothesis_drop_fails():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    recs = _recs(hyps[:1], act)
    summ = {"conclusion": "one finding stands",
            "status_recommendations": recs,
            "uncertainties": ["something open"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("silently dropped" in f for f in res["failures"])


def test_m21_hidden_contradiction_fails():
    """Fixture h1 contradicts via act; omitting it + no mention fails."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    recs = _recs(hyps[:1], act)
    summ = {"conclusion": "uniform support across the board",
            "status_recommendations": recs,
            "uncertainties": ["nothing further"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("contradict" in f for f in res["failures"])


def test_m21_contradiction_preserved_passes():
    """Citing the contradicting action (or naming it) preserves honesty."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "mixed evidence with contradicting slice result",
            "status_recommendations": _recs(hyps, act),
            "uncertainties": ["cause unmeasured; slice gap contradicts "
                              " uniformity"],
            "recommended_next": "collect labels"}
    res = _check(s, inv, summ)
    assert res["passed"] is True, res["failures"]


def test_m21_invented_number_fails():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "precision gap of 7.77 points observed",
            "status_recommendations": _recs(hyps, act),
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("unsupported numeric claim" in f for f in res["failures"])


def test_m21_wrong_experiment_count_fails():
    """Proposed-only work must not read as executed: counts are checked."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "ran 3 diagnostics with convergent results",
            "status_recommendations": _recs(hyps, act),
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("incorrect" in f and "recorded: 1" in f
               for f in res["failures"])


def test_m21_unledgered_tool_warns():
    """Naming a tool with no ledger entry warns (not silent acceptance)."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "hadronic_probe settles the question",
            "status_recommendations": _recs(hyps, act),
            "uncertainties": ["cause unmeasured"],
            "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert any("hadronic_probe" in w for w in res["warnings"])


def test_m21_open_hypotheses_need_uncertainties():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "verdict with no limits stated",
            "status_recommendations": _recs(hyps, act),
            "uncertainties": [], "recommended_next": "done"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("uncertainties are missing" in f for f in res["failures"])


# ---- frozen M20 contract pins -------------------------------------------------

def test_m21_native_valid_with_findings_still_accepted():
    """M20 record-not-reject is frozen: advisory fails, validity stands."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    text = _block("CONFIRMED: mechanism established",
                  _recs(hyps, act), unc=("cause unmeasured",))
    v = _validate(s, inv, text)
    assert v["valid"] is True  # frozen: advisory never rejects native output
    assert v["output_class"] == "valid_structured"
    assert v["consistency_passed"] is False
    assert any("confirmation" in f for f in v["consistency_failures"])
    ev = _evs(s, inv, "summary")[-1]
    assert ev.payload["valid"] is True
    assert ev.payload["consistency_passed"] is False
    assert ev.payload["output_class"] == "valid_structured"


def test_m21_native_honest_advisory_passes():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    text = _block("mixed evidence; mechanism still open",
                  _recs(hyps, act),
                  unc=("cause unmeasured; slice gap contradicts uniformity",))
    v = _validate(s, inv, text)
    assert v["valid"] is True
    assert v["consistency_passed"] is True, v["consistency_failures"]
    assert v["consistency_failures"] == []


def test_m21_advisory_never_breaks_validation():
    """Snapshot failure degrades to a warning, never invalidates."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    text = _block("mixed evidence; mechanism still open",
                  _recs(hyps, act),
                  unc=("cause unmeasured; slice gap contradicts uniformity",))
    v = _validate(s, inv, text)
    assert v["valid"] is True
    assert isinstance(v["consistency_failures"], list)
    assert isinstance(v["consistency_warnings"], list)


# ---- live-boundary harness recording (S1-S9, offline fixtures) ----------------

def _good_block(hyps, act):
    return _block("mixed evidence with contradicting slice result noted",
                  [{"hypothesis_id": hyps[0].id, "status": "investigating",
                    "basis": [act.id]},
                   {"hypothesis_id": hyps[1].id, "status": "investigating",
                    "basis": [act.id]}],
                  unc=("cause unmeasured; slice gap contradicts uniformity",))


def test_m21_harness_native_path_records_everything(monkeypatch):
    """S1: raw text, class, eligibility, validation, advisory all recorded."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    text = _good_block(hyps, act)
    out, sent = _turn(monkeypatch, s, inv, [_msg(text, rid="r1")])
    assert out["status"] == "ok", out
    assert out["summary"]["valid"] is True
    assert out["fallback"] is None
    assert out["repairs"] == []
    meta = _evs(s, inv, "meta_response")
    assert meta and meta[0].payload["text"] == text  # raw verbatim
    summ = _evs(s, inv, "summary")[-1]
    assert summ.payload["valid"] is True
    assert summ.payload["output_class"] == "valid_structured"
    assert summ.payload["repair_eligible"] is False
    assert summ.payload["consistency_passed"] is True
    roll = out["usage_rollup"]
    assert roll["summary_repair_attempts"] == 0
    assert roll["fallback_used"] is False
    assert (roll["tokens"] or {}).get("input_tokens", 0) > 0


def test_m21_harness_repair_path_single_attempt(monkeypatch):
    """S2+S8: prose -> exactly one repair; raw repair text + usage kept."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("prose without any block, but substantive discussion", rid="r1"),
        _msg(_good_block(hyps, act), rid="r2")])
    assert out["status"] == "ok", out
    assert out["summary"]["valid"] is True
    assert out["summary"].get("repaired_via") == "summary_repair"
    assert len(out["repairs"]) == 1  # strictly one attempt
    assert out["usage_rollup"]["summary_repair_attempts"] == 1
    assert out["usage_rollup"]["api_calls"] == 2
    assert out["fallback"] is None
    repairs = _evs(s, inv, "summary_repair")
    assert len(repairs) == 3  # attempt + consistency gate + success
    assert any((e.payload or {}).get("passed") is True for e in repairs)
    first = _evs(s, inv, "summary")[0]
    assert first.payload["output_class"] == "prose_without_block"
    assert first.payload["repair_eligible"] is True
    # repair sends no tools and executes nothing new
    assert sent[1].get("tools") == []
    assert sent[1].get("previous_response_id") is None


def test_m21_harness_repair_rejection_keeps_original(monkeypatch):
    """S5+S9: valid-but-inconsistent repair rejected; fallback carries on."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    bad = _block("CONFIRMED: mechanism established",
                 _recs(hyps, act), unc=("cause unmeasured",))
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("prose without any block, but substantive discussion", rid="r1"),
        _msg(bad, rid="r2")])
    assert out["status"] == "ok", out
    assert out["summary"]["valid"] is False  # original verdict stands
    assert out["fallback"] is not None
    assert out["fallback"]["kind"] == "deterministic-fallback"
    assert len(out["repairs"]) == 1
    gate = [e for e in _evs(s, inv, "summary_repair")
            if (e.payload or {}).get("passed") is False]
    assert gate and gate[0].payload["failures"]


def test_m21_harness_empty_output_fallback_no_repair(monkeypatch):
    """S6: empty output is ineligible; repair never attempted."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [_msg("   ", rid="r1")])
    assert out["status"] == "ok", out
    assert out["repairs"] == []
    assert out["fallback"] is not None
    assert out["fallback"]["kind"] == "deterministic-fallback"
    inelig = [e for e in _evs(s, inv, "summary_repair")
              if "not eligible" in (e.title or "")]
    assert inelig
    assert inelig[0].payload["output_class"] == "empty_output"


def test_m21_harness_provider_failure_recorded(monkeypatch):
    """S7: provider failure is ineligible, recorded, never billed as work."""
    from model_autopsy.backend.meta_api import client as C
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("prose without any block, but substantive discussion", rid="r1"),
        C.MetaUnavailable("upstream 503")])
    assert out["status"] == "ok", out
    assert out["repairs"] and out["repairs"][0]["valid"] is None
    assert out["fallback"] is not None
    assert out["fallback"]["kind"] == "deterministic-fallback"
    # fallback provenance never claims a successful investigation
    assert "deterministic" in (out["fallback"]["provenance"] or "").lower()
    assert "CONFIRM" not in (out["fallback"]["conclusion"] or "").upper()


def test_m21_harness_provider_error_event_shape(monkeypatch):
    """Provider errors land in events with category; spend is accounted."""
    from model_autopsy.backend.meta_api import client as C
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        C.MetaUnavailable("HTTP 503: provider outage", status_code=503)])
    assert out["status"] == "meta_unavailable"
    assert not (out.get("summary") or {}).get("valid")  # no valid summary
    assert out.get("fallback") is None  # no chain, no fallback: honest stop
    reqs = _evs(s, inv, "meta_request")
    assert any((e.payload or {}).get("failure_category") for e in reqs)


def test_m21_harness_investigation_id_traceability(monkeypatch):
    """Every event and the eval report trace to the same investigation."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("prose without any block, but substantive discussion", rid="r1"),
        _msg(_good_block(hyps, act), rid="r2")])
    from model_autopsy.backend.db import Event
    ids = {e.investigation_id for e in
           s.query(Event).filter(Event.investigation_id == inv.id).all()}
    assert ids == {inv.id}
    from model_autopsy.backend import engine
    from model_autopsy.backend.live import adapter as AD
    engine.ensure_finalizable(s, inv)
    final = engine.build_report(s, inv)
    engine.finalize(s, inv, final)
    eval_report = AD.meta_report_to_eval(s, inv, final,
                                        out["message_text"], out["summary"],
                                        fallback=out["fallback"])
    assert eval_report["investigation_id"] == inv.id
    assert eval_report["report_generation_status"] == "model_repaired"


def test_m21_provenance_three_statuses_distinct(monkeypatch):
    """native / repaired / fallback provenance never collapse."""
    from model_autopsy.backend import engine
    from model_autopsy.backend.live import adapter as AD
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    final = engine.build_report(s, inv)
    native_text = _good_block(hyps, act)
    native = _validate(s, inv, native_text)
    r_native = AD.meta_report_to_eval(s, inv, final, native_text, native)
    assert r_native["report_generation_status"] == "model_native"
    assert r_native["report_provenance"]["status"] == "model_native"
    assert r_native["fallback_used"] is False
    repaired = dict(native, repaired_via="summary_repair")
    r_rep = AD.meta_report_to_eval(s, inv, final, native_text, repaired)
    assert r_rep["report_generation_status"] == "model_repaired"
    from model_autopsy.backend.causal import fallback as FB
    fb = FB.compose(inv, final, ["no block"], session=s)
    r_fb = AD.meta_report_to_eval(s, inv, final, "prose", native,
                                  fallback=fb)
    assert r_fb["report_generation_status"] == "deterministic_fallback"
    assert r_fb["fallback_used"] is True
    assert r_fb["deterministic_fallback"]["kind"] == "deterministic-fallback"
    statuses = {r_native["report_generation_status"],
                r_rep["report_generation_status"],
                r_fb["report_generation_status"]}
    assert statuses == {"model_native", "model_repaired",
                        "deterministic_fallback"}


def test_m21_engine_dedup_no_double_execution():
    """Same tool+args never executes twice (retry safety at the engine)."""
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    from model_autopsy.backend import engine
    first = engine.run_tool(s, inv, "ranking_slice_diagnostics",
                            dict(SLICE_ARGS), source_meta=True)
    assert first.get("reused") is True  # fixture already ran it
    from model_autopsy.backend.db import Action
    n = s.query(Action).filter(Action.investigation_id == inv.id,
                               Action.tool_name ==
                               "ranking_slice_diagnostics").count()
    assert n == 1


def test_m21_repair_consumes_attempt_budget(monkeypatch):
    """The single repair attempt is budget-accounted, never free."""
    from model_autopsy.backend.live import governor as G
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.meta_api import client as C
    sent = []
    queue = [_msg("prose without any block, substantive", rid="r1"),
             _msg(_good_block(hyps, act), rid="r2")]

    def fake(**kw):
        sent.append(kw)
        return queue.pop(0)

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    before = b.attempts_used
    out = L.run_meta_turn(s, inv, max_rounds=1, budget=b)
    assert out["status"] == "ok", out
    assert b.attempts_used == before + 2  # round + exactly one repair


# ---- API / dashboard surfacing -------------------------------------------------

def test_m21_causal_view_exposes_native_advisory():
    """Causal view carries per-summary consistency + generation status."""
    from fastapi.testclient import TestClient
    from model_autopsy.backend import api as API
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    _validate(s, inv, _block("CONFIRMED: mechanism established",
                             _recs(hyps, act), unc=("cause unmeasured",)))
    inv_id = inv.id
    s.close()
    with TestClient(API.app) as c:
        r = c.get(f"/api/investigations/{inv_id}/causal")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["report_validation"]["summaries"]
    s0 = body["report_validation"]["summaries"][0]
    assert s0["valid"] is True
    assert s0["output_class"] == "valid_structured"
    assert s0["consistency_passed"] is False
    assert any("confirmation" in f for f in s0["consistency_failures"])
    assert body["report_validation"]["generation_status"] == "model_native"
    # pre-existing keys untouched
    assert "hypotheses" in body and "coverage" in body
    assert "selection" in body and "transitions" in body
