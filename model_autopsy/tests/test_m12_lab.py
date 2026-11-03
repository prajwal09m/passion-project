"""M12 continuous-laboratory tests (offline, deterministic)."""


def test_project_persistence_roundtrip(tmp_path):
    from model_autopsy.backend.m12 import projects as P
    doc = P.create(str(tmp_path), "understand ward gaps",
                   [{"id": "q1", "status": "queued"}],
                   {"tool_calls": 5})
    assert doc["status"] == "active"
    P.set_status(str(tmp_path), doc["id"], "paused")
    assert P.load(str(tmp_path), doc["id"])["status"] == "paused"
    assert any(p["id"] == doc["id"]
               for p in P.list_all(str(tmp_path)))


def test_experiment_idempotency_no_double_count(tmp_path):
    from model_autopsy.backend.m12 import projects as P
    doc = P.create(str(tmp_path), "obj")
    P.record_experiment(str(tmp_path), doc["id"], "t", {}, "k1",
                        {"ok": True})
    P.record_experiment(str(tmp_path), doc["id"], "t", {}, "k1",
                        {"ok": True, "other": 1})  # retried resume
    d = P.load(str(tmp_path), doc["id"])
    assert len(d["experiments"]) == 1
    assert d["resource_usage"]["tool_calls"] == 1


def test_scheduler_refuses_paid_without_approval(tmp_path):
    from model_autopsy.backend.m12 import projects as P
    from model_autopsy.backend.m12 import scheduler as S
    doc = P.create(str(tmp_path), "obj", budget={"tool_calls": 4})
    doc["agenda"] = [
        {"id": "off1", "kind": "offline", "status": "queued",
         "importance": 2, "info_gain": 2, "cost": 1},
        {"id": "paid1", "kind": "paid", "status": "queued",
         "importance": 9, "info_gain": 9, "cost": 1}]
    ran = []
    out = S.tick(doc, executor=lambda proj, prop: ran.append(
        prop["id"]))
    assert ran == ["off1"]  # offline ran
    assert out["deferred"] and out["deferred"][0]["id"] == "paid1"
    assert doc["agenda"][1]["status"] == "awaiting-approval"


def test_scheduler_ranking_and_budget(tmp_path):
    from model_autopsy.backend.m12 import scheduler as S
    props = [
        {"id": "cheap-good", "status": "queued", "importance": 5,
         "info_gain": 5, "cost": 1, "kind": "offline"},
        {"id": "pricey", "status": "queued", "importance": 9,
         "info_gain": 9, "cost": 99, "kind": "offline"}]
    ranked = S.rank(props, budget_left=5)
    assert [p["id"] for p in ranked] == ["cheap-good"]


def test_memory_transfer_guard(tmp_path):
    from model_autopsy.backend.m12 import memory as M
    M.remember(str(tmp_path), "replication", "ward gaps replicate",
               "proj_a", "run_1")
    denied = M.promote_to_universal(str(tmp_path),
                                    "ward gaps replicate")
    assert denied["ok"] is False
    M.remember(str(tmp_path), "replication", "ward gaps replicate",
               "proj_b", "run_2")
    ok = M.promote_to_universal(str(tmp_path), "ward gaps replicate")
    assert ok["ok"] is True
    assert ok["entry"]["scope"] == "universal"
    assert M.recall(str(tmp_path), "replication")


def test_repro_grades_honestly(tmp_path):
    from model_autopsy.backend.m12 import repro as R
    f = tmp_path / "a.csv"
    f.write_text("x\n1\n")
    s1 = R.snapshot(str(f), "t", {}, {"ok": True, "mae": 1.0})
    s2 = R.snapshot(str(f), "t", {}, {"ok": True, "mae": 1.0})
    assert R.grade(s1, s2)["grade"] == "exact"
    f.write_text("x\n2\n")
    s3 = R.snapshot(str(f), "t", {}, {"ok": True, "mae": 1.0})
    assert R.grade(s1, s3)["grade"] == "unreproducible"


def test_lab_api_smoke():
    from fastapi.testclient import TestClient
    from model_autopsy.backend import api as A
    c = TestClient(A.app)
    r = c.post("/api/lab/projects", json={"objectives": "smoke"})
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    assert c.get("/api/lab/projects").status_code == 200
    assert c.get(f"/api/lab/projects/{pid}").status_code == 200
    m = c.post("/api/lab/memory",
               json={"kind": "finding", "content": "x",
                     "project_id": pid, "run_id": "r"})
    assert m.status_code == 200, m.text
    assert c.get("/api/lab/memory",
                 params={"project_id": pid}).status_code == 200
    # Paid proposal without approval stays put.
    p = c.post(f"/api/lab/projects/{pid}/propose",
               json={"id": "paidX", "kind": "paid",
                     "importance": 9, "info_gain": 9, "cost": 1})
    assert p.status_code == 200
    t = c.post(f"/api/lab/projects/{pid}/tick", json={})
    assert t.status_code == 200
    assert any(d["id"] == "paidX" for d in t.json()["deferred"])


def test_knowledge_store_transfer_and_strategy(tmp_path):
    from model_autopsy.backend.m12 import knowledge as K
    K.store(str(tmp_path), "confounder", "ward mix shifts pooled AUC",
            "proj_a", evidence={"tool": "classification_metrics"},
            confidence=0.7, conditions="columns ward label score")
    cands = K.propose_transfer(
        str(tmp_path), {"columns": ["ward", "label", "score"],
                        "task": "classification"})
    assert any(c["treat_as"].startswith("hypothesis") for c in cands)
    K.record_transfer_outcome(str(tmp_path),
                              "ward mix shifts pooled AUC", "proj_b",
                              True, "confirmed with per-ward AUC")
    K.record_transfer_outcome(str(tmp_path),
                              "ward mix shifts pooled AUC", "proj_c",
                              False, "no ward column present")
    rep = K.strategy_record(str(tmp_path))
    assert rep["transfers_helped"] == 1 and rep["transfers_misled"] == 1


def test_verify_finding_independent_path(tmp_path):
    from model_autopsy.backend.m12 import verify as V
    from model_autopsy.backend.m12 import projects as P
    from model_autopsy.backend.db import SessionLocal, init_db
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import Hypothesis
    init_db()
    s = SessionLocal()
    try:
        art = "model_autopsy/tests/fixture_m10/m10_ward_gap.csv"
        inv = engine.create_investigation(
            s, "ml", "v", "b",
            {"max_iterations": 6, "predictions_path": art})
        engine.propose_hypothesis(
            s, inv, "One subgroup performs materially worse " + "v" * 20)
        r = engine.run_tool(
            s, inv, "classification_metrics",
            {"predictions_path": art, "score_column": "score",
             "split_by": "ward"}, source_meta=True)
        assert r["ok"], r
        from model_autopsy.backend.db import Action
        from model_autopsy.backend.causal import linker as LK
        LK.link_tool_result(s, inv, s.get(Action, r["action_id"]))
        hs = s.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv.id).all()
        target = next(h for h in hs if "subgroup" in h.text)
        hv = {"id": target.id, "text": target.text,
              "status": target.status,
              "evidence_refs": target.evidence_refs or []}
        out = V.verify_finding(s, inv, hv, art)
        assert out["grade"] in V.GRADES, out
        assert out["manifest"]["manifest_hash"]
        rep = V.grade_report([out])
        assert rep["counts"][out["grade"]] == 1
    finally:
        s.close()
