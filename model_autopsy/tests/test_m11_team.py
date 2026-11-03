"""M11 multi-agent collaboration tests (offline, deterministic)."""
import threading

from model_autopsy.backend.db import SessionLocal, init_db


def test_role_contracts():
    from model_autopsy.backend.m11 import roles
    facts = {"columns": ["ward", "label", "score"], "readable": True,
             "segments": ["ward"], "temporal_col": None,
             "split_col": None, "score_col": "score",
             "label_col": "label"}
    ds = roles.data_scientist(facts)
    assert ds["role"] == "data_scientist" and ds["segments"] == ["ward"]
    ma = roles.model_analyst([{"tool": "t",
                               "result": {"ok": True,
                                          "establishes": "e",
                                          "does_not_establish": "n"}}])
    assert ma["measurements"][0]["tool"] == "t"
    lead = roles.lead([{"id": "q1", "status": "open", "family": "f",
                        "priority": "high"}], [], 2)
    assert lead["assignments"] and lead["rationale"]
    j = roles.judge([{"id": "h", "text": "t", "status": "supported",
                      "evidence_refs": [
                          {"action_id": "a", "relation": "supports"},
                          {"action_id": "b", "relation": "supports"}]}])
    assert j["verdicts"][0]["independent_verdict"] == "upheld"


def test_skeptic_catches_unsupported_support():
    from model_autopsy.backend.m11 import roles
    sk = roles.skeptic([{"id": "h1", "text": "ward gap is real",
                         "status": "supported",
                         "evidence_refs": [
                             {"action_id": "a",
                              "relation": "supports"}]}],
                       [{"id": "a", "tool": "regression_metrics"}])
    blocking = [c for c in sk["challenges"]
                if c["type"] == "unsupported-support"]
    assert blocking and blocking[0]["blocks"] is True


def test_judge_downgrades_evidence_free_support():
    from model_autopsy.backend.m11 import roles
    j = roles.judge([{"id": "h1", "text": "x causes y",
                      "status": "supported", "evidence_refs": []}])
    assert j["verdicts"][0]["independent_verdict"] == \
        "overturned-to-investigating"


def test_judge_signature_excludes_lead_outputs():
    import inspect
    from model_autopsy.backend.m11 import roles
    params = set(inspect.signature(roles.judge).parameters)
    assert params == {"hypotheses"}, params  # independence by contract


def test_ledger_parallel_safety():
    from model_autopsy.backend.m11.ledger import Ledger, BudgetExceeded
    ledger = Ledger(tool_calls=10)
    errors = []

    def worker(n):
        for _ in range(5):
            try:
                ledger.reserve(f"agent-{n}", "tool")
            except BudgetExceeded as exc:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,))
               for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert ledger.used == 10  # never overspent
    assert len(errors) == 10  # 20 attempts - 10 cap


def test_disagreement_preserved_without_budget():
    from model_autopsy.backend.m11 import team as T
    init_db()
    s = SessionLocal()
    try:
        out = T.investigate(
            s, "m10_sparse",
            "model_autopsy/tests/fixture_m10/m10_sparse.csv",
            "classification", "Tiny pilot.", max_steps=2)
        for d in out["team"]["disagreements"]:
            assert d["challenge"] and d["resolution"]
            assert "preserved" in d["resolution"]  # never voted away
        assert out["team"]["ledger"]["used"] <= 2
        assert out["team"]["judge"]["verdicts"]
    finally:
        s.close()


def test_multi_vs_single_baseline():
    from model_autopsy.backend.m11 import team as T
    from model_autopsy.backend.m10 import runner as R
    from model_autopsy.backend.m10 import evaluator as E
    from model_autopsy.backend.m10 import sealed as S
    init_db()
    truth = S.load_truth()["m10_ward_gap"]
    s1, s2 = SessionLocal(), SessionLocal()
    try:
        single = R.run_scenario("m10_ward_gap", s1)
        g1 = E.grade("m10_ward_gap", single, truth, s1)
        multi = T.investigate(
            s2, "m10_ward_gap",
            "model_autopsy/tests/fixture_m10/m10_ward_gap.csv",
            "classification", "Tags look off across wards.",
            max_steps=6)
        g2 = E.grade("m10_ward_gap", multi["baseline"], truth, s2)
        assert g1["score"] >= 0.5, g1
        assert g2["score"] >= g1["score"], (g1, g2)  # never worse
        assert multi["team"]["judge"]["verdicts"]
    finally:
        s1.close()
        s2.close()


def test_investigator_responds_to_blocking_challenge():
    from model_autopsy.backend.m11 import team as T
    init_db()
    s = SessionLocal()
    try:
        out = T.investigate(
            s, "m10_ward_gap",
            "model_autopsy/tests/fixture_m10/m10_ward_gap.csv",
            "classification", "Tags look off across wards.",
            max_steps=6)
        team = out["team"]
        assert team["skeptic"]["challenges"], "ward gap must draw fire"
        # Every challenge ends answered-by-evidence or preserved;
        # blocking ones additionally demand a recorded response
        # whenever budget allowed a probe.
        for d in team["disagreements"]:
            assert d["challenge"] and d["resolution"]
        for r in team["investigator_responses"]:
            assert r["probe"] and "hypothesis_status_after" in r
        assert team["judge"]["verdicts"]
    finally:
        s.close()


def test_ablation_flags_disable_roles():
    from model_autopsy.backend.m11 import team as T
    init_db()
    s = SessionLocal()
    try:
        out = T.investigate(
            s, "m10_sparse",
            "model_autopsy/tests/fixture_m10/m10_sparse.csv",
            "classification", "Tiny pilot.", max_steps=2,
            skeptic=False, judge=False)
        assert out["team"]["skeptic"]["challenges"] == []
        assert out["team"]["judge"]["verdicts"] == []
        assert "ablation" in out["team"]["judge"]["limitations"][0]
    finally:
        s.close()


def test_response_probe_mechanism_runs_and_links():
    from model_autopsy.backend.m11 import team as T
    from model_autopsy.backend.m11.ledger import Ledger
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import Action
    init_db()
    s = SessionLocal()
    try:
        import os
        os.environ["MODEL_AUTOPILOT_TESTING"] = "1"
        art = "model_autopsy/tests/fixture_m10/m10_ward_gap.csv"
        inv = engine.create_investigation(
            s, "ml", "probe test", "b",
            {"max_iterations": 3, "predictions_path": art})
        from model_autopsy.backend.research import invention as INV
        facts = INV.artifact_facts(art)
        led = Ledger(tool_calls=3)
        led.reserve("investigator-response",
                    "residual_feature_dependence")
        out = T._run_probe(s, inv, "residual_feature_dependence",
                           art, facts)
        assert out.get("ok"), out
        assert led.remaining() == 2
    finally:
        s.close()
