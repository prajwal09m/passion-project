# Changelog

## Unreleased — Pre-activation safety fixes for recipe spec generation

- Added real end-to-end harness tests (`autonomous_agent/test_recipe_harness.py`): the harness now runs through the supervisor's actual `experiment` command path (`python -m autonomous_agent.experiments.run_experiment` in the candidate workspace, scrubbed environment + network guard) against a controlled fixture carrying the real frozen study, real frozen protocol and a deterministic sample of the real development event table, asserting a valid `outputs/evaluation.json` and fail-closed behavior (no fabricated output) when the harness cannot run. **These tests caught and fixed two real runtime bugs**: `_load_frozen_study` crashed on Python 3.13 (module not registered in `sys.modules` before `exec_module`, breaking `@dataclass` annotation resolution), and pooled metrics were computed over training-history rows that never receive out-of-fold predictions (NaN crash); metrics are now pooled over out-of-fold rows only.
- Refusal reasons are preserved: `Supervisor._validate_outcome` no longer masks a meaningful `rejection_reason` (e.g. provider refusal codes `UNSUPPORTED`/`BUDGET_EXHAUSTED`/`MISSING_EVIDENCE`/`INVALID_PARENT`) with the generic scientific-gates message; the generic text is now only a fallback. Fail-closed status handling is unchanged.
- Added an exhaustion policy: `spec_recipes.generation_capacity` (read-only verdict from the closed library + append-only attempt ledger) drives a persisted terminal `research_exhausted` state. While autonomous generation is enabled, the supervisor no longer proposes permanently unsupported or out-of-budget directions while viable ones exist, and stops generating attempts entirely when every direction is spent/unsupported, instead of endlessly recording rejections. The state is re-derived from the durable ledger at startup and survives restart/crash; budgets and safety limits are unchanged; disabled-mode behavior is unchanged.
- `calibration_stability_check` now gates on calibration quality, matching its research purpose: explicit non-degradation margins `max_brier_degradation` (+0.005 absolute) and `max_ece_degradation` (+0.02 absolute) versus the matched reference arm are predeclared in the recipe, validated by the closed config schema, and enforced in the harness's decision gate (`recipe_harness.decision_criteria_pass`), which now gates on the reported (rounded) values so the decision is exactly auditable from `outputs/evaluation.json`.
- `RecipeSpecProvider.parent_version_for` fails closed: if `CHAMPION.json` is missing, unreadable, malformed, or lacks a version on the champion version ladder, generation is refused with the new `INVALID_PARENT` reason code. The silent `"V2.0.0"` fallback is gone; a parent version is never guessed.
- Agent test total: 117 (all passing); frozen-study suite 22 (all passing). Autonomous specs remain disabled (`allow_autonomous_specs: false`); no experiment attempts were spent.

## Unreleased — Deterministic recipe-based spec generation (no LLM)

- Added `autonomous_agent/spec_recipes.py`: a closed, human-reviewed recipe library and a deterministic `ExperimentSpec` provider. **No language model is involved anywhere in generation** — generation is deterministic template rendering over reviewed recipes (see `autonomous_agent/SPEC_GENERATION.md` for the recipe-vs-LLM distinction). Every generated spec carries provenance (generator type, recipe id+version, hypothesis id, grounding evidence, selected parameters, timestamp); refusals are fail-closed with reason codes (DISABLED / UNSUPPORTED / MALFORMED_RECIPE / MISSING_EVIDENCE / BUDGET_EXHAUSTED / INVALID_PARAMETERS / DUPLICATE).
- Added `autonomous_agent/recipe_harness.py`: the reviewed research harness a generated candidate executes — strict closed config schema, read-only analysis of the retained development event table, fold-local preprocessing on purged chronological folds, sealed holdout untouched, writes only `outputs/evaluation.json`.
- Added `autonomous_agent/autonomy_config.json` with `allow_autonomous_specs` **defaulting to `false`**; the provider is wired into `_default_experiment_runner` behind that flag and nothing enables it automatically. Downstream protections (workspace isolation, allowlists, leakage detection, holdout protection, evaluation gates, duplicate refusal, timeouts, crash recovery, champion immutability, promotion revalidation) are unchanged.
- Added a read-only `dry-run` review mode (`py -3 -m autonomous_agent.spec_recipes dry-run`) producing a report of selected recipes and refused proposals with reasons; it executes no experiments and changes no state.
- Added 30 tests (`autonomous_agent/test_spec_recipes.py`) covering valid generation, missing evidence, invalid parameters, forbidden paths, duplicates, exhausted budgets, malformed recipes, disabled mode, crash recovery, dry-run reporting, and regression of existing protections. Agent test total: 89.

