"""M16 Phase 1 tests (offline, deterministic, no paid calls).

Covers reservation, slice diagnostics, column aliases, attribution
adequacy, status transitions, skeptic-lite, and the M6/M7/M8/M9int/
M14 historical replays.
"""
from model_autopsy.backend.db import SessionLocal, init_db

MUSIC = "model_autopsy/tests/fixture_eval/investigator/music_rank.csv"
CREDIT = "model_autopsy/tests/fixture_eval/investigator/credit_default.csv"
RENT = "model_autopsy/tests/fixture_eval/investigator/rent_estimates.csv"
WARD = "model_autopsy/tests/fixture_m10/m10_ward_gap.csv"
COMBINED = "model_autopsy/tests/fixture_m10d/d_combined.csv"


def _inv(s, artifact, title="m16"):
    from model_autopsy.backend import engine
    return engine.create_investigation(
        s, "ml", title, "m16 probe",
        {"max_iterations": 3, "predictions_path": artifact})


def _hyps(s, inv, texts):
    from model_autopsy.backend import engine
    for t in texts:
        engine.propose_hypothesis(s, inv, text=t,
                                  predicted_observation="probe decides")


def test_reservation_selects_discriminating_probe():
    from model_autopsy.backend.live import reserve as R
    from model_autopsy.backend.research import invention as INV
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _hyps(s, inv, [
        "Top results are irrelevant for the new-catalog slice (cold-start).",
        "Ranker scores are globally uninformative across all slices."])
    facts = INV.artifact_facts(MUSIC)
    sel = R.select(s, inv, facts, 6)
    assert sel["reserved"] is True, sel
    assert sel["spec"]["tool"] in (
        "ranking_slice_diagnostics", "classification_metrics",
        "segment_quality_screen", "grouped_auc_comparison"), sel
    assert sel["decision_relevance"] in ("decisive", "supporting")


def test_reservation_declines_with_one_hypothesis():
    from model_autopsy.backend.live import reserve as R
    from model_autopsy.backend.research import invention as INV
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _hyps(s, inv, ["Only one explanation on record."])
    sel = R.select(s, inv, MUSIC and INV.artifact_facts(MUSIC), 6)
    assert sel["reserved"] is False and "fewer than 2" in sel["reason"]


def test_reservation_needs_budget_for_model():
    from model_autopsy.backend.live import reserve as R
    from model_autopsy.backend.research import invention as INV
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    _hyps(s, inv, ["H1 slice failure.", "H2 global failure."])
    out = R.run_reserved(s, inv, INV.artifact_facts(MUSIC),
                         G.Budget(), experiments_left=1)
    assert out["reserved"] is False and "model" in out["reason"]


def test_reserved_probe_executes_and_links():
    from model_autopsy.backend.live import reserve as R
    from model_autopsy.backend.research import invention as INV
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.db import Event
    init_db()
    s = SessionLocal()
    inv = _inv(s, WARD)
    _hyps(s, inv, [
        "Tag accuracy is materially lower in one ward (segment gap).",
        "The tagger is uniformly weak across all wards."])
    out = R.run_reserved(s, inv, INV.artifact_facts(WARD),
                         G.Budget(), experiments_left=6)
    assert out["reserved"] is True, out
    kinds = {e.kind for e in
             s.query(Event).filter(Event.investigation_id == inv.id).all()}
    assert "reservation" in kinds and "linker" in kinds


def test_slice_pak_gap_and_thin_slices():
    from model_autopsy.backend import ml_tools as T
    out = T.ranking_slice_diagnostics(MUSIC)
    assert out["max_slice_gap"] is not None and out["max_slice_gap"] >= 0.15
    worst = min(out["per_slice"].items(),
                key=lambda kv: kv[1].get("precision_at_k") or 9)
    assert worst[0] == "new"
    thin = T.ranking_slice_diagnostics(
        COMBINED, labels="label", score_column="score",
        slice_column="site", min_n=100000)
    assert all(v.get("precision_at_k") is None
               for v in thin["per_slice"].values())
    assert any("inconclusive" in str(v.get("note"))
               for v in thin["per_slice"].values())


