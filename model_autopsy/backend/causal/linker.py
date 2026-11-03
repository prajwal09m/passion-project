"""Deterministic post-tool evidence linking (M7 Part 2A).

After a diagnostic runs, the backend — not the model — decides which
recorded hypotheses the result bears on, and records the link with an
explicit justification. Rules are generic per diagnostic semantics with
wide indecision bands (ambiguous numbers link nothing); they never
reference projects, mechanisms, or ground truth. Only `ran` actions are
linked; failed actions and `propose_hypothesis` records never generate
evidence. Every application goes through
`hypotheses.update_with_evidence`, so confidence, status, and history
stay auditable. Per-hypothesis errors are recorded as linker events and
do not break the investigation turn.

What this establishes: that recorded evidence was connected to the
hypotheses it tests. What it does not establish: truth — links are
evidence grades; promotion to `supported` still needs corroboration.
"""
from __future__ import annotations


def _family(text: str) -> str:
    from .selection import _family_of
    return _family_of(text)


def _is_quality(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ("quality", "missing", "null", "duplicat",
                                "corrupt", "hygiene", "artifact"))


def _is_bias(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ("bias", "overpredict", "underpredict",
                                "systematic", "shift")) and "split" not in t


def _is_leakage(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ("leak", "overlap", "split", "hygiene",
                                "chronolog"))


def _is_subgroup(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in ("subgroup", "region", "ward", "slice",
                                "segment", "district", "uneven", "gap",
                                "across", "per-"))


