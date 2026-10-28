"""Model Autopsy FastAPI application — API surface.

Explicit contracts:
  POST /api/investigations              create (mode, title, question, config)
  GET  /api/investigations              list (filters, from SQLite)
  GET  /api/investigations/{id}         details incl hypotheses/actions/report
  GET  /api/investigations/{id}/timeline
  POST /api/investigations/{id}/context         load real repo/context step
  POST /api/investigations/{id}/tool            run one approved tool now
  POST /api/investigations/{id}/meta-turn       run bounded Meta turn
  POST /api/investigations/{id}/hypotheses      add hypothesis (manual)
  POST /api/investigations/{id}/hypotheses/{hid}/evidence   link action evidence
  PATCH /api/hypotheses/{id}                    update hypothesis status
  POST /api/investigations/{id}/findings        record a finding (evidence-optional)
  POST /api/investigations/{id}/report          build + persist the final report
  POST /api/investigations/{id}/revision-plan/{idx}/applied  owner ack (manual apply)
  GET  /api/case-study/demand-zone              real artifact overview
  GET  /api/case-study/demand-zone/metrics      real computed chart metrics
  GET  /api/tool-contract                       validated parameter schemas
  GET  /api/meta/status                 key configured? last test result?
  POST /api/meta/test-connection          live GET /models using stored key
  GET  /api/settings                     non-secret settings
"""
from __future__ import annotations

import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import config, db, engine, tools_registry
from .meta_api import client as meta_client
from .meta_api import loop as meta_loop

app = FastAPI(title="Model Autopsy", version="0.2.0")

# Dashboard on :5173 talks to this backend; loopback dev origins only.
app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173",
                                   "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "PATCH"], allow_headers=["*"])


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


def get_db() -> Session:  # request-scoped session
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _detail(exc: Exception, limit: int = 400) -> str:
    """Sanitized, truncated error detail (never leaks paths/keys wholesale)."""
    text = str(exc) or type(exc).__name__
    return text[:limit]


class InvestigationCreate(BaseModel):
    mode: str
    title: str = Field(max_length=200)
    question: str = Field(max_length=5000)
    max_iterations: int | None = Field(default=None, ge=1, le=3)
    workspace_root: str | None = Field(default=None, max_length=512)
    predictions_path: str | None = Field(default=None, max_length=512)
    tags: list[str] = Field(default=[], max_length=10)


class ToolRun(BaseModel):
    tool_name: str = Field(max_length=80)
    arguments: dict = Field(default={}, max_length=200)


class MetaTurn(BaseModel):
    max_rounds: int | None = Field(default=3, ge=1, le=5)
    previous_response_id: str | None = Field(default=None, max_length=120)


class HypothesisIn(BaseModel):
    text: str = Field(min_length=5, max_length=800)
    source: str = Field(default="manual", pattern="^(manual|meta)$")
    rationale: str | None = Field(default=None, max_length=800)


class HypothesisPatch(BaseModel):
    status: str
    confidence: int | None = Field(default=None, ge=0, le=100)
    rationale: str | None = Field(default=None, max_length=800)


class FindingIn(BaseModel):
    summary: str = Field(min_length=3, max_length=2000)
    status: str
    evidence_action_id: str | None = Field(default=None, max_length=32)


class EvidenceLink(BaseModel):
    action_id: str = Field(max_length=32)
    relation: str = Field(pattern="^(supports|contradicts)$")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "model-autopsy", "time": time.time()}


def _inv_or_404(session: Session, investigation_id: str) -> db.Investigation:
    inv = session.get(db.Investigation, investigation_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="investigation not found")
    return inv


def _inv_summary(inv: db.Investigation) -> dict:
    from . import prune as _prune
    _is_test, _test_reason = _prune.is_test_record(inv)
    cfg = inv.config if isinstance(inv.config, dict) else {}
    return {"id": inv.id, "mode": inv.mode, "title": inv.title,
            "status": inv.status, "iteration_count": inv.iteration_count,
            "max_iterations": inv.max_iterations,
            "tool_call_count": inv.tool_call_count,
            "max_tool_calls": inv.max_tool_calls,
            "created_at": str(inv.created_at) + "Z",
            "latest_findings": inv.latest_findings,
            "tags": cfg.get("tags") or [],
            "is_test_record": _is_test,
            "has_final_report": inv.final_report is not None}


@app.post("/api/investigations")
def create_investigation(payload: InvestigationCreate,
                         session: Session = Depends(get_db)) -> dict:
    try:
        inv = engine.create_investigation(
            session, payload.mode, payload.title, payload.question,
            {"max_iterations": payload.max_iterations or 3,
             "predictions_path": payload.predictions_path,
             "tags": payload.tags},
            workspace_root=payload.workspace_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))
    return _inv_summary(inv)


