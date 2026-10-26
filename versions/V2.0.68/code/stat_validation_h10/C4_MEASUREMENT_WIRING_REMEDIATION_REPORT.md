# C4 Measurement-Wiring Remediation Report — 2026-10-16

**Scope:** isolated engineering work and testing only. No campaign was run, no
experiment was executed against persistent state, no historical artifact was
modified, the sealed holdout was never opened, and launch authorization
remains outstanding (§10).

---

## 1. Root cause and evidence

**Root cause.** The single production experiment entry point
(`python -m autonomous_agent.experiments.run_experiment`, installed verbatim
into every candidate workspace by `spec_recipes.EXPERIMENT_ENTRYPOINT`) calls
`recipe_harness.run_from_config`. That function executed the reviewed v1.0.0
pooled evaluation path *unconditionally*. The v1.1.0 compiler renders configs
carrying `harness_version: "1.1.0"` and `primitive_id`, and
`validate_experiment_config` accepts those keys — but `run_from_config` never
branched on them, so a family-feeding experiment persisted pooled metrics
only. The v1.1.0 per-cell / per-rung evaluators existed
(`recipe_harness.evaluate_regime_cells` / `evaluate_horizon_rungs` /
`evaluate_purge_rungs` / `evaluate_complexity_reduction`) and were exercised
by unit tests, but no production code path ever called them; the frozen
implementation plan's "thin adapter that would collect real measurements"
was never written.

**Evidence.**

* Owner decision record
  (`MAIN AUDITS AND REFLECTIONS/C4_MEASUREMENT_WIRING_FINDING_OWNER_DECISION_RECORD_2026_10_16.md`)
  and the final archive README (`CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16/README_FINAL.md`
  lines 112–113) record the same finding.
* The campaign-end multiplicity record
  (`autonomous_agent/state/campaign_end_multiplicity.jsonl`, sha256
  `75477043…`) contains 24 family members — 8 regime, 12 horizon, 4
  complexity — all `UNAVAILABLE`, `raw_delta: null`, `unadjusted_p: null`:
  no per-member measurement existed in any `evaluation.json`, ledger row, or
  memory file, so the frozen C-2 Option A rule (unavailable members count
  toward m at p = 1.0) applied to every member and the campaign produced
  zero formal refutations by construction.
* Direct code trace (this remediation): `run_from_config` had exactly one
  evaluation call (`_run_pooled`), and the evaluators' only callers were
  `test_v110_primitives.py`.

Campaign 4 stays closed: this remediation changes no historical record and
reconstructs no missing historical measurement.

## 2. Production data-flow changes

Three links, all verified end-to-end (§4):

1. **Execution → persistence.** `run_from_config` now branches on
   `harness_version == "1.1.0"`. After the *unchanged* pooled evaluation, the
   declared family primitive's collector builds member frames from the same
   purged walk-forward run:
   * `regime_split_analysis` — OOF rows sliced by the frozen
     `spy_above_sma200` column into the two frozen cells;
   * `target_horizon_robustness` — labels rebuilt per rung (1/2/3 sessions,
     same +2 % inclusive threshold) from the frozen OHLCV cache, exit dates
     recomputed, unmatured rows dropped, maturity purge re-verified by full
     refit on identical chronological folds; the 1-session rung must
     reproduce the frozen table's `hold1_ret` / `label` / `exit_date`
     exactly or the run fails (anchor);
   * `purge_sensitivity_probe` — refits with the training maturity purge
     widened by +0/+5/+10 market sessions on the frozen SPY session
     calendar; the +0 rung is the frozen fold rule itself;
   * `complexity_reduction_check` — the primary estimator-comparison frame
     (the compiler renders `arm_a == arm_b` for this primitive; the
     collector refuses any other shape).
   Every member gets `point`/`ci_lower`/`ci_upper` (same moving-block
   bootstrap machinery and seed as the pooled path, same 95 % level),
   `n_rows`/`n_events`, the frozen sample floors' verdict via the IUT
   evaluator, provenance flags, and **the exact week-level sign-flip linear
   form** `g` of the frozen reference (`simh10.TrialStats`): week-bucketed
   comparison sums zero-padded onto the pooled week index, with the
   all-`+1` identity `Σg = 2·n⁺·n⁻·δ̂` enforced fail-closed at execution
   time. The block is persisted under `results.family_measurements` in
   `outputs/evaluation.json` (and durably copied by the adapter into
   `result.json`). A frame too degenerate to measure (no rows, no events,
   single label class) is recorded `unavailable` with its reason; any other
   anomaly (missing frozen column, unseen week, bootstrap machinery error)
   **fails the run**: non-zero exit, no evaluation output written. There is
   no pooled-only fallback for a v1.1.0 family config. The v1.0.0 path is
   byte-for-byte the reviewed behavior.

