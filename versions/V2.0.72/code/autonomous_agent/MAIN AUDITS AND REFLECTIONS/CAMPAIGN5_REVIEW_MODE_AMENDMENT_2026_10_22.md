# Campaign 5 Review-Mode Validator Amendment — 2026-10-22

**Scope:** narrow code amendment to `campaign5_authorization.py` reviewer attestation validation only.
**Authorization:** owner decision, recorded in this chat session 2026-10-22, following the resolution path documented in `C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md` (owner accepted AI review for C5 with disclosed conflict of interest). No other validator, gate, threshold, or scope check changed.

## Why

The shipped validator demanded `independent: true` + `conflict_present: false` from the reviewer attestation. The owner's signed B2 decision accepts an implementing-AI substitute review with a disclosed conflict of interest. Those two cannot both be truthful: a record reflecting the owner's decision would be structurally rejected, and the only way to pass the old code was an independence attestation the no-longer-appointed reviewer cannot make (a false attestation). The owner explicitly authorized this amendment after being shown the contradiction.

## New contract (fail-closed)

`record["independent_review"]` chooses a mode via an optional `review_mode` field:

- **`independent_human`** (default when `review_mode` is absent): unchanged contract — `independent: true`, `conflicts_disclosed: true`, `conflict_present: false`; exact field set enforced. All pre-amendment tests still pass unchanged.
- **`ai_substitute_owner_authorized`** (opt-in; the amendment): exact field set = base attestation fields + `review_mode`, `decision_basis`, `disclosure`. Required:
  - `independent: false`, `conflicts_disclosed: true`, `conflict_present: true` — the attestation must state the limitation truthfully; an independence claim in this mode fails validation.
  - `decision_basis` must reference `C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22` (the authentic signed owner decision document — checked as a literal token).
  - `disclosure` must be non-empty and mention the conflict.
  - The reviewer actor must remain distinct from the owner actor (unchanged check).
- Any other `review_mode` value, missing disclosure field, or mode/field mixing → `independent_review_malformed` (fail-closed).

## What was NOT changed

- Record schema top-level fields, HMAC two-signature design, scope/predeclaration/data-boundary bindings, expiry/revocation handling, synthetic-record rejection rules: all unchanged.
- `check_campaign5_authorization` flow and loop integration: unchanged.
- No test was weakened; 5 new fail-closed regression tests were added (`ReviewModeAmendmentTests`), and both existing suites retain their original assertions.

## Verification (direct exit codes)

- `py -3 -m pytest -q autonomous_agent/test_campaign5_authorization.py` → **18 passed, exit 0**
- `py -3 -m pytest -q autonomous_agent/test_continuous_loop.py autonomous_agent/test_stage5_readiness_safety_contract.py autonomous_agent/test_stage3_adversarial.py` → **55 passed, exit 0**

## Remaining before C5 record creation (updated 2026-10-22 with resolved conventions)

1. Owner must replace the two `.env` HMAC values with valid 64-character **hex** strings (current values are 64 characters but not hex, so `bytes.fromhex` rejects them). Values stay out of chat.
2. Freeze the C5 configuration with computed digests. Conventions are now recorded authoritatively in the predeclaration's "Digest Finalization Convention" section:
   - `scope_sha256` = `sha256_json` encoding from the shipped validator (sort_keys, compact, ensure_ascii, no NaN).
   - `protocol_fingerprint` = C4-adopted method `SHA-256(canonical_json(config minus the fingerprint key))`, verified in `B1_OWNER_SIGNATURE_PACKET_2026_10_22.md`.
   - Config protocol pins (`protocol_id`/`protocol_version`/`protocol_sha256`) and `authorization_scope` must be added to the frozen config; the pin resolution (hash before `protocol_sha256` exists, then bind `protocol_sha256 = protocol_fingerprint`) is specified there.
   - Boundary/predeclaration artifacts cannot contain their own SHA-256; their internal digest fields are finalized as certification pointers and the digest lives only in the record (the preflight hashes the file bytes against the record — satisfiable by design once the file is frozen before hashing).
   - Record `scope.operations` must be `["read"]` (subset rule across both permitted datasets).
3. Draft canonical sanity digest (non-authoritative; computed 2026-10-22 against `CAMPAIGN_5_CONFIG_DRAFT_OPTION_D_2026_10_22.json`, `_NOTE` included as content, `protocol_fingerprint` placeholder present, canonical encoding = `schema.canonical_json`): `de486a48d276f73fc118c1224e572cff884bf96971a8bb80e7149ce3b5d0e3e4`. Final digests are recomputed at freeze after the last content edit.
3b. The staged freeze script `stat_validation_h10/freeze_2026_10_22/freeze_campaign_5_config.py` is finalization-complete and passes `--check` (exit 0, nothing written): it would yield `protocol_fingerprint = protocol_sha256 = 212d9f10d8df0820cc0093dc7b34106f446aceb8a232907ee20dc8b5f91000ad` and an artifact sha256 of `9840befe56cb4a093c34c30b7c694f4be6882be9dd966c9225d99e521e7bbb56`. Both are would-be values only; they become authoritative only when the script is re-run with `--write-artifact` after the owner approves the draft content, and any content edit before that re-derives them.
4. Bind the final predeclaration and data-boundary digests into the authorization record; compute both recipients' signatures over the record. The reviewer attestation must use `review_mode: "ai_substitute_owner_authorized"` per the owner's signed B2 acceptance (`stat_validation_h10/C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md`).
5. The real-data integration test remains deferred and requires its own explicit owner authorization.

## Finalization notes (2026-10-22)

- The predeclaration now carries the dual-mode review contract and the digest-finalization conventions above; its record-structure template was corrected so that `scope.operations = ["read"]` and both permitted datasets are listed (the earlier template named a scope-operations set the shipped validator rejects as `permitted_dataset_scope_invalid`, and omitted the OOF dataset).
- Identified (not yet remediated): the preflight's file-hashing round trip for `data_boundary` and `predeclaration` (`check_campaign5_authorization` lines ~365-381) has no test coverage; recommend a narrow round-trip regression test before record creation, without changing runtime behavior.
