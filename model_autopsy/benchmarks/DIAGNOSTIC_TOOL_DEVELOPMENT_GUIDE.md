# Diagnostic Tool Development Guide

## Two layers
1. **Tool function** — pure, read-only, JSON-serializable output with provenance
   (`source` path, `n` rows). Lives in `backend/ml_tools.py` (classification/OOF
   family) or `backend/task_diagnostics/` (regression/forecast/clustering).
2. **Registry declaration** — in `tools_registry.ml_tools()` + `PARAM_SCHEMA`
   (arg validation) + `task_diagnostics.TOOL_CARDS` (tasks, capabilities,
   required inputs, outputs, limits). All three, or the tool is unreachable /
   unselectable.

## Required declaration fields (TOOL_CARDS)
`tasks` (subset of classification/regression/forecasting/ranking/clustering/other),
`capabilities`, `requires_columns`, `outputs`, `read_only: True`, `modifies: False`,
`limitations`, `evidence`. Selection (`select_tools`) excludes a tool when its
task mismatches, a capability is missing, or a required input is absent — with
a recorded reason, never silently.

## Rules
- Read-only: never modify artifacts, models, or the database except through
  the registry's recorded action path.
- Column names are parameters with sane defaults, never hardcoded project columns.
- Metrics recompute from the artifact; prose never invents numbers.
- Leakage-style tools report association + provenance; confirmation requires
  pipeline evidence and stays a hypothesis status, never a tool verdict.
- Add regression tests that run the tool on a seeded fixture and assert the
  known injected effect (see `tests/test_universal_projects.py`).
