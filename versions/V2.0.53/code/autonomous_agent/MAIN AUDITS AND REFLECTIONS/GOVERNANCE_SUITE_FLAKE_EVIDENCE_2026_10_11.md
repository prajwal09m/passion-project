# GOVERNANCE-SUITE FLAKE — CAPTURED EVIDENCE AND DISPOSITION PATH

Date: 2026-10-11 (ET). Status: **DISPOSITIONED — identity captured,
test-only fix applied and verified.** Applied 2026-10-11 under the owner's
explicit execution instruction to fix authorized agent-engineering issues
("identify and fix authorized agent-engineering issues that impede
reliable execution… test changes before integrating"). Fix verified
30/30 targeted runs plus 11 consecutive green full-suite runs (235
tests each: 1 verification run + the 10/10 acceptance loop below).
Production lock code untouched; no gate, threshold, or safety behavior
changed. (Historical superseded status: identity captured; fix defined
but not yet applied.)

## 1. What was previously known

Disclosed limitation in the H-10 decision record and review packet §8: the
governance suite failed 1 run in 10 with the failing test's identity not
captured. This file supplies the identity and evidence trail.

## 2. Reproduction performed (2026-10-11)

Command (repo root): `py -3 -X utf8 -m unittest discover -s autonomous_agent
-p "test_*.py" -t .` — 10 full-suite runs, 235 tests per run.

| Run | Exit | Duration |
|---|---|---|
| 1 | 0 (OK) | 102.97 s |
| 2 | 0 | ~98 s |
| **3** | **1 (FAILED, failures=1)** | 98.38 s |
| 4–10 | 0 (OK) | ~98–103 s |

Observed failure rate: **1/10** — matching the historical report.

## 3. Failing test identity (first capture)

```
FAIL: test_live_lock_blocks_and_stale_lock_recovers
      (autonomous_agent.test_continuous_loop.LoopTestCase)
File "autonomous_agent\test_continuous_loop.py", line 238, in
    test_live_lock_blocks_and_stale_lock_recovers
    self.assertTrue(loop2.acquire_lock())
AssertionError: False is not true
```

Raw log of the failing run: system temp `/tmp/gov_run_3.log` (ephemeral;
this file is the durable record of its relevant content). Full run-exit
matrix: `/tmp/gov_flake_summary.txt` (ephemeral).

## 4. Mechanism (deduced from the code path; not a production defect)

The test writes a lock owned by a **real dead PID** (`cmd /c exit 0`, then
`dead.wait()`, `del dead`) and expects `ResearchLoop.acquire_lock()`
(`continuous_loop.py:191`) to recover it via the provably-dead-owner path
(`ProcessLookupError` / `OSError ESRCH` / winerror 87,1168 → unlink →
retry). On Windows, PIDs are recycled: if any live or access-restricted
process claims `dead_pid` between `dead.wait()` and `os.kill(dead_pid, 0)`
inside `acquire_lock`, the check finds a live/inaccessible owner and
**correctly refuses** to steal a lock it cannot prove dead (returns
`False` at the `return False` fallthrough), so the test's
`assertTrue(loop2.acquire_lock())` at line 238 fails.

This is a **test-fixture race, not a lock-logic defect**: the production
behavior is fail-closed and safe (never steal an unprovable lock; the
`stale_loop_lock` stop condition covers the real loop). Contrast:
`test_core.py:367` uses the sentinel PID `999999999` (outside Windows'
PID space, always provably invalid) and is deterministic.

## 5. Disposition (defined; to be applied with the authorized v1.1.0 work)

Test-only fix; production lock code untouched and not weakened:

- In `test_live_lock_blocks_and_stale_lock_recovers`, after
  `dead.wait()` / `del dead`, **verify the precondition the test
  assumes**: assert that `os.kill(dead_pid, 0)` raises
  `ProcessLookupError`/`OSError ESRCH`; if it does not (PID was recycled),
  spawn a fresh `cmd /c exit 0` and re-verify before writing the lock
  file. No production behavior changes; no assertion is weakened — the
  precondition check strengthens the test.

Acceptance: the disposition is complete when the fix is applied and the
full suite passes 10/10 consecutive runs with the fixed test present.
**Result 2026-10-11: ACCEPTED — runs 1–10 all exit 0 (235 tests each),
zero failures; plus 30/30 isolated targeted runs.** The fix verifies
the provably-dead-pid precondition (os.kill confirmation, bounded
10-attempt retry, explicit assertion on exhaustion) instead of assuming
it; it strengthens the test without weakening production lock safety.

## 6. Boundaries observed

This record is additive (one new file). No test, production file, config,
ledger, champion, or holdout artifact was modified; the suite runs used
temporary directories, and protected pins were re-verified after all 10
runs (campaign_config `1e0e30b8…` OK; record `b9db3233…` OK; holdout
`prospective/` absent).
