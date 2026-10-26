# Model Discovery — Phase 2 Report (development only)

Date: 2026-10-17. Scope: `.model_discovery_workspace/` only. No production source, frozen campaign configuration, holdout, or campaign state was modified. No experiment was run and no AUC was computed or predicted.

**Status: partial.** The mission's completion criteria are not met. The search-space expansion is implemented and tested. The deadlock comparison, selection-policy benchmark, ranker evaluation and outcome taxonomy are not done (see §3).

## 1. What was implemented

| File | Status |
|---|---|
| `dev/autonomous_agent/proposal_layer/search_space.py` | New. Atom-level novelty classifier, direction-free canonical key, expanded key generator, harness-contract validator. |
| `dev/autonomous_agent/test_search_space.py` | New. 13 tests, all passing. |
| `atom_analysis.py` | New analysis script (measured history vs expansion). |

### Core finding (source evidence)

- `recipe_harness._run_pooled` computes each arm's score from that arm's own features, its own estimator, and the folds. Seeds only resample rows. So the predictive evidence atom is `(arm, estimator, seeds, folds, baseline)`, not the comparison.
- `delta_auc = auc_b - auc_a`, so `A->B` and `B->A` are the same evidence with the sign flipped. The canonical key merges them.
- `validate_experiment_config` accepts any pair from `ALLOWED_ARMS = (A, B, C, D)`. The production library (`primitives._ARM_PAIRS`) admits only `A->B`, `B->C`, `C->D`. So skip pairs are harness-legal but blocked by the production enum. The expansion stays in the dev module and does not touch the enum.

### Measured result of the expansion (atom_analysis.py, real history: 12 measured keys)

- Every skip pair (`A->C`, `A->D`, `B->D`) and every reversed pair is **recombination-only** under the default seeds `(42, 43, 44)`. Every default-seed atom is already measured.
- Only the replication seed set `(7, 17, 29)` produces **new predictive evidence**. Its atoms have never been measured.

So under the frozen arms, estimators, folds and default seeds, the expansion yields new decision questions on existing evidence, not new AUC evidence.

## 2. Verification

| Check | Command | Exit | Result |
|---|---|---|---|
| New search-space tests | `py -3 -m pytest autonomous_agent/test_search_space.py -q` (in `dev/`) | 0 | 13 passed |
| Dev suite excluding v110 | `py -3 -m pytest -q --ignore=autonomous_agent/test_v110_wiring_e2e.py` | 1 | 405 passed, 17 failed, 10 errors |
| v110 wiring suite (with production `stat_validation_h10` on PYTHONPATH) | `py -3 -m pytest -q autonomous_agent/test_v110_wiring_e2e.py` | 1 | 37 passed, 1 failed |
| Full dev suite (default) | `py -3 -m pytest -q` | 2 | collection error: `No module named 'family_records'` |
| Protected production hashes | recomputed sha256 vs `.c4_protected_hashes_before.json` | 0 | 11 checked, 0 mismatches |

### The failures are test-fixture problems, not regressions

- `test_v110_wiring_e2e.py` sets `REPO = parents[1]` and inserts `REPO/stat_validation_h10`. In the dev tree that directory doesn't exist, so collection fails. The one remaining failure needs `autonomous_agent/state/campaign_end_multiplicity.jsonl`, which the dev tree doesn't contain.
- The 27 other failures/errors all come from dev-tree paths that exist only at the production root: `state/campaign_config.json`, `state/proposal_ledger.jsonl`, `study_files/outputs/study_v1/development/event_table.csv`, `study_files/backend/demand_zone_study_v1.py`, `simh10`, and the `MAIN AUDITS` pinned artifacts.
- None of the failing tests touch `search_space.py` or `evidence_key.py`. I didn't change any test that existed before this phase.
- I did not fix the fixtures or weaken assertions. Making the suite green would need a dev-tree fixture mirror, which is a separate task.

## 3. Not done (honest limitations)

- **Quota-mode benchmark** (legacy / dedup / dedup+quota / expanded / expanded+quota): **not run.** No emitted-candidate, quota-refusal or stopping-reason numbers exist for these modes. The earlier claims about redundancy and novelty come from the earlier audit, not from this phase.
- **Leakage-safe temporal ranker evaluation** (base-rate vs prior vs last-outcome vs group-aware vs upgraded ranker): **not run.** The ranker's Brier improvement remains unverified. The repeated-configuration and near-constant-label concerns are open.
- **Outcome taxonomy and future-leakage tests:** **not implemented.**
- **Adaptive selection policy:** not built. Selection-benchmark claims are not made.
- **Feature transformations, new feature sets, and new estimators:** not implemented. The harness hard-codes four frozen feature arms and two estimators. Adding arms or estimators would change the frozen study and needs a protocol amendment. That amendment is not drafted here.

## 4. Conclusions

- **Can the agent now explore a substantively broader predictive space?** No. The expansion adds decision questions over existing evidence. Only the replication seed set adds new evidence, and that is a seed resampling, not a new model hypothesis.
- **Does the ranker show reliable improvement?** Not demonstrated. It was not evaluated in this phase.
- **Was any predictive improvement measured?** No. No model was trained or evaluated, and no AUC was computed.
- **Quota amendments:** not enabled, not benchmarked, and not activated in production.

## 5. Recommended next steps (for owner review)

1. Decide whether the replication seed set should be allowed as a development-only atom family. It is the only dimension that yields new evidence under the frozen harness.
2. If feature-arm or estimator expansion is wanted, draft a protocol amendment with a hypothesis, a baseline, and falsification criteria. Do not implement it in production.
3. Build a dev-tree fixture mirror so the full dev suite can run from `dev/` without the production root.
4. Run the quota-mode benchmark and the temporal ranker evaluation before any production wiring.
