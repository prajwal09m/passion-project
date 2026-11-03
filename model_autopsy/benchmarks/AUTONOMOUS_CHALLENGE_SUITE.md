# Autonomous Challenge Suite (Milestone 3, Part 8)

Runner: `test_challenge_suite_nine_scenarios_offline` (offline,
deterministic, no provider calls). Investigator input per scenario =
brief spec + artifact path ONLY (`challenge.discovery_input`); hidden
ground truth lives in `fixture_universal/ground_truth.json` and
`fixture_challenge/ground_truth_challenge.json`, read by assertions,
never by triage code.

## The 9 scenarios (8 families + interacting pair)

| # | id | Family (required) | Planted weakness | Kind |
|---|---|---|---|---|
| 1 | fin_time_class | financial time-series classification | proxy column mirrors label | single |
| 2 | nonfin_tab_class | non-financial tabular classification | proxy column mirrors label | single |
| 3 | regression | regression | +bias on one segment | single |
| 4 | nonfin_forecast | non-financial forecasting | 30-day split overlap + missed drift | single |
| 5 | clustering | clustering | none (healthy control) | clean |
| 6 | ranking | ranking/recommendation | tail-slice P@K collapse under pooled mean | single |
| 7 | blackbox | black-box prediction | predictions+labels only (leak screen impossible) | limited |
| 8 | pipeline | preprocessing+evaluation pipeline | train/infer scaling mismatch on bmi | single |
| 9 | multi | interacting weaknesses | leak column AND near-random south slice | multi |

Distractions: legitimate columns, overlapping date spans, pooled
metrics that look fine, healthy controls. Scenario 9's pooled AUC
(0.83) looks acceptable while ward AUCs split 1.00 vs 0.53.

## Results (2026-11-01, max_experiments=3, all offline)

| Scenario | Experiments | Confirmed | Hit |
|---|---|---|---|
| fin_time_class | feature_target_suspiciousness (leak_flag r=0.89, gap 0.64), classification_metrics (AUC 1.00) | proxy leak | YES |
| nonfin_tab_class | same as above | proxy leak | YES |
| regression | regression_metrics (MAE 10279, bias -7952) | segment bias | YES |
| nonfin_forecast | forecast_diagnostics (overlap true, late MAE 2.3x) | stale split/drift | YES |
| clustering | clustering_stability (sil 0.72, imb 1.1) | none (correct null) | YES |
| ranking | ranking_diagnostics (slice P@K gap 0.65) | slice collapse | YES |
| blackbox | leak screen inapplicable (honest), classification_metrics (AUC 1.00) | none claimed (correct) | YES |
| pipeline | regression_metrics (bias -656, resid-bmi corr -0.99) | systematic bias, bmi-indicative | YES |
| multi | leak screen (r=0.91) + per-ward AUC (1.00 vs 0.53, gap 0.47) | BOTH leak and subgroup failure | YES |

9/9 hits (aggregate 1.0; blackbox 1.0 after honest-limit wording).
Per-scenario wall time 0.3-2.4 s. No false confirmations on clean /
limited scenarios: the null hypothesis held where nothing replicated.

## Honesty notes

n=1 scenario per family (except classification); LLM reasoning across
projects untested (needs paid calls); fixtures are synthetic with
strong signals — real-world subtlety will be harder.
