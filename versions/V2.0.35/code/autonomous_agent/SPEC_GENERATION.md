# Deterministic Recipe-Based Spec Generation (no LLM)

This document describes the autonomous `ExperimentSpec` generation layer added
in `autonomous_agent/spec_recipes.py`, and it is explicit about one thing up
front:

**There is no LLM in this system.** No language model, no model provider, and
no learned component is configured or consulted anywhere in the generation
path. "Autonomous" here means only that the supervisor can request a spec
without a human typing one. Generation is *deterministic recipe-based
template rendering* over a closed, human-reviewed recipe library.

## Deterministic recipe generation vs. LLM generation

| Property | Deterministic recipe generation (this system) | LLM generation (NOT used here) |
|---|---|---|
| Source of designs | Closed library of reviewed `Recipe` definitions in `spec_recipes.py` | A model's sampled output |
| Reproducibility | Same state ⇒ same recipe, same parameters, same spec (only the recorded timestamp differs) | Not guaranteed |
| New code | Never invented; a fixed reviewed entry-point template + a reviewed config JSON | Could synthesize arbitrary code |
| Allowlist expansion | Impossible; target files validated against `autonomous_agent/experiments/**` at recipe-validation time and again at spec-validation time | Would require trust |
| Failure mode | Refusal (`SpecGenerationRefused`) with a machine-readable reason code | Silent plausible output |
| Review surface | The recipe library is code; every change is a code review | Prompt/model changes |

If a language-model provider is ever implemented and configured, it must be a
separate, explicitly reviewed generator type; this document and the
`provenance.generator_type` field must never claim `llm` involvement without
that provider existing.

## Components

- `autonomous_agent/spec_recipes.py` — recipe library (`RECIPE_LIBRARY`),
  recipe validation (`validate_recipe` / `validated_library`), evidence
  gathering (`gather_evidence`), the deterministic provider
  (`RecipeSpecProvider`), the crash-safe attempt ledger, the
  `allow_autonomous_specs` config, and the read-only `dry-run` CLI.
- `autonomous_agent/recipe_harness.py` — the reviewed research harness that a
  generated candidate executes (`run_from_config`). Strict closed config schema
  (`validate_experiment_config`), read-only analysis of the retained
  development event table, walk-forward folds fit inside each fold, sealed
  holdout never opened, no network, no model deserialization, writes only
  `outputs/evaluation.json`.
- `autonomous_agent/autonomy_config.json` — the explicit
  `allow_autonomous_specs` flag. **Default `false`.** Missing or malformed
  config also means disabled.
- `autonomous_agent/test_recipe_harness.py` — end-to-end tests that execute the
  harness through the supervisor's real `experiment` command path
  (`python -m autonomous_agent.experiments.run_experiment` in the candidate
  workspace, scrubbed environment + network guard) against a controlled
  fixture carrying the real frozen study, the real frozen protocol and a
  deterministic sample of the real development event table. Also unit-tests
  the predeclared decision gate (`decision_criteria_pass`), including the
  calibration margins.

## Recipe library (closed)

Each recipe declares: research direction and purpose; permitted target files
(only `autonomous_agent/experiments/**`); a parameter grid (the only values
that can ever be selected); required grounding evidence; predeclared evaluation
criteria; written rejection conditions; and an attempt budget (`max_attempts`).

| Recipe | Direction | Purpose | Grid | Evidence required | Budget |
|---|---|---|---|---|---|
| `feature_arm_nested_ablation` v1.0.0 | feature_engineering | Do larger nested feature arms add OOF discrimination beyond a matched smaller arm on identical purged folds? | arm_pair ∈ {A→B, B→C, C→D}; estimator ∈ {LogisticRegression, LightGBM}; n_boot ∈ {500, 1000} | established baseline + prior findings in direction | 3 |
| `model_class_matched_comparison` v1.0.0 | model_architecture | Does model class change generalization under one fixed arm/cohort/target/folds? | arm ∈ {B, C}; n_boot ∈ {500, 1000} | established baseline + prior findings in direction | 3 |
| `calibration_stability_check` v1.0.0 | calibration | Are probability estimates stable across folds and years (Brier, ECE)? Calibration quality is **gated**: Brier must not degrade by more than +0.005 absolute and ECE by more than +0.02 absolute versus the matched reference arm | arm_pair ∈ {B→C, C→D}; estimator ∈ {LightGBM}; calibration_bins ∈ {5, 10}; n_boot ∈ {500} | established baseline + prior findings in direction | 2 |

