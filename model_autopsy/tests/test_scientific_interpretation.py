"""P0/P1 acceptance: scientific status, auto hypotheses, experiments, scripts, uploads."""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from model_autopsy.backend import db, engine, tools_registry
from model_autopsy.backend import scientific as SCI
from model_autopsy.backend import hypothesis_gen as HG
from model_autopsy.backend import script_inspection as SI


def _fresh_session(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_AUTOPSY_DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("MODEL_AUTOPSY_TESTING", "1")
    import importlib
    import model_autopsy.backend.db as dbmod
    importlib.reload(dbmod)
    import model_autopsy.backend.engine as emod
    importlib.reload(emod)
    dbmod.init_db()
    return dbmod.SessionLocal()


def _mk_csv(path: Path, leak: bool = True):
    from model_autopsy.backend import config as _cfg
    path = Path(_cfg.PROJECT_ROOT) / "model_autopsy" / "backend" / "data" / "uploads" / ("sci_" + path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    import numpy as np
    rng = np.random.default_rng(0)
    n = 200
    y = rng.integers(0, 2, n)
    leak_col = y.astype(float) + rng.normal(0, 0.05, n) if leak else rng.normal(0, 1, n)
    df = pd.DataFrame({"score": leak_col, "label": y, "leak_feat": leak_col, "noise": rng.normal(0, 1, n)})
    df.to_csv(path, index=False)
    return path


def test_battery_no_hypotheses_is_inconclusive(tmp_path, monkeypatch):
    s = _fresh_session(tmp_path, monkeypatch)
    inv = engine.create_investigation(s, "ml", "t", "q", {})
    out = SCI.evaluate(s, inv)
    assert out["status"] == "inconclusive"
    s.close()


def test_suspicion_without_provenance_not_confirmed(tmp_path, monkeypatch):
    s = _fresh_session(tmp_path, monkeypatch)
    p = _mk_csv(tmp_path / "a.csv", leak=True)
    inv = engine.create_investigation(s, "ml", "t", "leak?", {"predictions_path": str(p)})
    engine.run_tool(s, inv, "feature_target_suspiciousness", {"feature_csv": str(p), "label_csv": str(p)})
    gen = HG.generate_candidates(s, inv)
    assert 1 <= len(gen["created"]) <= 3
    htext = s.get(db.Hypothesis, gen["created"][0]["id"]).text
    assert "may" in htext.lower() or "warrant" in htext.lower()
    assert "leak" in htext.lower() or "target" in htext.lower()
    # must not claim confirmed leakage
    assert "is leaking" not in htext.lower() or "may" in htext.lower()
    sci = SCI.evaluate(s, inv)
    assert sci["status"] in ("inconclusive", "partially_supported")
    assert sci["status"] != "supported"
    s.close()


def test_no_fabricated_evidence_refs(tmp_path, monkeypatch):
    s = _fresh_session(tmp_path, monkeypatch)
    p = _mk_csv(tmp_path / "b.csv", leak=True)
    inv = engine.create_investigation(s, "ml", "t", "q", {"predictions_path": str(p)})
    engine.run_tool(s, inv, "feature_target_suspiciousness", {"feature_csv": str(p), "label_csv": str(p)})
    HG.generate_candidates(s, inv)
    from model_autopsy.backend.db import Hypothesis, Action
    valid = {a.id for a in s.query(Action).filter(Action.investigation_id == inv.id).all()}
    for h in s.query(Hypothesis).filter(Hypothesis.investigation_id == inv.id).all():
        for r in (h.evidence_refs or []):
            assert r["action_id"] in valid
    s.close()


def test_deterministic_and_deduped(tmp_path, monkeypatch):
    s = _fresh_session(tmp_path, monkeypatch)
    p = _mk_csv(tmp_path / "c.csv", leak=True)
    inv = engine.create_investigation(s, "ml", "t", "q", {"predictions_path": str(p)})
    engine.run_tool(s, inv, "feature_target_suspiciousness", {"feature_csv": str(p), "label_csv": str(p)})
    g1 = HG.generate_candidates(s, inv)
    g2 = HG.generate_candidates(s, inv)
    assert len(g1["created"]) >= 1 and len(g2["created"]) == 0
    # manual preserved
    engine.add_hypothesis(s, inv.id, "manual explanation", "manual", "r")
    g3 = HG.generate_candidates(s, inv)
    assert len(g3["created"]) == 0
    from model_autopsy.backend.db import Hypothesis
    assert s.query(Hypothesis).filter(Hypothesis.investigation_id == inv.id).count() == len(g1["created"]) + 1
    s.close()


def test_verified_leakage_supported_and_unverified_partial(tmp_path, monkeypatch):
    s = _fresh_session(tmp_path, monkeypatch)
    p = _mk_csv(tmp_path / "d.csv", leak=True)
    inv = engine.create_investigation(s, "ml", "t", "q", {"predictions_path": str(p)})
    engine.run_tool(s, inv, "feature_target_suspiciousness", {"feature_csv": str(p), "label_csv": str(p)})
    engine.run_tool(s, inv, "classification_metrics", {"predictions_path": str(p), "score_column": "score"})
    HG.generate_candidates(s, inv)
    from model_autopsy.backend.db import Hypothesis
    h = s.query(Hypothesis).filter(Hypothesis.investigation_id == inv.id).first()
    engine.update_hypothesis(s, h.id, "supported")
    sci = SCI.evaluate(s, inv)
    # only one supporting tool -> partially_supported, not supported
    assert sci["status"] == "partially_supported"
    s.close()


def test_no_issue_within_scope_and_contradicted(tmp_path, monkeypatch):
    s = _fresh_session(tmp_path, monkeypatch)
    p = _mk_csv(tmp_path / "e.csv", leak=False)
    # force low suspicion by using noise only? evaluator reads top_correlations; noise may still be low
    inv = engine.create_investigation(s, "ml", "t", "q", {"predictions_path": str(p)})
    engine.run_tool(s, inv, "classification_metrics", {"predictions_path": str(p), "score_column": "noise"})
    engine.run_tool(s, inv, "dataset_validation", {"predictions_path": str(p), "score_columns": ["noise"]})
    sci = SCI.evaluate(s, inv)
    # with 2 relevant tools and no open hyps, either inconclusive (if suspicion) or no_issue
    assert sci["status"] in ("inconclusive", "no_issue_detected_within_scope")
    assert "universally" not in (sci["guidance"] or "").lower() or "not" in (sci["guidance"] or "").lower()
    # contradicted path
    h = engine.add_hypothesis(s, inv.id, "x leaks", "manual", None)
    engine.update_hypothesis(s, h["id"], "rejected")
    sci2 = SCI.evaluate(s, inv)
    assert sci2["status"] in ("contradicted", "inconclusive", "no_issue_detected_within_scope", "partially_supported")
    s.close()


def test_experiments_from_hypotheses(tmp_path, monkeypatch):
    s = _fresh_session(tmp_path, monkeypatch)
    p = _mk_csv(tmp_path / "f.csv", leak=True)
    inv = engine.create_investigation(s, "ml", "t", "leak?", {"predictions_path": str(p)})
    engine.run_tool(s, inv, "feature_target_suspiciousness", {"feature_csv": str(p), "label_csv": str(p)})
    HG.generate_candidates(s, inv)
    recs = HG.recommend(s, inv)
    assert len(recs) >= 1
    r = recs[0]
    for k in ("title", "what", "why", "support_if", "contradict_if", "hypothesis_id"):
        assert r.get(k)
    s.close()


def test_script_inspection_safe(tmp_path, monkeypatch):
    _ = _fresh_session(tmp_path, monkeypatch)
    from model_autopsy.backend import config as cfg
    root = Path(cfg.PROJECT_ROOT)
    target = tmp_path / "train_demo.py"
    target.write_text("import pandas as pd\nX = pd.read_csv('a.csv')\nmodel.fit(X)\nfrom sklearn.model_selection import train_test_split\n", encoding="utf-8")
    # resolve_restricted requires path inside allowed roots: copy under project root uploads
    dest = root / "model_autopsy" / "backend" / "data" / "uploads" / "test_script_demo.py"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(target.read_bytes())
    try:
        out = SI.inspect_script(str(dest))
        assert out["ok"] is True and out["executed"] is False
        assert "never executed" in out["note"].lower() or "static" in out["note"].lower()
        bad = dest.with_name("bad_demo.py")
        bad.write_text("def broken(:\n", encoding="utf-8")
        out2 = SI.inspect_script(str(bad))
        assert out2["ok"] is False
    finally:
        try:
            dest.unlink()
        except OSError:
            pass
        try:
            dest.with_name("bad_demo.py").unlink()
        except OSError:
            pass


def test_upload_dedupe_and_remove(tmp_path, monkeypatch):
    from model_autopsy.backend import api as api_mod
    up = api_mod._uploads_root()
    up.mkdir(parents=True, exist_ok=True)
    b1 = up / "batch_test_1"
    b1.mkdir(exist_ok=True)
    (b1 / "f.csv").write_bytes(b"a,b\n1,2\n")
    b2 = up / "batch_test_2"
    b2.mkdir(exist_ok=True)
    (b2 / "copy.csv").write_bytes(b"a,b\n1,2\n")
    try:
        listed = api_mod.list_uploads()["uploads"]
        mine = [e for e in listed if e["batch"] in ("batch_test_1", "batch_test_2")]
        assert len(mine) == 2
        assert any(e.get("is_duplicate") for e in mine)
    finally:
        import shutil
        shutil.rmtree(b1, ignore_errors=True)
        shutil.rmtree(b2, ignore_errors=True)


def test_report_additive_sections(tmp_path, monkeypatch):
    s = _fresh_session(tmp_path, monkeypatch)
    p = _mk_csv(tmp_path / "g.csv", leak=True)
    inv = engine.create_investigation(s, "ml", "t", "leak?", {"predictions_path": str(p)})
    engine.run_tool(s, inv, "classification_metrics", {"predictions_path": str(p), "score_column": "score"})
    HG.generate_candidates(s, inv)
    rep = engine.build_report(s, inv)
    for k in ("confirmed", "likely", "rejected", "unresolved", "evidence_performed",
              "recommended_next", "execution_status", "scientific_assessment",
              "main_interpretation", "investigation_scope", "recommended_experiments"):
        assert k in rep
    assert rep["scientific_assessment"]["status"] in SCI.VALID_SCIENTIFIC
    s.close()
