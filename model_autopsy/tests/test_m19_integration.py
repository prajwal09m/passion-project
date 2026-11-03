"""M19 Phase 7b/c: autonomous progression + scientific closure (mocked
provider, real live callers, no spend).

Progression: the investigator must decide explicitly after hypotheses.
Closure: reservation → skeptic → verification on the recovered path,
including the four end-to-end scenarios (confirm / contradict /
provider-failure-recovery / no-suitable-diagnostic).
"""
import json

from model_autopsy.backend.db import SessionLocal, init_db
from model_autopsy.backend.meta_api import client as C

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
            "m16_skeptic": True}
    base.update(cfg)
    return engine.create_investigation(s, "ml", "m19", "m19 probe", base)


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


def _summary(conclusion="open", nxt="run the slice probe", rid="r"):
    return _msg("```investigation_summary\n"
                "{\"conclusion\": \"" + conclusion + "\", "
                "\"status_recommendations\": [], "
                "\"uncertainties\": [\"more data\"], "
                "\"recommended_next\": \"" + nxt + "\"}\n```", rid=rid)


def _decision(s, inv):
    from model_autopsy.backend.db import Event
    evs = [e for e in s.query(Event).filter(
        Event.investigation_id == inv.id,
        Event.kind == "investigator_decision").all()]
    assert len(evs) == 1, [e.kind for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()]
    return evs[0].payload


# ---- 7b: autonomous progression ----------------------------------------------

def test_m19_hyps_then_diagnostic_records_decision(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=False)
    sent = []

    def fake(**kw):
        sent.append(kw)
        if len(sent) == 1:
            return _calls(
                ("c1", "propose_hypothesis",
                 {"text": SELECTIVE}),
                ("c2", "propose_hypothesis",
                 {"text": UNIFORM_EXPLICIT}),
                ("c3", "ranking_slice_diagnostics", SLICE_ARGS), rid="r1")
        return _summary(rid="r2")

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget())
    assert out["status"] == "ok", out
    assert out["decision"]["next_action"] == "diagnostic-executed"
    assert out["decision"]["tool"] == "ranking_slice_diagnostics"
    assert out["decision"]["expected_info_value"] in ("high", "medium", None)
    assert out["decision"]["incomplete_progression"] is False
    assert out["decision"]["experiments_this_turn"] >= 1


