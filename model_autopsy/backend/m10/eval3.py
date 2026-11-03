"""M14 Evaluation 3.0 (offline, evidence-required).

Extends eval2 with M14 dimensions: novel discovery, robustness
discovery, risk prioritization, falsification quality,
independent reproduction, live/offline parity, generalization.
Untestable dimensions are recorded as n/a, never zero-filled.
Per-project and per-mechanism rows preserved; novelty reported
separately from ordinary discovery.
"""
from __future__ import annotations

from . import eval2 as E2


def score(behavior: dict, truth: dict, session=None,
          team: dict | None = None,
          verifications: list[dict] | None = None,
          robustness: dict | None = None,
          risks: list[dict] | None = None,
          falsification: dict | None = None,
          parity: dict | None = None) -> dict:
    base = E2.score(behavior, truth, session=session, team=team,
                    verifications=verifications)
    dims = dict(base["dimensions"])
    if truth.get("novel"):
        hit = dims.get("discovery_recall") == 1.0
        dims["novel_discovery"] = 1.0 if hit else 0.0
    if robustness is not None:
        sens = [k for k, v in (robustness.get("regions") or {}).items()
                if isinstance(v, dict) and v.get("status")
                == "sensitive"]
        dims["robustness_discovery"] = 1.0 if sens else 0.0
    if risks is not None:
        dims["risk_prioritization"] = 1.0 if any(
            r.get("status") == "risk-hypothesis" for r in risks) else 0.0
    if falsification is not None:
        dims["falsification_quality"] = 1.0 if falsification.get(
            "experiment") else 0.0
    if parity is not None:
        dims["parity"] = parity.get("parity") if isinstance(
            parity.get("parity"), (int, float)) else "n/a"
    dims["generalization"] = "n/a"
    filt = {k: v for k, v in dims.items() if v != "n/a"}
    nums = [v for v in filt.values() if isinstance(v, (int, float))]
    base["dimensions"] = dims
    base["mean"] = round(sum(nums) / len(nums), 3) if nums else 0.0
    return base


def aggregate(rows: list[dict]) -> dict:
    return E2.aggregate(rows)
