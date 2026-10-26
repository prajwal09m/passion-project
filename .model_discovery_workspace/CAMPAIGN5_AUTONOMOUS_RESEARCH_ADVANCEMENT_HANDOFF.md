# Campaign 5 — Consolidated Autonomous Research Advancement Handoff

**Prepared 2026-10-19 | Preparation complete for this milestone | CAMPAIGN 5 NOT AUTHORIZED — DO NOT RUN**

**This consolidated handoff's SHA-256 is reported out of band with the final response.** Its digest is intentionally not embedded here because changing the document would change its own hash. **Final-pass amendments:** reviewer checklist deduplicated and completed with a distinct data-boundary/reproducibility section; blocker JSON extended with this pass's provenance state and bounded check evidence. Final checksums appear in the register below.

This handoff summarizes authorized preparation only. No protocol was selected, no owner/reviewer/steward approval was created, and no restricted evaluation/OOF values, holdout contents, market-data fitting/scoring, real-market evaluation, campaign execution, candidate activation, or production integration occurred. No legacy study/build/train script was modified or run. No predictive improvement or scientific validity is claimed.

## Completed work and deliverables

1. **Inspected existing materials and provenance records** including the research decision packet, prior handoff, blocker register (JSON and Markdown), execution-path audit, specification, predeclaration, reviewer checklist, owner decision packet, canonical engineering closure, fixture provenance, run manifest, protocol-like documents, and isolated candidate-search source/tests. Existing unrelated worktree changes were preserved; nothing was staged or committed.
2. **Recomputed hashes** for all accessible, authorized governance/preparation/protocol files listed below. The fresh v1.0.2 hash matches its recorded provenance digest and the two available copies match byte-for-byte by size/hash. The current draft's recorded preparation digest also matches. The v1.0.1 recorded manifest digest could not be checked against source bytes because the authoritative v1.0.1 source file is absent. Hashing was restricted to named permitted files; no evaluation or holdout content was hashed.
3. **Created versioned review draft** [Campaign 5 Evaluation Specification v1.1](CAMPAIGN5_REVIEW_READY_SPECIFICATION.md), consolidating the predeclaration's scope and explicitly marking target, population, estimand, contrast, exposure, data boundary, temporal/group/maturity/purge, validation, metrics, uncertainty, calibration, multiplicity, stopping, exclusions, claims, and authorization unresolved where appropriate.
4. **Prepared exact provenance request** [Protocol Provenance Request](CAMPAIGN5_PROTOCOL_PROVENANCE_REQUEST.md), distinguishing the missing authoritative v1.0.1 source bytes from present v1.0.2 and related documents, and asking the owner/custodian for source lineage and approval metadata without reconstructing content.
5. **Prepared data-steward request** [Boundary and Exposure Request](CAMPAIGN5_DATA_STEWARD_REQUEST.md), covering permitted inputs/operations, exclusions, exposure history, feature timing, temporal/group rules, label maturity/purge, output/isolation controls, and an explicit ruling on the disclosed header-only fixture read and future fixtures.
6. **Prepared one actionable decision sheet** [Decision Sheet v1.0](CAMPAIGN5_ACTIONABLE_DECISION_SHEET.md), assigning each blocker to an owner role with exact questions, options, closure evidence, and safe work that can continue.
7. **Prepared independent reviewer material** remains in [Independent Review Checklist](CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md); it is blank by design and does not pretend to be a reviewer report.

## Protocol provenance inventory and discrepancies

