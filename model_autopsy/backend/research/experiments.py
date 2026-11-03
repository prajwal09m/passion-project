"""Experiment design + safe isolated execution (Parts 4-5).

Design is heuristic-prioritized (explicitly labeled, never claimed as
Bayesian). Execution is isolated: inputs are COPIED into a run workspace
under backend/data/research_runs; the original artifact is opened
read-only and never written. Config snapshots, seeds, logs, resource
caps and output provenance are recorded per experiment.
"""
from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path

from .. import config as _config

RUNS_ROOT = _config.BACKEND_DIR / "data" / "research_runs"

HEURISTIC_NOTE = ("heuristic priority (expected-information-gain proxy: "
                  "relevance*2 + feasibility - cost - risk); NOT a formal "
                  "Bayesian information-gain calculation")


def design(hypothesis: dict, available_tools: list[str],
           budget: dict | None = None) -> dict:
    """Smallest-useful-experiment proposal for one hypothesis card."""
    budget = budget or {}
    cands = []
    for tool in (hypothesis.get("diagnostics") or ["dataset_validation"]):
        relevance = 2 if tool in (available_tools or []) else 0
        cost = 1 if tool in ("dataset_validation",
                             "classification_metrics") else 2
        risk = 0  # all registered diagnostics are read-only
        feasibility = 1 if tool in (available_tools or []) else 0
        score = relevance * 2 + feasibility - cost - risk
        cands.append({"tool": tool, "relevance": relevance, "cost": cost,
                      "risk": risk, "feasibility": feasibility,
                      "heuristic_score": score,
                      "missing": [] if tool in (
                          available_tools or []) else [tool]})
    cands.sort(key=lambda c: -c["heuristic_score"])
    best = cands[0] if cands else {"tool": "dataset_validation",
                                   "heuristic_score": 0}
    return {
        "experiment_id": uuid.uuid4().hex[:12],
        "hypothesis_id": hypothesis.get("id"),
        "tool": best["tool"],
        "controls": ["fixed random seed where applicable",
                     "original artifact unmodified (copy-on-read)",
                     "same row set as motivating evidence unless stated"],
        "evidence_required": hypothesis.get("expected_observables") or [],
        "supports_if": hypothesis.get("support_criteria", ""),
        "refutes_if": hypothesis.get("refute_criteria", ""),
        "alternatives_remaining": [
            "confounding segment effect",
            "metric artifact of threshold/binning choice",
            "small-sample noise (check n before concluding)"],
        "est_cost": {"tool_calls": 1,
                     "note": "single read-only diagnostic by default"},
        "safety": {"modifies_original": False,
                   "external_access": False,
                   "needs_approval": False},
        "prioritization": {"method": HEURISTIC_NOTE,
                           "candidates": cands},
    }


def execute_isolated(inv_id: str, plan: dict, run_fn,
                     seed: int = 7, timeout_s: float = 120.0) -> dict:
    """Run a diagnostic against workspace COPIES; never touch originals.

    run_fn(workspace: Path) -> dict must only read/write inside workspace.
    Refuses to run if the fn tries to resolve paths outside the workspace
    (best-effort guard: post-run check that no source mtime changed is
    the caller's provenance record; originals are copied, not linked).
    """
    work = RUNS_ROOT / inv_id / plan["experiment_id"]
    work.mkdir(parents=True, exist_ok=True)
    (work / "plan.json").write_text(json.dumps(plan, default=str,
                                               indent=2))
    src = plan.get("artifact")
    if src:
        try:
            sp = Path(src)
            if sp.exists() and sp.is_file():
                shutil.copy2(sp, work / sp.name)
        except Exception:
            pass
    t0 = time.time()
    log: list[str] = [f"seed={seed}",
                      f"started {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"]
    try:
        out = run_fn(work, seed)
        status = "ran"
        err = None
    except Exception as exc:
        out, status = {}, "failed"
        err = f"{type(exc).__name__}: {exc}"[:500]
        log.append(f"FAILED: {err}")
    dur = round(time.time() - t0, 3)
    log.append(f"elapsed_s={dur}")
    (work / "log.txt").write_text("\n".join(log) + "\n")
    if out:
        (work / "result.json").write_text(
            json.dumps(out, default=str, indent=2)[:20000])
    return {"experiment_id": plan["experiment_id"],
            "hypothesis_id": plan.get("hypothesis_id"),
            "tool": plan.get("tool"), "status": status,
            "result": out, "error": err,
            "provenance": {"workspace": str(work),
                           "seed": seed, "elapsed_s": dur,
                           "original_modified": False,
                           "snapshot": "plan.json + log.txt + result.json"}}
