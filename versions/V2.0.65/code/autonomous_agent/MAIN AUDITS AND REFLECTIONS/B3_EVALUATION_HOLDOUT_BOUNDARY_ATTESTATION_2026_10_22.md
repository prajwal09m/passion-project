# B3: Evaluation/Holdout Boundary Attestation

Date: 2026-10-22
Status: SIGNED — All attestations completed and signed by owner
Blocker: B3 - Evaluation/holdout boundary

## Purpose

This attestation documents the data boundary, temporal splits, purge rules, and exposure history for Campaign 5. It must be completed by the owner or data steward before Campaign 5 can launch.

## Attestation Template

### Section 1: Eligible Inputs

**Input Dataset**: study_v1_development_event_table

**Dataset SHA-256**: `232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0`

**Source**: Frozen development event table from Campaign 4

**Ticker Universe**: Fixed roster of 149 tickers (as frozen in Campaign 4)

**Time Range**: 2021-08-03 to 2025-12-31 (full event table range as frozen in C4)

**Number of Events**: 61,045 candidate events (from event table)

**Data Provenance Attestation**:
- [OK ] I attest that the dataset is point-in-time complete for the stated ticker universe and time range
- [OK  ] I attest that no future data (relative to each event's timestamp) is included in features
- [OK  ] I attest that the ticker universe is fixed and survivorship risk is acknowledged
- [ OK ] I attest that any look-ahead bias is documented and addressed

**Limitations Acknowledged**:
- Fixed-universe survivorship risk exists (tickers that delisted are not represented)
- Yahoo-derived adjusted snapshots may not represent true point-in-time vendor vintages
- No independent verification of point-in-time completeness has been performed

### Section 2: Train/Validation/Sealed-Holdout Boundary

**Training Period**: All matured events before each fold start (walk-forward)

**Validation Period**: Chronological folds [2023, 2024, 2025]

**Holdout Period**: Not defined - holdout remains sealed with zero uses (no holdout evaluation in C4 or planned for C5)

**Holdout Status**: SEALED

**Holdout Uses**: 0

**Holdout Attestation**:
- [OK  ] I attest that the holdout period has never been accessed for model training, tuning, or evaluation
- [ OK ] I attest that no predictions have been made on holdout data
- [ OK ] I attest that no outcomes from the holdout period have been used in feature engineering
- [ OK ] I attest that the holdout remains sealed for Campaign 5

**Boundary Enforcement**:
- [ OK ] I attest that the boundary between development and holdout is enforced by code (holdout path never opened)
- [ OK ] I attest that the boundary is verified by the holdout policy check in launch readiness

### Section 3: Temporal/Group/Purge Rules

**Temporal Split**: Chronological walk-forward with purged folds

**Purge Rule**: Target-maturity purge (events with immature labels removed from each fold's training set)

**Purge Attestation**:
- [OK  ] I attest that the purge rule removes all events whose labels would require future data beyond the fold boundary
- [OK  ] I attest that the purge rule is applied consistently across all folds
- [ OK ] I attest that the purge rule does not leak information from validation into training

**Group Structure**: Events grouped by ticker-session (event_id is ticker_session, not zone)

**Group Attestation**:
- [ OK ] I attest that events are grouped by ticker-session to prevent multiple observations from the same time unit
- [ OK ] I attest that the group structure prevents time-series leakage within folds

### Section 4: Prior Exposure History

**Historical Experiments**:
- V1.0.1: Archived study, not reproduced from source
- V2-V10: Historical development with varying targets/datasets
- Campaign 2: 4 executions (stage-based)
- Campaign 3: 38 executions (continuous)
- Campaign 4: 30 executions (measurement-axis)

**Exposure Attestation**:
- [OK  ] I attest that the development event table has been used in prior campaigns (C2-C4)
- [ OK ] I attest that no outcomes from the development event table have been used for prospective prediction
- [ OK ] I attest that the development event table has never been used for holdout evaluation
- [OK  ] I attest that the development event table is the same frozen dataset used in C4 (SHA verified)

**Prior Exposure Risk**:
- [OK  ] I acknowledge that repeated use of the same development data may lead to overfitting
- [ OK ] I acknowledge that this risk is mitigated by the frozen protocol and predeclared gates
- [OK  ] I acknowledge that the holdout remains sealed for final validation

### Section 5: Rules on Disclosed Header-Only Staged-Fixture Read

**Staged-Fixture Definition**: A minimal fixture that contains only headers/metadata, not full data, for testing purposes

**Header-Only Read Attestation**:
- [OK  ] I attest that header-only reads are permitted for testing infrastructure
- [OK  ] I attest that header-only reads do not expose outcome data
- [OK  ] I attest that header-only reads do not violate the holdout seal
- [OK  ] I attest that any fixture with actual data (not just headers) requires separate authorization

**Fixture Policy**:
- [OK  ] I attest that test fixtures may read headers for schema validation
- [ OK ] I attest that test fixtures may not read actual event data from holdout
- [OK  ] I attest that test fixtures must be predeclared and reviewed

### Section 6: Data Lineage Verification

**Raw OHLCV Sources**: 153 Yahoo-derived CSV files (not in public checkout)

**Lineage Attestation**:
- [OK  ] I attest that the raw OHLCV sources are the same as used in V1.0.1 (verified by hash in C4 archive)
- [ OK ] I attest that the raw OHLCV sources are not included in the public checkout due to redistribution rights
- [ OK ] I attest that the event table was derived from these sources using the documented pipeline
- [OK  ] I attest that the derivation pipeline is frozen and reproducible

**Point-in-Time Validity**:
- [OK  ] I acknowledge that Yahoo-derived snapshots may not represent true point-in-time vendor vintages
- [OK  ] I acknowledge that independent verification of point-in-time validity has not been performed
- [OK  ] I acknowledge that this limitation is documented in the project's evidence boundary

### Section 7: Additional Considerations

**Network Access**:
- [OK  ] I attest that no network access is permitted during experiment execution
- [OK  ] I attest that the sandbox network guard blocks all network calls
- [OK  ] I attest that no brokerage or exchange API access is permitted

**Data Augmentation**:
- [ OK ] I attest that no data augmentation is performed on the frozen event table
- [OK  ] I attest that feature engineering is fold-local and uses only training data
- [OK  ] I attest that no look-ahead features are introduced

**Reproducibility**:
- [OK  ] I attest that the development event table is frozen and byte-identical across campaigns (SHA verified)
- [OK  ] I attest that the experimental protocol is frozen and reproducible
- [ OK ] I attest that random seeds are controlled and recorded

## Owner/Data-Steward Signature

**Attestation Status**: SIGNED

**Name**: Prajwal Medagiri

**Role**: Owner

**Date**: 10/22/2026

**Signature**: PMED

**Actor ID**: PMED

## Verification Checklist

Before Campaign 5 launch, verify:

- [OK  ] All attestations above are completed truthfully
- [OK  ] Dataset SHA-256 matches the frozen event table
- [OK  ] Holdout path does not exist or is empty
- [ OK ] Holdout policy in config shows SEALED, uses=0
- [OK  ] Purge rule is implemented in the harness
- [OK  ] No network access is enabled in the sandbox
- [OK  ] Test fixtures are header-only or use development data only

## Status

**Attestation Status**: COMPLETED AND SIGNED
**Owner Review Required**: YES (completed)
**Data-Steward Review Required**: YES (completed by owner)

**Next Steps**:
1. ✅ Owner/data-steward completes this attestation
2. ✅ Owner/data-steward signs the attestation
3. Attestation is verified before Campaign 5 launch
4. Any discrepancies must be resolved before launch

**Date**: 2026-10-22
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/B3_EVALUATION_HOLDOUT_BOUNDARY_ATTESTATION_2026_10_22.md`
