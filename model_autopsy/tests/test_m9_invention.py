"""M9 Workstream 4: experiment invention."""
import pytest

from model_autopsy.backend.db import SessionLocal, init_db
from model_autopsy.backend.research import invention as INV

CREDIT = "model_autopsy/tests/fixture_eval/investigator/credit_default.csv"
RENT = "model_autopsy/tests/fixture_eval/investigator/rent_estimates.csv"

Q = {"id": "subgroup-performance:0", "family": "subgroup-performance",
     "text": "Does performance differ across regions?"}
H = [{"id": "h1", "text": "region W underperforms"},
     {"id": "h2", "text": "uniform miscalibration"}]


def test_facts_come_from_the_artifact():
    f = INV.artifact_facts(CREDIT)
    assert f["readable"] is True
    assert f["segments"] == ["region"]
    assert f["score_col"] == "score" and f["label_col"] == "label"
    assert f["temporal_col"] is None
    bad = INV.artifact_facts("no/such/file.csv")
    assert bad["readable"] is False


def test_propose_invents_segmented_spec():
    f = INV.artifact_facts(CREDIT)
    specs = INV.propose(Q, H, f, [], {"experiments": 5})
    assert specs, "must invent at least one experiment"
    top = specs[0]
    assert top["spec_version"] == "m9-spec-v1"
    assert top["args"].get("split_by") == "region"
    assert len(top["hypotheses_distinguished"]) == 2
    assert top["interpretation_rule"]
    assert "inconclusive" in top["interpretation_rule"]


def test_propose_skips_duplicates():
    f = INV.artifact_facts(CREDIT)
    ran = [{"tool": "classification_metrics",
            "args": {"predictions_path": CREDIT, "score_column": "score",
                     "split_by": "region"}}]
    specs = INV.propose(Q, H, f, ran, {"experiments": 5})
    sigs = {(s["tool"], tuple(sorted(s["args"].items()))) for s in specs}
    assert ("classification_metrics",
            tuple(sorted(ran[0]["args"].items()))) not in sigs


def test_validate_refuses_bad_specs():
    f = INV.artifact_facts(CREDIT)
    ok_spec = {"spec_id": "s1", "tool": "classification_metrics",
               "args": {"predictions_path": CREDIT,
                        "score_column": "score", "split_by": "region"}}
    assert INV.validate(ok_spec, f, [], {"experiments": 2})["valid"]
    bad_col = dict(ok_spec, args={**ok_spec["args"],
                                  "split_by": "province"})
    v = INV.validate(bad_col, f, [], {"experiments": 2})
    assert not v["valid"] and any("province" in e for e in v["errors"])
    dup = INV.validate(ok_spec, f, [ok_spec], {"experiments": 2})
    assert not dup["valid"] and any("duplicate" in e for e in dup["errors"])
    broke = INV.validate(ok_spec, f, [], {"experiments": 0})
    assert not broke["valid"] and any("budget" in e for e in broke["errors"])
    unknown = INV.validate({"spec_id": "s9", "tool": "telepathy",
                            "args": {}}, f, [], {"experiments": 2})
    assert not unknown["valid"]


def test_execute_and_interpret_end_to_end():
    import os
    os.environ["MODEL_AUTOPSY_TESTING"] = "1"
    init_db()
    s = SessionLocal()
    try:
        from model_autopsy.backend import engine
        inv = engine.create_investigation(s, "ml", "t", "q",
                                          {"max_tool_calls": 6})
        f = INV.artifact_facts(CREDIT)
        specs = INV.propose(Q, H, f, [], {"experiments": 6})
        spec = next(x for x in specs
                    if x["tool"] == "classification_metrics")
        assert INV.validate(spec, f, [], {"experiments": 6})["valid"]
        out = INV.execute(s, inv, spec)
        assert out["ok"], out
        from model_autopsy.backend.db import Action
        act = s.get(Action, out["action_id"])
        interp = INV.interpret(spec, act.result)
        # Credit fixture: region W ~0.54 vs ~1.0 elsewhere.
        assert interp["verdict"] == "segment", interp
        assert "spread" in interp["detail"]
    finally:
        s.close()


def test_interpret_uniform_case():
    spec = {"tool": "regression_metrics", "hypotheses_distinguished": [],
            "interpretation_rule": "r"}
    out = INV.interpret(spec, {"mae_by_group": {"a": 10.0, "b": 10.5}})
    assert out["verdict"] == "uniform"
    out2 = INV.interpret(spec, {"mae_by_group": {"a": 10.0}})
    assert out2["verdict"] == "inconclusive"
