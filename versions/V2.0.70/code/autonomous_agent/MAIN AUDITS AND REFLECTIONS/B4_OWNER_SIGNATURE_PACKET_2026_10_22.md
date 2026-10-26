# B4 Owner Signature Packet — Campaign 5 Authorization (GATED)

**Created:** 2026-10-22
**Status:** PREPARED — **NOT SIGNABLE UNTIL THE PREREQUISITES GATE (below) IS CLOSED.**
**Closes (when signed after gating):** B4, per `CAMPAIGN5_BLOCKER_REGISTER.json`.
**Predecessor packets:** B1 must be signed first; this packet is a distinct, separate authorization act. Nothing in B1 authorizes integration or launch, and nothing in this packet is implied by B1, by Campaign 4 records, or by silence.

## Rule of record

- **Every section is a separate decision: APPROVE / DEFER / REJECT.** Blank or unsigned = DEFER = all C5 operations stay blocked.
- This packet is signed **once**, after prerequisites, and binds exact digests recorded at later freeze time; a freeze may not occur without re-binding the actual digests into the countersigned authorization record.
- Integration into production and launch each require **separate** explicit authorization acts after this one. Signing here authorizes one precisely bounded C5 study operation, nothing more.

## Why this packet is gated

The blocker register dependency order is B1 → B2/B3 → B5 → (all) → B4. Authorizing before the gates are closed would manufacture an approval that no independent party has checked.

## Prerequisite gate (all boxes must reference authentic records — verify each path exists and is not AI-authored)

- [ ] **G1 — B1 closed:** signed `B1_OWNER_SIGNATURE_PACKET_2026_10_22.md`
- [ ] **G2 — B2 closed:** reviewer-authored assessment recorded at `stat_validation_h10/H10_C5_INDEPENDENT_STATISTICAL_REVIEW.md`, with reviewer identity, independence/conflict disclosure, and the exact protocol digest it reviewed (must match G1's frozen digest)
- [ ] **G3 — B3 closed:** signed owner/data-steward boundary attestation `B3_EVALUATION_HOLDOUT_BOUNDARY_ATTESTATION_2026_10_22.md`, including the ruling on the disclosed header-only staged-fixture read
- [ ] **G4 — B5 frozen:** final predeclaration hash-recorded; reviewer and owner both approved **the same digest** (record the digest: `____________________________`)
- [ ] **G5 — B7 closed:** owner path-by-path legacy classification decision recorded in `B7_LEGACY_EXECUTION_PATHS_CLASSIFICATION_2026_10_22.md` with enforcement state noted
- [ ] **G6 — C5 trust keys provisioned:** `C5_OWNER_HMAC_KEY` and `C5_REVIEWER_HMAC_KEY` (distinct) set in the environment; keys never written to any file

If any box cannot be checked truthfully, **stop — do not sign.** The packet remains deferred and blocked.

## Decisions (mark each explicitly)

- [ ] **A-1. Scope (Option D — Regime/Error Analysis):** campaign ID `campaign-5-regime-error-analysis-2026-10-22`; budgets 45 executions / 60 proposals; class budgets confirmatory 12, exploration 16, falsification 24, replication 8; parent champion V2.0.61.
      Prior decision reference: B1 packet (P-2). ________
- [ ] **A-2. Permitted operations** exactly as itemized in `B4_OWNER_DECISION_PACKET_2026_10_22.md` §3 (development event table read-only; fold-local purged preprocessing; training-fold training; OOF on validation folds; regime/error analysis; multiplicity testing). ________
- [ ] **A-3. Prohibited operations** exactly as itemized in §4 (no holdout access/training/evaluation on holdout; no network; no brokerage/exchange APIs; no writes to frozen artifacts or the holdout path; no standalone-script invocation around the B7 controls; `llm_involved` must remain false throughout). ________
- [ ] **A-4. Expiry `2026-12-31T23:59:59Z` + revocation triggers and process** as itemized in §5. ________
- [ ] **A-5. Additional constraints** as itemized in §7 (no prospective outcomes; no trading simulation; no LLM assistance; champion integrity policy preserved). ________

## Digest register (verification at signing)

The countersigned authorization record binds all of the following; each must be recomputed at signing time and must match the values recorded in the record:

| Where | Bound at |
|---|---|
| Frozen C5 campaign config | computed at config freeze: `SHA-256(canonical_json(config_without_fingerprint_key))` — enter in record |
| Independent reviewer's reviewed protocol digest | from G2 |
| Final predeclaration digest | from G4 |
| Signed B1 packet bytes | `____________________________` (fill from the signed file at signing time) |
| Dataset: study_v1_development_event_table | `232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0` (per B1 resolution §Dataset) — verify against fixture provenance before recording |
| Dataset: study_v1_development_oof_predictions | `011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829` |

**Rule:** if any digest in the record differs from the artifact you believe you approved, the record is void until re-signed.

## Signature block (owner completes AFTER the gate closes)

```
Prerequisite gate closed:   [ ] verified (date: __________)
Decision:                   [ ] AUTHORIZE the single bounded C5 study operation as itemized
                            [ ] DEFER (blocked indefinitely; no default approval)
                            [ ] REJECT (state reason: ______________________)
Separate future acts:       production integration [ ] not authorized | launch [ ] not authorized
Owner name:                  ____________________________
Role:                        Project Owner
Date (UTC):                  ______________________
Signature:                   ____________________________
Actor ID:                    ____________________________  (= C5_OWNER_ACTOR_ID)
HMAC key commitment:         [ ] private 32+ byte hex key set via C5_OWNER_HMAC_KEY; never in files
```

## Verification checklist at signing time

- [ ] Every prereq box cites an existing file whose content includes a genuine reviewer/owner record (not AI-authored placeholders)
- [ ] All A-decisions explicitly marked
- [ ] Digest blanks filled from real computation at signing time
- [ ] Separate acts (integration/launch) left explicitly unauthorized
- [ ] Signed packet byte-digest recorded into `autonomous_agent/state/campaign5_authorization.json` creation notes with revocation ledger path noted

**This signature authorizes exactly one bounded C5 study operation. It does not authorize production integration, launch, or any holdout access. Separate explicit acts after prerequisites remain required.**
