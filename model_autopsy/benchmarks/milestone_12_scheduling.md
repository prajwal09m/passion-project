# Milestone 12 Scheduling

Ranked queue, budget-capped, with hard authorization states.
`test_scheduler_refuses_paid_without_approval` proves the key
property end to end (also via the API smoke test): a high-value
paid proposal does not run when no human token is present — it
parks in awaiting-approval with its reason, while offline work
proceeds. No background scheduler exists, so approval cannot be
bypassed by timing.
