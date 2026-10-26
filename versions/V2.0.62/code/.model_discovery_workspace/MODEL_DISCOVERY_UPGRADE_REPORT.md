# Model-Discovery Upgrade Report (development only)

Scope: all changes are in `.model_discovery_workspace/` (dev copy and bench/diagnostic scripts). No file under the repo's production code, frozen configs, ledger, or campaign state was edited. No experiments were executed, no campaign was launched, and the sealed holdout was not touched.

## 1. What changed (dev copy only)

| Change | File | Default | Status |
|---|---|---|---|
| Measurement-key dedup (mirrors production renderer) | `dev/autonomous_agent/proposal_layer/evidence_key.py` | opt-in via `measured_keys` | tested |
| Candidate identity recomputed on demand (no new candidate field) | `proposal_layer/generator.py` `_candidate_evidence_key` | n/a | fixes a frozen-contract failure I introduced earlier |
| Falsification-floor prototype: floor is vacuous when no novel falsification candidate exists | `generator.py` (`falsification_floor_vacuous_when_no_novel`) | off | protocol amendment, prototype |
| Replication cold-start prototype: share cap skipped below `replication_cap_min_portfolio` | `bias_governor.py` | `1` = legacy | protocol amendment, prototype |
| Outcome-score bonus in ranking (weight 0 = legacy order) | `generator.py` (`outcome_scores`, `outcome_ranking_weight`) | off | tested for reordering only |
| Outcome-prior module (Beta-shrunk, temporal guard) | `proposal_layer/outcome_ranking.py` | not wired by default | tested |
| Gate guards (fail-closed on missing/undecided records) | `dev/autonomous_agent/gate_enforcement.py` | not wired into loop | tested |

## 2. Corrected diagnosis of the deadlock

My earlier report said the 35% falsification floor alone blocks the 4 unmeasured keys. That was incomplete. Verified on the real view:

- With the floor fully off, 304 candidates exist, but **zero** have an unmeasured key. The 18 `seed_set_replication` candidates are refused as `BIAS_QUOTA`.
- Cause: in a fresh scope, the first replication candidate projects a portfolio of one, so its replication share is 1.0 against the 0.5 cap. The cold-start cap blocks replication before any falsification question arises.
- Relaxing only the floor therefore leaves the deadlock in place. Both rules need amendment.

## 3. Benchmark (offline, outcome-free; same real view; budget 64, 3 per cycle, 40 cycles)

| Mode | Emitted | Novel | Redundant | Cycles | Stop reason |
|---|---|---|---|---|---|
| Legacy | 18 | 0 | 18 (100%) | 7 | no admissible candidate |
| Dedup only | 0 | 0 | 0 | 1 | no admissible candidate |
| Dedup + both prototype amendments | 2 | 2 | 0 (0%) | 3 | no admissible candidate |

- Novel keys reached: 2 of the 4 unmeasured keys. The remaining limit is the replication class budget of 2 in `bias_policy.json`.
- Legacy regression: with the dev code and no options, the legacy output equals the saved baseline (`bench_legacy.json`) exactly, except the `code_root` string. Verified before and after the refactor.
- Files: [bench_legacy_v4.json](.model_discovery_workspace/bench_legacy_v4.json), [bench_dedup_v3.json](.model_discovery_workspace/bench_dedup_v3.json), [bench_dedup_amend_v3.json](.model_discovery_workspace/bench_dedup_amend_v3.json).

## 4. Outcome-aware replay (temporal, on the real ledger)

- 69 adjudicated experiments, 68 scored, 12 measurement groups, 7 directions (after fixing a direction mapping bug; the directions now come from proposal rows).
- Each prediction uses only observations strictly before its time. The leakage guard refuses an observation at or after the cutoff (verified: `true`).
- Brier, outcome-aware prior: **0.116528**. Brier, base-rate predictor: **0.172921**.
- File: [outcome_replay.json](.model_discovery_workspace/outcome_replay.json).

**Caveats, which limit this result:**
- The label is near-constant: 56 of 69 pass, and only 10 distinct `primary_delta` values exist.
- Groups repeat the same configurations, so the gain may come from group memory of duplicated outcomes, which is the redundancy problem itself. I did not test this against a same-group-last-outcome baseline.
- 68 points, one ledger, no significance test, no independent validation.
- The ranker cannot yet reorder the 4 unmeasured keys, since they have no outcomes.

## 5. Tests (exit codes are from the commands run)

- `test_evidence_dedup.py` + `test_gate_enforcement.py` + `test_upgrade.py`: **29 passed, exit 0**.
  - `test_upgrade.py` (12): leakage refusal, known-before cutoff, future outcome cannot change an earlier estimate, base-rate fallback, Brier validation, replication cold-start default and flagged behavior, default-off equivalence with legacy output, zero outcome weight is inert, and reordering only among admissible candidates (checked against `_build_candidates`).
- Dev regression across `test_stage4_capabilities`, `test_proposal_layer`, `test_generator_repair`, `test_stage3_adversarial`, plus the three dev files: **134 passed, 1 failed**.
  - The failure is `test_campaign1_evidence_unchanged`. It looks for an audit file under the dev folder, which exists only in the real repo. Running the same test in the repo gives **exit 0**. This is a path problem in the dev copy, not a regression.
  - An earlier failure, `test_stage4 test_14`, was caused by my `evidence_key` candidate field. It is fixed by recomputing the key on demand, and that suite now passes.
- Not run: the full repo suite (428 tests reported earlier) was not re-run after these dev changes. The repo source was not edited.

## 6. Not achieved

- **Search-space expansion: not implemented.** The harness hard-codes four feature arms from the frozen study module and two estimators in `ALLOWED_ESTIMATORS`. Expanding the grid therefore needs a protocol amendment, and I did not prototype one. No expansion tests exist.
- **Predictive improvement: not measured.** No model was executed. AUC gains remain unmeasured.
- **Outcome-aware ranking in the generator: not validated end-to-end.** The reorder hook is tested, but it is not validated on historical replay beyond the Section 4 result.

## 7. Items requiring owner or statistical approval

1. **Falsification-floor amendment** (`falsification_floor_vacuous_when_no_novel`). Limit: the 35% floor blocks progress once novel falsification evidence is exhausted. Risk: if the "no novel falsification candidate" check is wrong, the floor is switched off while falsification evidence is still available, weakening the steering rule. Evidence needed: a validated check of that condition on the frozen view, plus a regression test. Owner and statistical sign-off required.
2. **Replication cold-start amendment** (`replication_cap_min_portfolio`). Limit: the share cap is 100% on a portfolio of one. Risk: allows up to the class budget of replications early in a campaign. Owner and statistical sign-off required.
3. **Evidence-universe expansion.** Needs a protocol amendment to the harness's allowed arms and estimators. Not prototyped.
4. **Wiring outcome-aware priors into the loop.** Needs the replay to be validated on a larger, independent history. Not authorized here.
5. **Gate guards into the loop** (`gate_enforcement.py`). The campaign loop still does not read `launch_gates.json`. Owner decision.
6. **`require_human_approval: false`** in frozen configs. Its authorization record is not found in the repo. Owner decision.
7. **Independent statistical review.** Still outstanding. An AI review, code tests, or an owner substitute do not satisfy it.

## 8. Stop

I am stopping here for owner review. The dedup and cold-start fixes produce novel, non-redundant proposals in an offline replay, but that is a replay result only. The predictive value of any new candidate is unknown.
