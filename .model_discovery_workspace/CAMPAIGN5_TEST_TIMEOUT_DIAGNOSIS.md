# Campaign 5 Preparation — Test Timeout Diagnosis (Historical)

**Status: Historical runtime diagnostics.** This report predates the final evaluator validation change and its complete 520-test run. The current authoritative post-change result is **520 passed + 26 subtests, 0 failures/skips, 756.82s, exit 0**; see [post-fix full-suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log) and [canonical closure](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md). C5 remains unauthorized. This report is engineering evidence only, not campaign authorization or statistical evidence.

## Boundary and test root

- Commands ran from `.model_discovery_workspace/dev/`, the self-contained development/test fixture tree described in `FIXTURE_PROVENANCE.json`.
- The E2E fixture constructs fresh temporary synthetic roots (synthetic frozen-study module, synthetic event table, synthetic OHLCV cache), has no prospective/holdout data, and invokes disposable subprocesses. The fixture manifest also says the sealed directory was not copied.
- No real-market event table or OOF prediction artifact was read or scored in this test work. No production campaign command was run, no persistent campaign state was intentionally written, and no integration or launch action was performed.

## Findings

**VERIFIED FACT, refined by final diagnostic:** The late E2E production-entrypoint tests are very expensive on this runner. Full-suite verbose output names the final active item as the purge refit case; that case independently passes in 174.56s, and the horizon refit independently passes in 141.40s. A prior seven-test production-entrypoint class passed in 381.12s. These isolated passes support a slow synthetic subprocess/model/bootstrap explanation and argue against an intrinsic hang in those individual reruns. They do not prove that the full suite has no order-dependent wait, deadlock, or resource interaction; none was established from available evidence.

**Historical verified fact:** Before the final evaluator validation change, the coordinated run selected 518 tests and completed with **518 passed + 26 subtests, 0 failed/skipped in 293.88s**, exit 0. Its exact command and output are retained in [coordinated full-suite log](CAMPAIGN5_COORDINATED_FULL_SUITE.log). This historical result is superseded for current verification by the 520-test post-change run linked above. Scope disclosure: the complete dev suite includes the manifest-backed `ScaffolderTests` that read only the header of the staged development event-table fixture; see the integrity audit for the boundary interpretation caveat.

**UNRESOLVED historical detail:** Prior reports say the E2E and full dev suites timed out, but the saved logs reviewed here do not include a timeout termination timestamp/exit code for those reported events. Therefore the precise historical command, timeout duration, termination mechanism, and whether the full suite was interrupted versus simply outlasting a caller limit cannot be independently reconstructed. The current verbose full run and individual case reruns show variable costs in expensive production-entrypoint E2E refit/bootstrap work. The final complete run passed after 293.88s; its horizon and purge refit calls took about 36s each, versus prior standalone reruns at 141.40s and 174.56s. This supports variable runner/runtime costs rather than an inherent hang. No deadlock, subprocess wait, filesystem contention, or test-order dependency was established.

**No test was omitted, skipped, assertion weakened, or timeout suppressed** to obtain these results. No source change was made to the E2E/full-suite tests in response to the reported timeouts.

## Reproduction record

Local machine clock is Eastern Daylight Time (`-04:00`), as shown by the shell. Each command was run with an external `timeout` and the shell recorded the inner command's exit status. Captured logs: [E2E reproduction](dev/phase5b_e2e_repro.log) and [full-suite reproduction](dev/phase5b_full_suite_repro.log).

