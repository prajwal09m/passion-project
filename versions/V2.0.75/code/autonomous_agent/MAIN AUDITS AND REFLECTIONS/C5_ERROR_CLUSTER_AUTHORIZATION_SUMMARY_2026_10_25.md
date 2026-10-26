# C5 Error-Cluster Authorization Summary

**Date**: 2026-10-25
**Status**: AUTHORIZED AND FROZEN
**Predeclaration**: `C5_ERROR_CLUSTER_PREDECLARATION_2026_10_25.json`

## Owner Decisions

All four decisions have been recorded as **YES**:

| Decision | Decision | Meaning |
|----------|----------|---------|
| **A1_resume** | YES | Resume the stopped Campaign 5 loop for error-clustering experiments |
| **A2_record** | YES | Freeze the predeclaration (5 axes, cluster definitions) as binding |
| **A3_activation** | YES | Approve code change to enable `error_clustering_analysis` execution |
| **A4_ledger_rows** | YES | Authorize 5 new experiment rows in the proposal ledger |

## Authorized By

- **Owner**: PMED
- **Authorized At**: 2026-10-25T00:00:00+00:00
- **Record Status**: FROZEN_2026_10_25
- **Canonical Pin (verified against the record bytes)**: `dca3e744e850d6aa7b38b477ed7352e549d5d14f5092a21cca73744487da9c2c`
- **Lineage re-pin (2026-10-25, predeclared ordering A2 freeze -> A3 activation commit -> lineage re-pin)**: `implementation_lineage.primitives.py` re-pinned to the post-activation bytes (`ce4e9844...` -> see the record) under the owner's A3=YES authorization; the earlier placeholder pin `75c65870...` in this summary was never a verified value and is corrected here.

## What This Authorizes

### Scope
- **5 error-clustering experiments** (10 experiment ceiling set by owner)
- **5 cluster definition axes**:
  1. vix_regime (high_volatility vs low_volatility)
  2. first_retest (first_retest vs subsequent_retest)
  3. volume_confirmation (elevated_volume vs sub_average_volume)
  4. departure_magnitude (large_departure vs small_departure)
  5. departure_candle_direction (bullish_departure vs bearish_or_doji_departure)

### Constraints
- **Baseline**: V2.0.74 (champion, no promotion on diagnostic runs)
- **Budget**: 5 experiments maximum (10 family members total)
- **Data**: study_v1_development_event_table only (holdout sealed)
- **Method**: week_level_signflip_holm, familywise alpha 0.05
- **Outcomes**: Honest reporting of INCONCLUSIVE/UNAVAILABLE clusters

### What Is NOT Authorized
- No holdout or prospective data access
- No trading, cost, or profitability metrics
- No changes to frozen campaign_config.json protocol_fingerprint
- No changes to duplicate policy, outcome-blindness, or holdout policy
- No champion promotion (these are diagnostics only)

## A3 Activation Implementation ✅

**Status**: COMPLETED (2026-10-25)

### Code Changes Implemented

1. **Harness version 1.3.0 added** (`recipe_harness.py`):
   - `HARNESS_VERSION_1_3_0 = "1.3.0"`
   - `V130_PRIMITIVES = {"error_clustering_analysis"}`
   - `V130_ONLY_KEYS = {"error_cluster_axis"}`

2. **Config validation updated**:
   - Accepts harness_version = "1.3.0"
   - Validates `error_cluster_axis` parameter
   - Restricts axis to predeclared set (vix_regime, first_retest, volume_confirmation, departure_magnitude, departure_candle_direction)

3. **Error-cluster collector added** (`_collect_error_cluster`):
   - Loads frozen predeclaration record
   - Validates axis is predeclared
   - Applies owner-predeclared masks to OOF frame
   - Computes per-cluster AUC deltas with moving-block bootstrap CI
   - Checks minimum sample floors (min_rows=50, min_events=5)
   - Records INCONCLUSIVE/UNAVAILABLE for undersized clusters

