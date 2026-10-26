# H-10 Statistical Review Packet — `week_level_signflip_holm`

Status: **PREPARED FOR REVIEW. NOT REVIEWED. NOT APPROVED.**
Prepared: 2026-10-17 by the AI engineering assistant. This packet is an evidence bundle and a list of
questions. It does not state a conclusion about validity.

## 1. What is being asked

Is the method below valid for its intended use: a multiplicity-controlled, procedure-level
(marginal over the randomized flip draw) decision that a family member's effect is degraded, with
familywise α = 0.05 under Holm step-down?

Method (as recorded): week-level sign-flip Monte-Carlo p-values, M = 1000, Holm step-down over the
frozen family members, familywise α = 0.05. Name: `week_level_signflip_holm`.

## 2. Records that govern this review (cite exactly)

| Record | Role | SHA-256 (per record text) |
|---|---|---|
| `stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md` | Newer owner decision: D2 ADOPT (substitute-review route, disclosed COI); C-3 RATIFIED | verify at review time |
| `stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md` | Older record: D2 DEFERRED; "not adopted and not validated"; C4 BLOCKED | b9db32335c93ccf5a06b764023f21b6595c2fa4a0a4dd7ccbec6f87d2e9f0a42 |
| `stat_validation_h10/D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md` | AI statistical assessment (cited by the owner record) | sha256 `0bfcf1df…` per owner record (27,920 bytes) |
| Addendum A to the above | Retracts Result 2; operative verdict "APPROVE WITH CONDITIONS — REVISED" | sha256 `2fc0ed3f…` per owner record |
| `stat_validation_h10/D2_REVIEW_SUPERSESSION_NOTE_2026_10_13.md` | Supersession note | not hashed in this packet |

**Important status distinction.** The owner record states that the external human statistical
review is unavailable and that the owner explicitly adopted the AI assessment as a substitute,
with the conflict of interest disclosed. The AI reviewer is the same agent that implemented parts
of the system under review. This packet does **not** treat that substitute as independent external
review. Whether the owner's substitute route satisfies the project's requirement for independent
review is a governance question for the owner and is listed as unresolved in §8.

## 3. Computations and disclosures to be checked

Reported in the owner record (each must be independently reproduced by the reviewer; none is
reproduced here):

- **Result 2′ (operative):** procedure-level validity of the randomized sign-flip procedure,
  marginal over the random flip draw. **Result 2 (fixed-set conditional exactness) is retracted and
  may not be cited.**
- **Size under asymmetry:** marginal size 0.055 and 0.060 under two tested equal-AUC asymmetry
  classes (Clopper–Pearson 95% upper bounds 0.071 and 0.077). Tail behaviour at the Holm thresholds
  under asymmetry is recorded as **unmeasured**.
- **SIM-3 failure:** a predeclared ≤1% XOR criterion between the CI functional and the test
  functional failed for every candidate method, with near-null disagreement of 1.4–8.7%. The owner
  attributes this to the CI resampling unit (4-week blocks) differing from the test unit (whole
  weeks). **This attribution is the owner's reconciliation and is itself unreviewed.**
- **Monte-Carlo resolution:** minimum representable p = 1/1001 at M = 1000; borderline members at
  large m are resolved with 25–48% probability, biased toward non-rejection.
- **C-2 Option A:** an unavailable member enters at p = 1.0, which tightens the remaining Holm
  thresholds.

Conditions attached to the owner's adoption (binding in the production port, per the owner
record): **C-1** (flip rows drawn i.i.d. uniform over the full week-level group; never curated or
redrawn after outcome inspection), **C-2** (flip-set generation is a data-independent draw recorded
before outcome evaluation; a constant seed is not automatically a valid draw), **C-5** (guarantees
stated only at procedure level).

## 4. Specific questions for the reviewer

**Q1 — Exchangeability / sign symmetry.** Under the intended null, are the week-level units
exchangeable in arm label (or is the sign-flip symmetric) on the real data? The owner record says
this is "unestablished and unestablishable by local artifact." Is there a defensible
diagnostic, and does a diagnostic on development OOF rows alone support any inference?

**Q2 — Temporal dependence.** Weeks are adjacent in time and share training data. Under what
dependence structure is the sign-flip p-value valid, and does shared-training dependence (listed as
"not simulated" in the older record) invalidate super-uniformity? Is a block or dependence-aware
randomization needed instead?