@app.get("/api/investigations")
def list_investigations(mode: str | None = None, status: str | None = None,
                        limit: int = 100,
                        session: Session = Depends(get_db)) -> dict:
    q = session.query(db.Investigation).order_by(
        db.Investigation.created_at.desc())
    if mode:
        q = q.filter(db.Investigation.mode == mode)
    if status:
        q = q.filter(db.Investigation.status == status)
    return {"items": [_inv_summary(i) for i in
                      q.limit(max(1, min(int(limit), 500))).all()]}


@app.get("/api/investigations/{investigation_id}")
def get_investigation(investigation_id: str,
                      session: Session = Depends(get_db)) -> dict:
    inv = _inv_or_404(session, investigation_id)
    return {**_inv_summary(inv), "question": inv.question, "config": inv.config,
            "final_report": inv.final_report,
            "hypotheses": [{"id": h.id, "text": h.text, "status": h.status,
                            "confidence": h.confidence, "source": h.source,
                            "rationale": h.rationale,
                            "predicted_observation": h.predicted_observation,
                            "confidence_note": h.confidence_note,
                            "evidence_refs": h.evidence_refs,
                            "revisions": h.revisions,
                            "created_at": str(h.created_at) + "Z"}
                           for h in inv.hypotheses],
            "actions": [{"id": a.id, "seq": a.seq, "kind": a.kind,
                         "tool_name": a.tool_name, "status": a.status,
                         "arguments": a.arguments, "result": a.result,
                         "error": a.error, "iteration": a.iteration}
                        for a in inv.actions]}


@app.get("/api/investigations/{investigation_id}/timeline")
def timeline(investigation_id: str, limit: int = 300,
             session: Session = Depends(get_db)) -> dict:
    inv = _inv_or_404(session, investigation_id)
    events = (session.query(db.Event)
              .filter(db.Event.investigation_id == inv.id)
              .order_by(db.Event.seq.asc()).limit(min(max(1, limit), 1000)).all())
    return {"investigation_id": inv.id, "events": [
        {"seq": e.seq, "kind": e.kind, "title": e.title, "detail": e.detail,
         "payload": e.payload, "created_at": str(e.created_at) + "Z"}
        for e in events]}


@app.post("/api/investigations/{investigation_id}/context")
def build_context(investigation_id: str,
                  session: Session = Depends(get_db)) -> dict:
    inv = _inv_or_404(session, investigation_id)
    try:
        context = engine.build_context(session, inv)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))
    return {"ok": True, "context": context, "status": inv.status}


@app.post("/api/investigations/{investigation_id}/tool")
def run_tool(investigation_id: str, payload: ToolRun,
             session: Session = Depends(get_db)) -> dict:
    inv = _inv_or_404(session, investigation_id)
    if int(inv.tool_call_count) >= int(inv.max_tool_calls):
        return {"ok": False, "error": "tool_call_budget_exhausted",
                "max_tool_calls": inv.max_tool_calls}
    try:
        return engine.run_tool(session, inv, payload.tool_name,
                               payload.arguments)
    except (LookupError, PermissionError, FileNotFoundError, ValueError,
            TypeError) as exc:
        try:
            tools_registry.record_failed_call(
                session, inv, payload.tool_name, dict(payload.arguments),
                _detail(exc))
            session.commit()
        except Exception:
            session.rollback()
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/investigations/{investigation_id}/meta-turn")
def meta_turn(investigation_id: str, payload: MetaTurn,
              session: Session = Depends(get_db)) -> dict:
    inv = _inv_or_404(session, investigation_id)
    if not inv.config.get("context"):
        engine.build_context(session, inv)
    return meta_loop.run_meta_turn(session, inv,
                                   max_rounds=min(int(payload.max_rounds or 3), 5),
                                   previous_response_id=payload.previous_response_id)


@app.post("/api/investigations/{investigation_id}/hypotheses")
def add_hypothesis(investigation_id: str, payload: HypothesisIn,
                   session: Session = Depends(get_db)) -> dict:
    _inv_or_404(session, investigation_id)
    try:
        return engine.add_hypothesis(session, investigation_id, payload.text,
                                     payload.source, payload.rationale)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.patch("/api/hypotheses/{hypothesis_id}")
def patch_hypothesis(hypothesis_id: str, payload: HypothesisPatch,
                     session: Session = Depends(get_db)) -> dict:
    try:
        return engine.update_hypothesis(session, hypothesis_id,
                                        payload.status, payload.confidence,
                                        payload.rationale)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/hypotheses/{hypothesis_id}/evidence")
def link_evidence(hypothesis_id: str, payload: EvidenceLink,
                  session: Session = Depends(get_db)) -> dict:
    try:
        return engine.link_evidence(session, hypothesis_id,
                                    payload.action_id, payload.relation)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/investigations/{investigation_id}/findings")
