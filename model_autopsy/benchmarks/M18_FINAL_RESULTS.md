# M18 — Final Results: Autonomous Scientific Closure

One authorized live run. No retries, no second run. This document is the
complete record.

## 1. Executive summary

M18 fixed the exact architectural reason M17 could not close live:
hypothesis bookkeeping no longer consumes experiment slots, all real
probes share one allocator with a verification hold, and the resolution
contract consumes genuine transition events. Offline, closure is proven
end to end (confirmation, contradiction, and budget-starvation paths).
Live, the run proved Phase 1 under real provider conditions (3
registrations, 0 experiment slots) but did not reach verification: the
provider refused round 2 with HTTP 400, the turn ended honestly, no
diagnostic ever ran, and the finding was preserved as unresolved. Per the
preregistered rule, the integration milestone is **incomplete on the live
leg**. No further runs were launched.

## 2. M17 defects addressed

1. **Hypothesis registration consumed experiment slots** — fixed by the
   `accounting.is_experiment` taxonomy + kind-checked dispatch in
   `loop.py`. Live proof: 3 × `propose_hypothesis`, `experiments_used = 0`.
2. **No verification-capacity guarantee** — fixed by the candidate-gated
   verification hold in `accounting.py`, honored by loop, reservation,
   and skeptic. Proven offline (6th non-verification spend refused;
   verification consumes the held slot).
3. **Resolution contract consumed snapshots** — fixed by
   `resolve.collect_transitions()` + tightened `contract()` status rule.
   Live proof: the run's contract reports `unresolved` (correct — nothing
   advanced), where M17's snapshot input reported `partially-resolved`.

## 3. Architecture changes

- NEW `backend/live/accounting.py`: taxonomy, single reserve/settle/
  release choke point, hold policy, `experiment_ledger` purpose records.
- `meta_api/loop.py`: hypothesis ops bypass experiment budget; call-list
  slicing governed only by tool-call budget; per-dispatch allocator
  enforcement with recorded refusals.
- `live/reserve.py`, `live/skeptic.py`, `live/verify.py`: all spend via
  `accounting`; dedup reuses release; skeptic/reservation honor the hold;
  verification consumes it.
- `research/resolve.py`: ADD `collect_transitions()`; `partially-resolved`
  only on genuine advancement to supported/rejected.
- `live/verify.py`: contract fed by real transitions; hypotheses re-read
  post-probe.
- `live/governor.py`: `CAPS["cost_usd"]` 0.40 → **0.65** (M18-authorized
  single-run ceiling; all other caps unchanged).
- `api.py` + `Workspace.tsx`/`api.ts`: read-only scientific-closure view
  over recorded backend data.

## 4. Exact live caller paths

- `driver.run_live_investigation` → `preflight` (go) → `build_live_context`
  → `meta_loop.run_meta_turn` (selection → model rounds → linker →
  `maybe_reserve_end_of_turn` → `skeptic.review` → grounded summary) →
  `verify.maybe_verify` → `resolve.contract` → `engine.build_report` /
  `finalize` → `adapter.meta_report_to_eval` → `scorer.score` →
  `recorder.finalize_run`. The 400 terminated the turn inside
  `run_meta_turn` round 2; every downstream step still executed on record.

## 5. Hypothesis-versus-experiment accounting before and after

- Before (M17 live): 3 proposes + 1 diagnostic + 1 reserved + 1 skeptic =
  6/6, verification starved by bookkeeping.
- After (M18 live): 3 proposes = **0/6**; the model simply chose no
  diagnostic before the provider refused round 2. The structural tax is
  gone — verified live, not just offline.
- Offline loop test: propose + diagnostic in one real turn →
  `experiments_used == 1`, `tool_call_count == 2`.

## 6. Experiment allocation and verification reservation

Live: 0 spent, hold never needed (no candidate ever existed). Offline
simulation through the real allocator: worst-case planned spend
(diagnostic + reservation + skeptic + verification) = 4/6 with 2 slots
margin; a 6th non-verification spend with a candidate on record is
refused with the hold reason while verification still dispatches.

## 7. Reservation execution

Live: never ran. The turn returned `meta_unavailable` inside round 2, so
control never reached the end-of-turn `maybe_reserve_end_of_turn` (no
reservation event exists in the run record). No reservation was refused
by budget; it was pre-empted by provider failure. Offline:
`maybe_reserve_end_of_turn` fires after round-1 hypotheses (reserved +
executed, 1 slot), with the exactly-once guard holding across turns.

## 8. Skeptic challenges and responses

Live: none (no evidence existed to challenge). Offline: blocking
challenges persist, gate `supported`, resolve via budgeted probe or
preserved dissent; skeptic probes share the allocator and honor the hold.

## 9. Verification eligibility and execution

Live: no eligible hypothesis (zero evidence on record) → honestly skipped
("no eligible hypothesis"), 0 slots spent, finding preserved as
unresolved. **Verification was not executed live.** Offline: eligible
candidate → independent `slice_gap_significance` probe dispatched,
checklist executed, confirmation recorded with `resolve.contract`
status `confirmed`.

