"""Ground-truth comparison and scoring (Milestone 4, rubric v2).

Dimensions A-F + verdict taxonomy. Scores MECHANISM identification
against concealed ground truth using finding titles AND attached
evidence numbers — never title keywords alone. Claim checks: (1) the
confirmed set names the planted mechanism family; (2) at least one
linked experiment carries numbers consistent with it (recomputed
threshold bands, not string matching); (3) no confirmed distractor
(false positive); (4) calibration: null/weak cases must not confirm.

Verdicts: correct / partial / incorrect / unsupported / inconclusive /
correct-null. Overall score is explicitly weighted and always reported
with per-dimension values.
"""
from __future__ import annotations

WEIGHTS = {"discovery": 0.30, "evidence": 0.25, "reasoning": 0.15,
           "calibration": 0.15, "efficiency": 0.05, "reproducibility": 0.10}

# Mechanism families the scorer recognizes, with the evidence numbers
# that must accompany a genuine discovery (bands, not exact values).
MECHANISMS = {
    "eval_credit": {"family": "subgroup",
                    "need": {"tool": "classification_metrics",
                             "min_group_gap": 0.10}},
    "eval_rent": {"family": "segment",
                  "need": {"tool": "regression_metrics",
                           "require": "group_spread_or_bias"}},
    "eval_turbine": {"family": "drift",
                     "need": {"tool": "forecast_diagnostics",
                              "require": "drift_no_overlap"}},
    "eval_docs": {"family": "instability",
                  "need": {"tool": "clustering_stability",
                           "require": "low_silhouette_or_imbalance"}},
    "eval_music": {"family": "slice",
                   "need": {"tool": "ranking_diagnostics",
                            "min_gap": 0.20}},
    "eval_claim": {"family": "input_dependence",
                   "need": {"tool": "regression_metrics",
                            "require": "residual_feature_corr"}},
    "eval_wellness": {"family": None, "need": {}},
    "eval_pilot": {"family": None, "need": {}},
}

DISTRACTOR_MARKERS = {
    "eval_credit": ["leak", "proxy"],
    "eval_turbine": ["leak", "overlap"],
    "eval_pilot": ["leak", "bias", "drift", "subgroup", "proxy"],
}


def _numbers(report: dict) -> list[dict]:
    return [e.get("numbers", {}) for e in report.get("experiments", [])]


def _confirmed_text(report: dict) -> str:
    return " ".join(c.get("title", "") for c in
                    report.get("confirmed_findings", [])).lower()


def _evidence_supports(pid: str, report: dict) -> tuple[bool, str]:
    """Mechanism-level check: do attached numbers support the finding?"""
    need = MECHANISMS[pid]["need"]
    if not need:
        return True, "no failure planted; nothing to support"
    nums = _numbers(report)
    tool = need.get("tool")
    rel = [n for n in nums if n] or []
    if tool == "classification_metrics":
        gaps = [n.get("group_gap", 0) for n in nums]
        ok = any(g >= need["min_group_gap"] for g in gaps)
        return ok, f"max group_gap={max(gaps) if gaps else None}"
    if tool == "regression_metrics":
        for n in nums:
            g = n.get("groups", {}) or {}
            vals = list(g.values()) if isinstance(g, dict) else []
            spread = (max(vals) / max(min(vals), 1e-9)) if len(vals) >= 2 \
                and min(vals) > 0 else 0
            if spread >= 2.0 or abs(n.get("bias", 0)) > 100 \
                    or abs(n.get("residual_feature_corr", 0)) > 0.5:
                return True, (f"bias={n.get('bias')} spread~{spread:.2f} "
                               f"featcorr={n.get('residual_feature_corr')}")
        return False, "no regression breach in evidence numbers"
    if tool == "forecast_diagnostics":
        for n in nums:
            d = n.get("drift") or []
            late_high = len(d) == 2 and d[0] and d[1] / max(d[0], 1e-9) >= 1.5
            if late_high and not n.get("overlap"):
                return True, f"drift={d} overlap={n.get('overlap')}"
        return False, "no drift-without-overlap in evidence numbers"
    if tool == "clustering_stability":
        for n in nums:
            if n.get("silhouette", 1) < 0.4 or n.get("imbalance", 0) > 5:
                return True, (f"sil={n.get('silhouette')} "
                               f"imb={n.get('imbalance')}")
        return False, "no instability signal in evidence numbers"
    if tool == "ranking_diagnostics":
        gaps = [n.get("gap", 0) for n in nums]
        ok = any(g >= need["min_gap"] for g in gaps)
        return ok, f"max slice gap={max(gaps) if gaps else None}"
    return bool(rel), "generic numbers present"


