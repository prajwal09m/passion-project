# Campaign 5 Final Blocker Closure Report — Superseded Historical Record

**Canonical handoff:** [CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md). This earlier report predates the final evaluator validation change and is retained as history only; if anything differs, the coordinated handoff and linked post-change evidence are authoritative.

**Historical engineering status: COMPLETE FOR THE THEN-CURRENT SUITE — HUMAN DECISIONS PENDING**

**Campaign 5 is NOT AUTHORIZED. No campaign was launched.** This handoff authorizes no market evaluation, OOF scoring, production integration, restricted-data access, holdout access, or execution.

## Blocker status

| Blocker | Status | Closure evidence / responsible party |
|---|---|---|
| **B1 Protocol/version/scope** | **OPEN — owner** | Owner selects purpose and exact protocol artifact/digest; documents every C4→C5 scientific/policy difference. Reviewer assesses same digest. |
| **B2 Independent review** | **OPEN — owner + independent reviewer** | Owner appoints qualified non-implementing reviewer; reviewer-authored authenticated report, independence/conflict statement, exact protocol/predeclaration digests, findings and owner disposition. AI material is preparation only. |
| **B3 Data boundary** | **OPEN — owner/data steward** | Source-cited input/operation allowlist and exclusions; resolve staged development-copy header-only read from governance evidence without inspecting restricted contents; reviewer assesses leakage/boundary. |
| **B4 Owner authorization** | **OPEN — owner** | Authentic dated authorization for one exact operation, with protocol/predeclaration/data/scope hashes, allowed outputs, exclusions, expiry/revocation. Separate later launch decision required. |
| **B5 Predeclaration** | **OPEN — owner + reviewer** | Freeze complete declaration matching selected protocol and boundary; reviewer and owner accept the same digest. Hypotheses, split/purge, metrics, uncertainty, multiplicity, stopping/missingness, exposure, outputs and non-claims must be resolved. |
| **B6 Full development-suite verification** | **VERIFIED CLOSED — historical baseline** | Pre-final-edit suite from isolated dev root: 518 passed, 26 subtests, 0 failed/skipped, 293.88s, exit 0 using `timeout 1200s py -3 -m pytest -vv --durations=10`. Current post-change verification is 520 passed + 26 subtests, 0 failed/skipped, 756.82s, exit 0; see [canonical closure](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md) and [current suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log). |
| **B7 Execution-path scope** | **PARTIALLY GUARDED; OPEN — owner** | Autonomous supervisor/loop/adapter boundaries are tested for denial, but standalone study/build/train scripts remain outside the gate. Owner must classify scope and authorize any bounded remediation before edits. |

B1–B5 require authentic human decisions; engineering cannot close them. The former 518-test result is historical; current B6 is closed by the 520-test post-change run. B7 remains blocked pending the owner's scope decision; repository-wide execution coverage is not established.

## Protocol choice: evidence, not a recommendation of version

The v1.0.1 output manifest records `DZAI-MARKET-STRUCTURE-ABLATION-V1` and digest `486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07`; a distinct authoritative v1.0.1 source artifact is not available in this checkout. The current v1.0.2 artifact is pinned at SHA-256 `6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05`. v1.0.2 lists historical primary contrasts LightGBM-A−LogisticRegression-A and LightGBM-C−LightGBM-B; within-estimator B−A is secondary. It labels historical folds pre-lock/retrospective and separately describes a prospective design using eight frozen models, no retraining, up to 2,000 predictions, a 12–18 month window, and no result-dependent stopping.

The existing draft instead proposes a retrospective LogisticRegression A→B contrast on previously exposed 2023–2025 OOF strata. That is not a v1.0.2 primary contrast. The draft’s target is `Open[T+2]/Open[T+1] - 1 >= 0.02`; folds are chronological with label-maturity purge; pooled paired OOF AUC delta is proposed as primary with Brier/ECE margins; the proposed uncertainty is a 1,000-draw seed-42 four-week circular paired moving-block bootstrap. Its ECE convention and bootstrap equivalence to the pinned producer remain unverified. These designs differ in estimand/exposure/data and must be chosen by the owner and assessed by the independent reviewer. No real-market evaluation was used to choose.

The [owner decision sheet](CAMPAIGN5_OWNER_DECISION_PACKET.md) gives the options/tradeoffs: defer/stop; obtain authoritative v1.0.1 source and assess lineage; propose a v1.0.2-aligned prospective study; or create a separately versioned retrospective amendment. It recommends deferral only as the conservative current posture, not as a campaign choice or approval.

## Engineering work actually performed

