# D2 AI INDEPENDENT STATISTICAL REVIEW — Campaign 4 (H-10 / D2)

**Date:** 2026-10-13. **Reviewer:** the project's assigned AI reviewer
(Buffy/Codebuff), acting as independent adversarial statistical reviewer at
the owner's explicit direction ("Instead of another expert reviewer, YOU are
one… I AM NOT PROVIDING A HUMAN REVIEWER").

**Independence disclosure (material).** This review was performed by the same
AI agent that implemented parts of the system under review (the proposal-layer
compiler, the v1.1.0 primitive activation, tests around the multiplicity
machinery). Relative to a truly external human statistician this is a
weakened form of independence, and the review is therefore adversarial in
method but not conflict-free in fact. This disclosure is unconditional and
must be carried into any signed record that relies on this review.

**Prior work audited, not trusted.** `stat_validation_h10/D2_AI_PRE_REVIEW.md`
was treated as a claim source to audit. Its material numerical claims were
re-derived independently with fresh slow-path code (§2); its central probe
result was re-run at 3.3× sample size and **shrank** (§8); one of its tools'
interpretations is corrected here (§6). Where this review repeats a
pre-review number, it is because this review re-derived it, not because the
pre-review said so.

**Boundaries observed.** Read-only against all evidence. No campaign
execution, no freeze, no gate/approval/pin modification, no write to
`D2_EXTERNAL_REVIEW_ASSESSMENT.md`, no population of
`APPROVED_P_VALUE_METHODS`, no holdout access. All new work is confined to
`stat_validation_h10/scratch_independent_review_2026_10_13/`. Evidence hashes
were captured before and after each phase and are unchanged (§2).

---

## 1. Executive verdict

**APPROVE WITH CONDITIONS** (statistical verdict).

The proposed procedure — one-sided week-level sign-flip Monte-Carlo
p-values `p = (#{δ_flip ≤ δ̂} + 1)/(M + 1)` at `M = 1000`, Holm step-down at
α = 0.05 over four frozen predeclared families, formal `REFUTED` issued only
by the campaign-end multiplicity record — is **mathematically exact against
its stated null**, implemented correctly in every component that exists,
empirically calibrated at 5.0% under the exchangeable null in my own
independent simulation (50/1000), and only mildly and non-significantly
elevated (5.5%, 6.0%; exact-binomial p = 0.25, 0.09) under two
constructive violations of exchangeability at *exactly equal* population
AUC. Its FWER behavior on the real campaign's family sizes was reproduced
from primary data with independent code. No credible alternative in the
candidate set is superior: the two alternatives that were simulated,
(a) and (c), fail FWER decisively (reproduced: up to 0.2705 / 0.2420 vs
0.0565 for (b)).

The residual risk is a *disclosed, structurally unverifiable assumption* —
week-level arm-label exchangeability for deterministic fitted models on
shared purged folds — plus a weak-null transfer that is exact only under that
assumption. My probes bound the degradation for two stylized asymmetry
classes at the 0.05 level; the behavior of the far tail (p ≈ 0.002) under
asymmetry remains unmeasured [Unknown]. This is acceptable for approval
*only* as an owner-accepted, explicitly documented limitation, because the
formal claims at stake are degradation findings about already-promoted
candidates, protected by a firewall that never lets a provisional signal
become a claim, and because no amount of additional evidence can convert the
exchangeability assumption into a verified fact.

The verdict is **conditions-gated**: the six conditions in §12 must be
satisfied before D2 may be recorded as closed. Independently, Campaign 4
launch and configuration freeze remain **blocked** on operational grounds
(§9) regardless of this verdict.

## 2. Scope, files inspected, and independent checks actually performed

