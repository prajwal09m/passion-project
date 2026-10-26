# ADDENDUM A — Adversarial Audit of Result 2 (Fixed-Set Sign-Flip Exactness)

**Date:** 2026-10-13. **Author:** the project's assigned AI reviewer
(Buffy/Codebuff) — the *same* agent that wrote the original review. This is a
self-correction performed adversarially at the owner's explicit instruction:
"Reopen Section 4, Result 2 ... Do not assume the existing proof is correct
... Do not preserve the existing APPROVE WITH CONDITIONS verdict merely for
consistency. The final conclusion must follow from the corrected mathematical
argument."

**Independence disclosure (material).** The reviewer is not external to the
work under review and wrote the claim being retracted here. This addendum's
only mitigation is that every step below is re-derived from scratch and every
number is produced by a new, standalone scratch implementation — the original
proof is not reused, and its failure is demonstrated computationally, not
asserted.

**Status and boundaries.** This file is an *addendum* to
`D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md`. The original review is left
**byte-identical** (27,920 bytes; sha256
`0bfcf1df0fbd3f27d7fc2f6b02b0ffcda7f11f8cd7986ae97f101ef60c880c74`,
re-verified after this work) — it is not edited, no approval field or verdict
field in it is changed, no gate, pin, record, or holdout is touched, the
configuration is **not** frozen, and Campaign 4 is **not** launched. This
addendum supersedes Result 2 wherever cited. All computations reproduce from
`scratch_independent_review_2026_10_13/fixed_set_exactness_audit.py` (run
EXIT=0; results in `fixed_set_exactness_audit_results.json` and
`fixed_set_exactness_audit.log`).

---

## 0. Conclusion

**Result 2 of the original review is false as stated, and its proof contains
a specific invalid inference.** The step "the vector has the same joint
distribution as its shift by any group element, **hence** all M+1 coordinates
are exchangeable" fails because a group shift maps the fixed flip set F to a
*different* set F·g unless F is a subgroup of the flip group — and the
report's null invariance only gives law(V∘g) = law(V), which relates nothing
about the coordinates of a single vector when V∘g is built from other
transformations.

Concretely, for the production statistic family under an **exact**
product-group-invariant null: conditional on one fixed 3-element flip set the
p-value's size at α = 1/3 is **0.36614** (closed form; Monte-Carlo
0.366089 ± 0.000341, N = 2,000,000; 95 % CI [0.365421, 0.366757]) — strictly
greater than 1/3, so "exactly super-uniform conditionally on the flip set" is
refuted. Exhaustive enumeration of **all 32,768** possible fixed sets on a
4-week panel found **6,549 threshold-level violations in non-closed sets and
zero among the 67 closed sets (subgroups)**. The joint vector is directly
**non-exchangeable** for the counterexample set (correlation matrix not
invariant under swapping coordinates 0 and 1).

What survives — and what the production procedure actually needs — is the
corrected two-part result **Result 2′** (§5): conditional-on-set exactness
holds **only** when the fixed set is a subgroup of the flip group (impossible
for production M = 1000, since |F| = M+1 = 1001 is odd and flip subgroups
have order 2^k), while **procedure-level exactness holds whenever the flip
rows are drawn i.i.d. uniform from the flip group independently of the data**
(verified: fresh-draw size 0.301675 ± 0.000726 against exact 0.3027344 ≤ 1/3;
and 0.044 ± 0.003243 ≤ 0.04995 at M = 1000, α = 0.05). The verdict
reassessment is in §8.

---

## 1. Formalization of the test (Q1)

- **Sample space / group action.** Let x denote the data (the vector of
  week-level signed contributions of the arm difference). The flip group is
  G = {−1, +1}^W acting by componentwise sign change (g·x = g ⊙ x); G ≅ Z_2^W.
  Composition of flips is componentwise multiplication = XOR of bit masks.