- Implemented/used a fail-closed C5 signed-authorization preflight at direct experiment adapter, baseline reproduction/establishment, continuous-loop startup/cycle/direct execution, and supervisor runner boundary. It binds campaign, scope, protocol, boundary, predeclaration, approvals, expiry/status/revocation and audit. Runtime has no authoritative record/trust keys and therefore blocks C5.
- Added inert synthetic denial tests covering supervisor injected runner, adapter direct/repeated serialized specs, reproduction CLI/API, baseline establishment, continuous-loop CLI/direct cycle/direct phase/restart and audit-write failure. Tests assert blocked work does not start. No positive authoritative C5 execution was attempted.
- Preserved development-only candidate identity improvements; synthetic matrix and subprocess determinism checks pass. Candidate search remains disconnected from production.
- Static audit identified legacy paths; no legacy scripts were edited because owner scope is unresolved.

## Fresh verification and limitations

**Passing targeted evidence:**
- Repository root command: `py -3 -m py_compile autonomous_agent/campaign5_authorization.py autonomous_agent/test_campaign5_authorization.py autonomous_agent/continuous_loop.py autonomous_agent/core.py autonomous_agent/experiment_adapter.py` — exit 0. Then `timeout 120s py -3 -m pytest -q autonomous_agent/test_campaign5_authorization.py autonomous_agent/test_experiment_adapter.py autonomous_agent/test_core.py autonomous_agent/test_continuous_loop.py autonomous_agent/test_stage5_readiness_safety_contract.py` — **79 passed + 4 subtests in 11.15s**, exit 0 (2026-10-18 13:20:33–13:20:45 `-04:00`). Log: [final targeted tests](CAMPAIGN5_FINAL_TARGETED_TESTS.log).
- Isolated dev root: `py -3 -m py_compile autonomous_agent/proposal_layer/candidate_search_v2.py autonomous_agent/test_candidate_search_v2.py` and `timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py` — **16 passed in 2.71s**, compile and pytest exit 0. Log: [identity tests](CAMPAIGN5_CURRENT_IDENTITY_TESTS.log).
- Fresh `py -3 -m pytest --collect-only -q` from isolated dev root: **518 tests collected**, exit 0. An earlier `-vv --durations=10` diagnostic preserved the same selection; 486 visible passes before exit 124 at 720s, no summary. That attempt is superseded by the complete run below.
- Earlier bounded E2E diagnostics: 31 selected non-production E2E tests passed in 165.99s, exit 0; separate production-entrypoint class 7/7 passed in 381.12s, exit 0. These are subsets/historical runtime evidence.

**Full suite — final result:**
- Existing pre-sync run: `timeout 720s py -3 -m pytest -q` from `.model_discovery_workspace/dev/`, 12:18:55–12:30:56 `-04:00`, exit 124 at 92% and no summary. A further 13:27:56–13:39:56 full run reported failures and ended exit 124; root cause of early failures was absent staged fixture module, with remaining current results then incomplete.
- After fixture synchronization, the adjacent dev-root suite passed 65 tests + 4 subtests (historical); repo-root targeted suite including C5 authorization tests passed 79 + 4. Fresh final checks: repo-root compile passed; `timeout 120s py -3 -m pytest -q` on authorization/adapter/core/loop/safety tests passed **79 + 4 subtests in 11.06s**; isolated candidate identity tests passed **16 in 2.14s** with compile exit 0.
- Complete current isolated full suite: `timeout 1200s py -3 -m pytest -vv --durations=10`, 2026-10-18 15:07:55–15:12:50 `-04:00`, **518 passed + 26 subtests, no failures/skips, 293.88s, exit 0**. Full log: [coordinated suite](CAMPAIGN5_COORDINATED_FULL_SUITE.log). This supersedes prior incomplete timeout attempts for current full-suite status.
- Final complete run from `.model_discovery_workspace/dev/`: `timeout 1200s py -3 -m pytest -vv --durations=10`, start 15:07:55 and end 15:12:50 `-04:00`, **518 passed, 26 subtests passed, 0 failed, 0 skipped in 293.88s**, exit 0. Full log: [coordinated full suite](CAMPAIGN5_COORDINATED_FULL_SUITE.log).
- Earlier bounded timeouts and isolated 141s/175s refit reruns are retained as runtime diagnosis only. On the successful complete run, the horizon/purge calls took about 36s each, showing variable runtime. No test selection/assertion/code change or parallelism was needed; no hang was established.

No tests were removed, skipped deliberately, or weakened. No test timeout was altered to claim success. No campaign, market evaluation, OOF metric/scoring, production integration, or holdout operation was performed.

## Execution paths and remaining coverage gaps

**Inert denial checks cover:** supervisor injected runner; continuous-loop CLI startup, direct `cycle_once`, `phase_execute_one`, restart; direct adapter `run_experiment`, serialized retry, `reproduce` CLI/API, and `establish-baseline` API. Tests check that executor/command factory/recovery are not called, no loop lock is created on denial, and no experiment workspace is created. Resume recovery only reconciles an existing durable result; no experiment restart was run. No signed allowed C5 path can be tested without authentic human records. The isolated dev fixture now contains the same C5 authorization module; its targeted adjacent integration tests passed after sync.

