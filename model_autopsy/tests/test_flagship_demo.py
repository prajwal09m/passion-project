"""Integrated flagship demonstration gate (offline)."""


def test_flagship_demo_single_multi_persist(tmp_path):
    from model_autopsy.backend.db import SessionLocal
    from model_autopsy.demo import flagship_m12 as F
    import subprocess
    subprocess.run(["py", "model_autopsy/tests/fixture_demo/generate.py"],
                   check=True)
    out = F.run_demo(SessionLocal, lab_base=str(tmp_path / "lab"))
    assert out["single"]["score"] >= 0.5, out["single"]
    assert out["multi"]["score"] >= out["single"]["score"], out
    assert out["multi"]["judge_verdicts"] > 0
    assert out["persistence"]["no_duplicate"], out["persistence"]
    assert out["persistence"]["checkpoints"] == 1