- **Null hypothesis (the report's own, §2/§4).** H0: the data law P is
  invariant under the product group of 2^W within-week arm-label swaps —
  i.e. P is G-invariant. (This is the sharp/distributional symmetry
  assumption whose real-data status is separately disclosed as an
  unverifiable assumption; this addendum takes it as given and audits only
  the conditional-exactness claim.)
- **Statistic.** T(x) = δ̂, and under a flip g the statistic is T(g·x) =
  δ_flip(g) = g·g_vec / (2·n_pos·n_neg) — a **linear form over weeks**
  (Result 3 of the review; re-verified there at 1.5e-16 vs brute force).
  Nothing below needs more than T being *some* function of g·x; the
  counterexample uses the plainest member of this family, the (equal-weight)
  mean over weeks.
- **Fixed transformation set.** A fixed set of flip vectors F = {s_1, …, s_M}
  chosen once (pinned seed), augmented with the identity: the p-value counts
  the observed statistic as coordinate 0, so the vector examined is
  V(x) = (T(x), T(s_1 x), …, T(s_M x)), an (M+1)-coordinate object indexed
  by F₀ := F ∪ {e}.
- **P-value.** p(x) = (1 + #{b ≤ M : T(s_b x) ≤ T(x)}) / (M+1)
  (exactly the implementation form, `simh10.py:452`; lower tail, "+1"
  correction, `≤` tie handling).

**Claim under audit (verbatim, Result 2).** "For any *fixed* set of M flip
vectors and the identity, under the invariance null the vector (T_obs,
T(s₁), …, T(s_M)) has the same joint distribution as its shift by any group
element, hence all M+1 coordinates are exchangeable, hence the rank of T_obs
is uniform on {0…M}, hence p_MC is exactly super-uniform conditionally on
the flip set (ties only make it conservative). A production port with a
pinned flip seed ... is therefore still exact under the null."

## 2. Where the proof breaks (Q2)

The chain has three links. Link 1 is true, links 2 and 3 are the problem.

1. **What null invariance does give.** For any g ∈ G,
   law(V(g·X)) = law(V(X)), because g·X =_d X under P. TRUE.
2. **The false step — "same joint distribution as its shift".** The
   shifted object is V(g·x) = (T(h x))_{h ∈ F₀·g}, i.e. a vector indexed by
   the *translated set* F₀·g = {h·g : h ∈ F₀}. For this to be a coordinate
   permutation of V(x) (what "its shift" must mean for step 3 to follow), one
   needs **F₀·g = F₀ as a set** — the setwise-stabilizer condition. The claim
   asserts it for "any group element"; it holds for all g ∈ G **only if F₀ is
   a subgroup of G**. In general F₀·g ≠ F₀ (§3), so the two invariance facts
   — law(V∘g) = law(V) and V(g·x) being built from a different set of
   transformations — never meet. "Hence exchangeable" does not follow.
3. **Even for subgroups, exchangeability does not follow.** If F₀ ≤ G, then
   V(g·x) *is* a coordinate permutation of V(x), with coordinate map
   h ↦ h·g (right multiplication). The permutations obtainable this way
   generate the regular representation of F₀ — a group isomorphic to F₀
   acting on |F₀| points — which for |F₀| ≥ 4 is **not** the full symmetric
   group (e.g. |F₀| = 4: the generated group has order 4, not 24). Full
   exchangeability of the coordinates is therefore still unproved exactly
   where the conclusion is needed. (For |F₀| = 2 — i.e. M = 1 — the claim
   happens to be true; it fails from M = 2 onward.)

So the stated theorem is false, its mechanism is wrong twice over, and a
*correct* substitute exists (§5) — one that does not need exchangeability at
all, only closure for the conditional statement, or the randomness of the
draw for the procedure-level statement.

## 3. Set-mapping check (Q3)

Shift by a group element maps the fixed set to a **different set** unless the
element stabilizes it:

- Counterexample set F₀ = {e, s₁, s₂} with flip masks {0,7,11} (flip sets
  {0,1,2} and {0,1,3} over W = 4). Right-translate by s₁: F₀·s₁ = {0, 7, 12}
  ≠ F₀ (the identity moved to s₁, s₁ moved to e, and s₂ moved to s₁·s₂ ∉
  F₀). Verified in the results JSON (`equals_F: false`).
- Stabilizer structure: F₀·g = F₀ ⟺ g ∈ Stab(F₀); for a *non-closed* F₀ the
  stabilizer is a proper subset of G, so "any group element" is wrong.
- **Parity obstruction for production.** Flip subgroups of {±1}^W have order
  2^k. Production pins M = 1000 rows: |F₀| = M+1 = 1001 = 7·11·13 is odd
  and greater than 1, so **no pinned production flip set can ever be a
  subgroup**, even in principle. The entire conditional-by-closure route is
  unavailable for the actual procedure (same for the SIM grids: M+1 ∈
  {501, 1001, 2001}).
- Multiplicity caveat: the implementation averages over *rows* with
  multiplicity; repeated rows make the average a weighted, non-uniform
  group average, which is not covered by any exactness argument either.
  For W ≥ 40 the chance of any duplicate among 1000 i.i.d. rows is ≤
  ~5·10⁻⁷, so distinctness holds a.s.; the caveat matters for small W only.

## 4. Counterexample (Q4)

All of the following satisfies the report's null **exactly** and uses the
report's statistic family.

**Construction.** W = 4 weeks. F₀ = {e, s₁, s₂}, flip sets {0,1,2} and
{0,1,3}. Statistic T(x) = mean over weeks (linear week form, Result 3
family). Null law: x ~ N(0, I₄) — invariant under the *full* product group,
so H0 holds without qualification. Define Y₁ = x₀+x₁+x₂, Y₂ = x₀+x₁+x₃.
Then T(s_b x) ≤ T(x) ⟺ Y_b ≥ 0, so p = (1 + 1{Y₁ ≥ 0} + 1{Y₂ ≥ 0})/3 and
p ≤ 1/3 ⟺ Y₁ < 0 and Y₂ < 0. Y₁, Y₂ are jointly Gaussian, Var = 3 each,
Cov = 2, ρ = 2/3, so

    P(p ≤ 1/3) = ¼ + arcsin(2/3)/(2π) = 0.366143 > 1/3.

Monte-Carlo (N = 2,000,000, seed 20261013): **0.366089 ± 0.000341**
(95 % CI [0.365421, 0.366757]) — agrees with the closed form and lies ≈96
standard errors above 1/3. Near-duplicate rows are worse (one flip set
contained in the other: sizes 4 and 3 sharing 3 coordinates, ρ = √(3/4)):
0.416667 at α = 1/3. A literally duplicated row
(F₀ = {e, s, s}) gives p ∈ {1/3, 1} with P(p = 1/3) = P(Y < 0) = 1/2.

**Non-exchangeability, directly (Q2/Q4 joint).** For the same F₀, the
correlation matrix of V = (T(x), T(s₁x), T(s₂x)) under the null is

    [ 1.0  -0.5  -0.5 ]
    [-0.5   1.0   0.0 ]
    [-0.5   0.0   1.0 ]

All three marginals are identical (each coordinate is a linear form of an
i.i.d. Gaussian), yet swapping coordinates 0 and 1 — the transposition the
exchangeability claim requires — maps the (0,2) entry from −0.5 to 0.0, so
the joint law is **not** invariant under it: the augmented vector is not
exchangeable under an exactly-satisfying null.

**Exhaustive enumeration (the general picture).** Null: x uniform on
{±1}⁴ (product-group invariant; ties present). T = mean. All 2¹⁵ = 32,768
subsets F₀ of the flip group containing e were enumerated; for each, p(x) was
computed for all 16 x and checked for super-uniformity at every attainable
threshold:

| class | count | violations |
|---|---|---|
| closed sets (subgroups; sizes 1, 2, 4, 8, 16) | 67 | **0** |
| non-closed sets | 32,701 | 6,549 threshold-events; worst: |F₀| = 6, α = 1/6, CDF 0.3125 (excess +0.146) |

Explicit size-3 example (F₀ masks {0,7,11}): p-distribution {1/3: 6/16,
2/3: 4/16, 1: 6/16}; CDF at 1/3 = **0.375 > 1/3**. This is the discrete-null
twin of the Gaussian counterexample above. The pattern across all 32,768 sets:
**violations occur exactly in the non-closed sets; closed sets never
violate** — which is precisely the corrected theorem of §5.

## 5. Conditional-on-a-fixed-seed vs randomly-sampled transformations (Q5)

Two different statements are routinely conflated; Result 2 conflates them.

**Result 2′-A (conditional validity — what IS true).** *If* the fixed set F₀
is a **subgroup** of G and P is F₀-invariant (automatic under H0), *then*
p₀(x) = |F₀|⁻¹·#{h ∈ F₀ : T(h x) ≤ T(x)} is super-uniform — for **any**
statistic T (no equivariance needed). Proof: condition on the F₀-orbit O of
x; invariance makes X uniform on O; p₀(x) is then the empirical CDF of the
orbit's T-values evaluated at T(X), i.e. a rank divided by |F₀| of a uniform
draw — super-uniform with ties (conservative). The enumeration in §4
confirms this with zero violations across all 67 subgroups of {±1}⁴.
Note: the proof needs **no exchangeability of V** — that concept was the
error. Note also the parity obstruction (§3): unavailable at production
M = 1000.

**Result 2′-B (randomized-procedure validity — what production can claim).**
*If* s₁, …, s_M are drawn **i.i.d. uniform on G, independently of the data**
(fresh per test, or drawn once and recorded as part of the procedure), then
p = (1 + #{b : T(s_b X) ≤ T(X)})/(M+1) is super-uniform **marginal over the
draw** (Dwass 1957; Phipson & Smyth 2010). Proof: condition on the G-orbit O
of X; then X is uniform on O, each s_b·X is an independent uniform point of O,
and T(X), T(s₁X), …, T(s_MX) are i.i.d. given O; p is the self-rank of one
i.i.d. sample — super-uniform. Verification in §4D: W = 4, M = 2,
α = 1/3 → size **0.301675 ± 0.000726** (exact with orbit ties 0.3027344 =
1240/4096) ≤ 1/3; W = 6, M = 1000, α = 0.05 → **0.044 ± 0.003243** ≤
50/1001 = 0.04995 (the i.i.d.-continuous rank bound). Same formula as
production, valid.

**The distinction, stated sharply.**

- Validity of the randomized statement is a property of the **procedure that
  includes the draw**. It is not conditional on the realized set: some
  realized sets are bad (§4: 0.366 and 0.375 for one fixed set; 6,549
  violating sets), and they occur with positive probability under the very
  generator production would use.
- Therefore "pinned flip seed ⇒ still exact **conditionally on the flip
  set**" (the retracted Result 2) does **not** follow from the procedure's
  randomness, and is false as a general statement. A pinned set can be
  *used* honestly only under the procedure-level reading: the draw is part of
  the test specification, made independently of the data, recorded, never
  selected or re-drawn after seeing results — and the record says so.
- The analogy in Result 2 to `seeds[0]=42` is instructive but cuts the other
  way: a bootstrap CI that conditions on its resampling seed is *describing
  a quantile of a resampled distribution*, not asserting a conditional
  p-value guarantee. For p-values the conditional guarantee is exactly what
  cannot be had for a non-subgroup set.

The pre-review's open question ("do deterministic seeds compromise
validity?") now has a correct answer: **a recorded draw does not compromise
procedure-level validity; a curated or hand-fixed transformation set would,
and no guarantee conditional on any particular realized set exists.** The
question is resolved — but in this weaker, correct form.

## 6. Conditions that justify the production procedure, and their status (Q6)

| # | condition | status |
|---|---|---|
| C-1 | Flip rows drawn **i.i.d. uniform** on {±1}^W (the full group), never curated/balanced/selected | **Satisfied** in the reference implementation: `simh10.py:450` `S = rng.integers(0, 2, size=(M, W)) * 2 - 1`; `run_sim.py:308` same for the nested-B grid (prefixes of i.i.d. stay i.i.d.) |
| C-2 | Flip-set generation is **part of the procedure**: a data-independent uniform draw recorded once (or fresh per test); never chosen, re-drawn, or re-used after any inspection of results | **Not yet satisfiable to verify** — no production sign-flip exists (re-verified today: 0 non-test hits in `autonomous_agent/`). Must be written into the port spec as a binding requirement. If a literal constant seed is used, the record must present the rows as one realized draw of the documented procedure and must not claim the set-conditional guarantee |
| C-3 | The null (product-group invariance / week-level arm-label exchangeability on real data) | Unchanged; remains the disclosed, unestablishable-by-local-artifact assumption (original §5) |
| C-4 | p = (1 + #{δ_flip ≤ δ̂})/(M+1), lower tail, M ≥ the Holm-granularity floor | **Satisfied**: `simh10.py:452`; granularity unchanged (§7) |
| C-5 | Documentation: all guarantees stated at the procedure level (Result 2′-B); no conditional-on-realized-set exactness claims anywhere in the record | Enforced by this addendum; **Result 2 retracted** |
| C-6 | If any reviewer or protocol demands set-conditional assurance: only subgroup enumeration (order 2^k) or fresh per-test draws are available; full enumeration 2^W is infeasible at W = 157 | Optional; not required for validity under C-1/C-2/C-5 |

The verdict in §8 is conditional on C-2 and C-5 being adopted with the
port.

## 7. Implications for the existing results (Q7)

1. **P-value calculation.** Formula, direction, "+1" correction, and `≤`
   tie handling are unchanged and correct; only the *guarantee label*
   changes: valid as a randomized-procedure statement (C-1/C-2), **not**
   certified conditional on the pinned flip set. Simulations and self-tests
   that evaluate the whole randomized procedure (SIM-1/SIM-2 fresh draws)
   are unaffected — they tested exactly the procedure Theorem 2′-B covers.
2. **Holm FWER.** Result 5 stands: Holm controls FWER under arbitrary
   dependence given super-uniform marginals; the corrected marginals
   (procedure-level, shared seed included as part of the dependence) deliver
   that. Any claim of *conditional-on-seed* FWER control must be withdrawn;
   the FWER conclusion itself (≤ 0.05 under the global null) survives on
   Result 2′-B. SIM-2's empirical FWER cells (0.032–0.0565) remain
   interpretable as procedure-level calibration.
3. **Monte-Carlo resolution table** (my prior review's Result 3: borderline
   members rejected only 25–48 % of the time at M = 1000; minimum
   representable p = 1/(M+1) needed for m ≥ 41). Pure combinatorics of
   (1+k)/(M+1) — **unaffected**. The parenthetical citation "(discreteness is
   conservative; Result 2)" in the original review line 263 repoints to
   Result 2′-A/B (discreteness conservatism is a rank argument, independent
   of the retracted claim).
4. **Simulation evidence & other results of the original review.** Result 1
   (fresh draws) is correct as stated (it is Theorem 2′-B in earlier form);
   Result 3 (linearity) and Result 4 (direction) untouched by this audit;
   Result 5 as above. Empirical probes and the far-tail "Unknown" stand.
5. **Real-data assumption status.** Unchanged: nothing here strengthens or
   weakens week-level exchangeability on the real frame; §5/§11 disclosures
   of the original review stand.

## 8. Verdict reassessment, defect, and required remedy (Q8)

**Defect (explicit).** Result 2's claim of *exact super-uniformity
conditionally on any fixed flip set* is false; its proof's pivotal inference
("shift by any group element, hence exchangeable") is invalid because a
shift maps a non-closed fixed set to a different set (and even closed sets
yield only regular-representation, not full, exchangeability). Counterexample:
size 0.36614 > 1/3 at α = 1/3 under an exactly-satisfying null, in-family
statistic (plus 0.375 discrete twin; 6,549 violating sets in exhaustive
enumeration; direct non-exchangeability of the augmented vector).

**Remedy (required).**

1. Retract Result 2; adopt Result 2′-A/B (§5) as its replacement text.
2. Repoint every citation of Result 2 (original review line 263; any bundle
   or decision-sheet reference; my prior addenda's MC-resolution note) to
   Result 2′.
3. Make C-1, C-2, C-5 binding conditions in the production port
   specification (the port does not exist yet, so this is cheap to impose
   now); record the flip-set draw (rows + seed) at freeze time as part of the
   procedure, independent of campaign data.
4. State in the campaign-end multiplicity record that validity is
   procedure-level; prohibit any record asserting validity "conditional on
   the pinned flip set".
5. If set-conditional assurance is ever demanded, only C-6 options exist.

**Revised statistical verdict: APPROVE WITH CONDITIONS — REVISED, not the
original verdict carried forward.** The corrected mathematics does support
the method: Theorem 2′-B + C-1/C-4 (already satisfied by the reference
implementation) establish valid p-values, and Result 5 lifts them to FWER
control — so the *method* remains approvable. But the approval now rests
**solely on Result 2′**, with two conditions added to the original list:

- **A-7:** this addendum is adopted, Result 2 formally retracted, and
  citations repointed (remedy items 1–2, 4);
- **A-8:** the production port spec binds C-1/C-2/C-5 (remedy item 3) before
  any flip p-value is produced.

Explicitly: **if this addendum is not adopted — i.e. if Result 2 stands
written as the operative guarantee in any signed record — the correct
verdict for that record is DEFER**, because the exactness guarantee it asserts
cannot be established. The label "APPROVE WITH CONDITIONS" survives here
only because Result 2′ is provable and its conditions are satisfiable; it is
not preserved for consistency. The original conditions (exchangeability
disclosure, C-3 ratification, M-granularity freeze fix, production port,
owner-signed protocol amendment for D2 closure) are untouched and unchanged;
Campaign 4 must not launch and nothing is frozen by this document.

---

*Reproducibility: `stat_validation_h10/scratch_independent_review_2026_10_13/`
— `fixed_set_exactness_audit.py` (EXIT=0),
`fixed_set_exactness_audit_results.json`, `fixed_set_exactness_audit.log`.
Original review sha256 re-verified unchanged after all of the above.*
