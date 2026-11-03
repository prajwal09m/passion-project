"""M10 independent-validation tests (offline, deterministic)."""
from model_autopsy.backend.db import SessionLocal, init_db


def test_unseen_env_sealed():
    from model_autopsy.backend.m10 import sealed as S
    audit = S.audit_unseen_env()
    assert audit["ok"], audit["violations"]


def test_investigator_path_never_touches_sealed():
    import subprocess
    import sys
    code = ("import model_autopsy.backend.m10.runner as R,"
            "import model_autopsy.backend.m10.scenarios as S,"
            "import model_autopsy.backend.m10.evaluator as E,"
            "import model_autopsy.backend.m10.stats as T,"
            "import model_autopsy.backend.m10.replication as RP,"
            "import model_autopsy.backend.m10.cross_framework as C")
    mods = ("scenarios", "sealed")
    # The investigator-side modules (scenarios, runner) must not import
    # the sealed module; enforce by source inspection.
    import pathlib
    import re
    for mod in ("scenarios", "runner"):
        src = pathlib.Path(
            f"model_autopsy/backend/m10/{mod}.py").read_text()
        assert not re.search(r"^\s*(from|import)\s+\S*sealed",
                             src, re.M), mod


def test_stats_helpers_honest_limits():
    from model_autopsy.backend.m10 import stats as ST
    assert ST.mean_ci([1.0])["ok"] is False
    import random as _r
    _rng = _r.Random(5)
    g = ST.subgroup_gap([1.0 + _rng.gauss(0, 0.1) for _ in range(40)],
                         [2.0 + _rng.gauss(0, 0.1) for _ in range(40)],
                         "A", "B")
    assert g["ok"] and g["magnitude"] == "large"
    assert "not a causal" in g["interpretation"]


def test_cross_framework_reports_honestly():
    from model_autopsy.backend.m10 import cross_framework as CF
    out = CF.validate_all()
    assert out["sklearn"]["available"] is True
    assert out["torch"]["available"] is True
    assert all(v["ok"] for v in out["sklearn"]["diagnostics"].values())
    assert out["torch"]["diagnostics"]["ok"] is True
    names = {o["framework"] for o in out["other"]}
    assert {"tensorflow", "huggingface"} <= names


def test_unseen_discovery_end_to_end():
    from model_autopsy.backend.m10 import runner as R
    from model_autopsy.backend.m10 import evaluator as E
    from model_autopsy.backend.m10 import sealed as S
    init_db()
    truth = S.load_truth()
    grades = {}
    for sid in ("m10_ward_gap", "m10_proxy_signal", "m10_steady",
                "m10_sparse"):
        s = SessionLocal()
        try:
            beh = R.run_scenario(sid, s)
            beh["investigation_id"] = _inv_id(s, beh)
            g = E.grade(sid, beh, truth[sid], s)
            grades[sid] = g["grade"]
        finally:
            s.close()
    # Honest bar: subgroup + leakage discovered, clean/spare uncommitted.
    assert grades["m10_ward_gap"] in ("discovered", "partial"), grades
    assert grades["m10_proxy_signal"] in ("discovered", "partial"), grades
    assert grades["m10_steady"] == "inconclusive-correct", grades
    assert grades["m10_sparse"] == "inconclusive-correct", grades


def _inv_id(session, behavior):
    # The behavior carries its own investigation_id (added M10-era).
    # Never re-derive via created_at ordering: ties under rapid
    # successive runs return the wrong investigation.
    return behavior.get("investigation_id")


def test_replication_uses_independent_probe():
    from model_autopsy.backend.m10 import runner as R
    from model_autopsy.backend.m10 import replication as RP
    init_db()
    s = SessionLocal()
    try:
        beh = R.run_scenario("m10_ward_gap", s)
        inv_id = _inv_id(s, beh)
        from model_autopsy.backend.db import Investigation, Hypothesis
        inv = s.get(Investigation, inv_id)
        hyps = s.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv_id).all()
        target = next((h for h in hyps if "ward" in h.text.lower()
                       or "segment" in h.text.lower()
                       or "subgroup" in h.text.lower()), hyps[0])
        ran = [{"tool": t} for t in beh.get("specs_executed", [])]
        rep = RP.replicate(s, inv, target.id, "subgroup",
                           "model_autopsy/tests/fixture_m10/"
                           "m10_ward_gap.csv", ran)
        assert rep["ok"], rep
        assert rep["tool"] not in beh.get("specs_executed", [])
    finally:
        s.close()
