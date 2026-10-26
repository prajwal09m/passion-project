# Campaign 5 Blocker Register — Readiness Preparation v1.0

**Status: PARTIALLY COMPLETE — CAMPAIGN 5 NOT AUTHORIZED, NOT READY TO LAUNCH.**
**Prepared:** 2026-10-18. **Scope:** document-only governance preparation and isolated development tests. This register authorizes no market-data analysis, campaign integration, campaign execution, protocol activation, or holdout access.

## Evidence classes

- **VERIFIED FACT**: directly supported by the cited governance or development artifacts, or by a command run in this preparation session.
- **PROPOSAL**: a possible plan for the owner/reviewer to accept, reject, or revise; it is not active.
- **ASSUMPTION**: a premise that has not been established by authoritative evidence.
- **UNRESOLVED**: not determinable within the no-evaluation-data boundary or without an authorized owner/reviewer decision.

No evaluation or OOF rows/predictions, sealed holdout contents, or market metrics were read for analysis, fitting, or scoring in this phase. The coordinated full dev suite did include the manifest-documented scaffolder test that read only the staged development event-table header; no rows were consumed. Whether this was within the permitted boundary remains unresolved for the owner/data steward. Existing manifests and governance documents were used as metadata references. The allowed working area is `.model_discovery_workspace/` and its isolated `dev/` fixtures; protected paths are itemized in the [integrity audit](CAMPAIGN5_FINAL_INTEGRITY_AUDIT.md).

## Status vocabulary

`OPEN` = action identified and not started/closed. `IN PROGRESS` = an artifact is prepared but required decision/evidence remains. `BLOCKED` = cannot proceed under current authorization or information boundary. `VERIFIED CLOSED` = required evidence exists and has been independently checked. B6 (the complete development-suite run only) is VERIFIED CLOSED; B1–B5 and B7 remain open/blocked.

## Blockers

### B1 — Protocol version and scope

- **Status:** BLOCKED.
- **Exact requirement:** Before any Campaign 5 proposal generation, fitting, scoring, measurement, or integration, identify exactly one protocol version and immutable digest. Enumerate every proposed difference from frozen Campaign 4 rules, classify which are editorial/engineering versus scientific/policy changes, and obtain the approvals required by the governing records. Do not choose the protocol for the owner.
- **VERIFIED FACT / evidence:** No Campaign 5 config or Campaign 5 gate record is identified in the C4 Next-Stage Readiness Report. C4 is closed and its frozen rules are held in the C4 freeze record/config; Campaign 4 used v1.1.0 measurement primitives and frozen quota/replication policy. Candidate search v2 is explicitly `PROPOSAL_ONLY_NOT_ACTIVATED`, with owner and independent review pending (`.model_discovery_workspace/dev/autonomous_agent/proposal_layer/protocol_amendment_v2.json`). The real-market predeclaration itself records a conflict between manifest v1.0.1 and working protocol v1.0.2 and explicitly does not select between them.
- **Why it matters:** Protocol-version ambiguity makes the estimand, eligible candidate universe, split/metrics, multiplicity, and authorization scope non-reproducible; unapproved expansion can alter selection and evidentiary claims.
- **Decision/artifact required:** Owner-selected Campaign 5 protocol and scope, an exact byte digest, a line/item-level C4→C5 change table, and explicit disposition of each change. Any scientific or governance delta requires a versioned amendment; independent statistical review required for inferential changes.
- **Responsible role:** Project owner decides scope/version; independent statistical reviewer assesses scientific changes; implementer records but does not decide.
- **Closure evidence:** Written owner decision with exact protocol name/version/SHA-256; reviewer assessment naming same digest; accepted/rejected/deferred row for every difference; tests/checks proving production entrypoints remain unchanged until separately authorized.
- **Dependencies / consequences:** Blocks B2–B5 final approval, candidate-generator activation, campaign config, integration, and all launch steps.
- **Change-by-change comparison (verified status):** (1) existing Campaign 4 protocol and frozen configuration: existing historical baseline, not proposed for automatic inheritance; (2) candidate search v2 model/feature universe: new development proposal, not part of C4; owner + independent review required; (3) quota floor/replication-cap/evidence-key changes in Phase 3 amendment: optional, not activated, owner/reviewer approval required; (4) measurement / multiplicity / target / split changes: not proposed as defaults; any difference must be explicitly identified and reviewed; (5) C5 campaign integration/launch gates: no C5 record/config exists in inspected readiness artifact; do not infer permission from C4 records or any machine `READY` output.

