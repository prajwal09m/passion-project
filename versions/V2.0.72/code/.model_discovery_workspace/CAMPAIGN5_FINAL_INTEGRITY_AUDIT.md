# Campaign 5 Preparation — Final Integrity Audit v1.0

**Status: Current post-change engineering suite verification complete; HUMAN/GOVERNANCE BLOCKERS REMAIN — NOT AUTHORIZED — NOT READY TO LAUNCH.** This audit includes earlier 518-test baseline records; current verification is the 520-test post-change suite. Prepared 2026-10-18.

## 1. Scope and boundary

This phase was limited to read-only governance/manifest review, synthetic fixture tests, and artifacts under `.model_discovery_workspace/` (including its isolated `dev/` subdirectory). No real-market evaluation dataset rows, OOF prediction rows/scores, sealed holdout, or prospective-evaluation contents were read, queried, copied, enumerated, trained on, or measured. **One bounded metadata access is disclosed:** the existing isolated dev suite includes a manifest-documented census scaffolder test that reads only the header of the staged development event-table fixture. Its provenance manifest classifies it as an allowlisted development/test fixture; no rows or metrics were consumed. Whether the owner considers even header-only access outside the intended boundary remains an unresolved interpretation, so no further event-table access is authorized by this package. No Campaign 5, production campaign, campaign integration, or statistical market evaluation was run.

Protected data/content boundary as specified by the request:
- `study_files/outputs/study_v1/prospective/` and any sealed/prospective equivalent: contents not accessed. Its absence in a current checkout or fixture is not evidence that the logical evaluation boundary is defined.
- `study_files/outputs/study_v1/development/oof_predictions.csv`: evaluation prediction contents were not read or used. Its path/hash may appear in pre-existing governance metadata; this preparation did not read prediction values.
- `study_files/outputs/study_v1/development/event_table.csv`: no data rows were read for analysis, fitting, or scoring. **Disclosure:** the full isolated dev pytest suite runs `test_census_manifest.ScaffolderTests`, whose documented `census.scaffold_manifest(TABLE)` reads the header of the staged copy under `.model_discovery_workspace/dev/`. The existing `FIXTURE_PROVENANCE.json` manifest classifies that copy as a retained development/test fixture; the test reads only schema/header metadata, not rows. No OOF predictions or market metrics were accessed. If the owner's intended boundary treats even this manifest-backed, header-only test read as prohibited, record it as a scope discrepancy; no further access was performed, and B3 remains unresolved.
- Campaign histories, candidate outputs, frozen config, signed decisions, owner records, and launch gates: no writes/changes were made by this task. Existing governance text and metadata were consulted as permitted evidence; no historical outcome was modified.

Permitted development roots used: `.model_discovery_workspace/` and `.model_discovery_workspace/dev/`. The isolated fixture provenance file says it stages allowlisted development/provenance artifacts and excludes prospective/holdout. Individual tests use fresh temporary synthetic datasets and synthetic OHLCV only.

**Boundary limitation:** Exact boundary membership, disjointness, and whether any historical result period should be treated as final evaluation cannot be established from the available path/hash metadata without owner/data-steward attestation. This remains B3 and no data access was used to resolve it.

## 2. Protected-path hash audit

Before/after hashes are taken from the already-existing `.c4_protected_hashes_before.json` manifest, which records 11 Campaign 4 protected paths. The audit script below verifies the exact recorded hashes for those paths only. It does not traverse, inspect, or hash holdout/prospective directories or evaluation/OOF artifacts. It reports missing or mismatched entries as failures.

Protected categories in the manifest include the frozen Campaign 4 config and sidecar, proposal ledger, loop state, experiment registry, campaign-end multiplicity record, launch gates, unsigned H-10 decision record, owner decision record, and Campaign 4 archive integrity file. No entry is reinterpreted as Campaign 5 approval.

Executed from repository root after deliverables were written (the manifest is a simple mapping of relative path to SHA-256):

```bash
py -3 - <<'PY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('.c4_protected_hashes_before.json').read_text(encoding='utf-8'))
rows = []
for relative, expected in manifest.items():
    path = Path(relative)
    if not path.is_file():
        rows.append((relative, 'MISSING', expected))
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    rows.append((relative, actual, expected))
for relative, actual, expected in rows:
    print(f'{relative}\\t{actual}\\t{expected}\\t{"OK" if actual == expected else "MISMATCH"}')
if len(rows) != 11 or any(actual != expected for _, actual, expected in rows):
    raise SystemExit(1)
print(f'VERIFIED {len(rows)} protected file hashes')
PY
```

