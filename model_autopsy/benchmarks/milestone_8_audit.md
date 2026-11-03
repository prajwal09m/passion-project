# Milestone 8 — Audit of M7 state (no paid API activity)

Sources: M5/M6/M7 results + validation docs, `live-1e19b2cdedfe`
artifacts + `live.sqlite3`, `backend/{live/{driver,resume,governor},meta_api/loop.py,causal/*,engine.py,tools_registry.py}`,
`tests/test_m{6,7}_*.py`, dashboard `CausalPanel.tsx` + `/causal` endpoint.

## 1. What M7 successfully implemented

- Closed-loop wiring that WORKS live: post-tool auto-linker
  (`causal/linker.py`, 8 generic rules + idempotency guard) invoked
  from `run_meta_turn`; per-turn selection briefs with recorded
  adherence (`selection` events); driver/resume stopping gates;
  `residual_feature_dependence` diagnostic; failed-tool exclusion in
  planning; starter briefs; subgroup family; `experiments_left`
  in-turn cap (post-run).
- Offline proof: 304/304 pytest, tsc 0, vite build ok, 6-scenario
  behavioral harness all-green, causal endpoint 200 with
  feedback/transitions/stopping keys.

## 2. What the live run actually demonstrated

- 2 of 3 hypotheses moved proposed→investigating with cited action ids
  and revisions — first evidence-driven transitions live.
- 6 `selection` events (briefs + adherence verdicts); adherence
  correctly recorded "deviated" twice, though partly the brief's fault
  (missing subgroup family — fixed post-run, unproven live).
- Honest inconclusive (M4 0.61); no false positive on the leakage
  distractor; failed `classification_metrics` call retried with
  corrected args instead of abandoned.

## 3. What failed (with root causes from records)

1. **Experiment cap breached: 8 executed vs 6 max.** Root: the cap
   lived in `Budget.caps` but no pre-execution check consumed it —
   driver checked only rounds, the turn honored only the engine's
   12-tool budget. Post-run `experiments_left` plumbing exists but was
   never live-tested and covers only the happy path (no reservation
   lifecycle, no durability, no concurrency story).
2. **Structured summaries invalid 3/3 turns, 6 failed repairs.**
   Mechanical cause (verified in `live.sqlite3` seq 16/17, 24/25,
   37/38): each turn ended with a status sentence and no
   `investigation_summary` block; every repair chained
   `previous_response_id` from a response whose tool calls were never
   answered (turn ended) → provider 400 "No tool output found" →
   "repair unavailable". So (a) the model never emits the block
   (contract/prompt weakness), and (b) the repair path is mechanically
   doomed in exactly this shape (no fallback, unlike the turn-level
   chain refusal which HAS one).
3. **Discovery 0.0.** The pooled `classification_metrics` run (AUC 0.97,
   no group columns) could not meet the scorer's `min_group_gap`.
   Per-region AUC was never computed. Contributing causes: brief ranked
   subgroup diagnostics "low" (missing family — fixed post-run but
   unproven), and no coverage layer names the missing measurement.

## 4. What was fixed post-run vs what remains unproven

Fixed + tested offline: `experiments_left` cap, subgroup family,
starter briefs, propose durability commit, failed-tool exclusion.
Unproven live: ALL of the above (none has run against the provider),
plus the repair-path redesign and any coverage layer (not yet built).

## 5. Architectural weaknesses found on inspection

- **Budget is memory-only.** `Budget` counters die with the process;
  only turn-level rollups persist (as events). No reservation concept:
  concurrent dispatches, crash-after-reserve/dispatch, duplicate
  settlement, and ambiguous requests have no representation. Resume
  rebuilds approximately (conservative +1s) rather than exactly.
- **Repair path has no fallback and chains blindly.** Turn-level
  continuation refusal → full-context fallback (robust); repair-level
  refusal → "unavailable", verdict stands (fragile, and the exact shape
  that always occurs when a turn ends with text).
- **No coverage model.** Nothing maps hypothesis family → required
  measurements → collected/missing; selection scores families, not
  evidence gaps.
- **Stopping is budget/terminal-state only.** It cannot recognize
  "no applicable experiment remains" or "two evidence-less turns" —
  the harness stops on step caps, the driver on round caps.
- **Fallback reporting is prose, not a contract.** The adapter falls
  back to `message_text[:800]` with only a boolean validity flag —
  no versioned schema, no required-field/type/ref validation beyond the
  M6 checks, no labeled deterministic fallback from records.
- **`update_with_evidence` confidence is unbounded across turns.**
  Repeated supports keep adding +15 (capped at 90 — fine), but there is
  no neutral/weakening handling and no contradiction decay; acceptable,
  but confidence is more "activity meter" than calibration.

## 6. Extend vs replace

Extend: `governor.Budget` (add reserve/settle/reconcile — keep
ledger/check/record_turn API), `loop.run_meta_turn` (repair path +
experiments_left already threaded), `causal/{selection,planning,
linker,report_validation}` (additive rules/coverage/fallback composer),
`eval/m7_challenge.py` (extend scenarios/dims), dashboard panels.
Replace: nothing — the driver/resume/loop/scorer shapes are sound and
battle-tested; M5/M6/M7 history stays frozen.
