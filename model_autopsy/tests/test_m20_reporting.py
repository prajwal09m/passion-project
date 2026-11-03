"""M20 Phase 7: reliable reporting + evidence-preserving repair (mocked
provider only, no live calls, no spend).

Covers: output classification (10), repair behavior (16), report
integrity (12), deterministic fallback (10), and regression guards
(M19 intact, API compatible, assembly read-only).
"""
import json

import pytest

from model_autopsy.backend.causal import summary_class as SC
from model_autopsy.backend.db import SessionLocal as _SessionLocal
from model_autopsy.backend.db import init_db

_open_sessions: list = []


def _session():
    """Session factory tracked for cleanup (M20: no leaked handles
    across the 600+ test full-suite run)."""
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


# ---- fixtures ---------------------------------------------------------------

def _inv(s, **cfg):
    from model_autopsy.backend import engine
    base = {"max_iterations": 3, "predictions_path": MUSIC,
            "m16_skeptic": False}
    base.update(cfg)
    return engine.create_investigation(s, "ml", "m20", "m20 probe", base)


def _mk(s, n_hyps=2, run_diag=True, statuses=None):
    """Investigation with hypotheses, one ran diagnostic, linked refs."""
    from model_autopsy.backend import engine
    inv = _inv(s)
    texts = [f"candidate mechanism {i}" for i in range(n_hyps)]
    for t in texts:
        engine.propose_hypothesis(s, inv, text=t,
                                  predicted_observation="probe decides")
    hyps = _hyps(s, inv)
    act = None
    if run_diag:
        out = engine.run_tool(s, inv, "ranking_slice_diagnostics",
                              dict(SLICE_ARGS), source_meta=True)
        assert out.get("ok"), out
        from model_autopsy.backend.db import Action
        act = s.get(Action, out["action_id"])
    if statuses:
        for h, st in zip(hyps, statuses):
            engine.update_hypothesis(s, h.id, st, rationale="m20 fixture")
    if act is not None:
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


def _snap(s, inv):
    from model_autopsy.backend.causal import report_consistency as RC
    return RC.build_snapshot(s, inv)


def _check(s, inv, summary):
    from model_autopsy.backend.causal import report_consistency as RC
    return RC.check(summary, RC.build_snapshot(s, inv))


def _turn(monkeypatch, s, inv, script, max_rounds=1):
    """Run one meta turn against a queued fake provider. Returns (out, sent)."""
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


# ---- 7.1 output classification (10) ------------------------------------------

def test_m20_class_valid_structured():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    h = hyps[0]
    v = _validate(s, inv, _block("done", [{"hypothesis_id": h.id,
                                           "status": "investigating",
                                           "basis": [act.id]}],
                                 unc=("cause unmeasured",)))
    assert v["valid"] is True
    assert v["output_class"] == "valid_structured"


def test_m20_class_prose_without_block_m19_verbatim():
    init_db(); s = _session(); inv, _, _ = _mk(s)
    m19_text = ("Testing whether top results stay relevant across catalog "
                "slices \u2014 measuring precision per slice.")
    v = _validate(s, inv, m19_text)
    assert v["valid"] is False
    assert v["output_class"] == "prose_without_block"


def test_m20_class_malformed_block():
    init_db(); s = _session(); inv, _, _ = _mk(s)
    v = _validate(s, inv, "```investigation_summary\n{conclusion: oops\n```")
    assert v["valid"] is False
    assert v["output_class"] == "malformed_block"


def test_m20_class_schema_invalid_missing_field():
    init_db(); s = _session(); inv, _, _ = _mk(s)
    v = _validate(s, inv, "```investigation_summary\n"
                         '{"status_recommendations": []}\n```')
    assert v["valid"] is False
    assert v["output_class"] == "schema_invalid"


def test_m20_class_schema_invalid_field_type():
    init_db(); s = _session(); inv, _, _ = _mk(s)
    v = _validate(s, inv, _block(42, []))
    assert v["valid"] is False
    assert v["output_class"] == "schema_invalid"


def test_m20_class_semantically_invalid_unknown_hyp():
    init_db(); s = _session(); inv, _, _ = _mk(s)
    v = _validate(s, inv, _block("c", [{"hypothesis_id": "nope-not-real",
                                        "status": "supported",
                                        "basis": []}]))
    assert v["valid"] is False
    assert v["output_class"] == "semantically_invalid"


