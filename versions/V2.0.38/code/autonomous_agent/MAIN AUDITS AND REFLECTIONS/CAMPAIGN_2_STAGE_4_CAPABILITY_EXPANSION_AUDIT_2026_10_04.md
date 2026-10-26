# Campaign 2 — Stage 4: Capability Expansion Audit

**Date:** 2026-10-04/05 (expansion implemented and analyzed 2026-10-05 UTC)
**Campaign:** `campaign-2-stage-2-2026-10-04` (frozen config, sha256 `684a0858…b1378`, unchanged)
**Stage-3 verdict relied upon:** GREEN (2 findings remediated, retested — see Stage 3 audit)
**Scope:** PART 8 inventory → PART 9 bounded deterministic primitive expansion behind the
17-point requirement matrix → PART 10 shadow-only before/after analysis → PART 11 this audit.
**Verdict: GREEN — capability expanded, all gates intact, nothing executed, no real state modified.**

---

## 1. Method and non-negotiables

- **No execution of any kind.** No experiment was compiled against the real repository, no
  adapter ran, no supervisor started, no loop started. The shadow driver
  (`autonomous_agent/stage4_shadow_analysis.py`) works exclusively in a **disposable mirror**
  built from allowlisted copies of real state; the real repository is only ever *read*.
- **Shadow-only generation:** `run_proposal_cycle` without an approver under
  `require_human_approval: true` — proposals stop at VALIDATING (awaiting approval), the
  historical Stage-1 shadow posture. The analysis campaign additionally carries
  `max_total_executions: 0`.
- **No LLM**, no free code, no arbitrary values: new capabilities are static reviewed library
  data rendered through the existing closed harness config schema.
- **Holdout:** untouched; `study_files/outputs/study_v1/prospective` absent before and after;
  champion `holdout_policy: SEALED, uses=0`.
- **Campaign config frozen:** file = sidecar = loop-state pin = `684a0858…b1378` verified
  after the stage (triple match).
- Unfavorable results are all reported, including the 6 shadow refusals (§5) and the two
  library-tracking test updates (§6).

## 2. PART 8 — Inventory of the proposal space (before)

**Library:** 9 primitives — 4 executable, 5 forward-declared (`executable=False`,
`harness_min_version="1.1.0"`).

| Primitive | Direction | Class (default) | Executable | Param grid (bounded) |
|---|---|---|---|---|
| feature_arm_comparison | feature_engineering | confirmatory | ✅ | 3 arm_pairs × 2 estimators × 2 n_boot = 12 |
| model_class_comparison | model_architecture | confirmatory | ✅ | 4 arms × 2 n_boot = 8 |
| calibration_stability_check | calibration | confirmatory | ✅ | 3 × 1 × 2 bins × 2 n_boot = 12 |
| year_stability_falsifier | validation | falsification | ✅ | 3 × 2 × 2 = 12 |
| purge_sensitivity_probe | validation | falsification | ❌ 1.1.0 | (declared, not runnable) |
| regime_split_analysis | error_analysis | exploration | ❌ 1.1.0 | (declared, not runnable) |
| complexity_reduction_check | model_complexity | confirmatory | ❌ 1.1.0 | (declared, not runnable) |
| target_horizon_robustness | target_design | exploration | ❌ 1.1.0 | (declared, not runnable) |
| point_in_time_data_audit | data_quality | exploration | ❌ 1.1.0 | (declared, not runnable) |

Gaps this stage targets (evidence-backed):

1. **Reach:** Stage 1 shadow reached only 2 of 4 executable primitives / 2 of 8 directions;
   the Stage 4 BEFORE shadow reached 3/4 primitives and 3/8 directions with
   **capacity exhausted after 12 proposals** (cycle 5 generated 0; asked-signature
   exclusions36 + recipe exclusions8 left `candidates_remaining: 0`).
2. **Classes:** no executable primitive defaults to `replication` — the replication class
   (budget exists in policy) was structurally unreachable.
3. **Acceptance margins were not a design dimension:** `_acceptance_criteria` hardcoded
   `primary_metric_min_delta = 0.0` for every primitive (only calibration carried
   brier/ece margins). "Does the gain clear a *practically meaningful* bar?" could not be asked.
