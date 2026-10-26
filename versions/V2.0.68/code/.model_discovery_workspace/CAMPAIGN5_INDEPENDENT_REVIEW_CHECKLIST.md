# Campaign 5 Independent Statistical Review Checklist — v1.1

**Status: PREPARATION TEMPLATE — NOT REVIEWED, NOT APPROVED.** Reviewer identity and answers are blank by design. This checklist supports the exact protocol artifact and versioned [review specification](CAMPAIGN5_REVIEW_READY_SPECIFICATION.md); it is not an approval record. The implementing AI is not an independent reviewer and must not complete this checklist as sign-off.

Preparation-time source status: the v1.0.1 digest `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07` is only a manifest reference; its authoritative source bytes are absent. The v1.0.2 protocol copies each hash to `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05`. During the final preparation pass, both copies were freshly hash-checked and parsed as JSON; the protocol ID, version (`1.0.2`), and status (`frozen_v1.0.2`) were verified. The workspace content reader still returns `[BLOCKED]`; no field-by-field scientific review, source-authority check, or approval verification is claimed. The prior draft digest `a8e15c6b9ba2d14188d8933b8cbeb89755110aebc210d37ec5e6e6c63b27433a` is not the current review specification. Before review, owner must select exact source artifact and the final approved-spec candidate must be hashed; recompute exact hashes from the reviewer's delivered bytes. These values are not a choice or approval.

**Review scope:** protocol authority/version and provenance; exact target, population, estimand and contrasts; exposure and boundary; temporal validation and maturity/purge; grouping/dependence; metrics/calibration; uncertainty; multiplicity and selection; missingness/stopping; claims; and execution/control scope. Assess only documents and metadata authorized for review—do not inspect protected outcomes to resolve ambiguity.

The reviewer should mark each item `ACCEPT`, `REVISE`, `REJECT`, or `NOT DETERMINABLE`, cite exact digests reviewed, and distinguish facts, empirical evidence, assumptions, and unknowns. Any blocking or `NOT DETERMINABLE` finding keeps evaluation blocked.

## Packet manifest — reviewer/owner to pin

- [ ] Selected authoritative protocol file(s), authority/status, byte count and SHA-256: `[REVIEWER TO COMPLETE]`
- [ ] Versioned specification and any supporting predeclaration SHA-256: `[REVIEWER TO COMPLETE]`
- [ ] Source-cited boundary/exposure determination SHA-256 or controlled record ID: `[REVIEWER TO COMPLETE]`
- [ ] Run/provenance metadata and relevant code/method implementation digests: `[REVIEWER TO COMPLETE]`
- [ ] Decision sheet and all assumptions/limitations included: `[REVIEWER TO COMPLETE]`
- [ ] Recompute all received byte digests; report mismatches rather than overwriting historical records: `[REVIEWER TO COMPLETE]`

**Exact pre-review digest caveat:** no digest for the final v1.1 spec, protocol provenance request, data-steward request, decision sheet, or consolidated handoff is asserted in this template; compute after final files are fixed.

## A. Identity, scope, and independence

- [ ] Exact Campaign 5 protocol name/version, authority and SHA-256 reviewed: `[REVIEWER TO COMPLETE]`
- [ ] Exact specification/predeclaration SHA-256 reviewed: `[REVIEWER TO COMPLETE]`
- [ ] Reviewer identity, affiliation, qualifications and review date: `[REVIEWER TO COMPLETE]`
- [ ] Independence from implementation, candidate selection, data production and outcome access described; all conflicts disclosed: `[REVIEWER TO COMPLETE]`
- [ ] Scope matches the owner’s written decision; no C4 permission is treated as C5 approval: `[REVIEWER TO COMPLETE]`
- [ ] Reviewer confirms review does not authorize data access, execution, integration or launch: `[REVIEWER TO COMPLETE]`

## B. Protocol provenance and version consistency