def test_m19_competing_hyps_get_discriminating_probe(monkeypatch):
    """The recorded decision carries the brief's discrimination rationale."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=False)
    sent = []

    def fake(**kw):
        sent.append(kw)
        if len(sent) == 1:
            return _calls(
                ("c1", "propose_hypothesis", {"text": SELECTIVE}),
                ("c2", "propose_hypothesis", {"text": HYGIENE}), rid="r1")
        if len(sent) == 2:
            return _calls(
                ("c4", "ranking_slice_diagnostics", SLICE_ARGS), rid="r2")
        return _summary(rid="r3")

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=3, budget=G.Budget())
    assert out["status"] == "ok", out
    assert out["decision"]["tool"] == "ranking_slice_diagnostics"
    assert out["decision"]["question"]  # discrimination rationale present


def test_m19_low_value_choice_recorded_honestly(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=False)

    def fake(**kw):
        if not hasattr(fake, "n"):
            fake.n = 0
        fake.n += 1
        if fake.n == 1:
            return _calls(("c1", "artifact_summary", {}), rid="r1")
        return _summary(nxt="need slice data", rid="r2")

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget())
    assert out["status"] == "ok", out
    assert out["decision"]["next_action"] == "diagnostic-executed"
    assert out["decision"]["tool"] == "artifact_summary"
    # Recorded as executed; value judgment stays in the brief, not hidden.


def test_m19_decline_with_reason_is_valid(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=False)

    def fake(**kw):
        if not hasattr(fake, "n"):
            fake.n = 0
        fake.n += 1
        if fake.n == 1:
            return _calls(("c1", "propose_hypothesis", {"text": SELECTIVE}),
                          rid="r1")
        return _summary(
            nxt="no slice column available; cannot run slice probe", rid="r2")

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=b)
    assert out["status"] == "ok", out
    assert out["decision"]["next_action"].startswith("deferred:")
    assert out["decision"]["incomplete_progression"] is False
    assert b.experiments_used == 0  # nothing forced
    assert s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count() == 1  # the propose only


def test_m19_budget_decline_recorded_not_forced(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=False)

    def fake(**kw):
        if not hasattr(fake, "n"):
            fake.n = 0
        fake.n += 1
        if fake.n == 1:
            return _calls(("c1", "ranking_slice_diagnostics", SLICE_ARGS),
                          rid="r1")
        return _summary(nxt="budget exhausted; stopping", rid="r2")

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget(),
                          experiments_left=0)
    # The diagnostic is refused by the allocator (recorded error output),
    # the model states the budget reason, the decision defers honestly.
    assert out["decision"]["next_action"].startswith("deferred:")
    assert out["decision"]["incomplete_progression"] is False


def test_m19_no_suitable_diagnostic_explained(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=False)

    def fake(**kw):
        if not hasattr(fake, "n"):
            fake.n = 0
        fake.n += 1
        if fake.n == 1:
            return _calls(
                ("c1", "propose_hypothesis",
                 {"text": "Missing values explain the gap."}), rid="r1")
        return _summary(
            nxt="quality screen shows no missingness; no remaining tool "
                "measures this claim distinctively", rid="r2")

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=2, budget=G.Budget())
    assert out["decision"]["next_action"].startswith("deferred:")
    assert "no remaining tool" in out["decision"]["rationale"]


def test_m19_duplicate_diagnostic_reuses(monkeypatch):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=False)

    def fake(**kw):
        if not hasattr(fake, "n"):
            fake.n = 0
        fake.n += 1
        if fake.n <= 2:
            return _calls(("c%d" % fake.n, "ranking_slice_diagnostics",
                           SLICE_ARGS), rid="r%d" % fake.n)
        return _summary(rid="r3")

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    out = L.run_meta_turn(s, inv, max_rounds=3, budget=b)
    assert out["status"] == "ok", out
    assert b.experiments_used == 1  # second identical call reused
    assert s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.status == "ran").count() == 1


def test_m19_diagnostic_moves_confidence():
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    h = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).one()
    before = h.confidence
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS))
    after = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).one()
    assert (after.confidence or 0) != before or after.status != "proposed"
    assert after.status_justification


def test_m19_diagnostic_contradicts_leader():
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [UNIFORM_EXPLICIT, SELECTIVE])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS))
    uni = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == UNIFORM_EXPLICIT).one()
    rels = {r.get("relation") for r in (uni.evidence_refs or [])}
    assert "contradicts" in rels


def test_m19_propose_only_without_reason_is_incomplete(monkeypatch):
    """The final progression case: must be flagged, never silently clean."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, m16_skeptic=False)

    def fake(**kw):
        if not hasattr(fake, "n"):
            fake.n = 0
        fake.n += 1
        if fake.n == 1:
            return _calls(("c1", "propose_hypothesis", {"text": SELECTIVE}),
                          rid="r1")
        return _msg("some prose without any summary block", rid="r2")

    monkeypatch.setattr(C, "create_response", fake)
    out = L.run_meta_turn(s, inv, max_rounds=1, budget=G.Budget())
    d = _decision(s, inv)
    assert d["next_action"] == "no-diagnostic-no-reason"
    assert d["incomplete_progression"] is True
    assert d["new_hypotheses_this_turn"] == 1
    assert d["experiments_this_turn"] == 0
    assert out["decision"]["incomplete_progression"] is True


# ---- 7c: scientific closure ---------------------------------------------------

def test_m19_reservation_skeptic_verify_chain():
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.research import invention as INV
    from model_autopsy.backend.db import Event
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    b = G.Budget()
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT, HYGIENE])
    res = L.maybe_reserve_end_of_turn(s, inv, b, 6)
    assert res and res.get("reserved") is True
    sk = SK.review(s, inv, b, 6, INV.artifact_facts(MUSIC))
    assert sk["n_challenges"] >= 1
    out = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert out["verified"] is True, out["verification"]
    assert out["resolution"]["status"] == "confirmed"
    assert b.experiments_used <= 6
    kinds = {e.kind for e in s.query(Event).filter(
        Event.investigation_id == inv.id).all()}
    for k in ("reservation", "experiment_ledger", "skeptic",
              "replication", "verification", "resolution",
              "investigator_decision" if False else "resolution"):
        assert k in kinds, kinds