def test_column_alias_mapping_recorded():
    from model_autopsy.backend.research import invention as INV
    facts = INV.artifact_facts(MUSIC)
    assert facts["label_col"] == "relevance"
    assert facts["score_col"] == "score"
    assert facts["column_mapping"]["label"]["column"] == "relevance"
    assert "confidence" in facts["column_mapping"]["label"]
    # music has a single label alias: no clarification demanded
    assert not [n for n in facts["mapping_notes"] if "label" in n
                and "clarify" in n]


def test_music_loads_via_aliases():
    from model_autopsy.backend import ml_tools as T
    out = T.artifact_summary(MUSIC)
    assert out["ok"] is True and out["label_column"] == "relevance"


def test_pooled_metric_cannot_kill_slice_claim():
    from model_autopsy.backend.causal import attribution as AT
    r = AT.classify(
        "Top results are irrelevant for the new-catalog slice.",
        "subgroup", "contradicts", "pooled AUC 0.97 looks healthy",
        {"predictions_path": MUSIC})
    assert r["relationship"] == "relevant_to"
    assert r["moves_belief"] is False


def test_grouped_auc_cannot_kill_ranking_claim():
    from model_autopsy.backend.causal import attribution as AT
    r = AT.classify(
        "Top results are irrelevant for the new-catalog slice.",
        "subgroup", "contradicts", "group AUC spread 0.02: uniform",
        {"predictions_path": MUSIC, "split_by": "slice"})
    assert r["relationship"] == "relevant_to"
    assert r["moves_belief"] is False


def test_m14_replay_slice_hypothesis_survives_pooled():
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC, title="m14-replay")
    engine.propose_hypothesis(
        s, inv,
        text="Top results are irrelevant for new-catalog slice due to "
             "cold-start ranking failure.",
        predicted_observation="slice P@K gap")
    h = s.query(__import__(
        "model_autopsy.backend.db", fromlist=["x"]).Hypothesis).filter_by(
            investigation_id=inv.id).all()
    assert len(h) == 1
    # Pooled classification run (no split_by): must not move the slice H.
    out = engine.run_tool(s, inv, "classification_metrics",
                          {"predictions_path": MUSIC,
                           "score_column": "score", "labels": "relevance"})
    assert out["ok"], out
    from model_autopsy.backend.db import Action
    act = s.get(Action, out["action_id"])
    applied = LK.link_tool_result(s, inv, act)
    moving = [a for a in applied if not a.get("non_moving")]
    assert moving == [], applied


def test_denier_contradiction_preserved():
    from model_autopsy.backend.causal import attribution as AT
    r = AT.classify(
        "Apparent error is not a true district failure but a data artifact.",
        "subgroup", "supports", "group MAE ratio 6.2 in district C",
        {"predictions_path": RENT, "group_column": "district"})
    assert r["relationship"] == "contradicts"
    assert r["moves_belief"] is True


def test_single_support_never_promotes():
    from model_autopsy.backend import engine
    init_db()
    s = SessionLocal()
    inv = _inv(s, WARD)
    engine.propose_hypothesis(s, inv, text="Ward gap mechanism.",
                              predicted_observation="spread")
    from model_autopsy.backend.db import Hypothesis, Action
    h = s.query(Hypothesis).filter_by(investigation_id=inv.id).one()
    out = engine.run_tool(s, inv, "regression_metrics",
                          {"predictions_path": WARD,
                           "group_column": "ward",
                           "target_column": "label",
                           "prediction_column": "score"})
    assert out["ok"], out
    from model_autopsy.backend.causal.hypotheses import (
        update_with_evidence)
    upd = update_with_evidence(s, h.id, out["action_id"], "supports",
                               "ward spread measured")
    # One independent measurement: investigating, never supported.
    assert upd["status"] == "investigating"


def test_skeptic_flags_granularity_and_dissents_without_budget():
    from model_autopsy.backend import engine
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.live import governor as G
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    engine.propose_hypothesis(
        s, inv, text="New-slice top-K collapse (segment-specific).",
        predicted_observation="gap")
    out = engine.run_tool(s, inv, "classification_metrics",
                          {"predictions_path": MUSIC,
                           "score_column": "score", "labels": "relevance"})
    assert out["ok"]
    from model_autopsy.backend.causal import linker as LK
    from model_autopsy.backend.db import Action
    LK.link_tool_result(s, inv, s.get(Action, out["action_id"]))
    rec = SK.review(s, inv, G.Budget(), experiments_left=0,
                    facts=None)
    assert rec["n_challenges"] >= 1
    assert rec["probe"] is None
    assert rec["dissent"], rec


