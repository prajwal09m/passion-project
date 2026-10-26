"""Append-only proposal ledger + lifecycle state machine (Phase 1 component 6).

Two row types, both append-only, fsync'd:

  * ``{"row_type": "proposal", ...}``   — immutable payload, written once.
  * ``{"row_type": "transition", ...}`` — state transitions with reason codes.

There is no update or delete API. Rejected proposals are recorded exactly as
carefully as accepted ones. State is reconstructed by folding rows, so the
ledger survives restarts and crashes (permanent already-asked memory).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from autonomous_agent.proposal_layer import schema


class LedgerError(Exception):
    """Illegal lifecycle operation or malformed ledger usage."""


class LedgerCorrupt(Exception):
    """A row could not be parsed; strict reads fail closed."""


def _default_clock() -> str:
    from autonomous_agent.core import utc_now
    return utc_now()


class ProposalLedger:
    def __init__(self, path: Path | str,
                 clock: Callable[[], str] | None = None) -> None:
        self.path = Path(path)
        self.clock = clock or _default_clock

    # -- raw append ----------------------------------------------------------
    def _append_row(self, row: dict[str, Any]) -> None:
        """Serialize fully, then a single fsync'd O_APPEND write."""
        line = json.dumps(row, sort_keys=True, default=str) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())

    def read_rows(self, *, strict: bool = True) -> list[dict[str, Any]]:
        """Read all rows. Strict mode fails closed on a corrupt/partial tail;
        tolerant mode returns intact rows plus a ``__corrupt_lines__`` count."""
        if not self.path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        corrupt = 0
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                rows.append(json.loads(raw))
            except json.JSONDecodeError:
                corrupt += 1
                if strict:
                    raise LedgerCorrupt(
                        f"Unparseable ledger row in {self.path}: {raw[:80]!r}")
        if corrupt and not strict:
            rows.append({"__corrupt_lines__": corrupt})
        return rows

    # -- proposal creation ---------------------------------------------------
    def create_proposal(self, payload: Mapping[str, Any]) -> str:
        """Append the immutable PROPOSED row; returns the assigned proposal_id.

        Identity: ``prop-<fingerprint[:12]>-<n>`` where n counts every prior
        attempt with the same fingerprint, so repeated identical proposals are
        *recorded* (and later refused) rather than silently dropped.
        """
        fingerprint = payload.get("proposal_fingerprint")
        if not isinstance(fingerprint, str) or len(fingerprint) < 16:
            raise LedgerError("Payload missing a valid proposal_fingerprint.")
        rows = self.read_rows(strict=True)
        for row in rows:
            if row.get("row_type") == "proposal" and row.get("proposal_id") == payload.get("proposal_id"):
                raise LedgerError(f"proposal_id collision: {payload.get('proposal_id')}")
        same_fp = sum(1 for row in rows
                      if row.get("row_type") == "proposal"
                      and (row.get("proposal") or {}).get("proposal_fingerprint") == fingerprint)
        proposal_id = f"prop-{fingerprint[:12]}-{same_fp + 1}"
        self._append_row({
            "row_type": "proposal",
            "at": self.clock(),
            "proposal_id": proposal_id,
            "proposal": dict(payload),
        })
        return proposal_id

    # -- state machine -------------------------------------------------------
    def status(self, proposal_id: str) -> str | None:
        current: str | None = None
        for row in self.read_rows(strict=True):
            if row.get("row_type") == "proposal" and row.get("proposal_id") == proposal_id:
                current = schema.STATUS_PROPOSED
            elif row.get("row_type") == "transition" and row.get("proposal_id") == proposal_id:
                current = row.get("to")
        return current

    def transition(self, proposal_id: str, to: str, *,
                   reason_code: str | None = None,
                   detail: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Append one legal transition. Illegal moves raise LedgerError —
        no transition can bypass validation (Phase 1 C/E, user lifecycle)."""
        if to not in schema.ALL_STATUSES:
            raise LedgerError(f"Unknown status {to!r}.")
        current = self.status(proposal_id)
        if current is None:
            raise LedgerError(f"Unknown proposal {proposal_id!r}.")
        allowed = schema.LEGAL_TRANSITIONS.get(current, frozenset())
        if to not in allowed:
            raise LedgerError(
                f"Illegal transition {current} -> {to} for {proposal_id}; "
                f"allowed: {sorted(allowed)}.")
        # No silent conversion into an execution candidate (OBS-3,
        # revalidate_at_approval@1.0.0): every ACCEPTED_FOR_EXECUTION
        # transition must persist the approval policy id/version, who
        # approved, and the exact quota_state snapshot the decision used.
        if to == schema.STATUS_ACCEPTED_FOR_EXECUTION:
            supplied = detail or {}
            missing = [key for key in ("approval_policy", "approved_by",
                                       "quota_state")
                       if key not in supplied]
            if missing:
                raise LedgerError(
                    f"ACCEPTED_FOR_EXECUTION for {proposal_id} requires "
                    f"recorded approval provenance {missing}; a validated "
                    "proposal may never silently become an execution "
                    "candidate (revalidate_at_approval policy).")
        # ADJUDICATED -> PROMOTED is conditionally legal only: the latest
        # adjudication must have recorded detail.result == "ACCEPTED".
        # Rejected/null adjudications are permanent — nothing can promote a
        # proposal whose recorded outcome was rejection (fail-closed).
        if to == schema.STATUS_PROMOTED:
            adjudications = [row for row in self.transitions_of(proposal_id)
                             if row.get("to") == schema.STATUS_ADJUDICATED]
            last_detail = (adjudications[-1].get("detail") or {}) \
                if adjudications else {}
            if last_detail.get("result") != "ACCEPTED":
                raise LedgerError(
                    f"PROMOTED requires the latest ADJUDICATED row to record "
                    f"detail.result == 'ACCEPTED' (got "
                    f"{last_detail.get('result')!r}) for {proposal_id}; rejected "
                    "adjudications are permanent.")
        row = {
            "row_type": "transition",
            "at": self.clock(),
            "proposal_id": proposal_id,
            "from": current,
            "to": to,
            "reason_code": reason_code,
            "detail": dict(detail or {}),
        }
        self._append_row(row)
        return row

    # -- reconstruction ------------------------------------------------------
    def transitions_of(self, proposal_id: str) -> list[dict[str, Any]]:
        return [row for row in self.read_rows(strict=True)
                if row.get("row_type") == "transition"
                and row.get("proposal_id") == proposal_id]

    def get(self, proposal_id: str) -> dict[str, Any] | None:
        payload: dict[str, Any] | None = None
        created_at: str | None = None
        for row in self.read_rows(strict=True):
            if row.get("row_type") == "proposal" and row.get("proposal_id") == proposal_id:
                payload = dict(row.get("proposal") or {})
                created_at = row.get("at")
        if payload is None:
            return None
        transitions = self.transitions_of(proposal_id)
        status = transitions[-1]["to"] if transitions else schema.STATUS_PROPOSED
        last_reason = next((row.get("reason_code") for row in reversed(transitions)
                            if row.get("reason_code")), None)
        return {
            "proposal_id": proposal_id,
            "created_at": created_at,
            "status": status,
            "last_reason_code": last_reason,
            "proposal": payload,
            "transitions": transitions,
        }

    def all_proposals(self) -> list[dict[str, Any]]:
        ids: list[str] = []
        for row in self.read_rows(strict=True):
            if row.get("row_type") == "proposal":
                pid = row.get("proposal_id")
                if pid not in ids:
                    ids.append(pid)
        return [merged for pid in ids if (merged := self.get(pid)) is not None]

    def fingerprint_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.read_rows(strict=True):
            if row.get("row_type") == "proposal":
                fp = (row.get("proposal") or {}).get("proposal_fingerprint")
                if isinstance(fp, str):
                    counts[fp] = counts.get(fp, 0) + 1
        return counts


def encode_rows(rows: Iterable[Mapping[str, Any]]) -> str:
    """Canonical single-line encoding (tests + determinism helpers)."""
    return "".join(json.dumps(dict(row), sort_keys=True, default=str) + "\n"
                   for row in rows)