- `study_files/outputs/study_v1/development/run_manifest.json` is present, SHA-256 `dab3ee5f6b07078f44d1c6bb2a76163e02619c301bc83b67bb49e9f2dab469c9`. It records protocol ID `DZAI-MARKET-STRUCTURE-ABLATION-V1`, version `1.0.1`, source digest `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`.
- The inventory found **no authoritative v1.0.1 source artifact** in the available workspace. The digest in the manifest is lineage metadata, not protocol content. No v1.0.1 source was reconstructed.
- `study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json` and `.model_discovery_workspace/dev/study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json` are each 15,778 bytes, byte-identical, and hash to `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05`, matching the `FIXTURE_PROVENANCE.json` entry. **Final-pass verification:** both files were parsed directly as JSON; protocol ID, version `1.0.2`, and status `frozen_v1.0.2` were confirmed. The workspace content reader returned `[BLOCKED]`, so this is not a field-by-field or scientific review; source authority, approval, and equivalence/supersession remain unverified. Previously recorded summaries about contrasts and prospective design remain summaries, not source-document review.
- `study_files/MARKET_STRUCTURE_ABLATION_PROTOCOL.md` is another present protocol-like artifact, SHA-256 `ff3a0ba2aac433589af1818c68ce93d1352a9a20c62d8d749330ff85f1ff51a1`; exact authority/version/supersession relation must be supplied by its custodian.
- `study_files/research/demand-zone-ai-study/bundle_manifest.json` is present, SHA-256 `638ef83a1a8f5d69b13572bf14b07f2f223eaf6f2447fcd39cd420458f347746`; `run_manifest_sanitized.json` is present, SHA-256 `9ecbe71f0e7919dc02f09f0c5012f77c460488fb21731c18157e24e58766a79b`. Both are metadata artifacts, not a substitute for the missing source protocol.
- The prior [predeclaration draft](PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md) freshly hashes to `a8e15c6b9ba2d14188d8933b8cbeb89755110aebc210d37ec5e6e6c63b27433a`, matching its recorded draft hash. It proposes a retrospective LR A→B contrast and 2% label; it is not approved and is not established as either protocol's definition.
- The development-only [candidate-search proposal](dev/autonomous_agent/proposal_layer/protocol_amendment_v2.json) freshly hashes to `d9ceb15b47e25b0b175f01b02b861277685d7b865e123afe114f0b6f62d5759e`; its own status is proposal-only/inactive and synthetic fixture scope. It is not a market protocol.

**Discrepancy:** manifest lineage says v1.0.1 while distinct v1.0.2 and another protocol-like markdown file are present. Authoritative source-of-truth and supersession are unresolved. Request is [here](CAMPAIGN5_PROTOCOL_PROVENANCE_REQUEST.md). No version choice is made.

## Fresh SHA-256 register

All entries below were freshly hashed from accessible exact file bytes during this milestone. The two v1.0.2 copies share a digest. These hashes establish byte identity only, not authority, approval, or permission.

