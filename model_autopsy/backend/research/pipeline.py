"""M15 Phase 3: observation-to-mechanism pipeline (offline).

Observation → anomaly characterization → candidate mechanisms →
competing predictions → discriminating experiments → evidence →
conclusion. Never jumps from anomaly to causal explanation.
Includes hypothesis diversity (clustering, redundancy,
alternative-family, counter-hypotheses) and a required
why-this-lead explanation.
"""
from __future__ import annotations


def characterize(observation: str, measurements: list[dict]) -> dict:
    return {
        "observation": observation,
        "anomaly": "deviation of measured behavior from the "
                   "project's stated expectation",
        "measurements": measurements,
        "character": {
            "concentrated": any("concentrat" in str(m) or "ratio"
                                in str(m) for m in measurements),
            "conditional": any("interact" in str(m) or "joint"
                               in str(m) for m in measurements),
        },
    }


def candidates(character: dict, families: list[str]) -> list[dict]:
    out = []
    for fam in families:
        out.append({
            "family": fam,
            "mechanism": f"{fam} explanation of: "
                         f"{character['observation'][:100]}",
            "predictions": [
                f"a {fam}-targeted probe reproduces the anomaly",
                f"removing the {fam} factor removes the anomaly"],
            "falsification": f"a {fam}-targeted probe shows nothing",
            "required_experiments": [f"{fam}-discriminating probe"],
            "confidence": 0.3, "status": "candidate",
        })
    return out


def diversify(hypotheses: list[dict]) -> dict:
    """Cluster near-duplicates, demand alternative families."""
    import re
    tok = lambda t: set(re.findall(r"[a-z]{4,}", t.lower()))  # noqa: E731
    clusters: list[list[int]] = []
    for i, h in enumerate(hypotheses):
        placed = False
        for c in clusters:
            a = tok(hypotheses[c[0]].get("text", ""))
            b = tok(h.get("text", ""))
            if a and b and len(a & b) / max(len(a | b), 1) > 0.6:
                c.append(i)
                placed = True
                break
        if not placed:
            clusters.append([i])
    fams = {h.get("family", "other") for h in hypotheses}
    return {
        "clusters": clusters,
        "redundant": sum(len(c) - 1 for c in clusters),
        "families": sorted(fams),
        "needs_counter": len(fams) < 2,
        "needs_missing_mechanism": len(hypotheses) < 3,
    }


def why_lead(lead: dict, rivals: list[dict], evidence: list[dict]) -> dict:
    moving = [e for e in evidence
              if e.get("relation") in ("supports", "contradicts")]
    return {
        "lead": lead.get("mechanism", "")[:160],
        "beats_rivals_because":
            f"{len([m for m in moving if m.get('for_lead')])} moving "
            f"measurements favor it vs "
            f"{len([m for m in moving if not m.get('for_lead')])} "
            "for rivals; see evidence refs",
        "would_change_mind":
            lead.get("falsification", "a failed discriminating probe"),
        "note": "usefulness comparison, not a vote",
    }


def conclude(cands: list[dict], evidence: list[dict]) -> dict:
    scored = []
    for c in cands:
        s = sum(1 for e in evidence
                if e.get("relation") == "supports"
                and e.get("candidate") == c["family"])
        x = sum(1 for e in evidence
                if e.get("relation") == "contradicts"
                and e.get("candidate") == c["family"])
        scored.append((s - x, c))
    scored.sort(key=lambda t: -t[0])
    if not scored or scored[0][0] <= 0:
        return {"conclusion": "no candidate earns belief; the anomaly "
                              "remains unexplained",
                "lead": None}
    return {"conclusion": f"lead: {scored[0][1]['family']} "
                          f"(net {scored[0][0]})",
            "lead": scored[0][1]}
