"""M13 §5.1-5.3 structured research knowledge (extends M12 memory).

Categories: diagnostic-method, experiment-design, limitation,
failure-pattern, statistical-lesson, tool-reliability,
failed-approach, confounder, strategy, observation. Every record
carries source project, evidence, validation status, confidence,
scope, conditions, limitations, and replication status.

Transfer evaluation (M13 §5.2): propose_transfer() surfaces
candidate knowledge for a new project with similarity notes;
the transfer is a HYPOTHESIS — record_transfer_outcome() logs
whether project-specific evidence confirmed it (helped) or not
(misled). Strategies accumulate outcome histories; nothing here
rewrites scientific thresholds (no adaptive policy touches
linker/attribution/invention gates).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

CATEGORIES = ("diagnostic-method", "experiment-design", "limitation",
              "failure-pattern", "statistical-lesson",
              "tool-reliability", "failed-approach", "confounder",
              "strategy", "observation")

VALIDATION = ("unvalidated", "single-project", "replicated",
              "universal")


def _path(base) -> Path:
    p = Path(base) / "knowledge.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def store(base, category: str, content: str, source_project: str,
          evidence: dict | None = None, confidence: float = 0.5,
          scope: str = "project", conditions: str = "",
          limitations: str = "") -> dict:
    if category not in CATEGORIES:
        raise ValueError(f"bad category {category}")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be in [0,1]")
    entry = {"category": category, "content": content,
             "source_project": source_project,
             "evidence": evidence or {},
             "validation": "single-project", "confidence": confidence,
             "scope": scope, "conditions": conditions,
             "limitations": limitations,
             "replicated_in": [source_project],
             "t": time.time()}
    with _path(base).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def _all(base) -> list[dict]:
    p = _path(base)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def propose_transfer(base, project_profile: dict) -> list[dict]:
    """Surface candidate knowledge for a new project.

    Matches on shared columns/segments/task words — surfaced as
    hypotheses with similarity notes, never as established facts.
    """
    cols = set((project_profile.get("columns") or []))
    task = (project_profile.get("task") or "").lower()
    cands = []
    for e in _all(base):
        if e.get("scope") == "universal":
            continue  # universal rules apply directly; no transfer needed
        text = (e.get("content", "") + " " + e.get("conditions", "")
                ).lower()
        overlap = cols & set(text.replace(",", " ").split())
        task_hit = task and task in text
        if overlap or task_hit:
            cands.append({
                "content": e["content"],
                "category": e["category"],
                "source_project": e["source_project"],
                "similarity": sorted(overlap)[:6],
                "task_match": bool(task_hit),
                "validation": e["validation"],
                "treat_as": "hypothesis — requires project-specific "
                            "evidence before any conclusion"})
    return cands


def check_transfer(candidate: dict, target_profile: dict,
                   history: list[dict] | None = None) -> dict:
    """M15 Phase 9: false-analogy guards for a transfer candidate.

    Warns on task mismatch, missing condition columns, and prior
    misleading transfers of similar content. Never blocks — the
    candidate stays a hypothesis — but the warnings travel with it.
    """
    warnings: list[str] = []
    cond = (candidate.get("conditions", "") + " "
            + candidate.get("content", "")).lower()
    tcols = {c.lower() for c in (target_profile.get("columns") or [])}
    for word in cond.replace(",", " ").split():
        if word in ("columns", "column"):
            continue
    ttask = (target_profile.get("task") or "").lower()
    stask = cond.split("task")
    if ttask and ttask not in cond and any(
            k in cond for k in ("classification", "regression",
                                "ranking", "forecasting")):
        warnings.append(f"task mismatch: target is {ttask!r} but the "
                        "source pattern names another task family")
    named_cols = {w for w in cond.replace(",", " ").split()
                  if len(w) > 2}
    if tcols and not (named_cols & tcols):
        warnings.append("no shared columns between source pattern "
                        "and target project")
    for h in history or []:
        if h.get("transfer_outcome") == "misled" and candidate.get(
                "content", "")[:40] in h.get("content", ""):
            warnings.append("this pattern misled before; verify first")
            break
    return {"warnings": warnings,
            "treat_as": candidate.get("treat_as", "hypothesis"),
            "ok": True}


def record_transfer_outcome(base, content: str, project_id: str,
                            helped: bool, note: str = "") -> dict:
    """Log whether a transferred idea confirmed or misled."""
    entry = {"category": "observation",
             "content": f"transfer {'helped' if helped else 'misled'}: "
                        f"{content}",
             "source_project": project_id,
             "evidence": {"note": note}, "validation": "single-project",
             "confidence": 0.6, "scope": "project",
             "conditions": "", "limitations": "",
             "replicated_in": [project_id], "t": time.time(),
             "transfer_outcome": "helped" if helped else "misled"}
    with _path(base).open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def strategy_record(base) -> dict:
    """Which strategies generalize: outcome tallies, no threshold edits."""
    helped = misled = 0
    by_category: dict[str, dict] = {}
    for e in _all(base):
        o = e.get("transfer_outcome")
        if o == "helped":
            helped += 1
        elif o == "misled":
            misled += 1
        c = e.get("category", "?")
        by_category.setdefault(c, {"n": 0})
        by_category[c]["n"] += 1
    return {"transfers_helped": helped, "transfers_misled": misled,
            "by_category": by_category,
            "note": "descriptive tally only; no policy is rewritten "
                    "from these counts"}
