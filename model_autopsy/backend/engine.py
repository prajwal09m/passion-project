"""Model Autopsy orchestration — investigation engine.

A finite-state workflow shared by both modes (software / ML) with hard
limits (iteration cap, tool-call cap). Meta (Muse Spark) is the runtime
investigator once configured; the engine's own job is bookkeeping,
validation, tool execution and honest evidence recording. It never writes
findings that Meta did not produce, and it never labels a result as
confirmed without a recorded tool result.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from . import config, db, tools_registry
from .db import (Investigation, record_event, to_json_blob)


def _investigation_scope(inv, actions) -> dict:
    """Files uploaded / examined / used / stored-only + missing evidence."""
    q = inv.question or ""
    import re as _re
    paths = _re.findall(r"[\w./\\-]+\.[A-Za-z0-9]{2,8}", q)
    uploaded = sorted(set(paths))[:20]
    used: list[str] = []
    for a in actions:
        if a.status != "ran":
            continue
        res = a.result if isinstance(a.result, dict) else {}
        src = res.get("source")
        if src:
            used.append(str(src))
        args = a.arguments if isinstance(a.arguments, dict) else {}
        for k in ("predictions_path", "feature_csv", "label_csv", "script_path"):
            if args.get(k):
                used.append(str(args[k]))
    # dedupe preserving order
    seen: set = set()
    used_u = [x for x in used if not (x in seen or seen.add(x))]
    examined = used_u
    stored_only = [p for p in uploaded if p not in used_u]
    missing: list[str] = []
    if not any(p.endswith(('.csv', '.json', '.jsonl', '.parquet')) for p in uploaded + used_u):
        missing.append("predictions/dataset artifact with score + label columns")
    if any(p.endswith('.py') for p in uploaded) and not any((a.tool_name == 'script_static_inspection') for a in actions if a.status == 'ran'):
        missing.append("static inspection of attached training script(s)")
    return {"uploaded": uploaded, "examined": examined,
            "used_by_diagnostics": used_u, "stored_not_examined": stored_only,
            "missing": missing}


def _main_interpretation(sci: dict, supported_h, sections, likely, unresolved_n: int, ran_n: int) -> str:
    status = sci.get("status", "inconclusive")
    expl = sci.get("explanation", "")
    if status == "supported":
        return f"The evidence currently supports an explanation. {expl} All claims below trace to recorded diagnostics."
    if status == "partially_supported":
        return f"The evidence suggests a possible explanation but does not yet prove it. {expl} Treat every candidate as a hypothesis to verify, not a confirmed finding."
    if status == "no_issue_detected_within_scope":
        return f"Relevant tests ran without detecting the suspected issue ({ran_n} diagnostics). {expl} This is limited strictly to what was tested."
    if status == "contradicted":
        return f"The investigated explanation was contradicted by recorded evidence. {expl}"
    return f"No explanation has been established yet ({ran_n} diagnostics, {unresolved_n} open hypotheses). {expl} A lack of findings is not evidence that no problem exists."

VALID_MODES = ("software", "ml")
VALID_TARGET_STATUSES = ("created", "context_ready", "hypotheses_proposed",
                         "investigating", "revising", "finalizing",
                         "complete", "blocked", "failed", "stopped")

STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "created": ("context_ready", "investigating", "blocked", "stopped"),
    "context_ready": ("hypotheses_proposed", "investigating", "blocked", "stopped"),
    "hypotheses_proposed": ("investigating", "blocked", "stopped"),
    "investigating": ("investigating", "revising", "finalizing", "complete",
                      "blocked", "failed", "stopped"),
    "revising": ("investigating", "finalizing", "complete", "blocked",
                 "failed", "stopped"),
    "finalizing": ("complete", "failed", "blocked", "stopped"),
    "complete": ("finalizing", "stopped"),
    "blocked": ("investigating", "revising", "finalizing", "stopped"),
    "failed": ("investigating", "stopped"),
    "stopped": (),
}


def budgets_for(config_: dict) -> tuple[int, int]:
    """(max_iterations, max_tool_calls) — never above the absolute caps."""
    max_it = min(int(config_.get("max_iterations", config.DEFAULT_MAX_ITERATIONS)),
                 config.ABSOLUTE_MAX_ITERATIONS)
    max_tc = min(int(config_.get("max_tool_calls", config.ABSOLUTE_MAX_TOOL_CALLS)),
                 config.ABSOLUTE_MAX_TOOL_CALLS)
    return max(max_it, 1), max(max_tc, 1)


def create_investigation(session: Session, mode: str, title: str, question: str,
                         config_: dict | None = None,
                         workspace_root: str | None = None) -> Investigation:
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {VALID_MODES}")
    if not title.strip() or not question.strip():
        raise ValueError("title and question are required")
    cfg = dict(config_ or {})
    if os.environ.get("MODEL_AUTOPSY_TESTING") == "1":
        # Every record created by a test run is tagged so it can always be
        # distinguished from real investigations (and owner-pruned).
        tags = list(cfg.get("tags") or [])
        if "test" not in tags:
            tags.append("test")
        cfg["tags"] = tags
    cfg["workspace_root"] = workspace_root
    max_it, max_tc = budgets_for(cfg)
    inv = Investigation(mode=mode, title=title.strip(), question=question.strip(),
                        config=cfg, max_iterations=max_it, max_tool_calls=max_tc)
    session.add(inv)
    session.flush()
    record_event(session, inv.id, "status_change", "Investigation created",
                 detail=f"mode={mode}; max_iterations={max_it}; max_tool_calls={max_tc}")
    session.commit()
    return inv


def add_hypothesis(session: Session, investigation_id: str, text: str,
                   source: str = "meta", rationale: str | None = None) -> dict:
    inv = session.get(Investigation, investigation_id)
    if inv is None:
        raise LookupError("investigation not found")
    if inv.mode == "ml" and source == "meta" and inv.status in ("created", "context_ready"):
        inv.status = "hypotheses_proposed"
    from .db import Hypothesis
    h = Hypothesis(investigation_id=inv.id, text=text.strip(), source=source,
                   rationale=rationale)
    session.add(h)
    record_event(session, inv.id, "hypothesis", f"Hypothesis proposed: {text.strip()[:140]}",
                 payload={"hypothesis_id": h.id, "source": source})
    session.commit()
    return {"id": h.id, "text": h.text, "status": h.status, "source": h.source}


def update_hypothesis(session: Session, hypothesis_id: str, status: str,
                      confidence: int | None = None,
                      rationale: str | None = None) -> dict:
    from .db import Hypothesis
    h = session.get(Hypothesis, hypothesis_id)
    if h is None:
        raise LookupError("hypothesis not found")
    if status not in ("proposed", "investigating", "supported", "rejected",
                      "inconclusive", "blocked"):
        raise ValueError(f"invalid hypothesis status {status!r}")
    prev = {"status": h.status, "confidence": h.confidence,
            "rationale": h.rationale}
    h.status = status
    if confidence is not None:
        h.confidence = max(0, min(int(confidence), 100))
    if rationale is not None:
        h.rationale = rationale
    h.revisions = (h.revisions or []) + [{"at": str(db.utcnow()),
                                         "from": prev["status"],
                                         "to": status}]
    record_event(session, h.investigation_id, "hypothesis",
                 f"Hypothesis {h.text[:60]}... -> {status}",
                 payload={"hypothesis_id": h.id, "status": status,
                          "from": prev, "rationale": rationale})
    session.commit()
    return {"id": h.id, "status": h.status, "confidence": h.confidence,
            "rationale": h.rationale, "revisions": h.revisions}




NON_MOVING_RELATIONS = ("relevant_to", "mentions", "neutral",
                        "insufficient", "uncertain")


def link_evidence(session: Session, hypothesis_id: str, action_id: str,
                  relation: str) -> dict:
    """Attach a real executed action to a hypothesis.

    supports/contradicts move belief (via update_with_evidence). M9
    non-moving relations are stored visibly but change neither status
    nor confidence. Both IDs must exist; relation is audited."""
    from .db import Action, Hypothesis
    h = session.get(Hypothesis, hypothesis_id)
    if h is None:
        raise LookupError("hypothesis not found")
    a = session.get(Action, action_id)
    if a is None or a.investigation_id != h.investigation_id:
        raise LookupError("action not found in this investigation")
    if relation not in ("supports", "contradicts") + NON_MOVING_RELATIONS:
        raise ValueError(f"relation must be supports/contradicts or one of "
                         f"{NON_MOVING_RELATIONS}")
    refs = list(h.evidence_refs or [])
    if any(r.get("action_id") == action_id and r.get("relation") == relation
           for r in refs):
        return {"id": h.id, "evidence_refs": refs, "unchanged": True}
    refs.append({"action_id": action_id, "tool": a.tool_name,
                 "relation": relation,
                 "action_status": a.status})
    h.evidence_refs = refs
    record_event(session, h.investigation_id, "hypothesis",
                 f"Evidence linked to {h.text[:60]}... ({relation})",
                 payload={"hypothesis_id": h.id, "action_id": action_id,
                          "tool": a.tool_name, "relation": relation})
    session.commit()
    return {"id": h.id, "evidence_refs": refs}


def propose_hypothesis(session: Session, inv: Investigation,
                       text: str, rationale: str | None = None,
                       predicted_observation: str | None = None,
                       confidence_note: str | None = None) -> dict:
    """Registry tool (both modes): the runtime investigator formally
    registers a structured, falsifiable hypothesis. Recorded with origin
    'meta'; any confidence is the MODEL's uncalibrated self-report and must
    say so. Enforces a per-investigation hypothesis cap."""
    if inv.status in ("complete", "failed", "stopped"):
        raise ValueError(f"investigation is {inv.status}; no new hypotheses")
    from .db import Hypothesis
    existing = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).count()
    if existing >= config.MAX_HYPOTHESES_PER_INVESTIGATION:
        raise ValueError(
            f"hypothesis cap reached ({config.MAX_HYPOTHESES_PER_INVESTIGATION}); "
            "revise existing hypotheses instead of adding more")
    if inv.mode == "ml" and inv.status in ("created", "context_ready"):
        inv.status = "hypotheses_proposed"
    h = Hypothesis(investigation_id=inv.id, text=text.strip(), source="meta",
                   rationale=rationale, predicted_observation=predicted_observation,
                   confidence_note=confidence_note)
    session.add(h)
    session.flush()
    record_event(session, inv.id, "hypothesis",
                 f"Meta hypothesis proposed: {text.strip()[:140]}",
                 payload={"hypothesis_id": h.id, "source": "meta",
                          "predicted_observation": predicted_observation,
                          "confidence_note": confidence_note})
    session.commit()  # durable now: a later failed tool's rollback must
    # never wipe an already-recorded hypothesis (M7 robustness).
    return {"ok": True, "hypothesis_id": h.id, "origin": "meta",
            "note": "model-generated confidence is uncalibrated; only "
                    "tool-computed facts are findings", "text": h.text}


def propose_revision_instructions(session: Session, inv: Investigation,
                                  root: str | None = None,
                                  findings: list | None = None,
                                  instructions: list | None = None,
                                  review_tests: str | None = None) -> dict:
    """Registry tool (software mode): record a proposed-revision instruction
    bundle for HUMAN review. Nothing is ever applied by this platform; the
    plan stays a proposal until the owner acts outside the engine."""
    if inv.status in ("complete", "failed", "stopped"):
        raise ValueError(f"investigation is {inv.status}; no new plans")
    plan_entry = {"at": str(db.utcnow()),
                  "root": root or inv.config.get("workspace_root") or ".",
                  "findings": findings or [],
                  "instructions": instructions or [],
                  "review_tests": review_tests,
                  "applied": None,
                  "origin": "meta"}
    plans = list(inv.config.get("revision_plans") or [])
    plans.append(plan_entry)
    inv.config = {**inv.config, "revision_plans": plans}
    record_event(session, inv.id, "revision",
                 f"Revision plan proposed ({len(instructions or [])} instruction(s))",
                 payload=plan_entry)
    return {"ok": True, "plan_index": len(plans) - 1,
            "note": "proposal only; a human applies changes outside this engine"}


def mark_revision_applied(session: Session, inv: Investigation,
                          plan_index: int) -> dict:
    """Owner-controlled acknowledgement that a proposed plan was reviewed and
    applied MANUALLY outside the engine. Meta can never invoke this."""
    plans = list(inv.config.get("revision_plans") or [])
    if not 0 <= plan_index < len(plans):
        raise LookupError("revision plan not found")
    plans[plan_index] = {**plans[plan_index],
                         "applied": {"at": str(db.utcnow()),
                                     "how": "manual, outside Model Autopsy"}}
    inv.config = {**inv.config, "revision_plans": plans}
    record_event(session, inv.id, "revision",
                 f"Revision plan {plan_index} marked applied (manual, owner action)",
                 payload={"plan_index": plan_index})
    session.commit()
    return {"ok": True, "plan": plans[plan_index]}


def set_status(session: Session, inv: Investigation, new_status: str) -> None:
    if new_status not in VALID_TARGET_STATUSES:
        raise ValueError(f"invalid status {new_status!r}")
    if new_status not in STATUS_TRANSITIONS[inv.status]:
        raise ValueError(f"illegal transition {inv.status} -> {new_status}")
    old = inv.status
    inv.status = new_status
    record_event(session, inv.id, "status_change", f"{old} -> {new_status}")


def record_finding(session: Session, inv: Investigation, summary: str,
                   status: str, evidence_action_id: str | None = None) -> dict:
    if status not in ("confirmed", "likely", "rejected", "unresolved"):
        raise ValueError(f"invalid finding status {status!r}")
    if evidence_action_id:
        from .db import Action
        action = session.get(Action, evidence_action_id)
        if action is None or action.investigation_id != inv.id:
            raise ValueError("evidence_action_id not found in this investigation")
    finding = {"status": status, "summary": summary.strip(),
               "evidence_action_id": evidence_action_id}
    findings = list(inv.latest_findings or [])
    for f in findings:
        if (f.get("summary") == finding["summary"]
                and f.get("status") == status):
            return {**f, "unchanged": True}
    findings.append(finding)
    inv.latest_findings = findings
    record_event(session, inv.id, "finding", f"[{status}] {summary.strip()[:160]}",
                 payload={"evidence_action_id": evidence_action_id})
    session.commit()
    return finding


# Hypothesis status vocabulary the model may RECOMMEND in its structured
# summary (the same statuses `update_hypothesis` accepts). Meta can never
# apply them itself.
HYPOTHESIS_RECOMMENDABLE_STATUSES = ("proposed", "investigating", "supported",
                                     "rejected", "inconclusive", "blocked")


def ensure_finalizable(session: Session, inv: Investigation) -> list[str]:
    """Single legal FSM walk to finalizing (M6 Part 3 hardening).

    Mirrors the report endpoint so the driver, API and tests share one
    path. Returns the walked statuses. Never skips stages.
    """
    walked: list[str] = []
    if inv.status in ("created", "context_ready", "hypotheses_proposed",
                      "revising", "blocked", "failed"):
        set_status(session, inv, "investigating")
        walked.append("investigating")
    if inv.status == "investigating":
        set_status(session, inv, "finalizing")
        walked.append("finalizing")
    session.commit()
    return walked


def validate_structured_summary(session: Session, inv: Investigation,
                                message_text: str) -> dict:
    """Parse and validate Meta's final structured summary.

    Looks for a fenced ```investigation_summary block (or a bare JSON
    object containing "conclusion") in the model's final message. Returns
    {'valid': bool, 'summary': parsed|None, 'errors': [...]} and records
    event kind 'summary' — invalid output is recorded, never silently
    trusted OR thrown away. Every referenced hypothesis_id must exist in
    THIS investigation (exact id or unique prefix), and every recommended
    status must come from the application's own vocabulary. The model
    cannot change statuses here; these are recommendations for the owner.
    """
    from .db import Hypothesis
    errors: list[str] = []
    parsed = None
    candidates: list[str] = re.findall(
        r"```\s*investigation_summary\s*\n?(.*?)```", message_text or "",
        flags=re.DOTALL)
    if not candidates:
        # fallback: a bare JSON object that introduces a conclusion field
        candidates = re.findall(r"\{\s*\"conclusion\"[^{}]*\}",
                                message_text or "", flags=re.DOTALL)
    for cand in candidates:
        try:
            parsed = json.loads(cand.strip())
            if isinstance(parsed, dict):
                break
            parsed = None
            errors.append("summary JSON parsed but is not an object")
        except json.JSONDecodeError as exc:
            errors.append(f"summary is not valid JSON: {exc}")
    if parsed is None:
        errors.append("no structured summary found in the final message")
        result = {"valid": False, "summary": None, "errors": errors,
                  "schema_version": "m8-v1"}
    else:
        # M8 versioned contract (superset of the M6 checks): strict
        # schema, types, refs, truncation and overconfidence gates.
        from .causal import report_schema as _RS
        from .db import Action as _Action
        hyps = session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv.id).all()
        acts = session.query(_Action).filter(
            _Action.investigation_id == inv.id).all()
        checked = _RS.validate(
            parsed, {h.id for h in hyps}, {a.id for a in acts})
        errors.extend(e for e in checked["errors"] if e not in errors)
        result = {"valid": checked["valid"],
                  "summary": checked["normalized"],
                  "errors": errors,
                  "warnings": checked["warnings"],
                  "schema_version": checked["schema_version"]}
    # M20 Phase 1: output classification recorded in report metadata.
    # Additive only: validation behavior unchanged. The raw model output
    # is preserved (payload prose head; full verbatim text already lives
    # in the meta_response event) and never overwritten by repair.
    from .causal import summary_class as _SC
    _cls = _SC.classify(message_text, result)
    result["output_class"] = _cls["class"]
    result["output_class_reason"] = _cls["reason"]
    # M21: read-only consistency advisory for valid summaries. Recorded,
    # not enforced — the M20 record-not-reject contract is frozen (see
    # M21_EVALUATION_PROTOCOL §4). Advisory only; validity unchanged.
    # Never breaks validation: any snapshot failure degrades to a warning.
    _advisory: dict = {"passed": True, "failures": [], "warnings": []}
    if result.get("valid"):
        try:
            from .causal import report_consistency as _RC
            _advisory = _RC.check(result.get("summary"),
                                  _RC.build_snapshot(session, inv))
        except Exception:
            _advisory = {"passed": True, "failures": [],
                         "warnings": ["consistency advisory unavailable"]}
    result["consistency_passed"] = _advisory["passed"]
    result["consistency_failures"] = list(_advisory["failures"])[:8]
    result["consistency_warnings"] = list(_advisory["warnings"])[:8]
    record_event(session, inv.id, "summary",
                 f"Structured summary parsed: "
                 f"{'valid' if result['valid'] else 'INVALID'} "
                 f"({_cls['class']})",
                 detail=(json.dumps(parsed, default=str)[:600] if parsed
                         else (message_text or "")[:600]),                         payload={"valid": result["valid"],
                          "errors": errors,
                          "output_class": _cls["class"],
                          "output_class_reason": _cls["reason"][:200],
                          "repair_eligible": _cls["repair_eligible"],
                          "consistency_passed": result[
                              "consistency_passed"],
                          "consistency_failures": result[
                              "consistency_failures"],
                          "consistency_warnings": result[
                              "consistency_warnings"],
                          "raw_block": (json.dumps(parsed, default=str)
                                        if parsed else None)})
    session.commit()
    return result


def build_report(session: Session, inv: Investigation) -> dict:
    """Deterministic final report assembled ONLY from recorded state:
    hypotheses, findings, actions and budgets. No section is invented; every
    confirmed/likely/rejected entry cites its evidence action id when one was
    recorded. Reproducible from saved evidence alone."""
    from .db import Action, Hypothesis
    findings = list(inv.latest_findings or [])
    statuses = ["confirmed", "likely", "rejected"]
    sections = {s: [] for s in (("confirmed", "likely", "rejected"))}
    seen: set = set()
    for f in findings:
        if f.get("status") in sections:
            entry = {"summary": f["summary"],
                     "evidence_action_id": f.get("evidence_action_id")}
            key = (entry["summary"], entry["evidence_action_id"])
            if key in seen:
                continue
            seen.add(key)
            sections[f["status"]].append(entry)
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    unresolved = [{"hypothesis_id": h.id, "text": h.text,
                   "status": h.status, "origin": h.source,
                   "confidence_is_model_note": bool(h.confidence_note)}
                  for h in hyps if h.status in ("proposed", "investigating",
                                                "inconclusive")]
    rejected_h = [{"hypothesis_id": h.id, "text": h.text,
                   "evidence_refs": h.evidence_refs or []}
                  for h in hyps if h.status == "rejected"]
    supported_h = [{"hypothesis_id": h.id, "text": h.text,
                    "evidence_refs": h.evidence_refs or []}
                   for h in hyps if h.status == "supported"]
    actions = (session.query(Action)
               .filter(Action.investigation_id == inv.id)
               .order_by(Action.seq).all())
    evidence_performed = []
    for a in actions:
        item = {"action_id": a.id, "seq": a.seq, "tool": a.tool_name,
                "status": a.status}
        if a.status == "failed" and a.error:
            item["error"] = str(a.error)[:200]
        elif a.result:
            res = dict(a.result)
            res.pop("budget", None)
            item["result_digest"] = {
                k: res[k] for k in sorted(res)[:8] if isinstance(
                    res[k], (int, float, str, bool)) or res[k] is None}
        evidence_performed.append(item)
    limitations = []
    ran = [a for a in actions if a.status == "ran"]
    if not ran and not findings:
        limitations.append("no diagnostic executed and no finding recorded; "
                           "this report contains recorded structure only and "
                           "no evidence-backed conclusions")
    if inv.tool_call_count >= inv.max_tool_calls:
        limitations.append(f"tool-call budget fully used "
                           f"({inv.tool_call_count}/{inv.max_tool_calls}); "
                           "further diagnostics were impossible")
    if inv.iteration_count >= inv.max_iterations:
        limitations.append(f"iteration budget used "
                           f"({inv.iteration_count}/{inv.max_iterations})")
    failed_tools = sorted({a.tool_name for a in actions if a.status == "failed"})
    if failed_tools:
        limitations.append(f"diagnostics that failed and were never "
                           "rerun: " + ", ".join(str(t) for t in failed_tools))
    unused = [t for t in (tools_registry.ml_tools() if inv.mode == "ml"
                          else tools_registry.software_tools())
              if t not in {a.tool_name for a in actions
                           if a.status == "ran"}
              and t not in ("propose_hypothesis",
                            "propose_revision_instructions")]
    if unused:
        limitations.append("available diagnostics never run in this "
                           "investigation: " + ", ".join(unused))
    recommended = []
    for h in unresolved:
        recommended.append({"for": h["hypothesis_id"],
                            "action": "Design a test that would falsify: "
                                      f"{h['text'][:120]}",
                            "status": "hypothesis remains " + h["status"]})
    if inv.tool_call_count < inv.max_tool_calls and not recommended:
        recommended.append({"for": None, "action": "No open hypotheses "
                            "remain; investigation may be closed", "status": "n/a"})
    # ---- scientific assessment + scope + experiments (additive, deterministic) ---
    try:
        from . import scientific as _sci
        sci = _sci.evaluate(session, inv)
    except Exception:
        sci = {"status": "inconclusive", "explanation": "scientific evaluation unavailable.",
               "guidance": "", "evidence_gaps": [], "scope_gaps": [],
               "suspicious_max_abs_r": None, "suspicious_feature": None}
    try:
        from . import hypothesis_gen as _hg
        experiments = _hg.recommend(session, inv)
    except Exception:
        experiments = []
    # investigation scope: files uploaded / examined / used / stored-only
    try:
        scope = _investigation_scope(inv, actions)
    except Exception:
        scope = {"uploaded": [], "examined": [], "used_by_diagnostics": [],
                 "stored_not_examined": [], "missing": []}
    main_interp = _main_interpretation(sci, supported_h, sections, likely=[f for f in findings if f.get("status") == "likely"], unresolved_n=len(unresolved), ran_n=len(ran))
    # Evidence-driven recommended experiments replace/augment generic ones
    exp_recs = []
    for e in experiments:
        exp_recs.append({"for": e.get("hypothesis_id"), "action": f"{e.get('title')}: {e.get('what')} Support if: {e.get('support_if')} Contradict if: {e.get('contradict_if')}", "status": "proposed experiment", "detail": e})
    recommended_combined = exp_recs + recommended
    # candidate explanations split by origin
    machine_h = [{"hypothesis_id": h.id, "text": h.text, "status": h.status,
                   "evidence_refs": h.evidence_refs or [], "rationale": h.rationale,
                   "predicted_observation": h.predicted_observation}
                  for h in hyps if (h.source == "machine" or "[machine-generated]" in (h.rationale or ""))]
    manual_h = [{"hypothesis_id": h.id, "text": h.text, "status": h.status,
                 "origin": h.source, "evidence_refs": h.evidence_refs or []}
                for h in hyps if not ((h.source == "machine" or "[machine-generated]" in (h.rationale or "")))]
    report = {
        "investigation_id": inv.id, "mode": inv.mode,
        "question": inv.question, "generated_at": str(db.utcnow()) + "Z",
        "confirmed": sections["confirmed"],
        "likely": sections["likely"],
        "rejected": sections["rejected"] + rejected_h,
        "unresolved": unresolved,
        "supported_hypotheses": supported_h,
        "evidence_performed": evidence_performed,
        "limitations": limitations or ["none recorded"],
        "recommended_next": recommended_combined or recommended,
        "budget": {"tool_calls": [inv.tool_call_count, inv.max_tool_calls],
                   "iterations": [inv.iteration_count, inv.max_iterations]},
        "scope_note": "assembled deterministically from the investigation's "
                      "recorded findings, hypotheses and executed actions; "
                      "no section is model-invented and every rejected "
                      "hypothesis carries its contradicting action ids.",
        "execution_status": inv.status,
        "scientific_assessment": sci,
        "main_interpretation": main_interp,
        "investigation_scope": scope,
        "candidate_explanations": {"machine": machine_h, "manual": manual_h},
        "recommended_experiments": experiments,
        "diagnostics_not_run": unused,
        "reproducibility": {
            "artifact_identities": scope.get("examined", []),
            "eval_version": (inv.config or {}).get("eval_rubric_version"),
            "budget": {"tool_calls": [inv.tool_call_count, inv.max_tool_calls]},
        },
    }
    return report


def grounded_summary(session: Session, inv: Investigation) -> dict:
    """M16 P1-2: model-proof structured facts for summary grounding.

    Pure function of recorded state (no event, deterministic): every
    hypothesis id, status, confidence, evidence ref (action id + tool +
    relation), and independent-support counts, plus the action ledger.
    The model explains these facts; it must not regenerate them.
    """
    from .db import Action, Hypothesis
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == inv.id).order_by(Action.seq).all()
    hviews = []
    for h in hyps:
        refs = h.evidence_refs or []
        tools_sup = sorted({r.get("tool") or "?" for r in refs
                            if r.get("relation") == "supports"})
        tools_con = sorted({r.get("tool") or "?" for r in refs
                            if r.get("relation") == "contradicts"})
        hviews.append({
            "hypothesis_id": h.id, "text": h.text,
            "status": h.status, "confidence": h.confidence,
            "evidence_refs": [{"action_id": r.get("action_id"),
                                 "tool": r.get("tool"),
                                 "relation": r.get("relation")}
                                for r in refs],
            "independent_supports": len(tools_sup),
            "independent_contradicts": len(tools_con)})
    return {
        "investigation_id": inv.id,
        "hypotheses": hviews,
        "actions": [{"action_id": a.id, "seq": a.seq,
                       "tool": a.tool_name, "status": a.status}
                      for a in acts],
        "rule": ("explain ONLY these recorded facts; do not invent "
                   "hypothesis ids, statuses, action ids, or measured "
                   "numbers; anything not listed here is unresolved"),
    }


def build_context(session: Session, inv: Investigation,
                  workspace_root: str | None = None) -> dict:
    """Step 1 of both modes: load real, read-only context from disk.

    software: git status + diff stats of the configured working directory.
    ml: summary of the configured dataset / prediction artifacts.
    Returns the context payload and stores it in `inv.config['context']`.
    """
    if inv.mode == "software":
        root = workspace_root or inv.config.get("workspace_root") or "."
        resolved = str(Path(root).resolve()) if not str(root).startswith("::") else None
        sw = tools_registry.software_tools()
        context = {
            "workspace_root": str(Path(root).resolve()) if resolved is None else resolved,
            "git": sw["git_status_and_diff"](root=root, max_diff_chars=4000),
        }
    else:
        cfg = inv.config
        project_id = cfg.get("project_id")
        if project_id:
            # Universal path (Phase 5): the project adapter describes the
            # project; the engine never touches project-specific fields.
            from .projects import get_project
            adapter = get_project(project_id)
            context = adapter.context_summary()
            context["investigator_brief"] = adapter.investigator_brief()
            context["capabilities"] = adapter.available_capabilities()
        else:
            predictions = cfg.get("predictions_path")
            labels = cfg.get("labels")
            context_payload = tools_registry.ml_tools()["artifact_summary"]
            if not predictions:
                # No predictions file selected (e.g. script-only
                # investigation): record the gap explicitly instead of
                # silently loading the Demand Zone template as context.
                # Otherwise the workspace Source names a file the user
                # never uploaded and Meta spends turns diagnosing it.
                # Tool-level defaults (artifact_summary with no args)
                # are unchanged for benchmarks and the case study.
                context = {"ok": True, "source": None,
                           "filename": None,
                           "note": ("no predictions file selected — "
                                    "score-based diagnostics will report "
                                    "the gap; script/artifact-level "
                                    "diagnostics can proceed"),
                           "n_rows": 0, "n_columns": 0, "columns": [],
                           "label_column": None}
            elif predictions:
                try:
                    context = context_payload(predictions_path=predictions, labels=labels)
                except ValueError as exc:
                    # A user-selected file without a usable binary label
                    # column must not block the investigation at Start:
                    # record a label-free profile (never a guessed label)
                    # so dataset/script-level diagnostics and Meta turns can
                    # proceed. Metric tools keep refusing honestly until a
                    # real label is mapped.
                    context = _label_free_dataset_context(predictions, str(exc))
    inv.config = {**inv.config, "context": context}
    record_event(session, inv.id, "tool_result", "Context loaded",
                 detail=repr(context)[:400], payload=context)
    if inv.status == "created":
        set_status(session, inv, "context_ready")
    session.commit()
    return context


def _label_free_dataset_context(predictions: str, reason: str) -> dict:
    """Label-free context profile for a selected CSV with no usable label.

    Profiles the file with dataset_validation (which records the label gap
    factually) and lists binary-{0,1} columns as *mapping candidates* for
    the operator. Nothing here selects or synthesizes a label: metric tools
    keep reporting the gap until a real label is mapped."""
    import pandas as pd
    from . import ml_tools
    profile = ml_tools.dataset_validation(predictions_path=predictions)
    candidates: list[str] = []
    try:
        df = pd.read_csv(profile["source"])
        for col in df.columns:
            try:
                vals = set(pd.to_numeric(df[col], errors="coerce")
                           .dropna().unique().tolist())
            except Exception:
                continue
            if vals and vals <= {0, 1}:
                candidates.append(str(col))
    except Exception:
        candidates = []
    return {
        **profile,
        "label_status": ("no usable binary label column (" + reason + "); "
                          "label-free profile only — metric tools will "
                          "report the gap until a real label is mapped"),
        "binary_label_candidates": candidates,
    }


def run_tool(session: Session, inv: Investigation, tool_name: str,
             arguments: dict, source_meta: bool | None = None) -> dict:
    """Validate + execute a registered tool with real args; record evidence.

    Tool-call budget is enforced here — the motor behind "never unbounded".
    """
    if inv.tool_call_count >= inv.max_tool_calls:
        return {"ok": False, "error": "tool_call_budget_exhausted",
                "detail": f"max_tool_calls={inv.max_tool_calls}"}
    try:
        outcome = tools_registry.execute(session, inv, tool_name,
                                         dict(arguments or {}),
                                         allow_reuse=bool(source_meta))
    except Exception as exc:  # tool errors must be visible, not swallowed
        session.rollback()
        action, payload = tools_registry.record_failed_call(
            session, inv, tool_name, arguments or {}, str(exc))
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc),
                "action_id": action.id}
    inner = dict(outcome.get("result") or {})
    inner.pop("_dedup", None)          # internal fingerprint: not model/API-facing
    outcome["result"] = inner
    if not outcome.get("reused"):
        inv.tool_call_count += 1
    payload = {"budget": {"used": inv.tool_call_count,
                          "max": inv.max_tool_calls}, **outcome}
    session.commit()
    return payload


def can_continue(inv: Investigation) -> tuple[bool, str]:
    if inv.status == "revising" and inv.iteration_count >= inv.max_iterations:
        return False, "iteration_limit_reached"
    if inv.status in ("complete", "failed", "stopped"):
        return False, f"status_{inv.status}"
    return True, ""


def finalize(session: Session, inv: Investigation, report: dict) -> dict:
    """Record the structured final report (assembled by the caller from
    recorded evidence; never synthesized by the engine)."""
    required = {"confirmed", "likely", "rejected", "unresolved",
                "evidence_performed", "recommended_next"}
    missing = required - set(report.keys())
    if missing:
        raise ValueError(f"final report missing sections: {sorted(missing)}")
    inv.final_report = report
    record_event(session, inv.id, "report", "Final report recorded",
                 payload=report)
    if inv.status != "complete":
        set_status(session, inv, "complete")
    session.commit()
    return inv.final_report