| Run | Exact command (cwd `.model_discovery_workspace/dev/`) | Start → end | Configured timeout | Result / counts | Exit / completion |
|---|---|---|---:|---|---|
| E2E slow section | `timeout 540s py -3 -m pytest -v --durations=10 autonomous_agent/test_v110_wiring_e2e.py::ProductionEntryPointE2ETests` | 2026-10-18 10:32:35 → 10:38:57 `-04:00` | 540 s | 7 passed, 0 failed/skipped/errors, 381.12 s. Slowest: horizon 94.47s; purge 82.98s; campaign-end persistence 59.62s; regime 46.12s; complexity 39.31s; degenerate 39.29s; missing column 15.49s. | Inner exit 0; completed before timeout. |
| Initial entire isolated dev suite | `timeout 720s py -3 -m pytest -q` | 2026-10-18 10:39:33 → 10:45:08 `-04:00` | 720 s | 515 passed, 26 subtests passed, 0 failed/skipped/errors, 334.69 s. All discovered dev tests completed. | Inner exit 0; completed before timeout. |
| Prior entire isolated dev suite after malformed-input regressions | `timeout 720s py -3 -m pytest -q` | 2026-10-18 10:54:07 → 10:58:32 `-04:00` | 720 s | 517 passed, 26 subtests passed, 0 failed/skipped/errors, 263.30 s. | Inner exit 0; completed before timeout. |
| Historical entire isolated dev suite after identity safety refinement | `timeout 720s py -3 -m pytest -q` | 2026-10-18 11:03:12 → 11:12:13 `-04:00` | 720 s | 517 passed, 26 subtests passed, 0 failed/skipped/errors, 540.27 s. | Inner exit 0; historical run completed before timeout. |
| Historical coordinated full-suite run, pre-final evaluator edit | `timeout 1200s py -3 -m pytest -vv --durations=10` | 2026-10-18 15:07:55 → 15:12:50 `-04:00` | 1200 s bound | 518 passed, 26 subtests passed, 0 failed/skipped in 293.88s. | Exit 0; historical only. See [coordinated full-suite log](CAMPAIGN5_COORDINATED_FULL_SUITE.log). |
| Fast E2E non-production diagnostic, under-bounded | `timeout 60s py -3 -m pytest -q autonomous_agent/test_v110_wiring_e2e.py -k 'not ProductionEntryPointE2ETests'` | 2026-10-18 13:00:19 → 13:01:20 `-04:00` | 60 s | Partial dots only, no summary. | Timeout exit 124; superseded by 180s run below; not a pass. |
| E2E non-production subset | `timeout 180s py -3 -m pytest -v --durations=10 autonomous_agent/test_v110_wiring_e2e.py -k 'not ProductionEntryPointE2ETests'` | 2026-10-18 13:04:15 → 13:07:02 `-04:00` | 180 s | 31 passed, 7 deselected in 165.99s; slowest setup 52.55s; slow calls 50.03, 25.30, 24.06, 11.72s. | Exit 0. Useful timing diagnosis only; not full module because seven `ProductionEntryPointE2ETests` were excluded. |
| Duplicate E2E non-production subset with 120s bound | Same 31 tests as above | 2026-10-18 13:07:13 → 13:09:14 `-04:00` | 120 s | Reached first slow campaign-finalization setup, no summary. | Exit 124; too-short bound; not a pass. |
| Final targeted authorization/adjacent suite + compile after added loop/CLI/audit tests | `py -3 -m py_compile autonomous_agent/campaign5_authorization.py autonomous_agent/test_campaign5_authorization.py autonomous_agent/continuous_loop.py autonomous_agent/core.py autonomous_agent/experiment_adapter.py` then `timeout 120s py -3 -m pytest -q autonomous_agent/test_campaign5_authorization.py autonomous_agent/test_experiment_adapter.py autonomous_agent/test_core.py autonomous_agent/test_continuous_loop.py autonomous_agent/test_stage5_readiness_safety_contract.py` | 2026-10-18 13:20:33 → 13:20:45 `-04:00` | 120 s | 79 passed + 4 subtests in 11.15s. | Compile exit 0; pytest exit 0. See [final targeted log](CAMPAIGN5_FINAL_TARGETED_TESTS.log). |
| Fresh current targeted authorization suite and compilation | `py -3 -m py_compile ...` then `timeout 120s py -3 -m pytest -q autonomous_agent/test_campaign5_authorization.py autonomous_agent/test_experiment_adapter.py autonomous_agent/test_core.py autonomous_agent/test_continuous_loop.py autonomous_agent/test_stage5_readiness_safety_contract.py` | 2026-10-18 12:32:14 → 12:32:30 `-04:00` | 120 s | 76 passed, 4 subtests passed, 14.94s; compile exit 0. | Pytest exit 0; compilation exit 0. See [current targeted log](CAMPAIGN5_CURRENT_TARGETED_TESTS.log). |
| Fresh current candidate identity suite and compilation | `py -3 -m py_compile autonomous_agent/proposal_layer/candidate_search_v2.py autonomous_agent/test_candidate_search_v2.py` then `timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py` | 2026-10-18 12:36:09 → 12:36:13 `-04:00` | 120 s | 16 passed in 2.71s; compilation exit 0. | Pytest exit 0; compilation exit 0. See [current identity test log](CAMPAIGN5_CURRENT_IDENTITY_TESTS.log). |
| Initial focused search/ranking regressions | `timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py autonomous_agent/test_outcome_ranking_grouped.py autonomous_agent/test_phase3_research_memory.py` | 2026-10-18 10:51:49 → 10:51:52 `-04:00` | 120 s | 32 passed, 0 failed/skipped/errors, 2.38 s. | Exit 0; completed. |
| Latest focused search/ranking regressions after malformed-input fix | `timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py autonomous_agent/test_outcome_ranking_grouped.py autonomous_agent/test_phase3_research_memory.py` | 2026-10-18 10:53:54 → 10:53:58 `-04:00` | 120 s | 34 passed, 0 failed/skipped/errors, 2.33 s, plus `py -3 -m py_compile autonomous_agent/proposal_layer/candidate_search_v2.py` | Exit 0; completed. |
| Latest candidate identity tests + compile | `timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py` then `py -3 -m py_compile autonomous_agent/proposal_layer/candidate_search_v2.py` | 2026-10-18 11:02:47 → 11:02:49 `-04:00` | 120 s | 15 passed, 0 failed/skipped/errors, 1.96 s; compile exit 0. | Overall exit 0; completed. |
| Prior full isolated dev run | Prior log command text not recorded in this file; `.model_discovery_workspace/phase4_final_dev_suite.log` states full dev suite | Log records no start/end wall clock | Not present in log | 497 passed, 26 subtests passed, 330.65 s | Exit 0, recorded as complete. |

