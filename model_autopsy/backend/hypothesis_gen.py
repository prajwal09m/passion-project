"""Offline deterministic hypothesis generation + experiment recommendations.

Reads recorded diagnostic actions only. No provider calls, no invention:
every reference points at a real action id. Idempotent via deterministic
dedupe keys stored in hypothesis rationale marker.
"""
from __future__ import annotations

import hashlib

MACHINE_MARKER = "[machine-generated]"
MAX_HYPS = 3


def _existing_machine_texts(hyps) -> set[str]:
    out = set()
    for h in hyps:
        if (h.source == "machine") or (MACHINE_MARKER in (h.rationale or "")):
            out.add(_norm(h.text))
    return out


def _norm(t: str) -> str:
    return " ".join((t or "").strip().lower().split())


def _stable_key(text: str) -> str:
    return hashlib.sha256(_norm(text).encode()).hexdigest()[:12]


def _supports_for(session, inv_id: str, tool: str) -> list[str]:
    from .db import Action
    return [a.id for a in session.query(Action).filter(
        Action.investigation_id == inv_id,
        Action.tool_name == tool, Action.status == "ran").all()]


def generate_candidates(session, inv) -> dict:
    """Propose 0-3 machine hypotheses from recorded outputs (writes)."""
    from .db import Hypothesis
    from . import engine
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    existing = _existing_machine_texts(hyps)
    existing_manual = {_norm(h.text) for h in hyps if h.source != "machine"}
    created: list[dict] = []
    skipped: list[str] = []

    candidates = _build_candidates(session, inv)
    for c in candidates[:MAX_HYPS]:
        if _norm(c["text"]) in existing or _norm(c["text"]) in existing_manual:
            skipped.append("duplicate: " + c["text"][:80])
            continue
        h = Hypothesis(
            investigation_id=inv.id, text=c["text"], source="machine",
            status="proposed", rationale=f"{MACHINE_MARKER} key={_stable_key(c['text'])} | mechanism: {c['mechanism']} | why: {c['why']} | missing: {c['missing']} | support_if: {c['support_if']} | contradict_if: {c['contradict_if']}",
            predicted_observation=f"Supports if: {c['support_if']} Contradicts if: {c['contradict_if']}",
            expected_consequences=[c["experiment"]],
            missing_evidence=[c["missing"]],
            status_justification="Machine-proposed from recorded diagnostics; suspicion only, not proof.",
        )
        session.add(h)
        session.flush()
        for aid in c["support_action_ids"]:
            try:
                engine.link_evidence(session, h.id, aid, "supports")
            except Exception:
                pass
        for aid in c.get("contradict_action_ids", []):
            try:
                engine.link_evidence(session, h.id, aid, "contradicts")
            except Exception:
                pass
        # refresh to capture evidence_refs written by link_evidence
        session.refresh(h)
        created.append({"id": h.id, "text": h.text})
        existing.add(_norm(c["text"]))
        # budget: machine hypotheses do not consume tool calls; cap count
        if len(created) >= MAX_HYPS:
            break

    from .db import record_event
    if created:
        record_event(session, inv.id, "hypothesis",
                     f"Machine proposed {len(created)} candidate explanation(s)",
                     payload={"ids": [c["id"] for c in created]})
        session.commit()
    return {"created": created, "skipped": skipped,
            "note": "Suspicion only: associations are not proof of leakage." if created
            else "Insufficient recorded evidence to formulate a meaningful hypothesis."}