def _rules(tool: str, result: dict) -> list[tuple[str, str, str]]:
    """Return [(family_predicate, direction, reason)] for a ran result.

    Predicates: drift | split-hygiene | misspecification | quality |
    bias | leakage | input-dependence | subgroup | calibration.
    Indecision bands return [].
    """
    out: list[tuple[str, str, str]] = []
    if tool == "data_quality_profile":
        nulls = result.get("nulls") or {}
        total_null = sum(v for v in nulls.values()
                         if isinstance(v, (int, float)))
        dups = int(result.get("duplicate_rows") or 0)
        n = int(result.get("n") or 0)
        if n and total_null == 0 and dups == 0:
            out.append(("quality", "contradicts",
                        f"no nulls/duplicates in n={n}"))
        elif n and (total_null > 0.01 * n or dups > 0.01 * n):
            out.append(("quality", "supports",
                        f"material quality signal "
                        f"(nulls={total_null}, dups={dups}, n={n})"))
    elif tool == "segment_quality_screen":
        # Independent probe from the pooled screen: concentration
        # in a segment is the shape a segment-confounded quality
        # claim predicts; clean-everywhere contradicts it.
        by = result.get("by_segment") or {}
        small = [v for v in by.values()
                 if isinstance(v, dict)
                 and int(v.get("n", 0)) < 30]
        if by and not small:
            worst = max(float(result.get("worst_null_rate") or 0),
                          float(result.get("worst_dup_rate") or 0))
            if worst == 0:
                out.append(("quality", "contradicts",
                            f"clean in all {len(by)} segments "
                            f"(n={result.get('n')})"))
            elif worst > 0.05:
                out.append(("quality", "supports",
                            f"worst segment defect rate {worst:.3f}: "
                            "defects concentrate"))
        # Thin segments: ambiguous, no rule fires (indecision).
    elif tool == "forecast_diagnostics":
        d = result.get("drift_early_vs_late_mae") or []
        overlap = result.get("split_overlap_hint")
        if overlap is False:
            out.append(("split-hygiene", "contradicts",
                        "splits chronological, no overlap"))
        if len(d) == 2 and d[0] and d[1] / max(d[0], 1e-9) >= 1.5 \
                and overlap is False:
            out.append(("drift", "supports",
                        f"late error {d[1]:.1f} >> early {d[0]:.1f} "
                        f"with clean splits"))
    elif tool == "time_split_validation":
        overlap = result.get("overlap")
        if overlap is False:
            out.append(("split-hygiene", "contradicts",
                        "no split overlap detected"))
        elif overlap is True:
            out.append(("split-hygiene", "supports", "split overlap found"))
    elif tool == "distribution_shift_profile":
        shift = result.get("mean_shift")
        by = result.get("by_split") or {}
        stds = [v.get("std") for v in by.values()
                if isinstance(v, dict) and v.get("std")]
        scale = max(stds) if stds else None
        if isinstance(shift, (int, float)) and scale:
            if abs(shift) > 0.5 * scale:
                out.append(("drift", "supports",
                            f"target shift {shift} vs spread {scale}"))
            elif abs(shift) < 0.1 * scale:
                out.append(("drift", "contradicts",
                            f"target shift {shift} negligible"))
    elif tool == "calibration_snapshot":
        bias = result.get("bias_mean_residual")
        std = result.get("residual_std")
        if isinstance(bias, (int, float)) and isinstance(std, (int, float)) \
                and std > 0:
            if abs(bias) > 0.5 * std:
                out.append(("bias", "supports",
                            f"bias {bias:.2f} large vs std {std:.2f}"))
            elif abs(bias) < 0.1 * std:
                out.append(("bias", "contradicts",
                            f"bias {bias:.2f} negligible"))
    elif tool == "temporal_changepoint_scan":
        shift = result.get("shift_size")
        overall = result.get("overall_residual_mean")
        if isinstance(shift, (int, float)):
            if abs(shift) > 5:
                out.append(("drift", "supports",
                            f"changepoint shift {shift} at "
                            f"{result.get('changepoint_date')}"))
            elif abs(shift) < 1:
                out.append(("drift", "contradicts",
                            f"no meaningful break (shift {shift})"))
    elif tool == "residual_time_analysis":
        pat = result.get("pattern")
        if pat == "recent-shift pattern":
            out.append(("drift", "supports",
                        f"late MAE {result.get('late_mae')} >> early "
                        f"{result.get('early_mae')}"))
            out.append(("misspecification", "contradicts",
                        "errors concentrated late, not persistent"))
        elif pat == "persistent-error pattern":
            out.append(("misspecification", "supports",
                        "errors persistent across time"))
    elif tool == "residual_feature_dependence":
        peak = result.get("max_abs_corr") or 0.0
        ranked = result.get("ranked") or []
        top = ranked[0]["column"] if ranked else "?"
        if peak > 0.5:
            out.append(("input-dependence", "supports",
                        f"|r|={peak} for {top}"))
        elif peak < 0.2:
            out.append(("input-dependence", "contradicts",
                        f"max|r|={peak}: no tracking"))
    elif tool == "classification_metrics":
        per = result.get("per_split_auc") or {}
        vals = [v for v in per.values() if isinstance(v, (int, float))]
        if len(vals) >= 2:
            spread = max(vals) - min(vals)
            if spread >= 0.10:
                out.append(("subgroup", "supports",
                            f"per-split AUC spread {spread:.2f} "
                            f"(worst {min(vals):.2f}, best {max(vals):.2f}); "
                            "performance is not uniform"))
            elif spread < 0.03:
                out.append(("subgroup", "contradicts",
                            f"per-split AUC spread {spread:.3f}: uniform"))
    elif tool == "ranking_slice_diagnostics":
        per = result.get("per_slice") or {}
        vals = [v.get("precision_at_k") for v in per.values()
                 if isinstance(v, dict)
                 and isinstance(v.get("precision_at_k"), (int, float))]
        if len(vals) >= 2:
            gap = max(vals) - min(vals)
            if gap >= 0.15:
                out.append(("subgroup", "supports",
                            f"slice P@K gap {gap:.2f} "
                            f"(worst {min(vals):.2f}); ranking not "
                            f"uniform across slices"))
            elif gap < 0.03:
                out.append(("subgroup", "contradicts",
                            f"slice P@K gap {gap:.3f}: uniform ranking"))
    elif tool == "slice_gap_significance":
        if not result.get("testable"):
            pass  # inadequate slice support: no bearing, never forced
        else:
            p = result.get("p_value")
            gap = result.get("gap")
            try:
                p = float(p) if p is not None else None
                gap = float(gap) if gap is not None else None
            except (TypeError, ValueError):
                p, gap = None, None
            if (p is not None and gap is not None
                    and result.get("significant") is True):
                out.append(("subgroup", "supports",
                            f"permutation p={p:.4f}: slice P@K gap "
                            f"{gap:.2f} not noise"))
            elif (p is not None and gap is not None and p >= 0.10):
                out.append(("subgroup", "contradicts",
                            f"permutation p={p:.3f}: gap {gap:.2f} "
                            f"consistent with noise"))
    elif tool == "regression_metrics":
        per = result.get("mae_by_group") or {}
        vals = [v for v in per.values() if isinstance(v, (int, float))]
        if len(vals) >= 2 and max(vals) > 0:
            ratio = max(vals) / max(min(vals), 1e-9)
            if ratio >= 1.5:
                out.append(("subgroup", "supports",
                            f"group MAE ratio {ratio:.2f} "
                            f"(worst {max(vals):.2f}); errors concentrate"))
            elif ratio < 1.15:
                out.append(("subgroup", "contradicts",
                            f"group MAE ratio {ratio:.2f}: uniform"))
        bias = result.get("bias_mean_residual")
        std = result.get("residual_std")
        if isinstance(bias, (int, float)) and isinstance(std, (int, float)) \
                and std > 0:
            if abs(bias) > 0.5 * std:
                out.append(("bias", "supports",
                            f"bias {bias:.2f} large vs std {std:.2f}"))
            elif abs(bias) < 0.1 * std:
                out.append(("bias", "contradicts",
                            f"bias {bias:.2f} negligible"))
    elif tool == "feature_target_suspiciousness":
        rows = result.get("top_correlations") or []
        inputs = [r for r in rows if isinstance(r, dict)
                  and r.get("feature") not in ("label", "_label")
                  and not str(r.get("feature", "")).lower().startswith(
                      ("score", "prediction", "pred_"))]
        peak = max([abs(float(r.get("abs_r", 0) or 0)) for r in inputs]
                   or [0.0])
        if inputs and peak >= 0.95:
            out.append(("leakage", "supports",
                        f"non-score input |r|={peak:.3f}: near-duplicate "
                        "of the label"))
        elif inputs and peak < 0.5:
            out.append(("leakage", "contradicts",
                        f"max non-score |r|={peak:.2f}: no label duplicate"))
    elif tool == "calibration_and_error_analysis":
        rel = result.get("reliability_bins") or []
        gaps = [abs(b.get("mean_score", 0) - b.get("fraction_positive", 0))
                for b in rel if isinstance(b, dict)
                and isinstance(b.get("n"), int) and b["n"] >= 30]
        if gaps:
            worst = max(gaps)
            if worst > 0.15:
                out.append(("calibration", "supports",
                            f"max reliability gap {worst:.2f}: miscalibrated"))
            elif worst < 0.05:
                out.append(("calibration", "contradicts",
                            f"max reliability gap {worst:.3f}: calibrated"))
    return out


