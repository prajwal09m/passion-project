# H-10 Statistical Validation Evidence Report (SIM-1 … SIM-5)

**Status: ALL STAGES FINAL (SIM-1 … SIM-5). Awaiting human review; H-10
proposed resolution in §9. No live-harness change has been made.**
Prepared: 2026-10-10; completed 2026-10-11 (times reported in ET, UTC−4).
Scope: **isolated simulation work only**, per the predeclared protocols in
`autonomous_agent/MAIN AUDITS AND REFLECTIONS/HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`
(plan v3, SHA `094827b0e9a5f1c1b6d0ed13c32b9e22a6ff7c76568624228e8b2cb9f738eb4e`).

## 0. Scope and boundary statement

This work ran **only** synthetic-data simulations in the isolated directory
`stat_validation_h10/`. It did **not**: launch Campaign 4, execute or write
any research proposal, modify the frozen study backend, Campaign 3 records,
champion V2.0.35, duplicate memory, or the pinned configuration
(`autonomous_agent/state/campaign_config.json`, SHA-256
`1e0e30b8…fea5a` verified unchanged before and after), access the sealed
holdout (status SEALED, uses = 0), freeze any configuration, or change the
live research harness. The only reads outside this directory were:

- `study_files/backend/demand_zone_study_v1.py` — **read-only import** for the
  self-test and SIM-5 fixture equivalence (mirrors the documented read-only
  `_load_frozen_study` pattern; no writes, no backend file modified);
- `autonomous_agent/…/CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json` — **read-only
  parse** for SIM-4 feasibility (DRAFT_ONLY input; not modified, not frozen).

**Boundary re-verification at completion (2026-10-11):** pinned config
`campaign_config.json` SHA-256 `1e0e30b8…fea5a` — exact match; plan file SHA
`094827b0…8eb4e` — unchanged; champion `V2.0.35`; holdout policy
`SEALED, uses=0` and `study_files/outputs/study_v1/prospective/` absent;
git working-tree shows no modification outside `stat_validation_h10/`.

## 1. Candidate methods under test (unchanged from plan)

All candidates test H1: δ < 0 where δ = AUC(candidate) − AUC(reference) on
paired OOF rows, with the harness's existing paired moving-block bootstrap
over whole weeks (4-week circular blocks, backend semantics):

- **(a) sign proportion** — `p_a = (#{δ*_b ≥ 0} + 1) / (B + 1)` over the same
  paired replicates that produce the percentile CI;
- **(b) week-level sign-flip / permutation** — flip the two arms' scores
  independently per week (M flips), `p_b = (#{δ_flip ≤ δ̂} + 1) / (M + 1)`;
  null-imposed by construction, relies on week-level exchangeability;
- **(c) normal-z** — `z = δ̂ / SE_boot`, `p_c = Φ(z)`, SE from the same
  paired replicates; no granularity floor, relies on normal-tail accuracy.

Holm step-down at α = 0.05 across each family; H-10b granularity freeze test
`B + 1 ≥ 20·m` (fail-closed) applies to any method with a discrete floor.

## 2. What was built (isolated code)

- `stat_validation_h10/simh10.py` — simulation core, self-contained.
  - Exact fast path: AUC on a week-multiset resample computed as a quadratic
    form in full-week multiplicities plus closed-form corrections for the
    partially-truncated final week (sklearn-compatible 0.5 tie handling).
  - Sign-flip statistic computed exactly via a closed-form linear form over
    week-level flips (identity `δ_flip = s·g / (2·n_pos·n_neg)`), avoiding
    per-flip AUC recomputation while remaining algebraically exact.
  - Vectorized replica of the backend's block-sampling draw scheme, plus a
    literal sequential replica used only for equivalence testing.
- `stat_validation_h10/run_sim.py` — stage runner (`selftest|sim1|sim2|sim3|
  sim4|sim5|all`), deterministic seeds, JSON/NPZ outputs under
  `stat_validation_h10/results/`, per-stage `meta` (UTC timestamp,
  `simh10.py` SHA-256, actual N) so partial/non-plan runs can never be
  mistaken for plan-compliant evidence.

### 2.1 Correctness verification (self-test, all PASS)

