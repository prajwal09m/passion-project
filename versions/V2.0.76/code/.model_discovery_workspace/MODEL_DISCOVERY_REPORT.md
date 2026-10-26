# Model-Discovery Engine: Audit, Dev Remediation, Benchmark, Gate Review

Date: 2026-10-17. Scope: audit and offline benchmark only. **No campaign was launched, no experiment
was executed, no budget was consumed, the sealed holdout was not accessed, and no repository source
file was modified.** All new code lives in `.model_discovery_workspace/`.

## 1. Audited (source-inspected)

| Stage | Source | What it does |
|---|---|---|
| Candidate generation | `autonomous_agent/proposal_layer/generator.py` | Deterministic grid over primitives × parameters. Ranking uses a closed input set. `novelty_score` is a constant 1.0. Outcomes are not inputs by design. |
| Ranking and scoring | `proposal_layer/bias_governor.py` | Score = weighted quota pressure, novelty, evidence gap, priority, exploration. |
| Validation and approval | `proposal_layer/cycle.py` | Approval auto-accepts with `approver=policy:auto` when `require_human_approval` is false. |
| Execution order | `continuous_loop.py::_select_next` | Portfolio minimums first, then first-approved order. No value-based ordering. |
| Measurement | `recipe_harness.py`, `compiler.py::_render_config` | Renders the config. Measured AUC depends only on arms, estimators, seeds, folds, baseline. |
| Promotion | `recipe_harness.decision_criteria_pass` | Delta ≥ predeclared minimum, CI lower ≥ floor, folds ≥ 3, calibration margins. |

## 2. Verified weaknesses (measured on the existing ledger and artifacts)

| # | Finding | Evidence | Status |
|---|---|---|---|
| W1 | 69 adjudicated experiments produce only **12 distinct measured outcomes**. 68 of 69 proposals sit in repeated groups. | `.model_discovery_workspace/redundancy_summary.json`, `outcome_groups.txt` | independently verified |
| W2 | The executable grid spans **16 measurement keys**, of which 12 are measured. | `bench_dedup.json` (`evidence_universe_keys`) | independently verified |
| W3 | The measurement key partitions the 69 experiments exactly as measured AUCs do. | `measurement_key_validation.json` (`partitions_identical: true`) | independently verified |
| W4 | `premium` (complexity_premium_check) changes the acceptance threshold (0.005 vs 0.01), not the model. The generator therefore selects its own pass bar. | spec diff of two candidates; `primitives.py` | source-inspected and spec-verified |
| W5 | `n_boot` and threshold variants add proposals with no new evidence. | key invariance tests | independently verified |
| W6 | 56 of 69 adjudications pass the gate (81%). | `baseline_summary.json` | independently verified (counts only) |
| W7 | The selection is outcome-blind by design, so it does not learn from results. | `generator.py` docstring; `_ranking_key` | source-inspected |
| W8 | `require_human_approval: false` appears in the frozen Campaign 2–4 configs. Approvals are recorded as `policy:auto`. Campaign 2 audit documents it; no Campaign 4 owner sign-off on it was found. | `campaign_config.json` line 221; Campaign 2 audit | source-inspected; owner review needed |
| W9 | The campaign loop never reads `launch_gates.json`. Only the readiness checker and its tests do. | grep over `autonomous_agent/*.py`, `stat_validation_h10/*.py`, `proposal_layer/*.py` | source-inspected |

## 3. Implemented (dev copy only)

**A. Measurement-key deduplication (opt-in).** `.model_discovery_workspace/dev/autonomous_agent/proposal_layer/`
- `evidence_key.py`: `measurement_key(primitive, params, baseline_id)`. Mirrors the production renderer.
- `generator.py`: optional `measured_keys` argument. When `None`, behavior is unchanged.

Tests: `test_evidence_dedup.py`, 7 tests, **OK** (`dedup_tests.log`, exit 0). They cover drift against
the real `compiler._render_config` for every grid candidate, parameter invariance, exclusion of measured
evidence, one measurement per cycle, the disabled path, and fail-closed on malformed arm pairs.