The run-count entries only describe the stated command; “26 subtests” are pytest/unittest subtest assertions inside test methods and are not 26 separately discovered test functions.

## Other historical logs and their limitations

- `.model_discovery_workspace/.phase3_full_dev_suite.log` shows a completed pytest progress bar but contains 7 errors and multiple failures, chiefly fixture-root FileNotFound errors for development event table. It is a failing run, not a timeout and not a pass. It also shows subsequent tests reached 100%. The present suite uses the staged isolated `dev/` fixture root and passes.
- `.model_discovery_workspace/phase3_dev_suite.log` records collection failure: `ModuleNotFoundError: No module named 'family_records'` from running the E2E test before fixture staging/import path was prepared. This is a test-environment/fixture setup issue, not a runtime timeout.
- `.model_discovery_workspace/dev_regression.log` reports 133 passed, 2 failed in 14.41s: one expected Campaign 1 historical artifact absent from the then-incomplete dev tree, and one stale exact-key assertion after `evidence_key` was added. It did not time out. The full staged suite now passes; no assertion was suppressed.
- `.model_discovery_workspace/.full_suite.log` is a verbose historical full-suite output; its complete trailing summary was not included in the multi-file read, so it is not used as this report’s verification evidence.

## Suggested maintainable commands

Run the full intended isolated suite from the dev root with a documented upper bound sufficient for measured runtime (for example 720 seconds), retain output and exit code, and do not treat external timeout exit 124 as a pass:

```bash
cd .model_discovery_workspace/dev
timeout 720s py -3 -m pytest -q
```

Run the slower E2E production-entrypoint section independently for diagnostics; run all E2E classes when validating the complete E2E intent. Sectioning is additional observability only; it does not replace the complete suite:

```bash
cd .model_discovery_workspace/dev
timeout 540s py -3 -m pytest -v --durations=10 autonomous_agent/test_v110_wiring_e2e.py::ProductionEntryPointE2ETests
```

Keep timeout status visible when saving a log:

```bash
set +e
timeout 720s py -3 -m pytest -q > full-suite.log 2>&1
rc=$?
printf '\nEXIT_STATUS=%s\n' "$rc" >> full-suite.log
exit "$rc"
```

Do not pipe through `tail` or another output filter unless `set -o pipefail` is enabled and the tested process exit code is explicitly captured.

## Remaining verification limits

1. This diagnosis is historical. The current complete post-change suite passed 520 tests + 26 subtests, no failures/skips, in 756.82s, exit 0; the 18-test evaluator-focused suite and syntax checks passed. See the canonical closure for current status.
2. The complete `test_v110_wiring_e2e.py` module contains additional lightweight equivalence, family-record, boundary/drift, and other tests; this session ran the seven slow production-entrypoint tests plus the full suite, which includes the module. The standalone entire E2E module was not separately run under an external timeout in this session.
3. No real-data evaluation, OOF metric computation, campaign integration run, production campaign, or holdout access was attempted or authorized.
4. This diagnosis does not establish that any C5 protocol, statistical method, data boundary, or owner decision is complete.