def add_finding(investigation_id: str, payload: FindingIn,
                session: Session = Depends(get_db)) -> dict:
    inv = _inv_or_404(session, investigation_id)
    try:
        if payload.evidence_action_id:
            action = session.get(db.Action, payload.evidence_action_id)
            if action is None or action.investigation_id != inv.id:
                raise ValueError("evidence_action_id not found in this "
                                 "investigation")
        return engine.record_finding(session, inv, payload.summary,
                                     payload.status, payload.evidence_action_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/investigations/{investigation_id}/report")
def generate_report(investigation_id: str,
                    session: Session = Depends(get_db)) -> dict:
    """Deterministic final report assembled from RECORD evidence only."""
    inv = _inv_or_404(session, investigation_id)
    try:
        # Legal pre-transition: finalization requires the investigating stage.
        if inv.status in ("created", "context_ready", "hypotheses_proposed",
                          "revising", "blocked", "failed"):
            engine.set_status(session, inv, "investigating")
        report = engine.build_report(session, inv)
        return {"ok": True, "report": engine.finalize(session, inv, report)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/investigations/{investigation_id}/revision-plan/{plan_index}/applied")
def mark_plan_applied(investigation_id: str, plan_index: int,
                      session: Session = Depends(get_db)) -> dict:
    """Owner-controlled acknowledgement of a MANUAL application outside the
    engine. Never callable by the model."""
    inv = _inv_or_404(session, investigation_id)
    try:
        return engine.mark_revision_applied(session, inv, plan_index)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.get("/api/tool-contract")
def tool_contract(mode: str | None = None) -> dict:
    """The single authoritative tool contract (UI copy + demo)."""
    return tools_registry.parameter_documentation(mode)


@app.get("/api/meta/status")
def meta_status() -> dict:
    return {"key_configured": config.meta_api_key() is not None,
            "base_url": config.meta_base_url(),
            "model_id": config.meta_model_id(),
            "runtime_investigator": meta_client.__doc__.splitlines()[2].strip()}


@app.post("/api/meta/test-connection")
def test_meta_connection(session: Session = Depends(get_db)) -> dict:
    result = meta_client.test_connection()
    record = {"ok": result.get("ok"), "at": time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "detail": result.get("detail") or result.get("status_code"),
        "verified": "live" if result.get("ok") else "failed_or_absent"}
    db.set_setting(session, "meta_last_test", db.dump_payload(record))
    session.commit()
    return result


@app.get("/api/settings")
def get_settings(session: Session = Depends(get_db)) -> dict:
    test_record = None
    raw = db.get_setting(session, "meta_last_test")
    if raw:
        import json
        test_record = json.loads(raw)
    return {"meta": {"key_configured": config.meta_api_key() is not None,
                     "base_url": config.meta_base_url(),
                     "model_id": config.meta_model_id(),
                     "last_test": test_record},
            "safety": {"absolute_max_iterations": config.ABSOLUTE_MAX_ITERATIONS,
                       "absolute_max_tool_calls": config.ABSOLUTE_MAX_TOOL_CALLS,
                       "max_hypotheses_per_investigation":
                           config.MAX_HYPOTHESES_PER_INVESTIGATION,
                       "workspace_roots": [str(r) for r in config.allowed_workspace_roots()],
                       "write_tools": "none — applying changes is always a "
                                      "manual, human action outside this platform",
                       "campaign_isolation":
                           "The autonomous research supervisor under "
                           "autonomous_agent/ is fully independent: no tool "
                           "here can start, stop, or modify a campaign."}}


@app.get("/api/case-study/demand-zone")
def case_study(session: Session = Depends(get_db)) -> dict:
    """Real overview of the bundled Demand Zone study artifacts."""
    from . import ml_tools
    cfg = ml_tools.CASE_STUDY_CONFIG
    summary = None
    error = None
    try:
        summary = ml_tools.artifact_summary()
    except Exception as exc:            # real artifact missing -> say so
        error = f"{type(exc).__name__}: {exc}"
    return {"name": cfg["name"], "artifacts": {
        "oof_csv": cfg["oof_csv"], "event_csv": cfg["event_csv"],
        "models_dir": cfg["models_dir"]},
        "model_cols": cfg["model_cols"], "summary": summary, "error": error,
        "docs": {"reference": "study_files/README.md narrative: the original "
                             "suspicious AUC is a stored historical claim "
                             "over a leaked-feature dataset that is NOT in "
                             "this repository; the frozen v1.0.2 protocol "
                             "artifacts above are the real, recomputable "
                             "evidence."},
        "suggest_investigation": {
            "mode": "ml",
            "title": "Demand Zone AI — error-cluster investigation",
            "question": "Where does the frozen champion fail? Compare model "
                        "arms on the real OOF artifact and investigate "
                        "chronology, calibration, and arm deltas."}}


@app.get("/api/case-study/demand-zone/metrics")
def case_study_metrics(n_boot: int = 500) -> dict:
    """The REAL numbers behind the case-study charts, recomputed live from
    the frozen OOF artifact by the same diagnostic functions the tools use.
    Nothing here is hardcoded."""
    from .meta_api.case_metrics import build_case_metrics
    try:
        return build_case_metrics(n_boot=max(100, min(int(n_boot), 2000)))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=_detail(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_detail(exc))
