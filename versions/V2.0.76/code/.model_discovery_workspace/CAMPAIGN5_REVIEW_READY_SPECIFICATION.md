# Campaign 5 Evaluation Specification — Review Draft v1.1

**Prepared 2026-10-19 | Status: DRAFT FOR OWNER / DATA-STEWARD / INDEPENDENT-REVIEWER REVIEW | NOT APPROVED | NOT AUTHORIZED — DO NOT RUN**

This is a versioned preparation document, not a frozen protocol, independent review, owner decision, data-use permission, or execution authorization. It permits no evaluation/OOF/holdout access, market-data fitting or scoring, campaign execution, candidate activation, production integration, or launch. No result or predictive improvement is claimed. Every item marked **UNRESOLVED** is a blocking decision; silence supplies no default.

## 1. Protocol provenance and alternatives (not interchangeable)

- **Manifest lineage:** the development run manifest identifies `DZAI-MARKET-STRUCTURE-ABLATION-V1` v1.0.1 and records SHA-256 `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`. That digest is a manifest reference only here: the exact v1.0.1 source bytes are absent from the inventoried workspace. Its target, estimand, contrasts, and methods must not be reconstructed from the digest or other recollections.
- **v1.0.2 source:** canonical path `study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json`; a second copy is at `.model_discovery_workspace/dev/study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json`. `sha256sum` returned `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05` for both 15,778-byte files, matching the recorded fixture-provenance value. The workspace file reader returned `[BLOCKED]` for both, so this draft does not claim a fresh textual inspection of the source. Previously recorded governance summaries describe historical primaries LightGBM-A − LogisticRegression-A and LightGBM-C − LightGBM-B, and a distinct prospective design of eight frozen models/no retraining/up to 2,000 predictions over 12–18 months; the reviewer must verify all such details against the exact source bytes.
- **Current retrospective predeclaration draft:** `PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md`, SHA-256 `a8e15c6b9ba2d14188d8933b8cbeb89755110aebc210d37ec5e6e6c63b27433a` (freshly matches its recorded digest). It proposes the event `Open[T+2]/Open[T+1] - 1 >= 0.02`, a LogisticRegression Arm B − Arm A feature increment, and previously exposed 2023–2025 OOF strata. These are draft proposals, not approved values; the proposal is not established as a v1.0.2 primary contrast or v1.0.1 content.
- **Development-only candidate-search proposal:** `dev/autonomous_agent/proposal_layer/protocol_amendment_v2.json`, SHA-256 `d9ceb15b47e25b0b175f01b02b861277685d7b865e123afe114f0b6f62d5759e`. It is `PROPOSAL_ONLY_NOT_ACTIVATED`, synthetic-fixture scope, and is not a real-market protocol.

**UNRESOLVED — owner must select or defer exactly one study purpose/protocol path.** Do not select based on observed outcomes, recency, or engineering readiness. Do not combine a retrospective OOF amendment with the v1.0.2 prospective design. See [protocol provenance request](CAMPAIGN5_PROTOCOL_PROVENANCE_REQUEST.md) for the precise missing-source request.

## 2. Research question, target, unit, estimand, contrast

**Question template only:** For an owner-approved population, period, event unit, and prediction-time information set, what is the difference between two protocol-pinned prediction procedures under a specified validation design?

**UNRESOLVED — target:** exact label, horizon, threshold, maturity/validity, positive-class sign, missing-label rule, and whether the draft's 2% event is equivalent to the selected protocol. The 2% target is a proposal only.

**UNRESOLVED — population and unit:** eligible universe and point-in-time membership; event/ticker/date identity; duplicate policy; coverage and exclusions; prediction time; minimum event/group coverage; target generalization population. Existing records describe a recovered 149-symbol roster and unknown historical membership/delistings; this does not establish broad-market or survivorship-free coverage.

**UNRESOLVED — estimand and contrast:** select one exact comparison, direction, paired unit, and claim. The recorded v1.0.2 historical primaries differ from the draft's LogisticRegression Arm B − Arm A proposal; its prospective design is a separate question. Specify whether the goal is descriptive reproduction or inferential/confirmatory estimation and the population/period to which it applies. No existing option is approved here.

## 3. Data boundary, exposure, and permitted operations

No restricted rows, OOF prediction values, evaluation scores, or holdout contents may be opened, queried, listed, copied, or hashed to resolve these choices. The owner/data steward must use authoritative governance records to issue a source-cited allowlist/denylist naming exact dataset/run IDs, versions, paths, operations, and exclusions, plus non-content evidence that protected inputs are excluded from any future environment.

Known disclosures to carry forward: existing OOF artifacts and 2025 strata are previously exposed in historical work; a previous suite read only the header of the staged development event-table fixture, with no rows consumed, and the owner/data-steward ruling on that read remains pending. Fixture provenance states the isolated development snapshot omits a prospective directory; that alone does not establish source-data disjointness or a protected boundary.

**UNRESOLVED — exposure:** complete outcome-access history, prior analysis/selection/search/retries, who saw which outputs, which periods remain eligible for which claims, whether the prior header-only fixture read was permitted, and future fixture limits.

**UNRESOLVED — boundary/operations:** exact permitted identifiers and read/hash/copy operations; explicit OOF/evaluation/holdout exclusions; access, network, retention, and output constraints; proof of disjointness; protected boundary identifier from governance metadata. If not determinable without restricted access, stop and retain the block.

## 4. Validation, temporal and group rules, maturity and purge