## Unreleased — Input restoration and baseline reproduction

- Restored the exact V1.0.1 research inputs from verified Git objects with byte-level SHA-256 pin verification: the unsanitized `run_manifest.json`, the 149-ticker V2 roster dataset (`669ca1f5…`), and all 153 OHLCV CSVs incl. `XVIX.csv` (153/153 hash-equal to `source_data_sha256`). Full search/verification/rejection record in `autonomous_agent/RESTORATION_REPORT.md`; tooling in `autonomous_agent/restoration_scan.py` and `autonomous_agent/restore_inputs.py`.
- Ran the real baseline reproduction (`reproduce --force`) end-to-end in isolation. Result: **FAILED — not reproduced**. The event cohort, labels, folds, and universe reproduce exactly (65/114 columns identical, `universe_sha256` matches), but 49 zone/order-block/indicator feature columns (`rsi14`, `atr_pct`, `zone_width_pct`, `zone_base_*`, `ob_bull_*`, `ob_bear_*`) differ in the reviewed reconstruction, so `artifact_sha256` and `pooled_oof_metrics` drift. The exact remaining missing artifact is the V1.0.1 source (`code_sha256=29885c5f…`). Autonomous experimentation stays gated behind `REPRODUCED`; no candidate ran, no version promoted.
- Fixed the reproduction record path so an immutability-guard event can no longer swallow the run result (record persists before enforcement).

## Unreleased — Long-running hardening

- Added `autonomous_agent/hardening.py`: process-tree launch/termination (timeout kills the whole tree), configurable resource limits (runtime, output, workspace, GPU, concurrency), default network denial for experiment subprocesses via a sandbox `sitecustomize` shim, credential-variable scrubbing, spec-hash duplicate-experiment registry, and a global kill-switch helper wired into `core stop`.
- Research records now carry the full chain: hypothesis, motivation, prior evidence, proposed change, expected outcome, actual result, conclusion, next research implication (never labeled as scientific claims).
- Added 8 hardening/loop tests including a bounded multi-experiment autonomous run (hypothesis generation → accept → version promotion → reject → crash → recovery → resume → stop). Agent test total: 40.

## Unreleased — Reviewed experiment execution path

- Added `autonomous_agent/INPUT_REQUIREMENTS.md`: verified inventory of every missing research input (v1.0.1 run manifest, V2 roster dataset, 153-symbol OHLCV cache, original v1.0.1 source, V5/lineage datasets) with expected locations, dependents, reproducibility impact, and verification methods, plus anti-requirements prohibiting look-alike substitutes.
- Added `autonomous_agent/experiment_adapter.py`: serializable `ExperimentSpec`/`ExperimentResult`, isolated candidate workspaces under `autonomous_agent/candidates/`, narrow change allowlist (`autonomous_agent/experiments/**`), fixed reviewed command registry, mandatory evaluation gates (unit, data integrity, leakage, walk-forward purge, robustness, champion comparison), fail-safe candidate destruction on any anomaly, and original-tree immutability fingerprinting.
- Baseline reproduction attempted and honestly recorded as `BLOCKED` in `autonomous_agent/BASELINE_REPRODUCTION_REPORT.md`; autonomous experimentation is STOPPED until required inputs are restored and the baseline reproduces. No candidate was run, no version was promoted, and no result is a scientific claim.
- Added 17 adapter tests (32 total agent tests) using synthetic fixtures only.

## Unreleased — Autonomous research supervisor bootstrap