2. **Correct association.** Every member record carries the frozen
   family/primitive/member identity (member keys enumerated from
   `three_valued.ladder_for`, never derived at runtime), the experiment
   identity (hypothesis id, arms, estimators, seeds, n_boot, folds,
   `config_sha256`), the pooled week-index alignment (`W`, W-SUN convention,
   week list), measurement provenance (bootstrap block weeks, seed, floors),
   and the provisional-only firewall fields (`refutation_signal: "unadjusted"`,
   `formal_refutation: false`, provisional label). The block's member set is
   checked against the frozen ladder at execution time — a partial set fails
   the run.

3. **Persistence → multiplicity.** The new consumption module
   `stat_validation_h10/family_records.py` reads the persisted block (from
   `evaluation.json`, the durable `result.json`'s `metrics` copy, or a parsed
   mapping), validates it fail-closed against the frozen family table and
   ladders (schema, family↔primitive coherence, complete member set, week
   alignment with the campaign's recorded flip draw, linear-form identity,
   firewall), maps `unavailable` members to the frozen C-2 Option A
   treatment, computes each available member's unadjusted p-value by the
   owner-approved `week_level_signflip_holm` method from the persisted `g`
   with the campaign's own recorded flip draw, and builds the
   `multiplicity.FamilyMember` inputs for
   `multiplicity.campaign_end_record` (Holm step-down, unadjusted retention).
   Nothing about family membership, estimands, or statistical assumptions was
   changed.

**Import-boundary architecture (frozen constraint honored).** The frozen
T12 / freeze-integrity tests forbid the execution side from importing the
multiplicity machinery (`test_only_the_loop_imports_the_multiplicity_machinery`
allowlist: `continuous_loop.py`, `test_multiplicity.py`, `test_signflip_port.py`;
T12: `recipe_harness.py` may not import or even mention the proposal layer).
Therefore the wiring splits along that boundary: the execution side stamps
records using shared mirrors in `three_valued.py`
(`FAMILY_MEMBER_BOUNDS`, `REFUTATION_SIGNAL_VALUE`, `LABEL_NO_SIGNAL`,
`LABEL_PROVISIONAL_REFUTATION` — byte-equality with the campaign-side
authority asserted by drift tests), and the consumption side lives on the
stat-validation side beside the multiplicity machinery, exactly where the
campaign-end finalization step already operates
(`campaign_end_2026_10_16/build_multiplicity_record.py`). The firewall is
enforced where the block is adjudicated (`continuous_loop._adjudicate`
already runs `assert_firewall_intact` over results, which include the block)
and re-checked by `family_records.load_member_block` before any consumption.

## 3. Files changed and why

| File | Change |
|---|---|
| `autonomous_agent/recipe_harness.py` | v1.1.0 branch in `run_from_config`; `_run_pooled` additionally returns the OOF frame/week-index context (metrics identical); new wiring section: `week_level_g` (frozen linear form), `_week_positions`, `_family_member_record`, `_oof_scores`, `_rebuild_horizon_frame`, the four family collectors, `_collect_family_measurements`, `FAMILY_MEASUREMENTS_SCHEMA`, `CAMPAIGN_END_P_VALUE_METHOD`. v1.0.0 path unchanged. |
| `autonomous_agent/three_valued.py` | Shared-model mirrors of the frozen campaign-end vocabulary (family member bounds, firewall tokens) so the execution side can stamp records without importing the generation side. |
| `stat_validation_h10/family_records.py` | **New.** Third-link consumption module + thin facade over the frozen API (family table, statuses, firewall, `campaign_end_record`, flip-draw loaders). Lives on the stat-validation side per the frozen import boundary. |
| `autonomous_agent/test_v110_wiring_e2e.py` | **New.** 21-test acceptance suite (§4). |

