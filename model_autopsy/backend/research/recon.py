"""Autonomous project reconnaissance (Milestone 3, Part 2).

Builds a structured project-understanding document from the ProjectSpec
plus read-only inspection of the dataset artifact. Never invents missing
metadata: every unknown is recorded as unknown with an explicit
possible/impossible investigation list.
"""
from __future__ import annotations

import math
from pathlib import Path


def _load_head(location: str, n: int = 5) -> dict:
    """Read-only peek at the dataset artifact (schema + samples)."""
    info: dict = {"location": location, "readable": False}
    try:
        import pandas as pd
        p = Path(location)
        if not p.is_absolute():
            from .. import config as _cfg
            cand = (_cfg.PROJECT_ROOT / location).resolve()
            if cand.exists():
                p = cand
        if not p.exists():
            info["error"] = f"artifact not found: {location}"
            return info
        df = pd.read_csv(p, nrows=2000)
        info.update({
            "readable": True,
            "path": str(p),
            "n_rows_peek": int(len(df)),
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "null_counts": {c: int(df[c].isna().sum()) for c in df.columns},
            "samples": df.head(n).to_dict(orient="records"),
        })
        num = df.select_dtypes(include="number")
        if len(num.columns):
            info["numeric_summary"] = {
                c: {"mean": float(df[c].mean()), "std": float(df[c].std()),
                    "min": float(df[c].min()), "max": float(df[c].max())}
                for c in num.columns[:12]
            }
        for c in df.columns:
            if "date" in c.lower() or "time" in c.lower():
                try:
                    parsed = pd.to_datetime(df[c], errors="coerce")
                    if parsed.notna().sum():
                        info["temporal_hint"] = {
                            "column": c,
                            "min": str(parsed.min()),
                            "max": str(parsed.max()),
                            "n_valid": int(parsed.notna().sum()),
                        }
                        break
                except Exception:
                    pass
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return info


def build_understanding(spec, extra_docs: dict | None = None) -> dict:
    """Assemble the project-understanding document (all Part-2 sections)."""
    extra_docs = extra_docs or {}
    data = _load_head(spec.dataset.location or "")
    cols = data.get("columns", []) if data.get("readable") else []
    has_label = any(c in cols for c in ("label", "target", "y", "grade"))
    has_scores = any(c in cols for c in ("prediction", "score", "pred", "proba"))
    has_dates = ("temporal_hint" in data) or any(
        c in cols for c in ("date", "timestamp", "time"))

    possible, impossible = [], []
    possible.append("dataset_validation: schema/quality overview")
    if has_label and has_scores:
        possible.append("error_analysis: predictions vs ground truth")
    else:
        impossible.append("error_analysis: needs predictions + ground truth")
    if has_dates:
        possible.append("temporal_analysis: drift / split hygiene")
    else:
        impossible.append("temporal_analysis: no date column observed")
    if spec.model.availability == "black_box":
        impossible.append(
            "white-box inspection: black-box availability, "
            "inputs/outputs only")
    else:
        possible.append("model_inspection: per declared availability "
                        f"({spec.model.availability})")

    inconsistencies = []
    desc = (spec.description or "") + " " + (spec.objective or "")
    if "forecast" in desc.lower() and spec.task_type not in (
            "forecasting", "regression"):
        inconsistencies.append(
            "description mentions forecasting but task_type is "
            f"{spec.task_type!r}")
    if data.get("readable") and spec.dataset.n_rows and data.get(
            "n_rows_peek") == 2000 and spec.dataset.n_rows < 2000:
        inconsistencies.append(
            f"spec claims n_rows={spec.dataset.n_rows} but artifact "
            "peek already saw 2000 rows; row count may be stale")

    return {
        "project_id": spec.project_id,
        "predicting": spec.objective or spec.description or "not stated",
        "receives": {"columns": cols,
                     "note": "model inputs per observed artifact schema"},
        "produces": {"target": spec.dataset.target or spec.target_definition,
                     "note": "model outputs per spec"},
        "success": spec.evaluation_methodology or "not stated",
        "evaluation": spec.evaluation_methodology or "not stated",
        "evaluation_assumptions": [
            "reported metrics assume the supplied predictions match "
            "the described evaluation split",
            "recomputed metrics assume label/target columns are correct",
        ],
        "missing": (["objective"] if not spec.objective else [])
        + (["evaluation_methodology"]
           if not spec.evaluation_methodology else [])
        + (["readable_dataset_artifact"]
           if not data.get("readable") else []),
        "possible": possible,
        "impossible": impossible,
        "inconsistencies": inconsistencies,
        "dataset": data,
        "model": {"name": spec.model.name,
                  "framework": spec.model.framework,
                  "availability": spec.model.availability,
                  "training_config": spec.model.training_config},
        "docs": {k: str(v)[:500] for k, v in extra_docs.items()},
        "provenance": {"built_by": "recon.build_understanding",
                       "artifact": data.get("path", spec.dataset.location)},
    }
