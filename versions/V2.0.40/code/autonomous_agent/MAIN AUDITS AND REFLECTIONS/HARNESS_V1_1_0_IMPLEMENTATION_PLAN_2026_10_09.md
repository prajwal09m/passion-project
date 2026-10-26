# Harness v1.1.0 Implementation Plan (C4 prerequisite) — REVISED DRAFT v3

Date: 2026-10-09; revised 2026-10-10 after the plan-only statistical review
(H-10 method comparison specified, H-10b provisionally resolved, H-11
census specified, mirror experiment resolved, safeguards re-confirmed; the
original human decisions H-1…H-8 were recorded 2026-10-09). Companion to
`CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json`.
**Status: plan only. No harness code written. Not approved for implementation
until this revised plan is explicitly approved. Nothing here runs experiments
or launches campaigns.**

## Goal

Flip the five `executable=False` primitives in
`autonomous_agent/proposal_layer/primitives.py` to `executable=True` by
teaching the existing reviewed harness the five measurement axes they declare.
This opens the three never-executed directions (error_analysis, data_quality,
target_design) plus two dormant falsifiers (purge sensitivity, complexity
reduction) — the entire scientific delta of Campaign 4.

Primitives to implement (all already reviewed/declared; only execution support
is missing):

| Primitive | Direction | Class | Harness min version |
|---|---|---|---|
| `regime_split_analysis` | error_analysis | falsification | 1.1.0 |
| `point_in_time_data_audit` | data_quality | confirmatory (not falsification_capable) | 1.1.0 |
| `target_horizon_robustness` | target_design | falsification | 1.1.0 |
| `purge_sensitivity_probe` | validation | falsification | 1.1.0 |
| `complexity_reduction_check` | model_complexity | confirmatory | 1.1.0 |

(`seed_set_replication` is already executable; no change.)

## Design principles — no new gate architecture

1. **Same execution seam.** All five run through
   `experiment_adapter.ExperimentAdapter.run_experiment` inside the same
   candidate workspace model (`files_allowed_to_change` limited to
   `autonomous_agent/experiments/*`), the same fingerprint assertions
   (`original_fingerprint`, `assert_original_unchanged`), the same timeout and
   resource limits. No new subprocess paths, no new permissions.
2. **Same five gates, new predeclared acceptance criteria per primitive.**
   unit / data_integrity / walk_forward / leakage / robustness stay exactly as
   they are; each primitive's acceptance criteria are read from the spec's
   `evaluation_protocol.acceptance_criteria` (as today), with margins declared
   *in the primitive definition* and copied into each spec at generation time.
   Nothing is decided after results are seen.
3. **Same outcome blindness.** Ranking inputs unchanged; preregistered
   expectation still recorded after ranking and never scored.

## Freeze-before-generation rule (H-decision container)

Every ladder, primary comparison, margin, sample floor, and multiplicity rule
in this plan is **frozen into the primitive definitions at implementation
review time — before any proposal is generated**. None may be edited after
generation begins, and none may be tuned using Campaign 4 results. The
spec-fidelity test (below) enforces byte-identical transfer from primitive
definition to generated spec.

### Margin provenance (H-1)

The value **-0.01 is a provisional study-consistency margin** carried over
from the existing gates' `ci_lower_min: -0.01`. It is **not** a statistically
validated or application-derived margin: no cost model exists
(`backtest: NOT_RUN`; trading claims prohibited), so no domain-derived
equivalence bound can be computed. Every robustness or non-inferiority
**pass must additionally satisfy the appropriate confidence-interval
requirement specified per primitive below** — a point estimate alone never
passes anything (H-1). All uses of -0.01 are marked PROVISIONAL in the
primitive definitions.

## Shared three-valued result model (applies to all five primitives)

Every v1.1.0 experiment evaluates to exactly one of:

- **ROBUST** — every predeclared primary condition passes, including its
  CI requirement. Only ROBUST can satisfy the evaluation gate.
- **REFUTED** — a predeclared primary condition is refuted under the
  multiplicity rule below (a formal refutation claim).
- **INCONCLUSIVE** — neither (including all under-powered / under-sized /
  wide-CI outcomes).

**INCONCLUSIVE handling (H-8, fail-closed):** the experiment **consumes its
authorized execution slot, fails the evaluation gate, and cannot promote a
candidate. No automatic reruns. No threshold relaxation.** INCONCLUSIVE is
reported as-is in the ledger — never upgraded to a pass and never recorded
as a refutation.

**Point-estimate-only pass conditions are forbidden** everywhere in this
plan: every pass condition pairs a point-estimate threshold with its
CI requirement.

## Multiplicity handling (H-6, resolved: per-campaign Holm)

Predeclared and frozen before generation:

- **Intersection–union logic for claims requiring all primary conditions to
  pass** (regime robustness, every horizon rung, every purge rung): no
  multiplicity correction is applied to the pass direction — every member
  test must independently pass its own point + CI condition. IUT and Holm
  are strictly separate mechanisms: IUT governs ROBUST (promotion-eligible)
  claims; Holm governs formal refutation claims only.
- **Per-campaign Holm correction for formal refutation claims** within the
  four predeclared families below. Family **membership rules** are frozen
  here before proposal generation and may not be broadened, narrowed, or
  redefined after results exist; the concrete member count depends only on
  how many experiments of that family the campaign executes:
  - *Regime family:* every per-cell refutation test produced by every
    `regime_split_analysis` experiment adjudicated in Campaign 4
    (2 cells per experiment: above / below SMA200).
  - *Horizon family:* every per-rung refutation test produced by every
    `target_horizon_robustness` experiment in Campaign 4 (3 rungs per
    experiment: 1, 2, 3 sessions).
  - *Purge family:* every per-rung refutation test produced by every
    `purge_sensitivity_probe` experiment in Campaign 4 (3 rungs per
    experiment: +0, +5, +10 sessions).
  - *Complexity family:* every primary-rung refutation test produced by
    every `complexity_reduction_check` experiment in Campaign 4 (1 test per
    experiment).
  Only tests generated by Campaign 4 experiments of the named primitive
  enter a family; Campaign 1–3 tests are never pooled in, and no other
  primitive's tests enter these families.
