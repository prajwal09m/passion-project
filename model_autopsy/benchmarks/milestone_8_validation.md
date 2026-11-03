# Milestone 8 — Full Offline Validation Gate (Workstream F)

All gates passed. No live provider request was sent during validation.

## Backend — 346/346 pytest pass (105s)

Full suite green, including all new M8 tests: 9 budget-safety (atomic
reservation, concurrency races, crash/reconcile conservatism, malformed
state refusal, driver dry-run with experiments=1), 12 structured
reporting (versioned contract, adversarial inputs, fallback
determinism/records-only, end-to-end loop fallback), 9 discovery
(coverage, selection boost, stopping, inapplicable exclusion), 8 linker
(subgroup/calibration/leakage rules on real fixtures), 4 challenge
(12-scenario matrix, provenance, correct-null restraint). Three stale
repair-chaining assertions from the M6 era were updated to the
evidence-backed M8 fresh-context repair contract (production 400s prove
the old chain cannot work); all other assertions kept.

## Frontend

`tsc --noEmit` exit 0; `npm run build` succeeds (2.65s). CausalPanel
extends the existing visual language with coverage, validation, and
evidence for/against tables plus loading/empty/unavailable states.

## Research integrity

- `check_no_truth_leak` passes: sealed `_TRUTH` reachable only by the
  post-freeze scorer; run path and all engine modules clean.
- Evidence provenance: refs valid on all 12 challenge scenarios; zero
  references to failed actions; failed tools recorded and skipped.
- Historical M5/M6/M7 artifacts untouched (only `milestone_8_*` added).
- Reproducibility: deterministic fallback verified across sessions;
  challenge harness re-runnable via `evaluate_all`.

## Security

Credential scan of tracked files clean; new code carries only dummy
placeholders; `.env` gitignored; config reads env without echoing;
no verbose HTTP logging; no secrets in manifests, events, or reports.

## Live-run safety simulation (real driver, scripted provider)

Caps forced to experiments=1: exactly 1 executes, ledger [1, 1],
manifest written, duplicate launch refused, attempts within ceiling,
zero real provider calls. The M7 breach shape (ephemeral per-turn
counter) is gone: a single shared Budget flows driver → loop → resume.

Gate verdict: GO for exactly one authorized live evaluation.
