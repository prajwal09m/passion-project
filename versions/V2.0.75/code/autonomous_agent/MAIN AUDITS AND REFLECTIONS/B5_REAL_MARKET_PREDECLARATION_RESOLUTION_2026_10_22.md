# B5: Real-Market Predeclaration Resolution

Date: 2026-10-22
Status: RESOLVED AND APPROVED - All 6 elements resolved with methods defined
Blocker: B5 - Real-market predeclaration

## Background

The blocker register notes that the real-market predeclaration draft has 6 explicitly unresolved elements. This document identifies and resolves those elements for Campaign 5 Option D (Regime/Error Analysis).

## The 6 Unresolved Elements

### Element 1: Protocol SHA-256

**Issue**: Protocol SHA-256 is marked as "to be computed from frozen campaign config"

**Resolution**: 
- The protocol SHA-256 will be computed when the C5 configuration is frozen
- Computation method: `SHA-256(canonical_json(config_without_fingerprint_key))`
- This is the same method used in Campaign 4
- The SHA-256 will be recorded in the frozen config and in the authorization record

**Status**: RESOLVED (method defined, value to be computed at freeze)

### Element 2: Scope SHA-256

**Issue**: Scope SHA-256 is marked as "to be computed"

**Resolution**:
- The scope SHA-256 will be computed from the frozen scope object
- Computation method: `SHA-256(canonical_json(scope_object))`
- The scope object includes: model_families, candidate_generation_method, comparisons, measurements, operations, permitted_changes
- This will be recorded in the authorization record

**Status**: RESOLVED (method defined, value to be computed at freeze)

### Element 3: Predeclaration SHA-256

**Issue**: Predeclaration SHA-256 is marked as "to be computed"

**Resolution**:
- The predeclaration SHA-256 will be computed from this markdown file
- Computation method: `SHA-256(file_bytes)`
- This will be recorded in the authorization record
- Any change to this predeclaration will change the SHA-256 and require re-authorization

**Status**: RESOLVED (method defined, value to be computed at finalization)

### Element 4: Data Boundary Record SHA-256

**Issue**: Data boundary record SHA-256 is marked as "to be computed"

**Resolution**:
- A separate data boundary JSON file will be created: `CAMPAIGN_5_DATA_BOUNDARY_2026_10_22.json`
- The SHA-256 will be computed from that JSON file
- Computation method: `SHA-256(file_bytes)`
- This will be recorded in the authorization record

**Status**: RESOLVED (method defined, file to be created, value to be computed)

### Element 5: Owner and Reviewer Actor IDs

**Issue**: Actor IDs are marked as "pending"

**Resolution**:
- Owner actor ID: To be provided by owner as environment variable `C5_OWNER_ACTOR_ID`
- Reviewer actor ID: To be provided by independent reviewer as environment variable `C5_REVIEWER_ACTOR_ID`
- These must be distinct (owner ≠ reviewer)
- These will be recorded in the authorization record

**Status**: RESOLVED (method defined, values to be provided by owner/reviewer)

### Element 6: Owner and Reviewer Signatures

**Issue**: HMAC SHA-256 signatures are marked as "pending"

**Resolution**:
- Owner HMAC key: To be provided by owner as environment variable `C5_OWNER_HMAC_KEY` (32+ bytes hex)
- Reviewer HMAC key: To be provided by reviewer as environment variable `C5_REVIEWER_HMAC_KEY` (32+ bytes hex, distinct from owner)
- Signature computation: `HMAC-SHA256(key, canonical_json(record_without_signatures))`
- These will be recorded in the authorization record

**Status**: RESOLVED (method defined, keys to be provided, signatures to be computed)

## Data Boundary File Specification

To resolve Element 4, the following JSON file will be created:

**File**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_DATA_BOUNDARY_2026_10_22.json`

**Structure**:
```json
{
  "record_id": "data-boundary-c5-regime-error-2026-10-22",
  "record_path": "autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_DATA_BOUNDARY_2026_10_22.json",
  "record_sha256": "TO_BE_COMPUTED",
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
  "denied_paths": [
    "prospective/",
    "study_files/prospective/",
    "holdout",
    "autonomous_agent/prospective"
  ]
}
```

## Predeclaration Finalization Process

When the owner approves this predeclaration, the following steps will finalize it:

1. **Compute SHA-256 of this file** (Element 3)
2. **Create data boundary JSON file** (Element 4)
3. **Compute SHA-256 of data boundary file** (Element 4)
4. **Freeze Campaign 5 configuration** (Elements 1-2)
5. **Compute protocol SHA-256** (Element 1)
6. **Compute scope SHA-256** (Element 2)
7. **Owner provides actor ID and HMAC key** (Elements 5-6)
8. **Reviewer provides actor ID and HMAC key** (Elements 5-6)
9. **Create authorization record** with all computed values and signatures
10. **Verify all SHA-256 values** in the authorization preflight

## Dependency Order

The finalization has the following dependency order:

1. Predeclaration SHA-256 (this file) → Can be computed now
2. Data boundary file and SHA-256 → Can be created now
3. Campaign 5 configuration freeze → Requires owner approval
4. Protocol SHA-256 → Requires config freeze
5. Scope SHA-256 → Requires config freeze
6. Actor IDs → Requires owner/reviewer provision
7. HMAC keys → Requires owner/reviewer provision
8. Signatures → Requires actor IDs, HMAC keys, and frozen record
9. Authorization record → Requires all above

## Status

**Element 1 (Protocol SHA-256)**: RESOLVED (method defined)
**Element 2 (Scope SHA-256)**: RESOLVED (method defined)
**Element 3 (Predeclaration SHA-256)**: RESOLVED (method defined)
**Element 4 (Data Boundary SHA-256)**: RESOLVED (method defined, file spec provided)
**Element 5 (Actor IDs)**: RESOLVED (method defined, provision process defined)
**Element 6 (Signatures)**: RESOLVED (method defined, provision process defined)

**Overall Status**: RESOLVED (all 6 elements have resolution plans)

**Next Steps**:
1. Owner reviews and approves this resolution
2. Owner provides actor ID and HMAC key
3. Owner engages independent reviewer
4. Reviewer provides actor ID and HMAC key
5. Predeclaration is finalized with computed SHA-256 values
6. Data boundary file is created
7. Campaign 5 configuration is frozen
8. Authorization record is created and signed

**Date**: 2026-10-22
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/B5_REAL_MARKET_PREDECLARATION_RESOLUTION_2026_10_22.md`

## Owner Approval Signature

**Approval Status**: APPROVED

**Name**: Prajwal Medagiri

**Role**: Project Owner

**Date**: 10/22/2026

**Signature**: PMED

**Actor ID**: PMED

**Approval**: I approve the resolution of all 6 unresolved elements and the methods defined for finalization. I acknowledge that the actual SHA-256 values will be computed at configuration freeze time and that any change to the predeclaration will require re-authorization.
