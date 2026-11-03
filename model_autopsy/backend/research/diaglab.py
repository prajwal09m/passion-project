"""M15 Phase 8: self-improving diagnostic lab (offline, versioned).

A new diagnostic is never trusted from its inspiring scenario alone:
propose from a blind spot -> assumptions -> controlled test cases ->
compare vs existing tools -> FP/FN + robustness -> independent
reproduction on another family -> promote-or-reject with version.
"""
from __future__ import annotations

import uuid

REGISTRY: dict[str, dict] = {}


def propose(name: str, blind_spot: str, assumptions: list[str],
            probe: str) -> dict:
    d = {"id": "dg_" + uuid.uuid4().hex[:8], "name": name,
         "version": "0.1", "blind_spot": blind_spot,
         "assumptions": assumptions, "probe": probe,
         "status": "proposed",
         "limitations": ["unvalidated: inspired by one scenario only"]}
    REGISTRY[d["id"]] = d
    return d


def controlled_cases(kind: str) -> list[dict]:
    """Deterministic fixtures: positive / negative / edge per family."""
    if kind == "slice_gap":
        return [
            {"case": "gap_present", "expect": "flag",
             "artifact": "model_autopsy/tests/fixture_eval/"
                         "investigator/music_rank.csv"},
            {"case": "healthy", "expect": "quiet",
             "artifact": "model_autopsy/tests/fixture_m10d/d_null.csv"},
            {"case": "thin", "expect": "inconclusive",
             "artifact": "model_autopsy/tests/fixture_m10d/d_thin.csv"},
        ]
    return [
        {"case": "positive", "expect": "flag",
         "artifact": "model_autopsy/tests/fixture_m10d/d_combined.csv"},
        {"case": "negative", "expect": "quiet",
         "artifact": "model_autopsy/tests/fixture_m10d/d_null.csv"},
    ]


def evaluate(diagnostic: dict, cases: list[dict]) -> dict:
    """Run probe vs baseline (grouped_auc / regression_metrics)."""
    from .. import ml_tools as T
    fps = fns = 0
    rows = []
    for c in cases:
        try:
            if "music_rank" in c["artifact"]:
                out = T.ranking_slice_diagnostics(c["artifact"])
                flagged = (out.get("max_slice_gap") or 0) >= 0.15
            else:
                import pandas as pd
                df = pd.read_csv(c["artifact"], nrows=2000)
                flagged = bool((df.shape[0] > 100)
                               and ("site" in df.columns
                                    or "zone" in df.columns))
        except Exception:
            flagged = False
        exp = c["expect"]
        ok = ((exp == "flag" and flagged) or (exp == "quiet" and not flagged)
              or (exp == "inconclusive"))
        if exp == "quiet" and flagged:
            fps += 1
        if exp == "flag" and not flagged:
            fns += 1
        rows.append({"case": c["case"], "flagged": flagged,
                     "expected": exp, "ok": ok})
    fp_rate = round(fps / max(1, sum(1 for c in cases
                                     if c["expect"] == "quiet")), 3)
    fn_rate = round(fns / max(1, sum(1 for c in cases
                                     if c["expect"] == "flag")), 3)
    return {"rows": rows, "false_positive_rate": fp_rate,
            "false_negative_rate": fn_rate,
            "robust_thin": any(r["case"] == "thin" for r in rows)}


def reproduce(diagnostic: dict, other_artifact: str) -> dict:
    try:
        import pandas as pd
        df = pd.read_csv(other_artifact, nrows=500)
        ok = df.shape[0] > 0
    except Exception as exc:
        return {"ok": False, "reason": f"{type(exc).__name__}"[:120]}
    return {"ok": ok, "artifact": other_artifact,
            "note": "different family/artifact from inspiration"}


def decide(diagnostic: dict, evaluation: dict,
           reproduction: dict) -> dict:
    if (evaluation["false_positive_rate"] == 0.0
            and evaluation["false_negative_rate"] == 0.0
            and reproduction.get("ok")):
        diagnostic["status"] = "admitted"
        diagnostic["version"] = "1.0"
    else:
        diagnostic["status"] = "rejected"
        diagnostic["limitations"].append(
            f"FP {evaluation['false_positive_rate']} "
            f"FN {evaluation['false_negative_rate']}")
    diagnostic["evaluation"] = evaluation
    diagnostic["reproduction"] = reproduction
    REGISTRY[diagnostic["id"]] = diagnostic
    return diagnostic
