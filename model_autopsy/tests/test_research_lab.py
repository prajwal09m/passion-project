"""Research lab tests (Milestone 3, offline, no provider calls)."""
from __future__ import annotations


def _inv(session, mode="ml", **cfg):
    from model_autopsy.backend import engine
    return engine.create_investigation(
        session, mode, "t", "q",
        {"max_iterations": 3, "predictions_path": None, **cfg})


def test_recon_document_sections_and_honesty():
    from model_autopsy.backend.projects import ProjectSpec
    from model_autopsy.backend.research import recon
    s = ProjectSpec.from_dict({
        "project_id": "t", "name": "T",
        "task_type": "classification", "objective": "",
        "evaluation_methodology": "",
        "dataset": {"location": "nope.csv"}})
    doc = recon.build_understanding(s)
    for key in ("predicting", "receives", "produces", "success",
                "evaluation", "evaluation_assumptions", "missing",
                "possible", "impossible", "inconsistencies"):
        assert key in doc, key
    assert "readable_dataset_artifact" in doc["missing"]
    assert any("white-box" in m or "black-box" in m
               for m in doc["impossible"])


def test_hypothesis_lifecycle_and_evidence_gate(db_session=None):
    from model_autopsy.backend.db import SessionLocal, init_db
    from model_autopsy.backend.research import hypotheses as H
    init_db()
    session = SessionLocal()
    try:
        inv = _inv(session)
        card = H.propose(session, inv, {
            "title": "Leak?", "mechanism": "proxy mirrors label",
            "support_criteria": "s", "refute_criteria": "r",
            "priority": "high"})
        assert card["status"] == "proposed"
        H.transition(session, inv, card["id"], "investigating", "run it")
        import pytest
        with pytest.raises(ValueError):
            H.transition(session, inv, card["id"], "supported", "no ev")
        H.transition(session, inv, card["id"], "supported", "found",
                     evidence=[{"experiment_id": "e1"}])
        cards = H.list_cards(inv)
        assert cards[0]["status"] == "supported"
        with pytest.raises(ValueError):
            H.transition(session, inv, card["id"], "proposed", "bad jump")
    finally:
        session.close()


def test_experiment_design_labels_heuristic_and_isolation():
    from model_autopsy.backend.research import experiments as E
    plan = E.design(
        {"id": "h1", "diagnostics": ["dataset_validation"],
         "expected_observables": ["x"],
         "support_criteria": "s", "refute_criteria": "r"},
        ["dataset_validation"])
    assert "heuristic" in plan["prioritization"]["method"].lower()
    assert "NOT" in plan["prioritization"]["method"] or \
        "not" in plan["prioritization"]["method"].lower() or \
        "never" in plan["prioritization"]["method"].lower() or \
        "Bayesian" in plan["prioritization"]["method"]
    assert plan["safety"]["modifies_original"] is False
    out = E.execute_isolated(
        "test-inv", {**plan, "artifact": None},
        lambda work, seed: {"ok": True, "n": 3})
    assert out["status"] == "ran"
    assert out["provenance"]["original_modified"] is False


def test_verification_preserves_disagreement():
    from model_autopsy.backend.research import verification as V
    review = V.review_claim({"summary": "big claim", "n": 5,
                             "method": "", "numbers": {}},
                            [])
    assert review["verdict"] in ("rejected", "downgraded")
    assert review["disagreement"]


def test_challenge_suite_nine_scenarios_offline():
    from model_autopsy.backend.db import SessionLocal, init_db
    init_db()
    from model_autopsy.backend.projects import ProjectSpec
    from model_autopsy.backend.research import lab, evaluate, challenge
    assert len(challenge.SCENARIOS) >= 8
    families = {s["family"] for s in challenge.SCENARIOS}
    assert len(families) >= 8
    assert any(s["kind"] == "clean" for s in challenge.SCENARIOS)
    assert any(s["kind"] == "multi" for s in challenge.SCENARIOS)
    session = SessionLocal()
    try:
        hits = 0
        for sc in challenge.SCENARIOS:
            spec = ProjectSpec.from_dict(dict(sc["spec"]))
            inv = _inv(session)
            report = lab.run_autonomous_investigation(
                session, inv, spec,
                artifact_path=sc["artifact"], max_experiments=3)
            scored = evaluate.score_run(report, sc)
            assert "aggregate" in scored
            assert set(scored["dimensions"]) >= {
                "discovery", "reasoning", "experimentation",
                "accuracy", "efficiency", "reliability"}
            if scored["hit"]:
                hits += 1
        assert hits >= 6, f"only {hits} hits"
    finally:
        session.close()


def test_research_api_endpoints():
    from fastapi.testclient import TestClient
    from model_autopsy.backend.db import init_db
    init_db()
    from model_autopsy.backend.api import app
    c = TestClient(app)
    iid = c.post("/api/investigations", json={
        "mode": "ml", "title": "lab api",
        "question": "does the lab run end to end?"}).json()["id"]
    assert c.post(f"/api/investigations/{iid}/research/run").status_code == 200
    st = c.get(f"/api/investigations/{iid}/research").json()
    assert st["report"] and st["report"]["executive_summary"]
    hid = c.post(f"/api/investigations/{iid}/research/hypotheses",
                 json={"title": "manual idea", "mechanism": "m",
                       "support_criteria": "s",
                       "refute_criteria": "r"}).json()["id"]
    r = c.post(f"/api/research/hypotheses/{hid}/transition",
               json={"investigation_id": iid, "to": "blocked",
                     "note": "no data"})
    assert r.status_code == 200 and r.json()["status"] == "blocked"
    bad = c.post(f"/api/research/hypotheses/{hid}/transition",
                 json={"investigation_id": iid, "to": "supported"})
    assert bad.status_code == 400  # blocked -> supported needs evidence path
    assert len(c.get(
        f"/api/investigations/{iid}/research").json()["hypotheses"]) >= 2


def test_research_contexts_dedup_and_measure():
    from model_autopsy.backend.research import rcontexts as R
    entries = [{"tool": "a", "summary": "same"},
               {"tool": "a", "summary": "same"},
               {"tool": "b", "summary": "diff"}]
    assert len(R.dedup(entries)) == 2
    m = R.measure(1000, 300)
    assert m["reduction_pct"] == 70.0
    assert "universal" in m["honesty"] or "%" in m["honesty"]
