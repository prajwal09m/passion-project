"""Tool registry + argument validation + evidence recording.

Single source of truth: `PARAM_SCHEMA` declares every tool's real
parameters (types, requirements, bounds, string limits). Two consumers:

  1. `validate_arguments()` — server-side validation that runs immediately
     before execution, regardless of whether the caller is Meta, the UI,
     or a direct API request. Unknown keys, wrong types, out-of-range
     values and oversized strings are rejected before any fn runs.
  2. `meta_tool_schemas()` — Meta function-tool JSON Schemas generated
     from THE SAME definitions, so the advertised tool contract can never
     drift from what the backend actually enforces.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from sqlalchemy.orm import Session

from . import config
from .db import (Action, Investigation, record_event, next_seq, to_json_blob)

MAX_ARGUMENT_BYTES = 8 * 1024
MAX_STRING_VALUE_CHARS = 4_096

def _i(minimum: int | None = None, maximum: int | None = None,
       required: bool = False, description: str = "") -> dict:
    return {"type": "integer", "required": required, "minimum": minimum,
            "maximum": maximum, "description": description}


def _n(minimum: float | None = None, maximum: float | None = None,
       required: bool = False, description: str = "") -> dict:
    return {"type": "number", "required": required, "minimum": minimum,
            "maximum": maximum, "description": description}


def _b(required: bool = False, description: str = "") -> dict:
    return {"type": "boolean", "required": required, "description": description}


def _o(**props: dict) -> dict:
    return {"type": "object", "required": True, "properties": props,
            "description": "recorded tool-result payload (dict)."}



PARAM_SCHEMA: dict[str, dict[str, dict]] = {
    # --- software tools -----------------------------------------------------
    "git_status_and_diff": {
        "root": {"type": "string", "required": False, "max_length": 512,
                 "description": "Workspace root; resolved inside authorized roots only."},
        "max_diff_chars": _i(200, 20000, False,
                             "Maximum diff body characters retained (200..20000)."),
        "commit_range": {
            "type": "string", "required": False, "max_length": 160,
            "pattern": "^(?:[0-9a-fA-F]{6,64}|HEAD(?:~[0-9]{1,3})?)"
                       "(?:\\.\\.\\.?(?:[0-9a-fA-F]{6,64}|HEAD(?:~[0-9]{1,3})?))?$",
            "description": "Git revision range: a 6-64 hex SHA, HEAD, HEAD~N (N<=999), "
                           "or two of those joined by '..' or '...'. Options, symbolic "
                           "refs and whitespace are rejected before any git subprocess runs."},
    },
    "list_changed_files": {
        "root": {"type": "string", "required": False, "max_length": 512,
                 "description": "Workspace root; resolved inside authorized roots only."},
        "commit_range": {
            "type": "string", "required": False, "max_length": 160,
            "pattern": "^(?:[0-9a-fA-F]{6,64}|HEAD(?:~[0-9]{1,3})?)"
                       "(?:\\.\\.\\.?(?:[0-9a-fA-F]{6,64}|HEAD(?:~[0-9]{1,3})?))?$",
            "description": "Git revision range (same grammar as git_status_and_diff)."},
    },
    "read_changed_file_head": {
        "root": {"type": "string", "required": False, "max_length": 512,
                 "description": "Workspace root; resolved inside authorized roots only."},
        "file_path": {"type": "string", "required": True, "max_length": 512,
                      "description": "Relative file path inside the workspace; traversal "
                                     "outside authorized roots is refused."},
        "lines": _i(10, 400, False, "Head lines to read (10..400; default 120)."),
    },
    "run_tests": {
        "root": {"type": "string", "required": False, "max_length": 512,
                 "description": "Workspace root; the runner is a fixed pytest-family command."},
        "test_path": {"type": "string", "required": False, "max_length": 512,
                      "description": "Subdirectory/target inside the workspace; resolved against restricted roots."},
        "timeout_seconds": _n(1.0, float(config.ABSOLUTE_TOOL_TIMEOUT_SECONDS), False,
                              "Test timeout (1..%s s; clamped to the absolute cap)." % config.ABSOLUTE_TOOL_TIMEOUT_SECONDS),
    },
    "compare_test_results": {
        "before": _o(exit_code=_i(0, 99, True, "pytest exit code before the change."),
                     passed=_b(True, "True when the pre-change run passed.")),
        "after": _o(exit_code=_i(0, 99, True, "pytest exit code after the change."),
                    passed=_b(True, "True when the post-change run passed.")),
    },
    "check_apply_approval": {
        "requested_by_meta": _b(False, "True when the model requested an apply."),
        "owner_approved": _b(False, "Explicit human approval flag; Meta can never set it."),
    },
    "propose_hypothesis": {
        "text": {"type": "string", "required": True, "min_length": 10, "max_length": 800,
                 "description": "Falsifiable hypothesis statement (10..800 chars)."},
        "rationale": {"type": "string", "required": False, "max_length": 800,
                      "description": "Why this explanation is plausible, citing evidence seen so far."},
        "predicted_observation": {"type": "string", "required": False, "max_length": 400,
                                  "description": "What a diagnostic would have to show for this to hold (or fail)."},
        "confidence_note": {"type": "string", "required": False, "max_length": 400,
                            "description": "What the model's own uncalibrated confidence means (never a guarantee)."},
    },
    "propose_revision_instructions": {
        "root": {"type": "string", "required": False, "max_length": 512,
                 "description": "Workspace the instructions apply to."},
        "findings": {"type": "array", "item_type": "string", "required": True,
                     "min_items": 1, "max_items": 20, "max_length": 400,
                     "description": "Findings to address, one per string (each <= 400 chars)."},
        "instructions": {"type": "array", "item_type": "string", "required": True,
                         "min_items": 1, "max_items": 25, "max_length": 400,
                         "description": "Concrete revision instructions for a human reviewer; nothing is applied automatically."},
        "review_tests": {"type": "string", "required": False, "max_length": 400,
                         "description": "Which tests the reviewer should run before and after applying."},
    },
    # --- ML tools -----------------------------------------------------------
    "artifact_summary": {
        "predictions_path": {"type": "string", "required": False, "max_length": 512,
                             "description": "Project-root-relative CSV override; omit to use the configured case study."},
        "labels": {"type": "string", "required": False, "max_length": 80,
                   "description": "Label column name (default 'label')."},
    },
    "dataset_validation": {
        "predictions_path": {"type": "string", "required": True, "max_length": 512,
                             "description": "Project-root-relative CSV to validate for arbitrary projects."},
        "score_columns": {"type": "array", "item_type": "string", "required": False,
                          "min_items": 1, "max_items": 32, "max_length": 120,
                          "description": "Score columns expected for AUC tools; reported missing if absent."},
        "label_column": {"type": "string", "required": False, "max_length": 80,
                         "description": "Label column name (default 'label'); must exist with 0/1 values."},
        "date_column": {"type": "string", "required": False, "max_length": 80,
                        "description": "Optional chronology column; fold/date coverage is reported."},
        "fold_column": {"type": "string", "required": False, "max_length": 80,
                        "description": "Optional fold column name (default 'fold')."},
    },
    "classification_metrics": {
        "predictions_path": {"type": "string", "required": False, "max_length": 512,
                             "description": "Project-root-relative CSV override."},
        "labels": {"type": "string", "required": False, "max_length": 80,
                   "description": "Label column name (default 'label')."},
        "score_column": {"type": "string", "required": False, "max_length": 80,
                         "description": "Score column to evaluate (default 'LightGBM_C' for the case study)."},
        "threshold": _n(0.0, 1.0, False, "Operating threshold in [0,1] (default 0.5)."),
        "split_by": {"type": "string", "required": False, "max_length": 80,
                     "description": "Optional grouping column (e.g. 'fold') for per-group AUC."},
    },
    "time_split_validation": {
        "predictions_path": {"type": "string", "required": False, "max_length": 512,
                             "description": "Project-root-relative CSV override."},
        "labels": {"type": "string", "required": False, "max_length": 80,
                   "description": "Label column name (default 'label')."},
        "date_column": {"type": "string", "required": False, "max_length": 80,
                        "description": "Date column for fold-span chronology (auto-detected if present)."},
    },
    "feature_target_suspiciousness": {
        "feature_csv": {"type": "string", "required": True, "max_length": 512,
                        "description": "Project-root-relative feature CSV to screen."},
        "label_csv": {"type": "string", "required": False, "max_length": 512,
                      "description": "Optional label CSV; its 'label' column is merged."},
        "n_top": _i(1, 50, False, "Number of strongest |point-biserial| rows to report (1..50)."),
    },
    "calibration_and_error_analysis": {
        "predictions_path": {"type": "string", "required": False, "max_length": 512,
                             "description": "Project-root-relative CSV override."},
        "labels": {"type": "string", "required": False, "max_length": 80,
                   "description": "Label column name (default 'label')."},
        "score_column": {"type": "string", "required": False, "max_length": 80,
                         "description": "Score column (default 'LightGBM_C' for the case study)."},
        "bins": _i(2, 20, False, "Calibration bins (2..20; default 10)."),
    },
    "grouped_auc_comparison": {
        "predictions_path": {"type": "string", "required": False, "max_length": 512,
                             "description": "Project-root-relative CSV override."},
        "labels": {"type": "string", "required": False, "max_length": 80,
                   "description": "Label column name (default 'label')."},
        "score_a": {"type": "string", "required": False, "max_length": 80,
                    "description": "Baseline score column."},
        "score_b": {"type": "string", "required": False, "max_length": 80,
                    "description": "Challenger score column (delta = B - A)."},
        "n_boot": _i(1, 5000, False, "Bootstrap replicates (1..5000; default 2000)."),
    },
}


def _engine_propose_hypothesis(session: Session, inv: Investigation, **kwargs):
    """Registry tool (both modes): formally register a structured, falsifiable
    hypothesis. Origin 'meta'; confidence is the model's uncalibrated note."""
    from . import engine  # deferred: engine imports tools_registry at startup
    return engine.propose_hypothesis(session, inv, **kwargs)