## 10. Independent tool identity and evidence

Live: n/a (no probe). Offline: `slice_gap_significance` (permutation null,
seeded) as the ranking family's second probe — different method and code
path from `ranking_slice_diagnostics`; same-tool reruns refused and never
counted.

## 11. Adversarial checklist results

Live: not run (nothing to review). Offline: `review_claim` upheld on the
corroborated candidate (n ≥ 30, methodology stated, evidence linked,
numbers reproducible); downgrade path covered by the contradiction test.

## 12. Resolution transitions and final statuses

Live: `collect_transitions` → [] (no status ever moved; hypotheses stayed
`proposed`) → contract `unresolved`, conclusion "no finding met the
verification bar". This is the fixed behavior: M17's snapshot input would
have said `partially-resolved` here. All three hypotheses remain
`proposed`/unresolved with zero evidence refs — accurately reflecting
that the investigation never got past registration.

## 13. Confirmed findings

**None — correctly.** Corroboration bar (≥2 independent tools + checklist)
was not met for any hypothesis. `confirmed_findings` is empty.

## 14. Unresolved findings and limitations

- H1 uniformity ("differences are small/noise"), H2 selective
  ("degraded for new-catalog slice"), H3 hygiene ("artifacts, not model
  failure"): all `proposed`, untested, preserved with model rationales.
- The run never measured anything: no diagnostic, no evidence, no
  transitions. The limitation is provider availability, not budget.

## 15. Exact test results

`py -m pytest model_autopsy/tests -q`: **520 passed, 0 failed**
(495 pre-existing + 25 new M18). `npx tsc --noEmit`: exit 0.
`npm run build`: ✓ built. `test_api.py`, `test_m9_challenge.py`,
`test_m10_validation.py`, M8/M17 budget suites: green. Separation grep:
no sealed/ground-truth refs in `live/`/`meta_api/`. Credential grep:
clean. Docs: `M18_ARCHITECTURE_AUDIT.md`, `M18_OFFLINE_VALIDATION.md`,
`M18_LIVE_READINESS.md` (GO), this file.

## 16. Token and financial usage

Input 0 / cached 0 / output 0 / total 0 of 50,000. Spend **$0.0000** of
$0.65 (0%). Rounds 1/3, experiments 0/6, attempts 2/12. Pre-run worst-case
projection $0.1172 ≤ $0.65. No cap approached; headroom gate never
triggered.

## 17. M17 versus M18 comparison

| Integration point | M17 live | M18 live |
|---|---|---|
| Hypothesis bookkeeping cost | 3 slots | **0 slots** |
| Reservation fires | yes (1 slot) | pre-empted by provider 400 (0 slots) |
| Denier-supports | 0 | 0 (no evidence at all) |
| Verification caller reached | yes, declined (6/6 spent) | reached, declined (no candidate) |
| Resolution honesty | overstated (snapshot) | **correct (`unresolved`)** |
| Spend | $0.0226 | **$0.0000** |
| False positives | 0 | 0 |

## 18. Remaining architectural weaknesses

1. **In-turn 400 has no fallback.** The full-context fallback triggers
   only for cross-turn chaining at round 1 (`round_no == 1 and
   previous_response_id`); a round ≥ 2 failure with a chain id in play
   kills the turn even when budget and rounds remain. This is what ended
   the M18 run. Pre-existing gap (request construction untouched by M18),
   now precisely characterized: outputs-only round-2 input +
   `previous_response_id` → provider 400 → `meta_unavailable`.
2. Candidate emerging exactly on the 6th experiment still starves
   verification (hold cannot precede the candidate) — honest skip.
3. The model may propose without ever diagnosing (observed live); the
   selection brief urges the top diagnostic first but cannot compel it.
4. Single scenario, single model, one live run.

## 19. Honest milestone verdict

- Offline closure demonstrated: **yes** (confirm / contradict /
  budget-starved paths, 25 tests).
- Live integration demonstrated: **partially** (accounting fix + honest
  contract proven live; reservation/skeptic/verification unexercised live).
- Live verification executed: **no**.
- Live independent corroboration: **no**.
- Scientific discovery confirmed: **no** (nothing measured live).

**M18 is incomplete as a live-closure milestone.** The accounting
bottleneck that defined M17 is fixed and live-proven at the bookkeeping
layer, but autonomous scientific closure was not demonstrated end to end
in the live system. No confirmation was manufactured to hide this.

## 20. Capability ledger

- **Implemented:** authoritative experiment accounting, verification hold,
  transition-based resolution, closure dashboard/API, $0.65 governance.
- **Offline-tested:** all of the above (520/520) plus e2e confirm /
  contradict / starve paths.
- **Live-executed:** hypothesis registration at zero experiment cost (3
  proposes, 0 slots); honest provider-failure handling; transition-based
  `unresolved` contract. Reservation, skeptic probe, and verification
  probe: **not** live-executed.
- **Independently verified:** offline only (`slice_gap_significance`
  corroboration in controlled tests).
- **Scientifically confirmed:** nothing (live or offline campaign claims
  no finding beyond controlled-test fixtures).
