# Demand Zone AI — Phase 4 implementation and validation

**Overall: PARTIALLY COMPLETE.** The development fixture tree is now self-contained and provenance-checked; the missing imports and all previously recorded test failures/errors were resolved without changing protected source assertions. Candidate-search and ranking code received concrete development-only improvements and was benchmarked. The replay finds no reliable unseen-group advantage. No eligible real-market AUC comparison was authorized/performed; no campaign integration was activated.

## Code and fixture changes

- [restore_dev_test_fixtures.py](restore_dev_test_fixtures.py) stages an explicit allowlist of 53 retained development/provenance inputs into `dev/`, verifies source pins and copy hashes, and writes [FIXTURE_PROVENANCE.json](dev/FIXTURE_PROVENANCE.json). It does not copy or enumerate the prospective/holdout directory. Every staged file reverified against the manifest: **53/53 match; holdout path absent**.
- [test_v110_wiring_e2e.py](dev/autonomous_agent/test_v110_wiring_e2e.py) now imports the staged `family_records`, campaign finalization and `simh10` copies and verifies their fixture hashes against the manifest. [test_signflip_port.py](dev/autonomous_agent/test_signflip_port.py), [test_census_manifest.py](dev/autonomous_agent/test_census_manifest.py), and [test_recipe_harness.py](dev/autonomous_agent/test_recipe_harness.py) read explicit staged event-table/study/reference inputs. Missing fixtures now fail clearly rather than silently falling through to the source checkout.
- The original 17 test failures and 10 errors were environment fixture omissions, not a reason to weaken assertions: absent Campaign 3/4 state, exact pin/governance records, campaign ledger/results, Campaign 1 audit and retained data were copied from their authoritative source locations. The R-3 authorization was verified from the recorded owner grant; the C4 real-data predeclaration explicitly says NOT AUTHORIZED, and the next-stage record says owner approval and independent statistical review are pending.
- [candidate_search_v2.py](dev/autonomous_agent/proposal_layer/candidate_search_v2.py) is versioned v2.0.2 and remains dev-only. The catalog now spans three estimator families, three feature operators (original, pairwise interactions, nonlinear marginals), three preprocessing transforms and feature subsets. Effective identities canonicalize unordered columns and tree-only standardization; expanded feature maps remain distinct hypotheses. Candidate selection validates exact schemas, removes equivalent configs and uses measurable marginal diversity, not novelty claims based on prose.
- [outcome_ranking.py](dev/autonomous_agent/proposal_layer/outcome_ranking.py) now parses timestamps as UTC instants, enforces strict as-of cutoffs, gives each direction/config group at most one vote, retains statuses/IDs/reasons, and excludes failed, refused and inconclusive outcomes from binary labels. `rank_candidates` exposes an optional uncertainty bonus for explore/exploit experiments; it is a dev heuristic, explicitly not a calibrated market-AUC prediction or campaign hook. [test_outcome_ranking_grouped.py](dev/autonomous_agent/test_outcome_ranking_grouped.py) adds tests for status attribution, exploration, tied/offset timestamps, group weighting and leakage.
- [phase4_replay.py](phase4_replay.py) uses the append-only ledger plus linked spec/results. It scores the first adjudicated outcome for each exact measurement config once, regardless of direction; repeat executions cannot re-label the first unseen-group target. Strictly earlier configs alone form priors, simultaneous timestamps are batched, and the fixed median-time second half is reported separately. Failed safety-gate runs are not called model successes.

## Test results

The final command `py -3 -m pytest -q autonomous_agent` was rerun against the entire isolated development test directory after the final fixture/ranking/replay edits: **497 passed, 26 subtests passed; 0 failed, 0 errors; exit 0** (330.65 seconds). No modules were excluded or skipped. Full output is captured in [phase4_final_dev_suite.log](phase4_final_dev_suite.log), including the explicit `EXIT_STATUS=0` marker.

Additional verification after the full-suite run: `py -3 -m pytest -q autonomous_agent/test_v110_wiring_e2e.py autonomous_agent/test_signflip_port.py` passed **54 tests, 4 subtests** in 329.70 seconds. The ranking/search targeted tests passed **19/19** after the uncertainty-ranking addition. The real recipe-harness group also passed **11 tests, 4 subtests**. These were separate reruns, not substituted for the full suite.

The suite run operates exclusively under `.model_discovery_workspace/dev`; no experiment/campaign launch command was run. Protected source values rechecked: Campaign 4 config, live and archived loop-state, campaign proposal ledger, campaign-end multiplicity artifact, launch gates, owner decision record and archive SHA manifest all match their recorded SHA-256 pins. The final test working directory has no `experiment_registry.json` fixture because this suite uses disposable fixtures and must not create or mutate it. The source registry was not changed. Sealed prospective directory remains absent.

## Candidate diversity benchmark

Reproduced [phase4_benchmark_legacy.json](phase4_benchmark_legacy.json), [phase4_benchmark_dedup.json](phase4_benchmark_dedup.json), [phase4_benchmark_dedup_amend.json](phase4_benchmark_dedup_amend.json) under the same legacy protocol (budget 64, 3 per cycle, same 16-key renderer universe; 12 already measured):

