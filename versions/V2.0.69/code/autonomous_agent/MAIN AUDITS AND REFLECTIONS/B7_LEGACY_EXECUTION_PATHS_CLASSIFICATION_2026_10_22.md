# B7: Legacy Standalone Execution Paths Classification

Date: 2026-10-22
Status: CLASSIFICATION APPROVED - Documentation-only enforcement accepted
Blocker: B7 - Legacy standalone execution paths

## Background

The autonomous supervisor's signed-authorization preflight (`campaign5_authorization.py`) guards only the autonomous supervisor/loop/adapter boundaries. Legacy standalone training scripts in `study_files/backend/` and `study_files/Python/` can still be invoked directly, bypassing the authorization system.

This document classifies each legacy path as:
- **PROHIBITED**: Must not be invoked under any circumstances
- **OPERATIONALLY SEPARATED**: May be used for maintenance/diagnostics but not for research experiments
- **AUTHORIZED FOR NARROW FAIL-CLOSED CHANGES**: May be used only for specific, predeclared changes with owner authorization

## Classification of Legacy Paths

### study_files/backend/ Paths

| Path | Classification | Rationale | Restrictions |
|------|----------------|-----------|--------------|
| `demand_zone_study_v1.py` | **OPERATIONALLY SEPARATED** | V1.0.1 reconstruction harness, used by the autonomous adapter through the recipe_harness. This is the production path and should only be invoked through the adapter, not standalone. | Must not be invoked directly. All invocations must go through `experiment_adapter.ExperimentAdapter.run_experiment`. |
| `train_v2.py` | **PROHIBITED** | Historical V2 training script. V2 used different target, dataset, and validation than the frozen protocol. Invoking this would create incomparable results. | Must not be invoked. If V2 reconstruction is needed, it must be through a new adapter with separate authorization. |
| `train_v3.py` | **PROHIBITED** | Historical V3 training script. V3 used different target (alpha-SPY) and validation. Incomparable to frozen protocol. | Must not be invoked. |
| `train_v4.py` | **PROHIBITED** | Historical V4 training script. V4 used outcome-derived encodings and different target. Incomparable. | Must not be invoked. |
| `train_v5.py` | **PROHIBITED** | Historical V5 training script. V5 used near-full-sample encodings and different target. Incomparable. | Must not be invoked. |
| `train_v7.py` | **PROHIBITED** | Historical V7 training script. V7 was an ensemble approach with different target. Incomparable. | Must not be invoked. |
| `train_hold1.py` | **PROHIBITED** | Holdout training script. Holdout is SEALED and must not be accessed under any circumstances. | Must not be invoked. Holdout access requires separate authorization and is not part of C5. |
| `build_v2_dataset.py` | **PROHIBITED** | Historical V2 dataset builder. V2 dataset is not the frozen protocol dataset. | Must not be invoked. |
| `build_v3_dataset.py` | **PROHIBITED** | Historical V3 dataset builder. V3 dataset is not the frozen protocol dataset. | Must not be invoked. |
| `build_v5_dataset.py` | **PROHIBITED** | Historical V5 dataset builder. V5 dataset is not the frozen protocol dataset. | Must not be invoked. |
| `build_hold1_targets.py` | **PROHIBITED** | Holdout target builder. Holdout is SEALED. | Must not be invoked. |
| `v2_features.py` | **PROHIBITED** | Historical V2 feature definitions. Not aligned with frozen protocol. | Must not be invoked. |
| `v4_features.py` | **PROHIBITED** | Historical V4 feature definitions. Not aligned with frozen protocol. | Must not be invoked. |
| `tests/test_demand_zone_study_v1.py` | **OPERATIONALLY SEPARATED** | V1.0.1 test suite. This is the 22-test frozen study suite that must pass for all experiments. | May be invoked for verification and CI. Must not be modified without separate authorization. |

### study_files/Python/ Paths

| Path | Classification | Rationale | Restrictions |
|------|----------------|-----------|--------------|
| `generate_ml_dataset.py` | **PROHIBITED** | Historical dataset generation script. Not aligned with frozen protocol. | Must not be invoked. |
| `augment_v10_to_v11.py` | **PROHIBITED** | Historical dataset augmentation script. V10/V11/V12/V13 datasets are not the frozen protocol dataset. | Must not be invoked. |
| `augment_v11_to_v12.py` | **PROHIBITED** | Historical dataset augmentation script. | Must not be invoked. |
| `augment_v12_to_v13.py` | **PROHIBITED** | Historical dataset augmentation script. | Must not be invoked. |
| `augment_with_order_blocks.py` | **PROHIBITED** | Historical augmentation script. Order block features are now in the frozen protocol, but this script is not the authorized path. | Must not be invoked. |
| `order_block_detector.py` | **PROHIBITED** | Historical detector script. Not the authorized path for frozen protocol. | Must not be invoked. |

