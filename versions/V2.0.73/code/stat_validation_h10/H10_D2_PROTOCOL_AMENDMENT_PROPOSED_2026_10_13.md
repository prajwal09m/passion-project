# H-10 / D2 — PROPOSED PROTOCOL AMENDMENT (UNSIGNED, NO EFFECT UNTIL SIGNED)

**Prepared:** 2026-10-13 by the coding agent at the owner's remediation
instruction ("Prepare, but do not sign or falsely mark complete: a proposed
owner-signed amendment explicitly permitting the disclosed AI review to
substitute for the originally required external human assessment").

**Status: PROPOSED — NOT SIGNED — NOT DECIDED.** This document is a draft
for the owner's signature. No signature, name, date, or approval has been
entered by the agent. Nothing in `launch_gates.json` was modified
(`review_received`, `d2_decided`, `c3_ratified`, `freeze_approved` remain
`decided: false`). The existing external-review assessment location
(`stat_validation_h10/D2_EXTERNAL_REVIEW_ASSESSMENT.md`) was not created,
populated, or modified. This document adopts no method, freezes nothing,
and authorizes no launch.

---

## 1. What the governing protocol requires today

The D2 review route of the governing protocol (HARNESS_V1_1_0 plan and the
D2 external review packet) requires a **written assessment from a reviewer
independent of this project's authorship** — explicitly "not the owner's
authorization, not this agent, not the project author" — before D2 may be
decided. The owner has stated that no external human reviewer will be
provided. Absent the amendment below, D2 remains DEFERRED and the review
already in the repository is advisory evidence only.

## 2. What this amendment proposes

The owner signs a recorded decision to **substitute the disclosed AI review
for the originally required external human assessment** for the purpose of
deciding D2. Specifically:

1. `stat_validation_h10/D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md`
   (sha256 `0bfcf1df…`, 27,920 bytes), together with
   `stat_validation_h10/D2_AI_INDEPENDENT_STATISTICAL_REVIEW_ADDENDUM_A_FIXED_SET_EXACTNESS.md`
   (sha256 `2fc0ed3f…`, 21,702 bytes) and
   `stat_validation_h10/D2_REVIEW_SUPERSESSION_NOTE_2026_10_13.md`,
   is accepted as the written assessment on which the D2 decision may be
   recorded.
2. The original review's verdict is **APPROVE WITH CONDITIONS — REVISED**
   (Addendum A §8): it rests solely on Result 2′ (procedure-level validity
   of the randomized sign-flip procedure) and is conditional on C-1, C-2,
   and C-5 being binding in the production port. **Result 2 (exactness
   conditional on a fixed set of flip vectors) is retracted** and may not be
   cited as an operative guarantee in any signed record; if any signed
   record relies on it, the verdict for that record is DEFER.

## 3. Conflict-of-interest disclosure (material; must be carried verbatim into any signed record)

This disclosure is unconditional. The AI reviewer that produced the
assessment **is the same agent that implemented parts of the system under
review** — specifically the proposal-layer compiler, the v1.1.0 primitive
activation, and tests around the multiplicity machinery — and it wrote the
original Result 2 claim that its own Addendum A retracts. Relative to a
truly external human statistician this is a **weakened form of
independence: the review is adversarial in method but not conflict-free in
fact, and it is not an independent external reviewer in the personnel
sense.** The owner signing this amendment accepts that weakening explicitly.

## 4. Accepted statistical limitations and conditions (owner must restate at signing)

Per review §10 items 1–2 and Addendum A, the signed record must state:

1. FWER control is **exact only under week-level arm-label exchangeability**
   on the real data — a disclosed assumption, unestablishable and
   unestablishable-by-local-artifact. Under two tested equal-AUC asymmetry
   classes, marginal size was **0.055 / 0.060 (CP95 upper 0.071 / 0.077)**;
   tail behavior at Holm thresholds under asymmetry is **unmeasured**.
   The owner accepts this residual risk for degradation-only formal claims.
2. The production port must bind Addendum A conditions **C-1** (flip rows
   drawn i.i.d. uniform on the full week-level group; never curated or
   redrawn after outcome inspection), **C-2** (flip-set generation part of
   the procedure: a data-independent draw recorded before outcome
   evaluation; a constant seed is not automatically a valid draw — see
   `H10_SIGNFLIP_PORT_SPEC_2026_10_13.md` §4), and **C-5** (all guarantees
   stated at procedure level; no conditional-on-realized-set exactness
   claims anywhere). Validity is procedure-level (Result 2′-B), never
   conditional on the realized flip set.
3. M = 1000 is pinned; the campaign-end record discloses the Monte-Carlo
   resolution limitation (minimum representable p = 1/1001; borderline
   members at large m resolved with 25–48% probability, biased toward
   non-rejection).
4. C-2 Option A counting (unavailable member at p = 1.0) **strictens,
   never loosens**, the remaining members' Holm thresholds (corrected
   wording; the pinned decision sheet's "unchanged" is superseded — see
   `D2_REVIEW_SUPERSESSION_NOTE_2026_10_13.md` item 1).

## 5. What signing this amendment does and does not do

**Does:** permits the owner to record the D2 decision (adopt / reject /
deferred-with-rationale) on the strength of the disclosed AI review, with
the independence weakening and COI disclosure written into the signed
record.

**Does not:** sign C-3 (a separate record), freeze any configuration, write
any pin, populate `APPROVED_P_VALUE_METHODS`, authorize the production port
(decision-sheet gate 4 remains the authorizing act), or authorize launch
(gate 8 remains separate and already-recorded-as-contingent).

---

## Owner decision block (to be completed by the owner, by hand)

- Decision on this amendment:  ACCEPT / REJECT / DEFER
  — Rationale: ______________________________
  — Date: ____________
- If ACCEPTED, the D2 decision recorded in `launch_gates.json`
  (`d2_decided`) must carry: `decided_by`, `date`, `evidence_path` pointing
  at this signed record, and `decision` naming adopt/reject/defer with the
  limitations of §4 restated.

**Owner signature:** ______________________________  **Date:** ____________
