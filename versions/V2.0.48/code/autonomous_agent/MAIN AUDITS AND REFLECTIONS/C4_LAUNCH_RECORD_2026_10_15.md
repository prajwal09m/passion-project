# Campaign 4 Launch Record — 2026-10-15

**Status: LAUNCHED AND EXECUTING.** This record documents the actual launch of
Campaign 4 through the project's existing continuous-loop mechanism, the first
two completed executions, the bounded run's clean termination, and the
post-launch integrity re-verification.

## 1. Run identification

| Field | Value |
| --- | --- |
| Campaign ID | `campaign-4-continuous-2026-10-14` |
| Config SHA-256 (pinned in loop state) | `33334d14a2140ab149669f12d4ddedf15f9bc427fa1fcce91f971f8a97471e9d` |
| Config file (live) | `autonomous_agent/state/campaign_config.json` |
| Config file (frozen artifact) | `stat_validation_h10/freeze_2026_10_14/CAMPAIGN_4_CONFIG_FROZEN_2026_10_14.json` |
| Byte-identical to frozen artifact? | YES (both hash to the pinned value) |
| Seed base | 20261014 |
| Started at | 2026-10-15T00:11:07+00:00 |
| Launch log | `autonomous_agent/state/campaign4_launch_2026_10_14.log` |

## 2. Bounded launch run (verified end-to-end)

The launch ran as a bounded run (`max_cycles=7`) to prove the complete
loop lifecycle under the frozen config. It terminated cleanly:

```json
{"campaign_id": "campaign-4-continuous-2026-10-14", "cycles": 7,
 "executions_done": 2, "status": "STOPPED", "stop_reason": "MAX_CYCLES"}
```

Final loop state (2026-10-15T01:26:50+00:00): `STOPPED`, `MAX_CYCLES`,
`executions_done: 2`, `consecutive_failures: 0`, `last_error: null`, loop
process exited normally. Zero execution failures.

Note: the first cycle's three proposals were refused by the bias governor
(`BIAS_QUOTA`) — normal governor churn against the global signature caps,
not a blockage; the offline probe showed seeds 20261019/20261020 each
yield an admissible proposal, and the loop reached them by walking
`seed_base + cycle`.

## 3. Executions completed under the frozen config (both PROMOTED)

Both Campaign 4 executions traversed the full legal lifecycle with every
gate green and the holdout never opened:

### exp-proposal-5d52d16b94ca (prop-5d52d16b94ca-1)

- `PROPOSED → VALIDATING` 00:18:09
- `VALIDATING → ACCEPTED_FOR_EXECUTION` 00:18:12 (`POLICY_AUTO_APPROVAL`,
  policy `revalidate_at_approval@1.0.0`)
- `→ COMPILED → EXECUTED` 00:18:22
- `EXECUTED → ADJUDICATED` 00:51:10 (`GATES_PASSED`, artifact tree
  `7cc1bdc76ef9…`)
- `ADJUDICATED → PROMOTED` 00:52:32
- Candidate version: `V2.0.35-candidate`; checks: unit, data_integrity,
  leakage, walk_forward, robustness, evaluation — all PASS;
  `holdout_status: SEALED`; `blockers: []`; result SHA-256 (tree):
  `7cc1bdc76ef986c03c3c901c18da285e8c0b28087c7941f2521bfeb8c1069c90`

### exp-proposal-4fdf6dd35236 (prop-4fdf6dd35236-1)

- `PROPOSED → VALIDATING → ACCEPTED_FOR_EXECUTION` 00:18:12–00:18:16
  (`POLICY_AUTO_APPROVAL`)
- `→ COMPILED → EXECUTED` 00:52:48
- `EXECUTED → ADJUDICATED` 01:25:28 (`GATES_PASSED`, artifact tree
  `3071f5d695e7…`)
- `ADJUDICATED → PROMOTED` 01:26:47
- Candidate version: `V2.0.36-candidate`; checks: all six PASS;
  `holdout_status: SEALED`; `blockers: []`; result SHA-256 (tree):
  `3071f5d695e764ba95dd6bf73262e96095f7380fae3e0ed5d8938ac0d44ffc59`

Artifacts for both experiments are preserved under
`autonomous_agent/candidates/<experiment_id>/` (`spec.json`, `result.json`,
and the hashed `workspace/` trees listed in each result's `artifacts` map).

## 4. Post-launch integrity re-verification

- Live config vs frozen artifact: byte-identical (pinned hash matches both).
- `test_freeze_integrity.py`: after launch the live `loop_state.json` is
  Campaign 4's, so `test_campaign_3_state_is_archived_and_stopped` was
  updated to read the Campaign-3 preserved state from its archive
  (`loop_state.campaign-3-continuous-2026-10-05.final.json`, verified
  campaign-3 / STOPPED / 38 executions, never rewritten) while still
  asserting the live state is campaign-4. Suite: **20/20 OK**.
- Full repository suite after all post-launch changes: **367 tests OK**
  (`python -m unittest discover`, exit 0).

## 5. Continuation

The bounded launch run stopped by design at `MAX_CYCLES`. Campaign 4's
configuration, ledger, evidence view, and holdout are intact and
append-only; a subsequent run with a larger cycle budget continues the
same campaign id, ledger, and governor state (cycle counters are
cumulative across restarts).

## 6. Governance trail (pointers)

- Freeze: `stat_validation_h10/freeze_2026_10_14/` (builder, frozen config,
  sidecar hashes)
- Freeze record: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/C4_FREEZE_RECORD_2026_10_14.md`
- Gate-4 implementation report:
  `autonomous_agent/MAIN AUDITS AND REFLECTIONS/H10_SIGNFLIP_PORT_IMPLEMENTATION_REPORT_2026_10_14.md`
- Launch gates: `stat_validation_h10/launch_gates.json` (gate 4 recorded;
  readiness check returned READY / exit 0 before launch)
- H-10 decision record: unsigned (`H10_DECISION_RECORD_AWAITING_SIGNATURE.md`);
  the p-value allowlist remains empty — campaign-end multiplicity
  resolution stays fail-closed/inconclusive until the owner signs and the
  sign-flip method is adopted. This does not gate execution.