| Mode | Emitted | Distinct novel measurement keys | Redundant | Duplicate rate | Status |
|---|---:|---:|---:|---:|---|
| Legacy frozen generator | 18 | 0 | 18 | 1.00 | Exhausted admissible candidates |
| Evidence dedup only | 0 | 0 | 0 | n/a | Correctly stopped: all eligible keys already measured |
| Dedup + quota amendment prototype | 2 | 2 | 0 | 0.00 | Reaches two seed-replication keys; amendment is unapproved and was not activated |

The quota-amendment row is engineering simulation only, not an authorized protocol change. Same-unit simulation confirms the amendment improves key reachability but not evidence that new model concepts improve prediction.

The separate synthetic candidate-search benchmark is recorded in [generator_v2_benchmark.json](generator_v2_benchmark.json) / [generator_v2_benchmark.log](generator_v2_benchmark.log): the v2 generator produced 360 raw configs; canonicalized 96 equivalents away; retained 264 executable identities; selected 18 unique synthetic evidence keys under budget 18 with 0 invalid/repeated selections. Selected coverage was 3 model families, 3 transforms and 4 feature subsets. Synthetic-only chronological 160/80 results: mean ROC-AUC **0.7678**, AP **0.8098**, Brier **0.2030**; no comparable market-data baseline exists. This demonstrates engineering diversity only, not predictive lift.

## Outcome-ranking generalization

Reproducible output: [phase4_outcome_replay.json](phase4_outcome_replay.json) and [phase4_replay.py](phase4_replay.py). Source ledger SHA-256 is `d97da268…f9ba8` (646 rows). The append-only data contains 74 executed attempts, 69 adjudications, 43 refusals, 5 interrupted failures. Of adjudications, 53 pass and 13 fail the predeclared criteria; three additionally rejected for non-statistical safety/integrity gates are treated as failed, not predictive successes. Nine linked spec/result artifacts are missing; their attempts are preserved as individually unlinked rather than merged. This missing provenance limits the replay.

The 12 exact executed measurement configurations produce 11 scored first-config groups with prior history (the earliest has no prior); the one-group-per-config outcome rate is 9/11 positive. Base-rate Brier **0.2311**, outcome-aware Brier **0.2415**; base AUC **0.111**, outcome-aware AUC **0.306**. Paired group-bootstrap 95% CI for outcome-aware minus base Brier: **[-0.0426, 0.0626]**. On the fixed chronological second half: 6 groups (4 positive), base Brier **0.2492**, outcome-aware **0.2913**, paired 95% CI **[-0.0399, 0.1167]**; AUC values are descriptive and unstable at n=6. Both intervals include zero, and the held-forward point estimate is worse. Posterior uncertainty is broad at these sample sizes. The exploration-weight heuristic is unit-tested only; replay did not promote it or claim gain.

The prior Phase 3 replay that scored all repeated rows (n=68 and favorable Brier/AUC) is not evidence of generalization: the row-weighted analysis inflates repeated group evidence. The corrected config-level replay is controlling for this report. The source history is concentrated in one October 2026 month and only 12 configs, so there is no unseen campaign or multiple-calendar-period validation. No ranker is promoted.

## Real-market AUC and approvals

The retained development event table and OOF predictions exist and are pinned in the source run manifest. The manifest identifies the development artifacts, but it is not owner confirmation that the proposed C4 integration procedure is approved or that the stage-specific holdout boundary is approved. The project's [C4 real-data predeclaration](../stat_validation_h10/C4_REAL_DATA_INTEGRATION_PREDECLARATION.md) is explicitly a draft, “NOT EXECUTED. NOT AUTHORIZED,” with unresolved holdout boundary and configuration/metrics details; [C4 next-stage readiness](../stat_validation_h10/C4_NEXT_STAGE_READINESS_REPORT.md) records real-data integration as owner-pending and independent statistical review unresolved. Therefore no new model comparison/AUC calculation against retained market data was run. No sealed holdout was accessed. Exact blocker: written owner authorization and a completed, reviewed predeclaration (including eligible dataset/split/holdout boundary) are absent. Model/feature expansion also remains proposal-only pending owner and independent statistical approval.

## Integrity, scope, and final status

- Campaigns launched: **0**. Production generator, production harness and frozen policy were not changed.
- Holdout reads/accesses: **0**; prospective directory remains absent.
- Protocol amendment status: proposal only; owner approval and independent review are pending.
- Protected artifacts: pinned hashes match; no campaign state/ledger/archive was written by the fixture or replay tools.
- Full intended dev suite: **497 passed, 26 subtests, no failures/errors; exit 0**.
- Real market AUC gain: **not tested**; no result fabricated.
- Main remaining limitations: no valid market-data head-to-head AUC run authorized; only 12 historic config groups in one short month; 9 linked artifacts missing; corrected out-of-time replay does not outperform base rate reliably; experiment exploration ranking not validated; original five-mode common production-protocol benchmark is not fully complete (modes 4 and 5 remain simulations/dev capability); model expansion and integration must remain disabled pending recorded approvals.

**Definition of done is not fully met; status remains PARTIALLY COMPLETE.** Engineering, fixtures and reproducibility improved, but demonstrated real-market prediction improvement and authorization for actual market evaluation remain outstanding.