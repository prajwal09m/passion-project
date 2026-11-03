"""Ground-truth separation (Milestone 4, trust boundary).

Investigation environment: sanitized dir with data CSVs + briefs.json
only. Evaluation environment: ground_truth_eval.json + reference
solutions + scoring rules, stored OUTSIDE the investigator tree and
never passed to triage/lab code. audit_investigator_env() scans every
investigator-readable file for forbidden ground-truth tokens and fails
if any leak through filenames, contents, or briefs.

Trust boundary and limits are documented in
benchmarks/m4_ground_truth_separation.md; hiding the JSON alone is NOT
the control — the audit test is.
"""
from __future__ import annotations

from pathlib import Path

FIX = Path("model_autopsy/tests/fixture_eval")
INV_DIR = FIX / "investigator"
TRUTH_FILE = FIX / "ground_truth_eval.json"


def discovery_input(project: dict) -> dict:
    """What the investigator receives: brief spec + artifact ONLY."""
    import json
    briefs = json.loads((INV_DIR / "briefs.json").read_text(
        encoding="utf-8"))
    return {"spec": project["spec"], "artifact": project["artifact"],
            "brief": briefs.get(project["id"], "")}


def audit_investigator_env(truth: dict | None = None) -> dict:
    """Scan the investigator environment for ground-truth leakage.

    Returns {ok, violations[]}. Any forbidden token found in any
    investigator-readable file (name or content) is a violation.
    """
    import json
    truth = truth or json.loads(TRUTH_FILE.read_text(encoding="utf-8"))
    tokens: set[str] = set()
    for pid, t in truth.items():
        # Project identity (ids, filenames, brief keys) is legitimately
        # known to the investigator; only MECHANISM tokens are concealed.
        for tok in (t.get("forbidden_tokens") or []):
            tokens.add(tok.lower())
    violations = []
    for f in sorted(INV_DIR.iterdir()):
        if not f.is_file():
            continue
        # Every file is readable text in this env; scan all extensions —
        # hints can hide in any file type, not just .csv/.json.
        text = (f.name + "\n")
        try:
            text += f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
        low = text.lower()
        for tok in tokens:
            if tok and tok in low:
                violations.append({"file": f.name, "token": tok})
    # The investigator must never resolve the truth file itself.
    if TRUTH_FILE.exists():
        try:
            TRUTH_FILE.resolve().relative_to(INV_DIR.resolve())
            violations.append({"file": str(TRUTH_FILE),
                               "token": "(truth file inside investigator dir)"})
        except ValueError:
            pass
    return {"ok": not violations, "violations": violations,
            "files_scanned": len(list(INV_DIR.iterdir())),
            "tokens_checked": len(tokens),
            "limitation": "lexical audit only: it cannot catch semantic "
                          "hints a human would notice; see the separation doc"}
