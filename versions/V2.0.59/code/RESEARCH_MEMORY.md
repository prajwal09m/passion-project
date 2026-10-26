# Research Memory

This is the durable human-readable companion to `autonomous_agent/state/research_memory.json`. Update it when evidence changes. A historical metric is not a scientific discovery, a paper claim, or a validated version by itself.

## Spec generation: deterministic recipes, not LLM generation

The autonomous experiment-spec layer (`autonomous_agent/spec_recipes.py`) generates `ExperimentSpec` proposals **deterministically from a closed, human-reviewed recipe library**. No language model, no model provider, and no learned component is configured or consulted in generation; `provenance.generator_type` is always `deterministic_recipe` and `llm_involved` is always `false`. Any future LLM-based generator would be a separate, explicitly reviewed generator type and must never be conflated with this one. Recipes declare their research direction and purpose, permitted target files (`autonomous_agent/experiments/**` only), parameter ranges, required grounding evidence, predeclared evaluation criteria, and rejection conditions; unsupported, ungrounded, out-of-budget, invalid-parameter, and duplicate proposals are refused fail-closed. Autonomous generation is controlled by `allow_autonomous_specs` in `autonomous_agent/autonomy_config.json`, **default `false`**; a dry-run audit (`py -3 -m autonomous_agent.spec_recipes dry-run`) reviews proposals without executing anything. Full documentation: `autonomous_agent/SPEC_GENERATION.md`.

## Current status

- **CHAMPION: NONE VALIDATED.** V1.0.1 is an internally consistent archive but not reproduced from its original source; scoped feature parity failed. V1.0.2 is a frozen protocol, not an executed version. V2–V10 do not provide a matched reproducible ladder.
- No prospective outcomes exist. The final holdout is sealed and unavailable for iterative selection.
- The V2 roster dataset (sha `669ca1f5…`) and the historical 153-symbol OHLCV set (incl. `XVIX.csv`) were restored byte-exactly from verified Git objects on 2026-10-02 (see `autonomous_agent/RESTORATION_REPORT.md`); the V10 ZIP remains a non-substitute. The real baseline reproduction was run and **did not reproduce**: the cohort/labels/folds/universe match exactly, but the reviewed reconstruction computes `rsi14`, `atr_pct`, `zone_width_pct` and the zone-base/order-block features differently (the documented parity failure), so archived artifact hashes and metrics drift. The single remaining blocker is the V1.0.1 source (`code_sha256=29885c5f…`).
- The project has known risk areas: full-data median imputation before temporal split in the local legacy trainer; broad feature inference; historical use of outcome-derived encodings; forward benchmark/return alignment; fixed-universe survivorship; retrospective/non-point-in-time market data; target maturity and overlap; and unmatched evaluations.
- No brokerage capability is permitted. No network download or old pipeline execution is allowed by default.

## Evidence ledger

Use these classifications for future records:

- **EXPERIMENT** — one isolated candidate run; may fail or be blocked. Never a paper claim.
- **VERSION** — accepted, reproducible candidate with all gates passed, immutable artifacts and a parent champion.
- **RESEARCH DISCOVERY** — evidence-backed general lesson supported by reproducible analysis; include scope and uncertainty.
- **PAPER CLAIM** — requires deliberate scientific review and evidence appropriate to its wording; never inferred automatically from a metric or agent decision.

| Topic | Durable finding | Evidence strength | Action |
|---|---|---|---|
| V1.0.1 archive integrity | Saved event/label/OOF identities and point metrics were consistent with archived records; hashes matched. | Archive-only audit; not source reproduction. | Preserve archive as immutable historical evidence; do not claim independent reproduction. |
| Historical source parity | Exact v1.0.1 source was not recovered; all 480 scoped AAL rows differed for `rsi14`, `atr_pct`, and `zone_width_pct`. | Explicit scoped audit. | Treat reconstruction outputs as a different implementation until validated. |
| Confidence intervals | Archived bootstrap intervals did not reproduce with reconstructed helper. | Audit explicitly says root cause unknown. | Do not quote as independently reproduced uncertainty bounds. |
| Prospective evidence | Zero prospective predictions/outcomes. | Protocol/archive status. | Keep holdout sealed; no historical backfill as prospective data. |
| Version comparability | V2–V10 vary target, cohort, feature set, and/or validation method. | History/documentation inspection. | Only matched protocol comparisons may support an improvement decision. |
| AUC vs utility | V2 reports walk-forward AUC ~0.676 but negative simulation PF ~0.97 and Sharpe ~-0.16; broad V6 pipeline also weak. | Historical reports, not fresh audit. | Report predictive metrics and realistic backtests separately; never infer profitability from AUC. |
| Leakage | V9/V10 lineage removed forward outcome fields, but the local legacy trainer still imputes using all rows before splitting and broadly infers features. | Source review. | No legacy training command may be invoked without a fold-local preprocessing and explicit feature allowlist audit. |
| Point-in-time data | Yahoo-derived adjusted snapshots and fixed roster do not establish point-in-time vendor vintages or universe membership. | Archive closeout. | Treat survivorship/revision risks as unresolved blockers for broad claims. |
| Network and trading | Dataset augmentation includes utilities that can fetch market data; repository is research-only. | Source-tree review and user mandate. | No network access, brokerage integration, real-money trades, or implicit execution of historical pipeline scripts. |

## Prioritization and stagnation

The planner should first remove validity/data blockers. Once a reproducible matched baseline exists, diversify among data quality, validation, features, calibration, error analysis, model complexity, target design, and architecture. At five consecutive candidate rejections/failures, turn on stagnation mode and prefer methodological/target/data/model-class questions over minor tuning. Blocked cycles do not count as model rejections or releases.

## Future entry template

Append entries in `autonomous_agent/state/research_memory.json` with at least:

```json
{
  "experiment_id": "exp-...",
  "direction": "validation",
  "status": "REJECTED | ACCEPTED | BLOCKED | FAILED",
  "question": "...",
  "evidence": {"artifact_sha256": "...", "scope": "..."},
  "lesson": "...",
  "scientific_claim": false
}
```

Do not mark evidence permanent based on a single failed or blocked candidate. Do not change the frozen protocol or paper automatically.

## BLOCKED exp-b8a2d60ffcc0 — 2026-10-02T15:16:26+00:00

- **Direction:** data_quality
- **Question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Lesson:** Prerequisite failure or adapter result recorded; no scientific conclusion.
- **Scientific claim:** No

## BLOCKED exp-bbd6e04f0f03 — 2026-10-02T19:08:11+00:00

- **Direction:** data_quality
- **Question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Lesson:** Prerequisite failure or adapter result recorded; no scientific conclusion.
- **Scientific claim:** No