_MATCH = {
    "drift": lambda t: _family(t) == "drift",
    "split-hygiene": lambda t: _family(t) == "split-hygiene" or _is_leakage(t),
    "misspecification": lambda t: _family(t) == "misspecification",
    "quality": lambda t: _family(t) == "quality" or _is_quality(t),
    "bias": lambda t: _family(t) in ("drift", "misspecification")
    or _is_bias(t),
    "leakage": lambda t: _is_leakage(t),
    "input-dependence": lambda t: _family(t) in ("input-dependence",
                                                 "misspecification"),
    "subgroup": lambda t: _family(t) == "subgroup" or _is_subgroup(t),
    "calibration": lambda t: _family(t) == "calibration",
}


MOVING_RELATIONS = ("supports", "contradicts")


def has_useful_evidence(session, inv) -> bool:
    """Option A visibility signal (M22 P0.1): True when this investigation
    has at least one moving (supports/contradicts) evidence ref whose
    action ran in this investigation.

    Pure read of recorded linking state — never model text. Baseline
    artifacts (no `_rules` branch, e.g. artifact_summary), unlinked
    actions, failed actions and non-moving relations do not count.
    """
    from ..db import Action, Hypothesis
    inv_id = getattr(inv, "id", None)
    if inv_id is None:
        return False
    aids: set[str] = set()
    for h in session.query(Hypothesis).filter(
            Hypothesis.investigation_id == inv_id).all():
        for r in (h.evidence_refs or []):
            if isinstance(r, dict) \
                    and r.get("relation") in MOVING_RELATIONS \
                    and r.get("action_id"):
                aids.add(str(r["action_id"]))
    if not aids:
        return False
    return session.query(Action).filter(
        Action.investigation_id == inv_id,
        Action.id.in_(sorted(aids)),
        Action.status == "ran").count() > 0


