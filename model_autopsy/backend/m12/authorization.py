"""M12 human authorization boundary.

Three operation classes: offline (always allowed), proposal
(allowed: creates a plan, never executes), paid/destructive
(requires a human-issued token). No agent, scheduler tick, retry,
or resume path can mint its own authorization — tokens are
created only by `issue` (the human surface: API/dashboard with
explicit user action) and verified on every protected call.
"""
from __future__ import annotations

import secrets

OFFLINE = "offline"       # local compute, DB, file reads/writes
PROPOSAL = "proposal"     # follow-up plans, scheduling entries
PROTECTED = "protected"   # paid API calls, destructive ops


class AuthorizationError(RuntimeError):
    pass


_ISSUED: set[str] = set()


def issue(scope: str = "paid:one-campaign") -> str:
    """Human surface only: mint a single-use authorization token."""
    tok = "auth_" + secrets.token_hex(12)
    _ISSUED.add(tok + "|" + scope)
    return tok


def _valid(token: str | None, scope: str) -> bool:
    return bool(token) and (token + "|" + scope) in _ISSUED


def require(token: str | None, scope: str, action: str) -> None:
    """Raise unless a human-issued token covers this protected action."""
    if not _valid(token, scope):
        raise AuthorizationError(
            f"refused {action}: no human authorization for scope "
            f"{scope!r}; proposals and offline analysis remain "
            f"available without approval")


def consume(token: str, scope: str) -> None:
    _ISSUED.discard(token + "|" + scope)