**Integrity, three snapshots [Verified fact].** All 11 manifest-hashed
evidence files verified against `review_submission/BUNDLE_MANIFEST.txt`
(before the audit computations, after the fast computations, and after all
three simulation probes): unchanged each time. Frozen C3 config pin
`1e0e30b8…`, C4 draft pin `307e98ab…`, `launch_gates.json`,
`APPROVED_P_VALUE_METHODS = []`, absent `prospective/`, and absent
`D2_EXTERNAL_REVIEW_ASSESSMENT.md` all re-verified after all work.
The bundle zip digest `ee345dab3a587b51…47b74bb03` was verified in full
earlier this session against the recorded digest; this review re-verified the
*contents* it protects (all 11 hashes) three times.

**Commands actually run (all captured with exit status):**
```
py -3 -X utf8 stat_validation_h10/scratch_independent_review_2026_10_13/independent_checks.py fast      # EXIT=0
py -3 -X utf8 stat_validation_h10/scratch_independent_review_2026_10_13/independent_checks.py sym       # EXIT=0
py -3 -X utf8 stat_validation_h10/scratch_independent_review_2026_10_13/independent_checks.py affine16  # EXIT=0
py -3 -X utf8 stat_validation_h10/scratch_independent_review_2026_10_13/independent_checks.py hetero    # EXIT=0
```
plus pandas metadata reads of `study_files/outputs/study_v1/development/event_table.csv`
(date/label columns only — no holdout, no arm scores, no diagnostic statistic)
and direct reads of `stat_validation_h10/simh10.py`, `run_sim.py`,
`autonomous_agent/proposal_layer/multiplicity.py`, `generator.py`,
`compiler.py`, `recipe_harness.py`, `spec_recipes.py`,
`autonomous_agent/three_valued.py`, `experiment_adapter.py:970-980`,
`autonomous_agent/state/campaign_config.json`, the C4 draft, the decision
sheet, the decision record, and the review packet.

**Not run:** the full SIM-1…SIM-5 battery (~14 core-hours) — instead the
primary per-trial arrays were re-analyzed directly; the shard-bit-identity
replay; any real-data arm-symmetry statistic (deliberately — see §5).

## 3. Exact estimand and null hypotheses

**Estimand [Verified fact + protocol].** δ = pooled OOF AUC(candidate) −
AUC(reference) over walk-forward validation folds 2023–2025 on the frozen
event frame; the production decision rule gates on the 6-decimal rounded
values (`recipe_harness.py:421-424`). Refining the submitted "~61k-row
frame" phrasing with the actual table: the full event table is 61,045 rows
spanning 2021-08-03 → 2025-12-31 (231 ISO weeks, π = 0.176), but the **OOF
evaluation frame is the 2023+ subset: 41,221 rows, 157 ISO weeks, π = 0.165**
(`folds: [2023, 2024, 2025]` in the frozen config). Week sizes 138–400 rows;
every week contains both classes (minimum 4 positives/week), so every week
contributes well-defined AUC structure. Precision note for the record: the
reviewable frame is ~41k rows / 157 weeks, not ~61k / 231.

**Null hypotheses.** Sharp null (the one the test is exact against): within
every week, the joint distribution of the two arms' score vectors over that
week's events is invariant to swapping arm labels — the product group of 2^W
week-swaps acts measure-preservingly. Weak null (the one the claim needs):
H1: δ < 0, tested one-sided with lower-tail p; formal REFUTED means
"statistically significant evidence that the candidate underperforms the
reference", family-wise at α = 0.05.

**Units.** Event rows are the sampling units; weeks are the exchangeable/resampling
unit (both the 4-week circular-block bootstrap for CIs and the whole-week
flips for the test); family members are the multiplicity units and share
events, labels, and training data by construction.

## 4. Mathematical validity analysis

