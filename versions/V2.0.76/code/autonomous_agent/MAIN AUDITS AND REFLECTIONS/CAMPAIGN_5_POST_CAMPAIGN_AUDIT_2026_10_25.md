# Campaign 5 Post-Campaign Audit

Date: 2026-10-25
Conducted: Read-only after verified completion of `campaign-5-regime-error-analysis-2026-10-22`
Evidence sources: proposal ledger (campaign-5-scoped recount 2026-10-25), loop events journal, agent state,
campaign config pin, versions snapshot directories, experiment adapter/test suites, loop process stack captures
(2026-10-24/25 incident records).

## Executive Summary

Campaign 5 (Option D, Regime/Error Analysis) completed normally. The loop stopped at
2026-10-25T14:33:19Z with `PORTFOLIO_COMPLETE` ("minimums met and no admissible proposal") — the
predeclared clean-success stop — after **23 of 45** predeclared execution-budget slots were consumed.
Final champion: **V2.0.74** (pooled ROC AUC 0.683633, delta +0.023312 over the standing 0.660322,
95% moving-block CI [0.008653, 0.036973]).

**Operational postscript (this campaign will be remembered for it):** the campaign's runtime was
dominated by a scaling defect in the original-tree immutability fingerprint. That defect was
diagnosed on 2026-10-25 from live stack captures and fixed (`versions/` snapshot exclusion), after
which the first post-fix cycle completed in ~26 minutes. Details in Part 6.

## Part 1 — Completion Verification

### Execution Summary

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Executions | 45 cap (`max_total_executions`) | 23 completed (21 adjudicated with ACCEPT/REJECT result, 2 FAILED_EXECUTION) | **STOPPED EARLY BY DESIGN** |
| Adjudication results | — | 14 ACCEPTED / 7 REJECTED | — |
| Proposals | budget governed by bias governor | 23 created (falsification 7, confirmatory 10, replication 3, exploration 3) | COMPLETE (agenda exhausted) |
| Champion promotions | — | 13 (V2.0.62 → V2.0.74) | COMPLETE |
| Stop reason | — | `PORTFOLIO_COMPLETE` | CLEAN |

