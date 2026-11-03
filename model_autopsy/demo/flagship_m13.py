"""M13 flagship demonstration (offline, no paid calls).

Unfamiliar project (b_unit_shift: south-zone unit inconsistency,
columns zone/sqft/target/prediction — outside M10 vocabulary).
Compares single-agent vs team vs team-no-skeptic vs team-no-judge
under equivalent budgets, plus memory-transfer vs no-transfer,
clean/inconclusive controls, interruption/resume, and eval2
multi-dimension scoring with novelty report.
"""
from __future__ import annotations

ARTIFACT = "model_autopsy/tests/fixture_m10b/b_unit_shift.csv"
BRIEF = "Southern estimates look wrong after a vendor change."
TRUTH = {"mechanism": "south-zone unit inconsistency",
         "family": "subgroup", "grade": "discovered",
         "key_tool": "regression_metrics"}
CLEAN = {"mechanism": "none (healthy)", "family": "clean",
         "grade": "correct-null", "key_tool": "none"}
CLEAN_ART = "model_autopsy/tests/fixture_m10b/b_steady.csv"
THIN_ART = "model_autopsy/tests/fixture_m10b/b_thin.csv"
THIN_TRUTH = {"mechanism": "unknown (n too small)",
              "family": "thin", "grade": "inconclusive",
              "key_tool": "none"}


def run_flagship(session_factory, lab_base: str = "model_autopsy/.lab",
                 max_steps: int = 6) -> dict:
    from ..backend.db import init_db
    from ..backend.m10 import eval2 as E2
    from ..backend.m10 import runner_b as RB
    from ..backend.m11 import team as T
    from ..backend.m12 import knowledge as K
    from ..backend.m12 import projects as P
    from ..backend.m12 import verify as V
    init_db()

    def _single(art, brief, truth):
        s = session_factory()
        try:
            b = RB.run_scenario_b("b_unit_shift", s, max_steps) \
                if art == ARTIFACT else _run_art(s, art, brief)
            g = E2.score(b, truth, session=s)
            nov = E2.novelty(["zone", "sqft", "target", "prediction"],
                             truth)
            return {"behavior": _slim(b), "eval2": g, "novelty": nov}
        finally:
            s.close()

    # 1. single-agent on the unfamiliar project.
    single = _single(ARTIFACT, BRIEF, TRUTH)
    # 2-4. team ablations, equivalent budgets.
    ablations = {}
    for name, kw in (("full", {}),
                     ("no-skeptic", {"skeptic": False}),
                     ("no-judge", {"judge": False})):
        s = session_factory()
        try:
            multi = T.investigate(s, "b_unit_shift", ARTIFACT,
                                  "regression", BRIEF,
                                  max_steps=max_steps, **kw)
            g = E2.score(multi["baseline"], TRUTH, session=s,
                         team=multi["team"])
            ablations[name] = {
                "eval2": g,
                "disagreements": len(multi["team"].get(
                    "disagreements", [])),
                "judge_verdicts": len((multi["team"].get("judge")
                                       or {}).get("verdicts", []))}
        finally:
            s.close()
    # 5. verification on the full-team run.
    s = session_factory()
    try:
        multi = T.investigate(s, "b_unit_shift", ARTIFACT,
                              "regression", BRIEF, max_steps=max_steps)
        from ..backend.db import Hypothesis
        hs = s.query(Hypothesis).filter(
            Hypothesis.investigation_id ==
            multi["baseline"]["investigation_id"]).all()
        target = next((h for h in hs if h.evidence_refs), None)
        ver = V.verify_finding(
            s, None,
            {"id": target.id, "evidence_refs": target.evidence_refs,
             "text": target.text} if target else
            {"id": "none", "evidence_refs": []}, ARTIFACT) \
            if target is not None else {"grade": "impossible"}
    finally:
        s.close()
    # 6. memory transfer: store + propose on a new project profile.
    K.store(lab_base, "confounder",
            "zone mix shifts pooled fit; segment before concluding",
            "b_unit_shift",
            evidence={"tool": "regression_metrics"}, confidence=0.7,
            conditions="columns zone target prediction")
    transfer = K.propose_transfer(
        lab_base, {"columns": ["zone", "target", "prediction"],
                   "task": "regression"})
    # 7. controls.
    clean = _single(CLEAN_ART, "Routine check.", CLEAN)
    thin = _single(THIN_ART, "Tiny pilot.", THIN_TRUTH)
    # 8. interruption/resume without duplicate execution.
    proj = P.create(lab_base, "flagship-m13", budget={"tool_calls": 8})
    P.checkpoint(lab_base, proj["id"], {"phase": "team-done"})
    P.record_experiment(lab_base, proj["id"], "regression_metrics",
                        {"predictions_path": ARTIFACT}, "m13-k1",
                        {"ok": True})
    P.record_experiment(lab_base, proj["id"], "regression_metrics",
                        {"predictions_path": ARTIFACT}, "m13-k1",
                        {"ok": True})
    resumed = P.load(lab_base, proj["id"])
    agg = E2.aggregate([single["eval2"]] + [v["eval2"] for v in
                                            ablations.values()])
    return {"single": single, "ablations": ablations,
            "verification": {"grade": ver.get("grade")},
            "transfer_candidates": len(transfer),
            "clean": clean["eval2"], "thin": thin["eval2"],
            "persistence": {
                "no_duplicate":
                    len(resumed["experiments"]) == 1},
            "aggregate": agg}


def _run_art(session, art, brief):
    from ..backend.research import autonomous as AU
    return AU.run_autonomous(session, art, "classification", brief,
                             max_steps=6,
                             investigation_title="flagship control")


def _slim(b: dict) -> dict:
    return {"scenario": b.get("scenario"),
            "specs_executed": b.get("specs_executed"),
            "tool_calls": b.get("tool_calls"),
            "statuses": b.get("statuses")}
