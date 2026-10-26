# Campaign 5 Research Decision Packet

**Prepared 2026-10-18 | Preparation only | NOT AUTHORIZED — DO NOT RUN**

This packet advances documentation only. It does not select a protocol, authorize data use, constitute independent review, or permit evaluation, training, scoring, holdout access, integration, or launch. No evaluation rows or outcomes were accessed to prepare it. The source v1.0.2 protocol file was not directly readable in this workspace; protocol facts below are limited to exact digests and descriptions already recorded in the handoff, provenance, and draft artifacts. Obtain source bytes for actual review; do not treat this summary as a substitute.

## 1. Evidence and protocol comparison

| Candidate / artifact | Exact recorded digest | Estimand, contrast, and intended conclusion | Data exposure and validation design | Status / consequence |
|---|---|---|---|---|
| **Manifest lineage: `DZAI-MARKET-STRUCTURE-ABLATION-V1` v1.0.1** | `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07` (recorded by the development run manifest) | The authoritative v1.0.1 protocol bytes are absent from this checkout. Its estimand, target, contrasts, metrics, and intended claim cannot be reconstructed from this digest alone. | Manifest lineage is associated with the retained 2023–2025 OOF artifacts; those results are historically exposed. Exact eligible rows, source-to-OOF provenance, and disjointness from protected evaluation data are not established by this lineage digest. | **Not byte-verifiable here.** Owner must supply the source artifact and provenance; reviewer must assess lineage. Do not infer equivalence to v1.0.2. |
| **Recorded v1.0.2 protocol artifact** ([development fixture path](dev/study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json)) | `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05` (recorded in fixture provenance and prior audits) | Existing records describe historical primary contrasts as LightGBM-A − LogisticRegression-A and LightGBM-C − LightGBM-B; within-estimator B − A contrasts are secondary. The selected target/estimand and exact versioned definitions still require review against source bytes. | Records describe historical folds as pre-lock/retrospective and a separate prospective design: eight frozen models, no retraining, up to 2,000 predictions, 12–18 months, with analysis after minimum-time and label-maturity conditions. Details not exposed in the records remain unknown. | Distinct from v1.0.1. The prospective design is not a retrospective OOF amendment; neither is authorized. Reviewer needs the exact source bytes and complete method. |
| **Current retrospective predeclaration draft** ([draft](PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md)) | `a8e15c6b9ba2d14188d8933b8cbeb89755110aebc210d37ec5e6e6c63b27433a` (recorded preparation-time digest; recompute before review) | Proposes a fixed LogisticRegression Arm A vs Arm B feature-increment comparison, target `Open[T+2]/Open[T+1] - 1 >= 0.02`, pooled paired chronological OOF ROC-AUC delta, with Brier/ECE safeguards. This is not listed as a v1.0.2 primary contrast. | Proposes chronological 2023/2024/2025 folds with training signal date and label exit before validation-year start. OOF/2025 artifacts are previously exposed; it is retrospective development, not a virgin confirmatory test. | A draft, not a protocol selection or authorization. Target-to-v1.0.2 equivalence, contrast authorization, method equivalence, boundary, and confirmatory interpretation are unresolved. |
| **Development candidate-search amendment proposal v2.0.2** ([proposal](dev/autonomous_agent/proposal_layer/protocol_amendment_v2.json)) | `d9ceb15b47e25b0b175f01b02b861277685d7b865e123afe114f0b6f62d5759e` (recorded preparation-time digest; recompute before review) | Proposes an expanded candidate universe (LogisticRegression, RandomForest, HistGradientBoosting; feature operators/transforms) with synthetic-fixture diagnostic metrics. It does not define an approved real-market estimand or claim. | Explicitly synthetic chronological development fixtures; no final holdout or production evaluation. | `PROPOSAL_ONLY_NOT_ACTIVATED`; owner approval and independent review pending. Not a substitute C5 protocol and not authority to evaluate. |

**Digest caveat:** The v1.0.1 value is only a recorded manifest reference; source bytes are unavailable. The v1.0.2, predeclaration, and proposal hashes above are recorded evidence, not fresh verification by this packet. Recompute each exact artifact hash from the bytes that the reviewer receives; any difference means review a new digest. Do not try to recover or inspect sealed content to resolve provenance.

### Material differences

- **Estimand/contrast:** v1.0.2's recorded historical primaries are model-class/matched-arm contrasts; the draft instead proposes LR Arm A vs LR Arm B. The v1.0.1 estimand is unknown without source bytes. Candidate-search v2 expands a dev-only search universe and has no market estimand.
- **Target:** the draft proposes a 2% two-step open-price event. Whether that equals either frozen protocol's target is unverified; do not assume it does.
- **Data/exposure:** the draft is retrospective and uses previously exposed 2023–2025 OOF strata. The v1.0.2 record also distinguishes historical retrospective folds from a prospective frozen-model design. The exact data boundary and evaluation/holdout disjointness remain unresolved. The candidate-search proposal is synthetic-only.
- **Validation/design:** the draft proposes annual chronological folds with label-maturity purge. v1.0.2's prospective design instead describes no retraining and a 12–18 month observation window; it is not interchangeable with retrospective OOF. Exact source-defined folds, maturity, and grouping rules require source review.
- **Conclusion strength:** a fixed retrospective comparison could at most support a conditional descriptive result on the selected recovered roster and exposed periods. It cannot establish prospective generalization, profitability, or sealed-holdout performance. No result may be used to choose among protocols.

