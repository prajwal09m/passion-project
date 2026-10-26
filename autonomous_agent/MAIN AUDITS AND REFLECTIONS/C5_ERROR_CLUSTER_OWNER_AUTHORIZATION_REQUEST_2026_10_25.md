# C5 ERROR-CLUSTER REVIVAL — OWNER AUTHORIZATION REQUEST (2026-10-25)

**Status at the moment of this request: nothing is running; nothing has been
resumed. Campaign 5 stays in its predeclared clean stop**
(`PORTFOLIO_COMPLETE`, 2026-10-25T14:33:19Z, cycle 24, 23/45 executions).
This packet only asks the owner to record YES/NO/DEFER decisions; no code,
config, or state changes beyond this file itself.

**What is being authorized.** The user-provided ceiling today is **no more
than 10 experiments** for this error-clustering revival. The predeclared
record proposes **5 experiments × 2 family members = 10 family members**
(half the declared family member bound of 20; no filler experiments are
proposed to reach the cap). The ceiling stays 10; the proposal sits inside
it.

**Record to sign:**
`autonomous_agent/MAIN AUDITS AND REFLECTIONS/C5_ERROR_CLUSTER_PREDECLARATION_2026_10_25.json`

Integrity, all re-verified today before making this request:

- canonical pin reproduces exactly (recomputed from
  `autonomous_agent.proposal_layer.schema.canonical_json` over the document
  minus the `pin` key): `25abbc7707faf56496f98d9fc5872f994ab813bd684622d3446f97cd4cae844e`
- file sha256 `3b6a5c0c14c5cc0c0dbac1e0eadb2d1cc62246cb3dc321e709f7cd0764f63cd9`
- all three implementation-lineage file digests match the live files
  byte-for-byte (`three_valued.py`, `multiplicity.py`, `primitives.py`);
  `test_error_clustering_declaration.py` is deliberately not pinned in the
  record (it is the pin's verifier and pins the record's digest instead,
  avoiding a self-referential pin)
- `test_error_clustering_declaration.py`: **23/23 passed**, exit 0

---

## 1. The two cluster definitions per experiment axis (frozen, outcome-free)

Every axis comes from the frozen demand-zone design vocabulary the
champion line already models. Every split threshold is intrinsic to the
feature's own scale (0 / {0,1} membership / 0.5 mid-percentile / 1.0 pivot
on a normalized or ATR-multiple scale); no quantile, median, or
data-derived constant is used, so no threshold was picked by looking at
the data. Both sides of every split are predeclared as members; there is
no favorable-side selection and no post-hoc renaming. No
outcome-dependent quantity (label, hold1_ret, any model score, any prior
result.json value) may be consulted in defining, selecting, or ordering
these definitions.

| Axis | Cluster 1 (error_cluster_1) | Cluster 2 (error_cluster_2) |
|------|------------------------------|------------------------------|
| vix_regime | high_volatility: `vix_percentile_60d >= 0.5` | low_volatility: `vix_percentile_60d < 0.5` |
| first_retest | first_retest: `zone_is_first_retest == 1` | subsequent_retest: `zone_is_first_retest == 0` |
| volume_confirmation | elevated_volume: `relative_volume20 >= 1.0` | sub_average_volume: `relative_volume20 < 1.0` |
| departure_magnitude | large_departure: `zone_departure_atr_multiple >= 1.0` | small_departure: `zone_departure_atr_multiple < 1.0` |
| departure_candle_direction | bullish_departure: `bullish_candle == 1` | bearish_or_doji_departure: `bullish_candle == 0` |

Scale verification (read-only, done before this request): all five feature
columns have 0 NaN, with `vix_percentile_60d` in [0.0167, 1.0],
`zone_is_first_retest` and `bullish_candle` in {0,1}, `relative_volume20`
in [0.0, 19.45], and `zone_departure_atr_multiple` in [0.1715, 34.28].
Labels were never aggregated for this purpose.

## 2. The frozen hypothesis family and its pin

Frozen in `state/campaign_config.json` `multiplicity_policy.families`
verbatim:

- family: `error_analysis`
- primitive: `error_clustering_analysis`
- members_per_experiment: 2
- member_bound: 20
- p_value_method: `week_level_signflip_holm`; familywise alpha: 0.05;
  pooling: `campaign_end_over_complete_family`; Holm step-down; frozen
  flip draw reused (seed 2613983839999682065, M=1000, PCG64, rows-hash
  verified at use time) — never redrawn.
- Feasibility at the proposed m=10: `n_boot` 2000+1 ≥ 20·10 = 200 and
  `n_flips` 1000+1 ≥ 200 — both satisfied.
- Disclosed resolution limit: at M=1000 the minimum representable p is
  1/1001 (same disclosure the frozen config already carries).

The pin mechanism: sha256 over
`autonomous_agent.proposal_layer.schema.canonical_json(record minus 'pin')`.
YES on A2 flips `_status` to `FROZEN_2026_10_25` and this pin becomes
load-bearing.

## 3. Evaluation rules (frozen, derived only from the authorized protocol)

- **Data.** `study_v1_development_event_table` (dataset sha pin
  `232de7db…a4d0`), path
  `study_files/outputs/study_v1/development/event_table.csv`.
- **Purged walk-forward OOF.** Folds exactly [2023, 2024, 2025]; train
  rows require label `exit_date < fold start` (target-maturity purge, the
  frozen study rule); scores are out-of-fold only; rows predating the
  first validation fold train only and are never scored; preprocessing
  fits on the training fold only (frozen study contract).
