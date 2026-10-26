# H-10 RECORD SUPERSESSION PROPOSAL (F-4) — FOR OWNER REVIEW

**Status: PROPOSAL ONLY. Not applied. Not approved. Nothing in the older
record has been modified. This document requests an owner decision.**

Prepared: 2026-10-16 as part of the F-4 remediation requested after
`stat_validation_h10/C4_POST_REMEDIATION_INDEPENDENT_AUDIT_2026_10_16.md`.
The audit classified F-4 as governance ambiguity: an older H-10 decision
record conflicts with a newer owner decision record, and a reader could
quote either one as current.

## 1. Records identified (exact paths and SHA-256)

**Older record (the record this proposal would annotate):**

- Path: `stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md`
- SHA-256: `b9db32335c93ccf5a06b764023f21b6595c2fa4a0a4dd7ccbec6f87d2e9f0a42`
- Prepared: 2026-10-11; signature block intentionally blank; states its own
  status as "NOT SIGNED; NOT IN EFFECT."

**Newer authoritative record (the record this proposal points to):**

- Path: `stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md`
- SHA-256: `6dd405554e7afd7689162d275662b6e11d701e670f0416a7c5e21897f19528e0`
- Recorded: 2026-10-14; status "RECORDED DECISION" recording the owner's
  written directive verbatim, with the signature constraint identified
  rather than falsified.

**Supporting governance artifacts referenced (not modified):**

- `stat_validation_h10/launch_gates.json` —
  SHA-256 `dfed21cda460f898f9958d0276db83b110a7a618b0e43591d008ff87af2adeea`
  (owner-maintained human-gate record; `d2_decided`, `c3_ratified` and
  `review_received` recorded 2026-10-14 citing the newer record).
- `stat_validation_h10/H10_OWNER_AUTHORIZATION_RECORD_2026_10_11.md` —
  SHA-256 `6d83443b9f834c5bb2b9421cb33fbb34bcc77e45038396e4d32d349179c47bed`.
- `autonomous_agent/MAIN AUDITS AND REFLECTIONS/C4_FREEZE_RECORD_2026_10_14.md`
  (configuration freeze act) and
  `autonomous_agent/MAIN AUDITS AND REFLECTIONS/C4_LAUNCH_RECORD_2026_10_15.md`
  (Campaign 4 launch act).

Because these hashes were captured in a working-tree snapshot, any
re-verification must recompute them before the owner acts.

## 2. What in the older record was superseded (and by what)

The older record is not wrong for its date; several of its statements
describe the governance state **as of 2026-10-11** and were overtaken by
documented acts. The proposed supersession annotation would record exactly
this, statement by statement:

| # | Older statement (2026-10-11) | Superseded by | Current status |
|---|---|---|---|
| 1 | "**D2 — Statistical method: DEFERRED.** Method (b) ... is **not adopted and not validated** ... D2 is the sole unresolved scientific-method decision." | Owner decision record 2026-10-14 §1: D2 **DECIDED — ADOPT** method (b) `week_level_signflip_holm` (M = 1000, Holm step-down, α = 0.05) via the substitute-review route with the disclosed conflict of interest, resting solely on Result 2′; `launch_gates.json:d2_decided.decided = true`. | D2 is **decided and recorded**, adopted on the strength of an owner-accepted **substitute** (AI) review — an act of owner decision, **not** independent external statistical approval. See §3. |
| 2 | "**C-3 — SIM-3 adoption ratification: PENDING by design.**" | Owner decision record 2026-10-14 §2: C-3 **RATIFIED** after documented evidence evaluation; SIM-3's ≤1% criterion failure **retained** in the record; `launch_gates.json:c3_ratified.decided = true`. | C-3 is ratified as a recorded owner decision. The underlying SIM-3 failure it reconciles remains standing evidence. |
| 3 | The record's own precondition: D2 must close before C-3 becomes decidable. | Sequence satisfied by the newer record's ordering (D2 decided, then C-3 evaluated), recorded 2026-10-14. | The precondition mechanism itself is unchanged; only the state advanced. |
| 4 | Status banner: "**Campaign 4 remains BLOCKED** ... NOT IN EFFECT." | `freeze_approved` gate executed 2026-10-14 (`C4_FREEZE_RECORD_2026_10_14.md`), `launch_authorized` reaffirmed 2026-10-14, Campaign 4 launched 2026-10-15 (`C4_LAUNCH_RECORD_2026_10_15.md`) and subsequently archived (`CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16`). | The "BLOCKED" wording describes the earlier state. It is historical, not current. |
| 5 | D3/D4/C-1/C-2/C-4 decisions and the unimplemented-adjudication caveat ("v1.1.0 pending"). | Harness v1.1.0 implementation acceptance (2026-10-12) and subsequent wiring remediation (F-1/F-2). | Not superseded in substance; **re-scope note only**: the implementation-status caveat is stale, the adjudication semantics remain as specified. |

