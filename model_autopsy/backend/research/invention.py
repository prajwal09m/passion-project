"""Experiment invention (M9 Workstream 4).

Invention here means new compositions from artifact facts — a question
plus competing hypotheses plus the observed schema yields a tool+args
combination nobody ran, with stated expected outcomes per hypothesis
and an interpretation rule. No new black-box tools, no invented data:

- propose: build candidate specs from question + hypotheses + facts.
- validate: columns exist, args legal, not a duplicate, budget fits,
  tool registered. Invalid specs are refused with reasons.
- execute: run through engine.run_tool (durable action, same budgets).
- interpret: apply the spec's own rule to the result → per-hypothesis
  verdicts (favors_a / favors_b / inconclusive), recorded as events.

A spec is worth running only because its possible outcomes
distinguish explanations — never merely because it is easy to run.
"""
from __future__ import annotations

import uuid

SPEC_VERSION = "m9-spec-v1"


def artifact_facts(artifact: str) -> dict:
    """Read-only peek: real columns, segments, temporal/split structure."""
    facts: dict = {"artifact": artifact, "readable": False, "columns": []}
    try:
        import pandas as pd
        from pathlib import Path
        p = Path(artifact)
        if not p.is_absolute():
            from .. import config as _cfg
            cand = (_cfg.PROJECT_ROOT / artifact).resolve()
            if cand.exists():
                p = cand
        if not p.exists():
            facts["error"] = f"artifact not found: {artifact}"
            return facts
        df = pd.read_csv(p, nrows=2000)
        cols = list(df.columns)
        facts.update({
            "readable": True, "columns": cols,
            "n_rows_peek": int(len(df)),
            "segments": [c for c in ("region", "slice", "district",
                                     "ward", "segment", "zone", "area",
                                     "group", "cluster", "cohort",
                                     "machine", "county", "sensor",
                                     "equipment", "device", "site",
                                     "category")
                          if c in cols],
            "temporal_col": next((c for c in cols if c.lower() in (
                "date", "timestamp", "time", "day", "dt")), None),
            "split_col": next((c for c in ("split", "fold")
                                 if c in cols), None),
            "score_col": next((c for c in cols if c.lower() in (
                "score", "prediction", "pred", "proba")), None),
            "label_col": next((c for c in cols if c.lower() in (
                "label", "target", "y", "grade", "relevance")), None),
            "feature_cols": [
                c for c in cols if c.lower() not in (
                    "label", "target", "y", "grade", "relevance",
                    "score", "prediction", "pred", "proba",
                    "date", "timestamp", "time", "split",
                    "region", "slice", "district", "ward", "segment",
                    "id", "index", "row", "key")],
        })
        # M16 P0-2: explicit column mapping with confidence. Canonical
        # names are high confidence; a single alias is medium; multiple
        # alias candidates for one role are ambiguous (low + clarification
        # note). Never guesses silently: ambiguity is recorded, and the
        # loader stays strict for explicit labels= requests.
        _label_cands = [c for c in ("label", "target", "y", "grade",
                                    "relevance") if c in cols]
        _score_cands = [c for c in ("score", "prediction", "pred",
                                    "proba", "LightGBM_C")
                        if c in df.columns]
        facts["column_mapping"] = {
            "label": {"column": facts.get("label_col"),
                       "confidence":
                       "high" if facts.get("label_col") == "label"
                       else ("medium" if len(_label_cands) == 1
                             else "low"),
                       "alternatives": _label_cands},
            "score": {"column": facts.get("score_col"),
                       "confidence":
                       "high" if facts.get("score_col") in (
                           "score", "prediction")
                       else ("medium" if len(_score_cands) <= 1
                             else "low"),
                       "alternatives": _score_cands},
            "segments": {"columns": list(facts["segments"]),
                          "confidence": "high",
                          "note": "vocabulary + low-cardinality fallback"},
        }
        facts["mapping_notes"] = [
            f"multiple {role} alias candidates {cands}: clarify which "
            f"column is authoritative"
            for role, cands in (
                ("label", _label_cands), ("score", _score_cands))
            if len(cands) > 1]
        if not facts.get("label_col"):
            facts["mapping_notes"].append(
                "no label column found: label-gated diagnostics "
                "unavailable (explicit limitation, not a silent skip)")
        # M14 generalization: data-driven segment fallback. When the
        # name vocabulary finds nothing, a low-cardinality string
        # column is an observed grouping whether or not its name is
        # known. Additive only: never removes vocabulary hits, never
        # promotes label/score/target/prediction columns.
        try:
            _known = set(facts["segments"])
            _excl = {facts.get("label_col"), facts.get("score_col"),
                      "label", "target", "score", "prediction",
                      "pred"} - {None}
            for c in cols:
                if c in _known or c in _excl:
                    continue
                if str(df[c].dtype) == "object":
                    _u = df[c].nunique(dropna=True)
                    if 2 <= int(_u) <= 20:
                        facts["segments"].append(c)
        except Exception:
            pass
    except Exception as exc:
        facts["error"] = f"{type(exc).__name__}: {exc}"[:200]
    return facts