def score(pid: str, report: dict, truth: dict) -> dict:
    t = truth[pid]
    text = _confirmed_text(report)
    confirmed = report.get("confirmed_findings", [])
    n_exp = len(report.get("experiments", []))
    markers = DISTRACTOR_MARKERS.get(pid, [])
    false_positive = any(m in text for m in markers) and bool(confirmed)

    if not t.get("failure"):
        if not confirmed:
            if pid == "eval_pilot":
                verdict = "inconclusive"
                discovery = 1.0
                note = ("correctly inconclusive at n=120: no finding "
                        "fabricated from weak hints")
            else:
                verdict = "correct-null"
                discovery = 1.0
                note = "correct null: no material issue established"
        else:
            verdict = "incorrect"
            discovery = 0.0
            note = "false positive on a no-failure project"
    else:
        supported, why = _evidence_supports(pid, report)
        fam = MECHANISMS[pid]["family"]
        fam_words = {"subgroup": ["subgroup", "ward", "region", "slice"],
                     "segment": ["segment", "bias", "district"],
                     "drift": ["drift", "split", "stale", "shift", "level"],
                     "instability": ["unstab", "separat", "silhouette",
                                     "balance"],
                     "slice": ["slice", "rank", "cold", "position", "p@k"],
                     "input_dependence": ["bias", "segment", "mismatch",
                                          "stale", "lag", "input", "device",
                                          "dependence"]}
        named = any(w in text for w in fam_words.get(fam, []))
        if named and supported and not false_positive:
            if t.get("expect_verdict") == "partial":
                verdict = "partial"
                discovery = 0.6
                note = ("mechanism found at symptom level; second "
                        "documented concern untestable -> partial")
            else:
                verdict = "correct"
                discovery = 1.0
                note = f"mechanism named + numbers support ({why})"
        elif named and supported and false_positive:
            verdict = "partial"
            discovery = 0.4
            note = "right mechanism but a distractor also confirmed"
        elif named and not supported:
            verdict = "unsupported"
            discovery = 0.2
            note = f"mechanism named without supporting numbers ({why})"
        elif not named and supported:
            verdict = "partial"
            discovery = 0.4
            note = "supporting numbers exist but mechanism not identified"
        else:
            verdict = "incorrect" if confirmed else "inconclusive"
            discovery = 0.0
            note = ("wrong mechanism confirmed" if confirmed else
                    "failure missed entirely")

    evidence = 1.0 if (verdict in ("correct", "correct-null")
                       or (verdict == "inconclusive" and not confirmed)) \
        else (0.5 if verdict == "partial" else 0.0)
    reasoning = 1.0 if verdict in ("correct", "correct-null") else (
        0.6 if verdict in ("partial", "inconclusive") else 0.0)
    calibration = 1.0 if verdict in ("correct", "correct-null",
                                     "inconclusive") else (
        0.5 if verdict == "partial" else 0.0)
    efficiency = 1.0 if n_exp <= 4 else max(0.0, 1.0 - 0.2 * (n_exp - 4))
    repro = 1.0 if report.get("executive_summary") and all(
        bool(e.get("experiment_id")) for e in
        report.get("experiments", [])) else 0.0
    dims = {"discovery": discovery, "evidence": evidence,
            "reasoning": reasoning, "calibration": calibration,
            "efficiency": efficiency, "reproducibility": repro}
    overall = round(sum(dims[k] * WEIGHTS[k] for k in WEIGHTS), 3)
    return {"project": pid, "verdict": verdict, "note": note,
            "false_positive": false_positive,
            "dimensions": dims, "weights": WEIGHTS, "overall": overall,
            "assessment": "deterministic + heuristic; LLM/human reserved"}