def test_m20_class_empty_output():
    assert SC.classify("   ", {"valid": False, "errors": ["x"]})["class"] \
        == "empty_output"
    assert SC.classify("", {"valid": False, "errors": ["x"]})["class"] \
        == "empty_output"


def test_m20_class_provider_failure():
    c = SC.classify("whatever", None, provider_error="HTTP 503 upstream")
    assert c["class"] == "provider_failure"
    assert c["repair_eligible"] is False


def test_m20_class_extra_fields_still_valid():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    body = {"conclusion": "done", "status_recommendations": [],
            "uncertainties": ["q"], "recommended_next": "n",
            "surprise_extra": 1}
    v = _validate(s, inv, "```investigation_summary\n"
                         + json.dumps(body) + "\n```")
    assert v["valid"] is True
    assert v["output_class"] == "valid_structured"


def test_m20_class_conflicting_blocks():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    h = hyps[0]
    text = (_block("first story", [{"hypothesis_id": h.id,
                                    "status": "investigating",
                                    "basis": [act.id]}])
            + "\n"
            + _block("second story", [{"hypothesis_id": h.id,
                                       "status": "rejected",
                                       "basis": [act.id]}]))
    c = SC.classify(text, {"valid": True, "errors": []})
    assert c["class"] == "semantically_invalid"


# ---- 7.2 repair behavior (16) -------------------------------------------------

def _rec_block(hid, aid, status="investigating", also=None):
    """Repair block accounting for every hypothesis (dropping one is itself
    a consistency violation, tested separately)."""
    recs = [{"hypothesis_id": hid, "status": status, "basis": [aid]}]
    if also is not None:
        recs.append({"hypothesis_id": also, "status": "investigating",
                     "basis": [aid]})
    return _block("repaired verdict with contradicting slice evidence noted",
                  recs, unc=("cause unmeasured; slice gap contradicts uniformity",))


def test_m20_repair_prose_only_succeeds(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("prose without any block, but useful", rid="r1"),
        _msg(_rec_block(hyps[0].id, act.id, also=hyps[1].id), rid="r2")])
    assert out["status"] == "ok"
    assert len(sent) == 2  # exactly one repair attempt
    assert out["summary"]["valid"] is True
    assert out["summary"]["repaired_via"] == "summary_repair"
    assert out["fallback"] is None


def test_m20_repair_malformed_succeeds(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("```investigation_summary\n{broken json\n```", rid="r1"),
        _msg(_rec_block(hyps[0].id, act.id, also=hyps[1].id), rid="r2")])
    assert out["summary"]["valid"] is True
    assert len(sent) == 2


def test_m20_repair_schema_invalid_succeeds(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("```investigation_summary\n"
             '{"status_recommendations": []}\n```', rid="r1"),
        _msg(_rec_block(hyps[0].id, act.id, also=hyps[1].id), rid="r2")])
    assert out["summary"]["valid"] is True
    assert len(sent) == 2


def test_m20_repair_semantic_invalid_succeeds(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg(_block("bad", [{"hypothesis_id": "fabricated",
                             "status": "supported"}]), rid="r1"),
        _msg(_rec_block(hyps[0].id, act.id, also=hyps[1].id), rid="r2")])
    assert out["summary"]["valid"] is True
    assert len(sent) == 2


def test_m20_repair_still_malformed_rejected(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("plain prose, no block", rid="r1"),
        _msg("more prose, still no block", rid="r2")])
    assert out["summary"]["valid"] is False
    assert len(sent) == 2
    assert out["fallback"] is not None
    assert out["fallback"]["kind"] == "deterministic-fallback"


