"""Canonical metric normalization (Eval v3, Stage 4).

Resolves the `gap` / `max_slice_gap` naming inconsistency between
`ranking_slice_diagnostics` (emits `max_slice_gap`) and the scorer
(which reads `gap`).

Canonical key: `gap` (float, >= 0). Priority: explicit `gap` wins;
`max_slice_gap` is accepted as a documented alias. Original keys are
preserved; aliasing is recorded in flags so provenance is never lost.

Rules:
- `gap` only            -> `gap` kept, no flags.
- `max_slice_gap` only  -> `gap` aliased, `alias_from=max_slice_gap`.
- both, equal (|d|<=1e-9) -> `gap` kept, no flags.
- both, conflicting     -> explicit `gap` wins, `gap_conflict=true`
  (both originals preserved).
- neither               -> absent (NEVER silently 0).
- invalid (non-numeric, NaN, bool, negative) -> dropped, `gap_invalid=true`.

`normalize_numbers(tool, numbers)` returns `(numbers, flags)`; the input
dict is never mutated.
"""
from __future__ import annotations

import math

CANONICAL_GAP = "gap"
ALIAS_GAP = "max_slice_gap"
_EQUAL_TOL = 1e-9


def _valid_gap(value) -> bool:
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    if not math.isfinite(value):
        return False
    return value >= 0


def normalize_numbers(tool: str, numbers: dict) -> tuple[dict, dict]:
    """Return (normalized_numbers, flags) without mutating the input."""
    src = dict(numbers or {})
    flags: dict = {}
    gap = src.get(CANONICAL_GAP)
    alias = src.get(ALIAS_GAP)
    gap_ok = _valid_gap(gap)
    alias_ok = _valid_gap(alias)
    if gap is not None and not gap_ok:
        flags["gap_invalid"] = True
    if alias is not None and not alias_ok:
        flags["gap_invalid"] = True
    if gap_ok and alias_ok:
        if abs(float(gap) - float(alias)) <= _EQUAL_TOL:
            src[CANONICAL_GAP] = float(gap)
        else:
            src[CANONICAL_GAP] = float(gap)
            flags["gap_conflict"] = True
    elif gap_ok:
        src[CANONICAL_GAP] = float(gap)
    elif alias_ok:
        src[CANONICAL_GAP] = float(alias)
        flags["alias_from"] = ALIAS_GAP
    else:
        src.pop(CANONICAL_GAP, None)
    # `max_slice_gap` original is preserved untouched for provenance.
    return src, flags


def canonical_gap(numbers: dict) -> float | None:
    """Single read path for scorers: normalized `gap`, else None (never 0)."""
    normed, _ = normalize_numbers("", numbers or {})
    value = normed.get(CANONICAL_GAP)
    return float(value) if _valid_gap(value) else None