- [ ] Manifest lineage vs. selected source version is reconciled with authoritative records, not inferred from digest or recency.
- [ ] Missing v1.0.1 source bytes are supplied or explicitly reported unavailable; no content reconstructed from memory.
- [ ] v1.0.2 source authority, approval/version history, and relationship to protocol-like companion documents are established.
- [ ] Every C4→C5 scientific/policy change is enumerated and accepted/rejected/deferred by owner; reviewer checks the exact source bytes.
- [ ] Proposal-only synthetic candidate search is excluded from real-market protocol and not activated.

Reviewer response / findings: `[REVIEWER TO COMPLETE]`

## C. Estimand, target, and data provenance

- [ ] Population, analysis unit, target/event definition, prediction time and event maturity are exact and reproducible.
- [ ] Each proposed contrast has a predeclared sign and unique primary estimand, compatible with selected protocol.
- [ ] Dataset/run IDs, manifest/input hashes, roster/coverage limitations and source provenance are pinned.
- [ ] Retrospective exposure to OOF/candidate/validation outputs is disclosed and does not support a false virgin-confirmatory claim.
- [ ] Missing rows, duplicate identities, invalid labels, unlinked records and exclusions have fail-closed rules.
- [ ] No data are selected, reconstructed, filtered or relabeled based on observed evaluation outcomes.

Reviewer response / findings: `[REVIEWER TO COMPLETE]`

## D. Temporal dependence, groups, and split integrity

- [ ] Training occurs strictly before validation/test prediction time including target maturity, purge and embargo.
- [ ] Label horizon, overlapping events, look-ahead, feature publication/availability and preprocessing-fit boundaries are addressed.
- [ ] Entity, event-family, date/week, common-shock, repeated-observation, shared-training and fold dependencies are identified.
- [ ] Inferential and resampling units support the intended generalization claim; group weights and effective sample size are justified.
- [ ] Calendar gaps, irregular sampling, fold construction and coverage criteria are explicit.
- [ ] Exposed final calendar strata are treated as retrospective/descriptive when appropriate; no relabeling as holdout.
- [ ] Protected boundary is attested from authorized governance metadata without opening/listing/hashing/querying protected contents; otherwise mark `NOT DETERMINABLE` and block.

Reviewer response / findings: `[REVIEWER TO COMPLETE]`

## E. Boundary, exposure, and fixture restrictions

- [ ] Data steward specifies exact allowed IDs/versions/operations and excluded evaluation/OOF/holdout artifacts.
- [ ] Prior access history and outcome exposure are source-cited; unknown history is not treated as no exposure.
- [ ] Temporal/group/maturity/purge rules and operational isolation are supported by authoritative records.
- [ ] The prior header-only staged-fixture read receives an explicit owner/steward ruling; future fixture rules are explicit.
- [ ] Copy, network, retention, output and recipient constraints are stated.

Reviewer response / findings: `[REVIEWER TO COMPLETE]`

## F. Candidate selection, multiplicity, and uncertainty

- [ ] Complete candidate/comparison/metric/subgroup/fold/retry family is defined; primary/secondary/exploratory/descriptive hierarchy is explicit.
- [ ] Multiplicity procedure controls stated error criterion for the claim; family membership, dependence and missing-member rules are addressed.
- [ ] Candidate search, tuning, feature/model choice and retries are confined to permitted training/validation data.
- [ ] Primary metric, interval/test, null and practical margins are justified for estimand and dependence structure.
- [ ] Resampling unit, block construction, circularity/truncation, seed, replicate count, paired-index policy, invalid-replicate rules, minimum valid count and endpoint convention are fully specified and independently checked.
- [ ] Temporal autocorrelation, cross-sectional/group dependence, common shocks, heteroskedasticity and fold overlap are addressed.
- [ ] If sign-flip/permutation is proposed, assess null, exchangeability/sign symmetry, weak-null meaning, p-value validity, finite-sample calibration, Monte Carlo resolution and multiplicity interaction.
- [ ] Calibration definitions, bins, boundary conventions, empty-bin handling, weighting and uncertainty are precise if used as gates.
- [ ] No threshold/margin was selected from observed evaluation outcomes.

