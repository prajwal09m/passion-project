# Milestone 4 — Architecture

`backend/eval/` is a NEW package beside (not inside) `backend/research/`.
The M3 investigation engine is reused unchanged as the investigator;
M4 adds the measurement apparatus around it.

## Components

| Module | Role | Depends on |
|---|---|---|
| `eval/projects.py` | 8 unfamiliar project specs + sealed-truth loader | fixtures only |
| `eval/separation.py` | investigation-env builder + lexical leakage audit | investigator dir |
| `eval/scorer.py` | rubric v2 (A–F + verdict taxonomy + weights) | report + truth |
| `eval/runner.py` | CLI + `run_all` (run IDs, run-scoped DB, no-overwrite) | lab, scorer |
| `eval/review.py` | blind-then-reveal human review store | run dir |
| `api.py` `/api/eval/*` | projects, audit, runs, drill-down, review endpoints | eval package |
| `frontend/Eval.tsx` | Independent Evaluation section + drill-down | eval API |

## Data flow

`runner.run_all` → per project: `discovery_input` (brief+artifact only)
→ `ProjectSpec` → `lab.run_autonomous_investigation` (deterministic
offline investigator) → forensic report → `scorer.score` vs sealed
truth → per-project JSON + manifest in `benchmarks/eval_runs/{run_id}/`
with a run-scoped `eval.sqlite3`. Reviews stored as
`{pid}.review.json` beside results, never inside scorecards.

## Compatibility risks (from reconnaissance, all avoided)

- No DB migrations: run-scoped SQLite via explicit session factories;
  app and test DBs untouched (tested).
- No shared mutable registry: eval projects live in their own module
  (`eval_` prefix); M3 `challenge.py` frozen.
- M3 diagnostic fix (`forecast_diagnostics` interval intersection) was
  required for correctness; two M3 unit assertions encoded the old
  buggy `True` and were corrected with dated comments (fixture bytes,
  ground truth, and M3 reports frozen — correction recorded in
  `m4_results_and_limitations.md`).
- Frontend follows ResearchLab patterns; `tsc` + `vite build` clean.

## What this architecture does NOT do

It does not sandbox code (nothing benchmark-supplied executes), does
not call providers (refuses when keys are set), and does not prove a
live model can investigate — it measures the deterministic pipeline
and reserves the interfaces (`reasoner` injection point in `lab.py`,
`INVESTIGATOR_VERSION` pin) for a future authorized live evaluation.