def propose(question: dict, hypotheses: list[dict], facts: dict,
            ran: list[dict], budget_left: dict | None = None) -> list[dict]:
    """Candidate specs; ranked by discriminating power, cost, novelty."""
    budget_left = budget_left or {}
    cands: list[dict] = []

    def add(tool: str, args: dict, distinguishes: str,
            favors: dict[str, str], rule: str, cost: int = 1,
            power_limits: str = "", mislead_risk: str = "") -> None:
        sig = (tool, tuple(sorted(args.items())))
        if any((r.get("tool"), tuple(sorted((r.get("args") or {}).items())))
               == sig for r in ran):
            return  # duplicate: already measured
        n_dist = len([h for h in hypotheses
                      if favors.get(h.get("id"), "no prediction")
                      != "no prediction"])
        dup = any(r.get("tool") == tool for r in ran)
        cands.append({
            "spec_id": uuid.uuid4().hex[:12], "spec_version": SPEC_VERSION,
            "question_ids": [question.get("id")],
            "question_family": question.get("family"),
            "hypotheses_distinguished": [
                {"hypothesis_id": h.get("id"),
                 "expected": favors.get(h.get("id"), "no prediction")}
                for h in hypotheses],
            "tool": tool, "args": args,
            "distinguishes": distinguishes,
            "interpretation_rule": rule,
            "est_cost": {"tool_calls": 1, "relative": cost},
            "info_value": {
                # M13A.3: every spec documents its expected purpose.
                "distinguishes_n": n_dist,
                "cost": cost,
                "power_limits": power_limits or "single diagnostic; "
                "see interpretation_rule indecision bands",
                "mislead_risk": mislead_risk or "low: indecision bands "
                "report inconclusive rather than forcing a verdict",
                "duplicates_existing": dup,
                "decision_relevance": ("decisive" if n_dist >= 2
                                        else "supporting" if n_dist == 1
                                        else "exploratory")},
            "provenance": {"facts_used": sorted(args.keys()),
                           "invented_from": "artifact schema + question"}})

    cols = facts.get("columns") or []
    segs = facts.get("segments") or []
    ids = [h.get("id") for h in hypotheses]
    favors = {i: ("effect concentrates" if k == 0 else "effect absent")
              for k, i in enumerate(ids)}
    # Classification works with label aliases (label/target/y/grade)
    # threaded through labels=; feature_target stays strict (literal).
    label_col = facts.get("label_col")
    has_label_alias = bool(label_col)
    has_label = "label" in cols  # strict: feature tools need literal
    has_target_pred = "target" in cols and "prediction" in cols
    has_relevance = "relevance" in cols and "score" in cols
    cls_labels: dict = {} if label_col in (None, "label") else \
        {"labels": label_col}
    if segs and has_label_alias and facts.get("score_col") not in (
            None, "prediction"):
        add("classification_metrics",
            {"predictions_path": facts["artifact"],
             "score_column": facts["score_col"], "split_by": segs[0],
             **cls_labels},
            f"segment-varying vs uniform quality across {segs[0]}",
            favors,
            "spread >= 0.10 favors the segment mechanism; < 0.03 "
            "favors the uniform mechanism; between: inconclusive")
    if segs and (has_target_pred or has_relevance):
        args = {"predictions_path": facts["artifact"],
                "group_column": segs[0]}
        if has_relevance and not has_target_pred:
            args["target_column"] = "relevance"
            args["prediction_column"] = "score"
        add("regression_metrics", args,
            f"segment-concentrated vs uniform error across {segs[0]}",
            favors,
            "group ratio >= 1.5 favors the segment mechanism; < 1.15 "
            "favors the uniform mechanism; between: inconclusive")
    if facts.get("temporal_col") and has_target_pred:
        add("temporal_changepoint_scan",
            {"predictions_path": facts["artifact"],
             "date_column": facts["temporal_col"]},
            "abrupt change vs gradual drift vs no break",
            favors,
            "break aligned with the suspected event favors the "
            "event-driven mechanism; no break weakens it")
        add("residual_time_analysis",
            {"predictions_path": facts["artifact"],
             "date_column": facts["temporal_col"]},
            "recent-shift vs persistent-error vs stable residuals",
            favors,
            "recent-shift pattern favors the event mechanism; "
            "persistent-error favors misspecification; else inconclusive")
    if has_label:
        add("feature_target_suspiciousness",
            {"feature_csv": facts["artifact"],
             "label_csv": facts["artifact"]},
            "label-duplicate input vs clean inputs",
            favors,
            "non-score |r| >= 0.95 favors leakage; < 0.5 weakens it; "
            "between: inconclusive",
            power_limits="full-column scan; linear association only",
            mislead_risk="medium: legitimate predictive features can "
            "correlate strongly without leaking")
    # Pooled discrimination + calibration baselines (M13A.2): the
    # headline metric and the reliability curve, unconditioned.
    # Distinct specs from grouped variants (exact-args dedup).
    cal_base: dict = {"predictions_path": facts["artifact"]}
    if facts.get("score_col") and facts["score_col"] != "LightGBM_C":
        cal_base["score_column"] = facts["score_col"]
    if label_col not in (None, "label"):
        cal_base["labels"] = label_col
    if has_label_alias and facts.get("score_col"):
        # Cost 2 (follow-up depth, not first-line): preserves the M9
        # frozen first-pick order while making calibration measurable.
        add("classification_metrics", dict(cal_base),
            "sound pooled discrimination vs poor headline quality",
            favors,
            "pooled AUC >= 0.8 weakens blanket-failure claims; "
            "AUC < 0.6 keeps every quality mechanism live; between: "
            "inconclusive",
            cost=2,
            power_limits="pooled metric hides segment failures; "
            "pair with a grouped spec for concentration claims",
            mislead_risk="medium: a good pooled number must never "
            "close segment questions on its own")
        add("calibration_and_error_analysis", dict(cal_base, bins=10),
            "calibrated reliability vs systematic miscalibration",
            favors,
            "max populated-bin gap > 0.15 favors miscalibration; "
            "< 0.05 weakens it; between or thin bins: inconclusive",
            cost=2,
            power_limits="bins with n<30 ignored; thin data cannot "
            "support a miscalibration claim",
            mislead_risk="medium: noisy small bins look like gaps; "
            "only populated bins count")
        add("calibration_and_error_analysis", dict(cal_base, bins=5),
            "operating-range reliability vs threshold-region distortion",
            favors,
            "coarse-bin gap in the operating score range favors a "
            "threshold-region problem; uniform coarse reliability "
            "weakens it; else inconclusive",
            cost=2,
            power_limits="coarse view only; fine structure needs "
            "bins=10",
            mislead_risk="low: coarse bins average out noise, but can "
            "hide narrow distortions")
    # Slice-aware ranking (M15): P@K per slice. Pooled AUC can stay
    # healthy while one slice's top-K collapses; this is the
    # discriminating probe for slice-specific ranking failures.
    if segs and has_label_alias and facts.get("score_col"):
        rank_args: dict = {"predictions_path": facts["artifact"],
                           "slice_column": segs[0]}
        if label_col not in (None, "label"):
            rank_args["labels"] = label_col
        add("ranking_slice_diagnostics", rank_args,
            f"slice-varying ranking vs uniform ranking across "
            f"{segs[0]}",
            favors,
            "slice P@K gap >= 0.15 favors the slice mechanism; "
            "< 0.03 weakens it; between or thin slices: inconclusive")
    # Pooled baseline: headline fit before/after any split. Always worth
    # one measurement when target+prediction exist; grouped and pooled
    # are different specs (dedup is exact-args), so both get measured.
    reg_base: dict = {"predictions_path": facts["artifact"]}
    if has_relevance and not has_target_pred:
        reg_base["target_column"] = "relevance"
        reg_base["prediction_column"] = "score"
    if has_target_pred or has_relevance:
        add("regression_metrics", dict(reg_base),
            "sound pooled fit vs poor headline fit (unconditioned)",
            favors,
            "r2 >= 0.8 establishes a sound pooled fit, weakening "
            "defect claims; r2 < 0.5 keeps every defect mechanism "
            "live; between: inconclusive")
        if facts.get("feature_cols"):
            add("residual_feature_dependence", dict(reg_base),
                "input-tracking vs input-independent error",
                favors,
                "max |r| > 0.5 favors the input-dependence mechanism; "
                "all |r| < 0.2 weakens it; between: inconclusive")
    if facts.get("split_col") and ("target" in cols or "label" in cols):
        shift_args = {"predictions_path": facts["artifact"],
                      "split_column": facts["split_col"]}
        if "target" not in cols:
            shift_args["target_column"] = "label"
        add("distribution_shift_profile", shift_args,
            "target moved between splits vs target stable",
            favors,
            "|mean_shift| large vs spread favors drift; negligible "
            "shift weakens it; between: inconclusive", cost=1)
    if facts.get("readable"):
        add("data_quality_profile",
            {"predictions_path": facts["artifact"]},
            "hygiene defect vs clean inputs",
            favors,
            "material nulls/duplicates favor the quality mechanism; "
            "none weaken it; between: inconclusive", cost=2)
    # Independent second quality probe (M13 §3.3): pooled hygiene
    # cannot be corroborated by itself; per-segment concentration
    # is a different measurement of the same family, so quality
    # rejection via two distinct tools becomes reachable.
    if facts.get("readable") and segs:
        add("segment_quality_screen",
            {"predictions_path": facts["artifact"],
             "segment_column": segs[0]},
            f"concentrated segment defects vs clean-everywhere "
            f"across {segs[0]}",
            favors,
            "worst segment rate > 0.05 favors the quality mechanism; "
            "clean in all adequate segments weakens it; thin "
            "segments: inconclusive",
            cost=2,
            power_limits="segments with n<30 cannot bear; "
            "pooled defects without concentration stay ambiguous",
            mislead_risk="low: rates are descriptive; impact still "
            "needs an error join")
    # Rank: distinguishes 2+ hypotheses first, then cheaper, then tool name.
    cands.sort(key=lambda c: (
        -len([h for h in c["hypotheses_distinguished"]
               if h["expected"] != "no prediction"]),
        c["est_cost"]["relative"], c["tool"]))
    return cands


