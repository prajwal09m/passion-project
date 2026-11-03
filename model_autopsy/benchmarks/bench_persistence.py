"""Durable per-run persistence for the Phase D benchmark harnesses.

The 2026-10-29 Meta campaign lost 3/4 complete final assistant messages
because the only complete copy lived in process memory plus a temporary
sandbox SQLite that the harness deleted with `shutil.rmtree` before any
external reader reached the final database state; the sandbox event log
additionally capped assistant-text detail at 600 characters. This module
implements the Phase 2 repair (audit R1-R6):

- R1: records are written incrementally (append-friendly JSONL, fsync'd)
  so a mid-run crash leaves the evidence that existed at the crash.
- R2: every response/assistant/usage/repair row carries the investigation
  id, turn/round linkage, and the provider response id, so rows from many
  investigations sharing one sandbox DB stay attributable.
- R3: complete provider payloads are preserved verbatim; credential and
  secret-shaped values are redacted (`_REDACT_PATTERNS`) before any byte
  reaches disk, and a redaction self-check is part of the test suite.
- R4: complete assistant text is stored verbatim (no 600-char cap); any
  truncation lives only in separate display fields (e.g. report
  `final_message_head`), never in the durable record.
- R5: finalization is fail-closed. The volatile sandbox directory may be
  deleted only when the durable manifest confirms `finalized` with every
  required artifact present AND every recorded SHA-256 hash re-verified
  against the bytes on disk; otherwise the sandbox is kept with a reason.
- R6: run status vocabulary is `in_progress` / `finalized` /
  `incomplete_preservation` / `interrupted`. `finalized` is the completed
  state (run finished AND all required evidence verified); an explicit
  `interrupted` is never overwritten by later finalization.
- R7: a run directory is never silently overwritten: the constructor
  refuses an existing directory, campaign roots refuse to reuse a name,
  and crash recovery only ever ADDS a manifest, never deletes evidence.

All writes happen only inside the campaign directory; raw records carry no
secret material because provider clients in this project read keys from the
environment and never embed them in kwargs stored here.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------

# Never-serialise markers. Applied defensively to every record before write;
# value patterns are matched case-insensitively against common secret shapes.
_REDACT_PATTERNS = (
    ("authorization", "[REDACTED]"),
    ("api_key", "[REDACTED]"),
    ("bearer ", "[REDACTED]"),
    ("sk-proj-", "[REDACTED]"),
)


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _redact(("[REDACTED-KEY]" if any(p in str(k).lower()
                                               for p, _ in _REDACT_PATTERNS)
                        else _redact(v)))
            for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, str):
        lowered = obj.lower()
        for needle, repl in _REDACT_PATTERNS:
            if needle in lowered:
                # Mask the credential marker AND any value glued to it via
                # word/`=`/`:`/space boundaries, keeping surrounding text.
                return re.sub(r"(?i)" + re.escape(needle) +
                              r"[\w\-\.\s=:]*", repl, obj)
        return obj
    return obj


def _fsync_write(path: Path, data: str, append: bool = True) -> None:
    mode = "a" if append else "w"
    with open(path, mode, encoding="utf-8", newline="\n") as fh:
        fh.write(data)
        fh.flush()
        try:
            import os
            os.fsync(fh.fileno())
        except (AttributeError, OSError):
            pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


REQUIRED_EVIDENCE = [
    "responses",          # every provider request/response recorded
    "assistant_messages", # complete turn texts with response ids
    "usage",              # provider usage per request
    "events_dump",        # full in-sandbox event/action/hypothesis dump
    "sandbox_final.db",   # durable copy of the sandbox DB
    # "repairs" is conditionally required: finalize() demands a non-empty
    # repairs.jsonl when outcome["repair_attempted"] is true, and ignores
    # it otherwise (a run with no repair must not fail for lacking one).
]


class RunRecorder:
    """Incremental durable store for one benchmark run."""

    def __init__(self, campaign_dir: Path, run_id: str):
        self.run_id = run_id
        self.dir = campaign_dir / run_id
        if self.dir.exists():
            raise RuntimeError(f"run dir already exists: {self.dir}")
        self.dir.mkdir(parents=True, exist_ok=False)
        self.status = "in_progress"
        self.context_items: dict[str, Any] = {}
        self.start_utc = _now()
        self.write("run_start.json", {
            "run": run_id, "started_utc": self.start_utc}, append=False)

    # -- incremental writers ------------------------------------------------
    def write(self, name: str, record: dict, append: bool = True) -> Path:
        path = self.dir / name
        data = json.dumps(_redact(record), sort_keys=True, default=str)
        _fsync_write(path, data + ("\n" if append and name.endswith("jsonl")
                                   else "\n"), append=append)
        return path

    def record_response(self, run: str, turn: int, round_no: int, resp: dict,
                        chained: bool,
                        investigation_id: str | None = None) -> None:
        self.write("responses.jsonl", {
            "run": run, "turn": turn, "round": round_no, "chained": chained,
            "investigation_id": investigation_id,
            "recorded_utc": _now(),
            "response": _redact(resp)})

    def record_assistant(self, run: str, turn: int, round_no: int, text: str,
                         response_id: str | None, status: str | None,
                         investigation_id: str | None = None) -> None:
        self.write("assistant_messages.jsonl", {
            "run": run, "turn": turn, "round": round_no, "text": text,
            "response_id": response_id, "status": status,
            "investigation_id": investigation_id,
            "recorded_utc": _now()})

    def record_repair(self, run: str, turn: int, record: dict,
                      investigation_id: str | None = None) -> None:
        payload = dict(record)
        payload.update({"run": run, "turn": turn,
                        "investigation_id": investigation_id,
                        "recorded_utc": _now()})
        self.write("repairs.jsonl", payload)

    def record_context(self, run: str, turn: int, context_kind: str,
                       context_chars: int) -> None:
        self.write("context_facts.jsonl", {
            "run": run, "turn": turn, "context_kind": context_kind,
            "context_chars": context_chars, "recorded_utc": _now()})

    def record_usage(self, run: str, entry: dict,
                     investigation_id: str | None = None) -> None:
        self.write("usage.jsonl", {**entry,
                                   "investigation_id": investigation_id,
                                   "recorded_utc": _now()})

    def dump_sandbox_db(self, sandbox_db: Path) -> bool:
        target = self.dir / "sandbox_final.db"
        src = dst = None
        try:
            src = sqlite3.connect(f"file:{sandbox_db}?mode=ro", uri=True)
            dst = sqlite3.connect(str(target))
            src.backup(dst)
        except Exception:
            # Fall back to a plain copy of a stable committed DB.
            try:
                shutil.copyfile(sandbox_db, target)
            except Exception:
                return False
        finally:
            # Always release both handles: an unclosed connection keeps a
            # Windows lock on the source file and blocks later cleanup.
            for conn in (dst, src):
                if conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass
        return target.exists() and target.stat().st_size > 0

    def dump_investigation(self, session, investigation_id: str,
                           engine=None, db=None) -> None:
        """Events/actions/hypotheses for this investigation, from the
        sandbox's own tables (same content the snapshot DB retained)."""
        if db is None:  # lazy import: PROJECT_ROOT is on sys.path by call time
            from model_autopsy.backend import db as db_mod
            db = db_mod
        from sqlalchemy import select
        rows = []
        for ev in session.execute(
                select(db.Event).order_by(db.Event.seq)).scalars():
            if ev.investigation_id != investigation_id:
                continue
            rows.append({"seq": ev.seq, "kind": ev.kind, "title": ev.title,
                         "detail": ev.detail,
                         "payload": ev.payload or {}})
        acts = [{a.seq: None} and {"seq": a.seq, "tool": a.tool_name,
                                   "status": a.status}
                for a in session.execute(select(db.Action)).scalars()
                if a.investigation_id == investigation_id]
        hyps = [{h.id: None} and {"id": h.id, "text": h.text,
                                  "status": h.status}
                for h in session.execute(select(db.Hypothesis)).scalars()
                if h.investigation_id == investigation_id]
        self.write("events_dump.json", {
            "investigation_id": investigation_id,
            "events": rows, "actions": acts, "hypotheses": hyps,
            "recorded_utc": _now()}, append=False)

    # -- finalisation -------------------------------------------------------
    def finalize(self, *, run: str, campaign: str, outcome: dict,
                 reason: str | None = None) -> dict:
        """Write `run_manifest.json` with per-artifact SHA-256 records and
        verify presence of every required evidence type."""
        required_present, _missing = self._verify_required()
        # Conditionally required evidence (R5): when the caller reports a
        # summary repair was attempted, a non-empty repairs.jsonl must
        # exist; runs without a repair attempt are not penalised for its
        # absence.
        if (outcome or {}).get("repair_attempted"):
            rep = self.dir / "repairs.jsonl"
            required_present["repairs"] = (
                rep.exists() and rep.stat().st_size > 0)
        # Fail-closed status vocabulary (R6): a run whose required
        # evidence is incomplete is NEVER marked finalized. An explicit
        # "interrupted" (aborted run) is never overwritten; a completed
        # run with gaps becomes "incomplete_preservation"; late-arriving
        # evidence can still promote it to "finalized" on re-finalize.
        if all(required_present.values()):
            if self.status in ("in_progress", "incomplete_preservation"):
                self.status = "finalized"
        else:
            if self.status in ("in_progress", "finalized"):
                self.status = "incomplete_preservation"
        artifacts = {}
        for artifact in ("run_start.json", "responses.jsonl",
                         "assistant_messages.jsonl", "usage.jsonl",
                         "repairs.jsonl", "events_dump.json",
                         "sandbox_final.db", "context_facts.jsonl"):
            path = self.dir / artifact
            if path.exists():
                artifacts[artifact] = _sha256(path)
        manifest = {
            "run": run, "campaign": campaign,
            "started_utc": self.start_utc,
            "finalized_utc": _now(),
            "status": self.status,
            "reason": reason,
            "outcome": outcome,
            "artifacts": artifacts,
            "required_evidence_present": required_present,
        }
        path = self.dir / "run_manifest.json"
        _fsync_write(path, json.dumps(manifest, indent=2, default=str),
                     append=False)
        return manifest

    def _verify_required(self) -> tuple[dict, list[str]]:
        out = {}
        missing = []
        for req in ("responses", "assistant_messages", "usage",
                    "events_dump", "sandbox_final.db"):
            filename = {"responses": "responses.jsonl",
                        "assistant_messages": "assistant_messages.jsonl",
                        "usage": "usage.jsonl",
                        "events_dump": "events_dump.json"}.get(
                            req, "sandbox_final.db")
            ok = (self.dir / filename).exists() and \
                (self.dir / filename).stat().st_size > 0
            out[req] = ok
            if not ok:
                missing.append(req)
        return out, missing