No other file was modified. (`git status` reports `autonomous_agent/` and
`stat_validation_h10/` as untracked wholesale in this checkout, so file-level
immutability of historical artifacts is evidenced by the sha256 guards in
§8, not by git diff.)

## 4. End-to-end test design and results

All tests are new (written for this remediation). Command:
`py -3 -X utf8 -m unittest autonomous_agent.test_v110_wiring_e2e -v`
→ **exit 0, 21 tests, OK (203.5 s)**.

**Fixture design (isolation contract).** Each E2E execution runs
`python -m autonomous_agent.experiments.run_experiment` **as a subprocess
with a scrubbed environment** — the exact production command — inside a
temporary root (`tempfile.mkdtemp`, removed by cleanup) containing:
a synthetic frozen-study module mirroring the reviewed contracts
(purged chronological `make_folds`, deterministic `fit_pipeline` /
`predict_pipeline`, the *exact* moving-block bootstrap, `read_ohlcv`), a
synthetic OHLCV cache (SPY + AAA/BBB/CCC, 254 weekly sessions 2021–2025,
open chains constructed so the recorded `hold1_ret`/`label` columns are
reproducible from opens), a 756-row event table (444 OOF rows, 148 pooled
weeks; regime cells 90/354 rows with 40/157 events — well above the frozen
floors of 50 rows / 5 events), the real `spec_recipes` shim text, and
byte-identical copies of the harness modules. Configs are rendered by the
**real production compiler** (`compiler._render_v110_config`) from the real
primitive library, with `n_boot = 1000` (H-10b floor). The module-level
guards hash the campaign-end multiplicity record, the final archive
manifest, the owner decision, and `launch_gates.json` before and after the
suite and assert bit-identity; each fixture workspace is asserted to contain
no holdout (`prospective`) directory.

**What each test proves:**

* `test_regime_family_execution_to_persistence` — link 1+2: measurements
  produced by the real entry point (not by a direct evaluator call), both
  frozen cells persisted with correct family/primitive/member identity,
  experiment identity (`config_sha256`, arms, seeds), week alignment,
  sign-flip payloads with `n_pos == n_events`,
  `n_pos+n_neg == n_rows`, and the `Σg = 2·n⁺·n⁻·δ̂` identity inside the
  persisted record; IUT result structure; pooled metrics still complete.
* `test_horizon_family_refits_and_flags` — 3 rungs persisted with
  `labels_rebuilt`/`maturity_purge_reverified`; the 1-session rung's point
  and `delta_hat` equal the pooled primary delta (exact anchor); rungs 2/3
  differ from rung 1 (per-rung rebuilds and refits, never pooled reuse).
* `test_purge_family_refits_and_anchors` — 3 purge rungs; +0 rung equals the
  pooled primary (anchor); stricter rungs change the measured `delta_hat`
  (refits verified); train-rule flags name the frozen rule vs the SPY
  session-calendar widening.
* `test_complexity_family_single_primary_rung` — single `primary` member,
  point equals the pooled primary delta, related-reanalysis flags set,
  `independent_confirmation: false`.
* `test_campaign_end_record_from_persisted_records` — link 3: the persisted
  block flows through `family_records` into `campaign_end_record`; every
  unadjusted p is independently re-derived (pure-Python enumeration of the
  recorded flip rows, no numpy) and matches to 1e-12; the record's feasibility
  and method stamp are checked.
* `test_fail_closed_when_frozen_column_missing` — dropping the frozen
  `spy_above_sma200` column makes the v1.1.0 run exit non-zero with **no**
  `evaluation.json` written: never pooled-only-while-claiming-family.
