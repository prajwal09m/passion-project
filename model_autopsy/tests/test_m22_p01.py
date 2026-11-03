"""M22 P0.1: useful_evidence visibility (Option A), offline only.

No live calls. Proves the persisted manifest/provenance signal —
not just the helper — distinguishes executed-only from useful
evidence, with completion semantics unchanged.
"""
import json

import pytest

from model_autopsy.backend.db import SessionLocal as _SessionLocal
from model_autopsy.backend.db import init_db

_open_sessions: list = []


def _session():
    s = _SessionLocal()
    _open_sessions.append(s)
    return s


@pytest.fixture(autouse=True)
def _close_test_sessions():
    yield
    while _open_sessions:
        s = _open_sessions.pop()
        try:
            s.close()
        except Exception:
            pass


MUSIC = "model_autopsy/tests/fixture_eval/investigator/music_rank.csv"


def _inv(s):
    from model_autopsy.backend import engine
    return engine.create_investigation(
        s, "ml", "m22p01", "p01 probe",
        {"max_iterations": 3, "predictions_path": MUSIC,
         "m16_skeptic": False})


def _hyps(s, inv):
    from model_autopsy.backend.db import Hypothesis
    return s.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).order_by(
        Hypothesis.id).all()


def _msg(text, rid="r"):
    return {"id": rid, "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": text}]}],
            "usage": {"input_tokens": 1, "output_tokens": 1}}


def _calls_msg(text, *specs, rid="r"):
    items = [{"type": "message", "content": [
        {"type": "output_text", "text": text}]}]
    for cid, name, args in specs:
        items.append({"type": "function_call", "call_id": cid,
                      "name": name,
                      "arguments": json.dumps(args, sort_keys=True)})
    return {"id": rid, "status": "completed", "output": items,
            "usage": {"input_tokens": 1, "output_tokens": 1}}


def _dynamic_block(kw):
    for item in kw.get("input_items") or []:
        try:
            body = json.loads(item.get("content") or "{}")
        except (ValueError, AttributeError):
            continue
        if isinstance(body, dict) and "allowed_hypothesis_ids" in body:
            ids = list(body["allowed_hypothesis_ids"] or [])
            recs = [{"hypothesis_id": i, "status": "investigating"}
                    for i in ids]
            unc = ["cause unmeasured"] if ids else ["nothing recorded"]
            return _msg(json.dumps({
                "conclusion": "open verdict.",
                "status_recommendations": recs,
                "uncertainties": unc,
                "recommended_next": ""}).join(
                    ["```investigation_summary\n", "\n```"]), rid="rep")
    raise AssertionError("no repair prompt seen")


def _run_driver(monkeypatch, tmp_path, script, max_rounds=1, tag="p01"):
    from model_autopsy.backend.meta_api import client as C
    queue = list(script)

    def fake(**kw):
        blob = json.dumps(kw, sort_keys=True, default=str)
        if "allowed_hypothesis_ids" in blob:
            return _dynamic_block(kw)
        assert queue, "provider called more times than scripted"
        return queue.pop(0)

    monkeypatch.setattr(C, "create_response", fake)
    from model_autopsy.backend.live import driver as D
    return D.run_live_investigation("eval_music", tmp_path,
                                   max_rounds=max_rounds,
                                   run_id="m22p01-" + tag)


def _read(rundir, name):
    import json as _json
    return _json.loads((rundir / name).read_text())


# ---- helper unit behavior -----------------------------------------------------

def test_p01_helper_moving_failed_nonmoving():
    init_db(); s = _session(); inv = _inv(s)
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    assert LK.has_useful_evidence(s, inv) is False
    engine.propose_hypothesis(s, inv, text="mechanism m",
                              predicted_observation="probe decides")
    h = _hyps(s, inv)[0]
    # failed action cited as supports: execution failed, not useful
    bad = engine.run_tool(s, inv, "ranking_slice_diagnostics",
                          {"predictions_path": MUSIC,
                           "slice_column": "no_such_column",
                           "score_column": "score", "labels": "relevance"},
                          source_meta=True)
    assert bad.get("ok") is False and bad.get("action_id")
    engine.link_evidence(s, h.id, bad["action_id"], "supports")
    assert LK.has_useful_evidence(s, inv) is False
    # non-moving relation on a ran action: visible, not useful
    good = engine.run_tool(s, inv, "artifact_summary",
                           {"predictions_path": MUSIC}, source_meta=True)
    assert good.get("ok") is True
    engine.link_evidence(s, h.id, good["action_id"], "mentions")
    assert LK.has_useful_evidence(s, inv) is False
    # moving relation on a ran action: useful
    engine.link_evidence(s, h.id, good["action_id"], "supports")
    assert LK.has_useful_evidence(s, inv) is True


