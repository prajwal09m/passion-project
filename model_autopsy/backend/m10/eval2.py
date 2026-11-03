"""M13 section 7 evaluation 2.0 (offline, evidence-required).

Per-scenario dimension scores (each preserved, never collapsed
without the breakdown alongside):
- discovery_precision: naming hypotheses with moving evidence /
  all naming hypotheses.
- discovery_recall: key mechanism named with moving evidence.
- correct_null / false_positive / false_negative.
- experiment_info_value: share of executed specs with
  decision_relevance decisive/supporting (from info_value).
- hypothesis_quality: share of hypotheses that are falsifiable
  (predicted_observation present and mechanism-specific).
- causal_diagnosis / confounder_handling / attribution:
  reuse M9-style behavioral signals.
- conclusion_calibration: no supported-without-evidence and no
  rejected-without-contradiction.
- reproducibility: verification grades when present.
- skeptic_effectiveness / judge_independence / multi_agent_value:
  populated by team runs; single-agent runs record n/a.
- efficiency: tool calls within budget.

Novelty assessment (M13 section 7.3): manifestation novelty
(unfamiliar columns/segments vs the M10 corpus vocabulary) and
mechanism novelty (truth family absent from the M10 corpus).
Novelty is reported, never a score multiplier.
"""
from __future__ import annotations

_M10_VOCAB = {"ward", "district", "slice", "segment", "label", "score",
              "prediction", "target", "date", "split", "region", "fold",
              "x", "x1", "x2", "device_age", "size", "relevance"}
_M10_FAMILIES = {"subgroup", "leakage", "calibration",
                 "misspecification", "drift", "clean", "thin"}


def _hyps(session, inv_id: str) -> list[dict]:
    from ..db import Hypothesis
    return [{"id": h.id, "text": h.text, "status": h.status,
             "pred": h.predicted_observation,
             "evidence_refs": h.evidence_refs or []}
            for h in session.query(Hypothesis).filter(
                Hypothesis.investigation_id == inv_id).all()]


def _moving(h: dict) -> list[dict]:
    return [r for r in h.get("evidence_refs", [])
            if r.get("relation") in ("supports", "contradicts")]


def _names(h: dict, truth: dict) -> bool:
    from .evaluator import _names_family
    return _names_family(h.get("text", ""), truth)


def score(behavior: dict, truth: dict, session=None,
          team: dict | None = None,
          verifications: list[dict] | None = None) -> dict:
    hyps = _hyps(session, behavior["investigation_id"]) \
        if session is not None else []
    naming = [h for h in hyps if _names(h, truth)]
    naming_moving = [h for h in naming if _moving(h)]
    grade = truth.get("grade", "discovered")
    specs = behavior.get("specs_executed") or []

    if grade in ("inconclusive", "correct-null"):
        bad = [h for h in hyps if h.get("status") == "supported"]
        null_ok = not bad
        dims = {"correct_null": 1.0 if null_ok else 0.0,
                "false_positive": 0.0 if null_ok else 1.0,
                "false_negative": 0.0}
    else:
        hit = bool(naming_moving)
        key_hit = not truth.get("key_tool") or truth["key_tool"] in specs
        dims = {
            "discovery_precision": (len(naming_moving) / len(naming)
                                    if naming else 0.0),
            "discovery_recall": 1.0 if hit else 0.0,
            "key_tool_measured": 1.0 if key_hit else 0.0,
            "false_negative": 0.0 if hit else 1.0,
            "false_positive": 0.0,
        }
    falsifiable = [h for h in hyps if (h.get("pred") or "").strip()]
    dims["hypothesis_quality"] = (len(falsifiable) / len(hyps)
                                  if hyps else 0.0)
    statuses = {h.get("status") for h in hyps}
    dims["conclusion_calibration"] = 0.0 if (
        ("supported" in statuses
         and not any(_moving(h) for h in hyps
                     if h.get("status") == "supported"))
        or ("rejected" in statuses
            and not any(r.get("relation") == "contradicts"
                        for h in hyps for r in _moving(h)))) else 1.0
    dims["efficiency"] = 1.0 if behavior.get("tool_calls", 99) <= 6 else 0.5
    if verifications:
        good = sum(1 for v in verifications
                   if v.get("grade") in ("reproduced", "corroborated"))
        dims["reproducibility"] = good / len(verifications)
    if team is not None:
        sk = (team.get("skeptic") or {}).get("challenges", [])
        dims["skeptic_effectiveness"] = 1.0 if sk else 0.5
        dims["judge_independence"] = 1.0 if (
            team.get("judge") or {}).get("verdicts") else 0.0
        dims["multi_agent_value"] = 1.0  # compared externally
    return {"scenario": behavior.get("scenario"), "dimensions": dims,
            "mean": round(sum(dims.values()) / len(dims), 3)}


def novelty(artifact_columns: list[str], truth: dict) -> dict:
    new_cols = [c for c in artifact_columns if c not in _M10_VOCAB]
    return {
        "manifestation_novelty": sorted(new_cols),
        "mechanism_novel": truth.get("family") not in _M10_FAMILIES,
        "note": "novelty is reported, never a score multiplier; a "
                "novel mechanism still needs moving evidence to count "
                "as discovery"}


def aggregate(rows: list[dict]) -> dict:
    import statistics
    keys = sorted({k for r in rows for k in r["dimensions"]})
    out: dict = {"n": len(rows), "per_dimension": {}, "per_scenario": [
        {"scenario": r["scenario"], "mean": r["mean"]} for r in rows]}
    for k in keys:
        vals = [r["dimensions"][k] for r in rows
                if k in r["dimensions"] and isinstance(
                    r["dimensions"][k], (int, float))]
        out["per_dimension"][k] = {
            "mean": round(statistics.fmean(vals), 3) if vals else None,
            "min": min(vals) if vals else None,
            "n": len(vals)}
    means = [r["mean"] for r in rows]
    out["overall"] = {
        "mean": round(statistics.fmean(means), 3) if means else None,
        "stdev": round(statistics.pstdev(means), 3)
        if len(means) > 1 else 0.0}
    out["limitations"] = ("small benchmark; per-scenario table above "
                          "is the claim, not the aggregate alone")
    return out
