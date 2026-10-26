# Campaign 5 — Final Coordinated Closure

**Canonical final handoff.** This report supersedes the earlier [verification sprint](CAMPAIGN5_FINAL_VERIFICATION_SPRINT.md) and [blocker closure report](CAMPAIGN5_FINAL_BLOCKER_CLOSURE_REPORT.md) where they reflect prior incomplete suite attempts.

**ENGINEERING COMPLETE WITHIN THE PERMITTED DEVELOPMENT SCOPE — HUMAN DECISIONS PENDING**  
**Campaign 5 remains NOT AUTHORIZED. DO NOT LAUNCH.** No real-market evaluation, restricted evaluation-data access, market-data training, OOF scoring, holdout access, production integration, or campaign execution was performed. Engineering verification grants no human approval.

## Final post-change engineering verification

The development-only temporal evaluator now rejects duplicate training/validation indices, duplicate feature IDs, and multidimensional index arrays. Without these checks, duplicate row IDs could silently give observations repeated weight and malformed split membership could pass downstream. Synthetic regression cases were added in [candidate_search_v2 tests](dev/autonomous_agent/test_candidate_search_v2.py). Candidate search/evaluation remain disconnected from production.

| Check | Exact command from `.model_discovery_workspace/dev/` | Result |
|---|---|---|
| Syntax + focused regressions | `py -3 -m py_compile autonomous_agent/proposal_layer/candidate_search_v2.py autonomous_agent/test_candidate_search_v2.py && timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py` | Final verification after handoff edits: compilation exit 0; **18 passed in 3.42s**, pytest exit 0. |
| Current test collection | `py -3 -m pytest --collect-only -q` | **520 tests collected in 1.27s**, exit 0. |
| Complete current dev suite | `timeout 1800s py -3 -m pytest -vv --durations=10` (persistent run; full output retained at [post-fix full-suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log)) | **520 passed, 26 subtests passed, 0 failed, 0 skipped in 756.82s**, exit 0. This ran after the final evaluator edit. |
| Integrity / authorization / isolation | Recomputed protected manifest; parsed blocker-register JSON and checked all four C5 authorization flags; searched production `autonomous_agent/` for candidate selector imports; `git diff --check` | **11/11 protected SHA-256 matches**; market evaluation, integration, execution and holdout authorization all `false`; no production candidate-search reference found; whitespace check exit 0. |

**Runner diagnostics:** earlier attempts bounded by the synchronous host call were interrupted during slow Windows subprocess E2E tests; their child processes reported Windows `0xC000013A`/empty-stderr artifacts, producing incomplete runs (recorded in [first diagnostic](CAMPAIGN5_POST_FIX_FULL_SUITE.log), [second diagnostic](CAMPAIGN5_POST_FIX_FULL_SUITE_FINAL_TIMEOUT.log), and [E2E diagnostic](CAMPAIGN5_POST_FIX_E2E_CLASS_TIMEOUT.log)). They are not the final result. The subsequent persistent run used a sufficiently long external bound, completed all tests with exit 0, and supersedes those attempts. No test/assertion was skipped, weakened, removed, or parallelized.

The earlier **518 passed + 26 subtests** full-suite result is pre-change historical evidence. The current 520-test exit-0 run is the authoritative post-change result. Campaign 5 remains unauthorized independently of engineering verification; B1–B5 and B7 remain unresolved human/governance blockers.

## Prior baseline evidence
The earlier 518-test suite completed before the final candidate-evaluator validation change; it is retained below only as historical context.

### Prior engineering verification — Track A (all results below predate final evaluator edit)

| Check | Exact command / evidence | Result |
|---|---|---|
| Collection before latest fix | From `.model_discovery_workspace/dev/`: `py -3 -m pytest --collect-only -q` | **518 tests collected in 1.16s**, exit 0. |
| Full suite before latest fix | From `.model_discovery_workspace/dev/`: `timeout 1200s py -3 -m pytest -vv --durations=10` | Start 2026-10-18 15:07:55 `-04:00`; end 15:12:50; elapsed 293.88s; exit **0**. Summary: **518 passed, 26 subtests passed, 0 failed, 0 skipped**. Full verbose log: [coordinated full-suite run](CAMPAIGN5_COORDINATED_FULL_SUITE.log). |
| Prior authorization regression + syntax | Repo root: compile of auth/continuous-loop/core/adapter touched files and targeted tests | Compile exit 0; **79 passed + 4 subtests**, exit 0. |
| Prior candidate identity suite + syntax | From isolated dev root | Compile exit 0; **16 passed**, exit 0. |
| Final integrity after this handoff | `.c4_protected_hashes_before.json`; current blocker JSON; C5 authorization flags; production candidate-search import scan; `git diff --check` | **11/11 protected hashes match**; authorization flags false; no production-tree candidate-search reference; `git diff --check` exit 0. |

The earlier host-interrupted post-change runs are not the final result. Their stderr/return-code artifacts reflect Windows child-process interruption under the synchronous host limit; the later persistent complete run is the authoritative current verification. Do not infer success from partial progress. No test selection or assertion was changed.

