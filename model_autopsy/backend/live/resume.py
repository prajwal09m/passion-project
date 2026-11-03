"""Resume an interrupted live run (M6 continuation authorization).

Reuses the exact driver/loop/recorder/scorer path — no methodology
change. Refuses unless the run is verifiably resumable (see
`reconcile()`): same run ID, same DB, same investigation, no manifest,
no dangling provider request, investigation not terminal.

Usage:
  py -3 -m model_autopsy.backend.live.resume <run_dir> [--check-only]
`--check-only` performs reconcile + preflight and exits before any
provider request (fully offline).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _payload(row) -> dict:
    p = row["payload"] if isinstance(row, dict) else row
    if isinstance(p, str):
        try:
            return json.loads(p)
        except (json.JSONDecodeError, TypeError):
            return {}
    return p or {}


def reconcile(run_dir: Path) -> dict:
    """Offline recovery plan from durable events. Sends no requests."""
    import sqlite3
    run_dir = Path(run_dir)
    live_db = run_dir / "live.sqlite3"
    if not live_db.exists():
        raise RuntimeError(f"no live.sqlite3 in {run_dir}")
    if (run_dir / "manifest.json").exists():
        raise RuntimeError("manifest exists: run already finalized, nothing to resume")
    c = sqlite3.connect(str(live_db))
    c.row_factory = sqlite3.Row
    invs = c.execute("select * from investigations").fetchall()
    if len(invs) != 1:
        raise RuntimeError(f"expected exactly 1 investigation, found {len(invs)}")
    inv = dict(invs[0])
    if inv["status"] in ("complete", "failed", "stopped"):
        raise RuntimeError(f"investigation is {inv['status']}: terminal, refusing resume")
    cfg = inv.get("config") or {}
    if isinstance(cfg, str):
        cfg = json.loads(cfg)
    pid = ((cfg.get("live") or {}).get("eval_project")
           or cfg.get("eval_project"))
    if not pid:
        raise RuntimeError("eval project not recorded in investigation config")
    # Evaluation rubric version: persisted selection wins; historical
    # version-less records resolve to v2 (backward compatible); corrupt
    # identifiers refuse resume (fail safe, never silent switch).
    stored_version = cfg.get("eval_rubric_version")
    if stored_version is None:
        eval_rubric = "v2"
    else:
        eval_rubric = str(stored_version).strip().lower()
        if eval_rubric not in ("v2", "v3"):
            raise RuntimeError(
                f"stored eval rubric version {stored_version!r} is invalid: "
                "refusing resume with an ambiguous rubric")
    events = [dict(r) for r in c.execute(
        "select seq,kind,title,detail,payload from events order by seq").fetchall()]
    # Dangling-request check: every meta_request must be followed (by row
    # order) by a meta_response, a fallback note, or an unavailable note
    # before the next meta_request — else the outcome is ambiguous.
    open_req = None
    for e in events:
        if e["kind"] == "meta_request" and e["title"].startswith("Meta round"):
            if open_req is not None:
                raise RuntimeError(
                    f"dangling meta_request at seq {open_req}: refusing resume")
            open_req = e["seq"]
        elif e["kind"] in ("meta_response",):
            open_req = None
    if open_req is not None:
        raise RuntimeError(
            f"dangling meta_request at seq {open_req}: refusing resume")
    responses = [e for e in events if e["kind"] == "meta_response"]
    if not responses:
        raise RuntimeError("no completed provider response to chain from")
    last = responses[-1]
    last_payload = _payload(last["payload"])
    response_id = last_payload.get("response_id")
    if not response_id:
        raise RuntimeError("last meta_response carries no usable response id")
    # Budget rebuild: completed-turn rollups + post-rollup partial activity.
    rollups = [e for e in events if e["kind"] == "meta_usage"]
    rounds_done = len(rollups)
    attempts = input_tok = cached_tok = output_tok = 0
    exp_from_rollups = 0
    for r in rollups:
        p = _payload(r["payload"])
        attempts += int(p.get("api_attempts") or 0)
        exp_from_rollups += int(p.get("tool_calls_executed") or 0)
        t = p.get("tokens") or {}
        input_tok += int(t.get("input_tokens") or 0)
        cached_tok += int(t.get("input_tokens_details.cached_tokens") or 0)
        output_tok += int(t.get("output_tokens") or 0)
    last_roll_seq = rollups[-1]["seq"] if rollups else -1
    partial_attempts = 0
    for e in events:
        if e["seq"] <= last_roll_seq:
            continue
        if e["kind"] == "meta_response":
            p = _payload(e["payload"])
            u = p.get("usage") or {}
            input_tok += int(u.get("input_tokens") or 0)
            cached_tok += int(u.get("input_tokens_details.cached_tokens") or 0)
            output_tok += int(u.get("output_tokens") or 0)
            partial_attempts += 1
        if (e["kind"] == "meta_request"
                and "Continuation state refused" in (e["title"] or "")):
            partial_attempts += 1  # refused call: no usage, count the attempt
    attempts += partial_attempts
    tool_count = int(inv.get("tool_call_count") or 0)
    c.close()
    return {"run_id": run_dir.name, "pid": pid,
            "eval_rubric_version": eval_rubric,
            "investigation_id": inv["id"],
            "inv_status": inv["status"],
            "response_id": response_id,
            "rounds_done": rounds_done,
            "experiments_done": tool_count,
            "rollup_experiments": exp_from_rollups,
            "attempts_done": attempts,
            "input_tokens": input_tok, "cached_tokens": cached_tok,
            "output_tokens": output_tok}


def resume_live_investigation(run_dir: str | Path,
                              max_total_rounds: int = 3) -> dict:
    """Resume the exact interrupted run in place. See module docstring."""
    import time
    run_dir = Path(run_dir)
    plan = reconcile(run_dir)
    from .. import config as C
    from .. import engine
    from ..db import record_event
    from ..eval import projects as P
    from ..eval import runner as R
    from .driver import preflight
    from ..meta_api import loop as meta_loop
    from .governor import Budget
    from .recorder import finalize_run

    t0 = time.time()
    pf = preflight(plan["pid"], run_dir.parent)
    if not pf["go"]:
        raise RuntimeError(f"preflight refused resume: {pf['reason']}")
    if (C.meta_model_id() != "muse-spark-1.3"
            or not C.meta_base_url().startswith("https://api.meta.ai")):
        raise RuntimeError("model/endpoint drift detected: refusing resume")

    factory = R.session_for(str((run_dir / "live.sqlite3").absolute()))
    session = factory()
    budget = Budget()
    budget.rounds_used = plan["rounds_done"]
    budget.experiments_used = plan["experiments_done"]
    budget.attempts_used = plan["attempts_done"]
    budget.input_tokens = plan["input_tokens"]
    budget.cached_tokens = plan["cached_tokens"]
    budget.output_tokens = plan["output_tokens"]
    proj = P.get_project(plan["pid"])
    truth = P.load_truth()
    status = "resumed"
    message_text = ""
    summary: dict = {"valid": False, "summary": None, "errors": []}
    response_id: str | None = plan["response_id"]
    iters_done = plan["rounds_done"]
    # The interrupted turn's tool result was never delivered as a
    # function_call_output; the chained turn carries the ledger digest,
    # and the loop's built-in fallback covers a continuation refusal.
    (run_dir / "resumption.json").write_text(json.dumps(
        {"plan": plan, "resumed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                  time.gmtime()),
         "note": ("same run ID, same DB, same investigation; no replayed "
                  "requests or re-executed tools; budget carried over")},
        indent=1), encoding="utf-8")
    try:
        inv = session.get(engine.Investigation, plan["investigation_id"])
        if inv is None:
            raise RuntimeError("investigation row vanished")
        from ..eval import pipeline as _EVALPIPE
        # Stored version wins over any global config change; corrupt
        # stored identifiers refuse (fail safe).
        _rubric = _EVALPIPE.select_eval_rubric(inv=inv)
        if _rubric != plan.get("eval_rubric_version"):
            raise RuntimeError(
                f"rubric mismatch: reconcile saw "
                f"{plan.get('eval_rubric_version')}, stored is {_rubric}")
        record_event(session, inv.id, "status_change",
                     f"Run resumed from interruption "
                     f"(chained from {response_id[:12]}…; "
                     f"budget carried: {budget.attempts_used}/12 attempts, "
                     f"${budget.cost_usd():.4f}/$0.40)")
        session.commit()
        fallback: dict | None = None
        stalls = 0
        from ..db import Action as _Action
        while iters_done < max_total_rounds:
            try:
                budget.check(rounds=1, experiments=1)
            except Exception as _pre:
                from .governor import BudgetExceeded as _BE
                if isinstance(_pre, _BE):
                    record_event(session, inv.id, "stopping",
                                 f"Stopping early: budget exhausted: {_pre}",
                                 payload={"rationale": str(_pre)})
                    session.commit()
                    status = "evidence_interpretation"
                    break
                raise
            if iters_done >= 1:
                from ..db import Hypothesis as _Hypothesis
                from ..causal import planning as _planning
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
                _Action.investigation_id == plan["investigation_id"],
                _Action.status == "ran").count()
            status = "hypothesis_generation"
            turn = meta_loop.run_meta_turn(
                session, inv, max_rounds=2,
                previous_response_id=response_id,
                experiments_left=budget.caps["experiments"]
                - budget.experiments_used,
                budget=budget)
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
                _Action.investigation_id == plan["investigation_id"],
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
                # M22 P0 evidence floor (mirrors driver): report validity
                # is not investigation completion.
                _ran_total = session.query(_Action).filter(
                    _Action.investigation_id == plan["investigation_id"],
                    _Action.status == "ran").count()
                if _ran_total > 0:
                    break
                record_event(session, inv.id, "decision_prompt",
                             "Valid summary but no diagnostic evidence — "
                             "continuing investigation",
                             payload={"ran_actions": 0,
                                      "rounds_done": iters_done})
                session.commit()
        status = "final_reporting" if status not in (
            "failed", "meta_unavailable") else status
        # Verification parity with the live driver: bounded, recorded,
        # never throws past this point (failure recorded, report proceeds).
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
        engine.ensure_finalizable(session, inv)
        report = engine.build_report(session, inv)
        final = engine.finalize(session, inv, report)
        status = "scoring"
        from .adapter import meta_report_to_eval
        eval_report = meta_report_to_eval(session, inv, final,
                                          message_text, summary,
                                          fallback=fallback)
        scorecard = _EVALPIPE.score_report(plan["pid"], eval_report,
                                            truth, _rubric)
        try:
            from ..eval import m6_scorer as M6
            m6 = M6.score_m6(plan["pid"], eval_report, truth)
            (run_dir / "m6_scorecard.json").write_text(
                json.dumps(m6, indent=2), encoding="utf-8")
        except Exception:
            pass
        # M22 P0: an evidence-less run is never a successful completion.
        _ran_final = session.query(_Action).filter(
            _Action.investigation_id == plan["investigation_id"],
            _Action.status == "ran").count()
        if _ran_final == 0:
            record_event(session, inv.id, "status_change",
                         "Run inconclusive: no diagnostic evidence recorded",
                         payload={"ran_actions": 0})
            session.commit()
            status = "inconclusive"
        else:
            status = "completed"
    except Exception as exc:
        from .governor import BudgetExceeded
        if isinstance(exc, BudgetExceeded):
            record_event(session, inv.id, "status_change",
                         f"Budget cap reached: {exc}")
            session.commit()
            status = "inconclusive"
            eval_report, scorecard = None, None
        else:
            try:
                record_event(session, inv.id, "status_change",
                             f"Resumed run failed: "
                             f"{type(exc).__name__}: {exc}"[:300])
                session.commit()
            except Exception:
                pass
            status = "failed"
            eval_report, scorecard = None, None
            finalize_run(run_dir, plan["run_id"], plan["pid"], plan[
                "investigation_id"], session, budget, status, None, None,
                message_text,
                error=f"{type(exc).__name__}: {exc}"[:300],
                eval_version=plan.get("eval_rubric_version"))
            session.close()
            raise
    manifest = finalize_run(
        run_dir, plan["run_id"], plan["pid"], plan["investigation_id"],
        session, budget, status, eval_report, scorecard, message_text,
        eval_version=plan.get("eval_rubric_version"))
    session.close()
    return {"run_id": plan["run_id"], "dir": str(run_dir), "status": status,
            "budget": budget.ledger(),
            "elapsed_s": round(time.time() - t0, 2),
            "manifest": manifest}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Resume an interrupted live run")
    ap.add_argument("run_dir", help="Existing run directory (same run, resumed)")
    ap.add_argument("--check-only", action="store_true",
                    help="Reconcile + preflight only; send no requests")
    ap.add_argument("--max-total-rounds", type=int, default=3)
    args = ap.parse_args(argv)
    from .. import config as _C
    _C.bootstrap_env()
    try:
        plan = reconcile(Path(args.run_dir))
    except RuntimeError as exc:
        print(f"REFUSED: {exc}")
        return 2
    print(f"PLAN: run={plan['run_id']} project={plan['pid']} "
          f"status={plan['inv_status']} rounds_done={plan['rounds_done']} "
          f"experiments={plan['experiments_done']} "
          f"attempts={plan['attempts_done']} "
          f"tokens={plan['input_tokens']}/{plan['cached_tokens']}c/"
          f"{plan['output_tokens']}")
    print(f"CHAIN: {plan['response_id'][:16]}… (last completed response)")
    if args.check_only:
        from .driver import preflight
        pf = preflight(plan["pid"], Path(args.run_dir).parent)
        print(f"PREFLIGHT: go={pf['go']} reason={pf.get('reason')}")
        return 0 if pf["go"] else 2
    try:
        rec = resume_live_investigation(args.run_dir,
                                        max_total_rounds=args.max_total_rounds)
    except RuntimeError as exc:
        print(f"Run failed (preserved where possible): {exc}")
        return 1
    print(f"STATUS: {rec['status']}  run={rec['run_id']}")
    print(f"BUDGET: {rec['budget']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