- **Pooling and timing:** each refutation test's *unadjusted* results are
  recorded at adjudication as today (three-valued provisional label:
  provisional-REFUTED if the unadjusted CI upper < 0, else provisional-
  ROBUST/INCONCLUSIVE). The **Holm step-down adjustment (familywise
  α = 0.05) is computed over the complete family at campaign end** and
  written as an append-only campaign-end multiplicity record listing every
  member test, its unadjusted p-value/CI/delta, its adjusted p-value, and
  its final REFUTED/not-REFUTED status. Campaign-end pooling is safe for
  selection integrity because REFUTED and INCONCLUSIVE both fail the
  evaluation gate — no promotion outcome can change retroactively; only the
  strength of the *refutation claim* is finalized.
- **Provisional-to-formal firewall (required before implementation):** at
  adjudication the ledger and loop events may record only a *refutation
  signal* with an explicit provisional marker (e.g. `refutation_signal:
  unadjusted`, `formal_refutation: false`). The bare three-valued label
  **`REFUTED` must not appear anywhere — ledger rows, loop events, stdout,
  reports, or summaries — until the campaign-end multiplicity record exists
  and assigns it via the Holm-adjusted decision.** Pre-campaign-end readers
  must render such signals as "provisional, not a refutation claim". If the
  campaign terminates before the campaign-end multiplicity pass runs
  (exhaustion, manual stop, crash), the pass still runs as a mandatory
  finalization step on the archived ledger; if it can never run, every
  provisional signal defaults to **INCONCLUSIVE** (fail-closed) and no
  formal refutation exists. No document may assert a formal refutation
  before that record is written.
- **p-value method (H-10, UNRESOLVED):** three candidates — (a) sign
  proportion `p = (#{δ*_b ≥ 0} + 1) / (B + 1)` over the harness's existing
  paired moving-block replicates, (b) paired week-block sign-flip/
  permutation, (c) normal-approximation z from the bootstrap SE — are
  compared against the actual paired OOF week-block design in the H-10
  specification below, with assumptions, failure modes, and predeclared
  null-calibration + Holm FWER simulation protocols (SIM-1…SIM-5). **None is
  chosen: the simulations have not been run, so no evidence supports a
  choice.** H-10 stays open until that evidence exists and a human decision
  is recorded.
- **Unadjusted retention:** raw deltas, raw CIs, unadjusted p-values, and
  adjusted p-values are all retained; the campaign-end record must show
  unadjusted and adjusted side by side. Final REFUTED labels are determined
  by the Holm-adjusted decision only; unadjusted signals that do not survive
  adjustment are recorded as INCONCLUSIVE, never as refutations.

### H-10 statistical specification — UNRESOLVED (three candidates compared, none chosen)

The candidate below is recorded for review; **it is not approved**. H-10
remains open until every element is justified in writing and a human
decision is recorded. No method may be adopted by default.