def _engine_propose_revision(session: Session, inv: Investigation, **kwargs):
    """Registry tool (software mode): record a proposed-revision instruction
    bundle for human review; never applied automatically."""
    from . import engine
    return engine.propose_revision_instructions(session, inv, **kwargs)


def software_tools() -> dict[str, Callable]:
    from . import software_tools as sw
    return {"git_status_and_diff": sw.git_status_and_diff,
            "list_changed_files": sw.list_changed_files,
            "read_changed_file_head": sw.read_changed_file_head,
            "run_tests": sw.run_tests,
            "compare_test_results": sw.compare_test_results,
            "check_apply_approval": sw.check_apply_approval,
            "propose_hypothesis": _engine_propose_hypothesis,
            "propose_revision_instructions": _engine_propose_revision}


def ml_tools() -> dict[str, Callable]:
    from . import ml_tools as ml
    return {"artifact_summary": ml.artifact_summary,
            "dataset_validation": ml.dataset_validation,
            "classification_metrics": ml.classification_metrics,
            "time_split_validation": ml.time_split_validation,
            "feature_target_suspiciousness": ml.feature_target_suspiciousness,
            "calibration_and_error_analysis": ml.calibration_and_error_analysis,
            "grouped_auc_comparison": ml.grouped_auc_comparison,
            "propose_hypothesis": _engine_propose_hypothesis}