def test_p01_helper_ignores_other_investigations():
    init_db(); s = _session()
    a = _inv(s)
    b = _inv(s)
    from model_autopsy.backend import engine
    from model_autopsy.backend.causal import linker as LK
    engine.propose_hypothesis(s, b, text="other mechanism",
                              predicted_observation="probe decides")
    h = _hyps(s, b)[0]
    act = engine.run_tool(s, b, "artifact_summary",
                          {"predictions_path": MUSIC}, source_meta=True)
    engine.link_evidence(s, h.id, act["action_id"], "supports")
    assert LK.has_useful_evidence(s, b) is True
    assert LK.has_useful_evidence(s, a) is False


# ---- persisted manifest / provenance ------------------------------------------

def test_p01_baseline_only_run_not_useful(monkeypatch, tmp_path):
    """artifact_summary ran fine; nothing linked; semantics preserved."""
    init_db()
    rec = _run_driver(monkeypatch, tmp_path, [
        _calls_msg("summarizing baseline",
                   ("c1", "artifact_summary", {"predictions_path": MUSIC}),
                   rid="r1"),
        _msg("round two prose, no block here", rid="r2")],
        tag="base")
    rundir = tmp_path / rec["run_id"]
    manifest = _read(rundir, "manifest.json")
    assert manifest["useful_evidence"] is False
    assert manifest["status"] == "completed"  # semantics unchanged
    assert rec["budget"]["experiments"][0] >= 1
    eval_report = _read(rundir, "eval_report.json")
    assert eval_report["report_provenance"]["useful_evidence"] is False
    hyps = _read(rundir, "hypotheses.json")
    assert hyps == []
    res = [e for e in _read(rundir, "events_dump.json")
           if e.get("kind") == "resolution"]
    assert res and res[-1]["payload"]["status"] == "unresolved"
    assert "available diagnostics never run" in " ".join(
        eval_report.get("limitations", []))


def test_p01_useful_run_true_in_manifest_and_provenance(monkeypatch,
                                                       tmp_path):
    init_db()
    rec = _run_driver(monkeypatch, tmp_path, [
        _calls_msg("proposing and measuring",
                   ("c1", "propose_hypothesis",
                    {"text": "selective slice mechanism causes the gap"}),
                   ("c2", "ranking_slice_diagnostics",
                    {"predictions_path": MUSIC, "slice_column": "slice",
                     "score_column": "score", "labels": "relevance"}),
                   rid="r1"),
        _msg("round two prose, no block here", rid="r2")],
        tag="useful")
    rundir = tmp_path / rec["run_id"]
    assert _read(rundir, "manifest.json")["useful_evidence"] is True
    assert _read(rundir,
                 "eval_report.json")["report_provenance"][
                     "useful_evidence"] is True


def test_p01_signal_restored_from_persisted_db(monkeypatch, tmp_path):
    """The signal recomputes identically from durable artifacts (resume)."""
    init_db()
    rec = _run_driver(monkeypatch, tmp_path, [
        _calls_msg("proposing and measuring",
                   ("c1", "propose_hypothesis",
                    {"text": "selective slice mechanism causes the gap"}),
                   ("c2", "ranking_slice_diagnostics",
                    {"predictions_path": MUSIC, "slice_column": "slice",
                     "score_column": "score", "labels": "relevance"}),
                   rid="r1"),
        _msg("round two prose, no block here", rid="r2")],
        tag="restore")
    rundir = tmp_path / rec["run_id"]
    manifest_val = _read(rundir, "manifest.json")["useful_evidence"]
    import shutil
    copy = tmp_path / "restore_copy.sqlite3"
    shutil.copy2(rundir / "live.sqlite3", copy)
    from model_autopsy.backend.eval import runner as R
    from model_autopsy.backend.causal import linker as LK
    fac = R.session_for(str(copy))
    s2 = fac()
    try:
        from model_autopsy.backend.db import Investigation
        inv_id = rec["run_id"] and s2.query(Investigation).first().id
        inv2 = s2.get(Investigation, inv_id)
        assert bool(LK.has_useful_evidence(s2, inv2)) == manifest_val
    finally:
        s2.close()


def test_p01_backward_compat_and_error_path(tmp_path):
    """Old manifests lack the key (.get → None); failure path records None."""
    import json as _json
    old = _json.loads(
        open("model_autopsy/benchmarks/live_runs/m19-music-01/"
             "manifest.json", encoding="utf-8").read())
    assert "useful_evidence" not in old
    assert old.get("useful_evidence") is None
    from model_autopsy.backend.live import recorder as REC
    rundir = tmp_path / "m22p01-compat"
    rundir.mkdir()
    manifest = REC.finalize_run(rundir, "m22p01-compat", "eval_music",
                               None, None, None, "failed", None, None,
                               "boom", error="simulated")
    assert manifest["useful_evidence"] is None
    assert manifest["required_evidence_present"]["sandbox_db"] is False
