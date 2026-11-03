# Integrated M9–M12 Validation Gate (offline)

Date: 2026-11-01. Every check executed; exact results below.

## Backend: 407 passed, 0 failed
- Full suite `model_autopsy/tests` (incl. groq/meta-env/readiness/
  live-investigator): 355 + 52. Zero skips hiding failures.
- M7 closed-loop (13, incl. rewritten double-contradiction + 2
  regression guards), M7 challenge, M8 (linker/challenge/
  discovery/reporting/budget), M9 (all six suites),
  M6 causal, research lab, eval independence, M10 (6),
  M11 (7), M12 (7), flagship demo (1).

## M9 frozen behavior preserved
Eight scenarios re-run after the attribution fix: identical
specs, statuses, transitions, and means (invention/planning/
attribution 1.0, discovery 0.938, causal 0.75, confounder 0.625).
`milestone_9_finalization.md` is the frozen reference.

## Frontend
- `tsc --noEmit`: exit 0.
- `npm run build`: exit 0 (5.90s; chunk-size warning only).

## Security
- `.env` git-ignored; `.env.example` placeholder empty.
- No secret values in tracked files (config only reads keys).
- No credentials in logs (usage figures are provider-reported
  aggregates, never keys).

## Research integrity
- M4 separation audit: ok. M10 unseen audit: ok. M9 leak check: ok.
- No historical artifacts modified (frozen CSVs untouched;
  `stable_output.csv` + demo fixtures are new files with their
  own generators).

## Budget safety
- M11 ledger: 4-thread × 5-reserve vs cap 10 → used exactly 10.
- M8 budget: dry-run cap test passes.
- M12: paid proposals park without human tokens (unit + API).
- No code path mints authorizations except the human surface.

## Integrated flagship demo (offline)
Unfamiliar ranking project (prime-slice inversion, unseen by
both systems): single discovered (score ≥0.5), team ≥ single
with judge verdicts, interruption resume without duplicate
execution. `test_flagship_demo` passes.

## Preflight for the single live evaluation
- All gates above pass. One campaign / one project / ≤3 rounds /
  ≤6 experiments / ≤12 attempts / ≤50k tokens / $0.40 enforced by
  the existing governor + preflight. No prior M9–M12 live run
  exists in benchmarks/live_runs for this program.
- Credentials load via the existing secure mechanism; nothing
  is displayed, logged, or committed.

GATE STATUS: GO for exactly one live Meta evaluation.
