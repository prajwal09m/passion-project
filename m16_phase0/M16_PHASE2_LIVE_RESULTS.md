# M16 Phase 2 — Live Results (eval_music, Arms B+C, 10 runs)

- **Authorization:** minimum controlled live evaluation, eval_music only, 5× Arm B + 5× Arm C, $0.65 aggregate ceiling.
- **Protocol:** `m16_phase0/M16_PHASE2_EVALUATION_PROTOCOL.md` (frozen; outcome categories §3, arms §4, reporting §5, safeguards §6).
- **Ground truth (sealed from loop; graded here only):** cold-start collapse — new-item slice P@K far below established items under a healthy pooled mean (`model_autopsy/tests/fixture_eval/ground_truth_eval.json`, `eval_music`).
- **Status:** campaign complete, 10/10 authorized runs executed, ceiling never approached. **No statistical significance is claimed** (preregistered bar not met — §8).

## 1. Results for every authorized run

Per-run caps (all pre-request governor gates): 3 rounds / 6 experiments / 12 attempts / 50,000 tokens / $0.40. Durations from first to last recorded event.

| Run | Arm | Verdict | Score | Meas. localized¹ | Uniformity rejected² | Strict³ | R/E/A | Tokens (in/cached/out) | Cost | Duration |
|---|---|---|---|---|---|---|---|---|---|---|
| m16b-music-01 | B | inconclusive | 0.62 | yes | no (investigating) | no | 2/6/7 | 26,605 / 5,218 / 6,001 | $0.0530 | 1m16s |
| m16b-music-02 | B | inconclusive | 0.62 | yes | **yes** | no | 3/6/10 | 43,845 / 27,257 / 9,777 | $0.0664 | 1m55s |
| m16b-music-03 | B | inconclusive | 0.62 | yes | **yes** | no | 2/6/7 | 26,711 / 20,006 / 6,227 | $0.0378 | 1m11s |
| m16b-music-04 | B | inconclusive | 0.63 | yes | **yes** | no | 2/5/7 | 26,409 / 20,134 / 6,075 | $0.0367 | 1m07s |
| m16b-music-05 | B | inconclusive | 0.62 | yes | **yes** | no | 3/6/10 | 43,812 / 30,457 / 11,301 | $0.0693 | 1m55s |
| m16c-music-01 | C | inconclusive | 0.63 | yes | no (supported!) | no | 2/5/7 | 26,472 / 18,854 / 6,239 | $0.0389 | 1m05s |
| m16c-music-02 | C | inconclusive | 0.63 | yes | **yes** | no | 2/5/7 | 26,441 / 20,006 / 6,378 | $0.0382 | 1m07s |
| m16c-music-03 | C | inconclusive | 0.63 | yes | **yes** | no | 2/6/7 | 26,677 / 18,982 / 5,698 | $0.0367 | 0m58s |
| m16c-music-04 | C | inconclusive | 0.62 | yes | no (supported!) | no | 2/6/7 | 26,637 / 20,134 / 5,458 | $0.0343 | 0m56s |
| m16c-music-05 | C | inconclusive | 0.62 | yes | no (supported!) | no | 2/6/7 | 26,665 / 20,134 / 6,378 | $0.0383 | 1m05s |

¹ **Measured localization** (protocol §3): affected segment measured at adequate granularity with moving evidence. All 10 runs executed `ranking_slice_diagnostics` and recorded per-slice P@K: **new slice 0.8305 (n=592, k=59) vs established 1.0000 (n=1168, k=117), gap 0.1695, pooled 0.9432** — the planted signature, on record in every run. Slice n is adequate (both ≫ 30-row minimum).
² **Uniformity rejected**: the "relevance is uniform / gaps are noise" rival ends `rejected` (via a `contradicts` link from the gap evidence) vs left standing.
³ **Strict discovery** (protocol §3): corroboration incl. independent second probe — 0/10 (see §6).

No run was interrupted, invalid, replaced, or omitted. All 10 records are complete on disk: `model_autopsy/benchmarks/live_runs/m16{b,c}-music-0{1..5}/` (manifest, usage.jsonl, actions, hypotheses, events_dump, eval_report, scorecard, sqlite3 + sandbox db).

## 2. Arm B versus Arm C comparison

| Outcome | Arm B (reservation, no skeptic) | Arm C (reservation + skeptic-lite) |
|---|---|---|
| Strict discovery | 0/5, Wilson 95% **[0.000, 0.434]** | 0/5, Wilson 95% **[0.000, 0.434]** |
| Measured localization | 5/5 [0.566, 1.000] | 5/5 [0.566, 1.000] |
| Uniformity rejected | 4/5 (B2–B5) | 2/5 (C2, C3) |
| False positives | 0/5 | 0/5 |
| Mean cost / run | $0.0526 | $0.0373 |
| Mean tokens / run | 41,353 | 32,609 |