4. **Error-cluster evaluator added** (`evaluate_error_cluster_rungs`):
   - Intersection-union three-valued logic
   - Both rungs must satisfy: point >= 0.0 AND ci_lower >= -0.01
   - Floors enforced (min_rows=50, min_events=5)
   - Undersized/unavailable clusters are INCONCLUSIVE

5. **Primitive library version updated**:
   - `PRIMITIVE_LIBRARY_VERSION = "1.3.0"` (from 1.2.0)

6. **Primitive enabled**:
   - `error_clustering_analysis` changed from `executable=False` to `executable=True`
   - `harness_min_version = "1.3.0"`

### Verification

✅ `test_error_clustering_declaration.py`: 23/23 passed
✅ `test_campaign5_authorization.py`: 18/18 passed
✅ `test_freeze_integrity.py`: 30/30 passed
✅ `test_multiplicity.py`: 38/38 passed
✅ Total: 109 tests passed, 0 failed

## Next Steps

### Ready to Resume Campaign 5

1. **Resume Campaign 5**:
   - Continuous loop will detect frozen predeclaration
   - Execute 5 error-clustering experiments
   - Record results in proposal ledger

2. **Campaign-end**:
   - Use frozen multiplicity machinery
   - Compute Holm-adjusted p-values
   - Report per-cluster AUC deltas with bootstrap CIs

## Technical Verification

✅ Canonical pin reproduces after freeze
✅ All implementation digests match
✅ 23/23 tests pass
✅ Feasibility satisfied at m=10
✅ No outcome-informed thresholds
✅ No holdout/prospective access
✅ Budget arithmetic valid (23/45 used, 5 more fits)

## Blocker (2026-10-25, after resume attempt) - OWNER DECISION REQUIRED

The resume attempt was cleanly stopped by the loop's own predeclared
`PORTFOLIO_COMPLETE` stop: the bias governor's post-creation
falsification-share steering (frozen, T9-pinned) refuses all 5 authorized
 exploration rows (7/24 = 0.29167 < 0.30 floor) and no falsification
row remains creatable to lift the share first. The predeclaration's
budget arithmetic counted class/direction budgets but not this steering
projection. Full verified facts and decision options (A/B/C, with A
recommended) are in
`C5_FALSIFICATION_SHARE_DEADLOCK_OWNER_DECISION_REQUEST_2026_10_25.md`.
Do not relaunch until the owner decision is signed; campaign state is
durably stopped (23/45 executions used, holdout untouched).

### Resolution (2026-10-25): Option A selected and implemented

The owner selected Option A in the live chat. Implementation follows the
A3-activation template, with no change to any frozen artifact or to the
error-cluster scientific identity:
- Signed record: `C5_STEERING_EXCEPTION_DECISION_A_2026_10_25.json` +
  sha256 pin record (`...sha256`) in the same directory.
- Loader (`proposal_layer.cycle._load_c5_steering_exception`): fail-closed
  (missing record -> exception off; tampered/stale pin -> loud refusal;
  other-campaign record -> exception off).
- Governor (`bias_governor.BiasGovernor._exception_admits`): admits only
  the 5 predeclared axis signatures, exploration class, per axis 1 row,
  5 rows total, with the disclosure carried into every admission detail.
- Behavior pins: `autonomous_agent/test_c5_steering_exception.py`
  (repo record/pin integrity, scope binding, admission + disclosure,
  out-of-scope refusals, per-axis and total limits, tamper cases).

## Status

**Authorization**: COMPLETE (all 4 decisions = YES)
**Predeclaration**: FROZEN
**A3 Activation**: COMPLETE (harness 1.3.0 implemented and tested)
**Campaign 5**: Unblocked - Option A steering exception implemented and
test-pinned (see Resolution above)
**Execution**: Ready to proceed (23/45 used; the 5 diagnostic rows now
admissible under the signed exception)

---

**Date**: 2026-10-25
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/C5_ERROR_CLUSTER_AUTHORIZATION_SUMMARY_2026_10_25.md`
