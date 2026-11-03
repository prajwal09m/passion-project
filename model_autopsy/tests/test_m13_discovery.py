"""M13 discovery engine + evidence reasoning tests (offline)."""
from model_autopsy.backend.db import SessionLocal, init_db


def _facts(cols, **kw):
    f = {"artifact": "a.csv", "readable": True, "columns": cols,
         "segments": [], "temporal_col": None, "split_col": None,
         "score_col": None, "label_col": None, "feature_cols": []}
    f.update(kw)
    return f


def test_ontology_capability_and_gaps():
    from model_autopsy.backend.research import ontology as O
    assert len(O.DIMENSIONS) >= 15
    f = _facts(["label", "score"],
               score_col="score", label_col="label")
    assert O.capable("calibration", f)["capable"] is True
    assert O.capable("calibration", f)["tools"]
    g = O.capable("temporal_behavior", f)
    assert g["capable"] is False and g["missing"] == ["temporal_col"]
    gaps = O.coverage_gaps(f)
    assert any(x["dimension"] == "model_implementation" for x in gaps)
    assert O.capable("model_implementation", f)["tools"] == []


def test_invention_info_value_on_every_spec():
    from model_autopsy.backend.research import invention as INV
    f = _facts(["label", "score"], score_col="score",
               label_col="label")
    hyps = [{"id": "h1", "text": "t"}, {"id": "h2", "text": "t2"}]
    q = {"id": "q", "family": "metric-adequacy"}
    cands = INV.propose(q, hyps, f, [], {"experiments": 6})
    assert cands
    for c in cands:
        iv = c["info_value"]
        assert set(iv) == {"distinguishes_n", "cost", "power_limits",
                           "mislead_risk", "duplicates_existing",
                           "decision_relevance"}
        assert iv["decision_relevance"] in ("decisive", "supporting",
                                            "exploratory")


def test_pooled_calibration_candidates_invented():
    from model_autopsy.backend.research import invention as INV
    f = _facts(["x", "label", "score"], score_col="score",
               label_col="label")
    cands = INV.propose({"id": "q", "family": "calibration-population"},
                        [{"id": "h", "text": "t"}], f, [],
                        {"experiments": 6})
    tools = [(c["tool"], c["args"].get("bins")) for c in cands]
    assert ("calibration_and_error_analysis", 10) in tools
    assert ("calibration_and_error_analysis", 5) in tools
    assert ("classification_metrics", None) in tools


def test_cross_family_persistence_contradicted_by_break():
    from model_autopsy.backend.causal import attribution as AT
    h = ("Forecast errors are uniform throughout; no change over "
         "time.")
    assert AT.classify(h, "drift", "supports", "break found",
                       {"predictions_path": "x"}, n=500)[
                           "relationship"] == "contradicts"


def test_cross_family_recency_contradicted_by_persistence():
    from model_autopsy.backend.causal import attribution as AT
    h = "A recent level shift in the test period causes the miss."
    assert AT.classify(h, "misspecification", "supports",
                       "errors persistent",
                       {"predictions_path": "x"}, n=500)[
                           "relationship"] == "contradicts"


def test_ambiguous_markers_never_force():
    from model_autopsy.backend.causal import attribution as AT
    h = "A recent persistent uniform change throughout the period."
    r = AT.classify(h, "drift", "supports", "break",
                    {"predictions_path": "x"}, n=500)["relationship"]
    assert r in ("relevant_to", "neutral", "mentions", "uncertain")


def test_false_support_topical_overlap_stays_put():
    from model_autopsy.backend.causal import attribution as AT
    h = "Ward gap is caused by missing labels in district 9."
    # drift evidence vs a quality/subgroup claim: no commitment ->
    # never supports.
    assert AT.classify(h, "drift", "supports", "break",
                       {"predictions_path": "x"}, n=500)[
                           "relationship"] != "supports"


def test_quality_rejection_via_two_distinct_tools():
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    from model_autopsy.backend.db import Action
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm
    from model_autopsy.backend import db as DB
    e = _ce("sqlite:///:memory:")
    DB.Base.metadata.create_all(e)
    s = _sm(bind=e, autoflush=False, expire_on_commit=False)()
    import os
    os.environ["MODEL_AUTOPILOT_TESTING"] = "1"
    art = "model_autopsy/tests/fixture_m10/m10_district_scale.csv"
    inv = engine.create_investigation(
        s, "ml", "q", "b",
        {"max_iterations": 3, "predictions_path": art})
    engine.propose_hypothesis(
        s, inv, "Miss is a data quality artifact with nulls " + "q" * 20)
    for tool, args in (
            ("data_quality_profile", {"predictions_path": art}),
            ("segment_quality_screen",
             {"predictions_path": art, "segment_column": "district"})):
        r = engine.run_tool(s, inv, tool, args, source_meta=True)
        assert r["ok"], r
        a = s.get(Action, r["action_id"])
        LK.link_tool_result(s, inv, a)
    from model_autopsy.backend.db import Hypothesis
    hs = s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    qual = next(h for h in hs if "quality artifact" in h.text)
    moving = [x for x in qual.evidence_refs
              if x.get("relation") in ("supports", "contradicts")]
    tools = {x.get("tool") for x in moving}
    assert tools == {"data_quality_profile", "segment_quality_screen"}
    # district_scale is clean: both probes contradict via DISTINCT
    # tools -> rejected. Quality rejection is now reachable without
    # weakening any threshold.
    assert qual.status == "rejected", \
        (qual.status, qual.status_justification)
