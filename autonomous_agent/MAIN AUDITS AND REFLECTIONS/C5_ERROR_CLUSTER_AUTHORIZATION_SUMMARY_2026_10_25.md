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

### 2026-10-25 OOF-projection defect fix (same A3 countersign scope)

The first three authorized rows under the steering exception
(`exp-proposal-5d1d8cf4cc6e` axis `departure_candle_direction`,
`exp-proposal-dbcb254d4212` axis `vix_regime`,
`exp-proposal-bb94a5b38792` axis `first_retest`) executed then adjudicated
REJECT with every evidence gate missing: the harness's pooled OOF frame
projection ("_keep") carried only `date/ticker/entry_date/exit_date/
spy_above_sma200`, so `_evaluate_cluster_mask` raised `Column ... not in
frame columns` on its own owner-frozen masks, the harness exited 1 before
writing `evaluation.json`, and the adapter fail-closed on missing
release evidence. Diagnosed from the durable records (adapter_events
returncode 1, ledger adjudication detail, result.json) without
fabricating anything; verified by running the exact row-1 compiled
config end-to-end (junction-replica workspace) which reproduced the exit-1
pre-fix and produced a valid 1.3.0 evaluation post-fix.

Fix (no change to any cluster definition, mask, threshold, gate, budget,
or multiplicity rule): `recipe_harness._run_pooled` now extends the OOF
projection with the selected axis's predeclared mask columns via new
helper `_cluster_axis_columns` (reads the frozen record; fail-closed to
() on unreadable/unfrozen state). New pins:
- `test_error_clustering_declaration.py::TestOofFrameMaskColumns`
  (masks columns per axis; non-axis configs add none; every predeclared
  mask column exists in the frozen event table).
- Era-pin re-pinned in `test_v2074_evidence.py`
  (`8aa32a22a6425fb6` -> `f724c33081d706e9`, dated note in-module).
Verified: junction-replica end-to-end run exit 0 with both rungs
measured; live loop post-fix: `exp-proposal-446394633420` axis
`departure_magnitude` ACCEPTED (rung 1 point 0.024960 / CI-lo 0.017289
n=37329; rung 2 point 0.009042 / CI-lo -0.010706 n=3892 -> IUT FAIL
disclosed in family_measurements) and `exp-proposal-fe3aa3a377ad` axis
`volume_confirmation` ACCEPTED with IUT PASS (rung 1 CI-lo 0.010359,
rung 2 CI-lo 0.014294).

Bookkeeping consequence (honest): the defect consumed 3 of the 5
authorized scouting rows, so axes `departure_candle_direction`,
`vix_regime`, and `first_retest` have an executed REJECT-diagnostic each
under the signed per-axis limit 1; only `departure_magnitude` and
`volume_confirmation` carry usable family measurements. Re-measuring the
three burnt axes requires a NEW owner authorization amendment (the
signature/duplicate machinery never re-fires an executed signature).

## Status

**Authorization**: COMPLETE (all 4 decisions = YES)
**Predeclaration**: FROZEN
**A3 Activation**: COMPLETE (harness 1.3.0 implemented and tested)
**Campaign 5**: Unblocked - Option A steering exception implemented and
test-pinned (see Resolution above)
**Execution**: COMPLETE - the continuous loop wound down cleanly
(`loop_stopped reason=MAX_CYCLES`, holdout untouched); all 5 authorized
error-cluster rows executed and honestly adjudicated. Inventory:
28 proposals adjudicated (10 confirmatory, 7 falsification, 8
exploration, 3 replication); `error_analysis` now shows 5 experiments
executed (2 with usable IUT evidence, 3 honest REJECT diagnostics from
the defect-burnt rows); `volume_confirmation` family PASS,
`departure_magnitude` family FAIL under the predeclared IUT.
**Era-pin**: `test_family_inventory.py::test_era_pinned_c5_reconstruction_matches_recorded_facts`
re-pinned 2026-10-25 to the post-campaign inventory (23->28, exploration
3->8, error_analysis 0->5) — the campaign-era snapshot had frozen the
pre-exception day state.

## Post-campaign verification reconciliation (2026-10-25, read-only audit)

Independently recounted against the durable records (no re-fitting, no holdout access, no re-runs of authorized axes):

