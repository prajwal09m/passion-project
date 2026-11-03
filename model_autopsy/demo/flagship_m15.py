"""M15 flagship end-to-end demonstration (offline, deterministic).

Loads unfamiliar artifacts, establishes baselines, generates
competing explanations, runs discriminating experiments, pivots on
contradiction, validates a model improvement separately, and emits a
scientific report. No hardcoded conclusions, no sealed truth imports.

Two tracks:
  A. d_combined (site-b over-scoring): pooled metric looks fine, the
     slice-aware probe contradicts the healthy-lead and forces a pivot.
  B. d_null (healthy): must end verified-null, not a false discovery.
"""
from __future__ import annotations


def run_demo(session_factory, max_steps: int = 5) -> dict:
    from ..backend.db import init_db
    from ..backend.research import workflow as WF
    from ..backend.research import diaglab as DG
    from ..backend.research import replay as RP
    init_db()
    tracks = {}
    for art, task, brief in [
        ("model_autopsy/tests/fixture_m10d/d_combined.csv",
         "classification", "Site B conversions look inflated."),
        ("model_autopsy/tests/fixture_m10d/d_null.csv",
         "classification", "Routine check: is this classifier healthy?"),
    ]:
        s = session_factory()
        try:
            out = WF.run(s, art, task, brief, max_steps=max_steps,
                         idempotency=f"flagship-{art.split('/')[-1]}")
            rep = RP.replay_investigation(s, out["behavior"][
                "investigation_id"])
            tracks[art.split("/")[-1]] = {
                "stop": out["behavior"]["stop_rationale"],
                "ran": out["behavior"]["ran_tools"],
                "statuses": out["behavior"]["statuses"],
                "resolution": out["behavior"].get("resolution", {}).get(
                    "diagnosis"),
                "replay_missed": rep["missed_opportunities"],
            }
        finally:
            s.close()
    # Diagnostic self-improvement on the slice-gap blind spot.
    dg = DG.propose("slice-gap-screen",
                    "pooled metrics hide concentrated slice failures",
                    ["slice column observable", "adequate samples"],
                    "per-slice P@K / AUC spread probe")
    ev = DG.evaluate(dg, DG.controlled_cases("slice_gap"))
    rp = DG.reproduce(dg, "model_autopsy/tests/fixture_m10d/"
                          "d_combined.csv")
    dec = DG.decide(dg, ev, rp)
    return {
        "tracks": tracks,
        "diagnostic": {"name": dec["name"], "status": dec["status"],
                       "fp": ev["false_positive_rate"],
                       "fn": ev["false_negative_rate"]},
        "model_improvement": "see /api/lab/model-performance "
                             "(strict held-out gate, measured separately)",
        "reproduction": "deterministic: rerun demo/flagship_m15.py::run_demo",
    }
