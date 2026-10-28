"""Model Autopsy — backend configuration.

All secrets come from environment variables; nothing secret is ever
imported into frontend code or written to the repository. Only the
non-secret operational knobs live in `settings` (persisted in SQLite).
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
MODEL_AUTOPSY_DIR = BACKEND_DIR.parent
PROJECT_ROOT = MODEL_AUTOPSY_DIR.parent          # model_autopsy -> Demand Zone repo root

# Meta Model API (Muse Spark). Endpoint facts verified against dev.meta.ai
# docs: base https://api.meta.ai/v1, Responses API at /responses, bearer key.
META_BASE_URL_DEFAULT = "https://api.meta.ai/v1"
DEFAULT_MODEL_ID = "muse-spark-1.3"

DB_PATH = (Path(os.environ["MODEL_AUTOPSY_DB_PATH"]).expanduser()
           if os.environ.get("MODEL_AUTOPSY_DB_PATH", "").strip()
           else BACKEND_DIR / "data" / "model_autopsy.db")


def meta_api_key() -> str | None:
    key = os.environ.get("MODEL_API_KEY", "").strip()
    return key or None


def meta_base_url() -> str:
    return os.environ.get("MODEL_API_BASE_URL", "").strip() or META_BASE_URL_DEFAULT


def meta_model_id() -> str:
    return os.environ.get("MODEL_API_MODEL_ID", "").strip() or DEFAULT_MODEL_ID


# Safety defaults (each investigation may tighten, never loosen, iteration caps)
ABSOLUTE_MAX_ITERATIONS = 3
DEFAULT_MAX_ITERATIONS = 3
ABSOLUTE_TOOL_TIMEOUT_SECONDS = 300.0
DEFAULT_TOOL_TIMEOUT_SECONDS = 60.0
ABSOLUTE_MAX_TOOL_CALLS = 12
# Structural caps that keep a runaway investigator from flooding the record.
MAX_HYPOTHESES_PER_INVESTIGATION = 12
MAX_REVISION_PLANS_PER_INVESTIGATION = 8

# Restricted working-directory roots for software tools. Relative paths from
# the API are resolved only inside these roots — an arbitrary path is refused.
ALLOWED_WORKSPACES_DEFAULT = "."   # repo root, resolved read/run-only inside


def allowed_workspace_roots() -> list[Path]:
    raw = os.environ.get("MODEL_AUTOPSY_ALLOWED_WORKSPACES", ALLOWED_WORKSPACES_DEFAULT)
    roots: list[Path] = []
    for part in raw.split(":"):
        part = part.strip()
        if not part:
            continue
        p = Path(part)
        if not p.is_absolute():
            p = (Path.cwd() / p)
        roots.append(p.resolve())
    return roots or [PROJECT_ROOT]


def resolve_restricted(rel_or_abs: str) -> Path:
    """Resolve a user/model-supplied path inside the allowed workspace roots."""
    candidate = Path(rel_or_abs)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    for root in allowed_workspace_roots():
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise PermissionError(f"path {rel_or_abs!r} is outside the allowed workspace roots")