| Element | Proposed specification | Status |
|---|---|---|
| Null / alternative | Per refutation test: H0: δ ≥ 0 vs H1: δ < 0, where δ = candidate − reference pooled OOF AUC for that cell/rung | Consistent with existing gate semantics (CI upper < 0 = "clearly worse") — ESTABLISHED |
| Test statistic | One-sided bootstrap sign proportion `p = (#{δ*_b ≥ 0} + 1) / (B + 1)` over existing paired replicates | CANDIDATE, NOT JUSTIFIED: percentile-bootstrap sign p-values are not guaranteed super-uniform under H0, which Holm requires |
| Resampling unit | Moving-block bootstrap of whole weeks over pooled OOF rows (the harness's existing `block_weeks` machinery); B = the spec's `n_boot` | Established as machinery; B-feasibility below is open |
| Pairing | The same resampled week blocks drive both arms (paired replicates of the delta), matching the harness's `paired_week_block_bootstrap` | ESTABLISHED (must match CI pairing); divergence test required |
| Dependence assumptions | Whole-week blocks preserve within-week cross-event and cross-sectional dependence; block length is assumed sufficient for serial dependence of daily OOF residuals | NOT validated empirically on this dataset; misspecification direction (conservative vs liberal) unknown — must be disclosed in any result record |
| Multiplicity integration | Holm step-down, FWER α = 0.05, once at campaign end over the predeclared families; requires each member p to be super-uniform under its H0 | Holm machinery ESTABLISHED; validity is conditional on the unresolved statistic choice |
| Granularity / feasibility | Sign p has minimum 1/(B+1); Holm's first threshold is α/m, so any rejection requires B + 1 ≥ 20·m. Exact bounds: **B=500 valid only for family size m ≤ 25; B=1000 for m ≤ 50.** With `max_per_direction: 12`, horizon/purge families reach m = 36 → **n_boot must be ≥ 719 → 500 is infeasible for those families**; if direction caps did not bind, m could reach 90 (B ≥ 1799, outside the grid) | RESOLVED PROVISIONALLY by H-10b (below): B = 1000 provisional minimum + `B + 1 ≥ 20·m` freeze-time test, fail-closed |
| Validation tests | Applied to **every** candidate, not just (a): (1) null-calibration simulation → p super-uniform, type-I ≤ nominal; (2) family-level simulation → Holm FWER ≤ 0.05; (3) disagreement rate between the p decision and percentile `CI upper < 0` reported; (4) feasibility check `B + 1 ≥ 20·m` executed at freeze; (5) paired-vs-unpaired divergence test asserting the paired form. Full protocols predeclared as SIM-1…SIM-5 below | REQUIRED before any method choice; none run yet |

#### H-10 method comparison — candidates vs the actual paired OOF week-block design

The design every candidate must be judged against (the harness's existing
machinery): pooled out-of-fold scores over chronological folds [2023, 2024,
2025]; one score per event row per arm; whole calendar weeks are the
resampling unit (`block_weeks`); each bootstrap draw samples weeks with
replacement and applies the **same** sampled weeks to both arms (paired),
producing B replicate deltas δ*_b; percentile CIs for the gates come from
these replicates. Two properties matter for p-values: (i) the replicates
are **centered on the observed δ̂, not on a null-imposed distribution**, and
(ii) the effective sample size is the number of weeks (~150 in-sample
weeks), not 61,045 rows.

**Candidate (a) — sign proportion over the existing paired replicates.**
`p_a = (#{δ*_b ≥ 0} + 1)/(B + 1)`; no new machinery.
- *Assumptions:* the percentile bootstrap distribution proxies the sampling
  distribution of δ in the region ≥ 0 under H0 (null-consistency of the
  percentile bootstrap); p_a is super-uniform under H0 for every member
  test (what Holm requires); the CI's block/dependence assumptions hold.
- *Failure modes:* (1) non-null-centered replicates make this a percentile-
  interval inversion rather than a null-imposed test — under H0 with a
  biased or skewed bootstrap distribution the error rate can be liberal or
  conservative in an unknown direction; (2) granularity floor 1/(B+1)
  collides with Holm's α/m thresholds (H-10b); (3) coarse step function →
  tied p-values across members, requiring deterministic tie handling in the
  step-down; (4) inherits every block-length misspecification of the CI.
- *Cost / consistency with the gate:* zero new computation; mechanically
  aligned with the percentile-CI gate, so the disagreement rate is directly
  measurable (SIM-3).

**Candidate (b) — paired week-block sign-flip/permutation.**
M recomputations of the AUC delta under blockwise arm-label inversions;
`p_b = (#{T* ≤ T_obs} + 1)/(M + 1)`.
- *Assumptions:* exchangeability of the two arm labels under H0. The arms
  are deterministic, non-randomized model configurations, so there is no
  randomization basis; the test must rest on symmetry of the week-level
  paired contribution distribution about 0, plus adequate whole-week
  blocking.
- *Failure modes:* (1) AUC is a rank statistic over pooled rows and week
  contributions are typically skewed (unequal week sizes, uneven positives)
  → symmetry is doubtful and the type-I distortion direction is unknown;
  (2) requires **new** resampling machinery — a full AUC recomputation per
  flip — and a new budget knob M with its own granularity floor 1/(M+1)
  against Holm; (3) flip granularity matters: row-level flipping destroys
  the within-week dependence the design exists to preserve; (4) it does not
  reuse the existing replicate set, so its p and the gate's CI would come
  from different resampling runs (divergence risk — SIM-5).

**Candidate (c) — normal-approximation z from the bootstrap SE.**
`z = δ̂ / SE_boot`, `p_c = Φ(z)` (one-sided, H1: δ < 0); SE reuses the
existing paired replicates.
- *Assumptions:* asymptotic normality of the pooled OOF AUC difference;
  consistent block-bootstrap SE; normal-tail accuracy at the small levels
  Holm demands (α/m ≈ 5.6×10⁻⁴ at m = 90).
- *Failure modes:* (1) effective n is the number of weeks and small cells
  (below-SMA200: n = 3,752, 932 positives) make skewness of the AUC-
  difference distribution plausible → tail extrapolation unreliable;
  (2) anti-conservative if the one-week block under-captures serial
  dependence (SE underestimated → z inflated); (3) structural possibility of
  disagreeing with the percentile-CI gate (a z-test can reject where the
  percentile CI does not) — the five gates and the campaign-end record
  could then contradict each other (SIM-3); (4) no granularity floor (its
  one advantage), but every small p-value rests entirely on the asymptotic
  tail.

**Comparison summary:**

| Criterion | (a) sign proportion | (b) sign-flip/permutation | (c) normal z |
|---|---|---|---|
| New machinery | none | full AUC-recompute loop + new budget M | none |
| Null-imposed resampling | no (centered on δ̂) | yes (by construction) | no (asymptotic) |
| Granularity floor vs Holm | 1/(B+1) → H-10b | 1/(M+1) → same issue | none |
| Distributional reliance | bootstrap proxy + super-uniformity | symmetry/exchangeability of week contributions | normality at ~150 effective n |
| Same resampling as CI gate | yes (identical replicates) | no (separate run) | yes (SE only) |
| Principal open risk | liberal or conservative in unknown direction | invalid symmetry assumption | anti-conservative small-n tail |

**Predeclared simulation protocols (must run before any choice; synthetic
data only, no campaign results, no real-data tuning):**

- **SIM-1 — null calibration (per candidate).** DGP cells with δ = 0
  exactly: (i) balanced weeks, symmetric contributions; (ii) skewed week
  sizes / positive rates (market-regime-like); (iii) within-week
  correlation ρ ∈ {0, 0.5, 0.9}; (iv) regime-cell-like small sample
  (n ≈ 3,752, ≈932 positives); (v) power side-check at true δ = −0.01 (not
  a calibration cell). N = 1,000 simulated trials per cell; record empirical
  rejection rates at α ∈ {0.10, 0.05, 0.025, 0.01} with exact binomial
  intervals, plus p-value histograms. *Pass criterion:* no cell
  significantly **above** nominal (liberal ⇒ invalid under Holm);
  conservative cells are valid but must be disclosed as power loss.
- **SIM-2 — Holm family-wise error (per candidate).** Global-null families
  with m ∈ {1, 4, 12, 24, 36, 50, 90}; member-test correlation induced
  through shared weeks at ρ ∈ {0, 0.3, 0.7}; B or M ∈ {500, 1000, 2000};
  N = 2,000 simulated campaigns per configuration. *Pass criterion:* FWER
  not significantly above 0.05 (one-sided, exact binomial); conservative
  results reported as such. The frequency of any-rejection also
  empirically documents the 1/(B+1) grid (analytical bound: B + 1 ≥ 20·m).
  One mixed configuration (one true H0 among strong H1s) confirms the
  adjustment does not destroy all power.
- **SIM-3 — CI-vs-p disagreement (per candidate).** On SIM-1/SIM-2
  outputs, count cases where the unadjusted p decision (p ≤ α) disagrees
  with the percentile `CI upper < 0` decision. *Pass criterion:* disagreement
  ≤ 1% at α = 0.05; above that, the method's decision rule must be
  reconciled with the gate before adoption, else the gates and the
  multiplicity record can contradict each other.
- **SIM-4 — freeze-time feasibility (deterministic; applies whichever
  method is chosen).** `B + 1 ≥ 20·m` for every declared family under the
  frozen config — this is the H-10b freeze test below, run regardless of
  method because any candidate with a discrete floor inherits it.
- **SIM-5 — paired-implementation divergence.** The paired path must match
  `paired_week_block_bootstrap` outputs bit-for-bit on a fixture, and a
  deliberately unpaired control must show measurably different null
  behavior (guards against accidentally implementing (a)/(c) unpaired).

**Decision rule (predeclared):** a candidate is adoptable only if it passes
SIM-1 (no liberal cell), SIM-2, SIM-3, and SIM-4. If exactly one passes, it
is adopted subject to explicit human confirmation; if more than one passes,
the human picks and the choice is recorded as the H-10 decision; if none
passes, **H-10 stays UNRESOLVED and Campaign 4 launch is blocked**
(fail-closed — the p-value gate test already refuses to compute adjusted
p-values until H-10 is resolved).

**H-10 status: UNRESOLVED.** No SIM has been executed — running them
requires writing simulation/test code, which is out of scope for this
plan-only review. No evidence exists yet, therefore **no method is chosen**
and none may be adopted by default.

**H-10b — RESOLVED PROVISIONALLY (granularity/feasibility only):**

- `n_boot = 1,000` is the **PROVISIONAL minimum** for every experiment
  feeding a Holm family (500 is disallowed for those primitives).
- Predeclared freeze-time feasibility condition: for **every** declared
  Holm family with member bound `m`, the frozen `n_boot` must satisfy
  **`B + 1 ≥ 20·m`**. Checked deterministically at freeze (SIM-4 is its
  empirical counterpart). Under B = 1000: families up to m ≤ 50 are
  feasible — regime (m ≤ 24), horizon (m ≤ 36), purge (m ≤ 36), and
  complexity (m = 1) all pass under `max_per_direction: 12`; a family that
  could reach the unbound m = 90 needs B ≥ 1799, so the freeze must either
  cap that family's member count in config or set `n_boot ≥ 1799` (grid
  ceiling 2000).
