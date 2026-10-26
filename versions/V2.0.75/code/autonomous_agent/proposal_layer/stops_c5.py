"""Campaign 5's two declared signal stops (enforcement wired before launch).

Campaign 5's frozen configuration extends the Campaign 4 stop set with:

* ``regime_predefinition_violation`` — regime definitions must come from the
  frozen C5 predeclaration, never be discovered from outcome labels at
  execution time;
* ``data_snooping_detected`` — regime/error analysis must not read outcome
  labels into regime detection.

Enforcement follows the same declared (not inferred) contract as the v1.1.0
audit stops: an experiment outcome whose payload carries a violation verdict
maps onto a fail-closed campaign stop, is recorded durably in the ledger
BEFORE the halt, and the recorded signal survives restarts. The signals are
absent from every pre-Campaign-5 outcome, so the walker is inert for prior
campaigns and never fires on any ordinary acceptance/rejection verdict.

This module is deliberately standalone (it imports nothing): the loop stays
the only importer of the multiplicity machinery.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

STOP_REGIME_PREDEFINITION = "regime_predefinition_violation"
STOP_DATA_SNOOPING = "data_snooping_detected"

C5_SIGNAL_STOPS: frozenset[str] = frozenset(
    {STOP_REGIME_PREDEFINITION, STOP_DATA_SNOOPING})

_REGIME_PREDEFINITION_MARKERS = (
    "REGIME_PREDEFINITION_VIOLATION",
    "VIOLATION_OF_REGIME_PREDECLARATION",
    "REGIME_DEFINITIONS_DISCOVERED_FROM_LABELS",
)
_DATA_SNOOPING_MARKERS = ("DATA_SNOOPING_DETECTED", "DATA_SNOOPING_CONFIRMED")
# Keys that may carry a data-snooping / regime-predefinition verdict;
# ordinary ``status`` fields only fire on the full marker text above.
_SNOOP_STATUS_KEYS = ("data_snooping", "snooping_status", "data_snooping_status")
_REGIME_STATUS_KEYS = ("regime_predefinition_status",
                       "regime_predefinition_violation")
_AUDIT_STATUS_KEYS = ("status", "lineage_status", "audit_status",
                      *_SNOOP_STATUS_KEYS, *_REGIME_STATUS_KEYS)


def _walk_status_fields(node: Any, path: str = "$") -> Iterable[tuple[str, str, str]]:
    """Yield (key, verdict, path) for every status-like string field."""
    if isinstance(node, Mapping):
        for key, item in node.items():
            child = f"{path}.{key}"
            if key in _AUDIT_STATUS_KEYS and isinstance(item, str):
                yield str(key), item, child
            yield from _walk_status_fields(item, child)
    elif isinstance(node, (list, tuple)):
        for index, item in enumerate(node):
            yield from _walk_status_fields(item, f"{path}[{index}]")


def c5_signal_stop(outcome: Mapping[str, Any]) -> tuple[str, str] | None:
    """Map a completed experiment's declared C5 status fields onto a stop.

    Contract (declared, not inferred): fires only on explicit violation
    verdicts; absence of these fields signals nothing, and ordinary
    accept/reject verdicts never match.
    """
    for key, raw, where in _walk_status_fields(outcome):
        verdict = raw.upper()
        if any(marker in verdict for marker in _REGIME_PREDEFINITION_MARKERS):
            return (STOP_REGIME_PREDEFINITION,
                    f"{raw!r} at {where}: regime split used outcome-influenced, "
                    "not predeclared, definitions")
        if key == "regime_predefinition_status" and "VIOLATION" in verdict:
            return (STOP_REGIME_PREDEFINITION,
                    f"{raw!r} at {where}")
        if any(marker in verdict for marker in _DATA_SNOOPING_MARKERS):
            return (STOP_DATA_SNOOPING,
                    f"{raw!r} at {where}: outcome labels reached regime/error "
                    "detection inputs")
        if key in _SNOOP_STATUS_KEYS and verdict.startswith("DETECTED"):
            return (STOP_DATA_SNOOPING,
                    f"{raw!r} at {where}")
    return None


def recorded_c5_signal_stop(rows: Iterable[Mapping[str, Any]]) -> tuple[str, str] | None:
    """Fold durable ledger rows: a recorded signal stop survives restarts."""
    for row in rows:
        detail = row.get("detail")
        if not isinstance(detail, Mapping):
            continue
        stop = c5_signal_stop(detail)
        if stop is not None:
            return stop
    return None
