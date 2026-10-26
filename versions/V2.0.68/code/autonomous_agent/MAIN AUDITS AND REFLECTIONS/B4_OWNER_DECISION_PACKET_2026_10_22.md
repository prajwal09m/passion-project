# B4: Owner Decision Packet - Campaign 5 Authorization

Date: 2026-10-22
Status: SIGNED - Owner decision packet completed and signed
Blocker: B4 - Written owner authorization

## Owner Decision Packet

This document contains the owner's decisions for Campaign 5 authorization. It addresses every item required by the blocker register: scope, digests, permitted/prohibited operations, expiry/revocation.

### Section 1: Scope Decision

**Campaign Option Selected**: Option D - Regime/Error Analysis

**Campaign ID**: `campaign-5-regime-error-analysis-2026-10-22`

**Research Objective**: Deepen regime and error analysis work from Campaign 4 to understand when and why the model fails, with emphasis on falsification and explanatory results.

**Protocol Basis**: Campaign 4 (`campaign-4-continuous-2026-10-14`, SHA: `b4ced0e00493f7636efc74baee2424146cb1840233d2b48fda1061b8d50d86b4`)

**Parent Champion**: V2.0.61

**Execution Budget**: 45 executions

**Proposal Budget**: 60 proposals

**Class Budgets**:
- Confirmatory: 12
- Exploration: 16
- Falsification: 24
- Replication: 8

**Scope Decision**: APPROVED for Option D with the above parameters.

### Section 2: Digests

**Protocol Digest (SHA-256)**: TO_BE_COMPUTED from frozen C5 configuration

**Scope Digest (SHA-256)**: TO_BE_COMPUTED from frozen scope object

**Predeclaration Digest (SHA-256)**: TO_BE_COMPUTED from `CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md`

**Data Boundary Digest (SHA-256)**: TO_BE_COMPUTED from `CAMPAIGN_5_DATA_BOUNDARY_2026_10_22.json`

**Dataset Digests**:
- study_v1_development_event_table: `232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0`
- study_v1_development_oof_predictions: `011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829`

**Digest Decision**: APPROVED subject to computation of frozen digests at configuration freeze time.

### Section 3: Permitted Operations

**Permitted Model Operations**:
- Read-only analysis of development event table
- Fold-local preprocessing on purged chronological folds
- Model training on training folds only
- Out-of-fold prediction on validation folds
- Calibration analysis on OOF predictions
- Regime split analysis (predeclared regime definitions)
- Error clustering analysis (no label snooping)
- Multiplicity testing with week_level_signflip_holm

**Permitted Data Operations**:
- Read operations on permitted datasets only
- Feature computation within training folds only
- Bootstrap resampling for confidence intervals
- Sign-flip resampling for multiplicity testing
- No writes to persistent state except outputs/evaluation.json

**Permitted Candidate Operations**:
- Generate proposals via deterministic recipe-based generation
- Validate proposals against closed schema
- Execute approved proposals in isolated workspaces
- Destroy candidate workspaces on rejection or non-acceptance

**Permitted Operations Decision**: APPROVED as listed above.

### Section 4: Prohibited Operations

**Prohibited Model Operations**:
- Any training or evaluation on holdout data
- Any network access for data fetching
- Any brokerage or exchange API access
- Any operation that bypasses the sandbox network guard
- Any operation that modifies frozen artifacts
- Any operation that writes to holdout path

**Prohibited Data Operations**:
- Write operations on development event table
- Access to any dataset not in permitted list
- Access to raw OHLCV files (not in permitted list)
- Any data augmentation beyond fold-local preprocessing

**Prohibited Candidate Operations**:
- LLM-assisted proposal generation (llm_involved must remain false)
- Execution of proposals not approved through the normal validation path
- Direct invocation of standalone training scripts (see B7 classification)
- Any operation that bypasses duplicate/already-asked checks

**Prohibited Operations Decision**: APPROVED as listed above.

### Section 5: Expiry and Revocation

**Authorization Expiry**: 2026-12-31T23:59:59Z

**Revocation Conditions**:
- Holdout is accessed without separate authorization
- Network access is detected in experiment execution
- Any prohibited operation is detected
- Integrity violation (artifact hash mismatch, ledger corruption)
- Independent reviewer withdrawal
- Owner decision to revoke (explicit written record)

**Revocation Process**:
- Owner writes revocation record with reason and timestamp
- Revocation record is appended to `autonomous_agent/state/campaign5_authorization_revocations.jsonl`
- Continuous loop checks revocation ledger on each cycle
- If revoked, loop stops immediately with REVOKED status

**Expiry/Revocation Decision**: APPROVED with expiry 2026-12-31 and revocation conditions as listed.

### Section 6: Prerequisites

