"""Versioned structured-report contract (M8 Workstream B).

Schema `m8-v1` (superset of the M6 contract — same required fields, plus
version, types, truncation and overconfidence checks). A syntactically
valid report is NOT automatically scientifically valid: this validator
additionally flags evidence-integrity problems (unknown refs),
unsupported confidence, and missing uncertainty — without ever inventing
content. On failure the caller preserves the original and may compose an
explicitly labeled deterministic fallback (see fallback.py).
"""
from __future__ import annotations

REPORT_SCHEMA_VERSION = "m8-v1"

_MAX_CONCLUSION_CHARS = 2000
_MAX_LIST_ITEMS = 50


def validate(summary: dict | None, hypothesis_ids: set[str],
             experiment_ids: set[str]) -> dict:
    from . import report_validation as RV
    base = RV.validate(summary, hypothesis_ids, experiment_ids)
    errors = list(base["errors"])
    warnings = list(base["warnings"])
    if isinstance(summary, dict):
        ver = summary.get("schema_version", None)
        if ver is not None and ver != REPORT_SCHEMA_VERSION:
            errors.append(f"unknown schema_version {ver!r}; "
                          f"expected {REPORT_SCHEMA_VERSION!r}")
        concl = summary.get("conclusion")
        if isinstance(concl, str) and len(concl) > _MAX_CONCLUSION_CHARS:
            errors.append(f"conclusion truncated or oversized "
                          f"({len(concl)} chars > {_MAX_CONCLUSION_CHARS})")
        for field in ("uncertainties", "status_recommendations"):
            val = summary.get(field)
            if isinstance(val, list) and len(val) > _MAX_LIST_ITEMS:
                errors.append(f"{field} has {len(val)} items "
                              f"(max {_MAX_LIST_ITEMS})")
        conf = summary.get("confidence")
        if isinstance(conf, (int, float)) and conf == 100:
            errors.append("confidence 100 claims certainty; no investigation "
                          "establishes certainty — cap at 99 with caveats")
        recs = summary.get("status_recommendations") or []
        for r in recs:
            if isinstance(r, dict) and r.get("status") == "supported" \
                    and not r.get("basis") and not r.get("basis_action_ids"):
                errors.append(f"supported {r.get('hypothesis_id')} cites no "
                              "basis actions")
    return {"valid": not errors and base["valid"], "errors": errors,
            "warnings": warnings,
            "normalized": base["normalized"] if not errors else None,
            "schema_version": REPORT_SCHEMA_VERSION}
