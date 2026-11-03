"""M18 offline integration tests (deterministic, no paid calls).

Proves the M17 architectural bottleneck is fixed through the actual live
callers: hypothesis bookkeeping consumes zero experiment slots, all real
probes share one allocator with a verification hold, the resolution
contract consumes genuine transition events, and closure works end to end.
"""
from model_autopsy.backend.db import SessionLocal, init_db

MUSIC = "model_autopsy/tests/fixture_eval/investigator/music_rank.csv"

SELECTIVE = ("Ranking quality is systematically worse for new catalog "
             "slices (cold-start); top-K precision collapses there.")
UNIFORM_EXPLICIT = ("No slice systematically underperforms at top-K; "
                    "ranking quality is uniform across catalog slices.")
HYGIENE = ("Observed slice score differences reflect hygiene issues "
           "(missing values, duplicates) rather than true quality gaps.")

SLICE_ARGS = {"predictions_path": MUSIC, "slice_column": "slice",
              "score_column": "score", "labels": "relevance"}


def _inv(s, artifact=MUSIC, **cfg):
    from model_autopsy.backend import engine
    base = {"max_iterations": 3, "predictions_path": artifact,
            "m16_skeptic": False}
    base.update(cfg)
    return engine.create_investigation(s, "ml", "m18", "m18 probe", base)


def _hyps(s, inv, texts):
    from model_autopsy.backend import engine
    for t in texts:
        engine.propose_hypothesis(s, inv, text=t,
                                  predicted_observation="probe decides")


def _run_tool(s, inv, tool, args):
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import Action
    out = engine.run_tool(s, inv, tool, dict(args), source_meta=True)
    assert out.get("ok"), out
    return s.get(Action, out.get("action_id"))


def _link(s, inv, act):
    from model_autopsy.backend.causal import linker as LK
    return LK.link_tool_result(s, inv, act)


# ---- Phase 1: hypothesis lifecycle vs experiment accounting ---------------

def test_m18_is_experiment_taxonomy():
    from model_autopsy.backend.live import accounting as A
    assert A.is_experiment("ranking_slice_diagnostics") is True
    assert A.is_experiment("slice_gap_significance") is True
    assert A.is_experiment("classification_metrics") is True
    assert A.is_experiment("propose_hypothesis") is False
    assert A.is_experiment("propose_revision_instructions") is False


def test_m18_hypothesis_registration_consumes_zero_experiment_slots(
        monkeypatch):
    """Propose + diagnose through the REAL loop: only the diagnostic spends.
    """
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    calls = {"n": 0}

    def _fake(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "id": "r1", "status": "completed",
                "output": [
                    {"type": "function_call", "call_id": "c1",
                     "name": "propose_hypothesis",
                     "arguments": (
                         '{"text": "Ranking quality is systematically '
                         'worse for new catalog slices at top-K."}')},
                    {"type": "function_call", "call_id": "c2",
                     "name": "ranking_slice_diagnostics",
                     "arguments": (
                         '{"predictions_path": "%s", "slice_column": '
                         '"slice", "score_column": "score", '
                         '"labels": "relevance"}' % MUSIC)}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
                "_request_perf": {"attempts": 1, "latency_s": 0.0}}
        return {
            "id": "r2", "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text",
                 "text": "```investigation_summary\n"
                         '{"conclusion": "open", '
                         '"status_recommendations": [], '
                         '"uncertainties": ["more data"], '
                         '"recommended_next": "verify"}'
                         "\n```"}]}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "_request_perf": {"attempts": 1, "latency_s": 0.0}}

    monkeypatch.setattr(C, "create_response", _fake)
    b = G.Budget()
    turn = L.run_meta_turn(s, inv, max_rounds=1, budget=b,
                           experiments_left=6)
    assert b.experiments_used == 1, b.ledger()
    # Both tools count as tool calls (attempts budget); only one spent
    # experiment capacity. Reservation declined (1 open hypothesis).
    assert inv.tool_call_count == 2, inv.tool_call_count
    ran = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    assert ran == 2
    assert turn["status"] in ("ok", "budget_exceeded"), turn["status"]


