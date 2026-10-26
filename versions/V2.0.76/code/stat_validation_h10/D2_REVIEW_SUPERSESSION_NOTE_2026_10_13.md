# D2 REVIEW SUPERSESSION NOTE — Result 2 retracted; Result 2' operative

**Date:** 2026-10-13. **Author:** the project's assigned AI reviewer
(Buffy/Codebuff), at the owner's remediation instruction ("Complete the
Addendum A corrections … create a clearly labeled supersession note if
necessary").

**What this note is.** A forward-looking corrective index. It supersedes
*claims*, not files: every pinned artifact stays byte-identical.

| artifact | sha256 (verified 2026-10-13, unchanged) | status |
|---|---|---|
| `D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md` | `0bfcf1df0fbd3f27d…` (27,920 B) | pinned evidence — **Result 2 retracted by Addendum A; all other results stand** |
| `D2_AI_INDEPENDENT_STATISTICAL_REVIEW_ADDENDUM_A_FIXED_SET_EXACTNESS.md` | `2fc0ed3feba82054…` (21,702 B) | pinned evidence — the operative correction |
| `H10_D2_REVIEW_SUBMISSION.zip` (bundle) | `ee345dab3a587b51…` | pinned evidence — untouched |
| `H10_DECISION_RECORD_AWAITING_SIGNATURE.md` | `b9db32335c93ccf5…` | pinned evidence — untouched |
| `MAIN AUDITS AND REFLECTIONS/CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json` | `307e98ab4b7207da…` | pinned evidence — untouched (superseded *for freeze preparation only* by the 2026-10-13 candidate) |

No approval field, gate, pin, seed record, or holdout artifact was modified
to produce this note. Nothing here is an approval; the human gates in
`launch_gates.json` remain exactly as recorded.

## 1. The retraction (operative statement)

