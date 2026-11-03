# Milestone 12 Dashboard

New Laboratory tab (`Lab.tsx` + `/api/lab/*`): project portfolio
with status/experiment/unresolved counts, per-project agenda and
scheduler tick (offline only), research memory (scope-pinned),
and the M10 unseen corpus index. Pending vs executed is
structural: queued/awaiting-approval vs completed. Loading,
empty, and error states on every panel; no fabricated metrics —
every number comes from the project documents. TypeScript
compiles clean (`tsc --noEmit` exit 0).
