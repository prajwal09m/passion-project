"""Research memory (M9 Workstream 6): a store, not a log.

Reusable methodology, observations, outcomes, and failures persist
across investigations with full provenance (run, project, experiments).
Retrieval is conservative:

- same project family + mechanism similarity → reusable methodology;
- observations/findings transfer only as priors-to-verify, never as
  conclusions (the new project needs independent verification);
- failures warn against repeating dead ends under similar conditions;
- unrelated families never transfer (no conclusion laundering).

Every entry separates what it is: methodology, observation,
project-specific finding, generalized conclusion, or unverified
hypothesis (kind field). Generalized conclusions require explicit
human-independent corroboration counts, not asserted here.
"""
from __future__ import annotations

KINDS = ("methodology", "observation", "finding", "failure",
         "unverified-hypothesis")


def store(session, kind: str, family: str, mechanism: str, summary: str,
          provenance: dict) -> dict:
    """Persist one memory entry. Provenance (run/project/experiments)
    is required — anonymous knowledge is not stored."""
    from ..db import MemoryEntry
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    if not provenance.get("run_id") and not provenance.get(
            "investigation_id"):
        raise ValueError("provenance must name the source run or "
                         "investigation")
    e = MemoryEntry(kind=kind, family=family, mechanism=mechanism,
                    summary=summary, provenance=dict(provenance))
    session.add(e)
    session.commit()
    return {"id": e.id, "kind": kind, "family": family}


def retrieve(session, family: str, mechanism: str = "",
             kinds: list[str] | None = None, limit: int = 10) -> dict:
    """Conservative retrieval: same-family entries ranked by mechanism
    token overlap; observations/findings flagged verify-first."""
    from ..db import MemoryEntry
    from ..causal.hypotheses import similarity
    kinds = kinds or list(KINDS)
    rows = session.query(MemoryEntry).filter(
        MemoryEntry.family == family,
        MemoryEntry.kind.in_(kinds)).all()
    scored = []
    for r in rows:
        sim = similarity(mechanism, r.mechanism) if mechanism else 0.0
        scored.append((sim, r))
    scored.sort(key=lambda t: -t[0])
    out = []
    for sim, r in scored[:limit]:
        transfer = ("reuse" if r.kind == "methodology"
                    else "verify-first" if r.kind in (
                        "observation", "finding", "unverified-hypothesis")
                    else "avoid-repeat")
        out.append({"id": r.id, "kind": r.kind, "family": r.family,
                    "mechanism": r.mechanism, "summary": r.summary,
                    "similarity": round(sim, 3), "transfer": transfer,
                    "provenance": r.provenance})
    return {"entries": out, "n": len(out),
            "note": "methodology may be reused; observations and findings "
                    "require independent verification in the new project"}


def applicable_prior(session, family: str, mechanism: str,
                     current_artifact: str) -> dict:
    """Should a prior result be reused here? Almost always no.

    Reuse requires: same artifact (exact path) + methodology kind.
    Anything else is verify-first or avoid-repeat. This is the
    duplicate-research check with replication allowed on new data.
    """
    res = retrieve(session, family, mechanism,
                   kinds=["methodology", "failure"])
    reusable, warnings = [], []
    for e in res["entries"]:
        prov = e.get("provenance") or {}
        if e["kind"] == "failure":
            warnings.append(e)
        elif prov.get("artifact") == current_artifact:
            reusable.append(e)
        else:
            e["transfer"] = "verify-first"
            warnings.append(e)
    return {"reusable": reusable, "warnings": warnings}