Nine independent checks (`results/selftest.json`), the critical ones:

| Check | Tolerance | Result |
|---|---|---|
| Quadratic-form AUC vs `sklearn.roc_auc_score` | 1e-12 | PASS (exact to float64) |
| Fast bootstrap deltas vs brute-force sklearn on **identical draws** | 1e-9 | PASS (max diff 2.2e-16) |
| Sign-flip linear form vs brute-force AUC recomputation | 1e-9 | PASS (max diff 1.5e-16) |
| Sign-flip identity at all-`+1` equals δ̂ | 1e-12 | PASS |
| Holm step-down hand fixture | exact | PASS |
| Frozen backend `block_bootstrap_delta` base δelta | 1e-12 | PASS |
| Frozen backend percentile CI (same seed, sequential replica) | 1e-9 | PASS (exact 0.0) |
| Frozen backend `n_boot_valid` match | exact | PASS |

The fast path was **bug-prone at first draft**: the self-test caught a
cross-arm/same-arm matrix mix-up and two indexing defects before any evidence
was produced; all simulation results in this report were generated only after
these checks passed. This is reported for transparency about the
verification burden of custom fast paths.

## 3. Assumptions (explicit)

1. **DGP**: score model `s_X = θ_X·(2y−1) + u_week + d_i + ε_Xi` with unit
   total variance, so population AUC_X = Φ(√2·θ_X) and true δ is known
   exactly. Labels Bernoulli (constant or regime-varying π_w). Within-week
   correlation via shared market-week factor u_week (level ρ) and shared
   event difficulty d_i.
2. **Paired arms**: both arms score the same events with shared
   difficulty/week factors — mirrors same-event arm comparisons in the
   harness. (Model-class comparisons share rows/labels too; residual
   dependence differs but the paired-delta machinery is identical.)
3. **Bootstrap scheme** = frozen backend semantics exactly (W-SUN weeks,
   4-week circular blocks, in-frame-order rows, truncate at n, percentile
   CI). The fast path uses batched RNG draws instead of one `rng.integers`
   call per block: **same statistical scheme, different RNG batching**
   (documented; sequential replica gives bit-for-bit backend equality).
4. **Null for calibration cells** is δ = 0 exactly (θ_A = θ_B), which is the
   hardest case for super-uniformity of (a)/(c).
5. **Sign-flip validity** assumes week-level exchangeability of the two arms
   under H0 (arm-label symmetry within week). SIM-1 cell (iii) at ρ ∈
   {0, 0.5, 0.9} stresses this.
6. Normal-z (c) assumes the bootstrap SE consistently estimates the sampling
   SE of δ̂ and the standardized statistic is approximately normal in the
   tails Holm demands (α/m ≈ 5.6e-4 at m = 90).

## 4. SIM-4 — freeze-time granularity feasibility (deterministic) — FINAL

Input: C4 draft JSON (DRAFT_ONLY) + H-10b test `B + 1 ≥ 20·m`
(`results/sim4.json`):

| Family | m bound (2 cells × `max_per_direction: 12`) | B_min | Feasible at B=1000? |
|---|---:|---:|---|
| regime_split_analysis | 24 | 479 | yes |
| target_horizon_robustness | 36 | 719 | yes |
| purge_sensitivity_probe | 36 | 719 | yes |
| complexity_reduction_check | 12 | 239 | yes |
| unbound contingency (no direction cap) | 90 | 1,799 | **no** — needs family cap in config or n_boot ≥ 1799 (grid ceiling 2000) |

**Finding:** the draft C4 config does **not** pin `n_boot` at all
(`n_boot` absent from the draft). Under the H-10b provisional minimum
B = 1,000 every capped family is feasible; the freeze must pin
`n_boot ≥ 1000` (and cap or raise B for any family allowed to reach m = 90)
or the freeze test fails closed. SIM-4 is method-independent (any candidate
with a discrete floor inherits it; (c) has no floor but the CI gate and
cross-method comparability still pin B).

## 5. SIM-5 — paired-implementation equivalence + unpaired divergence — FINAL

`results/sim5.json`.