1. **The two usable findings reconcile end-to-end.**
   - `exp-proposal-fe3aa3a377ad` (`volume_confirmation`): IUT **PASS** — rung 1 (`elevated_volume`, mask `relative_volume20 >= 1.0`) point 0.021100 / CI-lo 0.010359, n=18208 rows / 3335 events; rung 2 (`sub_average_volume`, mask `relative_volume20 < 1.0`) point 0.024112 / CI-lo 0.014294, n=23013 / 3457. Both rungs hold `point >= 0.0 AND ci_lower >= -0.01`; row sums 18208+23013 = 41221 match the pooled `resample_rows`. `outputs/evaluation.json` sha256 matches the `artifacts` entry in result.json; ledger shows COMPILED → EXECUTION_STARTED → GATES_PASSED → PROMOTED.
   - `exp-proposal-446394633420` (`departure_magnitude`): IUT **FAIL** — rung 1 (`large_departure`, mask `zone_departure_atr_multiple >= 1.0`) point 0.024960 / CI-lo 0.017289, n=37329 / 6087; rung 2 (`small_departure`, mask `zone_departure_atr_multiple < 1.0`) point 0.009042, **CI-lo −0.010706 < −0.01** (point 0.009042 ≥ 0.0 is fine; only the lower bound fails). The threshold −0.01 and the unrounded value are untouched; row sums 37329+3892 = 41221. Masks, floors (min_rows 50 / min_events 5, both satisfied), IUT rungs, n_boot 2000, seeds [42,43,44], folds [2023,2024,2025], and the frozen matched pair all match the FROZEN predeclaration and the compiled configs verbatim.
2. **Multiplicity accounting (fail-closed, honest).** Per **campaign end**: `stat_validation_h10/campaign_end_finalization.py --campaign-id campaign-5-regime-error-analysis-2026-10-22 --dry-run` REFUSES (MemberRecordError: the defect-era rows carry no `family_measurements` block). No C5 row exists in `state/campaign_end_multiplicity.jsonl` (only the C4 row); the declared `week_level_signflip_holm` was therefore **never executed** for the error_analysis family, and the family-wise status is **INCONCLUSIVE**, never a pass and never a formal refutation. The two consumed rows' `family_measurements` members predate the signflip-persistence fix and do **not** carry the frozen `signflip` payload — they cannot be retro-computed without re-running, which is not authorized. The live harness now persists the payload (era-pinned `be62412a0d0ca714`; `test_error_clustering_declaration.py` signs the linear-form identity), so only *future* diagnostic campaigns can produce a computable campaign-end record.
3. **The three defect-burnt rows remain unusable diagnostics.** Ledger transitions for `5d1d8cf4cc6e` / `dbcb254d4212` (`Walk-forward folds are missing…; Robustness evidence is incomplete…; Evaluation evidence is incomplete…`) and `bb94a5b38792` (`Original working tree changed during the experiment`) are recorded with `primary_delta: null` and `holdout_touched: false` — harness exit-1 receipts, not negative scientific findings. **Important reading note:** their candidate result.json files were regenerated post-fix as verification replicas (IUT PASS on `first_retest`, INCONCLUSIVE-equivalent plain runs otherwise); these are workspace diagnostics that were **never re-adjudicated** (no new ledger transitions; nothing consumed the family machinery from them). The per-axis limit of 1 for `departure_candle_direction`, `vix_regime`, and `first_retest` is **spent** in the eyes of the ledger signature/duplicate machinery; re-measuring requires a new owner authorization amendment.
4. **Stale champion-state metadata (documented, NOT rewritten):** the ledger PROMOTED the two diagnostic rows to V2.0.75/V2.0.76 before the diagnostic-promotion rule existed, so `CHAMPION.json`, `agent_state.champion`, and the `versions\V2.0.75`/`V2.0.76` snapshot directories currently name a diagnostic run (exp-proposal-fe3aa3a377ad → V2.0.76) while the frozen predeclaration's champion_rule says V2.0.74 stays the standing champion. History is preserved verbatim; the rule fix (`continuous_loop.diagnostic_promotion_outcome` + `DIAGNOSTIC_RETAINED` in `ledger.py`, pinned in `test_continuous_loop.py` and test_freeze_integrity pin `48d9f0eb`) prevents recurrence. Any champion viewer should use the frozen predeclaration + C4/C5 audit records, not these two pointers, until the owner decides whether to record a correction entry.
5. **Nothing else moved.** Config pin `29c905aa…` intact; holdout `uses=0`; no backtest/training/profitability claims added; no new ledger rows created today.

---

**Date**: 2026-10-25
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/C5_ERROR_CLUSTER_AUTHORIZATION_SUMMARY_2026_10_25.md`
