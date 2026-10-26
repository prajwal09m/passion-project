# Campaign 3 Post-Campaign Research Audit + Campaign 4 Proposal

Date: 2026-10-09. Conducted read-only after the verified completion of
`campaign-3-continuous-2026-10-05` (38/40 executions, `PORTFOLIO_COMPLETE`,
champion V2.0.35). No campaign was launched, no configuration was changed, no
experiment was run, the sealed holdout was not accessed, no frozen file was
modified. Evidence sources: `proposal_ledger.jsonl` (200 rows, all campaigns),
`loop_events.jsonl`, `agent_state.json`, `spec_attempts.json`, 39
`candidates/exp-proposal-*/spec.json` files, 12 reviewed primitives in
`proposal_layer/primitives.py`, `generator.py`, `bias_governor.py`,
`spec_recipes.py`, and the 35 `versions/` champion snapshots.

---

## Part 1 — Audit findings

### 1. Directions explored vs unexplored

The reviewed library defines 12 primitives across 8 declared directions.
Execution coverage in C3 (38 executed proposals, by spec hypothesis tag):

| Direction | C3 executed | Promoted | Gate-rejected | Status |
|---|---|---|---|---|
| model_complexity | 13 | 13 | 0 | Heavily explored (parameter sweeps) |
| validation | 14 | 6 | 8 | Heavily explored |
| feature_engineering | 5 | 2 | 3 | Moderately explored (only 3 nested arm pairs × 2 estimators) |
| model_architecture | 2 | 2 | 0 | Thinly explored (LR vs LightGBM on fixed arms) |
| calibration | 2 | 2 | 0 | Thinly explored (Brier/ECE non-degradation only) |
| **error_analysis** (regime_split_analysis) | **0** | — | — | **Never executed** (primitive `executable=False`) |
| **data_quality** (point_in_time_data_audit) | **0** | — | — | **Never executed** (primitive `executable=False`) |
| **target_design** (target_horizon_robustness) | **0** | — | — | **Never executed** (primitive `executable=False`) |

Additionally `purge_sensitivity_probe` (validation), `complexity_reduction_check`
(model_complexity), and `seed_set_replication` as a distinct replication family
were only partially exercised. Five of twelve primitives are
`executable=False` forward-declarations (harness v1.1.0 not yet implemented),
so three entire directions could never be generated. The harness itself
supports only: nested feature-arm A→B→C→D ablation, LR-vs-LightGBM matched
comparison, calibration stability, and bootstrap CIs on pooled OOF AUC. All
knowledge is therefore discrimination-only (AUC), development-set only.

### 2. Why proposals exhausted before 40 execution slots

The generator is deterministic composition over the closed primitive library:
candidate space = (7 executable primitives) × (small enum grids: 3 arm pairs ×
2 estimators × {n_boot: 500,1000}, 4 arms × {500,1000}, premium {standard,high},
calibration_bins {5,10}) × 2 proposal classes ≈ a few dozen distinct design
signatures. This space was further bounded by:

