"""M17 integration tests (offline, deterministic, no paid calls).

Phase 1: reservation-after-hypotheses. Later phases append here:
verification caller, actionable skeptic, attribution root fix,
headroom, end-to-end workflow.
"""
from model_autopsy.backend.db import SessionLocal, init_db

MUSIC = "model_autopsy/tests/fixture_eval/investigator/music_rank.csv"


def _inv(s, artifact, title="m17"):
    from model_autopsy.backend import engine
    return engine.create_investigation(
        s, "ml", title, "m17 probe",
        {"max_iterations": 3, "predictions_path": artifact})


def _hyps(s, inv, texts):
    from model_autopsy.backend import engine
    for t in texts:
        engine.propose_hypothesis(s, inv, text=t,
                                  predicted_observation="probe decides")


def test_m17_reservation_declines_before_hypotheses():
    """M16 failure reproduction: at turn start, 0 hypotheses exist, so
    the checkpoint must decline (not reserve blindly, not crash)."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Event
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    rec = L.maybe_reserve_end_of_turn(s, inv, G.Budget(), 6)
    assert rec is not None and rec.get("reserved") is False
    assert "fewer than 2" in rec.get("reason", "")
    evs = s.query(Event).filter(Event.investigation_id == inv.id,
                                Event.kind == "reservation").all()
    assert len(evs) == 1  # decline is recorded, not silent


def test_m17_reservation_fires_after_round1_hypotheses():
    """The fix: hypotheses proposed in round 1 trigger reservation."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action, Event
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _hyps(s, inv, [
        "Top results are irrelevant for the new-catalog slice (cold-start).",
        "Ranker scores are globally uninformative across all slices."])
    b = G.Budget()
    rec = L.maybe_reserve_end_of_turn(s, inv, b, 6)
    assert rec is not None and rec.get("reserved") is True, rec
    assert rec.get("action_id"), rec
    assert b.experiments_used == 1
    acts = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").all()
    assert any(a.tool_name == rec.get("spec_tool") for a in acts)
    evs = s.query(Event).filter(Event.investigation_id == inv.id,
                                Event.kind == "reservation").all()
    assert len(evs) == 1 and (evs[0].title or "").startswith(
        "Reserved probe ran")


SELECTIVE = ("Ranking quality is systematically worse for new catalog "
             "slices (cold-start); top-K precision collapses there.")
UNIFORM_EXPLICIT = ("No slice systematically underperforms at top-K; "
                    "ranking quality is uniform across catalog slices.")


def _run_tool(s, inv, tool, args):
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import Action
    out = engine.run_tool(s, inv, tool, dict(args), source_meta=True)
    assert out.get("ok"), out
    act = s.get(Action, out.get("action_id"))
    assert act is not None
    return act


def _link(s, inv, act):
    from model_autopsy.backend.causal import linker as LK
    return LK.link_tool_result(s, inv, act)


SLICE_ARGS = {"predictions_path": MUSIC, "slice_column": "slice",
              "score_column": "score", "labels": "relevance"}


def _support_selective_once(s, inv):
    """First moving support: the descriptive slice gap."""
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    act = _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS)
    return _link(s, inv, act)


def test_m17_verification_reaches_confirmation():
    """Caller reachable; second probe executes, attaches, confirms."""
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.db import Action, Event, Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _support_selective_once(s, inv)
    b = G.Budget()
    rec = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert rec["verified"] is True, rec["verification"]
    assert rec["verification"]["tool"] == "slice_gap_significance"
    assert b.experiments_used == 1
    acts = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").all()
    tools = sorted({a.tool_name for a in acts})
    assert tools == ["ranking_slice_diagnostics",
                     "slice_gap_significance"], tools
    sel = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == SELECTIVE).one()
    assert rec["verification"]["hypothesis_id"] == sel.id
    assert sel.status == "supported", sel.status
    findings = [f for f in (inv.latest_findings or [])
                if f.get("status") == "confirmed"]
    assert len(findings) == 1, inv.latest_findings
    assert rec["resolution"]["status"] == "confirmed", \
        rec["resolution"]
    kinds = {e.kind for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()}
    assert {"verification", "resolution", "replication"} <= kinds


