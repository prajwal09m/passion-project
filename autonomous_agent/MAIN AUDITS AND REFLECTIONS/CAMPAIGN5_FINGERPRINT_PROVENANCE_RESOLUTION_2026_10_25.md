# Campaign 5 Protocol Fingerprint Provenance Resolution

**Date**: 2026-10-25
**Scope**: continuation task 1 (resolve protocol-fingerprint provenance). This
report reproduces what is reproducible, documents exactly what can and cannot
be established from surviving evidence, and adds fail-closed regression tests
plus a verify-only utility. Nothing was overwritten, re-signed, or redefined
to make verification pass.

## 1. The exact expected value and its claimed chain

| Chain node | Artifact | Value / content |
| --- | --- | --- |
| Pinned value | `autonomous_agent/state/campaign_config.json` | `protocol_fingerprint` = `protocol_sha256` = `553ac77f65b6b8afee852159fe654ea25b0116e490860e3e3153af937ce44327` |
| Signed owner/reviewer decision | `autonomous_agent/state/campaign5_authorization.json` (HMAC, owner PMED / reviewer KMED, mode `ai_substitute_owner_authorized`) | `protocol.sha256`, `predeclaration.protocol_sha256`, `owner_approval.protocol_sha256`, `independent_review.protocol_sha256` — all `553ac77f…` |
| Signed-record authenticity (re-verified 2026-10-25) | rotated owner/reviewer keys in `.env` | `validate_authorization(record, scope, keys)` returns **zero errors** |
| Canonicalization procedure | `CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md` § Digest Finalization Convention | `F = SHA-256(canonical_json(config minus protocol_fingerprint key))`, computed while `protocol_sha256` does not exist; then `protocol_sha256 = protocol_fingerprint = F` |
| Canonicalization implementations | `proposal_layer.schema.canonical_json`, `freeze_campaign_5_config.canonical_json`, `campaign5_authorization.canonical_bytes` | byte-identical for these configs (pinned by regression test) |
| Hashing inputs | the full frozen-config content (including `_FREEZE_STATUS`, `authorization_scope`, `notes`), minus the identity keys | see §3 |
| File-bytes pin | `autonomous_agent/state/campaign_config.sha256` sidecar | `29c905aaf25012cdd20bf21270821f81f5a8e24b46b4a51163d2c65e2e9124a5` — matches the live file bytes |
| Execution-time verification at launch | `campaign5_authorization.check_campaign5_authorization` | requires config `protocol_sha256` == record `protocol.sha256` ( succeeded: both `553ac77f…` ); **never recomputes F from content** |

## 2. What DOES reproduce (controls)

Control pins were recomputed 2026-10-25 with the exact recorded convention
(config minus `protocol_fingerprint`; `protocol_sha256` absent from those
configs, matching "before `protocol_sha256` exists"):

| Control | Artifact | Pinned | Recomputed | Result |
| --- | --- | --- | --- | --- |
| C4 capacity refreeze | `stat_validation_h10/freeze_2026_10_15/CAMPAIGN_4_CONFIG_FROZEN_2026_10_15.json` | `49d73f67…` | `49d73f67…` | **reproduces** |
| C4 final archive (C5 parent lineage) | `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16/campaign_config.json` | `b4ced0e0…`, file bytes `d8bff195…` | `b4ced0e0…` | **reproduces** |
| Record scope digest | `campaign5_authorization.json` `scope` | `scope_sha256` = `3f711e5d…` | `sha256_json(scope)` = `3f711e5d…` | **reproduces** (validator encoding) |

The method itself is therefore sound and mechanically reproducible — the
canonicalization and the hashing convention used by the C4 freezes are pinned
regressively in `autonomous_agent/test_protocol_fingerprint.py`.

## 3. What does NOT reproduce (the C5 defect, precisely)

For the live C5 config, `F` per the recorded method:

| Input state | F (recompute) | Match to `553ac77f…`? |
| --- | --- | --- |
| Live content, strictly minus the two identity keys (convention-faithful) | `b20a4d9b147b17af5055e4531b392fc3f1652381fd3b7e28fffa7a1c0db2cff5` | **no** |
| Live content minus also `_NOTE` (reconstructing the pre-2026-10-23 additions) | `8527f1b4489b8c99313b2482c391752236f866bc52215f2fbb266af8fb532d11` | **no** |
| `_FREEZE_STATUS` only at freeze time (before `completions_2026_10_23` / provenance note / `authorized_by`) | not reproducible: the original freeze-time `_FREEZE_STATUS` text does not survive | n/a |
| Reconstruction from draft + current freeze script (`finalize(draft)`, both scope variants) | `0cb856bc511e1457556ff7f963ce7eca842ff17b53c13e269f8cc76340175cee` | **no** |
| Prior ~40-variant sweep recorded 2026-10-23 (owner decision, `documented-and-proceed`) | `7a479ea2…` vs then-content | **no** |
| Encoding variants tried 2026-10-25 beyond the prior sweep: `schema.canonical_json`, validator `canonical_bytes` (`ensure_ascii=True/False`, `allow_nan`), indent-2 payload bytes with LF, space separators, insertion-order dumps, `_NOTE`/`notes`/`authorization_scope`/`_FREEZE_STATUS` subset trims, historical `protocol_sha256` placeholder values | all tested | **no hit** |

**Statistical context on the misses**: across every surviving config state and
~100 faithful-but-plausible content/encoding variants, `553ac77f…` and the
earlier pin `be2e6d34…` (quoted in `CAMPAIGN_5_FINALIZATION_SUMMARY_2026_10_22.md`)
have no preimage among them. Finding one wrong variant matching would be
suspicious in itself; the consistent result across two independent sweeps on
two dates supports "the pinned value was not computed by this method over any
surviving content state", not "the sweep is incomplete".

