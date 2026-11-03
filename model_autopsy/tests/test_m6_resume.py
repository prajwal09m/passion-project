"""Resume safety tests (offline: synthetic DBs, never the live run dir)."""
import json


def _mk(tmp_path, name="live-test"):
    from model_autopsy.backend.eval import runner as R
    d = tmp_path / name
    d.mkdir()
    return d, R.session_for(str(d / "live.sqlite3"))


def _inv(session):
    from model_autopsy.backend import engine
    return engine.create_investigation(
        session, "ml", "t", "q",
        {"max_iterations": 3, "predictions_path": "x",
         "live": {"eval_project": "eval_claim"}})


def _ev(session, iid, kind, title="t", payload=None):
    from model_autopsy.backend.db import record_event
    e = record_event(session, iid, kind, title, payload=payload or {})
    session.commit()
    return e


def test_reconcile_refuses_finalized(tmp_path):
    from model_autopsy.backend.live import resume as RS
    d, _ = _mk(tmp_path)
    (d / "live.sqlite3").write_bytes(b"")
    (d / "manifest.json").write_text("{}")
    try:
        RS.reconcile(d)
    except RuntimeError as exc:
        assert "finalized" in str(exc)
    else:
        raise AssertionError("must refuse a finalized run")


def test_reconcile_refuses_dangling_request(tmp_path):
    from model_autopsy.backend.live import resume as RS
    d, fac = _mk(tmp_path)
    s = fac()
    inv = _inv(s)
    _ev(s, inv.id, "meta_request", "Meta round 1 (mode=ml)")
    s.close()
    try:
        RS.reconcile(d)
    except RuntimeError as exc:
        assert "dangling" in str(exc)
    else:
        raise AssertionError("must refuse on ambiguous in-flight request")


def test_reconcile_happy_path_rebuilds_budget(tmp_path):
    from model_autopsy.backend.live import resume as RS
    d, fac = _mk(tmp_path)
    s = fac()
    inv = _inv(s)
    _ev(s, inv.id, "meta_request", "Meta round 1 (mode=ml)")
    _ev(s, inv.id, "meta_response", "r",
        {"response_id": "resp_abc123",
         "usage": {"input_tokens": 100, "output_tokens": 10}})
    _ev(s, inv.id, "meta_usage", "Turn usage rollup",
        {"rounds": 1, "api_attempts": 1, "tool_calls_executed": 2,
         "tokens": {"input_tokens": 100, "output_tokens": 10}})
    _ev(s, inv.id, "meta_request", "Meta round 1 (mode=ml)")
    _ev(s, inv.id, "meta_response", "r2",
        {"response_id": "resp_def456",
         "usage": {"input_tokens": 50, "output_tokens": 5}})
    s.close()
    plan = RS.reconcile(d)
    assert plan["response_id"] == "resp_def456"
    assert plan["rounds_done"] == 1
    assert plan["attempts_done"] == 2  # 1 rollup + 1 partial response
    assert plan["input_tokens"] == 150
    assert plan["pid"] == "eval_claim"


def test_reconcile_refuses_terminal(tmp_path):
    from model_autopsy.backend.live import resume as RS
    from model_autopsy.backend import engine
    d, fac = _mk(tmp_path)
    s = fac()
    inv = _inv(s)
    engine.set_status(s, inv, "investigating")
    engine.set_status(s, inv, "finalizing")
    engine.set_status(s, inv, "complete")
    _ev(s, inv.id, "meta_request", "Meta round 1 (mode=ml)")
    _ev(s, inv.id, "meta_response", "r", {"response_id": "resp_x"})
    s.close()
    try:
        RS.reconcile(d)
    except RuntimeError as exc:
        assert "terminal" in str(exc)
    else:
        raise AssertionError("must refuse a terminal investigation")


def test_reconcile_real_run_offline():
    # Read-only reconcile of the actual M6 run: no requests sent.
    # While the run was interrupted this asserted the resume baseline
    # (resp_6ae756f51a…, 1 round, 4 exp, 4 attempts, 13443/4081/1336);
    # now that the resumed run finalized, reconcile must REFUSE it.
    from pathlib import Path
    from model_autopsy.backend.live import resume as RS
    d = Path("model_autopsy/benchmarks/live_runs/live-ae844753edce")
    if not (d / "live.sqlite3").exists():
        return  # run dir absent in this checkout; nothing to verify
    if (d / "manifest.json").exists():
        try:
            RS.reconcile(d)
        except RuntimeError as exc:
            assert "finalized" in str(exc)
        else:
            raise AssertionError("must refuse a finalized run")
        return
    plan = RS.reconcile(d)
    assert plan["run_id"] == "live-ae844753edce"
    assert plan["pid"] == "eval_claim"
    assert plan["response_id"].startswith("resp_6ae756f51a")
    assert plan["rounds_done"] == 1
    assert plan["experiments_done"] == 4
    assert plan["attempts_done"] == 4
    assert plan["input_tokens"] == 13443
    assert plan["cached_tokens"] == 4081
    assert plan["output_tokens"] == 1336
