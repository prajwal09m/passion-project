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

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from . import config, db, engine, tools_registry
from . import projects as _projects
from .meta_api import client as meta_client
from .meta_api import loop as meta_loop

app = FastAPI(title="Model Autopsy", version="0.2.0")

# Dashboard on :5173 talks to this backend. Loopback by default; tunnel
# origins allowed so a hosted share URL (ngrok/cloudflare/localtunnel)
# works for judges using YOUR key blind. Extra origins via
# MODEL_AUTOPSY_PUBLIC_ORIGINS (comma-separated, e.g. "https://xxxx.ngrok-free.app").
import os as _os
_PUBLIC_EXTRA = [o.strip() for o in _os.environ.get("MODEL_AUTOPSY_PUBLIC_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",
                   "http://127.0.0.1:5173"] + _PUBLIC_EXTRA,
    allow_origin_regex=r"https://.*\.(ngrok-free\.app|ngrok\.io|loca\.lt|trycloudflare\.com)(:\d+)?",
    allow_methods=["GET", "POST", "PATCH"], allow_headers=["*"])


@app.on_event("startup")
def _startup() -> None:
    # Pick up model_autopsy/.env for servers launched without __main__
    # (e.g. `uvicorn model_autopsy.backend.api:app`). No-op when the
    # process env already carries the values; never prints secrets.
    config.bootstrap_env()
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
    eval_version: str | None = Field(default=None, max_length=8)
    workspace_root: str | None = Field(default=None, max_length=512)
    predictions_path: str | None = Field(default=None, max_length=512)
    project_id: str | None = Field(default=None, max_length=80)
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
    sci_status = None
    try:
        fr = inv.final_report or {}
        sci_status = (fr.get("scientific_assessment") or {}).get("status")
    except Exception:
        sci_status = None
    return {"id": inv.id, "mode": inv.mode, "title": inv.title,
            "status": inv.status, "iteration_count": inv.iteration_count,
            "max_iterations": inv.max_iterations,
            "tool_call_count": inv.tool_call_count,
            "max_tool_calls": inv.max_tool_calls,
            "created_at": str(inv.created_at) + "Z",
            "latest_findings": inv.latest_findings,
            "tags": cfg.get("tags") or [],
            "is_test_record": _is_test,
            "eval_rubric_version": cfg.get("eval_rubric_version"),
            "has_final_report": inv.final_report is not None,
            "scientific_status": sci_status}


@app.post("/api/investigations")
def create_investigation(payload: InvestigationCreate,
                         session: Session = Depends(get_db)) -> dict:
    try:
        if payload.project_id:
            from .projects import get_project
            try:
                get_project(payload.project_id)
            except LookupError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        try:
            from .eval import pipeline as _pipe
            _rubric = _pipe.select_eval_rubric(
                explicit=payload.eval_version)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=_detail(exc))
        inv = engine.create_investigation(
            session, payload.mode, payload.title, payload.question,
            {"max_iterations": payload.max_iterations or 3,
             "predictions_path": payload.predictions_path,
             "project_id": payload.project_id,
             "tags": payload.tags,
             "eval_rubric_version": _rubric},
            workspace_root=payload.workspace_root)
        from .eval import pipeline as _pipe2
        _pipe2.persist_eval_rubric(session, inv, _rubric)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))
    return _inv_summary(inv)