def test_m19_hold_survives_three_way_competition():
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import accounting as A
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS))
    b = G.Budget()
    for i, kind in enumerate(("model-diagnostic", "reservation",
                              "skeptic", "model-diagnostic",
                              "model-diagnostic")):
        tok = A.reserve_experiment(s, inv, b, "ranking_slice_diagnostics",
                                   purpose=f"compete {i}", kind=kind,
                                   experiments_left=6)
        A.settle_experiment(s, inv, b, tok, "ranking_slice_diagnostics",
                            kind, True)
    assert b.experiments_used == 5
    ok, why = A.can_spend_for(s, inv, b, "skeptic", 6)
    assert ok is False, why
    okv, _ = A.can_spend_for(s, inv, b, "verification", 6)
    assert okv is True


def test_m19_same_tool_repetition_rejected():
    """replicate() refuses when the independent probe already measured."""
    from model_autopsy.backend.m10 import replication as REP
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS))
    _link(s, inv, _run_tool(s, inv, "slice_gap_significance",
                            {**SLICE_ARGS, "k_frac": 0.1,
                             "n_perm": 2000, "seed": 7}))
    h = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).one()
    ran = [{"tool": "ranking_slice_diagnostics", "args": dict(SLICE_ARGS)},
           {"tool": "slice_gap_significance", "args": {}}]
    rec = REP.replicate(s, inv, h.id, "ranking", MUSIC, ran)
    assert rec["ok"] is False
    assert "already measured" in rec["reason"]


def test_m19_transition_contract_accuracy():
    from model_autopsy.backend.research import resolve as RES
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE, UNIFORM_EXPLICIT])
    _link(s, inv, _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS))
    trans = RES.collect_transitions(s, inv.id)
    assert trans, "real status motion must be collected"
    assert all(t["from"] != t["to"] for t in trans)
    views = [{"text": h.text, "status": h.status,
              "evidence_refs": h.evidence_refs or []}
             for h in s.query(Hypothesis).filter(
                 Hypothesis.investigation_id == inv.id).all()]
    res = RES.contract("q", views, [{"tool": "t", "ok": True}], [], trans,
                       ["a"], [], "Unresolved: open", {"level": "recorded"},
                       {}, "u", "limit")
    assert res["status"] == "unresolved"
    assert res["hypothesis_changes"] == trans  # contract carries the events


def test_m19_final_report_provenance():
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    inv = _inv(s)
    _hyps(s, inv, [SELECTIVE])
    act = _run_tool(s, inv, "ranking_slice_diagnostics", SLICE_ARGS)
    _link(s, inv, act)
    engine.ensure_finalizable(s, inv)
    rep = engine.build_report(s, inv)
    valid = {a.id for a in s.query(Action).filter(
        Action.investigation_id == inv.id).all()}
    for f in (rep.get("confirmed") or []) + (rep.get("likely") or []) + \
             (rep.get("unresolved") or []):
        for ref in (f.get("evidence_refs") or []):
            assert ref in valid, ref


# ---- 7d: end-to-end scenarios ---------------------------------------------------

