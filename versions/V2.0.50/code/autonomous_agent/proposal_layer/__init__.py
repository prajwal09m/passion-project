"""Evidence-grounded proposal layer (Phase 2 implementation).

Inert by construction: this package can read its allowlisted evidence view,
compose declarative proposals, validate them, and record lifecycle rows in the
append-only proposal ledger. It cannot execute experiments, write candidate
source, open the holdout, or cross into the execution representation except
through ``compiler.compile_proposal`` under an ACCEPTED_FOR_EXECUTION state.

Feature flag: ``autonomous_agent/proposal_config.json`` ->
``allow_generated_proposals`` (default OFF; missing/malformed => OFF). This is
deliberately SEPARATE from Campaign 1's ``autonomy_config.json``, which this
phase does not touch. The supervisor never imports this package, so the flag
being OFF (or the package existing at all) cannot change supervisor behavior.
"""
from __future__ import annotations

import json
from pathlib import Path

FLAG_FILE = "proposal_config.json"
FLAG_NAME = "allow_generated_proposals"


def proposals_enabled(root: Path | str) -> bool:
    """Fail-closed: only an explicit ``true`` in the reviewed flag file enables
    the production proposal cycle. Everything else means OFF."""
    try:
        data = json.loads(
            (Path(root) / "autonomous_agent" / FLAG_FILE)
            .read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    return data.get(FLAG_NAME) is True