def _first_docline(fn: Callable) -> str:
    doc = (fn.__doc__ or "").strip()
    return doc.splitlines()[0] if doc else fn.__name__


TOOL_SPECS: dict[str, dict] = {}
for _name, _fn in software_tools().items():
    TOOL_SPECS[_name] = {"fn": _fn, "mode": "software",
                         "description": _first_docline(_fn)}
for _name, _fn in ml_tools().items():
    # 'propose_hypothesis' registered for both modes: the first (software)
    # registration wins for the function, mode fixed below.
    TOOL_SPECS.setdefault(_name, {"fn": _fn, "mode": "ml",
                                  "description": _first_docline(_fn)})

# Cross-mode tools: registered under both allowlists but defined once.
TOOL_SPECS["propose_hypothesis"]["mode"] = "both"
_TAKES_SESSION = {"propose_hypothesis", "propose_revision_instructions"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_arguments(tool_name: str, args: dict) -> dict:
    """Validate `args` against PARAM_SCHEMA; return a normalized dict.

    Raises ValueError with a structured, honest message. Never raises with
    a stack trace leaking internals; never silently coerces unexpected
    types. Called by every entry point (engine, API, Meta loop).
    """
    spec = TOOL_SPECS.get(tool_name)
    if spec is None:
        raise LookupError(f"unknown or not-allowed tool {tool_name!r}")
    schema = PARAM_SCHEMA[tool_name]

    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ValueError(f"{tool_name}: arguments must be an object, "
                         f"got {type(args).__name__}")
    try:
        payload = json.dumps(args or {}, default=str)
    except (TypeError, ValueError):
        payload = "unserializable"
    if len(payload) > MAX_ARGUMENT_BYTES:
        raise ValueError(f"{tool_name}: arguments total {len(payload)} bytes, "
                         f"above the {MAX_ARGUMENT_BYTES}-byte cap")

    unknown = sorted(k for k in args if k not in schema)
    if unknown:
        raise ValueError(f"{tool_name}: unknown parameter(s) {unknown}; "
                         f"accepted parameters are {sorted(schema)}")

    missing = [k for k, decl in schema.items() if decl.get("required")
               and (k not in args or args[k] is None)]
    if missing:
        raise ValueError(f"{tool_name}: missing required parameter(s) {missing}")

    normalized: dict = {}
    for key, value in args.items():
        decl = schema[key]
        normalized[key] = _validate_value(tool_name, key, value, decl)

    # array / item validation happens inside _validate_value for arrays.
    return normalized


def _validate_value(tool_name: str, key: str, value, decl: dict):
    expected = decl["type"]
    if value is None:
        if decl.get("required"):
            raise ValueError(f"{tool_name}.{key}: required value is null")
        return None

    if expected == "string":
        if not isinstance(value, str):
            raise ValueError(f"{tool_name}.{key}: expected a string, "
                             f"got {type(value).__name__}")
        limit = decl.get("max_length", MAX_STRING_VALUE_CHARS)
        if len(value) > limit:
            raise ValueError(f"{tool_name}.{key}: string of {len(value)} chars "
                             f"exceeds the {limit}-char limit")
        if decl.get("pattern") and not re.fullmatch(decl["pattern"], value.strip()):
            raise ValueError(f"{tool_name}.{key}: value {value[:60]!r} does not "
                             "match the required grammar")
        return value.strip()

    if expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{tool_name}.{key}: expected an integer, "
                             f"got {type(value).__name__}")
        if decl.get("minimum") is not None and value < decl["minimum"]:
            raise ValueError(f"{tool_name}.{key}: {value} below minimum "
                             f"{decl['minimum']}")
        if decl.get("maximum") is not None and value > decl["maximum"]:
            raise ValueError(f"{tool_name}.{key}: {value} above maximum "
                             f"{decl['maximum']}")
        return value

    if expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{tool_name}.{key}: expected a number, "
                             f"got {type(value).__name__}")
        if decl.get("minimum") is not None and value < decl["minimum"]:
            raise ValueError(f"{tool_name}.{key}: {value} below minimum "
                             f"{decl['minimum']}")
        if decl.get("maximum") is not None and value > decl["maximum"]:
            raise ValueError(f"{tool_name}.{key}: {value} above maximum "
                             f"{decl['maximum']}")
        return float(value)

    if expected == "boolean":
        if not isinstance(value, bool):
            raise ValueError(f"{tool_name}.{key}: expected a boolean, "
                             f"got {type(value).__name__}")
        return value

    if expected == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{tool_name}.{key}: expected an object, "
                             f"got {type(value).__name__}")
        if not value:
            raise ValueError(f"{tool_name}.{key}: object must not be empty")
        for sub, sub_decl in (decl.get("properties") or {}).items():
            sv = value.get(sub)
            if sub_decl.get("required") and sv is None:
                raise ValueError(f"{tool_name}.{key}.{sub}: required inside object")
            if sv is not None:
                _validate_value(tool_name, f"{key}.{sub}", sv, sub_decl)
        return value

    if expected == "array":
        if not isinstance(value, list):
            raise ValueError(f"{tool_name}.{key}: expected an array, "
                             f"got {type(value).__name__}")
        if decl.get("min_items") is not None and len(value) < decl["min_items"]:
            raise ValueError(f"{tool_name}.{key}: needs at least "
                             f"{decl['min_items']} item(s)")
        if decl.get("max_items") is not None and len(value) > decl["max_items"]:
            raise ValueError(f"{tool_name}.{key}: exceeds {decl['max_items']} items")
        item_decl = {"type": decl.get("item_type", "string"),
                     "required": True, "max_length": decl.get("max_length")}
        out = []
        for idx, item in enumerate(value):
            out.append(_validate_value(tool_name, f"{key}[{idx}]", item, item_decl))
        return out

    raise ValueError(f"{tool_name}.{key}: unsupported declared type {expected!r}")


