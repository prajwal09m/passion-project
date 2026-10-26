# Campaign 5 Launch Record — 2026-10-23

**Status: LAUNCHED AND EXECUTING under the wired code.** This record documents
the Campaign 5 launch: the pre-launch repair State, the Campaign 4→5
rollover, the first bounded run (and its 11.5-hour falsifier), the mid-flight
cutover to the C5-wired stop enforcement, and post-cutover verification.

## 1. Pre-launch state (completing the freeze work)

| Item | Result |
| --- | --- |
| Authorization record `campaign-5-regime-error-analysis-auth-2026-10-22` | **Zero validator errors** after implementer re-sign (PMED/KMED, rotated HMAC keys from `.env`; re-sign tool `stat_validation_h10/freeze_2026_10_22/record_resign_2026_10_23.py`). Repairs: `disclosure` and `decision_basis` normalized to lists; stale `predeclaration.protocol_sha256` propagated to the record pin `553ac77f…`. |
| Preflight (`check_campaign5_authorization`, full env) | **APPROVED**, `allowed: true`, zero reason codes (recorded in `state/campaign5_preflight_audit.jsonl`). |
| Env wiring | The four preflight variables (`C5_OWNER_HMAC_KEY`, `C5_REVIEWER_HMAC_KEY`, `C5_OWNER_ACTOR_ID=PMED`, `C5_REVIEWER_ACTOR_ID=KMED`) come from `.env`; the shipped loader `stat_validation_h10/freeze_2026_10_22/launch_campaign5.py` parses `.env` into `os.environ` (never echoing values) and fail-closes on missing/leaked/short keys. |
| Config pin | `autonomous_agent/state/campaign_config.json` → `29c905aaf25012cdd20bf21270821f81f5a8e24b46b4a51163d2c65e2e9124a5` (sidecar agrees). |

## 2. Campaign 4 → 5 rollover (campaign_rollover precedent)

- C4's live `loop_state.json` and `loop_events.jsonl` verified **byte-identical**
  (SHA-256) to the copies in `CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16/` before any
  change.
- A `campaign_rollover` event was appended to the journal (from-campaign
  `campaign-4-continuous-2026-10-14`, pin `d8bff195…` → to-campaign
  `campaign-5-regime-error-analysis-2026-10-22`, pin `29c905aa…`), then the
  live `loop_state.json` was removed so the loop self-initializes and pins the
  C5 digest (documented C3→C4 freeze precedent).
- Live `loop_state.json` after startup: `campaign-5…`, pin `29c905aa…`,
  `seed_base 20261022`, RUNNING.

## 3. Bounded run (pid 4136, `--max-cycles 120`)

Cycle 1 generated 3 proposals; the first executed proposal was the
purge-sensitivity falsifier `exp-proposal-a9141196f92c` (`prop-a9141196f92c-1`,
arm C→D, n_boot=2000). **It ran 11.5 hours** (00:53:07Z → 12:25:28Z; ~74% of a
core observed; `timeout` in the spec is per-command process-tree enforcement,
not a whole-experiment cap) and adjudicated **GATES_FAILED** — a normal
predeclared falsifier rejection that consumes its execution slot
(`executions_done: 1`, recomputed from the ledger).

## 4. Mid-flight cutover to the wired code

The frozen C5 config declares two stop conditions that had **no enforcement
anywhere**: `regime_predefinition_violation` and `data_snooping_detected`
(the readiness summary listed both as "implement before launch"; they were
not implemented). Enforcement was implemented and is now live:

- New module `autonomous_agent/proposal_layer/stops_c5.py` (standalone; the
  loop remains the only multiplicity importer): declared verdicts map to
  fail-closed stops; ordinary accept/reject verdicts never match (unit cover).
- `continuous_loop.py`: unconditional adjudication-time halt
  (`C5_SIGNAL_STOP`, durable-first ledger row, same contract as the v1.1.0
  audit stops) plus a declaration-scoped restart guard
  (`_enforce_c5_signal_stops`). Inert for every pre-C5 design (no payload
  carries the verdicts).
- The old process was ON (pre-wiring code); because it was mid-long-execution,
  a recorded watcher script
  (`stat_validation_h10/freeze_2026_10_22/restart_into_wired_c5.py`) was used
  to switch over at a cycle boundary. During that handoff the old process was
  abandoned mid-cycle after the adjudication had been durably recorded
  (no ledger damage; the loop's restart-safety covers exactly this). The
  details are journaled as the `cutover_relaunch` event.

## 5. Relaunch under the wired code (verified)

New pid **40672**, journal `loop_started`, state RUNNING on the same config
pin `29c905aa…`, cycle 2, `executions_done 1`, preflight **APPROVED**
(`allowed: true`, zero reason codes). Fresh log:
`autonomous_agent/state/campaign5_wired_relaunch_2026_10_23.log`.

## 6. Test surface (all green post-change)

| Suite | Result |
| --- | --- |
| `test_freeze_integrity.py` | **26/26 OK** after era-aware updates: live-config pin re-pinned deliberately `d8bff195 → 29c905aa` (C5 freeze comment trail added); `min_falsification_share` expectations made era-pinned (C4 0.35 / C5 0.3, neither silently relaxed); STOP_ENFORCEMENT grew with the C5 declared stops; new `C5SignalStopBehaviorTests` cover durable-first halt + restart guard + walker inertness for ordinary verdicts. |
| `test_continuous_loop.py` | 14/14 OK |
| `test_stage5_readiness_safety_contract.py` + `test_multiplicity.py` | 57/57 OK |

## 7. Known open defect (documented-and-proceed, owner decision 2026-10-23)

`protocol_fingerprint`/`protocol_sha256 = 553ac77f…` is not reproducible from
the installed content under the recorded method (or ~40 plausible variants),
while the C4 control `b4ced0e0…` verifies against its own content. The value
matches the signed record's protocol pin and every block that carries a pin
carries the same value; the non-reproducibility remains recorded in the
config's `_FREEZE_STATUS.provenance_note_protocol_fingerprint`.

## 8. Governance trail (pointers)

- Re-sign tool: `stat_validation_h10/freeze_2026_10_22/record_resign_2026_10_23.py`
- Launcher: `stat_validation_h10/freeze_2026_10_22/launch_campaign5.py`
- Cutover watcher (recorded handoff): `stat_validation_h10/freeze_2026_10_22/restart_into_wired_c5.py`
- Enforcement: `autonomous_agent/proposal_layer/stops_c5.py` + `continuous_loop.py`
- Launch gates: `autonomous_agent/launch_gates.json` (all decided=true; C5
  entries B1–B7 decided by PMED 2026-10-22)

**Date**: 2026-10-23