**(a) Bit-for-bit fixture equivalence.** Fixture (W=30 weeks × 15 rows,
π=0.28, ρ=0.5, n_boot=1000, seed=42): the literal sequential replica of the
backend draw loop reproduces the frozen `block_bootstrap_delta` outputs
**exactly** — max |ΔCI| = **0.0**, |Δδ| < 1e-12, `n_boot_valid` equal. The
production fast path computes **identical values on identical draws**
(max |ΔCI| vs sequential = 0.0 at these draws; brute-force equivalence holds
to 1e-9 in the self-test). The manifest metric
`paired_week_block_bootstrap_1000` in the study manifest is produced by
`block_bootstrap_delta` (verified by code inspection), so the plan's
"must match `paired_week_block_bootstrap` bit-for-bit" target is met by the
sequential replica and distributionally (exactly, on shared draws) by the
fast path.

**(b) Unpaired control (N=300 trials, cell-(i) DGP, B=1000).**
Deliberately unpaired resampling (independent week draws per arm):

| | paired | unpaired |
|---|---:|---:|
| Rejection rate at α=0.05 (p_a, δ=0 null) | 0.063 | 0.003 |
| Mean 95% CI width | 0.0264 | 0.0652 |

Fisher exact two-sided p = **3.1e-05** on rejection rates; mean CI width
ratio unpaired/paired = **2.47** — the unpaired control is measurably and
strongly different (variance inflation from breaking the paired replicate
structure), exactly the divergence the plan requires as a guard against
accidentally implementing (a)/(c) unpaired. **SIM-5 PASS.**
(Note: the paired 0.063 at N=300 is within exact-binomial noise of 0.05;
SIM-1 at N=1,000/cell provides the calibrated reading.)

## 6. SIM-1 — null calibration (N=1,000 trials/cell, B=M=1,000) — FINAL

Cells (plan (i)–(v); ρ=0.5 appears in both (i) and (iii) and is run twice as
separately-seeded cells): balanced/symmetric; skewed sizes/rates; ρ ∈
{0, 0.5, 0.9}; regime-like small n (3,752 rows, E[positives]=932); plus the
power side-check at true δ = −0.01 (not a calibration cell). Frames are
W=60 weeks × ~60 rows ≈ 3,600 rows (comparable to the regime cell).
Rejection rates at α ∈ {0.10, 0.05, 0.025, 0.01} with exact Clopper-Pearson
95% intervals, one-sided exact-binomial liberal tests (raw and
Bonferroni-corrected across calibration cells × α × methods), and p-value
histograms (`results/sim1_*.json`/`.npz`, `sim1_summary.json`).

**Rejection rates at α = 0.05** (k/1,000; CP95 in brackets; p_lib =
one-sided exact-binomial “liberal” p vs 0.05):

| Cell (plan) | (a) sign proportion | (b) sign-flip | (c) normal-z |
|---|---|---|---|
| (i) balanced/symmetric | 0.064 [0.050, 0.081] p=0.028 | 0.049 [0.036, 0.064] | 0.061 [0.047, 0.078] p=0.067 |
| (ii) skewed sizes/rates | 0.062 [0.048, 0.079] p=0.051 | 0.043 [0.031, 0.057] | 0.058 [0.044, 0.074] |
| (iii) ρ = 0 | 0.068 [0.053, 0.085] **p=0.007** | 0.050 [0.037, 0.065] | 0.066 [0.051, 0.083] p=0.015 |
| (iii) ρ = 0.5 | 0.071 [0.056, 0.089] **p=0.002** | 0.060 [0.046, 0.077] | 0.071 [0.056, 0.089] **p=0.002** |
| (iii) ρ = 0.9 | 0.064 [0.050, 0.081] p=0.028 | 0.054 [0.041, 0.070] | 0.066 [0.051, 0.083] p=0.015 |
| (iv) regime small n | 0.052 [0.039, 0.068] | 0.043 [0.031, 0.057] | 0.057 [0.043, 0.073] |
| **Mean over 6 calibration cells** | **0.0635** | **0.0498** | **0.0632** |
| (v) power δ = −0.01 (not calibration) | 0.453 | 0.411 | 0.457 |

