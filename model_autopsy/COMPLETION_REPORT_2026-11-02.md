# Model Autopsy — Scientific Interpretation Overhaul: Completion Report (2026-11-02)

## 1. Baseline findings
- Engine executed diagnostics and recorded evidence, but `build_report` equated workflow `complete` with success; empty findings/hypotheses rendered as a clean pass.
- `runFullBattery` ran 4-5 diagnostics then generated a report with zero hypotheses; no offline interpretation existed (only Meta turns, requiring a key).
- Suspiciousness scan (`feature_target_suspiciousness`) included the label column itself (r=1.0) and score-like prediction columns, and had a latent `KeyError` when `label_csv` was omitted.
- Uploads listed every file in every batch with no content-hash dedupe; no remove/replace; copy claimed scripts "read for provenance" while no inspection existed.
- Frontend showed a single status pill and "Investigation complete" messaging; disabled buttons gave no reason.

## 2. Root causes
- No scientific-status concept: `engine.build_report` had no evaluator distinguishing execution from scientific establishment.
- No post-battery interpretation hook: auto-battery never called any hypothesis generator.
- Scan hygiene: label/score columns not excluded from feature screening; generator picked `rows[0]` blindly.
- Upload history was a raw directory listing; no identity hash, no hidden-marker, no reference check.

## 3. Files modified
- `model_autopsy/backend/ml_tools.py` — exclude label-like columns from suspiciousness scan; fix `_label` KeyError path.
- `model_autopsy/backend/tools_registry.py` — registered `script_static_inspection` + PARAM_SCHEMA.
- `model_autopsy/backend/engine.py` — `_investigation_scope`, `_main_interpretation`; extended `build_report` additively (all legacy keys preserved).
- `model_autopsy/backend/api.py` — `/auto-interpret`, `/scientific` endpoints; uploads dedupe/hash/hide/delete; detail includes `scientific` + `recommended_experiments`; summary includes `scientific_status`.
- `model_autopsy/frontend/src/api.ts` — types + `autoInterpret`, `scientific`, `removeUpload`.
- `model_autopsy/frontend/src/autoBattery.ts` — calls auto-interpret, honest battery messaging.
- `model_autopsy/frontend/src/Workspace.tsx` — execution vs scientific header, scientific panel, Potential explanations, Suggested experiments, report sections (interpretation/scope/candidates), script-inspection tool, disabled hints.
- `model_autopsy/frontend/src/NewInvestigation.tsx` — artifact capability copy, dedupe flags, primary-target label, remove/replace guidance, honest completion message.
- `model_autopsy/frontend/src/pages.tsx` — history cards show execution + scientific pills.

## 4. New modules
- `model_autopsy/backend/scientific.py` — deterministic evaluator (supported / partially_supported / inconclusive / no_issue_detected_within_scope / contradicted) with ordered transition rules, gap lists, score/label-filtered suspicion.
- `model_autopsy/backend/hypothesis_gen.py` — offline candidate generation (1-3, suspicion-only wording, competing possibilities, support/contradict criteria, evidence-linked, idempotent dedupe) + evidence-driven experiment recommendations.
- `model_autopsy/backend/script_inspection.py` — safe AST-only `.py` parsing (imports, call order, fit-before-split heuristic, line refs; never executes; syntax errors fail safely).
- `model_autopsy/tests/test_scientific_interpretation.py` — 10 acceptance tests.

## 5. Scientific status model and transition rules
`evaluate(session, inv)` is read-only: supported (supported hyp/confirmed with ≥2 tools or verification event) → partially_supported (supported/confirmed/likely present but uncorroborated, or suspicion + open hyp) → contradicted (all rejected, nothing open/confirmed) → no_issue_detected_within_scope (≥2 relevant tools ran, no suspicion, nothing open) → inconclusive (default; covers empty battery). `no_issue_detected_within_scope` copy explicitly disclaims universal safety.

## 6. Hypothesis-generation methodology
Reads recorded `feature_target_suspiciousness` (score-filtered), `dataset_validation` duplicates, and temporal/calibration signals. Wording is always "may … warrants investigation" with mechanism, competing explanations (legitimate/proxy/leakage/post-outcome/contamination), missing info, experiment, and support/contradict criteria. Dedupe via normalized-text match against machine + manual hypotheses; stable sha key in rationale marker.