4. **Seed sets were not a design dimension:** config seeds hardcoded `[42,43,44]`; a true
   independent-seed replication could not be proposed.
5. `model_complexity` had no executable primitive (its only candidate was the 1.1.0
   forward declaration).

**Not expandable without harness 1.1.0 (honestly documented):** `error_analysis`,
`target_design`, `data_quality` directions have no key in the closed harness config
(`ALLOWED_CONFIG_KEYS`) that could express regime slicing, horizon comparison, or vintage
audits. Promoting those forward declarations to `executable=True` without harness support
would be a **false capability claim** and was deliberately NOT done.

## 3. PART 9 — The expansion (3 primitives) and the 17-point requirement matrix

New file-level changes: `proposal_layer/primitives.py` (+3 entries),
`proposal_layer/compiler.py` (render support: per-parameter criteria profiles and static
seed sets, both read from the primitive's static `extra` library data and re-validated
against the harness's closed schema — unknown keys or out-of-bounds values fail closed as
`CompileError RC_SPEC_CONTRACT`).

| # | Requirement | minimum_effect_falsifier | complexity_premium_check | seed_set_replication | Enforced by |
|---|---|---|---|---|---|
| 1 | Deterministic, no LLM | PASS | PASS | PASS | test_01, test_18 |
| 2 | Bounded parameter grid | PASS 24 combos | PASS 16 combos | PASS 12 combos | test_01, test_02 |
| 3 | No free-form values (enums/ints only) | PASS | PASS | PASS | test_02, test_07–09 |
| 4 | Executable by the reviewed harness TODAY | PASS | PASS | PASS | test_03 |
| 5 | `harness_min_version` honest (`1.0.0`) | PASS | PASS | PASS | test_03, test_19 |
| 6 | Renders into the closed harness config | PASS | PASS | PASS | test_03 |
| 7 | Structural mapping only (no free content) | PASS | PASS | PASS | test_04 |
| 8 | Distinct design signature (never collides) | PASS | PASS | PASS | test_15 |
| 9 | Falsifiable rule that can genuinely fail | PASS | PASS | PASS (replication rule) | test_13 |
| 10 | Null/adverse-capable outcome | PASS | PASS | PASS | test_13 |
| 11 | Evidence-grounded (hashed allowlist citations) | PASS | PASS | PASS | test_14 |
| 12 | Holdout-blind (holdout ref → refusal) | PASS | PASS | PASS | test_12 |
| 13 | Outcome-blind selection (closed inputs) | PASS | PASS | PASS | test_14 |
| 14 | Budget/quota accounting compatible | PASS | PASS | PASS | test_16 |
| 15 | Duplicate layers compatible (fingerprint/signature/recipe-replay) | PASS | PASS | PASS | test_15 |
| 16 | Lifecycle + approval provenance → compile | PASS | PASS (same chain) | PASS (same chain) | test_17 |
| 17 | Reproducible byte-identical regeneration | PASS | PASS | PASS | test_01, test_18 |

**What each primitive is (all data, no code):**

- `minimum_effect_falsifier` (validation, default falsification): params
  `{arm_pair, estimator, n_boot, min_effect ∈ {meaningful, strong}}`; the profile maps to
  reviewed margins `primary_metric_min_delta` 0.005 / 0.01 — the gain must clear a
  practically meaningful bar, not merely be non-negative.
- `complexity_premium_check` (model_complexity, default confirmatory, falsification-capable):
  params `{arm, n_boot, premium ∈ {standard, high}}` → margin 0.005 / 0.01 — the complexer
  estimator must justify its complexity premium over LogisticRegression or the simpler model
  stands. Serves the previously-unreachable `model_complexity` direction honestly.
- `seed_set_replication` (validation, **default replication**, not falsification-capable):
  params `{arm_pair, estimator, n_boot}`, static extra `seeds: [7, 17, 29]` — the identical
  design re-run on an independent predeclared seed set (the harness genuinely consumes
  `config.seeds`: per-seed metrics + bootstrap seed).

