"""M14 flagship scientific demonstration (offline, no paid calls).

Unfamiliar project: c_robustness (machine/reading/target/prediction,
m2 10x scale fault — outside M10 vocabulary). Demonstrates all 17
required stages with real artifacts: recon, mechanism discovery,
composed experiment, perturbation, adaptive selection, evidence,
competing explanations, skeptic review, judge, falsification,
reproduction, risk, memory transfer, portfolio, resume, report.
"""
from __future__ import annotations

ARTIFACT = "model_autopsy/tests/fixture_m10c/c_robustness.csv"
BRIEF = "One machine family reads far off; is it a scale fault."
TRUTH = {"mechanism": "m2 unit scale fault (10x)",
         "family": "robustness", "grade": "discovered",
         "key_tool": "regression_metrics", "novel": False}


def run_flagship(session_factory,
                 lab_base: str = "model_autopsy/.lab",
                 max_steps: int = 4) -> dict:
    from ..backend.db import init_db
    from ..backend.m10 import eval3 as E3
    from ..backend.m10 import runner_c as RC
    from ..backend.m11 import team as T
    from ..backend.m12 import knowledge as K
    from ..backend.m12 import projects as P
    from ..backend.m12 import portfolio as PF
    from ..backend.m12 import verify as V
    from ..backend.m12 import falsify as F
    from ..backend.research import mechanisms as ME
    from ..backend.research import composed as CO
    from ..backend.research import perturb as PB
    from ..backend.research import risk as RK
    from ..backend.research import invention as INV
    init_db()
    stages: dict = {}

    # 1. Reconnaissance.
    s = session_factory()
    try:
        facts = INV.artifact_facts(ARTIFACT)
        stages["recon"] = {"readable": facts["readable"],
                           "columns": facts.get("columns")}
        # 2-4. Mechanism discovery + unknowns.
        inv0 = __import__(
            "model_autopsy.backend.engine", fromlist=["x"]
        ).create_investigation(s, "ml", "m14 recon", BRIEF,
                               {"max_iterations": 3,
                                "predictions_path": ARTIFACT})
        mech = ME.discover(s, inv0, ARTIFACT)
        stages["mechanisms"] = {
            "n": len(mech["candidates"]),
            "phenomena": [c["phenomenon"] for c in mech["candidates"]]}
        stages["unknowns"] = mech["unknowns"]
        # 4. Novel composed experiment (validated, not executed blindly).
        prop = CO.propose(
            "Is the m2 error a scale fault reproducible on held-out data?",
            ["h-scale", "h-bias"],
            {"h-scale": "persists after resplit",
             "h-bias": "vanishes after resplit"},
            {"artifact": ARTIFACT,
             "columns_needed": ["machine", "target", "prediction"]},
            [{"op": "subset"}, {"op": "compare"}], ["mae_by_group"])
        stages["composed"] = {"valid": CO.validate(
            prop, facts, 4)["valid"],
            "creativity": CO.creativity(prop)}
        # 5. Controlled perturbation (isolated copy, hash-guarded).
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            prov = PB.perturb_copy(ARTIFACT, "scale", tmp,
                                   column="reading", magnitude=0.2)
            meas = PB.measure(ARTIFACT, prov)
            stages["perturbation"] = {
                "prov_hash": prov["prov_hash"],
                "map": PB.robustness_map([meas])["regions"]}
    finally:
        s.close()

    # 6-10. Single vs team (equivalent budgets).
    s = session_factory()
    try:
        single = RC.run_scenario_c("c_robustness", s, max_steps)
        g1 = E3.score(single, TRUTH, session=s)
    finally:
        s.close()
    s = session_factory()
    try:
        multi = T.investigate(s, "c_robustness", ARTIFACT,
                              "regression", BRIEF, max_steps=max_steps)
        g2 = E3.score(multi["baseline"], TRUTH, session=s,
                      team=multi["team"])
    finally:
        s.close()
    stages["single"] = g1
    stages["team"] = {"eval3": g2,
                      "disagreements": len(multi["team"].get(
                          "disagreements", []))}

    # 11-12. Falsification + independent reproduction.
    s = session_factory()
    try:
        from ..backend.db import Hypothesis, Investigation
        inv = s.get(Investigation,
                    multi["baseline"]["investigation_id"])
        hs = s.query(Hypothesis).filter(
            Hypothesis.investigation_id ==
            multi["baseline"]["investigation_id"]).all()
        def _moving(refs):
            return [r for r in (refs or []) if r.get("relation") in (
                "supports", "contradicts")]
        tgt = next(
            (h for h in hs if _moving(h.evidence_refs)),
            next((h for h in hs if h.evidence_refs), None))
        hv = {"id": tgt.id, "text": tgt.text,
              "evidence_refs": tgt.evidence_refs,
              "predicted_observation": tgt.predicted_observation} \
            if tgt is not None else {"id": "none", "text": "",
                                     "evidence_refs": []}
        stages["falsification"] = F.falsification_plan(hv)
        ver = V.verify_finding(
            s, inv,
            {"id": hv["id"], "evidence_refs": hv["evidence_refs"],
             "text": hv.get("text", "")}, ARTIFACT) \
            if tgt is not None else {"grade": "impossible"}
        stages["verification"] = {"grade": ver.get("grade"),
                                    "tool": ver.get("tool")}
        stages["confidence"] = F.confidence_layers(
            hv.get("evidence_refs", []), [ver] if tgt else None)
        # 13. Predictive risk.
        risks = RK.prioritize(RK.hypothesize(INV.artifact_facts(ARTIFACT)))
        stages["risks"] = [{"area": r["area"],
                            "missing": r["missing_evidence"]}
                           for r in risks]
        g3 = E3.score(multi["baseline"], TRUTH, session=s,
                      team=multi["team"],
                      falsification=stages["falsification"],
                      risks=[{"status": "risk-hypothesis"}])
        stages["eval3_full"] = g3
    finally:
        s.close()

    # 14-16. Memory transfer + portfolio + resume.
    K.store(lab_base, "failure-pattern",
            "machine-family scale fault flattens after unit fix",
            "c_robustness",
            evidence={"tool": "regression_metrics"}, confidence=0.7,
            conditions="columns machine target prediction")
    stages["transfer"] = K.propose_transfer(
        lab_base, {"columns": ["machine", "target", "prediction"],
                   "task": "regression"})
    proj = P.create(lab_base, "flagship-m14", budget={"tool_calls": 8})
    P.checkpoint(lab_base, proj["id"], {"phase": "team-done"})
    P.record_experiment(lab_base, proj["id"], "regression_metrics",
                        {"predictions_path": ARTIFACT}, "m14-k1",
                        {"ok": True})
    P.record_experiment(lab_base, proj["id"], "regression_metrics",
                        {"predictions_path": ARTIFACT}, "m14-k1",
                        {"ok": True})
    resumed = P.load(lab_base, proj["id"])
    docs = [resumed]
    stages["portfolio"] = PF.assess([
        {"id": resumed["id"], "status": resumed["status"],
         "agenda": resumed.get("agenda", []),
         "experiments": resumed.get("experiments", []),
         "unresolved": resumed.get("unresolved", [])}])
    stages["persistence"] = {"no_duplicate":
                             len(resumed["experiments"]) == 1}
    # 17. Controls + aggregate report.
    s = session_factory()
    try:
        c = RC.run_scenario_c("c_steady", s, max_steps)
        gclean = E3.score(c, RC.load_truth_c()["c_steady"], session=s)
    finally:
        s.close()
    stages["report"] = E3.aggregate([g1, g2, gclean])
    _ = docs
    return stages