* `test_degenerate_cell_recorded_unavailable_and_inconclusive` — a degenerate
  below-SMA cell (2 rows, one class) is persisted `unavailable` with reason;
  the IUT is INCONCLUSIVE; consumption maps it to the frozen C-2 Option A
  (`UNAVAILABLE`, never refuted) while the healthy cell stays `AVAILABLE`.

## 5. Negative-test results (missing / malformed / mismatched)

`FamilyRecordNegativeTests` (9 tests, all pass): missing block; unknown
schema; non-applicable block; incomplete member set (frozen ladder
disagrees); family↔primitive mismatch; week-index disagreement across
consumed blocks; broken linear-form identity (perturbed `g`); `g` length ≠
recorded W; duplicate member ids; and a bare formal-refutation label inside
a consumed block → `FirewallViolation`. Plus the two E2E negatives above
(missing frozen column → hard run failure; degenerate cell → recorded
unavailable, never a pass, never a silent skip). Every path fails closed or
produces an explicit recorded-unavailable row; none silently degrades.

## 6. Independently checked multiplicity examples

1. **Linear-form exactness** (`LinearFormEquivalenceTests`): on a synthetic
   240-row / 40-week frame, 60 random whole-week arm-swap vectors — the
   production linear form `(S @ g)/(2·n⁺·n⁻)` vs brute-force AUC
   recomputation under each swap: max absolute error < 1e-9; `Σg/(2·n⁺·n⁻)`
   equals `δ̂` and the standard AUC delta.
2. **Engineered known cases** (`HandVerifiedMultiplicityTests`): four
   members engineered over a recorded W=8 flip draw — g all −1 (δ̂ = −0.04,
   the smallest attainable delta), g = 0, g all +1, and one unavailable
   member. P-values re-derived by an independent pure-Python counter: the
   strong member's p ≈ 0.002–0.013 (grid `(1+k)/1001`), the zero and positive
   members p = 1.0, the unavailable member p = 1.0 by C-2 Option A (stored
   `unadjusted_p: null`, counted toward m). Independent Holm step-down
   (test-local implementation with the same prefix-max/cap/stop rules)
   matches `campaign_end_record`'s `adjusted_p` to 9 decimals: strong member
   REFUTED (adjusted p = m·p ≤ α), others INCONCLUSIVE, unavailable member
   never formally refuted; unadjusted and adjusted values retained side by
   side (H-6).
3. **E2E persisted p-values**: every p in §4's campaign-end test is
   re-derived from the persisted `g` and the campaign's hash-verified flip
   draw by the independent counter — 12-decimal agreement.

## 7. Full test suite and integrity checks (exact commands and exit codes)

All runs below were executed fresh during this remediation (no historical
results reused):

| Command | Exit | Result |
|---|---|---|
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_wiring_e2e` | 0 | Ran 21 tests — OK (203.5 s) — **new suite** |
| `py -3 -X utf8 -m unittest autonomous_agent.test_recipe_harness` | 0 | Ran 11 tests — OK |
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_primitives` | 0 | Ran 32 tests — OK |
| `py -3 -X utf8 -m unittest autonomous_agent.test_signflip_port` | 0 | Ran 16 tests — OK |
| `py -3 -X utf8 -m unittest autonomous_agent.test_multiplicity` | 0 | Ran 42 tests — OK |
| `py -3 -X utf8 -m unittest autonomous_agent.test_freeze_integrity` | 0 | Ran 23 tests — OK |
| `py -3 -X utf8 -m unittest discover -p "test_*.py" -t .` | 0 | **Ran 411 tests — OK (290.5 s)** |
| `py -3 -X utf8 autonomous_agent/launch_readiness_check.py` | 0 | `{'PASS': 31, 'RECORDED': 7}` → READY (machine checks; "this tool approves nothing") — unchanged pre-existing state |
| C4 final-archive self-verification (re-hashed all 12 entries of `SHA256SUMS.txt`) | 0 | 12/12 match, 0 bad |