def test_m20_repair_unsupported_claims_rejected(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, _ = _turn(monkeypatch, s, inv, [
        _msg("round prose without any structured block", rid="r1"),
        _msg(_block("c", [{"hypothesis_id": "invented-id",
                           "status": "supported"}]), rid="r2")])
    assert out["summary"]["valid"] is False
    assert out["fallback"] is not None


def test_m20_repair_terminal_move_rejected(monkeypatch):
    from model_autopsy.backend import engine
    init_db(); s = _session()
    inv, hyps, act = _mk(s, statuses=["supported", "investigating"])
    engine.update_hypothesis(s, hyps[0].id, "supported",
                             rationale="fixture")
    out, _ = _turn(monkeypatch, s, inv, [
        _msg("round prose without any structured block", rid="r1"),
        _msg(_rec_block(hyps[0].id, act.id, status="rejected"), rid="r2")])
    assert out["summary"]["valid"] is False
    assert out["fallback"] is not None


def test_m20_repair_drops_contradiction_rejected(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    # hyps[1] carries a contradicts ref; repair mentions neither hyp.
    out, _ = _turn(monkeypatch, s, inv, [
        _msg("round prose without any structured block", rid="r1"),
        _msg(_block("all good, nothing contradicts", [], unc=("none",)),
             rid="r2")])
    assert out["summary"]["valid"] is False
    assert out["fallback"] is not None


def test_m20_repair_invents_verification_rejected(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, _ = _turn(monkeypatch, s, inv, [
        _msg("round prose without any structured block", rid="r1"),
        _msg(_block("independently verified by a second probe",
                     [{"hypothesis_id": hyps[0].id,
                       "status": "investigating",
                       "basis": [act.id]}]), rid="r2")])
    assert out["summary"]["valid"] is False
    assert out["fallback"] is not None


def test_m20_repair_invents_tool_execution_rejected(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, _ = _turn(monkeypatch, s, inv, [
        _msg("round prose without any structured block", rid="r1"),
        _msg(_block("c", [{"hypothesis_id": hyps[0].id,
                           "status": "investigating",
                           "basis": ["invented-action-id"]}]), rid="r2")])
    assert out["summary"]["valid"] is False
    assert out["fallback"] is not None


def test_m20_repair_confirmation_language_rejected(monkeypatch):
    from model_autopsy.backend.db import record_event
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    record_event(s, inv.id, "resolution", "Resolution contract: unresolved",
                 payload={"status": "unresolved",
                          "conclusion": "nothing confirmed"})
    s.commit()
    out, _ = _turn(monkeypatch, s, inv, [
        _msg("round prose without any structured block", rid="r1"),
        _msg(_block("CONFIRMED: mechanism proven",
                     [{"hypothesis_id": hyps[0].id,
                       "status": "investigating",
                       "basis": [act.id]}]), rid="r2")])
    assert out["summary"]["valid"] is False
    assert out["fallback"] is not None


def test_m20_repair_provider_failure_uses_fallback(monkeypatch):
    from model_autopsy.backend.meta_api import client as C
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("round prose without any structured block here", rid="r1"),
        C.MetaUnavailable("upstream 503")])
    assert out["summary"]["valid"] is False
    assert len(sent) == 2
    assert out["fallback"] is not None


def test_m20_single_repair_attempt_enforced(monkeypatch):
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [
        _msg("first round prose without any block, still useful", rid="r1"),
        _msg("repair round prose without any block either", rid="r2")])
    assert len(sent) == 2
    assert out["usage_rollup"]["summary_repair_attempts"] == 1
    assert len(out["repairs"]) == 1
    assert out["fallback"] is not None


def test_m20_empty_output_skips_repair(monkeypatch):
    from model_autopsy.backend.db import Event
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, sent = _turn(monkeypatch, s, inv, [_msg("   ", rid="r1")])
    assert len(sent) == 1  # no repair dispatched
    rep_evs = [e for e in s.query(Event).filter(
        Event.investigation_id == inv.id,
        Event.kind == "summary_repair").all()]
    assert any("not eligible" in (e.title or "") for e in rep_evs)
    assert out["fallback"] is not None


def test_m20_repair_eligibility_matrix():
    for cls in ("prose_without_block", "malformed_block",
                "schema_invalid", "semantically_invalid"):
        assert SC.repair_eligible_for(cls) is True
    for cls in ("valid_structured", "empty_output", "provider_failure"):
        assert SC.repair_eligible_for(cls) is False


def test_m20_repair_output_persisted_for_audit(monkeypatch):
    from model_autopsy.backend.db import Event
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out, _ = _turn(monkeypatch, s, inv, [
        _msg("round prose without any structured block", rid="r1"),
        _msg("repair prose without any structured block", rid="r2")])
    rep_evs = [e for e in s.query(Event).filter(
        Event.investigation_id == inv.id,
        Event.kind == "summary_repair").all()]
    assert any((e.payload or {}).get("repair_text_head") for e in rep_evs)


# ---- 7.3 report integrity (12) ------------------------------------------------

def _recs(s, inv, act):
    hyps = _hyps(s, inv)
    return [{"hypothesis_id": h.id, "status": "investigating",
             "basis": [act.id]} for h in hyps]


def test_m20_confirm_only_with_contract():
    from model_autopsy.backend.db import record_event
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "CONFIRMED: mechanism established",
            "status_recommendations": _recs(s, inv, act),
            "uncertainties": ["cause detail open"],
            "recommended_next": "collect labels"}
    record_event(s, inv.id, "resolution", "Resolution contract: confirmed",
                 payload={"status": "confirmed",
                          "conclusion": "CONFIRMED"})
    s.commit()
    assert _check(s, inv, summ)["passed"] is True


