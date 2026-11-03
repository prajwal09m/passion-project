"""Eval v3 Stage 2/7/8: versioned pipeline, resume preservation, rollback.

Offline only: temp DBs, fixture CSVs, no providers, no spend.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from model_autopsy.backend import config as C
from model_autopsy.backend.api import app
from model_autopsy.backend.db import SessionLocal, init_db
from model_autopsy.backend.eval import pipeline as P


def _rep():
    return json.load(open("model_autopsy/benchmarks/live_runs/m22-live-01/"
                          "eval_report.json"))


def _truth():
    return json.load(open("model_autopsy/tests/fixture_eval/"
                          "ground_truth_eval.json"))


def test_default_is_v2_and_env_selects_v3(monkeypatch):
    monkeypatch.delenv("MODEL_AUTOPSY_EVAL_VERSION", raising=False)
    assert P.select_eval_rubric() == "v2"
    monkeypatch.setenv("MODEL_AUTOPSY_EVAL_VERSION", "v3")
    assert P.select_eval_rubric() == "v3"
    assert P.select_eval_rubric(explicit="v2") == "v2"  # explicit wins


def test_invalid_versions_fail_fast(monkeypatch):
    with pytest.raises(ValueError):
        P.select_eval_rubric(explicit="v9")
    monkeypatch.setenv("MODEL_AUTOPSY_EVAL_VERSION", "bogus")
    with pytest.raises(ValueError):
        P.select_eval_rubric()


def test_stored_version_wins_over_global_change(monkeypatch):
    inv = SimpleNamespace(config={"eval_rubric_version": "v2"})
    monkeypatch.setenv("MODEL_AUTOPSY_EVAL_VERSION", "v3")
    assert P.select_eval_rubric(inv=inv) == "v2"  # no silent switch
    assert P.select_eval_rubric(inv=SimpleNamespace(config={})) == "v2"


def test_corrupt_stored_version_refuses():
    inv = SimpleNamespace(config={"eval_rubric_version": "v99"})
    with pytest.raises(ValueError):
        P.select_eval_rubric(inv=inv)


def test_persist_records_version_and_event():
    init_db(); s = SessionLocal()
    from model_autopsy.backend import engine
    inv = engine.create_investigation(s, "ml", "t", "q", {})
    assert P.persist_eval_rubric(s, inv, "v3") == "v3"
    assert s.get(type(inv), inv.id).config["eval_rubric_version"] == "v3"


def test_pipeline_v2_stamps_version_without_changing_scores():
    from model_autopsy.backend.eval import scorer as V2
    out = P.score_report("eval_music", _rep(), _truth(), "v2")
    assert out["rubric_version"] == "v2"
    ref = V2.score("eval_music", _rep(), _truth())
    assert {k: out[k] for k in ("verdict", "overall", "dimensions")} == \
        {k: ref[k] for k in ("verdict", "overall", "dimensions")}


def test_pipeline_v3_scores_m22_honest_partial():
    out = P.score_report("eval_music", _rep(), _truth(), "v3")
    assert out["rubric_version"] == "v3"
    assert out["dimensions"]["discovery"] == 0.7
    assert out["dimensions"]["verification"] == 0.0
    assert out["overall"] is not None


def test_pipeline_v3_failure_is_explicit_never_silent_v2(monkeypatch):
    import model_autopsy.backend.eval.scorer_v3 as V3
    monkeypatch.setattr(V3, "score_v3",
                        lambda *a, **k: (_ for _ in ()).throw(
                            RuntimeError("boom")))
    out = P.score_report("eval_music", _rep(), _truth(), "v3")
    assert out["verdict"] == "unscored" and out["rubric_version"] == "v3"
    assert out["overall"] is None and "boom" in out["notes"]["error"]


def test_rollback_switch_leaves_archives_untouched(monkeypatch, tmp_path):
    target = ("model_autopsy/benchmarks/live_runs/m22-live-01/"
              "scorecard.json")
    before = open(target, "rb").read()
    monkeypatch.setenv("MODEL_AUTOPSY_EVAL_VERSION", "v3")
    assert P.select_eval_rubric() == "v3"
    v3 = P.score_report("eval_music", _rep(), _truth(), "v3")
    monkeypatch.setenv("MODEL_AUTOPSY_EVAL_VERSION", "v2")
    assert P.select_eval_rubric() == "v2"
    v2 = P.score_report("eval_music", _rep(), _truth(),
                        P.select_eval_rubric())
    assert v2["rubric_version"] == "v2" and v3["rubric_version"] == "v3"
    assert open(target, "rb").read() == before  # archives never rewritten


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_AUTOPSY_TMP", str(tmp_path))
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_AUTOPSY_EVAL_VERSION", raising=False)
    init_db()
    with TestClient(app) as c:
        yield c


def test_api_eval_versions_endpoint(client):
    body = client.get("/api/eval/versions").json()
    assert body["versions"] == ["v2", "v3"] and body["selected"] == "v2"


def test_api_create_accepts_and_persists_rubric(client):
    r = client.post("/api/investigations", json={
        "mode": "ml", "title": "T", "question": "why?",
        "eval_version": "v3"})
    assert r.status_code == 200
    assert r.json()["eval_rubric_version"] == "v3"
    bad = client.post("/api/investigations", json={
        "mode": "ml", "title": "T", "question": "why?",
        "eval_version": "v9"})
    assert bad.status_code == 400


def test_api_stop_parks_active_and_refuses_terminal(client):
    iid = client.post("/api/investigations", json={
        "mode": "ml", "title": "T", "question": "why?"}).json()["id"]
    r = client.post(f"/api/investigations/{iid}/stop")
    assert r.status_code == 200 and r.json()["status"] == "stopped"
    r2 = client.post(f"/api/investigations/{iid}/stop")
    assert r2.status_code == 400
    assert client.post("/api/investigations/nope/stop").status_code == 404


def test_reconcile_reads_stored_version_and_refuses_corrupt(tmp_path):
    import sqlite3
    from model_autopsy.backend.db import record_event
    from model_autopsy.backend.eval import runner as R
    from model_autopsy.backend.live import resume as RS
    factory = R.session_for(str((tmp_path / "r.sqlite3").absolute()))
    s = factory()
    from model_autopsy.backend import engine
    inv = engine.create_investigation(
        s, "ml", "t", "q",
        {"eval_project": "eval_music",
         "eval_rubric_version": "v3"})
    record_event(s, inv.id, "meta_response", "r",
                 payload={"response_id": "resp_1"})
    s.commit()
    run_dir = tmp_path / "run-x"
    run_dir.mkdir()
    import shutil
    shutil.copy2(tmp_path / "r.sqlite3", run_dir / "live.sqlite3")
    plan = RS.reconcile(run_dir)
    assert plan["eval_rubric_version"] == "v3"
    s2 = factory()
    inv2 = engine.create_investigation(
        s2, "ml", "t2", "q2",
        {"eval_project": "eval_music",
         "eval_rubric_version": "v99"})
    record_event(s2, inv2.id, "meta_response", "r",
                 payload={"response_id": "resp_2"})
    s2.commit()
    run_dir2 = tmp_path / "run-y"
    run_dir2.mkdir()
    # second investigation in same DB would break the exactly-1 rule, so
    # craft a dedicated DB file for the corrupt case
    factory3 = R.session_for(str((tmp_path / "r3.sqlite3").absolute()))
    s3 = factory3()
    inv3 = engine.create_investigation(
        s3, "ml", "t3", "q3",
        {"eval_project": "eval_music",
         "eval_rubric_version": "v99"})
    record_event(s3, inv3.id, "meta_response", "r",
                 payload={"response_id": "resp_3"})
    s3.commit()
    s3.close()
    shutil.copy2(tmp_path / "r3.sqlite3", run_dir2 / "live.sqlite3")
    import pytest as _pt
    with _pt.raises(RuntimeError, match="invalid"):
        RS.reconcile(run_dir2)


def test_offline_runner_records_rubric_version(tmp_path):
    from model_autopsy.backend.eval import runner as R
    rec = R.run_all(tmp_path, only="eval_wellness", max_experiments=1,
                    run_id="eval-test-v3",
                    session_factory=R.session_for(
                        str((tmp_path / "t.sqlite3").absolute())),
                    eval_version="v3")
    assert rec["manifest"]["eval_rubric_version"] == "v3"
    assert rec["manifest"]["eval_version"] == "m4-v1"  # framework intact
    proj = json.load(open(tmp_path / "eval-test-v3" / "eval_wellness.json"))
    assert proj["scorecard"]["rubric_version"] == "v3"