def verify_manifest_hashes(manifest: dict, run_dir: Path) -> list[str]:
    """Recompute SHA-256 for every artifact the manifest records and
    return the names whose bytes no longer match (empty list = all verify).
    This is the R5 second half: presence alone is not preservation."""
    mismatched = []
    for name, expected in (manifest.get("artifacts") or {}).items():
        if not expected:
            continue
        actual = _sha256(run_dir / name)
        if actual != expected:
            mismatched.append(name)
    return mismatched


def delete_dir_after_verify(dest: Path, *, manifest_path: Path | None = None,
                            reason_if_kept: str | None = None) -> dict:
    """Delete the volatile sandbox dir only when a durable record exists whose
    manifest confirms `finalized` with all required evidence AND every
    recorded SHA-256 hash re-verifies against the bytes on disk; otherwise
    keep and report. `manifest_path` is the run_manifest.json in the
    campaign dir (the durable side), not inside `dest`."""
    keep = {"kept": True, "reason": reason_if_kept or "no manifest"}
    manifest_path = manifest_path or (dest / "run_manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return keep
    missing = [k for k, ok in (manifest.get("required_evidence_present")
                               or {}).items() if not ok]
    mismatched = verify_manifest_hashes(manifest, manifest_path.parent)
    if mismatched:
        return {"kept": True,
                "reason": ("hash mismatch after finalize (bytes changed "
                             "or truncated): " + ", ".join(mismatched))}
    if manifest.get("status") == "finalized" and not missing:
        # Retry briefly: on Windows, a just-closed file handle can take a
        # moment to release, and antivirus/indexers transiently lock files.
        last_error: OSError | None = None
        for _ in range(5):
            try:
                shutil.rmtree(dest)
                return {"kept": False, "reason": None}
            except OSError as exc:
                last_error = exc
                time.sleep(0.2)
        return {"kept": True,
                "reason": f"preservation verified but deletion was "
                          f"blocked: {last_error}"}
    keep["reason"] = (manifest.get("reason") or reason_if_kept or
                      "missing evidence: " + ", ".join(missing))
    return keep


_RECOVERABLE_CAMPAIGN_PREFIXES = ("phase_d_meta_live_",
                                     "phase_d_groq_live_")


def recover_incomplete_runs(campaign_root: Path) -> list[str]:
    """Crash recovery: after a previous process died, any run directory still
    holding incremental JSONL evidence but no finalized run_manifest.json is
    marked `interrupted` with a recovery manifest. Nothing is ever
    deleted; evidence written before the crash survives verbatim. Historical
    artifacts are untouched: only live-campaign run dirs (run_start.json +
    incremental evidence, no manifest) are eligible."""
    recovers = []
    if not campaign_root.is_dir():
        return recovers
    for campaign_dir in sorted(campaign_root.iterdir()):
        if not campaign_dir.is_dir() or not campaign_dir.name.startswith(
                _RECOVERABLE_CAMPAIGN_PREFIXES):
            continue
        for run_dir in sorted(campaign_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            if (run_dir / "run_manifest.json").exists():
                continue
            has_evidence = (run_dir / "run_start.json").exists() and any(
                (run_dir / name).exists()
                for name in ("responses.jsonl", "usage.jsonl",
                             "assistant_messages.jsonl",
                             "failed_permalink.jsonl"))
            if not has_evidence:
                continue
            manifest = {
                "run": run_dir.name, "campaign": campaign_dir.name,
                "status": "interrupted",
                "recovered_utc": _now(),
                "recovery_note": (
                    "process died before finalize; incremental evidence "
                    "was preserved verbatim and NOTHING was deleted"),
                "artifacts": {p.name: _sha256(p)
                              for p in sorted(run_dir.iterdir())
                              if p.is_file()},
            }
            _fsync_write(run_dir / "run_manifest.json",
                         json.dumps(manifest, indent=2, default=str),
                         append=False)
            recovers.append(str(run_dir))
    return recovers
