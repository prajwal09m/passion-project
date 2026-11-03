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


def load_env_file(env_file: Path | None = None) -> bool:
    """Load a simple KEY=VALUE .env file without echoing any values.

    Same secure mechanism the Meta benchmark campaigns use
    (benchmarks/meta_paired_continuation_benchmark.py): UTF-8 BOM,
    optional `export ` prefixes, matching quotes; an empty process
    value never shadows a file value; a non-empty process value always
    wins. Returns True when the file was read (even if it set nothing).
    """
    target = Path(env_file) if env_file else (MODEL_AUTOPSY_DIR / ".env")
    try:
        text = target.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1].strip()
        if not key:
            continue
        if key == "MODEL_API_KEY":
            if not os.environ.get(key, "").strip():
                os.environ[key] = value
        else:
            os.environ.setdefault(key, value)
    return True


def bootstrap_env() -> None:
    """Explicit .env initialization for CLI entry points.

    Loads model_autopsy/.env only when MODEL_API_KEY is missing from
    the process environment. Call BEFORE any preflight/availability
    check; never prints values.

    No-op under test isolation (MODEL_AUTOPSY_TESTING=1): suites control
    the environment explicitly, and a developer's local .env must never
    leak into tests (it would flip no-key expectations and risk live
    traffic from test doubles)."""
    if os.environ.get("MODEL_AUTOPSY_TESTING", "").strip() == "1":
        return
    if not os.environ.get("MODEL_API_KEY", "").strip():
        load_env_file()


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


# Versioned evaluation rubric selection (V2/V3 integration).
# Env name is MODEL_AUTOPSY_EVAL_VERSION with values strictly "v2"|"v3".
# This is the SCORING RUBRIC version, distinct from the offline runner's
# framework stamp (EVAL_VERSION "m4-v1" in eval/__init__.py). Persisted
# as inv.config["eval_rubric_version"] and scorecard["rubric_version"].
EVAL_RUBRIC_VERSIONS = ("v2", "v3")
EVAL_RUBRIC_DEFAULT = "v2"  # existing installs keep v2 unless explicit


def eval_rubric_default() -> str:
    return (os.environ.get("MODEL_AUTOPSY_EVAL_VERSION", "")
            .strip().lower() or EVAL_RUBRIC_DEFAULT)


def resolve_eval_rubric(value: str | None) -> str:
    """Validate a rubric version; invalid values fail fast and loud."""
    v = (value or "").strip().lower() or eval_rubric_default()
    if v not in EVAL_RUBRIC_VERSIONS:
        raise ValueError(
            f"invalid eval rubric version {value!r}: expected one of "
            f"{list(EVAL_RUBRIC_VERSIONS)}")
    return v


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
