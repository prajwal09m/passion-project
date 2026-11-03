"""M12 resource-aware scheduler (proposals are free; execution needs approval).

Ranks queued proposals by (importance × info_gain) / cost against
remaining budget. The scheduler NEVER executes paid work: paid
proposals move to awaiting-approval and stay there until a human
token arrives (see authorization). Offline proposals may run
through the provided executor callback.
"""
from __future__ import annotations


def score(prop: dict) -> float:
    return (float(prop.get("importance", 1))
            * float(prop.get("info_gain", 1))
            / max(float(prop.get("cost", 1)), 1e-9))


def rank(proposals: list[dict], budget_left: int) -> list[dict]:
    feasible = [p for p in proposals
                if p.get("status") == "queued"
                and int(p.get("cost", 1)) <= budget_left]
    return sorted(feasible, key=score, reverse=True)


def tick(project: dict, executor=None,
         auth_token: str | None = None) -> dict:
    """One scheduling pass. Returns what happened; mutates project."""
    from . import authorization as AZ
    budget_left = int(project.get("budget", {}).get("tool_calls", 0)) \
        - int(project.get("resource_usage", {}).get("tool_calls", 0))
    acted, deferred = [], []
    for prop in rank(project.get("agenda", []), budget_left):
        kind = prop.get("kind", "offline")
        if kind == "paid":
            try:
                AZ.require(auth_token, "paid:one-campaign",
                           prop.get("id", "proposal"))
            except AZ.AuthorizationError:
                prop["status"] = "awaiting-approval"
                deferred.append({"id": prop.get("id"),
                                 "why": "paid work needs human approval"})
                continue
        if kind == "offline" and executor is not None:
            executor(project, prop)
            prop["status"] = "completed"
            acted.append(prop.get("id"))
        else:
            prop["status"] = "awaiting-approval" if kind == "paid" \
                else "completed"
            (deferred if kind == "paid" else acted).append(
                prop.get("id") if kind == "paid"
                else {"id": prop.get("id")})
        budget_left -= int(prop.get("cost", 1))
    return {"acted": acted, "deferred": deferred,
            "budget_left": budget_left}
