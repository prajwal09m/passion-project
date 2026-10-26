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