def test_m20_supported_cannot_become_confirmed():
    from model_autopsy.backend.db import record_event
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "the leading hypothesis is confirmed",
            "status_recommendations": _recs(s, inv, act),
            "uncertainties": ["detail open"],
            "recommended_next": "n"}
    record_event(s, inv.id, "resolution", "Resolution contract",
                 payload={"status": "partially-resolved",
                          "conclusion": "partial"})
    s.commit()
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("confirmation" in f for f in res["failures"])


def test_m20_rejected_cannot_become_supported():
    from model_autopsy.backend import engine
    init_db(); s = _session()
    inv, hyps, act = _mk(s, statuses=["rejected", "investigating"])
    summ = {"conclusion": "re-examining the rejected idea",
            "status_recommendations": [
                {"hypothesis_id": hyps[0].id, "status": "supported",
                 "basis": [act.id]},
                {"hypothesis_id": hyps[1].id, "status": "investigating",
                 "basis": [act.id]}],
            "uncertainties": ["q"], "recommended_next": "n"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("terminal" in f for f in res["failures"])


def test_m20_unresolved_must_be_carried():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "only the first idea matters",
            "status_recommendations": [
                {"hypothesis_id": hyps[0].id, "status": "investigating",
                 "basis": [act.id]}],
            "uncertainties": ["something open"], "recommended_next": "n"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("silently dropped" in f for f in res["failures"])


def test_m20_missing_evidence_reference_rejected():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "cites nothing",
            "status_recommendations": [
                {"hypothesis_id": hyps[0].id, "status": "investigating",
                 "basis": []},
                {"hypothesis_id": hyps[1].id, "status": "investigating",
                 "basis": []}],
            "uncertainties": ["q"], "recommended_next": "n"}
    # supported-without-basis is a base-validation failure; consistency
    # must also refuse when basis ids are absent-but-required. Here the
    # check targets unknown refs:
    summ["status_recommendations"][0]["basis"] = ["ghost-action"]
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("unknown evidence reference" in f for f in res["failures"])


def test_m20_fabricated_measurement_rejected():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "the gap is 9.8765 on every slice",
            "status_recommendations": _recs(s, inv, act),
            "uncertainties": ["q"], "recommended_next": "n"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("unsupported numeric" in f for f in res["failures"])


def test_m20_recorded_measurement_accepted():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    from model_autopsy.backend.db import Action as A
    corpus_num = None
    a = s.get(A, act.id)
    for v in json.dumps(a.result or {}, default=str).split('"'):
        t = v.strip().strip(":, ")
        try:
            float(t)
            if "." in t:
                corpus_num = t
                break
        except ValueError:
            continue
    assert corpus_num, "fixture diagnostic must record a decimal"
    summ = {"conclusion": f"the recorded gap is {corpus_num} on slices",
            "status_recommendations": _recs(s, inv, act),
            "uncertainties": ["cause open"], "recommended_next": "n"}
    assert _check(s, inv, summ)["passed"] is True


def test_m20_wrong_experiment_count_rejected():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "ran 99 experiments and all agree",
            "status_recommendations": _recs(s, inv, act),
            "uncertainties": ["q"], "recommended_next": "n"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("incorrect" in f for f in res["failures"])


def test_m20_invented_verification_rejected_without_probe():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "an independent probe verified the finding",
            "status_recommendations": _recs(s, inv, act),
            "uncertainties": ["q"], "recommended_next": "n"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("independent verification" in f for f in res["failures"])


def test_m20_verification_accepted_with_probe_record():
    from model_autopsy.backend.db import record_event
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    record_event(s, inv.id, "verification", "second probe confirms",
                 payload={"confirmed": True, "hypothesis_id": hyps[0].id})
    s.commit()
    summ = {"conclusion": "an independent probe verified the finding",
            "status_recommendations": _recs(s, inv, act),
            "uncertainties": ["residual q"], "recommended_next": "n"}
    assert _check(s, inv, summ)["passed"] is True


