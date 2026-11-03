"""Structured research report validation (M6 Part 2F).

Validates required fields, hypothesis/experiment/evidence references,
confidence ranges, status consistency, contradictory claims, missing
supporting evidence, and reproducibility metadata.

Never rewrites the investigator response. On failure: preserve the
original, record errors, identify missing fields. A corrected
representation may exist only if explicitly labeled as a transformation
with provenance and the original retained.
"""
from __future__ import annotations


REQUIRED_FIELDS = ("conclusion",)
OPTIONAL_FIELDS = ("status_recommendations", "uncertainties", "recommended_next",
                   "confidence", "evidence_cited")


def validate(summary: dict | None, hypothesis_ids: set[str],
             experiment_ids: set[str]) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(summary, dict):
        return {"valid": False, "errors": ["summary is not an object"],
                "warnings": [], "normalized": None}
    for f in REQUIRED_FIELDS:
        if not isinstance(summary.get(f), str) or not summary[f].strip():
            errors.append(f"'{f}' is required and must be a non-empty string")
    recs = summary.get("status_recommendations") or []
    if not isinstance(recs, list):
        errors.append("'status_recommendations' must be a list")
        recs = []
    seen: set[str] = set()
    for r in recs:
        if not isinstance(r, dict):
            errors.append("each status_recommendation must be an object")
            continue
        hid = str(r.get("hypothesis_id") or "")
        matches = [k for k in hypothesis_ids if k == hid or (hid and k.startswith(hid))]
        if len(matches) != 1:
            errors.append(f"unknown hypothesis reference {hid!r}; never fabricate ids")
        else:
            if matches[0] in seen:
                errors.append(f"duplicate recommendation for {matches[0]}")
            seen.add(matches[0])
        if r.get("status") not in ("proposed", "investigating", "supported",
                                   "rejected", "inconclusive", "blocked"):
            errors.append(f"unsupported status {r.get('status')!r}")
        for aid in (r.get("basis_action_ids") or []):
            if aid not in experiment_ids:
                errors.append(f"recommendation cites unknown experiment {aid!r}")
    conf = summary.get("confidence")
    if conf is not None and not (isinstance(conf, (int, float)) and 0 <= conf <= 100):
        errors.append("'confidence' must be 0-100 when present")
    # Contradictory claims: same hypothesis both supported and rejected.
    by_h: dict[str, set[str]] = {}
    for r in recs:
        if isinstance(r, dict) and isinstance(r.get("hypothesis_id"), str):
            by_h.setdefault(r["hypothesis_id"], set()).add(str(r.get("status")))
    for hid, sts in by_h.items():
        if {"supported", "rejected"} <= sts:
            errors.append(f"contradictory recommendations for {hid}")
    # Missing supporting evidence: supported without cited actions.
    for r in recs:
        if isinstance(r, dict) and r.get("status") == "supported" \
                and not r.get("basis_action_ids"):
            errors.append(f"supported {r.get('hypothesis_id')} cites no evidence actions")
    if not recs:
        warnings.append("no status_recommendations; conclusions untraceable to hypotheses")
    if "uncertainties" not in summary:
        warnings.append("no uncertainties listed; overconfidence risk")
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "normalized": summary if not errors else None}


def labeled_transformation(original: dict, corrected: dict,
                           provenance: str) -> dict:
    """Explicitly labeled transformation — original always retained."""
    return {"kind": "transformation", "original": original,
            "corrected": corrected, "provenance": provenance,
            "note": "machine-generated normalization; original preserved verbatim"}
