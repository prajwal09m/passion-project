"""Proposal cycle orchestration (the production entry point, flag-gated).

Order of operations (every refusal recorded):

  flag OFF? -> raise DisabledError BEFORE any ledger write (nothing happens)
  build EvidenceView -> generate -> per proposal:
    create (PROPOSED) -> VALIDATING -> gate chain ->
      gate fail:  REFUSED | FAILED_VALIDATION   (terminal, recorded)
      gate pass:  approval (human or auto policy) ->
                  REVALIDATE against current state (revalidate_at_approval@1.0.0) ->
                    still valid:  ACCEPTED_FOR_EXECUTION -> compile -> COMPILED
                                                  or FAILED_COMPILATION
                    state changed: REFUSED | FAILED_VALIDATION (recorded)

Approval-time revalidation (OBS-3, Policy B, 2026-10-04): a proposal that
passed every gate at creation time T1 may become REFUSED/BUDGET_EXHAUSTED at
approval time T2 if budget/quota state changed in between. It can never
silently become an execution candidate. `approve_pending` is the restart-safe
entry point that applies this policy to proposals awaiting approval from an
earlier run; it never compiles and never executes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from autonomous_agent.proposal_layer import compiler, generator, schema
from autonomous_agent.proposal_layer import evidence_view as _evidence_view
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor, merge_policy
from autonomous_agent.proposal_layer.ledger import ProposalLedger

LEDGER_RELATIVE_PATH = "autonomous_agent/state/proposal_ledger.jsonl"
POLICY_RELATIVE_PATH = "autonomous_agent/proposal_layer/bias_policy.json"
CAMPAIGN_CONFIG_RELATIVE_PATH = "autonomous_agent/state/campaign_config.json"
# Owner-signed Option A steering exception record (2026-10-25): admits the
# 5 predeclared error-cluster axis rows through the post-creation
# falsification-share steering rule, narrowly scoped by decision record.
C5_EXCEPTION_RECORD_RELATIVE_PATH = (
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
    "C5_STEERING_EXCEPTION_DECISION_A_2026_10_25.json")
C5_EXCEPTION_PIN_RELATIVE_PATH = (
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
    "C5_STEERING_EXCEPTION_DECISION_A_2026_10_25.sha256")

# The approval policy id/version persisted in every ACCEPTED_FOR_EXECUTION
# (and every approval-attempt) transition detail. See OBS-3 resolution.
APPROVAL_POLICY = "revalidate_at_approval@1.0.0"


class DisabledError(Exception):
    """Proposal-layer flag is OFF: the production cycle must do nothing."""


def _load_campaign(root: Path) -> dict[str, Any] | None:
    """Read the active (immutable, hashed) campaign configuration, if any.

    The campaign config overlays budget policy for the proposal layer:
    budgets are campaign-scoped while duplicate/already-asked memory stays
    global and permanent. Absence = legacy uncampaigned behavior.
    """
    import json
    path = root / CAMPAIGN_CONFIG_RELATIVE_PATH
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("campaign_id"), str):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return None


def _load_c5_steering_exception(root: Path,
                                campaign_id: str | None) -> dict[str, Any] | None:
    """Load + verify the owner-signed steering exception record, fail-closed.

    * Record absent -> ``None``: plain frozen steering applies (exception off).
      This is the correct state for every other campaign or a tmp fixture.
    * Record present but its bytes do not hash to the pinned digest, it is
      unparseable, it misses required fields, or it contradicts the Option A
      contract -> loud ``ValueError``: a broken signed record must stop the
      process, never silently disable the exception it authorizes.
    * Record present and valid but written for a different campaign ->
      ``None`` (not applicable here).

    The exception admits exactly ``total_rows_limit`` rows, at most
    ``per_axis_limit`` per predeclared axis signature, all within the named
    campaign scope. Verification is deterministic; nothing here can widen
    the scope.
    """
    import hashlib
    import json
    record_path = root / C5_EXCEPTION_RECORD_RELATIVE_PATH
    if not record_path.is_file():
        return None
    record_bytes = record_path.read_bytes()
    pin_path = root / C5_EXCEPTION_PIN_RELATIVE_PATH
    try:
        pin_text = pin_path.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    except (OSError, IndexError) as error:
        raise ValueError(
            "refusing to load the C5 steering exception: pin file unreadable"
        ) from error
    if hashlib.sha256(record_bytes).hexdigest() != pin_text:
        raise ValueError(
            "refusing to load the C5 steering exception: record bytes do not "
            "match the pinned digest (tamper detected)")
    try:
        record = json.loads(record_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "refusing to load the C5 steering exception: unparseable record"
        ) from error
    required = ("decision", "status", "authorized_by", "authorization_id",
                "campaign_id", "primitive_id", "proposal_class", "axes",
                "per_axis_limit", "total_rows_limit", "disclosure")
    if not isinstance(record, dict) or any(k not in record for k in required):
        raise ValueError(
            "refusing to load the C5 steering exception: missing required "
            "record fields")
    if record["decision"] != "Option A" \
            or record["status"] != "DECIDED_2026_10_25":
        raise ValueError(
            "refusing to load the C5 steering exception: record is not the "
            "decided Option A record")
    if record["primitive_id"] != "error_clustering_analysis" \
            or record["proposal_class"] != "exploration" \
            or record["direction"] != "error_analysis":
        raise ValueError(
            "refusing to load the C5 steering exception: primitive/class "
            "mismatch with the frozen predeclaration")
    axes = record["axes"]
    if (not isinstance(axes, list) or len(axes) != 5
            or not all(isinstance(a, str) and a for a in axes)):
        raise ValueError(
            "refusing to load the C5 steering exception: axes must be the "
            "5 predeclared axis names")
    if (int(record["per_axis_limit"]) != 1
            or int(record["total_rows_limit"]) != 5):
        raise ValueError(
            "refusing to load the C5 steering exception: limits must be "
            "per_axis 1 / total 5 (the owner's 5-row grant)")
    if campaign_id is None or record["campaign_id"] != campaign_id:
        return None  # valid record, but not for this campaign: exception off
    signatures = [
        schema.design_signature(primitive_ids=(str(record["primitive_id"]),),
                                params={"error_cluster_axis": axis})
        for axis in axes]
    return {
        "decision_id": str(record["decision_id"]),
        "authorization_id": str(record["authorization_id"]),
        "campaign_id": str(record["campaign_id"]),
        "primitive_id": str(record["primitive_id"]),
        "proposal_class": str(record["proposal_class"]),
        "design_signatures": signatures,
        "per_axis_limit": int(record["per_axis_limit"]),
        "total_rows_limit": int(record["total_rows_limit"]),
        "disclosure": str(record["disclosure"]),
    }


def _load_policy(root: Path) -> dict[str, Any]:
    import json
    path = root / POLICY_RELATIVE_PATH
    policy: dict[str, Any] = merge_policy(None)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                policy = merge_policy(data)
        except (OSError, json.JSONDecodeError):
            pass
    campaign = _load_campaign(root)
    if campaign is not None:
        overrides = campaign.get("policy_overrides")
        if isinstance(overrides, dict):
            policy.update(overrides)
        policy.setdefault("campaign_id", campaign.get("campaign_id"))
    exception = _load_c5_steering_exception(root, policy.get("campaign_id"))
    if exception is not None:
        # Injected AFTER every merge so no frozen artifact text can strip or
        # widen it; the governor treats it as a read-only closed record.
        policy["c5_steering_exception"] = exception
    return policy


def run_proposal_cycle(root: Path | str, *, seed: int,
                       clock: Callable[[], str] | None = None,
                       approver: str | None = None,
                       limit: int | None = None) -> dict[str, Any]:
    """Generate, validate, and compile proposals for one cycle.

    Refuses with DisabledError before touching anything when the feature flag
    is OFF (the default). Never executes experiments, never writes outside the
    proposal ledger.
    """
    from autonomous_agent.proposal_layer import proposals_enabled
    root = Path(root)
    if not proposals_enabled(root):
        raise DisabledError(
            "[DISABLED] allow_generated_proposals is false; the proposal "
            "cycle writes nothing and does nothing.")

    policy = _load_policy(root)
    ledger = ProposalLedger(root / LEDGER_RELATIVE_PATH, clock=clock)
    view = _evidence_view.build(root, clock=clock or _now,
                                ledger_rows=ledger.read_rows(strict=True))
    governor = BiasGovernor(policy)
    payloads = generator.generate_proposals(view, policy, seed=seed, limit=limit)

    summary: dict[str, Any] = {"created": [], "awaiting_approval": [],
                               "refused": [], "failed_validation": [],
                               "refused_at_approval": [],
                               "failed_at_approval": [],
                               "compiled": [], "failed_compilation": []}
    for payload in payloads:
        proposal_id = ledger.create_proposal(payload)
        summary["created"].append(proposal_id)
        ledger.transition(proposal_id, schema.STATUS_VALIDATING)
        merged = ledger.all_proposals()
        report = generator_validate(payload, root=root, view=view,
                                    history=merged, policy=policy,
                                    governor=governor,
                                    proposal_id=proposal_id)
        if not report.passed:
            target = report.status_target or schema.STATUS_FAILED_VALIDATION
            ledger.transition(proposal_id, target,
                              reason_code=report.reason_code,
                              detail=report.to_dict())
            bucket = ("refused" if target == schema.STATUS_REFUSED
                      else "failed_validation")
            summary[bucket].append({"proposal_id": proposal_id,
                                    "reason_code": report.reason_code})
            continue

        auto_approve = not bool(policy.get("require_human_approval", True))
        if auto_approve:
            approver_id: str | None = "policy:auto"
        elif approver:
            approver_id = str(approver)
        else:
            summary["awaiting_approval"].append(proposal_id)
            continue
        # OBS-3 / revalidate_at_approval@1.0.0: approval ALWAYS re-runs the
        # full gate chain against current ledger state before an execution
        # candidate can exist. A T1-valid proposal may refuse at T2.
        target, report = _revalidate_and_approve(
            ledger, payload=payload, proposal_id=proposal_id, root=root,
            view=view, policy=policy, governor=governor, approver=approver_id,
            auto_approve=auto_approve)
        if target != schema.STATUS_ACCEPTED_FOR_EXECUTION:
            bucket = ("refused_at_approval"
                      if target == schema.STATUS_REFUSED
                      else "failed_at_approval")
            summary[bucket].append({"proposal_id": proposal_id,
                                    "reason_code": report.reason_code})
            continue

        merged = ledger.get(proposal_id)
        try:
            spec, spec_sha = compiler.compile_proposal(
                payload, root=root, status=merged["status"])
        except (compiler.CompileError, compiler.BoundaryViolation) as error:
            code = getattr(error, "code", schema.RC_SPEC_CONTRACT)
            ledger.transition(proposal_id, schema.STATUS_FAILED_COMPILATION,
                              reason_code=code, detail={"error": str(error)})
            summary["failed_compilation"].append(
                {"proposal_id": proposal_id, "reason_code": code})
            continue
        ledger.transition(proposal_id, schema.STATUS_COMPILED,
                          reason_code="COMPILED",
                          detail={"spec_sha256": spec_sha,
                                  "experiment_id": spec.experiment_id})
        summary["compiled"].append({"proposal_id": proposal_id,
                                    "spec_sha256": spec_sha})
    return summary


def _revalidate_and_approve(ledger: ProposalLedger, *, payload: Mapping[str, Any],
                            proposal_id: str, root: Path,
                            view: Mapping[str, Any],
                            policy: Mapping[str, Any], governor: BiasGovernor,
                            approver: str, auto_approve: bool):
    """Policy B — revalidate_at_approval@1.0.0 (OBS-3 resolution).

    Approval ALWAYS re-runs the complete 9-gate chain against the CURRENT
    ledger state (post-creation accounting, proposal included). Returns
    ``(target_status, report)``:

      * still valid -> (ACCEPTED_FOR_EXECUTION, report) with approval
        provenance persisted: approval_policy id/version, approved_by, and
        the exact quota_state snapshot the decision used;
      * state changed since T1 -> (REFUSED | FAILED_VALIDATION, report) with
        the failing reason code and the same quota_state snapshot.

    Deterministic and restart-safe: state is reconstructed from the
    append-only ledger, never from process memory.
    """
    current = ledger.all_proposals()
    report = generator_validate(payload, root=root, view=view,
                                history=current, policy=policy,
                                governor=governor, proposal_id=proposal_id)
    if not report.passed:
        target = report.status_target or schema.STATUS_FAILED_VALIDATION
        ledger.transition(
            proposal_id, target, reason_code=report.reason_code,
            detail={**report.to_dict(),
                    "revalidated_at_approval": True,
                    "approval_policy": APPROVAL_POLICY,
                    "approval_attempted_by": str(approver),
                    "quota_state": governor.quota_state(
                        current, campaign_id=policy.get("campaign_id"))})
        return target, report
    ledger.transition(
        proposal_id, schema.STATUS_ACCEPTED_FOR_EXECUTION,
        reason_code=("POLICY_AUTO_APPROVAL" if auto_approve
                     else "HUMAN_APPROVAL"),
        detail={"approval_policy": APPROVAL_POLICY,
                "approved_by": str(approver),
                "quota_state": governor.quota_state(
                    current, campaign_id=policy.get("campaign_id")),
                "revalidated_at_approval": True,
                # Stage 2 approval provenance: identity + grounding of the
                # exact proposal that crossed the boundary.
                "proposal_fingerprint": payload.get("proposal_fingerprint"),
                "design_signature": payload.get("design_signature"),
                "evidence_hashes": {
                    str(c.get("artifact_path")): str(c.get("sha256"))
                    for c in (payload.get("evidence_citations") or [])
                    if isinstance(c, dict)},
                "parent_version": payload.get("parent_version"),
                "baseline_id": payload.get("baseline_id"),
                "protocol_sha256": _protocol_sha(view)})
    return schema.STATUS_ACCEPTED_FOR_EXECUTION, report


def _protocol_sha(view: Mapping[str, Any]) -> str | None:
    """Protocol fingerprint from the evidence view's recorded sources."""
    for row in view.get("sources", []) or []:
        path = str(row.get("path", ""))
        if path.endswith("MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json"):
            return row.get("sha256")
    return None


