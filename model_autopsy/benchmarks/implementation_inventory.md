# Implementation Inventory (M9–M12 program)

## New backend modules
- `backend/m10/{scenarios,sealed,runner,evaluator,replication,stats,cross_framework}.py`
- `backend/m11/{roles,ledger,team}.py`
- `backend/m12/{authorization,projects,scheduler,memory,repro}.py`
- `backend/causal/attribution.py`: += `_MECHANISM_EQUIV`,
  `same_mechanism()` (M7 fix; only semantic change in program)
- `backend/research/autonomous.py`: += `investigation_id` in
  behavior (additive)
- `backend/api.py`: += 11 `/api/lab/*` endpoints

## New fixtures (frozen, generated)
- `tests/fixture_m9/` (M9, 8 scenarios + demand-zone)
- `tests/fixture_m10/` + `_sealed/truth.json` (8 unseen)
- `tests/fixture_eval/investigator/{stable_output.csv,generator}`
- `tests/fixture_demo/flagship_rank.csv` + generator

## New tests (all pass)
test_m7_closed_loop (13), test_m10_validation (6),
test_m11_team (7), test_m12_lab (7), test_flagship_demo (1).

## New frontend
- `src/Lab.tsx` + api client additions + Laboratory nav tab.

## New benchmarks docs
milestone_9_finalization; M10 ×7 (audit, architecture,
unseen_projects, cross_framework, replication, challenge_report,
validation, results — challenge content folded into audit/results
per concision rule); M11 ×7; M12 ×8; integrated_m9_m12_validation;
master_architecture; this inventory; integrated live results
(when the single run completes).

## Reproducible commands
- `py -m pytest model_autopsy/tests -q` (full offline suite)
- `py model_autopsy/tests/fixture_m10/generate.py` (corpus)
- `cd model_autopsy/frontend && npx tsc --noEmit && npm run build`
- Live (authorized once): `run_live_investigation('eval_turbine',
  benchmarks/live_runs, max_rounds=3, run_id=...)` under governor
  caps; never re-run without fresh authorization.
