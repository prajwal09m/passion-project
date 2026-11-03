"""M12 cumulative research memory (traceable, transfer-guarded).

Stores methods, findings, failures, confounders, replications, and
disagreements — each pinned to its project + run provenance.
Project-specific findings NEVER become universal rules without
independent replication in >=2 distinct projects (transfer guard).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

KINDS = ("method", "finding", "failure", "confounder",
         "replication", "disagreement")


def _path(base) -> Path:
    p = Path(base) / "memory.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def remember(base, kind: str, content: str, project_id: str,
             run_id: str) -> dict:
    if kind not in KINDS:
        raise ValueError(f"bad kind {kind}")
    entry = {"kind": kind, "content": content,
             "project_id": project_id, "run_id": run_id,
             "t": time.time(), "scope": "project"}
    with _path(base).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def recall(base, kind: str | None = None,
           project_id: str | None = None) -> list[dict]:
    p = _path(base)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if kind and e.get("kind") != kind:
            continue
        if project_id and e.get("project_id") != project_id:
            continue
        out.append(e)
    return out


def promote_to_universal(base, content: str) -> dict:
    """Transfer guard: >=2 replications in distinct projects required."""
    reps = [e for e in recall(base, "replication")
            if e.get("content") == content]
    projects = {e.get("project_id") for e in reps}
    if len(projects) < 2:
        return {"ok": False,
                "reason": f"only {len(projects)} independent project(s) "
                          f"replicated this; need >= 2 distinct projects",
                "projects": sorted(projects)}
    entry = {"kind": "method", "content": content,
             "project_id": "universal", "run_id": "promotion",
             "t": time.time(), "scope": "universal",
             "provenance": sorted(projects)}
    with _path(base).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return {"ok": True, "entry": entry}