**VERIFIED FACT:** 11/11 protected file hashes matched exactly; no missing or mismatched entries. The command exited 0. It read/hash-checked only the 11 allowlisted paths and did not traverse, inspect, or hash holdout/prospective/evaluation/OOF files.

## 3. Current verification results

| Check | Result | Evidence |
|---|---|---|
| Isolated E2E production-entrypoint section (historical) | **PASS** — 7 tests passed in 381.12s, exit 0, bounded by 540s | [E2E log](dev/phase5b_e2e_repro.log) |
| Initial full isolated dev pytest suite (historical) | **PASS** — 515 passed, 26 subtests, 334.69s, exit 0, bounded by 720s | superseded by latest run below |
| Historical full isolated dev pytest suite after identity refinement | **PASS (historical)** — 517 passed, 26 subtests, 540.27s, exit 0, bounded by 720s | [Historical full suite log](dev/phase5b_full_suite_repro.log) |
| Historical full-suite run before final evaluator edit | **PASS** — all 518 selected, 518 passed + 26 subtests, 0 failed/skipped, 293.88s, exit 0; serial verbose run | [Historical coordinated suite log](CAMPAIGN5_COORDINATED_FULL_SUITE.log) |
| Current full-suite run after final evaluator edit | **PASS** — 520 passed + 26 subtests, 0 failed/skipped, 756.82s, exit 0 | [Current post-fix suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log) |
| Fresh final authorization-focused suite + compilation | **PASS** — 79 passed, 4 subtests, pytest elapsed 11.15s; syntax compilation exit 0 | [Final targeted log](CAMPAIGN5_FINAL_TARGETED_TESTS.log) |
| Current candidate-evaluator suite + compilation | **PASS** — 18 passed, compilation exit 0 | [Candidate validation report](CAMPAIGN5_CANDIDATE_IDENTITY_VALIDATION.md); current result also recorded in [canonical closure](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md) |
| Earlier full suite after malformed-input regressions (historical) | **PASS** — 517 passed, 26 subtests, 263.30s, exit 0 | Prior completed run; runtime varied substantially on shared runner. |
| Candidate search/ranking/research memory focused tests after malformed-input fix | **PASS** — 34 passed, 2.33s; compile exit 0; bounded by 120s | [Focused test log](dev/phase5_focused_tests.log) |
| `git diff --check` | **PASS** — exit 0 | Final full-worktree whitespace check after sprint report edits. |
| Candidate identity regression + compilation after identity update (historical) | **PASS** — 15 passed, 1.96s; compilation exit 0 | [Identity test log](dev/phase5_candidate_identity_tests.log) |
| Synthetic candidate-catalog identity count | **PASS engineering check** — 360 generated raw configurations, 264 canonical identities, 96 duplicates removed; no predictive claim | Reproduce with command in Section 5 |
| Protected 11-file SHA-256 manifest | **PASS** — 11/11 match | Fresh recheck executed after deliverable edits; command exit 0. |
| Market/evaluation/OOF metrics | **NOT RUN / NOT AUTHORIZED** | This is intentional and not a failed test. |
| Campaign 5 integration / launch | **NOT RUN / NOT AUTHORIZED** | No Campaign 5 config/gate or owner authorization exists. |

**Do not interpret C4 machine `READY` output as C5 readiness.** The existing readiness artifact is explicitly C4 scoped.

## 4. Non-execution and state-change audit

- No campaign runner, continuous loop, production adapter, candidate campaign generator, or real-market model-fitting entrypoint was invoked. The bounded E2E model/bootstrap tests used only synthetic fixture inputs inside disposable temporary roots; this engineering test execution is not campaign evaluation.
- E2E tests were run only inside the `.model_discovery_workspace/dev/` fixture root; they invoke the reviewed entrypoint within disposable synthetic temporary roots and verify source guards. This is development testing, not campaign integration.
- No production integration, network, promotion, champion, freeze, gate, or launch action was performed.
- No owner approval, reviewer identity, signature, authorization record, or status was manufactured.
- The new preparation documents state pending decisions; they are not placed in authoritative approval/gate locations.

The following facts are established by this task's actions and bounded tests; any stronger filesystem-wide assertion (such as proving no background campaign process exists) requires a fresh process/state check. No such process scan was run, to avoid broad or unrelated system inspection. Historical readiness metadata reports no live loop lock at its capture time, but it is not a current process attestation.

## 5. Reproducible development-only candidate identity check

From `.model_discovery_workspace/dev/`:

