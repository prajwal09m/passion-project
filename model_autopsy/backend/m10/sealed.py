"""M10 sealed truth + separation audit (evaluator side only).

The investigator path imports `scenarios` only. This module reads
_sealed/truth.json and scans investigator-readable files for
mechanism tokens. Importing this module from investigator code is a
contamination event the audit test forbids.
"""
from __future__ import annotations

from pathlib import Path

BASE = Path("model_autopsy/tests/fixture_m10")
SEALED = BASE / "_sealed" / "truth.json"


def load_truth() -> dict:
    import json
    return json.loads(SEALED.read_text(encoding="utf-8"))


def audit_unseen_env(truth: dict | None = None) -> dict:
    """Scan investigator-readable M10 files for mechanism leakage."""
    truth = truth or load_truth()
    # Only genuinely secret strings are forbidden: tool names (a tool
    # name in an artifact would tell the investigator what to run)
    # and distinctive mechanism phrases. Ordinary column/data words
    # (district, stale, gap, lag) are the investigator's legitimate
    # working material, not leaks.
    tokens = set()
    for _pid, t in truth.items():
        key = (t.get("key_tool") or "").lower()
        if key and key != "none":
            tokens.add(key)
    tokens |= {"near-duplicate", "unit inconsistency",
               "cold-start", "conditional subgroup"}
    tokens -= {"with", "plus", "weak", "mild", "none", "tool",
               "unknown", "small", "signal", "error", "shift",
               "target", "score", "label"}
    violations = []
    for f in sorted(BASE.iterdir()):
        if not f.is_file() or f.suffix not in (".csv",):
            continue
        low = (f.name + "\n" + f.read_text(
            encoding="utf-8", errors="replace")).lower()
        for tok in tokens:
            if tok and tok in low:
                violations.append({"file": f.name, "token": tok})
    return {"ok": not violations, "violations": violations,
            "tokens_checked": len(tokens)}
