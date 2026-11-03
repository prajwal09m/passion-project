"""M14 Phase 1: novel failure discovery engine (offline, deterministic).

Discovers candidate mechanisms WITHOUT requiring an ontology label
first. Representation is observation-first: each candidate carries
identity, phenomenon, context, evidence, competing explanations,
confounders, falsifiable predictions, proposed experiments,
confidence, validation and reproduction status.

Sources of candidates (all from real artifact measurements):
- unexplained error concentrations (per-segment residual spreads
  beyond what current hypotheses explain);
- conditional behavior shifts (error depends on a feature range or
  a feature-pair interaction);
- residual structure (autocorrelated or heteroscedastic patterns);
- multi-family spanning observations (one observation bearing on
  two families without resolving either).

A surprising observation is never a proven mechanism: initial
validation is always "unvalidated", confidence is capped, and
classification against the ontology is recorded as bearing
(informative) rather than identity.
"""
from __future__ import annotations

import uuid

VALIDATION = ("unvalidated", "supported", "contested", "rejected")
CONF_CAP = 0.45


def _new(phenomenon: str, context: dict, evidence: list[dict],
         competing: list[str], confounders: list[str],
         predictions: list[str], experiments: list[dict]) -> dict:
    return {
        "id": "mech_" + uuid.uuid4().hex[:10],
        "phenomenon": phenomenon,
        "context": context,
        "evidence": evidence,
        "competing_explanations": competing,
        "confounders": confounders,
        "falsifiable_predictions": predictions,
        "proposed_experiments": experiments,
        "confidence": CONF_CAP,
        "validation": "unvalidated",
        "reproduction": "not-attempted",
        "note": "candidate observation, not a proven mechanism",
    }


def discover(session, inv, artifact: str,
             hypotheses: list[dict] | None = None) -> dict:
    """Run observation-first discovery over the artifact.

    Returns candidates + unknown-unknowns (section 1.3 questions).
    Never raises on thin data: reports limits instead.
    """
    from . import invention as INV
    from .. import engine as ENG
    facts = INV.artifact_facts(artifact)
    cols = facts.get("columns") or []
    cands: list[dict] = []
    limits: list[str] = []
    if not facts.get("readable"):
        return {"candidates": [], "unknowns": unknowns([], [], [], []),
                "limits": ["artifact unreadable; nothing discoverable"]}
    ctx = {"artifact": artifact, "columns": cols,
           "segments": facts.get("segments") or []}
    # 1. Unexplained error concentration across observed segments.
    if facts.get("segments") and (
            "target" in cols or "label" in cols):
        seg = facts["segments"][0]
        args: dict = {"predictions_path": artifact,
                      "group_column": seg}
        if "target" not in cols and "label" in cols:
            args["target_column"] = "label"
        if "prediction" not in cols and facts.get("score_col"):
            args["prediction_column"] = facts["score_col"]
        try:
            out = ENG.run_tool(session, inv, "regression_metrics",
                               dict(args), source_meta=True)
            if out.get("ok"):
                per = (out.get("result") or {}).get("mae_by_group") or {}
                vals = [v for v in per.values()
                        if isinstance(v, (int, float))]
                if len(vals) >= 2 and min(vals) > 0 and (
                        max(vals) / min(vals)) >= 1.5:
                    worst = max(per, key=lambda k: per[k])
                    cands.append(_new(
                        f"error concentrates in {seg}={worst} "
                        f"(ratio {max(vals)/min(vals):.2f})",
                        {**ctx, "measurement": "regression_metrics"},
                        [{"tool": "regression_metrics", "args": args,
                          "result_digest": {
                              "mae_by_group": per}}],
                        ["segment reflects true difficulty, not a defect",
                         "preprocessing treats one segment differently"],
                        ["segment mix", "sample size per segment"],
                        [f"per-{seg} recomputation reproduces the "
                         f"concentration on a held-out split",
                         f"removing {worst} flattens pooled error"],
                        [{"kind": "held-out-split",
                          "detail": "recompute per-segment error on "
                                    "an independent partition"}]))
        except Exception as exc:
            limits.append(f"segment screen failed: {type(exc).__name__}")
    # 2. Conditional dependence: residual tracks an input feature.
    if facts.get("feature_cols"):
        try:
            base: dict = {"predictions_path": artifact}
            if "target" not in cols and "label" in cols:
                base["target_column"] = "label"
            if "prediction" not in cols and facts.get("score_col"):
                base["prediction_column"] = facts["score_col"]
            out = ENG.run_tool(session, inv,
                               "residual_feature_dependence",
                               dict(base), source_meta=True)
            res = (out.get("result") or {}) if out.get("ok") else {}
            ranked = res.get("ranked") or []
            top = ranked[0] if ranked else {}
            if isinstance(top.get("abs_r"), (int, float)) and \
                    top["abs_r"] > 0.5:
                cands.append(_new(
                    f"residuals track input {top.get('column')} "
                    f"(|r| {top['abs_r']:.2f})",
                    {**ctx, "measurement":
                     "residual_feature_dependence"},
                    [{"tool": "residual_feature_dependence",
                      "args": base,
                      "result_digest": {"top": top}}],
                    ["legitimate predictive dependence, not leakage",
                     "single-feature proxy for a joint interaction"],
                    ["collinear inputs", "leakage via derived column"],
                    [f"ablating {top.get('column')} changes residual "
                     f"correlation materially",
                     "permutation of the column flattens the effect"],
                    [{"kind": "ablation",
                      "detail": f"recompute without "
                                f"{top.get('column')}"}]))
        except Exception as exc:
            limits.append(f"dependence screen failed: {type(exc).__name__}")
    # 3. Multi-family spanning: one observation, two bearings.
    if len(cands) >= 2:
        cands.append(_new(
            "concentration and dependence co-occur; neither alone "
            "resolves the failure",
            ctx,
            [e for c in cands for e in c["evidence"]],
            ["single joint mechanism explains both",
             "two independent issues coincide"],
            ["shared segment-feature correlation"],
            ["a joint perturbation separates the explanations"],
            [{"kind": "joint-perturbation",
              "detail": "vary the tracked feature within the worst "
                        "segment vs outside it"}]))
    hyps = hypotheses or []
    acts = [{"tool": "regression_metrics"},
            {"tool": "residual_feature_dependence"}]
    return {"candidates": cands,
            "unknowns": unknowns(hyps, acts,
                                 ctx.get("segments") or [],
                                 [c["phenomenon"] for c in cands]),
            "limits": limits}


def unknowns(hypotheses: list[dict], actions: list[dict],
             segments: list[str],
             observed_phenomena: list[str]) -> dict:
    """Explicit unknown-unknown investigation (M14 1.3)."""
    named = " ".join(h.get("text", "") for h in hypotheses).lower()
    unexplained = [p for p in observed_phenomena if not any(
        w in named for w in p.lower().split()[:4])]
    untested = [s for s in segments if s not in named]
    tools = {a.get("tool") for a in actions}
    return {
        "unexplained_behavior": unexplained,
        "untested_assumptions": [
            "pooled metric adequacy" if "classification_metrics"
            not in tools and "regression_metrics" not in tools else
            "none new",
            "segment coverage" if untested else "segments named"],
        "contradictions": [h.get("text", "")[:120] for h in hypotheses
                           if h.get("status") == "rejected"],
        "unmeasured_relationships": [
            "feature-pair interactions (pairwise screen not run)",
            "temporal structure (no temporal column or no scan)"],
        "new_diagnostic_needed": bool(unexplained),
    }
