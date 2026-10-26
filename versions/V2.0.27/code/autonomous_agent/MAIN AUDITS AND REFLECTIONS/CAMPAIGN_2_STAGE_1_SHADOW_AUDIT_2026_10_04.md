# CAMPAIGN 2 — STAGE 1: SHADOW GENERATION AUDIT

**Date:** 2026-10-04
**Stage window (UTC):** pre-flight completed before 2026-10-04T23:04Z; record written 2026-10-04T23:04:47Z
**Operator:** autonomous agent (Buffy/Codebuff), human-authorized stage prompt
**Scope:** Generate and validate a bounded portfolio of research proposals from the REAL evidence view and REAL Campaign 1 history. **No experiment execution, no compilation, no adapter invocation.**

Authoritative references:
- Campaign 1 frozen audit: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md` (SHA-256 `47904cb1ba0f7b58f63a3c19a3853c10d8dcf7f673e060039ac9d076cdfab3e0`)
- Phase 1 design: `autonomous_agent/PROPOSAL_LAYER_DESIGN_PHASE1.md`
- Phase 2 implementation: `autonomous_agent/proposal_layer/`

---

## 1. PRE-FLIGHT VERIFICATION (before enabling the flag)

| Check | Result |
|---|---|
| Supervisor PID 243592 stopped | PASS — no such task |
| No python supervisor/experiment process running | PASS — `wmic` scan empty |
| Holdout sealed (`study_files/outputs/study_v1/prospective` absent) | PASS |
| Campaign 1 audit SHA unchanged | PASS `47904cb1…ab3e0` |
| 17 protected files match Phase-1 hashes (incl. `autonomy_config.json` `663088ea…5866`, flag `allow_autonomous_specs: true`) | PASS |
| Record counts 8/8/39/155/149 (spec_attempts/registry/adapter_events/events/agent_state) | PASS |
| Candidate workspaces = 11 | PASS |
| `allow_generated_proposals` OFF before stage | PASS |
| No `proposal_ledger.jsonl` existed before stage | PASS |
| Proposal-layer baseline suite green (27/27) before any change | PASS |

## 2. CONFIGURATION CHANGE (the ONLY authorized change before generation)

- `autonomous_agent/proposal_config.json`: `allow_generated_proposals` false → **true**
  - SHA-256 after: `3c902db086433b87e71bf847af8e6f423514d5970c44e41e1ff6b7150b2d6032`
- `autonomous_agent/autonomy_config.json`: **NOT modified** (hash still `663088eae957931689ac692d8664ab26d02f8b4b7e090894a5d3a89177885866`).
- **Documented test change (not silent):** `test_real_repository_flag_is_off` encoded the Phase-2 invariant "real-repo flag OFF" and was superseded by this stage's explicit authorization. It was replaced by `test_real_repository_flag_matches_reviewed_file`, which keeps the durable invariants: flag is a strict boolean, the reader mirrors the file fail-closed (missing/malformed ⇒ OFF), and the flag stays separate from `autonomy_config.json` (Campaign-1 setting asserted true). No safety gate was weakened; the fail-closed reader behavior is now tested MORE thoroughly (missing file + malformed file cases added).
- Full suites re-run with flag ON: **27 + 117 + 22 = 166/166 PASS**.

## 3. GENERATION RUN (shadow only)

Method: `cycle.run_proposal_cycle(root, seed=N)` for N = 1..5, **`approver=None`** (so proposals are created, transitioned to VALIDATING, run the full 9-gate chain, and **stop at awaiting-approval** — the cycle's compile step is unreachable without approval). Real evidence view (28 allowlisted sources), real Campaign 1 history, real ledger.

| Seed | created | awaiting approval | refused | failed validation | compiled | failed compilation |
|---|---|---|---|---|---|---|
| 1 | 3 | 3 | 0 | 0 | 0 | 0 |
| 2 | 3 | 2 | 1 | 0 | 0 | 0 |
| 3 | 3 | 1 | 2 | 0 | 0 | 0 |
| 4 | 3 | 0 | 3 | 0 | 0 | 0 |
| 5 | 3 | 0 | 3 | 0 | 0 | 0 |
| **Total** | **15** | **6** | **9** | **0** | **0** | **0** |

**0 compilations, 0 executions, 0 candidate workspaces created, 0 registry writes.**

Ledger: `autonomous_agent/state/proposal_ledger.jsonl` — 39 rows (15 proposal + 24 transition), 50,282 bytes, SHA-256 `7824853d82144d845a48f92b769fc25ff89205bd149725edebc409f11ecc040a` (append-only, fsync'd).
Evidence view at evaluation: `da4095f2d462cd04d6efab13fba2b199eeb09cbab7cc3a548fc29af42527fa2f`.
Bias policy: `df4e42a66fbf111523ab2d40dba04f9fd47de75e90d3f0e512b52915f4f127b4` (unchanged file).

Status histogram: `VALIDATING: 6, REFUSED: 9` (every proposal reached a terminal or held state; no proposal is unaccounted).

## 4. THE 17 EVALUATIONS

| # | Dimension | Result |
|---|---|---|
| 1 | Proposal count | **15** created across 5 bounded cycles (limit 3/cycle from `max_proposals_per_cycle`) |
| 2 | Refusal count | **9** refused, 6 awaiting approval, 0 failed-validation |
| 3 | Refusal reasons | `NEAR_DUPLICATE` ×9 — text-level near-duplicate of an earlier hypothesis (see OBS-1) |
| 4 | Falsification share | **0.47** (7/15) ≥ required floor 0.35 — PASS |
| 5 | Replication share | **0.00** ≤ cap 0.50 — PASS (replication is capped, not floored) |
| 6 | Design-signature diversity | **15/15 distinct signatures**, max signature count 1 (cap 2) |
| 7 | Exact duplicates | **0** in-run (15/15 distinct fingerprints); replay probe: all 8 Campaign 1 attempts refused `DUPLICATE` (8/8) |
| 8 | Near duplicates | 9 refused; every refusal independently re-verified: max difflib similarity vs prior hypotheses ≥ 0.90 (worst best-match **0.940**) — refusals correct, none spurious |
| 9 | Already-asked behavior | View built WITH ledger: `already_asked = 15` entries with statuses {VALIDATING: 6, REFUSED: 9}; view WITHOUT ledger: 0. Memory is ledger-derived and restart-safe |
| 10 | Campaign 1 rediscovery | Generated payloads overlapping Campaign-1 signatures: **0/15**; live replay of all 8 Campaign-1 attempts against real view+ledger → **8/8 refused DUPLICATE** |
| 11 | Holdout references | Ledger bytes contain **no** `/prospective/` path; injected holdout-path hypothesis → refused at `HOLDOUT_BLIND` / `HOLDOUT_REFERENCE`; real champion contained no holdout-path strings to strip (fixture test proves stripping works) |
| 12 | Free-code attempts | 0 code/path-looking strings in any payload's `design`+`parameters`; injected `__import__` param → `SURFACE`/`SURFACE_ESCAPE`; unknown payload key → `SCHEMA`; `generator_type=llm_assisted` → `GENERATOR_NOT_PERMITTED` |
| 13 | Validation bypass attempts | No proposal bypassed validation: every proposal is either VALIDATING (passed all 9 gates at creation) or REFUSED with a recorded gate/reason; illegal lifecycle transitions raise `LedgerError` (T10); probes confirm SCHEMA/SURFACE/HOLDOUT refusal paths live |
| 14 | Expected-outcome selection bias | Live: `BiasGovernor.score` identical with and without `preregistered_expectation`/`predicted_delta` (0.9492105263157894 == 0.9492105263157894); closed input set = {direction, proposal_class, novelty_score, evidence_gap_score, quota_pressure, priority, attempts_in_direction} — expectations excluded structurally |
| 15 | Quota enforcement | Live probes vs real policy: over-direction (5>4) → `BUDGET_EXHAUSTED`; over-signature (3>2) → `SIGNATURE_CAP`; below-floor confirmatory (fals share 0.00 < 0.35) → `BIAS_QUOTA`; replication class budget (3>2) → `BUDGET_EXHAUSTED`; total 21>20 → `BUDGET_EXHAUSTED`; control within caps → accepted. The in-run portfolio itself sits within every cap (awaiting: 3 validation + 3 calibration ≤ 4/direction; total 15 ≤ 20; signatures ≤ 1 ≤ 2) |
| 16 | Genuinely different designs | 15 unique fingerprints/signatures; params span 3 arm pairs × 2 estimators × 3 n_boot × 2 bin settings; **but** only 2 of 4 executable primitives and 2 of 8 directions were reached (see OBS-1/OBS-2) |
| 17 | Null/adverse-capable proposals | **15/15** carry a falsification rule that can fail: comparator `<`, threshold 0.0, metrics `min_year_delta` ×10 / `pooled_roc_auc_delta` ×5; 7 falsification-class proposals; all `preregistered_expectation` recorded as `uncertain` (prior evidence against) |

**Provenance completeness:** all 15 payloads carry all 18 required keys (schema/generator versions, direction, class, hypothesis, rationale.trigger, preregistered_expectation, falsification_rule, 5 evidence citations each with SHA-256, parent_version `V2.0.8`, baseline, design, parameters, fingerprint, signature); `generator_type` = `deterministic_compositional` on all 15; every transition row carries `at/from/to/reason_code`.

## 5. AWAITING-APPROVAL POOL (input for Stage 2, NOT yet approved)

| proposal_id | class | direction | primitive | params |
|---|---|---|---|---|
| prop-a2bbded289ab-1 | falsification | validation | year_stability_falsifier | B->C, LightGBM, n_boot 500 |
| prop-cf9f1efdf513-1 | falsification | calibration | calibration_stability_check | A->B, LGBM, bins 10, n_boot 500 |
| prop-0d1307b07bc5-1 | falsification | calibration | calibration_stability_check | A->B, LGBM, bins 5, n_boot 1000 |
| prop-226c2d55d3ae-1 | confirmatory | validation | year_stability_falsifier | C->D, LGBM, n_boot 1000 |
| prop-482b0e5b39cd-1 | confirmatory | validation | year_stability_falsifier | A->B, LR, n_boot 500 |
| prop-a40896751da3-1 | confirmatory | calibration | calibration_stability_check | A->B, LGBM, bins 5, n_boot 500 |

Class mix 3 falsification + 3 confirmatory (mixed-class, falsification present).

## 6. OBSERVATIONS (documented, NOT silently fixed)

**OBS-1 (moderate — diversity):** All 9 cross-cycle refusals are text near-duplicates. Templated hypothesis wording makes distinct-signature designs of the same primitive score ≥0.90 similarity (worst 0.940), so cycles 4–5 refused 3/3. This is *conservative* behavior (refuse, never execute) and the refusals are genuinely correct by the F.4.3 rule, but it concentrates the portfolio: only `calibration_stability_check` and `year_stability_falsifier` (directions calibration/validation) were reached. Effectively, the text gate — not the budget gate — is the binding cross-cycle limiter. Feeds Stage 3 (C: proposal diversity, G: duplicate detection).

**OBS-2 (moderate — steering):** The generator ranks by evidence-gap/priority, which permanently favors validation/calibration (0 accepted / 0 accepted history) over feature_engineering/model_architecture (3/3 accepted — high evidence, low gap). It also does not steer away from directions whose proposal budget is already consumed. Refused records count toward budgets by design ("forgetting refusals is the bias risk"), so repeated attempts in exhausted directions burn total budget (20) and could drive a budget-exhaustion stop. This is fail-safe (refusals, then stop) but wasteful; Stage 5's "repeated duplicate generation"/budget stop conditions must watch it. Feeds Stage 3 (V: budget enforcement) and Stage 5 design.

**OBS-3 (info — Stage 2 policy decision):** The 6 awaiting proposals passed ALL gates at their validation time (post-creation accounting then). Since then, 7 additional validation-direction and 2 calibration-direction refusals were recorded, so the direction caps (4) are now exceeded by *records* (validation 10, calibration 5). Re-running full validation NOW against current ledger state would refuse all 6 at the BUDGET gate, even though each passed when validated. Stage 2 must explicitly choose and record one coherent policy — (a) honor the recorded validation result (the cycle's designed flow validates then approves), or (b) re-validate and record the budget refusals — before approving anything. NOT decided or pre-applied here.

**No CRITICAL safety or scientific-integrity defect was found** (see exit criteria).

## 7. STAGE 1 EXIT CRITERIA

| Criterion | Result |
|---|---|
| No execution occurred | **PASS** — 0 compiled, registry still 8, adapter_events still 39, candidates still 11, no experiment processes |
| No holdout access | **PASS** — `prospective/` absent, 0 references in ledger, live injection refused `HOLDOUT_BLIND` |
| No Campaign 1 mutation | **PASS** — audit SHA + 17 protected hashes + 24 frozen artifact hashes + counts all unchanged (re-verified post-generation in §8) |
| No free-code generation | **PASS** — 0 code strings in payloads; live injection refused `SURFACE_ESCAPE`; static suite T11 green |
| Duplicate protection works | **PASS** — 9 near-dup refusals (all re-verified ≥0.90), 8/8 Campaign-1 replays refused `DUPLICATE`, 0 exact dups |
| Falsification quota works | **PASS** — share 0.47 ≥ 0.35; floor steering active; below-floor probe refused `BIAS_QUOTA` |
| Expected outcomes do not influence selection | **PASS** — identical scores with/without predicted outcomes; closed input set |
| Proposal provenance complete | **PASS** — 15/15 payloads all 18 keys, 5 hashed citations each, full transition history |
| At least one proposal can reasonably fail | **PASS** — 15/15 rules `metric < 0.0` (adverse/null outcome refutes); 7 falsification-class |
| No critical safety defect remains | **PASS** — OBS-1..3 are conservatism/efficiency/policy-ambiguity findings, none enabling leakage, execution, evidence tampering, gate bypass, or misleading science; all documented for Stage 3 |

**STAGE 1 RESULT: PASS (with observations OBS-1..3 carried forward).**

## 8. POST-STAGE IMMUTABILITY RE-VERIFICATION

Re-run of the full read-only check after generation:
- Campaign 1 audit SHA `47904cb1…ab3e0` unchanged; 17 protected hashes unchanged; 16 candidate + 8 version.json frozen hashes unchanged; baseline unchanged
- counts still 8/8/39/155/149; candidates still 11; `prospective/` absent
- `autonomy_config.json` `663088ea…5866` unchanged (flag `true` untouched)
- only new state: `proposal_ledger.jsonl` (39 rows) + `proposal_config.json` flag flip + this record
- supervisor still stopped (verified in final check)

*Full check output reproduced in the stage report; all lines PASS.*

---

**STOP.** Stage 1 ends here. No proposal was approved, compiled, or executed. Stage 2 (curated mixed-class execution) must not begin until its own entry verification passes and the OBS-3 policy question is explicitly resolved in the Stage 2 record.
