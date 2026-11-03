"""M9 Workstream 2: autonomous research planning."""
import pytest

from model_autopsy.backend.db import SessionLocal, init_db
from model_autopsy.backend.research import agenda as AG

CREDIT_COLS = ["age", "income", "tenure", "region", "delinq", "score",
               "label"]
RENT_COLS = ["area", "rooms", "district", "target", "prediction"]


def _knowledge(cols, objective="Scores look uneven across regions.",
               temporal=None):
    return {
        "observed": {"columns": cols, "readable": True,
                     "evaluation_methodology": "AUC overall + per region",
                     "spec_objective": objective,
                     "temporal_hint": temporal},
        "inferred": {"has_labels": True, "has_scores": True,
                     "possible_investigations": [],
                     "inconsistencies": []},
        "missing": [], "assumptions": ["labels assumed correct"],
        "provenance": {"built_by": "recon.build_understanding"}}


def test_knowledge_view_separates_fact_from_inference():
    from model_autopsy.backend.research import recon as R
    from model_autopsy.backend.projects import (
        ProjectSpec, ModelMetadata, DatasetMetadata)
    spec = ProjectSpec(
        project_id="t", name="t", domain="d", objective="o",
        task_type="classification", target_definition="t",
        evaluation_methodology="AUC",
        model=ModelMetadata(name="m", framework="xgboost",
                            availability="black_box"),
        dataset=DatasetMetadata(
            location="model_autopsy/tests/fixture_eval/"
                     "investigator/credit_default.csv",
            n_rows=1500))
    u = R.build_understanding(spec)
    kv = AG.knowledge_view(u)
    assert "region" in kv["observed"]["columns"]
    assert kv["inferred"]["has_labels"] is True
    assert kv["observed"]["readable"] is True
    # Inferences live under inferred/, never as observed facts.
    assert "has_labels" not in kv["observed"]
    assert kv["provenance"]


def test_questions_name_real_artifact_facts():
    qs = AG.generate(_knowledge(CREDIT_COLS),
                     ["grouped_auc_comparison"],
                     {"experiments": 5})
    fams = {q["family"] for q in qs}
    assert "subgroup-performance" in fams
    sub = next(q for q in qs if q["family"] == "subgroup-performance")
    assert "region" in sub["text"]  # the actual observed segment
    assert "region" in sub["motivated_by"][0]
    assert sub["status"] == "open"


def test_no_temporal_no_temporal_question():
    qs = AG.generate(_knowledge(RENT_COLS), [], {"experiments": 5})
    assert "temporal-stability" not in {q["family"] for q in qs}
    temporal = {"column": "date", "min": "2023", "max": "2024", "n_valid": 1}
    qs2 = AG.generate(_knowledge(RENT_COLS + ["date"], temporal=temporal),
                      [], {"experiments": 5})
    assert "temporal-stability" in {q["family"] for q in qs2}


def test_schema_change_generates_preprocessing_question():
    qs = AG.generate(_knowledge(
        RENT_COLS,
        objective="Rent off in one district after a schema update."),
        [], {"experiments": 5})
    assert "preprocessing-effect" in {q["family"] for q in qs}


def test_prioritization_states_reasons_and_respects_budget():
    qs = AG.generate(_knowledge(CREDIT_COLS), [], {"experiments": 5})
    ranked = AG.prioritize(qs, {"segments": ["region"], "temporal": False,
                                "budget_left": {"experiments": 5},
                                "open_hypotheses": [{}, {}]})
    assert ranked[0]["priority"] == "high"
    assert all(r["priority_reason"] for r in ranked)
    starved = AG.prioritize(qs, {"segments": ["region"],
                                 "budget_left": {"experiments": 1},
                                 "open_hypotheses": [{}]})
    assert all(r["priority"] != "high" or "budget" in r["priority_reason"]
               for r in starved)


def test_agenda_durable_and_revisable():
    init_db()
    s = SessionLocal()
    try:
        from model_autopsy.backend import engine
        inv = engine.create_investigation(s, "ml", "t", "q", {})
        qs = AG.generate(_knowledge(CREDIT_COLS), [], {"experiments": 5})
        AG.save(s, inv, qs, "initial agenda")
        assert len(AG.load(inv)) == len(qs)
        out = AG.revise_on_evidence(
            s, inv, [], {"needs_discrimination": True})
        assert out["changed"] is True
        fams = {q["family"] for q in AG.load(inv)}
        assert "confounder-discrimination" in fams
        out2 = AG.revise_on_evidence(
            s, inv, [], {"needs_discrimination": True})
        assert out2["changed"] is False  # no duplicate confounder question
    finally:
        s.close()


def test_answered_questions_retire():
    init_db()
    s = SessionLocal()
    try:
        from model_autopsy.backend import engine
        inv = engine.create_investigation(s, "ml", "t", "q", {})
        qs = [{"id": "q0", "family": "subgroup-performance",
               "text": "t", "motivated_by": [], "answered_by": [],
               "status": "open", "hypothesis_ids": ["h1"]}]
        AG.save(s, inv, qs, "initial")
        out = AG.revise_on_evidence(
            s, inv, [{"id": "h1", "status": "supported"}],
            {"needs_discrimination": False})
        assert out["changed"] is True
        assert AG.load(inv)[0]["status"] == "answered"
    finally:
        s.close()