**Adversarial points (test_07–test_11):** a free numeric margin (`min_effect: 0.5`), an
unknown profile (`"extreme"`), an unknown parameter (`margin_free`), a smuggled unknown
criterion key in profile data, and an out-of-bounds margin in profile data are each refused —
the first three at the SURFACE gate (`RC_INVALID_PARAMETER`), the profile attacks fail closed
at render (`RC_SPEC_CONTRACT`). Library data (purpose/config_note/profile notes/seeds) is
scanned for code/path shapes and contains none (two purpose strings were reworded during
development when the scan caught a semicolon and a `class <word>` pattern — the gate was
right, the text was fixed).

**Regression guarantees:** `test_05` pins the existing primitives' rendered criteria/seeds
byte-for-byte (feature_arm/model_class/year: `0.0/-0.01/min_folds 3`, seeds `[42,43,44]`;
calibration keeps `0.005/0.02` brier/ece margins); `test_19` re-verifies future (1.1.0)
primitives are still refused at compile and excluded from generation.

## 4. PART 10 — Shadow before/after (identical conditions)

Method: `py -3 -X utf8 -m autonomous_agent.stage4_shadow_analysis before|after` — builds a
disposable mirror of real state (CHAMPION, full `state/` including the real 85-row ledger,
allowlisted `versions/*/version.json|evaluation.json`, protocol, campaign audit, the 100 MB
event table; `versions/` is 19 GB and is NOT copied wholesale), attaches the analysis-only
campaign (`campaign-2-stage-4-shadow-analysis`, execution budget **0**, human approval
required, no approver → nothing approves/compiles/executes), and runs 5 bounded shadow cycles
(seeds 101–105, fixed clock). Both runs used the same mirror recipe, seeds, and policy; only
the primitive library differed. Stats: `stats_before.json` / `stats_after.json` in each run's
temp mirror (paths printed by the driver).

**The 17 evaluations, before → after:**

| # | Dimension | BEFORE (9-primitive library) | AFTER (12-primitive library) |
|---|---|---|---|
| 1 | Proposal count | **12** (capacity exhausted; cycle 5 = 0) | **15** (all 5 cycles filled; 87 candidates remain) |
| 2 | Refusals | 0 | 6 |
| 3 | Refusal reasons | — | `BIAS_QUOTA` ×6 (falsification-share floor steering) |
| 4 | Falsification share | 0.4167 ≥ 0.35 PASS | 0.4667 ≥ 0.35 PASS |
| 5 | Replication share | 0.0000 (class unreachable) | 0.0667 ≤ 0.50 PASS (class reachable) |
| 6 | Design-signature diversity | 12/12 distinct | 15/15 distinct |
| 7 | Exact duplicates in run | 0 | 0 |
| 8 | Near-duplicate refusals | 0 | 0 |
| 9 | Already-asked behavior | 24 prior proposals, statuses view-derived (identical mirror both runs) | identical |
| 10 | Campaign 1 rediscovery | 8/8 refused `DUPLICATE` | 8/8 refused `DUPLICATE` |
| 11 | Holdout references | 0 in payloads; injection → `HOLDOUT_BLIND`/`HOLDOUT_REFERENCE` | identical |
| 12 | Free-code attempts | 0 | 0 |
| 13 | Validation bypass | all 12 in VALIDATING | 9 VALIDATING + 6 REFUSED only; nothing else |
| 14 | Expected-outcome selection bias | score equal with/without predicted outcomes; closed inputs | identical |
| 15 | Quota enforcement probes | 4/4 refused (total, direction, signature, floor) | 4/4 refused |
| 16 | Genuinely different designs | 12 distinct; **3 primitives, 3 directions** (of 4 executable / 8 total) | 15 distinct; **6 primitives, 5 directions** (of 7 executable / 8 total); param span now includes margin profiles + premium + seed-set dims |
| 17 | Null/adverse-capable proposals | 12/12 carry a rule that can fail | 15/15 |

**Capability deltas (the point of the stage):**

- Executable primitives **4 → 7**; primitives actually reached in shadow **3 → 6**
  (only `year_stability_falsifier` unranked this run — ranking, not capability).
- Directions reached **3 → 5**; `model_complexity` went from unreachable to **7 proposals**;
  `validation` grew 0 → 4 (incl. 3 minimum-effect falsifiers).
- `replication` class **0 → 1** (structurally possible for the first time).
- Shadow capacity **exhausted at 12 → 87 candidates remaining after 15**: the binding limit
  returned to the declared budgets (40 proposals / per-cycle 3), not asked-signature exhaustion.
