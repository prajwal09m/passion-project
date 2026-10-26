"""Append-only registry of experiment baselines.

This module is the clean separation point between two tracks:

* **Historical V1.0.1 reproduction** -- evidence lives in
  ``autonomous_agent/state/baseline_reproduction.json`` and remains
  FAILED/BLOCKED.  Nothing in this module ever writes that file.
* **Reconstructed active baseline** (e.g. ``BASELINE_RECONSTRUCTED_2026_10``)
  -- established from the verified reconstructed implementation by the
  dedicated ``establish-baseline`` routine.

A reconstructed baseline is explicitly NOT a reproduction of V1.0.1:

    RECONSTRUCTED_STATEMENT

Registry semantics are append-only: an existing ``baseline_id`` can never be
overwritten, and an established record can never be relabeled as V1.0.1.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

# The immutable, non-negotiable historical identity pin.
PIN_V1_0_1_CODE_SHA256 = "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b"

RECONSTRUCTED_STATEMENT = (
    "This baseline is a reconstruction and is NOT a reproduction of V1.0.1."
)

# Field in any champion/baseline record that must keep the historical verdict.
HISTORICAL_V1_0_1_STATUS = "FAILED"

BASELINE_REGISTRY_NAME = "baseline_registry.json"


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    with temporary.open("a", encoding="utf-8") as stream:
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError):
        return default


def validate_established_record(record: Mapping[str, Any]) -> list[str]:
    """Return the reasons an established-baseline record is unusable (empty = valid)."""
    reasons: list[str] = []
    if record.get("status") != "ESTABLISHED":
        reasons.append(f"Baseline record status is {record.get('status')!r}, not 'ESTABLISHED'.")
    if record.get("kind") != "reconstructed_baseline":
        reasons.append(f"Baseline record kind is {record.get('kind')!r}, not 'reconstructed_baseline'.")
    if record.get("statement") != RECONSTRUCTED_STATEMENT:
        reasons.append("Baseline record is missing the mandatory reconstruction disclaimer statement.")
    lineage = record.get("lineage")
    if not isinstance(lineage, Mapping):
        reasons.append("Baseline record has no lineage block.")
    else:
        if lineage.get("relation") != "reconstruction":
            reasons.append("Baseline lineage must state relation == 'reconstruction'.")
        if lineage.get("v1_0_1_status") != HISTORICAL_V1_0_1_STATUS:
            reasons.append("Baseline lineage must preserve v1_0_1_status == 'FAILED'.")
        if lineage.get("historical_v1_0_1_sha256") != PIN_V1_0_1_CODE_SHA256:
            reasons.append("Baseline lineage must preserve the historical V1.0.1 SHA-256 pin.")
    self_reproduction = record.get("self_reproduction")
    if not isinstance(self_reproduction, Mapping) or self_reproduction.get("byte_identical") is not True:
        reasons.append("Baseline lacks valid self-reproduction evidence (two byte-identical runs).")
    elif int(self_reproduction.get("runs", 0)) < 2:
        reasons.append("Baseline self-reproduction evidence must cover at least two runs.")
    if record.get("leakage", {}).get("status") != "PASS":
        reasons.append("Baseline leakage status is not PASS.")
    holdout = record.get("holdout")
    if not isinstance(holdout, Mapping) or holdout.get("status") != "SEALED" or holdout.get("uses") != 0:
        reasons.append("Baseline requires holdout status SEALED with uses == 0.")
    if not record.get("pipeline_fingerprint"):
        reasons.append("Baseline record has no pipeline fingerprint.")
    return reasons


class BaselineRegistry:
    """Append-only store of baseline records; the newest ESTABLISHED record is active."""

    def __init__(self, state_root: Path):
        self.state_root = Path(state_root)
        self.path = self.state_root / BASELINE_REGISTRY_NAME

    def load(self) -> dict[str, Any]:
        data = read_json(self.path, {})
        if not isinstance(data, dict):
            return {"schema_version": 1, "baselines": []}
        data.setdefault("schema_version", 1)
        data.setdefault("baselines", [])
        return data

    def records(self) -> list[dict[str, Any]]:
        return [row for row in self.load()["baselines"] if isinstance(row, dict)]

    def ids(self) -> list[str]:
        return [str(row.get("baseline_id")) for row in self.records()]

    def find(self, baseline_id: str) -> dict[str, Any] | None:
        for row in self.records():
            if row.get("baseline_id") == baseline_id:
                return row
        return None

    def active(self) -> dict[str, Any] | None:
        """The newest ESTABLISHED baseline record, validated before it is trusted."""
        for row in reversed(self.records()):
            if row.get("status") == "ESTABLISHED":
                return row
        return None

    def append(self, record: Mapping[str, Any]) -> None:
        """Append a record. Ids are immutable: duplicates are refused outright."""
        baseline_id = str(record.get("baseline_id") or "")
        if not baseline_id:
            raise ValueError("Baseline record requires an explicit baseline_id.")
        if self.find(baseline_id) is not None:
            raise FileExistsError(
                f"Baseline {baseline_id} already exists; registry entries are immutable."
            )
        data = self.load()
        data["baselines"].append(dict(record))
        write_json_atomic(self.path, data)
