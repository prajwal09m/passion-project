"""ProposalValidator: the pre-execution gate chain (Phase 1 component 4).

Gates run in the Phase 1 C.4 order and fail closed. Every result — pass or
fail — is returned so the caller can record it in the ledger; refusals are
preserved as carefully as acceptances.

Gate -> lifecycle mapping (documented in PROPOSAL_SPEC.md):
  * policy-class gates (DUPLICATE / BUDGET / BIAS_QUOTA) -> status REFUSED
  * evidence/mechanical gates -> status FAILED_VALIDATION
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from autonomous_agent.proposal_layer import evidence_view, schema
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor
from autonomous_agent.proposal_layer import primitives as primitive_lib


@dataclass
class GateResult:
    gate: str
    passed: bool
    reason_code: str | None = None
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"gate": self.gate, "passed": self.passed,
                "reason_code": self.reason_code, "detail": self.detail}


@dataclass
class ValidationReport:
    passed: bool
    gates: list[GateResult] = field(default_factory=list)
    failed_gate: str | None = None
    reason_code: str | None = None
    status_target: str | None = None   # REFUSED | FAILED_VALIDATION | None

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed,
                "gates": [gate.to_dict() for gate in self.gates],
                "failed_gate": self.failed_gate,
                "reason_code": self.reason_code,
                "status_target": self.status_target}


def _fail(report: ValidationReport, gate: str, reason_code: str,
          detail: str) -> None:
    report.gates.append(GateResult(gate=gate, passed=False,
                                   reason_code=reason_code, detail=detail))
    report.passed = False
    report.failed_gate = gate
    report.reason_code = reason_code
    report.status_target = ("REFUSED" if gate in schema.POLICY_REFUSAL_GATES
                            else "FAILED_VALIDATION")


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def _gate_schema(payload: Mapping[str, Any], report: ValidationReport) -> bool:
    if not isinstance(payload, dict):
        _fail(report, schema.GATE_SCHEMA, schema.RC_SCHEMA, "payload not a mapping")
        return False
    missing = sorted(schema.REQUIRED_PAYLOAD_KEYS - set(payload))
    if missing:
        _fail(report, schema.GATE_SCHEMA, schema.RC_SCHEMA,
              f"missing required keys: {missing}")
        return False
    unknown = sorted(set(payload) - schema.ALLOWED_PAYLOAD_KEYS)
    if unknown:
        _fail(report, schema.GATE_SCHEMA, schema.RC_SCHEMA,
              f"unknown keys are prohibited: {unknown}")
        return False
    if payload.get("generator_type") not in schema.ALLOWED_GENERATOR_TYPES:
        _fail(report, schema.GATE_SCHEMA, schema.RC_GENERATOR_NOT_PERMITTED,
              f"generator_type {payload.get('generator_type')!r} not permitted "
              "in this phase (deterministic/human only; no LLM)")
        return False
    if payload.get("schema_version") != schema.SCHEMA_VERSION:
        _fail(report, schema.GATE_SCHEMA, schema.RC_SCHEMA,
              f"schema_version must be {schema.SCHEMA_VERSION}")
        return False
    if payload.get("proposal_class") not in schema.PROPOSAL_CLASSES:
        _fail(report, schema.GATE_SCHEMA, schema.RC_SCHEMA,
              f"unknown proposal_class {payload.get('proposal_class')!r}")
        return False
    if payload.get("rationale", {}).get("trigger") not in schema.TRIGGERS:
        _fail(report, schema.GATE_SCHEMA, schema.RC_SCHEMA,
              "rationale.trigger outside the reviewed set")
        return False
    if not isinstance(payload.get("hypothesis"), str) \
            or not payload["hypothesis"].strip():
        _fail(report, schema.GATE_SCHEMA, schema.RC_SCHEMA, "hypothesis empty")
        return False
    return True


def _gate_evidence(payload: Mapping[str, Any], root: Path,
                   view: Mapping[str, Any],
                   report: ValidationReport) -> bool:
    citations = payload.get("evidence_citations")
    if not isinstance(citations, list) or not citations:
        _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
              "no evidence citations")
        return False
    for citation in citations:
        if not isinstance(citation, dict):
            _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                  "citation not a mapping")
            return False
        path = str(citation.get("artifact_path", ""))
        claimed = str(citation.get("sha256", ""))
        # Allowlist + denylist enforced FIRST (fail closed, holdout-blind).
        try:
            rel = evidence_view.assert_source_allowed(path)
        except evidence_view.EvidenceViewError as error:
            _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                  str(error))
            return False
        try:
            file_path = evidence_view._resolve_inside_root(root, rel)
        except evidence_view.EvidenceViewError as error:
            _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                  str(error))
            return False
        try:
            if not file_path.is_file():
                _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                      f"cited artifact missing: {rel}")
                return False
            import hashlib
            # Hash through the SAME race-hardened read gate the evidence view
            # uses, so citation verification is never an alternate read path.
            current = hashlib.sha256(
                evidence_view._read_bytes(root, rel)).hexdigest()
        except evidence_view.EvidenceViewError as error:
            _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                  str(error))
            return False
        except OSError as error:
            # Unreadable between the is-file check and the read (removed,
            # permission): record a failed validation, never crash the gate
            # chain.
            _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                  f"cited artifact unreadable: {rel} ({error})")
            return False
        recorded = evidence_view.source_hash(view, rel)
        if recorded is None:
            # Fail closed: the path is on the allowlist and exists on disk,
            # but the evidence view that authorizes this proposal carries no
            # hash for it (created after the view was built — a stale view).
            # Only the dataset's CHAMPION-recorded hash lives outside
            # view.sources, and only when the champion declares it.
            _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                  f"cited artifact not present in the evidence view: {rel}")
            return False
        if claimed != current:
            _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                  f"hash mismatch for {rel}: cited {claimed[:12]} != "
                  f"current {current[:12]}")
            return False
        if recorded != current:
            _fail(report, schema.GATE_EVIDENCE, schema.RC_UNRECALLED_EVIDENCE,
                  f"view hash stale for {rel}")
            return False
    return True


def _gate_falsifiability(payload: Mapping[str, Any],
                         report: ValidationReport) -> bool:
    rule = payload.get("falsification_rule")
    if not isinstance(rule, dict):
        _fail(report, schema.GATE_FALSIFIABILITY, schema.RC_NOT_FALSIFIABLE,
              "falsification_rule missing")
        return False
    metric = rule.get("metric")
    comparator = rule.get("comparator")
    threshold = rule.get("threshold")
    scope = rule.get("scope")
    if metric not in schema.FALSIFICATION_METRICS:
        _fail(report, schema.GATE_FALSIFIABILITY, schema.RC_NOT_FALSIFIABLE,
              f"unknown metric {metric!r}")
        return False
    if comparator not in schema.COMPARATORS:
        _fail(report, schema.GATE_FALSIFIABILITY, schema.RC_NOT_FALSIFIABLE,
              f"unknown comparator {comparator!r}")
        return False
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        _fail(report, schema.GATE_FALSIFIABILITY, schema.RC_NOT_FALSIFIABLE,
              "threshold not numeric")
        return False
    low, high = schema.FALSIFICATION_METRICS[metric]
    if not low <= float(threshold) <= high:
        _fail(report, schema.GATE_FALSIFIABILITY, schema.RC_NOT_FALSIFIABLE,
              f"threshold {threshold} outside [{low}, {high}] for {metric}")
        return False
    if not isinstance(scope, str) or not scope.strip():
        _fail(report, schema.GATE_FALSIFIABILITY, schema.RC_NOT_FALSIFIABLE,
              "scope missing")
        return False
    return True


def _gate_surface(payload: Mapping[str, Any],
                  report: ValidationReport) -> bool:
    design = payload.get("design")
    if not isinstance(design, dict) or not isinstance(design.get("primitives"), list) \
            or not design["primitives"]:
        _fail(report, schema.GATE_SURFACE, schema.RC_UNSUPPORTED_PRIMITIVE,
              "design.primitives missing")
        return False
    for entry in design["primitives"]:
        primitive_id = str((entry or {}).get("primitive_id", ""))
        problems = primitive_lib.validate_params(
            primitive_id, (entry or {}).get("params"))
        if problems:
            joined = " ".join(problems)
            reason = (schema.RC_UNSUPPORTED_PRIMITIVE
                      if "Unknown primitive" in joined
                      else schema.RC_INVALID_PARAMETER)
            # Path/code-looking values escalate to SURFACE_ESCAPE.
            values = _walk_strings((entry or {}).get("params"))
            if any(schema.looks_like_path(value) or schema.looks_like_code(value)
                   for value in values):
                reason = schema.RC_SURFACE_ESCAPE
            _fail(report, schema.GATE_SURFACE, reason, joined)
            return False
    # No free code / no arbitrary paths anywhere in design or parameters.
    for container_name in ("design", "parameters"):
        for text in _walk_strings(payload.get(container_name)):
            if schema.looks_like_path(text) or schema.looks_like_code(text):
                _fail(report, schema.GATE_SURFACE, schema.RC_SURFACE_ESCAPE,
                      f"path/code-looking value in {container_name}: {text!r}")
                return False
    return True


def _gate_holdout(payload: Mapping[str, Any],
                  report: ValidationReport) -> bool:
    for text in _walk_strings(payload):
        if schema.contains_holdout_path(text):
            _fail(report, schema.GATE_HOLDOUT, schema.RC_HOLDOUT_REFERENCE,
                  f"holdout path reference in proposal: {text[:80]!r}")
            return False
    return True


def _gate_duplicate(payload: Mapping[str, Any],
                    merged_history: list[Mapping[str, Any]],
                    recipe_signatures: Mapping[str, str],
                    policy: Mapping[str, Any],
                    report: ValidationReport,
                    proposal_id: str | None = None) -> bool:
    # The proposal under review is itself in the ledger (post-creation
    # accounting); exclude it so it cannot "duplicate" itself.
    merged_history = [item for item in merged_history
                      if item.get("proposal_id") != proposal_id]
    fingerprint = payload.get("proposal_fingerprint")
    signature = payload.get("design_signature")
    hypothesis = str(payload.get("hypothesis", ""))

    if signature in recipe_signatures:
        _fail(report, schema.GATE_DUPLICATE, schema.RC_DUPLICATE,
              f"design already executed in a prior campaign attempt: "
              f"{recipe_signatures[str(signature)]}")
        return False

    same_fingerprint = any(
        (item.get("proposal") or {}).get("proposal_fingerprint") == fingerprint
        for item in merged_history)
    if same_fingerprint:
        _fail(report, schema.GATE_DUPLICATE, schema.RC_DUPLICATE,
              "proposal fingerprint already asked")
        return False

    same_signature = [item for item in merged_history
                      if (item.get("proposal") or {}).get("design_signature") == signature]
    if same_signature and not payload.get("delta_from_prior"):
        _fail(report, schema.GATE_DUPLICATE, schema.RC_NEAR_DUPLICATE,
              "same design signature previously asked without a declared "
              "delta_from_prior justification")
        return False

    # Layer 3 (text similarity): applies ONLY within the same design
    # signature (OBS-1 resolution, 2026-10-04). Wording can never exonerate
    # a same-signature re-ask — even with delta_from_prior declared, the
    # framing must actually differ. Cross-signature text similarity is a
    # generation-side diversity preference only: a templated hypothesis may
    # NOT refuse a scientifically distinct design. Cross-signature semantic
    # equivalence is not deterministically decidable without an LLM, so it
    # is a documented limitation (Stage-1 resolution audit §G) rather than
    # a heuristic gate. Layers 1 (fingerprint) and 2 (signature) are
    # unchanged and remain the authoritative duplicate controls.
    threshold = float(policy.get("near_duplicate_text_threshold",
                                 schema.NEAR_DUPLICATE_TEXT_THRESHOLD))
    for item in same_signature:
        prior = str((item.get("proposal") or {}).get("hypothesis", ""))
        if prior and schema.text_similarity(hypothesis, prior) >= threshold:
            _fail(report, schema.GATE_DUPLICATE, schema.RC_NEAR_DUPLICATE,
                  "same-signature proposal with near-identical hypothesis "
                  "text despite declared delta_from_prior")
            return False
    return True


def _gate_budget(payload: Mapping[str, Any], state: Mapping[str, Any],
                 policy: Mapping[str, Any],
                 report: ValidationReport) -> bool:
    # Fail-closed campaign scope: under an active campaign, only proposals
    # of THAT campaign are admissible — a proposal from another campaign
    # (or with no campaign) can never consume or bypass this campaign's
    # budget (Stage 2, revalidate_at_approval@1.0.0).
    campaign_id = policy.get("campaign_id")
    if campaign_id is not None and payload.get("campaign_id") != campaign_id:
        _fail(report, schema.GATE_BUDGET, schema.RC_CAMPAIGN_MISMATCH,
              f"proposal campaign {payload.get('campaign_id')!r} does not "
              f"match active campaign {campaign_id!r}")
        return False
    direction = str(payload.get("direction"))
    count = int(state["by_direction"].get(direction, 0))
    # Post-creation accounting: the proposal itself is already in `state`.
    if count > int(policy.get("max_per_direction", 4)):
        _fail(report, schema.GATE_BUDGET, schema.RC_BUDGET_EXHAUSTED,
              f"direction {direction} exceeds {policy.get('max_per_direction')}")
        return False
    if int(state["total"]) > int(policy.get("max_total_proposals", 20)):
        _fail(report, schema.GATE_BUDGET, schema.RC_BUDGET_EXHAUSTED,
              "total proposal budget exceeded")
        return False
    return True


def _gate_bias(payload: Mapping[str, Any], governor: BiasGovernor,
               state: Mapping[str, Any],
               report: ValidationReport) -> bool:
    ok, reason, detail = governor.check_accept(payload, state)
    if not ok:
        _fail(report, schema.GATE_BIAS, reason or schema.RC_BIAS_QUOTA, detail)
        return False
    return True


def _gate_mechanical(payload: Mapping[str, Any], root: Path,
                     view: Mapping[str, Any],
                     report: ValidationReport) -> bool:
    """Validate the produced spec AND bind provenance to the validated
    snapshot.

    The spec is compiled bound to the champion snapshot the evidence view
    recorded: if CHAMPION.json changed between the evidence gate and
    provenance resolution, the parent version can never silently diverge
    from the validated evidence (consistent provenance snapshot across all
    gates)."""
    from autonomous_agent.proposal_layer import compiler
    champion_sha = evidence_view.source_hash(view, "CHAMPION.json")
    if champion_sha is None:
        _fail(report, schema.GATE_MECHANICAL, schema.RC_UNRECALLED_EVIDENCE,
              "evidence view does not record CHAMPION.json; provenance "
              "snapshot cannot be bound")
        return False
    try:
        spec = compiler.preview_spec(payload, root=root,
                                     champion_sha256=champion_sha)
        spec.validate()
    except compiler.CompileError as error:
        _fail(report, schema.GATE_MECHANICAL, str(error.code), str(error))
        return False
    except Exception as error:  # noqa: BLE001 - fail closed on anything else
        _fail(report, schema.GATE_MECHANICAL, schema.RC_SPEC_CONTRACT,
              f"spec validation raised: {error}")
        return False
    return True


def validate_proposal(payload: Mapping[str, Any], *, root: Path | str,
                      view: Mapping[str, Any],
                      merged_history: list[Mapping[str, Any]],
                      policy: Mapping[str, Any],
                      governor: BiasGovernor | None = None,
                      run_mechanical: bool = True,
                      proposal_id: str | None = None) -> ValidationReport:
    """Run the full gate chain in Phase 1 C.4 order; fail fast on first gate."""
    root = Path(root)
    governor = governor or BiasGovernor(policy)
    report = ValidationReport(passed=True)

    if not _gate_schema(payload, report):
        return report
    if not _gate_evidence(payload, root, view, report):
        return report
    if not _gate_falsifiability(payload, report):
        return report
    if not _gate_surface(payload, report):
        return report
    if not _gate_holdout(payload, report):
        return report

    recipe_signatures: dict[str, str] = {}
    for row in view.get("recipe_attempts", []):
        signature = schema.signature_from_recipe_attempt(
            row.get("recipe_id"), row.get("selected_parameters") or {})
        if signature:
            recipe_signatures[signature] = str(row.get("experiment_id"))
    if not _gate_duplicate(payload, merged_history, recipe_signatures,
                           policy, report, proposal_id=proposal_id):
        return report

    state = governor.quota_state(list(merged_history),
                                 campaign_id=policy.get("campaign_id"))
    if not _gate_budget(payload, state, policy, report):
        return report
    if not _gate_bias(payload, governor, state, report):
        return report
    if run_mechanical and not _gate_mechanical(payload, root, view, report):
        return report

    report.gates.append(GateResult(gate=schema.GATE_MECHANICAL if run_mechanical
                                   else "ALL", passed=True))
    report.status_target = None
    return report
