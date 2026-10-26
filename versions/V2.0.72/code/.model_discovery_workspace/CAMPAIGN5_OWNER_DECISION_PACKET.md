# Campaign 5 Owner Decision Sheet — Final Handoff

**Prepared 2026-10-18. Status: decisions pending; NOT AUTHORIZED; DO NOT RUN.** This is the single C5 owner decision packet (no parallel approval form). Blank or silence means defer. It supplies no signature, approval, data permission, integration permission, or launch authorization. Campaign 4 decisions do not transfer to Campaign 5.

**Decision summary for the owner:** complete B1 protocol choice; appoint the independent reviewer and obtain the reviewer-authored B2 report; obtain the owner/data-steward B3 boundary; jointly freeze/approve one B5 predeclaration digest; decide B7 script scope before any legacy-path edits; then, only after prerequisites, create B4 authorization for one exact operation. A separate launch/integration authorization is later and distinct. All options below are alternatives for human decision, not AI recommendations about efficacy.

## Decision order

1. **Owner (B1):** choose one exact protocol artifact/digest or explicitly defer; itemize C4→C5 changes.
2. **Owner (B2):** appoint a qualified reviewer independent of the implementation, data production, and outcome access. The **reviewer** then authors an assessment against the exact protocol and predeclaration digests, including independence/conflicts, assumptions, findings, limitations, and recommendation.
3. **Owner/data steward (B3):** issue source-cited boundary and exposure determinations, explicitly rule on the header-only staged-fixture access, and specify future fixture restrictions. Reviewer independently assesses leakage/dependence or marks not determinable.
4. **Owner + reviewer (B5):** settle all declaration elements; freeze and accept the same immutable predeclaration digest.
5. **Owner (B7):** classify legacy scripts path-by-path before any engineering change; remediation only after narrow written authorization.
6. **Owner (B4):** after prerequisites, authorize or defer one exact operation with all required digests, outputs, exclusions, expiry, and revocation. Integration/launch requires a separate later decision.

## B1 — Select a protocol and scope (owner; reviewer assesses selected digest)

**Exact question:** Which immutable protocol/version and scientific purpose, if any, may be proposed for Campaign 5? Do not select a version merely because it is newer.

**Evidence and consequences:**
- The development run manifest records `DZAI-MARKET-STRUCTURE-ABLATION-V1` v1.0.1 and digest `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`; the distinct authoritative v1.0.1 source artifact is not present in the checkout. A reconstruction needs owner-supplied source-of-truth and reviewer lineage assessment.
- The v1.0.2 protocol artifact in the isolated dev fixture, [MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json](dev/study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json), has SHA-256 `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05`. It lists historical primary contrasts LightGBM-A−LogisticRegression-A and LightGBM-C−LightGBM-B; within-estimator B−A contrasts are secondary. It characterizes historical folds as pre-lock/retrospective. Its separate prospective design specifies eight frozen models, no retraining, up to 2,000 predictions, 12–18 months, and final analysis after minimum-time and matured-event conditions. It is not v1.0.1 and does not authorize use.
- Current digest of the [predeclaration draft](PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md): `a8e15c6b9ba2d14188d8933b8cbeb89755110aebc210d37ec5e6e6c63b27433a`. Current digest of the development-only [candidate-search proposal](dev/autonomous_agent/proposal_layer/protocol_amendment_v2.json): `d9ceb15b47e25b0b175f01b02b861277685d7b865e123afe114f0b6f62d5759e`; it is proposal-only, inactive, and not a C5 protocol. The v1.0.1 digest recorded in a manifest is a lineage reference only because its authoritative source bytes are absent; it is not a verifiable artifact digest in this checkout.
- The attached draft proposes target `Open[T+2]/Open[T+1] - 1 >= 0.02` and a retrospective LogisticRegression A→B comparison on previously exposed 2023–2025 OOF strata; that contrast is not listed as a v1.0.2 primary contrast. Because the authoritative v1.0.1 source bytes are absent and the draft has not been reconciled to the selected v1.0.2 artifact, target equivalence/difference is **unresolved**; do not assume the draft target matches either protocol. The prospective v1.0.2 design and a retrospective amendment also differ in design, exposure, data, and duration. The owner/reviewer must compare target and estimand explicitly; no evaluation should be used to choose between them, and no option implies an AUC improvement.