def approve_pending(root: Path | str, *, approver: str,
                    clock: Callable[[], str] | None = None) -> dict[str, Any]:
    """Apply revalidate_at_approval@1.0.0 to proposals awaiting approval.

    The restart-safe T1 -> T2 path: proposals left in VALIDATING by an
    earlier run are revalidated against CURRENT ledger state before any
    ACCEPTED_FOR_EXECUTION transition. A proposal whose direction/signature/
    total budget or any other gate no longer passes becomes
    REFUSED/FAILED_VALIDATION with the exact reason recorded.

    Never compiles, never executes, writes only to the proposal ledger.
    """
    from autonomous_agent.proposal_layer import proposals_enabled
    root = Path(root)
    if not proposals_enabled(root):
        raise DisabledError(
            "[DISABLED] allow_generated_proposals is false; approve_pending "
            "writes nothing and does nothing.")
    policy = _load_policy(root)
    ledger = ProposalLedger(root / LEDGER_RELATIVE_PATH, clock=clock)
    governor = BiasGovernor(policy)
    summary: dict[str, Any] = {"approved": [], "refused_at_approval": [],
                               "failed_at_approval": [],
                               "already_decided": []}
    pending = [merged for merged in ledger.all_proposals()
               if merged.get("status") == schema.STATUS_VALIDATING]
    if not pending:
        return summary
    view = _evidence_view.build(root, clock=clock or _now,
                                ledger_rows=ledger.read_rows(strict=True))
    for merged in pending:
        proposal_id = merged["proposal_id"]
        # Sequential processing on one ledger: a proposal already decided
        # (e.g. by an interleaved run) is never touched again.
        if ledger.status(proposal_id) != schema.STATUS_VALIDATING:
            summary["already_decided"].append(proposal_id)
            continue
        target, report = _revalidate_and_approve(
            ledger, payload=merged["proposal"], proposal_id=proposal_id,
            root=root, view=view, policy=policy, governor=governor,
            approver=approver, auto_approve=False)
        if target == schema.STATUS_ACCEPTED_FOR_EXECUTION:
            summary["approved"].append(proposal_id)
        else:
            bucket = ("refused_at_approval"
                      if target == schema.STATUS_REFUSED
                      else "failed_at_approval")
            summary[bucket].append({"proposal_id": proposal_id,
                                    "reason_code": report.reason_code})
    return summary


def generator_validate(payload: Mapping[str, Any], *, root: Path,
                       view: Mapping[str, Any],
                       history: list[Mapping[str, Any]],
                       policy: Mapping[str, Any],
                       governor: BiasGovernor,
                       proposal_id: str | None = None):
    from autonomous_agent.proposal_layer.validator import validate_proposal
    return validate_proposal(payload, root=root, view=view,
                             merged_history=history, policy=policy,
                             governor=governor, proposal_id=proposal_id)


def _now() -> str:
    from autonomous_agent.core import utc_now
    return utc_now()
