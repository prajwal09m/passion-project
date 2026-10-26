# Campaign 5 Real-Data Integration Test Status

Date: 2026-10-22
Author: Project Owner
Status: DOCUMENTATION OF PRIOR STATUS + C5 REQUIREMENTS

## Campaign 4 Real-Data Integration Test Status

### What Was Prepared

A predeclaration for a real-data integration test was drafted in `stat_validation_h10/C4_REAL_DATA_INTEGRATION_PREDECLARATION.md` (2026-10-17). This document included:

- Fingerprints for development inputs and code
- Prohibitions (no Campaign 5 launch, no holdout access, etc.)
- Expected checks (C1-C9)
- Persistence and consumption path
- Budget and disposable-output isolation

### What Was NOT Done

The real-data integration test was **NOT EXECUTED** for Campaign 4. The predeclaration states clearly:

> Owner authorization for execution: **NOT GRANTED.**
> Owner signature / date: **[pending — to be completed only by the owner]**

### Why It Was Not Executed

The C4 readiness report (`C4_NEXT_STAGE_READINESS_REPORT.md`) identified:

1. **Unresolved configuration**: The single configuration under test was not selected
2. **Unresolved entry point**: The exact invocation was not specified
3. **Unresolved expectations**: Exact member identifiers, counts, week-alignment, and tolerances were not recorded
4. **Unresolved holdout boundary**: The dataset's sealed-holdout boundary was not verified

### Campaign 4 Family Measurements

Campaign 4's campaign-end multiplicity record shows that many family members were marked "unavailable":
- Regime family: 24 members, many unavailable
- Horizon family: 36 members, many unavailable  
- Purge family: 36 members, many unavailable
- Complexity family: 12 members, many unavailable

This was expected and documented - the measurement wiring for Campaign 4 was incomplete.

## Campaign 5 Requirements

### Decision: Real-Data Integration Test REQUIRED for Campaign 5

**Decision**: Campaign 5 requires a completed real-data integration test before launch. The following must be satisfied:

### Prerequisites Before Test Execution

1. **Owner Authorization**: Explicit written owner authorization recorded in an append-only record
2. **Configuration Selection**: A single frozen configuration must be selected and pinned before execution
3. **Entry Point Specification**: The exact command invocation must be recorded
4. **Expectations Documented**: Exact member identifiers, counts, week-alignment rules, and tolerances must be cited from the frozen record
5. **Holdout Boundary Verified**: The owner must confirm the development files contain no holdout rows

### Test Execution Requirements

1. **Disposable Workspace**: Test must run in a disposable workspace, never against `autonomous_agent/state/`
2. **No Campaign Launch**: Must not launch Campaign 5 or any campaign
3. **No Budget Consumption**: Must not consume or decrement campaign execution budget
4. **No Persistent State Changes**: Must not write to persistent campaign state
5. **Holdout Protection**: Must not access, open, query, or evaluate on the sealed prospective holdout
6. **Network Disabled**: Must run with network guard (sandbox environment)
7. **Evidence Capture**: Before/after hashes, execution logs, and check results must be recorded

### Expected Deliverables

After test execution, the following must be produced:

1. **Execution Log**: Full command text, exit status, runtime
2. **Evidence Hashes**: Before/after hashes of protected artifacts
3. **Check Results**: Independent calculations for C1-C9 with computing-script hashes
4. **Disposable Workspace Listing**: File list and hashes
5. **State Verification**: Proof that `autonomous_agent/state/` was unchanged
6. **Pass/Fail Determination**: Clear statement of pass/fail with reasons

### If Test Fails

If the real-data integration test fails:
- Campaign 5 is **BLOCKED** until the failure is resolved
- No manual override or "good enough" exception is permitted
- The failure must be investigated, fixed, and the test re-run with a new predeclaration

## Relationship to Campaign 4

Campaign 4's incomplete family measurements do not invalidate Campaign 4's results:
- Campaign 4 completed its 30-execution target successfully
- The multiplicity method was adopted and frozen
- Family measurements were a secondary objective, not the primary validation

However, Campaign 5 cannot proceed without addressing the integration test gap:
- The measurement infrastructure must be verified end-to-end
- Campaign 5 may have different measurement requirements
- A passing integration test provides confidence in the production path

## Authorization

This status document documents the prior state and sets requirements for Campaign 5.

**Status**: INTEGRATION TEST NOT EXECUTED FOR C4, REQUIRED FOR C5
**Signed by**: Project Owner
**Date**: 2026-10-22
**Evidence path**: `stat_validation_h10/C5_REAL_DATA_INTEGRATION_STATUS_2026_10_22.md`