**No arm effect is claimed.** Fisher exact on strict discovery (0/5 vs 0/5) gives p = 1.0; the preregistered bar (5-vs-0 split or nothing) is not met. The uniformity-rejection gap (4/5 vs 2/5, Fisher p ≈ 0.52) is **not** a skeptic effect — see §5: skeptic-lite never blocked, probed, or moved a status in any run. The gap is fully explained by §4's wording-sensitive denial bug interacting with model-chosen hypothesis phrasing ("no slice underperforms" → correctly contradicted; "any differences are noise" → wrongly supported). Arm C's three non-rejections are the bug's footprint, not skeptic-lite's doing.

**Structural caveat that redefines this comparison:** the reservation fired in **0/10 runs in both arms** (always declined — §5.1). So Arm B did not test P0-1 at all; in practice the campaign compared **status-quo-ante vs status-quo-ante + advisory skeptic review**, and the review changed nothing observable. P0-1 (reservation) and the skeptic probe path both remain **untested live**.

## 3. Localization and strict discovery rates

- **Detection** (anomaly referenced by moving evidence): **10/10**, Wilson 95% **[0.722, 1.000]**.
- **Localization measured** (per-slice gap at adequate n, moving evidence): **10/10 [0.722, 1.000]**. Falsifies "never localizes" descriptively — every run put the planted slice gap on record.
- **Localization endorsed** (model rejects uniformity AND carries a new-item-selective hypothesis): 6/10 (B2–B5, C2, C3) **[0.313, 0.832]**; 1 run left both rivals open (B1); 3 runs endorsed contradictory rivals (C1, C4, C5 — uniformity `supported` alongside selective-failure `supported`).
- **Mechanism named** (cold-start / feature-sparsity / low-history wording for the new slice): 7/10 hypotheses (B1, B4, C1, C2, C3, C4, C5); all unconfirmed.
- **Strict discovery: 0/10 [0.000, 0.278]** — extends the frozen M6–M14 0/6 streak to 0/16 live. Restraint held (0 FPs), but the confirmation path never engaged (§6).
- **Correctly inconclusive verdicts: 10/10** — no run overclaimed; every report's `confirmed_findings` is empty and `limitations` lists never-run diagnostics.

## 4. Evidence attribution and hypothesis transitions

- **Referential integrity: perfect.** 66 evidence refs across 30 hypotheses; **0 dangling** (every ref resolves to a recorded action id) in all 10 runs.
- **Status motion: 27/30 hypotheses reached evidence-driven terminal states (supported/rejected)** (Wilson 95% [0.744, 0.966]); every run had ≥1 rejection or support; 4 `status_change` events per run. No-motion cases (B1 ×2, B2 ×1) are recorded with cited evidence, per protocol §5.
- **Attribution errors (denier-supports; protocol bar: must be 0): 4 runs — B1, C1, C4, C5.** Gap evidence (0.1695, "ranking not uniform") was auto-linked as **`supports`** to uniformity hypotheses worded without an explicit negation ("any slice differences are sampling noise / reflect base rates"), moving three of them to `supported`. The sibling wording ("no slice systematically underperforms") correctly drew `contradicts` → `rejected` in 6 runs.
- **Root cause (reproduced offline, zero spend):** `causal/attribution.py::denies()` requires a negation token within 4 tokens before the segment word. "No slice…" trips it; "any slice differences are…" does not, and the fallthrough broad topical match (`_is_subgroup` hits "slice"/"across") returns `supports` with `moves_belief=True`. Denial detection is phrasing-sensitive: uniformity claims that euphemize ("differences are noise") evade the symmetry the system relies on. Fix direction (not applied — out of scope): route uniformity/denial-shaped claims through `denies_family`, or make the fallthrough non-moving for denied-effect evidence.
- **Hypothesis provenance:** all 30 hypotheses model-worded via `propose_hypothesis` (origin: meta), 3 per run: one uniformity null, one slice-selective, one hygiene/artifact or global-failure rival — good coverage, no duplicates. Model confidence notes correctly flagged uncalibrated throughout.

## 5. Skeptic challenges and their actual impact

