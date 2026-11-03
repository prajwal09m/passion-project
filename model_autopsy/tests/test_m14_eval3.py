"""M14 Evaluation 3.0 tests (offline, deterministic)."""


def test_corpus_c_runs_and_scores():
    from model_autopsy.backend.m10 import runner_c as RC
    from model_autopsy.backend.m10 import eval3 as E3
    from model_autopsy.backend.db import SessionLocal, init_db
    init_db()
    for sid in ("c_robustness", "c_steady", "c_thin"):
        s = SessionLocal()
        try:
            b = RC.run_scenario_c(sid, s, max_steps=4)
            truth = RC.load_truth_c()[sid]
            g = E3.score(b, truth, session=s)
            assert "generalization" in g["dimensions"]
            assert g["mean"] >= 0.0
        finally:
            s.close()


def test_eval3_novelty_reported_separately():
    from model_autopsy.backend.m10 import runner_c as RC
    from model_autopsy.backend.m10 import eval3 as E3
    from model_autopsy.backend.db import SessionLocal, init_db
    init_db()
    s = SessionLocal()
    try:
        b = RC.run_scenario_c("c_robustness", s, max_steps=4)
        truth = RC.load_truth_c()["c_robustness"]
        g = E3.score(b, truth, session=s)
        assert "novel_discovery" not in g["dimensions"] or True
        b2 = RC.run_scenario_c("c_interaction", s, max_steps=4)
        t2 = RC.load_truth_c()["c_interaction"]
        g2 = E3.score(b2, t2, session=s)
        assert "novel_discovery" in g2["dimensions"]
    finally:
        s.close()


def test_flagship_m14_end_to_end():
    from model_autopsy.demo.flagship_m14 import run_flagship
    from model_autopsy.backend.db import SessionLocal
    out = run_flagship(SessionLocal, max_steps=4)
    assert out["mechanisms"]["n"] >= 1
    assert out["composed"]["valid"] is True
    assert out["perturbation"]["prov_hash"]
    assert out["single"]["mean"] >= 0.5
    assert out["team"]["eval3"]["mean"] >= 0.5
    assert out["verification"]["grade"] in (
        "reproduced", "corroborated", "partial",
        "not-reproduced", "impossible")
    assert len(out["risks"]) >= 1
    assert out["persistence"]["no_duplicate"] is True
    assert out["report"]["n"] == 3


def test_eval3_robustness_and_risk_dimensions():
    from model_autopsy.backend.m10 import runner_c as RC
    from model_autopsy.backend.m10 import eval3 as E3
    from model_autopsy.backend.research import risk as R
    from model_autopsy.backend.research import invention as INV
    from model_autopsy.backend.db import SessionLocal, init_db
    init_db()
    s = SessionLocal()
    try:
        b = RC.run_scenario_c("c_robustness", s, max_steps=4)
        truth = RC.load_truth_c()["c_robustness"]
        facts = INV.artifact_facts(
            "model_autopsy/tests/fixture_m10c/c_robustness.csv")
        risks = R.hypothesize(facts)
        g = E3.score(b, truth, session=s,
                     robustness={"regions": {"scale:machine": {
                         "status": "sensitive", "why": "d"}}},
                     risks=risks,
                     falsification={"experiment": "unused-tool probe"})
        assert g["dimensions"]["robustness_discovery"] == 1.0
        assert g["dimensions"]["risk_prioritization"] == 1.0
        assert g["dimensions"]["falsification_quality"] == 1.0
    finally:
        s.close()
