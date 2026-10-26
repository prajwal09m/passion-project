# Campaign 5 Final Verification Sprint — Historical Baseline, Superseded

**Historical record only.** This report predates the final development-only evaluator validation and is superseded by the current 520-test result and [coordinated closure](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md). Campaign 5 remains **NOT AUTHORIZED. DO NOT LAUNCH.**

The 518-test pass and targeted results below are historical baseline evidence, not verification of the final code state. Current post-change tests: **520 passed + 26 subtests, 0 failures/skips, 756.82s, exit 0**; see [post-fix full-suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log). The final evaluator change and its 18-test focused result are documented in the canonical closure.

## Historical complete-suite result

From `.model_discovery_workspace/dev/`, the unchanged default pytest selection collected all **518 tests** (collection check: `py -3 -m pytest --collect-only -q`, 1.16s, exit 0). The final full suite command was:

```bash
timeout 1200s py -3 -m pytest -vv --durations=10
```

Start 2026-10-18 15:07:55 `-04:00`; end 15:12:50; wall duration 293.88s; pytest exit **0**. Complete summary: **518 passed, 26 subtests passed, 0 failed, 0 skipped**. Full captured output, command and exit record: [coordinated full-suite log](CAMPAIGN5_COORDINATED_FULL_SUITE.log). The complete test selection and assertions were preserved; the run was serial, with no skip/selection/assertion changes and no source modifications for runtime.

## Runtime diagnosis

Prior 720-second full-suite attempts timed out at the late synthetic production-entrypoint E2E model/bootstrap section. The verbose attempt saw 486 passes and ended during the purge-refit case; its isolated rerun passed in 174.56s, and horizon refit independently passed in 141.40s. The earlier seven-case class passed in 381.12s. On the successful complete run, pytest’s slowest relevant E2E calls were horizon refit 35.87s, purge refit 36.36s, regime 22.86s, and campaign-end persistence 21.23s. This demonstrates variable test/runner runtime, not a reproducible intrinsic hang. No evidence established deadlock, filesystem contention, subprocess wait, or test-order dependency; no code or timeout adjustment to the tests was justified. The selected 1200s external bound was grounded in historical full-suite timing through 540.27s and the historical E2E class at 381.12s; the full run completed well within it.

Earlier diagnostic evidence remains preserved for auditability:

- [Prior 720s verbose timeout](CAMPAIGN5_DIAGNOSTIC_FULL_SUITE_FINAL.log): 518 selected, 486 visible passes, exit 124, active purge-refit item, no summary.
- [Isolated horizon rerun](CAMPAIGN5_LATE_TEST_DIAGNOSTIC.log): 1 passed in 141.40s, exit 0.
- [Isolated purge rerun](CAMPAIGN5_LATE_PURGE_TEST_DIAGNOSTIC.log): 1 passed in 174.56s, exit 0.
- [Earlier E2E class timing](dev/phase5b_e2e_repro.log): 7 passed in 381.12s, exit 0.

Those timeouts are not passes; the later full exit-0 run is the complete verification result.

## Targeted regression and authorization boundary

Fresh checks after the complete-suite run:

- Repo-root syntax compilation of `campaign5_authorization.py`, its tests, `continuous_loop.py`, `core.py`, and `experiment_adapter.py`: exit 0.
- Repo-root focused suite `timeout 120s py -3 -m pytest -q autonomous_agent/test_campaign5_authorization.py autonomous_agent/test_experiment_adapter.py autonomous_agent/test_core.py autonomous_agent/test_continuous_loop.py autonomous_agent/test_stage5_readiness_safety_contract.py`: **79 passed + 4 subtests in 11.06s**, exit 0.
- Dev-root candidate identity compilation: exit 0; `timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py`: **16 passed in 2.14s**, exit 0.
- Existing synthetic authorization tests establish denial when records/keys are absent or unavailable; signatures/approval malformed or invalid; reviewer independence/qualification fails; authorization is revoked/expired; protocol, predeclaration, data-operation, or scope digests mismatch; audit write fails. They also assert denial precedes executor/work-factory/subprocess/workspace/loop-lock activity at guarded entrypoints. No positive production execution was attempted and no authentic approvals were fabricated.
- Statical wiring review covers supervisor runner, loop startup/cycle/direct execute/restart, adapter direct/replay, reproduction CLI/API, and baseline-establishment API. Legacy standalone study/build/train scripts remain outside the C5 preflight; do not modify until the owner makes the B7 scope decision. Candidate search remains development-only and disconnected from production.

## Integrity and prohibited operations

Final check: protected Campaign 4 hash manifest **11/11 matches**; blocker JSON parses and execution authorization is false; modified authorization and development candidate-identity files compile; `git diff --check` exits 0. Frozen historical records represented by the protected manifest remain unchanged. Existing unrelated checkout changes were preserved; no staging, commit, reset, or unrelated cleanup occurred.

No campaign, real-market evaluation, market-data model training, OOF scoring, holdout operation, or production integration occurred. Synthetic E2E tests used only isolated synthetic fixtures. Boundary disclosure remains open: a previous manifest-backed scaffolder test read the header only of a staged development event-table copy; no rows were used for fitting/scoring. Owner/data steward must decide whether that header-only access was within the allowed boundary, using authoritative governance evidence and without examining restricted contents.

## Human decisions still pending

B1 owner protocol/version/scope selection; B2 qualified independent reviewer appointment and reviewer-authored report; B3 owner/data-steward boundary and header-read ruling; B5 owner/reviewer approval of the same immutable predeclaration digest; B7 owner path-by-path legacy script scope; B4 owner authorization for one exact operation after prerequisites. These are detailed in the [owner decision packet](CAMPAIGN5_OWNER_DECISION_PACKET.md) and the [coordinated closure handoff](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md). Full-suite completion does not close any human blocker or authorize Campaign 5.

**Final status:** ENGINEERING COMPLETE — HUMAN DECISIONS PENDING. Campaign 5 remains NOT AUTHORIZED; stop pending authentic human decisions.
