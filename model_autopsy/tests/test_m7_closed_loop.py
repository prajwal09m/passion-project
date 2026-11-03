"""M7 closed-loop tests (offline: scripted provider, zero credits).

Proves the REAL live path (`loop.run_meta_turn` + `engine.run_tool` +
`linker` + `planning`) moves hypothesis statuses, injects selection
briefs, and records adherence — not isolated utilities.
"""
from __future__ import annotations

import json

TURBINE = "model_autopsy/tests/fixture_eval/investigator/turbine_output.csv"
CLAIM = "model_autopsy/tests/fixture_eval/investigator/claim_severity.csv"


def _resp(text="", calls=(), rid="resp_1"):
    out = []
    if text:
        out.append({"type": "message", "content": [
            {"type": "output_text", "text": text}]})
    for call_id, name, args in calls:
        out.append({"type": "function_call", "call_id": call_id,
                    "name": name, "arguments": json.dumps(args)})
    return {"id": rid, "status": "completed", "output": out,
            "usage": {"input_tokens": 100, "output_tokens": 50,
                      "total_tokens": 150}}


def _mem_session():
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm
    from model_autopsy.backend import db as DB
    e = _ce("sqlite:///:memory:")
    DB.Base.metadata.create_all(e)
    return _sm(bind=e, autoflush=False, expire_on_commit=False)()


def _new_inv(s, predictions=TURBINE):
    import os
    os.environ["MODEL_AUTOPSY_TESTING"] = "1"
    from model_autopsy.backend import engine
    return engine.create_investigation(
        s, "ml", "Closed loop test", "What fails?",
        {"max_iterations": 3, "predictions_path": predictions})


def _hyps(s, inv_id):
    from model_autopsy.backend.db import Hypothesis
    return list(s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv_id).all())


def _one(hyps, needle):
    hits = [h for h in hyps if needle in h.text]
    assert len(hits) == 1, (needle, [h.text[:40] for h in hyps])
    return hits[0]


# 1. Live turn moves statuses + records brief/adherence/linker events.
def test_live_turn_auto_links_and_briefs(monkeypatch):
    from model_autopsy.backend import db
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    db.init_db()
    s = db.SessionLocal()
    try:
        from model_autopsy.backend import engine
        inv = engine.create_investigation(
            s, "ml", "Loop test", "What fails?",
            {"max_iterations": 3, "predictions_path": TURBINE})
        seen_inputs = []
        script = [
            _resp(calls=(
                ("c1", "propose_hypothesis", {
                    "text": "Recent level shift in the test period causes "
                            "the forecast miss",
                    "predicted_observation": "late error much larger than "
                                             "early error with clean splits",
                    "confidence_note": "uncalibrated prior"}),
                ("c2", "propose_hypothesis", {
                    "text": "Apparent miss is a data quality artifact with "
                            "nulls and duplicate rows",
                    "predicted_observation": "quality screen shows nulls or "
                                             "duplicates",
                    "confidence_note": "uncalibrated prior"})), rid="r1"),
            _resp(calls=(("c3", "data_quality_profile",
                           {"predictions_path": TURBINE}),), rid="r2"),
            _resp("nothing further to add", rid="r3"),
        ]

        def fake(**kw):
            seen_inputs.append(kw.get("input_items"))
            return script[min(len(seen_inputs) - 1, len(script) - 1)]
        monkeypatch.setattr(C, "create_response", fake)
        out = L.run_meta_turn(s, inv, max_rounds=2)
        assert out["status"] == "ok"
        hyps = _hyps(s, inv.id)
        drift = _one(hyps, "level shift")
        qual = _one(hyps, "data quality")
        # data_quality on clean turbine contradicts the quality hypothesis.
        assert qual.status == "investigating"
        assert qual.confidence == 15
        assert "auto-link" in (qual.status_justification or "")
        assert drift.status == "proposed"  # untouched: no evidence either way
        kinds = [e.kind for e in s.query(db.Event).filter(
            db.Event.investigation_id == inv.id).all()]
        assert "selection" in kinds and "linker" in kinds
        # Selection brief was actually sent to the provider.
        assert any("selection_brief" in json.dumps(it or "")
                   for items in seen_inputs for it in (items or []))
        # Adherence recorded with a boolean verdict.
        sel = [e for e in s.query(db.Event).filter(
            db.Event.investigation_id == inv.id,
            db.Event.kind == "selection").all()]
        assert any((e.payload or {}).get("followed") in (True, False)
                   for e in sel)
    finally:
        s.close()


