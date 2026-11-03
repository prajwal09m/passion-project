# M17 — Final Results: Autonomous Scientific Closure

One authorized live run. No retries, no second run. This document is the
complete record.

## 0. Run identity and artifacts

- **Run:** `m17-music-01`, scenario `eval_music`, status `completed`.
- **Artifacts:** `model_autopsy/benchmarks/live_runs/m17-music-01/`
  (manifest, usage.jsonl, actions.json, hypotheses.json,
  events_dump.json, eval_report.json, scorecard.json, live.sqlite3,
  sandbox_final.db). Scorecard: verdict **inconclusive**, overall
  **0.62** (discovery 0.0 / evidence 1.0 / reasoning 0.6 /
  calibration 1.0 / efficiency 0.6 / reproducibility 1.0).
- **Spend:** $0.0226 of $0.65 (3.5%). Tokens 16,636 of 50,000.
  Rounds 1/3, experiments 6/6, attempts 3/12. No cap breached; the
  headroom gate never triggered (projection never approached the cap).

## 1. Critical defects fixed (all five)

1. **Reservation timing** — checkpoint moved from pre-round (0
   hypotheses, always declined) to `maybe_reserve_end_of_turn`,
   once per investigation.
2. **Verification caller** — new `live/verify.maybe_verify`: eligibility
   (≥1 moving support, 0 contradicts), `replication.replicate`
   different-tool probe, adversarial checklist, `record_finding` only
   on corroboration, `resolve.contract` on every path.
3. **Actionable skeptic** — blocking challenges persist in investigation
   config, gate `supported` until answered, resolve via budgeted probe
   or preserved dissent; once-per-(type, hypothesis).
4. **Attribution root** — stemmed segment matching, euphemistic-denial
   symmetry, insufficiency bar; broad topical fallthrough can no longer
   manufacture moving support.
5. **Token headroom** — `check_dispatch` refuses before sending when
   used + estimated input + output allowance would breach nominal cap.

Plus: `ranking` second probe (`slice_gap_significance`, permutation
null) because no existing tool tests the music finding without
misfiring (per-slice AUC is uniform 0.974 vs 0.982; verified offline).

## 2. Architecture changes and actual live callers

- `run_meta_turn` → `maybe_reserve_end_of_turn` → `reserve.run_reserved`
  → `invention.execute` → `linker` (end of turn 1).
- `run_meta_turn` → `skeptic.review` → `roles.skeptic` + granularity →
  budgeted probe → `linker`; gate inside
  `hypotheses.update_with_evidence`.
- `driver.run_live_investigation` → `verify.maybe_verify` →
  `replication.replicate` → `verification.review_claim/record_review`
  → `record_finding` → `resolve.contract`.
- `run_meta_turn` → `governor.check_dispatch` before every provider
  request (main, fallback, summary-repair).

## 3. Offline validation results

495 passed / 0 failed (full suite, 307s), incl. 18 new M17 tests and
the end-to-end closure test (hypothesize → reserve → diagnose →
attribute → challenge → respond → verify → resolve → confirmed).
`tsc` clean, Vite build succeeds, separation audit ok (11 files),
credential scan clean, M9/M10 grades unchanged, scorer/evaluators/
history/Demand-Zone untouched. Verdict was GO. Details:
`benchmarks/M17_OFFLINE_VALIDATION.md`.

## 4–5. Initial hypotheses and provenance

All three model-worded via `propose_hypothesis` (origin: meta,
uncalibrated priors stated, round 1):

- H1 uniformity: "Ranking quality (precision@top-K) is uniform across
  catalog slices; no slice systematically receives less relevant top
  results." (~50% prior)
- H2 selective: "Top-K relevance is systematically worse for
  new/long-tail catalog slice(s) due to model under-ranking relevant
  cold items." (~40% prior)
- H3 hygiene: "Observed slice P@K differences are driven by
  data/evaluation hygiene (missingness, duplicates, or tiny slice
  size), not by true ranking-quality differences." (~30% prior)

Good competing coverage: null, mechanism, rival.

## 6. Reservation: selection, execution, outcome