## 2. Smallest actionable human decisions

### A. Project owner — B1 protocol/scope (first decision)

**Question:** Which single path is intended, or should Campaign 5 be deferred/stopped? Choose one option without reference to observed scores:

1. **Defer/stop.** Keep all C5 data operations blocked; preparation and provenance work may continue. This is the current safe state, not an efficacy recommendation.
2. **Reconstruct v1.0.1.** Supply the authoritative source bytes and source-of-truth lineage; reviewer assesses that exact artifact. Without them the recorded digest alone cannot define the protocol.
3. **Propose v1.0.2 prospective study.** Pin the exact source and settle target, population, operational boundary, and complete prospective plan. Requires prospective collection, frozen models, and the stated 12–18-month window; no retrospective OOF substitution.
4. **Propose a new retrospective amendment.** Create a versioned, fully specified amendment that discloses prior OOF/2025 exposure and limits claims accordingly; obtain independent review and owner decision. It cannot inherit v1.0.2 primary status by implication.

**Closure evidence:** dated authenticated owner record naming exact protocol bytes, SHA-256, scientific purpose, scope, and an itemized accepted/rejected/deferred C4→C5 change list. If choosing v1.0.1, attach the authoritative source artifact. No response means defer.

### B. Project owner — B2 reviewer appointment

**Question:** Who is the qualified reviewer independent of implementation, data production, and outcome access? Appoint the reviewer or defer all evaluation. The reviewer—not this AI or implementer—must author a report that names exact protocol and specification digests, qualifications/affiliation, independence/conflicts, assumptions, findings, limitations, blocking items, and recommendation. Appointment alone is not review or approval.

### C. Owner/data steward — B3 boundary and exposure

**Question:** From authoritative governance records only, what exact input IDs/versions and operations are permitted, what is excluded, and what are the temporal/group/maturity/purge and prior-exposure rules? The record must explicitly decide whether the previously disclosed header-only read of the staged development fixture was in scope and set future fixture restrictions. Options: defer access; provide a source-cited allowlist/denylist and explicit fixture ruling; or reject the proposed source/operation. If authority is insufficient, record unresolved and keep access blocked. Do not inspect restricted contents to answer.

**Closure evidence:** authenticated source-cited determination; exact allowed/denied scope; exposure history; maturity/purge/group boundary; fixture ruling; reviewer assessment or `NOT DETERMINABLE`; and non-content evidence that protected data are excluded from any future execution environment.

### D. Independent reviewer + owner — B5 declaration; owner — B7/B4

- **B5:** after B1–B3, reviewer assesses the complete specification and methods; owner and reviewer must separately accept the same immutable final predeclaration digest. Unknowns remain blocking; AI preparation is not review.
- **B7:** owner classifies every legacy study/build/train entrypoint in [the path audit](CAMPAIGN5_EXECUTION_PATH_AUDIT.md) as prohibited for the operation, covered by enforceable separation, or in scope for narrowly authorized remediation. No legacy-path edits before this decision.
- **B4:** only after prerequisites, owner may authorize one exact operation bound to protocol, predeclaration, boundary, and scope digests, with permitted outputs, exclusions, expiry, and revocation. Any production integration or launch needs separate later authorization.

## 3. Safe work that can continue now

- Obtain authoritative protocol/source artifacts and metadata from the owner; compare hashes and prepare a versioned text diff without examining evaluation or holdout contents.
- Complete this review-draft specification and checklist; keep every unresolved field explicit and recalculate hashes at handoff.
- Ask the data steward to write the source-cited allowlist/denylist, exposure record, temporal/group/maturity/purge rules, and fixture-header ruling from governance records only.
- Conduct offline static code/provenance review and deterministic synthetic-only tests within the already permitted development roots; preserve the synthetic/production boundary.
- Prepare isolated-run/reproducibility checklists and reviewer materials. Do not execute or read source evaluation rows, score OOF predictions, train on market data, or modify legacy scripts.

## 4. Current gate and next milestone

The canonical baseline reports **520 passed + 26 subtests, 0 failures/skips, exit 0, 756.82s**, and **11/11 protected Campaign 4 hashes matching**. This is engineering verification only. The machine-readable blocker register records evaluation, integration, execution, and holdout authorization as false. Worktree changes present before this packet—including `.gitignore`, `README.md`, and untracked project material—were preserved; no tests were rerun because no code was changed.

**Next milestone:** owner supplies/chooses the exact protocol path and appoints the independent reviewer; owner/data steward issues the source-cited boundary ruling. Until those records exist, the only permitted next steps are preparation listed above. **Campaign 5 remains NOT AUTHORIZED — DO NOT RUN.**