### B2 — Independent statistical review

- **Status:** BLOCKED.
- **Exact requirement:** A non-implementing, appropriately independent statistical reviewer must review the exact proposed C5 protocol, target/estimand, assumptions, temporal design, group structure, multiplicity, uncertainty, selection, stopping, and boundaries, then provide a traceable written opinion and sign-off evidence.
- **VERIFIED FACT / evidence:** `stat_validation_h10/D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md` discloses the reviewer was the implementing AI and that this is not personnel-independent. `H10_OWNER_AUTHORIZATION_RECORD_2026_10_11.md` says no independent review request was sent and D2 remained deferred at that point. Later C4 records accepted an AI substitute for C4 only; they do not establish a C5 external review. `H10_D2_EXTERNAL_REVIEW_PACKET.md` is available for C4 method context, not C5 approval.
- **Why it matters:** The AI implementation/review conflict cannot satisfy an independent-review requirement; current statistical uncertainties include calibration and multiplicity, dependent temporal observations, overlapping/grouped entities, and retrospective selection/exposure.
- **Decision/artifact required:** Independent reviewer engagement and a written report against the exact proposed C5 protocol digest. Review must answer the checklist in `CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md` and explicitly list blocking/non-blocking issues.
- **Responsible role:** Project owner appoints/obtains reviewer. Reviewer identity is intentionally blank pending authentic evidence.
- **Closure evidence:** Reviewer-authored assessment, identity/affiliation and independence/conflict disclosure, exact reviewed protocol digest, signed or otherwise authenticated approval method consistent with governance, issue disposition, and owner’s subsequent decision. Do not count this AI’s work as approval.
- **Dependencies / consequences:** Blocks B1 final protocol acceptance, B3 boundary/analysis signoff, B5 final predeclaration, and authorization for any real-market evaluation or campaign integration.

### B3 — Evaluation and holdout boundary

- **Status:** BLOCKED.
- **Exact requirement:** Establish a documented allowlist of eligible development inputs and a precise train/validation/final-evaluation boundary using only metadata and governance documentation. Identify the protected prospective/final-evaluation boundary, row/time/group partition rules, data-use permissions, leakage controls, and whether any historical OOF/final-period outputs have been exposed. Do not inspect protected contents to resolve this.
- **VERIFIED FACT / evidence:** Existing governance states holdout is `SEALED`, uses `0`, and the prospective directory is absent in the current checkout (`.readiness.json`, `FIXTURE_PROVENANCE.json`, frozen C4 record). The C4 predeclaration and Phase 5 draft both say development-vs-sealed membership/boundary is not established. Manifest/provenance records identify the development event table, OOF output, run manifest, and study producer by paths/hashes; they do not by themselves prove the exact sealed boundary or disjointness. `FIXTURE_PROVENANCE.json` records a development-only fixture snapshot and says no prospective directory was copied; that is not a boundary attestation for the source data.
- **Why it matters:** Without an authoritative boundary, the team cannot prove eligibility, prevent leakage, or claim that training, validation, retrospective OOF, and protected final evaluation are disjoint.
- **Decision/artifact required:** Owner-authored boundary specification citing existing design/governance records; allowed input identifiers and metadata; signal/outcome maturity; temporal embargo/purge; grouping unit; historical exposure status; protected boundary identifier/path as recorded in governance without opening/listing/hashing its contents; and operating controls that deny access.
- **Responsible role:** Owner/data steward confirms boundary and permissions; independent reviewer assesses leakage and dependence; implementer can add guards only after approval.
- **Closure evidence:** Written owner/data-steward attestation with cited authoritative document locations, reviewer acceptance, a path allowlist/denylist test, and non-content evidence that execution environment excludes the protected boundary.
- **Dependencies / consequences:** Blocks B5, data-use authorization, any evaluation, and meaningful readiness verification. If a boundary cannot be established without prohibited access, it remains open and the operation remains blocked.

### B4 — Written owner authorization

