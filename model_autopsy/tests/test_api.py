"""API surface tests via FastAPI TestClient; SQLite is the real store."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from model_autopsy.backend.api import app
from model_autopsy.backend.db import init_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_AUTOPSY_TMP", str(tmp_path))
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    init_db()
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/api/health").json()["ok"] is True


def test_create_list_get_investigation(client):
    r = client.post("/api/investigations", json={
        "mode": "ml", "title": "T1", "question": "Where does the model fail?"})
    assert r.status_code == 200
    iid = r.json()["id"]
    assert r.json()["status"] == "created" and r.json()["max_iterations"] == 3
    lst = client.get("/api/investigations").json()["items"]
    assert any(i["id"] == iid for i in lst)
    detail = client.get(f"/api/investigations/{iid}").json()
    assert detail["question"].startswith("Where")


def test_bad_mode_rejected(client):
    r = client.post("/api/investigations", json={
        "mode": "chaos", "title": "x", "question": "y"})
    assert r.status_code == 400


def test_meta_status_and_settings(client):
    s = client.get("/api/meta/status").json()
    assert isinstance(s["key_configured"], bool)


def test_meta_turn_without_key_reports_unavailable(client):
    r = client.post("/api/investigations", json={
        "mode": "ml", "title": "T2", "question": "why?"})
    iid = r.json()["id"]
    res = client.post(f"/api/investigations/{iid}/meta-turn", json={}).json()
    assert res["status"] == "meta_unavailable"


def test_tool_endpoint_runs_real_ml_tool(client):
    r = client.post("/api/investigations", json={
        "mode": "ml", "title": "T3", "question": "why?"})
    iid = r.json()["id"]
    res = client.post(f"/api/investigations/{iid}/tool", json={
        "tool_name": "classification_metrics",
        "arguments": {"score_column": "LightGBM_C"}}).json()
    assert res["ok"] is True and res["result"]["n"] > 0


def test_tool_endpoint_refuses_unknown_tool(client):
    r = client.post("/api/investigations", json={
        "mode": "ml", "title": "T4", "question": "why?"})
    iid = r.json()["id"]
    res = client.post(f"/api/investigations/{iid}/tool", json={
        "tool_name": "deploy_to_production", "arguments": {}}).json()
    assert res["ok"] is False


def test_timeline_ordered(client):
    r = client.post("/api/investigations", json={
        "mode": "ml", "title": "T5", "question": "why?"})
    iid = r.json()["id"]
    client.post(f"/api/investigations/{iid}/tool", json={
        "tool_name": "artifact_summary", "arguments": {}})
    events = client.get(f"/api/investigations/{iid}/timeline").json()["events"]
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs) and len(seqs) >= 2


def test_case_study_endpoint(client):
    out = client.get("/api/case-study/demand-zone").json()
    assert out["name"].startswith("Demand Zone AI")
    if out.get("error") is None and out.get("summary"):
        assert out["summary"]["n_rows"] == 41221
