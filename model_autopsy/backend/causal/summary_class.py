"""Summary-output classification (M20 Phase 1).

Seven mutually exclusive categories for model-generated summary output.
Never collapsed into one generic invalid status: the class drives repair
eligibility (Phase 3) and report provenance (Phase 6).

Pure function of (message text, validation errors, provider error) — no
DB access, no mutation, no model calls.
"""
from __future__ import annotations

import json
import re

VALID_STRUCTURED = "valid_structured"
PROSE_WITHOUT_BLOCK = "prose_without_block"
MALFORMED_BLOCK = "malformed_block"
SCHEMA_INVALID = "schema_invalid"
SEMANTICALLY_INVALID = "semantically_invalid"
EMPTY_OUTPUT = "empty_output"
PROVIDER_FAILURE = "provider_failure"

ALL_CLASSES = (VALID_STRUCTURED, PROSE_WITHOUT_BLOCK, MALFORMED_BLOCK,
               SCHEMA_INVALID, SEMANTICALLY_INVALID, EMPTY_OUTPUT,
               PROVIDER_FAILURE)

# Repair may be attempted for these classes only (M20 Phase 3.1).
REPAIR_ELIGIBLE = frozenset({PROSE_WITHOUT_BLOCK, MALFORMED_BLOCK,
                             SCHEMA_INVALID, SEMANTICALLY_INVALID})

_FENCE_RE = re.compile(r"```\s*investigation_summary\s*\n?(.*?)```",
                       flags=re.DOTALL)
_BARE_JSON_RE = re.compile(r"\{\s*\"conclusion\"[^{}]*\}", flags=re.DOTALL)

# Error-message signals emitted by engine.validate_structured_summary
# (via report_validation / report_schema). Semantic signals first: they
# describe claims against recorded reality, not shape problems.
_SEMANTIC_SIGNALS = ("unknown hypothesis", "unknown experiment",
                     "fabricat", "contradict", "cites no",
                     "cites unknown", "unsupported status",
                     "claims certainty", "no evidence actions")


def _candidates(text: str) -> list[str]:
    cands = _FENCE_RE.findall(text or "")
    if not cands:
        cands = _BARE_JSON_RE.findall(text or "")
    return cands


def _parseable_blocks(text: str) -> list[dict]:
    out: list[dict] = []
    for cand in _candidates(text):
        try:
            parsed = json.loads(cand.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    return out


def classify(message_text: str | None,
             validation_result: dict | None = None,
             provider_error: str | None = None) -> dict:
    """Classify one summary output.

    validation_result is the dict returned by
    engine.validate_structured_summary (or a test double with
    'valid'/'errors' keys). provider_error is a non-empty string when
    generation/repair failed provider-side.
    Returns {'class': ..., 'reason': ..., 'repair_eligible': bool}.
    """
    if provider_error:
        return {"class": PROVIDER_FAILURE,
                "reason": f"provider-side failure: {str(provider_error)[:160]}",
                "repair_eligible": False}
    text = message_text or ""
    if not text.strip():
        return {"class": EMPTY_OUTPUT,
                "reason": "no summary content returned",
                "repair_eligible": False}
    errors = list((validation_result or {}).get("errors") or [])
    err_blob = " | ".join(errors).lower()
    # Parse-failure signals first: the validator appends a generic
    # 'no structured summary found' after a JSON error, which must not
    # mask a genuine malformed-block attempt.
    if any(sig in err_blob for sig in ("not valid json", "not an object")):
        return {"class": MALFORMED_BLOCK,
                "reason": "a structured block was attempted but not parsed",
                "repair_eligible": True}
    # Conflicting blocks override a passing verdict: the validator only
    # checks the first parseable object.
    blocks = _parseable_blocks(text)
    if len(blocks) >= 2:
        conclusions = {str(b.get("conclusion") or "").strip()
                       for b in blocks}
        statuses = {json.dumps(b.get("status_recommendations") or [],
                               sort_keys=True, default=str) for b in blocks}
        if len(conclusions) > 1 or len(statuses) > 1:
            return {"class": SEMANTICALLY_INVALID,
                    "reason": ("multiple conflicting structured blocks in "
                               "one message"),
                    "repair_eligible": True}
    if validation_result is not None and validation_result.get("valid"):
        return {"class": VALID_STRUCTURED,
                "reason": "schema and semantic validation passed",
                "repair_eligible": False}
    if any("no structured summary found" in e.lower() for e in errors) \
            or (not _candidates(text) and not errors):
        if len(text.strip()) >= 20:
            return {"class": PROSE_WITHOUT_BLOCK,
                    "reason": ("useful prose returned but no structured "
                               "summary block found"),
                    "repair_eligible": True}
        return {"class": EMPTY_OUTPUT,
                "reason": "no usable summary content and no block",
                "repair_eligible": False}
    if any(sig in err_blob for sig in _SEMANTIC_SIGNALS):
        return {"class": SEMANTICALLY_INVALID,
                "reason": ("structured content parsed but violates "
                           "scientific/reporting requirements"),
                "repair_eligible": True}
    return {"class": SCHEMA_INVALID,
            "reason": "structured content parsed but failed schema validation",
            "repair_eligible": True}


def repair_eligible_for(output_class: str) -> bool:
    """Eligibility boundary (M20 Phase 3.1)."""
    return output_class in REPAIR_ELIGIBLE