- **Status:** OPEN.
- **Exact requirement:** Owner makes and records each explicit C5 decision in `CAMPAIGN5_OWNER_DECISION_PACKET.md`. No silence/default approval or inherited C4 permission. Decisions must identify scope, exact artifact digests, permissible operations, exclusions, and expiry/revocation conditions where applicable.
- **VERIFIED FACT / evidence:** Current C4 records are scoped to C4. The 2026-10-11 H-10 authorization says it did not authorize H-10 statistical-method adoption/D2 closure, implementation/freeze/launch; later 2026-10-14 and 10-16 decisions concern C4-specific acts and state no authorization to launch another campaign. The Phase 5 draft status is `NOT AUTHORIZED`; no Campaign 5 owner decision record was identified.
- **Why it matters:** Documentation and passing tests are not authorization; the project has no explicit owner-granted C5 scope, data use, protocol, review acceptance, or integration permission.
- **Decision/artifact required:** Owner answers the separated questions in the decision packet, including defer/reject options, and creates a durable authentic decision record. A later integration authorization is a separate act, not implied by study authorization.
- **Responsible role:** Project owner; implementer transcribes only with exact provenance and does not manufacture signature/identity.
- **Closure evidence:** Owner-authored or faithfully transcribed, provenance-linked, dated written decisions for each item; exact hashes; explicit allowed/prohibited actions. Integration requires a distinct explicit decision after prerequisites are closed.
- **Dependencies / consequences:** Blocks every real-market action, generator activation, production integration, and C5 run.

### B5 — Real-market predeclaration

- **Status:** IN PROGRESS.
- **Exact requirement:** Finalize a one-run, immutable, reviewed predeclaration before any real-market read/fit/score/metric. Specify dataset/run identifiers, target, comparator, split boundaries/purge, baseline, metrics, uncertainty, multiplicity, selection/one-use rules, acceptance/stopping conditions, outputs, and holdout restrictions. Unknown values remain unresolved.
- **VERIFIED FACT / evidence:** `.model_discovery_workspace/PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md` already documents `NOT AUTHORIZED`, a version conflict (manifest v1.0.1 vs protocol v1.0.2), primary-contrast mismatch, unresolved holdout boundary, bootstrap/ECE reconciliation, and exposed retrospective 2025 status. No market comparison was performed in this phase.
- **Why it matters:** An incomplete or post-hoc declaration invites protocol selection, multiple comparisons, information leakage, and optimistic interpretation.
- **Decision/artifact required:** Update the existing draft only to add explicit structured unresolved fields and owner/reviewer gates; do not resolve conflict by selection. Owner/reviewer must finalize exact IDs/digests and all analysis/stopping details before execution.
- **Responsible role:** Owner selects policy and scope; reviewer assesses statistical content; analyst/implementer prepares and pins the document.
- **Closure evidence:** Final predeclaration with immutable hash, independent review against that hash, owner approval naming that hash, reproducibility plan, and documented boundary/access controls. This does not itself authorize campaign integration.
- **Dependencies / consequences:** Depends on B1–B4, particularly dataset-boundary and review. Blocks any real-market evaluation.

### B6 — Current full-suite verification

- **Status:** VERIFIED CLOSED — current engineering suite only; no governance permission inferred.
- **Exact command/root:** From `.model_discovery_workspace/dev/`: `timeout 1800s py -3 -m pytest -vv --durations=10`, run persistently so the host's synchronous call cap did not interrupt Windows subprocesses.
- **Current result:** **520 passed, 26 subtests passed, 0 failed, 0 skipped in 756.82s**, exit 0. Full verbose log: `CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log`.
- **Historical pre-change result:** 518 passed + 26 subtests in 293.88s, exit 0 (`CAMPAIGN5_COORDINATED_FULL_SUITE.log`); this is superseded as the latest result.
- **Runner diagnostics:** Earlier post-change runs had long Windows subprocess E2E tests interrupted; captured runs showed 6 failures/514 passes and 4 failures/516 passes, including child return code `3221225794` (`0xC000013A`) and missing expected stderr. A standalone E2E-class run hit 540s (exit 124). These were not counted as passes; the later persistent complete run passed all tests. Diagnostics: `CAMPAIGN5_POST_FIX_FULL_SUITE.log`, `CAMPAIGN5_POST_FIX_FULL_SUITE_FINAL_TIMEOUT.log`, and `CAMPAIGN5_POST_FIX_E2E_CLASS_TIMEOUT.log`.
- **Closure evidence:** Complete current pytest summary and exit 0 with all 520 selected. No tests/assertions were changed, skipped, weakened, or run in parallel. Does not close B1–B5 or B7 and grants no C5 data use, execution, or launch authorization.