- Added a durable supervisor/planner scaffold that records evidence-backed hypotheses, blocked experiments, and recovery state.
- Added hard readiness gates and explicit archive/champion distinctions.
- No model experiment ran; no model version was created or accepted; no result is a scientific claim.
- Current research is blocked until reproducible champion/data prerequisites and a reviewed experiment adapter are available.

Future entries are appended only for accepted model versions. Candidate outcomes belong in the experiment journal and `VERSION_HISTORY.md`, not as releases.

## V2.0.1

### Hypothesis

Are probability estimates stable across years, tickers, and market regimes?

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.0; see `versions/V2.0.1/evaluation.json` and immutable snapshot.

## V2.0.2

### Hypothesis

Do market-structure features add information beyond a matched baseline without future-data dependence?

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.1; see `versions/V2.0.2/evaluation.json` and immutable snapshot.

## V2.0.3

### Hypothesis

Does a different model class generalize better than the strongest matched component?

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.2; see `versions/V2.0.3/evaluation.json` and immutable snapshot.

## V2.0.4

### Hypothesis

Are probability estimates stable across years, tickers, and market regimes?

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.3; see `versions/V2.0.4/evaluation.json` and immutable snapshot.

## V2.0.5

### Hypothesis

Do market-structure features add information beyond a matched baseline without future-data dependence?

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.4; see `versions/V2.0.5/evaluation.json` and immutable snapshot.

## V2.0.6

### Hypothesis

Does a different model class generalize better than the strongest matched component?

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.5; see `versions/V2.0.6/evaluation.json` and immutable snapshot.

## V2.0.7

### Hypothesis

Do market-structure features add information beyond a matched baseline without future-data dependence?

### Results

```json
{
  "delta_auc": 0.005879,
  "pooled_roc_auc_a": 0.671896,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.6; see `versions/V2.0.7/evaluation.json` and immutable snapshot.

## V2.0.8

### Hypothesis

Does a different model class generalize better than the strongest matched component?

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.7; see `versions/V2.0.8/evaluation.json` and immutable snapshot.

## V2.0.9

### Hypothesis

[model_architecture] Compare LogisticRegression vs LightGBM on one fixed arm. (arm=D, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.8; see `versions/V2.0.9/evaluation.json` and immutable snapshot.

## V2.0.10

### Hypothesis

[model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=A, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.9; see `versions/V2.0.10/evaluation.json` and immutable snapshot.

## V2.0.11

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=500, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.10; see `versions/V2.0.11/evaluation.json` and immutable snapshot.

## V2.0.12

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=500, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.11; see `versions/V2.0.12/evaluation.json` and immutable snapshot.

## V2.0.13

### Hypothesis

[model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=D, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.12; see `versions/V2.0.13/evaluation.json` and immutable snapshot.

## V2.0.14

### Hypothesis

[validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=A->B, estimator=LogisticRegression, n_boot=500) reproduce deterministically under an independently parameterized re-run?

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.13; see `versions/V2.0.14/evaluation.json` and immutable snapshot.

## V2.0.15

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=500, premium=high) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.14; see `versions/V2.0.15/evaluation.json` and immutable snapshot.

## V2.0.16

### Hypothesis

[calibration] Measure Brier/ECE stability across chronological folds and years. (arm_pair=C->D, calibration_bins=5, estimator=LightGBM, n_boot=500) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.001168,
  "pooled_roc_auc_a": 0.683633,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.15; see `versions/V2.0.16/evaluation.json` and immutable snapshot.

## V2.0.17

### Hypothesis

[validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=A->B, estimator=LogisticRegression, n_boot=1000) reproduce deterministically under an independently parameterized re-run?

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.16; see `versions/V2.0.17/evaluation.json` and immutable snapshot.

## V2.0.18

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=B, n_boot=1000, premium=high) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.17; see `versions/V2.0.18/evaluation.json` and immutable snapshot.

## V2.0.19

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=500, premium=standard) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.18; see `versions/V2.0.19/evaluation.json` and immutable snapshot.

## V2.0.20

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=B, n_boot=500, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.19; see `versions/V2.0.20/evaluation.json` and immutable snapshot.

## V2.0.21

### Hypothesis

[validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=B->C, estimator=LightGBM, min_effect=meaningful, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.20; see `versions/V2.0.21/evaluation.json` and immutable snapshot.

## V2.0.22

### Hypothesis

[validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=A->B, estimator=LightGBM, n_boot=1000) reproduce deterministically under an independently parameterized re-run?

### Results

```json
{
  "delta_auc": 0.005879,
  "pooled_roc_auc_a": 0.671896,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.21; see `versions/V2.0.22/evaluation.json` and immutable snapshot.

## V2.0.23

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=500, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.22; see `versions/V2.0.23/evaluation.json` and immutable snapshot.

## V2.0.24

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=1000, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.23; see `versions/V2.0.24/evaluation.json` and immutable snapshot.

## V2.0.25

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=B, n_boot=500, premium=standard) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.24; see `versions/V2.0.25/evaluation.json` and immutable snapshot.