Fired end of turn 1 (first live firing ever): selected
`classification_metrics` split-by-slice ("segment-varying vs uniform
quality across slice", decision-relevance supporting), budget-reserved,
executed, linked as **`relevant_to` (non-moving) to all three** —
correctly: the AUC rule cannot bear on top-K claims (adequacy gate),
and per-slice AUC came back uniform. Cost: 1 experiment. The
discriminating probe did its job: it separated "headline quality"
(uniform AUC) from "ranking quality" (slice P@K gap).

## 7. Diagnostics and measurements

| # | Tool | By | Result |
|---|---|---|---|
| 1–3 | propose_hypothesis ×3 | model | H1–H3 registered |
| 4 | ranking_slice_diagnostics | model | gap **0.1695** (new 0.8305/n=592, est 1.0000/n=1168, pooled 0.9432) |
| 5 | classification_metrics (reserved) | backend | per-slice AUC uniform (0.974 vs 0.982) → non-moving |
| 6 | ranking_slice_diagnostics (skeptic probe) | skeptic | gap reproduced 0.1695 |

## 8. Evidence attribution and status transitions

Both slice measurements linked identically and correctly:

- H1 uniformity → **`contradicts` ×2** (explicit "no slice…"
  denial met by gap evidence). Stays investigating (1 distinct tool —
  same-tool repeats do not corroborate, M13 rule, correctly applied).
- H2 selective → **`supports` ×2 actions, 1 distinct tool** →
  investigating (correct: needs an independent second tool).
- H3 hygiene → `supports` ×2 (rival hedging: gap evidence does not
  deny a hygiene contribution; disclosed, not an error).
- Classification → `relevant_to` ×3 (adequacy gate, correct).

**Denier-supports: 0.** The M16 4-run failure pattern did not recur.
All hypotheses moved proposed → investigating on evidence (3/3).

## 9. Skeptic challenges and investigator responses

5 challenges (confounder-ignored advisory; missing-falsification
blocking ×2 after the role upgrade). Responses on record:

- H2 missing-falsification → **probe executed** (slice diagnostic
  re-run, gap reproduced, linked, challenge marked
  answered-probe). A genuine investigator response with evidence.
- H3 missing-falsification → **dissent preserved**: probe refused by
  budget (experiments 6/6 spent), recorded with reason, gate released
  with the objection visible. No forced low-quality run.
- Open challenges at end: **0**. Skeptic disagreement never recorded
  as evidence against any hypothesis (asserted in tests, holds live).

## 10. Independent verification records

Eligible candidate correctly identified: H2 selective (1 independent
moving support, 0 contradicts, investigating; family `ranking`).
**Probe not dispatched: experiments 6/6 spent** (`Verification skipped:
no experiment budget left`, finding preserved as unresolved, no
confirmation manufactured). Resolution contract built regardless.

Budget autopsy (6/6): 3 × `propose_hypothesis` + 1 model diagnostic +
1 reservation + 1 skeptic probe = 6. Hypothesis *registration*
consumes the experiment budget — the structural reason verification
starved. This accounting predates M17; changing it mid-campaign would
have redefined the cap, so it stands, disclosed here as the primary
integration bottleneck.

## 11. Final resolution

`resolve.contract` from recorded state: **partially-resolved**
(6 moving refs, proposed → investigating ×3, rivals preserved, no
contradictions among confirmed items because nothing is confirmed).
Substance caveat (disclosed): the contract's `transitions` input was
built from status snapshots, so `partially-resolved` overstates what
is really "advanced but open" — no hypothesis passed investigating.
A contract-input fix (true status-change transitions) is recorded as
remaining work; the run's artifacts are unaffected.

## 12. Confirmed discoveries

**None — correctly.** Corroboration bar (≥2 independent tools + second
probe + checklist) was not met for any hypothesis. `confirmed_findings`
is empty; all three hypotheses are `unresolved/investigating` with
cited evidence and stated bounds.

## 13. Unresolved findings and limitations

- H2 selective: strongest (gap measured twice, uniformity contradicted
  twice, checklist never run) — one independent probe short of
  confirmation.
- H1 uniformity: contradicted but not yet rejected (1 distinct tool).
- H3 hygiene: hedged support, untested either way.
- Report limitations list all 14 never-run diagnostics by name.

## 14–15. Tokens, cost, budget compliance

Input 14,165 (cached 5,105) / output 2,471 / total 16,636 (33% of
nominal cap); $0.0226 (5.6% of the $0.40 per-run cap, 3.5% of the
$0.65 campaign ceiling). Rounds 1/3, attempts 3/12, experiments 6/6
(all legitimate dispatches; no overshoot — headroom policy held with
margin). Pre-run worst-case check passed ($0.1172 ≤ $0.65).

## 16. Comparison against M16 (10 runs, $0.45)

| Integration point | M16 live | M17 live |
|---|---|---|
| Reservation fires | 0/10 | **1/1** |
| Skeptic probe/dissent | 0 probes, 0 dissent | **1 probe + 1 dissent** |
| Denier-supports | 4 runs | **0** |
| Verification caller reached | never existed | reached, honestly declined |
| Strict discovery | 0 (unreachable) | 0 (correct: unearned) |
| False positives | 0 | 0 |

## 17. Remaining architectural gaps

1. Verification **executed** nowhere live (caller proven offline +
   reached live; probe starved by experiment accounting).
2. `propose_hypothesis` consumes experiment budget (3/6 this run).
3. Contract `transitions` input is snapshots, not changes.
4. Euphemistic uniformity wordings corrected offline but not
   live-tested (the model used explicit negation this run).
5. Single scenario, single model, one run.

## 18. Honest verdict

**Integration milestone: INCOMPLETE** — the preregistered rule
(reservation, skeptic intervention, *and* verification unreachable →
incomplete) is triggered by verification alone. Reservation and
skeptic intervention are now **live-executed**; verification is
**offline-proven and live-reached** but not live-executed.

**Autonomous scientific closure: not yet demonstrated end-to-end
live.** What the run did demonstrate is the integrity of the
incomplete path: every stage that could run did run, everything that
could not run said so on the record, and nothing was manufactured to
hide the gap. The machine works; it needs one more experiment's worth
of budget accounting to close.

Capability ledger: implemented (5 fixes + probe + caller) →
offline-tested (495 green, e2e closure confirmed offline) →
live-executed (reservation, skeptic probe/dissent, attribution,
headroom path armed) → independently-verified (not yet live) →
confirmed (none claimed, none earned).
