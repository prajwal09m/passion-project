# H-10 / D2 / C-3 — OWNER DECISION RECORD (RECORDED 2026-10-14)

**Status: RECORDED DECISION.** This file records decisions made by the
project owner and transcribed, with verbatim provenance, by the coding
agent. No handwritten signature is claimed, forged, or represented. The
proposed drafts `H10_D2_PROTOCOL_AMENDMENT_PROPOSED_2026_10_13.md` and
`H10_C3_RATIFICATION_PROPOSED_2026_10_13.md` remain unsigned historical
drafts; their unfilled hand-signature blocks are superseded in form by the
written owner directive recorded below, not filled in by the agent.

---

## 0. Source of owner authorization (verbatim)

The decisions in this record originate from the project owner's written
message titled **"FINAL DIRECTIVE — COMPLETE AND LAUNCH CAMPAIGN 4"**,
delivered to the agent's execution channel and dated 2026-10-14 (the
repository session date; no timestamp is fabricated — the date is the
session date of the directive). Operative passages quoted verbatim:

> "I explicitly authorize you to complete all remaining work within your
> capabilities and governing rules, make the documented owner decisions
> specified below, conduct exactly one final integrated review, and launch
> Campaign 4 in this execution if all mandatory technical and governance
> conditions are legitimately satisfied."

> "**My instruction in this message authorizes the following owner
> decisions, subject to the project's valid approval mechanism:**
> **D2:** Adopt the AI statistical review as the project's explicitly
> authorized substitute for the unavailable external review, with full
> disclosure that the reviewing AI also implemented parts of the system.
> Accept the documented residual statistical limitations only to the extent
> supported by the review. Record the decision and its provenance
> accurately.
> **C-3:** Evaluate the documented SIM-3 reconciliation and ratify it if
> the existing evidence supports the proposed disposition. Record the
> actual rationale.
> **Freeze:** Authorize the configuration freeze after every prerequisite
> is satisfied, including the final statistical-method specification,
> declared tolerances, census validation, all required stops, and a fresh
> configuration fingerprint and SHA-256 pin.
> **Launch:** Use my explicit instruction to proceed with Campaign 4 as
> launch authorization once the authoritative launch gate passes."

> "Do not invent an external reviewer, forge a signature, fabricate a
> timestamp, backdate approval, or claim that an unsigned record is signed.
> If the protocol requires an actual signature that cannot legitimately be
> represented by this instruction, identify that narrowly defined
> constraint rather than falsifying it."

**Signature constraint (identified, not falsified).** The proposed records'
hand-signature blocks contemplate a handwritten owner signature. A
handwritten signature cannot be transcribed or synthesized by the agent
without falsification, so none appears anywhere. The narrow constraint is
recorded here: what exists is the owner's written directive (quoted above)
and the owner-maintained `launch_gates.json` mechanism, whose own template
states that a gates entry "is the owner's recorded evidence, not machine
proof." The owner has directed that these two artifacts together constitute
the owner's decision act for this campaign; the gates entries below record
`decided_by` truthfully as the owner acting through that written directive,
with the agent named as the transcriber.

---

## 1. D2 — DECIDED: ADOPT (substitute-review route, disclosed COI)

**Decision.** The owner adopts the AI statistical review as the project's
explicitly authorized substitute for the unavailable external human
review, and records D2 as decided with the decision: **adopt method (b) —
week-level sign-flip Monte-Carlo p-values (M = 1000) with Holm step-down at
familywise α = 0.05 — under the protocol amendment, on the strength of
Result 2′ only.** The method is named `week_level_signflip_holm`.

**Conflict-of-interest disclosure (carried verbatim per amendment §3).**
The AI reviewer that produced the assessment **is the same agent that
implemented parts of the system under review** — specifically the
proposal-layer compiler, the v1.1.0 primitive activation, and tests around
the multiplicity machinery — and it wrote the original Result 2 claim that
its own Addendum A retracts. Relative to a truly external human
statistician this is a **weakened form of independence: the review is
adversarial in method but not conflict-free in fact, and it is not an
independent external reviewer in the personnel sense.** The owner accepts
that weakening explicitly.

**Accepted record set.** The assessment on which this decision rests is
`stat_validation_h10/D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md` (sha256
`0bfcf1df…`, 27,920 bytes), together with Addendum A (sha256 `2fc0ed3f…`)
and `D2_REVIEW_SUPERSESSION_NOTE_2026_10_13.md`. The review's operative
verdict is APPROVE WITH CONDITIONS — REVISED (Addendum A §8): it rests
solely on Result 2′ (procedure-level validity of the randomized sign-flip
procedure) and is conditional on C-1, C-2, and C-5 being binding in the
production port.

