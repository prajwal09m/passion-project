# Campaign 5 Preflight Test Report — Historical Baseline

**Historical status: targeted preflight and identity tests passed; the then-current 518-test dev suite passed.** This report predates the final evaluator validation change and is retained as prior evidence only. The current post-change suite result is **520 passed + 26 subtests, 0 failed/skipped, 756.82s, exit 0**; see [post-fix full-suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log) and [canonical closure](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md). No authorization was created or inferred.

## Targeted tests

Command from repository root:

```bash
py -3 -m py_compile autonomous_agent/campaign5_authorization.py autonomous_agent/test_campaign5_authorization.py autonomous_agent/experiment_adapter.py autonomous_agent/continuous_loop.py autonomous_agent/core.py
py -3 -m pytest -q autonomous_agent/test_campaign5_authorization.py autonomous_agent/test_experiment_adapter.py autonomous_agent/test_core.py autonomous_agent/test_continuous_loop.py autonomous_agent/test_stage5_readiness_safety_contract.py
```

Historical focused execution: 2026-10-18 12:01:17–12:01:31 `-04:00`; 76 tests + 4 subtests, 13.15s. Fresh previous focused execution: 12:32:14–12:32:30; 76 + 4, 14.94s. After adding inert loop restart/CLI and audit-write denial tests, the final focused command completed 2026-10-18 13:20:33–13:20:45 `-04:00`: **79 passed + 4 subtests**, pytest exit 0 in 11.15s; compilation of campaign5_authorization.py, test_campaign5_authorization.py, continuous_loop.py, core.py, and experiment_adapter.py exited 0. Full output: [final targeted log](CAMPAIGN5_FINAL_TARGETED_TESTS.log). The synthetic suite covers missing record, absent owner/reviewer approval, reviewer independence/qualification, mismatches in scope/protocol/digests, unclear data permission, revoked, malformed/unknown fields, expired, absent/bad keys, unavailable record, audit-write failure, synthetic positive control, active C5 adapter denial before workspace/subprocess, repeated serialized-spec calls, supervisor-injected-runner bypass attempt, and preservation of non-C5 checker behavior. Positive control is accepted by the pure validator only with explicit `allow_synthetic=True`; runtime always rejects synthetic record class.

Earlier targeted attempt before corrections: 28 passed, 4 subtests, one unrelated supervisor test failed due assertion mismatch; subsequent final command above passed. Earlier syntax/collection and test failures were repaired, not suppressed.

Synthetic candidate identity check (separate dev root): fresh `py -3 -m py_compile autonomous_agent/proposal_layer/candidate_search_v2.py autonomous_agent/test_candidate_search_v2.py` and `timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py` → **16 passed in 2.71s**, pytest/compile exit 0. See [current identity log](CAMPAIGN5_CURRENT_IDENTITY_TESTS.log), [current full-suite log](CAMPAIGN5_CURRENT_FULL_SUITE.log), and [identity validation](CAMPAIGN5_CANDIDATE_IDENTITY_VALIDATION.md) for scope.

## Post-sync final targeted verification

The isolated dev fixture originally contained the guarded loop but lacked `campaign5_authorization.py`, producing an import failure in an existing loop test and hiding the intended startup-stop assertion path. The canonical C5 authorization module was synchronized into the dev fixture; the dev loop entry now translates a missing module into an explicit fail-closed `LoopStop` (the module is present in the current fixture). No tests were removed or loosened.

- Dev-root adjacent regression command: `py -3 -m pytest -q autonomous_agent/test_experiment_adapter.py autonomous_agent/test_core.py autonomous_agent/test_continuous_loop.py autonomous_agent/test_stage5_readiness_safety_contract.py` → **65 passed + 4 subtests in 21.01s**, exit 0.
- Repo-root final focused command: `py -3 -m pytest -q autonomous_agent/test_campaign5_authorization.py autonomous_agent/test_experiment_adapter.py autonomous_agent/test_core.py autonomous_agent/test_continuous_loop.py autonomous_agent/test_stage5_readiness_safety_contract.py` → **79 passed + 4 subtests in 34.33s**, exit 0. C5 authorization tests alone: **14 passed in 0.70s**.
- Production touched-file `py_compile` passed. Candidate identity compilation passed from the isolated dev root.

The historical complete run from the isolated dev root used the then-current 518-test selection: `timeout 1200s py -3 -m pytest -vv --durations=10`, start 2026-10-18 15:07:55 and end 15:12:50 `-04:00`. Result: **518 passed, 26 subtests passed, 0 failed, 0 skipped in 293.88s**, exit 0. Log: [coordinated full-suite run](CAMPAIGN5_COORDINATED_FULL_SUITE.log). Earlier bounded diagnostics and the two isolated refit reruns show variable runtime; the complete-run horizon/purge calls were about 36s each. No fix was necessary and no assertion/selection was changed. Earlier timeout logs remain historical context, not the current suite result.

## Historical full-suite verification

The complete pre-final-edit run from `.model_discovery_workspace/dev/` used the then-current 518-test selection and completed: **518 passed + 26 subtests, 0 failures/skips, 293.88s, exit 0**. Exact command: `timeout 1200s py -3 -m pytest -vv --durations=10`; see [CAMPAIGN5_COORDINATED_FULL_SUITE.log](CAMPAIGN5_COORDINATED_FULL_SUITE.log). Earlier 720s attempts ended exit 124 during expensive synthetic E2E work; they remain diagnostic history only. Runtime varied across attempts; the complete run's refit calls were ~36s. No test was removed/skipped, assertions weakened, or suite parallelized.

The repo-root syntax compilation and focused suite covered the modified authorization path and existing adjacent supervisor/adapter/loop tests at that time. The historical coordinated full-suite run also passed; current post-change verification is recorded in the linked canonical closure. Neither targeted nor full-suite verification grants authorization. No command was run against real-market training/evaluation, no Campaign 5 launch, no holdout access, no scoring, and no production integration.

## Enforcement findings

- Runtime authorization record and trust keys are absent, therefore C5 fails closed.
- The C5 gate currently protects the autonomous supervisor, continuous loop, and adapter execution APIs.
- Static audit found legacy study training/build scripts directly invokable outside these APIs. They remain a bypass outside the protected boundary; see [execution-path audit](CAMPAIGN5_EXECUTION_PATH_AUDIT.md). This is an explicit blocker to complete repository-wide enforcement.
- Trust material requires separate external owner/reviewer secret keys and actor IDs. No credentials or approvals were put in this repo.
- The owner/data-boundary question about header-only staged fixture access remains unresolved. Earlier 720-second attempts are historical diagnostics. The 518-test coordinated run superseded them at that time; both are now superseded as current verification by the post-change 520-test pass. See the post-fix suite log linked above.

## Conclusion

At the time, repo-root authorization/adjacent tests passed (79 + 4 subtests in 11.06s); candidate identity tests passed (16 in 2.14s); touched-file compilation passed. Full 518-test dev suite passed (518 + 26 subtests, no failures/skips, 293.88s, exit 0). The current post-change 520-test suite and focused evaluator result are in the canonical closure. See the [coordinated closure report](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md) and [complete suite log](CAMPAIGN5_COORDINATED_FULL_SUITE.log). Repository-wide execution coverage is not established because legacy scripts remain outside the gate. Engineering verification is complete; human protocol, independent review, boundary, predeclaration and exact authorization remain pending.
