# Campaign 5 Authorization Predeclaration — Option D: Regime/Error Analysis

Date: 2026-10-22
Status: PREDECLARATION DRAFT (NOT APPROVED, NOT AUTHORIZED)
Campaign Option: D (Regime/Error Analysis)

## Predeclaration Identity

| Field | Value |
|-------|-------|
| ID | campaign-5-regime-error-analysis-predeclaration-2026-10-22 |
| Version | 1.0 |
| Path | `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md` |
| SHA-256 | (to be computed at freeze) |
| Protocol SHA-256 | (to be computed from frozen campaign config) |
| Scope SHA-256 | (to be computed from frozen scope) |
| Approval Status | NOT APPROVED |

## Protocol Definition

| Field | Value |
|-------|-------|
| ID | protocol-demand-zone-ai-c5-regime-error |
| Version | 1.0 |
| SHA-256 | (to be computed from frozen campaign config) |

## Execution Scope

### Model Families

- LightGBM
- LogisticRegression
- (Additional models if ensemble-of-specialists primitive is added)

### Candidate Generation Method

- Deterministic recipe-based generation (from spec_recipes.py)
- Proposal layer composition (from proposal_layer/generator.py)
- NO LLM assistance (llm_involved: false)

### Comparisons

- Nested feature-arm comparisons (A→B→C→D)
- Regime-conditional comparisons (bull/bear/high-vol)
- Error-cluster-based comparisons
- Calibration comparisons

### Measurements

- Pooled out-of-fold ROC-AUC (primary metric)
- Regime-specific AUC (secondary metric)
- Calibration metrics (Brier score, ECE)
- Error cluster statistics
- Subgroup stability metrics

### Operations

- Read-only analysis of development event table
- Fold-local preprocessing on purged chronological folds
- No writes to persistent state
- No holdout access
- No network access

### Permitted Changes

- Add new primitives to `DesignPrimitiveLibrary` (regime definitions, error analysis primitives)
- Modify regime primitive parameters (predeclared regime splits)
- Add error analysis output primitives
- NO changes to core gates, duplicate layers, or holdout policy

## Data Boundary

### Record Identity

| Field | Value |
|-------|-------|
| Record ID | data-boundary-c5-regime-error-2026-10-22 |
| Record Path | `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_DATA_BOUNDARY_2026_10_22.json` |
| Record SHA-256 | (to be computed at freeze) |
| Permission Status | explicitly_permitted |

### Permitted Datasets

| Dataset ID | SHA-256 | Operations |
|------------|---------|------------|
| study_v1_development_event_table | 232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0 | read, preprocessing, fold-local analysis |
| study_v1_development_oof_predictions | 011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829 | read, calibration analysis |

### Denied Paths

- `prospective/` (sealed holdout)
- `study_files/prospective/`
- Any path containing "holdout"
- Any network-accessible data source
- Any brokerage or exchange API endpoint

## Approval Structure

### Owner Approval

| Field | Value |
|-------|-------|
| Decision | (pending: approve / reject) |
| Actor ID | (pending: owner identifier) |
| Campaign ID | campaign-5-regime-error-analysis-2026-10-22 |
| Protocol SHA-256 | (to be computed) |
| Scope SHA-256 | (to be computed) |
| Predeclaration SHA-256 | (to be computed) |
| Decided At | (pending) |

### Independent Review (updated 2026-10-22 per owner-authorized review-mode amendment)

The validator supports two fail-closed review modes (`autonomous_agent/campaign5_authorization.py`).

**Mode A — `independent_human` (default; unchanged contract):** the reviewer attests `independent: true`, `conflicts_disclosed: true`, `conflict_present: false`, with an exact field set. This remains the required mode whenever a genuinely independent human reviewer is engaged.

**Mode B — `ai_substitute_owner_authorized` (operative for C5):** selected by the owner's signed decision `stat_validation_h10/C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md` (owner accepted an AI substitute review with a disclosed conflict of interest). Mode B attestation is valid only if it states the limitation truthfully: `independent: false`, `conflicts_disclosed: true`, `conflict_present: true`, a non-empty `disclosure` naming the conflict, and a `decision_basis` that references the signed owner decision. An independence claim in Mode B fails validation; the reviewer actor must still be distinct from the owner actor.

