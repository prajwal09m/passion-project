# Milestone 12 Persistence

Projects survive restarts as JSON documents; every mutation
appends history and rewrites atomically. Crash-recovery contract:
replaying an experiment with an already-seen idempotency key
returns the original record without incrementing usage —
verified by `test_experiment_idempotency_no_double_count`.
Checkpoints store opaque resumable state alongside the timeline.
Status transitions are explicit and validated against the five
allowed states.
