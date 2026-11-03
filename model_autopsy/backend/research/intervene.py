"""M15 Phase 4: causal discovery and intervention engine (offline).

Controlled interventions (perturbation, ablation, counterfactual
rescoring, matched comparison, subgroup intervention, temporal
comparison, sensitivity sweep) each record what changed, what was
held constant, validity, permitted causal interpretation,
assumptions, and outcome. A synthetic perturbation is never a
real-world causal intervention: causal claims stay bounded.
"""
from __future__ import annotations

KINDS = ("perturbation", "ablation", "counterfactual",
         "matched-comparison", "subgroup-intervention",
         "temporal-comparison", "sensitivity-sweep",
         "confounding-check")


def plan(kind: str, hypothesis: str, change: str, held: list[str],
         validity: str) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown intervention {kind!r}")
    return {
        "kind": kind, "hypothesis": hypothesis[:160],
        "changed": change, "held_constant": held,
        "validity": validity,
        "permitted_claim": "associational unless a real-world "
                           "intervention with exchangeability",
        "assumptions": ["no unmeasured confounding (untestable "
                        "here)", "measurement faithful"],
        "status": "planned",
    }


def record(plan_: dict, outcome: str, supports: bool | None) -> dict:
    return {**plan_, "outcome": outcome, "supports": supports,
            "status": "executed",
            "causal_note": "synthetic probe: informs mechanism "
                           "plausibility, not real-world causation"}


def confounding_check(measurements: list[dict],
                      suspect: str) -> dict:
    hits = [m for m in measurements if suspect in str(m)]
    return {"suspect": suspect, "n_mentions": len(hits),
            "verdict": "possible confounder — stratify before "
                       "claiming" if hits else "no sign in these "
                       "measurements",
            "required": "stratified or matched comparison"}