Regression: with dedup disabled, the dev code produces the same first-cycle fingerprints and statistics
as the repo (`bench_legacy.json` vs `bench_dev_legacy.json`: identical).

**B. Gate guards (proposed, not wired in).** `dev/autonomous_agent/gate_enforcement.py`
- `require_human_gates`: fails closed on missing, undecided, malformed, or absent gate records. Reuses the readiness checker's rules.
- `require_authorized_auto_approval`: refuses `require_human_approval: false` without an existing named authorization record.

Tests: `test_gate_enforcement.py`, 10 tests, **OK** (`gate_tests2.log`, exit 0; one check read the real gate
record and reported that it currently passes).

## 4. Benchmarked (offline, outcome-free)

Same real evidence view, 64-proposal fresh budget, 3 per cycle, up to 40 cycles, every emitted proposal
assumed executed. Scoring uses the production renderer. No AUC is read or predicted.

| Generator | Emitted | Redundant with history | Novel evidence | Stop reason |
|---|---|---|---|---|
| Current (repo) | 18 | **18 (100%)** | 0 | no admissible candidate |
| Dedup (dev) | 0 | 0 | **0** | no admissible candidate |

**Why dedup stalls.** The 4 unmeasured keys all come from `seed_set_replication`, a replication-only
primitive (`falsification_capable: False`). The frozen falsification-share floor (35%) refuses all
non-falsification candidates (174 refusals, `BIAS_QUOTA`). Dedup removes the redundant falsification
candidates that could raise the share, so the floor can never be met and the novel candidates never
open. This is a deadlock between two rules.

**What this shows.** Dedup removes all wasted duplicate proposals (100% → 0%). It produces no new
evidence. **Predictive improvement is not demonstrated.** No AUC was measured, because execution is not
authorized.

## 5. Launch-gate and approval review (W8, W9)

- The guards in §3B would **pass** today's `launch_gates.json`, because every gate is recorded. They would
not have blocked Campaign 4. Their value is for future campaigns.
- Presence is verified, not substance. The independent-review gate is satisfied by the owner's
  substitute route, which the owner record discloses as a weakened form of independence. This report
  does not treat it as independent review.

## 6. Needs prospective owner approval (not applied)

1. Activating measurement-key dedup in the production generator and evidence view.
2. Amending the falsification-share rule, which the dedup deadlock requires. This is a protocol change.
3. Removing `premium` and other threshold parameters from the search space (W4).
4. Wiring the gate guards into the campaign loop.
5. Reviewing `require_human_approval: false` in the frozen configs and whether it was owner-authorized (W8).
6. Widening the evidence universe with new measurement dimensions (estimators, feature sets). This is the
   real lever for discovering new predictive information. It needs a protocol amendment.

## 7. Verification log

| Check | Command | Result |
|---|---|---|
| Dedup tests | `py -3 -X utf8 -m unittest autonomous_agent.test_evidence_dedup` (in dev) | 7 OK, exit 0 |
| Gate tests | `py -3 -X utf8 -m unittest autonomous_agent.test_gate_enforcement` (in dev) | 10 OK, exit 0 |
| Regression (disabled path) | benchmark legacy in repo vs dev | identical fingerprints and stats |
| Protected artifacts | SHA-256 vs `.c4_protected_hashes_before.json` | 11 checked, 0 mismatches |
| Repo source | no repo source edited this session | verified by scope of writes |
| Full repo suite | not rerun | no repo source changed; last run 428 OK, exit 0 |

## 8. Limitations

- The benchmark replays current evidence only. It cannot show predictive value without new execution, which is not authorized.
- The benchmark assumes every proposal is executed before the next cycle.
- The measurement key was validated only on the 69 Campaign 2–4 experiments.
- Independent statistical review remains outstanding. The owner's substitute review is not independent review.
- The sealed holdout was not accessed.
