"""M19 Phase 1: provider request validation + fallback eligibility boundary.

Stdlib-only, no session access: pure decisions about request shape and
failure category. Recovery construction (which needs recorded state)
lives in `loop.py`; everything that decides *whether* recovery is allowed
lives here so both the cross-turn and in-turn paths share one policy.

Never handles credentials: diagnostics carry modes, categories, and
counts only — never keys, tokens, or request bodies.
"""
from __future__ import annotations

# Continuation-state failures: the request died because the chain
# reference (or the chained input shape) was refused — never retried
# identically, exactly once recoverable via full-context re-send.
# Mirrors client.CHAIN_STATE_ERROR_STATUSES; kept local so the policy is
# explicit and import-safe.
CHAIN_FAILURE_STATUSES = frozenset({400, 404, 409, 410, 413})

# Failures that must NEVER trigger a fallback: credentials/permission
# (retrying is useless and noisy), provider overload/rate-limit (the
# client's own bounded retry already owns those), or local budget stops.
NO_FALLBACK_STATUSES = frozenset({401, 403, 429, 500, 502, 503, 504})


def validate_request(input_items, previous_response_id,
                     tools) -> dict:
    """Pre-dispatch validation. Unknown-good shapes pass; known-bad fail.

    Returns {"mode": "chained"|"full", "problems": [...]}. Empty problems
    means sendable. Checks shape only — budgets are enforced separately
    by the governor so financial/token policy stays in one place.
    """
    problems: list[str] = []
    if not isinstance(input_items, list) or not input_items:
        problems.append("input must be a non-empty list")
        items = []
    else:
        items = input_items
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            problems.append(f"item {i}: not a dict")
            continue
        # Role/content shape (initial context, briefs, nudges, recovery
        # messages): the standard Responses input message.
        if "role" in it:
            content = it.get("content")
            if isinstance(content, list):
                rtext = "".join(
                    str(p.get("text") or "")
                    for p in content if isinstance(p, dict))
            else:
                rtext = str(content or "")
            if not rtext.strip():
                problems.append(f"item {i}: role message has no content")
            continue
        if not it.get("type"):
            problems.append(f"item {i}: missing type")
            continue
        t = it.get("type")
        if t == "function_call_output":
            if not it.get("call_id") or it.get("output") in (None, ""):
                problems.append(
                    f"item {i}: function_call_output needs call_id+output")
        elif t == "message":
            content = it.get("content")
            if isinstance(content, list):
                text = "".join(
                    str(p.get("text") or "")
                    for p in content if isinstance(p, dict))
            else:
                text = str(content or "")
            if not text.strip():
                problems.append(f"item {i}: message has no usable content")
        elif t == "function_call":
            if not it.get("call_id") or not it.get("name"):
                problems.append(
                    f"item {i}: function_call needs call_id+name")
        # Other item types: accepted as unknown-good — validation rejects
        # known-bad, never unknown-good.
    chained = bool(previous_response_id)
    if chained:
        if not isinstance(previous_response_id, str) or \
                not previous_response_id.strip():
            problems.append("continuation id is blank")
        # A chained request whose input carries no substantive content
        # (e.g. only empty outputs) is the M18 failure shape: refuse
        # locally instead of billing an attempt on a known rejection.
        substantive = False
        for it in items:
            if not isinstance(it, dict):
                continue
            if "role" in it:
                _rtext = it.get("content")
                if isinstance(_rtext, list):
                    _rtext = "".join(
                        str(p.get("text") or "")
                        for p in _rtext if isinstance(p, dict))
                if str(_rtext or "").strip():
                    substantive = True
                    break
                continue
            t = it.get("type")
            if t == "message":
                substantive = True
                break
            if t in ("function_call_output", "function_call"):
                out = it.get("output")
                if isinstance(out, str) and out.strip():
                    substantive = True
                    break
                if isinstance(out, dict) and out:
                    substantive = True
                    break
                if t == "function_call":
                    substantive = True
                    break
        if items and not substantive:
            problems.append(
                "chained input has no substantive content "
                "(M18 empty-input shape)")
    if not isinstance(tools, list) or not tools:
        problems.append("tool definitions must be a non-empty list")
    return {"mode": "chained" if chained else "full",
            "problems": problems}


def failure_category(status_code: int | None, had_chain: bool) -> str:
    """Classify a provider failure for recovery decisions."""
    if status_code is None:
        return "transport-or-network"
    if status_code in (401, 403):
        return "authentication"
    if status_code in NO_FALLBACK_STATUSES:
        return "transient-or-server"
    if status_code in CHAIN_FAILURE_STATUSES:
        return ("continuation-state" if had_chain
                else "request-shape")
    return "other-provider-error"


def fallback_eligible(status_code: int | None, had_chain: bool,
                      fallback_used: bool) -> tuple[bool, str]:
    """Single policy for every fallback site (cross-turn and in-turn).

    Eligible only for continuation-state/request-shape failures with a
    chain in play and no fallback used yet this turn. Everything else —
    auth, transient/server (owned by client retry), unknown, or an
    already-spent fallback — is refused with a reason.
    """
    if fallback_used:
        return False, "a fallback was already attempted"
    if status_code in (401, 403):
        return False, "authentication failure must not trigger fallback"
    if status_code is None:
        return False, "network failure carries no chain diagnosis"
    if status_code in NO_FALLBACK_STATUSES:
        return False, (f"status {status_code} is owned by bounded retry, "
                       "not fallback")
    if status_code in CHAIN_FAILURE_STATUSES and had_chain:
        return True, ""
    if status_code in CHAIN_FAILURE_STATUSES:
        return False, "chain failure without a chain in play"
    return False, f"status {status_code} is not fallback-eligible"
