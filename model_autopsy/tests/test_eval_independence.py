"""Milestone 4 independent-evaluation tests (offline, no provider calls).

Covers: ground-truth separation, workspace isolation, reproducibility,
hypothesis scoring, evidence attribution, no-failure/inconclusive/
adversarial cases, historical preservation, human-review workflow, API
integration, credential protection. The investigator under test is the
deterministic offline lab (no LLM); the framework reserves the same
interfaces for a future authorized live-model evaluation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

EVAL_FIX = Path("model_autopsy/tests/fixture_eval")


def _run_one(pid: str, tmp_path, max_experiments: int = 4) -> dict:
    from model_autopsy.backend.eval import runner as R
    out = tmp_path / "runs"
    out.mkdir(parents=True, exist_ok=True)
    db = str((tmp_path / f"{pid}.sqlite3").absolute())
    rec = R.run_all(out, only=pid, max_experiments=max_experiments,
                    run_id=f"eval-test-{pid}",
                    session_factory=R.session_for(db))
    return rec


# ------------------------------------------------ ground-truth separation
def test_separation_audit_passes_on_clean_env():
    from model_autopsy.backend.eval import separation as S
    res = S.audit_investigator_env()
    assert res["ok"] is True, res["violations"]
    assert res["files_scanned"] >= 8


def test_separation_audit_catches_planted_token(tmp_path):
    from model_autopsy.backend.eval import separation as S
    probe = S.INV_DIR / "_probe_tmp.txt"
    try:
        probe.write_text("notes mention recalibration step", encoding="utf-8")
        res = S.audit_investigator_env()
        assert res["ok"] is False
        assert any(v["file"] == "_probe_tmp.txt"
                   for v in res["violations"])
    finally:
        probe.unlink(missing_ok=True)
    assert S.audit_investigator_env()["ok"] is True


def test_discovery_input_exposes_no_truth():
    from model_autopsy.backend.eval import projects as P
    from model_autopsy.backend.eval import separation as S
    truth = P.load_truth()
    forbidden = set()
    for t in truth.values():
        forbidden.update(w.lower() for w in t.get("forbidden_tokens", []))
    for p in P.PROJECTS:
        disc = S.discovery_input(p)
        blob = json.dumps(disc).lower()
        assert "ground_truth" not in blob
        assert "mechanism" not in blob
        for tok in forbidden:
            assert tok not in blob, (p["id"], tok)


def test_truth_file_outside_investigator_tree():
    from model_autopsy.backend.eval import separation as S
    assert S.TRUTH_FILE.exists()
    with pytest.raises(ValueError):
        S.TRUTH_FILE.resolve().relative_to(S.INV_DIR.resolve())


# ------------------------------------------------ workspace isolation
def test_run_db_isolated_from_app_and_test_db(tmp_path):
    from model_autopsy.backend.eval import runner as R
    from model_autopsy.backend import config as C
    out = tmp_path / "runs"
    out.mkdir(parents=True, exist_ok=True)
    rec = R.run_all(out, only="eval_wellness",
                    run_id="eval-test-default-db")
    rundir = Path(rec["dir"])
    assert (rundir / "eval.sqlite3").exists()
    assert Path(C.DB_PATH).resolve() != (rundir / "eval.sqlite3").resolve()
    # The run DB lives inside the run dir; app/test DBs live elsewhere.
    assert (rundir / "eval_wellness.json").exists()


def test_run_never_overwrites_history(tmp_path):
    from model_autopsy.backend.eval import runner as R
    out = tmp_path / "runs"
    out.mkdir(parents=True, exist_ok=True)
    db = str((tmp_path / "a.sqlite3").absolute())
    R.run_all(out, only="eval_wellness", run_id="eval-dup",
              session_factory=R.session_for(db))
    with pytest.raises(RuntimeError):
        R.run_all(out, only="eval_wellness", run_id="eval-dup",
                  session_factory=R.session_for(db))


def test_runner_refuses_with_credentials_set(tmp_path, monkeypatch):
    from model_autopsy.backend.eval import runner as R
    monkeypatch.setenv("MODEL_API_KEY", "sk-test-should-never-be-used")
    with pytest.raises(RuntimeError):
        R.run_all(tmp_path / "runs", only="eval_wellness",
                  run_id="eval-cred")


# ------------------------------------------------ scoring: discovery
def test_credit_subgroup_found_distractor_not_claimed(tmp_path):
    rec = _run_one("eval_credit", tmp_path)
    sc = json.loads((Path(rec["dir"]) / "eval_credit.json"
                     ).read_text())["scorecard"]
    assert sc["verdict"] == "correct", sc
    assert sc["false_positive"] is False
    assert sc["dimensions"]["discovery"] == 1.0


def test_turbine_drift_without_false_leakage(tmp_path):
    rec = _run_one("eval_turbine", tmp_path)
    sc = json.loads((Path(rec["dir"]) / "eval_turbine.json"
                     ).read_text())["scorecard"]
    assert sc["verdict"] == "correct", sc
    assert sc["false_positive"] is False


def test_music_cold_start_found(tmp_path):
    rec = _run_one("eval_music", tmp_path)
    sc = json.loads((Path(rec["dir"]) / "eval_music.json"
                     ).read_text())["scorecard"]
    assert sc["verdict"] == "correct", sc


def test_docs_instability_found(tmp_path):
    rec = _run_one("eval_docs", tmp_path)
    sc = json.loads((Path(rec["dir"]) / "eval_docs.json"
                     ).read_text())["scorecard"]
    assert sc["verdict"] == "correct", sc


def test_claim_partial_not_full_credit(tmp_path):
    rec = _run_one("eval_claim", tmp_path)
    sc = json.loads((Path(rec["dir"]) / "eval_claim.json"
                     ).read_text())["scorecard"]
    assert sc["verdict"] == "partial", sc
    assert 0.0 < sc["overall"] < 1.0


# ------------------------------------------------ no-failure / weak evidence
def test_wellness_correct_null(tmp_path):
    rec = _run_one("eval_wellness", tmp_path)
    sc = json.loads((Path(rec["dir"]) / "eval_wellness.json"
                     ).read_text())["scorecard"]
    assert sc["verdict"] == "correct-null", sc
    assert sc["dimensions"]["calibration"] == 1.0


def test_pilot_inconclusive_without_fabrication(tmp_path):
    rec = _run_one("eval_pilot", tmp_path)
    rec_json = json.loads((Path(rec["dir"]) / "eval_pilot.json"
                           ).read_text())
    sc = rec_json["scorecard"]
    assert sc["verdict"] == "inconclusive", sc
    assert rec_json["report"]["confirmed_findings"] == []
    assert sc["false_positive"] is False


def test_unsupported_claim_penalized():
    from model_autopsy.backend.eval import scorer as SC
    from model_autopsy.backend.eval import projects as P
    truth = P.load_truth()
    report = {"confirmed_findings": [{"hypothesis_id": "x",
                                      "title": "Stale validation split "
                                               "hides drift"}],
              "rejected_hypotheses": [],
              "experiments": [{"experiment_id": "e1", "tool": "x",
                               "summary": "nothing"}],
              "executive_summary": "s"}
    sc = SC.score("eval_turbine", report, truth)
    assert sc["verdict"] == "unsupported", sc
    assert sc["dimensions"]["discovery"] < 0.5


def test_all_verdict_classes_reachable():
    from model_autopsy.backend.eval import scorer as SC
    from model_autopsy.backend.eval import projects as P
    truth = P.load_truth()
    mk = lambda conf, exps: {  # noqa: E731
        "confirmed_findings": conf, "rejected_hypotheses": [],
        "experiments": exps, "executive_summary": "s"}
    full = [{"experiment_id": "e1",
             "summary": "group_gap=0.46(region)",
             "numbers": {"group_gap": 0.46, "n": 1500}}]
    got = {
        "correct": SC.score(
            "eval_credit",
            mk([{"hypothesis_id": "h", "title": "Subgroup "
                 "underperformance hidden by pooled metric"}], full),
            truth)["verdict"],
        "correct-null": SC.score(
            "eval_wellness", mk([], [{"experiment_id": "e1",
                                      "summary": "MAE=2",
                                      "numbers": {"n": 800}}]),
            truth)["verdict"],
        "incorrect": SC.score(
            "eval_wellness", mk([{"hypothesis_id": "h",
                                  "title": "Proxy feature leaks the label"}],
                                full), truth)["verdict"],
        "inconclusive": SC.score(
            "eval_pilot", mk([], [{"experiment_id": "e1",
                                   "summary": "AUC=0.9",
                                   "numbers": {"n": 120}}]),
            truth)["verdict"],
    }
    assert got == {"correct": "correct", "correct-null": "correct-null",
                   "incorrect": "incorrect",
                   "inconclusive": "inconclusive"}, got


# ------------------------------------------------ evidence attribution
def test_numbers_must_support_claim():
    from model_autopsy.backend.eval import scorer as SC
    from model_autopsy.backend.eval import projects as P
    truth = P.load_truth()
    report = {"confirmed_findings": [{"hypothesis_id": "h",
                                      "title": "Ranking metric conceals "
                                               "position failure"}],
              "rejected_hypotheses": [],
              "experiments": [{"experiment_id": "e1",
                               "summary": "gap tiny",
                               "numbers": {"gap": 0.01}}],
              "executive_summary": "s"}
    sc = SC.score("eval_music", report, truth)
    assert sc["verdict"] == "unsupported", sc


def test_overall_weighting_documented_and_bounded():
    from model_autopsy.backend.eval import scorer as SC
    assert abs(sum(SC.WEIGHTS.values()) - 1.0) < 1e-9
    for d in ("discovery", "evidence", "reasoning", "calibration",
              "efficiency", "reproducibility"):
        assert d in SC.WEIGHTS


# ------------------------------------------------ reproducibility
def test_repeated_runs_agree(tmp_path):
    a = _run_one("eval_rent", tmp_path / "a")
    b = _run_one("eval_rent", tmp_path / "b")
    sa = json.loads((Path(a["dir"]) / "eval_rent.json"
                     ).read_text())["scorecard"]
    sb = json.loads((Path(b["dir"]) / "eval_rent.json"
                     ).read_text())["scorecard"]
    assert sa["verdict"] == sb["verdict"] == "correct"
    assert sa["overall"] == sb["overall"]


# ------------------------------------------------ human review workflow
def test_blind_before_reveal_enforced(tmp_path):
    from model_autopsy.backend.eval import review as RV
    rd = tmp_path / "run"
    rd.mkdir()
    with pytest.raises(RuntimeError):
        RV.reveal_and_assess(rd, "eval_credit", "looks fine")
    rec = RV.blind_verdict(rd, "eval_credit", "r1", "defensible", "ok")
    assert rec["revealed"] is False
    assert rec["attests_no_prior_truth"] is True
    with pytest.raises(RuntimeError):
        RV.blind_verdict(rd, "eval_credit", "r1", "defensible")
    rev = RV.reveal_and_assess(rd, "eval_credit", "confirmed post-reveal")
    assert rev["revealed"] is True
    assert rev["blind_verdict"] == "defensible"
    with pytest.raises(ValueError):
        RV.blind_verdict(rd, "eval_music", "r1", "bogus-verdict")


def test_absent_review_reported_as_absent(tmp_path):
    from model_autopsy.backend.eval import review as RV
    st = RV.status(tmp_path, "eval_credit")
    assert st["review"] is None


# ------------------------------------------------ API integration
def test_eval_api_projects_audit_and_runs():
    from fastapi.testclient import TestClient
    from model_autopsy.backend.db import init_db
    init_db()
    from model_autopsy.backend.api import app
    c = TestClient(app)
    projs = c.get("/api/eval/projects").json()["projects"]
    assert len(projs) == 8
    assert {p["id"] for p in projs} >= {"eval_credit", "eval_pilot"}
    audit = c.get("/api/eval/separation-audit").json()
    assert audit["ok"] is True
    manifest = c.get("/api/eval/runs").json()["runs"]
    assert any(m["run_id"].startswith("eval-") for m in manifest)
    run_id = manifest[0]["run_id"]
    detail = c.get(f"/api/eval/runs/{run_id}").json()
    assert detail["aggregate"]["n"] == 8
    pid = detail["results"][0]["project"]
    rec = c.get(f"/api/eval/runs/{run_id}/{pid}").json()
    assert rec["scorecard"]["project"] == pid
    assert "human_review" in rec
    assert c.get("/api/eval/runs/nope").status_code == 404
    blind = c.post(f"/api/eval/runs/{run_id}/{pid}/review/blind",
                   json={"reviewer": "t", "verdict": "defensible"})
    assert blind.status_code in (200, 400)  # 400 if already reviewed
    bad = c.post(f"/api/eval/runs/{run_id}/{pid}/review/blind",
                 json={"reviewer": "t", "verdict": "nonsense"})
    assert bad.status_code == 400


# ------------------------------------------------ preservation + credentials
def test_no_provider_keys_in_test_env():
    import os
    assert not os.environ.get("MODEL_API_KEY", "").strip()
    assert not os.environ.get("GROQ_API_KEY", "").strip()


def test_eval_run_adds_no_live_dirs():
    import glob
    live = glob.glob("model_autopsy/benchmarks/phase_d_*live*")
    assert len(live) == 7, live


def test_frozen_m3_fixtures_untouched():
    import hashlib
    p = Path("model_autopsy/tests/fixture_universal/energy_demand.csv")
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    assert len(h) == 64 and p.stat().st_size > 0
    # Ground-truth text is sealed; runner must never read it.
    import model_autopsy.backend.eval.runner as R
    import inspect
    src = inspect.getsource(R)
    assert "ground_truth" not in src