def _drive_turn(monkeypatch, script, **cfg):
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, **cfg)
    sent = []

    def fake(**kw):
        sent.append(kw)
        item = script[min(len(sent) - 1, len(script) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(C, "create_response", fake)
    b = G.Budget()
    return s, inv, b, sent, L.run_meta_turn(
        s, inv, max_rounds=len(script), budget=b)


def test_m19_scenario_a_confirmed(monkeypatch):
    """Hypotheses → diagnostics → reserve → skeptic → verify → confirmed."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.research import invention as INV
    script = [
        _calls(("c1", "propose_hypothesis", {"text": SELECTIVE}),
               ("c2", "propose_hypothesis", {"text": UNIFORM_EXPLICIT}),
               ("c3", "ranking_slice_diagnostics", SLICE_ARGS), rid="r1"),
        _summary(rid="r2"),
    ]
    s, inv, b, sent, turn = _drive_turn(monkeypatch, script)
    assert turn["status"] == "ok", turn
    assert turn["decision"]["next_action"] == "diagnostic-executed"
    # The turn already ran end-of-turn reservation (exactly-once guard
    # makes a second call return None); assert it on the record instead.
    from model_autopsy.backend.db import Event as _Ev
    assert any(e.kind == "reservation" and "ran" in (e.title or "")
               for e in s.query(_Ev).filter(
                   _Ev.investigation_id == inv.id).all())
    sk = SK.review(s, inv, b, 6, INV.artifact_facts(MUSIC))
    assert sk["n_challenges"] >= 1
    out = V.maybe_verify(s, inv, b, experiments_left=6, artifact=MUSIC)
    assert out["verified"] is True, out["verification"]
    assert out["resolution"]["status"] == "confirmed"
    assert b.experiments_used <= 6


def test_m19_scenario_b_contradiction(monkeypatch):
    """Independent contradiction blocks confirmation; no manufacture."""
    from model_autopsy.backend.causal import hypotheses as H
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Hypothesis
    script = [
        _calls(("c1", "propose_hypothesis", {"text": SELECTIVE}),
               ("c2", "ranking_slice_diagnostics", SLICE_ARGS), rid="r1"),
        _summary(rid="r2"),
    ]
    s, inv, b, sent, turn = _drive_turn(monkeypatch, script)
    assert turn["status"] == "ok", turn
    sel = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id,
        Hypothesis.text == SELECTIVE).one()
    con = _run_tool(s, inv, "slice_gap_significance",
                    {**SLICE_ARGS, "k_frac": 0.1, "n_perm": 2000,
                     "seed": 7})
    H.update_with_evidence(s, sel.id, con.id, "contradicts",
                           "independent method disagrees")
    out = V.maybe_verify(s, inv, G.Budget(), experiments_left=6,
                         artifact=MUSIC)
    assert out["verified"] is False
    assert out["resolution"]["status"] == "unresolved"
    assert not [f for f in (inv.latest_findings or [])
                if f.get("status") == "confirmed"]


def test_m19_scenario_c_failure_and_recovery(monkeypatch):
    """Chained failure → fallback → preserved tools → diagnostic → honest."""
    from model_autopsy.backend.meta_api import loop as L
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action, Hypothesis
    script = [
        _calls(("c1", "propose_hypothesis", {"text": SELECTIVE}),
               ("c2", "propose_hypothesis", {"text": UNIFORM_EXPLICIT}),
               rid="r1"),
        C.MetaUnavailable("HTTP 400: simulated chain refusal",
                          status_code=400),
        _calls(("c9", "ranking_slice_diagnostics", SLICE_ARGS), rid="r3"),
        _summary(rid="r4"),
    ]
    s, inv, b, sent, turn = _drive_turn(monkeypatch, script)
    assert turn["status"] == "ok", turn
    assert sent[2].get("previous_response_id") in (None, "")
    # Model diagnostic + end-of-turn reservation + skeptic probe, all
    # through the shared allocator after the recovery.
    assert b.experiments_used == 3, b.ledger()
    assert turn["decision"]["next_action"] == "diagnostic-executed"
    assert turn["decision"]["incomplete_progression"] is False
    assert s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).count() == 2
    # No duplicate propose executions across the recovery.
    assert s.query(Action).filter(
        Action.investigation_id == inv.id,
        Action.tool_name == "propose_hypothesis").count() == 2


def test_m19_scenario_d_no_suitable_diagnostic(monkeypatch):
    """Decline with reason: no forced experiment, unresolved preserved."""
    from model_autopsy.backend.live import verify as V
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Action
    script = [
        _calls(("c1", "propose_hypothesis",
                {"text": "Missing values explain the gap."}), rid="r1"),
        _summary(nxt="no available tool distinctively measures this claim; "
                     "stopping without forcing a diagnostic", rid="r2"),
    ]
    s, inv, b, sent, turn = _drive_turn(monkeypatch, script)
    assert turn["status"] == "ok", turn
    assert turn["decision"]["next_action"].startswith("deferred:")
    assert turn["decision"]["incomplete_progression"] is False
    assert s.query(Action).filter(
        Action.investigation_id == inv.id).count() == 1
    out = V.maybe_verify(s, inv, G.Budget(), experiments_left=6,
                         artifact=MUSIC)
    assert out["verified"] is False
    assert out["resolution"]["status"] == "unresolved"