## Additional Considerations

### Network-Fetching Utilities

The blocker register notes that some augmentation scripts include utilities that can fetch market data. These are:
- **PROHIBITED**: No network access is permitted in the autonomous supervisor sandbox
- The sandbox network guard (`hardening.py`) blocks this for autonomous runs
- Standalone invocation would bypass this guard

### Holdout Access

Any script that references "hold1" or "holdout" is:
- **PROHIBITED**: The holdout is SEALED with uses=0
- Access requires separate authorization that has not been granted
- Access would violate the project's evidence boundary

### Version-Specific Scripts

All V2-V5/V7/V10-V13 scripts are:
- **PROHIBITED**: These historical versions used different targets, datasets, features, or validation
- Invoking them would create incomparable results
- They are part of the development history, not the frozen protocol

## Enforcement Mechanisms

To enforce these classifications, the following measures are recommended:

1. **File-System Permissions** (owner action):
   - Make PROHIBITED scripts non-executable
   - Move PROHIBITED scripts to an archive directory
   - Add filesystem-level restrictions if possible

2. **Code-Level Guards** (if owner authorizes):
   - Add guard checks at the top of each standalone script
   - Check for authorization flag before execution
   - Log all standalone invocations to an audit trail

3. **CI/CD Integration** (if applicable):
   - Prevent PROHIBITED scripts from being invoked in CI
   - Only allow OPERATIONALLY SEPARATED scripts for verification

4. **Documentation**:
   - Add comments to each script noting its classification
   - Update README to clarify which scripts are authorized

## Authorized Execution Paths

The only authorized execution path for Campaign 5 experiments is:

```
autonomous_agent.core.run
  → continuous_loop.ContinuousLoop.run
    → continuous_loop.ContinuousLoop.cycle_once
      → continuous_loop.ContinuousLoop.phase_execute_one
        → experiment_adapter.ExperimentAdapter.run_experiment
          → autonomous_agent.experiments.run_experiment
            → recipe_harness.run_from_config
              → study_files.backend.demand_zone_study_v1.py (through adapter)
```

This path is guarded by:
- Campaign 5 authorization preflight (`campaign5_authorization.py`)
- Launch gates check (`launch_gates.json`)
- All existing gates (6 promotion gates, 16 stop conditions)
- Workspace isolation
- Network guard
- Duplicate/already-asked checks

## Exceptions

If the owner determines that a specific legacy script needs to be invoked for a legitimate purpose (e.g., data maintenance, diagnostic analysis), the following must happen:

1. **Owner decision**: Explicit written authorization for the specific invocation
2. **Scope limitation**: Narrow, fail-closed scope for the change
3. **Separate authorization**: Not under the Campaign 5 authorization
4. **Audit trail**: Record the invocation and its purpose
5. **Re-authorization**: Each invocation requires separate authorization

## Status

**Classification Status**: COMPLETE
**Owner Review Required**: YES (completed)
**Implementation Status**: APPROVED - Documentation-only enforcement

## Owner Approval Signature

**Approval Status**: APPROVED

**Name**: Prajwal Medagiri

**Role**: Project Owner

**Date**: 10/22/2026

**Signature**: PMED

**Actor ID**: PMED

**Enforcement Decision**: I approve the classification of all 21 legacy scripts (20 PROHIBITED, 1 OPERATIONALLY SEPARATED). I authorize documentation-only enforcement (Option 4) as sufficient because the autonomous supervisor path is the only authorized execution path and is guarded by the authorization preflight. I acknowledge that any invocation of PROHIBITED scripts for legitimate purposes requires separate written authorization.

## Next Steps

1. ✅ **Owner reviews** this classification
2. ✅ **Owner decides** on enforcement mechanism (documentation-only approved)
3. ✅ **Owner authorizes** implementation of chosen enforcement
4. **Implementation** of documentation updates (add comments to scripts, update README)
5. **Verification** that documentation is clear and complete

**Date**: 2026-10-22
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/B7_LEGACY_EXECUTION_PATHS_CLASSIFICATION_2026_10_22.md`
