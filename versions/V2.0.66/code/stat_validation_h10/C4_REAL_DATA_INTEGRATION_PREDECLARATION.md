# C4 Real-Data Integration Test — Predeclaration (DRAFT FOR OWNER REVIEW)

Status: **DRAFT. NOT EXECUTED. NOT AUTHORIZED.**
Prepared: 2026-10-17. Author: AI engineering assistant (not an owner, not an independent reviewer).
Authority required before execution: explicit written owner authorization recorded in an
append-only record. This document does not grant that authorization.

## 0. Prohibitions (binding on any execution of this plan)

The integration test MUST NOT:
1. Launch Campaign 5 or any other campaign, or invoke `continuous_loop` / `run()` against the
   persistent `autonomous_agent/state/` directory.
2. Consume, decrement, or reconcile any campaign execution budget.
3. Write to persistent campaign state: `proposal_ledger.jsonl`, `loop_state.json`,
   `experiment_registry.json`, `campaign_config.json`/`.sha256`, `campaign_end_multiplicity.jsonl`.
4. Modify promotions, `CHAMPION.json`, frozen configurations, pins, or any historical artifact
   (including the Campaign 4 final archive and `SHA256SUMS.txt`).
5. Access, open, query, or evaluate on the sealed prospective holdout, in any form.
6. Reconstruct, backfill, or reclassify Campaign 4 family measurements (24 members recorded as
   `unavailable` remain `unavailable`).
7. Alter hypotheses, estimands, thresholds, family membership, or the approved p-value procedure.
8. Connect to any brokerage, exchange, credential store, or network service (the sandbox denies
   network; do not override it).
9. Treat a passing result as statistical approval, independent review, H-10 sign-off, or launch
   authorization.

## 1. Fingerprints to pin before execution (capture, do not infer)

Current values observed on 2026-10-17 (SHA-256 of file bytes). Re-capture immediately before
execution; any difference means the plan is void until re-reviewed.

| Artifact | Path | SHA-256 (2026-10-17) |
|---|---|---|
| Development event table | study_files/outputs/study_v1/development/event_table.csv | 232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0 |
| Development OOF predictions | study_files/outputs/study_v1/development/oof_predictions.csv | 011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829 |
| Development run manifest | study_files/outputs/study_v1/development/run_manifest.json | dab3ee5f6b07078f44d1c6bb2a76163e02619c301bc83b67bb49e9f2dab469c9 |
| Study module | study_files/backend/demand_zone_study_v1.py | cea2440425e1f2f56a95b576481ae2ef603fe1f6a9816078e0a998781e0cef2a |
| Recipe harness (producer) | autonomous_agent/recipe_harness.py | 932bd1ee64245f6f2700afbc8ecaa6c43ab00afb70ea85aa76ca28cd2c1e3459 |
| Experiment adapter | autonomous_agent/experiment_adapter.py | d80723d38183ac43e66f89566cacade141f6bfcf1463d6318414d3c3b6cc61aa |
| Multiplicity module | autonomous_agent/proposal_layer/multiplicity.py | b98b22d148f01dc1ed7673cfc1c81899bc0f0d5172d5252c2a625dcdadda3a79 |
| Sign-flip module | autonomous_agent/proposal_layer/signflip.py | 3b3d5b3116e36effe6f4a0bbb437cce298b49b9ed02fb52d78be0d5db62d0219 |
| Three-valued vocabulary | autonomous_agent/three_valued.py | 58dadc220360bd3112b3c9de3668971466e3a34a2b320aa18ccf45740967d4f9 |
| Family records validator | stat_validation_h10/family_records.py | a6f0583dca3caf0e83c363026dd4d1ea9eb6e669268a48fca9e9a5da538eaca1 |
| Campaign-end finalization | stat_validation_h10/campaign_end_finalization.py | 10d89e947bd65a9f944043f210e4288eacba3c8cddd0fac43adf788e4c95b4c1 |
| Frozen campaign config (protected) | autonomous_agent/state/campaign_config.json | d8bff195eb6e3e1e81c201f78b9961f1d0d9738a611498eaca593f394e238862 |
| Proposal ledger (protected) | autonomous_agent/state/proposal_ledger.jsonl | d97da2680245be8a690ab097d1e25b1ac99b7668b74ce064cf8068f6a51f9ba8 |
| Campaign-end multiplicity (protected) | autonomous_agent/state/campaign_end_multiplicity.jsonl | 7547704337738e829ce71bddd524b7458cdc62f38ee3642443597eedd5abe9d3 |

Also record: `git rev-parse HEAD` (repository is currently uncommitted; the working-tree file list
must be captured with its hashes instead), Python version, and the full output of the test-suite
command used.

**Unresolved:** the dataset's sealed-holdout boundary is not verified in this draft. The execution
owner must confirm, from the frozen design record, that the development files above contain no
holdout rows before any run. If that cannot be confirmed, execution is blocked.

## 2. Single configuration under test

**Unresolved — not selected.** The configuration must be chosen and pinned BEFORE execution, by the
owner, from the frozen design, and must not be chosen after inspecting any integration output.
Selection criteria to be declared by the owner (proposed, not approved):
- It is an existing, frozen, non-promoted-or-promoted configuration whose spec is in the ledger
  (so the `spec_sha256` cross-check of F-6 can be exercised end to end).
- It exercises the families whose measurements were missing in Campaign 4 (regime, horizon, purge,
  complexity), not only the pooled path.
- Its `n_boot`, `folds`, and `seeds` are the frozen values, not reduced for speed.

Record the chosen configuration's `hypothesis_id`, `recipe_id`, `arm_a`, `arm_b`, `estimator_a`,
`estimator_b`, `seeds`, `n_boot`, `folds`, and its `config_sha256` (the producer convention is
`sha256(json.dumps(config, sort_keys=True).encode("utf-8"))`, verified in
`recipe_harness.py` line ~1282 and `family_records.config_identity_sha256`).

