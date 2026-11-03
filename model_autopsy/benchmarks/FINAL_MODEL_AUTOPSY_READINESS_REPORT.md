# FINAL Model Autopsy readiness report (2026-10-31)

## Reuse verdict (§7, from code inspection — no paid requests)
- Generic core, no rewrite needed: `engine.py` (investigations, hypotheses, evidence links, budgets, summaries, reports) is fully project-agnostic.
- Provider separation: billing/usage measurement isolated in `meta_api/` (Meta) and the Groq harness; investigation logic is provider-independent.
- Project adapters already parameterized: every diagnostic tool accepts caller-supplied CSV paths (`predictions_path`, `feature_csv`, …) sandboxed to the project root; `CASE_STUDY_CONFIG` is defaults-only. A new classification project with OOF-style CSVs reuses the core by passing paths — no engine changes.
- Reusable methodology: frozen blind rubric (mechanism/numeric/linkage/calibration/diagnostics/honesty), paired Full/Delta design, incremental persistence + fail-closed cleanup transfer as-is.
- Proven: 2 Groq + 1 Meta live campaigns, 202/202 tests, 65/65 historical hashes verify.

## Can it be reused on another project now?
Yes for classification/OOF-style investigations with tabular prediction artifacts. For other shapes, three minimal additions (reliability/reuse only, no gold-plating):
1. Per-project config loader (replace the `CASE_STUDY_CONFIG` const with a project config file: label/fold/score columns, artifact paths).
2. Regression-metric tools (current set is classification-only).
3. Threshold-sweep / calibration follow-up tool (flagged UNRESOLVED uncertainty in 2/2 valid finals — the top recurring diagnostic gap).

## Known limitations
- n=2 Meta pairs; no statistical significance claimed.
- Reasoning-heavy models can exhaust the frozen 1200-token repair budget (observed once); completion flaked 50% on Groq spot-checks, condition-independent.
- 8/24 Meta responses hit max-output truncation; full contexts truncate more.
- 2 transient HTTP 400s (preserved, unattributed beyond provider-side).
- Total-input comparisons are session-order cache-confounded; use uncached.
- Groq token deltas are not Meta billing evidence.

## Bottom line
Delta is retained (better-observed quality, lower uncached input both pairs). The system is reliable (all evidence preserved, all hashes verify), reusable (generic core + parameterized adapters), and honestly measured (savings reported on uncached input with confounds disclosed).