**Result 2 of the original review — "the MC sign-flip p-value is exactly
super-uniform *conditionally on any fixed set of flip vectors*" — is
RETRACTED.** Both its proof mechanism ("the augmented vector has the same
joint distribution as its shift, *hence* exchangeable") and its conclusion
are false: a group shift maps a fixed set F₀ to a *different* set F₀·g,
equal to F₀ only when g stabilizes F₀; and even for subgroup sets the
obtainable coordinate permutations form only the regular representation,
never full exchangeability for |F₀| ≥ 4. Exhaustive enumeration of all
32,768 fixed sets on {±1}⁴ confirmed violations only in non-closed sets
(6,549 threshold-events; worst +0.146), zero among all 67 subgroups
(`scratch_independent_review_2026_10_13/fixed_set_exactness_audit.py`,
EXIT=0).

**What replaces it (Result 2′, Addendum A §5):**

- **2′-A (conditional):** exactness conditional on a fixed set holds only
  for *subgroup* sets (order 2^k). Impossible in production: |F₀| = M+1 =
  1001 is odd, flip subgroups have order a power of 2.
- **2′-B (procedure-level):** with flip rows drawn **i.i.d. uniform from
  the group, independent of the data**, p is valid *marginal over the
  draw* (verified: 0.301675 ± 0.000726 vs exact 0.3027344 at α = 1/3;
  0.044 ± 0.0032 ≤ 0.04995 at M = 1000, α = 0.05).

The old "deterministic seeds compromise validity" concern is therefore
**not** removed by the retraction's opposite: validity is a statement about
the *randomized procedure*, never about the realized flip set.

## 2. Conditions carried forward (binding on any production port)

| # | condition | status today |
|---|---|---|
| C-1 | flip rows drawn i.i.d. uniform on {±1}^W; never curated, balanced, or redrawn after outcome inspection | satisfied by the reference implementation (`simh10.py:450`, `run_sim.py:308`); **binding on the not-yet-existing port** |
| C-2 | flip-set generation is part of the procedure: a data-independent draw *recorded before outcome evaluation*; a compile-time constant seed is **not** automatically a valid draw — the record must show the seed was drawn by the documented randomization before any outcome existed, present the rows as one realized draw, and must not claim set-conditional validity | binding on the port; see `H10_SIGNFLIP_PORT_SPEC_2026_10_13.md` |
| C-3 | week-level arm-label exchangeability on the real data | unchanged, disclosed, unestablishable by any local artifact (original §5) |
| C-4 | p = (1 + #{δ_flip ≤ δ̂})/(M+1), lower tail, M ≥ the Holm-granularity floor | satisfied (`simh10.py:452`) |
| C-5 | all guarantees stated at procedure level; no conditional-on-realized-set exactness claims anywhere in the record | enforced; Result 2 retracted |

## 3. Documentation corrections (non-pinned references only)

The pinned review's own §10 items 6–8 required these at the next
documentation revision; they are applied here because the affected pinned
texts (decision sheet draft `5a62c9d0…`, packet `9ad91785…`, pre-review)
may not be edited — their hashes are quoted in the pinned bundle's
provenance table.

1. **C-2 missing-member wording — corrected.** The decision sheet's Option A
   text says an unavailable member is counted at p = 1.0 and "other members'
   thresholds are unchanged". **That is wrong.** Under Holm step-down,
   counting an extra member at p = 1.0 leaves every other member's rank in
   the ordering but increases m, so each threshold α/(m−i+1) becomes
   *smaller*: the rule **strictens, never loosens, the remaining members'
   thresholds** (worked example: a lone p = 0.03 rejects at 0.05; with an
   unavailable member added, m = 2, the first threshold drops to 0.025 and it
   does not — `test_multiplicity.py::MissingMemberRuleTests`). The decision
   sheet is pinned evidence; this note, not an edit, carries the correction,
   and the corrected wording is what the C4 candidate config records.
2. **Frame precision — corrected.** The reviewable evaluation frame is
   **~41,221 OOF rows / 157 weeks / π = 0.165**, not the "~61k-row / 231
   week" figure carried in the packet and pre-review (review §4/§10.7).
3. **Monte Carlo resolution — disclosure added to the campaign-end record
   reader text.** The sign-flip p grid is (1+k)/(M+1); its floor 1/(M+1)
   reaches Holm's first threshold α/m only while m ≤ α(M+1) (m ≤ 50 at
   M = 1000), and borderline members (true p near a threshold) are resolved
   with low probability (25–48 % at M = 1000), always biased toward
   non-rejection. This is now carried in the `note` field emitted by
   `multiplicity.assemble_record` (documentation only; no decision logic
   changed).
4. **Conditional-on-seed FWER claims — withdrawn.** Holm's FWER guarantee
   rests on super-uniform *marginals*; with Result 2 retracted those
   marginals are procedure-level (Result 2′-B, shared seed included in the
   dependence). Any record asserting *conditional-on-seed* FWER control is
   superseded by this note.

## 4. What the retraction does **not** change

- The p-value formula, "+1" correction, and ≤ tie handling (Results 1, 3, 4)
  — untouched and correct.
- Holm validity under arbitrary dependence (Result 5) — stands.
- The MC-resolution table (pure combinatorics) — stands; its parenthetical
  citation "(discreteness is conservative; Result 2)" repoints to Result
  2′-B: the conservatism is a rank argument, independent of the retracted
  claim.
- The SIM-1/2 calibrations and the independent probes — they tested the
  whole randomized procedure, exactly what 2′-B covers.
- The verdict's *structure*: still APPROVE WITH CONDITIONS — REVISED (per
  Addendum A §8), resting solely on Result 2′ and conditional on C-1/C-2/C-5
  being binding in the port. If any signed record relies on Result 2 as the
  operative guarantee, the verdict for that record is **DEFER**, because
  that guarantee cannot be established.

## 5. Owner decisions this note does **not** make

D2 remains undecided (`launch_gates.json`: `d2_decided.decided = false`).
The proposed protocol amendment and C-3 ratification are prepared, unsigned,
and ineffective until signed: see
`H10_D2_PROTOCOL_AMENDMENT_PROPOSED_2026_10_13.md` and
`H10_C3_RATIFICATION_PROPOSED_2026_10_13.md`.
