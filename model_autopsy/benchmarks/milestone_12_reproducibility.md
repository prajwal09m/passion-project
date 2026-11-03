# Milestone 12 Reproducibility

Snapshots pin artifact SHA-256, package versions, args, and
result summaries. Grades: exact (same bytes + env + outputs),
approximate (version drift or stochastic internals, with
re-run instructions), unreproducible (artifact changed).
Tested in all three branches. No exactness is claimed where
the environment cannot guarantee it.
