"""M14 Phase 7: falsification + layered confidence (offline).

For every high-confidence finding: falsifiable prediction,
falsification experiment, outcome, survival, remaining
uncertainty. Confidence is layered: observation / measurement /
mechanism / causal / generalization / reproduction. High
observation confidence never auto-creates causal confidence.
"""
from __future__ import annotations


def falsification_plan(hypothesis: dict) -> dict:
    text = hypothesis.get("text", "")
    return {
        "hypothesis_id": hypothesis.get("id"),
        "falsifiable_prediction": hypothesis.get("predicted_observation")
        or f"an independent probe of {text[:80]} fails to reproduce",
        "experiment": "independent probe via an unused tool on the "
                      "same artifact (see m12.verify)",
        "outcome": "not-run",
        "survived": None,
        "uncertainty": "finding stands only with moving evidence; "
                       "absence of falsification attempt is uncertainty",
    }


def confidence_layers(evidence_refs: list[dict],
                      verifications: list[dict] | None = None) -> dict:
    moving = [r for r in (evidence_refs or [])
              if r.get("relation") in ("supports", "contradicts")]
    obs = "high" if moving else "low"
    grades = [(v or {}).get("grade") for v in (verifications or [])]
    repro = "high" if "reproduced" in grades else (
        "medium" if "corroborated" in grades else "low")
    return {"observation": obs,
            "measurement": "medium" if moving else "low",
            "mechanism": "medium" if len(moving) >= 2 else "low",
            "causal": "low",
            "generalization": "low",
            "reproduction": repro,
            "note": "causal and generalization confidence stay low "
                    "without designed interventions and new projects"}


def structured_report(sections: dict) -> dict:
    keys = ("confirmed", "strong", "plausible", "unresolved",
            "rejected", "untested_risks", "inconclusive")
    return {k: list(sections.get(k, [])) for k in keys}