**Not covered until B7 scope decision:** standalone `study_files/backend/` paths `demand_zone_study_v1.py`, `build_hold1_targets.py`, `build_v2_dataset.py`, `build_v3_dataset.py`, `build_v5_dataset.py`, `train_hold1.py`, `train_v2.py`, `train_v3.py`, `train_v4.py`, `train_v5.py`, `train_v7.py`, and support modules `v2_features.py`, `v4_features.py`. Static audit found direct main/fit/build paths outside the autonomous adapter. They were not run. This is a concrete possible bypass if an operator invokes them against sensitive data. Owner must decide whether each is in scope and authorize either enforceable separation, named controls, or prohibited use. Do not claim repository-wide protection.

## Integrity and data boundary

- Fresh recheck of the existing 11-entry protected Campaign 4 SHA-256 manifest: **11/11 match**. Frozen C4 config/sidecar, ledgers/state, launch gates, decision artifacts and archive integrity records are unchanged.
- Blocker-register JSON parses successfully; `git diff --check` passes. No C4 protected record is treated as C5 approval.
- No real-market evaluation, model fitting, OOF scoring/metric operation, sealed holdout access, campaign integration, or launch occurred. Disclosure: a prior manifest-backed test read only the header of the staged development event-table copy; no rows were used for fitting/scoring. Whether that read is permitted remains unresolved for the owner/data steward. Governance metadata and protocol text were inspected. No holdout contents were opened, listed, hashed, queried, or copied. The boundary question cannot be resolved without authoritative governance evidence.

## Exact human decisions, in order

1. **Owner — B1:** choose/defer the study purpose and exact protocol bytes/digest; resolve v1.0.1 lineage vs v1.0.2 scope, record C4→C5 deltas. Do not select solely by recency.
2. **Owner — B2:** appoint an independent qualified reviewer. **Reviewer:** assess the exact protocol and full predeclaration packet (hypotheses, target/contrast, splits/purge, exposure, metrics/margins, uncertainty and ECE conventions, multiplicity, stopping, missingness, assumptions and non-claims); give authenticated findings against exact digests. AI preparation is not sign-off.
3. **Owner/data steward — B3:** provide source-cited permitted input/operation allowlist, exclusions, boundary and exposure determination; explicitly rule on the fixture-header access without inspecting restricted contents. Reviewer assesses leakage/dependence and can mark not determinable.
4. **Owner + reviewer — B5:** revise/freeze a complete predeclaration matching protocol and boundary; reviewer report and owner acceptance must name the same hashes.
5. **Owner — B7:** classify every legacy path above and authorize bounded controls or enforceable separation/prohibition. Only then may engineering make scoped changes and test inert denial paths.
6. **Owner — B4:** after prerequisites, record separate authentic authorization for one exact operation with protocol/predeclaration/data/scope hashes, permitted outputs, exclusions, expiry and revocation. A further explicit launch/integration decision remains separate. Engineering B6 is closed by the complete 518-test run documented above.

**Canonical status:** This historical report is superseded by [CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md), which records the current complete 520-test post-change suite and is the controlling final handoff.

## Canonical evidence

- [Owner decision sheet](CAMPAIGN5_OWNER_DECISION_PACKET.md)
- [Independent-review checklist](CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md)
- [Protocol/predeclaration draft](PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md)
- [Blocker register](CAMPAIGN5_BLOCKER_REGISTER.md) and [machine-readable register](CAMPAIGN5_BLOCKER_REGISTER.json)
- [Execution-path audit](CAMPAIGN5_EXECUTION_PATH_AUDIT.md)
- [Preflight tests](CAMPAIGN5_PREFLIGHT_TEST_REPORT.md), [timeout diagnosis](CAMPAIGN5_TEST_TIMEOUT_DIAGNOSIS.md), and [candidate identity validation](CAMPAIGN5_CANDIDATE_IDENTITY_VALIDATION.md)
- [Final integrity audit](CAMPAIGN5_FINAL_INTEGRITY_AUDIT.md)
- [Final targeted test log](CAMPAIGN5_FINAL_TARGETED_TESTS.log), [identity test log](CAMPAIGN5_CURRENT_IDENTITY_TESTS.log), [prior timeout diagnostic](CAMPAIGN5_DIAGNOSTIC_FULL_SUITE_FINAL.log), and [final complete coordinated run](CAMPAIGN5_COORDINATED_FULL_SUITE.log)

**No campaign was launched.** The preflight blocks absent authentic records. Full engineering suite verification is complete; legacy-path scope, protocol, independent review, data boundary, predeclaration, and exact owner authorization remain pending.

**ENGINEERING COMPLETE — HUMAN DECISIONS PENDING**