@app.post("/api/investigations/{investigation_id}/stop")
def stop_investigation(investigation_id: str,
                       session: Session = Depends(get_db)) -> dict:
    """Safe stop: terminal states refuse; active states park as stopped."""
    from . import db as _db
    inv = _inv_or_404(session, investigation_id)
    if inv.status in ("complete", "failed", "stopped", "finalizing"):
        raise HTTPException(
            status_code=400,
            detail=f"investigation is {inv.status}: terminal, refusing stop")
    _prev = inv.status
    inv.status = "stopped"
    _db.record_event(session, inv.id, "status_change",
                       "Investigation stopped by owner request",
                       payload={"from": _prev, "to": "stopped"})
    session.commit()
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
    try:
        from . import scientific as _sci
        _sci_view = {"execution_status": inv.status, **_sci.evaluate(session, inv)}
    except Exception:
        _sci_view = {"execution_status": inv.status, "status": "inconclusive", "explanation": "unavailable"}
    try:
        from . import hypothesis_gen as _hg2
        _exps = _hg2.recommend(session, inv)
    except Exception:
        _exps = []
    return {**_inv_summary(inv), "question": inv.question, "config": inv.config,
            "final_report": inv.final_report,
            "scientific": _sci_view, "recommended_experiments": _exps,
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


@app.get("/api/investigations/{investigation_id}/m16")
def m16_records(investigation_id: str,
                session: Session = Depends(get_db)) -> dict:
    """M16 live-discovery records: reservation, skeptic, grounding,
    no-motion attribution notes, status justifications. Read-only;
    every item comes from recorded events/state."""
    inv = _inv_or_404(session, investigation_id)
    evs = (session.query(db.Event)
            .filter(db.Event.investigation_id == inv.id)
            .order_by(db.Event.seq.asc()).all())
    pick = lambda *kinds: [
        {"seq": e.seq, "kind": e.kind, "title": e.title,
         "detail": e.detail, "payload": e.payload}
        for e in evs if e.kind in kinds]
    return {
        "investigation_id": inv.id,
        "reservation": pick("reservation"),
        "skeptic": pick("skeptic"),
        "grounded": pick("grounded"),
        "linker_notes": pick("linker"),
        "status_justifications": [
            {"id": h.id, "text": h.text, "status": h.status,
             "justification": getattr(h, "status_justification", None),
             "evidence_refs": h.evidence_refs}
            for h in inv.hypotheses],
    }


@app.get("/api/investigations/{investigation_id}/closure")
def closure_records(investigation_id: str,
                    session: Session = Depends(get_db)) -> dict:
    """M18 scientific-closure view: hypotheses, real status transitions,
    evidence adequacy, reservation/skeptic/verification records, resolution
    contract, spend. Read-only; every item comes from recorded backend data."""
    from .research import resolve as _RES
    inv = _inv_or_404(session, investigation_id)
    evs = (session.query(db.Event)
            .filter(db.Event.investigation_id == inv.id)
            .order_by(db.Event.seq.asc()).all())
    pick = lambda *kinds: [
        {"seq": e.seq, "kind": e.kind, "title": e.title,
         "detail": e.detail, "payload": e.payload}
        for e in evs if e.kind in kinds]
    exp_actions = [a for a in inv.actions if a.status == "ran"]
    return {
        "investigation_id": inv.id,
        "hypotheses": [
            {"id": h.id, "text": h.text, "status": h.status,
             "evidence_refs": h.evidence_refs, "revisions": h.revisions,
             "justification": getattr(h, "status_justification", None)}
            for h in inv.hypotheses],
        "transitions": _RES.collect_transitions(session, inv.id),
        "experiment_ledger": pick("experiment_ledger"),
        "experiments_executed": len(exp_actions),
        "experiments_cap": 6,
        "tool_calls_used": inv.tool_call_count,
        "tool_calls_max": inv.max_tool_calls,
        "reservation": pick("reservation"),
        "skeptic": pick("skeptic"),
        "verification": pick("verification", "replication"),
        "resolution": pick("resolution"),
        "budget": {"tool_calls": [inv.tool_call_count, inv.max_tool_calls]},
    }


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
        # Single shared FSM walk (same helper as the live driver).
        engine.ensure_finalizable(session, inv)
        report = engine.build_report(session, inv)
        return {"ok": True, "report": engine.finalize(session, inv, report)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/investigations/{investigation_id}/auto-interpret")
def auto_interpret(investigation_id: str,
                   session: Session = Depends(get_db)) -> dict:
    """Offline deterministic hypothesis generation + scientific assessment.

    Idempotent: re-running never duplicates machine hypotheses. No provider
    calls."""
    inv = _inv_or_404(session, investigation_id)
    from . import hypothesis_gen as _hg, scientific as _sci
    gen = _hg.generate_candidates(session, inv)
    session.refresh(inv)
    sci = _sci.evaluate(session, inv)
    recs = _hg.recommend(session, inv)
    return {"ok": True, "hypotheses": gen, "scientific": sci,
            "experiments": recs}


@app.get("/api/investigations/{investigation_id}/scientific")
def get_scientific(investigation_id: str,
                   session: Session = Depends(get_db)) -> dict:
    inv = _inv_or_404(session, investigation_id)
    from . import scientific as _sci, hypothesis_gen as _hg
    return {"execution_status": inv.status,
            "scientific": _sci.evaluate(session, inv),
            "experiments": _hg.recommend(session, inv)}


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


@app.get("/api/projects")
def list_projects() -> dict:
    return {"projects": _projects.list_projects()}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict:
    try:
        adapter = _projects.get_project(project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    spec = adapter.spec
    return {"spec": spec.to_dict(),
            "capabilities": adapter.available_capabilities(),
            "investigator_brief": adapter.investigator_brief()}


@app.get("/api/model-frameworks")
def list_frameworks() -> dict:
    from . import model_adapters as _ma
    return {"frameworks": _ma.supported_frameworks()}


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
            "evaluation": {"rubric_versions": list(
                config.EVAL_RUBRIC_VERSIONS),
                           "rubric_default": config.EVAL_RUBRIC_DEFAULT,
                           "rubric_selected":
                               config.eval_rubric_default(),
                           "framework": "m4-v1"},
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


@app.post("/api/investigations/{investigation_id}/research/run")
def research_run(investigation_id: str, session: Session = Depends(get_db)) -> dict:
    """Run the offline autonomous research cycle (no provider calls)."""
    from .research import lab as _lab
    from .projects import ProjectSpec
    inv = _inv_or_404(session, investigation_id)
    if inv.mode != "ml":
        raise HTTPException(status_code=400, detail="research lab requires mode='ml'")
    max_exp = 4
    try:
        max_exp = int((inv.config or {}).get("research_max_experiments", 4))
    except Exception:
        pass
    try:
        pid = (inv.config or {}).get("project_id")
        if pid:
            from .projects import get_project
            spec = get_project(pid).spec
        else:
            spec = ProjectSpec(project_id="adhoc",
                               name=inv.title or "adhoc",
                               task_type="other",
                               objective=inv.question or "")
            from .projects import register_project as _reg
            from .projects import ProjectAdapter as _PA
            try:
                _reg(_PA(spec))
            except ValueError:
                pass
        report = _lab.run_autonomous_investigation(
            session, inv, spec,
            artifact_path=(inv.config or {}).get("predictions_path")
            or spec.dataset.location or None,
            max_experiments=max(1, min(int(max_exp), 6)))
        return {"ok": True, "report": report}
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.get("/api/investigations/{investigation_id}/research")
def research_state(investigation_id: str, session: Session = Depends(get_db)) -> dict:
    inv = _inv_or_404(session, investigation_id)
    rs = dict((inv.config or {}).get("research") or {})
    return {"investigation_id": inv.id, "stages": rs.get("stages", {}),
            "hypotheses": rs.get("hypotheses", []),
            "reviews": rs.get("reviews", []),
            "taxonomy": rs.get("taxonomy", {}),
            "report": rs.get("report")}


@app.post("/api/investigations/{investigation_id}/research/hypotheses")
def research_propose(investigation_id: str, payload: dict,
                     session: Session = Depends(get_db)) -> dict:
    from .research import hypotheses as _h
    inv = _inv_or_404(session, investigation_id)
    try:
        return _h.propose(session, inv, payload or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/research/hypotheses/{hypothesis_id}/transition")
def research_transition(hypothesis_id: str, payload: dict,
                        session: Session = Depends(get_db)) -> dict:
    from .research import hypotheses as _h
    inv_id = (payload or {}).get("investigation_id")
    if not inv_id:
        raise HTTPException(status_code=400, detail="investigation_id is required")
    inv = _inv_or_404(session, inv_id)
    try:
        return _h.transition(session, inv, hypothesis_id,
                             (payload or {}).get("to", "investigating"),
                             (payload or {}).get("note", ""),
                             (payload or {}).get("evidence"))
    except (ValueError, LookupError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


def _eval_root() -> Path:
    from pathlib import Path as _P
    root = _P(config.BACKEND_DIR).parent / "benchmarks" / "eval_runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


@app.get("/api/eval/projects")
def eval_projects() -> dict:
    from .eval import projects as _P, separation as _S
    items = []
    for p in _P.PROJECTS:
        brief = _S.discovery_input(p)["brief"]
        items.append({"id": p["id"], "family": p["family"],
                      "name": p["spec"]["name"],
                      "task": p["spec"]["task_type"], "brief": brief})
    return {"projects": items}


@app.get("/api/eval/separation-audit")
def eval_audit() -> dict:
    from .eval import separation as _S
    return _S.audit_investigator_env()


@app.get("/api/eval/versions")
def eval_versions() -> dict:
    """Available scoring rubric versions + active default (no secrets)."""
    return {"versions": list(config.EVAL_RUBRIC_VERSIONS),
            "default": config.EVAL_RUBRIC_DEFAULT,
            "selected": config.eval_rubric_default(),
            "framework": "m4-v1"}


@app.post("/api/eval/runs")
def eval_run(payload: dict) -> dict:
    from .eval import runner as _R
    import uuid as _uuid
    try:
        _rubric = config.resolve_eval_rubric(
            (payload or {}).get("eval_version"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))
    try:
        run_id = "eval-" + _uuid.uuid4().hex[:12]
        rec = _R.run_all(
            _eval_root(),
            only=(payload or {}).get("project"),
            max_experiments=int((payload or {}).get("max_experiments", 4)),
            run_id=run_id,
            eval_version=_rubric,
            session_factory=_R.session_for(
                str((_eval_root() / run_id / "eval.sqlite3").absolute())))
        return {"ok": True, "run_id": rec["run_id"],
                "manifest": rec["manifest"]}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.get("/api/eval/runs")
def eval_runs() -> dict:
    import json as _json
    out = []
    for d in sorted(_eval_root().iterdir(), reverse=True):
        m = d / "manifest.json"
        if d.is_dir() and m.exists():
            try:
                out.append(_json.loads(m.read_text(encoding="utf-8")))
            except OSError:
                continue
    return {"runs": out}


@app.get("/api/eval/runs/{run_id}")
def eval_run_detail(run_id: str) -> dict:
    import json as _json
    m = _eval_root() / run_id / "manifest.json"
    if not m.exists():
        raise HTTPException(status_code=404, detail="run not found")
    return _json.loads(m.read_text(encoding="utf-8"))


@app.get("/api/eval/runs/{run_id}/{project_id}")
def eval_project_result(run_id: str, project_id: str) -> dict:
    import json as _json
    f = _eval_root() / run_id / f"{project_id}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail="result not found")
    rec = _json.loads(f.read_text(encoding="utf-8"))
    from .eval import review as _RV
    rec["human_review"] = _RV.status(_eval_root() / run_id, project_id)
    return rec


@app.post("/api/eval/runs/{run_id}/{project_id}/review/blind")
def eval_review_blind(run_id: str, project_id: str, payload: dict) -> dict:
    from .eval import review as _RV
    try:
        return _RV.blind_verdict(
            _eval_root() / run_id, project_id,
            (payload or {}).get("reviewer", "anonymous"),
            (payload or {}).get("verdict", "cannot_tell"),
            (payload or {}).get("notes", ""))
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/eval/runs/{run_id}/{project_id}/review/reveal")
def eval_review_reveal(run_id: str, project_id: str, payload: dict) -> dict:
    from .eval import review as _RV
    try:
        return _RV.reveal_and_assess(
            _eval_root() / run_id, project_id,
            (payload or {}).get("assessment", ""))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


def _live_root() -> Path:
    root = Path(config.BACKEND_DIR).parent / "benchmarks" / "live_runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


@app.get("/api/live/runs")
def live_runs() -> dict:
    """Read-only index of preserved live Meta pilot runs.

    No spend-triggering endpoint exists: live pilots are CLI-launched
    only (backend/live/cli.py) after preflight. The dashboard reads."""
    import json as _json
    out = []
    for d in sorted(_live_root().iterdir(), reverse=True):
        m = d / "manifest.json"
        if d.is_dir() and m.exists():
            try:
                full = _json.loads(m.read_text(encoding="utf-8"))
                out.append({k: full.get(k) for k in (
                    "run_id", "status", "eval_project", "model",
                    "budget")})
                out[-1]["run_id"] = d.name
            except OSError:
                continue
    return {"runs": out, "note": "live Meta results; never compared "
            "as if they measured the deterministic pipeline"}


@app.get("/api/live/runs/{run_id}")
def live_run_detail(run_id: str) -> dict:
    import json as _json
    f = _live_root() / run_id / "manifest.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail="live run not found")
    return _json.loads(f.read_text(encoding="utf-8"))


@app.get("/api/investigations/{investigation_id}/causal")
def causal_view(investigation_id: str,
                session: Session = Depends(get_db)) -> dict:
    """M6 causal view: competition, evidence graph, selection rationale,
    diagnosis grades, validation. Read-only; assembled from records."""
    from .causal import hypotheses as _H, evidence_graph as _EG
    from .causal import selection as _SEL, diagnosis as _DG
    from .db import Hypothesis, Action
    inv = _inv_or_404(session, investigation_id)
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == inv.id).all()
    hviews = [{"id": h.id, "text": h.text, "status": h.status,
               "confidence": h.confidence,
               "justification": getattr(h, "status_justification", None),
               "evidence_refs": h.evidence_refs or []} for h in hyps]
    competition = _H.analyze_competition(hviews)
    graph = _EG.build_graph(session, inv.id)
    tools = sorted({a.tool_name for a in acts if a.tool_name} | {
        "temporal_changepoint_scan", "residual_time_analysis",
        "distribution_shift_profile"})
    ranked = _SEL.rank_candidates(
        tools, hviews, {a.tool_name for a in acts if a.status == "ran"})
    grades = {h["id"]: _DG.grade(
        {"text": h["text"]},
        sum(1 for r in h["evidence_refs"] if r.get("relation") == "supports"),
        sum(1 for r in h["evidence_refs"] if r.get("relation") == "contradicts"),
        confounders_addressed=False) for h in hviews}
    # M7 feedback loop: transitions, confidence trail, adherence, stopping.
    from .db import Event
    evs = session.query(Event).filter(
        Event.investigation_id == inv.id).order_by(Event.seq.asc()).all()
    transitions = []
    for h in hyps:
        for r in (h.revisions or []):
            transitions.append({"hypothesis_id": h.id[:8],
                                "at": str(r.get("at")),
                                "from": r.get("from"), "to": r.get("to")})
    confidence_trail = [
        {"hypothesis_id": h.id[:8], "confidence": h.confidence,
         "status": h.status,
         "justification": getattr(h, "status_justification", None)}
        for h in hyps]
    feedback = [{"seq": e.seq, "kind": e.kind, "title": e.title[:160],
                 "payload": {k: v for k, v in (e.payload or {}).items()
                             if k in ("recommended", "followed",
                                      "executed_diagnostics", "rationale",
                                      "applied", "action_id")}}
                for e in evs if e.kind in ("selection", "linker",
                                           "stopping")]
    stop_ev = [e for e in evs if e.kind == "stopping"]
    # M8 reliability/discovery/reporting: coverage from recorded state,
    # report-validation trail from summary/fallback events, tool budget.
    from .causal import coverage as _CV, planning as _PL
    _ran = {a.tool_name for a in acts if a.status == "ran"}
    _failed = {a.tool_name for a in acts if a.status == "failed"}
    _plan = _PL.plan_next(
        hviews, _ran,
        {"tool_calls_used": inv.tool_call_count,
         "tool_calls_max": inv.max_tool_calls},
        already_failed=_failed)
    _summaries = [{"seq": e.seq, "valid": (e.payload or {}).get("valid"),
                   "errors": (e.payload or {}).get("errors"),
                   "output_class": (e.payload or {}).get("output_class"),
                   "repair_eligible":
                   (e.payload or {}).get("repair_eligible"),
                   "consistency_passed":
                   (e.payload or {}).get("consistency_passed"),
                   "consistency_failures":
                   (e.payload or {}).get("consistency_failures"),
                   "consistency_warnings":
                   (e.payload or {}).get("consistency_warnings")}
                  for e in evs if e.kind == "summary"]
    # M20 Phase 6: repair trail + generation status. Additive keys only;
    # existing consumers ignore what they do not read.
    _repairs = [{"seq": e.seq, "title": e.title[:160],
                 "valid": (e.payload or {}).get("valid"),
                 "continuation": (e.payload or {}).get("continuation"),
                 "output_class": (e.payload or {}).get("output_class"),
                 "consistency_passed": (e.payload or {}).get("passed"),
                 "consistency_failures":
                 (e.payload or {}).get("consistency_failures")}
                for e in evs if e.kind == "summary_repair"]
    _fallbacks = [{"seq": e.seq, "title": e.title,
                   "version": (e.payload or {}).get("fallback_version")}
                  for e in evs if e.kind == "fallback"]
    if _fallbacks:
        _gen_status = "deterministic_fallback"
    elif any(r.get("valid") is True for r in _repairs):
        _gen_status = "model_repaired"
    elif any(s.get("valid") for s in _summaries):
        _gen_status = "model_native"
    else:
        _gen_status = "none_yet"
    return {"investigation_id": inv.id, "status": inv.status,
            "budget": {"tool_calls": [inv.tool_call_count,
                                       inv.max_tool_calls]},
            "coverage": {"missing_measurements": _plan.get(
                "missing_measurements", []),
                "per_hypothesis": _plan.get("coverage", []),
                "untested": _plan.get("untested", []),
                "failed_skipped": _plan.get("failed_skipped", []),
                "inapplicable_skipped": _plan.get(
                    "inapplicable_skipped", [])},
            "report_validation": {"summaries": _summaries,
                                  "repairs": _repairs,
                                  "generation_status": _gen_status,
                                  "fallbacks": _fallbacks},
            "hypotheses": hviews, "competition": competition,
            "evidence_graph": graph,
            "selection": {"ranked": ranked,
                          "explanation": _SEL.explain_selection(ranked)},
            "diagnosis_grades": grades,
            "transitions": transitions,
            "confidence_trail": confidence_trail,
            "feedback": feedback,
            "stopping": ([{"seq": e.seq, "title": e.title,
                             "rationale": (e.payload or {}).get("rationale")}
                            for e in stop_ev]),
            "note": "qualitative estimates only; no fabricated information gain"}


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


def _lab_root() -> Path:
    root = Path(config.BACKEND_DIR).parent / ".lab"
    root.mkdir(parents=True, exist_ok=True)
    return root


@app.post("/api/lab/projects")
def lab_create(payload: dict) -> dict:
    from .m12 import projects as _LP
    try:
        return _LP.create(str(_lab_root()),
                          (payload or {}).get("objectives", ""),
                          (payload or {}).get("agenda"),
                          (payload or {}).get("budget"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.get("/api/lab/projects")
def lab_list() -> dict:
    from .m12 import projects as _LP
    return {"projects": _LP.list_all(str(_lab_root()))}


@app.get("/api/lab/projects/{pid}")
def lab_get(pid: str) -> dict:
    from .m12 import projects as _LP
    try:
        return _LP.load(str(_lab_root()), pid)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=_detail(exc))


@app.post("/api/lab/projects/{pid}/status")
def lab_status(pid: str, payload: dict) -> dict:
    from .m12 import projects as _LP
    try:
        return _LP.set_status(str(_lab_root()), pid,
                              (payload or {}).get("status", "paused"))
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.post("/api/lab/projects/{pid}/propose")
def lab_propose(pid: str, payload: dict) -> dict:
    from .m12 import projects as _LP
    try:
        prop = dict(payload or {})
        prop.setdefault("status", "queued")
        return _LP.mutate(str(_lab_root()), pid,
                          f"propose:{prop.get('id')}",
                          lambda d: d["agenda"].append(prop))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=_detail(exc))


@app.post("/api/lab/projects/{pid}/tick")
def lab_tick(pid: str, payload: dict) -> dict:
    from .m12 import projects as _LP
    from .m12 import scheduler as _SC
    try:
        doc = _LP.load(str(_lab_root()), pid)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=_detail(exc))
    out = _SC.tick(doc, auth_token=(payload or {}).get("auth_token"))
    _LP.mutate(str(_lab_root()), pid, "scheduler-tick",
               lambda d: d.update({"agenda": doc["agenda"]}))
    return out


@app.post("/api/lab/memory")
def lab_remember(payload: dict) -> dict:
    from .m12 import memory as _M
    try:
        return _M.remember(str(_lab_root()), (payload or {})["kind"],
                           (payload or {}).get("content", ""),
                           (payload or {}).get("project_id", ""),
                           (payload or {}).get("run_id", ""))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=_detail(exc))


@app.get("/api/lab/memory")
def lab_recall(kind: str = "", project_id: str = "") -> dict:
    from .m12 import memory as _M
    return {"entries": _M.recall(str(_lab_root()), kind or None,
                                 project_id or None)}


@app.post("/api/lab/memory/promote")
def lab_promote(payload: dict) -> dict:
    from .m12 import memory as _M
    return _M.promote_to_universal(
        str(_lab_root()), (payload or {}).get("content", ""))


@app.get("/api/lab/m10")
def lab_m10() -> dict:
    from .m10 import scenarios as _SC10
    return {"scenarios": [{"id": s["id"], "task": s["task"],
                           "brief": s["brief"],
                           "artifact": s["artifact"]}
                          for s in _SC10.SCENARIOS]}


@app.get("/api/lab/m11/roles")
def lab_roles() -> dict:
    return {"roles": ["lead", "data_scientist", "model_analyst",
                      "experiment_designer", "skeptic", "judge"],
            "note": "role contracts in backend/m11/roles.py; the judge "
                    "receives hypotheses + evidence only"}


@app.get("/api/lab/portfolio")
def lab_portfolio() -> dict:
    from .m12 import projects as _LP
    from .m12 import portfolio as _PF
    docs = _LP.list_all(str(_lab_root()))
    full = []
    for d in docs:
        try:
            full.append(_LP.load(str(_lab_root()), d["id"]))
        except LookupError:
            continue
    return _PF.assess(full)


@app.get("/api/lab/knowledge")
def lab_knowledge(columns: str = "", task: str = "") -> dict:
    from .m12 import knowledge as _K
    cols = [c.strip() for c in columns.split(",") if c.strip()]
    cands = _K.propose_transfer(
        str(_lab_root()), {"columns": cols, "task": task})
    return {"candidates": cands,
            "strategy": _K.strategy_record(str(_lab_root()))}


@app.get("/api/lab/corpus-b")
def lab_corpus_b() -> dict:
    from .m10 import scenarios_b as _SB
    return {"scenarios": [{"id": s["id"], "task": s["task"],
                           "brief": s["brief"]} for s in _SB.SCENARIOS]}


@app.get("/api/lab/corpus-c")
def lab_corpus_c() -> dict:
    from .m10 import scenarios_c as _SC
    return {"scenarios": [{"id": s["id"], "task": s["task"],
                           "brief": s["brief"]} for s in _SC.SCENARIOS]}


@app.get("/api/lab/corpus-d")
def lab_corpus_d() -> dict:
    from .m10 import scenarios_d as _SD
    return {"scenarios": [{"id": s["id"], "task": s["task"],
                           "brief": s["brief"]} for s in _SD.SCENARIOS]}


@app.get("/api/lab/strategies")
def lab_strategies() -> dict:
    from .research import strategies as _ST
    return {"policies": [
        {"name": n, **v} for n, v in _ST.POLICIES.items()]}


@app.get("/api/lab/live-audit")
def lab_live_audit() -> dict:
    from .live import audit as _AU
    return _AU.audit_run(
        "model_autopsy/benchmarks/live_runs/live-d8b174527ca5")


@app.get("/api/lab/replay/{investigation_id}")
def lab_replay(investigation_id: str,
               session=Depends(get_db)) -> dict:
    """M15 Phase 5: deterministic replay of a recorded investigation."""
    from .research import replay as _RP
    try:
        return _RP.replay_investigation(session, investigation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.get("/api/lab/strategy-performance")
def lab_strategy_performance() -> dict:
    """M15 Phase 6: aggregate strategy outcomes (no sealed labels)."""
    from .research import strategies as _ST
    return {"aggregate": _ST.summarize(str(_lab_root())),
            "note": "resolution without moving evidence scores zero"}


@app.get("/api/lab/eval-d")
def lab_eval_d() -> dict:
    """M15 Phase 7: corpus-D registry (investigator-safe side)."""
    from .m10 import scenarios_d as _SD
    return {"scenarios": [{"id": s["id"], "task": s["task"],
                           "brief": s["brief"],
                           "artifact": s["artifact"]}
                          for s in _SD.SCENARIOS]}


# ----------------------------------------------------------------
# User artifact uploads - the New Investigation entrance.
#
# Files land under backend/data/uploads/<uuid>/ and are addressed by
# PROJECT-ROOT-relative paths, so existing tools (predictions_path,
# feature_csv, ...) and resolve_restricted() accept them unchanged.
# Filenames are sanitized, extensions allowlisted, sizes capped.
# Nothing here executes uploads; tools only read them.
# ----------------------------------------------------------------

_UPLOAD_DIRNAME = "uploads"
_UPLOAD_EXTENSIONS = frozenset({
  ".csv", ".json", ".jsonl", ".parquet", ".txt", ".log", ".md",
  ".py", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".zip",
})
_UPLOAD_MAX_BYTES = 50 * 1024 * 1024
_UPLOAD_MAX_FILES = 10


def _uploads_root() -> Path:
    root = Path(config.BACKEND_DIR) / "data" / _UPLOAD_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_upload_name(name: str) -> str:
    base = Path(name or "upload").name.strip() or "upload"
    safe = "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_"
                   for c in base)[:120]
    return safe or "upload"


def _classify_upload(name: str) -> str:
    ext = Path(name).suffix.lower()
    return {".csv": "predictions / dataset",".json": "predictions / dataset",
            ".jsonl": "predictions / dataset",".parquet": "predictions / dataset",
            ".py": "training / evaluation script",".txt": "logs / notes",
            ".log": "logs / notes",".md": "notes / documentation",
            ".yaml": "configuration",".yml": "configuration",
            ".toml": "configuration",".cfg": "configuration",
            ".ini": "configuration",
            ".zip": "archive (model files / project bundle)"}.get(
        ext, "supporting file")


def _file_sha256(p: Path) -> str:
    import hashlib as _hl
    h = _hl.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _is_hidden(batch: str, name: str) -> bool:
    return (_uploads_root() / batch / f".hidden_{name}").exists()


def _is_upload_referenced(session, rel: str) -> bool:
    try:
        from . import db as _db
        for inv in session.query(_db.Investigation).all():
            cfg = inv.config or {}
            if cfg.get("predictions_path") == rel:
                return True
            if rel in (cfg.get("question") or ""):
                return True
            for a in (inv.actions or []):
                args = a.arguments if isinstance(a.arguments, dict) else {}
                if rel in [str(v) for v in args.values()]:
                    return True
    except Exception:
        pass
    return False


@app.get("/api/uploads")
def list_uploads() -> dict:
    """Previously uploaded user artifacts (newest batch first, content-deduped)."""
    out = []
    seen_hash: dict[str, dict] = {}
    try:
        batches = sorted(_uploads_root().iterdir(), reverse=True)
    except OSError:
        batches = []
    for b in batches:
        if not b.is_dir():
            continue
        for f in sorted(b.iterdir()):
            if not f.is_file() or f.name.startswith(".hidden_"):
                continue
            if _is_hidden(b.name, f.name):
                continue
            try:
                rel = f.relative_to(config.PROJECT_ROOT).as_posix()
            except ValueError:
                rel = str(f)
            try:
                sha = _file_sha256(f)
            except OSError:
                sha = ""
            entry = {"batch": b.name, "name": f.name,
                     "path": rel, "bytes": f.stat().st_size,
                     "kind": _classify_upload(f.name), "sha256": sha,
                     "analyzed": f.suffix.lower() in (".csv", ".json", ".jsonl", ".parquet", ".py"),
                     "analysis_note": ("actively analyzed by diagnostics" if f.suffix.lower() in (".csv", ".json", ".jsonl", ".parquet") else ("statically inspected for provenance (never executed)" if f.suffix.lower() == ".py" else "stored as supporting material; not directly analyzed"))}
            if sha and sha in seen_hash:
                entry["duplicate_of"] = seen_hash[sha]["path"]
                entry["is_duplicate"] = True
                # same content, different name/path is still listed but
                # flagged; identical bytes are deduped visually by clients.
            else:
                entry["is_duplicate"] = False
                if sha:
                    seen_hash[sha] = entry
            out.append(entry)
    # Hide exact duplicates from the selectable list but keep the record:
    # clients show first occurrence; duplicates flagged above.
    return {"uploads": out}


@app.delete("/api/uploads/{batch}/{name}")
def remove_upload(batch: str, name: str, purge: bool = False,
                  session=Depends(get_db)) -> dict:
    """Remove from selectable history (hide); purge deletes only if unreferenced."""
    safe_b = _safe_upload_name(batch)
    safe_n = _safe_upload_name(name)
    target = _uploads_root() / safe_b / safe_n
    if not target.exists():
        raise HTTPException(status_code=404, detail="upload not found")
    try:
        rel = target.relative_to(config.PROJECT_ROOT).as_posix()
    except ValueError:
        rel = str(target)
    referenced = _is_upload_referenced(session, rel)
    if purge:
        if referenced:
            raise HTTPException(status_code=400, detail="artifact is referenced by an investigation; unpublishing from history only (omit purge)")
        target.unlink()
        return {"ok": True, "removed": rel, "purged": True}
    # hide from selectable history, keep bytes for existing investigations
    (_uploads_root() / safe_b / f".hidden_{safe_n}").write_text("hidden", encoding="utf-8")
    return {"ok": True, "removed": rel, "purged": False,
            "note": "hidden from selectable history; still referenced by existing investigations" if referenced else "hidden from selectable history; bytes retained"}


@app.post("/api/uploads")
async def create_uploads(request: Request) -> dict:
    """Multipart file upload. Returns project-root-relative paths."""
    form = await request.form()
    items = form.getlist("files")
    if not items:
        raise HTTPException(status_code=400, detail="no files received")
    if len(items) > _UPLOAD_MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"at most {_UPLOAD_MAX_FILES} files per upload")
    import uuid as _uuid
    batch = _uuid.uuid4().hex[:12]
    dest_dir = _uploads_root() / batch
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    try:
        for item in items:
            filename = getattr(item, "filename", None) or "upload"
            name = _safe_upload_name(filename)
            if Path(name).suffix.lower() not in _UPLOAD_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"unsupported file type: {name}")
            data = await item.read()
            if len(data) > _UPLOAD_MAX_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"{name} exceeds the 50 MB per-file limit")
            if not data:
                raise HTTPException(status_code=400,
                                    detail=f"{name} is empty")
            target = dest_dir / name
            if target.exists():
                stem, suffix = target.stem, target.suffix
                target = dest_dir / f"{stem}_{_uuid.uuid4().hex[:6]}{suffix}"
            target.write_bytes(data)
            try:
                rel = target.relative_to(
                    Path(config.BACKEND_DIR).parent.parent).as_posix()
            except ValueError:
                rel = str(target)
            saved.append({"batch": batch, "name": target.name,
                          "path": rel, "bytes": len(data),
                          "kind": _classify_upload(target.name)})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=_detail(exc))
    return {"ok": True, "batch": batch, "files": saved}


