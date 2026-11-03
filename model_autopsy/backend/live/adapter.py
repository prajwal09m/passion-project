"""Meta report → M4 scorer adapter (Milestone 5, §6).

Converts the engine's deterministic final report (assembled ONLY from
recorded Meta hypotheses/findings/actions) plus the frozen final message
into the `{confirmed_findings, experiments, executive_summary}` shape
`eval.scorer.score` consumes. No new claims are introduced: titles come
from recorded findings, numbers from recorded action results.
"""
from __future__ import annotations


def meta_report_to_eval(session, inv, final_report: dict,
                          message_text: str, summary: dict,
                          fallback: dict | None = None) -> dict:
    from ..db import Action
    confirmed = []
    for entry in (final_report.get("confirmed", [])
                  + final_report.get("likely", [])):
        confirmed.append({
            "hypothesis_id": entry.get("evidence_action_id")
                             or entry.get("summary", "")[:24],
            "title": entry.get("summary", "")})
    rejected = [{"hypothesis_id": r.get("hypothesis_id", ""),
                 "title": r.get("text", "")}
                for r in final_report.get("rejected", [])
                if isinstance(r, dict)]
    experiments = []
    actions = (session.query(Action)
               .filter(Action.investigation_id == inv.id)
               .order_by(Action.seq.asc()).all())
    for a in actions:
        if a.status != "ran" or not a.tool_name:
            continue
        result = dict(a.result or {})
        experiments.append({"experiment_id": a.id, "tool": a.tool_name,
                            "summary": _summarize_result(a.tool_name,
                                                         result),                             "numbers": _numbers_only(a.tool_name,
                                                          result)})
    conclusion = ""
    if isinstance(summary.get("summary"), dict):
        conclusion = str(summary["summary"].get("conclusion") or "")
    # M20 Phase 4: assembly is read-only and every accepted report is
    # re-checked against authoritative state. The summary (native or
    # repaired) may explain the records but cannot override them: the
    # consistency result is recorded alongside the report. Native-valid
    # reports are recorded, not rejected (audit trail); repairs must
    # already have passed these gates before acceptance (loop.py).
    from ..causal import linker as _LINK
    try:
        _useful = _LINK.has_useful_evidence(session, inv)
    except Exception:
        _useful = None  # advisory only; never break assembly
    from ..causal import report_consistency as _RC
    _before = _RC.state_fingerprint(session, inv)
    _snap = _RC.build_snapshot(session, inv)
    _accepted = summary.get("summary") if summary.get("valid") else None
    _consistency = _RC.check(_accepted, _snap) if _accepted is not None \
        else {"passed": True, "failures": [],
              "warnings": ["no valid model summary; deterministic "
                             "fallback carries the report"]}
    _after = _RC.state_fingerprint(session, inv)
    # M20 Phase 6: report-generation provenance. One status:
    # model_native / model_repaired / deterministic_fallback.
    from datetime import datetime, timezone
    if fallback is not None:
        _gen_status = "deterministic_fallback"
    elif summary.get("repaired_via"):
        _gen_status = "model_repaired"
    else:
        _gen_status = "model_native"
    out = {"executive_summary": conclusion or message_text[:800],
            "confirmed_findings": confirmed,
            "rejected_hypotheses": rejected,
            "inconclusive": final_report.get("unresolved", []),
            "experiments": experiments,
            "verification": _verification_entries(session, inv),
            "limitations": final_report.get("limitations", []),
            "investigation_id": inv.id,
            "structured_summary_valid": bool(summary.get("valid")),
            "report_generation_status": _gen_status,
            "report_provenance": {
                "status": _gen_status,
                "output_class": summary.get("output_class"),
                "repair_attempted": bool(summary.get("repaired_via")),
                "repair_via": summary.get("repaired_via"),
                "consistency_passed": _consistency["passed"],
                "consistency_failures":
                _consistency["failures"][:8],
                "consistency_warnings":
                _consistency["warnings"][:8],
                "assembly_mutated_state": _before != _after,
                "useful_evidence": _useful,
                "schema_version":
                summary.get("schema_version") or "m8-v1",
                "generated_at":
                datetime.now(timezone.utc).isoformat(),
                "fallback_reason":
                (fallback.get("model_summary_errors") or [])[:4]
                if fallback is not None else None,
            }}
    if fallback is not None:
        # Labeled deterministic fallback (M8): the invalid original is
        # preserved; the fallback is records-only with provenance.
        out["deterministic_fallback"] = fallback
        out["fallback_used"] = True
        if not out["executive_summary"]:
            out["executive_summary"] = fallback.get("conclusion", "")
    else:
        out["fallback_used"] = False
    return out


def _verification_entries(session, inv) -> list:
    """Verification trail for scorer v3 (read-only; preserves assembly
    non-mutation: queries events, records nothing).

    Executed probes carry action_id + result; planned-but-unexecuted and
    explicit non-runs carry reason codes. Empty list (v2 archives) means
    'no verification recorded'."""
    try:
        from . import verification as _V
        status = _V.verification_status(session, inv)
    except Exception:
        return []
    entries: list = []
    for e in status.get("executed", []):
        entries.append({"hypothesis_id": e.get("hypothesis_id"),
                        "tool": e.get("tool"),
                        "action_id": e.get("action_id"),
                        "result": e.get("result")})
    for p in status.get("planned", []):
        if not any(x.get("hypothesis_id") == p.get("hypothesis_id")
                   and x.get("tool") == p.get("tool") for x in entries):
            entries.append({"hypothesis_id": p.get("hypothesis_id"),
                            "tool": p.get("tool"),
                            "planned": True})
    for u in status.get("unexecuted", []):
        entries.append({"hypothesis_id": u.get("hypothesis_id"),
                        "reason": u.get("reason"),
                        "detail": u.get("detail")})
    return entries


def _summarize_result(tool: str, result: dict) -> str:
    bits = []
    for key in ("auc", "group_gap", "bias_mean_residual", "mae",
                "drift_early_vs_late_mae", "split_overlap_hint",
                "silhouette", "imbalance_ratio", "gap", "n"):
        if key in result:
            bits.append(f"{key}={result[key]}")
    head = "; ".join(bits)[:220]
    return f"{tool}: {head}" if head else f"{tool}: recorded"


def _numbers_only(tool: str, result: dict) -> dict:
    out = {}
    for key, value in result.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[key] = value
        elif key in ("mae_by_group", "auc_by_group", "drift",
                     "split_date_spans") and isinstance(value, (dict, list)):
            out[key] = value
    # Forecast drift arrives as a pair; scorer reads `drift`.
    if "drift_early_vs_late_mae" in result:
        out["drift"] = result["drift_early_vs_late_mae"]
    if "split_overlap_hint" in result:
        out["overlap"] = result["split_overlap_hint"]
    if "residual_feature_corr" in result:
        out["residual_feature_corr"] = result["residual_feature_corr"]
    if isinstance(result.get("groups"), dict):
        out["groups"] = result["groups"]
    # Raw numbers preserved verbatim: v2 sees exactly what the tools
    # recorded. Canonical normalization for v3 happens centrally in
    # eval.pipeline.score_report on a copy (single version-aware boundary).
    return out
