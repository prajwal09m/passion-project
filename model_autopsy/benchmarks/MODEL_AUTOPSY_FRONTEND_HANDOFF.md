# MODEL_AUTOPSY FRONTEND HANDOFF (Stage 6)

Backend contract for the frontend-design phase. No visual redesign is
included here; `Eval.tsx`/`CausalPanel.tsx` already render the new fields.
Backend: FastAPI (`backend/api.py`), SQLite via SQLAlchemy, loopback CORS
(`:5173` only). No auth layer — operator-local tool assumption.

## 1. Architecture

Investigation (FSM: created → context_ready → hypotheses_proposed →
investigating → revising/blocked → finalizing → complete/failed/stopped) →
hypotheses + actions + events (append-only) → deterministic report →
versioned scorecard → persisted manifests. Resolution contract
(`research/resolve.py`) is the SOLE confirmation authority. Live pilots are
CLI-launched only; the dashboard never spends (`/api/live/*` read-only).

## 2. Endpoints (stable)

- `GET /api/health` → `{ok, service, time}`
- `POST /api/investigations` `{mode, title, question, max_iterations?,
  workspace_root?, predictions_path?, project_id?, tags?, eval_version?}`
  → summary (400 on bad mode/version). `eval_version`: "v2"|"v3", default v2.
- `GET /api/investigations[?mode&status&limit]` → `{items: [summary]}`
- `GET /api/investigations/{id}` → summary + question + config + final_report
  + hypotheses[] + actions[] (full shapes in §5/§6).
- `POST /api/investigations/{id}/stop` → parks active states as `stopped`;
  400 on terminal (complete/failed/stopped/finalizing), 404 unknown.
- `POST …/context|tool|meta-turn|hypotheses|findings|report`,
  `PATCH /api/hypotheses/{id}`, `POST …/hypotheses/{hid}/evidence`,
  `POST …/revision-plan/{idx}/applied` → existing shapes, unchanged.
- `GET …/timeline|m16|closure|causal` → read-only record views.
- `GET /api/eval/projects|separation-audit|runs|runs/{run}|runs/{rid}/{pid}`
  (+ blind/reveal review POSTs), `GET /api/eval/versions` →
  `{versions:["v2","v3"], default, selected, framework:"m4-v1"}`,
  `POST /api/eval/runs` `{project?, max_experiments?, eval_version?}`.
- `GET /api/live/runs|runs/{run_id}` (manifest passthrough incl.
  `eval_rubric_version`), `GET /api/settings` (non-secret incl.
  `evaluation:{rubric_versions, rubric_default, rubric_selected, framework}`),
  `GET /api/meta/status`, `POST /api/meta/test-connection` (only
  spend-adjacent endpoint; requires configured key).

## 3. Key schemas

- Investigation summary: `{id, mode, title, status, iteration_count,
  max_iterations, tool_call_count, max_tool_calls, created_at,
  latest_findings, tags, is_test_record, eval_rubric_version|null,
  has_final_report}`.
- Hypothesis: `{id, text, status (proposed|investigating|supported|
  rejected|inconclusive|blocked), confidence 0-100|null, source, rationale,
  predicted_observation, confidence_note, evidence_refs:[{action_id, tool,
  relation (supports|contradicts|relevant_to|mentions|neutral|insufficient|
  uncertain), action_status}], revisions:[{at,from,to}]}`.
- Action: `{id, seq, kind, tool_name, status (ran|failed), arguments,
  result (numbers), error, iteration}`.
- Verification trail (report `verification[]`): executed
  `{hypothesis_id, tool, action_id, result}`; planned-but-unexecuted
  `{hypothesis_id, tool, planned:true}`; non-run
  `{hypothesis_id?, reason (8 codes), detail}`.
- Scorecard: `{project, rubric_version ("v2"|"v3"), verdict, overall|null,
  dimensions {discovery, evidence, verification, confirmation|reasoning,
  calibration?, efficiency, reproducibility (values or null)},
  weights, notes {per-dim + numbers_gate + cost}, unavailable[],
  formula?, false_positive?, assessment}`. v2 dims: discovery/evidence/
  reasoning/calibration/efficiency/reproducibility. v3 dims: discovery/
  evidence/verification/confirmation/efficiency/reproducibility.
  `overall:null` + `unavailable` = insufficient data (render as
  "unavailable", never 0).
- Manifest (live): `{run_id, kind, eval_rubric_version, status, budget
  {cost_usd{spent,cap}, tokens{...}}, required_evidence_present, artifacts
  {sha256}}`; eval-run manifest adds `eval_version:"m4-v1"` (framework).

## 4. Rules the UI must communicate

Discovery ≠ confirmation (explainer already in `Eval.tsx`); evidence ≠
verification; honest `partially-resolved`/`inconclusive` can carry discovery
>0; high aggregate never conceals unsupported conclusions (confirmation 0.0
is decisive); v2 vs v3 dims must never be mixed without the rubric label;
missing metrics render "unavailable".

## 5. Remaining frontend-only work

Visual/UX redesign; v3 dimension charts; verification-timeline view;
stop-button wiring; cost/usage display from manifest budget blocks;
historical v2 vs v3 comparison view (data in COMPARISON report).