## Cross-referenced evidence status

The [blocker register](CAMPAIGN5_BLOCKER_REGISTER.md), [owner packet](CAMPAIGN5_OWNER_DECISION_PACKET.md), [execution-path audit](CAMPAIGN5_EXECUTION_PATH_AUDIT.md), and [final integrity audit](CAMPAIGN5_FINAL_INTEGRITY_AUDIT.md) now reflect the 520-test current result. Earlier verification-sprint and timeout-diagnosis documents describe prior 518-test / runtime history and are explicitly historical, not current completion evidence. The [final owner handoff](CAMPAIGN5_FINAL_HANDOFF.md) is the concise entry point.


### Historical baseline logs

The 518-test coordinated run is retained at [historical suite log](CAMPAIGN5_COORDINATED_FULL_SUITE.log). The post-change run and the earlier host-interrupted diagnostics are listed above and in the cross-referenced evidence register.

## Authorization enforcement and legacy gap

The fail-closed C5 preflight denies when the authorization record or trust keys are absent/unavailable, approval/signature is invalid or malformed, reviewer independence/qualification fails, authorization is revoked/expired, or protocol, predeclaration, data boundary, operation, identity, and scope digests do not match. Static wiring is present at:

- Autonomous supervisor runner (`core.py`).
- Continuous-loop startup, cycle, direct execution phase, and restart (`continuous_loop.py`).
- Direct experiment adapter, reproduction, and baseline-establishment paths (`experiment_adapter.py`).

Existing inert synthetic tests exercise missing/invalid/revoked/mismatched authorization, audit-write failure, direct/retried adapter specs, supervisor/custom-runner denial, continuous-loop cycle/execution/restart denial, reproduction CLI/API, and baseline-establishment denial. The current full-suite run and the previously completed targeted authorization suite passed. No positive production execution or fabricated approval fixture was used to authorize a real runner.

**Coverage limitation:** standalone legacy study/build/train scripts remain outside the C5 preflight and were not run or modified. Owner must decide whether they are prohibited, operationally separated, or in scope for narrowly authorized fail-closed changes. Do not claim repository-wide execution protection. Candidate search remains development-only and disconnected from production; a code search found no `candidate_search_v2` import/reference in the production `autonomous_agent/` tree.

## Integrity and boundary

- Protected Campaign 4 baseline: **11/11 exact SHA-256 matches**. The protected frozen configuration/sidecar, historical records, ledgers/state, launch gates, and archive-integrity entries remain unchanged.
- Latest syntax/focused checks pass; the complete current suite passed 520 tests + 26 subtests (exit 0). `git diff --check` passes. Protected Campaign 4 hashes are 11/11 unchanged; C5 operation flags remain false. Existing unrelated checkout changes (`.gitignore`, `README.md`, and pre-existing untracked project material) were preserved; nothing was staged, committed, reset, or cleaned up.
- No campaign launch, real-market evaluation, market-data model training, OOF scoring, holdout operation, or production integration occurred. E2E regression tests used the existing disposable synthetic fixtures only.
- **Unresolved boundary disclosure:** an earlier manifest-backed scaffolder test read only the header of the staged development event-table fixture. No rows were used for fitting/scoring. Whether that header-only read was within the intended permitted-data boundary must be determined by the owner/data steward from authoritative governance evidence. This sprint did not inspect restricted contents to resolve the question. Future test-fixture policy also needs the steward's decision.

## Human decision table — all pending

| Blocker | Exact decision needed | Responsible role | Required evidence to close | Status |
|---|---|---|---|---|
| **B1 Protocol** | Select exactly one immutable C5 protocol and scope, or explicitly defer; resolve v1.0.1/v1.0.2 mismatch and C4→C5 deltas. | Owner | Authenticated dated record naming exact artifact and SHA-256, rationale, scope, and accepted/rejected/deferred changes. | **OPEN** |
| **B2 Independent review** | Appoint a qualified reviewer genuinely independent of implementation/data production/outcome access; reviewer assesses exact protocol + predeclaration. | Owner appoints; reviewer authors | Reviewer-authored report with identity/qualifications, affiliation, independence/conflict statement, exact reviewed digests, assumptions/findings/limitations/recommendation. Explicitly assess temporal/group dependence, exchangeability/sign symmetry where applicable, p-value/interval validity, and multiplicity. | **OPEN** |
| **B3 Data boundary** | Decide permitted input IDs/operations, excluded evaluation/OOF/holdout assets, temporal/group/maturity/purge rules, exposure history, header-only fixture ruling, and future fixture restrictions. | Owner/data steward; reviewer assesses boundary | Source-cited authoritative determination; do not inspect restricted contents. If authority is insufficient, record unresolved and keep access blocked. | **OPEN** |
| **B5 Predeclaration** | Settle target/estimand, hypothesis/contrast, splits/purge, data/exposure boundary, metrics, uncertainty/calibration conventions, multiplicity, missingness/stopping/one-use, output/exclusion/non-claim rules. Freeze and approve the same digest. | Owner + reviewer | Final immutable predeclaration hash tied to selected protocol and boundary digests; reviewer report and owner acceptance name the identical digest. Do not freeze placeholders as approvals. | **OPEN** |
| **B7 Legacy paths** | Classify each identified standalone study/build/train path as prohibited, protected by enforceable operational separation, or explicitly in scope for narrow enforcement. | Owner; engineering only after scope decision | Path-by-path scope and control record; only if authorized, inert denial tests after narrowly scoped code changes. | **BLOCKED — owner scope decision** |
| **B4 Exact operation authorization** | After B1–B3/B5 and B2, authorize or defer one exact operation. Evaluation permission is not production integration permission. | Owner | Authentic dated authorization binds exact operation/campaign/scope/protocol/predeclaration/data digests, outputs, exclusions, expiry/revocation. Separate later launch/integration decision required. | **OPEN** |
| **B6 Engineering suite** | Complete the current isolated development suite with full selection, summary, and exit status. | Engineering maintainer | Post-change `timeout 1800s py -3 -m pytest -vv --durations=10`: **520 passed, 26 subtests, 0 failed/skipped in 756.82s**, exit 0; [full log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log). | **CLOSED — engineering verification only** |