- **Fail-closed:** if the configured `n_boot` cannot meet `B + 1 ≥ 20·m`
  for every declared family, the **freeze is blocked** (no activation); and
  if an experiment with infeasible granularity nevertheless executes, none
  of its signals can ever become a formal refutation — they default to
  INCONCLUSIVE.
- **Scope of this resolution:** H-10b resolves only the attainable-p
  granularity/feasibility question. It **does not establish** that any
  p-value method is statistically valid (H-10 remains open), does not
  establish power for any test, and does not validate −0.01 or any ladder
  margin (H-1 stands). Resolution ≠ validity ≠ power.

## Raw-source lineage inventory — prerequisite for `point_in_time_data_audit` (H-5)

**STATUS: READ-ONLY INVENTORY COMPLETED 2026-10-09** — full findings in the
companion report `POINT_IN_TIME_LINEAGE_INVENTORY_2026_10_09.md` (same
folder). Summary: (a) all 153 raw OHLCV CSVs hash-verify against the v1.0.1
run manifest's `source_data_sha256` (153/153), roster and event-table hashes
match their recorded pins; (b) raw sources carry daily `Date` timestamps
with documented coverage (2020-08-03 → 2026-08-03); (c) structural
point-in-time invariants hold across all 61,045 event rows
(`feature_asof_date ≤ date`, 0 violations; entry/exit strictly after signal
; label = `hold1_ret ≥ 0.02` consistent, 0 violations; no
future/forward/alpha_ columns); (d) an independent recompute spot-check of
the market-regime family from raw SPY bars matched 245/245 sampled rows
using only data available at/before the event date; (e) value-level parity
of `rsi14`, `atr_pct`, `zone_width_pct` with the original V1.0.1 generation
is **unverifiable** (source unrecovered — documented archive limitation,
not evidence of look-ahead).

The temporal-lineage prerequisite for the audit is therefore **satisfied**;
the value-parity limitation must shape the audit's semantics (below).

Before the point-in-time audit primitive is implemented or executed:

- **Audit semantics revision (required before freeze):** "confirmed
  contamination" means demonstrable use of data postdating the event
  timestamp (structural look-ahead), **not** a value mismatch with the
  archive — known parity failures in the three columns above would otherwise
  false-trigger the campaign stop on day one. A value mismatch on a
  parity-unverifiable column yields **UNVERIFIABLE** (audit FAIL, no partial
  pass), while a structural look-ahead finding yields **CONFIRMED
  CONTAMINATION** (stop).
- If a critical feature family's temporal availability cannot be established
  by as-of structure + dated raw inputs: audit FAILS and the campaign
  **stops for human review before further research executions** — unverifiable
  lineage is never treated as proof of safety, and no audit result may be
  fabricated.
- **Completed dependency:** whether trustworthy raw timestamps and lineage
  records exist — answered **YES** by the inventory report (hash-verified
dated raw cache + manifest prefix hashes + as-of invariants).

### Remaining value-level checks — 90 feature columns UNTESTED (H-11)

