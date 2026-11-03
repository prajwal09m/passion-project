# M18 Phase 0 — Architecture Audit (read-only; no behavior changed)

Scope: trace the live execution path and name exactly why M17 closed
offline but starved live, plus the resolution-contract snapshot defect.
No M9/M10 artifacts touched. Demand Zone AI untouched.

## 1. Live execution graph (money path)

`live/cli.main` → `driver.run_live_investigation` (≤3 outer turns) →
`meta_api/loop.run_meta_turn` (`max_rounds=2` provider rounds) →
`engine.build_report` → `finalize` → `live/adapter.meta_report_to_eval`
→ `eval/scorer.score`. `live/recorder.finalize_run` persists the run dir.

Per-turn order in `run_meta_turn` (`backend/meta_api/loop.py`):
selection brief → `maybe_reserve_end_of_turn` (once per investigation)
→ provider rounds (per-execution budget reserve) → linker auto-link →
`skeptic.review` → grounded summary → summary validation/repair → usage
rollup. Driver folds rounds/tokens via `Budget.record_turn(fold_work=False)`.
After the turn loop, driver calls `live/verify.maybe_verify` once, then
`engine.ensure_finalizable/build_report/finalize`.

Two counters govern capacity, and they are conflated:

- `Investigation.tool_call_count / max_tool_calls` (DB, default 12/12).
  Incremented in `engine.run_tool` for EVERY tool including
  `propose_hypothesis`. Enforced in `run_tool` itself and in loop
  (`remaining = max_tool_calls - tool_call_count`).
- `Budget.experiments_used / caps["experiments"]` (governor, 6).
  Reserved/settled in `loop.py` (~L563: `budget.reserve("experiments",1)`
  for every `call["name"]` including `propose_hypothesis`), in
  `reserve.run_reserved`, `skeptic.review`, `verify.maybe_verify`.
  Enforced via `reserve()` (raises `BudgetExceeded`) and via
  `remaining = min(max_tool_calls - tool_call_count, experiments_left)`.

`record_turn(fold_work=False)` folds only rounds + tokens; attempts and
experiments are settled per-op inside the turn. Correct — no double count.

## 2. M17 defect 1 (primary): hypothesis registration consumes experiments

Exact lines:

- `loop.py` tool-dispatch loop: `for call in calls[:max(0,remaining)]` →
  `_etok = budget.reserve("experiments", 1, note=call["name"])` with no
  tool-kind check → `engine.run_tool(...)` → settle 1. Every
  `propose_hypothesis` call burns one of six experiment slots.
- `engine.run_tool` increments `inv.tool_call_count` for every tool,
  including hypothesis ops. That counter (cap 12) is the attempts-like
  budget; spending it on bookkeeping is tolerable. Spending the 6-slot
  experiment budget on bookkeeping is the starvation bug.

M17 live autopsy (`m17-music-01`, 6/6 spent): 3 × `propose_hypothesis` +
1 model diagnostic + 1 reserved probe + 1 skeptic probe = 6. Verification
correctly identified H2 (selective, 1 moving support, 0 contradicts,
investigating, ranking family) and then honestly declined: "no experiment
budget left". Offline e2e passed only because the offline test drove
fewer model calls and never paid the 3-registration tax through the
budgeted loop path.

Fix (Phase 1): authoritative operation taxonomy in one new module
(`backend/live/accounting.py`): `HYPOTHESIS_OPS = {"propose_hypothesis",
"propose_revision_instructions"}` consume ZERO experiment slots;
everything else that measures/intervenes is an experiment and MUST go
through `accounting.reserve_experiment()` (reserve-or-raise with purpose,
hypothesis link, tool identity). Loop dispatch, reservation, skeptic, and
verification all call it. Dedup reuse releases the hold (already the rule
in loop + skeptic; extend to all paths). Cached results never settle and
never qualify as independent verification (already enforced by
`replication.replicate` same-tool refusal + `verify` post-probe distinct-
tool count; keep). Failed dispatches settle 1 (started = counted, M8
rule); pre-dispatch refusals release. Every experiment records purpose,
hypothesis relationship, tool identity, status, and budget charge in the
event payload + Action row.

Cap stays 6 actual experiments. No increase — the fix recovers 3 slots
by not charging bookkeeping, it does not add slots.

## 3. M17 defect 2: no verification-capacity guarantee

Even with correct accounting, 1 diagnostic + 1 reserved + 1 skeptic = 3,
plus model follow-ups could still starve the 1 verification slot. No hold
exists today: `reserve.run_reserved` requires `remaining >= 2` (1 for
itself + 1 for the model) but knows nothing of verification;
`skeptic.review` spends while `remaining >= 1`; the model loop spends
while `remaining >= 1`. Verification is last and gets leftovers.

Fix (Phase 2): `accounting.py` verification hold of 1 slot. While no
verification event exists and eligibility is still possible (any open
hypothesis with ≥1 moving support and 0 contradicts, or any investigating
hypothesis that could still gain support), non-verification experiment
dispatches must leave 1 slot free: `used + held + 1 (this) + 1 (hold) <=
cap`. Verification dispatch consumes the hold. When verification completes
or is ruled impossible/ineligible on the record, the hold releases.
Decline paths stay honest (dissent preserved, unresolved kept unresolved).

