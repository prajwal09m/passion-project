"""Proposal -> ExperimentSpec compiler: the single crossing point (component 7).

This module is the ONLY sanctioned transition from proposal generation into
the execution representation. It builds an in-memory ``ExperimentSpec`` that
is subject to ALL existing validation and execution gates:

  * harness config contract (``validate_experiment_config``)
  * ``ExperimentSpec.validate()`` mechanical contract
  * ``SpecRegistry.check`` duplicate detection (the adapter re-checks at run)
  * everything downstream (adapter isolation, six gates, promotion) stays on
    the existing, unchanged execution path.

``compile_proposal`` refuses any proposal whose lifecycle state is not
ACCEPTED_FOR_EXECUTION — this is the hard boundary (Phase 1 K). Nothing in
this module writes files, spawns processes, or opens the holdout.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from autonomous_agent.proposal_layer import schema
from autonomous_agent.proposal_layer.primitives import get as get_primitive

from autonomous_agent.experiment_adapter import ExperimentSpec
from autonomous_agent import hardening
from autonomous_agent.recipe_harness import validate_experiment_config
from autonomous_agent.spec_recipes import (EXPERIMENT_DIR, EXPERIMENT_ENTRYPOINT,
                                           INIT_CONTENT)


class CompileError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code


class BoundaryViolation(Exception):
    """Attempted to compile a proposal that is not ACCEPTED_FOR_EXECUTION."""


def resolve_parent_version(root: Path | str) -> str:
    """Fail-closed parent resolution (Campaign 1 INVALID_PARENT rule)."""
    from autonomous_agent.core import VersionManager, read_json
    path = Path(root) / "CHAMPION.json"
    champion = read_json(path, None)
    if not isinstance(champion, dict):
        raise CompileError(schema.RC_INVALID_PARENT,
                           "CHAMPION.json missing, unreadable, or malformed")
    version = champion.get("version")
    if not isinstance(version, str) or VersionManager.VERSION_PATTERN.fullmatch(version) is None:
        raise CompileError(schema.RC_INVALID_PARENT,
                           "CHAMPION.json has no valid version field")
    return version


def _first_primitive(payload: Mapping[str, Any]):
    entries = (payload.get("design") or {}).get("primitives") or []
    if not entries:
        raise CompileError(schema.RC_UNSUPPORTED_PRIMITIVE,
                           "design has no primitives")
    entry = entries[0]
    primitive = get_primitive(str(entry.get("primitive_id")))
    if primitive is None:
        raise CompileError(schema.RC_UNSUPPORTED_PRIMITIVE,
                           f"unknown primitive {entry.get('primitive_id')!r}")
    return primitive, dict(entry.get("params") or {})


def _acceptance_criteria(primitive, payload: Mapping[str, Any],
                         params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    criteria: dict[str, Any] = {
        "primary_metric_min_delta": 0.0,
        "ci_lower_min": -0.01,
        "min_folds": 3,
        "note": (primitive.config_note
                 or "Candidate must not degrade pooled out-of-fold AUC "
                    "(delta >= 0, CI lower >= -0.01) on the frozen purged folds."),
    }
    if primitive.primitive_id == "calibration_stability_check":
        criteria["max_brier_degradation"] = 0.005
        criteria["max_ece_degradation"] = 0.02
    # Stage 4 (2026-10-05): reviewed per-parameter criteria profiles. The
    # mapping is static library data keyed by the proposal's own bounded enum
    # parameter; the rendered keys and bounds are re-checked against the
    # harness's closed criteria schema (validate_experiment_config) below, so
    # a bad profile can only fail closed as a CompileError.
    for key, profiles in (getattr(primitive, "extra", None) or {}).get(
            "criteria_by_param", {}).items():
        if params is None or key not in params:
            continue
        patch = profiles.get(str(params[key]))
        if isinstance(patch, dict):
            criteria.update(patch)
    return criteria


def _render_config(payload: Mapping[str, Any], primitive, params) -> dict[str, Any]:
    """Structural unpack, identical shapes to the reviewed recipe renderer —
    no free-form content can reach the harness config."""
    if "arm_pair" in params:
        value = str(params["arm_pair"])
        if "->" not in value:
            raise CompileError(schema.RC_INVALID_PARAMETER,
                               f"arm_pair {value!r} is not 'X->Y'")
        arm_a, arm_b = value.split("->", 1)
        estimator_a = estimator_b = str(params.get("estimator", "LightGBM"))
    elif "arm" in params:
        arm_a = arm_b = str(params["arm"])
        estimator_a, estimator_b = "LogisticRegression", "LightGBM"
    else:
        raise CompileError(schema.RC_INVALID_PARAMETER,
                           "primitive declares no arm/arm_pair parameter")

    config = {
        "schema_version": 1,
        "generator": "deterministic_compositional",
        "recipe_id": "proposal_layer",
        "recipe_version": "1.0.0",
        "hypothesis_id": str(payload.get("research_question_id", "")),
        "hypothesis_text": str(payload.get("hypothesis", ""))[:400],
        "baseline_id": str(payload.get("baseline_id") or ""),
        "arm_a": arm_a,
        "arm_b": arm_b,
        "estimator_a": estimator_a,
        "estimator_b": estimator_b,
        # Reviewed seed set: a primitive may declare an independent
        # predeclared seed set in its static library data (Stage 4);
        # nothing else can change the seeds.
        "seeds": [int(seed) for seed in
                  ((getattr(primitive, "extra", None) or {}).get("seeds")
                   or [42, 43, 44])],
        "n_boot": int(params.get("n_boot", 500)),
        "calibration_bins": int(params.get("calibration_bins", 10)),
        "folds": [2023, 2024, 2025],
        "evaluation_criteria": _acceptance_criteria(primitive, payload, params),
    }
    problems = validate_experiment_config(config)
    if problems:
        raise CompileError(schema.RC_SPEC_CONTRACT,
                           "rendered config failed harness contract: "
                           + "; ".join(problems))
    return config


def preview_spec(payload: Mapping[str, Any], *, root: Path | str) -> ExperimentSpec:
    """Build the ExperimentSpec WITHOUT lifecycle checks (validation gate 9
    uses this; only ``compile_proposal`` crosses the boundary)."""
    root = Path(root)
    primitive, params = _first_primitive(payload)
    if not primitive.executable:
        raise CompileError(
            schema.RC_PRIMITIVE_NOT_EXECUTABLE,
            f"primitive {primitive.primitive_id!r} requires harness "
            f">= {primitive.harness_min_version}; current harness does not "
            "support it")
    parent_version = resolve_parent_version(root)
    config = _render_config(payload, primitive, params)

    fingerprint = str(payload.get("proposal_fingerprint", ""))
    experiment_id = f"exp-proposal-{fingerprint[:12]}"
    allowed_files = (
        f"{EXPERIMENT_DIR}/__init__.py",
        f"{EXPERIMENT_DIR}/run_experiment.py",
        f"{EXPERIMENT_DIR}/experiment_config.json",
    )
    spec = ExperimentSpec(
        experiment_id=experiment_id,
        parent_version=parent_version,
        hypothesis=str(payload.get("hypothesis", "")),
        proposed_change={
            "summary": (f"Proposal layer ({primitive.primitive_id}): "
                        f"{primitive.purpose}"),
            "files": [
                {"path": allowed_files[0], "content": INIT_CONTENT},
                {"path": allowed_files[1], "content": EXPERIMENT_ENTRYPOINT},
                {"path": allowed_files[2],
                 "content": json.dumps(config, indent=2, sort_keys=True) + "\n"},
            ],
        },
        files_allowed_to_change=allowed_files,
        evaluation_protocol={"acceptance_criteria":
                             _acceptance_criteria(primitive, payload, params)},
        random_seed=42,
        resource_limits={},
        timeout=1800.0,
        allow_repeat=False,
        baseline_id=str(payload.get("baseline_id") or "") or None,
        provenance={
            "generator_type": str(payload.get("generator_type", "")),
            "generator_version": str(payload.get("generator_version", "")),
            "primitive_library_version":
                str(payload.get("primitive_library_version", "")),
            "provider": "evidence_grounded_proposal_layer",
            "proposal_fingerprint": fingerprint,
            "design_signature": str(payload.get("design_signature", "")),
            "hypothesis_id": str(payload.get("research_question_id", "")),
            "selected_parameters": dict(payload.get("parameters") or {}),
            "falsification_rule": dict(payload.get("falsification_rule") or {}),
            "llm_involved": False,
        },
    )
    return spec


def compile_proposal(payload: Mapping[str, Any], *, root: Path | str,
                     status: str | None) -> tuple[ExperimentSpec, str]:
    """The single controlled transition: validated proposal -> spec.

    Raises BoundaryViolation unless the lifecycle state is exactly
    ACCEPTED_FOR_EXECUTION. Returns (spec, spec_sha256). Writes nothing.
    """
    if status != schema.STATUS_ACCEPTED_FOR_EXECUTION:
        raise BoundaryViolation(
            f"[{schema.RC_BOUNDARY}] proposal status {status!r} may not be "
            f"compiled; only {schema.STATUS_ACCEPTED_FOR_EXECUTION} may cross "
            "into the execution representation")
    spec = preview_spec(payload, root=root)
    spec.validate()   # existing mechanical contract, re-asserted here
    registry = hardening.SpecRegistry(Path(root) / "autonomous_agent" / "state")
    allowed, reason = registry.check(spec.to_dict())
    if not allowed:
        raise CompileError(schema.RC_DUPLICATE, reason)
    return spec, hardening.spec_fingerprint(spec.to_dict())