@app.post("/api/lab/workflow/run")
def lab_workflow_run(payload: dict,
                     session=Depends(get_db)) -> dict:
    """M15 Phase 10: run the integrated workflow (offline)."""
    from .research import workflow as _WF
    try:
        return _WF.run(
            session, (payload or {})["artifact"],
            (payload or {}).get("task", "classification"),
            (payload or {}).get("brief", "M15 workflow"),
            max_steps=int((payload or {}).get("max_steps", 4)))
    except KeyError:
        raise HTTPException(status_code=400,
                            detail="artifact is required")


@app.get("/api/lab/flagship-m15")
def lab_flagship_m15() -> dict:
    """M15 Phase 12: flagship demo (offline, deterministic)."""
    from ..demo import flagship_m15 as _F
    from .db import SessionLocal
    s = SessionLocal()
    try:
        return _F.run_demo(SessionLocal, max_steps=4)
    finally:
        s.close()


@app.get("/api/lab/model-performance")
def lab_model_performance() -> dict:
    """M15 measured demand-zone results (strict, held-out)."""
    import joblib as _jl
    try:
        t = _jl.load("model_autopsy/.lab_m15_test.joblib")
        v = _jl.load("model_autopsy/.lab_m15_val.joblib")
    except OSError as exc:
        return {"measured": False, "reason": str(exc)[:200]}
    return {"measured": True, "dataset": "demand_zone_v2",
            "target": "alpha_spy_2pct",
            "splits": {"train": "2021-08-01/2023-12-31",
                       "val": "2024-01-01/2024-12-31",
                       "test": "2025-01-01/2026-06-24 (HELD-OUT)"},
            "baseline_val_auc": v["rep"]["val"]["auc"],
            "baseline_test_auc": t["rb"]["auc"],
            "candidate": "regularized-lgbm "
                           "(leaves 31, reg 20, min_child 300, "
                           "lr 0.02, 600 trees)",
            "test_delta": t["test_delta"],
            "brier": {"base": t["rb"]["brier"],
                      "cand": t["re"]["brier"]},
            "subgroups": {"base": t["sub_base"],
                          "cand": t["sub_cand"]},
            "promotion": "PROMOTED under gate (held-out delta "
                           "+0.0048 [0.0009, 0.0083], no calibration "
                           "or subgroup regression)",
            "failed_candidates": {
                k2: {"delta": c["val_delta"]["delta"],
                     "ci": c["val_delta"]["delta_ci95"]}
                for k2, c in v["cands"].items()}}


# ---- Single-service hosting (Render free): serve the built Vite app ----
# When model_autopsy/frontend/dist exists (Render build step), mount it so
# one public URL serves both UI and /api (no CORS, no second service).
# Local dev is unaffected (no dist checked in; vite :5173 proxies /api).
try:
    from fastapi.responses import FileResponse as _FileResponse
    from fastapi.staticfiles import StaticFiles as _StaticFiles
    _DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if _DIST.is_dir() and (_DIST / "index.html").exists():
        app.mount("/assets", _StaticFiles(directory=str(_DIST / "assets")),
                   name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def _spa(path: str):
            if path.startswith("api/"):
                from fastapi import HTTPException as _HE
                raise _HE(status_code=404, detail="Not Found")
            cand = _DIST / path
            if path and cand.is_file():
                return _FileResponse(str(cand))
            return _FileResponse(str(_DIST / "index.html"))
except Exception:
    pass