def test_m20_contradiction_cannot_disappear():
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import Action as A
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    out = engine.run_tool(s, inv, "artifact_summary", {},
                          source_meta=True)
    assert out.get("ok"), out
    other = out["action_id"]
    # Both recs cite only the second action; the action that carries the
    # contradicting evidence for hyps[1] vanishes without a trace.
    summ = {"conclusion": "everything supports the first idea",
            "status_recommendations": [
                {"hypothesis_id": hyps[0].id, "status": "investigating",
                 "basis": [other]},
                {"hypothesis_id": hyps[1].id, "status": "investigating",
                 "basis": [other]}],
            "uncertainties": ["all clear"], "recommended_next": "n"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("contradict" in f for f in res["failures"])


def test_m20_wrong_budget_figures_rejected():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    summ = {"conclusion": "used 999 tool calls of the budget",
            "status_recommendations": _recs(s, inv, act),
            "uncertainties": ["q"], "recommended_next": "n"}
    res = _check(s, inv, summ)
    assert res["passed"] is False
    assert any("incorrect" in f for f in res["failures"])


def test_m20_assembly_does_not_mutate_state():
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import report_consistency as RC
    from model_autopsy.backend.live import adapter as AD
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    valid = _validate(s, inv, _block(
        "recorded verdict",
        [{"hypothesis_id": h.id, "status": "investigating",
          "basis": [act.id]} for h in hyps]))
    assert valid["valid"]
    before = RC.state_fingerprint(s, inv)
    report = engine.build_report(s, inv)
    engine.ensure_finalizable(s, inv)
    engine.finalize(s, inv, report)
    AD.meta_report_to_eval(s, inv, report, "msg", valid, fallback=None)
    after = RC.state_fingerprint(s, inv)
    assert before == after


# ---- 7.4 deterministic fallback (10) -----------------------------------------

def _fallback(s, inv, report=None, errors=("e",), **kw):
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import fallback as FB
    report = report if report is not None else engine.build_report(s, inv)
    kw.setdefault("session", s)  # the live loop always passes a session
    return FB.compose(inv, report, list(errors), **kw)


def test_m20_fallback_complete_investigation():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    fb = _fallback(s, inv, session=s,
                   usage={"tokens": {"total_tokens": 10}})
    for key in ("investigation", "main_findings",
                "supported_but_unconfirmed", "unresolved_hypotheses",
                "evidence_for_each_finding", "contradictory_evidence",
                "independent_verification", "adversarial_outcome",
                "experiment_tool_summary", "token_financial_usage",
                "limitations", "final_scientific_resolution",
                "generation_statement", "conclusion", "uncertainties",
                "recommended_next", "evidence_action_ids",
                "model_summary_errors", "provenance", "kind"):
        assert key in fb, key
    assert fb["kind"] == "deterministic-fallback"
    assert fb["experiment_tool_summary"]["ran_count"] >= 1
    assert fb["independent_verification"]["performed"] is False


def test_m20_fallback_partial_investigation():
    init_db(); s = _session(); inv, hyps, act = _mk(
        s, run_diag=False)
    fb = _fallback(s, inv)
    assert fb["experiment_tool_summary"]["ran_count"] == 0
    assert "Inconclusive" in fb["conclusion"]


def test_m20_fallback_no_findings():
    from model_autopsy.backend import engine
    init_db(); s = _session(); inv = _inv(s)
    fb = _fallback(s, inv)
    assert "no supported or open hypotheses" in fb["conclusion"]
    assert fb["unresolved_hypotheses"] == []


def test_m20_fallback_multiple_statuses():
    init_db(); s = _session()
    inv, hyps, act = _mk(s, n_hyps=3,
                         statuses=["supported", "rejected",
                                   "investigating"])
    fb = _fallback(s, inv)
    assert len(fb["supported_but_unconfirmed"]) == 1
    assert len(fb["unresolved_hypotheses"]) == 1
    assert any(h["hypothesis_id"] == hyps[1].id
               for h in fb["rejected_findings"])


def test_m20_fallback_confirmed_and_unresolved():
    from model_autopsy.backend import engine
    init_db(); s = _session()
    inv, hyps, act = _mk(s, statuses=["investigating",
                                     "investigating"])
    report = engine.build_report(s, inv)
    report["confirmed"] = [{"summary": "recorded confirmed finding",
                            "evidence_action_id": act.id}]
    fb = _fallback(s, inv, report=report)
    assert fb["confirmed_findings"] == [
        {"summary": "recorded confirmed finding",
         "evidence_action_id": act.id}]
    assert fb["unresolved_hypotheses"]


def test_m20_fallback_contradictory_evidence():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    fb = _fallback(s, inv)
    assert fb["contradictory_evidence"] != "none recorded"
    assert any(c["action_id"] == act.id
               for c in fb["contradictory_evidence"])


def test_m20_fallback_missing_optional_metadata():
    from model_autopsy.backend import engine
    init_db(); s = _session(); inv = _inv(s)
    report = engine.build_report(s, inv)
    report.pop("generated_at", None)
    fb = _fallback(s, inv, report=report)
    assert fb["investigation"]["generated_at"] is None
    assert fb["token_financial_usage"]["tokens"].startswith("not recorded")


def test_m20_fallback_provider_failure_errors():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    fb = _fallback(s, inv, errors=["provider 503"])
    assert fb["model_summary_errors"] == ["provider 503"]
    assert fb["kind"] == "deterministic-fallback"


def test_m20_fallback_invalid_summary_errors():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    v = _validate(s, inv, "prose without block " * 5)
    fb = _fallback(s, inv, errors=v["errors"])
    assert "no structured summary" in fb["model_summary_errors"][0]


def test_m20_fallback_large_evidence_graph():
    from model_autopsy.backend import engine
    init_db(); s = _session()
    inv, hyps, act = _mk(s, run_diag=False)
    for i in range(60):
        out = engine.run_tool(s, inv, "ranking_slice_diagnostics",
                              dict(SLICE_ARGS), source_meta=True)
    report = engine.build_report(s, inv)
    fb = _fallback(s, inv, report=report)
    assert len(fb["evidence_action_ids"]) <= 50
    assert fb["experiment_tool_summary"]["ran_count"] >= 1


def test_m20_fallback_deterministic():
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    assert _fallback(s, inv) == _fallback(s, inv)


# ---- 7.5 regression ----------------------------------------------------------

def test_m20_eval_report_contract_stable():
    """Scorer-critical keys keep their shapes (additive provenance only)."""
    from model_autopsy.backend import engine
    from model_autopsy.backend.live import adapter as AD
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    valid = _validate(s, inv, _block(
        "recorded verdict",
        [{"hypothesis_id": h.id, "status": "investigating",
          "basis": [act.id]} for h in hyps]))
    report = engine.build_report(s, inv)
    out = AD.meta_report_to_eval(s, inv, report, "raw message text",
                                 valid, fallback=None)
    for key in ("executive_summary", "confirmed_findings",
                "rejected_hypotheses", "inconclusive", "experiments",
                "verification", "limitations", "investigation_id",
                "structured_summary_valid"):
        assert key in out, key
    assert out["report_generation_status"] == "model_native"
    assert out["report_provenance"]["output_class"] == "valid_structured"
    assert out["report_provenance"]["assembly_mutated_state"] is False


def test_m20_fallback_eval_report_provenance():
    from model_autopsy.backend import engine
    from model_autopsy.backend.live import adapter as AD
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    invalid = _validate(s, inv, "prose without block " * 5)
    report = engine.build_report(s, inv)
    fb = _fallback(s, inv, report=report)
    out = AD.meta_report_to_eval(s, inv, report, "raw message",
                                 invalid, fallback=fb)
    assert out["fallback_used"] is True
    assert out["report_generation_status"] == "deterministic_fallback"
    assert out["report_provenance"]["consistency_passed"] is True


def test_m20_original_preserved_across_repair(monkeypatch):
    """The invalid original is never overwritten by a repair attempt."""
    from model_autopsy.backend.db import Event
    init_db(); s = _session(); inv, hyps, act = _mk(s)
    orig = "original prose without block " * 4
    out, _ = _turn(monkeypatch, s, inv, [
        _msg(orig, rid="r1"),
        _msg("still prose, still no block", rid="r2")])
    texts = [(e.payload or {}).get("text", "")
             for e in s.query(Event).filter(
                 Event.investigation_id == inv.id,
                 Event.kind == "meta_response").all()]
    assert any(orig[:60] in t for t in texts)
    assert out["summary"]["valid"] is False