- **Arm B:** skeptic-lite disabled by flag; both turns/run recorded `Skeptic-lite disabled by arm flag (comparison arm)` — manipulation verified on record.
- **Arm C:** skeptic-lite ran 2 turns × 5 runs: **54 challenges total** (types: `confounder-ignored`, `missing-falsification`), **0 blocking, 0 probes dispatched, 0 dissent preserved**.
- **Impact: none observable.** No status transition, tool choice, or report line in any C run traces to a skeptic challenge; all belief motion came from linker auto-links. Two structural reasons: (a) on this scenario the role-scorer never rates anything blocking, so the probe branch is unreachable here; (b) the one probe path that could fire without blocking (reservation reuse) never had a reservation to reuse (§5.1).
- **Verdict on skeptic-lite:** reviewed-and-filed, not reviewed-and-acted. Its live probe/dissent machinery is still untested — the challenges themselves were reasonable (confounder + falsification demands), but advisory-only review cannot move the outcomes §3 measures.

### 5.1 Reservation: declined 10/10 (ordering defect)

Every run records `Reservation declined: fewer than 2 open hypotheses; no discrimination to buy`. Cause: `loop.py` runs the once-per-investigation reservation checkpoint **before the first model round**, i.e. before any hypothesis exists (the model proposes all three hypotheses via tool in round 1), and the `_already` guard never retries. P0-1 is therefore **unreachable in the live loop as coded** — in this scenario (and likely any scenario where hypotheses are model-proposed rather than pre-seeded). This is the campaign's most consequential defect: the B arm's defining feature never engaged, and no offline test caught it because the reservation unit tests pre-seed hypotheses. Fix direction (not applied): move the checkpoint after round 1 (or re-arm when hypothesis count crosses 2).

## 6. Independent verification outcomes

**Zero second probes in 10/10 runs.** Every report has `"verification": []`; no `verification`-kind events exist in any run; `m10/replication.py` is never invoked by the live loop. Consequences:

1. Strict discovery was **structurally unreachable** this campaign, independent of evidence quality — even B4 (perfect attribution: uniformity contradicted + rejected, new-slice cold-start supported with refs) could not advance past `supported` because nothing dispatches the confirming probe.
2. The corroboration bar held exactly as designed (0 confirmations, 0 FPs) — restraint is real, but it is currently **restraint by missing machinery**, not restraint by passed verification. These look identical in scorecards and must not be confused in roadmap claims.
3. The loop has no caller for the offline loop's strengths (`research/verification.py`, `m10/replication.py`, `research/resolve.py` contracts) — confirming the pipeline-map gap (P1 assessment): the capability exists offline but has no budgeted live invocation.

## 7. Per-run and aggregate token usage and spending

Spend ledger (governor `cost_usd.spent`, cross-checked against pricing muse-spark-1.3 Standard $1.25/$0.15-cached input, $4.25 output per 1M — B1 recomputed by hand: $0.05302 ✓):

| Run | Input (cached) | Output | Total toks | $ |
|---|---|---|---|---|
| B1 | 26,605 (5,218) | 6,001 | 32,606 | 0.0530 |
| B2 | 43,845 (27,257) | 9,777 | 53,622 | 0.0664 |
| B3 | 26,711 (20,006) | 6,227 | 32,938 | 0.0378 |
| B4 | 26,409 (20,134) | 6,075 | 32,484 | 0.0367 |
| B5 | 43,812 (30,457) | 11,301 | 55,113 | 0.0693 |
| C1 | 26,472 (18,854) | 6,239 | 32,711 | 0.0389 |
| C2 | 26,441 (20,006) | 6,378 | 32,819 | 0.0382 |
| C3 | 26,677 (18,982) | 5,698 | 32,375 | 0.0367 |
| C4 | 26,637 (20,134) | 5,458 | 32,095 | 0.0343 |
| C5 | 26,665 (20,134) | 6,378 | 33,043 | 0.0383 |

- **Aggregate: $0.4496 of $0.65 (69.2%)** — ceiling never binding; pre-run remaining-vs-worst-case ($0.1172) checks passed 10/10. Mean $0.0450/run, median $0.0384. Cost per measured localization: $0.045; cost per strict discovery: undefined (0/10).
- **Per-run $ cap ($0.40):** never approached (max $0.0693, 17% of cap). Rounds (≤3/3), experiments (≤6/6), attempts (≤10/12) held everywhere.
- **Token cap disclosure (M7-breach rule):** B2 (53,622) and B5 (55,113) exceeded the nominal 50,000-token cap by ~7% and ~10%. The governor's token gate is **pre-request**: it refuses to *start* a request over cap but cannot un-send tokens once dispatched, so a long final round overshoots. Cost/toyl-call caps were unaffected. Sensitivity: excluding B2/B5 changes nothing (strict 0/8, localization measured 8/8, uniformity-rejected 4/8); they are retained in primary figures with this flag, per "disclosed not hidden." Recommend either a reservation headroom rule (stop dispatching within ~15% of cap) or restating the cap as post-hoc-invalidating.

