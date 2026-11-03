"""M15 Phase 5/8/10/12 tests (offline, deterministic)."""


def _session():
    from model_autopsy.backend.db import SessionLocal, init_db
    init_db()
    return SessionLocal()


def test_replay_roundtrip():
    from model_autopsy.backend.research import autonomous as AU
    from model_autopsy.backend.research import replay as RP
    s = _session()
    try:
        beh = AU.run_autonomous(
            s, "model_autopsy/tests/fixture_m10d/d_null.csv",
            "classification", "replay check", max_steps=2,
            investigation_title="replay-t")
        r = RP.replay_investigation(s, beh["investigation_id"])
        assert r["replayed"]["n_actions"] >= 0
        assert "diagnosis" in r
        p = RP.parity_report([r])
        assert p["n_replays"] == 1 and "fix" in p["answers"]
    finally:
        s.close()


def test_runner_d_all_four():
    from model_autopsy.backend.m10 import runner_d as RD
    from model_autopsy.backend.db import SessionLocal
    out = RD.run_all(SessionLocal, max_steps=2)
    assert len(out["scenarios"]) == 4


def test_diaglab_admit_or_reject_with_reasons():
    from model_autopsy.backend.research import diaglab as DG
    d = DG.propose("t-probe", "pooled hides slice", ["slice col"], "probe")
    ev = DG.evaluate(d, DG.controlled_cases("slice_gap"))
    rp = DG.reproduce(d, "model_autopsy/tests/fixture_m10d/d_combined.csv")
    dec = DG.decide(d, ev, rp)
    assert dec["status"] in ("admitted", "rejected")
    assert "false_positive_rate" in ev


def test_workflow_checkpoints_idempotent():
    from model_autopsy.backend.research import workflow as WF
    s = _session()
    try:
        out = WF.run(s, "model_autopsy/tests/fixture_m10d/d_null.csv",
                     "classification", "wf check", max_steps=2)
        assert set(out["stages"]) == {"recon", "baseline", "hypotheses",
                                      "experiments", "challenge",
                                      "improvement", "verify", "report",
                                      "memory"}
        assert out["checkpoints"]["recon"]["readable"] is True
    finally:
        s.close()


def test_flagship_m15_two_tracks():
    from model_autopsy.demo import flagship_m15 as F
    from model_autopsy.backend.db import SessionLocal
    out = F.run_demo(SessionLocal, max_steps=2)
    assert "d_combined.csv" in out["tracks"]
    assert "d_null.csv" in out["tracks"]
    assert out["diagnostic"]["status"] in ("admitted", "rejected")