**Status: preliminary only. No column outside the spot-check is
"verified".** The inventory's evidence is: structural invariants over all
101 feature columns (as-of ordering — necessary but not sufficient for
correct values), plus *direct value recompute* for exactly **2 of 101**
columns (`spy_above_sma200`, `spy_dist_sma200`, 245/245 sampled rows).
Remaining value-level checks before the audit primitive can return PASS
(enumerated by family, with what each requires):

1. **Price/volume technical (48 columns — `rsi14`, `atr_pct`,
   `ema*`, `dist_ema*`, `macd*`, `roc14`, `close_strength`, `daily_return`,
   `return_*`, `realized_vol_*`, `relative_*`, `volume_*`, `bullish_candle`,
   `accumulation_days10`, `zone_width_pct`, …):** recompute each from raw
   OHLCV bars ≤ event date and compare against the frozen table at exact or
   declared-tolerance equality, over all 61,045 rows or a predeclared full-
   column census. **`rsi14`, `atr_pct`, `zone_width_pct`: value parity is
   unverifiable** (V1.0.1 source unrecovered) → these return UNVERIFIABLE,
   never PASS, and never CONFIRMED CONTAMINATION from a value mismatch.
2. **Market-benchmark family (11 columns):** 2 of 11 spot-checked
   (`spy_above_sma200`, `spy_dist_sma200`). The other **9** (`spy_return_5d/
   20d`, `qqq_return_*`, `iwm_return_*`, `relative_strength_*`, `vix_*` —
   exact list to be enumerated from the header at implementation time) still
   need direct recompute from their raw sources (SPY/QQQ/IWM/XVIX CSVs).
3. **`zone_base_*` (8 columns):** recompute zone-base geometry from OHLCV
   bars ≤ event date using the frozen backend's zone definitions.
4. **Order-block structural (34 `ob_bull_*`/`ob_bear_*` columns):**
   recompute impulse/distance/age/volume-ratio features from OHLCV ≤ event
   date using the frozen backend definitions.

**H-11 — RESOLVED (coverage specified; execution still pending): full
feature-by-feature census with frozen tolerances.**

- **Coverage:** every one of the 101 feature columns appears in a **frozen
  census manifest** (column → tier, raw source file + column(s), formula
  reference, tolerance, rows compared, verdict). Any column missing from
  the manifest blocks audit PASS.
- **Tier 1 — full-column recompute** (the default, wherever raw source and
  formula are recoverable): independently recompute the column from raw
  inputs available at/before each event date and compare against the frozen
  table over **all 61,045 rows** — no sampling. The earlier 245/245 market
  spot-check is absorbed into the full census for its 2 columns.
- **Tier 2 — UNVERIFIABLE** (raw source or original formula unrecoverable):
  the column is marked **UNVERIFIABLE** — it can never return PASS, and a
  value mismatch on it can never yield CONFIRMED CONTAMINATION. Known
  Tier-2 members from the archive closeout: `rsi14`, `atr_pct`,
  `zone_width_pct` (V1.0.1 source `29885c5f…` never recovered; 480/480 AAL
  rows differ). Tier assignment is made at freeze from **documented
  recoverability**, never from observed match/mismatch results.
- **Tolerances frozen from documented precision and computation** (before
  any recompute runs): per column, tolerance = (a) half a unit of the last
  documented decimal place of its raw inputs, combined with (b) relative
  tolerance 1e-9 for float64 derived-computation chains, plus (c) any
  documented rounding step in the frozen formula. Integer, boolean, and
  categorical columns compare at exact equality. Tolerances are written
  into the manifest at freeze; **no tolerance may be widened after a
  mismatch is observed** — an out-of-tolerance value is reported as a
  mismatch and investigated, never absorbed by retuning.
- **Structural checks never imply cleanliness:** the as-of ordering,
  banned-column, and label-consistency results (0 violations) are reported
  in a separate structural section and **may not be cited to upgrade any
  column's value verdict**. No column is "verified" by structure alone;
  each is Tier-1 verified by recompute or explicitly disclosed
  UNVERIFIABLE.
- **Residual ruling needed at freeze:** how the audit's three-state outcome
  treats a run whose only defects are disclosed Tier-2 columns (audit FAIL
  vs PASS-with-disclosure). This must be decided and recorded before the
  primitive is implemented — never inferred from results.
- Until the census runs **as part of the audit primitive's execution**, all
  90 unchecked columns (plus the 9 remaining market columns) remain
  **UNTESTED — not verified**.

## Per-primitive acceptance criteria (frozen at implementation review)

### 1. `regime_split_analysis` (H1)

- **Primary split (H-4):** `spy_above_sma200` is the **sole** primary regime
  split. Any VIX-percentile split is **descriptive-only** and can never
  determine acceptance. Regimes come only from event-time columns of the
  frozen event table; no new data.
- **Metric:** per-regime pooled OOF AUC of the champion configuration vs its
  matched reference arm on identical purged folds; primary quantity =
  worst-regime delta (`min_regime_delta`).
- **Sample floors (H-7, provisional feasibility floors):** each regime cell
  requires **≥ 1,500 events and ≥ 150 positives** in the validation folds,
  else the result is **INCONCLUSIVE**. *These floors do not establish
  adequate statistical power* — they are feasibility screens only.
  (Measured today: below-SMA200 cell n=3,752 / 932 positives in folds
  2023–2025 — passes the floor, but power remains unproven.)
- **ROBUST** = worst-regime point estimate ≥ **-0.01 (PROVISIONAL, H-1)**
  **AND** worst-regime CI lower bound ≥ -0.01, with both cells at/above the
  floors.
- **REFUTED** = a regime cell whose CI upper bound < 0, confirmed by
  **Holm correction across the 2-cell regime family** (unadjusted estimates
  retained).
- **INCONCLUSIVE** = anything else (floors unmet, or point/CI conditions
  straddle) → evaluation gate FAIL.

### 2. `point_in_time_data_audit` (H2)

- Deterministic recomputation over the frozen inputs: for every feature
  family, recompute the value as-of each event from raw columns only; flag
  any feature whose recomputation differs or whose inputs postdate the event
  label window. No model training. **Prerequisite: the raw-source lineage
  inventory above.**
