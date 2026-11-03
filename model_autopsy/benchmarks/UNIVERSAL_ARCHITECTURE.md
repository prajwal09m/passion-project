# Universal Architecture — Phase 1 Audit (2026-10-31, offline, no provider calls)

## System map (actual code)
- `backend/engine.py` (~535 lines): investigation FSM, hypotheses, evidence links, findings, structured-summary validation, deterministic `build_report`, `build_context`, budgeted `run_tool`. **Generic.**
- `backend/tools_registry.py` (~619): PARAM_SCHEMA validation, allowlists, dedup/reuse, `ml_tools()`/`software_tools()`. **Generic mechanism; tool set is classification/OOF-specific.**
- `backend/ml_tools.py` (~424): real pandas/sklearn computations. Generic I/O (caller-supplied CSV paths, project-root sandbox) BUT: `load_predictions_csv` hard-requires binary `label`+`fold`; defaults `score_column="LightGBM_C"`; `CASE_STUDY_CONFIG` hardcodes Demand Zone paths/model arms; `grouped_auc_comparison` docstring is Demand-Zone-specific; no regression/ranking/clustering/forecast metrics.
- `backend/meta_api/loop.py` (~533): `MODE_INSTRUCTIONS` — the "ml" investigator prompt is already **domain-independent forensic method** (no finance terms). Context/delta packaging generic. `build_context` ml-branch assumes predictions/labels artifact.
- `backend/meta_api/client.py` (~198): generic Meta Responses API wrapper. **Provider-specific (Meta).**
- `backend/meta_api/case_metrics.py` (~181): **fully Demand-Zone-specific** (hardcoded arms, champion, ticker, OOF artifact path). Dashboard-only.
- `backend/api.py` (~410): generic REST; `GET /api/case-study/demand-zone*` are project-specific; `InvestigationCreate` has no project field.
- `backend/db.py`, `config.py`, `software_tools.py`, `prune.py`: generic.
- `frontend/`: Landing/Workspace/charts/pages heavily Demand-Zone/OOF/AUC-specific copy, hardcoded arms (`LightGBM_B`), fold-strip charts. `api.ts` generic REST client.
- `benchmarks/`: intentionally project-specific (frozen campaign definitions, OBJECTIVE, study files). **Must not be generalized** — they are historical evidence.

## Classification of every finance/domain assumption
| Location | Assumption | Class |
|---|---|---|
| `ml_tools.CASE_STUDY_CONFIG` paths/arms | study files, model columns | project-specific (defaults only; overridable) |
| `ml_tools.load_predictions_csv` binary label+fold requirement | binary classification w/ folds | task-specific (classification) |
| `ml_tools` default score columns | `LightGBM_C` etc. | project-specific defaults |
| `ml_tools` missing metrics | no regression/ranking/clustering/forecast | task gap |
| `case_metrics.py` everything | Demand Zone arms/champion/ticker | project-specific |
| frontend copy + charts | OOF/AUC/folds/arms | project-specific presentation |
| `api.py` case-study routes | Demand Zone endpoints | project-specific |
| benchmarks OBJECTIVE/harness | Demand Zone study | project-specific (frozen evidence) |
| engine FSM/hypotheses/evidence/reports | — | generic |
| investigator "ml" prompt | — | generic (domain-independent already) |
| registry validation/dedup/budgets | — | generic |
| `dataset_validation` tool | — | generic already |
| Meta client/loop transport | Responses API shape | provider-specific |

## Environment reality (tested)
Available: sklearn 1.9, pandas, numpy, scipy. NOT installed: torch, tensorflow, xgboost, lightgbm, pyarrow.
→ Actually testable: sklearn adapters, CSV/black-box, regression/classification/clustering metrics. Others: import-guarded, honestly marked untested.

## What was built (2026-10-31; all offline, suite green)
- `backend/projects/` — ProjectSpec/ModelMetadata/DatasetMetadata + validation, adapter base, registry; `demand_zone.py` reference; `synthetic.py` 5 fixtures adapters.
- `backend/model_adapters/` — capability-declaring ABC; real black-box, sklearn, xgboost, lightgbm, catboost, predict-only pytorch, api; guarded tensorflow/huggingface stubs.
- `backend/task_diagnostics/` — TOOL_CARDS (9 tools: tasks/caps/inputs/limits) + `select_tools` + real regression/forecast/clustering tools.
- Engine consumes specs (`build_context` project branch; investigator brief injection); legacy path byte-identical.
- `backend/ingestion/` (csv/json/jsonl/npy + capability report), `backend/providers/` (Meta/Groq/Ollama interface, fake-tested), `backend/contexts.py` (Full/Delta packages + savings).
- API: `/api/projects`, `/api/projects/{id}`, `/api/model-frameworks`, `project_id` on create.
- Dashboard: Projects page (spec-driven overview, task-aware panels, start-with-project); Case Study untouched.
- One genuine project assumption removed: `load_predictions_csv` no longer requires `fold`.

## Migration plan (what follows)
1. `backend/projects/`: ProjectSpec (metadata/model/dataset/task), validation, registry; Demand Zone adapter + synthetic adapters. Engine consumes spec; legacy config path kept.
2. `backend/model_adapters/`: capability-declaring ABC; real BlackBox + sklearn adapters; import-guarded framework stubs (honestly marked).
3. `backend/task_diagnostics/`: declared tool registry (tasks/capabilities/limits) + real regression metrics; capability-aware selection.
4. Engine: spec-driven `build_context` + investigator brief injection; no legacy breakage.
5. `backend/ingestion/`: csv/json/jsonl/npy loaders + partial-input capability report (parquet only if pyarrow present).
6. `backend/providers/`: provider interface + Meta/Groq/Ollama adapters over existing transports; fake-tested, no paid calls.
7. Context packages (`build_context_package`) reusing the validated Full/Delta machinery generically.
8. Dashboard: project selector + spec-driven overview + task-aware panels; Demand Zone pages untouched.
9. Offline multi-project validation suite (6 categories, sealed ground truth, deterministic triage — LLM reasoning covered by prior frozen campaigns, stated honestly).
10. Full regression + historical hash verification; 10 final docs.