# ---------------------------------------------------------------------------
# Recording + execution
# ---------------------------------------------------------------------------

def record_tool_call(session: Session, inv: Investigation, tool_name: str,
                     arguments: dict, status: str, result: dict | None,
                     error: str | None) -> Action:
    seq = next_seq(session, inv.id)
    action = Action(investigation_id=inv.id, seq=seq, kind="tool_call",
                    tool_name=tool_name, arguments=dict(arguments or {}),
                    status=status, result=result, error=error,
                    iteration=inv.iteration_count)
    session.add(action)
    record_event(session, inv.id, "tool_request",
                 f"Requested {tool_name}",
                 payload={"tool": tool_name,
                          "arguments": to_json_blob(arguments or {}),
                          "action_seq": seq})
    session.flush()
    return action


def record_result_event(session: Session, inv: Investigation, tool: str,
                        status: str, result: dict | None, error: str | None,
                        action_seq: int) -> None:
    record_event(session, inv.id, "tool_result",
                 f"tool:{tool} ({status})",
                 detail=(error or json.dumps(
                     to_json_blob(result or {}), default=str)[:400]),
                 payload={"tool": tool, "status": status,
                          "result": to_json_blob(result or {}),
                          "action_seq": action_seq})


def _mode_allows(tool_name: str, inv_mode: str) -> bool:
    spec = TOOL_SPECS.get(tool_name)
    return bool(spec) and spec["mode"] in (inv_mode, "both")