**Predeclared pass criterion (no cell significantly above nominal,
one-sided exact binomial, Bonferroni-corrected over 6 calibration cells ×
4 α levels × 3 methods = 72 tests, threshold 6.9e-4):**

- **(a) sign proportion: PASSES** the corrected criterion, but 12 of 24
  raw cell×α tests flag liberal (smallest raw p = 0.0023 at ρ=0.5/α=0.05),
  and the cell-mean rejection rate is 6.35% vs nominal 5% — a **consistent
  mild anti-conservative bias (~+1.3pp, ~26% relative)** across
  independently-seeded cells, in the direction that matters for Holm.
- **(b) sign-flip: PASSES** with 1 raw flag of 24 (ρ=0.9/α=0.01, p=0.026)
  and cell-mean 4.98% — **well calibrated**, no consistent bias direction.
- **(c) normal-z: PASSES** the corrected criterion with 8 of 24 raw flags
  (smallest p = 0.0023) and cell-mean 6.32% — **mild anti-conservative
  bias similar to (a)**, as its asymptotic-tail risk predicted.

Reading: at the per-cell granularity the plan predeclared, none of the
three candidates is formally invalidated. However the across-cell pattern
is not noise: six independent calibration cells agree in sign for (a) and
(c) (all means ≥ 6.3%), while (b) centers on nominal. Because Holm’s small
thresholds (α/m) sit exactly in the tail where (a)/(c) are inflated, this
mild liberality is decision-relevant — SIM-2 quantifies the family-level
consequence. Power side-check (v): at true δ = −0.01 and this frame size,
rejection is ~41–46% for all three candidates (no candidate materially
outpowers another at m=1).

## 7. SIM-2 — Holm family-wise error (N=2,000 campaigns/config) — FINAL

Global-null families m ∈ {1, 4, 12, 24, 36, 50, 90} × member correlation
ρ ∈ {0, 0.3, 0.7} (shared weeks/labels) × B=M ∈ {500, 1000, 2000}; frames
W=40 × 20 = 800 rows. Design: each campaign generates a 90-member
correlated pool; config (m) uses the first m members (exchangeable), and
config (B) uses nested prefixes of a single 2,000-replicate draw — each
configuration's FWER estimate is valid; estimates across configurations are
correlated (disclosed). Plus one mixed configuration (11 strong H1s
δ ≈ −0.079 + one true H0 at ρ=0.3, m=12, B=1000).

Execution: 3 ρ × 2,000 campaigns × 90 members = **540,000 member trials**
(+24,000 mixed) ≈ 14 core-hours, run as 8 strided shards with per-campaign
deterministic seeds; a pre-launch smoke proved the sharded+merged output
**bit-identical** to a sequential run (all four arrays exactly equal on a
shared small config). Merged arrays complete: 2,000 × 90 × 3 per ρ, 0 NaN.
Wall clock (21 h) exceeded compute by ~4× due to an overnight OS sleep
suspension and daytime user-application contention (detected via per-process
CPU-time audit, not assumed); checkpoints made this harmless — no result was
ever re-generated under different conditions.

**FWER at α=0.05, attainable cells only** (ranges over m × B within each ρ;
`attainable` = the H-10b floor 1/(B+1) ≤ 0.05/m, meaningful for (a)/(b);
(c) has no floor and rejects even in floor-blocked cells):

| ρ | (a) sign proportion | (b) sign-flip | (c) normal-z |
|---|---|---|---|
| 0.0 | **0.066 – 0.260** | 0.036 – 0.053 | **0.063 – 0.242** |
| 0.3 | **0.072 – 0.271** | 0.034 – 0.057 | **0.068 – 0.229** |
| 0.7 | **0.072 – 0.234** | 0.032 – 0.055 | **0.067 – 0.186** |

**C4-producible family sizes at B=1000** (the decision-relevant cells;
CP95 upper in brackets):

| cell | (a) | (b) | (c) |
|---|---|---|---|
| m=24 | 0.160–0.174 [≤0.191] | 0.041–0.049 [≤0.059] | 0.124–0.150 [≤0.166] |
| m=36 | 0.147–0.167 [≤0.184] | 0.033–0.037 [≤0.046] | 0.144–0.176 [≤0.193] |