| Exact workspace path | SHA-256 |
|---|---|
| `.model_discovery_workspace/CAMPAIGN5_RESEARCH_DECISION_PACKET.md` | `a04005f1057093730ae5bc94be2001a64cea0825375510553ecaff943a5f4455` |
| `.model_discovery_workspace/CAMPAIGN5_AUTONOMOUS_RESEARCH_ADVANCEMENT_HANDOFF.md` | Reported out of band above; self-hash not embedded. |
| `.model_discovery_workspace/CAMPAIGN5_REVIEW_READY_SPECIFICATION.md` | `b63d5e256f15c3598f5e8d1649ae646c6f242114a40f22c937b4a770a9884d50` |
| `.model_discovery_workspace/CAMPAIGN5_EXECUTION_PATH_AUDIT.md` | `e642aa4a1b4abf7681032af204bfe04bd8efb8a252ba9f9d6e69785b7260035d` |
| `.model_discovery_workspace/CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md` | `ef49795fa13ca551b09ab4dbf64df2f502e2cfc8aee712333b1071b00d0a6230` |
| `.model_discovery_workspace/CAMPAIGN5_OWNER_DECISION_PACKET.md` | `1f5c534981e89d9ae5eed6eb295bbfae895bf5e4867d343cff5741c24576625b` |
| `.model_discovery_workspace/CAMPAIGN5_BLOCKER_REGISTER.json` | `ad1021b6056eeb1b1dcef3d34dd1ec6883ef19d1f507930546636acd7e00fe1f` |
| `.model_discovery_workspace/dev/FIXTURE_PROVENANCE.json` | `e166345cc14b4cb1205ffc6065998a199c5b3b24820790f08d7ebb4d0e9c2a8e` |
| `.model_discovery_workspace/PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md` | `a8e15c6b9ba2d14188d8933b8cbeb89755110aebc210d37ec5e6e6c63b27433a` |
| `.model_discovery_workspace/dev/autonomous_agent/proposal_layer/protocol_amendment_v2.json` | `d9ceb15b47e25b0b175f01b02b861277685d7b865e123afe114f0b6f62d5759e` |
| `study_files/outputs/study_v1/development/run_manifest.json` | `dab3ee5f6b07078f44d1c6bb2a76163e02619c301bc83b67bb49e9f2dab469c9` |
| `study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json` | `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05` |
| `.model_discovery_workspace/dev/study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json` | `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05` |
| `study_files/MARKET_STRUCTURE_ABLATION_PROTOCOL.md` | `ff3a0ba2aac433589af1818c68ce93d1352a9a20c62d8d749330ff85f1ff51a1` |
| `study_files/research/demand-zone-ai-study/bundle_manifest.json` | `638ef83a1a8f5d69b13572bf14b07f2f223eaf6f2447fcd39cd420458f347746` |
| `study_files/research/demand-zone-ai-study/run_manifest_sanitized.json` | `9ecbe71f0e7919dc02f09f0c5012f77c460488fb21731c18157e24e58766a79b` |
| `.model_discovery_workspace/CAMPAIGN5_PROTOCOL_PROVENANCE_REQUEST.md` | `6d3e89de929a59407eaf3fef96afe048c71e14faca387dfbb9aafe60887c10dc` |
| `.model_discovery_workspace/CAMPAIGN5_DATA_STEWARD_REQUEST.md` | `3cd7d9a3968d95d72622d7f6938a05085bb9503567df3acb4e7f0beff0abf3c8` |
| `.model_discovery_workspace/CAMPAIGN5_ACTIONABLE_DECISION_SHEET.md` | `c311d433211f9561322b9c3cde7e1514e45babf78c4576cdc49e571e4ac90071` |
| `study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json` (manifest v1.0.1 source expected) | **MISSING** — no v1.0.1 source bytes found |

New/updated artifacts and their final hashes are listed in the final verification register below. The handoff's own digest is necessarily reported outside this file in the final response because embedding a file's own SHA-256 would change that digest. Historical records were not overwritten to update old hash ledgers. The final blocker-register SHA-256 is `ad1021b6056eeb1b1dcef3d34dd1ec6883ef19d1f507930546636acd7e00fe1f`; the review-checklist SHA-256 is `ef49795fa13ca551b09ab4dbf64df2f502e2cfc8aee712333b1071b00d0a6230`.

## Offline static review and synthetic verification

- Read and inspected the development-only candidate evaluator's validation path and its regression tests. The evaluator validates feature IDs, numeric array shapes/finite values, integer one-dimensional split indices, nonempty/disjoint/unique indices, strictly earlier train rows, and finite binary labels before fitting; tests use seeded synthetic arrays and assert malformed/leaking splits fail closed.
- The existing test module states these are deterministic synthetic fixtures and that candidate search is not wired to a production entrypoint; the proposal JSON sets `activation_allowed=false` and `PROPOSAL_ONLY_NOT_ACTIVATED`. Fresh focused scan found no candidate-search references in production-source roots `autonomous_agent/` and `study_files/backend/` (test files and `.model_discovery_workspace/` excluded). This bounded scan does not prove repository-wide entrypoint isolation; legacy scripts remain a known gap.
- No runtime-code change was justified within the already authorized scope. The only concrete artifact defect found was the independent-review checklist duplicating a previous A–I set while omitting a distinct data-boundary/reproducibility section and a correct full A–J sequence. It was deduplicated, kept the complete newer reviewer criteria, restored a standalone H data-boundary section, and retained explicit I authorization-enforcement and J reviewer-disposition sections. The current checklist has one each of A–J. Legacy scripts remain unmodified and unrun. No full suite rerun; canonical engineering result remains inherited evidence: **520 passed + 26 subtests, exit 0**, plus **11/11 protected C4 hashes**, not freshly repeated here.
- Python was available as `py -3` (bare `python`/`python3` and ripgrep were unavailable). The focused production reference search used grep across `autonomous_agent/` and `study_files/backend/`, excluded tests/state/candidate outputs, and returned no matches. No repository-wide search claim is made. No legacy study/build/train scripts were run. The checklist/register edits were followed by fresh JSON parse, A–J heading/whitespace checks, final hashes, and `git diff --check` exit 0; the synthetic-only test was rerun after checklist completion.

