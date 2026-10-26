# CAMPAIGN 2 — STAGE 2: EXECUTION AUDIT

**Date:** 2026-10-04/05 (UTC)
**Stage window (UTC):** first launch 2026-10-05T00:28:07Z → budget stop 2026-10-05T10:14:52Z; record written after post-run verification
**Operator:** autonomous agent (Buffy/Codebuff), human-authorized stage prompt
**Scope:** Execute exactly the frozen campaign's bounded experiment budget (4/4) through the real loop, real compiler, real adapter, real gates. **No holdout use, no code generation, no gate weakening, no outcome-based selection.**

Authoritative references:
- Campaign 1 frozen audit: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md` (SHA-256 `47904cb1ba0f7b58f63a3c19a3853c10d8dcf7f673e060039ac9d076cdfab3e0`)
- Stage 1 shadow audit + resolution audit (same directory)
- Pre-run snapshot: `pre_stage2_snapshot_2026_10_04.json`; post-run snapshot: `post_stage2_snapshot_2026_10_04.json`
- Frozen campaign config: `autonomous_agent/state/campaign_config.json` (SHA-256 `684a0858a972dd7756c25f8fd5f0f09594a2b5b661ace1cd53572dfa61cb1378`, sidecar verified before AND after the run)

---

## 1. PRE-FLIGHT VERIFICATION (before the first launch)

| Check | Result |
|---|---|
| Campaign config SHA + sidecar match | PASS `684a0858…1378` |
| Campaign id / budget / seed frozen | `campaign-2-stage-2-2026-10-04`, `max_total_executions: 4`, `seed_base: 20261004`, `require_human_approval: false`, approver `policy:campaign-2-stage-2-2026-10-04` |
| 26 Campaign-1 frozen hashes (audit, baseline_repro, 18 candidate spec/results, versions V2.0.1–V2.0.8) | PASS 26/26 |
| `autonomy_config.json` `663088ea…`, `SPEC_GENERATION.md` `07a5864b…` | PASS |
| `core.py` `3042f356…`, `experiment_adapter.py` `d80723d3…`, `spec_recipes.py` `be5a6291…`, `recipe_harness.py` `8bea419f…` | PASS |
| `spec_attempts.json` `13b1cb03…`, `baseline_registry.json` `f37e9667…` | PASS |
| Holdout: no holdout files anywhere; `study_files/outputs/study_v1/prospective` absent; champion `holdout_policy: SEALED, uses=0` | PASS |
| Pre-run ledger 47 rows, SHA-256 `4ceb1f85…` | PASS |
| No STOP file, no loop lock, no loop process | PASS |
| Test suites green before launch | PASS — 179 + 22 |
| Pre-run snapshot written | PASS `pre_stage2_snapshot_2026_10_04.json` |

## 2. FROZEN CONFIGURATION (unchanged throughout)

- `immutable: true`; approval mode `autonomous_revalidation` (policy `revalidate_at_approval@1.0.0`; human authorization = the stage prompt itself, approval revalidated against current ledger state with full provenance).
- `execution.max_total_executions: 4`; `execution.execution_selection: portfolio_minimums_first_then_approval_order`.
- `direction_limits.max_per_direction: 2`.
- Duplicate policy: exact fingerprint + bucketed design signature + near-duplicate text (≥0.90) + prior-campaign recipe replay + already-asked memory; budgets campaign-scoped and never weakening duplicates.
- Holdout policy: prospective never opened, never cited, never generated; `uses: 0`.
- Portfolio minimums: falsification ≥1, confirmatory ≥1.

## 3. LAUNCH TIMELINE (honest, including two non-standard starts)

| # | Time (UTC) | PID | What happened | Budget consumed |
|---|---|---|---|---|
| 1 | 00:28:07 | 131028 | Launch crashed three times with `cycle_error: cycle KeyError: 'state'` inside the cycle precheck. **The loop's own crash guard stopped it: `REPEATED_CRASHES`, status FAILED.** Defect diagnosed and fixed (`continuous_loop.py` 00:43Z, tests 00:47–00:58Z, `ledger.py` 01:05Z); both suites re-run green; pre-flight re-verified; pre-run snapshot written. **No proposals, no executions, no budget consumed** (verified: no `phase_generate` journal entry before 01:10:05Z; first campaign-2 ledger row is 01:10:05Z). | 0 |
| 2 | 01:10:05 | 30880 | Cycle 1 (seed 20261005): 3 proposals created, 3 approved. Execution #1 `exp-proposal-c834d3a14888` started 01:10:06Z. The operator's foreground tool timed out after 600 s and killed the process mid-execution. | 1 (after recovery) |
| 3 | 01:24:07 | 144152 (detached) | Crash recovery ran first: durable-result check found none, so `EXECUTED → FAILED_EXECUTION / EXECUTION_INTERRUPTED` was recorded — *"process interrupted before a durable result existed; the attempt is recorded, never silently retried"*. Cycles 2–4 then ran to the budget stop. Loop exited cleanly; lock released; run log: `{"status": "STOPPED", "stop_reason": "EXECUTION_BUDGET", "executions_done": 4, "cycles": 4}`. | (as above) |

**End state:** `loop_state.json` → `status: STOPPED`, `last_stop_reason: EXECUTION_BUDGET`, `last_error: "4/4 executed"`, `cycle: 4`, `consecutive_failures: 0`. No STOP file, no lock file, **no loop process remains** (process table contains only the pre-existing study backend).

## 4. GENERATION (outcome-blind, seeded, capacity-bounded)

| Cycle | Seed | created | approved | refused | failed validation |
|---|---|---|---|---|---|
| 1 | 20261005 | 3 | 3 | 0 | 0 |
| 2 | 20261006 | 3 | 3 | 0 | 0 |
| 3 | 20261007 | 2 | 2 | 0 | 0 |
| 4 | 20261008 | 0 | 0 | 0 | 0 |
| **Total** | | **8** | **8** | **0** | **0** |

Cycle 4 created 0 because the campaign proposal budget was already **exhausted** (`remaining_total: 0`): all four active directions at cap 2/2 (calibration, feature_engineering, model_architecture, validation), all 8 design signatures unique (`max_signature_count: 2`, observed max 1), class split falsification 4 / confirmatory 4, `falsification_share: 0.5`. The budget check runs **before** generation, so no proposal was ever created that the execution budget could not consume.

(Pre-campaign ledger content: 15 REFUSED + 1 held-at-VALIDATING proposals, all with `campaign_id: null`, all inside the frozen 47-row prefix — Stage 1 artifacts, byte-identical pre/post.)

## 5. EXECUTIONS — ALL FOUR (the complete budget)

| # | Experiment | Proposal (class / direction) | Started → Finished (UTC) | Outcome |
|---|---|---|---|---|
| 1 | `exp-proposal-c834d3a14888` | falsification / calibration | 01:10:06 → killed ~01:20 | **FAILED_EXECUTION — EXECUTION_INTERRUPTED** (no durable result; recorded, never retried; candidate workspace never created; 0 adapter commands) |
| 2 | `exp-proposal-df6e2b2b9189` | falsification / feature_engineering | 01:24:08 → 02:05:48 | **ADJUDICATED / GATES_FAILED → REJECTED** |
| 3 | `exp-proposal-d4f0556a2553` | confirmatory / model_architecture | 02:05:49 → 03:05:31 | **ADJUDICATED / GATES_PASSED → ACCEPTED → PROMOTED (V2.0.9)** at 03:14:32 |
| 4 | `exp-proposal-9aea15974ec3` | falsification / model_architecture | 03:14:33 → 10:08:31 | **ADJUDICATED / GATES_PASSED → ACCEPTED → PROMOTED (V2.0.10)** at 10:14:52 |

Execution #4 contains a wall-clock gap: no adapter or file activity between 03:14:33Z and 09:35:03Z (the host appears to have suspended; the detached process survived and the execution resumed from where it left off, completing normally). This is recorded as-is; it affected wall time only, not evidence: the attempt count, spec SHA, and gates are unchanged.

## 6. GATES, METRICS, PROVENANCE (per execution, from durable result.json)

All three adjudicated executions ran the full adapter contract: 6 gates (unit, data_integrity, leakage, walk_forward, robustness, evaluation), a temporary repository copy under `autonomous_agent/candidates/<id>/workspace` with drift rejection, written hypothesis required, no code mutation.

**#2 `df6e2b2b9189` — REJECTED (valid, unfavorable evidence; retained):**
- gates: unit PASS, data_integrity PASS, leakage PASS, walk_forward PASS, robustness PASS, **evaluation FAIL**
- primary `pooled_roc_auc_delta`: value 0.659609 vs champion 0.660322, **delta −0.000713**, moving-block-bootstrap 95% CI [−0.00334, +0.001917], `decision_criteria_passed: false`
- calibration: brier_delta +0.00012, ece_delta +7.5e-05 (degradation, not improvement)
- `artifact_sha256: null`, blockers `[]`, holdout_touched `false`, holdout_status SEALED

**#3 `d4f0556a2553` — ACCEPTED → V2.0.9:**
- gates: all 6 PASS; leakage PASS; holdout_touched `false`
- primary: value 0.684801 vs champion 0.659609, **delta +0.025192**, 95% CI [+0.010301, +0.039233] (excludes 0), criteria passed
- `artifact_sha256: c5f28f35f915babe8bbfa5cf2d862e8b57bdaff8a54fd2747f010149a6ba1ea3`

**#4 `9aea15974ec3` — ACCEPTED → V2.0.10:**
- gates: all 6 PASS; holdout_status SEALED; backtest `NOT_RUN` (trading simulation unauthorized, by design)
- primary: value 0.671896 vs 0.590078, **delta +0.081817**, 95% CI [+0.063787, +0.099227], criteria passed
- calibration improved: brier_delta −0.004225, ece_delta −0.009454; complexity_delta 0 (20 → 20 features)
- `artifact_sha256: 823e78971df7ce354fee18317d14d0d794b5651152e42423c33cdf6b68c2cd7a`, `dataset_sha256: 232de7db…`, full `artifacts` map with per-file SHA-256, `reproduction_command` recorded

Provenance chain per execution: proposal fingerprint + design signature (ledger) → spec SHA-256 (registry `attempts` + ledger COMPILED/EXECUTED rows) → candidate `result.json` with artifact tree SHA → PROMOTED ledger row + `VERSION_HISTORY.md`. Registry attempts grew 8 → 12 — exactly one entry per execution attempt, **including the interrupted one**.

## 7. SELECTION-BIAS / OUTCOME-BLINDNESS EVIDENCE

- **Selection order is fixed before outcomes exist**: `portfolio_minimums_first_then_approval_order`. Observed order: #1 c834 (cycle-1 approval), #2 df6e (cycle-1 approval), #3 d4f0 (cycle-2 approval), #4 9aea (cycle-1 approval — held until minimums satisfied, then approval order). No reordering after any result.
- **The rejection was not retried**: `df6e2b2b9189` remains ADJUDICATED/REJECTED; its direction (feature_engineering) and signature stay consumed; no variant was submitted afterward.
- **The interruption was not retried**: c834's attempt is a permanent FAILED_EXECUTION; the same experiment id never re-appears in the registry.
- **No predicted-outcome selection**: the generator produced all 8 proposals before any of them executed; cycle-4 generation returned 0 (budget exhausted) rather than tailoring proposals to the two live results.
- **Both results kept regardless of favorability**: 1 rejection and 1 interruption are preserved in ledger, research memory, and this audit.

## 8. IMmutability VERIFICATION (post-run vs pre-run snapshot)

| Artifact | Pre | Post | Verdict |
|---|---|---|---|
| 26 Campaign-1 frozen hashes | 26 match | **26 match** | UNCHANGED |
| `autonomy_config` `663088ea`, `SPEC_GENERATION` `07a5864b`, `core` `3042f356`, `adapter` `d80723d3`, `spec_recipes` `be5a6291`, `recipe_harness` `8bea419f`, `spec_attempts` `13b1cb03`, `baseline_registry` `f37e9667`, `baseline_repro` `a5c6d303` | — | **all PASS** | UNCHANGED |
| Campaign config + sidecar | `684a0858…` | `684a0858…` (sidecar recomputed match) | UNCHANGED |
| `events.jsonl` | 155 lines, `81e9a4e9…` | 155 lines, `81e9a4e9…` | UNCHANGED |
| `proposal_ledger.jsonl` | 47 rows, `4ceb1f85…` | 85 rows; **first 47 rows SHA still `4ceb1f85…`** | APPEND-ONLY (verified by prefix hash) |
| `RESEARCH_MEMORY.md` | 2009 lines, `89153807…` | 2048 lines; **first 2009 lines SHA still `89153807…`** | APPEND-ONLY |
| `CHANGELOG.md` | 270 lines, `9f5ef06c…` | 326 lines; **first 270 lines SHA still `9f5ef06c…`** | APPEND-ONLY |
| `VERSION_HISTORY.md` | 31 lines, `09ee4965…` | 35 lines; **first 31 lines SHA still `09ee4965…`** | APPEND-ONLY |
| `adapter_events.jsonl` | 39 lines | 48 lines (+3 per completed execution; 0 for the interrupted one) | GROWN as designed |
| `experiment_registry.json` | 8 attempts | 12 attempts (+1 per execution attempt) | GROWN as designed |
| `research_memory.json` / `RESEARCH_MEMORY.md` | `d3d672b5…` / `89153807…` | appended (results recorded) | GROWN as designed |
| `CHAMPION.json` | `e1624709…`, V2.0.8 | `297d5475…`, **V2.0.10** | CHANGED ONLY BY LEGITIMATE PROMOTION (2 × GATES_PASSED; `versions/V2.0.9`, `versions/V2.0.10` created; VERSION_HISTORY rows appended) |
| Lifecycle legality | — | **0 illegal transitions, 0 from-state jumps** across all 61 transitions (checked against `schema.LEGAL_TRANSITIONS`) | PASS |
| Holdout | SEALED, uses=0, no files | SEALED, uses=0, no files, `holdout_touched=false` on every adjudication, `holdout_status: SEALED` in every result | SEALED |

## 9. END-STATE ACCOUNTING

- Budget: **4/4 executed**, stop reason `EXECUTION_BUDGET` enforced *before* any further generation.
- Portfolio: minimums **met** (falsification 1, confirmatory 1), `portfolio_complete: true`; executed-by-class falsification 2 / confirmatory 1 (+1 interrupted falsification attempt).
- Approved-but-unexecuted: 4 proposals remain in `ACCEPTED_FOR_EXECUTION` (valid, never executed — the budget stopped first). They are neither deleted nor silently consumed.
- Campaign proposal budget: `remaining_total: 0`, `scheduler_exhausted: true` — the next launch would stop on budget/portfolio before generating anything.
- Champion lineage: V2.0.8 → V2.0.9 (`Parent V2.0.8`, `exp-proposal-d4f0556a2553`) → V2.0.10 (`Parent V2.0.9`, `exp-proposal-9aea15974ec3`).
- Loop artifacts: no STOP file, no lock, no loop process, run log contains the final summary JSON.

## 10. TESTS (post-run)

- `py -3 -X utf8 -m unittest autonomous_agent.test_proposal_layer autonomous_agent.test_core autonomous_agent.test_experiment_adapter autonomous_agent.test_hardening autonomous_agent.test_baseline autonomous_agent.test_spec_recipes autonomous_agent.test_recipe_harness autonomous_agent.test_stage2_campaign autonomous_agent.test_continuous_loop` → **179 tests OK** (58.8 s)
- `py -3 -X utf8 -m unittest discover -s study_files/backend/tests` → **22 tests OK** (6.7 s)

## 11. OBSERVATIONS (recorded honestly, no invariant violated)

1. **First launch crashed and was stopped by the crash guard** (§3 #1): `REPEATED_CRASHES`/FAILED did its job; zero proposals, executions, or budget consumed; defect fixed and suites re-verified before relaunch. This is the safety machinery working on a real defect, not a silent retry.
2. **`parent_version` in PROMOTED ledger rows is the proposal-declared parent** (both proposals declared V2.0.8, being what existed at generation time), while `VERSION_HISTORY.md` records the actual promotion parent (V2.0.9 for V2.0.10). Both fields are truthful in their own frame; version immutability and artifact hashes are unaffected. Flagged for Stage 3 scrutiny rather than changed here — production code was not modified during this stage.
3. **Execution #4 wall-clock gap** (§5): host suspend suspected; process survived; attempt accounting unaffected.
4. **Cycle-1 execution was operator-interrupted**, recorded as FAILED_EXECUTION/EXECUTION_INTERRUPTED, never re-run — the "attempt is recorded, never silently retried" contract held on the real repository.

## 12. VERDICT

**STAGE 2 = COMPLETE.** The frozen budget (4/4) was consumed with full provenance: 1 interruption recorded honestly, 1 rejection preserved as valid unfavorable evidence, 2 promotions (V2.0.9, V2.0.10) through all 6 gates. All frozen evidence UNCHANGED, ledger append-only with 0 illegal transitions, holdout SEALED (uses=0), selection order fixed before outcomes, campaign config untouched, suites 179 + 22 green, loop stopped itself on `EXECUTION_BUDGET` with no supervisor, lock, or STOP artifact remaining.

**Next:** Stage 3 adversarial audit (26 attacks on disposable fixture state).