The exact wording of any annotation applied to the older record is drafted
in §5 below.

## 3. What remains outstanding and is NOT superseded

The following statements of the older record are **not** overtaken and must
travel with the annotation verbatim in substance:

1. **Signature never executed.** The older record's human signature block
   remains blank — correctly. No signature may be synthesized or inferred.
   The newer record does not fill it in; it identifies the handwritten-
   signature constraint instead (its §0). Whether the older record is ever
   signed is an owner act that this proposal neither performs nor presumes.
2. **Standing limitations 1–6 remain in force**: week-level
   exchangeability unverified on the real dataset; simulation evidence is a
   falsification battery, not proof of real-data validity; SIM-2 supports
   only "no significant excess detected," never FWER ≤ 0.05 as a guarantee;
   the governance-suite flake disposition; the reconstructed baseline
   caveat; the sealed holdout untouched.
3. **Independent statistical review is still outstanding.** The newer
   record adopted a *substitute* review performed by an AI agent that also
   implemented parts of the system, with that conflict of interest
   disclosed and explicitly accepted. That substitution is an owner
   decision about process; it is **not** an independent statistical
   approval and does not close the outstanding statistical questions
   (finding F-3; see `stat_validation_h10/H10_STATISTICAL_REVIEW_PACKET.md`
   prepared for submission to an independent reviewer).
4. **D1's SIM-3 failure retention** ("the SIM-3 failure stands in the
   record and is not erased") is consistent with, and reinforced by, the
   newer record's §2.

## 4. The three-way distinction this annotation must preserve

Readers must be able to tell apart, at all times:

- **(A) A recorded owner decision** — recorded in
  `H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md` and in
  `launch_gates.json`, which is itself documented as "recorded evidence,
  not machine proof."
- **(B) Independent statistical approval** — *outstanding.* Not claimed by
  either record. The adopted review is a disclosed substitute, not the
  conflict-free external review the protocol contemplated.
- **(C) Authorization to launch** — supplied separately by the owner's
  written directive and recorded in `launch_gates.json:launch_authorized`,
  exercised only after the readiness gate's genuine success result;
  readiness approval and execution are distinct evidences.

Neither this proposal nor the annotation it drafts moves anything from
column (B) into any other column, and it does not alter column (C).

## 5. Proposed annotation text (draft — applies only after owner approval)

To be inserted **at the top of**
`stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md`
**as a new section**, leaving every pre-existing byte of the record intact
(and never rewriting its 2026-10-11 dates):

> ## SUPERSESSION ANNOTATION — STATUS AS RECORDED 2026-10-14
>
> This record was prepared 2026-10-11 and records the owner's confirmed
> choices as they stood on that date. Statements above describing D2 as
> DEFERRED, C-3 as PENDING, the method as not adopted, and Campaign 4 as
> BLOCKED describe an earlier state of the project. The superseding
> authority is `stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md`
> (SHA-256 `6dd405554e7afd7689162d275662b6e11d701e670f0416a7c5e21897f19528e0`),
> recording the owner's decisions of 2026-10-14 (D2 ADOPT via the
> disclosed substitute-review route; C-3 RATIFIED), with gate entries in
> `stat_validation_h10/launch_gates.json`.
>
> Supersession is limited to those status statements. **This annotation
> does not claim that independent statistical review has been completed or
> approved** — the review adopted on 2026-10-14 is an owner-accepted
> substitute carrying a disclosed conflict of interest, and independent
> statistical approval remains outstanding. The signature block below was
> never completed and is not completed by this annotation: no owner
> signature is claimed, inferred, or synthesized. All standing limitations
> recorded above (exchangeability unverified; simulation is falsification,
> not proof; SIM-3 failure retained; sealed holdout untouched) remain in
> force. A recorded owner decision, an independent statistical approval,
> and authorization to launch are three distinct things; this annotation
> creates none of them.
>
> Annotating this proposal's own identity: older record SHA-256 at
> proposal time `b9db32335c93ccf5a06b764023f21b6595c2fa4a0a4dd7ccbec6f87d2e9f0a42`.
> Owner approval of this annotation to be recorded in
> `stat_validation_h10/launch_gates.json` or a successor decision record,
> naming the approving person and date.

## 6. Owner decision requested

1. Approve / reject / amend the §5 annotation as written.
2. Decide whether the older record is (a) annotated in place, or (b)
   marked obsolete by a pointer file that does not touch it, or (c) left
   untouched with this proposal filed alone.
3. Confirm that the four superseded statements listed in §2 are correctly
   scoped and no other statement of the older record is being reclassified.
4. Confirm nothing in this proposal is to be read as completing H-10's
   outstanding independent statistical review.

No agent may apply the annotation, edit the older record, or record an
owner approval in `launch_gates.json` without an explicit owner instruction.