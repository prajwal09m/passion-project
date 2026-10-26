# Campaign 5 Final Prelaunch Handoff

**As of 2026-10-18 — DO NOT LAUNCH. Campaign 5 is NOT AUTHORIZED / NOT READY.** Engineering completion is not scientific validation, data-use permission, or campaign authorization.

## Current status

**ENGINEERING COMPLETE WITHIN PERMITTED DEVELOPMENT SCOPE — HUMAN DECISIONS PENDING.** The current complete suite passed after the final development-only evaluator edit. Candidate search remains isolated from production.

- **Change:** temporal candidate evaluation rejects duplicate training/validation indices, duplicate feature IDs, and multidimensional split-index arrays. The prior behavior could silently weight duplicated rows multiple times or accept malformed split membership. Synthetic regressions cover those cases.
- **Focused verification** (from `.model_discovery_workspace/dev/`): `py -3 -m py_compile autonomous_agent/proposal_layer/candidate_search_v2.py autonomous_agent/test_candidate_search_v2.py && timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py` — compilation exit 0; **18 passed**, pytest exit 0.
- **Collection:** `py -3 -m pytest --collect-only -q` — **520 collected**, exit 0.
- **Complete post-change suite:** `timeout 1800s py -3 -m pytest -vv --durations=10` — **520 passed, 26 subtests passed, 0 failed, 0 skipped in 756.82s**, exit 0. Full output: [current suite log](CAMPAIGN5_POST_FIX_FULL_SUITE_STABLE_RUN.log).
- **Integrity and guards:** all **11/11 protected Campaign 4 SHA-256 hashes match**; evaluation/integration/execution/holdout authorization flags remain false; no production-tree import of `candidate_search_v2` was found; `git diff --check` passes. See [canonical closure](CAMPAIGN5_FINAL_COORDINATED_CLOSURE.md).
- Earlier synchronous-host-limited attempts left useful diagnostics, including Windows subprocess interrupt codes and expected-stderr assertions; they are superseded by the later persistent complete exit-0 run. See [first attempt](CAMPAIGN5_POST_FIX_FULL_SUITE.log), [second attempt](CAMPAIGN5_POST_FIX_FULL_SUITE_FINAL_TIMEOUT.log), and [E2E attempt](CAMPAIGN5_POST_FIX_E2E_CLASS_TIMEOUT.log). No tests/assertions were skipped, removed, or weakened.

## Scientific and authorization limits

No predictive-performance improvement, market accuracy, calibration, profitability, or scientific validity is demonstrated by this engineering work. No real-market evaluation, market-data training, OOF scoring, sealed-holdout access, Campaign 5 integration, or launch was performed. One earlier suite test read only the header of the staged development event-table fixture; no rows were used, and the owner/data-steward ruling on whether that metadata read was within scope remains unresolved.

Outstanding human/governance blockers:

1. **B1:** owner selects or defers the exact C5 protocol and resolves the v1.0.1/v1.0.2 mismatch.
2. **B2:** owner appoints a qualified, genuinely independent statistical reviewer; reviewer authors assessment against exact digests.
3. **B3:** owner/data steward attests eligible inputs, temporal/group/purge boundary, exposure history, fixture policy, and the header-only-read ruling.
4. **B5:** owner and reviewer settle and approve the same immutable predeclaration digest.
5. **B7:** owner scopes standalone legacy study/build/train paths; repository-wide execution protection is not established.
6. **B4:** only after prerequisites, owner gives authentic authorization for one exact operation. Production integration/launch needs separate explicit authorization.

No remaining high-priority engineering defect is known within the permitted development scope. The principal unresolved engineering/control limitation is B7, which requires an owner scope decision before legacy paths can be modified. For complete blocker evidence, see the [human decision packet](CAMPAIGN5_OWNER_DECISION_PACKET.md), [execution-path audit](CAMPAIGN5_EXECUTION_PATH_AUDIT.md), and [machine-readable blocker register](CAMPAIGN5_BLOCKER_REGISTER.json).

**Final status: ENGINEERING COMPLETE — CAMPAIGN 5 NOT AUTHORIZED.** Do not access restricted evaluation data or launch Campaign 5 unless genuine required approvals and exact-operation authorization are completed.