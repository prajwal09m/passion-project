# Milestone 8 — Atomic Execution Safety (Workstream A)

## The M7 breach, honestly stated

M7 capped experiments at 6 but executed 8 live. Root cause, found in the
M8 audit: the Meta turn built an **ephemeral per-turn budget** while the
driver folded usage post-hoc — two counters, each allowing 6, for a real
ceiling of up to 12. The cap existed; the enforcement point was wrong.

## The architectural fix

- **One shared `Budget` object** is constructed in the driver (and in
  resume after reconcile) and passed into every `run_meta_turn`. The loop
  reserves attempts before each request and experiments before each
  dispatch on that object, settling with actuals afterwards. There is no
  second counter: `record_turn(..., fold_work=False)` folds rounds, tokens
  and cost only.
- **Atomic reservation lifecycle**: `reserve` (lock-guarded capacity check
  + hold) → dispatch → `settle` (idempotent; repeats return False) or
  `release` (explicit reason recorded). Ambiguous post-dispatch work is
  never assumed free and never auto-replayed.
- **Durable cumulative accounting**: `to_state()` serializes counters plus
  open holds; `reconcile()` rebuilds from them and counts every open hold
  as spent. Resume refuses to start when reconstruction raises.
- **Retry safety**: every request path (rounds, summary repair, full-context
  fallback) reserves attempts first; bounded policies only; no bypass of
  the manager exists in the loop, driver, or resume code paths.

## Proof (tests: `test_m8_budget.py`, 9 tests)

Two workers racing the last experiment slot → exactly one winner; two
retries racing the last attempt → one winner; crash after reserve and
crash after dispatch both count as spent on reconcile; duplicate settle
is a no-op; release requires a reason and frees exactly once; malformed
or negative state refuses reconstruction; missing provider usage never
reduces counters; reservations breaching any cap raise before dispatch.

## Live-run dry simulation (no network)

`test_driver_dry_run_respects_experiment_cap` runs the REAL driver with
caps forced to experiments=1: the scripted provider proposes two calls,
exactly one executes, the ledger reads [1, 1], the manifest is written,
a duplicate launch on the same directory is refused, and total provider
attempts stay within the ceiling. The M7 breach shape cannot recur:
a second turn cannot mint a fresh counter.
