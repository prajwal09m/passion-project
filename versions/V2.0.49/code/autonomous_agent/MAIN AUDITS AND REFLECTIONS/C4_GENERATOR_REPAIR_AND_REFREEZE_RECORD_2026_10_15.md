# Campaign 4 — Generator Repair and Re-freeze Record — 2026-10-15

Owner directive: **"Campaign 4 — Repair Proposal Exhaustion and Resume
Execution"** (2026-10-15). This record documents the repaired root cause,
the exact scope of the versioned change, what was preserved, the proof,
and the re-freeze act. It is the evidence path referenced by
`launch_gates.json` → `freeze_approved._re_freeze_2026_10_15`.

## 1. Root cause (verified from primary artifacts)

The bounded launch run of 2026-10-15 stopped after 8 cycles with
`PROPOSAL_EXHAUSTED` at 2/30 executions, 0 failures. Diagnosis:

1. **Doomed creations (defect).** The falsification-share floor
   (`min_falsification_share = 0.35`) refuses every non-falsification
   proposal while the share is below the floor. All 24 Campaign-4
   refusals carry reason `BIAS_QUOTA` with the identical detail
   ("accepting confirmatory/exploration keeps falsification share at
   0.08 < required 0.35"). The generator ranked and created those
   candidates anyway; refusals consume permanent direction/class budget
   by design, so the campaign burned **validation 12/12** and
   **exploration 9/9** on proposals that were provably refusable at
   creation time. The OBS-2 guard covered only *budget*-doomed
   creations, never the share-floor/replication-cap surface.
2. **Unreachable falsification framing (defect).**
   `regime_split_analysis` and `target_horizon_robustness` declare
   `falsification_capable=True`, but shipped with
   `default_class="exploration"` and `_OPPOSITE_CLASS` maps
   exploration→exploration, so the falsification framing was
   structurally unreachable. The reviewed
   `HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md` table (pinned
   `094827b0`) assigns **both primitives the falsification class** —
   the implementation deviated from the reviewed design. Their
   semantics support falsification framing: each frozen ladder is an
   intersection–union test whose failing cell refutes the robustness
   claim, and the regime/horizon families feed the campaign-end Holm
   refutation test.
3. **Exhausted signature space (constraint).** Of the 64 candidate
   grid cells outside the direction-capped `validation` direction, 53
   were already asked (92 asked signatures globally, 42 from Campaign
   3) and 8 recipe-excluded; the 3 remaining cells were
   exploration-framed (blocked by both class budget and share floor).
   No falsification-framed signature remained, so the share could never
   rise: a deadlock, not a transient.

## 2. The repair (smallest defensible, versioned)

| Component | Version | Change |
|---|---|---|
| `proposal_layer/generator.py` | generator **1.0.0 → 1.1.0** | (a) Pre-creation governor guard: `_build_candidates` projects the post-creation quota state (`_project_quota_state`) and runs the governor's own `check_accept` before a candidate is ever ranked; (b) `generate_proposals` re-projects **cumulatively** over the cycle's selections so creation and validation can never disagree. |
| `proposal_layer/generator.py` | generator 1.1.0 | Candidate space: `GRID_INT_CANDIDATES["n_boot"]` gains **2000**, completing the reviewed s/m/l bucket vocabulary that `schema.bucket_n_boot` already defines as design-identity-significant (500=s, 1000=m, 2000=l). In-bounds for every primitive's declared `ParamSpec`; no new config key, no new code path; satisfies the H-10b n_boot ≥ 1000 floor. |
| `proposal_layer/primitives.py` | library **1.1.0 → 1.2.0** | `default_class` corrected to the reviewed plan table for `regime_split_analysis` and `target_horizon_robustness` (exploration → **falsification**). `_OPPOSITE_CLASS` untouched; `point_in_time_data_audit` (not falsification_capable) untouched; no param, bound, ladder, family, margin, or gate changed. |
| `proposal_layer/schema.py` | — | Version constants + rationale comments only. |

Explicitly **not** done: no change to the 0.35 floor, the six promotion
gates, recipe exclusions, the statistical method (sign-flip + Holm with
the recorded Case-A flip draw), any stop rule, any budget, or any
prior adjudication. `_OPPOSITE_CLASS` was not edited; exploration was
not relabeled wholesale (only the two primitives the reviewed plan
assigns to falsification, both `falsification_capable=True`).

## 3. Proof

- **Targeted regression tests** — `autonomous_agent/test_generator_repair.py`,
  **20 tests OK**, covering all five required groups:
  1. doomed candidates rejected before creation (share floor +
     replication cap; guard refuses exactly what validation refuses,
     same `BIAS_QUOTA` reason; cumulative per-cycle mirror),
  2. a genuinely admissible falsification candidate is generated when
     the approved space contains one (and no blind relabel of
     non-capable/neutral classes),
  3. asked signatures, permanent refusal accounting, direction/class/
     total budgets, signature cap, and recipe exclusions all still
     enforced,
  4. with no admissible candidate the loop still stops honestly with
     `PROPOSAL_EXHAUSTED` (0 executions, 0 records created), and
     budget-only exhaustion also still reports honestly,
  5. grid expansion stays inside every declared bound with distinct
     s/m/l buckets.
- **Prior-evidence preservation** — `test_freeze_integrity.py` gains
  `RepairPreservesPriorEvidence`: both pre-repair promotions remain
  recorded verbatim (artifact trees `7cc1bdc7…` and `3071f5d6…`), both
  results still carry six PASS gates + `holdout_status: SEALED`, and
  live loop state still counts every prior execution.
- **Full regression suite** on the repaired tree: **390 tests, OK,
  exit 0** (two checks changed as required by the requested behavior,
  each explained inline: the stage-4 grid-size expectations grew with
  the sanctioned candidate-space expansion; the primitives-comment
  proximity window in the R-3 grant test was satisfied by moving the
  comment above `primitive_id=` — the assertion itself is unchanged).
- **Real candidate pool inspected** (read-only): `candidates_remaining
  = 37`, all falsification-framed, across six directions with live
  budget; 37 share-doomed confirmatory framings blocked pre-creation
  (`excluded_governor_reasons: ['BIAS_QUOTA']`); asked 53 / recipe 8
  exclusions intact; budgets untouched. Three generated payloads
  passed full validation (`passed: True`, `status_target: None`)
  against the real ledger — the repair creates **legitimate choices**,
  it does not merely hide refusals.

## 4. Capacity assessment (honest ceiling)

Remaining proposal budget is **19** (45 − 26 consumed; budgets are
never reset). Therefore the maximum reachable outcome under the frozen
budgets is **21/30 executions** (2 promoted + ≤19 new). Reaching 30
would require amending the frozen 45-proposal budget — which the
authoritative readiness check hard-pins at "30 executions / 45
proposals" and which the directive forbids resetting. This ceiling is
reported, not worked around. To unlock the share floor, ≥11 of the new
proposals must be falsification-class (share (2+f)/(26+f) ≥ 0.35 →
f ≥ 11); 37 admissible falsification candidates exist and the
falsification class budget allows 16 more, so the unlock is feasible
inside the remaining 19 slots, after which one confirmatory slot
(portfolio minimum) and further falsifications fill the rest.

## 5. Re-freeze act

- Built by `stat_validation_h10/freeze_2026_10_15/refreeze_campaign_4_config.py`
  (exit 0) from the byte-verified 2026-10-14 frozen config (digest
  `33334d14…` confirmed before use).
- New frozen config: `stat_validation_h10/freeze_2026_10_15/CAMPAIGN_4_CONFIG_FROZEN_2026_10_15.json`
  — **sha256 `f529370822defd45c76f8e16e8b75132b32f4f5b148fc86805ff1905e8697421`**,
  protocol fingerprint `49d73f672ae237a9…`, placeholder scan clean.
- **Preservation verified programmatically before install:**
  `multiplicity_policy` (including the Case-A flip draw — seed
  `2613983839999682065`, rows hash `c9b6afb0…`, never redrawn),
  `policy_overrides` (budgets, floor 0.35), `execution`, the 16
  `stop_conditions`, `holdout_policy`, `duplicate_policy`,
  `outcome_blindness_policy`, `portfolio`, `approval.policy`,
  `campaign_id`, `seed_base`, `immutable` — all byte-identical; the
  only added top-level key is `refrozen_at`; the only changed
  `versions` keys are the three intended ones.
- **Installed** (exit 0): live config + sidecar replaced, and the
  loop-state `campaign_config_sha256` pin deliberately re-pinned to
  `f5293708…` (the pin's purpose is tamper detection; this re-pin is
  part of this recorded act, exactly once per freeze, and no other
  loop-state field was touched — `executions_done: 2` carried
  forward).
- The integrity-test config pin updated `33334d14` → `f5293708` with an
  inline comment (same once-per-freeze convention used at the 2026-10-14
  freeze).

## 6. Capacity re-freeze (same day, owner directive "Continue Campaign 4 Through Completion")

The repair restored admissibility; the remaining binding constraint is
**capacity**. With the frozen ceilings the campaign could reach only
~19-21 of 30 executions (class budgets falsification 18 with 2 used,
confirmatory 12 with 11 used, exploration 9 with 9 used; proposal total
45 with 19 slots left). Under the owner's directive to complete the
30-execution target through the normal freeze rules, a **capacity-only
re-freeze** was applied:

- `policy_overrides.max_total_proposals` 45 → **64**;
- `class_budgets.falsification` 18 → **34**, `class_budgets.confirmatory`
  12 → **14** (replication 6 and exploration 9 unchanged).

This is a ceiling change, never a reset: every already-created record —
including all 29+ pre-repair and post-repair proposals and every
refusal — continues to count against the raised ceilings. Verified
byte-identical by the build script before install: `multiplicity_policy`
(including the Case-A flip draw), the 0.35 share floor,
`max_replication_share`, `execution` (30), all 16 stop conditions,
`holdout_policy`, `duplicate_policy`, `outcome_blindness_policy`,
`portfolio`, `versions`, `notes`, `seed_base`, `immutable`.

Built by `stat_validation_h10/freeze_2026_10_15/refreeze_campaign_4_capacity.py`
from the live 2026-10-15 config (pin `f5293708…` verified first):
`CAMPAIGN_4_CONFIG_CAPACITY_FROZEN_2026_10_15.json`, sha256
**`b40c9c01cdd426c15f4a21d656de762d1ad20eb1d3887a8384b767be386669d6`**,
protocol fingerprint `0c701c41cacf5662…`. Installed atomically (write
+ `os.replace`) while the relaunched loop was mid-execution, with a
deliberate loop-state config re-pin; the in-flight execution
(`exp-proposal-006cd3433838`) was unaffected and the loop re-reads the
policy each cycle. The readiness budget expectation was updated in step
(`30/64`) with the amendment cited inline, and the integrity-test
config pin re-pinned `f5293708` → `b40c9c01` under the same
once-per-freeze convention.

### 6b. Second capacity re-freeze — interruption slack (same day)

The relaunched loop recorded one `EXECUTION_INTERRUPTED` attempt when
the earlier agent session was cut off mid-execution. Per the standing
budget accounting (H-8), interruptions consume budget slots, so a
campaign of 30 *completed* executions needs the ceiling to cover one
interrupted attempt. A second capacity-only re-freeze applied the
smallest sufficient delta:

| Knob | Before | After |
|---|---|---|
| `execution.max_total_executions` | 30 | **31** |
| `max_total_proposals` | 64 | 64 (unchanged) |
| class budgets | falsification 34 / confirmatory 14 / exploration 9 / replication 6 | unchanged |

The tool now accumulates amendment provenance instead of overwriting
the section-6 delta text, and its idempotency guard accepts
execution-only changes. Same preservation set as section 6, verified
byte-identical before install (0.35 share floor, six gates, 16 stops,
duplicate layers, statistical method + Case-A flip draw, holdout
SEALED, all consumed records still counted). Installed atomically
mid-run; loop carried (cycle 11, `executions_done` 3). New pin
**`3e6a5ae447ad5b7e…`**, re-pinned in the integrity test and the gate-7
readiness literal (`31/64`). Verification after install: 390 tests
OK, readiness READY (exit 0 on both).

**Stop and recovery (same day, recorded for completeness).** The
mid-run install raced the running loop: the loop process rewrites
`loop_state.json` from its in-memory pin each heartbeat, so the
re-pin applied at install was clobbered and the loop stopped at
22:05:31 UTC with `CAMPAIGN_CONFIG_CHANGED` (the freeze-integrity
guard working as designed — config `3e6a5ae4…` vs stale pinned
`b40c9c01…`). The cycle's execution (`exp-proposal-4dbe8e8ccc66`)
had already completed and adjudicated normally before the stop;
`executions_done` = 4, no slot lost, no data touched. Recovery:
with the loop confirmed dead, `loop_state.campaign_config_sha256`
re-pinned to `3e6a5ae4…` (verified against the sidecar) and the
loop relaunched as run4 (`campaign4_run4_2026_10_15.log`), which
started with the correct pin at cycle 12. Lesson recorded: capacity
installs must either be applied while no loop process is alive or
followed by a stop → re-pin → relaunch sequence; a bare mid-run
re-pin does not survive the loop's heartbeat write.

## 7. Authorization basis

The owner's directive of 2026-10-15 reaffirms the previously recorded
authorizations (`OWNER_AUTHORIZATION_TO_PROCEED_2026_10_12.md`,
`C4_FREEZE_RECORD_2026_10_14.md`, gate 8 `launch_authorized`) wherever
they validly cover the action, and explicitly instructs automatic
re-freeze + launch once the mandatory prerequisites are genuinely
satisfied. No signature, approval, or review was simulated: the
substitute-review D2 record and all human gates remain exactly as
recorded on 2026-10-14.