The 45 was a safety cap, not a goal. The predeclared selection rule ("portfolio minimums first,
then approval order") ends the campaign when the generator's agenda is empty and the minimums are
met — which happened at execution 23.

### Budget Utilization

- **Execution budget**: 45 declared, 23 used (51%). Underspend is legitimate under the stop rule;
  forcing the remaining 22 would have violated the anti-rubbery machinery intent of the config.
- **Portfolio shape**: both predeclared minimums satisfied with margin —
  confirmatory executed 10 (min 1), falsification executed 6 (min 1).
- **Generator floor held**: 7 of 23 created proposals (30.4%) were falsification-class,
  satisfying the predeclared `falsification_minimum.share_floor = 0.3` to the very last proposal.

### Stop Condition Verification (read-only recount, 2026-10-25)

1. Stop branch taken: [continuous_loop.py `phase_execute_one`] — no compiled proposal, no approved
   admissible target, and `report["portfolio_complete"] == True` → `LoopStop(PORTFOLIO_COMPLETE)`.
2. Journal last rows: cycle promotion 14:32:40Z → `phase_generate` 14:33:01Z with `created: 0,
   approved: 0` → `loop_stopped` 14:33:19Z. Nothing was killed mid-phase.
3. `agent_state.json`: `last_cycle_status: RESEARCH_EXHAUSTED`, `research_exhausted: true`.
4. Process tree clean: zero python processes remain; no orphaned candidates; `versions\` contains
   no leftover `.tmp` promotion directories.

## Part 2 — What Campaign 5 Measured

Campaign 5's authorization scope (B4 owner decision packet, PMED, signed 2026-10-22) targeted
regime/error analysis with `regime_conditional`-scoped metrics (`regime_auc` family) and no
`modify_regime_parameters` changes. The 21 adjudications split:

| Class | Created | ACCEPTED | REJECTED | FAILED_EXECUTION |
|-------|---------|----------|----------|------------------|
| confirmatory | 10 | 7 | 3 | — |
| falsification | 7 | 3 | 3 | — |
| replication | 3 | 2 | 1 | — |
| exploration | 3 | 2 | — | — |

Reading: the campaign was **regime-conditional confirmatory-heavy by design** — 10 of 23 created
proposals tested whether prior accepted gains hold under regime conditioning; 3 of 7 falsification
proposals survived. Every adjudication row records `leakage_status`, `holdout_touched`,
`robustness_status`, `decision_criteria_passed`, and dual delta context (`primary_delta`,
`parent_version`), preserving the C4 champion-integrity instrumentation.

## Part 3 — Champion Line Analysis

### Trajectory V2.0.61 → V2.0.74

Campaign 4 ended at V2.0.61. Campaign 5 promoted the line through **13 versions
(V2.0.62–V2.0.74)**, matching the journal's 13 `promoted` cycle rows (first 2026-10-23T14:54:43Z,
last 2026-10-25T14:32:40Z).

### V2.0.74 Final Metrics

From `versions/V2.0.74/evaluation.json` (read directly 2026-10-25):
- **Pooled ROC AUC**: 0.683633 (candidate) vs 0.660322 (standing champion)
- **Delta**: +0.023312 (`pooled_roc_auc_delta` is the predeclared primary metric)
- **Uncertainty interval**: [0.008653, 0.036973], 95% moving-block bootstrap (block_weeks 4) —
  strictly positive; the standing champion's number **does not** fall in the interval's center.
- **Model**: LightGBM (versus LogisticRegression on arm C)
- **Dataset pin**: `study_v1_development_event_table`, dataset_sha256
  `232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0`
- **Backtest status**: `NOT_RUN` with the standing prohibition text (real-money trading prohibited;
  cost modeling is a separate predeclared track) — the boundary held.

### Interpretation caution

V2.0.74 is the standing champion under the campaign's own gates (accepted at adjudication,
promotion recorded). It is *not yet* a validated production artifact: the holdout remains sealed,
the real-market track is a separate predeclared authorization, and the protocol-fingerprint
provenance defect (below) is still open. "Internally validated within the loop's contracts" is the
correct strength of claim.

## Part 4 — Authorization and Review Trail

- Authorization: B4 owner decision packet signed by PMED 2026-10-22; authorization record re-signed
  with `record_resign_2026_10_23.py` on 2026-10-23 after the launch preflight refused the first
  wiring state; approval mode `autonomous_revalidation` (every proposal revalidated at approval
  time against current ledger state — no hidden human selection).
- Prerequisites recorded as satisfied in the frozen config: B1 (protocol scope resolution,
  2026-10-22), B2 (AI independent statistical review accepted with risk acknowledgment,
  `C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md`), B3 (evaluation/holdout attestation),
  B5 (real-market predeclaration), B7 (legacy execution path classification).
- Config pin integrity: `campaign_config.sha256` = `29c905aaf25012cdd20bf21270821f81f5a8e24b46b4a51163d2c65e2e9124a5`
  remained byte-identical across every crash, restart, and code fix in this campaign — verified at
  least 8 times between 2026-10-24 and 2026-10-25, including after the fingerprint fix.

## Part 5 — Open Defects Carried Forward

1. **Protocol-fingerprint provenance defect (documented-and-proceed)**: the signed
   `protocol_fingerprint` (`be2e6d34…` as installed; see config `provenance_note_protocol_fingerprint`)
   could not be reproduced from installed content by the recorded method or ~40 plausible variants.
   The C4-era control (`553ac77f…` family) still does not reconcile. Owner decision on 2026-10-23
   was **documented and proceed**; the defect remains open and is the highest-value item for the
   next independent review.
2. **No campaign-end multiplicity record for C5**: `state/campaign_end_multiplicity.jsonl` contains
   only the Campaign 4 row. If C5's familywise claims ever feed a downstream decision, a C5
   multiplicity record (method, familywise alpha, retained-at-alpha list) should be produced from
   the ledger before relying on it.
3. **Legacy fields in `agent_state.json` champion object**: `version: "V2.0.8"` /
   `parent_champion: "V2.0.7"` do not match the actual champion line (V2.0.74, promoted 14:32:40Z).
   Impact appears cosmetic (the champion's metrics/artifact sha256 match V2.0.74's evaluation), but
   the field-viewer should use the ledger + versions registry, not this object, until fixed.

## Part 6 — Operational Incident Audit (the 2026-10-24/25 runtime failure mode)

This campaign survived two >11-hour silent "wedges," one `PROMOTION_FAILED` stop, one crash-recovery
restart, and one live code fix — all without corrupting durable state. Factual record:

| Time (UTC) | Event |
|------------|-------|
| 10-23 00:52 | First launch (pid 4136), preflight wiring green |
| 10-23 12:36 | Restart (pid 40672) after authorization record re-sign |
| 10-23→10-24 | ~45-minute cycle cadence; 13 promotions begin |
| 10-24 (overnight) | **Wedge #1**: generation-phase stall ~11.7 h, unwedded by restart |
| 10-24 13:40 | Recovery restart (pid 11360) |
| 10-24 20:30 | `PROMOTION_FAILED`: `PermissionError [WinError 5]` renaming `.V2.0.70.<hash>.tmp` → `versions\V2.0.70` (external handle holder, likely antivirus/contention on the bloated snapshot tree) |
| 10-24 22:07 | Restart (pid 32444); queued cycle adjudicated immediately; steady ~42-min cycles resume |
| 10-25 00:03 | Cycle 21 execution begins |
| 10-25 ~13:09 | Cycle 21 completes after ~13 h — **Wedge #2 observed in the execution phase** |
| 10-25 13:05 | **Diagnosis**: py-spy stack captures of the live pid: 6/6 samples inside `original_fingerprint()` → `sha256_file()` |
| 10-25 13:20 | **Root cause quantified**: fingerprint enumerates 450,930 files; 444,372 (98.5%) under `versions\` — 72 accumulated full-project promotion snapshots (~6,150 entries each). Two full hashes per experiment. Enumeration alone: 231 s. |
| 10-25 13:22 | Wedged pid killed; **fix applied**: `versions` added to `original_fingerprint` skipped names ([experiment_adapter.py:744](../experiment_adapter.py#L744)) |
| 10-25 13:30–16:00 | Verification: `test_experiment_adapter.py` 18/18 (incl. new `OriginalFingerprintTests`: snapshot tampering excluded, real-tree tampering still detected), `test_baseline.py` 19/19, `test_v110_wiring_e2e.py` 38/38 |
| 10-25 14:05 | Relaunch (pid 41852) via the authorized fail-closed launcher |
| 10-25 14:32 | **Post-fix cycle 23 completes in ~26 minutes** (vs ~13 h) — the fix is validated in production |
| 10-25 14:33 | `PORTFOLIO_COMPLETE` clean stop |

Root cause classification: **not** a hang, deadlock, or external interference — a
computational-scaling defect (documented as an "operational scaling issue" in
`AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md`, item 9, 2026-10-04) where the immutability-fingerprint
cost grew linearly with promotions: every promotion froze another full-project snapshot that the
guard then re-hashed twice per experiment, forever.

### Guardrails for future campaigns (recommended)

1. **Fingerprint budget assertion** — measure/report `original_fingerprint()` duration at
   experiment start; abort/flag if it exceeds a predeclared budget (e.g., >10 min) instead of
   silently scaling.
2. **Snapshot hygiene** — decide per promotion whether old full-tree snapshots are pruned,
   compressed, or converted to a hash-pinned manifest + delta; re-hashing 72 frozen copies per
   cycle buys zero information (their integrity was verified at promotion time).
3. **Generation heartbeat** — a periodic journal row during long phases so silent stalls are
   visible without a stack capture (this incident was caught only because a human asked "status").
4. **Promotion-retry** — the WinError 5 rename stop will recur under AV contention; a small
   bounded backoff retry on the promotion rename is warranted.
5. **Watchdog auto-relaunch** — for future long campaigns: monitor `loop_state.heartbeat_at` and
   relaunch via the authorized launcher when heartbeat is stale or the process exits on a
   non-terminal stop reason.

## Part 7 — Verdict

Campaign 5 **completed normally** under its predeclared contract: portfolio minimums satisfied,
generator agenda exhausted, clean documented stop, config pin intact end-to-end, holdout sealed,
and 13 honest, gate-passed champion promotions culminating in **V2.0.74**. The operational incidents
were caused by one identified scaling defect, were contained without data loss, and their fix is
covered by regression tests. Two open items travel forward honestly: the protocol-fingerprint
provenance defect and the missing C5 multiplicity record.

— Audit generated 2026-10-25; all figures recounted from `proposal_ledger.jsonl`, `loop_events.jsonl`,
`campaign_config.json`, and `versions\V2.0.74\evaluation.json` on that date.