Notes on the discovery run: an intermediate run (408 tests) surfaced two
failures caused by this remediation — `test_only_the_loop_imports_the
_multiplicity_machinery` and `test_t12_import_boundaries` — because the
first placement of the wiring/consumption imports violated the frozen
import boundary. The wiring was restructured (shared mirrors in
`three_valued.py`, consumption moved to the stat-validation side) rather
than the frozen tests being touched; the final 411-test run is fully green.
Three additional drift/boundary guards were added to the new suite as a
result.

## 8. Historical-state and holdout confirmation

* Append-only multiplicity record
  `autonomous_agent/state/campaign_end_multiplicity.jsonl` — sha256
  `7547704337738e829ce71bddd524b7458cdc62f38ee3642443597eedd5abe9d3`,
  **UNCHANGED** (before, during, and after every run; also enforced by the
  suite's setUp/tearDown hash guards).
* Campaign 4 final archive — all 12 entries of `SHA256SUMS.txt` re-verified,
  **0 mismatches**.
* Owner decision record — sha256
  `7d837caa9123be50ca0407d167b6c69aed29dc90d86f59968c693dcfc0d54130`,
  **UNCHANGED**.
* `stat_validation_h10/launch_gates.json` — sha256
  `dfed21cda460f898f9958d0276db83b110a7a618b0e43591d008ff87af2adeea`,
  **UNCHANGED**; no H-10 signature, approval, gate change, or freeze
  authorization was made.
* Frozen configurations and pinned artifacts — untouched (only read).
* Holdout: the sealed prospective directory is absent from this checkout
  (owner-controlled); the suite's module guards hash its absence before and
  after, every fixture workspace is asserted to contain no `prospective`
  directory, and no test, script, or execution in this remediation ever
  constructed or opened a holdout path. **Holdout access: zero.**
* No campaign or experiment ran against persistent state: every execution
  was a subprocess in a temporary directory that is deleted by test
  cleanup; nothing wrote under `autonomous_agent/state/` (the hash guards
  prove it); no ledger transition, promotion, adjudication, or freeze
  record was created or altered.

## 9. Remaining ambiguities, defects, and limitations

* **Regime split column** is hard-coded to the frozen `spy_above_sma200`
  column (the frozen cell names are `above_sma200`/`below_sma200`). Any
  other regime definition is a frozen-design amendment, not a code knob;
  the collector fails closed if the column is absent.
* **Complexity family** assumes the compiler's `arm_a == arm_b` matched-arm
  contract; an arm-pair config for this primitive raises rather than
  silently changing the estimand.
* **Purge session calendar** comes from the frozen SPY OHLCV cache; a cache
  without SPY fails the run (fail-closed), it never falls back to another
  calendar.
* **Degenerate-week member frames** (rows exist but too few calendar weeks
  for the frozen block bootstrap) fail the run rather than being recorded
  unavailable; only row/event/class degeneracy maps to `unavailable`. This
  is deliberate fail-closed behavior and is documented in the wiring
  section comment.
* **The synthetic study module mirrors the frozen study's contracts but is
  not the frozen study itself**; wiring correctness is proven against the
  contract, and the real module's block-bootstrap behavior is covered
  separately by `test_recipe_harness` against the real module (11/11 OK).
  The first real-data execution of the wiring remains an owner-gated event.
* **`n_boot` for member CIs** reuses the experiment's configured value
  (≥ 1000 enforced); the member bootstrap reuses the experiment seed, so a
  member CI is reproducible from the persisted record alone.
* The wiring has never executed with real market data; all measurements in
  this report come from synthetic fixtures and are not evidence about any
  trading hypothesis.

## 10. Explicit statements

* **No new campaign was launched, scheduled, or executed.** Campaign 4
  remains closed and unchanged; neither interrupted execution was resumed.
* **Launch authorization remains outstanding**: the H-10 decision record
  remains unsigned, no statistical approval was granted, no launch gate was
  altered, and no freeze was authorized. This remediation passes tests; it
  approves nothing. Owner review is the next step.
