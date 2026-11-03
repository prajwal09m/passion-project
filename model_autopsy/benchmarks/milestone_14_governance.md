# M14 Governance (Phase 10)

Unchanged enforcement: OFFLINE/PROPOSAL always allowed,
PROTECTED (paid, destructive) needs a human-issued single-use
token; scheduler defers paid work; UI never mints tokens. All
agents and projects share the atomic live budget with
reserve/settle and crash-safe reconciliation (rounds 3,
experiments 6, attempts 12, tokens 50k, spend $0.40). Portfolio
assess plus checkpoints plus resume plus audit history give
multi-investigation control. Tests: scheduler refusal, budgets,
idempotency in test_m12_lab.py; 439 passing overall.