- **Matched pair.** `arm_a == arm_b == C`; LogisticRegression vs
  LightGBM; identical folds, seeds [42,43,44], and frame for both
  pipelines.
- **Per-cluster AUC delta.** Member statistic is
  `pooled_roc_auc_delta` = AUC(score_b) − AUC(score_a) within the cluster
  member frame (OOF rows only), with a moving-block bootstrap CI
  (block_weeks=4, n_boot=2000, seed 42) for uncertainty, plus week-level
  sign-flip linear-form persistence so the campaign-end procedure derives
  p-values from the persisted record with the frozen flip draw.
- **Minimum samples.** Floors `min_rows = 50` and `min_events = 5`.
  Undersized or underpowered clusters are INCONCLUSIVE — never a pass,
  never a refutation. Degenerate clusters are recorded UNAVAILABLE with
  reason and counted toward m at p=1.0 per C-2 Option A (strictens Holm,
  never loosens).
- **Exclusions (all frozen in the record).** The sealed holdout /
  prospective set is never opened, generated, or cited (uses stay 0);
  pre-first-fold rows are train-only; no cross-campaign pooling beyond
  this family's members adjudicated in this resumed C5 execution; no
  outcome-informed redefinition if a cluster turns out degenerate; the
  duplicate/already-asked layer stays global and permanent; no trading,
  cost, or profitability metrics (hold1_ret is used solely for labels per
  the frozen study target; no backtest output).
- **Champion rule.** V2.0.74 stays the standing champion; these are
  diagnostics, not promotions, and champion_regression is never triggered
  by a diagnostic run.

## 4. Decisions the owner must record (verbatim from the record's
`requires_explicit_owner_approval` and `countersign_block`)

- **A1_resume**: resuming the STOPPED loop at all. PORTFOLIO_COMPLETE was
  a predeclared clean stop; running further executions is a protocol
  action the owner must record YES/NO on.
- **A2_record**: this predeclaration record itself, including the five
  axes and both members of each split, becomes binding only when the
  owner signs the countersign block and the state flips to
  `FROZEN_2026_10_25`.
- **A3_activation**: enabling execution. `error_clustering_analysis` is
  currently declared executable=False at harness < 1.3.0; enabling
  execution requires flipping executable=True and adding the reviewed
  harness 1.3.0 collector plus the 1.3.0 config-selector gate. Owner
  approves this code change at signature time; until then the compiler
  refuses the primitive (fail-closed).
- **A4_ledger_rows**: five new experiment rows in the proposal ledger
  under the resumed campaign id (the ledger is append-only; the owner
  authorizes new rows).

Each decision is recorded as YES / NO / DEFER in the countersign block.
DEFER means the revival does not start.

What this request does **not** require: no byte change to the frozen
campaign_config.json (protocol_fingerprint untouched); no change to
duplicate policy, outcome-blindness policy, holdout policy, or stop
conditions; no multiplicity machinery change (the family table wiring is
already in place); no champion artifact, version directory, or
CHAMPION.json change.

## 5. Authorization coverage already in place (owned by existing signed
records, not by this packet)

- `state/campaign_config.json` `authorization_scope` already covers:
  `add_primitives`, `modify_regime_parameters`, comparisons include
  `error_cluster`, measurements include `pooled_oof_auc`, `brier_score`,
  `ece`, `error_cluster_stats`, model families LogisticRegression and
  LightGBM, and read-only operations on the events table and frozen
  OHLCV.
- `B1` signed protocol scope already freezes the `error_analysis` family
  (error_clustering_analysis, members_per_experiment=2, member_bound=20)
  verbatim in the config multiplicity_policy.
- The frozen multiplicity policy's method, alpha, flip draw, feasibility
  rule, and campaign-end pooling are reused unchanged.
- Campaign-end consumption machinery (`stat_validation_h10/family_records.py`)
  already imports the multiplicity family table including `error_analysis`,
  so no new statistics are invented.
- Champion integrity policy is carried forward unchanged; V2.0.74 remains
  the baseline.

## 6. What I commit to after authorization (and only then)

- Execute **only** the predeclared budget: at most 5 error-clustering
  experiments under the owner-provided ceiling of 10, always preserving
  V2.0.74 as the baseline.
- Report actual measured results — per-cluster AUC deltas with moving-block
  bootstrap CIs (block_weeks=4, n_boot=2000, seed 42) — together with the
  campaign-end Holm-adjusted outcomes from the frozen multiplicity
  machinery, with no post-hoc adjustment of any choice made here.
- Report honestly whichever clusters are INCONCLUSIVE or UNAVAILABLE
  rather than substituting definitions.
- Never open holdout or prospective data; never deploy to production;
  never claim profitability. The objective is only to determine whether
  error clustering reveals a reproducible weakness that can guide a real
  model improvement.

## 7. Sign

In the record file, fill `countersign_block`:
`authorized_by`, `authorized_at`, and one of YES / NO / DEFER for each of
`A1_resume`, `A2_record`, `A3_activation`, `A4_ledger_rows`. The agent acts
as transcriber only; nothing in this packet is itself a signature.

If all four are YES, the immediate next step is: flip `_status` to
`FROZEN_2026_10_25`, re-pin, re-run the declaration tests, and only then
resume with 5 error-clustering experiments inside the 10-experiment
ceiling. If NO or DEFER on any item, Campaign 5 remains stopped and this
packet is kept as the unexecuted record of that.
