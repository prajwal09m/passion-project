"""M14 Phase 5: predictive failure intelligence (offline).

Risk hypotheses are research priorities, never confirmed defects.
Every estimate explains evidence, missing evidence, assumptions,
uncertainty, and what would change confidence. Prioritization is
transparent and validated against held-out projects (see eval3).
"""
from __future__ import annotations


def hypothesize(facts: dict, measurements: dict | None = None) -> list[dict]:
    measurements = measurements or {}
    risks: list[dict] = []

    def add(area: str, evidence: str, missing: str, assume: str,
            up: str, down: str) -> None:
        risks.append({
            "area": area, "status": "risk-hypothesis",
            "evidence_used": evidence, "missing_evidence": missing,
            "assumptions": assume,
            "uncertainty": "high until a targeted test runs",
            "raise_confidence": up, "lower_confidence": down})

    cols = facts.get("columns") or []
    if not facts.get("readable"):
        return [{"area": "artifact unreadable",
                 "status": "risk-hypothesis",
                 "evidence_used": "no readable artifact",
                 "missing_evidence": "everything",
                 "assumptions": "none possible",
                 "uncertainty": "total",
                 "raise_confidence": "readable artifact",
                 "lower_confidence": "n/a"}]
    if facts.get("segments"):
        add("thin-segment coverage",
            f"segments observed: {facts['segments']}",
            "per-segment sample sizes",
            "segment column denotes evaluation slices",
            "a segment with n<30 and high error",
            "all segments adequate with flat errors")
    if facts.get("score_col") and facts.get("label_col"):
        add("calibration weakness",
            "scores and labels present; reliability unmeasured",
            "reliability bins in operating range",
            "scores are intended as probabilities",
            "populated-bin gap >0.15",
            "populated-bin gap <0.05")
    if facts.get("feature_cols"):
        add("unusual input dependence",
            f"features: {len(facts['feature_cols'])} numeric inputs",
            "residual-feature screen",
            "features are model inputs, not identifiers",
            "max |r| > 0.5", "all |r| < 0.2")
    if not facts.get("split_col") and not facts.get("temporal_col"):
        add("unevaluated distribution shift",
            "no split or temporal column to test shift",
            "a held-out partition",
            "evaluation data may differ from training",
            "a shift probe on new data", "shift probe flat")
    return risks


def prioritize(risks: list[dict]) -> list[dict]:
    order = {"thin-segment coverage": 0, "calibration weakness": 1,
             "unusual input dependence": 2,
             "unevaluated distribution shift": 3}
    return sorted(risks,
                  key=lambda r: order.get(r.get("area", ""), 9))


def early_warning(risk: dict, artifact: str) -> dict:
    """Targeted test proposal for a high-priority risk."""
    area = risk.get("area", "")
    if "segment" in area:
        return {"test": "per-segment error recomputation",
                "why": "ordinary pooled metrics miss concentrations",
                "tool": "regression_metrics or classification_metrics"}
    if "calibration" in area:
        return {"test": "reliability bins in operating range",
                "why": "headline AUC hides reliability gaps",
                "tool": "calibration_and_error_analysis"}
    if "dependence" in area:
        return {"test": "residual-feature screen",
                "why": "ordinary fit metrics miss input tracking",
                "tool": "residual_feature_dependence"}
    return {"test": "held-out partition probe",
            "why": "no shift test exists yet",
            "tool": "distribution_shift_profile"}