- **(b) sign-flip: PASSES.** FWER ≤ 0.057 in every attainable cell of every
  ρ; Clopper-Pearson upper bounds ≤ 0.064 (consistent with nominal 0.05 at
  N=2,000); mildly *conservative* at large m (0.032–0.042) — the direction
  Holm tolerates. Even at m=1: 0.050–0.055. Mixed config: P(true H0
  rejected) = **0.0525** with 98.5% of H1s rejected — calibrated with power
  intact.
- **(a) sign proportion: FAILS decisively.** Liberal at *every* m including
  m=1 (0.066–0.074; CP lower bound 0.056 > 0.05 — significantly above
  nominal), inflating with m to FWER 0.23–0.27. This is the SIM-1 mild
  bias (~+1.3pp per test) compounding through Holm's tail thresholds,
  exactly the decision-relevant failure SIM-1 anticipated.
- **(c) normal-z: FAILS decisively** in the same pattern (m=1: 0.063–0.072;
  m=90: up to 0.242) — the asymptotic-tail anti-conservatism materialized.

Mechanical zeros confirm the H-10b floor behaves fail-closed for (a)/(b):
wherever 1/(B+1) > 0.05/m (e.g., m=90, B≤1000), FWER is exactly 0.000
(no rejection is representable), and the runner flags those cells
`any_rejection_attainable = false`.

## 8. SIM-3 — CI-vs-p disagreement — FINAL

Derived from SIM-1 per-trial records and SIM-2 m=1 configurations:
count of (p ≤ 0.05) XOR (percentile CI upper < 0); predeclared pass ≤ 1%
(`results/sim3.json`).

**SIM-1 cells (rates at α=0.05):**

| Cell | (a) | (b) | (c) |
|---|---|---|---|
| (i) balanced/symmetric | 3.5% | 2.4% | 3.2% |
| (ii) skewed sizes/rates | 2.5% | **1.4%** | 2.1% |
| (iii) ρ = 0 | 3.2% | **1.6%** | 3.0% |
| (iii) ρ = 0.5 | 3.1% | 2.8% | 3.1% |
| (iii) ρ = 0.9 | 2.9% | 2.5% | 3.3% |
| (iv) regime small n | 2.1% | **1.6%** | 2.6% |
| (v) power δ = −0.01 (near-null) | 10.1% | 8.7% | 10.5% |

**SIM-2 m=1 (informational):** 2.0–3.0% across ρ × B; (b) lowest in every
combination (~2.0–2.25%).

**Result: no candidate meets the ≤1% criterion** — including (b), whose
rate is nonetheless the lowest in every cell/config. Reading: the
disagreement is structural — a percentile-bootstrap-CI decision and *any*
sampled p-value decision invert different functionals, and near the null
boundary (cell v) they straddle 0 at different points. It is not a defect
of any one candidate. Per the plan, the adopted method's decision rule
**must be reconciled with the gate before adoption** (§9 item 3).

## 9. Decision-rule application and recommendation — PROPOSED, AWAITING
HUMAN REVIEW

Plan decision rule: adoptable only if SIM-1 (no liberal cell), SIM-2, SIM-3
and SIM-4 all pass; exactly one pass → adopted subject to human
confirmation; more than one → human picks (recorded as the H-10 decision);
none → H-10 stays UNRESOLVED, launch blocked (fail-closed).

| Candidate | SIM-1 | SIM-2 | SIM-3 | SIM-4 | Joint |
|---|---|---|---|---|---|
| (a) sign proportion | formal pass, consistent mild liberality | **FAIL** (FWER ≤ 0.27) | fail (≤1%) | n/a (feasible) | **NOT ADOPTABLE** |
| (b) week-level sign-flip | pass, well calibrated (4.98%) | **PASS** (FWER ≤ 0.057) | fail (≤1%, lowest everywhere) | n/a (feasible) | **only survivor** |
| (c) normal-z | formal pass, mild liberality | **FAIL** (FWER ≤ 0.24) | fail (≤1%) | n/a (floor-free) | **NOT ADOPTABLE** |

SIM-3's ≤1% criterion fails for all three candidates and its prescribed
remedy (reconcile the decision rule with the gate) applies to whichever
method is adopted; it does not single out a different candidate than
SIM-1+SIM-2 do. Applying the rule: exactly one candidate survives the
decisive tests — **(b)**.