# 2. Corroboration promotes; double contradiction rejects (real engine path).
def test_corroboration_promotes_to_supported():
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    from model_autopsy.backend.db import Action
    s = _mem_session()
    inv = _new_inv(s)
    engine.propose_hypothesis(
        s, inv, "Recent level shift in test period causes forecast miss " +
        "x" * 20)
    hid = _one(_hyps(s, inv.id), "level shift").id
    for tool, args in (
            ("temporal_changepoint_scan", {"predictions_path": TURBINE}),
            ("residual_time_analysis", {"predictions_path": TURBINE})):
        r = engine.run_tool(s, inv, tool, args, source_meta=True)
        assert r["ok"], r
        a = s.get(Action, r["action_id"])
        LK.link_tool_result(s, inv, a)
    h = _one(_hyps(s, inv.id), "level shift")
    assert h.status == "supported", (h.status, h.status_justification)
    assert len(h.evidence_refs) == 2


STABLE = "model_autopsy/tests/fixture_eval/investigator/stable_output.csv"


def test_double_contradiction_rejects():
    """Two DISTINCT drift probes both contradict a level-shift claim.

    History: the original version of this test paired
    forecast_diagnostics (split-hygiene contradicts: splits are clean)
    with data_quality_profile (quality contradicts: no nulls/dups) on
    TURBINE and expected both to reject a 'split overlap leakage
    artifact' hypothesis. Under M8/M9 evidence semantics that second
    link is invalid: a clean null/duplicate screen says nothing about
    whether train/test splits overlap -- the old expectation passed
    only because the word 'artifact' in the hypothesis matched the
    quality family's word list ('artifact' is in _is_quality). That is
    exactly the topic-word over-attribution M8/M9 fixed: mentioning a
    topic is not evidence about the mechanism.

    Genuine double contradiction therefore needs two measurements that
    each test the claimed mechanism. A level-shift claim on the frozen
    STABLE fixture (stationary target, no break, negligible
    train/test shift) is contradicted by temporal_changepoint_scan
    (|shift| < 1) AND distribution_shift_profile (|mean_shift| < 0.1
    scale) -- two tools, same mechanism, both genuinely contradicting.
    """
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    from model_autopsy.backend.db import Action
    s = _mem_session()
    inv = _new_inv(s, predictions=STABLE)
    engine.propose_hypothesis(
        s, inv, "Recent level shift in test period causes forecast miss " +
        "y" * 20)
    hid = _one(_hyps(s, inv.id), "level shift").id
    for tool, args in (
            ("temporal_changepoint_scan", {"predictions_path": STABLE}),
            ("distribution_shift_profile", {"predictions_path": STABLE,
                                              "split_column": "split"})):
        r = engine.run_tool(s, inv, tool, args, source_meta=True)
        assert r["ok"], r
        LK.link_tool_result(s, inv, r["action_id"] and s.get(
            Action, r["action_id"]))
    h = _one(_hyps(s, inv.id), "level shift")
    assert h.status == "rejected", (h.status, h.status_justification)
    assert len([r for r in h.evidence_refs
                if r.get("relation") == "contradicts"]) == 2


def test_genuine_split_contradiction_links():
    """No-overlap evidence DOES contradict a split-overlap claim.

    Regression guard for the attribution fix (split-hygiene <->
    leakage mechanism equivalence, parity with linker._MATCH): a
    clean-split measurement directly tests an overlap claim, so it
    must move belief exactly once.
    """
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    from model_autopsy.backend.db import Action
    s = _mem_session()
    inv = _new_inv(s)
    engine.propose_hypothesis(
        s, inv, "Apparent miss is split overlap leakage artifact " + "y" * 20)
    r = engine.run_tool(s, inv, "forecast_diagnostics",
                        {"predictions_path": TURBINE,
                         "split_column": "split"}, source_meta=True)
    assert r["ok"], r
    LK.link_tool_result(s, inv, s.get(Action, r["action_id"]))
    h = _one(_hyps(s, inv.id), "split overlap")
    moving = [x for x in h.evidence_refs
              if x.get("relation") in ("supports", "contradicts")]
    assert len(moving) == 1 and moving[0]["relation"] == "contradicts"
    assert h.status == "investigating", (h.status, h.status_justification)


