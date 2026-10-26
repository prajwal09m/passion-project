"""Shared schema, fingerprints, and lifecycle rules for the proposal layer.

This module is pure data + pure functions: no I/O, no imports from the
execution path (experiment_adapter / compiler / supervisor). Everything here
was specified in autonomous_agent/PROPOSAL_LAYER_DESIGN_PHASE1.md.

Truthfulness rule: ``generator_type`` can only ever be one of the reviewed
values. This phase emits ``deterministic_compositional`` only. There is no LLM
in this system.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA_VERSION = 1

# --- generator identity (truthful authorship) -------------------------------
GENERATOR_TYPE_DETERMINISTIC = "deterministic_compositional"
GENERATOR_TYPE_HUMAN = "human"
ALLOWED_GENERATOR_TYPES = frozenset({
    GENERATOR_TYPE_DETERMINISTIC,
    GENERATOR_TYPE_HUMAN,
    # "llm_assisted" is deliberately NOT permitted in this phase. Adding it
    # requires a reviewed change plus prompt/response hashing (Phase 1 G.4).
})
# v1.1.0 (2026-10-15 repair, owner directive "Campaign 4 — Repair Proposal
# Exhaustion and Resume Execution"): the generator performs an exact
# pre-creation BiasGovernor projection (class, projected falsification
# share, direction/class budgets, signature history) so a proposal the
# governor would refuse at validation is never created, and the candidate
# grid completes the reviewed s/m/l n_boot bucket vocabulary (adds the
# 2000 / bucket-l grid point inside the already-declared ParamSpec bounds).
# No gate, threshold, budget, stop rule, or approval policy changed.
GENERATOR_VERSION = "1.1.0"
# v1.1.0 (owner R-3 grant, 2026-10-12): the five previously dormant
# primitives are executable and carry frozen ladders, provisional margins,
# sample floors, and multiplicity-family bindings. No gate, threshold, or
# approval policy changed with this bump.
# v1.2.0 (2026-10-15 repair): default_class corrected for
# regime_split_analysis and target_horizon_robustness to the class the
# reviewed HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md table assigns
# them (falsification) - the implementation had shipped "exploration",
# making their declared falsification_capable=True unreachable. Pure class
# data: no param, bound, ladder, family, margin, or gate changed.
PRIMITIVE_LIBRARY_VERSION = "1.2.0"

# --- lifecycle state machine -------------------------------------------------
STATUS_PROPOSED = "PROPOSED"
STATUS_VALIDATING = "VALIDATING"
STATUS_ACCEPTED_FOR_EXECUTION = "ACCEPTED_FOR_EXECUTION"
STATUS_COMPILED = "COMPILED"
STATUS_REFUSED = "REFUSED"
STATUS_FAILED_VALIDATION = "FAILED_VALIDATION"
STATUS_FAILED_COMPILATION = "FAILED_COMPILATION"
STATUS_EXECUTED = "EXECUTED"
STATUS_FAILED_EXECUTION = "FAILED_EXECUTION"
STATUS_ADJUDICATED = "ADJUDICATED"
STATUS_PROMOTED = "PROMOTED"

ALL_STATUSES = frozenset({
    STATUS_PROPOSED, STATUS_VALIDATING, STATUS_ACCEPTED_FOR_EXECUTION,
    STATUS_COMPILED, STATUS_REFUSED, STATUS_FAILED_VALIDATION,
    STATUS_FAILED_COMPILATION, STATUS_EXECUTED, STATUS_FAILED_EXECUTION,
    STATUS_ADJUDICATED, STATUS_PROMOTED,
})

# No transition may bypass validation. Refusal/failure states are terminal.
LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    STATUS_PROPOSED: frozenset({STATUS_VALIDATING}),
    STATUS_VALIDATING: frozenset({
        STATUS_ACCEPTED_FOR_EXECUTION,   # all gates passed (+ approval)
        STATUS_REFUSED,                  # policy-class refusal (recorded)
        STATUS_FAILED_VALIDATION,        # evidence/schema/etc. gate failed
    }),
    STATUS_ACCEPTED_FOR_EXECUTION: frozenset({
        STATUS_COMPILED, STATUS_FAILED_COMPILATION}),
    STATUS_COMPILED: frozenset({STATUS_EXECUTED}),
    STATUS_EXECUTED: frozenset({STATUS_FAILED_EXECUTION, STATUS_ADJUDICATED}),
    STATUS_ADJUDICATED: frozenset({STATUS_PROMOTED}),
    STATUS_REFUSED: frozenset(),
    STATUS_FAILED_VALIDATION: frozenset(),
    STATUS_FAILED_COMPILATION: frozenset(),
    STATUS_FAILED_EXECUTION: frozenset(),
    STATUS_PROMOTED: frozenset(),
}

# Validation gates (Phase 1 C.4 order). Policy-class refusals map to REFUSED;
# evidence/mechanical gate failures map to FAILED_VALIDATION.
GATE_SCHEMA = "SCHEMA"
GATE_EVIDENCE = "EVIDENCE_RESOLVED"
GATE_FALSIFIABILITY = "FALSIFIABILITY"
GATE_SURFACE = "SURFACE"
GATE_HOLDOUT = "HOLDOUT_BLIND"
GATE_DUPLICATE = "DUPLICATE"
GATE_BUDGET = "BUDGET"
GATE_BIAS = "BIAS_QUOTA"
GATE_MECHANICAL = "MECHANICAL"
GATE_ORDER = (GATE_SCHEMA, GATE_EVIDENCE, GATE_FALSIFIABILITY, GATE_SURFACE,
              GATE_HOLDOUT, GATE_DUPLICATE, GATE_BUDGET, GATE_BIAS,
              GATE_MECHANICAL)

POLICY_REFUSAL_GATES = frozenset({GATE_DUPLICATE, GATE_BUDGET, GATE_BIAS})

# --- refusal / reason codes --------------------------------------------------
RC_SCHEMA = "SCHEMA"
RC_UNRECALLED_EVIDENCE = "UNRECALLED_EVIDENCE"
RC_NOT_FALSIFIABLE = "NOT_FALSIFIABLE"
RC_SURFACE_ESCAPE = "SURFACE_ESCAPE"
RC_UNSUPPORTED_PRIMITIVE = "UNSUPPORTED_PRIMITIVE"
RC_INVALID_PARAMETER = "INVALID_PARAMETER"
RC_HOLDOUT_REFERENCE = "HOLDOUT_REFERENCE"
RC_DUPLICATE = "DUPLICATE"
RC_NEAR_DUPLICATE = "NEAR_DUPLICATE"
RC_SIGNATURE_CAP = "SIGNATURE_CAP"
RC_BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
RC_CAMPAIGN_MISMATCH = "CAMPAIGN_MISMATCH"
RC_BIAS_QUOTA = "BIAS_QUOTA"
RC_SPEC_CONTRACT = "SPEC_CONTRACT"
RC_INVALID_PARENT = "INVALID_PARENT"
RC_PRIMITIVE_NOT_EXECUTABLE = "PRIMITIVE_NOT_EXECUTABLE"
RC_BOUNDARY = "BOUNDARY_VIOLATION"
RC_DISABLED = "DISABLED"
RC_GENERATOR_NOT_PERMITTED = "GENERATOR_NOT_PERMITTED"
RC_LEDGER_ERROR = "LEDGER_ERROR"

# --- proposal payload --------------------------------------------------------
REQUIRED_PAYLOAD_KEYS = frozenset({
    "schema_version", "generator_type", "generator_version",
    "primitive_library_version", "direction", "proposal_class",
    "research_question_id", "hypothesis", "rationale",
    "preregistered_expectation", "falsification_rule",
    "evidence_citations", "parent_version", "baseline_id",
    "design", "parameters", "proposal_fingerprint", "design_signature",
})
# Known payload keys; anything else fails SCHEMA (no free-form fields — this is
# how "no arbitrary code / paths / imports" is structurally enforced).
ALLOWED_PAYLOAD_KEYS = frozenset({
    "delta_from_prior",  # optional, only for justified near-duplicates
    "campaign_id",  # optional: identifies the campaign whose budget this
                    # proposal consumes (not part of scientific identity:
                    # excluded from the fingerprint so historical payloads
                    # are byte-stable across campaigns)
}) | REQUIRED_PAYLOAD_KEYS

PROPOSAL_CLASSES = frozenset({"confirmatory", "falsification", "replication",
                              "exploration"})
TRIGGERS = frozenset({"budget_slot", "quota_class", "novelty_score",
                      "human_request"})

# Metrics a falsification rule may name, with valid numeric bounds.
FALSIFICATION_METRICS: dict[str, tuple[float, float]] = {
    "pooled_roc_auc_delta": (-1.0, 1.0),
    "ci_lower": (-1.0, 1.0),
    "brier_delta": (-1.0, 1.0),
    "ece_delta": (-1.0, 1.0),
    "min_year_delta": (-1.0, 1.0),
}
COMPARATORS = frozenset({"<", "<=", ">", ">=", "=="})


# --- path / code heuristics (SURFACE + HOLDOUT gates) ------------------------
_HOLDOUT_MARKERS = frozenset({"prospective", "holdout"})
# A string that "looks like a path" may never appear inside a design/param.
_PATH_RE = re.compile(r"[\\/]|\.py$|\.csv$|\.json$|\.sh$|\.py\b")
# A string that "looks like code" may never appear inside a design/param.
_CODE_RE = re.compile(
    r"__|\bimport\b|\bexec\b|\beval\b|\bos\.|\bsubprocess\b|\bopen\s*\("
    r"|;|`|\$\{|%s\(|\breturn\b|\bdef\b|\bclass\b\s+\w+",
    re.IGNORECASE,
)


def contains_holdout_path(value: str) -> bool:
    """True when a string references the sealed holdout directory itself.

    Policy text such as 'holdout SEALED, uses=0' is intentionally NOT a hit:
    status/policy metadata is allowed evidence; holdout *data paths* are not.
    The marker set is component-based and always identical to ``is_denied``'s
    denylist (both 'prospective' and 'holdout' aliases), so a path that the
    evidence gate refuses can never survive in another payload field under a
    different spelling.
    """
    lowered = value.replace("\\", "/").lower()
    parts = "/" + lowered.strip("/") + "/"
    return any(f"/{marker}/" in parts for marker in _HOLDOUT_MARKERS)


def looks_like_path(value: str) -> bool:
    return bool(_PATH_RE.search(value))


def looks_like_code(value: str) -> bool:
    return bool(_CODE_RE.search(value))


# --- canonical hashing -------------------------------------------------------
def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def proposal_fingerprint(payload: Mapping[str, Any]) -> str:
    """Scientific identity of a proposal; volatile ledger fields excluded.

    The fingerprint/signature fields themselves are excluded (they are
defs of the identity, not inputs to it).
    """
    derived = {"proposal_fingerprint", "design_signature"}
    identity = {key: value for key, value in payload.items()
                if (key in REQUIRED_PAYLOAD_KEYS or key == "delta_from_prior")
                and key not in derived}
    return sha256_hex(canonical_json(identity))


# --- bucketed design signatures ---------------------------------------------
def bucket_n_boot(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        return f"invalid:{value!r}"
    if value <= 600:
        return "s"        # ~500
    if value <= 1200:
        return "m"        # ~1000
    return "l"


def bucket_bins(value: Any) -> str:
    return str(value)


_BUCKETED_KEYS = {"n_boot": bucket_n_boot, "calibration_bins": bucket_bins}


def _bucketed_params(params: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in sorted(params):
        value = params[key]
        if key in _BUCKETED_KEYS:
            out[key] = _BUCKETED_KEYS[key](value)
        else:
            out[key] = str(value)
    return out


def design_signature(*, primitive_ids: tuple[str, ...],
                     params: Mapping[str, Any],
                     folds: Any = (2023, 2024, 2025)) -> str:
    """Bucketed signature: robust to bootstrap/binning noise, exact on the
    design identity that actually determines what an experiment tests."""
    payload = {
        "primitives": sorted(primitive_ids),
        "params": _bucketed_params(params),
        "folds": list(folds),
    }
    return sha256_hex(canonical_json(payload))


# Campaign 1 recipe parameters map onto the equivalent primitive identity so
# that new proposals are checked against experiments that already ran.
_RECIPE_TO_PRIMITIVE = {
    "feature_arm_nested_ablation": "feature_arm_comparison",
    "model_class_matched_comparison": "model_class_comparison",
    "calibration_stability_check": "calibration_stability_check",
}


def signature_from_recipe_attempt(recipe_id: str,
                                  selected_parameters: Mapping[str, Any]) -> str | None:
    primitive_id = _RECIPE_TO_PRIMITIVE.get(str(recipe_id))
    if primitive_id is None:
        return None
    return design_signature(primitive_ids=(primitive_id,),
                            params=dict(selected_parameters))


# --- deterministic text similarity ------------------------------------------
def text_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


NEAR_DUPLICATE_TEXT_THRESHOLD = 0.90
