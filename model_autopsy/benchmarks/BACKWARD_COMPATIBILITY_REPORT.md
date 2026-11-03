# Backward Compatibility Report (2026-10-31)

- Full suite: **227 passed, 0 failed** (202 pre-existing + 25 new; exit status 0).
- Legacy investigation path preserved: `build_context` without `project_id`
  uses the exact Demand Zone artifact flow; `load_predictions_csv` still
  defaults to the frozen case-study CSV (fold now optional — additive only).
- Existing diagnostics, tool schemas, registry allowlists, API routes, and
  dashboard pages untouched; Demand Zone case-study endpoints and charts intact.
- Historical evidence: **121/121 manifest artifact hashes re-verify, 0
  mismatches** (covers all prior campaigns plus the final validation runs).
  No benchmark artifact created, modified, or deleted by this work.
- Provider transports (Meta client, Groq harness constants) unchanged; new
  provider adapters wrap or duplicate constants without touching them.
- One deliberate behavior extension: unknown `project_id` on investigation
  creation returns 400 (new validation, no prior behavior).