## REJECTED exp-ddc04a338c83 — 2026-10-03T23:24:35+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** ['no prior experiments in this direction']
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-2cc1c0b41b31 — 2026-10-03T23:30:16+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** ['no prior experiments in this direction']
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-59b4deea06cc — 2026-10-03T23:35:22+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** ['no prior experiments in this direction']
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-a8bb2465ec53 — 2026-10-03T23:40:29+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** ['no prior experiments in this direction']
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-93e4a2601e97 — 2026-10-03T23:45:35+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** ['no prior experiments in this direction']
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-79c31b924ca1 — 2026-10-03T23:51:28+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** ['no prior experiments in this direction']
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-9d67e07b00ab — 2026-10-03T23:56:39+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** ['no prior experiments in this direction']
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-f93f0f63af91 — 2026-10-04T00:01:49+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** ['no prior experiments in this direction']
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e1c5558296be — 2026-10-04T00:06:59+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-ddc04a338c83', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e8a348b38712 — 2026-10-04T00:12:09+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-2cc1c0b41b31', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-bbfe0012bdb0 — 2026-10-04T00:17:19+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-79c31b924ca1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-6e3ce182cc6d — 2026-10-04T00:22:28+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-59b4deea06cc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-c3961989dd06 — 2026-10-04T00:27:38+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-9d67e07b00ab', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e84eddb93345 — 2026-10-04T00:32:48+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-a8bb2465ec53', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-342bb2faaa0f — 2026-10-04T00:37:58+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-93e4a2601e97', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-660a188640d9 — 2026-10-04T00:43:08+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-f93f0f63af91', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-cae96dd2aadb — 2026-10-04T00:48:18+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-ddc04a338c83', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e1c5558296be', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-9a7cdb9c9fc7 — 2026-10-04T00:53:27+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-2cc1c0b41b31', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e8a348b38712', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-3f589c056757 — 2026-10-04T00:58:37+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-79c31b924ca1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-bbfe0012bdb0', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-41aaae3a92e1 — 2026-10-04T01:03:47+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-59b4deea06cc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6e3ce182cc6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-293988c18290 — 2026-10-04T01:08:56+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-9d67e07b00ab', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-c3961989dd06', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-1459c482701b — 2026-10-04T01:14:08+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-a8bb2465ec53', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e84eddb93345', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-79a345c3d529 — 2026-10-04T01:19:13+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-93e4a2601e97', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-342bb2faaa0f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-9497c175e10a — 2026-10-04T01:24:19+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-f93f0f63af91', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-660a188640d9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-758cbcc7cae2 — 2026-10-04T01:29:26+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-ddc04a338c83', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e1c5558296be', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-cae96dd2aadb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-4fae64eda58f — 2026-10-04T01:34:33+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-2cc1c0b41b31', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e8a348b38712', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-9a7cdb9c9fc7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-fb41e42d383e — 2026-10-04T01:39:39+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-79c31b924ca1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-bbfe0012bdb0', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-3f589c056757', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-89c4d7b8abf8 — 2026-10-04T01:44:48+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-59b4deea06cc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6e3ce182cc6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-41aaae3a92e1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-91e3b78c3e52 — 2026-10-04T01:49:58+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-9d67e07b00ab', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-c3961989dd06', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-293988c18290', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-c825e715189a — 2026-10-04T01:55:08+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-a8bb2465ec53', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e84eddb93345', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1459c482701b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e9763da58b6d — 2026-10-04T02:00:18+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-93e4a2601e97', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-342bb2faaa0f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-79a345c3d529', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-1982513ed3a7 — 2026-10-04T02:05:28+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-f93f0f63af91', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-660a188640d9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-9497c175e10a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-8b593f752c6d — 2026-10-04T02:10:37+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-e1c5558296be', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-cae96dd2aadb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-758cbcc7cae2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-4d2c7a4255b0 — 2026-10-04T02:15:48+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-e8a348b38712', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-9a7cdb9c9fc7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4fae64eda58f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-ea738a0d36c4 — 2026-10-04T02:20:58+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-bbfe0012bdb0', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-3f589c056757', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-fb41e42d383e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-6da1498f0572 — 2026-10-04T02:26:07+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-6e3ce182cc6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-41aaae3a92e1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-89c4d7b8abf8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-490d94ee8e05 — 2026-10-04T02:31:18+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-c3961989dd06', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-293988c18290', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-91e3b78c3e52', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e0a950e90ecf — 2026-10-04T02:36:28+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-e84eddb93345', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1459c482701b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-c825e715189a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e265e9c5aa22 — 2026-10-04T02:41:38+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-342bb2faaa0f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-79a345c3d529', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e9763da58b6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-caac2029abe8 — 2026-10-04T02:46:48+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-660a188640d9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-9497c175e10a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1982513ed3a7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-134b74ab7877 — 2026-10-04T02:51:58+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-cae96dd2aadb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-758cbcc7cae2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-8b593f752c6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-c59b1064da24 — 2026-10-04T02:57:07+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-9a7cdb9c9fc7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4fae64eda58f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4d2c7a4255b0', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-d5f38363f66b — 2026-10-04T03:02:17+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-3f589c056757', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-fb41e42d383e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ea738a0d36c4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-cef620aaa955 — 2026-10-04T03:07:27+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-41aaae3a92e1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-89c4d7b8abf8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6da1498f0572', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-0251af2ed5f9 — 2026-10-04T03:12:37+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-293988c18290', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-91e3b78c3e52', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-490d94ee8e05', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-ff4821a821a5 — 2026-10-04T03:17:47+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-1459c482701b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-c825e715189a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e0a950e90ecf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-902668042d1b — 2026-10-04T03:22:57+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-79a345c3d529', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e9763da58b6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e265e9c5aa22', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-f0800a42ecd6 — 2026-10-04T03:28:07+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-9497c175e10a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1982513ed3a7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-caac2029abe8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-93e2b9c19a14 — 2026-10-04T03:33:18+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-758cbcc7cae2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-8b593f752c6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-134b74ab7877', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-69cd72e3572a — 2026-10-04T03:38:27+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-4fae64eda58f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4d2c7a4255b0', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-c59b1064da24', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-ab1d190eaa02 — 2026-10-04T03:43:37+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-fb41e42d383e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ea738a0d36c4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d5f38363f66b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-b01c0dabffef — 2026-10-04T03:48:46+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-89c4d7b8abf8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6da1498f0572', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-cef620aaa955', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-dba78a5b626d — 2026-10-04T03:53:56+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-91e3b78c3e52', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-490d94ee8e05', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-0251af2ed5f9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-a5a313448bfd — 2026-10-04T03:59:06+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-c825e715189a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e0a950e90ecf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ff4821a821a5', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-724afb5b1a0b — 2026-10-04T04:04:16+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-e9763da58b6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e265e9c5aa22', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-902668042d1b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-af16ec95e31f — 2026-10-04T04:09:26+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-1982513ed3a7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-caac2029abe8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-f0800a42ecd6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-9c045b45be73 — 2026-10-04T04:14:36+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-8b593f752c6d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-134b74ab7877', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-93e2b9c19a14', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e658ab449a95 — 2026-10-04T04:19:48+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-4d2c7a4255b0', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-c59b1064da24', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-69cd72e3572a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-56d5ba246006 — 2026-10-04T04:24:58+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-ea738a0d36c4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d5f38363f66b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ab1d190eaa02', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-a738070a70e3 — 2026-10-04T04:30:08+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-6da1498f0572', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-cef620aaa955', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-b01c0dabffef', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-053d9e27eedc — 2026-10-04T04:35:22+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-490d94ee8e05', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-0251af2ed5f9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-dba78a5b626d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-2794a25e0ed9 — 2026-10-04T04:40:32+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-e0a950e90ecf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ff4821a821a5', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a5a313448bfd', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-f377033c471c — 2026-10-04T04:45:42+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-e265e9c5aa22', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-902668042d1b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-724afb5b1a0b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-85c37f91506e — 2026-10-04T04:50:51+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-caac2029abe8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-f0800a42ecd6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-af16ec95e31f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-16253638b3eb — 2026-10-04T04:56:02+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-134b74ab7877', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-93e2b9c19a14', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-9c045b45be73', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-d78946083d12 — 2026-10-04T05:01:12+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-c59b1064da24', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-69cd72e3572a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e658ab449a95', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-eca023eb3b23 — 2026-10-04T05:06:22+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-d5f38363f66b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ab1d190eaa02', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-56d5ba246006', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-647aa58c8d11 — 2026-10-04T05:11:32+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-cef620aaa955', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-b01c0dabffef', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a738070a70e3', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-f2aa99a978dc — 2026-10-04T05:16:42+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-0251af2ed5f9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-dba78a5b626d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-053d9e27eedc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-4ddfaf5b082a — 2026-10-04T05:21:51+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-ff4821a821a5', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a5a313448bfd', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-2794a25e0ed9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-5b34deed49ab — 2026-10-04T05:27:02+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-902668042d1b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-724afb5b1a0b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-f377033c471c', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-d41148d01587 — 2026-10-04T05:32:12+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-f0800a42ecd6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-af16ec95e31f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-85c37f91506e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-bfc2cc1c49fd — 2026-10-04T05:37:22+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-93e2b9c19a14', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-9c045b45be73', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-16253638b3eb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-8f7e49f64070 — 2026-10-04T05:42:32+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-69cd72e3572a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e658ab449a95', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d78946083d12', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-6f6f8c0a88ca — 2026-10-04T05:47:42+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-ab1d190eaa02', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-56d5ba246006', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-eca023eb3b23', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-4407c777208b — 2026-10-04T05:52:58+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-b01c0dabffef', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a738070a70e3', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-647aa58c8d11', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-1a142614abb8 — 2026-10-04T05:58:11+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-dba78a5b626d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-053d9e27eedc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-f2aa99a978dc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-d64290b4fcc9 — 2026-10-04T06:03:24+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-a5a313448bfd', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-2794a25e0ed9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4ddfaf5b082a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-6dfe35ea6725 — 2026-10-04T06:08:36+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-724afb5b1a0b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-f377033c471c', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-5b34deed49ab', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-6ba076d7088e — 2026-10-04T06:13:49+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-af16ec95e31f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-85c37f91506e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d41148d01587', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-8aea6c8dce03 — 2026-10-04T06:19:01+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-9c045b45be73', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-16253638b3eb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-bfc2cc1c49fd', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-1292213d8eae — 2026-10-04T06:24:14+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-e658ab449a95', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d78946083d12', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-8f7e49f64070', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-2376162a45a2 — 2026-10-04T06:29:27+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-56d5ba246006', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-eca023eb3b23', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6f6f8c0a88ca', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-41345cafee46 — 2026-10-04T06:34:39+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-a738070a70e3', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-647aa58c8d11', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4407c777208b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-ed09a1ab5bfe — 2026-10-04T06:39:53+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-053d9e27eedc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-f2aa99a978dc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1a142614abb8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-a8e389158e63 — 2026-10-04T06:45:06+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-2794a25e0ed9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4ddfaf5b082a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d64290b4fcc9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-dace72adf4b6 — 2026-10-04T06:50:19+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-f377033c471c', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-5b34deed49ab', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6dfe35ea6725', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-54f9b6347ef8 — 2026-10-04T06:55:32+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-85c37f91506e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d41148d01587', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6ba076d7088e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e54d04ea1fc9 — 2026-10-04T07:00:45+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-16253638b3eb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-bfc2cc1c49fd', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-8aea6c8dce03', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-839279559d1d — 2026-10-04T07:05:57+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-d78946083d12', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-8f7e49f64070', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1292213d8eae', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-797dfd315f8a — 2026-10-04T07:11:10+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-eca023eb3b23', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6f6f8c0a88ca', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-2376162a45a2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-06c73d45375f — 2026-10-04T07:16:24+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-647aa58c8d11', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4407c777208b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-41345cafee46', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-ebb3291a0ea8 — 2026-10-04T13:52:35+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-f2aa99a978dc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1a142614abb8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ed09a1ab5bfe', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-a87fb6db993b — 2026-10-04T13:57:43+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-4ddfaf5b082a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d64290b4fcc9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a8e389158e63', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-069dc24511ad — 2026-10-04T14:02:52+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-5b34deed49ab', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6dfe35ea6725', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-dace72adf4b6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-4660f78257cb — 2026-10-04T14:07:59+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-d41148d01587', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6ba076d7088e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-54f9b6347ef8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-ae394cf241c1 — 2026-10-04T14:13:03+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-bfc2cc1c49fd', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-8aea6c8dce03', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e54d04ea1fc9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e9bb7fd63454 — 2026-10-04T14:18:10+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-8f7e49f64070', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1292213d8eae', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-839279559d1d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-bbfdb7d4a119 — 2026-10-04T14:23:18+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-6f6f8c0a88ca', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-2376162a45a2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-797dfd315f8a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-2361fec03cec — 2026-10-04T14:28:24+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-4407c777208b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-41345cafee46', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-06c73d45375f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-fd1991d4a6aa — 2026-10-04T14:33:31+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-1a142614abb8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ed09a1ab5bfe', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ebb3291a0ea8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-03fe96a7d490 — 2026-10-04T14:38:37+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-d64290b4fcc9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a8e389158e63', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a87fb6db993b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-22dfb638dc91 — 2026-10-04T14:43:43+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-6dfe35ea6725', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-dace72adf4b6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-069dc24511ad', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-72b84cb09daf — 2026-10-04T14:48:50+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-6ba076d7088e', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-54f9b6347ef8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4660f78257cb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-76a007f58c0a — 2026-10-04T14:53:55+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-8aea6c8dce03', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e54d04ea1fc9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ae394cf241c1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-2f48eb7be6f1 — 2026-10-04T14:59:01+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-1292213d8eae', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-839279559d1d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e9bb7fd63454', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-75fead57dee9 — 2026-10-04T15:04:07+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-2376162a45a2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-797dfd315f8a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-bbfdb7d4a119', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-6caea1c8ea0f — 2026-10-04T15:09:14+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-41345cafee46', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-06c73d45375f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-2361fec03cec', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-19966dd824d1 — 2026-10-04T15:14:19+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-ed09a1ab5bfe', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ebb3291a0ea8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-fd1991d4a6aa', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-abf02af2c600 — 2026-10-04T15:19:25+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-a8e389158e63', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a87fb6db993b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-03fe96a7d490', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-35487736e4f2 — 2026-10-04T15:24:30+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-dace72adf4b6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-069dc24511ad', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-22dfb638dc91', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-067df296c032 — 2026-10-04T15:29:37+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-54f9b6347ef8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4660f78257cb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-72b84cb09daf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-b232feecd6f7 — 2026-10-04T15:34:47+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-e54d04ea1fc9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ae394cf241c1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-76a007f58c0a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-806e216a226a — 2026-10-04T15:39:57+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-839279559d1d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e9bb7fd63454', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-2f48eb7be6f1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-62db01047782 — 2026-10-04T15:45:06+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-797dfd315f8a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-bbfdb7d4a119', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-75fead57dee9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-8dd0faa1aa55 — 2026-10-04T15:50:16+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-06c73d45375f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-2361fec03cec', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6caea1c8ea0f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-5e0b10e04bf4 — 2026-10-04T15:55:26+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-ebb3291a0ea8', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-fd1991d4a6aa', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-19966dd824d1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-b38e4a59c7a4 — 2026-10-04T16:00:36+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-a87fb6db993b', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-03fe96a7d490', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-abf02af2c600', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-a553ef6429e6 — 2026-10-04T16:05:46+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-069dc24511ad', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-22dfb638dc91', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-35487736e4f2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-75c6812cd939 — 2026-10-04T16:10:56+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-4660f78257cb', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-72b84cb09daf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-067df296c032', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-60e9c56811d6 — 2026-10-04T16:16:06+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-ae394cf241c1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-76a007f58c0a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-b232feecd6f7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-bbe92dfd0818 — 2026-10-04T16:21:16+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-e9bb7fd63454', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-2f48eb7be6f1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-806e216a226a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-ac71d3fdc87f — 2026-10-04T16:26:32+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-bbfdb7d4a119', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-75fead57dee9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-62db01047782', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-9cf5bcb3160a — 2026-10-04T16:31:43+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-2361fec03cec', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-6caea1c8ea0f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-8dd0faa1aa55', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-d0fc3a9a9dbf — 2026-10-04T16:36:53+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-fd1991d4a6aa', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-19966dd824d1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-5e0b10e04bf4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-b41179b94871 — 2026-10-04T16:42:03+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-03fe96a7d490', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-abf02af2c600', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-b38e4a59c7a4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-64687df9eaf2 — 2026-10-04T16:47:12+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-22dfb638dc91', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-35487736e4f2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a553ef6429e6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-df3a00a3ccb7 — 2026-10-04T16:52:26+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-72b84cb09daf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-067df296c032', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-75c6812cd939', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-1dc7934ca7fc — 2026-10-04T16:57:35+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-76a007f58c0a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-b232feecd6f7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-60e9c56811d6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-095cff483424 — 2026-10-04T17:02:45+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-2f48eb7be6f1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-806e216a226a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-bbe92dfd0818', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-201bd407b301 — 2026-10-04T17:07:56+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-75fead57dee9', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-62db01047782', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ac71d3fdc87f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-4bb499c55158 — 2026-10-04T17:13:06+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-6caea1c8ea0f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-8dd0faa1aa55', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-9cf5bcb3160a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-3d716c3ef86d — 2026-10-04T17:18:11+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-19966dd824d1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-5e0b10e04bf4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d0fc3a9a9dbf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-e508513127a2 — 2026-10-04T17:23:17+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-abf02af2c600', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-b38e4a59c7a4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-b41179b94871', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-4d8618855917 — 2026-10-04T17:28:27+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** Are errors concentrated by time, ticker, volatility regime, or prediction confidence?
- **Motivation:** The project has substantial history, but current audited artifacts do not establish robust error slices.
- **Prior evidence:** [{'experiment_id': 'exp-35487736e4f2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-a553ef6429e6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-64687df9eaf2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Build error slices from strictly out-of-fold predictions and predeclared subgroup definitions.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'error_analysis' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-fd573e609f40 — 2026-10-04T17:33:46+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** Can the model be simplified without sacrificing stable out-of-sample performance?
- **Motivation:** The historical generation sequence changes targets, features, and validation, preventing a reliable complexity comparison.
- **Prior evidence:** [{'experiment_id': 'exp-067df296c032', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-75c6812cd939', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-df3a00a3ccb7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Run a matched ablation with identical cohort, target, folds, and multiple fixed seeds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-7df918e0cc93 — 2026-10-04T17:38:57+00:00

- **Direction:** data_quality
- **Hypothesis / question:** Are the available inputs point-in-time and complete enough for a valid comparison?
- **Motivation:** Historical audit records missing source data, fixed-universe survivorship risk, and no prospective outcomes.
- **Prior evidence:** [{'experiment_id': 'exp-b232feecd6f7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-60e9c56811d6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-1dc7934ca7fc', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Verify source vintage, universe membership, timestamps, and target maturity before modeling.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'data_quality' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-593e242ef739 — 2026-10-04T17:44:03+00:00

- **Direction:** validation
- **Hypothesis / question:** Would stronger purging and independent time-block inference change the ranking of feature arms?
- **Motivation:** The archived bootstrap bounds were not reproduced and the reconstruction differs from archived features.
- **Prior evidence:** [{'experiment_id': 'exp-806e216a226a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-bbe92dfd0818', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-095cff483424', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Reproduce the frozen chronological folds with target-maturity purge and block-level uncertainty.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-67847a5cd9c1 — 2026-10-04T17:49:13+00:00

- **Direction:** target_design
- **Hypothesis / question:** Does the target horizon encode an objective that remains useful after realistic costs and maturity rules?
- **Motivation:** V2–V10 used different target definitions and AUC alone does not establish utility or profitability.
- **Prior evidence:** [{'experiment_id': 'exp-62db01047782', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-ac71d3fdc87f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-201bd407b301', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** First pre-register a horizon comparison on development folds; keep final holdout sealed and report simulation separately.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'target_design' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-12b1f60fef45 — 2026-10-04T17:54:17+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-8dd0faa1aa55', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-9cf5bcb3160a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4bb499c55158', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED exp-0045e0603f56 — 2026-10-04T17:59:27+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-5e0b10e04bf4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-d0fc3a9a9dbf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-3d716c3ef86d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; One or more mandatory scientific gates did not PASS.
- **Conclusion:** One or more mandatory scientific gates did not PASS.
- **Next research implication:** Direction 'model_architecture' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED exp-853a0b9e2520 — 2026-10-04T18:16:51+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-b38e4a59c7a4', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-b41179b94871', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e508513127a2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005859; decision_criteria_passed=True
- **Conclusion:** Candidate result recorded; review detailed evaluation artifacts.
- **Next research implication:** Build on accepted direction 'calibration' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED exp-41b8ce05bda2 — 2026-10-04T18:41:35+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-9cf5bcb3160a', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4bb499c55158', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-12b1f60fef45', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.070673; decision_criteria_passed=True
- **Conclusion:** Candidate result recorded; review detailed evaluation artifacts.
- **Next research implication:** Build on accepted direction 'feature_engineering' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED exp-667edcb5c26e — 2026-10-04T18:56:31+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-d0fc3a9a9dbf', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-3d716c3ef86d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-0045e0603f56', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.017023; decision_criteria_passed=True
- **Conclusion:** Candidate result recorded; review detailed evaluation artifacts.
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED exp-26bd4111e923 — 2026-10-04T19:11:35+00:00

- **Direction:** calibration
- **Hypothesis / question:** Are probability estimates stable across years, tickers, and market regimes?
- **Motivation:** Historical reports emphasize discrimination; prospective calibration and drift evidence are absent.
- **Prior evidence:** [{'experiment_id': 'exp-b41179b94871', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-e508513127a2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-853a0b9e2520', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}]
- **Proposed change:** Evaluate calibration and subgroup reliability on untouched chronological research folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005859; decision_criteria_passed=True
- **Conclusion:** Candidate result recorded; review detailed evaluation artifacts.
- **Next research implication:** Build on accepted direction 'calibration' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED exp-98fca9f79724 — 2026-10-04T19:27:48+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-4bb499c55158', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-12b1f60fef45', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-41b8ce05bda2', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.070673; decision_criteria_passed=True
- **Conclusion:** Candidate result recorded; review detailed evaluation artifacts.
- **Next research implication:** Build on accepted direction 'feature_engineering' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED exp-44e6aefe7902 — 2026-10-04T19:43:48+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-3d716c3ef86d', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-0045e0603f56', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-667edcb5c26e', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.017023; decision_criteria_passed=True
- **Conclusion:** Candidate result recorded; review detailed evaluation artifacts.
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED exp-21602e076136 — 2026-10-04T20:02:46+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** Do market-structure features add information beyond a matched baseline without future-data dependence?
- **Motivation:** The archive reports a small C-minus-B AUC delta, but feature parity failed and attribution is not established.
- **Prior evidence:** [{'experiment_id': 'exp-12b1f60fef45', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-41b8ce05bda2', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-98fca9f79724', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}]
- **Proposed change:** Compare nested feature arms on identical events, fit all transforms inside each fold, and audit time alignment.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005879; decision_criteria_passed=True
- **Conclusion:** Candidate result recorded; review detailed evaluation artifacts.
- **Next research implication:** Build on accepted direction 'feature_engineering' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED exp-3bbc4266814d — 2026-10-04T20:57:13+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** Does a different model class generalize better than the strongest matched component?
- **Motivation:** Historical architecture results are not comparable across changing datasets and labels.
- **Prior evidence:** [{'experiment_id': 'exp-0045e0603f56', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-667edcb5c26e', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-44e6aefe7902', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}]
- **Proposed change:** Compare model classes under one fixed cohort, target, feature contract, and chronological folds.
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Candidate result recorded; review detailed evaluation artifacts.
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-df6e2b2b9189 — 2026-10-05T02:05:48+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LogisticRegression, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'exp-41b8ce05bda2', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-98fca9f79724', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-21602e076136', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=-0.000713; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-d4f0556a2553 — 2026-10-05T03:14:32+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** [model_architecture] Compare LogisticRegression vs LightGBM on one fixed arm. (arm=D, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_architecture
- **Prior evidence:** [{'experiment_id': 'exp-667edcb5c26e', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-44e6aefe7902', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-3bbc4266814d', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.9
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-9aea15974ec3 — 2026-10-05T10:14:52+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** [model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=A, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_architecture
- **Prior evidence:** [{'experiment_id': 'exp-44e6aefe7902', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-3bbc4266814d', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'prop-d4f0556a2553', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.9'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.10
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-a965e420e11b — 2026-10-05T21:42:15+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=C->D, estimator=LogisticRegression, min_effect=meaningful, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'exp-bbe92dfd0818', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-095cff483424', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-593e242ef739', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=-0.000713; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-50a88b8ff482 — 2026-10-05T23:01:02+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=500, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'exp-75c6812cd939', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-df3a00a3ccb7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-fd573e609f40', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.11
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-5af6fb3fd11f — 2026-10-06T00:31:56+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=500, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'exp-df3a00a3ccb7', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-fd573e609f40', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'prop-50a88b8ff482', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.11'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.12
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-7b2f1a05d315 — 2026-10-06T11:03:25+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** [model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=D, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_architecture
- **Prior evidence:** [{'experiment_id': 'exp-3bbc4266814d', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'prop-d4f0556a2553', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.9'}, {'experiment_id': 'prop-9aea15974ec3', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.10'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.13
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-40a65b7c37d5 — 2026-10-06T13:03:45+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=A->B, estimator=LogisticRegression, n_boot=500) reproduce deterministically under an independently parameterized re-run?
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'exp-095cff483424', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-593e242ef739', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'prop-a965e420e11b', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.070673; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.14
- **Next research implication:** Build on accepted direction 'validation' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-004b9efe173c — 2026-10-06T14:51:37+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=500, premium=high) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'exp-fd573e609f40', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'prop-50a88b8ff482', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.11'}, {'experiment_id': 'prop-5af6fb3fd11f', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.12'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.15
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-94c013994544 — 2026-10-06T16:47:09+00:00

- **Direction:** calibration
- **Hypothesis / question:** [calibration] Measure Brier/ECE stability across chronological folds and years. (arm_pair=C->D, calibration_bins=5, estimator=LightGBM, n_boot=500) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** calibration
- **Prior evidence:** [{'experiment_id': 'exp-e508513127a2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-853a0b9e2520', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-26bd4111e923', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.001168; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.16
- **Next research implication:** Build on accepted direction 'calibration' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-0dd2734d128f — 2026-10-06T18:42:45+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=C->D, estimator=LightGBM, min_effect=meaningful, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'exp-593e242ef739', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'prop-a965e420e11b', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-40a65b7c37d5', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.14'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=0.001168; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED prop-3405a1833f05 — 2026-10-06T20:37:09+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=C->D, estimator=LightGBM, min_effect=strong, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-a965e420e11b', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-40a65b7c37d5', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.14'}, {'experiment_id': 'prop-0dd2734d128f', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=0.001168; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-1521fa631548 — 2026-10-06T23:07:50+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=A->B, estimator=LogisticRegression, n_boot=1000) reproduce deterministically under an independently parameterized re-run?
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-40a65b7c37d5', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.14'}, {'experiment_id': 'prop-0dd2734d128f', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-3405a1833f05', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.070673; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.17
- **Next research implication:** Build on accepted direction 'validation' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-60b3a5eaefb9 — 2026-10-07T01:02:57+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=B, n_boot=1000, premium=high) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-50a88b8ff482', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.11'}, {'experiment_id': 'prop-5af6fb3fd11f', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.12'}, {'experiment_id': 'prop-004b9efe173c', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.15'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.017023; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.18
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-e5e8542b4bb7 — 2026-10-07T03:10:23+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=500, premium=standard) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-5af6fb3fd11f', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.12'}, {'experiment_id': 'prop-004b9efe173c', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.15'}, {'experiment_id': 'prop-60b3a5eaefb9', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.18'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.19
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-54baf2c80165 — 2026-10-07T05:21:24+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=B, n_boot=500, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-004b9efe173c', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.15'}, {'experiment_id': 'prop-60b3a5eaefb9', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.18'}, {'experiment_id': 'prop-e5e8542b4bb7', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.19'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.017023; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.20
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-0bf4344df50c — 2026-10-07T14:17:31+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=A->B, estimator=LightGBM, min_effect=strong, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-0dd2734d128f', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-3405a1833f05', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-1521fa631548', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.17'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=0.005879; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED prop-3729cb758570 — 2026-10-07T16:25:17+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=B->C, estimator=LogisticRegression, min_effect=meaningful, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-3405a1833f05', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-1521fa631548', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.17'}, {'experiment_id': 'prop-0bf4344df50c', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=-0.00043; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-3412693676ec — 2026-10-07T18:42:27+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=B->C, estimator=LightGBM, min_effect=meaningful, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-1521fa631548', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.17'}, {'experiment_id': 'prop-0bf4344df50c', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-3729cb758570', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005859; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.21
- **Next research implication:** Build on accepted direction 'validation' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-6cb732f3a51c — 2026-10-07T20:57:33+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Replication: does Re-run the identical comparison on the independent predeclared seed set 7, 17, 29 so the non-degradation claim must reproduce on different random draws. (arm_pair=A->B, estimator=LightGBM, n_boot=1000) reproduce deterministically under an independently parameterized re-run?
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-0bf4344df50c', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-3729cb758570', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-3412693676ec', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.21'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005879; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.22
- **Next research implication:** Build on accepted direction 'validation' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-7d1b96faa0f8 — 2026-10-07T23:17:09+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=B->C, estimator=LightGBM, min_effect=strong, n_boot=500) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-3729cb758570', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-3412693676ec', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.21'}, {'experiment_id': 'prop-6cb732f3a51c', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.22'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=0.005859; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED prop-b6e7f3dc7e44 — 2026-10-08T01:33:01+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LogisticRegression, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'exp-98fca9f79724', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-21602e076136', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'prop-df6e2b2b9189', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=-0.000713; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED prop-6aa5e85e530a — 2026-10-08T03:54:28+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=B->C, estimator=LogisticRegression, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'exp-21602e076136', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'prop-df6e2b2b9189', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-b6e7f3dc7e44', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=-0.00043; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-7f35d266df53 — 2026-10-08T06:23:10+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=500, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-60b3a5eaefb9', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.18'}, {'experiment_id': 'prop-e5e8542b4bb7', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.19'}, {'experiment_id': 'prop-54baf2c80165', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.20'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.23
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-98c6db9c9f2b — 2026-10-08T08:54:25+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=1000, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-e5e8542b4bb7', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.19'}, {'experiment_id': 'prop-54baf2c80165', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.20'}, {'experiment_id': 'prop-7f35d266df53', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.23'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.24
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-2b798bd99239 — 2026-10-08T11:26:53+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=B, n_boot=500, premium=standard) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-54baf2c80165', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.20'}, {'experiment_id': 'prop-7f35d266df53', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.23'}, {'experiment_id': 'prop-98c6db9c9f2b', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.24'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.017023; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.25
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-1afacd2289cb — 2026-10-08T13:54:55+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=1000, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-7f35d266df53', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.23'}, {'experiment_id': 'prop-98c6db9c9f2b', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.24'}, {'experiment_id': 'prop-2b798bd99239', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.25'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.26
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-b1e7f236c72d — 2026-10-08T19:53:06+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=C->D, estimator=LogisticRegression, min_effect=strong, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-3412693676ec', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.21'}, {'experiment_id': 'prop-6cb732f3a51c', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.22'}, {'experiment_id': 'prop-7d1b96faa0f8', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=-0.000713; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-70e1e8174843 — 2026-10-08T20:19:05+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=B->C, estimator=LightGBM, min_effect=meaningful, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-6cb732f3a51c', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.22'}, {'experiment_id': 'prop-7d1b96faa0f8', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-b1e7f236c72d', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005859; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.27
- **Next research implication:** Build on accepted direction 'validation' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-32828c19b4a2 — 2026-10-08T20:41:20+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Compare two nested feature arms on identical purged folds. (arm_pair=B->C, estimator=LogisticRegression, n_boot=500) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'prop-df6e2b2b9189', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-b6e7f3dc7e44', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-6aa5e85e530a', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=-0.00043; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-2e4387098c93 — 2026-10-08T21:05:22+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=B->C, estimator=LightGBM, n_boot=500) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'prop-b6e7f3dc7e44', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-6aa5e85e530a', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-32828c19b4a2', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005859; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.28
- **Next research implication:** Build on accepted direction 'feature_engineering' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-ab8a5888d8da — 2026-10-08T21:37:00+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LightGBM, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'prop-6aa5e85e530a', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-32828c19b4a2', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-2e4387098c93', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.28'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.001168; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.29
- **Next research implication:** Build on accepted direction 'feature_engineering' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-8e4a2730bb49 — 2026-10-08T22:54:42+00:00

- **Direction:** calibration
- **Hypothesis / question:** [calibration] Measure Brier/ECE stability across chronological folds and years. (arm_pair=C->D, calibration_bins=5, estimator=LightGBM, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** calibration
- **Prior evidence:** [{'experiment_id': 'exp-853a0b9e2520', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'exp-26bd4111e923', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'prop-94c013994544', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.16'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.001168; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.30
- **Next research implication:** Build on accepted direction 'calibration' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-fe8cc84e0b89 — 2026-10-08T23:25:40+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=A->B, estimator=LogisticRegression, min_effect=strong, n_boot=500) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-7d1b96faa0f8', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-b1e7f236c72d', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-70e1e8174843', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.27'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.070673; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.31
- **Next research implication:** Build on accepted direction 'validation' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-bacc03af9608 — 2026-10-08T23:57:57+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=1000, premium=standard) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-98c6db9c9f2b', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.24'}, {'experiment_id': 'prop-2b798bd99239', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.25'}, {'experiment_id': 'prop-1afacd2289cb', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.26'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.32
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-90de6d378815 — 2026-10-09T00:30:13+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=1000, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-2b798bd99239', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.25'}, {'experiment_id': 'prop-1afacd2289cb', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.26'}, {'experiment_id': 'prop-bacc03af9608', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.32'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.33
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-95620250a2d4 — 2026-10-09T01:01:58+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=500, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-1afacd2289cb', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.26'}, {'experiment_id': 'prop-bacc03af9608', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.32'}, {'experiment_id': 'prop-90de6d378815', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.33'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.34
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-22dfde2c603c — 2026-10-09T01:34:32+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** [model_architecture] Compare LogisticRegression vs LightGBM on one fixed arm. (arm=C, n_boot=1000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_architecture
- **Prior evidence:** [{'experiment_id': 'prop-d4f0556a2553', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.9'}, {'experiment_id': 'prop-9aea15974ec3', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.10'}, {'experiment_id': 'prop-7b2f1a05d315', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.13'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.35
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-018dc4d8e0ec — 2026-10-09T02:03:03+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=C->D, estimator=LightGBM, min_effect=strong, n_boot=500) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-b1e7f236c72d', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-70e1e8174843', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.27'}, {'experiment_id': 'prop-fe8cc84e0b89', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.31'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=0.001168; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'validation' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-5d52d16b94ca — 2026-10-15T00:52:32+00:00

- **Direction:** validation
- **Hypothesis / question:** [validation] Falsifier: Challenge a marginal gain: it must clear a predeclared practically meaningful minimum effect, not merely a non-negative bar. (arm_pair=A->B, estimator=LogisticRegression, min_effect=meaningful, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** validation
- **Prior evidence:** [{'experiment_id': 'prop-70e1e8174843', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.27'}, {'experiment_id': 'prop-fe8cc84e0b89', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.31'}, {'experiment_id': 'prop-018dc4d8e0ec', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.070673; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.36
- **Next research implication:** Build on accepted direction 'validation' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-4fdf6dd35236 — 2026-10-15T01:26:47+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=A, n_boot=1000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-bacc03af9608', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.32'}, {'experiment_id': 'prop-90de6d378815', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.33'}, {'experiment_id': 'prop-95620250a2d4', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.34'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.37
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-4dbe8e8ccc66 — 2026-10-15T22:05:30+00:00

- **Direction:** calibration
- **Hypothesis / question:** [calibration] Falsifier: Measure Brier/ECE stability across chronological folds and years. (arm_pair=C->D, calibration_bins=5, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** calibration
- **Prior evidence:** [{'experiment_id': 'exp-26bd4111e923', 'status': 'ACCEPTED', 'lesson': 'Candidate result recorded; review detailed evaluation artifacts.'}, {'experiment_id': 'prop-94c013994544', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.16'}, {'experiment_id': 'prop-8e4a2730bb49', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.30'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=0.001168; decision_criteria_passed=True
- **Conclusion:** Original working tree changed during the experiment; the repository is not in a known-safe state.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## REJECTED prop-85ec7554a97f — 2026-10-15T22:47:06+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=2000, premium=high) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-90de6d378815', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.33'}, {'experiment_id': 'prop-95620250a2d4', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.34'}, {'experiment_id': 'prop-4fdf6dd35236', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.37'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Original working tree changed during the experiment; the repository is not in a known-safe state.
- **Next research implication:** Direction 'model_complexity' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-a5866f7efc61 — 2026-10-15T23:22:51+00:00

- **Direction:** calibration
- **Hypothesis / question:** [calibration] Falsifier: Measure Brier/ECE stability across chronological folds and years. (arm_pair=B->C, calibration_bins=5, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** calibration
- **Prior evidence:** [{'experiment_id': 'prop-94c013994544', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.16'}, {'experiment_id': 'prop-8e4a2730bb49', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.30'}, {'experiment_id': 'prop-4dbe8e8ccc66', 'status': 'REJECTED', 'lesson': 'Original working tree changed during the experiment; the repository is not in a known-safe state.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005859; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.38
- **Next research implication:** Build on accepted direction 'calibration' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-5e72c5c28728 — 2026-10-16T00:01:57+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=D, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-95620250a2d4', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.34'}, {'experiment_id': 'prop-4fdf6dd35236', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.37'}, {'experiment_id': 'prop-85ec7554a97f', 'status': 'REJECTED', 'lesson': 'Original working tree changed during the experiment; the repository is not in a known-safe state.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.39
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-7bfa795b4c04 — 2026-10-16T00:22:43+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=C, n_boot=2000, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-4fdf6dd35236', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.37'}, {'experiment_id': 'prop-85ec7554a97f', 'status': 'REJECTED', 'lesson': 'Original working tree changed during the experiment; the repository is not in a known-safe state.'}, {'experiment_id': 'prop-5e72c5c28728', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.39'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.40
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-b02fcee28cf4 — 2026-10-16T00:45:39+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=B, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-85ec7554a97f', 'status': 'REJECTED', 'lesson': 'Original working tree changed during the experiment; the repository is not in a known-safe state.'}, {'experiment_id': 'prop-5e72c5c28728', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.39'}, {'experiment_id': 'prop-7bfa795b4c04', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.40'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.017023; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.41
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-2e720b1cb335 — 2026-10-16T01:07:40+00:00

- **Direction:** calibration
- **Hypothesis / question:** [calibration] Falsifier: Measure Brier/ECE stability across chronological folds and years. (arm_pair=C->D, calibration_bins=10, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** calibration
- **Prior evidence:** [{'experiment_id': 'prop-8e4a2730bb49', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.30'}, {'experiment_id': 'prop-4dbe8e8ccc66', 'status': 'REJECTED', 'lesson': 'Original working tree changed during the experiment; the repository is not in a known-safe state.'}, {'experiment_id': 'prop-a5866f7efc61', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.38'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.001168; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.42
- **Next research implication:** Build on accepted direction 'calibration' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-fe0a0d9c120b — 2026-10-16T01:29:43+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=D, n_boot=2000, premium=standard) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-5e72c5c28728', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.39'}, {'experiment_id': 'prop-7bfa795b4c04', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.40'}, {'experiment_id': 'prop-b02fcee28cf4', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.41'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.43
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-baff5074640f — 2026-10-16T01:52:39+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] Falsifier: Test whether a simpler model class retains within-margin performance under the matched protocol. (arm=A, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-7bfa795b4c04', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.40'}, {'experiment_id': 'prop-b02fcee28cf4', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.41'}, {'experiment_id': 'prop-fe0a0d9c120b', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.43'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.44
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-8afa516dd237 — 2026-10-16T02:16:44+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** [error_analysis] Falsifier: Slice out-of-fold errors by predeclared volatility/time regimes. (arm=C, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** error_analysis
- **Prior evidence:** [{'experiment_id': 'exp-a553ef6429e6', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-64687df9eaf2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4d8618855917', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.45
- **Next research implication:** Build on accepted direction 'error_analysis' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-c84744aeccbb — 2026-10-16T02:39:09+00:00

- **Direction:** target_design
- **Hypothesis / question:** [target_design] Falsifier: Pre-registered horizon comparison on development folds only. (arm=B, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** target_design
- **Prior evidence:** [{'experiment_id': 'exp-ac71d3fdc87f', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-201bd407b301', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-67847a5cd9c1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.017023; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.46
- **Next research implication:** Build on accepted direction 'target_design' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-7ace12bead87 — 2026-10-16T03:02:30+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=B->C, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'prop-32828c19b4a2', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}, {'experiment_id': 'prop-2e4387098c93', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.28'}, {'experiment_id': 'prop-ab8a5888d8da', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.29'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005859; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.47
- **Next research implication:** Build on accepted direction 'feature_engineering' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-392606fef7f1 — 2026-10-16T03:25:07+00:00

- **Direction:** model_complexity
- **Hypothesis / question:** [model_complexity] The complexer estimator must clear a predeclared complexity premium over LogisticRegression to justify its extra complexity, otherwise the simpler model stands. (arm=A, n_boot=2000, premium=high) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** model_complexity
- **Prior evidence:** [{'experiment_id': 'prop-b02fcee28cf4', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.41'}, {'experiment_id': 'prop-fe0a0d9c120b', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.43'}, {'experiment_id': 'prop-baff5074640f', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.44'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.48
- **Next research implication:** Build on accepted direction 'model_complexity' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-75513a36d0c5 — 2026-10-16T03:48:15+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** [model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=A, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_architecture
- **Prior evidence:** [{'experiment_id': 'prop-9aea15974ec3', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.10'}, {'experiment_id': 'prop-7b2f1a05d315', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.13'}, {'experiment_id': 'prop-22dfde2c603c', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.35'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.49
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-5825479a4b13 — 2026-10-16T04:10:28+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LogisticRegression, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'prop-2e4387098c93', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.28'}, {'experiment_id': 'prop-ab8a5888d8da', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.29'}, {'experiment_id': 'prop-7ace12bead87', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.47'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=-0.000713; decision_criteria_passed=False
- **Conclusion:** Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).
- **Next research implication:** Direction 'feature_engineering' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-4ce0abcadd5d — 2026-10-16T04:35:01+00:00

- **Direction:** calibration
- **Hypothesis / question:** [calibration] Measure Brier/ECE stability across chronological folds and years. (arm_pair=B->C, calibration_bins=10, estimator=LightGBM, n_boot=2000) — does it satisfy the predeclared non-degradation criteria on the frozen development folds?
- **Motivation:** calibration
- **Prior evidence:** [{'experiment_id': 'prop-4dbe8e8ccc66', 'status': 'REJECTED', 'lesson': 'Original working tree changed during the experiment; the repository is not in a known-safe state.'}, {'experiment_id': 'prop-a5866f7efc61', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.38'}, {'experiment_id': 'prop-2e720b1cb335', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.42'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005859; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.50
- **Next research implication:** Build on accepted direction 'calibration' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-e4537e38cdcf — 2026-10-16T04:59:07+00:00

- **Direction:** calibration
- **Hypothesis / question:** [calibration] Falsifier: Measure Brier/ECE stability across chronological folds and years. (arm_pair=A->B, calibration_bins=5, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** calibration
- **Prior evidence:** [{'experiment_id': 'prop-a5866f7efc61', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.38'}, {'experiment_id': 'prop-2e720b1cb335', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.42'}, {'experiment_id': 'prop-4ce0abcadd5d', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.50'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.005879; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.51
- **Next research implication:** Build on accepted direction 'calibration' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-251521165b10 — 2026-10-16T05:23:10+00:00

- **Direction:** target_design
- **Hypothesis / question:** [target_design] Falsifier: Pre-registered horizon comparison on development folds only. (arm=A, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** target_design
- **Prior evidence:** [{'experiment_id': 'exp-201bd407b301', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-67847a5cd9c1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'prop-c84744aeccbb', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.46'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.081817; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.52
- **Next research implication:** Build on accepted direction 'target_design' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## REJECTED prop-1f863aaa1b33 — 2026-10-16T10:34:03+00:00

- **Direction:** calibration
- **Hypothesis / question:** [calibration] Falsifier: Measure Brier/ECE stability across chronological folds and years. (arm_pair=A->B, calibration_bins=10, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** calibration
- **Prior evidence:** [{'experiment_id': 'prop-2e720b1cb335', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.42'}, {'experiment_id': 'prop-4ce0abcadd5d', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.50'}, {'experiment_id': 'prop-e4537e38cdcf', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.51'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=REJECTED; primary delta=0.005879; decision_criteria_passed=True
- **Conclusion:** Original working tree changed during the experiment; the repository is not in a known-safe state.
- **Next research implication:** Direction 'calibration' did not clear the gates under this design; change the design or pivot to a structural question rather than making tiny variations.
- **Scientific claim:** No

## ACCEPTED prop-7563472c00dd — 2026-10-16T10:57:56+00:00

- **Direction:** model_architecture
- **Hypothesis / question:** [model_architecture] Falsifier: Compare LogisticRegression vs LightGBM on one fixed arm. (arm=C, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** model_architecture
- **Prior evidence:** [{'experiment_id': 'prop-7b2f1a05d315', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.13'}, {'experiment_id': 'prop-22dfde2c603c', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.35'}, {'experiment_id': 'prop-75513a36d0c5', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.49'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.53
- **Next research implication:** Build on accepted direction 'model_architecture' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-f8a740131122 — 2026-10-16T12:32:16+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** [error_analysis] Falsifier: Slice out-of-fold errors by predeclared volatility/time regimes. (arm=B, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** error_analysis
- **Prior evidence:** [{'experiment_id': 'exp-64687df9eaf2', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'exp-4d8618855917', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'prop-8afa516dd237', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.45'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.017023; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.54
- **Next research implication:** Build on accepted direction 'error_analysis' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-134f44d740b4 — 2026-10-16T13:19:19+00:00

- **Direction:** target_design
- **Hypothesis / question:** [target_design] Falsifier: Pre-registered horizon comparison on development folds only. (arm=C, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** target_design
- **Prior evidence:** [{'experiment_id': 'exp-67847a5cd9c1', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'prop-c84744aeccbb', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.46'}, {'experiment_id': 'prop-251521165b10', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.52'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.023312; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.55
- **Next research implication:** Build on accepted direction 'target_design' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-dbcceddf3839 — 2026-10-16T19:27:11+00:00

- **Direction:** error_analysis
- **Hypothesis / question:** [error_analysis] Falsifier: Slice out-of-fold errors by predeclared volatility/time regimes. (arm=D, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** error_analysis
- **Prior evidence:** [{'experiment_id': 'exp-4d8618855917', 'status': 'REJECTED', 'lesson': 'One or more mandatory scientific gates did not PASS.'}, {'experiment_id': 'prop-8afa516dd237', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.45'}, {'experiment_id': 'prop-f8a740131122', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.54'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.56
- **Next research implication:** Build on accepted direction 'error_analysis' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-377ffe96de73 — 2026-10-16T19:56:32+00:00

- **Direction:** target_design
- **Hypothesis / question:** [target_design] Falsifier: Pre-registered horizon comparison on development folds only. (arm=D, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** target_design
- **Prior evidence:** [{'experiment_id': 'prop-c84744aeccbb', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.46'}, {'experiment_id': 'prop-251521165b10', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.52'}, {'experiment_id': 'prop-134f44d740b4', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.55'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.025192; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.57
- **Next research implication:** Build on accepted direction 'target_design' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No

## ACCEPTED prop-35b196ee5e7e — 2026-10-16T20:31:33+00:00

- **Direction:** feature_engineering
- **Hypothesis / question:** [feature_engineering] Falsifier: Compare two nested feature arms on identical purged folds. (arm_pair=C->D, estimator=LightGBM, n_boot=2000) — predeclared refutation: metric below zero under the frozen purged protocol.
- **Motivation:** feature_engineering
- **Prior evidence:** [{'experiment_id': 'prop-ab8a5888d8da', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.29'}, {'experiment_id': 'prop-7ace12bead87', 'status': 'ACCEPTED', 'lesson': 'Promoted as V2.0.47'}, {'experiment_id': 'prop-5825479a4b13', 'status': 'REJECTED', 'lesson': 'Evaluation evidence is incomplete or predeclared acceptance criteria failed (missing results: []; missing release metadata: []).'}]
- **Proposed change:** not recorded
- **Expected outcome:** All predeclared acceptance criteria pass with a positive primary-metric delta (see the experiment specification).
- **Actual result:** status=ACCEPTED; primary delta=0.001168; decision_criteria_passed=True
- **Conclusion:** Promoted as V2.0.58
- **Next research implication:** Build on accepted direction 'feature_engineering' from the new champion; keep testing unresolved questions in other directions.
- **Scientific claim:** No
