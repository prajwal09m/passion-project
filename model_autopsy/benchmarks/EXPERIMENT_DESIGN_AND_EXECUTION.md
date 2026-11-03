# Experiment Design and Execution (Milestone 3, Parts 4 + 5)

## Design (`experiments.design`)

Per hypothesis: smallest useful experiment = one read-only diagnostic
already capability-selected for that card. Plan records tool,
controls (fixed seeds, copy-on-read, same row set), evidence required,
supports/refutes criteria, remaining alternatives, cost, and safety
flags (`modifies_original: false`, `external_access: false`).

Prioritization is an explicitly labeled HEURISTIC
(`relevance*2 + feasibility - cost - risk`), documented in every plan
as "NOT a formal Bayesian information-gain calculation". Candidates
with scores are stored in `prioritization.candidates` for audit.

## Isolation (`experiments.execute_isolated`)

- Run workspace: `backend/data/research_runs/{inv}/{exp}/` with
  `plan.json` + `log.txt` + `result.json` (config snapshot, seed,
  elapsed time, output provenance).
- Originals opened read-only; inputs COPIED into the workspace, never
  moved or linked; `provenance.original_modified: false` recorded.
- Failures recorded with type + message (never swallowed); no
  untrusted project scripts execute in the main process — the runner
  calls registered deterministic diagnostics only.

## Approval gates

Destructive operations (overwrite originals, modify weights, change
production config, external access, expensive runs, private-data
upload) are not implemented by the lab; any future op of that class
must require explicit owner approval before execution. Current
diagnostics are all read-only (`TOOL_CARDS[*].read_only == true`).

## Measured behavior

13 experiments across 9 scenarios, all `ran` (0 failed, 0 unexecuted);
per-scenario time 0.3-2.4 s offline. Reproducibility: fixed seeds,
committed fixtures, recorded workspaces.

## Limitations

No resource/timeout enforcement beyond diagnostic-level caps; no
container isolation (documented: in-process sandbox = copy-on-read +
read-only registered tools, not a security boundary against
adversarial code).