Reviewer response / findings: `[REVIEWER TO COMPLETE]`

## G. Missingness, stopping, and claims

- [ ] Fail-closed exclusions for invalid/missing data, immature labels, duplicates, empty/one-class folds, insufficient groups, invalid resamples, hash mismatch, incomplete outputs, failures/deviations are explicit.
- [ ] Execution failure, refusal, inconclusive analysis, missing artifact and model outcome remain distinct.
- [ ] One-use, retries, interim inspection, outcome-independent stop rules and early termination handling are explicit.
- [ ] Retrospective/prospective interpretation and claim limits follow actual exposure, roster, period and design.
- [ ] No result implies profitability, causality, holdout performance, production safety, integration or launch.

Reviewer response / findings: `[REVIEWER TO COMPLETE]`

## H. Data-boundary controls and reproducibility

- [ ] Metadata-only protocol/governance review is distinguished from any evaluation-data access; access logging protects contents.
- [ ] Exact permitted development inputs and prohibited evaluation/OOF/prospective/holdout paths are source-cited, with non-content evidence of isolation.
- [ ] Proposed harness cannot reach campaign/production entrypoints, persistent campaign state, promotion/champion paths, network data sources, or protected holdout inputs.
- [ ] Exact command, environment/dependency versions, source/input hashes, outputs, stdout/stderr, status, runtime, and output hashes are recorded for any later authorized operation.
- [ ] Outputs are disposable and an independent recalculation/reproduction path is specified; synthetic fixtures cannot prove real-data boundary or protocol validity.

Reviewer response / evidence: `[REVIEWER TO COMPLETE]`

## I. Engineering authorization-enforcement review (not statistical approval)

- [ ] C5 authorization binds exact operation, campaign/scope, protocol/predeclaration/boundary digests, permitted inputs/operations/outputs, status, expiry/revocation, and required human approvals.
- [ ] Trust identities/keys have an approved governance mechanism; none are assumed or fabricated by this package.
- [ ] Every in-scope direct script, alternate runner, retry/resume/recovery/subprocess is blocked before restricted access; standalone legacy study/train/build scripts remain outside current preflight coverage pending B7.
- [ ] Audit evidence is append-only, deterministic, and contains no restricted values.
- [ ] Synthetic positive fixtures are non-authoritative and cannot pass the runtime authorization gate.

Reviewer response / evidence: `[REVIEWER TO COMPLETE]`

## J. Required reviewer disposition

The reviewer-authored decision must be tied to the exact immutable protocol and predeclaration SHA-256 values reviewed, not merely this checklist version. It must include a clear recommendation and limitations, independence/conflict disclosure, findings on temporal and group structure, exchangeability/sign symmetry where applicable, p-value/interval validity, and multiplicity; unresolved assumptions must be marked blocking or `NOT DETERMINABLE`, never treated as approval.

- Overall disposition: `[ACCEPT / REVISE / REJECT / NOT DETERMINABLE — reviewer to complete]`
- Recommendation and limitations, including whether evidence supports only descriptive retrospective inference or a confirmatory claim: `[REVIEWER TO COMPLETE]`
- Blocking issues, non-blocking issues, assumptions and dissent: `[REVIEWER TO COMPLETE]`
- Exact artifact names, versions, byte counts and hashes reviewed: `[REVIEWER TO COMPLETE]`
- Reviewer-authored report location/hash and authenticated sign-off: `[REVIEWER TO COMPLETE]`
- Reviewer identity, qualifications, affiliation, independence/conflicts: `[REVIEWER TO COMPLETE]`
- Reviewer statement that this is not owner authorization: `[REVIEWER TO COMPLETE]`

**Owner action after review:** owner separately dispositions each finding and decides whether any later evaluation or integration is authorized. Reviewer acceptance is not owner authorization. No response or unsigned draft is approval.

