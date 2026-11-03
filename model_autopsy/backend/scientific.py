"""Deterministic scientific-status evaluator.

Separates *execution* (did the workflow finish?) from *science* (what does
the recorded evidence establish?). Pure function of recorded state: no
provider calls, no invention. Never retroactively assigns conclusions to
historical records — callers decide when to persist/display.
"""
from __future__ import annotations

VALID_SCIENTIFIC = (
    "supported",
    "partially_supported",
    "inconclusive",
    "no_issue_detected_within_scope",
    "contradicted",
)

EXPLANATIONS = {
    "supported": "Recorded evidence independently verifies the explanation.",
    "partially_supported": "Some recorded evidence supports an explanation, but verification or corroboration is still missing.",
    "inconclusive": "Available evidence is insufficient to establish or reject the suspected problem.",
    "no_issue_detected_within_scope": "Relevant tests ran without detecting the suspected issue within the tested scope. This does not mean the model is universally safe.",
    "contradicted": "Recorded evidence contradicts the investigated explanation.",
}

# Diagnostics that count as "relevant tests" for the no-issue verdict.
RELEVANT_ML_TOOLS = (
    "classification_metrics",
    "dataset_validation",
    "feature_target_suspiciousness",
    "calibration_and_error_analysis",
    "time_split_validation",
    "grouped_auc_comparison",
    "data_quality_profile",
    "distribution_shift_profile",
)


def _distinct_support_tools(hyp) -> set:
    tools = set()
    for r in (hyp.evidence_refs or []):
        if r.get("relation") == "supports" and r.get("tool"):
            tools.add(r["tool"])
    return tools


def _has_verification_event(session, inv_id: str) -> bool:
    from .db import Event
    kinds = ("verification", "replication", "resolution")
    q = session.query(Event).filter(
        Event.investigation_id == inv_id, Event.kind.in_(kinds)).first()
    return q is not None


