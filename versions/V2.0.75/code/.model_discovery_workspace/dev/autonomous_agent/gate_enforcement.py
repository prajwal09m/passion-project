"""Fail-closed guards proposed for the campaign loop (NOT wired in; dev only).

Two guards:

1. ``require_human_gates``: the loop must not start unless every human gate in
   the owner-maintained record is present, decided, and provenance-complete.
   It reuses the read-only checker's own rules, so the loop and the readiness
   tool cannot disagree about what "recorded" means.

2. ``require_authorized_auto_approval``: a campaign config may set
   ``require_human_approval: false`` only with a named owner authorization
   record that exists on disk. Otherwise proposals would be approved as
   ``policy:auto`` with no human involved.

Limits (stated, not hidden): these guards verify that the record is present
and well-formed. They cannot verify that an independent statistical review
was genuinely performed; that remains an owner and reviewer judgement.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from autonomous_agent import launch_readiness_check as lrc


class GateError(Exception):
    """A required human gate or authorization is missing, undecided or malformed."""


def require_human_gates(root: Path | str, gates_path: Path | str) -> None:
    root = Path(root)
    gates_path = Path(gates_path)
    report = lrc.Report()
    lrc.check_human_gates(root, gates_path, report)
    outstanding = [code for status, code, _ in report.rows if status == lrc.HUMAN]
    failures = [f"{code}: {msg}" for status, code, msg in report.rows if status == lrc.FAIL]
    if failures or outstanding:
        raise GateError("human gates not satisfied; loop must not start: "
                        + "; ".join(failures + [f"outstanding {c}" for c in outstanding]))


def require_authorized_auto_approval(root: Path | str, campaign: Mapping[str, Any],
                                     policy: Mapping[str, Any]) -> None:
    """Refuse policy auto-approval unless a named, existing owner record backs it."""
    if bool(policy.get("require_human_approval", True)):
        return                                   # human approval on: nothing to guard
    record = campaign.get("auto_approval_authorization")
    if not isinstance(record, Mapping):
        raise GateError("require_human_approval=false without an "
                        "auto_approval_authorization record in the campaign config")
    evidence = str(record.get("evidence_path") or "")
    if not evidence or not (Path(root) / evidence).is_file():
        raise GateError(f"auto_approval_authorization evidence missing: {evidence!r}")
    if not str(record.get("decided_by") or "").strip() or not str(record.get("date") or "").strip():
        raise GateError("auto_approval_authorization lacks decided_by or date")