**Result 2 retraction.** Result 2 (fixed-set conditional exactness) is
retracted and may not be cited as an operative guarantee anywhere. Result
2′ is operative: validity is **procedure-level** — marginal over the
randomized flip draw — never conditional on the realized flip set.

**Accepted statistical limitations (bounded by what the review supports,
per amendment §4):**

1. FWER control is exact only under week-level arm-label exchangeability
   on the real data — a disclosed assumption, unestablished and
   unestablishable by local artifact. Under two tested equal-AUC asymmetry
   classes, marginal size was **0.055 / 0.060 (CP95 upper 0.071 / 0.077)**;
   tail behavior at Holm thresholds under asymmetry is unmeasured. The
   owner accepts this residual risk for degradation-only formal claims.
2. Conditions **C-1** (flip rows drawn i.i.d. uniform on the full
   week-level group; never curated or redrawn after outcome inspection),
   **C-2** (flip-set generation is part of the procedure: a
   data-independent draw recorded before outcome evaluation; a constant
   seed is not automatically a valid draw), and **C-5** (all guarantees
   stated at procedure level; no conditional-on-realized-set exactness
   claims anywhere) are binding in the production port.
3. **M = 1000 is pinned**; the campaign-end record discloses the
   Monte-Carlo resolution limitation (minimum representable p = 1/1001;
   borderline members at large m resolved with 25–48% probability, biased
   toward non-rejection).
4. C-2 Option A counting (unavailable member at p = 1.0) **strictens,
   never loosens**, the remaining members' Holm thresholds (corrected
   wording; the pinned decision sheet's "unchanged" is superseded).

---

## 2. C-3 — RATIFIED (evidence-supported)

**Evaluation.** The owner instructed: ratify "if the existing evidence
supports the proposed disposition." The evidence does:

- SIM-3 failed its predeclared ≤1% XOR criterion for **every** candidate
  method: structural CI-vs-test disagreement near the null of **1.4–8.7%**
  (reproduced independently in the D2 review §7). This is a genuine,
  disclosed failure of a predeclared criterion, retained in the record.
- The structural cause is established: the CI's resampling unit (4-week
  blocks) and the decision's test unit (whole weeks) differ by design, so
  near-null disagreement is expected and is not evidence that either
  functional is miscalibrated.
- The reconciliation is coherent and keeps the two functionals from
  silently contradicting a claim: formal decisions follow the adjusted
  p-value alone (the sign-flip test + Holm step-down is the only pathway
  to a formal REFUTED claim); the CI is a provisional marker and
  effect-size functional with explicit "not statistically validated (H-1)"
  provenance; disagreement is recorded per member in
  `ci_disagrees_with_p` in every campaign-end record; point-only passes
  are impossible (three-valued Margin raises).

**Ratification.** The owner **RATIFIES** adopting method (b) —
`week_level_signflip_holm`, M = 1000, Holm step-down, familywise α = 0.05
— despite SIM-3's ≤1% failure, via the reconciliation clause above. The
actual rationale is the evidence evaluation recorded in this section. If
the recorded evidence had not supported the proposed disposition, C-3
would have been refused; it was evaluated, not presumed.

---

## 3. Freeze and launch authorization

- **Freeze:** authorized conditional on every prerequisite being
  satisfied first: final statistical-method specification (this record +
  the production port), declared float tolerances via a documented,
  evidence-based rule, census manifest validation with zero errors, all 16
  stop conditions declared, and a fresh configuration fingerprint and
  SHA-256 pin written at freeze time.
- **Launch:** this directive is the owner's explicit launch authorization
  for Campaign 4 (`campaign-4-continuous-2026-10-14`, 30 executions / 45
  proposals) to be exercised once the authoritative launch-readiness gate
  returns its genuine success result. Readiness approval and actual
  execution are distinct; both must be evidenced.
- The sealed holdout (`study_files/outputs/study_v1/prospective/`) remains
  untouched, unopened, unused — invariant verified continuously.

---

## 4. Gates entries this record supports

`stat_validation_h10/launch_gates.json` is updated by this decision:
`review_received` (the substitute-review assessment accepted with the COI
disclosure above), `d2_decided` (decision ADOPT, evidence this record),
`c3_ratified` (RATIFIED, evidence this record). `freeze_approved` and
`launch_authorized` are recorded later, each at its own act, citing this
record as the underlying owner authorization.

**Recorded by:** the coding agent, as transcription of the owner's written
directive. **Decision date:** 2026-10-14 (session date of the directive;
no other timestamp is asserted).