| Field | Value |
|-------|-------|
| Review Mode | `ai_substitute_owner_authorized` |
| Decision | (pending: approve / reject) |
| Actor ID | (pending: Mode B reviewer identifier, distinct from owner) |
| Qualifications | (pending: reviewer credentials) |
| Independent | false (must truthfully record the reviewer's limitation of implementation independence) |
| Conflicts Disclosed | true |
| Conflict Present | true (owner's signed B2 decision discloses the conflict of interest) |
| Decision Basis | `C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22` |
| Disclosure | (pending: non-empty text naming the conflict of interest) |
| Campaign ID | campaign-5-regime-error-analysis-2026-10-22 |
| Protocol SHA-256 | (to be computed) |
| Scope SHA-256 | (to be computed) |
| Predeclaration SHA-256 | (to be computed) |
| Decided At | (pending) |

### Signatures

| Field | Value |
|-------|-------|
| Owner HMAC SHA-256 | (pending: computed with owner key) |
| Reviewer HMAC SHA-256 | (pending: computed with reviewer key) |

## Authorization Record Structure

The final authorization record (`autonomous_agent/state/campaign5_authorization.json`) will have this structure:

```json
{
  "schema": "campaign5-authorization/v1",
  "record_class": "authoritative",
  "record_id": "campaign-5-regime-error-analysis-auth-2026-10-22",
  "status": "approved",
  "issued_at": "2026-10-22T...",
  "expires_at": "2026-12-31T23:59:59Z",
  "campaign_id": "campaign-5-regime-error-analysis-2026-10-22",
  "execution_scope": "real_market_evaluation",
  "protocol": {
    "id": "protocol-demand-zone-ai-c5-regime-error",
    "version": "1.0",
    "sha256": "..."
  },
  "scope": {
    "model_families": ["LightGBM", "LogisticRegression"],
    "candidate_generation_method": "deterministic_recipe",
    "comparisons": ["nested_feature_arms", "regime_conditional", "error_cluster", "calibration"],
    "measurements": ["pooled_oof_auc", "regime_auc", "brier_score", "ece", "error_cluster_stats"],
    "operations": ["read"],
    "permitted_changes": ["add_primitives", "modify_regime_parameters"]
  },
  "scope_sha256": "...",
  "data_boundary": {
    "record_id": "data-boundary-c5-regime-error-2026-10-22",
    "record_path": "autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_DATA_BOUNDARY_2026_10_22.json",
    "record_sha256": "... (64-hex digest of the boundary file's final frozen bytes, computed at freeze)",
    "permission_status": "explicitly_permitted",
    "permitted_datasets": [
      {
        "dataset_id": "study_v1_development_event_table",
        "sha256": "232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0",
        "operations": ["read", "preprocessing", "fold_local_analysis"]
      },
      {
        "dataset_id": "study_v1_development_oof_predictions",
        "sha256": "011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829",
        "operations": ["read", "calibration_analysis"]
      }
    ],
    "denied_paths": ["prospective/", "study_files/prospective/", "holdout", "autonomous_agent/prospective"]
  },
  "predeclaration": {
    "id": "campaign-5-regime-error-analysis-predeclaration-2026-10-22",
    "version": "1.0",
    "path": "autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md",
    "sha256": "...",
    "protocol_sha256": "...",
    "scope_sha256": "...",
    "approval_status": "approved"
  },
  "owner_approval": {
    "decision": "approve",
    "actor_id": "...",
    "campaign_id": "campaign-5-regime-error-analysis-2026-10-22",
    "protocol_sha256": "...",
    "scope_sha256": "...",
    "predeclaration_sha256": "...",
    "decided_at": "2026-10-22T..."
  },
  "independent_review": {
    "review_mode": "ai_substitute_owner_authorized",
    "decision": "approve",
    "actor_id": "...",
    "qualifications": ["..."],
    "independent": false,
    "conflicts_disclosed": true,
    "conflict_present": true,
    "decision_basis": ["C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22"],
    "disclosure": "...REQUIRED: text must name the conflict of interest (implementing-AI reviewing its own work, conflict disclosed and owner-accepted) ...",
    "campaign_id": "campaign-5-regime-error-analysis-2026-10-22",
    "protocol_sha256": "...",
    "scope_sha256": "...",
    "predeclaration_sha256": "...",
    "decided_at": "2026-10-22T..."
  },
  "signatures": {
    "owner_hmac_sha256": "...",
    "reviewer_hmac_sha256": "..."
  }
}
```

## Prerequisites Before Authorization

Before this predeclaration can be converted to an authorization record, the following must be completed:

1. **Frozen Campaign 5 Configuration**
   - Draft config reviewed and approved by owner
   - Config frozen with protocol_fingerprint computed
   - All prerequisite gates satisfied

2. **Independent Statistical Review**
   - Independent reviewer engaged
   - Review completed with written approval
   - Review recorded in `stat_validation_h10/H10_C5_INDEPENDENT_STATISTICAL_REVIEW.md`

3. **Real-Data Integration Test**
   - Test completed successfully
   - All checks C1-C9 passed
   - Test results documented

4. **Trust Keys Provisioned**
   - Owner HMAC key provisioned as environment variable `C5_OWNER_HMAC_KEY`
   - Reviewer HMAC key provisioned as environment variable `C5_REVIEWER_HMAC_KEY`
   - Keys are distinct (owner key ≠ reviewer key)

5. **Actor IDs Registered**
   - Owner actor ID registered in environment variable `C5_OWNER_ACTOR_ID`
   - Reviewer actor ID registered in environment variable `C5_REVIEWER_ACTOR_ID`
   - IDs are distinct

## Authorization Process

1. **Owner Approval**: Owner reviews predeclaration, frozen config, and independent review, then signs with owner HMAC key
2. **Reviewer Approval**: Independent reviewer reviews predeclaration, frozen config, and scope, then signs with reviewer HMAC key
3. **Record Creation**: Authorization record created with both signatures
4. **Record Placement**: Record written to `autonomous_agent/state/campaign5_authorization.json`
5. **Verification**: Campaign 5 preflight in `continuous_loop.py` verifies record integrity before launch

## Digest Finalization Convention (self-referential artifact fields)

Added 2026-10-22 so freeze-time hashing is mechanical and cannot produce an unsatisfiable self-reference:

- **`scope_sha256`** = SHA-256 over the canonical encoding `json.dumps(scope_object, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)` encoded UTF-8 — byte-identical to `validate_authorization`'s `sha256_json` in `autonomous_agent/campaign5_authorization.py`.
- **`protocol_fingerprint`** = SHA-256 of `schema.canonical_json(config minus the `protocol_fingerprint` key)`, the method adopted at the Campaign 4 freeze and verified in `B1_OWNER_SIGNATURE_PACKET_2026_10_22.md`.
- **`data_boundary.record_sha256`** and **predeclaration `sha256`** = SHA-256 over the artifact's FINAL frozen bytes, stored in the certification record — i.e., the `campaign5_authorization.json` record fields `data_boundary.record_sha256` and `predeclaration.sha256`. A file cannot contain a hash of its own bytes: each artifact's internal digest field is therefore finalized as a truthful certification pointer (stating that this artifact is hashed into the authorization record), NOT as the artifact's own SHA-256. The runtime preflight hashes the file bytes and compares against the record — satisfiable exactly because the record carries the digest and the file is frozen before hashing.
- **Artifact immutability**: after its digest is bound, an artifact is never rewritten. Any later byte change invalidates the record (fail-closed `data_boundary_hash_mismatch` / `predeclaration_hash_mismatch`).
- **Scope-operations subset rule** (shipped validator `validate_authorization`): the record scope's `operations` must be a subset of EVERY permitted dataset's `operations`. The two permitted datasets' operation sets intersect only at `read`, so the satisfiable scope is `operations: ["read"]`; detailed analysis classes (fold-local preprocessing, calibration analysis) are declared in the boundary's per-dataset operations and in scope `comparisons`/`measurements`, never asserted as scope operations the OOF dataset does not permit.
- **Campaign-config protocol pins** (shipped preflight `check_campaign5_authorization`): the frozen C5 config must carry top-level `protocol_id` (`protocol-demand-zone-ai-c5-regime-error`), `protocol_version` (`1.0`), and `protocol_sha256`, plus an `authorization_scope` object byte-identical to the record's scope. Resolution: the config is hashed WITHOUT a `protocol_sha256` key to compute `F = SHA-256(canonical_json(config minus protocol_fingerprint key))` per the recorded method; then `protocol_sha256 = protocol_fingerprint = F`. F binds everything else in the config; the config-file bytes are additionally pinned by the `campaign_config.sha256` sidecar.

## Fail-Closed Behavior

If any of the following conditions fail, Campaign 5 launch is blocked:

- Authorization record missing or malformed
- Authorization record expired
- Campaign ID mismatch
- Protocol SHA-256 mismatch
- Scope SHA-256 mismatch
- Predeclaration SHA-256 mismatch
- Owner signature invalid
- Reviewer signature invalid
- Owner and reviewer keys not distinct
- Owner or reviewer identity not trusted
- Data boundary record missing or hash mismatch
- Predeclaration artifact missing or hash mismatch

## Status

**Predeclaration Status**: DRAFT
**Frozen Config Status**: NOT FROZEN
**Independent Review Status**: NOT COMPLETED
**Real-Data Integration Test Status**: NOT COMPLETED
**Authorization Status**: NOT AUTHORIZED

**Next Steps**:
1. Owner reviews and approves this predeclaration
2. Owner freezes Campaign 5 configuration
3. Independent statistical review completed
4. Real-data integration test completed
5. Trust keys and actor IDs provisioned
6. Owner and reviewer sign authorization record
7. Authorization record created and verified

**Date**: 2026-10-22
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md`
