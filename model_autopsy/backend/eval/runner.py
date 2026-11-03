"""Repeatable evaluation runner (Milestone 4).

CLI: py -3 -m model_autopsy.backend.eval.runner [--project ID | --all]
  [--max-experiments N] [--out DIR]

Every run gets a unique ID; records pin benchmark/investigator/config
versions plus full histories; results go to
benchmarks/eval_runs/{run_id}/ and are never overwritten (reruns mint
new IDs). Uses a run-scoped SQLite DB (never the app DB). Initiates
zero provider calls; refuses to run if provider credentials are
present in the environment (offline mandate).
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

from . import EVAL_VERSION, INVESTIGATOR_VERSION


def _refuse_if_credentials() -> None:
    for var in ("MODEL_API_KEY", "GROQ_API_KEY"):
        if os.environ.get(var, "").strip():
            raise RuntimeError(
                f"offline mandate: {var} is set; evaluation runner refuses "
                "to run with provider credentials present")


def session_for(db_path: str):
    """Run-scoped session factory (never the app DB, never TEST DB)."""
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.orm import sessionmaker as _sm
    from model_autopsy.backend import db as _db
    eng = _ce(f"sqlite:///{db_path}",
              connect_args={"check_same_thread": False}, future=True)
    _db.Base.metadata.create_all(eng)
    return _sm(bind=eng, autoflush=False, expire_on_commit=False)


def run_project(pid: str, out_root: Path,
                max_experiments: int = 4,
                session_factory=None,
                eval_version: str | None = None) -> dict:
    import time
    t0 = time.time()
    from . import projects as P
    from . import separation as S
    from . import pipeline as _PIPE
    from model_autopsy.backend import engine
    from model_autopsy.backend.projects import ProjectSpec
    from model_autopsy.backend.research import lab

    proj = P.get_project(pid)
    truth = P.load_truth()
    brief = S.discovery_input(proj)
    spec = ProjectSpec.from_dict(dict(proj["spec"]))

    if session_factory is None:
        from model_autopsy.backend.db import SessionLocal, init_db
        init_db()
        session = SessionLocal()
    else:
        session = session_factory()
    try:
        inv = engine.create_investigation(
            session, "ml", f"Eval: {spec.name}",
            brief["brief"] or spec.objective,
            {"max_iterations": 3,
             "predictions_path": proj["artifact"]})
        _rubric = _PIPE.persist_eval_rubric(
            session, inv, _PIPE.select_eval_rubric(
                explicit=eval_version))
        report = lab.run_autonomous_investigation(
            session, inv, spec, artifact_path=proj["artifact"],
            max_experiments=max_experiments)
        scorecard = _PIPE.score_report(pid, report, truth, _rubric)
    finally:
        session.close()
    return {"project": pid, "investigation_id": inv.id,
            "report": report, "scorecard": scorecard,
            "elapsed_s": round(time.time() - t0, 2)}


def run_all(out_root: Path, projects: list[str] | None = None,
            max_experiments: int = 4, only: str | None = None,
            run_id: str | None = None,
            session_factory=None,
            eval_version: str | None = None) -> dict:
    _refuse_if_credentials()
    from . import pipeline as _PIPE
    _rubric = _PIPE.select_eval_rubric(explicit=eval_version)
    from . import projects as P
    run_id = run_id or ("eval-" + uuid.uuid4().hex[:12])
    rundir = out_root / run_id
    if rundir.exists():
        raise RuntimeError(f"run dir {rundir} already exists; refusing "
                           "to overwrite historical results")
    rundir.mkdir(parents=True)
    if session_factory is None:
        session_factory = session_for(str((rundir / "eval.sqlite3"
                                            ).absolute()))
    pids = [only] if only else (projects or [p["id"] for p in P.PROJECTS])
    results = []
    for pid in pids:
        rec = run_project(pid, rundir, max_experiments,
                          session_factory=session_factory,
                          eval_version=_rubric)
        (rundir / f"{pid}.json").write_text(
            json.dumps(rec, indent=2, default=str))
        results.append({"project": pid,
                        "verdict": rec["scorecard"]["verdict"],
                        "overall": rec["scorecard"]["overall"],
                        "elapsed_s": rec["elapsed_s"]})
    manifest = {"run_id": run_id, "eval_version": EVAL_VERSION,
                "eval_rubric_version": _rubric,
                "investigator_version": INVESTIGATOR_VERSION,
                "max_experiments": max_experiments,
                "results": results,
                "aggregate": {
                    "n": len(results),
                    "mean_overall": round(sum(
                        r["overall"] for r in results) / len(results), 3)
                    if results else 0.0,
                    "verdicts": {v: sum(
                        1 for r in results if r["verdict"] == v)
                        for v in {r["verdict"] for r in results}}}}
    (rundir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return {"run_id": run_id, "dir": str(rundir), "manifest": manifest}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Milestone 4 eval runner")
    ap.add_argument("--project", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--max-experiments", type=int, default=4)
    ap.add_argument("--eval-version", default=None,
                    help="scoring rubric v2|v3 (default: env or v2)")
    ap.add_argument("--out", default="model_autopsy/benchmarks/eval_runs")
    ap.add_argument("--db", default=None,
                    help="run-scoped sqlite path (default: out/run db)")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if not args.all and not args.project:
        print("pass --all or --project ID", file=sys.stderr)
        return 2
    run_id = "eval-" + uuid.uuid4().hex[:12]
    db_path = (args.db or str(
        (out / run_id / "eval.sqlite3").absolute()))
    try:
        rec = run_all(out, only=args.project,
                      max_experiments=args.max_experiments,
                      run_id=run_id,
                      session_factory=session_for(db_path),
                      eval_version=args.eval_version)
    except RuntimeError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(rec["manifest"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