def test_m17_verification_refuses_duplicate_tool():
    """Independence: an already-ran probe is not re-executed as proof."""
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    # Significance probe already on record (linked): it cannot verify.
    _link(s, inv, _run_tool(s, inv, "slice_gap_significance",
                            dict(SLICE_ARGS, n_perm=200, seed=7)))
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    n_before = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    b = G.Budget()
    rec = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert rec["verified"] is False
    assert "not dispatched" in rec["verification"]["title"].lower() \
        or "already measured" in rec["verification"]["reason"], \
        rec["verification"]
    n_after = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    assert n_after == n_before  # no duplicate execution
    assert b.experiments_used == 0  # hold released, nothing spent
    assert not [f for f in (inv.latest_findings or [])
                if f.get("status") == "confirmed"]


def test_m17_verification_skips_unknown_family():
    """No independent probe exists for the leading family: skip honestly."""
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _hyps(s, inv, ["Some rows have missing values in the artifact."])
    _link(s, inv, _run_tool(s, inv, "segment_quality_screen",
                            {"predictions_path": MUSIC}))
    n_before = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    rec = V.maybe_verify(s, inv, G.Budget(), experiments_left=6,
                          artifact=MUSIC)
    assert rec["verified"] is False
    assert "no independent probe" in rec["verification"]["title"].lower()
    assert s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count() == n_before


def test_m17_contradicted_hypothesis_never_confirms():
    """A finding with contradicting evidence cannot be verified."""
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _hyps(s, inv, [UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    rec = V.maybe_verify(s, inv, G.Budget(), experiments_left=6,
                          artifact=MUSIC)
    assert rec["verified"] is False
    assert not [f for f in (inv.latest_findings or [])
                if f.get("status") == "confirmed"]
    assert rec["resolution"]["status"] != "confirmed"


def test_m17_verification_budget_refused_stays_unresolved():
    """No budget: recorded skip, finding preserved, nothing spent."""
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _support_selective_once(s, inv)
    n_before = s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count()
    broke = G.Budget(caps=dict(G.CAPS, experiments=0))
    rec = V.maybe_verify(s, inv, broke, experiments_left=0, artifact=MUSIC)
    assert rec["verified"] is False
    assert "budget" in (rec["verification"]["title"]
                         + rec["verification"]["reason"]).lower()
    assert s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count() == n_before
    assert not [f for f in (inv.latest_findings or [])
                if f.get("status") == "confirmed"]


def test_m17_attribution_five_cases():
    """Phase 4: the five required wordings through the real pipeline."""
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    texts = ["No slice systematically underperforms.",
             "Any observed differences are sampling noise.",
             "The difference reflects base-rate variation.",
             "New slices perform substantially worse.",
             "There is insufficient evidence to establish a subgroup "
             "effect."]
    _hyps(s, inv, texts)
    act = _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS)
    applied = _link(s, inv, act)
    rel_of = {}
    for a in applied:
        h = s.get(Hypothesis, a["hypothesis_id"])
        rel_of[h.text] = a["direction"]
    assert rel_of[texts[0]] == "contradicts", rel_of
    assert rel_of[texts[1]] == "contradicts", rel_of
    # Base-rate rival: untested by gap evidence -> no link at all (neutral
    # short-circuits before recording), status untouched.
    assert texts[2] not in rel_of, rel_of
    h3 = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == texts[2]).one()
    assert (h3.evidence_refs or []) == [] and h3.status == "proposed"
    assert rel_of[texts[3]] == "supports", rel_of
    assert rel_of[texts[4]] == "uncertain", rel_of
    # No denier-supports anywhere in this run.
    assert "supports" not in (rel_of[texts[0]], rel_of[texts[1]])