def validate(spec: dict, facts: dict, ran: list[dict],
             budget: dict | None = None) -> dict:
    """Refuse invalid, redundant, or unaffordable specs with reasons."""
    from .. import tools_registry as TR
    errors: list[str] = []
    tool = spec.get("tool", "")
    args = dict(spec.get("args") or {})
    if tool not in set(TR.TOOL_SPECS):
        errors.append(f"unknown tool {tool!r}")
    cols = set(facts.get("columns") or [])
    # Semantic prerequisites: the tool reads these at runtime.
    # Classification-family tools accept label aliases (target/y/grade)
    # via the labels= argument; only feature_target stays strict.
    if tool in ("classification_metrics", "calibration_and_error_analysis",
                "grouped_auc_comparison") \
            and not facts.get("label_col"):
        errors.append(f"{tool} requires a label column; artifact has none")
    if tool == "feature_target_suspiciousness" and "label" not in cols:
        errors.append(f"{tool} requires a literal 'label' column; "
                      "artifact has none")
    if tool in ("temporal_changepoint_scan", "residual_time_analysis",
                "forecast_diagnostics") and "target" not in cols:
        errors.append(f"{tool} requires target/prediction columns")
    for key in ("split_by", "group_column", "date_column", "split_column",
                "score_column", "target_column", "prediction_column",
                "labels"):
        if args.get(key) and args[key] not in cols:
            errors.append(f"{key}={args[key]!r} not in artifact columns")
    for col_key in ("predictions_path", "feature_csv", "label_csv"):
        if args.get(col_key) and args[col_key] != facts.get("artifact"):
            errors.append(f"{col_key} must reference the project artifact")
    sig = (tool, tuple(sorted(args.items())))
    if any((r.get("tool"), tuple(sorted((r.get("args") or {}).items())))
           == sig for r in ran):
        errors.append("duplicate of an already-executed experiment")
    left = (budget or {}).get("experiments")
    if left is not None and int(left) < 1:
        errors.append("no experiment budget remaining")
    try:
        TR.validate_arguments(tool, args)
    except Exception as exc:
        errors.append(f"argument validation: {exc}")
    return {"valid": not errors, "errors": errors,
            "spec_id": spec.get("spec_id")}