### B7 — Legacy standalone study/build/train execution-path scope

- **Status:** BLOCKED — owner scope decision required before any legacy-path remediation.
- **Exact requirement:** Owner classifies the identified standalone paths as prohibited for the intended C5 operation, controlled by documented and enforceable operational separation, or explicitly in scope for narrowly authorized fail-closed enforcement. Do not claim repository-wide execution protection unless every in-scope path is controlled and tested.
- **Engineering evidence:** The C5 signed-authorization preflight is wired at supervisor, continuous-loop, and experiment-adapter boundaries. It binds identity, protocol, predeclaration, boundary, operation/scope, approvals, status/expiry/revocation, and audit. No authoritative C5 record/trust keys are present, so guarded autonomous routes deny execution. The current post-change full dev suite passed **520 tests + 26 subtests, 0 failures/skips, in 756.82s**, exit 0; evaluator syntax compilation and 18 focused tests pass. Prior authorization/adjacent suite passed **79 tests + 4 subtests in 11.15s**, exit 0. See [coordinated closure](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md), [execution-path audit](CAMPAIGN5_EXECUTION_PATH_AUDIT.md), and [current suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log).
- **Known limitation / verified gap:** Static inspection found standalone `study_files/backend` model training/data-build scripts with direct CLI paths outside this preflight. None was executed or modified. They could bypass the autonomous boundary if invoked against sensitive data. The owner must first choose: prohibit C5 use; establish enforceable operational separation; or authorize exact scripts for narrow fail-closed changes and inert tests.
- **Full-suite status:** B6 is VERIFIED CLOSED by the complete 520-test post-change suite; it is not an authorization and does not establish B7 all-path coverage.
- **Responsible role:** Owner decides legacy-path scope and permitted controls; engineering maintainer acts only within that written scope and retests; independent reviewer assesses the data/statistical boundary.
- **Closure artifact:** Owner-authored path-by-path scope decision; if changes are authorized, updated audit and inert per-path denial tests. No positive production authorization is required or may be fabricated for those tests.
- **Dependencies:** Owner must resolve B1–B5 authorization/protocol prerequisites before any C5 operation. This code does not supply human approval.

## Immediate owner/reviewer actions

1. Owner — B1: select exactly one protocol artifact/digest or explicitly defer; assess the evidence/options in `CAMPAIGN5_OWNER_DECISION_PACKET.md` without selecting by recency or observed outcomes.
2. Owner — B2: appoint a qualified reviewer genuinely independent of implementation, data production, and outcome access; AI preparation is not a substitute.
3. Owner/data steward — B3: issue a source-cited decision on permitted inputs/operations, exclusions, temporal/group/purge rules, exposure, future fixture restrictions, and the disclosed header-only staged-fixture read. Do not access restricted contents; if not determinable, leave B3 blocked.
4. Independent reviewer — B2: return a reviewer-authored, authenticated assessment against exact protocol/predeclaration digests, including dependence/group structure, exchangeability/sign symmetry where applicable, p-value/interval validity, multiplicity, assumptions, findings, limitations, recommendation, and conflicts.
5. Owner + reviewer — B5: settle all declaration elements, freeze an immutable declaration aligned to the selected protocol and boundary, and record both approvals against the same digest.
6. Owner — B7: classify legacy scripts path-by-path as prohibited, operationally separated with enforceable controls, or in scope for narrowly authorized fail-closed changes. Engineering must not edit them first.
7. Owner — B4: only after prerequisites, record authentic authorization for one exact operation with protocol/predeclaration/data-boundary/scope digests, permitted outputs, exclusions, expiry, and revocation. Integration/launch requires separate explicit authorization.

**Readiness conclusion:** B1–B5 remain pending; B6 current full-suite verification is complete (520 passed + 26 subtests, 0 failures/skips, 756.82s, exit 0); B7 remains blocked pending owner scope for legacy standalone entrypoints. Campaign 5 is **NOT AUTHORIZED / NOT READY TO LAUNCH**. No test pass or paperwork changes that status. See the [final coordinated closure](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md).
