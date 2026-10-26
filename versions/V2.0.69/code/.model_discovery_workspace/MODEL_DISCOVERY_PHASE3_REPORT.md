# Demand Zone AI — Phase 3 engineering status

**Status: PARTIALLY COMPLETE.** Implemented and executed an isolated, explicitly disabled candidate-search v2 in the development tree, added group-weighted outcome priors, and added regression tests. Search engineering diversity improved on deterministic synthetic fixtures. No real-market predictive improvement is established, no campaign ran, no production generator or frozen policy changed, and the sealed holdout was not accessed.

## What changed in this run

- [candidate_search_v2.py](dev/autonomous_agent/proposal_layer/candidate_search_v2.py): standalone v2.0.1 candidate generator, canonical candidate/evidence identities, strict schema, novelty/deduplication, diversity-aware budget selection, three executable sklearn model families, three transforms, feature-subset ablations, and chronological evaluation with ROC-AUC, average precision, Brier, runtime. Canonicalization now collapses reordered feature columns and tree standardization (a positive affine transform that leaves the included tree splits invariant); the original authored config is retained. It is isolated and not imported by a production path.
- [protocol_amendment_v2.json](dev/autonomous_agent/proposal_layer/protocol_amendment_v2.json): records the v2.0.1 canonical identity refinement; still proposal-only, owner and independent statistical approvals pending.
- [outcome_ranking.py](dev/autonomous_agent/proposal_layer/outcome_ranking.py): group-weighted Beta priors; repeated ledger rows for the same (direction, measurement key) count at most once, preventing repeated experiments from creating unjustified confidence. Missing/non-boolean outcomes and invalid shrinkage strength fail closed.
- [research_memory.py](dev/autonomous_agent/proposal_layer/research_memory.py): clarified canonical measurement-key attribution for ranker inputs; existing taxonomy continues to distinguish rejection, unavailability, interruption, invalid config, inconclusive, redundancy, replication, and novelty.
- [test_candidate_search_v2.py](dev/autonomous_agent/test_candidate_search_v2.py), [test_outcome_ranking_grouped.py](dev/autonomous_agent/test_outcome_ranking_grouped.py): validity, identity, duplicate, temporal split, metrics, opt-in, group weighting, uncertainty, and fail-closed tests.
- [generator_v2_benchmark.py](generator_v2_benchmark.py), [generator_v2_benchmark.json](generator_v2_benchmark.json), [generator_v2_benchmark.log](generator_v2_benchmark.log): reproducible synthetic candidate search comparison and execution output.
- [phase3_temporal_ranker.py](phase3_temporal_ranker.py), [phase3_temporal_ranker_v2.json](phase3_temporal_ranker_v2.json), [phase3_temporal_ranker_v2.log](phase3_temporal_ranker_v2.log): group-weighted chronological replay on adjudicated ledger outcomes.

The prior [generator.py](dev/autonomous_agent/proposal_layer/generator.py), [evidence_key.py](dev/autonomous_agent/proposal_layer/evidence_key.py), [search_space.py](dev/autonomous_agent/proposal_layer/search_space.py), legacy bias policy, production harness, and production entrypoints were not modified. The current approved generator collapses n_boot/calibration variations to evidence identities because they affect only uncertainty/calibration decision reporting; directionally reversed evidence and atoms also explain apparent different proposals mapping to same measurements. On the production renderer there are 16 executable evidence keys, 12 historically measured and 4 unmeasured. Legacy emitted 18 with 18/18 redundant; measured-evidence dedup emitted 0. Dedup-plus-amendment's 2 new keys depended on proposed quota changes and remains unauthorized.

## Search benchmark (deterministic fixture, not market evidence)

Original benchmark rerun (budget 64): legacy emitted 18, all redundant (1.0 duplicate rate), 0 novel evidence; dedup emitted 0; dedup-plus-unapproved quota amendment emitted 2 novel seed-replication keys with 0 duplicates. Expanded frozen-arm pool (previous mode 4 simulation, rerun) yielded 56 raw keys / 32 direction-deduplicated keys, 32 harness-valid and 0 invalid, 20 simulated emits (6 default-seed keys, 14 replication-seed keys), then pool-exhausted. This is a pool simulation, not a real generator/harness campaign.

New isolated search (mode 5 dev capability) in [generator_v2_benchmark.json](generator_v2_benchmark.json): raw catalog 120 candidates; after actual canonical deduplication, selection now removes 32 effectively equivalent tree-scaling configurations, leaving 88 unique identities; it selected **18 distinct synthetic evidence keys** within budget with no repeats/invalids. Coverage: 3 model families, 3 transforms, 4 feature subsets. In the synthetic 160-train/80-validation run, validation positive rate was 56.25%; mean ROC-AUC .7684, AP .8122, Brier .2025; latest measured total runtime 10.57 seconds. These are fixture smoke-test metrics, not evidence of prediction improvement. Mode 5 is implemented and benchmarked only in the isolated synthetic framework, not approved campaign protocol.

The same synthetic fixture produces 18/18 new fixture identities but cannot serve as a real same-universe performance comparison with historical legacy's 0/18 distinct eligible real evidence: one is synthetic engineering coverage, the other real-history measurement-key exhaustion. Interpret as implementation capability, not scientific uplift.