**Result 1 (exactness under the sharp null) [Mathematical].** Under the
product-group invariance null, for the observed statistic T and M group
elements drawn uniformly, p_MC = (1 + #{b : T(s_b) ≤ T_obs})/(M+1) is
super-uniform. The ≤ tie handling makes ties conservative.

**Result 2 (fixed-seed exactness) [Mathematical — resolves an open question
the pre-review left implicit].** The exactness does **not** require fresh
randomization per experiment. For any *fixed* set of M flip vectors and the
identity, under the invariance null the vector
(T_obs, T(s₁), …, T(s_M)) has the same joint distribution as its shift by
any group element, hence all M+1 coordinates are exchangeable, hence the
rank of T_obs is uniform on {0…M}, hence p_MC is exactly super-uniform
conditionally on the flip set (ties only make it conservative). A production
port with a pinned flip seed (as the harness pins `seeds[0]=42` for the
bootstrap) is therefore still exact under the null. This removes the
"deterministic seeds compromise validity" concern.

**Result 3 (linearity) [Verified fact].** δ_flip(s) = s·g/(2·n_pos·n_neg)
over week-level contributions is algebraically exact for all 2^W sign
vectors — re-confirmed on this machine (self-test rerun: max |diff| vs
brute-force AUC recomputation 1.527e-16; identity at all-+1 exact).
n_pos/n_neg are invariant to within-week arm swaps.

**Result 4 (direction) [Verified fact].** Lower-tail counting matches H1:
δ < 0; the +1 correction matches the protocol text exactly (`simh10.py:452`).

**Result 5 (Holm validity under dependence) [Mathematical].** Holm controls
FWER under arbitrary dependence given super-uniform marginals. Family
members share events, labels, training rows, and market weeks — maximally
dependent — which Holm tolerates. The marginal question is therefore the
only inferential bottleneck (§5).

## 5. Exchangeability and weak-null analysis

**What exchangeability requires here.** The arms are deterministic fitted
models evaluated on identical events with identical purged folds. The sharp
null is not a design feature (there is no randomization to points of
treatment); it is a *distributional symmetry assumption* about how the two
models' score vectors relate within weeks. Concretely it requires that, in
the campaign-relevant data-generating law, swapping the two models' scores
within any subset of weeks leaves the joint law invariant — which fails to
the extent that the arms differ in score *shape* (scale, skew,
heteroskedasticity) in ways not reducible to a monotone transformation of a
shared latent.

**Benign vs dangerous asymmetries [Mathematical + Empirical].** Purely
monotone transformations of a shared score (identical ranking power) make
δ̂ ≡ 0 identically and the test is *conservative* — a benign class.
Dangerous asymmetries are those that can move δ̂ spuriously relative to the
flip distribution. Shared-training dependence (overlapping OOF fits) and
calibration differences plausibly create shape asymmetries of exactly this
kind; none of it is simulated in the submitted battery [Assumption], and I
did not compute any real-data symmetry statistic — the project's own
governance requires such a diagnostic to be preregistered before inspection,
and an unpreregistered version from this review would be unreviewable.

**My independent probes [Empirical; own DGP, own AUC (validated against
sklearn to 1e-12), own flip loop; frame 24 weeks × 15 rows = 360, π = 0.18
matched to the real ~0.165; M = 1000; N = 1000 trials each; seeds
20261014/15/16]:**

| Scenario | Exchangeability | Population AUC | Rejections @0.05 | Rate | CP95 | one-sided exact p vs 0.05 |
|---|---|---|---|---|---|---|
| sym (control) | holds by construction | equal | 50/1000 | 0.050 | [0.037, 0.065] | 0.52 |
| affine ×1.6 | broken (scale) | equal exactly (affine invariance) | 55/1000 | 0.055 | [0.042, 0.071] | 0.25 |
| hetero σ⁺_B=1.5 | broken (heteroskedastic positives) | equal by numeric calibration (θ_B = 0.9668 vs θ_A = 0.8) | 60/1000 | 0.060 | [0.046, 0.077] | 0.087 |

Mean δ̂ centered (−0.0020 / −0.0013 / −0.0018); p-distributions approximately
uniform (medians 0.489 / 0.498 / 0.488). **Reading:** under the null the test
is exactly calibrated; under two independently constructed, equal-AUC
symmetry violations, size elevation is mild (≤ +1.0 pp point estimate) and
not individually significant; the consistent sign across both (and the
pre-review's third probe) suggests a small real effect of asymmetry on size
that this design can only bound, not pin down. The pre-review's 300-trial
"0.067" for the scale case shrank to 0.055 at N=1000 — its own "underpowered"
caveat was correct, and no significant inflation was found.

**Weak-null transfer: the precise conditions [Mathematical].** The REFUTED
claim is about δ < 0. Exactness transfers to that claim only under one of:
(i) the sharp null holds (exchangeability); or (ii) an approximate-symmetry
argument with quantified bound — which my probes supply empirically at the
α = 0.05 level for two asymmetry shapes (≤ ~1 pp), **not** at the Holm
decision level (α/m ≈ 0.001–0.002) [Unknown]; or (iii) a studentized
construction with asymptotic weak-null validity (§8, alternative). The
protocol's honest position is (i) with (ii) as bounded empirical support.
This review finds that position defensible for *degradation* claims about
promotion-eligible candidates, and only with the limitation written into the
signed record (Condition 2).

## 6. Multiplicity and Monte Carlo resolution

**Multiplicity machinery [Verified fact].** Family definitions
(`multiplicity.py:50-57`), ladder agreement (regime 2 / horizon 3 / purge 3 /
complexity 1, verified live against `three_valued.ladder_for`), frozen caps
24/36/36/12, exclusions of all non-family primitives from any Holm family
(scoping formal claims accordingly — conservative), C-2 Option A (unavailable
→ p = 1.0, counted, never REFUTED), the empty `APPROVED_P_VALUE_METHODS`
gate (exercised: raises `PValueMethodUnresolved`), the firewall, and the
append-only once-per-campaign record all re-verified this session. Holm
itself: my slow textbook loop agrees with production and with `simh10` on
every case exercised (including the exact-boundary `p = α/m` rejection).

**Audit of the pre-review's numbers [Verified fact].** Independent slow-path
re-derivations from the primary arrays: SIM-1 (b) six-cell mean = 0.0498,
cell (i) 0.049, cell (iii, ρ=0.5) 0.060 — match; SIM-2 ρ=0.3/m=4/B=1000 (b)
rejections = **113/2000** (exact-binomial p = 0.1014) — matches the claimed
worst cell; SIM-2 ρ=0/m=24/B=1000 (b) = 97/2000 = 0.0485 — inside the
claimed 0.041–0.049 band; SIM-3 cell (i) (b) disagreement = 24/1000 —
matches. The pre-review's two "failed" tolerance checks are confirmed as
display-rounding artifacts (113/2000 = 0.0565 ≤ 0.057; 131/2000 = 0.0655 ≤
0.066). One of my own first-pass MC tables contained an off-by-one in the
rejection-count boundary (X ≤ t(M+1) − 1); it was caught, fixed, and
re-run — the corrected table is below. This is disclosed because it
demonstrates the audit loop working, not because any conclusion depended on
the wrong version.

**Monte Carlo resolution at Holm's first thresholds [Mathematical, exact
binomial, corrected]:**

| m | first threshold α/m | max count that rejects | P(reject \| true p = α/m) | P(reject \| true p = α/2m) | P(reject \| true p = 2α/m) |
|---|---|---|---|---|---|
| 1 | 0.05 | 49 | 0.480 | ≈1 | ~0 |
| 12 | 0.00417 | 3 | 0.401 | 0.842 | 0.033 |
| 24 | 0.00208 | 1 | 0.384 | 0.720 | 0.080 |
| 36 | 0.00139 | 0 | 0.249 | 0.499 | 0.062 |
| 50 | 0.001 | 0 | 0.368 | 0.606 | 0.135 |

**Reading.** At M = 1000 the test is *conservative-leaning and coarse* where
families are largest: for m = 36–50 a member must produce the minimum
representable p (1/1001, zero flips ≤ δ̂) to survive the first step.
Borderline members (true p near the threshold) are decided with only 25–48%
probability, always biased toward non-rejection. Statistical **validity is
unaffected** (discreteness is conservative; Result 2); **power and decision
stability** are the costs, and they fall exactly where C4's families are
largest. The H-10b floor 1/(B+1) ≤ α/m → m ≤ 50 is confirmed exact at its
boundary (1/1001 = 0.000999 ≤ 0.001; fails at m = 51). The campaign-end
record already carries per-member adjusted p-values, so borderline decisions
will be visible; the limitations text should say so (Condition 7).

**Freeze-test gap [Verified fact, blocks freeze].** D4 defines feasibility
on **M**, but `feasibility()` and the campaign-end record key on `n_boot`;
M appears nowhere in production. A reduced M would silently make formal
refutations unattainable while the freeze test passes (conservative, but
wrongly labeled feasible). Condition 3 fixes this.

## 7. Bootstrap and confidence-interval assessment

The CI is the frozen backend's paired moving-block bootstrap (whole weeks,
4-week circular blocks, truncate at n, percentile 95%, seed = `seeds[0]`),
reproduced bit-for-bit by the submitted replica and re-verified exact on this
machine's self-test rerun [Verified fact]. The resampling unit (4-week
blocks) and the test unit (whole weeks) differ by design — the structural
cause of the SIM-3 disagreement (reproduced: (b) 1.4–8.7% XOR-rate near the
null; all candidates >1% everywhere) — and the reconciliation (formal
decisions by the adjusted p alone; CI as provisional marker + effect-size
functional; disagreement recorded per member in `ci_disagrees_with_p`) is
coherent: it never lets the two functionals silently contradict a claim.

