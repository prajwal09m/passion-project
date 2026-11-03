"""Universal data ingestion (Phase 7).

Loads common formats into pandas frames inside the project root, and
reports honestly what investigations are possible with PARTIAL inputs
(e.g. predictions-only without model weights). Never invents data.
"""
from __future__ import annotations

from pathlib import Path


SUPPORTED_SUFFIXES = (".csv", ".parquet", ".json", ".jsonl", ".npy", ".npz")


def load_artifact(path: str, project_root: str | None = None):
    """Load a data artifact into a pandas DataFrame (or dict for .npz).

    Only reads inside the project root. Parquet requires pyarrow/fastparquet;
    without them a clear error names the missing dependency.
    """
    import pandas as pd
    from .. import config
    root = Path(project_root or config.PROJECT_ROOT).resolve()
    candidate = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise PermissionError(f"artifact {path!r} outside the project root")
    if not candidate.exists():
        raise FileNotFoundError(f"artifact not found: {candidate}")
    suffix = candidate.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(candidate), str(candidate)
    if suffix == ".parquet":
        try:
            return pd.read_parquet(candidate), str(candidate)
        except ImportError:
            raise ImportError("parquet support needs pyarrow or fastparquet; "
                              "convert to CSV to proceed") from None
    if suffix == ".json":
        return pd.read_json(candidate), str(candidate)
    if suffix == ".jsonl":
        return pd.read_json(candidate, lines=True), str(candidate)
    if suffix in (".npy", ".npz"):
        import numpy as np
        return np.load(candidate, allow_pickle=False), str(candidate)
    raise ValueError(f"unsupported format {suffix!r}; supported: {list(SUPPORTED_SUFFIXES)}")


def capability_report(frame=None, columns: list | None = None,
                      has_model_weights: bool = False,
                      has_training_pipeline: bool = False) -> dict:
    """What investigations are possible with the supplied inputs."""
    cols = list(columns or (list(frame.columns) if frame is not None else []))
    has_label = any(c in cols for c in ("label", "target", "y"))
    has_scores = any(c in cols for c in ("prediction", "score", "proba"))
    has_dates = any(c in cols for c in ("date", "timestamp", "time"))
    possible, impossible = [], []
    possible.append("dataset_validation: schema/quality overview")
    if has_label and has_scores:
        possible.append("error_analysis: predictions vs ground truth")
        possible.append("calibration: when scores are probabilities")
    else:
        impossible.append("error_analysis: needs label/target AND prediction/score columns")
    if has_dates:
        possible.append("temporal_validation: chronology and split overlap")
    else:
        impossible.append("temporal_validation: needs a date/timestamp column")
    if has_model_weights:
        possible.append("feature_importance: model internals available")
    else:
        impossible.append("feature_importance: no model weights supplied "
                          "(permutation screening on predictions may substitute)")
    if has_training_pipeline:
        possible.append("leakage_confirmation: pipeline provenance available")
    else:
        impossible.append("leakage_confirmation: association screening only, "
                          "without pipeline provenance")
    return {"columns_seen": cols, "possible": possible, "impossible": impossible,
            "note": "partial inputs are supported; impossible items explain "
                    "exactly what is missing"}