## 8. Confidence intervals and statistical limitations

- All rates carry Wilson 95% CIs (§2–§3). With n=5/arm, the CIs are inherently wide (0/5 → [0, 0.434]): this campaign can **rule nothing in or out** about arm differences — by design (minimum campaign) and by outcome (no variance on strict).
- **No significance claimed.** Preregistered bar (Fisher exact on a 5-vs-0 split) was not met and no other test was preregistered; none was run.
- **Comparability limits:** (a) P0-1 never engaged — B arm untested as designed (§5.1); (b) skeptic never blocked/probed — C-vs-B reduces to advisory review (§5); (c) B2/B5 token-cap overshoot — retained + flagged (§7); (d) single scenario, single model, ~1–2 min runs — no generalization beyond eval_music on this loop.
- **Baseline pairing:** M13/M14-shape baselines are offline-heuristic, not live arms; Arm A (status-quo-ante live) was not run (out of scope). The honest baseline statement is: live strict discovery on eval_music is 0/10 here vs 0/6 strict live M6–M14 — continuity of restraint, not progress on confirmation.

## 9. Honest conclusions and unresolved weaknesses

**What worked (keep):**
1. **Restraint is real:** 10/10 honest inconclusives, 0 FPs, 0 overclaims, bounds stated in every report. The corroboration bar survived contact with suggestive evidence.
2. **Measurement is real:** the planted slice gap was measured at adequate granularity in 10/10 runs with clean referential integrity (0 dangling refs) and near-universal status motion (28/30).
3. **Budget machinery is real:** $0.45 total, every cap except the token-overshoot footnote held, pre-run aggregate checks all passed, records complete and replayable.

**What is broken or missing (the actual breakthrough is finding these before scaling spend):**
1. **Confirmation is unreachable live** — no caller dispatches a second probe (replication/verification never invoked). Strict discovery cannot exceed 0/10 until the loop can spend budget on confirmation. This is the single largest blocker for any future "discovery" claim.
2. **Reservation is dead code live** — once-per-investigation checkpoint fires before hypotheses exist; never retries. P0-1's live value is entirely unmeasured, and the B arm tested nothing.
3. **Skeptic-lite is advisory-only here** — 54 challenges, 0 blocking, 0 probes, 0 traceable impact. Its intervention machinery is untested live.
4. **Denial detection is phrasing-sensitive** — 4/10 runs carry denier-supports (protocol bar: 0), all from uniformity claims euphemized as "noise/base rates." Root cause reproduced offline; fix scoped but not applied.
5. **Token cap is a gate, not a ceiling** — B2/B5 overshoot by 7–10%. Decide the semantics before a larger campaign.

**Unresolved weaknesses (do not claim otherwise):** no live confirmation exists anywhere in program history (0/16); localization endorsement is 6/10 with 3 contradictory; skeptic/reservation live effects are unmeasured, not zero; all findings are single-scenario (eval_music), single-model, n=10.

**Recommended next steps (require fresh authorization; none executed here):** (i) wire a budgeted second-probe caller (replication/verification) into the live loop and re-run; (ii) move the reservation checkpoint post-round-1 with re-arm; (iii) make non-blocking skeptic challenges capable of spending 1 experiment on a discriminating probe; (iv) harden `denies()`/fallthrough for euphemized denials; (v) add token headroom stop; (vi) then run the preferred 25-run campaign (A+B+C × music, B+C × credit).

## Appendix — compliance and provenance

- **Scope:** 10 runs, eval_music only. No eval_credit, no extra arms, no Demand-Zone AI changes, no scorer/evaluator changes, no historical-artifact modifications (verified: zero tracked-file modifications under `benchmarks/`, `scorer`, `evaluator`, demand-zone paths; campaign artifacts are new run-dirs only).
- **Code delta for the campaign:** arm-flag plumbing only — `live/cli.py` (`--no-skeptic`), `live/driver.py` (`skeptic_enabled`), `meta_api/loop.py` (flag-respecting skip + disabled-note), `live/skeptic.py` (`enabled()`), plus `tests/test_m16_phase1.py` (18/18 green incl. no-duplicate-spend) — full suite 476/476 green pre-campaign.
- **Reproducibility:** `backend/live/cli.py` + `preflight` (GO 10/10, separation audit clean, fixture readable) + per-run dirs (manifest/usage/actions/hypotheses/events/report/scorecard/sqlite). Sealed truth never entered the loop (boundary audit pre-launch).
- **Tokens spent on this report's analysis:** $0 (all grading offline from preserved records).