`ci_lower_min = −0.01` is a provisional non-inferiority floor on the ROBUST
(promotion) side, carried with explicit "not statistically validated (H-1)"
provenance into every v1.1.0 primitive [Verified fact]. Its leverage is
documented in-repo (3 of 8 Campaign-2 acceptances depend on it). Point-only
passes are impossible (`three_valued.Margin` raises). Two residual
observations: (i) the ROBUST gate (δ ≥ 0 and CI lower ≥ −0.01) and the
REFUTED test (δ < 0 significant) are deliberately different claims about the
same estimand — the campaign-end text should say so; (ii) CI endpoints carry
unquantified MC error from a single fixed-seed B = 1000 run; a boundary-proximity
flag would be a cheap improvement (nonblocking).

## 8. Simulation evidence, power, sensitivity, alternatives, limitations

**Evidence audit [Verified fact].** The battery is a genuine falsification
exercise: it rejects (a) and (c) decisively (reproduced FWER ≤ 0.2705 /
0.2420 vs (b) ≤ 0.0565 over attainable cells; floor-blocked cells exactly
0.000), retains its own failure (SIM-3), and its DGP is documented (unit-variance
Gaussian scores, AUC = Φ(√2θ), shared week/difficulty factors, backend-exact
bootstrap). Seeds, environment, and per-output metadata are recorded and the
environment matches exactly (py 3.13.1 / numpy 2.3.3 / scipy 1.16.2 /
sklearn 1.9.0).

