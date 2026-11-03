"""Central version-aware evaluation pipeline (V2/V3 integration).

Single entry point for ALL scoring paths (live driver, resume, offline
runner, API). Rules:

- Selection: explicit arg > investigation.config["eval_rubric_version"] >
  env default (v2 unless MODEL_AUTOPSY_EVAL_VERSION=v3). Historical
  version-less records resolve to "v2" (documented backward-compatible
  default); invalid identifiers raise (fail fast, never silent switch).
- Scoring: `score_report` deep-copies the report, applies canonical metric
  normalization to the COPY for v3 only (v2 sees raw numbers — v2 behavior
  is byte-identical), dispatches to the frozen v2 scorer or scorer v3,
  stamps `rubric_version`.
- Failure isolation: a v3 scorer exception yields an explicit
  `verdict: "unscored"` error scorecard — never a silent v2 substitution,
  never a corrupted investigation (callers persist what we return).
- No mixing: every scorecard carries exactly one `rubric_version`.
"""
from __future__ import annotations

import copy


def select_eval_rubric(explicit: str | None = None,
                       inv=None) -> str:
    """Resolve the rubric version. See module docstring for precedence."""
    from .. import config as C
    if explicit is not None:
        return C.resolve_eval_rubric(explicit)
    if inv is not None:
        cfg = getattr(inv, "config", None) or {}
        stored = cfg.get("eval_rubric_version")
        if stored is not None:
            # Corrupt stored identifiers fail fast (fail safe at resume).
            v = str(stored).strip().lower()
            if v not in C.EVAL_RUBRIC_VERSIONS:
                raise ValueError(
                    f"stored eval rubric version {stored!r} is invalid: "
                    f"refusing to resume with an ambiguous rubric")
            return v
        return C.EVAL_RUBRIC_DEFAULT  # historical version-less -> v2
    return C.resolve_eval_rubric(None)


def persist_eval_rubric(session, inv, version: str) -> str:
    """Persist the selected rubric on the investigation + record event."""
    from ..db import record_event
    version = select_eval_rubric(explicit=version)
    cfg = dict(getattr(inv, "config", None) or {})
    cfg["eval_rubric_version"] = version
    inv.config = cfg
    session.commit()
    record_event(session, inv.id, "evaluation",
                 f"Evaluation rubric selected: {version}",
                 payload={"eval_rubric_version": version})
    session.commit()
    return version


def _normalized_copy(report: dict) -> dict:
    from . import normalize as N
    rep = copy.deepcopy(report)
    for e in rep.get("experiments", []) or []:
        nums = e.get("numbers")
        if isinstance(nums, dict):
            normed, flags = N.normalize_numbers(str(e.get("tool") or ""),
                                               nums)
            e["numbers"] = normed
            if flags:
                e["normalization"] = flags
    return rep


def score_report(pid: str, eval_report: dict, truth: dict,
                 version: str) -> dict:
    """Score one eval report under exactly one rubric version."""
    from .. import config as C
    version = C.resolve_eval_rubric(version)
    if version == "v3":
        from . import scorer_v3 as V3
        try:
            return V3.score_v3(pid, _normalized_copy(eval_report), truth)
        except Exception as exc:  # explicit, recorded, never silent v2
            return {"project": pid, "rubric_version": "v3",
                    "verdict": "unscored", "overall": None,
                    "dimensions": {}, "weights": dict(V3.R.WEIGHTS),
                    "notes": {"error": f"v3 scoring failed: "
                                       f"{type(exc).__name__}: {exc}"[:300]},
                    "unavailable": ["all"],
                    "assessment": "evaluation failure, not an "
                                  "investigation failure"}
    from . import scorer as V2
    out = V2.score(pid, eval_report, truth)
    out = dict(out)
    out["rubric_version"] = "v2"
    return out