- Every safety dimension (rows 7–15, 17) is **unchanged**: 0 duplicates, 0 holdout refs,
  0 free code, outcome-blind, quota probes intact, C1 replay 8/8 refused, refusals recorded
  in the only permitted terminal states.

**Observations (documented, not silently fixed):**

- **OBS-4-1 (minor, efficiency):** the generator scores the falsification share from
  *pre-cycle* ledger state, so a batch of 3 can include confirmatory proposals that become
  `BIAS_QUOTA` refusals once recorded (6 refusals this run). This is conservative fail-closed
  behavior — refusals are recorded permanently, nothing executes, budgets still bind — the
  same family as Stage-1 OBS-2 ("never rank doomed candidates"), now with a share-aware
  dimension. Carried forward; prospective share accounting belongs to a future authorized stage.
- **OBS-4-2 (info):** `complexity_premium_check` dominates ranking when the champion's
  direction history shows a zero-acceptance direction (evidence-gap 1.0). Neutral for safety
  (closed inputs), relevant for Stage-5 cycle tuning.

## 5. Test results (post-expansion)

| Suite | Result |
|---|---|
| `autonomous_agent.test_stage4_capabilities` (new, 19 tests, the matrix of §3) | **OK — 0.9 s** |
| Full autonomous suite (179 prior + 26 Stage 3 + 19 Stage 4 = 224) | **OK — 224 tests, ~120 s** |
| Frozen `study_files/backend/tests` | **OK — 22 tests** |

Two pre-existing tests were updated because they hard-coded the old library's shape — both
updates make the tests *track the library* rather than encode a snapshot (documented here as
required; no assertion was weakened):

1. `test_t21e_all_exhausted_reports_research_exhaustion`: "one record in every executable
   direction" now samples **one payload per executable primitive derived from `LIBRARY`** and
   compares exclusions against the library-derived direction set (and the total-budget check
   against the new record count). The exhaustion properties asserted are unchanged.
2. `test_t21f_exhausted_class_budget_excluded_from_ranking`: asserted that *all* generated
   payloads were falsification — incidental to the old class set. Now asserts the actual
   property: **the capped class (confirmatory) is never ranked**, while other admissible
   classes may appear (falsification, replication). The downstream "every generated payload
   passes validation end-to-end" assertions are unchanged.

No other test changed. No production gate, budget, or approval path was relaxed; the only
production edits are the two additive render hooks in `compiler.py` (criteria profiles, seed
sets) — both fail closed through `validate_experiment_config`.

## 6. Real-repository integrity (verified after the stage)

- `campaign_config.json` sha = sidecar = loop-state pin = `684a0858a972…b1378` (triple match);
- loop state `STOPPED / EXECUTION_BUDGET / 4 of 4 / cycle 4`; no STOP file; no loop lock;
  no loop process started; ledger unchanged at **85 rows, sha `90f819d7…`** (Stage-2 post hash);
- champion `V2.0.10`, holdout absent, `holdout_policy: SEALED, uses=0`;
- git status identical to stage start (no real-state file added/modified/deleted; Stage 4
  wrote only: `primitives.py`, `compiler.py`, `test_stage4_capabilities.py`,
  `stage4_shadow_analysis.py`, two library-tracking test updates, and this audit).

## 7. Verdict and carry-forward

**STAGE 4 RESULT: PASS (GREEN).** Capability expanded by 3 bounded deterministic primitives
behind a 17-point requirement matrix, each point tested; shadow before/after proves wider
reach with every safety dimension unchanged; nothing executed; no real state modified.

Carried to Stage 5 / readiness:

1. OBS-4-1 (within-cycle share staleness → recorded refusals) and OBS-4-2 (ranking dynamics).
2. Directions `error_analysis`, `target_design`, `data_quality` remain forward-declared
   pending a reviewed harness 1.1.0 — explicitly out of Stage-4 scope (no false claims).
3. Stage-3 OBS-11 (parent_version dual-frame) and the cross-signature semantic-equivalence
   limitation remain documented.
4. The exact Stage-5 start command (NOT started) and full readiness checklist live in
   `CAMPAIGN_2_STAGE_4_FINAL_STAGE5_READINESS_AUDIT_2026_10_04.md`.

*End of Stage 4 capability expansion audit.*