def test_topical_overlap_does_not_reject():
    """Clean nulls/duplicates must NOT reject a split-overlap claim.

    Pins the M8/M9 semantic: data_quality_profile's clean screen is
    recorded visibly (relevant_to via the generic word 'artifact')
    but never moves belief about splits. One genuine contradiction
    (clean splits) + one topical observation = investigating, never
    rejected.
    """
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    from model_autopsy.backend.db import Action
    s = _mem_session()
    inv = _new_inv(s)
    engine.propose_hypothesis(
        s, inv, "Apparent miss is split overlap leakage artifact " + "y" * 20)
    for tool, args in (
            ("forecast_diagnostics", {"predictions_path": TURBINE,
                                        "split_column": "split"}),
            ("data_quality_profile", {"predictions_path": TURBINE})):
        r = engine.run_tool(s, inv, tool, args, source_meta=True)
        assert r["ok"], r
        LK.link_tool_result(s, inv, r["action_id"] and s.get(
            Action, r["action_id"]))
    h = _one(_hyps(s, inv.id), "split overlap")
    assert h.status == "investigating", (h.status, h.status_justification)
    assert len([x for x in h.evidence_refs
                if x.get("relation") == "contradicts"]) == 1
    assert any(x.get("relation") == "relevant_to"
               for x in h.evidence_refs)


# 3. Failed experiments never generate evidence; linking is idempotent.
def test_failed_tool_never_links():
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    from model_autopsy.backend.db import Action
    s = _mem_session()
    inv = _new_inv(s)
    engine.propose_hypothesis(
        s, inv, "Recent level shift in test period causes forecast miss " +
        "z" * 20)
    r = engine.run_tool(s, inv, "time_split_validation",
                        {"predictions_path": TURBINE}, source_meta=True)
    assert not r["ok"]
    a = s.get(Action, r["action_id"])
    assert a.status == "failed"
    assert LK.link_tool_result(s, inv, a) == []
    h = _one(_hyps(s, inv.id), "level shift")
    assert h.status == "proposed" and not h.evidence_refs


def test_link_idempotent():
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    from model_autopsy.backend.db import Action
    s = _mem_session()
    inv = _new_inv(s)
    engine.propose_hypothesis(
        s, inv, "Recent level shift in test period causes forecast miss " +
        "w" * 20)
    r = engine.run_tool(s, inv, "temporal_changepoint_scan",
                        {"predictions_path": TURBINE}, source_meta=True)
    a = s.get(Action, r["action_id"])
    first = LK.link_tool_result(s, inv, a)
    assert len(first) == 1
    assert LK.link_tool_result(s, inv, a) == []
    h = _one(_hyps(s, inv.id), "level shift")
    assert len(h.evidence_refs) == 1


# 4. New diagnostic makes feature-dependence evidence producible.
def test_residual_feature_dependence_on_claim():
    from model_autopsy.backend.causal import adaptive as AD
    out = AD.residual_feature_dependence(predictions_path=CLAIM)
    assert out["ok"] and out["n"] == 1500
    assert out["n_numeric_scanned"] >= 1
    top = {r["column"]: r["abs_corr"] for r in out["ranked"]}
    assert "device_age" in top, top
    assert top["device_age"] > 0.5, top


def test_residual_feature_dependence_registered():
    from model_autopsy.backend import tools_registry as TR
    assert "residual_feature_dependence" in TR.ml_tools()
    assert "residual_feature_dependence" in TR.PARAM_SCHEMA


