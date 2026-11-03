"""M8 Workstream A: atomic budget enforcement (offline, no paid traffic)."""
import threading

import pytest


def _budget(**kw):
    from model_autopsy.backend.live import governor as G
    caps = dict(G.CAPS)
    caps.update(kw)
    return G.Budget(caps=caps)


def test_reserve_cap_refused():
    from model_autopsy.backend.live.governor import BudgetExceeded
    b = _budget(experiments=1)
    tok = b.reserve("experiments", 1)
    assert tok
    with pytest.raises(BudgetExceeded):
        b.reserve("experiments", 1)
    assert b.settle(tok, 1) is True
    with pytest.raises(BudgetExceeded):
        b.reserve("experiments", 1)


def test_concurrent_last_slot_single_winner():
    from model_autopsy.backend.live.governor import BudgetExceeded
    b = _budget(attempts=1)
    wins, losses = [], []

    def worker():
        try:
            wins.append(b.reserve("attempts", 1))
        except BudgetExceeded:
            losses.append(1)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(wins) == 1 and len(losses) == 7
    assert b.settle(wins[0], 1) is True


def test_duplicate_settle_idempotent():
    b = _budget(experiments=6)
    tok = b.reserve("experiments", 1)
    assert b.settle(tok, 1) is True
    assert b.settle(tok, 1) is False  # duplicate: no double counting
    assert b.experiments_used == 1


def test_release_and_reuse():
    b = _budget(experiments=1)
    tok = b.reserve("experiments", 1, note="dedup reuse?")
    assert b.release(tok, "dedup reuse: no new execution") is True
    assert b.release(tok, "again") is False
    tok2 = b.reserve("experiments", 1)
    assert b.settle(tok2, 1) is True
    assert b.experiments_used == 1


def test_reconcile_counts_orphans():
    from model_autopsy.backend.live import governor as G
    b = _budget(experiments=6, attempts=12)
    b.reserve("experiments", 2, note="crashed after reserve")
    b.reserve("attempts", 1, note="crashed after dispatch")
    state = b.to_state()
    r = G.Budget.reconcile(state, [], conservative_extra_attempts=0)
    # Open holds count as spent — never assumed free.
    assert r.experiments_used == 2
    assert r.attempts_used == 1


def test_reconcile_malformed_refuses():
    from model_autopsy.backend.live import governor as G
    with pytest.raises(ValueError):
        G.Budget.reconcile({"caps": {}, "rounds_used": -1,
                            "experiments_used": 0, "attempts_used": 0,
                            "input_tokens": 0, "cached_tokens": 0,
                            "output_tokens": 0}, [])
    with pytest.raises(ValueError):
        G.Budget.reconcile({"caps": {}}, [{"kind": "bogus", "amount": 1,
                                           "status": "open"}])
    with pytest.raises(ValueError):
        G.Budget.reconcile(None, [])


def test_missing_usage_never_reduces():
    b = _budget()
    b.settle_usage(input_tokens=100, cached_tokens=10, output_tokens=5)
    b.settle_usage()  # missing usage: no-op, never negative
    b.settle_usage(input_tokens=None, cached_tokens=-5, output_tokens=0)
    assert (b.input_tokens, b.cached_tokens, b.output_tokens) == (100, 10, 5)


def test_unknown_kind_rejected():
    b = _budget()
    with pytest.raises(ValueError):
        b.reserve("bandwidth", 1)
    with pytest.raises(ValueError):
        b.reserve("attempts", 0)


def _scripted_turn(calls_first=(), rid="resp_1"):
    import json
    out = []
    for call_id, name, args in calls_first:
        out.append({"type": "function_call", "call_id": call_id,
                    "name": name, "arguments": json.dumps(args)})
    if not out:
        out.append({"type": "message", "content": [
            {"type": "output_text", "text": "done, no further tools"}]})
    return {"id": rid, "status": "completed", "output": out,
            "usage": {"input_tokens": 100, "output_tokens": 50,
                      "total_tokens": 150}}


# Live-run safety simulation: exact configured caps, scripted provider,
# real driver path — proves the experiment cap cannot be exceeded and no
# duplicate run can start on the same directory.
def test_driver_dry_run_respects_experiment_cap(tmp_path, monkeypatch):
    import json
    from model_autopsy.backend import config as C
    from model_autopsy.backend.live import governor as G
    from model_autopsy.backend.meta_api import client as MC
    monkeypatch.setenv("MODEL_API_KEY", "dummy-test-key")
    monkeypatch.setattr(G, "CAPS", {**G.CAPS, "experiments": 1,
                                    "rounds": 3, "attempts": 12,
                                    "tokens": 50_000, "cost_usd": 0.40})
    TURBINE = "model_autopsy/tests/fixture_eval/investigator/turbine_output.csv"
    script = [
        _scripted_turn([("c1", "propose_hypothesis", {
            "text": "Level shift causes the miss xxxxxxxxxxxxxxxxxxxx"}),
            ("c2", "data_quality_profile",
             {"predictions_path": TURBINE})], rid="r1"),
        _scripted_turn(rid="r2"),
        _scripted_turn(rid="r3"),  # summary repair (invalid text)
    ]
    seen = []

    def fake(**kw):
        seen.append(kw)
        return script[min(len(seen) - 1, len(script) - 1)]
    monkeypatch.setattr(MC, "create_response", fake)
    from model_autopsy.backend.live import driver as D
    rec = D.run_live_investigation("eval_turbine", tmp_path, max_rounds=1)
    assert rec["status"] == "completed"
    assert rec["budget"]["experiments"] == [1, 1], rec["budget"]
    assert rec["budget"]["attempts"][0] <= 12
    manifest = tmp_path / rec["run_id"] / "manifest.json"
    assert manifest.exists()
    body = json.loads(manifest.read_text())
    assert body["run_id"] == rec["run_id"]
    # No duplicate run may start on the same directory.
    import uuid
    with pytest.raises(RuntimeError):
        D.run_live_investigation("eval_turbine", tmp_path, max_rounds=1,
                                 run_id=rec["run_id"])
    assert len(seen) <= 12  # hard attempt ceiling holds on the wire count