**Limits of transport [Empirical limitation].** Simulated frames are 800–3,600
rows / 40–60 weeks at π = 0.28–0.30; the real OOF frame is 41,221 rows / 157
weeks at π = 0.165. Larger frames and more weeks help granularity and
approximations, but that is an argument, not evidence. Power evidence is
light: 41–46% at δ = −0.01 (m = 1, small frames) and 98.5% at δ ≈ −0.078 in
the mixed config (both reproduced from primary arrays). Non-significance
must not be read as evidence of no effect.

**Alternatives [Assessment].** (a)/(c): rejected by reproduced evidence.
Block-level (4-week) flips: would tolerate within-block clustering
asymmetry; costs units (≈39 blocks over 157 weeks → less power, coarser
structure); untested here. Weekly sign test / HAC-t on week contributions:
different estimand (median/dominance, mean contributions), different
assumptions (independence or asymptotic normality of ~157 week units — the
last is actually plausible and worth remembering as a fallback).
**Studentized permutation** (Chung & Romano-type constructions): asymptotically
valid for weak nulls without symmetry — the theoretically correct upgrade
for the §5 gap; it introduces per-resample variance estimation and would
require its own predeclared SIM battery and a protocol amendment. This review
does **not** recommend replacing (b) now; it recommends recording studentized
permutation as the named upgrade path if the weak-null question is ever
re-opened.