| Option | Trade-off | Closure evidence |
|---|---|---|
| **P1 Defer/stop (recommended now if objective/source is unclear)** | Keeps C5 disconnected and avoids choosing an estimand without authority. | Dated owner record states defer/reject, whether preparation may continue, and explicit exclusions. |
| P2 Reconstruct v1.0.1 | Preserves manifest lineage only if its authoritative source bytes can be obtained; not evidence of v1.0.2 compliance. | Owner supplies source artifact and digest; reviewer assesses exact lineage; itemized C4→C5 disposition. |
| P3 Propose v1.0.2 prospective design | Honors the prospective direction stated in v1.0.2 but requires prospective collection, frozen models, boundary permissions, and a longer observation period. | Owner pins exact artifact/scope; reviewer assesses it; new complete predeclaration and boundary record. |
| P4 Propose a new retrospective amendment | Could describe a fixed analysis of previously exposed OOF, but cannot silently inherit v1.0.2 primary status or support a virgin-confirmatory claim. | New version/diff/digest, exposure statement, independent assessment, owner decision. |

**Owner choice/rationale/date/authenticated record:** `[PENDING — select exactly one of P1/P2/P3/P4 or explicitly defer; name exact artifact SHA-256, scope, rationale, dated authenticated record URI/hash]`

**Reviewer disposition:** `[PENDING — identity, independence/conflicts, exact digest, report URI/hash]`

## B2 — Independent statistical review (owner appoints; reviewer authors)

**Exact question:** Will the owner appoint a genuinely independent, qualified, non-implementing reviewer to assess the exact selected protocol and predeclaration? Options: appoint before protocol approval (recommended); defer and keep all data use blocked; or reject/revise a submitted review. AI-authored analysis is preparation, never independent approval.

**Complete reviewer packet:** Supply the exact selected protocol bytes and digest; the complete [predeclaration draft](PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md); the linked run manifest/provenance and boundary determination; and the full [review checklist](CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md). The current draft proposes: target `Open[T+2]/Open[T+1] - 1 >= 0.02`; one event per ticker/date on a recovered 149-symbol roster (coverage/delistings limitation); retrospective LogisticRegression Arm A vs B increment; chronological 2023/2024/2025 folds, training signal date and label exit before validation-year start; pooled paired OOF ROC-AUC delta as primary and Brier/ECE calibration margins; proposed margins AUC point delta ≥0, paired 95% lower endpoint ≥−0.01, Brier degradation ≤+0.005, ECE degradation ≤+0.02, all years present; proposed four-calendar-week circular paired moving-block bootstrap, seed 42, 1,000 draws, with implementation equivalence unverified; local ECE bins `[0,.1), …, [.9,1]`, empty bins skipped and occupancy weighted, protocol match unverified; one fixed contrast/no search; stop on missing, invalid, mismatched, unauthorized, or uncertain-boundary inputs; and retrospective exposure of 2025/OOF. The draft does **not** establish the correct null/alternative, multiplicity family/control, resampling validity for the dependence/group structure, confirmatory interpretation, or exact v1.0.2 method match. Reviewer must explicitly accept/revise/reject/not-determine hypotheses and every split/purge, metric, uncertainty, multiplicity, stopping, missingness, exposure, and assumption; no unknown may be defaulted.

**Reviewer assessment required:** The reviewer personally evaluates temporal dependence, group structure/common shocks, exchangeability or sign-symmetry assumptions when applicable, p-value/interval validity, multiplicity, split/purge design, metric/calibration definitions, missingness/stopping/one-use rules, exposure, and non-claims; explicitly accepts, revises, rejects, or marks not determinable. The reviewer must be independent of implementation, data production, and outcome access. AI-generated preparation is not independent review.

