"""M10 independent replication (offline).

A replication re-tests a claimed mechanism with a DIFFERENT tool
than the original measurement, preserving the original evidence and
recording its own provenance. Same tool + same args never counts.
"""
from __future__ import annotations

# Independent second probe per mechanism family (different tool,
# same question). The replication must discriminate, not repeat.
SECOND_PROBE = {
    "subgroup": ("residual_feature_dependence", "error tracks an input"),
    "leakage": ("calibration_and_error_analysis",
                "skill survives reliability check"),
    "calibration": ("regression_metrics",
                    "headline fit vs reliability gap"),
    "misspecification": ("temporal_changepoint_scan",
                         "abrupt break vs persistent lag"),
    "drift": ("residual_time_analysis",
              "recent-shift vs persistent pattern"),
    "ranking": ("slice_gap_significance",
                "gap survives a permutation null"),
}


def replicate(session, inv, hypothesis_id: str, family: str,
              artifact: str, ran: list[dict]) -> dict:
    """Run one independent replication probe. Returns a report."""
    from .. import engine
    from ..db import record_event
    from ..causal import linker as LK
    if family not in SECOND_PROBE:
        return {"ok": False, "reason": f"no replication probe for "
                                       f"{family}"}
    tool, question = SECOND_PROBE[family]
    if any(r.get("tool") == tool for r in ran):
        return {"ok": False, "reason": f"{tool} already measured; "
                                       f"replication must be independent"}
    from ..research import invention as INV
    facts = INV.artifact_facts(artifact)
    cols = facts.get("columns") or []
    args: dict = {"predictions_path": artifact}
    if family != "ranking":
        if "target" not in cols and "label" in cols:
            args["target_column"] = "label"
        if "prediction" not in cols and facts.get("score_col"):
            args["prediction_column"] = facts["score_col"]
    if family == "ranking":
        # Same finding, inferential method: the permutation null tests
        # gap-is-real vs gap-is-noise at the descriptive operating point.
        segs = facts.get("segments") or []
        if segs:
            args["slice_column"] = segs[0]
        if facts.get("score_col"):
            args["score_column"] = facts["score_col"]
        if facts.get("label_col") and facts["label_col"] != "label":
            args["labels"] = facts["label_col"]
        args["k_frac"] = 0.1
        args["n_perm"] = 2000
        args["seed"] = 7
    try:
        out = engine.run_tool(session, inv, tool, dict(args),
                              source_meta=True)
    except Exception as exc:
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    if not out.get("ok"):
        return {"ok": False, "reason": out.get("error", "tool failed")}
    from ..db import Action
    act = session.get(Action, out.get("action_id"))
    applied = LK.link_tool_result(session, inv, act) if act else []
    record_event(session, inv.id, "replication",
                 f"Independent replication via {tool}: {question}",
                 payload={"hypothesis_id": hypothesis_id,
                          "tool": tool, "question": question,
                          "action_id": out.get("action_id"),
                          "links_applied": len(applied)})
    session.commit()
    return {"ok": True, "tool": tool, "question": question,
            "links_applied": len(applied),
            "action_id": out.get("action_id")}