def test_m17_attribution_m16_euphemism_regression():
    """M16 4-run failure pattern: euphemized uniformity must contradict."""
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    euph = ("Top-K relevance is uniform across catalog slices; any "
            "slice differences are sampling noise.")
    sel = ("A specific catalog slice (e.g. new items) has degraded top-K "
           "ranking quality due to weaker model scoring for that slice.")
    _hyps(s, inv, [euph, sel])
    act = _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS)
    applied = _link(s, inv, act)
    rel_of = {}
    for a in applied:
        h = s.get(Hypothesis, a["hypothesis_id"])
        rel_of[h.text] = a["direction"]
    assert rel_of[euph] == "contradicts", rel_of
    assert rel_of[sel] == "supports", rel_of
    uni = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == euph).one()
    assert uni.status in ("investigating", "rejected"), uni.status
    assert uni.status != "supported"


def test_m17_skeptic_blocks_and_responds():
    """Phase 3: a blocking challenge gets a probe or preserved dissent."""
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.research import invention as INV
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _support_selective_once(s, inv)
    b = G.Budget()
    rec = SK.review(s, inv, b, 6, INV.artifact_facts(MUSIC))
    assert rec["n_blocking"] >= 1, rec
    responded = rec.get("probe") is not None or bool(rec.get("dissent"))
    assert responded, rec
    # Every blocking challenge answered one way or another: none left open.
    assert rec.get("open", 0) == 0, rec
    assert b.experiments_used <= 1, b.experiments_used
    # Skeptic disagreement is never auto-recorded as evidence against.
    from model_autopsy.backend.db import Hypothesis as _H
    for h in s.query(_H).filter_by(investigation_id=inv.id):
        assert not any(
            r.get("relation") == "contradicts"
            and "skeptic" in str(r.get("tool", "")).lower()
            for r in (h.evidence_refs or []))


def test_m17_skeptic_advisory_stays_non_blocking():
    """Advisory observations never block, probe, or spend."""
    from model_autopsy.backend import engine
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.research import invention as INV
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    engine.propose_hypothesis(s, inv, text=SELECTIVE)
    from model_autopsy.backend.db import Hypothesis
    hid = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).one().id
    engine.update_hypothesis(s, hid, "investigating",
                             rationale="test setup")
    # Slice measured (granularity satisfied) but nothing linked: the
    # confounder observation must stay advisory.
    _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS)
    b = G.Budget()
    rec = SK.review(s, inv, b, 6, INV.artifact_facts(MUSIC))
    assert rec["n_blocking"] == 0, rec
    assert rec.get("probe") is None
    assert b.experiments_used == 0


def test_m17_gate_caps_premature_support():
    """An open blocking challenge holds 'supported' until answered."""
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.causal import hypotheses as H
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _support_selective_once(s, inv)
    sel = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == SELECTIVE).one()
    # Simulate a challenge opened by a prior turn's review.
    state = SK._state(inv)
    state.setdefault("open", []).append(
        {"type": "missing-falsification", "hypothesis_id": sel.id,
         "detail": "test-injected open challenge"})
    SK._save_state(s, inv, state)
    # Second independent support arrives while the challenge is open.
    sig = _run_tool(s, inv, "slice_gap_significance",
                    dict(SLICE_ARGS, n_perm=200, seed=7))
    out = H.update_with_evidence(s, sel.id, sig.id, "supports",
                                 "second independent support")
    assert out["status"] == "investigating", out
    assert "challenge" in out["justification"], out
    # After the investigator answers, corroboration can advance.
    SK.mark_answered(s, inv, sel.id, "test answer")
    out2 = H.update_with_evidence(s, sel.id, sig.id, "supports",
                                  "re-audit after answer")
    assert out2["status"] == "supported", out2


def test_m17_headroom_refuses_breach():
    """Phase 5: projection over cap refuses before dispatch."""
    from model_autopsy.backend.live.governor import (
        Budget, BudgetExceeded)
    b = Budget()
    b.input_tokens = 40_000
    try:
        b.check_dispatch(5_000)
        raise AssertionError("should have refused")
    except BudgetExceeded as exc:
        assert "headroom" in str(exc), exc
    assert b.input_tokens == 40_000  # refusal spends nothing