def execute(session: Session, inv: Investigation, tool_name: str,
            arguments: dict) -> dict:
    """Validation, execution, recording. Caller commits."""
    if tool_name not in TOOL_SPECS or not _mode_allows(tool_name, inv.mode):
        raise LookupError(f"unknown or not-allowed tool {tool_name!r} "
                          f"for mode {inv.mode!r}")
    normalized = validate_arguments(tool_name, arguments)
    fn = TOOL_SPECS[tool_name]["fn"]
    if tool_name in _TAKES_SESSION:
        result = fn(session, inv, **normalized)
    else:
        result = fn(**normalized)
    result_json = to_json_blob(result) or {"ok": False}
    action = record_tool_call(session, inv, tool_name, normalized,
                              "ran", result_json, None)
    record_result_event(session, inv, tool_name, "ran", result_json, None,
                        action.seq)
    return {"ok": True, "result": result_json, "action_id": action.id}


def record_failed_call(session: Session, inv: Investigation, tool_name: str,
                       arguments: dict, error: str) -> tuple[Action, dict]:
    record_tool_call(session, inv, tool_name, arguments, "failed", None, error)
    action = (session.query(Action)
              .filter(Action.investigation_id == inv.id,
                      Action.tool_name == tool_name,
                      Action.status == "failed")
              .order_by(Action.seq.desc()).first())
    record_result_event(session, inv, tool_name, "failed", None, str(error),
                        action.seq if action else 0)
    return action, {"ok": False, "error": str(error)[:400],
                    "action_id": action.id if action else None}


