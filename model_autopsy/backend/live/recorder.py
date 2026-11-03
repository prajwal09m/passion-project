"""Durable live-run recording (Milestone 5, §9; phase_d pattern).

Preserves: request/response metadata, assistant texts, response-id
linkage, provider usage, hypothesis history, experiment requests +
results, tool-call records, repair records, final report, scorecard,
run manifest. Incomplete/invalid responses are preserved, never
truncated or discarded. Manifest is written LAST with a
required-evidence checklist; a run without a manifest is by definition
not finalized (recovery path documented in the limitations doc).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize_run(rundir: Path, run_id: str, pid: str,
                 investigation_id: str | None, session,
                 budget, status: str, eval_report: dict | None,
                 scorecard: dict | None, message_text: str,
                 error: str | None = None,
                 eval_version: str | None = None) -> dict:
    from .. import config as C
    from ..db import Action, Event, Hypothesis
    rundir = Path(rundir)
    artifacts: dict[str, str] = {}

    def _write(name: str, payload) -> None:
        tmp = rundir / (name + ".tmp")
        final = rundir / name
        tmp.write_text(json.dumps(payload, indent=2, default=str),
                       encoding="utf-8")
        tmp.replace(final)
        artifacts[name] = _sha(final)

    events, assistant, usage = [], [], []
    hypotheses, actions = [], []
    if session is not None and investigation_id:
        try:
            for e in (session.query(Event).filter(
                    Event.investigation_id == investigation_id).order_by(
                    Event.seq.asc()).all()):
                events.append({"seq": e.seq, "kind": e.kind, "title": e.title,
                               "detail": e.detail, "payload": e.payload,
                               "created_at": str(e.created_at)})
                if e.kind == "meta_response":
                    assistant.append({
                        "seq": e.seq,
                        "response_id": (e.payload or {}).get("response_id"),
                        "n_tool_calls": (e.payload or {}).get(
                            "n_tool_calls"),
                        "usage": (e.payload or {}).get("usage"),
                        "text": (e.payload or {}).get("text") or ""})
                if e.kind == "meta_usage":
                    usage.append(e.payload)
            for h in (session.query(Hypothesis).filter(
                    Hypothesis.investigation_id == investigation_id).all()):
                hypotheses.append({"id": h.id, "text": h.text,
                                   "status": h.status, "source": h.source,
                                   "rationale": h.rationale,
                                   "evidence_refs": h.evidence_refs,
                                   "revisions": h.revisions})
            for a in (session.query(Action).filter(
                    Action.investigation_id == investigation_id).order_by(
                    Action.seq.asc()).all()):
                actions.append({"id": a.id, "seq": a.seq, "kind": a.kind,
                                "tool": a.tool_name, "status": a.status,
                                "arguments": a.arguments, "result": a.result,
                                "error": a.error})
        except Exception as exc:
            events.append({"seq": -1, "kind": "recorder_note",
                           "title": "partial event dump",
                           "detail": f"{type(exc).__name__}: {exc}"[:200]})
    _write("events_dump.json", events)
    _write("assistant_messages.jsonl",
           "\n".join(json.dumps(m, default=str) for m in assistant))
    _write("usage.jsonl",
           "\n".join(json.dumps(u, default=str) for u in usage))
    _write("hypotheses.json", hypotheses)
    _write("actions.json", actions)
    if eval_report is not None:
        _write("eval_report.json", eval_report)
    if scorecard is not None:
        _write("scorecard.json", scorecard)
    if session is not None:
        try:
            bind = session.get_bind()
            src = Path(str(bind.url.database or ""))
            import shutil
            if src.exists():
                shutil.copy2(src, rundir / "sandbox_final.db")
                artifacts["sandbox_final.db"] = _sha(
                    rundir / "sandbox_final.db")
        except Exception:
            pass
    # M22 P0.1 Option A: visibility signal, recomputed from durable
    # linking state at finalize time (resumed runs restore it the same
    # way). None when the DB is unavailable (e.g. failure path without
    # a session); additive key, old manifests simply lack it.
    _useful = None
    if session is not None and investigation_id:
        try:
            from ..db import Investigation as _INV
            from ..causal import linker as _LINK
            _inv = session.get(_INV, investigation_id)
            if _inv is not None:
                _useful = bool(_LINK.has_useful_evidence(session, _inv))
        except Exception:
            _useful = None
    manifest = {
        "run_id": run_id, "kind": "m5-live-meta-pilot",
        "eval_rubric_version": eval_version,
        "useful_evidence": _useful,
        "eval_project": pid, "investigation_id": investigation_id,
        "status": status, "error": error,
        "model": C.meta_model_id(),
        "endpoint": C.meta_base_url() + "/responses",
        "budget": budget.ledger() if budget is not None else None,
        "structured_summary_note": "verbatim assistant text preserved in "
                                   "assistant_messages; no truncation",
        "artifacts": artifacts,
        "required_evidence_present": {
            "events_dump": "events_dump.json" in artifacts,
            "assistant_messages": "assistant_messages.jsonl" in artifacts,
            "usage": "usage.jsonl" in artifacts,
            "hypotheses": "hypotheses.json" in artifacts,
            "actions": "actions.json" in artifacts,
            "sandbox_db": "sandbox_final.db" in artifacts,
            "eval_report": ("eval_report.json" in artifacts
                            if eval_report is not None else "n/a"),
            "scorecard": ("scorecard.json" in artifacts
                          if scorecard is not None else "n/a"),
        },
    }
    _write("manifest.json", manifest)
    return manifest