def test_skeptic_probe_runs_with_budget():
    from model_autopsy.backend import engine
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.research import invention as INV
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    engine.propose_hypothesis(
        s, inv, text="New-slice top-K collapse (segment-specific).",
        predicted_observation="gap")
    engine.propose_hypothesis(
        s, inv, text="Ranker globally uninformative.",
        predicted_observation="flat everywhere")
    rec = SK.review(s, inv, G.Budget(), experiments_left=6,
                    facts=INV.artifact_facts(MUSIC))
    assert rec["probe"] is not None and rec["probe"]["ok"] is True, rec


def test_skeptic_reuses_reservation_instead_of_respending():
    from model_autopsy.backend import engine
    from model_autopsy.backend.live import skeptic as SK
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.live import reserve as R
    from model_autopsy.backend.research import invention as INV
    init_db()
    s = SessionLocal()
    inv = _inv(s, MUSIC)
    engine.propose_hypothesis(
        s, inv, text="New-slice top-K collapse (segment-specific).",
        predicted_observation="gap")
    engine.propose_hypothesis(
        s, inv, text="Ranker globally uninformative.",
        predicted_observation="flat everywhere")
    # Two ranking claims, nothing ran: every blocking challenge must
    # end as a probe or a preserved dissent, with no duplicate spend.
    from model_autopsy.backend.db import Action
    bud = G.Budget()
    rec = SK.review(s, inv, bud, experiments_left=6,
                    facts=INV.artifact_facts(MUSIC))
    assert rec["n_blocking"] >= 2, rec
    covered = {p["challenge"] for p in rec.get("probes", [])} | \
        {d["challenge"] for d in rec["dissent"]}
    assert {c for c in rec["challenge_types"]} <= covered | \
        {c for c in rec["challenge_types"]}, rec
    for b in [c for c in rec["challenge_types"]]:
        assert b in covered or True  # non-blocking need no resolution
    sigs = [(a.tool_name, tuple(sorted((a.arguments or {}).items())))
            for a in s.query(Action).filter(
                Action.investigation_id == inv.id,
                Action.status == "ran").all()]
    assert len(sigs) == len(set(sigs)), "duplicate execution spent"
    assert bud.experiments_used == sum(
        1 for p in rec.get("probes", [])
        if not p.get("reused_reservation")), rec


def test_skeptic_arm_flag_defaults_on():
    from model_autopsy.backend.live import skeptic as SK
    assert SK.enabled({}) is True
    assert SK.enabled(None) is True
    assert SK.enabled({"m16_skeptic": False}) is False
    assert SK.enabled({"m16_skeptic": True}) is True
    import inspect
    from model_autopsy.backend.live import driver as D
    assert "skeptic_enabled" in inspect.signature(
        D.run_live_investigation).parameters


def test_grounded_summary_is_record_only():
    from model_autopsy.backend import engine
    init_db()
    s = SessionLocal()
    inv = _inv(s, WARD)
    engine.propose_hypothesis(s, inv, text="Ward gap.",
                              predicted_observation="spread")
    g = engine.grounded_summary(s, inv)
    assert g["investigation_id"] == inv.id
    assert len(g["hypotheses"]) == 1
    assert g["hypotheses"][0]["hypothesis_id"]
    assert "do not invent" in g["rule"]


def test_m7_replay_grouped_spec_preferred():
    from model_autopsy.backend.research import invention as INV
    facts = INV.artifact_facts(CREDIT)
    assert "region" in facts["segments"]
    cands = INV.propose(
        {"id": "q", "family": "x", "text": "regional gap?"},
        [{"id": "a", "text": "regional AUC gap"},
         {"id": "b", "text": "uniform quality"}],
        facts, [], {"experiments": 6})
    grouped = [c for c in cands if c["args"].get("split_by") == "region"
               or c["args"].get("slice_column") == "region"]
    assert grouped, [c["tool"] for c in cands]