## 4. What CAN be established (confidence levels)

1. **The pin is uniformly attested and authentic.** The same value sits in all
   four digest-bearing blocks of the authorization record, the record's two
   HMAC signatures verify under the owner-authorized rotated keys (zero
   validator errors, re-verified 2026-10-25), and the signed owner decision of
   2026-10-22 (`C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md`) plus the
   `documented-and-proceed` decision of 2026-10-23 own the protocol — i.e.,
   the *authorization* of the frozen C5 protocol is genuine; only the
   *recomputability* of its digest fails.
2. **The live artifact pins hold.** Config file bytes = sidecar = `29c905aa…`;
   predeclaration artifact = `845d4bee…`; data boundary = `5b661ad5…` (both
   verified by the shipped preflight). Unrelated digest machinery works.
3. **The canonicalization and method are correct** — proven by the two C4
   control reproductions; the convention cannot be blamed for the mismatch.
4. **The value changed once, undocumented.** `CAMPAIGN_5_FINALIZATION_SUMMARY_2026_10_22.md`
   records the record signed on 2026-10-22 with all pins `be2e6d34…`; the
   re-signed record of 2026-10-23 carries `553ac77f…`. An intermediate
   "external re-finalization" (referenced in `record_resign_2026_10_23.py`'s
   docstring as having "propagated the same value … into the owner/review
   blocks") replaced the pin in both the config and the record. That step's
   actor, method, and hashed input are **not recorded anywhere in this
   checkout**, and no frozen config artifact exists in
   `stat_validation_h10/freeze_2026_10_22/` (only scripts; no
   `CAMPAIGN_5_CONFIG_FROZEN_2026_10_22.json`), so the original frozen C5
   content state cannot be recovered locally.

## 5. What CANNOT be established

* The preimage content state for `553ac77f…` (or `be2e6d34…`) under the
  recorded method.
* Whether the original freeze-time fingerprint was ever computed over the
  content the freeze script would produce today (the draft, the script, and
  the installed config all differ from what their current bytes imply).
* The identity and method of the 2026-10-23 pin replacement
  (`be2e6d34… → 553ac77f…`).
* Whether `_NOTE`, `notes`, or later `_FREEZE_STATUS` edits were present when
  F was computed.

## 6. Why this must not be "fixed" by recomputation

The predeclaration's fail-closed contract binds the record signatures to a
protocol pin; recomputing F and writing it into the config would (a) rewrite
those artifacts without authority (config is `immutable: true`), (b) require
re-signing the record — a signature-regeneration this audit is forbidden
from performing — and (c) convert a *provenance defect* into a *naively
papered-over* state. The defect therefore remains open, exactly as the owner
decision of 2026-10-23 recorded. The truth-preserving deliverables instead:
era-pinned regression tests (`test_protocol_fingerprint.py`), a verify-only
utility (`autonomous_agent/protocol_fingerprint.py`), and this report.

**A future predeclaration should add one control**: require that a recompute
of the method over the frozen content **at freeze time** be printed in the
owner decision record itself, so a later session can re-verify without
needing the (necessarily absent) original frozen artifact bytes.

## 7. Regression tests added

`autonomous_agent/test_protocol_fingerprint.py` (9 tests, all passing
2026-10-25 on Python 3.13/pytest, see §Test evidence in the final report):

1. canonicalization agreement across the three shipped implementations;
2. convention-definition equivalence (hashing is invariant to whether
   `protocol_sha256` is excluded, since the convention computes before it exists);
3. C4 capacity control reproduces;
4. C4 archive control reproduces;
5. C5 live state is *exactly* the documented defect (era-pinned file-bytes
   `29c905aa…`, recompute `b20a4d9b…`, pin `553ac77f…`, recompute ≠ pin) —
   byte drift of the live config or a canonicalization change now fails
   loudly;
6. the era-record classification table verifies all three known configs
   (two `reproduced`, one `documented_defect_mismatch`);
7. verify is write-free and fail-closed on a mutated config (reports
   `unexpected_mismatch`, repairs nothing);
8. missing file → `unavailable` → CLI exit 1;
9. the era pin table itself cannot drift from the artifacts it names.

## 8. Verdict

| Claim | Support |
| --- | --- |
| The C5 protocol *is* the owner-authorized one (signed record, verifying signatures, matching pins everywhere) | strong |
| The pin `553ac77f…` was produced by the recorded method over the frozen C5 content | **not supported — open defect; no preimage exists in surviving evidence** |
| The method, canonicalization, and non-protocol digest machinery are correct | strong (C4 controls) |
| Pin replacement `be2e6d34…→553ac77f…` happened in an undocumented 2026-10-23 "external re-finalization" | strong (contradictory dated docs; actor/method unknown) |

## 9. Evidence pointers (paths + line refs)

* Recorded convention: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md` ("Digest Finalization Convention").
* Signed record: `autonomous_agent/state/campaign5_authorization.json` (protocol block, predeclaration, owner_approval, independent_review).
* Re-sign tool: `stat_validation_h10/freeze_2026_10_22/record_resign_2026_10_23.py`.
* Launch doc: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_LAUNCH_RECORD_2026_10_23.md` §7 (documented defect).
* Earlier owner decision: `stat_validation_h10/C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md`.
* Verify utility: `autonomous_agent/protocol_fingerprint.py`.
* Tests: `autonomous_agent/test_protocol_fingerprint.py`.