def test_m17_headroom_allows_normal_dispatch():
    from model_autopsy.backend.live.governor import Budget
    b = Budget()
    b.input_tokens = 20_000
    b.check_dispatch(8_000)  # 20k + 8k + 6k = 34k < 50k: fine


def test_m17_headroom_hard_gate_intact():
    """At/over cap still refuses via the original hard gate."""
    import pytest
    from model_autopsy.backend.live.governor import (
        Budget, BudgetExceeded)
    b = Budget()
    b.input_tokens = 60_000
    with pytest.raises(BudgetExceeded):
        b.check_dispatch(0)
    edge = Budget()
    edge.input_tokens = 49_000
    with pytest.raises(BudgetExceeded):
        edge.check_dispatch(0)  # 49k + 0 + 6k > 50k: headroom refuses


def test_m17_headroom_blocks_provider_dispatch(monkeypatch):
    """The live turn never sends a request past the headroom gate."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.meta_api import client as C
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    sent = []

    def _must_not_send(**kwargs):
        sent.append(kwargs)
        raise AssertionError("provider must not be contacted")

    monkeypatch.setattr(C, "create_response", _must_not_send)
    b = G.Budget()
    b.input_tokens = 45_000  # projection breaches even for small inputs
    turn = L.run_meta_turn(s, inv, max_rounds=1, budget=b)
    assert turn["status"] == "budget_exceeded", turn["status"]
    assert sent == []


def test_m17_end_to_end_scientific_closure():
    """Phase 6: the full chain on one offline investigation.

    hypothesize -> reserve -> diagnose -> attribute -> skeptic ->
    respond -> verify -> resolve, through the actual live callers.
    """
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.research import invention as INV
    from model_autopsy.backend.db import Action, Event, Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    b = G.Budget()
    # Round 1 (simulated model): two competing hypotheses.
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    # Reservation fires after hypotheses exist.
    res = L.maybe_reserve_end_of_turn(s, inv, b, 6)
    assert res and res.get("reserved") is True, res
    # Model diagnostics: the discriminating slice probe.
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics",
                            SLICE_ARGS))
    # Skeptic challenges and the investigator responds on record.
    sk = SK.review(s, inv, b, 6, INV.artifact_facts(MUSIC))
    assert sk["n_challenges"] >= 1, sk
    assert sk.get("open", 0) == 0, sk
    # Verification completes corroboration; resolution contracts it.
    out = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert out["verified"] is True, out["verification"]
    assert out["resolution"]["status"] == "confirmed"
    # No silent steps: every stage left its event.
    kinds = {e.kind for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()}
    for k in ("reservation", "experiment", "skeptic",
              "replication", "verification", "resolution"):
        assert k in kinds, kinds
    # Budget respected throughout (6-experiment cap shared by all).
    assert b.experiments_used <= 6
    tools = sorted({a.tool_name for a in s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").all()})
    assert "slice_gap_significance" in tools, tools
    sel = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == SELECTIVE).one()
    assert sel.status == "supported", sel.status


def test_m17_reservation_exactly_once():
    """Second call (next turn) must not re-reserve or double-spend."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Event
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _hyps(s, inv, [
        "Top results are irrelevant for the new-catalog slice (cold-start).",
        "Ranker scores are globally uninformative across all slices."])
    b = G.Budget()
    first = L.maybe_reserve_end_of_turn(s, inv, b, 6)
    assert first and first.get("reserved") is True
    used_after_first = b.experiments_used
    second = L.maybe_reserve_end_of_turn(s, inv, b, 6)
    assert second is None
    assert b.experiments_used == used_after_first
    evs = s.query(Event).filter(Event.investigation_id == inv.id,
                                Event.kind == "reservation").all()
    assert len(evs) == 1