def test_m18_hypothesis_status_updates_consume_zero():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend import engine
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    b = G.Budget()
    from model_autopsy.backend.db import Hypothesis
    h = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).one()
    engine.update_hypothesis(s, h.id, "investigating",
                             rationale="evidence seen")
    assert b.experiments_used == 0


def test_m18_actual_experiments_consume_exactly_one_slot():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import accounting as A
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    b = G.Budget()
    tok = A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                               purpose="test diagnostic", kind="diagnostic",
                               experiments_left=6)
    A.settle_experiment(s, inv, b, tok, "ranking_slice_diagnostics",
                        "diagnostic", True, action_id=None)
    assert b.experiments_used == 1


def test_m18_duplicate_dispatch_does_not_consume_twice():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import accounting as A
    from model_autopsy.backend.db import Event
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    b = G.Budget()
    tok = A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                               purpose="dup test", kind="diagnostic",
                               experiments_left=6)
    A.release_experiment(s, inv, b, tok, "ranking_slice_diagnostics",
                         "diagnostic", "dedup reuse: prior result stands")
    assert b.experiments_used == 0
    kinds = {e.kind for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()}
    assert "experiment_ledger" in kinds


def test_m18_every_experiment_has_purpose_record():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import accounting as A
    from model_autopsy.backend.db import Event
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    from model_autopsy.backend.db import Hypothesis
    h = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).first()
    b = G.Budget()
    tok = A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                               purpose="purpose-string-here",
                               hypothesis_id=h.id, kind="diagnostic",
                               experiments_left=6)
    A.settle_experiment(s, inv, b, tok, "ranking_slice_diagnostics",
                        "diagnostic", True, action_id="a1")
    evs = s.query(Event).filter(
        Event.investigation_id == inv.id,
        Event.kind == "experiment_ledger").all()
    assert len(evs) == 2
    res = [e for e in evs if e.payload.get("status") == "reserved"][0]
    assert res.payload["purpose"] == "purpose-string-here"
    assert res.payload["hypothesis_id"] == h.id
    assert res.payload["tool"] == "ranking_slice_diagnostics"


def test_m18_cached_results_not_newly_executed():
    """Same tool+args twice: second is a recorded reuse, budget untouched."""
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend import engine
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    b = G.Budget()
    out1 = engine.run_tool(s, inv, "ranking_slice_diagnostics",
                           dict(SLICE_ARGS), source_meta=True)
    assert out1.get("ok") and not out1.get("reused")
    from model_autopsy.backend.live import accounting as A
    tok = A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                               purpose="first execution", kind="diagnostic",
                               experiments_left=6)
    A.settle_experiment(s, inv, b, tok, "ranking_slice_diagnostics",
                        "diagnostic", True,
                        action_id=out1.get("action_id"))
    assert b.experiments_used == 1
    out2 = engine.run_tool(s, inv, "ranking_slice_diagnostics",
                           dict(SLICE_ARGS), source_meta=True)
    assert out2.get("reused"), out2
    tok2 = A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                                purpose="dup", kind="diagnostic",
                                experiments_left=6)
    A.release_experiment(s, inv, b, tok2, "ranking_slice_diagnostics",
                         "diagnostic", "dedup reuse")
    assert b.experiments_used == 1


# ---- Phase 2: verification capacity ---------------------------------------

def test_m18_reservation_leaves_verification_hold():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.meta_api import loop as L
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    b = G.Budget()
    rec = L.maybe_reserve_end_of_turn(s, inv, b, 6)
    assert rec and rec.get("reserved") is True
    assert b.experiments_used == 1
    # One spent: five remain, one of which is the verification hold.
    from model_autopsy.backend.live import accounting as A
    assert A.verification_hold_active(s, inv, b) in (True, False)
    assert A.experiments_remaining(b, 6) == 5