## 3. Entry point and command

**Unresolved.** The production entry point for family-measurement generation is the v1.1.0 branch
of `recipe_harness.py` reached through the experiment adapter. The exact invocation (function
name, arguments, workspace path) must be taken from the source at execution time and recorded in
the execution log. It must be run only against a **disposable workspace** (e.g. a fresh temporary
directory containing a copy of the development inputs), never against `autonomous_agent/state/`.

The command must be run with the hardening environment (`hardening.scrubbed_environment`,
network disabled, no GPU), with its exit status captured and not piped through a filter that
hides it.

## 4. Families and measurements to generate

Frozen member bounds (from `three_valued.FAMILY_MEMBER_BOUNDS`, which mirrors the frozen
campaign-end family table): regime 24, horizon 36, purge 36, complexity 12.

**Unresolved:** the exact number of members the frozen family table expects per family for the
chosen configuration, and the exact member identifiers. These must be read from the frozen
campaign-end table and recorded here before execution; they are not reproduced from memory.

Expected output per family block: one persisted member record per frozen member, each carrying the
identity block (`experiment_id`, `config_sha256`, `spec_sha256`, arms, seeds), the week index
(W-SUN convention), and the provenance flags. Non-family v1.1.0 primitives must emit
`applicable: false` and must not be counted as family members.

## 5. Expected checks (independently calculated)

Each check below must be computed by a method independent of the code under test (for example a
separate script using pandas/numpy on the raw event table), and its result recorded with the
computing script's hash.

| # | Check | Expected | Status |
|---|---|---|---|
| C1 | Sample count per regime cell | derived from event table with frozen cell definitions | unresolved (cell definitions to be cited) |
| C2 | Maturity-purge: rows removed per purge member | matches frozen purge definition (purge 36) | unresolved (rule to be cited) |
| C3 | Week alignment: W-SUN week index of every row | recomputed independently; equal to persisted week index | expected to be checkable; method unresolved |
| C4 | Week count vs. block-bootstrap minimum | must meet the frozen minimum; below it → fail closed | threshold unresolved |
| C5 | Bootstrap count floor (H-10b) | `n_boot >= MIN_BOOT_FOR_INFERENCE` (1000) | source-verified constant |
| C6 | Sign-flip p-values | recomputed independently for each member; must equal persisted values within a stated tolerance | tolerance unresolved |
| C7 | Holm-adjusted values | recomputed independently from the C6 p-values | method frozen; tolerance unresolved |
| C8 | Frozen anchors | any frozen anchor value in the campaign config reproduced exactly | anchors to be listed from the frozen record |
| C9 | Identity cross-check (F-6) | `load_authoritative_identity` agrees with persisted identity | mechanism implemented and unit-tested |

Thresholds marked "unresolved" must not be invented. If they cannot be cited from the frozen
record, the test cannot be declared passed.

## 6. Persistence and consumption path

Expected path (to be traced and recorded during execution, not assumed):
1. Production execution writes family member records into the **disposable** workspace only.
2. Records are read back through the actual adapter path (not by constructing dictionaries in the
   test).
3. `family_records.py` validates completeness, identity, and week index for every member.
4. `campaign_end_finalization.py` consumes the validated records and writes its output **only** to
   the disposable workspace.

Pass criterion for 1–4: every record survives the adapter round trip unchanged in its identity and
measurement fields, and the finalization output recomputes exactly from the records.

## 7. Partial results, missing members, and failures

Fail-closed rules (binding):
- Any missing, duplicated, mismatched, or malformed member → the integration test is **FAILED**,
  not partially passed. No partial finalization record is kept as a result.
- A pooled-only result presented to finalization → FAILED.
- A block whose identity disagrees with its authoritative spec or ledger → FAILED.
- A `unavailable` member is reported as `unavailable`. It is never converted to pass or fail.
- A runtime exception, timeout, or non-zero exit → FAILED; the log is retained; no retry with
  altered parameters is permitted under this plan. Any rerun requires a new predeclaration.

## 8. Budget and disposable-output isolation

Demonstration required:
- Before and after the run, a hash listing of `autonomous_agent/state/` shows **no change**.
- The disposable workspace is the only location with new files; its file list and hashes are
  recorded.
- The campaign execution counter (in `loop_state.json` / ledger) is unchanged.
- No process accesses the holdout path; the access log (or the monitored path list) is retained.
- After evidence capture, the disposable workspace is deleted, and the deletion is logged.

## 9. Holdout and historical-artifact protection

- The sealed holdout is not read. Its path is not opened, and no file under it is hashed unless the
  owner specifies a non-content method approved in the frozen design.
- Protected artifacts in §1 are hashed before and after; any difference is a FAILURE and stops
  work.
- Archives and `SHA256SUMS.txt` are verified by read-only checks only.

## 10. Evidence captured before and after

Before: §1 hashes; working-tree file list with hashes; Python and package versions; chosen
configuration; the exact command text; the test-suite result used as baseline.
After: the same hashes; disposable workspace listing and hashes; execution log; each check C1–C9
with its computing-script hash and result; a statement of every failure or unresolved item.

## 11. Explicit non-claims

Passing this integration test would show only that the production code path executes end-to-end
on the retained development data and that its outputs match independent recalculations. It would
**not** establish statistical validity of `week_level_signflip_holm` (see F-3 packet), independent
review, H-10 approval, campaign authorization, or any profitability or predictive claim.

## 12. Owner authorization

Owner authorization for execution: **NOT GRANTED.**
Owner signature / date: **[pending — to be completed only by the owner]**
