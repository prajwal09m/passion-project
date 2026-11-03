"""M12 persistent research projects (file-backed, crash-safe).

Each project is one JSON document under <root>/projects/<id>.json,
written atomically (tmp + rename). State machine:
active -> paused | awaiting-approval | completed | aborted.
Every mutation appends to history; experiment executions carry
idempotency keys so a retried resume never double-counts.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

STATES = ("active", "paused", "awaiting-approval", "completed",
          "aborted")


def root(base: str | Path = "model_autopsy/.lab") -> Path:
    p = Path(base) / "projects"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create(base, objectives: str, agenda: list[dict] | None = None,
           budget: dict | None = None) -> dict:
    pid = "proj_" + uuid.uuid4().hex[:10]
    doc = {"id": pid, "objectives": objectives,
           "status": "active", "agenda": agenda or [],
           "hypotheses": [], "experiments": [],
           "evidence": [], "decisions": [],
           "unresolved": [], "resource_usage": {"tool_calls": 0},
           "budget": budget or {"tool_calls": 20},
           "checkpoints": [], "idempotency_keys": [],
           "history": [{"t": time.time(), "event": "created"}]}
    _write(base, doc)
    return doc


def load(base, pid: str) -> dict:
    p = root(base) / f"{pid}.json"
    if not p.exists():
        raise LookupError(f"unknown project {pid}")
    return json.loads(p.read_text(encoding="utf-8"))


def _write(base, doc: dict) -> None:
    p = root(base) / f"{doc['id']}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    tmp.replace(p)


def mutate(base, pid: str, event: str, fn) -> dict:
    """Apply fn(doc), append history, persist atomically."""
    doc = load(base, pid)
    fn(doc)
    doc["history"].append({"t": time.time(), "event": event})
    _write(base, doc)
    return doc


def record_experiment(base, pid: str, tool: str, args: dict,
                      idempotency_key: str, result: dict) -> dict:
    """Idempotent: a retried key returns the original record."""
    doc = load(base, pid)

    def _fn(d):
        for e in d["experiments"]:
            if e.get("idempotency_key") == idempotency_key:
                return  # duplicate resume: keep the original
        d["experiments"].append({"tool": tool, "args": args,
                                  "idempotency_key": idempotency_key,
                                  "result": result,
                                  "t": time.time()})
        d["resource_usage"]["tool_calls"] += 1
        d["idempotency_keys"].append(idempotency_key)
    return mutate(base, pid, f"experiment:{tool}", _fn)


def checkpoint(base, pid: str, state: dict) -> dict:
    def _fn(d):
        d["checkpoints"].append({"t": time.time(), "state": state})
    return mutate(base, pid, "checkpoint", _fn)


def set_status(base, pid: str, status: str) -> dict:
    if status not in STATES:
        raise ValueError(f"bad status {status}")
    return mutate(base, pid, f"status->{status}",
                  lambda d: d.update({"status": status}))


def list_all(base) -> list[dict]:
    out = []
    for f in sorted(root(base).glob("proj_*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            out.append({"id": d["id"], "objectives": d["objectives"],
                        "status": d["status"],
                        "n_experiments": len(d.get("experiments", [])),
                        "n_unresolved": len(d.get("unresolved", []))})
        except OSError:
            continue
    return out