**Closure evidence:** Reviewer-authored report with identity/qualifications/affiliation, independence and conflict statement, exact protocol/predeclaration digests, assumptions, findings, limitations, recommendation, blocking issues and dissent, authenticated sign-off; owner’s separate disposition.

**Reviewer and record:** `[PENDING]`

## B3 — Determine data boundary (owner/data steward; reviewer checks leakage)

**Exact question:** From authoritative governance/provenance evidence only, identify permitted input IDs/versions and operations, exclusions, exposure history, and protected boundary. Does the prior manifest-backed test read of only the header of the staged development event-table copy fit the approved development boundary? Do not inspect restricted contents to answer.

Options: **D1 defer all real-data use; D2 issue a source-cited allowlist/denylist and explicitly resolve the header-only fixture question; D3 reject the proposed source/operation.** None permits access by itself. The historical 2025/OOF strata are disclosed as previously exposed. The steward's decision must identify permitted input IDs/versions and operations; exclusions for OOF/evaluation/holdout assets; temporal, group, maturity, purge/embargo, and prior-exposure rules; whether the previously disclosed header-only read of the staged dev fixture was permitted; and future test-fixture restrictions. Use authoritative governance records only—do not infer permission from paths/names or from not seeing rows. If authority is insufficient, record the boundary unresolved and keep B3 blocked.

**Closure evidence:** Authenticated, dated, cited owner/data-steward determination naming exact permitted datasets/operations, denied scopes, temporal/group/maturity/purge boundary, prior exposure, fixture-header ruling, copies/network/retention controls, and confirmation that restricted contents were not consulted; independent reviewer accepts or marks not determinable.

**Owner/data-steward determination and reviewer response:** `[PENDING]`

## B5 — Freeze the complete predeclaration (owner + reviewer)

**Exact question:** After B1–B3, will the owner and reviewer accept one complete plan, tied to the exact protocol and boundary digests, before any authorized data operation? Options: defer; revise this draft; or replace it with a new version. No current contrast or method is approved.

**Required contents before a digest can be frozen:** target and estimand; primary hypothesis and contrast/sign; temporal splits, label maturity, group structure, purge/embargo; permitted data IDs/operations and exposure boundary; primary and secondary metric definitions and thresholds; uncertainty method, dependence unit, calibration/ECE conventions and code equivalence; multiplicity family/control; missingness, invalid resamples, stopping, retries, one-use, deviations and inconclusive rules; allowed outputs, path/network/copy controls, exclusions and explicit non-claims. Each must be resolved by the responsible owner/reviewer; do not freeze placeholders as approvals. Then the owner and reviewer must independently accept the exact same immutable predeclaration digest tied to the chosen protocol and data-boundary digests. The v1.0.2 primary-contrast mismatch, local ECE convention, bootstrap equivalence, retrospective exposure, multiplicity, temporal/group dependence, exchangeability/sign-symmetry and p-value validity, and protected boundary remain unresolved in the existing draft. Reviewer handoff: [independent-review checklist](CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md) and [predeclaration draft](PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md); requested reviewer-authored report must cite the exact protocol and declaration hashes, qualifications, independence/conflicts, assumptions, findings, limitations and recommendation. Assess serial dependence, cross-sectional/group structure, common shocks, overlapping folds, block/resampling unit, exchangeability or sign symmetry if used, p-value/interval validity, and multiplicity. AI preparation is not the review.

**Closure evidence:** Frozen document SHA-256; independent reviewer report against that exact hash; separate owner acceptance naming the same hash and exclusions. Any mismatch or unresolved assumption keeps B5 open.

## B4 — Record exact owner authorization (owner only, after prerequisites)

**Exact question:** Defer/reject all operations, allow preparation/review only, or authorize one precisely named operation after B1–B3/B5 and B2 are complete? No bundled evaluation, integration, or launch authorization. A future launch/integration decision is separate.