The existing retrospective draft proposes expanding chronological 2023/2024/2025 folds, training signal date and label exit strictly before each validation-year start, and paired event keys. This remains a proposal; existing OOF/2025 exposure means it cannot be presumed virgin confirmation. Previously recorded v1.0.2 summaries describe a separate prospective frozen-model/no-retraining design; exact details require source review.

**UNRESOLVED — validation:** exact training/validation periods, split population and eligibility, fold coverage, repeated-look policy, and retrospective versus prospective design.

**UNRESOLVED — temporal/group controls:** feature publication/availability versus prediction time; signal and target exit/maturity; horizon and embargo; overlap between events/folds; ticker/entity, date/week, event-family and shared-training dependence; group holdout or resampling unit; duplicate and unmatched keys; missing/ineligible rows; point-in-time universe membership; leakage and preprocessing-fit boundary. The independent reviewer must determine whether the chosen split and unit support the intended claim.

## 5. Baselines, metrics, uncertainty, and multiplicity

The current draft proposes LogisticRegression Arm A versus Arm B, paired pooled OOF ROC-AUC difference, and Brier/ECE safeguards. It also records proposed thresholds (AUC point delta ≥0; paired 95% lower endpoint ≥−0.01; Brier degradation ≤+0.005; ECE degradation ≤+0.02; all three years present), a 1,000-replicate seed-42 four-calendar-week circular paired moving-block bootstrap, and local ECE bins `[0,.1), …, [.9,1]` with empty bins skipped and occupancy weighting. These are unapproved draft values; bootstrap/protocol implementation equivalence and ECE/protocol equivalence are unverified. The historical protocol's exact definitions must be read from the chosen source and reviewed, not inferred from local code or this document.

**UNRESOLVED — baseline/metrics:** exact model/config/feature/code digests; primary and secondary outcomes; metric definitions, direction, thresholds/margins and scientific basis; calibration bin edges/weighting/uncertainty; required strata and valid sample/group counts.

**UNRESOLVED — uncertainty:** estimand-compatible interval/test, inferential and resampling unit, temporal and cross-sectional dependence, common shocks, fold overlap, block construction, paired-index rule, invalid resample handling and minimum valid count, seed/reproducibility, endpoint convention, and independent implementation check. Reviewer must assess validity; this AI selects no method.

**UNRESOLVED — multiplicity/selection:** full family across contrasts, candidates, metrics, subgroups, folds, thresholds, retries and interim looks; primary/secondary/exploratory/descriptive hierarchy; error criterion/control; dependence assumptions; unavailable members; prior search/exposure adjustment. “One contrast” is not automatically multiplicity-free after candidate or outcome selection. Do not choose among methods or claims after seeing outcomes.

## 6. Missingness, exclusions, stopping, outputs, interpretation

Before any future authorization, freeze fail-closed handling for missing/invalid features or labels, immature events, duplicate/unmatched keys, empty/one-class folds, insufficient time/events/groups, failed/invalid resamples, incomplete outputs, hash mismatch, boundary uncertainty, command/infrastructure failure, deviation, and early stopping. Keep execution failure, refusal, inconclusive analysis, missing artifact, and model outcome distinct. Define exclusions/denominators, one-use/retry rules, who may inspect outputs, and outcome-independent stop rules.

Any future operation would require separate exact authorization and an isolated, disposable, offline environment with pinned inputs/code/dependencies/command/outputs and an independent recomputation plan. The previous draft's suggested output filenames are proposals only; this document authorizes no output creation, campaign state mutation, training, scoring, or access.

Claims, if ever reviewed and authorized, must be limited to the chosen roster, period, design, and exposure status. No evaluation result alone establishes profitability, causality, point-in-time integrity, survivorship-free coverage, prospective generalization, holdout performance, production safety, campaign readiness, or launch permission.

## 7. Blocking decision register

| Decision | Current status | Responsible role | Required closure before any evaluation |
|---|---|---|---|
| Protocol/provenance and scientific purpose | **UNRESOLVED** | Owner; reviewer assesses | Exact immutable source bytes/digest, selected path or explicit defer, authoritative provenance, and itemized C4→C5 change dispositions. |
| Target, population, estimand, contrast and claim | **UNRESOLVED** | Owner; reviewer assesses | One complete protocol-consistent definition with sign, event unit, population, and descriptive/inferential scope; no outcome-based selection. |
| Data boundary, exposure and fixture policy | **UNRESOLVED** | Owner/data steward; reviewer assesses | Source-cited allowlist/denylist, exclusions, exposure history, header-only-read ruling, future fixture limits, and temporal/group/maturity/purge rules. |
| Independent review | **PENDING** | Owner appoints; qualified independent reviewer authors | Reviewer identity/qualifications/affiliation, independence/conflicts, and signed/authenticated findings tied to exact protocol and spec digests; AI is not reviewer. |
| Validation, uncertainty, calibration and multiplicity | **UNRESOLVED** | Reviewer assesses; owner decides | Exact methods, assumptions, implementation equivalence, multiplicity family/control, exclusions, stopping and claim limits; unknowns remain blocking. |
| Legacy entrypoints | **BLOCKED pending scope** | Owner; engineering only after narrow authorization | Path-by-path prohibit/separate/remediate decision; do not edit legacy scripts before it. |
| Exact operation, integration, launch | **NOT AUTHORIZED** | Owner, later and separately | Authentic exact-operation authorization only after prerequisites; integration/launch each needs distinct later approval. |

**Gate:** Campaign 5 remains **NOT AUTHORIZED — DO NOT RUN**. This v1.1 draft completes document preparation only; it resolves none of the human scientific, boundary, review, or authorization decisions.
