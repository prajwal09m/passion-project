"""M14 Phase 1-3 tests (offline, deterministic)."""
import os

os.environ["MODEL_AUTOPSY_TESTING"] = "1"


def _sess():
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm
    from model_autopsy.backend import db as DB
    from model_autopsy.backend import engine
    e = _ce("sqlite:///:memory:")
    DB.Base.metadata.create_all(e)
    s = _sm(bind=e, autoflush=False, expire_on_commit=False)()
    inv = engine.create_investigation(
        s, "ml", "m14", "b",
        {"max_iterations": 3,
         "predictions_path":
         "model_autopsy/tests/fixture_m10b/b_unit_shift.csv"})
    return s, inv


def test_mechanism_discovery_finds_concentration():
    from model_autopsy.backend.research import mechanisms as M
    s, inv = _sess()
    try:
        out = M.discover(
            s, inv, "model_autopsy/tests/fixture_m10b/b_unit_shift.csv")
        assert out["candidates"], out["limits"]
        assert all(c["validation"] == "unvalidated" for c in
                   out["candidates"])
        assert all(c["confidence"] <= 0.45 for c in out["candidates"])
        assert out["unknowns"]["new_diagnostic_needed"] in (True, False)
    finally:
        s.close()


def test_unknown_unknowns_structure():
    from model_autopsy.backend.research import mechanisms as M
    u = M.unknowns([], [], ["zone"], ["error concentrates"])
    assert u["unexplained_behavior"]
    assert u["unmeasured_relationships"]


def test_composed_proposal_validation_and_creativity():
    from model_autopsy.backend.research import composed as C
    from model_autopsy.backend.research import invention as INV
    facts = INV.artifact_facts(
        "model_autopsy/tests/fixture_m10b/b_unit_shift.csv")
    p = C.propose("Does south-zone error persist on held-out data?",
                  ["h1", "h2"], {"h1": "persists", "h2": "vanishes"},
                  {"artifact": "x",
                   "columns_needed": ["zone", "target", "prediction"]},
                  [{"op": "subset"}, {"op": "compare"}],
                  ["mae_by_group"], cost=1)
    v = C.validate(p, facts, 4, sealed_tokens={"south-zone-secret"})
    assert v["valid"], v
    bad = C.validate(dict(p, procedure=[]), facts, 4)
    assert not bad["valid"]
    leak = C.validate(dict(
        p, research_question="probe south-zone-secret mechanism"),
        facts, 4, sealed_tokens={"south-zone-secret"})
    assert not leak["valid"]
    cr = C.creativity(p)
    assert cr["score"] >= 2 and cr["novelty"] == 0


def test_perturbation_isolated_and_map():
    import tempfile
    from model_autopsy.backend.research import perturb as P
    art = "model_autopsy/tests/fixture_m10b/b_unit_shift.csv"
    with tempfile.TemporaryDirectory() as tmp:
        before = open(art, "rb").read()[:100]
        prov = P.perturb_copy(art, "scale", tmp, column="sqft",
                              magnitude=0.2)
        assert prov["prov_hash"]
        assert open(art, "rb").read()[:100] == before
        m = P.measure(art, prov)
        assert "metric_degradation" in m
        mp = P.robustness_map([m])
        assert mp["regions"]["_untested"]["status"] == "untested"