def evaluate(session, inv) -> dict:
    """Compute scientific assessment from recorded state (read-only)."""
    from .db import Action, Hypothesis
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    actions = session.query(Action).filter(
        Action.investigation_id == inv.id).all()
    ran = [a for a in actions if a.status == "ran"]
    failed = [a for a in actions if a.status == "failed"]
    ran_tools = {a.tool_name for a in ran}

    findings = list(inv.latest_findings or [])
    confirmed = [f for f in findings if f.get("status") == "confirmed"]
    likely = [f for f in findings if f.get("status") == "likely"]

    supported_h = [h for h in hyps if h.status == "supported"]
    open_h = [h for h in hyps if h.status in ("proposed", "investigating", "inconclusive", "blocked")]
    rejected_h = [h for h in hyps if h.status == "rejected"]

    verified_event = _has_verification_event(session, inv.id)

    gaps: list[str] = []
    unused = [t for t in RELEVANT_ML_TOOLS if t not in ran_tools]
    if unused:
        gaps.append("diagnostics never run: " + ", ".join(unused))
    if failed:
        gaps.append("failed diagnostics: " + ", ".join(sorted({str(a.tool_name) for a in failed})))

    # Suspicious-signal scan from recorded suspiciousness output.
    suspicious_max: float | None = None
    suspicious_feature: str | None = None
    _sl = {"score","prediction","pred","prob","proba","probability","y_score","y_pred","logit","oof","label","target","y"}
    for a in ran:
        if a.tool_name == "feature_target_suspiciousness" and isinstance(a.result, dict):
            _rows = [r for r in (a.result.get("top_correlations") or []) if str(r.get("feature","")).lower() not in _sl] or (a.result.get("top_correlations") or [])
            for row in _rows:
                try:
                    r = abs(float(row.get("abs_r", 0)))
                except Exception:
                    continue
                if suspicious_max is None or r > suspicious_max:
                    suspicious_max = r
                    suspicious_feature = str(row.get("feature", ""))
    has_suspicion = suspicious_max is not None and suspicious_max >= 0.4

    # provenance gap: any .py artifact attached but never statically inspected
    cfg = inv.config or {}
    scope_gaps: list[str] = []
    try:
        q = (cfg.get("question") or "")
        if ".py" in q and "script_static_inspection" not in ran_tools:
            scope_gaps.append("training script attached but static inspection not run")
    except Exception:
        pass

    # --- transition rules (ordered, most-established first) ---
    # 1. Supported: supported hypothesis (or confirmed finding) with
    #    independent corroboration (>=2 distinct supporting tools or a
    #    verification event).
    for h in supported_h:
        tools = _distinct_support_tools(h)
        n_sup = len([r for r in (h.evidence_refs or []) if r.get("relation") == "supports"])
        if n_sup >= 1 and (len(tools) >= 2 or verified_event):
            return _out("supported", f"Hypothesis '{h.text[:120]}' is supported by {n_sup} supporting evidence ref(s) across {len(tools) or 1} tool(s)" + (" with independent verification." if verified_event else "."), gaps, scope_gaps, suspicious_max, suspicious_feature)
    if confirmed and (verified_event or len({f.get('evidence_action_id') for f in confirmed if f.get('evidence_action_id')}) >= 1 and len(ran_tools) >= 2):
        # confirmed findings need corroboration too; single uncorroborated
        # confirmation degrades to partially_supported below.
        if verified_event or len(ran) >= 3:
            return _out("supported", f"{len(confirmed)} confirmed finding(s) with corroborating diagnostics and verification." if verified_event else f"{len(confirmed)} confirmed finding(s) with corroborating diagnostics.", gaps, scope_gaps, suspicious_max, suspicious_feature)

    # 2. Partially supported: supported/confirmed/likely exists but
    #    verification/corroboration missing, OR strong suspicion with a
    #    proposed hypothesis.
    if supported_h or confirmed or likely:
        why = []
        if supported_h:
            why.append(f"{len(supported_h)} supported hypothesi(s) await independent verification")
        if confirmed:
            why.append(f"{len(confirmed)} confirmed finding(s) await independent verification")
        if likely:
            why.append(f"{len(likely)} likely finding(s) need corroboration")
        return _out("partially_supported", "; ".join(why) + ".", gaps, scope_gaps, suspicious_max, suspicious_feature)
    if has_suspicion and open_h:
        return _out("partially_supported", f"Feature '{suspicious_feature}' shows a strong target association (|r|={suspicious_max:.3f}) with a proposed explanation, but provenance and re-evaluation are still missing; association alone is not proof of leakage.", gaps, scope_gaps, suspicious_max, suspicious_feature)

    # 3. Contradicted: every registered hypothesis rejected and no
    #    confirmed/likely findings.
    if rejected_h and not open_h and not supported_h and not confirmed and not likely:
        return _out("contradicted", f"All {len(rejected_h)} registered explanation(s) were contradicted by recorded evidence.", gaps, scope_gaps, suspicious_max, suspicious_feature)

    # 4. No issue within scope: relevant tests ran, no suspicion, no open
    #    hypotheses, no findings.
    relevant_ran = [t for t in RELEVANT_ML_TOOLS if t in ran_tools]
    if len(relevant_ran) >= 2 and not has_suspicion and not open_h and not confirmed and not likely and not supported_h:
        return _out("no_issue_detected_within_scope", f"Relevant tests ({', '.join(relevant_ran[:4])}) ran without detecting the suspected issue. Limited strictly to the tested scope.", gaps, scope_gaps, suspicious_max, suspicious_feature)

    # 5. Default: inconclusive.
    if not ran and not hyps:
        return _out("inconclusive", "Diagnostic execution finished, but no diagnostics ran and no explanations were proposed; nothing is established.", gaps, scope_gaps, suspicious_max, suspicious_feature)
    if not hyps:
        return _out("inconclusive", "Diagnostic execution finished, but the available evidence does not establish whether the suspected problem is present.", gaps, scope_gaps, suspicious_max, suspicious_feature)
    return _out("inconclusive", "Available evidence is insufficient to establish or reject the suspected problem; verification or corroboration is missing.", gaps, scope_gaps, suspicious_max, suspicious_feature)


def _out(status: str, explanation: str, gaps: list, scope_gaps: list, smax, sfeat) -> dict:
    return {
        "status": status,
        "explanation": explanation,
        "guidance": EXPLANATIONS[status],
        "evidence_gaps": gaps,
        "scope_gaps": scope_gaps,
        "suspicious_max_abs_r": smax,
        "suspicious_feature": sfeat,
    }