## 9. Production and governance blockers (separate from the statistical verdict)

1. **The method does not exist in production [Verified fact].** No sign-flip
   p-value code anywhere in `autonomous_agent/` (non-test); no production
   caller of `campaign_end_record`; no producer of `unadjusted_p`; the
   fail-closed pipeline is empty by design. Decision-sheet gate 4 (port +
   equivalence tests) is outstanding and legitimately cannot start before D2.
2. **The configuration is not frozen [Verified fact].** C4 remains the
   2026-10-09 draft: no `n_boot`, no M, no multiplicity block, 15 of the
   R-2-ratified 16 stops, unfrozen census tolerances, placeholder provenance
   fields. Launch readiness correctly reports NOT READY
   (20 PASS / 1 BLOCKED `c4.not_frozen` / human gates outstanding).
3. **The governing protocol's D2 route names an external human reviewer, and
   the owner has stated none will be provided [Verified fact + governance].**
   The packet's own text requires "a written assessment from a reviewer
   independent of this project's authorship … not the owner's authorization,
   not this agent, not the project author". An AI review by the
   implementing agent does not satisfy that wording, and this review will not
   pretend otherwise. Closing D2 on the strength of this review requires an
   **explicit owner-signed protocol amendment**: a recorded decision to
   substitute an adversarial internal AI review for the external assessment,
   with the independence weakening and the conflict-of-interest disclosure
   (top of this file) written into the signed record. Absent that amendment,
   D2 remains DEFERRED and this report is advisory evidence only.
4. **Signatures and records [Verified fact].** The H-10 decision record is
   unsigned; `launch_gates.json` records implementation_authorized /
   implementation_complete (for the authorized subset — see pre-review C3
   note) / launch_authorized; review_received, d2_decided, c3_ratified, and
   freeze_approved remain honestly outstanding. Nothing has launched; no
   campaign experiment was executed by this review.

## 10. Prioritized required corrections

**Blocking for D2 closure (statistical use of this review):**
1. Owner-signed protocol amendment substituting this (or a future) AI review
   for the external assessment, with the COI disclosure verbatim in the
   signed record (§9.3).
2. The signed record must state: FWER control is exact only under
   week-level arm-label exchangeability; under two tested equal-AUC
   asymmetry classes marginal size was 0.055/0.060 (CP95 upper 0.071/0.077);
   tail behavior at Holm thresholds under asymmetry is unmeasured; the owner
   accepts this residual risk for degradation-only formal claims.
3. C-3 (SIM-3 remedial reconciliation) explicitly ratified alongside D2.

**Blocking for freeze (not for the statistical verdict):**
4. Freeze package: pin `n_boot = 1000` **and `M = 1000`**; add M to the
   multiplicity record and the feasibility check (fix the §6 gap); declare
   all 16 stops; apply the multiplicity block; finalize provenance
   placeholders; freeze census tolerances and execute the census; fresh
   config pin + fingerprint.

**Blocking for launch (not for the statistical verdict):**
5. Production port of (b) with equivalence tests against `simh10.py`
   references; campaign-end record wiring end-to-end; gate-7 readiness exit
   0; explicit launch authorization (already recorded, contingent).

