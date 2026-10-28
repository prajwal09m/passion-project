"""Model Autopsy orchestration — investigation engine.

A finite-state workflow shared by both modes (software / ML) with hard
limits (iteration cap, tool-call cap). Meta (Muse Spark) is the runtime
investigator once configured; the engine's own job is bookkeeping,
validation, tool execution and honest evidence recording. It never writes
findings that Meta did not produce, and it never labels a result as
confirmed without a recorded tool result.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

from . import config, db, tools_registry
from .db import (Investigation, record_event, to_json_blob)

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
                      "inconclusive"):
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




def link_evidence(session: Session, hypothesis_id: str, action_id: str,
                  relation: str) -> dict:
    """Attach a real executed action to a hypothesis as supporting or
    contradicting evidence. Both IDs must exist; relation is audited."""
    from .db import Action, Hypothesis
    h = session.get(Hypothesis, hypothesis_id)
    if h is None:
        raise LookupError("hypothesis not found")
    a = session.get(Action, action_id)
    if a is None or a.investigation_id != h.investigation_id:
        raise LookupError("action not found in this investigation")
    if relation not in ("supports", "contradicts"):
        raise ValueError("relation must be 'supports' or 'contradicts'")
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
        "recommended_next": recommended,
        "budget": {"tool_calls": [inv.tool_call_count, inv.max_tool_calls],
                   "iterations": [inv.iteration_count, inv.max_iterations]},
        "scope_note": "assembled deterministically from the investigation's "
                      "recorded findings, hypotheses and executed actions; "
                      "no section is model-invented and every rejected "
                      "hypothesis carries its contradicting action ids."}
    return report


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
        predictions = cfg.get("predictions_path")
        labels = cfg.get("labels")
        context_payload = tools_registry.ml_tools()["artifact_summary"]
        context = context_payload(predictions_path=predictions, labels=labels)
    inv.config = {**inv.config, "context": context}
    record_event(session, inv.id, "tool_result", "Context loaded",
                 detail=repr(context)[:400], payload=context)
    if inv.status == "created":
        set_status(session, inv, "context_ready")
    session.commit()
    return context


def run_tool(session: Session, inv: Investigation, tool_name: str,
             arguments: dict, source_meta: bool | None = None) -> dict:
    """Validate + execute a registered tool with real args; record evidence.

    Tool-call budget is enforced here — the motor behind "never unbounded".
    """
    if inv.tool_call_count >= inv.max_tool_calls:
        return {"ok": False, "error": "tool_call_budget_exhausted",
                "detail": f"max_tool_calls={inv.max_tool_calls}"}
    try:
        outcome = tools_registry.execute(session, inv, tool_name, dict(arguments or {}))
    except Exception as exc:  # tool errors must be visible, not swallowed
        session.rollback()
        action, payload = tools_registry.record_failed_call(
            session, inv, tool_name, arguments or {}, str(exc))
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc),
                "action_id": action.id}
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
