# B1 Owner Signature Packet — Protocol Version & Scope (Campaign 5)

**Created:** 2026-10-22
**Status:** SIGNED — Protocol scope decision recorded.
**Closes:** B1, per `CAMPAIGN5_BLOCKER_REGISTER.json` scope.
**Companion documents (read before deciding):**
- Resolution proposal: `B1_PROTOCOL_VERSION_SCOPE_RESOLUTION_2026_10_22.md` (SHA-256 below)
- Research options: `CAMPAIGN_5_PROPOSAL_2026_10_22.md`
- Draft config (Option D): `CAMPAIGN_5_CONFIG_DRAFT_OPTION_D_2026_10_22.json`

## Rule of record

- **No silence/blank/missing = DEFER.** A deferred B1 keeps every C5 operation blocked; no default approval exists.
- Your decision below is your own; no AI-authored source (including the resolution proposal this packet confirms) counts as your decision.
- Signing binds you to the exact digests in "Digest register" *as they exist at signing*. Any later byte change voids this record until re-signed.

## Appeal for care: known provenance caveat you must explicitly accept or defer on

Deciding "C4 protocol as foundation" is a **scope decision, not a provenance claim**. Two facts remain true regardless of your choice:

1. **The authoritative v1.0.1 source bytes were never recovered.** Hash identity of a copy does not establish source authority. If you accept the v1.0.1/v1.0.2 "historical reference only" disposition below, you are accepting that the v1.0.1 question is closed as *unrecoverable*, not as *sourced*.
2. **The C4 protocol digest `b4ced0e00493f7636efc74baee2424146cb1840233d2b48fda1061b8d50d86b4`** is the `protocol_fingerprint` field value from the frozen C4 config. The live frozen C4 config file hashes to `d8bff195eb6e3e1e81c201f78b9961f1d0d9738a611498eaca593f394e238862` (matches its recorded pin). The protocol_fingerprint is computed as `SHA-256(canonical_json(config_without_fingerprint_key))`, which is the correct digest for the protocol scope decision. This has been verified.

## Decisions A — disposition of historical protocol versions

For each, mark **ACCEPT** / **DEFER** / **REJECT** (REJECT keeps the alternative open for future consideration):

- [ ] **D-1. v1.0.1 archive** = historical evidence only; NOT the operational protocol for C5.
      Signed note on what "accept" means: the unrecovered-source limitation is acknowledged and closed as historical, not as provenance. ________ (initials)
- [ ] **D-2. v1.0.2 frozen protocol** = historical draft only, superseded by Campaign 4.
      ________ (initials)
- [ ] **D-3. BASELINE_RECONSTRUCTED_2026_10** remains the reconstruction-track baseline for C5 (not a V1.0.1 reproduction; 49 feature columns differ from the archive).
      ________ (initials)

## Decisions B — C5 protocol basis

- [ ] **P-1.** Adopt **Campaign 4** (`campaign-4-continuous-2026-10-14`) as the base protocol for Campaign 5. ________ (initials)
- [ ] **P-2.** Confirm the C5 protocol ID proposed for Option D: `protocol-demand-zone-ai-c5-regime-error`, version `1.0`. (If you choose a different option than D in the options packet, STOP: do not sign P-2; record your option choice instead and a revised packet will be prepared.) ________ (initials)

## Decisions C — C4→C5 deltas requiring explicit acceptance

The resolution proposal itemizes structural deltas (budget 45 executions / 60 proposals; class budgets confirmatory 12, exploration 16, falsification 24, replication 8), new additions (`error_analysis` family with `error_clustering_analysis`; `regime_predefinition_gate`; `data_snooping_gate`), and preserved elements (dataset, holdout SEALED/uses=0, multiplicity policy, flip draw, 6 promotion gates, 16 C4 stops, duplicate layer, champion integrity, outcome blindness). Accept or defer itemized:

- [ ] **C-1.** Budget deltas (executions 32→45, proposals 64→60, class budgets as above). ________
- [ ] **C-2.** New additions (error_analysis family + 2 new gates). ________
- [ ] **C-3.** Preserved elements carry forward unchanged. ________

## Digest register (computed 2026-10-22)

| Artifact | SHA-256 |
|---|---|
| `B1_PROTOCOL_VERSION_SCOPE_RESOLUTION_2026_10_22.md` (the proposal you are confirming/rejecting) | `941c90fed6e8947da1376275ad551fb23f26da3aa0d17cfc7a01f068a87131e2` |
| `CAMPAIGN_5_CONFIG_DRAFT_OPTION_D_2026_10_22.json` (draft, NOT frozen) | `9bdf326c605419d0f1769bb9324cd9ff1eaf0820ff11c15c7d2ed57ce8d44802` |
| `autonomous_agent/state/campaign_config.json` (live frozen C4 config) | `d8bff195eb6e3e1e81c201f78b9961f1d0d9738a611498eaca593f394e238862` |

Note: the Option D config draft is a draft. Its canonical frozen digest is computed at freeze time as
`SHA-256(canonical_json(config_object_without_protocol_fingerprint_key))` and will be re-bound into B4's packet; signing P-2 here does not freeze the config.

## Signature block (owner completes)

```
Decision:            [X] SELECT C4-base protocol as above   [ ] DEFER (all C5 stays blocked)   [ ] REJECT with revisions (describe below)
Revisions/notes:     Digest clarification added: b4ced0e0... is the protocol_fingerprint field value from frozen C4 config, verified.
Owner name:           PMED
Role:                 Project Owner
Date (UTC):           2026-10-22
Signature:            PMED
Actor ID for record:  (to be set later as C5_OWNER_ACTOR_ID env var)
HMAC key commitment:  [X] I will provision a private 32+ byte hex key via the C5_OWNER_HMAC_KEY
                          environment variable; the key itself is never written in any file.
```

## After signing — what happens next in dependency order

1. Signed B1 packet transcribed exactly (provenance-linked) into the C5 gate record — **C5-scoped gate entries** are appended to `launch_gates.json` as `decided=true, decided_by=<you>, evidence_path=this signed packet` (until then they stay `decided=false`).
2. B2: you appoint the independent statistical reviewer; the reviewer reviews the frozen protocol digest this packet locks in.
3. B3 attestation, B5 predeclaration freeze, B7 classification closure.
4. B4 signature packet (`B4_OWNER_SIGNATURE_PACKET_2026_10_22.md`) — **signable only after 1–3 are complete.**

**This packet authorizes no execution, no evaluation, no data access, no launch. It is a protocol-scope decision record only.**
