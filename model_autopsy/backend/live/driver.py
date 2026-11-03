"""Live investigation driver (Milestone 5, §4-6).

One pilot: recon (neutral brief + real schema) → ≤3 chained Meta turns →
freeze report → independent M4 scoring (post-freeze only). Meta is never
handed hypotheses, mechanisms, or ground truth; the backend never
confirms anything on Meta's behalf. Stops on caps, on Meta's own stop,
or on insufficient evidence — a forced discovery is a failure mode.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from . import LIVE_VERSION
from .governor import Budget, BudgetExceeded, project_cost_brief


def _neutral_title(project: dict) -> str:
    return f"Live pilot: {project['spec']['name']}"


def build_live_context(session, inv, project: dict, brief: str) -> dict:
    """Recon: neutral brief + real artifact schema + tool contract.

    Contains no mechanism words, no ground truth, no reference solution.
    Recorded as an event so the exact Meta input is auditable."""
    import pandas as pd
    from ..db import record_event
    from .. import tools_registry
    frame = pd.read_csv(project["artifact"], nrows=5)
    context = {
        "project": project["spec"]["name"],
        "task": project["spec"]["task_type"],
        "objective": brief,
        "target_definition": project["spec"]["target_definition"],
        "evaluation_methodology":
            project["spec"]["evaluation_methodology"],
        "artifact": project["artifact"],
        "columns": list(frame.columns),
        "sample_rows": frame.to_dict(orient="records"),
        "model": {"name": project["spec"]["model"]["name"],
                  "framework": project["spec"]["model"]["framework"],
                  "availability":
                      project["spec"]["model"]["availability"]},
        "tools_available": sorted(
            t["name"] for t in tools_registry.meta_tool_schemas("ml")),
        "instruction": ("Investigate this project with the available "
                        "diagnostic tools. Column names: label/score for "
                        "classification; target/prediction for regression "
                        "and forecasting; date for time fields; split for "
                        "split hygiene. Pass explicit column arguments; "
                        "defaults refer to a different case study."),
    }
    inv.config = {**(inv.config or {}), "context": context,
                  "live": {"eval_project": project["id"],
                           "version": LIVE_VERSION}}
    session.commit()
    record_event(session, inv.id, "tool_result",
                 "Live recon context prepared (neutral brief + schema)",
                 payload={"columns": context["columns"],
                          "tools": context["tools_available"]})
    session.commit()
    return context


def preflight(pid: str, out_root: Path) -> dict:
    """All gates BEFORE any live request. Any failure aborts launch."""
    from .. import config as C
    from ..eval import projects as P
    from ..eval import separation as S
    # Reuse the campaigns' secure .env mechanism (model_autopsy/.env,
    # setdefault semantics, never echoes values) BEFORE reading key
    # availability. No requests are sent here.
    C.bootstrap_env()
    checks: dict = {}
    try:
        proj = P.get_project(pid)
        checks["project_known"] = True
    except LookupError as exc:
        return {"go": False, "reason": str(exc)}
    audit = S.audit_investigator_env()
    checks["separation_audit"] = audit
    key = C.meta_api_key()
    checks["key_configured"] = bool(key)
    checks["model"] = C.meta_model_id()
    checks["endpoint"] = C.meta_base_url() + "/responses"
    art = Path(proj["artifact"])
    checks["artifact_readable"] = art.exists()
    brief_len = len(S.discovery_input(proj)["brief"]) + 4000
    checks["cost_projection"] = project_cost_brief(brief_len)
    rundir = out_root / "PENDING"
    try:
        out_root.mkdir(parents=True, exist_ok=True)
        checks["preservation_writable"] = True
    except OSError as exc:
        checks["preservation_writable"] = f"NO: {exc}"
    go = (audit["ok"] and bool(key) and art.exists()
          and checks["cost_projection"]["within_cap"]
          and checks["preservation_writable"] is True)
    reason = None
    if not go:
        missing = [k for k, v in checks.items()
                   if v is False or (isinstance(v, dict)
                                     and v.get("within_cap") is False)]
        reason = f"preflight blocked: {missing}"
    return {"go": go, "reason": reason, "checks": checks,
            "run_hint": str(rundir)}


def run_live_investigation(pid: str, out_root: Path,
                           max_rounds: int = 3,
                           run_id: str | None = None,
                           skeptic_enabled: bool = True) -> dict:
    """Execute exactly one live pilot. Raises BudgetExceeded on caps;
    never retries automatically; preserves whatever exists on failure."""
    import time
    from .. import engine
    from ..db import record_event
    from ..eval import projects as P
    from ..eval import runner as R
    from ..eval import separation as S
    from ..eval import pipeline as _EVALPIPE
    from ..meta_api import loop as meta_loop
    from .governor import Budget
    from .recorder import finalize_run

    t0 = time.time()
    pf = preflight(pid, out_root)
    if not pf["go"]:
        raise RuntimeError(f"preflight refused launch: {pf['reason']}")
    run_id = run_id or ("live-" + uuid.uuid4().hex[:12])
    rundir = out_root / run_id
    if rundir.exists():
        raise RuntimeError(f"run dir {rundir} exists; refusing to overwrite")
    rundir.mkdir(parents=True)

    proj = P.get_project(pid)
    truth = P.load_truth()
    brief = S.discovery_input(proj)["brief"]
    factory = R.session_for(str((rundir / "live.sqlite3").absolute()))
    session = factory()
    budget = Budget()
    status = "initializing"
    message_text = ""
    summary: dict = {"valid": False, "summary": None, "errors": []}
    fallback: dict | None = None
    response_id: str | None = None
    _rubric: str | None = None
    try:
        inv = engine.create_investigation(
            session, "ml", _neutral_title(proj), brief,
            {"max_iterations": 3, "predictions_path": proj["artifact"],
             "live_run": run_id, "eval_project": pid,
             "m16_skeptic": bool(skeptic_enabled),
             "m16_arm": "C" if skeptic_enabled else "B"})
        _rubric = _EVALPIPE.persist_eval_rubric(
            session, inv, _EVALPIPE.select_eval_rubric())
        status = "reconnaissance"
        build_live_context(session, inv, proj, brief)
        from ..db import Hypothesis as _Hypothesis
        from ..causal import planning as _planning
        iters_done = 0
        stalls = 0
        from ..db import Action as _Action
        for _ in range(max_rounds):
            # M8: every hard ceiling enforced BEFORE dispatch. An
            # exhausted experiment budget stops the loop (final report
            # still produced) instead of overrunning it.
            try:
                budget.check(rounds=1, experiments=1)
            except BudgetExceeded as _pre:
                record_event(session, inv.id, "stopping",
                             f"Stopping early: budget exhausted: {_pre}",
                             payload={"rationale": str(_pre)})
                session.commit()
                status = "evidence_interpretation"
                break
            if iters_done >= 1:
                _hvs = [{"id": h.id, "text": h.text,
                         "status": h.status,
                         "evidence_refs": h.evidence_refs or []}
                        for h in session.query(_Hypothesis).filter(
                            _Hypothesis.investigation_id == inv.id).all()]
                _stop, _why = _planning.stopping(
                    inv.status, _hvs, inv.tool_call_count,
                    inv.max_tool_calls, iters_done)
                if _stop:
                    record_event(session, inv.id, "stopping",
                                 f"Stopping early: {_why}",
                                 payload={"rationale": _why})
                    session.commit()
                    status = "evidence_interpretation"
                    break
            _ran_before = session.query(_Action).filter(
                _Action.investigation_id == inv.id,
                _Action.status == "ran").count()
            status = "hypothesis_generation"
            turn = meta_loop.run_meta_turn(
                session, inv, max_rounds=2,
                previous_response_id=response_id,
                experiments_left=budget.caps["experiments"]
                - budget.experiments_used,
                budget=budget)
            # M8: attempts/experiments already settled per-op inside the
            # turn; fold rounds + tokens only (fold_work=False avoids
            # double counting).
            budget.record_turn(turn.get("usage_rollup") or {},
                               fold_work=False)
            iters_done += 1
            response_id = turn.get("response_id") or response_id
            message_text = turn.get("message_text") or message_text
            summary = turn.get("summary") or summary
            fallback = turn.get("fallback") or fallback
            status = "evidence_interpretation"
            if turn.get("status") == "budget_exceeded":
                record_event(session, inv.id, "stopping",
                             "Stopping early: turn hit a hard budget "
                             f"ceiling ({turn.get('error') or 'cap'})")
                session.commit()
                break
            _ran_after = session.query(_Action).filter(
                _Action.investigation_id == inv.id,
                _Action.status == "ran").count()
            stalls = stalls + 1 if _ran_after == _ran_before else 0
            if stalls >= 2:
                record_event(session, inv.id, "stopping",
                             "Stopping early: two consecutive turns "
                             "produced no new evidence",
                             payload={"rationale": "two evidence-less "
                                      "turns; further requests unlikely to "
                                      "change the conclusion"})
                session.commit()
                status = "evidence_interpretation"
                break
            if turn.get("status") != "ok":
                status = turn.get("status", "failed")
                break
            if not turn.get("tool_calls") and summary.get("valid"):
                # M22 P0 evidence floor: a valid report is not a completed
                # investigation. Break only with diagnostic evidence on
                # record; otherwise continue — the stall rule still bounds
                # the run and stops honestly with a recorded reason.
                _ran_total = session.query(_Action).filter(
                    _Action.investigation_id == inv.id,
                    _Action.status == "ran").count()
                if _ran_total > 0:
                    break
                record_event(session, inv.id, "decision_prompt",
                             "Valid summary but no diagnostic evidence — "
                             "continuing investigation",
                             payload={"ran_actions": 0,
                                      "rounds_done": iters_done})
                session.commit()
        # M17 Phase 2: budgeted verification + resolution contract from
        # recorded state. Never throws: a caller failure is recorded and
        # the deterministic report path proceeds regardless.
        try:
            from . import verification as _verify_live
            _verify_live.run_verification_phase(
                session, inv, budget,
                experiments_left=budget.caps["experiments"]
                - budget.experiments_used,
                artifact=proj["artifact"])
        except Exception as _vexc:
            record_event(session, inv.id, "verification",
                         "Verification caller failed: "
                         f"{type(_vexc).__name__}",
                         payload={"reason": str(_vexc)[:200]})
            session.commit()
        status = "final_reporting" if status not in (
            "failed", "meta_unavailable") else status
        # Legal FSM walk before finalization via the single shared helper
        # (same path as the report endpoint; never skip stages).
        engine.ensure_finalizable(session, inv)
        report = engine.build_report(session, inv)
        final = engine.finalize(session, inv, report)
        status = "scoring"
        from .adapter import meta_report_to_eval
        eval_report = meta_report_to_eval(session, inv, final,
                                          message_text, summary,
                                          fallback=fallback)
        scorecard = _EVALPIPE.score_report(pid, eval_report, truth,
                                            _rubric)
        # M22 P0: an evidence-less run is never a successful completion.
        _ran_final = session.query(_Action).filter(
            _Action.investigation_id == inv.id,
            _Action.status == "ran").count()
        if _ran_final == 0:
            record_event(session, inv.id, "status_change",
                         "Run inconclusive: no diagnostic evidence recorded",
                         payload={"ran_actions": 0})
            session.commit()
            status = "inconclusive"
        else:
            status = "completed"
    except BudgetExceeded as exc:
        record_event(session, inv.id, "status_change",
                     f"Budget cap reached: {exc}")
        session.commit()
        status = "inconclusive"
        eval_report, scorecard = None, None
    except Exception as exc:
        try:
            record_event(session, inv.id, "status_change",
                         f"Live run failed: {type(exc).__name__}: {exc}"[:300])
            session.commit()
        except Exception:
            pass
        status = "failed"
        eval_report, scorecard = None, None
        finalize_run(rundir, run_id, pid, inv.id if "inv" in dir() else None,
                     session if "session" in dir() else None, budget,
                     status, None, None, message_text,
                     error=f"{type(exc).__name__}: {exc}"[:300],
                     eval_version=_rubric)
        session.close()
        raise
    manifest = finalize_run(
        rundir, run_id, pid, inv.id, session, budget, status,
        eval_report, scorecard, message_text, eval_version=_rubric)
    session.close()
    return {"run_id": run_id, "dir": str(rundir), "status": status,
            "budget": budget.ledger(),
            "elapsed_s": round(time.time() - t0, 2),
            "manifest": manifest}
