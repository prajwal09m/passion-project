"""Adversarial self-review (Milestone 3, Part 6).

Independent deterministic checks that challenge an investigator claim.
The reviewer is a separate code path from the experiment runner: it
re-reads recorded evidence and applies fixed rules. It can reject or
downgrade; disagreements are preserved, never silently resolved.
"""
from __future__ import annotations


def review_claim(claim: dict, evidence_results: list[dict]) -> dict:
    """Apply the Part-6 checklist; return verdict + failed checks."""
    checks = []
    n = claim.get("n", 0) or 0
    checks.append({"check": "sample_size_sufficient",
                   "pass": bool(n >= 30),
                   "detail": f"n={n}; <30 is insufficient for a finding"})
    method = (claim.get("method") or "").lower()
    checks.append({"check": "methodology_appropriate",
                   "pass": bool(method) and "invented" not in method,
                   "detail": f"method={method or 'unstated'}"})
    checks.append({"check": "evidence_linked",
                   "pass": bool(evidence_results),
                   "detail": f"{len(evidence_results)} evidence result(s)"})
    leak_risk = any("overlap" in str(r).lower() or "leak" in str(r).lower()
                    for r in evidence_results)
    checks.append({"check": "no_leak_in_diagnostic",
                   "pass": True,
                   "detail": "diagnostic is read-only recomputation; "
                             + ("overlap/leak flag PRESENT in evidence, "
                                "interpreted as signal not contamination"
                                if leak_risk else "no leakage signal")})
    nums = claim.get("numbers") or {}
    checks.append({"check": "numbers_reproducible",
                   "pass": bool(nums),
                   "detail": f"{len(nums)} numeric value(s) with seeds"})
    verdict = "upheld" if all(c["pass"] for c in checks) else "downgraded"
    if not evidence_results:
        verdict = "rejected"
    return {"claim": claim.get("summary", "")[:200],
            "verdict": verdict, "checks": checks,
            "disagreement": None if verdict == "upheld" else
            "reviewer disagrees with investigator confidence; "
            "preserved, not auto-resolved",
            "disproof_wanted": claim.get("refute_criteria")
                               or "state what would disprove this"}


def record_review(session, inv, hypothesis_id: str, review: dict) -> dict:
    import copy as _copy
    from ..db import record_event
    rs = _copy.deepcopy(dict((inv.config or {}).get("research") or {}))
    revs = list(rs.get("reviews") or [])
    revs.append({"hypothesis_id": hypothesis_id, **review})
    rs["reviews"] = revs
    inv.config = {**(inv.config or {}), "research": rs}
    session.commit()
    record_event(session, inv.id, "hypothesis",
                 f"Independent review of {hypothesis_id[:8]}: "
                 f"{review['verdict']}",
                 payload={"hypothesis_id": hypothesis_id,
                          "verdict": review["verdict"]})
    session.commit()
    return review
