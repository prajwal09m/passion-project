"""Diagnostic coverage layer (M8 Workstream C).

For every open hypothesis, maps its mechanism family to the measurements
that could support or weaken it, then tracks which are collected (a ran
tool of the right kind) and which are still missing. Selection prefers
tools that fill missing measurements; the dashboard shows the gaps; the
investigator can state exactly which measurement it lacks instead of
guessing.

Families come from `selection._family_of` (generic mechanism words, never
project answers). No ground truth is consulted.
"""
from __future__ import annotations

FAMILY_MEASUREMENTS: dict[str, list[str]] = {
    "drift": ["temporal_changepoint_scan", "residual_time_analysis",
              "distribution_shift_profile", "forecast_diagnostics"],
    "split-hygiene": ["time_split_validation", "forecast_diagnostics"],
    "input-dependence": ["residual_feature_dependence",
                         "regression_metrics"],
    "misspecification": ["residual_time_analysis",
                         "calibration_snapshot", "regression_metrics"],
    "quality": ["data_quality_profile", "dataset_validation"],
    "bias": ["calibration_snapshot", "calibration_and_error_analysis",
             "regression_metrics"],
    "leakage": ["feature_target_suspiciousness",
                "time_split_validation"],
    "subgroup": ["grouped_auc_comparison", "classification_metrics"],
    "calibration": ["calibration_and_error_analysis",
                    "calibration_snapshot"],
    "other": [],
}


def family_of(text: str) -> str:
    from .selection import _family_of
    return _family_of(text or "")


def required_measurements(hypothesis_text: str) -> list[str]:
    return list(FAMILY_MEASUREMENTS.get(family_of(hypothesis_text), []))


def coverage(hypotheses: list[dict], ran_tools: set[str]) -> list[dict]:
    """Per-hypothesis collected/missing measurement sets."""
    out = []
    for h in hypotheses:
        req = required_measurements(h.get("text", ""))
        collected = [t for t in req if t in ran_tools]
        missing = [t for t in req if t not in ran_tools]
        out.append({"hypothesis_id": h.get("id"),
                    "family": family_of(h.get("text", "")),
                    "required": req, "collected": collected,
                    "missing": missing,
                    "covered": not missing or not req})
    return out


def missing_union(hypotheses: list[dict], ran_tools: set[str]) -> list[str]:
    seen: list[str] = []
    for c in coverage(hypotheses, ran_tools):
        for t in c["missing"]:
            if t not in seen:
                seen.append(t)
    return seen