# 5. Governor experiment cap is enforced inside the live turn.
def test_experiments_left_caps_executions(monkeypatch):
    from model_autopsy.backend import db
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.meta_api import loop as L
    db.init_db()
    s = db.SessionLocal()
    try:
        from model_autopsy.backend import engine
        inv = engine.create_investigation(
            s, "ml", "Cap test", "What fails?",
            {"max_iterations": 3, "predictions_path": TURBINE})
        script = [
            _resp(calls=(
                ("c1", "data_quality_profile",
                 {"predictions_path": TURBINE}),
                ("c2", "calibration_snapshot",
                 {"predictions_path": TURBINE}),
                ("c3", "distribution_shift_profile",
                 {"predictions_path": TURBINE,
                  "split_column": "split"}),), rid="r1"),
            _resp("done", rid="r2"),
            _resp("done", rid="r3"),
        ]
        seen = []

        def fake(**kw):
            seen.append(kw)
            return script[min(len(seen) - 1, len(script) - 1)]
        monkeypatch.setattr(C, "create_response", fake)
        out = L.run_meta_turn(s, inv, max_rounds=1,
                              experiments_left=1)
        assert out["status"] == "ok"
        from model_autopsy.backend.db import Action
        ran = [a for a in s.query(Action).filter(
            Action.investigation_id == inv.id,
            Action.status == "ran").all()]
        assert len(ran) == 1  # cap honored; no overrun possible
    finally:
        s.close()


# 6. Subgroup hypotheses rank subgroup diagnostics first.
def test_subgroup_family_ranking():
    from model_autopsy.backend.causal import selection as SEL
    hyps = [{"text": "Discrimination differs by region: AUC lower in one "
                       "region"}]
    ranked = SEL.rank_candidates(
        ["grouped_auc_comparison", "distribution_shift_profile",
         "artifact_summary"], hyps, set())
    assert ranked[0]["tool"] in ("grouped_auc_comparison",)


# 7. Empty roster still yields a starter brief.
def test_starter_brief_without_hypotheses():
    from model_autopsy.backend.causal import planning as P
    plan = P.plan_next([], set(),
                       {"tool_calls_used": 0, "tool_calls_max": 6})
    assert plan["recommended"], "first turn must not brief 'none'"
    assert plan["explanation"]


# 8. Stopping policy.
def test_stopping_policy():
    from model_autopsy.backend.causal import planning as P
    H = lambda i, st, ev=None: {"id": i, "text": "t", "status": st,
                                "evidence_refs": ev or []}
    stop, why = P.stopping("investigating", [], 2, 6, 1)
    # M22: an empty roster is "nothing to target", never "resolved" —
    # claiming resolution with zero hypotheses was the M21 mislabel.
    assert stop and "no hypotheses on record" in why
    stop, _ = P.stopping("investigating",
                         [H("a", "investigating")], 6, 6, 1)
    assert stop  # budget exhausted
    stop, _ = P.stopping("investigating",
                         [H("a", "proposed")], 2, 6, 1)
    assert not stop  # open work + budget remain
    stop, why_all = P.stopping("investigating",
                         [H("a", "supported", [{"action_id": "x"}]),
                          H("b", "rejected", [{"action_id": "y"}])], 3, 6, 1)
    assert stop and "resolved" in why_all  # genuinely all resolved


def test_family_denial_flips_drift_support():
    """Live-run finding: 'not a level change' denies drift; a break
    contradicts the hypothesis instead of supporting it."""
    from model_autopsy.backend.causal import attribution as AT
    deny = ("Forecasts miss due to persistent systematic bias present "
            "throughout history, not a new level change.")
    assert AT.classify(deny, "drift", "supports", "break found",
                       {"predictions_path": "x"}, n=730)[
                           "relationship"] == "contradicts"
    affirm = ("Forecasts miss because target underwent a recent "
              "persistent level shift (regime change).")
    assert AT.classify(affirm, "drift", "supports", "break found",
                       {"predictions_path": "x"}, n=730)[
                           "relationship"] == "supports"
    # "artifact" is a claim word, not a denial: quality hypothesis
    # with nulls still gets contradicted by a clean screen.
    qual = ("Apparent miss is a data quality artifact with nulls "
            "and duplicate rows")
    assert AT.classify(qual, "quality", "contradicts", "clean",
                       {"predictions_path": "x"}, n=730)[
                           "relationship"] == "contradicts"