```bash
py -3 - <<'PY'
from autonomous_agent.proposal_layer import candidate_search_v2 as search
candidates = search.generate_candidates(
    ('trend', 'volatility', 'interaction'), allow_development_fixture=True)
identities = {search.candidate_identity(candidate) for candidate in candidates}
print({
    'raw_configurations': len(candidates),
    'unique_configurations': len(identities),
    'duplicates_removed': len(candidates) - len(identities),
    'activation_status': search.DEV_FIXTURE_STATUS,
    'campaign_activation': search.ACTIVATED_FOR_CAMPAIGNS,
})
PY
```

Measured after the development change: 360 raw, 264 unique, 96 duplicates removed. This is catalog-engineering coverage only; it measures neither predictive value nor live-market performance.

## 6. New deliverables

- [Blocker register](CAMPAIGN5_BLOCKER_REGISTER.md)
- [Machine-readable blocker register](CAMPAIGN5_BLOCKER_REGISTER.json)
- [Owner decision packet](CAMPAIGN5_OWNER_DECISION_PACKET.md)
- [Independent-review checklist](CAMPAIGN5_INDEPENDENT_REVIEW_CHECKLIST.md)
- [Updated predeclaration draft](PHASE5_REAL_MARKET_EVALUATION_PREDECLARATION.md)
- [Timeout diagnosis and verification report](CAMPAIGN5_TEST_TIMEOUT_DIAGNOSIS.md)
- [Prior full-suite attempt log](CAMPAIGN5_CURRENT_FULL_SUITE.log); historical 518-test pass is [coordinated full-suite log](CAMPAIGN5_COORDINATED_FULL_SUITE.log); current post-change 520-test pass is [post-fix suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log)
- [Final targeted authorization test log](CAMPAIGN5_FINAL_TARGETED_TESTS.log)
- [Final candidate-identity test log](CAMPAIGN5_CURRENT_IDENTITY_TESTS.log)
- [Final prelaunch handoff](CAMPAIGN5_FINAL_HANDOFF.md)
- [Final verification sprint handoff](CAMPAIGN5_FINAL_VERIFICATION_SPRINT.md)
- This integrity audit
- Development-only candidate-search canonicalization: [candidate_search_v2.py](dev/autonomous_agent/proposal_layer/candidate_search_v2.py) now includes the model's scaling behavior in identity, so RandomForest/HistGradientBoosting standardization aliases deduplicate with identity; the equivalent semantic-transform statement was corrected to distinguish square-only marginal transforms from cross-feature polynomial maps. [test_candidate_search_v2.py](dev/autonomous_agent/test_candidate_search_v2.py) asserts the distinctions. Candidate search remains disconnected from production.
- Development-only temporal evaluation now rejects duplicate train/validation indices, duplicate feature IDs, and multidimensional split-index arrays; [test_candidate_search_v2.py](dev/autonomous_agent/test_candidate_search_v2.py) has synthetic regressions. The final focused selector suite passes 18 tests with syntax compilation. Earlier host-interrupted suite attempts are preserved at [first diagnostic](CAMPAIGN5_POST_FIX_FULL_SUITE.log), [second diagnostic](CAMPAIGN5_POST_FIX_FULL_SUITE_FINAL_TIMEOUT.log), and [E2E diagnostic](CAMPAIGN5_POST_FIX_E2E_CLASS_TIMEOUT.log). The authoritative current complete post-change suite passes 520 tests + 26 subtests, no failures/skips, in 756.82s, exit 0; see [current suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log). The previous 518-test pass remains historical only.

Final integrity recheck after current report edits: all 11 protected hashes match; blocker JSON parses and C5 evaluation/integration/execution/holdout authorization remains false; B6 is recorded verified for the current 520-test suite while `engineering_preflight_verified` and `execution_path_coverage_complete` remain false because legacy-path scope is open; candidate source/tests compile; focused selector tests and full post-change suite pass; production tree has no candidate-search import; `git diff --check` exits 0. New preparation reports/logs remain in the pre-existing untracked workspace; no staging or commit occurred. Existing unrelated checkout changes were preserved. Human governance blockers remain open; see [coordinated closure report](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md).

## 7. Remaining blockers and conclusion

Current post-change development full-suite verification is complete (520 tests + 26 subtests, exit 0). B1 protocol version/scope, B2 independent statistical review, B3 data boundary (including ruling on the disclosed header-only fixture read), B4 exact operation authorization, and B5 final predeclaration remain pending. B7 remains blocked because legacy standalone entrypoints are outside the gate pending owner scope.

The objective is readiness verifiability, not a READY appearance. Full development-suite verification is complete, but paperwork preparation and passing tests do not imply authorization. **Campaign 5 is NOT AUTHORIZED and NOT READY TO LAUNCH; human decisions remain pending.**