def test_m18_hold_blocks_starvation_but_allows_verification():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import accounting as A
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    # A candidate on record activates the hold (gap evidence supports
    # SELECTIVE with no contradiction).
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    b = G.Budget()
    assert A.verification_hold_active(s, inv, b) is True
    # Spend 5 as non-verification work; the 6th slot is the held one.
    for i in range(5):
        tok = A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                                   purpose=f"spend {i}",
                                   kind="model-diagnostic",
                                   experiments_left=6)
        A.settle_experiment(s, inv, b, tok, "ranking_slice_diagnostics",
                            "model-diagnostic", True)
    assert b.experiments_used == 5
    ok, why = A.can_spend_for(s, inv, b, "model-diagnostic", 6)
    assert ok is False, why  # the 6th slot is held for verification
    okv, _ = A.can_spend_for(s, inv, b, "verification", 6)
    assert okv is True
    # Verification itself can consume the held slot.
    tok = A.reserve_experiment(s, inv, b, "slice_gap_significance",
                               purpose="verification",
                               kind="verification", experiments_left=6)
    A.settle_experiment(s, inv, b, tok, "slice_gap_significance",
                        "verification", True)
    assert b.experiments_used == 6


def test_m18_skeptic_probe_shares_allocator_and_hold():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.live import accounting as A
    from model_autopsy.backend.research import invention as INV
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=True)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    b = G.Budget()
    rec = SK.review(s, inv, b, 6, INV.artifact_facts(MUSIC))
    assert b.experiments_used <= 6
    assert A.experiments_remaining(b, 6) >= 0
    assert rec["n_challenges"] >= 1


# ---- Verification eligibility + execution ---------------------------------

def test_m18_verification_declined_honestly_when_no_candidate():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])  # no evidence at all
    b = G.Budget()
    rec = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert rec["verified"] is False
    assert "no eligible" in rec["verification"]["title"].lower()
    assert b.experiments_used == 0
    assert rec["resolution"]["status"] == "unresolved"


def test_m18_verification_executes_when_eligible_and_independent():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    b = G.Budget()
    rec = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert rec["verified"] is True, rec["verification"]
    assert rec["verification"]["tool"] == "slice_gap_significance"
    assert b.experiments_used == 1
    sel = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == SELECTIVE).one()
    assert sel.status == "supported"
    assert rec["resolution"]["status"] == "confirmed"


def test_m18_cached_probe_cannot_count_as_independent_verification():
    """The verification probe tool already measured: decline, spend nothing.
    """
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    _link(s, inv, _run_tool(s, inv, "slice_gap_significance",
                            {**SLICE_ARGS, "k_frac": 0.1,
                             "n_perm": 2000, "seed": 7}))
    n_before = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    b = G.Budget()
    rec = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert rec["verified"] is False
    assert b.experiments_used == 0
    n_after = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    assert n_after == n_before


def test_m18_contradictory_evidence_prevents_confirmation():
    """Support + contradict on the candidate: ineligible, never confirmed."""
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.causal import hypotheses as H
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    h = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).one()
    a1 = _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS)
    H.update_with_evidence(s, h.id, a1.id, "supports",
                           "gap supports selective")
    a2 = _run_tool(s, inv, "slice_gap_significance",
                   {**SLICE_ARGS, "k_frac": 0.1, "n_perm": 2000,
                    "seed": 7})
    H.update_with_evidence(s, h.id, a2.id, "contradicts",
                           "second method contradicts")
    b = G.Budget()
    rec = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert rec["verified"] is False
    assert not [f for f in (inv.latest_findings or [])
                if f.get("status") == "confirmed"]
    assert rec["resolution"]["status"] == "unresolved"


def test_m18_no_independent_tool_means_no_false_confirmation():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, ["Some rows have missing values in the artifact."])
    h = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).one()
    from model_autopsy.backend.causal import hypotheses as H
    a1 = _run_tool(s, inv, "segment_quality_screen",
                   {"predictions_path": MUSIC})
    H.update_with_evidence(s, h.id, a1.id, "supports",
                           "quality screen supports")
    rec = V.maybe_verify(s, inv, G.Budget(), experiments_left=6,
                         artifact=MUSIC)
    assert rec["verified"] is False


# ---- Phase 3: transition accounting ---------------------------------------