## 4. M17 defect 3: resolution contract consumes snapshots, not transitions

Exact lines: `verify._contract()` builds `transitions = [{"hypothesis",
"status", "moving_refs"}]` — current-status snapshots, one per hypothesis.
`research/resolve.contract()` then does `elif sup or transitions:` →
`partially-resolved`. Since `transitions` is non-empty whenever hypotheses
exist, ANY run with hypotheses reports partially-resolved even when no
hypothesis ever left `investigating` (M17 live: proposed → investigating
×3, nothing further, yet contract said partially-resolved).

Genuine transition records DO exist and are ignored: `engine.
update_hypothesis` records kind=`hypothesis` events with
`payload={hypothesis_id, status, from:{status,...}}`; `hypotheses.
update_with_evidence` funnels through it; `record_finding("confirmed")`
is the confirmation transition. The contract simply never reads them.

Fix (Phase 3): `resolve.collect_transitions(session, inv)` reads
kind=`hypothesis` events + `Hypothesis.revisions`, emitting real
`{hypothesis_id, from, to, seq, reason}` events. `verify._contract` feeds
those in. `resolve.contract` semantic fix: `partially-resolved` ONLY when
a real transition advanced a hypothesis (to supported/rejected, or a
confirmed/falsified terminal), or `supported`/`rejected` sets are
non-empty. Evidence-without-advancement (investigating + moving refs) →
`unresolved` with conclusion "evidence collected but still unresolved".
No confirmation without the full contract (≥2 independent moving supports
+ checklist upheld — keep in `verify`). No rejection on weak evidence
alone (keep `update_with_evidence` rules). Null vs never-tested stays
distinguishable via diagnosis class (keep `diagnose()`).

## 5. What must be preserved

- Scorer (`eval/scorer.py`), M9/M10 evaluators, sealed truth, historical
  `benchmarks/` artifacts: frozen, byte-identical.
- Demand Zone AI: untouched (no files under its paths, no model/feature/
  metric changes).
- Token headroom (`governor.check_dispatch`), attempt/round caps,
  reserve-then-settle discipline, dedup-release rule, skeptic gate
  (blocking challenges gate `supported`), attribution adequacy +
  denial-symmetry rules, `record_finding` only on corroboration.
- Per-run nominal caps: rounds 3, experiments 6, attempts 12, tokens
  50,000. Financial cap moves 0.40 → 0.65 ONLY because M18 authorizes a
  $0.65 single-run ceiling (Phase 6/10); this is the authorized cap, not
  a silent increase, and is disclosed in the readiness + final reports.
- `replication.SECOND_PROBE` different-tool rule; `slice_gap_significance`
  ranking probe; cached-result disqualification.

## 6. Proposed changes (minimal, additive)

1. NEW `backend/live/accounting.py` (~150 lines): taxonomy, single
   reserve/settle/release API, verification-hold policy, purpose ledger.
2. `loop.py`: kind-checked dispatch (hypothesis ops bypass experiment
   reserve; still count `tool_call_count` and still dedup), hold check
   before non-verification experiments, purpose in event payload.
3. `reserve.py` + `skeptic.py`: route through `accounting`, honor hold,
   record purpose/hypothesis links (behavior otherwise unchanged).
4. `verify.py`: route through `accounting` (consume hold), feed real
   transitions into contract.
5. `resolve.py`: ADD `collect_transitions()`; tighten `contract()` status
   rule as above. No other semantic change.
6. `governor.py`: `CAPS["cost_usd"] = 0.65` (authorized M18 ceiling).
7. `api.py` + `Workspace.tsx`: scientific-closure view reading recorded
   backend data (hypotheses, transitions, attribution, skeptic,
   allocation, verification, contract, spend). No fabricated state.
8. NEW `tests/test_m18_integration.py` (~19 unit + 3 e2e cases).
9. Docs: this audit, `M18_OFFLINE_VALIDATION.md`, `M18_LIVE_READINESS.md`,
   `M18_FINAL_RESULTS.md`.

## 7. Risks + test strategy

- Risk: kind-check bypass breaks tool-call accounting tests. Mitigate:
  `tool_call_count` still increments for hypothesis ops (attempts budget);
  only experiment slots are exempt. Existing M8/M16/M17 tests assert
  `experiments_used == 1` after single diagnostic/reservation/verification
  — all still experiments, unaffected. The M17 e2e asserts `<= 6` — holds.
- Risk: hold deadlocks the model (refuses everything). Mitigate: hold is
  1 slot, releases on verification terminal event; decline events record
  the reason; e2e covers budget-prevents-verification → unresolved.
- Risk: transition-parser misses payload shapes. Mitigate: parse both
  event payload (`from.status`/`status`) and `Hypothesis.revisions`;
  regression test replays the M17 snapshot shape and asserts `unresolved`,
  plus a supported-transition case asserting `partially-resolved`.
- Offline gates before any spend: full suite (≥495), 19+ new M18 tests,
  tsc, Vite build, API smoke, separation + credential scans, M9/M10 green.
  Readiness simulation must show the verification probe fits in 6 actual
  experiments; otherwise NO-GO, no live run.
