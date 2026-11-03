"""Integrated flagship demonstration (offline).

Unfamiliar ranking project, unknown issue. Single-investigator
baseline vs M11 team on equivalent inputs; M12 persistence with a
simulated mid-run interruption and resume; independent evaluator
scores both with evidence requirements.
"""
from __future__ import annotations

ARTIFACT = "model_autopsy/tests/fixture_demo/flagship_rank.csv"
BRIEF = "Prime-slice results look thin; pooled metrics look fine."
TRUTH = {"mechanism": "prime-slice under-service with hot scores",
         "family": "subgroup", "grade": "discovered",
         "key_tool": "regression_metrics"}


def run_demo(session_factory, lab_base: str = "model_autopsy/.lab",
             max_steps: int = 6) -> dict:
    from ..backend.db import init_db
    from ..backend.m10 import evaluator as E
    from ..backend.m10 import runner as R
    from ..backend.m11 import team as T
    from ..backend.m12 import projects as P
    from ..backend.m12 import memory as M
    init_db()

    # 1. Single-investigator baseline.
    s = session_factory()
    try:
        single = R.run_scenario("flagship_rank", s) \
            if False else _run_single(s, max_steps)
        g1 = E.grade("flagship_rank", single, TRUTH, s)
    finally:
        s.close()

    # 2. Multi-agent team on equivalent inputs.
    s = session_factory()
    try:
        multi = T.investigate(
            s, "flagship_rank", ARTIFACT, "ranking", BRIEF,
            max_steps=max_steps)
        g2 = E.grade("flagship_rank", multi["baseline"], TRUTH, s)
        n_dis = len(multi["team"]["disagreements"])
        judge = multi["team"]["judge"]["verdicts"]
    finally:
        s.close()

    # 3. Persistence: project survives a simulated interruption.
    proj = P.create(lab_base, "flagship: prime-slice ranker",
                    budget={"tool_calls": 10})
    P.checkpoint(lab_base, proj["id"], {"phase": "baseline-done"})
    # Simulated crash: reload from disk, resume, retried write.
    reloaded = P.load(lab_base, proj["id"])
    P.record_experiment(lab_base, proj["id"], "regression_metrics",
                        {"predictions_path": ARTIFACT},
                        "flagship-k1", {"ok": True})
    P.record_experiment(lab_base, proj["id"], "regression_metrics",
                        {"predictions_path": ARTIFACT},
                        "flagship-k1", {"ok": True})  # retried resume
    resumed = P.load(lab_base, proj["id"])
    M.remember(lab_base, "finding", TRUTH["mechanism"], proj["id"],
               "flagship-run")
    return {
        "single": {"grade": g1["grade"], "score": g1["score"],
                   "detail": g1["detail"]},
        "multi": {"grade": g2["grade"], "score": g2["score"],
                  "detail": g2["detail"],
                  "disagreements": n_dis,
                  "judge_verdicts": len(judge)},
        "persistence": {
            "checkpoints": len(resumed["checkpoints"]),
            "experiments": len(resumed["experiments"]),
            "tool_calls": resumed["resource_usage"]["tool_calls"],
            "no_duplicate": len(resumed["experiments"]) == 1
            and resumed["resource_usage"]["tool_calls"] == 1},
        "project_id": proj["id"]}


def _run_single(session, max_steps: int) -> dict:
    from ..backend.research import autonomous as AU
    return AU.run_autonomous(
        session, ARTIFACT, "ranking", BRIEF, max_steps=max_steps,
        investigation_title="flagship single baseline")
