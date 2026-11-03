"""M13 Evaluation 2.0: second corpus, novelty, stats (offline)."""
from model_autopsy.backend.db import SessionLocal, init_db


def test_corpus_b_runs_and_scores():
    from model_autopsy.backend.m10 import runner_b as RB
    from model_autopsy.backend.m10 import eval2 as E2
    init_db()
    s = SessionLocal()
    try:
        b = RB.run_scenario_b("b_unit_shift", s, max_steps=4)
        truth = RB.load_truth_b()["b_unit_shift"]
        g = E2.score(b, truth, session=s)
        assert g["dimensions"]["discovery_recall"] == 1.0
        assert g["dimensions"]["key_tool_measured"] == 1.0
        nov = E2.novelty(["zone", "sqft", "target", "prediction"], truth)
        assert "zone" in nov["manifestation_novelty"]
    finally:
        s.close()


def test_eval2_controls():
    from model_autopsy.backend.m10 import runner_b as RB
    from model_autopsy.backend.m10 import eval2 as E2
    from model_autopsy.backend.research import autonomous as AU
    init_db()
    for art, sid, task, brief in (
            ("model_autopsy/tests/fixture_m10b/b_steady.csv",
             "b_steady", "classification", "Routine check."),
            ("model_autopsy/tests/fixture_m10b/b_thin.csv",
             "b_thin", "classification", "Tiny pilot.")):
        s = SessionLocal()
        try:
            b = AU.run_autonomous(s, art, task, brief, max_steps=4,
                                  investigation_title=f"controls {sid}")
            b["scenario"] = sid
            truth = RB.load_truth_b()[sid]
            g = E2.score(b, truth, session=s)
            assert g["mean"] >= 0.5, g
        finally:
            s.close()


def test_portfolio_assess():
    from model_autopsy.backend.m12 import portfolio as PF
    out = PF.assess([
        {"id": "a", "status": "active", "agenda": [],
         "experiments": [{"tool": "x"}], "unresolved": []},
        {"id": "b", "status": "active", "agenda": [
            {"id": "p", "kind": "paid", "status": "awaiting-approval"}],
         "experiments": [], "unresolved": ["q"]}])
    assert out["promising"] and out["needs_review"]


def test_flagship_m13_demo():
    from model_autopsy.demo.flagship_m13 import run_flagship
    from model_autopsy.backend.db import SessionLocal
    out = run_flagship(SessionLocal,
                       lab_base="model_autopsy/.lab", max_steps=4)
    assert out["single"]["eval2"]["dimensions"][
        "discovery_recall"] == 1.0
    assert out["ablations"]["full"]["eval2"]["dimensions"][
        "discovery_recall"] == 1.0
    assert out["persistence"]["no_duplicate"] is True
    assert out["aggregate"]["n"] == 4
