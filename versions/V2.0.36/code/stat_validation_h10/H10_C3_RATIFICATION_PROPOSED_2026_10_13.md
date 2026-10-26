# H-10 — C-3 SIM-3 RATIFICATION RECORD (PROPOSED, UNSIGNED, NO EFFECT UNTIL SIGNED)

**Prepared:** 2026-10-13 by the coding agent at the owner's remediation
instruction ("Prepare, but do not sign or falsely mark complete: a separate
decision record accurately describing the SIM-3 reconciliation and the
owner's ratification decision").

**Status: PROPOSED — NOT SIGNED — NOT DECIDED.** No signature, name, date,
or approval has been entered by the agent. `launch_gates.json` was not
modified (`c3_ratified` remains `decided: false`). This record is separate
from, and downstream of, the D2 protocol amendment
(`H10_D2_PROTOCOL_AMENDMENT_PROPOSED_2026_10_13.md`): per the governing
plan, C-3 is required only if D2 is decided as adopt, and it may not be
absorbed implicitly by any other decision.

---

## 1. The factual background (accurate description of SIM-3 and its reconciliation)

**What SIM-3 tested.** The predeclared simulation battery included SIM-3,
which measured the disagreement between the percentile moving-block
bootstrap CI (4-week circular blocks; the CI functional) and the week-level
sign-flip test (whole-week flips; the decision functional) on the same
synthetic frames. The plan's acceptance criterion was an XOR-rate (the two
functionals disagreeing on the direction call) of at most 1%.

**What SIM-3 found.** SIM-3 failed that criterion for **every** candidate
method: the structural disagreement rate near the null was **1.4–8.7%**
(reproduced independently in the D2 review §7), with all candidates above
1% everywhere. This is a genuine, disclosed failure of a predeclared
criterion — not a rounding artifact (the review re-derived it from primary
arrays and matched the pre-review's 24/1000 cell).

**The structural cause (established, not speculative).** The resampling
unit of the CI (4-week blocks) and the test unit of the decision (whole
weeks) differ by design. Near the null, the two functionals answer subtly
different questions, so disagreement is expected and is not evidence that
either functional is miscalibrated. Campaign 3's frozen backend and the
reference implementation share this design.

**The reconciliation (what adoption would rest on).** The reconciliation
recorded in the review (§7) and the evidence report is:

1. **Formal decisions follow the adjusted p-value alone.** The sign-flip
   test + Holm step-down is the only pathway to a formal `REFUTED` claim.
2. **The CI is kept as a provisional marker and effect-size functional**,
   never as a co-decider. Its non-inferiority floor (`ci_lower_min = −0.01`)
   carries explicit "not statistically validated (H-1)" provenance.
3. **Disagreement is recorded per member** in `ci_disagrees_with_p` in the
   campaign-end multiplicity record — surfaced, never silently absorbed.
4. Point-only passes are impossible (three-valued `Margin` raises).

The review assessed this reconciliation as coherent: "it never lets the two
functionals silently contradict a claim."

## 2. Why this is a separate owner act

The governing plan requires, verbatim, that the remedial branch "is adopted
subject to explicit human confirmation" and that "H-10 stays open until
that evidence exists and a human decision is recorded", under a fail-closed
rule ("if none passes, H-10 stays UNRESOLVED and Campaign 4 launch is
blocked"). Because SIM-3 failed for every candidate, adoption under the
remedial reading cannot be absorbed implicitly by approving D1/D2: it
requires this ratification, recorded separately.

## 3. What the owner is being asked to decide

Ratify (or refuse) **adopting method (b) — week-level sign-flip Monte-Carlo
p-values at M = 1000 with Holm step-down — despite SIM-3's ≤1% failure**,
via the reconciliation clause above. If ratified:

- The CI-vs-p disagreement stays disclosed per member
  (`ci_disagrees_with_p`) in every campaign-end record.
- The campaign-end record note now also carries the Monte-Carlo resolution
  disclosure (Addendum A / review §6: minimum representable p = 1/1001;
  borderline members at large m resolved with 25–48% probability, biased
  toward non-rejection) — implemented 2026-10-13 in
  `multiplicity.assemble_record`.
- Validity statements remain procedure-level (Result 2′-B); Result 2 stays
  retracted.

If refused: H-10 stays UNRESOLVED, `APPROVED_P_VALUE_METHODS` stays empty,
the fail-closed p-value gate stays closed, and Campaign 4 must not launch
with method (b).

---

## Owner decision block (to be completed by the owner, by hand)

- Decision:  RATIFY / REFUSE / DEFER
  — Rationale: ______________________________
  — Date: ____________
- If RATIFIED, `launch_gates.json` `c3_ratified` must be filled with
  `decided: true`, `decided_by`, `date`, and `evidence_path` pointing at
  this signed record.

**Owner signature:** ______________________________  **Date:** ____________