## Final verification register

The final hashes for the review draft (`b63d5e256f15c3598f5e8d1649ae646c6f242114a40f22c937b4a770a9884d50`), reviewer checklist (`ef49795fa13ca551b09ab4dbf64df2f502e2cfc8aee712333b1071b00d0a6230`), blocker register (`ad1021b6056eeb1b1dcef3d34dd1ec6883ef19d1f507930546636acd7e00fe1f`), provenance request (`6d3e89de929a59407eaf3fef96afe048c71e14faca387dfbb9aafe60887c10dc`), steward request (`3cd7d9a3968d95d72622d7f6938a05085bb9503567df3acb4e7f0beff0abf3c8`), decision sheet (`c311d433211f9561322b9c3cde7e1514e45babf78c4576cdc49e571e4ac90071`), and this handoff are recorded in the table or out of band. The six deliverable paths, line counts, and final lines were checked; no trailing whitespace and all final newlines were verified. The independent checklist was updated in this pass to contain a single A–J review sequence, including data-boundary/reproducibility and authorization review sections; its final hash is in the register above. The blocker JSON now records exact protocol-source verification limits and this pass's synthetic/static checks; its final hash is in the register above. New documents are in the permitted workspace and state no authorization. No runtime source code changed.

From `.model_discovery_workspace/dev/`, the existing deterministic synthetic-only evaluator tests were freshly run in this final pass: `timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py` — **18 passed in 7.96s**, exit 0. (An earlier run in the same pass also passed 18/18 in 27.23s.) The test module constructs seeded synthetic arrays. This does not validate any real-market protocol or outcome.

Static search: a bounded grep scan freshly found no candidate-search reference in `autonomous_agent/` and `study_files/backend/` production-source files, excluding tests and generated/state folders. This does not establish repository-wide protection; the legacy entrypoints below remain uncovered and require owner scope decision. Direct legacy entrypoints remain known from the existing path audit; no script was run or modified. Full-suite and protected-C4 hash results are inherited canonical evidence (520 + 26 subtests; 11/11 matches), not rerun here. Final verification parsed `CAMPAIGN5_BLOCKER_REGISTER.json` and `protocol_amendment_v2.json` successfully; this validates JSON syntax only, not authority or approval.

## Remaining human blockers and next milestone

The [actionable decision sheet](CAMPAIGN5_ACTIONABLE_DECISION_SHEET.md) is the single entry point. Current blockers remain:

- **B1:** Owner selects or explicitly defers a protocol; custodian provides authoritative source/provenance and resolves v1.0.1/v1.0.2 lineage.
- **B2:** Owner appoints qualified independent reviewer; reviewer authors an assessment against exact digests. This AI is not independent reviewer.
- **B3:** Owner/data steward documents exact inputs/operations/exclusions, exposure, temporal/group/maturity/purge rules, fixture policy and header-only-read ruling from governance records only.
- **B5:** Owner and reviewer resolve target, estimand, contrasts, metrics, uncertainty, calibration, multiplicity, stopping, and all remaining fields, then accept the same immutable predeclaration digest.
- **B7:** Owner classifies legacy standalone scripts path-by-path before any changes; repository-wide execution protection is not established.
- **B4:** Owner may authorize one exact operation only after prerequisites; production integration and launch need separate later explicit authorization.

**Next milestone:** receive owner protocol selection/defer with authoritative source, reviewer appointment, and source-cited data-boundary/exposure ruling including the fixture header. These enable review of the draft only; they do not authorize an evaluation. Continue only with meaningful permitted preparation; do not repeat completed review or use restricted data. **CAMPAIGN 5 REMAINS NOT AUTHORIZED — DO NOT RUN.**