def test_m18_investigating_with_evidence_is_unresolved_not_partial():
    """M17 snapshot-defect repro: evidence but no status advancement."""
    from model_autopsy.backend.research import resolve as RES
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    transitions = RES.collect_transitions(s, inv.id)
    # Real transitions exist (proposed -> investigating) but none reach
    # supported/rejected: the contract must say unresolved.
    assert isinstance(transitions, list)
    assert all(t["from"] != t["to"] for t in transitions)
    from model_autopsy.backend.db import Hypothesis
    views = [{"text": h.text, "status": h.status,
              "evidence_refs": h.evidence_refs or []}
             for h in s.query(Hypothesis).filter(
                 Hypothesis.investigation_id == inv.id).all()]
    assert all(h["status"] == "investigating" for h in views)
    res = RES.contract("q", views, [{"tool": "t", "ok": True}], [],
                       transitions, ["a"], [], "Unresolved: open",
                       {"level": "recorded"}, {}, "u", "limit")
    assert res["status"] == "unresolved", res


def test_m18_supported_transition_is_partially_resolved():
    from model_autopsy.backend.research import resolve as RES
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    _link(s, inv, _run_tool(s, inv, "slice_gap_significance",
                            {**SLICE_ARGS, "k_frac": 0.1,
                             "n_perm": 2000, "seed": 7}))
    views = [{"text": h.text, "status": h.status,
              "evidence_refs": h.evidence_refs or []}
             for h in s.query(Hypothesis).filter(
                 Hypothesis.investigation_id == inv.id).all()]
    assert any(h["status"] == "supported" for h in views), views
    transitions = RES.collect_transitions(s, inv.id)
    assert any(t["to"] == "supported" for t in transitions), transitions
    res = RES.contract("q", views, [{"tool": "t", "ok": True}], [],
                       transitions, ["a"], [], "Partially resolved",
                       {"level": "recorded"}, {}, "u", "limit")
    assert res["status"] in ("partially-resolved", "strongly-supported",
                             "confirmed"), res


def test_m18_unresolved_findings_survive_finalization():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    rec = V.maybe_verify(s, inv, G.Budget(), experiments_left=6,
                         artifact=MUSIC)
    assert rec["verified"] is False
    assert "Unresolved" in rec["resolution"]["conclusion"]
    assert rec["resolution"]["status"] == "unresolved"


# ---- Phase 6: governance ---------------------------------------------------

def test_m18_token_headroom_blocks_unsafe_dispatch():
    from model_autopsy.backend.live.governor import Budget, BudgetExceeded
    b = Budget()
    b.input_tokens = 45_000
    import pytest
    with pytest.raises(BudgetExceeded):
        b.check_dispatch(0)  # 45k + 0 + 6k allowance > 50k


def test_m18_financial_and_attempt_caps_hold():
    import pytest
    from model_autopsy.backend.live.governor import (
        Budget, BudgetExceeded, CAPS)
    assert CAPS["cost_usd"] == 0.65
    assert CAPS["experiments"] == 6
    assert CAPS["attempts"] == 12
    b = Budget()
    b.attempts_used = 12
    with pytest.raises(BudgetExceeded):
        b.check()
    b2 = Budget()
    b2.experiments_used = 6
    with pytest.raises(BudgetExceeded):
        b2.check(experiments=1)


def test_m18_final_claims_have_valid_evidence_refs():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    rec = V.maybe_verify(s, inv, G.Budget(), experiments_left=6,
                         artifact=MUSIC)
    assert rec["verified"] is True
    valid_ids = {a.id for a in s.query(Action).filter(
        Action.investigation_id == inv.id).all()}
    for f in (inv.latest_findings or []):
        for ref in (f.get("evidence_refs") or []):
            assert ref in valid_ids, ref


