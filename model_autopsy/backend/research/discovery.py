"""Open-ended anomaly discovery (Milestone 3, Part 7).

Nine-step workflow for patterns no template covers. Novelty is never
proof: an anomaly becomes a candidate finding only after a targeted
experiment + independent review. New mechanisms join the taxonomy as
'candidate', never 'confirmed', without replicated evidence.
"""
from __future__ import annotations

import uuid

TAXONOMY = [
    "leakage_via_proxy_feature",
    "split_hygiene_failure",
    "subgroup_underperformance",
    "distribution_shift_miss",
    "systematic_bias_region",
    "feature_dominance",
    "miscalibration",
    "temporal_degradation",
    "metric_concealment",
    "preprocessing_train_infer_mismatch",
    "invalid_comparison",
    "perturbation_sensitivity",
    "candidate_novel_mechanism",
]


def describe_anomaly(observation: str, context: dict | None = None) -> dict:
    return {"anomaly_id": uuid.uuid4().hex[:12],
            "observation": observation,
            "context": context or {},
            "status": "described"}


def explanations(observation: str) -> list[dict]:
    """Seed candidate explanations; investigator/reasoner extends freely."""
    return [
        {"mechanism": "leakage_via_proxy_feature",
         "testable": True,
         "test": "ablate suspicious feature; AUC should drop "
                 "materially if leak is real"},
        {"mechanism": "subgroup_underperformance",
         "testable": True,
         "test": "segment metrics; one segment materially worse"},
        {"mechanism": "candidate_novel_mechanism",
         "testable": False,
         "test": "needs a custom targeted experiment"},
    ]


def register_novel_mechanism(session, inv, name: str,
                             evidence: list) -> dict:
    """Record a candidate taxonomy entry (never auto-confirmed)."""
    import copy as _copy
    from ..db import record_event
    rs = _copy.deepcopy(dict((inv.config or {}).get("research") or {}))
    tax = dict(rs.get("taxonomy") or {"base": list(TAXONOMY),
                                      "novel": []})
    tax["base"] = list(tax.get("base") or [])
    tax["novel"] = list(tax.get("novel") or [])
    entry = {"name": name, "status": "candidate",
             "evidence": list(evidence or []),
             "note": "novelty is not proof; needs replication + review"}
    tax["novel"].append(entry)
    rs["taxonomy"] = tax
    inv.config = {**(inv.config or {}), "research": rs}
    session.commit()
    record_event(session, inv.id, "finding",
                 f"Candidate novel mechanism recorded: {name[:100]}",
                 payload={"name": name})
    session.commit()
    return entry