- Three states, **no partial pass**:
  - **PASS** — every critical feature family's historical availability is
    established and recomputation matches.
  - **CONFIRMED CONTAMINATION** — a reproducible
    (feature, event, source-column) triple where a used input postdates the
    event/label window → evaluation FAIL **and fail-closed campaign stop**
    (`point_in_time_contamination_detected`) for human data-lineage review.
  - **UNVERIFIABLE** — critical historical lineage cannot be established →
    audit **FAIL** and **campaign stop for human review before further
    research executions** (H-5). Missing evidence is never proof of safety;
    no result may be fabricated.
- This is the only primitive that can STOP the campaign rather than merely
  reject one proposal; that asymmetry is intentional and must be wired
  fail-closed before freeze.

### 3. `target_horizon_robustness` (H3)

- **Corrected target definition (required edit):** the frozen target is
  **"binary label: 1-session hold ≥ +2% (inclusive)"** — there is no 20-day
  target (`return_20d` is a feature). All references to a "20d target" are
  removed from this plan.
- **Horizon ladder (H-2, frozen):** rungs = **1 session, 2 sessions,
  3 sessions**, each using the **same +2% threshold**; the **1-session rung
  is the original reference target**. Per rung: rebuild labels from the same
  frozen raw columns (derived data only — holdout seal and dataset freeze
  unaffected), **recompute exit dates, remove unmatured rows, and verify
  target-maturity purging (`train exit_date < fold start`) for every rung**,
  on identical chronological folds [2023, 2024, 2025].
- **ROBUST** = **every rung** has point delta ≥ 0 **AND** CI lower ≥
  **-0.01 (PROVISIONAL, H-1)** vs the reference arm at that same horizon.