### Exact protocol artifacts presented to the owner

- Manifest lineage names v1.0.1 digest `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`; the authoritative v1.0.1 source bytes are not in this checkout, so that digest cannot currently be verified against the source artifact here.
- [v1.0.2 protocol](dev/study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json) SHA-256 `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05`. It identifies historical primary contrasts LightGBM-A−LogisticRegression-A and LightGBM-C−LightGBM-B, with within-estimator B−A secondary; describes prior historical folds as pre-lock/retrospective; and separately describes a prospective frozen-model design (eight models, no retraining, up to 2,000 predictions, 12–18 months). The existing draft proposes target `Open[T+2]/Open[T+1] - 1 >= 0.02` and a different retrospective LogisticRegression A→B comparison on previously exposed 2023–2025 OOF strata. The draft is not reconciled to either version: because the authoritative v1.0.1 source bytes are unavailable and the v1.0.2 target must be read from the selected artifact, target equivalence/difference remains unresolved. Its contrast, retrospective exposure, data, and temporal design differ from the v1.0.2 prospective design. The owner/reviewer must explicitly settle target/estimand; no claim is made that either choice improves AUC. Do not use an evaluation to choose protocol.
- Current [predeclaration draft](PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md) digest `a8e15c6b9ba2d14188d8933b8cbeb89755110aebc210d37ec5e6e6c63b27433a`; current dev-only [candidate-search proposal](dev/autonomous_agent/proposal_layer/protocol_amendment_v2.json) digest `d9ceb15b47e25b0b175f01b02b861277685d7b865e123afe114f0b6f62d5759e` (proposal only, not a C5 protocol). Recompute hashes for any modified final artifacts before review.

The already updated [owner decision packet](CAMPAIGN5_OWNER_DECISION_PACKET.md) contains the four B1 options, exact digest evidence, target/estimand reconciliation request, reviewer handoff requirements, data-steward request, B5 resolution list, B7 path options, B4 authorization requirements, and B6 latest outcome. The [independent review checklist](CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md) is a blank template, not an approval.

## Next actions — exact order

1. **Owner — B1:** choose one exact protocol artifact/digest or explicitly defer; do not select by recency or observed scores.
2. **Owner — B2 appointment:** appoint a qualified reviewer genuinely independent of implementation, data production, and outcome access.
3. **Owner/data steward — B3:** from authoritative governance records, document permitted inputs/operations, exclusions, temporal/group/maturity/purge rules, prior exposure, future fixture restrictions, and an explicit ruling on the staged-fixture header-only read. Do not access restricted contents; if not determinable, keep B3 blocked.
4. **Independent reviewer — B2 assessment:** review the selected protocol, current predeclaration draft, and B3 boundary against exact digests; personally assess dependence/group structure, exchangeability or sign symmetry where applicable, p-value/interval validity, multiplicity, and assumptions. Return authenticated findings, limitations, recommendation, and independence/conflict statement. AI preparation is not independent review.
5. **Owner + reviewer — B5:** settle every predeclaration element; freeze an immutable declaration aligned to the selected protocol and approved boundary; both accept the same digest. Do not freeze unresolved choices as approved.
6. **Owner — B7:** classify the legacy paths path-by-path as prohibited, operationally separated with enforceable controls, or in scope for narrowly authorized remediation. Engineering must not modify them before this scope decision.
7. **Owner — B4:** only after B1–B3, B2, B5, and B7 are addressed, record authentic authorization for one exact operation, binding protocol/predeclaration/data-boundary/scope digests, outputs, exclusions, expiry, and revocation. A later production integration/launch requires a separate explicit owner decision.

**Engineering verification is complete within the permitted development scope.** Remaining blockers are human protocol, independent-review, data-steward, predeclaration, owner authorization, and legacy-path scope decisions. Campaign 5 remains NOT AUTHORIZED; no action above authorizes evaluation or launch.

`ENGINEERING COMPLETE — HUMAN DECISIONS PENDING`
