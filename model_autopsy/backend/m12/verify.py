"""M13 section 6 independent verification engine (offline).

For an important finding: re-test through an independent path
(different tool from the original evidence), grade the outcome,
and bind everything with content hashes into an immutable
manifest. Grades: reproduced / corroborated / partial /
not-reproduced / impossible. Missing reproduction is never
treated as disproof -- it is recorded as uncertainty.
"""
from __future__ import annotations

import hashlib
import json
import time

GRADES = ("reproduced", "corroborated", "partial", "not-reproduced",
          "impossible")

_PROBE_POOL = ("residual_feature_dependence", "calibration_snapshot",
               "temporal_changepoint_scan", "regression_metrics",
               "classification_metrics", "data_quality_profile",
               "segment_quality_screen")


def _hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def manifest(finding: dict, evidence_refs: list[dict],
             actions: list[dict]) -> dict:
    """Immutable provenance manifest for one finding."""
    body = {
        "finding": finding,
        "evidence_refs": evidence_refs,
        "actions": [
            {"tool": a.get("tool"), "args": a.get("args", {}),
             "result_digest": _hash(a.get("result", {}))}
            for a in actions
        ],
        "t": time.time(),
    }
    body["manifest_hash"] = _hash(body)
    return body


def _probe_args(tool: str, artifact: str, facts: dict) -> dict:
    cols = facts.get("columns") or []
    args: dict = {"predictions_path": artifact}
    if "target" not in cols and "label" in cols:
        args["target_column"] = "label"
    if "prediction" not in cols and facts.get("score_col"):
        args["prediction_column"] = facts["score_col"]
    if tool in ("classification_metrics",
                "calibration_and_error_analysis") \
            and facts.get("score_col"):
        args["score_column"] = facts["score_col"]
    if tool == "segment_quality_screen" and facts.get("segments"):
        args["segment_column"] = facts["segments"][0]
    return args


def verify_finding(session, inv, hypothesis: dict, artifact: str,
                   second_tool: str | None = None) -> dict:
    """Independent re-test of one hypothesis's mechanism."""
    from ..causal import linker as LK
    from ..db import Action
    from .. import engine
    from ..research import invention as INV

    refs = hypothesis.get("evidence_refs") or []
    moving = [r for r in refs
              if r.get("relation") in ("supports", "contradicts")]
    if not moving:
        return {"grade": "impossible",
                "reason": "no moving evidence to reproduce",
                "manifest": manifest(hypothesis, refs, [])}
    used = {r.get("tool") for r in moving}
    facts = INV.artifact_facts(artifact)
    pool = [t for t in ([second_tool] if second_tool else
                        list(_PROBE_POOL)) if t not in used]
    if not pool:
        return {"grade": "impossible",
                "reason": "no independent tool remains",
                "manifest": manifest(hypothesis, refs, [])}
    tool = pool[0]
    try:
        out = engine.run_tool(
            session, inv, tool,
            _probe_args(tool, artifact, facts), source_meta=True)
    except Exception as exc:
        return {"grade": "impossible",
                "reason": ("%s: %s" % (type(exc).__name__, exc))[:150],
                "manifest": manifest(hypothesis, refs, [])}
    if not out.get("ok"):
        return {"grade": "impossible",
                "reason": out.get("error", "tool failed"),
                "manifest": manifest(hypothesis, refs, [])}
    act = session.get(Action, out.get("action_id"))
    orig_dirs = {r.get("relation") for r in moving}
    linked = LK.link_tool_result(session, inv, act) if act else []
    agree = [a for a in linked
             if a.get("hypothesis_id") == hypothesis.get("id")]
    if not agree:
        grade, why = ("not-reproduced",
                      "independent probe bears differently or not at all")
    elif agree[0].get("direction") in ("supports", "contradicts"):
        if agree[0]["direction"] in orig_dirs:
            grade, why = ("reproduced", "independent tool agrees")
        else:
            grade, why = ("partial",
                          "independent probe partially aligns")
    else:
        grade, why = ("corroborated",
                      "independent probe topically consistent, "
                      "non-moving")
    return {"grade": grade, "reason": why, "tool": tool,
            "manifest": manifest(
                hypothesis, refs,
                [{"tool": tool,
                  "args": _probe_args(tool, artifact, facts),
                  "result": out.get("result", {})}])}


def grade_report(verifications: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for v in verifications:
        counts[v.get("grade", "?")] = counts.get(v.get("grade", "?"), 0) + 1
    return {"counts": counts,
            "note": "missing reproduction is uncertainty, never "
                    "disproof; see per-finding manifests"}