**Independent Statistical Review**:
- [X] Owner accepted AI review in lieu of independent reviewer (B2 signed)
- [X] Review completed with written approval (H10_C5_AI_REVIEW_2026_10_22.md)
- [X] Review addresses 9 questions from H-10 packet
- [X] Risk acceptance documented (C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md)
- Note: Owner explicitly accepted AI review with full risk acknowledgment per C5_STATISTICAL_REVIEW_RESOLUTION_2026_10_22.md

**Reviewer Engagement for Authorization**:
- [ ] Reviewer actor ID provided (C5_REVIEWER_ACTOR_ID)
- [ ] Reviewer HMAC key provided (C5_REVIEWER_HMAC_KEY)
- [ ] Reviewer distinct from owner (owner actor ID ≠ reviewer actor ID)
- [ ] Reviewer will sign authorization record
- Note: Reviewer role is key-holding and authorization signature only; statistical review already completed via AI per B2

**Real-Data Integration Test**:
- [ ] Integration test completed successfully - DEFERRED (not authorized)
- [ ] All checks C1-C9 passed - DEFERRED
- [ ] Test results documented - DEFERRED
- [ ] Data boundary verified - DEFERRED
- Note: Real-data integration test requires separate owner authorization and is not part of C5 scope

**Evaluation/Holdout Boundary Attestation**:
- [X] B3 attestation completed by owner/data-steward
- [X] All attestations completed truthfully (27 attestations)
- [X] Holdout seal verified (SEALED, uses=0)
- [X] Purge rules verified

**Legacy Execution Path Classification**:
- [X] B7 classification reviewed and approved
- [X] Enforcement mechanism implemented (documentation-only)
- [X] All prohibited scripts marked as such (20 PROHIBITED, 1 OPERATIONALLY SEPARATED)

**Prerequisites Decision**: APPROVED subject to real-data integration test being deferred (requires separate authorization if needed in future).

### Section 7: Additional Constraints

**No Prospective Outcomes**:
- This authorization does NOT permit accessing the sealed holdout for any purpose
- This authorization does NOT permit making prospective predictions
- This authorization does NOT permit evaluating on real-market data

**No Trading Simulation**:
- This authorization does NOT permit profitability or backtesting experiments
- This authorization does NOT permit any connection to brokerage or exchange APIs
- This authorization is for research and development only, not for trading

**No LLM Assistance**:
- This authorization requires `llm_involved: false` throughout
- No LLM-based proposal generation is permitted
- No LLM-based hypothesis drafting is permitted

**Champion Integrity**:
- The dual comparison rule from C4 must be preserved
- Champion regressions must be recorded with `champion_regression: true`
- No silent replacement of a better absolute scorer

**Additional Constraints Decision**: APPROVED as listed above.

### Section 8: Owner Signature

**Owner Name**: Prajwal Medagiri

**Owner Role**: Project Owner

**Decision**: APPROVE Campaign 5 Option D (Regime/Error Analysis) subject to all prerequisites and constraints listed above.

**Date**: 10/22/2026

**Signature**: PMED

**Actor ID**: PMED

**HMAC Key Commitment**: I will provide a 32+ byte hex HMAC key via environment variable C5_OWNER_HMAC_KEY.

## Verification Checklist

Before Campaign 5 launch, verify:

- [X] All sections of this decision packet are completed
- [X] Owner signature is present
- [X] Owner actor ID is provided (PMED)
- [X] Owner HMAC key is provisioned (C5_OWNER_HMAC_KEY in .env)
- [X] All prerequisites (Section 6) are completed (real-data integration test deferred)
- [X] Independent statistical review is approved (AI review accepted with risk acknowledgment)
- [X] Reviewer actor ID is provided (C5_REVIEWER_ACTOR_ID=KMED in .env)
- [X] Reviewer HMAC key is provisioned (C5_REVIEWER_HMAC_KEY in .env)
- [X] Reviewer distinct from owner verified (KMED ≠ PMED)
- [X] .env file is populated with all four values
- [X] .env file is in .gitignore (security check)
- [ ] Real-data integration test passed (deferred - requires separate authorization)
- [X] Evaluation/holdout attestation completed
- [X] Legacy execution path classification implemented
- [ ] Authorization record is created with all digests computed (requires config freeze)
- [ ] Authorization record is signed by owner and reviewer (requires config freeze + signatures)

## Status

**Decision Packet Status**: COMPLETED PENDING OWNER SIGNATURE
**Owner Signature Required**: YES
**Independent Reviewer Signature Required**: YES (separate document)

**Next Steps**:
1. Owner reviews and signs this decision packet
2. Owner provides actor ID and HMAC key
3. Owner engages independent statistical reviewer
4. Reviewer completes review and signs
5. All prerequisites are completed
6. Authorization record is created with both signatures
7. Campaign 5 configuration is frozen
8. Campaign 5 launch proceeds if all checks pass

**Date**: 2026-10-22
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/B4_OWNER_DECISION_PACKET_2026_10_22.md`