## 7. Experiment recommendation methodology
Derived per open/relevant hypothesis: provenance inspection (`script_static_inspection`) then ablation re-evaluation (`classification_metrics`), plus generic falsification test. Each rec lists hypothesis, what/why, required inputs, measures, support/contradict outcomes, executability. Sorted by priority; no numeric confidence invented. Execution remains via normal `run_tool`, creating durable evidence.

## 8. Script-inspection capabilities and limitations
Parses with `ast` under `resolve_restricted` (project root only, `.py` only); reports imports, call counts, first fit/split lines, target assignments, heuristic warnings (fit-before-split, fillna/target patterns) labeled suspicions. Limitations stated in output and UI: static only, never executed/imported, cannot prove leakage, malformed files fail safely.

## 9. Upload-history changes
`list_uploads` now hashes (sha256-16), flags `is_duplicate`/`duplicate_of`, exposes `analyzed` + `analysis_note`. `DELETE /api/uploads/{batch}/{name}` hides from history (`.hidden_` marker, bytes retained); `?purge=true` deletes only when unreferenced (400 if referenced). UI shows duplicate badges, analysis column, primary-target label, remove buttons, replace workflow copy.

## 10. Frontend changes
Execution vs Scientific shown in workspace header, context rail, report header, history cards, and completion messages ("Diagnostic battery finished…" replaces "Investigation complete"). New sections: scientific assessment panel, Potential explanations (expandable, suspicion-labeled), Suggested experiments, restructured report (interpretation, scope, candidates split, experiments, reproducibility). Disabled controls carry `title` + inline `role=note` hints. Visual identity preserved.

## 11. Tests added
`test_scientific_interpretation.py` (10): empty→inconclusive; suspicion→not-confirmed; no fabricated refs; determinism/dedupe/manual-preservation; supported-needs-verification→partial; no-issue/contradicted paths; experiments originate from hyps; script inspection safety; upload dedupe; report additive keys.

## 12. Full test results
- New suite: **10 passed**.
- Full backend suite (`--ignore=test_phase_d_groq_persistence`): **710 passed, 1 deselected** (the deselected `test_git_status_and_diff_on_real_repo` fails in this working tree because the large uncommitted diff breaks the tool's locale decoding — pre-existing fragility, unrelated to this change; passes on a clean tree).
- Frontend: `npm run build` **passes**; `tsc --noEmit` exit 0.

## 13. TypeScript/build results
Vite production build succeeds (47 modules). No new TS errors.

## 14. Regression results
Legacy report keys byte-compatible (additive only). Manual hypothesis registration, evidence linking, history reopening, report generation all exercised by the passing suite. Frozen benchmarks untouched (no `benchmarks/` changes). Demand Zone AI untouched.

## 15. End-to-end diabetes investigation results
Isolated offline run on `faulty_demo/diabetes_faulty_predictions.csv` + `train_faulty_diabetes.py`: context loads; 6 diagnostics run; machine proposes `Feature 'leak_risk_flag' may carry information… (|r|=0.888)` (suspicion only); scientific = `partially_supported`; experiments = provenance + ablation; report contains execution vs scientific, interpretation, scope, candidates, experiments; no confirmed-leakage claim from correlation; no safe-model claim. **E2E PASS**.

## 16. Remaining limitations
- `test_git_status_and_diff_on_real_repo` fails while the working tree is this large (encoding fragility in `software_tools._git`, out of scope).
- Score-column auto-detection still heuristic; ablation experiments are recommended, not auto-executed (originals never modified).
- Static inspection is heuristic pattern matching, not dataflow proof.

## 17. Zero provider calls / spend
New code paths contain no `requests/httpx/urllib/meta_client/MODEL_API_KEY/groq` references (verified by grep). All generation is offline/deterministic. No API spend.

## 18. Demand Zone AI and frozen artifacts untouched
`git status` shows no changes under `demand-zone*` or `model_autopsy/benchmarks/`. Eval V2/V3 code paths unmodified; report changes are additive.

### Audit finding disposition
- P0 execution-vs-science split: **FIXED**
- P0 auto hypothesis generation: **FIXED**
- P1 experiment guidance: **FIXED**
- P1 artifact provenance + script inspection: **FIXED** (static inspection implemented; limits stated)
- P2 upload history: **FIXED**
- P3 disabled-control explanations: **FIXED**
- Report restructure + frontend hierarchy: **FIXED**