**Required authentic record:** Owner identity and authentication; date/time; exact operation, campaign/scope/protocol/predeclaration/data digests, paths and outputs; permitted and prohibited actions; no-holdout/no-network/copy constraints; expiry/revocation; and explicit statement that launch/integration is not granted unless separately stated. Trust evidence must be provisioned through the governed mechanism, not fabricated in this packet.

**Owner choice and record URI/hash:** `[PENDING]`

## B7 — Define legacy-script scope before any remediation (owner)

**Exact question:** Are these standalone paths within the future C5 operation boundary? Static audit found direct study/build/train entrypoints outside the autonomous preflight; none was run. Options: (E1) declare out of scope only with enforceable operational data separation; (E2) name scripts and authorize a bounded fail-closed wrapper/entrypoint design; (E3) prohibit their C5 use and name a separately reviewed implementation. Do not edit them before this decision.

Identified paths: `study_files/backend/demand_zone_study_v1.py`, `build_hold1_targets.py`, `build_v2_dataset.py`, `build_v3_dataset.py`, `build_v5_dataset.py`, `train_hold1.py`, `train_v2.py`, `train_v3.py`, `train_v4.py`, `train_v5.py`, `train_v7.py`, and feature helpers `v2_features.py`, `v4_features.py`. These were identified by static audit; none was executed. Choose: **L1 prohibit these paths for the exact C5 operation** (and state enforceable operator/data separation); **L2 define documented operational separation and controls** with evidence that protected data cannot reach those paths; or **L3 identify exact in-scope paths and authorize narrowly scoped fail-closed enforcement changes plus inert tests**. Name each path and operation; do not authorize a blanket repository rewrite. Engineering must not modify these scripts until the owner records this scope decision.

**Closure evidence:** Owner record classifies each path/command and data boundary, states permitted changes or separation controls; after authorization, engineering supplies inert per-path denial tests and current suite result. No claim of repository-wide coverage before then.

**Owner choice/rationale/exact paths and authenticated record:** `[PENDING — L1/L2/L3; path-by-path scope, controls, rationale, date and record URI/hash]`

## B6 — Current development-suite verification (engineering; not an authorization gate)

The isolated dev root collected **520 tests** (pytest 9.1.1; no pytest root configuration/conftest). The post-change complete default selection and all assertions were preserved: `timeout 1800s py -3 -m pytest -vv --durations=10` from `.model_discovery_workspace/dev/`; **520 passed, 26 subtests passed, 0 failed, 0 skipped in 756.82s**, exit 0. Persistent output: [current post-fix suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log). Earlier host-interrupted runs during slow subprocess E2E tests produced diagnostic failures/timeouts; they are retained in the linked logs but superseded by the later complete exit-0 run. No parallelism, test selection changes, skipped tests, or assertion weakening was used. Human decisions remain pending and no C5 operation is authorized.

## B6/B7 status and next engineering step

B6 (current 520-test development suite) is closed by the complete post-change run above. This does **not** close the separate legacy-path scope issue: B7 remains blocked until the owner chooses whether each identified standalone study/build/train entrypoint is prohibited for C5, covered by enforceable operational separation, or in scope for narrowly authorized fail-closed changes and inert tests. No such script has been run or modified.

## Decision record — leave blank until humans complete it

- Owner identity/role; decision IDs, rationale, date/time/timezone: `[PENDING]`
- Protocol, boundary, predeclaration and scope digests covered: `[PENDING]`
- Owner-authored authenticated record URI/hash and expiry/revocation: `[PENDING]`
- Independent reviewer identity, conflicts, report URI/hash and owner disposition: `[PENDING]`
- Explicit excluded actions (real-market evaluation, OOF scoring, holdout access, candidate activation, integration, launch): `[PENDING]`

**Current effect:** None. All human decisions remain pending. No C5 data access or execution is authorized. A passing preflight or complete engineering suite establishes neither authentic approval nor method validity. **NOT AUTHORIZED — DO NOT RUN.**