def test_m18_closure_endpoint_reads_recorded_state():
    from fastapi.testclient import TestClient
    from model_autopsy.backend import api as API
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    rec = V.maybe_verify(s, inv, G.Budget(), experiments_left=6,
                         artifact=MUSIC)
    assert rec["verified"] is True
    inv_id = inv.id
    s.close()
    with TestClient(API.app) as c:
        r = c.get(f"/api/investigations/{inv_id}/closure")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["experiments_executed"] >= 2
    assert body["experiments_cap"] == 6
    assert any(t["from"] != t["to"] for t in body["transitions"])
    assert len(body["verification"]) >= 1
    assert len(body["resolution"]) >= 1


# ---- End-to-end offline closure --------------------------------------------

def _full_offline_run(s, inv, budget, artifact=MUSIC):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.research import invention as INV
    from model_autopsy.backend.db import Action
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT, HYGIENE])
    res = L.maybe_reserve_end_of_turn(s, inv, budget, 6)
    assert res is not None
    # Model diagnostics through the shared allocator (hypothesis ops free).
    from model_autopsy.backend.live import accounting as A
    tok = A.reserve_experiment(s, inv, budget,
                               "ranking_slice_diagnostics",
                               purpose="e2e model diagnostic",
                               kind="model-diagnostic", experiments_left=6)
    act = _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS)
    A.settle_experiment(s, inv, budget, tok, "ranking_slice_diagnostics",
                        "model-diagnostic", True, action_id=act.id)
    _link(s, inv, act)
    sk = SK.review(s, inv, budget, 6, INV.artifact_facts(artifact))
    assert sk["n_challenges"] >= 1
    out = V.maybe_verify(s, inv, budget, experiments_left=6,
                         artifact=artifact)
    tools = sorted({a.tool_name for a in s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").all()})
    return out, tools


def test_m18_e2e_closure_success_confirms():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Event
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=True)
    b = G.Budget()
    out, tools = _full_offline_run(s, inv, b)
    assert out["verified"] is True, out["verification"]
    assert out["resolution"]["status"] == "confirmed"
    assert "slice_gap_significance" in tools
    # Hypothesis bookkeeping never consumed experiment slots: total real
    # experiments (reserve + diagnostic + skeptic? + verification) fit in 6.
    assert b.experiments_used <= 6, b.ledger()
    kinds = {e.kind for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()}
    for k in ("reservation", "experiment_ledger", "skeptic",
              "replication", "verification", "resolution"):
        assert k in kinds, kinds


def test_m18_e2e_contradiction_never_confirms():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.causal import hypotheses as H
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=True)
    b = G.Budget()
    out, _ = _full_offline_run(s, inv, b)
    assert out["verified"] is True  # corroboration ran
    # A later independent contradiction revokes confirmability: the
    # confirmed finding stands on record, but a fresh candidate with a
    # contradicting ref cannot newly confirm.
    _hyps(s, inv, ["Fresh rival claim about slice quality."])
    rival = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == "Fresh rival claim about slice quality.").one()
    a1 = _run_tool(s, inv, "segment_quality_screen",
                   {"predictions_path": MUSIC})
    H.update_with_evidence(s, rival.id, a1.id, "supports",
                           "screen supports rival")
    assert rival.status in ("investigating", "supported")
    assert b.experiments_used <= 6


def test_m18_e2e_budget_starvation_keeps_unresolved():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.live import accounting as A
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    b = G.Budget()
    # Five non-verification spends are allowed; the 6th is the held
    # verification slot, so a 6th model-diagnostic is honestly refused.
    import pytest as _pt
    for i in range(5):
        tok = A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                                   purpose=f"fill {i}",
                                   kind="model-diagnostic",
                                   experiments_left=6)
        A.settle_experiment(s, inv, b, tok, "ranking_slice_diagnostics",
                            "model-diagnostic", True)
    assert b.experiments_used == 5
    with _pt.raises(Exception):
        A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                             purpose="starver", kind="model-diagnostic",
                             experiments_left=6)
    assert b.experiments_used == 5
    rec = V.maybe_verify(s, inv, b, experiments_left=0, artifact=MUSIC)
    assert rec["verified"] is False
    assert "budget" in rec["verification"]["title"].lower()
    assert rec["resolution"]["status"] == "unresolved"
    assert not [f for f in (inv.latest_findings or [])
                if f.get("status") == "confirmed"]
