# V3 INTEGRATION & ROLLBACK (Stage 7)

## 1. Integration mechanism (shipped)

- Selection: `config.resolve_eval_rubric` (env `MODEL_AUTOPSY_EVAL_VERSION`,
  default `v2`, invalid → `ValueError` before any spend/work).
- Recording: `pipeline.persist_eval_rubric` writes
  `inv.config["eval_rubric_version"]` + `evaluation` event at creation
  (driver, offline runner, API create). No schema migration: version lives
  in the existing JSON config column.
- Scoring: `pipeline.score_report(pid, report, truth, version)` — deep copy,
  v3-only canonical normalization on the copy, version-stamped output,
  explicit `unscored` error scorecard on v3 failure (never silent v2).
- Manifests: live `finalize_run(..., eval_version=...)` →
  `manifest["eval_rubric_version"]`; eval-run manifests carry both
  `eval_version:"m4-v1"` (framework) and `eval_rubric_version`.
- Resume: `reconcile` reads the stored version (missing → v2, corrupt →
  refuse); `select_eval_rubric(inv=...)` re-validates after load; global
  env changes cannot switch a resumed run (mismatch → refuse).
- API: `GET /api/eval/versions`, `POST /api/eval/runs {eval_version?}`,
  `POST /api/investigations {eval_version?}`, summary exposes
  `eval_rubric_version` (null for pre-version records — honest).

## 2. Rollback (no data migration required)

Because v2 code is untouched and selection defaults to v2, rollback is
configuration, not surgery:
1. Unset `MODEL_AUTOPSY_EVAL_VERSION` (or set `v2`) → all new runs score v2.
2. In-flight v3 runs keep their stored version (persisted per investigation);
   resume re-validates and continues with v3 for those runs only.
3. To force a historical run back to v2 semantics, re-score its persisted
   `eval_report.json` offline with `pipeline.score_report(..., "v2")` and
   store the result as a NEW file (never overwrite the archived scorecard).
4. Frontend: v2 scorecards render unchanged (new fields optional).
5. No database migration was introduced (config-JSON versioning), so there
   is nothing to reverse in the schema. `inv.config` keys are additive and
   ignored by older readers.

Rollback is tested in isolation: `test_rollback_switch_leaves_archives_
untouched` flips env v3→v2, re-scores the M22 report under both rubrics,
and asserts the archived scorecard bytes are unchanged (temp env only;
conftest pins tests to a throwaway SQLite DB, never the app DB).

## 3. Failure semantics

- Invalid env/selection value: `ValueError` → API 400 / CLI refusal / driver
  pre-creation failure. No partial run.
- v3 scorer exception: explicit `unscored` scorecard with error note;
  investigation records and artifacts are preserved as-is.
- Resume version mismatch/corruption: refusal with reason; original run
  directory untouched (reconcile is read-only until the run proceeds).
- Evaluation failure is recorded as an evaluation outcome (`unscored`),
  never confused with an investigation outcome.
