"""M14 Phase 8: multi-project research network (offline).

Cross-project relationships, shared diagnostic knowledge,
transfer proposals with independent validation, dependency
graphs, portfolio scheduling hooks. Transfer always creates a
hypothesis requiring new evidence, never an established fact.
"""
from __future__ import annotations


def relationships(projects: list[dict]) -> dict:
    edges = []
    for i, a in enumerate(projects):
        for b in projects[i + 1:]:
            shared = set(a.get("columns", [])) & set(b.get("columns", []))
            if shared and a.get("id") != b.get("id"):
                edges.append({"from": a["id"], "to": b["id"],
                              "shared_columns": sorted(shared)[:6],
                              "kind": "shared-structure"})
    return {"edges": edges,
            "note": "relationships propose transfer hypotheses only"}


def propose_transfer(source_finding: dict, target_profile: dict) -> dict:
    return {"source": source_finding.get("project_id"),
            "content": source_finding.get("content", ""),
            "target": target_profile.get("id", "?"),
            "treat_as": "hypothesis — requires project-specific evidence",
            "validation_required": ["run the discriminating diagnostic",
                                    "record helped/misled outcome"]}


def validate_transfer(proposal: dict, evidence_refs: list[dict],
                      helped: bool) -> dict:
    moving = [r for r in evidence_refs
              if r.get("relation") in ("supports", "contradicts")]
    return {"proposal": proposal.get("content", "")[:120],
            "validated": bool(moving),
            "outcome": "helped" if helped else "misled",
            "note": "validation needs moving evidence on the target"}
