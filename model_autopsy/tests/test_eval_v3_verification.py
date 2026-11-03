"""Eval v3 Stage 5: verification planning/execution/non-run tests.

Offline only: real local tools on the fixture CSV, no providers.
"""
from model_autopsy.backend.db import Event, Hypothesis, SessionLocal, init_db

MUSIC = "model_autopsy/tests/fixture_eval/investigator/music_rank.csv"
SELECTIVE = ("Ranking quality is systematically worse for new catalog "
             "slices (cold-start); top-K precision collapses there.")
SLICE_ARGS = {"predictions_path": MUSIC, "slice_column": "slice",
              "score_column": "score", "labels": "relevance"}


def _inv(s, **cfg):
    from model_autopsy.backend import engine
    base = {"max_iterations": 3, "predictions_path": MUSIC,
            "m16_skeptic": False}
    base.update(cfg)
    return engine.create_investigation(s, "ml", "v3verify", "probe", base)


def _hyps(s, inv, texts):
    from model_autopsy.backend import engine
    for t in texts:
        engine.propose_hypothesis(s, inv, text=t,
                                  predicted_observation="probe decides")


def _run(s, inv, tool, args):
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import Action
    out = engine.run_tool(s, inv, tool, dict(args), source_meta=True)
    assert out.get("ok"), out
    return s.get(Action, out.get("action_id"))


def _link(s, inv, act):
    from model_autopsy.backend.causal import linker as LK
    return LK.link_tool_result(s, inv, act)


def _kinds(s, inv):
    return {e.kind for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()}


def test_plan_records_expectations_without_spending():
    from model_autopsy.backend.live import verification as VF
    init_db(); s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    _link(s, inv, _run(s, inv, "ranking_slice_diagnostics", SLICE_ARGS))
    hyp = s.query(Hypothesis).filter_by(
        investigation_id=inv.id).all()
    hyp = [h for h in hyp if h.text == SELECTIVE][0]
    plan = VF.plan_verification(s, inv, hyp.id)
    assert plan["planned"] is True
    assert plan["tool"] == "slice_gap_significance"
    assert "expected_if_true" in plan and "expected_if_false" in plan
    assert "verification_plan" in _kinds(s, inv)
    # Planning dispatches nothing and spends nothing.
    assert inv.tool_call_count == 1


def test_plan_unknown_hypothesis_is_info_unavailable():
    from model_autopsy.backend.live import verification as VF
    init_db(); s = SessionLocal()
    inv = _inv(s)
    rec = VF.plan_verification(s, inv, "deadbeef" * 4)
    assert rec == {"planned": False, "reason": "info_unavailable"}


def test_non_verification_reason_codes_validated():
    from model_autopsy.backend.live import verification as VF
    init_db(); s = SessionLocal()
    inv = _inv(s)
    for code in VF.REASON_CODES:
        rec = VF.record_non_verification(s, inv, None, code, "d")
        assert rec["reason"] == code and rec["executed"] is False
    rec = VF.record_non_verification(s, inv, None, "bogus", "d")
    assert rec["reason"] == "info_unavailable"
    assert "non_verification" in _kinds(s, inv)


def test_status_rollup_distinguishes_planned_executed_unexecuted():
    from model_autopsy.backend.live import verification as VF
    init_db(); s = SessionLocal()
    inv = _inv(s)
    assert VF.verification_status(s, inv) == {"planned": [], "executed": [],
                                              "unexecuted": []}
    VF.record_non_verification(s, inv, None, "budget_exhausted", "cap")
    st = VF.verification_status(s, inv)
    assert st["unexecuted"][0]["reason"] == "budget_exhausted"
    assert st["executed"] == []


def test_phase_with_no_eligible_hypothesis_explains_itself():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verification as VF
    init_db(); s = SessionLocal()
    inv = _inv(s)
    rec = VF.run_verification_phase(s, inv, G.Budget(), experiments_left=6,
                                    artifact=MUSIC)
    assert rec["verified"] is False
    st = VF.verification_status(s, inv)
    assert st["unexecuted"] and st["unexecuted"][0]["reason"] in (
        "insufficient_data", "no_suitable_tool")


def test_phase_executes_independent_probe_when_available():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verification as VF
    init_db(); s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    _link(s, inv, _run(s, inv, "ranking_slice_diagnostics", SLICE_ARGS))
    rec = VF.run_verification_phase(s, inv, G.Budget(), experiments_left=6,
                                    artifact=MUSIC)
    assert rec["verified"] is True, rec["verification"]
    assert rec["verification"]["tool"] == "slice_gap_significance"
    st = VF.verification_status(s, inv)
    assert st["planned"] and st["planned"][0]["tool"] == \
        "slice_gap_significance"


def test_phase_refuses_already_measured_probe_without_spending():
    from model_autopsy.backend.db import Action
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verification as VF
    init_db(); s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    _link(s, inv, _run(s, inv, "slice_gap_significance",
                       dict(SLICE_ARGS, n_perm=200, seed=7)))
    _link(s, inv, _run(s, inv, "ranking_slice_diagnostics", SLICE_ARGS))
    n_before = s.query(Action).filter_by(investigation_id=inv.id,
                                         status="ran").count()
    rec = VF.run_verification_phase(s, inv, G.Budget(), experiments_left=6,
                                    artifact=MUSIC)
    assert rec["verified"] is False
    n_after = s.query(Action).filter_by(investigation_id=inv.id,
                                        status="ran").count()
    assert n_after == n_before  # independence: no duplicate execution
    st = VF.verification_status(s, inv)
    assert any(u["reason"] == "already_measured" for u in
               st["unexecuted"]), st