def link_tool_result(session, inv, action) -> list[dict]:
    """Link one ran diagnostic action to matching hypotheses.

    Returns applied updates. Never raises: per-hypothesis failures are
    recorded as linker events so a rule bug cannot break a paid turn.
    """
    from ..db import Hypothesis, record_event
    from .attribution import classify as _classify
    from .hypotheses import update_with_evidence
    if action.status != "ran" or not action.tool_name:
        return []
    if action.tool_name == "propose_hypothesis":
        return []
    rules = _rules(action.tool_name, dict(action.result or {}))
    if not rules:
        return []
    applied = []
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    for h in hyps:
        if h.status == "rejected":
            continue
        seen_actions = {(r.get("action_id") or "")
                        for r in (h.evidence_refs or [])}
        if action.id in seen_actions:
            continue  # idempotent: one link per hypothesis per action
        for fam, direction, reason in rules:
            try:
                # M9 attribution: a rule hit is classified into an
                # explicit relationship. Only supports/contradicts with
                # direct mechanism bearing move belief; topical overlap
                # is recorded visibly but never moves status/confidence.
                attr = _classify(
                    h.text, fam, direction, reason,
                    dict(action.arguments or {}),
                    n=(dict(action.result or {}).get("n")
                       if isinstance(
                           (dict(action.result or {}).get("n")), int)
                       else None))
                rel = attr["relationship"]
                if rel == "neutral":
                    continue  # no bearing: try next rule, else no link
                if attr["moves_belief"]:
                    upd = update_with_evidence(
                        session, h.id, action.id, rel,
                        f"auto-link [{rel}]: {reason} "
                        f"({attr['justification']})")
                    applied.append({"hypothesis_id": h.id,
                                    "direction": rel, **upd})
                    break  # one moving link per hypothesis per action
                from .. import engine as _engine
                _engine.link_evidence(session, h.id, action.id, rel)
                applied.append({"hypothesis_id": h.id,
                                "direction": rel, "status": h.status,
                                "non_moving": True,
                                "justification": attr["justification"]})
                break  # one link per hypothesis per action
            except Exception as exc:  # rule/model bug: record, continue turn
                record_event(session, inv.id, "linker",
                             f"auto-link skipped for {h.id[:8]}",
                             detail=f"{type(exc).__name__}: {exc}"[:200],
                             payload={"hypothesis_id": h.id,
                                      "action_id": action.id})
                session.commit()
    # M16 P1-2: audit the hypotheses this action did NOT move. A
    # skipped hypothesis gets a recorded reason (no bearing of any
    # rule), so 'why did this evidence change nothing' is answerable.
    linked_ids = {a["hypothesis_id"] for a in applied}
    skipped = [{"h": h.id[:8],
                "tried_rules": [f for f, _, _ in rules]}
               for h in hyps
               if h.id not in linked_ids and h.status != "rejected"]
    if skipped:
        record_event(session, inv.id, "linker",
                     f"{action.tool_name} #{action.seq}: no bearing on "
                     f"{len(skipped)} hypotheses",
                     payload={"action_id": action.id, "skipped": skipped})
        session.commit()
    if applied:
        record_event(session, inv.id, "linker",
                     f"auto-linked {action.tool_name} "
                     f"#{action.seq} to {len(applied)} hypotheses",
                     payload={"action_id": action.id, "applied": [
                         {"h": a["hypothesis_id"][:8],
                          "d": a["direction"],
                          "s": a["status"]} for a in applied]})
        session.commit()
    return applied