**Q3 — Super-uniformity of marginal p-values.** Under the actual null (including the asymmetry
classes actually produced by the estimators), are the marginal p-values super-uniform? The reported
size 0.055–0.060 at nominal 0.05 is above nominal; is that within the Monte-Carlo error, and is it
acceptable for a multiplicity-corrected decision?

**Q4 — Adequacy of the null calibration.** Are the two asymmetry classes and the simulations
sufficient to support the inference? What null scenarios are missing (e.g. autocorrelated arm
differences, regime-dependent variance)?

**Q5 — Monte-Carlo resolution near Holm thresholds.** With M = 1000, the minimum p is 1/1001 and
borderline decisions are resolved with 25–48% probability. Is the decision reliable enough near the
Holm thresholds? Is a larger M, a sequential stopping rule, or an exact enumeration on a reduced
space required, and would changing M be a protocol amendment?

**Q6 — Holm with resolution-limited p-values.** Is Holm step-down still controlled when p-values are
discrete and biased toward 1 for borderline members? Are ties handled correctly?

**Q7 — One-sided conventions and degenerate samples.** Are the one-sidedness, empty-week, and
degenerate-sample conventions handled correctly (C-2 Option A and `unavailable` members in
particular)?

**Q8 — The CI-versus-test disagreement.** Is the owner's structural explanation (resampling unit
mismatch) sufficient to justify ratifying a method with a predeclared ≤1% criterion that failed at
1.4–8.7%? Should the CI be removed from any formal claim?

**Q9 — Conflict of interest and the substitute route.** The owner accepted a weakened form of
independence. Does the reviewer consider a substitute acceptable, and what independent check would
be needed to remove the conflict?

## 5. Reproduction material (to be supplied to the reviewer, not hashed here)

- Frozen method implementation: `autonomous_agent/proposal_layer/signflip.py` (sha256
  3b3d5b3116e36effe6f4a0bbb437cce298b49b9ed02fb52d78be0d5db62d0219 at 2026-10-17).
- Multiplicity machinery: `autonomous_agent/proposal_layer/multiplicity.py` (sha256
  b98b22d148f01dc1ed7673cfc1c81899bc0f0d5172d5252c2a625dcdadda3a79).
- Campaign-end finalization: `stat_validation_h10/campaign_end_finalization.py` (sha256
  10d89e947bd65a9f944043f210e4288eacba3c8cddd0fac43adf788e4c95b4c1).
- Development inputs: `study_files/outputs/study_v1/development/` (hashes in
  `C4_REAL_DATA_INTEGRATION_PREDECLARATION.md` §1). The sealed holdout is **not** part of this
  material and must not be provided for this review.
- Source-level check that the sign-flip draw is data-independent and recorded: **not yet verified
  by this assistant**; listed as unresolved in §8.

## 6. What the AI assistant verified and did not verify

Verified in this session (see the readiness report for exact commands): the Holm and sign-flip
test suites run inside the 422-test suite; no protected artifact changed. **Not** verified: the
statistical validity of the method, the size under the real null, the adequacy of M = 1000, or the
conditions C-1 and C-2 in the production code path.

## 7. Requested reviewer output

A written assessment stating, for each of Q1–Q9: supported / not supported / unresolved, with
reasons and any reproduction code, plus an overall verdict limited to the stated scope. The
assessment must state the reviewer's independence from the implementation.

## 8. Open items (unresolved)

1. Governance: whether the owner's substitute-review route satisfies the project's independent
   review requirement (owner decision).
2. Exchangeability on real data (Q1): unresolved.
3. Dependence-aware validity (Q2): unresolved.
4. Super-uniformity and the 0.055/0.060 size (Q3): unresolved.
5. Calibration sufficiency (Q4): unresolved.
6. Monte-Carlo resolution (Q5): unresolved; M = 1000 is pinned by the owner record.
7. Discrete Holm validity (Q6): unresolved.
8. Source-level verification of C-1 and C-2 in the production port: unresolved.

## 9. Status

- Independent statistical reviewer: **not engaged for this packet.**
- Reviewer approval: **none.**
- Method status: **adopted by owner decision with disclosed conditions; not independently validated.**
