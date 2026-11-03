"""Dataset profile (M9 Workstream 5.2): one honest document.

Composes existing read-only inspections (schema peek, quality screen,
target/label distributions, subgroup cardinality, temporal span,
label–segment prevalence) into observed facts with declared
assumptions and limits. No new statistics machinery; no sensitive
attribute inference — segment columns already in the artifact are
described, never enriched.
"""
from __future__ import annotations


def profile(artifact: str) -> dict:
    """Read-only profile; every number traces to the artifact."""
    facts: dict = {"artifact": artifact, "readable": False}
    try:
        import pandas as pd
        from pathlib import Path
        p = Path(artifact)
        if not p.is_absolute():
            from .. import config as _cfg
            cand = (_cfg.PROJECT_ROOT / artifact).resolve()
            if cand.exists():
                p = cand
        df = pd.read_csv(p, nrows=5000)
    except Exception as exc:
        facts["error"] = f"{type(exc).__name__}: {exc}"[:200]
        return facts
    facts["readable"] = True
    facts["n_rows_observed"] = int(len(df))
    cols = list(df.columns)
    facts["columns"] = cols
    facts["feature_types"] = {
        c: ("numeric" if pd.api.types.is_numeric_dtype(df[c])
            else "categorical" if df[c].nunique() <= 50
            else "free-text/id-like")
        for c in cols}
    facts["missingness"] = {c: int(df[c].isna().sum()) for c in cols
                            if int(df[c].isna().sum())}
    label = next((c for c in cols if c.lower() in (
        "label", "target", "y", "grade", "relevance")), None)
    if label is not None:
        vc = df[label].value_counts(dropna=False).head(20)
        facts["target_distribution"] = {str(k): int(v)
                                        for k, v in vc.items()}
        if pd.api.types.is_numeric_dtype(df[label]) and \
                df[label].nunique() <= 10:
            counts = df[label].value_counts(normalize=True)
            facts["class_imbalance_ratio"] = round(
                float(counts.max() / max(counts.min(), 1e-9)), 3)
    seg_col = next((c for c in ("region", "slice", "district", "ward",
                                "segment") if c in cols), None)
    if seg_col is not None:
        vc = df[seg_col].value_counts(dropna=False)
        facts["subgroup_structure"] = {
            "column": seg_col,
            "cardinality": {str(k): int(v) for k, v in vc.items()}}
        if label is not None:
            prev = df.groupby(seg_col)[label].mean(numeric_only=True)
            facts["subgroup_structure"]["label_prevalence"] = {
                str(k): round(float(v), 4) for k, v in prev.items()}
    date_col = next((c for c in cols if c.lower() in (
        "date", "timestamp", "time")), None)
    if date_col is not None:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        if parsed.notna().sum():
            facts["temporal_structure"] = {
                "column": date_col, "min": str(parsed.min()),
                "max": str(parsed.max()),
                "n_valid": int(parsed.notna().sum())}
    numerics = [c for c in cols
                if pd.api.types.is_numeric_dtype(df[c])]
    if len(numerics) >= 2:
        corr = df[numerics[:12]].corr(numeric_only=True).abs()
        pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                pairs.append((corr.columns[j], corr.columns[i],
                              round(float(corr.iloc[i, j]), 3)))
        pairs.sort(key=lambda t: -t[2])
        facts["top_correlations"] = [
            {"a": a, "b": b, "abs_r": r} for a, b, r in pairs[:8]]
    facts["assumptions"] = [
        "first 5000 rows represent the artifact",
        "column names are taken at face value",
        "segment columns are described, never enriched"]
    facts["limits"] = [
        "profile only: associations here are not causal evidence",
        "small subgroups may be noise; check n before concluding"]
    return facts