def _build_candidates(session, inv) -> list[dict]:
    from .db import Action
    actions = {a.tool_name: a for a in session.query(Action).filter(
        Action.investigation_id == inv.id, Action.status == "ran").all()}
    out: list[dict] = []

    # 1. Suspicious feature-target association -> leakage-suspicion hypothesis
    susp = actions.get("feature_target_suspiciousness")
    if susp and isinstance(susp.result, dict):
        rows = susp.result.get("top_correlations") or []
        _sl = {"score","prediction","pred","prob","proba","probability","y_score","y_pred","logit","oof"}
        rows = [r for r in rows if str(r.get("feature","")).lower() not in _sl] or rows
        if rows:
            top = rows[0]
            try:
                r = abs(float(top.get("abs_r", 0)))
            except Exception:
                r = 0.0
            feat = str(top.get("feature", "unknown"))
            n = top.get("n", "?")
            if r >= 0.4:
                strength = "very strong" if r >= 0.7 else "strong" if r >= 0.55 else "notable"
                out.append({
                    "text": f"Feature '{feat}' may carry information strongly associated with the target (|r|={r:.3f}) that could be unavailable at prediction time and warrants a leakage investigation.",
                    "mechanism": f"Proxy feature, direct target leakage, post-outcome information, or preprocessing/evaluation contamination involving '{feat}'.",
                    "why": f"{strength} statistical association (|r|={r:.3f}, n={n}) is screening evidence only; a legitimate predictive relationship is equally possible until provenance is established.",
                    "missing": "Feature provenance (how/when the feature becomes available), data-generating process, and an ablation re-evaluation with/without the feature.",
                    "experiment": f"Inspect provenance of '{feat}', then re-evaluate with and without it using the same validation methodology.",
                    "support_if": "the feature is derived from post-outcome information or removal materially changes validation performance",
                    "contradict_if": "the feature is available at prediction time and removal leaves validation performance essentially unchanged",
                    "support_action_ids": [susp.id],
                })
    # 2. Dataset validation gaps (duplicates / missing labels)
    dv = actions.get("dataset_validation")
    if dv and isinstance(dv.result, dict):
        dup = int(dv.result.get("n_duplicate_rows") or 0)
        if dup > 0:
            out.append({
                "text": f"Duplicate rows in the evaluation data (n={dup}) may distort validation metrics and mimic or mask a real performance problem.",
                "mechanism": "Evaluation contamination via duplicated records leaking across splits.",
                "why": "Duplicates inflate or deflate measured performance without reflecting true generalization.",
                "missing": "Deduplicated re-evaluation and split-overlap analysis.",
                "experiment": "Re-run classification metrics on a deduplicated frame and compare per-fold AUC.",
                "support_if": "metrics shift materially after deduplication",
                "contradict_if": "metrics are unchanged after deduplication",
                "support_action_ids": [dv.id],
            })
    # 3. Temporal / calibration signals
    for tool in ("time_split_validation", "calibration_and_error_analysis",
                 "distribution_shift_profile", "data_quality_profile"):
        a = actions.get(tool)
        if a and len(out) < MAX_HYPS:
            res = a.result if isinstance(a.result, dict) else {}
            # Only propose when the tool actually reported something notable
            note = str(res.get("note", "") or res.get("caveat", "") or "")[:160]
            out.append({
                "text": f"Validation behavior reported by '{tool}' may indicate a non-leakage failure mode (drift, miscalibration, or split design) that competes with the leakage explanation.",
                "mechanism": "Distribution shift, miscalibration, or validation-design artifact rather than target leakage.",
                "why": f"Recorded output from '{tool}' provides a competing explanation that must be ruled out before leakage can be claimed. {note}",
                "missing": "Targeted follow-up isolating this failure mode from leakage (ablation and provenance).",
                "experiment": f"Run a focused comparison using '{tool}' outputs against an ablation baseline.",
                "support_if": "the follow-up isolates this failure mode independent of any single feature",
                "contradict_if": "the follow-up shows no such effect once leakage-relevant features are controlled",
                "support_action_ids": [a.id],
            })
            break
    return out


# ---------------- experiment recommendations ----------------

def recommend(session, inv) -> list[dict]:
    """Evidence-driven next experiments (read-only, deterministic)."""
    from .db import Action, Hypothesis
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    ran_tools = {a.tool_name for a in session.query(Action).filter(
        Action.investigation_id == inv.id, Action.status == "ran").all()}
    recs: list[dict] = []
    for h in hyps:
        if h.status in ("rejected",):
            continue
        refs = h.evidence_refs or []
        tools = sorted({r.get("tool") or "" for r in refs if r.get("tool")})
        base_missing = h.missing_evidence or []
        # Recommend provenance inspection when suspicion-like text present
        if "leak" in h.text.lower() or "associated" in h.text.lower():
            recs.append({
                "hypothesis_id": h.id,
                "title": "Establish feature provenance and availability",
                "what": "Identify how the suspected feature is generated, when it becomes available, and whether it uses post-outcome information.",
                "why": "Association alone cannot distinguish legitimate prediction from leakage; provenance decides.",
                "evidence": [{"action_id": r.get("action_id"), "tool": r.get("tool")} for r in refs],
                "required_inputs": ["training/evaluation script or feature documentation"],
                "measures": "qualitative provenance verdict + file/line references",
                "support_if": "feature uses information unavailable at prediction time",
                "contradict_if": "feature is available at prediction time from legitimate inputs",
                "executable_now": "script_static_inspection" in ran_tools or True,
                "tool": "script_static_inspection",
                "missing": base_missing,
                "priority": 1,
            })
            recs.append({
                "hypothesis_id": h.id,
                "title": "Ablation re-evaluation with and without the feature",
                "what": "Re-run the same validation methodology on data with the suspected feature removed and compare metrics.",
                "why": "A leakage-carrying feature typically causes a material, reproducible performance drop when removed.",
                "evidence": [{"action_id": r.get("action_id"), "tool": r.get("tool")} for r in refs],
                "required_inputs": ["predictions/dataset artifact with feature columns"],
                "measures": "delta-AUC and calibration before vs after removal",
                "support_if": "material performance drop under identical methodology",
                "contradict_if": "no material change under identical methodology",
                "executable_now": "classification_metrics" in ran_tools,
                "tool": "classification_metrics",
                "missing": base_missing,
                "priority": 2,
            })
    # Generic verification when open hypotheses exist but no recs yet
    if not recs and any(h.status in ("proposed", "investigating") for h in hyps):
        h = next(h for h in hyps if h.status in ("proposed", "investigating"))
        recs.append({
            "hypothesis_id": h.id,
            "title": "Design a falsification test for the open explanation",
            "what": "Specify what recorded observation would support or contradict the hypothesis, then run that diagnostic.",
            "why": "Open explanations without falsification criteria cannot be resolved.",
            "evidence": [],
            "required_inputs": ["predictions/dataset artifact"],
            "measures": "pre-registered support/contradict criteria",
            "support_if": h.predicted_observation or "pre-registered supporting observation",
            "contradict_if": "pre-registered contradicting observation",
            "executable_now": False,
            "tool": "",
            "missing": h.missing_evidence or [],
            "priority": 3,
        })
    recs.sort(key=lambda r: r["priority"])
    return recs
