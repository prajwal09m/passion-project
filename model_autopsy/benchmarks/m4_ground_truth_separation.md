# Milestone 4 — Ground-Truth Separation & Trust Boundary

## Two environments

- **Investigation environment**: `tests/fixture_eval/investigator/`
  (8 data CSVs + `briefs.json`). This is ALL the investigator (and the
  triage/lab code paths) may resolve. `discovery_input()` returns only
  `{spec, artifact, brief}`.
- **Evaluation environment**: `ground_truth_eval.json` (beside, never
  inside, the investigator dir), reference numbers, scoring rules. Read
  only by `scorer.py` and test assertions — never by triage/lab code
  (a test asserts `runner.py` source never mentions `ground_truth`).

## Controls (not just a hidden JSON)

1. **Lexical audit** (`separation.audit_investigator_env`, exposed at
   `GET /api/eval/separation-audit`): scans EVERY investigator file
   (all extensions) for 17 mechanism-specific forbidden tokens and
   fails on any hit; verifies the truth file is not resolvable from
   inside the investigator tree. Covered by pass + planted-token tests.
2. **Neutral naming**: functional column names only
   (label/score/target/prediction/date/split/slice); no mechanism
   words in filenames, briefs, or columns.
3. **Structural**: investigator path resolution is restricted to the
   sanitized dir; run DBs are run-scoped; results never flow back into
   fixtures.

## Known limitations (honest)

- The audit is lexical, not semantic: it cannot catch a hint a human
  would notice (e.g. a suspiciously clean split column). Documented in
  the audit output itself.
- Project identity (which file is which project) is visible — by
  design; only mechanisms are concealed.
- The deterministic investigator and the fixtures were built by the
  same team in the same milestone: residual co-design bias is possible
  (thresholds and fixtures were tuned against each other where noted,
  e.g. the 0.4 silhouette bar). The separation machinery (audit,
  blind review, no-overwrite runs) is what makes future
  third-party/live-model evaluation trustworthy, not the current
  scores alone.