**Proposed H-10 resolution (for explicit human confirmation; nothing below
is implemented, frozen, or executed):**

1. **Adopt (b)** — week-level sign-flip p-values with Holm step-down at
   α=0.05 — as Campaign 4's family-wise test, at **B = M = 1,000**
   (satisfies H-10b `B+1 ≥ 20·m` for m ≤ 50; C4's capped families are
   m ≤ 36).
2. **Reject (a) and (c)** as the family-wise statistic: mildly liberal
   marginals (SIM-1) compound through Holm into FWER 0.12–0.27 at
   C4-producible family sizes (SIM-2) — a >2× to 5× inflation of the
   promised 0.05 error rate.
3. **Gate reconciliation (required by SIM-3 before adoption):** the five
   gates and the campaign-end record must decide via the p_b/Holm outcome;
   the percentile CI remains an effect-size summary, disclosed as a
   different functional whose 0-exclusion disagrees with the test at
   ~1.4–8.7% near the null boundary.
4. **Freeze-time requirements (from SIM-4, unchanged):** the C4 config must
   pin `n_boot ≥ 1000`, and any family allowed to reach m=90 must either be
   capped at m ≤ 50 or raise B to ≥ 1,799; otherwise the freeze test fails
   closed.
5. **Fail-closed stance preserved:** until the human records this decision,
   H-10 remains formally UNRESOLVED and Campaign 4 launch remains blocked.
   No live-harness code, frozen artifact, champion record, or configuration
   was modified by this work.

## 10. Limitations (fixed regardless of outcomes)

1. **Synthetic DGP only.** No simulation establishes validity on the real
   data-generating process; it can only falsify candidates under
   predeclared plausible DGPs. Resolution of H-10 by these SIMs is
   "no failure found under the predeclared battery", not proof.
2. **Frame sizes are proxies.** SIM-1 uses ~3,600-row frames (regime-cell
   scale); SIM-2 uses 800-row frames for tractability at N=2,000 × 63
   configs × up to 90 members (~1.4M member trials). The full-study frame
   (~61k rows, more weeks) is not simulated; larger n generally helps
   normal approximations and reduces discretization, but this is an
   argument, not evidence.
3. **RNG batching differs from the backend** in production draws (batched vs
   per-block integers); scheme equality is exact and equivalence is proven
   on shared draws (SIM-5).
4. **Family-wise claims rest on Holm under dependence.** Holm controls FWER
   under arbitrary dependence given super-uniform marginals, so SIM-2's
   correlation sweep demonstrates (not proves) the expected robustness; the
   marginal validity question is SIM-1's.
5. **Granularity floor remains** for (a)/(b): `B + 1 ≥ 20·m` is a
   feasibility condition, not power. SIM-2 documents zero attainable
   rejections for infeasible (m, B) combos — the empirical counterpart of
   H-10b; it does not validate any method's small-p tail.
6. **Power was probed only lightly** (one δ = −0.01 side-check at m=1; one
   mixed H1/H0 configuration). No statement about the −0.01 margin's
   detectability in the real campaign is made or implied (H-1 stands).
7. **The fast path is custom code.** Despite the self-test battery, residual
   bug risk is nonzero; the frozen backend remains the only production
   semantics authority.

## 11. Provenance

- Seeds: SIM-1 cells 1100–1106; SIM-2 ρ 2200–2202, mixed 2999; SIM-5 fixture
  21/42, unpaired control 5500; self-test 7/11/13/21. All recorded per-output
  file in `meta` with `simh10.py` SHA-256 and UTC timestamps.
- Environment: Python 3.13.1, numpy 2.3.3, scipy 1.16.2, sklearn 1.9.0.
- Reproduce: `py -3 -X utf8 stat_validation_h10/run_sim.py all` from the
  repository root (defaults are the plan-compliant N values). SIM-2 as run:
  `sh stat_validation_h10/run_sharded_sim2.sh` (8 strided workers + merge;
  smoke-proven bit-identical to the sequential path, which also remains
  runnable alone via `run_sim.py sim2`).