**Nonblocking, still required at the next documentation revision:**
6. C-2 wording: "strictens, never loosens, other members' thresholds".
7. Frame precision: "~41k OOF evaluation rows / 157 weeks / π = 0.165"
   alongside or replacing "~61k".
8. Borderline-decision visibility: disclose the §6 MC-resolution table in
   the campaign-end record's reader text; optionally flag ROBUST-gate
   boundary proximity to bootstrap MC error.
9. Optional preregistered (never retro-fitted) follow-ups: a real-data
   week-symmetry *diagnostic* (disclosure only) and/or an N ≥ 2000
   synthetic tail-focused probe at the exact C4 family sizes if empirical
   tail bounds are wanted before launch.

## 11. Explicit limitations and unresolved questions

- Real-data week-level exchangeability: **Assumption — unestablished and
  unestablishable by any local artifact**; my probes bound two stylized
  violations at α = 0.05 only.
- Far-tail behavior (p ≈ α/m) of the sign-flip p under asymmetry:
  **Unknown** — no design here has the ~10⁴-trial power to measure it.
- Transport of synthetic calibration to the 41k-row / 157-week frame:
  **Unverified** (favorable scaling argued, not demonstrated).
- Shared-training dependence specifically (overlapping OOF fits as an
  asymmetry source): **not simulated and not probed by me**.
- Shard-level bit-identity of the original SIM-2 run and full-battery
  re-execution: **not re-run** (~14 core-hours; primary arrays re-analyzed
  instead).
- The reviewer is the implementing agent: this review is adversarial but not
  independent in the personnel sense; a genuine external statistician could
  still overturn any conclusion here, and Condition 1 exists precisely to
  record that the owner accepted that risk.

## 12. Final recommendation and conditions

**APPROVE WITH CONDITIONS.** Method (b) with Holm step-down at α = 0.05,
M = 1000, over the four frozen families is statistically defensible for
Campaign 4's intended formal claims — one-sided degradation findings about
promotion-eligible candidates, issued only at campaign end, behind a
firewall, under fail-closed INCONCLUSIVE defaults — **conditional on** the
nine corrections in §10, of which items 1–3 gate the *recording of D2*,
items 4–5 gate freeze/launch, and items 6–9 are documentation/hardening.

**Why not the strongest competing verdict (DEFER — EVIDENCE REQUIRED).**
Deferral would rest on the unverifiability of exchangeability. But that
assumption is unverifiable *in principle*, not for lack of budget: no future
simulation, diagnostic, or review can convert it into a verified fact, so
"require more evidence" is infinite deferral wearing a technical costume.
The decision sheet itself anticipated this (its closure routes are
decision-acts, not proofs). Empirically, the degradation the assumption's
failure can cause is bounded and small for the shapes tested here (≤ +1 pp
marginal size, non-significant at N = 1000); the one *demonstrated* large
inflation precedent in this project — methods (a) and (c) — came from
method-intrinsic liberality present under full exchangeability, a failure
mode method (b) does not have (50/1000 exactly). Operationally, the residual
risk is confined to the false-refutation rate of candidates that already
passed promotion gates, never to promotions themselves, because the
firewall routes every unadjudicated signal to INCONCLUSIVE. Deferral remains
available to the owner as a *decision* at the D2-recording step; it is not
the statistically compelled answer.

**Why not APPROVE (unconditional).** Conditions 1–5 are not optional
preferences: without the amendment the approval would misrepresent the
protocol's review requirement; without the exchangeability disclosure the
signed record would overstate what was established; without the M pinning
and port, the approved method is not the one executable; without C-3 the
SIM-3 failure would be adopted implicitly rather than ratified.

**Final position.** With Conditions 1–3 signed, 4–5 implemented and tested,
and 6–9 recorded, this review supports closing D2 in favor of method (b)
and proceeding to freeze review. Until then: D2 is not closed, the config is
not frozen, and Campaign 4 must not launch. This report approves nothing by
its own existence; the approvals remain the owner's recorded acts.