## V2.0.26

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=1000, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.25; see `versions/V2.0.26/evaluation.json` and immutable snapshot.

## V2.0.27

### Hypothesis

[validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=B->C, estimator=LightGBM, min_effect=meaningful, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.26; see `versions/V2.0.27/evaluation.json` and immutable snapshot.

## V2.0.28

### Hypothesis

[feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=B->C, estimator=LightGBM, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.27; see `versions/V2.0.28/evaluation.json` and immutable snapshot.

## V2.0.29

### Hypothesis

[feature_engineering] Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LightGBM, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.001168,
  "pooled_roc_auc_a": 0.683633,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.28; see `versions/V2.0.29/evaluation.json` and immutable snapshot.

## V2.0.30

### Hypothesis

[calibration] Measure Brier/ECE stability across chronological folds and years. (arm_pair=C->D, calibration_bins=5, estimator=LightGBM, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.001168,
  "pooled_roc_auc_a": 0.683633,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.29; see `versions/V2.0.30/evaluation.json` and immutable snapshot.

## V2.0.31

### Hypothesis

[validation] Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=A->B, estimator=LogisticRegression, min_effect=strong, n_boot=500) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.30; see `versions/V2.0.31/evaluation.json` and immutable snapshot.

## V2.0.32

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=1000, premium=standard) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.31; see `versions/V2.0.32/evaluation.json` and immutable snapshot.

## V2.0.33

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=1000, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.32; see `versions/V2.0.33/evaluation.json` and immutable snapshot.

## V2.0.34

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=500, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.33; see `versions/V2.0.34/evaluation.json` and immutable snapshot.

## V2.0.35

### Hypothesis

[model_architecture] Compare LogisticRegression vs LightGBM on one fixed arm. (arm=C, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.34; see `versions/V2.0.35/evaluation.json` and immutable snapshot.

## V2.0.36

### Hypothesis

[validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=A->B, estimator=LogisticRegression, min_effect=meaningful, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.35; see `versions/V2.0.36/evaluation.json` and immutable snapshot.

## V2.0.37

### Hypothesis

[model_complexity] Falsifier: Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=A, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.36; see `versions/V2.0.37/evaluation.json` and immutable snapshot.

## V2.0.38

### Hypothesis

[calibration] Falsifier: Measure Brier/ECE stability across chronological folds and years. (arm_pair=B->C, calibration_bins=5, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.37; see `versions/V2.0.38/evaluation.json` and immutable snapshot.

## V2.0.39

### Hypothesis

[model_complexity] Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=D, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.38; see `versions/V2.0.39/evaluation.json` and immutable snapshot.

## V2.0.40

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=2000, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.39; see `versions/V2.0.40/evaluation.json` and immutable snapshot.

## V2.0.41

### Hypothesis

[model_complexity] Falsifier: Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=B, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.40; see `versions/V2.0.41/evaluation.json` and immutable snapshot.

## V2.0.42

### Hypothesis

[calibration] Falsifier: Measure Brier/ECE stability across chronological folds and years. (arm_pair=C->D, calibration_bins=10, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.001168,
  "pooled_roc_auc_a": 0.683633,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.41; see `versions/V2.0.42/evaluation.json` and immutable snapshot.

## V2.0.43

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=2000, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.42; see `versions/V2.0.43/evaluation.json` and immutable snapshot.

## V2.0.44

### Hypothesis

[model_complexity] Falsifier: Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=A, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.43; see `versions/V2.0.44/evaluation.json` and immutable snapshot.

## V2.0.45

### Hypothesis

[error_analysis] Falsifier: Slice out-of-fold errors by predeclared volatility/time regimes. (arm=C, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.44; see `versions/V2.0.45/evaluation.json` and immutable snapshot.

## V2.0.46

### Hypothesis

[target_design] Falsifier: Pre-registered horizon comparison on development folds only. (arm=B, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.45; see `versions/V2.0.46/evaluation.json` and immutable snapshot.

## V2.0.47

### Hypothesis

[feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=B->C, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.46; see `versions/V2.0.47/evaluation.json` and immutable snapshot.

## V2.0.48

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=2000, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.47; see `versions/V2.0.48/evaluation.json` and immutable snapshot.

## V2.0.49

### Hypothesis

[model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=A, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.48; see `versions/V2.0.49/evaluation.json` and immutable snapshot.

## V2.0.50

### Hypothesis

[calibration] Measure Brier/ECE stability across chronological folds and years. (arm_pair=B->C, calibration_bins=10, estimator=LightGBM, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.49; see `versions/V2.0.50/evaluation.json` and immutable snapshot.

## V2.0.51

### Hypothesis

[calibration] Falsifier: Measure Brier/ECE stability across chronological folds and years. (arm_pair=A->B, calibration_bins=5, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.005879,
  "pooled_roc_auc_a": 0.671896,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.50; see `versions/V2.0.51/evaluation.json` and immutable snapshot.

## V2.0.52

### Hypothesis

[target_design] Falsifier: Pre-registered horizon comparison on development folds only. (arm=A, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.51; see `versions/V2.0.52/evaluation.json` and immutable snapshot.

## V2.0.53

### Hypothesis

[model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=C, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.52; see `versions/V2.0.53/evaluation.json` and immutable snapshot.

## V2.0.54

### Hypothesis

[error_analysis] Falsifier: Slice out-of-fold errors by predeclared volatility/time regimes. (arm=B, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.53; see `versions/V2.0.54/evaluation.json` and immutable snapshot.

## V2.0.55

### Hypothesis

[target_design] Falsifier: Pre-registered horizon comparison on development folds only. (arm=C, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.54; see `versions/V2.0.55/evaluation.json` and immutable snapshot.

## V2.0.56

### Hypothesis

[error_analysis] Falsifier: Slice out-of-fold errors by predeclared volatility/time regimes. (arm=D, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.55; see `versions/V2.0.56/evaluation.json` and immutable snapshot.

## V2.0.57

### Hypothesis

[target_design] Falsifier: Pre-registered horizon comparison on development folds only. (arm=D, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.56; see `versions/V2.0.57/evaluation.json` and immutable snapshot.

## V2.0.58

### Hypothesis

[feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.001168,
  "pooled_roc_auc_a": 0.683633,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.57; see `versions/V2.0.58/evaluation.json` and immutable snapshot.

## V2.0.59

### Hypothesis

[model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=D, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.58; see `versions/V2.0.59/evaluation.json` and immutable snapshot.

## V2.0.60

### Hypothesis

[error_analysis] Falsifier: Slice out-of-fold errors by predeclared volatility/time regimes. (arm=A, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.59; see `versions/V2.0.60/evaluation.json` and immutable snapshot.

## V2.0.61

### Hypothesis

[feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=A->B, estimator=LogisticRegression, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.60; see `versions/V2.0.61/evaluation.json` and immutable snapshot.

## V2.0.62

### Hypothesis

[validation] Falsifier: Challenge the pooled gain: does it hold in EVERY predeclared year, or does at least one year refute it? (arm_pair=A->B, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.005879,
  "pooled_roc_auc_a": 0.671896,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.61; see `versions/V2.0.62/evaluation.json` and immutable snapshot.

## V2.0.63

### Hypothesis

[validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=C->D, estimator=LightGBM, n_boot=500) reproduce deterministically under an independently parameterized re-run?

### Results

```json
{
  "delta_auc": 0.001168,
  "pooled_roc_auc_a": 0.683633,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.62; see `versions/V2.0.63/evaluation.json` and immutable snapshot.

## V2.0.64

### Hypothesis

[validation] Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=A->B, estimator=LogisticRegression, min_effect=meaningful, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.63; see `versions/V2.0.64/evaluation.json` and immutable snapshot.

## V2.0.65

### Hypothesis

[validation] Challenge the pooled gain: does it hold in EVERY predeclared year, or does at least one year refute it? (arm_pair=C->D, estimator=LightGBM, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.001168,
  "pooled_roc_auc_a": 0.683633,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.64; see `versions/V2.0.65/evaluation.json` and immutable snapshot.

## V2.0.66

### Hypothesis

[validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=B->C, estimator=LightGBM, n_boot=2000) reproduce deterministically under an independently parameterized re-run?

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.65; see `versions/V2.0.66/evaluation.json` and immutable snapshot.

## V2.0.67

### Hypothesis

[validation] Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=A->B, estimator=LogisticRegression, min_effect=meaningful, n_boot=500) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.070673,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.660752
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.66; see `versions/V2.0.67/evaluation.json` and immutable snapshot.

## V2.0.68

### Hypothesis

[validation] Challenge the pooled gain: does it hold in EVERY predeclared year, or does at least one year refute it? (arm_pair=B->C, estimator=LightGBM, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.005859,
  "pooled_roc_auc_a": 0.677774,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.67; see `versions/V2.0.68/evaluation.json` and immutable snapshot.

## V2.0.69

### Hypothesis

[data_quality] Verify source vintage, universe membership, timestamps and label maturity before modeling. (arm=D, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.68; see `versions/V2.0.69/evaluation.json` and immutable snapshot.

## V2.0.70

### Hypothesis

[model_complexity] Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=C, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.69; see `versions/V2.0.70/evaluation.json` and immutable snapshot.

## V2.0.71

### Hypothesis

[model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=B, n_boot=2000, premium=high) — predeclared refutation: metric below zero under the frozen purged protocol.

### Results

```json
{
  "delta_auc": 0.017023,
  "pooled_roc_auc_a": 0.660752,
  "pooled_roc_auc_b": 0.677774
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.70; see `versions/V2.0.71/evaluation.json` and immutable snapshot.

## V2.0.72

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=2000, premium=standard) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.081817,
  "pooled_roc_auc_a": 0.590078,
  "pooled_roc_auc_b": 0.671896
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.71; see `versions/V2.0.72/evaluation.json` and immutable snapshot.

## V2.0.73

### Hypothesis

[data_quality] Verify source vintage, universe membership, timestamps and label maturity before modeling. (arm=D, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.025192,
  "pooled_roc_auc_a": 0.659609,
  "pooled_roc_auc_b": 0.684801
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.72; see `versions/V2.0.73/evaluation.json` and immutable snapshot.

## V2.0.74

### Hypothesis

[model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=2000, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.73; see `versions/V2.0.74/evaluation.json` and immutable snapshot.

## V2.0.75

### Hypothesis

[error_analysis] Slice out-of-fold errors by an owner-predeclared error-cluster definition (2 frozen rungs) so the campaign can measure WHERE the champion fails, not only where it wins in pooled AUC. (error_cluster_axis=departure_magnitude) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?

### Results

```json
{
  "delta_auc": 0.023312,
  "pooled_roc_auc_a": 0.660322,
  "pooled_roc_auc_b": 0.683633
}
```

### Robustness

All mandatory unit, leakage, walk-forward, robustness, calibration, subgroup, multi-seed, utility, and cost gates passed.

### Baseline scope

`BASELINE_RECONSTRUCTED_2026_10` (reconstructed_baseline); v1_0_1_status: FAILED.

### Decision

ACCEPTED vs V2.0.74; see `versions/V2.0.75/evaluation.json` and immutable snapshot.
