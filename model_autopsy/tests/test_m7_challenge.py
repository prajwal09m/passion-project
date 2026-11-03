"""M7 challenge harness test (offline, real fixtures, no paid traffic)."""
import os

os.environ["MODEL_AUTOPSY_TESTING"] = "1"


def test_closed_loop_behavioral_checks():
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm
    from model_autopsy.backend import db as DB
    e = _ce("sqlite:///:memory:")
    DB.Base.metadata.create_all(e)
    fac = _sm(bind=e, autoflush=False, expire_on_commit=False)
    from model_autopsy.backend.eval import m7_challenge as M7
    out = M7.evaluate_all(fac)
    assert out["checks"]["transitions_occur"]
    assert out["checks"]["refs_valid"]
    assert out["checks"]["no_duplicates"]
    assert out["checks"]["budget_ok"]
    assert out["checks"]["rationales"]
    assert len(out["scenarios"]) == 6
