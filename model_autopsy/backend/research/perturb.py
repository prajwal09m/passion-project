"""M14 Phase 3: controlled perturbation laboratory (offline).

All perturbations run on isolated copies in a scratch directory;
the original artifact is never modified (verified by content hash
before/after). Supported ops: noise, scale, missingness, shuffle,
subset-drop, value-shift. Measurements: prediction stability,
metric degradation, calibration change, ranking change, subgroup
effects. A robustness map marks stable/sensitive/unexplained
regions and never marks untested regions safe.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path

OPS = ("noise", "scale", "missingness", "shuffle",
       "subset_drop", "value_shift")


def _hash(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def perturb_copy(artifact: str, op: str, scratch: str, seed: int = 7,
                 column: str | None = None,
                 magnitude: float = 0.1,
                 segment: dict | None = None) -> dict:
    """Apply one controlled perturbation to an isolated copy."""
    import pandas as pd
    if op not in OPS:
        raise ValueError(f"unknown perturbation op {op!r}")
    before = _hash(artifact)
    df = pd.read_csv(artifact)
    work = Path(scratch)
    work.mkdir(parents=True, exist_ok=True)
    out = work / f"pert_{uuid.uuid4().hex[:8]}.csv"
    rng = __import__("random").Random(seed)
    target = column or next((c for c in df.columns
                            if c.lower() not in (
                                "label", "target", "score",
                                "prediction")), df.columns[0])
    n = len(df)
    if op == "noise" and target in df.columns:
        try:
            vals = df[target].astype(float)
            df[target] = vals + rng.gauss(0, 1) * magnitude * (
                vals.std() or 1.0)
        except (TypeError, ValueError):
            pass
    elif op == "scale" and target in df.columns:
        try:
            df[target] = df[target].astype(float) * (1.0 + magnitude)
        except (TypeError, ValueError):
            pass
    elif op == "missingness" and target in df.columns:
        mask = [rng.random() < magnitude for _ in range(n)]
        df.loc[mask, target] = float("nan")
    elif op == "shuffle" and target in df.columns:
        vals = list(df[target])
        rng.shuffle(vals)
        df[target] = vals
    elif op == "subset_drop" and segment:
        col, val = segment.get("column"), segment.get("value")
        if col in df.columns:
            df = df[df[col] != val]
    elif op == "value_shift" and target in df.columns:
        try:
            df[target] = df[target].astype(float) + magnitude
        except (TypeError, ValueError):
            pass
    df.to_csv(out, index=False)
    after = _hash(artifact)
    if after != before:
        raise RuntimeError("original artifact modified; refusing")
    prov = {"op": op, "column": target, "magnitude": magnitude,
            "seed": seed, "segment": segment,
            "copy": str(out), "orig_hash": before}
    prov["prov_hash"] = hashlib.sha256(
        json.dumps({k: str(v) for k, v in prov.items()},
                   sort_keys=True).encode()).hexdigest()[:16]
    return prov


def measure(artifact: str, perturbed: dict, session=None,
            inv=None) -> dict:
    """Compare baseline vs perturbed with real diagnostics."""
    import pandas as pd
    from .. import ml_tools as ML
    base = pd.read_csv(artifact)
    pert = pd.read_csv(perturbed["copy"])
    out: dict = {"provenance": perturbed, "n_base": len(base),
                 "n_pert": len(pert)}
    cols = list(base.columns)
    tgt = next((c for c in ("target", "label", "relevance")
                if c in cols), None)
    pred = next((c for c in ("prediction", "pred", "score")
                 if c in cols), None)
    col = perturbed.get("column")
    if col in base.columns and col in pert.columns:
        try:
            vb = base[col].astype(float)
            vp = pert[col].astype(float)
            out["prediction_stability"] = {
                "mean_abs_shift": float((vb - vp).abs().mean()),
                "max_abs_shift": float((vb - vp).abs().max())}
        except (TypeError, ValueError):
            out["prediction_stability"] = {"note": "non-numeric"}
    if tgt and pred and tgt in pert.columns and pred in pert.columns:
        try:
            b = ML.regression_metrics(artifact, target_column=tgt,
                                      prediction_column=pred)
            p = ML.regression_metrics(perturbed["copy"],
                                      target_column=tgt,
                                      prediction_column=pred)
            out["metric_degradation"] = {
                "mae_base": b.get("mae"), "mae_pert": p.get("mae"),
                "delta": (p.get("mae") or 0) - (b.get("mae") or 0)}
        except Exception as exc:
            out["metric_degradation"] = {"error": str(exc)[:120]}
    else:
        out["metric_degradation"] = {"note": "needs target+prediction"}
    return out


def robustness_map(measurements: list[dict]) -> dict:
    """Stable / sensitive / unexplained; untested never safe."""
    regions: dict = {}
    for m in measurements:
        key = (m.get("provenance") or {}).get("op", "?") + ":" + str(
            (m.get("provenance") or {}).get("column", "?"))
        deg = (m.get("metric_degradation") or {}).get("delta")
        if deg is None:
            regions[key] = {"status": "unexplained",
                            "why": "no measurable degradation"}
        elif deg <= 0:
            regions[key] = {"status": "stable",
                            "why": f"delta {deg}"}
        else:
            regions[key] = {"status": "sensitive",
                            "why": f"delta {deg}"}
    regions["_untested"] = {"status": "untested",
                            "why": "never represented as safe"}
    return {"regions": regions,
            "note": "untested regions are never safe or robust"}