Directions without a reviewed recipe (e.g. `target_design`, `data_quality`)
are **refused with `UNSUPPORTED`** — the library will not improvise a design.
Adding a recipe is a code change and a review event, never an automatic act.

## Provenance

Every generated spec carries `provenance`:

- `generator_type` = `deterministic_recipe` (never `llm`)
- `generator_version`, `provider`
- `recipe_id`, `recipe_version`
- `hypothesis_id` (deterministic hash of direction + question)
- `grounding_evidence` (baseline record identity + the prior findings used)
- `selected_parameters`
- `generated_at` (timestamp; the only volatile field)
- `llm_involved` = `false`

Provenance is metadata only: it is excluded from duplicate fingerprints
(`hardening.spec_fingerprint`) so it can never mask a duplicate, and the
adapter never trusts or executes it.

## Refusals (fail-closed)

The provider refuses, with reason codes: `DISABLED` (flag off), `UNSUPPORTED`
(no recipe for the hypothesis direction), `MALFORMED_RECIPE`, `MISSING_EVIDENCE`
(insufficiently grounded), `BUDGET_EXHAUSTED`, `INVALID_PARAMETERS`,
`INVALID_PARENT` (CHAMPION.json missing/unreadable/malformed or without a valid
version — the parent version is never guessed), and `DUPLICATE` (checked
against the provider's attempt ledger *and* the adapter's spec registry). A
refusal surfaces to the supervisor as an ordinary REJECTED cycle; nothing is
weakened and the loop keeps running. Refusal codes remain visible in the final
outcome and in research-memory diagnostics — the supervisor's outcome
validation preserves a meaningful `rejection_reason` instead of masking it
with the generic scientific-gates message.

All downstream protections are preserved unchanged: workspace isolation,
original-tree integrity fingerprints, input fingerprints, path allowlists and
forbidden-surface checks, leakage-token detection, holdout protection, the six
evaluation gates, duplicate-spec refusal, timeouts and process-tree
termination, crash recovery, rejection cleanup, immutable champion handling,
and promotion-time revalidation.

## Capacity and exhaustion policy

`spec_recipes.generation_capacity(root, directions)` is a read-only verdict,
derived from the closed library and the append-only attempt ledger, on which
directions can still ever yield a spec (recipe coverage + remaining attempt
budget; both properties are permanent). While autonomous generation is
enabled, the supervisor uses it to:

- never propose a permanently unsupported or out-of-budget direction while a
  viable one exists, and
- when *every* direction is spent or unsupported, enter a terminal persisted
  `research_exhausted` state: no further experiments are proposed or recorded,
  and the run loop stops instead of endlessly producing rejections.

The verdict is recomputed from the durable ledger on every cycle and at
startup, so it survives restarts and crashes. Budgets are never increased and
no safety limit is relaxed. Disabled-mode behavior is unchanged.

## Crash safety

The attempt ledger (`autonomous_agent/state/spec_attempts.json`) is written
*before* a spec is returned, so a crash can only lose a never-used spec — it
can never double-run one. An unreadable ledger fails closed (treated as
recorded attempts lost ⇒ conservative behavior via the spec registry).

## Dry-run review mode

Read-only: generates and validates proposals for every planner direction,
reports which recipes were selected and which proposals were refused and why,
and writes nothing (no attempt rows, no registry entries, no experiments, no
champion changes). Safe to run while the supervisor is live.

```bash
py -3 -m autonomous_agent.spec_recipes dry-run
py -3 -m autonomous_agent.spec_recipes show-recipes
```

## Enabling autonomous generation (after review)

1. Review the recipe library in `autonomous_agent/spec_recipes.py` and the
   harness in `autonomous_agent/recipe_harness.py` (this is the entire surface
   a generated candidate can execute).
2. Run the dry-run audit and review the report:
   `py -3 -m autonomous_agent.spec_recipes dry-run`.
3. Only after that review, edit `autonomous_agent/autonomy_config.json` and set
   `"allow_autonomous_specs": true`.
4. Restart the supervisor so it reloads the provider
   (`py -3 -m autonomous_agent.core stop`, then `py -3 -m autonomous_agent.core run`).
   Nothing enables the flag automatically.

Note: a supervisor that was started before this layer existed keeps its old
behavior until it is restarted; and even after restart, generation stays
refused while the flag is `false`.
