# Milestone 4 — Evaluation Instructions

## Run the benchmark (offline, no keys, no network)

```bash
# Full suite (8 projects, ~10 s):
py -3 -m model_autopsy.backend.eval.runner --all \
  --out model_autopsy/benchmarks/eval_runs

# Single project:
py -3 -m model_autopsy.backend.eval.runner --project eval_credit \
  --out model_autopsy/benchmarks/eval_runs
```

Requirements: provider credential variables MUST be unset (the runner
refuses otherwise). No network access is used.

## Outputs (never overwritten)

`benchmarks/eval_runs/{run_id}/`:
`eval.sqlite3` (run-scoped DB), `eval_{project}.json` × 8 (report +
scorecard + provenance), `{pid}.review.json` (when reviewed),
`manifest.json` (versions, per-project verdicts, aggregate, timings).

Versions pinned per run: `eval_version` (m4-v1), `investigator_version`
(lab-deterministic-v1), `max_experiments`.

## Reproduce / compare

Reruns mint new IDs; compare manifests across IDs. Determinism check:
`test_repeated_runs_agree` runs eval_rent twice and asserts identical
verdict + score. Regenerating fixtures (`tests/fixture_eval/
generate.py`, seed 23) reproduces identical CSV bytes.

## Dashboard / API

UI: nav **Evaluation** → run the suite, browse runs, drill into a
project (dimensions, evidence trail with numbers, human review).
API: `GET /api/eval/projects`, `GET /api/eval/separation-audit`,
`POST /api/eval/runs`, `GET /api/eval/runs[/{id}[/{project}]]`,
review endpoints under `/review/blind` + `/review/reveal`.

## Future live-model evaluation (NOT authorized)

The runner supports only the deterministic investigator. A
provider-backed reasoner may be injected at `lab`'s reasoner point;
any billed run requires separate, explicit authorization and must
record usage per run. Do not run paid campaigns under this protocol.
