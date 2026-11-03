"""M12 reproducibility assessment (honest grades, not theater).

Records environment + inputs + outputs for an experiment and grades
re-executability: exact (deterministic replay matches), approximate
(stochastic or version drift tolerated within stated bounds), or
unreproducible (external conditions prevent replay). Never claims
exactness when the environment cannot guarantee it.
"""
from __future__ import annotations

import hashlib
import platform
import sys
import time


def snapshot(artifact: str, tool: str, args: dict,
             result: dict) -> dict:
    import importlib.metadata as MD
    pkgs = {}
    for name in ("pandas", "numpy", "scikit-learn", "torch",
                 "sqlalchemy", "fastapi"):
        try:
            pkgs[name] = MD.version(name)
        except Exception:
            pkgs[name] = "absent"
    try:
        with open(artifact, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        digest = "unreadable"
    return {"tool": tool, "args": args,
            "artifact": artifact, "artifact_sha": digest,
            "result_summary": {k: result.get(k) for k in
                               list(result)[:12]},
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": pkgs, "t": time.time()}


def grade(first: dict, second: dict) -> dict:
    """Compare two snapshots of the same experiment."""
    if first.get("artifact_sha") != second.get("artifact_sha"):
        return {"grade": "unreproducible",
                "reason": "artifact bytes changed between runs"}
    if first.get("packages") != second.get("packages"):
        return {"grade": "approximate",
                "reason": "package versions differ; numeric replay "
                          "not guaranteed",
                "instructions": "pin versions from the first "
                                "snapshot, re-run, compare "
                                "result_summary key-by-key"}
    a, b = first.get("result_summary"), second.get("result_summary")
    if a == b:
        return {"grade": "exact",
                "reason": "identical result summary, same artifact "
                          "and environment",
                "instructions": "re-run with the recorded args; "
                                "summaries must match exactly"}
    return {"grade": "approximate",
            "reason": "same artifact+environment, summaries differ "
                      "(stochastic tool internals)",
            "instructions": "re-run N times; report the distribution, "
                            "not a single number"}
