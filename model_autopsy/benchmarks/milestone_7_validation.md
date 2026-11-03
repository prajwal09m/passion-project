# Milestone 7 — Full offline test gate (Part 7)

No paid API activity for any check below (§8 is the only authorized
live step, and it runs after this document). Commands from repo root.

## Backend

- `py -3 -m pytest model_autopsy/tests -q` → **301 passed**, exit 0
  (~113 s). Baseline 287 (M6 era) + 8 `test_m7_closed_loop` + 5
  `test_m6_resume` + 1 `test_m7_challenge`. No tests weakened; one
  adjacent failure surfaced honestly during development
  (`test_ml_instructions_stay_compact_but_behavioral`: prompt exceeded
  its 2000-char efficiency bound) and was fixed by compacting the
  prompt (1948 chars, all required behaviors kept) — cause fixed, not
  the assertion.
- New coverage: live-turn auto-link + brief + adherence through the
  REAL `run_meta_turn` path (scripted provider); corroboration →
  `supported`; double contradiction → `rejected`; failed tools never
  link; linker idempotency; `residual_feature_dependence` on the real
  claim fixture (`device_age` |r| > 0.5); registry registration;
  stopping policy; resume refusal cases; closed-loop harness checks.
- Regression: full suite re-run AFTER every backend change (prompt
  compaction, planner failed-tool exclusion, propose durability commit).

## Evaluation integrity

- Ground-truth separation audit: `ok: True`. M7 harness reads truth
  only for concealment assertions, never in the loop; seeds are generic
  per-family priors, not answers.
- Challenge suite: 6/6 scenarios run, all behavioral checks true
  (transitions occur, refs cite ran actions, no duplicates, budget ≤6,
  every stop justified). Report: `milestone_7_challenge_report.md`.
- Scoring: M4 definitions untouched; M6/M7 dims reported alongside,
  never averaged in. Reproducibility: harness is deterministic
  (seeded k-means, full sorts, no sampling).
- Historical manifests intact: M5 `live-140167117ef5` completed,
  `live-206dd3c2a288` failed, M6 `live-ae844753edce` completed —
  reads only, statuses verified above. No fabricated results.

## Frontend

- `npx tsc --noEmit` (in `model_autopsy/frontend`) → exit 0.
- `npm run build` → success (`dist/` written; chunk-size warning only).
- Dashboard: `CausalPanel` extended with feedback-loop table, status
  transitions + confidence trail, stopping rationale; verified against
  the extended causal endpoint (200, all keys present incl.
  `feedback`/`transitions`/`stopping`).

## Security

- Credential scan over new/changed files
  (`backend/causal/*`, `backend/live/*`, new tests): no key material.
- Key presence confirmed via loader (value never printed); model
  `muse-spark-1.3`, endpoint unchanged.

## End-to-end (offline)

- Closed-loop harness (scripted policy, real engine/tools/linker/
  planner, real fixtures): all checks green; failed tools recorded once
  then excluded from future picks (no failure loops); inapplicable
  tools skipped with reasons; inconclusive-with-rationale reachable.
- Live-path proof uses mocked transport only (zero credits, suite
  asserts no provider keys in test env).

## Preconditions for the authorized live run (all met)

Full suite green · tsc + build green · loop invokes status updates
(proven live-path test) · selection brief injected into live prompts
(proven live-path test) · project `eval_credit` unused by M5/M6, truth
sealed · credential path works · recovery resume path intact ·
preflight to be run fresh at launch with worst-case cost ≤ $0.40.

## Post-live hardening (offline, after the authorized run)

The live run exposed three defects; all were fixed and re-validated
without further paid traffic:

1. Experiment-cap enforcement gap (8 executed vs 6 authorized):
   `run_meta_turn` now accepts `experiments_left` and refuses execution
   beyond it; driver and resume pass the remaining allowance.
   Proven by `test_experiments_left_caps_executions`.
2. Missing subgroup family in selection ranking (regional-AUC question
   scored "low" for subgroup diagnostics): added the family and its
   discriminator mapping. Proven by `test_subgroup_family_ranking`.
3. Empty first-turn brief ("top=none" before hypotheses exist): starter
   briefs (artifact/dataset/quality) now seed turn 1. Proven by
   `test_starter_brief_without_hypotheses`.
4. `propose_hypothesis` durability: now commits, so a later failed
   tool's rollback cannot wipe recorded hypotheses (found by the new
   failure-path tests).

Re-verification after all fixes: full suite **304 passed** (301 + 3
new), exit 0. Frontend unchanged since its green build. The live run's
breach stands recorded in `milestone_7_results.md` and is not
retroactively excused by the fix.

## Known limitations

- Harness covers 6/12 M6 scenarios (generic-args subset);
  classification-only tools untested there.
- Scripted-policy adherence is 100% by construction; deviation handling
  is covered by the live-turn test instead.
- Offline evidence is machinery proof, not investigator-quality proof —
  that requires Part 8.
