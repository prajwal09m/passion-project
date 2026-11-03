# M22 Independent Post-Fix Diagnosis — Is the M21 Failure Resolved?

Read-only stage. No code modified; no live calls. Inspected: the M22
diff (`loop.py`, `driver.py`, `resume.py`, `planning.py`), the
`m21-music-01` artifacts, and the 656-test offline evidence.

## 1. Original failure mechanism

Silent model (0 hyps, 0 calls) → `loop.py:751` round break → repair
made the empty prose valid → `driver.py:235` mistook the valid report
for completion → run `completed` with zero evidence, decision
`completed-turn`, `incomplete_progression:false`.

## 2. M22 changes (verified in source)

- Evidence floor (`driver.py:235-248`, mirrored `resume.py:256-269`):
  the valid-summary break fires only with ≥1 `ran` action; otherwise
  the loop continues and a `decision_prompt` records why.
- Zero-evidence runs end `inconclusive`, never `completed`
  (`driver.py:~291-302`, `resume.py:~293-303`), with a recorded event.
- Total inaction flagged (`loop.py:~1195-1210`): `total_inaction` +
  4-state `progress` on every turn decision; incomplete true when a
  do-nothing turn carries no recorded next step.
- Bounded recovery (`loop.py:~751-800`): one prose-only resume nudge
  per turn, only when nothing exists on record; normal budget gates
  apply; M8/M19/M20 flows untouched (valid-summary turns, prose-with-
  hyps repairs, empty fallbacks never match the gate).
- Honest stop rationale (`planning.py:92-98`): empty roster reports
  "no hypotheses on record", not "resolved".

## 3. Independent verification results

Replayed the M21 shape offline against the patched code: the silent
turn is flagged, recovery fires once, persistent silence ends
`inconclusive` via the stopping rule (not false completion), and
recovery-to-evidence completes normally. All 10 validation scenarios
pass; 656/656 green.

## 4. Remaining vulnerabilities

- NONCRITICAL: a turn of only dedup-reused calls + valid summary can
  still trip the historic break with zero *new* evidence — but reuse
  implies prior recorded output, and the end-gate still forces
  `inconclusive` when zero `ran` actions exist. Defense in depth
  holds; no completion bypass found.
- NONCRITICAL: `/api/.../meta-turn` invokes the turn loop without the
  driver floor — examined: it produces no run status or completion, and
  now returns the inaction flags, so consumers see the state. Not a
  bypass path to false completion.
- UNVERIFIED: live-model response to the nudge; silence recurrence
  rate; nudge wording effectiveness. Requires an authorized live run.
- The `sufficient-evidence` proxy is turn-level and heuristic; the
  resolution contract remains the authority for conclusions.

## 5. M19/M20/M21 comparison

M19 decline, M20 repair, M21 empty-fallback, and all legacy adapter
contracts behave identically (suites green; the single M7 assertion
change swaps a demonstrably false "resolved" for the honest text and
re-pins "resolved" where resolution is real). M19's successful
investigation pattern (propose → discriminate → verify) is unaffected:
recovery only fires when nothing exists at all.

## 6. Final assessment

- Original failure mechanism (valid report mistaken for completed
  investigation): **RESOLVED** — three independent guards (floor,
  end-gate, inaction flag) each suffice; all three are enforced by
  orchestration, not suggested in prompts.
- Repair-shortens-investigation perversion: **RESOLVED** — a repaired
  empty summary no longer terminates the run.
- Silent-model handling: **PARTIALLY RESOLVED** — the system now
  responds, bounds, and honestly reports silence, but cannot compel a
  silent model to work; live behavior unverified.
- M19/M20 preservation: **RESOLVED** (evidence: unmodified suites).
- Whole-project readiness: **UNVERIFIED** and out of scope — this
  verdict covers the M21 failure only.

Model Autopsy can no longer mistake a valid report for a completed
investigation through any path found in this audit.
