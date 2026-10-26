"""Fail-closed, signed authorization preflight for Campaign 5 execution.

This module verifies explicit owner and independent-reviewer HMAC attestations.
It never creates approval records. Runtime signing keys must be provisioned
outside the repository as distinct secrets; no keys or C5 authorization exist
in this checkout. Synthetic records are accepted only by the pure validator's
explicit test-only switch, never by the runtime preflight.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

AUTH_RELATIVE_PATH = Path("autonomous_agent/state/campaign5_authorization.json")
PREDECLARATION_FIELDS = {"id", "version", "path", "sha256", "protocol_sha256",
                         "scope_sha256", "approval_status"}
SCOPE_FIELDS = {"model_families", "candidate_generation_method", "comparisons",
                "measurements", "operations", "permitted_changes"}
RECORD_FIELDS = {"schema", "record_class", "record_id", "status", "issued_at",
                 "expires_at", "campaign_id", "execution_scope", "protocol",
                 "scope", "scope_sha256", "data_boundary", "predeclaration",
                 "owner_approval", "independent_review", "signatures"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sign_for_test(record: Mapping[str, Any], key: bytes) -> str:
    """Synthetic helper for tests; never called by runtime code."""
    unsigned = {name: value for name, value in record.items() if name != "signatures"}
    return hmac.new(key, canonical_bytes(unsigned), hashlib.sha256).hexdigest()


def _parse_time(value: Any, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{field}_missing_or_invalid")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field}_invalid")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field}_timezone_missing")
        return None
    return parsed.astimezone(timezone.utc)


def _nonempty_strings(value: Any) -> bool:
    return (isinstance(value, list) and bool(value)
            and all(isinstance(item, str) and item.strip() for item in value)
            and len(value) == len(set(value)))


def validate_authorization(record: Any, planned_scope: Any, *,
                           owner_key: bytes | None, reviewer_key: bytes | None,
                           now: datetime | None = None,
                           allow_synthetic: bool = False) -> list[str]:
    """Return deterministic failure codes; an empty list means structurally valid.

    ``allow_synthetic`` exists solely for isolated validator unit tests. Runtime
    callers never enable it and the execution preflight rejects synthetic class
    records independently of signature validity.
    """
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["authorization_record_missing_or_not_object"]
    if any(not isinstance(key, str) for key in record):
        return ["authorization_record_fields_malformed"]
    if set(record) != RECORD_FIELDS:
        errors.append("authorization_record_fields_mismatch")
    if record.get("schema") != "campaign5-authorization/v1":
        errors.append("authorization_schema_unsupported")
    record_class = record.get("record_class")
    if record_class != "authoritative" and not (allow_synthetic and record_class == "synthetic"):
        errors.append("authorization_record_not_authoritative")
    elif allow_synthetic and record_class == "synthetic" and not str(record.get("record_id", "")).startswith("SYNTHETIC-ONLY-TEST"):
        errors.append("synthetic_record_marker_missing")
    if record.get("status") != "approved":
        errors.append("authorization_not_active_approved")
    if not isinstance(record.get("record_id"), str) or not record["record_id"].strip():
        errors.append("authorization_record_id_missing")
    campaign_id = record.get("campaign_id")
    if not isinstance(campaign_id, str) or not campaign_id.startswith("campaign-5"):
        errors.append("campaign_identity_mismatch")
    if record.get("execution_scope") != "real_market_evaluation":
        errors.append("execution_scope_mismatch")

    issued = _parse_time(record.get("issued_at"), "issued_at", errors)
    expires = _parse_time(record.get("expires_at"), "expires_at", errors)
    clock = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if issued and issued > clock:
        errors.append("authorization_not_yet_valid")
    if expires and expires <= clock:
        errors.append("authorization_expired")
    if issued and expires and expires <= issued:
        errors.append("authorization_expiry_invalid")

    protocol = record.get("protocol")
    if not isinstance(protocol, dict) or set(protocol) != {"id", "version", "sha256"}:
        errors.append("protocol_record_malformed")
        protocol = {}
    if any(not isinstance(protocol.get(k), str) or not protocol[k].strip()
           for k in ("id", "version")):
        errors.append("protocol_identity_incomplete")
    protocol_sha = protocol.get("sha256")
    if not isinstance(protocol_sha, str) or len(protocol_sha) != 64 or any(c not in "0123456789abcdef" for c in protocol_sha):
        errors.append("protocol_digest_invalid")

    scope = record.get("scope")
    if not isinstance(scope, dict) or set(scope) != SCOPE_FIELDS:
        errors.append("scope_fields_mismatch")
        scope = {}
    for field in ("model_families", "comparisons", "measurements", "operations"):
        if not _nonempty_strings(scope.get(field)):
            errors.append(f"scope_{field}_missing_or_invalid")
    if not isinstance(scope.get("candidate_generation_method"), str) or not scope.get("candidate_generation_method", "").strip():
        errors.append("scope_candidate_generation_method_missing")
    if not isinstance(scope.get("permitted_changes"), list) or not all(
            isinstance(item, str) and item.strip() for item in scope.get("permitted_changes", [])):
        errors.append("scope_permitted_changes_invalid")
    digest = sha256_json(scope)
    if record.get("scope_sha256") != digest:
        errors.append("scope_digest_mismatch")
    if not isinstance(planned_scope, dict) or planned_scope != scope:
        errors.append("planned_scope_mismatch")

    boundary = record.get("data_boundary")
    boundary_fields = {"record_id", "record_path", "record_sha256", "permission_status",
                       "permitted_datasets", "denied_paths"}
    if not isinstance(boundary, dict) or set(boundary) != boundary_fields:
        errors.append("data_boundary_record_malformed")
    else:
        if not boundary.get("record_id") or boundary.get("permission_status") != "explicitly_permitted":
            errors.append("data_permission_missing_or_unclear")
        if (not isinstance(boundary.get("record_sha256"), str)
                or len(boundary["record_sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in boundary["record_sha256"])):
            errors.append("data_boundary_digest_invalid")
        boundary_path = boundary.get("record_path")
        if (not isinstance(boundary_path, str) or not boundary_path
                or Path(boundary_path).is_absolute() or ".." in Path(boundary_path).parts):
            errors.append("data_boundary_path_invalid")
        datasets = boundary.get("permitted_datasets")
        if not isinstance(datasets, list) or not datasets:
            errors.append("permitted_datasets_missing")
        else:
            for dataset in datasets:
                if (not isinstance(dataset, dict)
                        or set(dataset) != {"dataset_id", "sha256", "operations"}
                        or not dataset.get("dataset_id")
                        or not isinstance(dataset.get("sha256"), str)
                        or len(dataset["sha256"]) != 64
                        or any(c not in "0123456789abcdef" for c in dataset.get("sha256", ""))
                        or not _nonempty_strings(dataset.get("operations"))
                        or not set(scope.get("operations", [])) <= set(dataset.get("operations", []))):
                    errors.append("permitted_dataset_scope_invalid")
                    break
        denied = boundary.get("denied_paths")
        if not _nonempty_strings(denied) or not any("prospective" in p.lower() or "holdout" in p.lower() for p in denied):
            errors.append("protected_data_denial_missing")

    predecl = record.get("predeclaration")
    if not isinstance(predecl, dict) or set(predecl) != PREDECLARATION_FIELDS:
        errors.append("predeclaration_record_malformed")
    else:
        if (not predecl.get("id") or not predecl.get("version")
                or predecl.get("approval_status") != "approved"):
            errors.append("predeclaration_not_approved")
        for field, expected in (("protocol_sha256", protocol_sha),
                                ("scope_sha256", digest)):
            if predecl.get(field) != expected:
                errors.append(f"predeclaration_{field}_mismatch")
        if (not isinstance(predecl.get("sha256"), str) or len(predecl["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in predecl["sha256"])):
            errors.append("predeclaration_digest_invalid")
        path = predecl.get("path")
        if not isinstance(path, str) or not path or Path(path).is_absolute() or ".." in Path(path).parts:
            errors.append("predeclaration_path_invalid")

    approval_fields = {"decision", "actor_id", "campaign_id", "protocol_sha256",
                       "scope_sha256", "predeclaration_sha256", "decided_at"}
    owner = record.get("owner_approval")
    if not isinstance(owner, dict) or set(owner) != approval_fields:
        errors.append("owner_approval_malformed")
    else:
        if owner.get("decision") != "approve" or not owner.get("actor_id"):
            errors.append("owner_approval_missing")
        for field, expected in (("campaign_id", campaign_id), ("protocol_sha256", protocol_sha),
                                ("scope_sha256", digest),
                                ("predeclaration_sha256", (predecl or {}).get("sha256"))):
            if owner.get(field) != expected:
                errors.append(f"owner_approval_{field}_mismatch")
        _parse_time(owner.get("decided_at"), "owner_decided_at", errors)

    review_fields = approval_fields | {"qualifications", "independent", "conflicts_disclosed", "conflict_present"}
    review = record.get("independent_review")
    if not isinstance(review, dict) or set(review) != review_fields:
        errors.append("independent_review_malformed")
    else:
        if (review.get("decision") != "approve" or not review.get("actor_id")
                or not _nonempty_strings(review.get("qualifications"))
                or review.get("independent") is not True
                or review.get("conflicts_disclosed") is not True
                or review.get("conflict_present") is not False):
            errors.append("independent_review_not_qualified_independent_approved")
        if owner and review.get("actor_id") == owner.get("actor_id"):
            errors.append("reviewer_not_independent_of_owner")
        for field, expected in (("campaign_id", campaign_id), ("protocol_sha256", protocol_sha),
                                ("scope_sha256", digest),
                                ("predeclaration_sha256", (predecl or {}).get("sha256"))):
            if review.get(field) != expected:
                errors.append(f"independent_review_{field}_mismatch")
        _parse_time(review.get("decided_at"), "review_decided_at", errors)

    signatures = record.get("signatures")
    if not isinstance(signatures, dict) or set(signatures) != {"owner_hmac_sha256", "reviewer_hmac_sha256"}:
        errors.append("authorization_signatures_missing_or_malformed")
    else:
        if owner_key is None or reviewer_key is None:
            errors.append("authorization_trust_keys_unavailable")
        else:
            expected_owner = sign_for_test(record, owner_key)
            expected_reviewer = sign_for_test(record, reviewer_key)
            if not hmac.compare_digest(str(signatures.get("owner_hmac_sha256", "")), expected_owner):
                errors.append("owner_signature_invalid")
            if not hmac.compare_digest(str(signatures.get("reviewer_hmac_sha256", "")), expected_reviewer):
                errors.append("reviewer_signature_invalid")
            if owner_key == reviewer_key:
                errors.append("owner_and_reviewer_trust_keys_not_distinct")
    return sorted(set(errors))


def _key_from_environment(name: str) -> bytes | None:
    value = os.environ.get(name)
    if not value:
        return None
    try:
        decoded = bytes.fromhex(value)
    except ValueError:
        return None
    return decoded if len(decoded) >= 32 else None


def _audit(root: Path, decision: Mapping[str, Any]) -> bool:
    try:
        path = root / "autonomous_agent/state/campaign5_preflight_audit.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(dict(decision), sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return True
    except OSError:
        return False


def check_campaign5_authorization(root: Path | str, campaign: Mapping[str, Any],
                                  planned_scope: Any = None) -> dict[str, Any]:
    """Check and audit C5 authorization; non-C5 campaign identities are unaffected."""
    campaign_id = campaign.get("campaign_id") if isinstance(campaign, Mapping) else None
    if not isinstance(campaign_id, str) or not campaign_id.startswith("campaign-5"):
        return {"allowed": True, "status": "NOT_APPLICABLE", "reason_codes": []}
    root = Path(root).resolve()
    record: Any = None
    reasons: list[str] = []
    try:
        record_path = root / AUTH_RELATIVE_PATH
        if not record_path.is_file():
            reasons = ["authorization_record_unavailable"]
            record = None
        else:
            expected_protocol = {
                "id": campaign.get("protocol_id"),
                "version": campaign.get("protocol_version"),
                "sha256": campaign.get("protocol_sha256"),
            }
            if any(not isinstance(value, str) or not value.strip()
                   for value in expected_protocol.values()):
                raise ValueError("campaign protocol pin missing")
            trusted_owner = os.environ.get("C5_OWNER_ACTOR_ID")
            trusted_reviewer = os.environ.get("C5_REVIEWER_ACTOR_ID")
            if not trusted_owner or not trusted_reviewer or trusted_owner == trusted_reviewer:
                raise ValueError("trusted owner/reviewer identities missing or not distinct")
            record = json.loads(record_path.read_text(encoding="utf-8"))
        if record is None:
            pass
        elif record.get("record_class") == "synthetic":
            reasons = ["authorization_record_not_authoritative"]
        elif record.get("campaign_id") != campaign_id:
            reasons = ["campaign_identity_mismatch"]
        elif record.get("protocol") != expected_protocol:
            reasons = ["campaign_protocol_mismatch"]
        else:
            reasons = validate_authorization(
                record, planned_scope if planned_scope is not None else campaign.get("authorization_scope"),
                owner_key=_key_from_environment("C5_OWNER_HMAC_KEY"),
                reviewer_key=_key_from_environment("C5_REVIEWER_HMAC_KEY"),
            )
            if isinstance(record.get("owner_approval"), dict) and record["owner_approval"].get("actor_id") != trusted_owner:
                reasons.append("owner_identity_not_trusted")
            if isinstance(record.get("independent_review"), dict) and record["independent_review"].get("actor_id") != trusted_reviewer:
                reasons.append("reviewer_identity_not_trusted")
        if not reasons and isinstance(record, dict):
            boundary = record["data_boundary"]
            boundary_path = (root / boundary["record_path"]).resolve()
            if root not in boundary_path.parents:
                reasons.append("data_boundary_path_outside_workspace")
            elif not boundary_path.is_file():
                reasons.append("data_boundary_record_unavailable")
            elif hashlib.sha256(boundary_path.read_bytes()).hexdigest() != boundary["record_sha256"]:
                reasons.append("data_boundary_hash_mismatch")
            predecl = record["predeclaration"]
            predecl_path = (root / predecl["path"]).resolve()
            if root not in predecl_path.parents:
                reasons.append("predeclaration_path_outside_workspace")
            elif not predecl_path.is_file():
                reasons.append("predeclaration_artifact_unavailable")
            elif hashlib.sha256(predecl_path.read_bytes()).hexdigest() != predecl["sha256"]:
                reasons.append("predeclaration_hash_mismatch")
    except Exception as error:  # fail closed on I/O, parse, and schema errors
        reasons = ["authorization_record_unavailable_or_malformed"]
        if isinstance(error, OSError):
            reasons = ["authorization_record_unavailable"]

    result = {
        "at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": campaign_id,
        "authorization_id": record.get("record_id") if isinstance(record, dict) else None,
        "protocol_version": ((record.get("protocol") or {}).get("version")
                             if isinstance(record, dict) else None),
        "allowed": not reasons,
        "status": "APPROVED" if not reasons else "BLOCKED",
        "reason_codes": sorted(set(reasons)),
    }
    if not _audit(root, result):
        return {**result, "allowed": False, "status": "BLOCKED",
                "reason_codes": sorted(set(result["reason_codes"] + ["preflight_audit_unavailable"]))}
    return result