- **REFUTED** = a rung whose CI upper < 0 ("gain exists only at the original
  horizon"), confirmed by **Holm correction across the 3-rung horizon
  family** (unadjusted retained).
- **INCONCLUSIVE** = anything else → evaluation gate FAIL.
- No "best rung" selection: the ladder is a frozen enum; acceptance is
  all-rungs (intersection–union).

### 4. `complexity_reduction_check` (H4)

- Reduced variants of the champion estimator under the same purged folds; a
  **single predeclared primary reduction rung — RESOLVED (H-9) as
  estimator-class substitution: LightGBM → LogisticRegression.** Evidence:
  the primitive's own declared purpose is "simpler **model class** retains
  within-margin performance" (`primitives.py:160-161`) and its parameter
  schema is `{arm, n_boot}` only — there is no hyperparameter-reduction
  knob, so the rung must be at model-class level. The harness permits exactly
  two estimators (`ALLOWED_ESTIMATORS = ("LogisticRegression", "LightGBM")`),
  and both configurations are frozen in
  `state/baseline_reproduction.json.configuration.estimators`:
  - **Reduced (candidate):** LogisticRegression — `C=1.0, penalty=l2,
    solver=lbfgs, max_iter=2000, random_state=42`, pipeline
    `SimpleImputer(median, keep_empty_features=True) → StandardScaler →
    LogisticRegression`, all fitted on training fold only.
  - **Reference:** LightGBM — `n_estimators=300, max_depth=6, num_leaves=31,
    learning_rate=0.03, min_child_samples=30, colsample_bytree=0.8,
    subsample=0.8, subsample_freq=1, reg_alpha=0.1, reg_lambda=0.5,
    deterministic=true, n_jobs=1, random_state=42, verbosity=-1`, pipeline
    `SimpleImputer(median) → LGBMClassifier`.
  - **Comparison protocol:** on the spec's declared arm (params `arm ∈
    {A,B,C,D}`, `n_boot` from the frozen grid), identical purged folds
    [2023, 2024, 2025], same moving-block bootstrap, pooled OOF AUC;
    `delta = AUC_LR − AUC_LGBM`.
  - **Explicitly NOT adopted:** any fewer-trees / fewer-leaves rung. No
    frozen record predeclares such a value; pinning one would be inventing
    a number (H-9 instruction). If a human later supplies exact values,
    that requires a plan amendment before generation.
  All other ladder rungs are **descriptive only**, reported unadjusted,
  never scored.
- **Framing: non-inferiority, not point-estimate equivalence.**
- **Overlap with `model_class_comparison` (documented, required):** this
  experiment measures the *same* paired (LR, LightGBM) OOF scores on the
  same arm/folds/bootstrap as the existing `model_class_comparison` primitive
  — the difference is the predeclared **decision rule and claim**: that
  primitive gates non-degradation of the complex class; this one tests
  **model-class non-inferiority** (is the simpler class within -0.01 of the
  full class?). Because the primitive IDs and hypothesis text differ,
  duplicate layers will not pair them; the relationship must instead be
  recorded in the spec and result record (`related_primitive:
  "model_class_comparison"`) and disclosed in any summary that reports it.
  Reuse of already-measured (LR, LightGBM) scores is permitted **only**
  under the mirror-experiment decision below (related reanalysis, count-once,
  no independent-confirmation claims).
- **Claim prohibition:** no output, report, or summary of this experiment
  may claim — directly or by implication — that it establishes **tree-count,
  leaf-count, depth, or any other hyperparameter/complexity reduction** of
  LightGBM. The rung tested is *estimator-class substitution only*. Any
  result phrased as "complexity reduction demonstrated" is a protocol
  violation, independent of the numbers.
- **ROBUST (non-inferiority demonstrated)** = primary rung's **CI lower
  bound of (reduced − full) ≥ -0.01 (PROVISIONAL, H-1)** under the existing
  moving-block bootstrap.
- **REFUTED** = primary rung CI upper < 0 (the reduction is clearly worse).
- **INCONCLUSIVE** = anything else — including wide-CI outcomes that would
  have "passed" on a point estimate → evaluation gate FAIL. A smaller model
  therefore cannot pass merely because uncertainty is large (H-1 CI
  requirement).
- Multiplicity: single-test family; Holm is a no-op (documented).

### 5. `purge_sensitivity_probe` (H5)

- **Purge ladder (H-3, frozen semantics):** extra embargo gaps of **0, 5,
  and 10 additional trading sessions beyond the existing target-maturity
  purge**. Exact semantics (gap applied strictly between last training
  signal date and fold start; gap expressed in trading sessions; interaction
  with label maturity unchanged) are **frozen here before implementation**.
  The ladder is a fixed enum in the primitive definition — never "read at
  runtime".
- **Never weakens the standard purge or the leakage gate:** the champion and
  all existing experiments keep their original target-maturity purge
  regardless of probe results; the probe only ever tests *stricter*
  settings, and its results cannot modify the leakage gate.
- **ROBUST** = **every rung** has point delta ≥ 0 **AND** CI lower ≥
  **-0.01 (PROVISIONAL, H-1)**.
- **REFUTED** = a rung whose CI upper < 0 (the gain depends on narrower
  purging), confirmed by **Holm correction across the 3-rung purge family**
  (unadjusted retained).
- **INCONCLUSIVE** = anything else (including a monotone decline with CIs
  crossing zero) → evaluation gate FAIL. Declining performance with
  widening purges is never interpreted as robustness evidence.

## Code touchpoints (implementation checklist — unchanged scope)

- [ ] `autonomous_agent/recipe_harness.py` — add the five run modes behind a
      single `harness_version == "1.1.0"` selector; v1.0.0 behavior stays
      byte-identical when the selector is absent (back-compat for any rerun of
      an archived spec).
- [ ] `autonomous_agent/proposal_layer/primitives.py` — flip the five
      `executable` flags to `True`; write the frozen ladders/margins/floors/
      multiplicity families into the primitive definitions; keep every other
      existing field untouched; bump the declared library version to 1.1.0.
- [ ] `autonomous_agent/proposal_layer/validator.py` — accept harness 1.1.0
      specs; no gate changes.
- [ ] `autonomous_agent/continuous_loop.py` — wire the new stop condition
      `point_in_time_contamination_detected` plus the UNVERIFIABLE-lineage
      stop (both fail-closed), **only after the raw-source lineage inventory
      reports verifiable lineage**.
- [ ] `autonomous_agent/experiments/*` — only if a primitive needs a new
      file in the allowed set; keep the allowed-set delta minimal and declared
      in each spec.
- [ ] Tests (required, in the existing suite style):
      - **Spec-fidelity test:** acceptance criteria embedded in a generated
        spec are byte-identical to the primitive definition (blocks post-hoc
        drift).
      - **Three-valued evaluator tests** per primitive on synthetic fixtures,
        **including an underpowered wide-CI fixture that must return
        INCONCLUSIVE, not pass**, and an under-sized regime cell returning
        INCONCLUSIVE.
      - `test_recipe_harness.py` — one happy-path + one refutation-path test
        per primitive on a synthetic fixture (no real data, no network).
      - **Horizon test:** each rung rebuilds labels, recomputes exit dates,
        drops unmatured rows, and re-verifies the maturity purge.
      - **PIT tri-state test:** UNVERIFIABLE returns FAIL (never PASS);
        CONFIRMED fires the stop fail-closed.
      - **Ladder-enum test:** purge gaps, horizon rungs, and the primary
        reduction rung come from the frozen enums; no runtime computation.
      - **Holm test:** adjustment applied within each declared family;
        unadjusted estimates retained.
      - **Family-membership tests (per-campaign pooling):** tests from
        multiple C4 experiments of the same primitive pool into one family;
        tests from other primitives or from Campaign 1–3 are excluded;
        family definitions read from frozen config, not from results.
      - **Adjustment test:** fixture p-values across ≥2 experiments in one
        family → expected Holm step-down decisions (incl. a case where an
        unadjusted refutation is NOT significant after adjustment and must
        end INCONCLUSIVE, not REFUTED).
      - **Unadjusted-retention test:** the campaign-end multiplicity record
        contains raw delta, raw CI, unadjusted p, and adjusted p for every
        member test.
      - **Provisional-vs-formal classification test (firewall):** before
        the campaign-end multiplicity record exists, no artifact produced by
        the loop (ledger rows, loop events, result records, stdout) contains
        the standalone label `REFUTED` — only `refutation_signal` /
        `formal_refutation: false`; after the campaign-end pass, `REFUTED`
        appears exactly for the Holm-surviving members and `INCONCLUSIVE` for
        unadjusted signals that did not survive. Also test the fail-closed
        path: no multiplicity record at all → every provisional signal ends
        `INCONCLUSIVE`.
      - **Holm-outcome fixture test (final vs provisional):** a family
        mixing survivors and non-survivors yields adjusted decisions matching
        a hand-computed step-down, and a provisional-REFUTED test that fails
        adjustment is stored as INCONCLUSIVE with its unadjusted numbers
        preserved (never erased, never promoted to REFUTED).
      - **Mirrored/related-experiment test:** a `complexity_reduction_check`
        spec records `related_primitive: "model_class_comparison"`; the
        duplicate layers still permit it (distinct primitive ID/signature)
        while continuing to refuse byte-identical signature replays of C1–C3;
        a result record for the complexity primitive cannot emit claim text
        containing tree/leaf/hyperparameter-reduction language (claim-
        prohibition lint on the result schema) **nor** independent-
        confirmation language (second lint: "independent confirm",
        "independently replicated", "corroborated independently"); and any
        independent-evidence tally applies the **count-once rule** — results
        linked via `related_primitive` count as one item, so the mirror can
        never inflate independent-evidence counts.
      - **p-value-method gate test:** until H-10 is resolved, any attempt to
        compute adjusted p-values fails closed (no silent fallback to the
        sign p-value or any other unapproved method).
      - **H-10b freeze-time feasibility test:** for every declared Holm
        family, `n_boot + 1 ≥ 20·m` under the frozen config; an infeasible
        config blocks freeze (fail-closed), and signals from an
        infeasible-granularity experiment can never become formal
        refutations (they end INCONCLUSIVE).
      - **Census-manifest tests (H-11):** all 101 columns present with
        frozen tolerances; a tolerance is never derived from observed
        mismatches (out-of-tolerance → reported mismatch, not retuning);
        unrecoverable columns are UNVERIFIABLE (never PASS, never
        contamination from a value mismatch); structural-check results
        cannot upgrade a column's value verdict; a missing manifest entry
        blocks audit PASS.
      - **Safety-gate preservation suite:** an exhaustive assertion that the
        existing safety surface is unchanged by v1.1.0 — the five existing
        gates' names/thresholds, holdout seal (SEALED/uses 0), duplicate
        layers (5 layers incl. ≥0.90 text and prior-campaign replay), bias
        governor floors (min_falsification_share 0.35, class budgets,
        max_replication_share), outcome-blindness closed input list,
        approval policy, all 15 original stop conditions (the two new stops
        are additions, never replacements), and byte-identical v1.0.0
        behavior when the harness selector is absent.
      - `test_proposal_layer.py` — generation includes the new directions;
        duplicate layers still refuse replayed C1–C3 signatures.
      - `test_stage5_readiness_safety_contract.py` — stops fire fail-closed;
        holdout seal untouched; v1.0.0 back-compat intact.
      - A test asserting **no** change to gate names/thresholds of the five
        existing gates.

## Explicit non-goals (safeguards preserved — item 7 of required changes)

- No changes to bias floors, duplicate layers, class-budget logic, outcome
  blindness, or approval policy.
- No changes to the sealed holdout policy or access controls, leakage
  protections, or existing gate thresholds.
- No new data sources, no network, no LLM.
- No changes to `bias_policy.json`, baseline registry, historical records, or
  Campaign 3's frozen config/ledger/champion/archive.
- No campaign launch, no budget change, no config freeze — those remain human
  actions after this plan (and the resulting code+tests) are reviewed.
- v1.0.0 behavior stays byte-identical (backward compatibility preserved).
- No claim in this plan or its outputs is made that -0.01 (or any ladder
  margin here) is statistically validated; all are PROVISIONAL per H-1.
  The reconstructed baseline is not, and will not be described as, a
  successful reproduction of historical V1.0.1. No profitability claims.
- **Re-confirmed by this revision (2026-10-10, item 5 of the statistical
  review):** the provisional-to-formal firewall, the per-campaign Holm
  family definitions and campaign-end multiplicity record, all five
  existing gates (names and thresholds), the fail-closed stop conditions,
  bias-governor floors and class budgets, duplicate layers, outcome
  blindness, approval policy, and the sealed holdout (SEALED, uses = 0,
  holdout directory absent) are unchanged — H-10b, H-11, and the
  mirror-experiment decision touch none of them.

## Order of operations after plan approval

1. ~~Raw-source lineage inventory~~ **DONE 2026-10-09** (read-only; see
   `POINT_IN_TIME_LINEAGE_INVENTORY_2026_10_09.md`); its required audit-
   semantics revision is incorporated in the prerequisite section above.
2. Remaining statistical decisions with the human: **H-10 only** — run the
   predeclared SIM-1/SIM-2/SIM-3/SIM-5 protocols (test/simulation code, at
   implementation review), report the evidence, then record the method
   choice — or leave H-10 unresolved, which blocks launch (fail-closed).
   **H-10b** (granularity floor B = 1000 + `B + 1 ≥ 20·m` freeze test),
   **H-11** (full census + frozen tolerances), and the **mirror-experiment
   terms** are RESOLVED in this revision, but their freeze-time checks
   (SIM-4, census-manifest completeness, count-once evidence rule) still
   run before activation. Residual ruling: disposition of disclosed Tier-2
   (parity-UNVERIFIABLE) columns in the audit's three-state outcome.
3. Implement harness v1.1.0 + primitive flags + stops + frozen ladders.
4. Run the full test suite; report results including any failures.
5. On green: freeze `campaign_config` (draft → state/ with SHA pin) — only
   when you explicitly authorize the freeze and the C4 launch.

**Mirror-experiment decision (RESOLVED 2026-10-10) — related reanalysis
only.** The previously flagged overlap (the resolved H-9 rung LR vs LGBM
re-measures paired scores already produced by `model_class_comparison`)
human decision: the analysis is **permitted only as a related reanalysis of
`model_class_comparison`**, under these binding terms:

1. **`related_primitive` linkage preserved.** Every spec and result record
   of `complexity_reduction_check` carries
   `related_primitive: "model_class_comparison"`, and any summary reporting
   the experiment discloses the linkage (duplicate layers may still permit
   the distinct primitive ID/signature; they continue to refuse
   byte-identical signature replays of C1–C3).
2. **Independent-confirmation claims prohibited.** No output, report, or
   summary may claim or imply that the complexity rung *independently
   confirms*, replicates, or corroborates the `model_class_comparison`
   result. Banned phrasing in claim-bearing text: "independent
   confirmation/confirm", "independently replicated", "corroborated
   independently" (enforced by the claim-prohibition lint test above).
3. **Independent-evidence counts cannot be inflated.** Any tally of
   independent confirmations / replications / evidence counts (reports,
   summaries, registry statistics, replication-class accounting) applies a
   **count-once rule**: results linked through `related_primitive` count as
   one piece of evidence, and a `complexity_reduction_check` result may
   never appear in a count that also counts `model_class_comparison`
   evidence as a separate item.
4. Executions still consume budget slots normally (no free
   re-measurement); class budgets, bias governor, and all gates are
   unchanged.

The previously flagged "human call at generation time" is now reduced to:
whether to spend a slot on the related reanalysis, subject to terms 1–4.