- **Global permanent already-asked memory** (`already_asked` +
  `recipe_attempts` + duplicate layers are "global and permanent across
  campaigns" — C1/C2 signatures can never be regenerated);
- `max_signature_count: 2` per design signature;
- `max_per_direction: 15`;
- class budgets (falsification 25 / confirmatory 30 / replication 3 /
  exploration 2).

Timeline: the last `phase_generate` with `created > 0` was
**2026-10-07T01:03Z** (cycle ~30 of 40). The final ~10 cycles produced
`created: 0` — the admissible-signature space was empty
(`candidates_remaining == 0`, `agent_state.research_exhausted: True`,
`stagnation_mode: True`). The loop kept draining the approved backlog
(11 executions after Oct 7 01:03) and stopped at 38/40 with the portfolio
minimums met and no admissible proposal. **The 40-slot cap was never the
binding constraint; the ~7-primitive signature space was.** Budget
underspend of 2 slots is an honest reflection of exhaustion, not a failure.

### 3. Refusal and rejection breakdown (all 19 REFUSED + 11 gate-rejections)

Pre-C3 generation refusals (15, ledger-wide, before C3 start):
- **NEAR_DUPLICATE: 9** — "hypothesis text near-duplicate of a prior proposal"
  (duplicate layer text-similarity ≥ 0.90).
- **BUDGET_EXHAUSTED: 6** — C2-stage-2's 4-execution budget was consumed;
  further admissible proposals were refused rather than executed.

C3 refusals (4, all at C3 start 2026-10-05T20:38Z):
- **BIAS_QUOTA: 4** — "accepting confirmatory keeps falsification share at
  0.00 < required 0.35". The bias governor correctly steered: while the
  falsification share is below the 0.35 floor, confirmatory proposals cannot
  be accepted.

C3 executed-but-rejected (11 at adjudication, not "refusals"):
- **Evaluation-gate failures: 11** — all with `checks.evaluation: FAIL`
  (other gates PASS), i.e. the predeclared primary-metric delta threshold
  (typically +0.01 complexity premium, CI lower ≥ -0.01) was not cleared.
  Example: `exp-proposal-a965e420e11b`, delta -0.000713.
- 2 C3 executions were **interrupted** (crash recovery; counted, not re-run).

No refusal came from outcome-based selection, LLM judgment, or gate weakening.
Every constraint that fired is a predeclared, documented policy.

### 4. Are the 27 promotions distinct research directions?

**No.** 27 total promotions (25 in C3 + 2 in C2) collapse to **8 distinct
hypothesis texts**:

- 13× the same model_complexity hypothesis ("complexer estimator must clear a
  predeclared complexity premium over LogisticRegression") with different
  (arm, n_boot, premium) parameters — and only **8 distinct primary_delta
  values** across the 25 C3 promotions (e.g. 0.023312 appears 4×, 0.081817 3×,
  0.025192 5×, 0.001168 3×). The same underlying measurement (same arm pair,
  same estimator comparison) was re-executed at different n_boot and against
  different pinned parents, producing near-identical deltas.
- 6× "Challenge a marginal gain" (minimum_effect_falsifier), 3×
  seed-set replication, 2× calibration stability, 1× feature-arm ablation,
  1× model-class comparison (the final champion).

**Comparison baselines:** every C3 spec pinned `baseline_id:
BASELINE_RECONSTRUCTED_2026_10` and a `parent_version` champion pinned at
approval time (ranging V2.0.10–V2.0.34). So comparisons are internally
consistent (same reconstructed baseline, same frozen dataset SHA, same purged
walk-forward folds), but promotions are chained to rotating parents, not to a
fixed root baseline — see finding 5.

### 5. Is the final champion's improvement supported by comparable experiments?

**Partially — with a significant caveat.** I reconstructed the absolute
champion trajectory from the 35 `versions/` snapshots:

```
V2.0.10 0.6719 | V2.0.11 0.6836 | V2.0.12 0.6848 | V2.0.13 0.6848
V2.0.14 0.6608 | V2.0.15 0.6836 | V2.0.16 0.6848 | V2.0.17 0.6608
V2.0.18 0.6778 | V2.0.19 0.6848 | V2.0.20 0.6778 | V2.0.21 0.6836
V2.0.22 0.6778 | V2.0.23 0.6719 | V2.0.24 0.6848 | V2.0.25 0.6778
V2.0.26 0.6848 | V2.0.27 0.6836 | V2.0.28 0.6836 | V2.0.29 0.6848
V2.0.30 0.6848 | V2.0.31 0.6608 | V2.0.32 0.6836 | V2.0.33 0.6719
V2.0.34 0.6719 | V2.0.35 0.6836  (pooled OOF AUC)
```

- **The trajectory is NOT monotone.** Absolute pooled AUC oscillates within a
  narrow band (0.6608–0.6848, range 0.024). The final champion V2.0.35
  (0.6836) is **not the best absolute scorer ever held** — V2.0.12/13/16/19/
  24/26/29/30 all held 0.6848.
- The recorded `delta_auc` of each promotion is measured **vs its pinned
  parent at approval time**, not vs the standing champion at execution time.
  Several promotions therefore *replaced a better absolute scorer with a
  slightly worse one* (e.g. V2.0.17 0.6608 → V2.0.18 0.6778 is fine, but
  V2.0.13 0.6848 → V2.0.14 0.6608 was a regression under a positive delta vs
  its own parent). The chain is internally consistent per-experiment (each
  passed its own gates against its own baseline), but "V2.0.35 is the best
  model" is **not** supported; "V2.0.35 is a validly-gated member of a
  plateau band around ~0.68" **is** supported.
- The final experiment `exp-proposal-22dfde2c603c` is correctly identified:
  baseline `BASELINE_RECONSTRUCTED_2026_10`, parent pinned V2.0.34,
  `holdout_touched: false`, six gates PASS, dataset SHA matches the frozen
  event table, artifact SHA recorded. Its +0.0233 delta is vs the
  reconstructed baseline's arm, as predeclared.
- Correctness of individual experiments: yes — comparable folds, frozen
  hyperparameters, no leakage, byte-reproducible artifacts. The weakness is
  **interpretive**, not procedural: the promotion rule optimizes
  "beat pinned parent," which does not equal "improve the champion line."

### 6. Would expanding the proposal space yield meaningful new experiments?

**Not by widening parameter grids alone.** More n_boot values, more
calibration bins, or more arm-pair permutations of the same 7 primitives
would produce re-measurements of already-recorded comparisons — the repeated
delta values in finding 4 prove the underlying statistics are saturated.

**Yes, if the expansion adds genuinely new measurement axes.** The three
never-executed directions measure things the current champion has *never*
been tested on:

- **Regime split** (bull/bear/high-vol subperiods): does the ~0.68 plateau
  hold across regimes, or is it concentrated? Currently unknown — a real
  scientific gap, not a variation.
- **Point-in-time data audit**: are the frozen inputs genuinely point-in-time
  complete? The baseline reproduction record already flags this as a known
  historical risk; it has never been experimentally probed in C3.
- **Target horizon robustness**: is the finding stable to the 20d-horizon
  label definition? Currently out of scope of the harness.
- **Purge sensitivity / complexity reduction**: do the gains survive wider
  purging and a smaller model? These falsify the plateau itself.

These are falsification-shaped questions with real refutation potential —
exactly what the bias governor wants — rather than incremental confirmatory
sweeps.

### 7. Smallest set of changes to make Campaign 4 meaningfully different

1. **Implement harness v1.1.0 support for the 5 `executable=False` primitives**
   (regime_split_analysis, point_in_time_data_audit,
   target_horizon_robustness, purge_sensitivity_probe,
   complexity_reduction_check) — the single highest-leverage change; it opens
   3 untouched directions without touching any existing gate.
2. **New campaign config** with a fresh campaign ID (the duplicate
   already-asked memory stays global/permanent by design — new primitives
   automatically generate new signatures, so no memory reset is needed).
3. **Champion-line integrity rule**: require promotion to compare against
   *both* the pinned parent and the current standing champion (or record a
   regression flag), fixing the non-monotone-line artifact of finding 5.
4. **Rebalance class budgets** toward falsification/replication (the 13×
   repeated confirmatory complexity sweeps showed the old budget favored
   low-information confirmatory volume).
5. Optionally widen `n_boot`/threshold grids — *not* recommended as the
   primary change (finding 6).

Everything else — gates, duplicate layers, bias governor floors, holdout
seal, outcome blindness — should stay identical. The safety architecture is
not the problem; the proposal vocabulary was.

---

## Part 2 — Campaign 4 Proposal (DRAFT — AWAITING HUMAN APPROVAL)

**Status: proposal only. No configuration written, no code implemented, no
experiments authorized. Requires explicit human approval of (a) the harness
v1.1.0 work and (b) a new frozen campaign config before anything runs.**

### Research objective and hypotheses

**Objective:** Test whether the champion plateau (~0.68 pooled OOF AUC,
V2.0.10–V2.0.35) is regime-robust, definition-robust, and parsimonious — the
orthogonal questions Campaign 3's primitive vocabulary could not ask.

Hypotheses (all falsifiable, predeclared):
- **H1 (regime):** The champion's pooled gain holds in every predeclared
  market regime split; refutation = any regime with delta < 0 and CI excluding
  improvement.
- **H2 (data):** Frozen inputs are point-in-time complete; refutation = any
  audited feature family with look-ahead contamination.
- **H3 (target):** The gain is stable to label-horizon perturbation;
  refutation = delta collapse at an adjacent horizon.
- **H4 (parsimony):** A reduced-complexity variant retains the gain within a
  predeclared equivalence margin; refutation = loss beyond margin.
- **H5 (purge):** Gains survive wider embargo purging; refutation = gain
  depends on narrow purge.

### What is genuinely new relative to Campaign 3

- 3 never-executed directions (error_analysis, data_quality, target_design)
  + 2 never/thinly-exercised validation primitives (purge sensitivity,
  complexity reduction).
- 5 of 12 primitives become executable for the first time (harness v1.1.0).
- Every experiment is a *new measurement axis*, not a parameter re-sweep of
  the 8 saturated hypothesis texts.
- Champion-line integrity rule (compare vs standing champion too) — new
  governance, not new science.

### Proposed experiment families and rationale

1. `regime_split_analysis` family — regime-conditional performance of the
   champion configuration (H1).
2. `point_in_time_data_audit` family — contamination audit of feature
   families, highest evidence priority per `direction_priorities` (H2).
3. `target_horizon_robustness` family — label-definition sensitivity (H3).
4. `complexity_reduction_check` family — falsifier: can a smaller model hold
   the gain? (H4).
5. `purge_sensitivity_probe` family — leakage-margin falsifier (H5).
6. A small `seed_set_replication` tranche on the champion config as the
   stability anchor (replication class; uses the freed replication budget).

### Budget and stopping criteria

- **Executions: 30** (lower than C3's 40 — the space is narrower per
  direction but each experiment is higher-information; the human funds the
  budget, I propose only).
- **Proposals: 45**, `max_per_direction: 12`, class budgets skewed
  falsification-heavy (e.g. falsification 18 / confirmatory 12 /
  replication 6 / exploration 9 — exact numbers to be set in the frozen
  config for your approval).
- **Stop conditions:** identical fail-closed set as C3
  (`PORTFOLIO_COMPLETE`/`PROPOSAL_EXHAUSTED`, duplicate exhaustion,
  invariant/bypass stops, config-hash mismatch, stale lock). No automatic
  budget increases; underspend is acceptable and reported honestly.

### Evaluation and comparison-baseline policy

- Same frozen baseline `BASELINE_RECONSTRUCTED_2026_10` and frozen dataset
  (`study_v1_development_event_table`, SHA `232de7db…`) unless H2 finds
  contamination, in which case the campaign stops for human review rather
  than silently switching data.
- Same purged walk-forward folds [2023, 2024, 2025], same gate set and
  thresholds (no weakening; new primitives get *new* predeclared gates written
  into the harness before launch).
- **Dual comparison rule:** every adjudication records delta vs pinned parent
  *and* vs the current standing champion, with an explicit
  `champion_regression: true/false` flag; regression is allowed only with the
  flag recorded (preserves outcome blindness while making the line honest).
- Backtest remains NOT_RUN; no trading claims.

### Leakage, duplicate, provenance, reproducibility checks

- Holdout SEALED/uses 0, untouched, same policy text in the new config.
- Duplicate layers unchanged: global permanent already-asked memory means
  C3's signatures can never be re-asked; new primitives yield new signatures
  organically (no memory reset).
- Spec fingerprints, five-gate validation, artifact SHA-256s,
  per-promotion `versions/` snapshots, append-only ledgers, and campaign
  config SHA pinning all carry over unchanged.
- Harness v1.1.0 additions must ship with unit tests in the existing test
  suite style (`test_*`) and a reviewed design note before any campaign
  config references them — reviewed by you, not by the loop.

### Expected limitations and failure conditions

- Still development-data-only; no prospective outcomes; fixed-universe
  survivorship risk persists (inherited, documented).
- Regime splits reduce per-cell sample sizes — CIs will widen; some
  falsifiers may be uninformative rather than passing (will be reported as
  such, not as success).
- Harness v1.1.0 is new code: the first executions carry integration risk;
  the interrupted-execution accounting (counted, never re-run) handles this
  honestly.
- If H2 finds real contamination, Campaign 4's premise is invalidated —
  the correct outcome is a STOP and a data-lineage review, not a pivot.
- The loop may again exhaust proposals early (a virtue, not a bug); expect
  possible underspend.

### What I need from you to proceed (in order, none taken yet)

1. Approve (or reject) implementing harness v1.1.0 for the 5 primitives.
2. Approve the dual-comparison champion-integrity rule.
3. Approve/finalize the C4 budget numbers and class budgets.
4. I then draft the frozen `campaign_config` for your review — you (the
   human) fund and authorize the campaign; I do not self-authorize.