# ---------------------------------------------------------------------------
# Generated Meta schemas
# ---------------------------------------------------------------------------

_JSON_TYPE = {"string": "string", "integer": "integer", "number": "number",
              "boolean": "boolean", "array": "array", "object": "object"}


def meta_tool_schemas(mode: str) -> list[dict]:
    """Flat function-tool definitions derived from PARAM_SCHEMA.

    `additionalProperties: false` + every parameter described with real
    bounds — the model can only call tools with the exact parameters the
    backend will validate again anyway.
    """
    schemas: list[dict] = []
    for name, spec in TOOL_SPECS.items():
        if mode != spec["mode"] and spec["mode"] != "both":
            continue
        decls = PARAM_SCHEMA[name]
        props: dict = {}
        required = []
        for pname, decl in decls.items():
            props[pname] = _decl_to_json_schema(decl)
            if decl.get("required"):
                required.append(pname)
        schemas.append({"type": "function", "name": name,
                        "description": spec["description"],
                        "parameters": {"type": "object", "properties": props,
                                       "required": required,
                                       "additionalProperties": False}})
    return schemas


def _decl_to_json_schema(decl: dict) -> dict:
    js: dict = {"description": decl.get("description", "")}
    t = decl["type"]
    js["type"] = _JSON_TYPE[t]
    if t == "string":
        if "min_length" in decl:
            js["minLength"] = decl["min_length"]
        if "max_length" in decl:
            js["maxLength"] = decl["max_length"]
        if decl.get("pattern"):
            js["pattern"] = decl["pattern"]
    if t in ("integer", "number"):
        if decl.get("minimum") is not None:
            js["minimum"] = decl["minimum"]
        if decl.get("maximum") is not None:
            js["maximum"] = decl["maximum"]
    if t == "boolean":
        pass  # json schema has no extra knobs here
    if t == "array":
        item = decl.get("item_type", "string")
        item_js: dict = {"type": _JSON_TYPE[item]}
        if "max_length" in decl:
            item_js["maxLength"] = decl["max_length"]
        js["items"] = item_js
        if "min_items" in decl:
            js["minItems"] = decl["min_items"]
        if "max_items" in decl:
            js["maxItems"] = decl["max_items"]
    if t == "object":
        policies = {}
        for sub, sub_decl in (decl.get("properties") or {}).items():
            policies[sub] = _decl_to_json_schema(sub_decl)
        js["properties"] = policies
        sub_required = [k for k, d in (decl.get("properties") or {}).items()
                        if d.get("required")]
        js["required"] = sub_required
        js["additionalProperties"] = False
    return js


def parameter_documentation(mode: str | None = None) -> dict:
    """Human-readable contract (UI + demo). Never a separate copy."""
    out: dict = {}
    for name, spec in TOOL_SPECS.items():
        if mode and spec["mode"] != mode:
            continue
        out[name] = {"mode": spec["mode"], "description": spec["description"],
                     "parameters": PARAM_SCHEMA[name]}
    return out