def execute(session, inv, spec: dict) -> dict:
    """Run a validated spec through the engine (same budgets, durable)."""
    from .. import engine as _engine
    from ..db import record_event
    out = _engine.run_tool(session, inv, spec["tool"],
                           dict(spec["args"]), source_meta=True)
    record_event(session, inv.id, "experiment",
                 f"Invented experiment ran: {spec['tool']} "
                 f"(spec {spec.get('spec_id', '?')[:8]})",
                 payload={"spec_id": spec.get("spec_id"),
                          "question_ids": spec.get("question_ids"),
                          "ok": bool(out.get("ok")),
                          "action_id": out.get("action_id"),
                          "distinguishes": spec.get("distinguishes")})
    if out.get("ok"):
        interp = interpret(spec, dict(out.get("result") or {}))
        record_event(session, inv.id, "experiment",
                     f"Spec interpreted: {interp['verdict']} "
                     f"({interp['detail']})",
                     payload={"spec_id": spec.get("spec_id"),
                              "verdict": interp["verdict"],
                              "detail": interp["detail"],
                              "rule": interp["rule"]})
    session.commit()
    return out


def interpret(spec: dict, result: dict) -> dict:
    """Apply the spec's own interpretation rule — no new judgment."""
    tool = spec.get("tool", "")
    verdicts: dict[str, str] = {}
    detail = ""
    if tool == "classification_metrics":
        per = result.get("per_split_auc") or {}
        vals = [v for v in per.values() if isinstance(v, (int, float))]
        spread = max(vals) - min(vals) if len(vals) >= 2 else None
        if spread is not None:
            detail = f"per-segment spread {spread}"
            verdict = ("segment" if spread >= 0.10
                       else "uniform" if spread < 0.03
                       else "inconclusive")
        else:
            auc = result.get("roc_auc")
            detail = f"pooled roc_auc {auc}"
            verdict = ("uniform" if isinstance(auc, (int, float))
                       and auc >= 0.8 else
                       "segment" if isinstance(auc, (int, float))
                       and auc < 0.6 else "inconclusive")
    elif tool == "calibration_and_error_analysis":
        rel = result.get("reliability_bins") or []
        gaps = [abs(b.get("mean_score", 0) - b.get("fraction_positive",
                                                     0))
                for b in rel if isinstance(b, dict)
                and isinstance(b.get("n"), int) and b["n"] >= 30]
        worst = max(gaps) if gaps else None
        detail = f"max populated-bin gap {worst} (brier " \
            f"{result.get('brier')})"
        verdict = ("segment" if worst is not None and worst > 0.15
                   else "uniform" if worst is not None and worst < 0.05
                   else "inconclusive")
    elif tool == "regression_metrics":
        per = result.get("mae_by_group") or {}
        vals = [v for v in per.values() if isinstance(v, (int, float))]
        ratio = (max(vals) / max(min(vals), 1e-9)) if len(vals) >= 2 else None
        if ratio is not None:
            detail = f"group error ratio {ratio:.3f}"
            verdict = ("segment" if ratio >= 1.5
                       else "uniform" if ratio < 1.15 else "inconclusive")
        else:
            r2 = result.get("r2")
            detail = f"pooled r2 {r2}, mae {result.get('mae')}"
            verdict = ("uniform" if isinstance(r2, (int, float))
                       and r2 >= 0.8 else
                       "segment" if isinstance(r2, (int, float))
                       and r2 < 0.5 else "inconclusive")
    elif tool == "ranking_slice_diagnostics":
        gap = result.get("max_slice_gap")
        detail = f"max slice P@K gap {gap} " \
            f"(pooled {result.get('pooled_precision_at_k')})"
        verdict = ("segment" if isinstance(gap, (int, float))
                   and gap >= 0.15
                   else "uniform" if isinstance(gap, (int, float))
                   and gap < 0.03 else "inconclusive")
    elif tool == "feature_target_suspiciousness":
        rows = [r for r in (result.get("top_correlations") or [])
                if isinstance(r, dict)
                and r.get("feature") not in ("label", "_label")
                and not str(r.get("feature", "")).lower().startswith(
                    ("score", "prediction", "pred_"))]
        peak = max([abs(float(r.get("abs_r", 0) or 0)) for r in rows]
                   or [0.0])
        detail = f"max non-score |r| {peak:.3f}"
        verdict = ("segment" if peak >= 0.95
                   else "uniform" if peak < 0.5 else "inconclusive")
    elif tool == "residual_time_analysis":
        pat = result.get("pattern")
        detail = (f"{pat} (late MAE {result.get('late_mae')} vs "
                  f"early {result.get('early_mae')})")
        verdict = ("segment" if pat == "recent-shift pattern"
                   else "uniform" if pat == "persistent-error pattern"
                   else "inconclusive")
    elif tool == "residual_feature_dependence":
        peak = result.get("max_abs_corr") or 0.0
        ranked = result.get("ranked") or []
        top = ranked[0].get("column") if ranked else "?"
        detail = f"max |r| {peak} ({top})"
        verdict = ("segment" if peak > 0.5
                   else "uniform" if peak < 0.2 else "inconclusive")
    elif tool == "distribution_shift_profile":
        by = result.get("by_split") or {}
        stds = [v.get("std") for v in by.values()
                 if isinstance(v, dict) and v.get("std")]
        shift = result.get("mean_shift")
        scale = max(stds) if stds else None
        detail = f"mean_shift {shift} vs spread {scale}"
        verdict = ("segment" if isinstance(shift, (int, float)) and scale
                   and abs(shift) > 0.5 * scale
                   else "uniform" if isinstance(shift, (int, float))
                   and scale and abs(shift) < 0.1 * scale
                   else "inconclusive")
    elif tool == "segment_quality_screen":
        by = result.get("by_segment") or {}
        worst = max(float(result.get("worst_null_rate") or 0),
                      float(result.get("worst_dup_rate") or 0))
        detail = f"worst segment defect rate {worst:.4f} " \
            f"({len(by)} segments)"
        verdict = ("uniform" if by and worst == 0
                   else "segment" if worst > 0.05
                   else "inconclusive")
    elif tool == "data_quality_profile":
        nulls = result.get("nulls") or {}
        total = sum(v for v in nulls.values()
                    if isinstance(v, (int, float)))
        dups = int(result.get("duplicate_rows") or 0)
        n = int(result.get("n") or 0)
        detail = f"nulls {total}, dups {dups}, n {n}"
        verdict = ("uniform" if n and total == 0 and dups == 0
                   else "segment" if n and (total > 0.01 * n
                                             or dups > 0.01 * n)
                   else "inconclusive")
    elif tool == "calibration_snapshot":
        bias = result.get("bias_mean_residual")
        std = result.get("residual_std")
        detail = f"bias {bias} vs std {std}"
        verdict = ("segment" if isinstance(bias, (int, float))
                   and isinstance(std, (int, float)) and std > 0
                   and abs(bias) > 0.5 * std
                   else "uniform" if isinstance(bias, (int, float))
                   and isinstance(std, (int, float)) and std > 0
                   and abs(bias) < 0.1 * std
                   else "inconclusive")
    elif tool == "temporal_changepoint_scan":
        shift = result.get("shift_size")
        detail = f"shift_size {shift}"
        verdict = ("segment" if isinstance(shift, (int, float))
                   and abs(shift) > 5
                   else "uniform" if isinstance(shift, (int, float))
                   and abs(shift) < 1 else "inconclusive")
    else:
        detail, verdict = "no rule for this tool", "inconclusive"
    for h in spec.get("hypotheses_distinguished", []):
        verdicts[h.get("hypothesis_id")] = verdict
    return {"verdict": verdict, "detail": detail,
            "per_hypothesis": verdicts,
            "rule": spec.get("interpretation_rule")}
