"""M13 §8.1 portfolio intelligence (offline).

Ranks investigations by promise/blockage/review-need from durable
project docs. No provider calls, no budget mutation — read-only
advice for the scheduler/human.
"""
from __future__ import annotations


def assess(projects: list[dict]) -> dict:
    promising, blocked, needs_review, pausable = [], [], [], []
    for p in projects:
        unres = len(p.get("unresolved", [])) if isinstance(
            p.get("unresolved"), list) else int(
            p.get("n_unresolved", 0) or 0)
        n_exp = len(p.get("experiments", []))
        status = p.get("status", "active")
        pid = p.get("id", "?")
        if status != "active":
            pausable.append({"id": pid, "why": f"status={status}"})
            continue
        if any("awaiting-approval" in str(a) for a in p.get("agenda", [])):
            needs_review.append({"id": pid,
                                 "why": "paid proposal awaits approval"})
        if unres == 0 and n_exp > 0:
            promising.append({"id": pid,
                              "why": "all questions answered; candidate "
                                     "for final report"})
        elif n_exp == 0:
            blocked.append({"id": pid, "why": "no experiments yet; "
                            "check artifact readability"})
        else:
            promising.append({"id": pid,
                              "why": f"{unres} unresolved, "
                                     f"{n_exp} experiments; active"})
    return {"promising": promising, "blocked": blocked,
            "needs_review": needs_review, "pausable": pausable,
            "note": "advisory only; scheduler and human approve actions"}