The existing intended five-mode benchmark remains **3/5 complete** based on prior deterministic runs. Modes 4–5' prior expanded-pool helper was a simulation over the frozen arms and independent seeds, not an executable model-space integration; I did not relabel it complete or conflate candidate_search_v2 with that original benchmark. New model families/features are executable offline via v2 but campaign eligibility remains blocked on protocol approval.

## Outcome ranking replay

The group-weighted replay [phase3_temporal_ranker_v2.json](phase3_temporal_ranker_v2.json) uses 69 adjudicated outcomes, 68 scored rows, 12 measurement groups, 7 directions, and outcomes dated 2026-10-05 through 2026-10-16. Future-flip check: 33 earlier predictions unchanged; direct estimator refuses future rows.

- All as-of rows (68; 56 pass; 12 groups): base-rate Brier .1654 / AUC .600; group-mean Brier .1251 / AUC .844; group-weighted outcome prior Brier **.1039** / AUC .923; seeded random-probability baseline Brier .2916 / AUC .554. Paired row-bootstrap interval from the prior replay for outcome-prior minus group-mean Brier was [-.0531, .0100], including zero.
- First occurrence with prior history (11 rows; 9 pass; 11 groups): base/group mean Brier .2347; outcome prior .2549; uncertainty wide and includes zero. Point estimate is worse on Brier.
- To give a one-record-per-key group view, the ranker now separately scores each measurement group once at its first occurrence (30 groups had prior outcomes; 25 passed). Base-rate Brier .1731 / AUC .588; outcome prior .1727 / AUC .752; group-cluster paired bootstrap of Brier difference (outcome minus base) 95% CI [-.0608, .0605]. This is inconclusive. Seeded random probability Brier .25 / AUC .50.
- Repeat-group rows (57; 47 pass; 11 groups): outcome prior Brier .0747 vs group mean .1039. This is repeat-key performance, not unseen-group evidence.

This replay is one October 2026 chronological cohort, not multiple chronological periods or unseen campaigns; same-key measurements are still related and the independent trial weight now caps at one per key. The first-seen group CI includes zero, so no ranker promotion. Ranker remains dev-only. Rejected hypotheses remain evidence; execution failures, unavailable evidence, and inconclusive runs are not converted to negative/positive outcomes.

## Verification and environment

Targeted dev regression command:

```bash
cd .model_discovery_workspace/dev
py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py autonomous_agent/test_outcome_ranking_grouped.py autonomous_agent/test_phase3_research_memory.py autonomous_agent/test_upgrade.py autonomous_agent/test_search_space.py autonomous_agent/test_generator_repair.py
```

Result after final canonical-identity repair: **68 passed, exit 0**. The new candidate benchmark and temporal ranker both ran successfully and wrote their JSON outputs/logs above. Full development suite from `cd .model_discovery_workspace/dev; py -3 -m pytest -q autonomous_agent` was attempted after the final source changes and **failed at collection**, exit 2: `test_v110_wiring_e2e.py` imports absent `family_records`. Full suite excluding only that collecting module was also run without altering tests: **17 failed, 428 passed, 10 errors, 26 subtests**, exit 1. Failures/errors are the recorded fixture/provenance blockers: campaign/frozen state and R-3 grant records absent from dev tree, missing `simh10`, missing development `event_table.csv`, missing `demand_zone_study_v1.py`, and a missing Campaign 1 audit artifact. No test was skipped or weakened; those outcomes remain failures, not passes.

Final targeted regression command after canonical-identity change: `py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py autonomous_agent/test_outcome_ranking_grouped.py autonomous_agent/test_phase3_research_memory.py autonomous_agent/test_upgrade.py autonomous_agent/test_search_space.py autonomous_agent/test_generator_repair.py` — **68 passed**, exit 0. Five-mode-compatible legacy, dedup and amendment benchmarks reran with the numbers above. The expanded-pool helper was rerun successfully from workspace root using `dev` as `code_root`. No campaign execution is involved.

No market-data predictive evaluation was performed. Synthetic fixture scores are not presented as market evidence. The separate source baseline replay reports a historical/approved model score in prior artifacts, but this run did not re-evaluate that model on comparable data or splits.

## Integrity gates and remaining work

- No campaign launched or experiment executed against real data.
- Sealed holdout was not opened, queried, fitted, tuned, or read by these changes.
- Frozen production configs, existing measurement pins, campaign history, and signed decisions were not edited.
- No protocol waiver, estimator, model family, feature family, quota, acceptance threshold, or sign-flip/multiplicity decision was activated.
- New v2 code is a genuine local candidate framework but is not yet validated against actual production entrypoint data contracts. Production allowlist and feature inventory remain closed.
- Owner approval plus independent statistical review required for model/feature-universe expansion, data eligibility, and evaluation protocol. Sign-flip inference for the intended data still requires review of temporal dependence, exchangeability/sign symmetry, multiplicity and p-value validity; executing fixture code is not validation.
- No valid multi-period, unseen-campaign evaluation of historical outcome ranking; broader eligible real-data evaluation remains unmeasured.
- Five canonical benchmark modes in a common production candidate protocol remain incomplete: modes 1–3 rerun; mode 4 is a deterministic frozen-arm pool simulation; mode 5 is an isolated synthetic candidate-search benchmark. Neither 4 nor 5 is authorized or integrated with campaign generation. Full suite fixture/provenance repair remains outstanding.

Next safe milestone is an isolated fixture package for the blocked dev suites plus an explicit approved feature/model protocol before any real-data evaluation or campaign integration.
