"""Causal diagnosis and conclusion discipline (M6 Part 2E).

Levels (strict order):
  anomaly < correlation < plausible < supported < established.

- anomaly: a measured deviation (a diagnostic ran and shows it).
- correlation: co-movement without a mechanism test.
- plausible: a hypothesis with a predicted observation, no contradiction yet.
- supported: 2+ supporting experiments, no unresolved contradiction,
  confounders addressed, cited action ids.
- established: supported + an intervention/counterfactual/ablation or a
  pre-registered changepoint confirmed on held-out data.

The gate refuses to promote without cited evidence. An accurate
inconclusive outranks an unsupported confirmation.
"""
from __future__ import annotations

LEVELS = ("anomaly", "correlation", "plausible", "supported", "established")


def grade(hypothesis: dict, supports: int, contradicts: int,
          has_intervention: bool = False,
          confounders_addressed: bool = False) -> dict:
    text = (hypothesis.get("text") or "")
    if contradicts >= 2:
        return {"level": "plausible", "verdict": "rejected",
                "reason": "contradicted by 2+ recorded experiments"}
    if contradicts >= 1:
        return {"level": "plausible", "verdict": "weakened",
                "reason": "one contradiction recorded; demoted pending replication"}
    if has_intervention and supports >= 2 and confounders_addressed:
        return {"level": "established", "verdict": "established",
                "reason": "intervention/counterfactual + corroboration, confounders addressed"}
    if supports >= 2 and confounders_addressed:
        return {"level": "supported", "verdict": "supported",
                "reason": "2+ supporting experiments, no contradiction, confounders addressed"}
    if supports >= 1:
        return {"level": "plausible", "verdict": "plausible",
                "reason": "single supporting experiment; needs independent corroboration"}
    return {"level": "anomaly", "verdict": "inconclusive",
            "reason": "no supporting experiment cited; report what is missing"}


CONFOUNDER_CHECKLIST = [
    "split hygiene (overlap / chronological order)",
    "label definition / leakage via feature-target correlation",
    "missingness / quality shift",
    "segment vs global effect",
    "calibration drift vs discrimination loss",
]


def check_confounders(addressed: dict[str, bool]) -> dict:
    missing = [c for c in CONFOUNDER_CHECKLIST if not addressed.get(c)]
    return {"addressed": [c for c in CONFOUNDER_CHECKLIST if addressed.get(c)],
            "missing": missing,
            "ok": not missing,
            "note": ("all confounders addressed" if not missing
                     else f"unaddressed: {', '.join(missing)}")}
