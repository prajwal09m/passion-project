# D2 AI PRE-REVIEW — Independent Statistical Pre-Review of Campaign 4 (H-10 / D2)

**Date:** 2026-10-13. **Reviewer role:** adversarial AI statistical pre-reviewer
(assigned by the project owner: "Instead of another expert reviewer, YOU are
one."). **Verdict class:** this is an *AI pre-review* prepared to sharpen and
short-circuit the external review; it is **not** the required independent
written assessment of a human reviewer, is **not** an approval, and cannot by
itself close D2 or ratify C-3.

**Operational boundaries observed.** Review only. No Campaign 4 launch, no
experiment execution, no configuration freeze or modification, no change to
pinned artifacts, H-10 decision records, launch gates, or approval fields, no
write to `stat_validation_h10/D2_EXTERNAL_REVIEW_ASSESSMENT.md`, no population
of `APPROVED_P_VALUE_METHODS`, no weakening of any fail-closed control, no
holdout access (`prospective/` absent; sealed policy verified). Scratch work is
confined to `stat_validation_h10/scratch_prereview_2026_10_13/` and is clearly
identified as such.

**Evidence-handling incident (disclosed).** While reproducing the submitted
self-test (`run_sim.py selftest`, exit 0, all 11 checks PASS), the runner
re-saved `stat_validation_h10/results/selftest.json`, which is a
manifest-pinned evidence file. The overwrite was detected by hash comparison
(new hash `1f56f8ed…`), and the file was **restored byte-identically** from the
signed bundle (`H10_D2_REVIEW_SUBMISSION.zip`), returning to the manifest
digest `fb7fce987be7…6da` (re-verified after restore). The rerun output is
preserved at `scratch_prereview_2026_10_13/selftest_rerun.log`. Consequence:
none to the evidence record; operational lesson: simulation stages must not be
re-run in place over pinned outputs.

**Evidence-class markers used below:** **[V]** independently verified by this
review (code, hash, or recomputation); **[S]** supported by submitted
documentation but not independently reproduced here; **[A]** assumption that
remains unverified and cannot be verified from local artifacts; **[D]**
demonstrated defect; **[U]** not resolvable from available evidence.

---

## 1. Executive verdict

**DEFENSIBLE ONLY AFTER SPECIFIED CORRECTIONS**

Reasoning in one paragraph. The proposed family-wise method — one-sided
week-level sign-flip p-values (`p_b = (#{δ_flip ≤ δ̂} + 1)/(M + 1)`, `M = 1000`)
combined with Holm step-down at α = 0.05 over frozen predeclared families, with
formal REFUTED status arising only from the campaign-end multiplicity record —
is mathematically correct **against its stated sharp null** (week-level
arm-label exchangeability), is implemented correctly in every piece of code
that exists today, and its synthetic calibration evidence is accurate: this
review independently reproduced SIM-1, SIM-2, SIM-3, and SIM-4 numbers from the
raw per-trial arrays using separately written code, with zero discrepancies
beyond display rounding, and reproduced the self-test battery on this machine.
However: (a) the exchangeability assumption and the sharp-null-to-weak-null
transfer are **[A] unverifiable** on the real data by construction, and this
review — like any local artifact — cannot establish them; the governing
protocol correctly requires the independent external assessment before D2 can
close. (b) The method itself is **not yet present in production** (no sign-flip
p-value computation, no caller of the campaign-end record) — correct
fail-closed ordering, but it must be implemented and tested after D2/C-3 per
the decision sheet's gate 4. (c) The freeze-time configuration package
(`n_boot`/M pins, multiplicity block, the 16th stop, census tolerances,
placeholders) is prepared but not applied; the sole machine launch blocker
(`c4.not_frozen`) is correct. (d) Several conditional corrections (§9) —
including one documentation imprecision in the C-2 rule's wording and one
freeze-test gap around M — must be fixed regardless of the external reviewer's
answer. None of the findings below indicate that the submitted evidence is
wrong; the corrections close the gap between "method validated in simulation"
and "method defensibly adopted and executable in production".

## 2. Evidence inspected

**Bundle identity [V].** `stat_validation_h10/H10_D2_REVIEW_SUBMISSION.zip`:
SHA-256 `ee345dab3a587b5183e3d80b7a45f2283047f6d1d972c6eff5fc3bb47b74bb03` —
matches the authoritative recorded digest in full (not just the prefix);
64,349 bytes; 13 entries. All 11 hashed files in
`review_submission/BUNDLE_MANIFEST.txt` verify **twice**: against the zip
content and against the repository copies. The two unhashed manifest entries
(outgoing request text, the manifest itself) are not evidence.

**Pinned artifacts claimed in packet §10, all re-verified against the current
repository [V]:** plan `HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`
`094827b0…8eb4e`; decision sheet `5a62c9d0…57159`; unsigned decision record
`b9db3233…9f0a42`; frozen Campaign-3 config `1e0e30b8…36fea5a` (sidecar
`campaign_config.sha256` consistent); C4 draft `307e98ab…168cdcd`; six-gate
adapter `experiment_adapter.py` `d80723d3…c61aa`; evidence report `85c6ac4f…`;
`simh10.py` `4b7ebd5f…`; `run_sim.py` `96aa497c…`.

**Documents read in full:** the external review packet (§1–§11), the
simulation evidence report (§0–§11), the decision sheet draft (D1–D5, C-1–C-4,
gate list), the unsigned decision record, the C4 draft config, the frozen
Campaign-3 config's relevant blocks, `CAMPAIGN_4_CONFIG_RECONCILIATION_2026_10_12.md`,
`OWNER_AUTHORIZATION_TO_PROCEED_2026_10_12.md`, the gate-3 authorization
record, and the Oct-4 autonomous-campaign audit (for the `ci_lower_min`
leniency analysis).

**Code read and exercised:** `autonomous_agent/proposal_layer/multiplicity.py`
(Holm, feasibility, C-2, firewall, audit-stop signals), `generator.py`
(param grid), `compiler.py`/`spec_recipes.py`/`recipe_harness.py`
(evaluation semantics), `proposal_layer/primitives.py` (family primitives,
margins), `autonomous_agent/three_valued.py` (Margin), the six-gate literal in
`experiment_adapter.py:975`, and the submitted simulation code
(`stat_validation_h10/simh10.py`, `run_sim.py`).

**Independent recomputation** (own code, own Holm, own AUC, own flip logic;
full outputs in `scratch_prereview_2026_10_13/recompute_results.json`,
runtime 353 s, exit 0): §3.B–§3.I below, plus 20,000 randomized
production-vs-textbook-vs-simulated Holm cross-checks, plus an independent
type-I mini-study (Section 7).

**Environment [V].** Python 3.13.1, numpy 2.3.3, scipy 1.16.2,
scikit-learn 1.9.0 on this machine — identical to the bundle's declared
reproduction environment.

**Not re-run / not reproduced here [S]:** the full SIM-1…SIM-5 battery
(~14 core-hours for SIM-2 alone); the 8-shard SIM-2 bit-identity claim (shard
logs exist); SIM-5 part A fixture equivalence as a fresh run (corroborated by
the self-test's exact backend-equality checks on rerun).

## 3. Research question, estimands, and hypothesis specification

**What Campaign 4 tests [S from draft/proposal; consistent with code].** A
measurement-axis campaign (30 executions / 45 proposals; class budgets
confirmatory 12 / exploration 9 / falsification 18 / replication 6;
`min_falsification_share` 0.35; `max_per_direction` 12; budgets campaign-scoped,
duplicate memory global and permanent across C1–C4). It opens the three
never-executed directions (error_analysis, data_quality, target_design) plus
the v1.1.0 primitives, including the four that feed Holm families:
`regime_split_analysis` (2 members: above/below SMA200),
`target_horizon_robustness` (3: 1/2/3-session horizons),
`purge_sensitivity_probe` (3: +0/+5/+10 purge), `complexity_reduction_check`
(1) — rung tables verified live against `three_valued.ladder_for` and the
`FAMILIES` table [V].

**Estimand.** δ = pooled out-of-frame AUC(candidate) − AUC(reference) on
identical purged walk-forward folds 2023–2025 over the frozen ~61k-row event
frame; event rows are the units, weeks are the dependence/clustering unit
(4-week circular blocks for the bootstrap; whole weeks for the flips). Target:
binary label, 1-session hold ≥ +2% [S: agent state]. The arms are deterministic
fitted model configurations — there is no randomization assignment; the packet
states this plainly (D2 mandatory disclosure).

**Decision rules [V from code + D3].**
- **ROBUST** (promotion): all six gates PASS (`experiment_adapter.py:975`:
  unit, data_integrity, leakage, walk_forward, robustness, evaluation), each
  required cell pairing a point condition (delta ≥ `primary_metric_min_delta`)
  with a CI condition (`ci_lower_min` ≥ −0.01) — IUT; `recipe_harness.decision_criteria_pass`
  implements exactly this and refuses nothing silently [V].
- **REFUTED** (formal): only from the campaign-end Holm-adjusted sign-flip
  decision over the complete family, one-sided (δ < 0); the bare label is
  firewalled everywhere else (`multiplicity.assert_firewall_intact`,
  token-bounded regex) [V].
- **INCONCLUSIVE**: everything else; provisional signals default INCONCLUSIVE
  when no campaign-end record exists (`resolve_without_record`) [V].

**Stopping rules.** The frozen config declares 14 stops; the C4 draft carries
15 (14 + `point_in_time_contamination_detected`); owner ruling R-2 ratifies
14 + 2 = 16 with `unverifiable_lineage_detected` to be declared at freeze —
verified: the draft's list is exactly the C3 set plus the point-in-time stop
[V]. All 16 have enforcement markers wired (`STOP_ENFORCEMENT`, readiness
`impl.stop.*` PASS). Budgets and direction exhaustion are fail-closed stops;
Holm is computed once, at campaign end — no mid-campaign formal testing.

**Preregistration status.** Plan v3 (pinned `094827b0…`) is the protocol
authority and predates the simulations; SIM protocols, seeds, and acceptance
criteria were predeclared and are recorded per output [V: seeds/meta in result
files, packet §10]. The C4 configuration is **not frozen** — it remains the
2026-10-09 DRAFT with placeholders and without `n_boot`, M, the multiplicity
block, or the 16th stop [V]. Family membership rules are frozen in code
(`FAMILIES`) and may not change after results exist [V].

**Design observations (not blockers).**
- The −0.01 `ci_lower_min` is a provisional non-inferiority floor, not
  evidence-of-gain; the repository's own Oct-4 audit quantifies its leverage:
  under a 0.0 floor, 3 of 8 Campaign-2 acceptances flip to rejection
  (`AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md` §3.6) [V as documented analysis;
  accepted as documentation, arithmetic not re-derived here].
- Primitives outside the four families (`minimum_effect_falsifier`,
  `complexity_premium_check`, `seed_set_replication`, and all C1–C3 recipes)
  are excluded from every Holm family [V: `EXCLUDED_PRIMITIVES`], so their
  refutation signals can **never** become formal REFUTED claims — only
  provisional/INCONCLUSIVE. This is conservative and documented, but it scopes
  C4's formal claims narrower than its proposal language; the freeze review
  should state that scope explicitly.

## 4. Independent assessment of the proposed statistical method

**The statistic [V].** In `simh10.py`, per week a fair-coin arm-label swap is
applied to all of that week's events; the pooled AUC difference is recomputed.
The implementation computes the flipped statistic exactly by the linear form
δ_flip = s·g / (2·n_pos·n_neg) over week-level contributions g
(`TrialStats.sign_flip_deltas`, `simh10.py:286`), verified against brute-force
`roc_auc_score` recomputation (max |diff| 1.527e-16 on this machine's rerun of
the self-test) [V]. The p-value `p_b = (#{δ_flip ≤ δ̂} + 1)/(M + 1)`
(`run_methods`, `simh10.py:452`) is one-sided lower-tail, matching H1: δ < 0,
with the +1 Monte-Carlo correction giving a super-uniform p-value under the
sharp null and a representable floor of 1/1001 [V].

**Validity logic [V as mathematics; conditional on A].** Under the sharp null
that the joint within-week distribution of the two arms' score vectors is
invariant to per-week label swaps, the group of 2^W transformations acts
measure-preservingly; the Monte-Carlo p-value built from uniformly drawn group
elements is then exactly super-uniform for any dependence structure across
weeks, and Holm converts super-uniform marginals into FWER ≤ α under arbitrary
dependence. This reasoning is sound. What it does **not** give is exactness for
the *weak* null (aggregate δ ≥ 0 with non-exchangeable arm distributions) —
which is the claim that motivates REFUTED decisions. That transfer is **[A]**
assumption, exactly as the packet states (§1 note, §5). Nothing in the
repository or in my recomputation can close it.

**What my independent probes add (Section 7).** Under an exchangeable-arm
null my own sign-flip implementation rejects at 5.0% (15/300) [V]; with an
AR(1) week factor (ρ = 0.7) and exchangeability intact, 4.7% (14/300) [V] —
empirically supporting the theoretical point that cross-week serial
correlation *alone* does not break the test; with population AUCs held exactly
equal by affine construction but arm B rescaled ×1.6 (within-week
exchangeability broken — the packet §5.2 "asymmetric arm construction"
mechanism), 6.7% (20/300; exact binomial p = 0.15 vs 0.05; CP95
[0.041, 0.101]) [V]. That point estimate is mildly elevated but the probe is
underpowered (≈830 trials needed to discriminate 0.067 from 0.05 at 80% power);
it neither validates nor refutes the assumption. Verdict on Q1: exactness
against the sharp null is proven; the weak-null transfer is a disclosed,
unverifiable assumption — adoption is defensible only as an explicit
owner-accepted risk, with the external reviewer's independent judgment on it.

**Monte-Carlo precision at Holm's first thresholds [V analysis].** With
M = 1000, the MC standard error of p̂ near the first Holm threshold for a
50-member family (α/m = 0.001) is ≈ 0.001 — the same order as the threshold.
Validity is unaffected (the +1 correction is conservative), but a member whose
true p sits near α/m can be decided by MC noise; SIM-2's empirical FWER already
integrates this. Consequence: decision instability for borderline members,
not error inflation. The protocol forbids increasing M without revision; the
mitigation is disclosure and the boundary-adjacent members being few by
construction.

**Week as the flip unit.** The real frame (~156 weeks of 2023–2025 [S]) gives
ample group size; W never limits resolution (M does). The unsimulated
mechanisms the packet flags (shared-training dependence; serial dependence)
remain **[A]/[U]**: no local artifact can establish their absence, and my
probe only bounds the scale-asymmetry variant weakly.

## 5. Multiple-comparison and p-value audit

**Holm implementation [V].** `multiplicity.holm_step_down`
(`multiplicity.py:230`) — sorted step-down, monotone adjusted values
capped at 1.0, rejection stops at the first non-rejection, ties broken by
index. I cross-checked it against two independently written textbook
implementations (my own vectorized version and the submitted `simh10.holm_step_down`)
on 20,000 randomized families (m = 1–60, ties, 0/1 masses, exact-threshold
cases): **0 mismatches** in adjusted values and rejection decisions, including
the exact-boundary case p = α/m (rejected — `≤`, correctly, not `<`).

**Family completeness and freezing [V].** Four families, membership defined by
primitive, caps 24/36/36/12 (2/3/3/1 members per experiment × 12 per
direction), frozen before generation; `FamilyMember` refuses undeclared
families, cross-family mixing, and any excluded primitive; `assemble_record`
refuses a record exceeding the frozen bound; the campaign-end record is
append-only, once per campaign (`append_record` refuses re-decision). Pooling
is campaign-end over the complete family only; no mid-campaign testing path
exists in production [V: no production caller at all — see §8].

**Granularity feasibility [V].** The H-10b rule B+1 ≥ 20·m is exactly the
condition that the representable p-floor 1/(B+1) can cross Holm's first
threshold α/m: 1/1001 = 0.0009990 ≤ 0.05/50 = 0.001 (m = 50 feasible) and
1/1001 > 0.05/51 (m = 51 infeasible) — verified numerically; the m ≤ 50 cap is
therefore exact, not arbitrary. `feasibility()` reproduces all SIM-4 numbers
(20m−1: 479/719/719/239/1799) with correct reasons [V]. Infeasible families
resolve every member to INCONCLUSIVE, never REFUTED; SIM-2's floor-blocked
cells show FWER exactly 0 for (a)/(b) — verified from the raw arrays [V].

**C-2 unavailable-member rule [V + D-doc].** Option A is implemented as
written: unavailable members count toward m at p = 1.0
(`FamilyMember.effective_p`), are rendered "unavailable", can never be
REFUTED, and the record lists every member's unadjusted and adjusted numbers.
This is conservative for FWER. **Documentation imprecision [D-doc,
nonblocking]:** the phrase "does not change other members' thresholds" (packet
§7, decision sheet C-2) is literally false: because the unavailable member
increases m, every other member's Holm threshold strictens (α/(m−i+1) shrinks).
The *effect* is conservative — refutation becomes harder, never easier — so
validity is preserved, but the rule text should say "strictens, never
loosens". Correction: amend the wording at freeze; no code change needed.

**Marginal validity before adjustment [A].** Holm presumes super-uniform
marginals; that rests on the exchangeability assumption of §4. The battery
found (b)'s marginals well centered under all tested DGPs [V from raw arrays];
the real-data case remains the open assumption.

**P-value gate [V].** `APPROVED_P_VALUE_METHODS` is empty; `require_approved_method`
raises `PValueMethodUnresolved` (exercised live during this review). There is
no silent fallback to any approximation. Adding a method name is an
owner-decision code change, gated on the signed record.

**Freeze-test gap around M [D-conditional, blocking for freeze].** D4 defines
feasibility on **M** (the sign-flip count), but production `feasibility()` and
the campaign-end record are keyed to **n_boot** (the CI bootstrap), and no
production artifact represents M at all. If M were ever reduced below 20·m−1
while `n_boot` stayed ≥ 1000, the freeze test would pass while formal
refutations became systematically unattainable (conservative, but silently
INCONCLUSIVE-forcing). Correction: pin M = 1000 explicitly in the frozen
config's `multiplicity_policy`, carry an `M` field into the campaign-end
record, and extend the freeze feasibility check to M. This must be fixed
before freeze approval.

## 6. Bootstrap, confidence-interval, and `ci_lower_min` audit

**Bootstrap semantics [V].** The CI comes from the frozen backend
`block_bootstrap_delta` (`recipe_harness.py:362`): whole-week resampling,
4-week circular blocks, in-frame order, truncate at n, paired across arms,
percentile 95% interval, `n_boot` from config, seed = `seeds[0]` (fixed 42) —
deterministic and exactly reproducible. The submitted SIM-5 replica matches
the backend bit-for-bit (max |ΔCI| = 0.0) [S submitted; the same
backend-equality checks re-ran exactly in this review's self-test rerun [V]].
The unpaired-control divergence (rejection 0.0633 → 0.0033; CI width ×2.466;
Fisher p = 3.07e-05, recomputed from the submitted counts [V]) confirms the
paired form is what is being tested for.

**Resampling unit vs dependence [analysis].** The bootstrap resamples 4-week
blocks; the test flips individual weeks. The two functionals therefore use
different dependence structures by design — disclosed (packet §6) and the
structural root of the SIM-3 disagreement. Both units are defensible for the
frame (≈156 weeks); neither is a defect, but the inconsistency is real and is
why CI and p must not be treated as interchangeable decision rules.

**`ci_lower_min` [V].** Range-limited to [−1, 1] (`recipe_harness.py:75,
139-146`); absent ⇒ −∞ (`:199`); pass condition `ci_lower ≥ ci_floor`
combined with `delta ≥ primary_metric_min_delta` and ≥3 folds (`:191-205`);
decisions gate on the rounded, reported 6-decimal values (documented choice,
deterministic from outputs; rounding at 1e-6 is negligible against a −0.01
margin). The v1.1.0 evaluator refuses point-only passes —
`three_valued.Margin` raises when `ci_lower_min is None` (`three_valued.py:94,
188`) [V]. Every family primitive carries the same provisional −0.01 floor
with an explicit provenance string stating it is **not** statistically
validated (H-1) [V: live primitive inspection]. The compiler routes
`acceptance_margin.ci_lower_min` into the harness config verbatim
(`compiler.py:155-156`) [V].

**CI-vs-p reconciliation (SIM-3, Q4).** The ≤1% criterion failed for all three
candidates (my recomputation from raw arrays: 0 discrepancies vs
`sim3.json`; (b) ranges 1.4%–2.8% in null cells and 8.7% near-null; all cells
>1% for all methods) [V]. The proposed reconciliation — formal REFUTED via
Holm p only; the CI kept as provisional signal + effect-size functional; any
disagreement recorded (`ci_disagrees_with_p`, never silently absorbed) — is
statistically coherent: a percentile-bootstrap CI and a sampled permutation
p-value invert different functionals, and letting a single valid test carry
the formal decision while the CI is disclosed avoids pretending they are the
same procedure. My assessment for Q4: **defensible, with two conditions** —
the disagreement must remain recorded per member (it is), and C-3 must be
explicitly ratified (it is pending). One operational note: the ROBUST
(non-inferiority) gate at `ci_lower ≥ −0.01` and the REFUTED test (δ < 0 with
CI upper < 0 as provisional signal) live on opposite sides of zero; a member
can be ROBUST-passing yet later formally REFUTED in a family context (or vice
versa) — this is by design (different claims: promotion vs degradation) but
should be stated in the campaign-end record's reader-facing text.

**Bootstrap MC noise [analysis, nonblocking].** With B = 1000 and a fixed
seed, CI endpoints carry MC error that is never quantified in the gate output;
a member sitting within MC-error distance of the −0.01 floor could flip pass/fail
under a different seed. Determinism (reproducibility) was chosen over
seed-averaging; the per-seed row-resample sweep exists for point estimates
but not for the CI gate. Correction (optional, requires protocol revision if
adopted as a gate change): report a boundary-proximity flag when
|ci_lower − floor| < a predeclared tolerance.

## 7. Dependence, assumptions, power, and sensitivity

**Dependence mechanisms.** Simulated: within-week shared factors (ρ up to
0.9), member correlation in families (ρ up to 0.7) — SIM-2 (b) FWER 0.032–0.057
over every attainable cell across all ρ [V, recomputed from raw arrays].
Not simulated anywhere: shared-*training* dependence (overlapping OOF fits)
and week-to-week serial correlation — honestly disclosed (packet §5–§6) **[A]**.

**My independent probes [V]** (own DGP, own AUC, own flip loop; N = 300
trials, M = 1000, 24 weeks × 15 rows): symmetric null 5.0%; AR(1) ρ = 0.7 with
symmetry intact 4.7% (serial correlation alone does not break exactness —
consistent with the group-invariance argument); equal-population-AUC but
rescaled arms (symmetry broken) 6.7%, not significantly above nominal at this
N (p = 0.15), underpowered (≈830 trials would discriminate 0.067 vs 0.05 at
80% power). These bound the concerns weakly and cannot substitute for the
real-data judgment.

**Power [S/V].** (i) Rejection at true δ = −0.01, m = 1, ~3.6k-row frames:
41–46% for all candidates (SIM-1 cell v; recomputed 0.453/0.411/0.457) — no
material power differences among candidates. (ii) Mixed configuration:
98.5% of strong H1s (δ ≈ −0.078) rejected at 5.25% true-H0 rejection
(recomputed 0.0525 / 0.9852) [V]. (iii) The real frame (~61k rows) is larger
than any simulated frame, which helps — as an argument, not evidence [S].
Non-significance at these power levels must not be read as evidence of no
effect; the record's INCONCLUSIVE semantics handle that correctly.

**Sensitivity alternatives.** Block-level flips (the bootstrap's own 4-week
unit) were proposed to the reviewer as an alternative construction (packet
Q2) and were not simulated **[U]** — worth a bounded SIM-1-style run at
ρ = 0.7 if the external reviewer requests it. Larger M for borderline members
is protocol-gated. Alternative methods (a)/(c) are decisively rejected by the
recomputed SIM-2 data (FWER up to 0.2705 / 0.2420 vs 0.0565) [V] — the
battery did not fail to discriminate candidates.

## 8. Reproducibility findings

1. **Integrity [V].** Bundle digest, all 11 manifest hashes (zip + repo), all
   packet §10 pins, the C3 config sidecar, and the C4 draft hash verify
   exactly. No artifact in the reviewed set has drifted.
2. **Self-test reproduced [V].** `run_sim.py selftest` reran on this machine:
   all 11 checks PASS in 5.4 s, including sign-flip linear-form vs brute-force
   (1.527e-16), sign-flip identity at all-+1 (exact), frozen-backend CI and
   `n_valid` exact equality, quadratic-form AUC vs sklearn (exact), Holm
   hand fixture. Output: `scratch_prereview_2026_10_13/selftest_rerun.log`.
   (Evidence-file overwrite incident disclosed at the top; file restored.)
3. **SIM summaries reproduced from primary arrays with independent code [V].**
   - SIM-1 from per-trial npz: cell-mean rejection at α = 0.05 —
     (a) 0.0635, (b) 0.0498, (c) 0.0632; raw liberal flags 12/24, 1/24, 8/24;
     **zero** Bonferroni-corrected flags (threshold 6.94e-4); power cell
     0.453/0.411/0.457 — all exactly the submitted claims.
   - SIM-3 from the same arrays: disagreement = XOR(p ≤ 0.05, CI upper < 0);
     **0 discrepancies** vs `sim3.json`; criterion (>1%) fails for every
     candidate in every cell — confirmed.
   - SIM-2 from raw member p-value arrays (2,000 × 90 × 3 per ρ) with my own
     Holm: (b) attainable FWER 0.032–0.0565 (submitted: 0.032–0.057, display
     rounding); worst cell exactly k = 113/2000 at (ρ = 0.3, m = 4,
     B = 1000), one-sided exact binomial p = 0.101424 (submitted 0.1014);
     (a) 0.0655–0.2705 and (c) 0.063–0.242 (submitted 0.066–0.271 / 0.063–0.242,
     rounding); C4-decision cells at B = 1000 — m = 24: (b) 0.041–0.0485,
     (a) 0.160–0.174, (c) 0.1235–0.150; m = 36: (b) 0.0325–0.0365,
     (a) 0.1465–0.1665, (c) 0.1435–0.176 — all submission-consistent; mixed
     config (b): 0.0525 true-H0 rejection, 0.9852 mean H1 rejection;
     floor-blocked cells: FWER exactly 0 for (a)/(b) — fail-closed confirmed
     from primary data.
   - SIM-4/feasibility arithmetic and production `feasibility()` agree
     (§5); SIM-5 submitted figures are internally consistent (Fisher p
     recomputed 3.07e-05) [V as arithmetic on submitted counts].
4. **Production-code statistical surfaces [V].** Holm/C-2/firewall/feasibility
   behave as specified (exercised live). `recipe_harness.decision_criteria_pass`
   and the six-gate literal match the written semantics. **No production
   implementation of the sign-flip p-value exists**, and nothing in
   production calls `campaign_end_record` or supplies `unadjusted_p` (grep
   over non-test source) — the formal-refutation pipeline is, today,
   fail-closed empty by design. The test suite (347 tests, green today)
   exercises the multiplicity machinery in isolation.
5. **Not verified here [S].** Full battery re-run (~14 core-hours); the 8-shard
   SIM-2 bit-identity (shard logs present, not re-executed); SIM-5 part A as a
   fresh fixture run (corroborated by the self-test's backend checks).

## 9. Blocking issues and exact remediation steps

**B1 — BLOCKER (governing, cannot be closed locally): exchangeability and
sharp→weak-null transfer.**
Artifact: packet §5 / decision record standing limitation 1–3. Claim: (b) is
valid for the campaign's REFUTED claims on the real data. Status **[A]/[U]** —
unverifiable by any local artifact or diagnostic; my probes bound it only
weakly (§4/§7). Remediation: the independent **written** human assessment
(answering packet §9's six questions) lands at
`stat_validation_h10/D2_EXTERNAL_REVIEW_ASSESSMENT.md`; the agent validates
provenance/scope; the owner records D2 (adopt/reject/defer) and, if adopting,
C-3 — each with signature, per the decision sheet. Nothing in this AI
pre-review substitutes for that artifact.

**B2 — BLOCKER (operational, correctly ordered): the method is not
implemented in production.**
Artifact: grep over `autonomous_agent/` (non-test): no sign-flip
computation; no production caller of `campaign_end_record`; `unadjusted_p`
has no producer. Remediation: after the signed D2 record and gate-3-style
implementation authorization, implement the port per decision-sheet gate 4 —
sign-flip p-value (M = 1000, +1 correction, lower-tail, week unit), wire the
campaign-end multiplicity record end-to-end, and add equivalence tests
against the `simh10.py` reference on fixtures (the same standard SIM-5 set
for the bootstrap). Until then the fail-closed empty pipeline is the correct
state.

**B3 — BLOCKER (freeze package, prepared but unapplied).**
Artifacts: C4 draft (`n_boot` absent [V]; `multiplicity_policy` absent [V];
15 stops vs the R-2-ratified 16 [V]; `unverifiable_lineage_detected`
undeclared; placeholders `campaign_id/created_at/seed_base/protocol_fingerprint`;
census tolerances unfrozen — draft manifest fails validation with 97
"tolerance not frozen" errors [S: reconciliation §5]). Remediation at freeze
(gate 6, only after B1): apply the prepared amendment
(`CAMPAIGN_4_CONFIG_RECONCILIATION_2026_10_12.md` §6), pin `n_boot = 1000`
**and M = 1000**, declare all 16 stops, finalize provenance fields, compute
the protocol fingerprint, execute the census under frozen tolerances, write
the fresh SHA pin. The readiness check correctly refuses today
(`c4.not_frozen`, exit 2).

**C1 — CONDITIONAL (freeze-test gap): M is invisible to feasibility and to
the record.** §5. Correction: M field in config + campaign-end record +
feasibility check on M; verify at freeze review.

**C2 — CONDITIONAL (documentation): the C-2 "thresholds unchanged" wording.**
§5. Correction: reword to "strictens, never loosens, other members'
thresholds" in the frozen config text and any reader-facing description.

**C3 — CONDITIONAL (governance sequencing note).** The recorded
`launch_gates.json` entry `implementation_complete` reflects the
owner-authorized scope (gate-3 subset + R-3 activation, 347 tests green). The
decision sheet's gate 4 additionally requires the *ported sign-flip* (B2),
which cannot exist before D2. Correction: when the external review returns and
D2/C-3 are recorded, re-affirm `implementation_complete` against the sheet's
full gate-4 wording, or amend the gate note to state the scope explicitly.

**C4 — CONDITIONAL (precision).** MC-noise of p̂ at Holm's first thresholds
(§4) and unquantified CI-endpoint MC error at the −0.01 floor (§6). Neither
affects validity (both conservative/neutral); both are disclosure items.
Correction: note them in the frozen record's limitations; optionally add a
boundary-proximity flag (protocol revision if it changes a gate).

**N1 — NONBLOCKING (operational).** Simulation stages re-save pinned outputs
in place (the selftest.json incident, fully restored). Correction: runners
should write to a scratch path by default, or a pre-run hash guard should
refuse to clobber a manifest-pinned file.

## 10. Final recommendation

**DEFENSIBLE ONLY AFTER SPECIFIED CORRECTIONS.**

1. The submitted statistical evidence is authentic, internally consistent, and
   independently reproducible in its decision-relevant numbers; I found **no
   fabricated, cherry-picked, or arithmetically wrong claim** in the packet,
   the evidence report, or the code. The battery behaved like a real
   falsification exercise (it rejected two of three candidates and retained
   its own failure, SIM-3).
2. Method (b) with Holm is mathematically sound against its sharp null and
   empirically well calibrated under every DGP tested; adoption for the
   campaign's claimed use is defensible **only** as an explicit
   owner-accepted assumption (week-level exchangeability; sharp→weak transfer)
   confirmed by the independent human assessment. That assessment — not this
   pre-review — is the mandatory next gate (B1).
3. Before any freeze: apply the freeze package (B3) including the new C1 fix
   (pin M and check it); after D2/C-3 and their signatures: implement and test
   the production port (B2), then re-run gate-7 readiness, then take the
   launch decision separately.
4. My probes (§4, §7) add: serial correlation alone appears benign under
   symmetry; a stylized scale-asymmetry violation produced a mildly elevated
   but non-significant 6.7% — if the external reviewer wants an empirical
   bound on that mechanism, run the preregistered N ≥ 1,000 version on
   synthetic data only (it still cannot prove the real-data assumption).

**Claims that could not be verified from available evidence:** real-data
week-level exchangeability **[A]**; sharp→weak-null transfer **[A]**;
transport of proxy-frame calibration (800–3,600 rows) to the ~61k-row frame
**[S]**; shard-level bit-identity of the SIM-2 run **[S]**; adequacy of power
for real-campaign decisions **[U]** (only two probes exist).
