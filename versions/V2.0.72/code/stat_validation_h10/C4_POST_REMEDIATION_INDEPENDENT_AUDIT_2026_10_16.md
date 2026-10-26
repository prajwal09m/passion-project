# C4 Post-Remediation Independent Audit — 2026-10-16

**Scope.** Independent, read-only audit of the measurement-wiring
remediation reported the same day. No source file was modified by this
audit; no campaign, experiment, freeze, or archive builder was run; the
sealed holdout was not accessed; no approval, signature, or gate was
changed. The only file written by this audit is this report.

Evidence labels used throughout:
**[IR]** independently reproduced by this audit (command + exit code given);
**[SC]** source-code observation (read, not executed);
**[TR]** result reported by an existing test run;
**[SU]** statistical assumption that remains unverified;
**[NC]** conclusion that cannot be drawn from available evidence.

---

## 1. Executive assessment

The remediation is real and materially correct within its tested scope.
The production entry point now dispatches v1.1.0 family configurations to
per-family collectors during ordinary execution, persists per-member
records with the frozen identities and the exact sign-flip linear form,
and the persisted records feed the approved campaign-end procedure through
a fail-closed consumption module. The reviewed v1.0.0 pooled path is
provably unchanged. The frozen import boundary, firewall, and archive
integrity all hold. Every headline claim in the remediation report that I
could test, I tested independently; none failed.

Three things keep this short of full closure:
(a) the third wiring link — campaign-end consumption — exists only in
tests; no production finalization script calls it yet (**F-1**);
(b) several fail-closed code paths exist without negative tests (**F-2**);
(c) the statistical assumptions behind the sign-flip p-values remain
unestablished exactly as the owner's own record documents — the remediation
fixed plumbing, not statistical validity (**F-3**).

**Engineering verdict: REMEDIATION VERIFIED WITHIN TESTED SCOPE.**
**Governance verdict: STATISTICAL REVIEW STILL BLOCKING.**

## 2. Scope, baseline, and evidence actually inspected

**Baseline [IR/SC].** The pre-remediation baseline was established from
the versioned snapshot tree, not from git (the repository tracks only two
public-bundle commits; `autonomous_agent/` and `stat_validation_h10/` are
untracked). `versions/V2.0.61/` (snapshot timestamp 18:09, before the
remediation session) contains `recipe_harness.py` and `three_valued.py`
with **zero** occurrences of `family_measurements` or
`FAMILY_MEMBER_BOUNDS`, and a 671-line `run_from_config` with no v1.1.0
branch. `stat_validation_h10/family_records.py` and
`autonomous_agent/test_v110_wiring_e2e.py` are new files with **no
pre-remediation baseline**; before/after comparison is impossible for them
(other than "did not exist").

**Files inspected.** Current `recipe_harness.py` (1328 lines),
`three_valued.py`, `stat_validation_h10/family_records.py`,
`autonomous_agent/test_v110_wiring_e2e.py` (21 tests);
`proposal_layer/multiplicity.py`, `proposal_layer/signflip.py`,
`proposal_layer/compiler.py`, `proposal_layer/primitives.py`;
`stat_validation_h10/simh10.py`; `study_files/backend/demand_zone_study_v1.py`
(real frozen-study contracts); the retained development event table and
OHLCV cache; `launch_gates.json`; the C4 state record, final archive and
manifest; `H10_DECISION_RECORD_AWAITING_SIGNATURE.md`;
`H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md`; the remediation report.

**Commands actually run by this audit (all read-only or synthetic; exit
codes captured directly, not through pipelines):**

| Command | Exit | Result |
|---|---|---|
| Baseline diffs (V2.0.61 vs current; pooled-core and results/write spans) | 0 | v1.0.0 path identical except one additive ctx block; write relocated |
| Exhaustive 2^10 week-flip check of `week_level_g` vs brute-force AUC | 0 | worst error 2.01e-16; identity 1.7e-13; sklearn agreement 1.1e-16 |
| 300 random families: independent Holm vs `holm_step_down` | 0 | 0 mismatches; monotone, capped, step-down verified |
| 400-rep null calibration of `week_level_g` + `signflip_p_value` | 0 | size 0.0600 (band [0.029, 0.071]) — see §5 |
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_wiring_e2e` | 0 | Ran 21 tests — OK (642 s) |
| `py -3 -X utf8 -m unittest autonomous_agent.test_freeze_integrity` | 0 | Ran 23 tests — OK |
| `py -3 -X utf8 -m unittest ...test_t12_import_boundaries ...test_t13...` | 0 | Ran 2 tests — OK |
| sha256 re-verification: state record, owner decision, launch_gates, 12-entry archive | 0 | all UNCHANGED; archive 12/12, 0 mismatches |
| multiplicity-import needle scan over `autonomous_agent/*.py` + `proposal_layer/*.py` | 0 | exactly {continuous_loop.py, test_multiplicity.py, test_signflip_port.py} |
| `py -3 -X utf8 autonomous_agent/launch_readiness_check.py` | 0 | PASS 31 / RECORDED 7 → READY ("this tool approves nothing") |
| Real event-table inspection (regime column, OOF-window cell sizes) | 0 | 0 nulls, binary; OOF cells 3 746 / 3 752 rows |

The full 411-test discovery run was **not** repeated during the audit:
no source file changed since the remediation run [TR], and the audit's own
reproductions (E2E 21, freeze-integrity 23, T12/T13, independent
calculations) cover the claims under examination. The 411-test result
itself is a **[TR]** item, freshly produced during the remediation session
and not re-executed here.

## 3. Before-and-after change table

| # | Original defect / limitation | Before (V2.0.61) | After (current) | Evidence the behavior changed | Tests / independent checks | Residual risk |
|---|---|---|---|---|---|---|
| 1 | v1.1.0 configs silently ran the pooled path | `run_from_config` (L290 ff.) has no `harness_version` branch | `run_from_config` L320–324: v1.1.0 branch calls `_collect_family_measurements` (L1247 ff.) before any write | [IR] baseline source lacks the branch; [SC] call graph; [TR+IR] E2E subprocess writes `family_measurements` into `evaluation.json` | E2E 21/21 reproduced, exit 0 | Non-family v1.1.0 primitives emit `applicable: false` — correct but untested (F-2) |
| 2 | v1.0.0 path must stay unchanged | 671-line monolith | pooled core **identical line-by-line** except one additive ctx block (`oof_frame`/`week_index`); write relocated from `run_from_config` into `_run_pooled`'s caller; print statement rephrased (same values) | [IR] span diffs: results-block diff = only the relocated write; pooled-core diff = only the additive 14 lines | test_recipe_harness 11/11 [TR+IR rerun in remediation]; anchors tie member points to the pooled value | None identified |
| 3 | Per-member measurements existed only in unit tests | `evaluate_*` callers: tests only | collectors (`_collect_regime` L995, `_collect_horizon` L1083, `_collect_purge` L1122, `_collect_complexity` L1161) invoked from production dispatch | [SC] baseline grep zero production callers → current call graph; [IR] E2E reads member records written by the subprocess, not by a direct evaluator call | E2E family tests + fail-closed test | Fixture-authored study module mirrors real contracts; mitigated by [SC] comparison against real `demand_zone_study_v1.py` (§4) |
| 4 | Persisted identity/association absent | no member records at all | block carries family/primitive/member keys from frozen ladders, experiment identity incl. `config_sha256`, W-SUN week index, provenance flags | [SC]+[IR] E2E asserts each field on the persisted file; 9 negative tests reject mismatched forms | BoundaryAndDrift + negative tests | `config_sha256` self-referential (F-6) |
| 5 | Campaign-end procedure had nothing to consume | all 24 members unavailable by construction | `stat_validation_h10/family_records.py` validates blocks and builds `FamilyMember` inputs with approved-method p-values | [IR] E2E test builds a campaign-end record from the persisted block; p-values re-derived independently | Hand-verified Holm + E2E consumption test | **No production caller yet (F-1)** |
| 6 | (design intent; not reachable before) fail-closed | n/a | collector exceptions occur **before** the evaluation write; consumption refuses incomplete/mismatched blocks | [IR] fail-closed E2E: missing frozen column → exit ≠ 0, no `evaluation.json` | fail-closed + 9 negative tests | Some fail-closed paths untested (F-2) |
| 7 | Import boundary under pressure from new wiring | n/a | execution side uses `three_valued` mirrors; consumption lives on the stat-validation side | [IR] needle scan reproduces the frozen allowlist exactly; T12/T13 OK | freeze-integrity 23/23, T12 [IR] | Mirrors duplicate constants; drift tests exist [TR+SC] |

## 4. Family-collector implementation findings

### A. Regime
[SC] `_collect_regime` slices the pooled OOF frame by the frozen
`spy_above_sma200` column, enumerated cells strictly from
`tv.ladder_for`, fails closed if the column is missing, and marks empty /
single-class / all-one-class cells `unavailable` with reasons. Cell
membership is positional slicing of the same OOF rows that produced the
pooled scores — no refit, correct by construction for a row-subset
estimand. [IR] On the **real** retained table the column has 0 nulls,
values {0,1}, and OOF-window cells of 3 746 rows / 932 events and
37 469 rows / 5 860 events — both far above the frozen floors (50 rows /
5 events), so the below-cell will not be spuriously unavailable on real
data. [SC] The fixture's regime split (trailing-median analogue) differs
from the real SMA-200 definition, but the wiring treats the column as
opaque input, so the fixture tests slicing mechanics, not the definition.

### B. Horizon
[SC] Labels rebuilt per rung from the frozen OHLCV opens
(`hold = open[t+h]/open[t] − 1 ≥ 0.02`, inclusive, matching the frozen
`build_hold1_targets` semantics); exit dates recomputed; unmatured rows
dropped; the 1-session rung **refuses to continue** unless rebuilt
`hold1_ret`/`label`/`exit_date` reproduce the frozen table exactly
(anchor). Rung ≥ 2 refits both arms via `_oof_scores` on the rebuilt
frame — train masks recompute from the new exit dates, so the maturity
purge genuinely tightens per rung. The frozen evaluator additionally
refuses any rung not declaring `labels_rebuilt`/`maturity_purge_reverified`
(`evaluate_horizon_rungs` L597 ff.), and the wiring passes those flags from
the member record. [IR] E2E confirms rung 1's point and `delta_hat` equal
the pooled delta and rungs 2/3 differ (not pooled reuse).

### C. Purge
[SC] `+0` rung: `_oof_scores` replicates `make_folds` exactly
(`train = dates < start & exits < start`) — the +0 anchor holds by
construction. `+5/+10`: cutoff = the 5th/10th-to-last **SPY session
strictly before** fold start (from the frozen OHLCV cache); train rows
require `exit_date < cutoff` — at least N sessions before start, matching
the persisted `train_rule` flag text; validation rows unchanged, so the
comparison isolates the training exclusion. No leakage pathway identified:
folds are chronological, exits must precede train cutoffs, and
preprocessing (imputer/scaler) is fitted on train rows only ([SC] real
study `fit_pipeline` L767–787). [IR] E2E confirms +0 equals the pooled
delta and stricter rungs change `delta_hat`. **Limitation:** no test uses a
calendar without SPY; the fail-closed path is [SC]-only.

### D. Complexity
[SC] `_collect_complexity` raises unless `arm_a == arm_b` (the compiler's
matched-arm contract for this primitive) and uses the pooled OOF frame
itself as the single `primary` member; flags stamp the related-reanalysis
disclosure (`independent_confirmation: false`). An arm-pair config would
be refused rather than silently redefined. [IR] E2E confirms the single
member's point equals the pooled primary delta. This member is a
**restatement** of the pooled comparison, not an independent measurement —
consistent with the frozen design (count-once rule) but worth stating
plainly: the complexity family's p-value tests the same estimand the
pooled gate already evaluated.

### Test independence caveat
The synthetic study module was authored by the same agent as the harness.
I mitigated this by [SC] comparing its contracts against the real frozen
study: `block_bootstrap_delta` (frame, score_a, score_b, \*, n_boot,
block_weeks, seed; percentile CI; `AUC(a) − AUC(b)`), `make_folds`,
`fit_pipeline`/`predict_pipeline` signatures, and the pooled call order
(`block_bootstrap_delta(boot_frame, "score_b", "score_a")` so the pooled
delta is B−A and the member anchor direction matches) are identical.
Residual [NC]: rung-2/3 and purge-refit behaviors have only fixture-based
evidence; only a real-data integration test can discriminate a shared
misunderstanding. (Finding F-8.)

## 5. Statistical-methodology assessment

### A. Effect estimates
[SC+IR] The primary delta is pooled OOF `AUC(candidate) − AUC(reference)`
(real study line: "Pooled out-of-fold AUC difference of arm/estimator B
versus A"); member points are the same quantity restricted to the member's
rows (bootstrap) and re-derived exactly from pair counts
(`week_level_g`: ΣC/P). OOF rows, labels, and both score columns are
co-indexed on the same frame; `n_pos`/`n_neg` equal `n_events`/
`n_rows − n_events` and are asserted at consumption.
[SC] Reusing the same OOF data across family members creates dependence
**between** members; Holm does not require inter-member independence, so
this is handled correctly at the multiplicity layer — the design addresses
it, and per-member CIs are provisional-only (H-1) so they carry no
familywise claim.

### B. Block bootstrap and CIs
[SC] The moving-block bootstrap is the frozen study's own function (4-week
blocks, wrap-around week draw, all rows of drawn weeks, percentile 2.5/97.5,
resamples with one label class discarded). Members pass the identical
machinery on their own frames with the configured `n_boot` (≥ 1000
enforced) and `seeds[0]`; `point` is the member's AUC delta; `ci_lower` is
the percentile lower bound. Interpretation caveats that hold for members
too: the percentile bootstrap CI is not studentized, week blocks of 4 are
shorter than the whole-week test unit (the documented SIM-3 structural
mismatch), and the discarded-single-class resamples slightly thin the
lower tail. None of this is new — it is the frozen pooled procedure
applied to subgroups — and the three-valued IUT treats the CI as a gate,
never as a standalone inferential claim.

### C. Week-level sign-flip inference
[IR] Exhaustive enumeration of all 2^10 week flips on a synthetic frame:
`(S @ g)/(2·n⁺·n⁻)` matches brute-force AUC recomputation to 2.01e-16;
`Σg = 2·n⁺·n⁻·δ̂` to 1.7e-13; `δ̂` matches sklearn to 1.1e-16. The port
(`signflip_p_value`) matches the reference (`simh10.py:287/452`): lower
tail, `≤` ties, `(1 + #{flips ≤ δ̂})/(M+1)`, fail-closed provenance
(stage + rows-hash). Empty weeks: `g` has length W over the pooled week
index; empty weeks contribute 0 to `g` and columns of ±1 in S that cancel —
verified [IR] inside the exhaustive check (weeks with no rows included in
W). Flip draw vs member week index: consumption requires
`payload.W == block.week_index.W == draw.W` and re-hashes the regenerated
draw. Minimum attainable p = 1/1001 ≈ 0.001 < first Holm threshold
0.05/24 ≈ 0.00208 — refutation is attainable for the largest declared
family. [IR] Null calibration of the complete member path (400 reps,
labels independent of scores, W=30 with naturally empty weeks): size at
α=0.05 is **0.0600**, 95% band for 400 reps around a true 0.05 being
[0.029, 0.071] — not distinguishable from nominal at this replication
count, and numerically consistent with the owner record's disclosed
equal-AUC asymmetry sizes (0.055/0.060, CP95 upper 0.071/0.077).

**Unresolved assumptions [SU] — unchanged by the remediation:**
* Week-level exchangeability / sign symmetry of the two arms under H0 is
  unestablished (owner record §0/§1; my calibration neither validates nor
  refutes exact size).
* Independence (or weak dependence) of week clusters — the marginal
  p-values must be super-uniform for Holm to control FWER; temporal
  autocorrelation across weeks is unmeasured.
* The MC-resolution/borderline-member behavior at large m is documented
  (biased toward non-rejection) and unmeasured at the Holm threshold under
  asymmetry.
* **[NC]** This audit cannot certify the method as statistically valid for
  this dataset; numerical exactness of the implementation is not evidence
  of inferential validity. Correct implementation of a test ≠ valid test.

### D. Holm multiplicity
[IR] 300 random families (m 1–12, ties, 0/1 extremes) against a
textbook step-down written independently: 0 mismatches in adjusted values
or rejection flags; monotone prefix-max, cap at 1.0, and stop-at-first-
non-rejection verified on a worked example ([0.006, 0.02, 0.12, 0.12,
0.8, 1.0] with rejects [T,T,F,F,F,F]). [SC] Frozen family membership comes
from the frozen table; unavailable members enter at effective p = 1.0
(C-2 Option A), are stored with `unadjusted_p: null`, and can never be
formally refuted; feasibility requires M+1 ≥ 20·m on both counts.
`unavailable` is never treated as empirical evidence — it is a recorded
absence counted conservatively.

### E. Leakage and robustness
[SC] Reviewed: chronological folds with train-exit-before-start maturity
purge; preprocessing fitted on train rows only; horizon rebuilds use only
frozen opens (derived data) and re-verify the 1-session anchor; purge
rungs widen only the training exclusion; regime slicing is post-OOF. No
leakage pathway identified in the wiring. Post-selection risk: the
primitive set, ladders, families, and margins were frozen before results
(freeze records, byte-verified). Undocumented analysis choices: none found
beyond those already disclosed (H-1 margin provisional; CI/flip-draw
structural mismatch).

## 6. Persistence and fail-closed assessment

Data flow verified end-to-end [IR]: subprocess production run →
`outputs/evaluation.json` `results.family_measurements` → `fr.load_member_block`
(accepts `evaluation.json`, the durable `metrics` nesting, or a mapping) →
validated → `FamilyMember` list → `campaign_end_record`.

* Each frozen member appears exactly once; duplicates, missing members,
  unexpected keys, family/primitive mismatch, week-index mismatch, broken
  identity, wrong `g` length, and bare formal labels are all refused
  (9 negative tests, reproduced in remediation run and by inspection).
* Week index vs flip draw enforced at consumption; firewall re-checked at
  consumption and at adjudication (`continuous_loop._adjudicate` scans
  results, which include the block).
* Missing measurements cannot masquerade as complete: incomplete member
  sets raise at execution *and* consumption; the fail-closed E2E proved no
  `evaluation.json` is written when the collector raises; exit code 0 on
  the entry point implies the block was written (collector runs before the
  write, returns 0 only after).
* Gaps: the **durable `result.json` path** is exercised only in remediation
  unit context, not through the real adapter in an E2E run; the
  execution-side H-10b floor raise and the member-vs-block identity check
  have no negative test (F-2); `config_sha256` is not cross-checked against
  the adapter's spec hash (F-6).

## 7. Test-quality and verification assessment

[IR] I reproduced the 21-test E2E module (exit 0), freeze-integrity (23,
exit 0), and T12/T13 (2, exit 0). The E2E tests do use the actual
production entry point via `python -m autonomous_agent.experiments.run_experiment`
in a scrubbed subprocess with the real `spec_recipes` shim and
compiler-rendered configs; member records are read from the file the
subprocess wrote — measurements are not produced by direct evaluator
calls. The 12-entry archive manifest re-verified 12/12; state record,
owner decision, and launch-gates hashes match the recorded values.

**Assertions that could pass while the implementation is wrong** — the
principal one: E2E "anchors" compare member points against the pooled
delta, both computed by the same harness; a shared error would pass. This
is mitigated (not eliminated) by the exhaustive/brute-force tie-ins of
`week_level_g` to sklearn's AUC and by the byte-identity of the pooled
path to the reviewed baseline. **Missing negative cases** (F-2): member
identity mismatch; execution-side n_boot floor raise; non-family v1.1.0
primitive (`applicable: false`); member frame with < block_weeks weeks;
durable result.json through the real adapter; SPY-less purge calendar.
**Fixture fidelity:** verified by source comparison against the real study
(§4), but rung-2/3, purge refit, and the real bootstrap on real data
remain fixture-only evidence — the exact gap a real-data integration test
must close. All 21 tests' claims in the remediation report are supported
by what the tests actually assert; I found no overclaim.

## 8. Artifact-integrity and governance findings

[IR] `campaign_end_multiplicity.jsonl` sha256 `75477043…`, owner decision
`7d837caa…`, `launch_gates.json` `dfed21cd…` — all UNCHANGED; final archive
12/12 entries match their manifest. Campaign 4's historical state
(24 unavailable members, 0 formal refutations) is preserved; nothing in
the remediation reconstructs or reclassifies it. Holdout: the prospective
directory is absent from this checkout; every fixture workspace is
asserted holdout-free; no audit command touched any holdout path.
**Holdout access: zero [IR].**

**Readiness vs H-10 [SC+IR].** `launch_readiness_check.py` exits 0 with
"READY (machine checks pass and all human gates recorded)" because every
gate in `launch_gates.json` is *recorded* — including the
2026-10-14 owner written-directive records (H10_D2_C3_OWNER_DECISION
_RECORD_2026_10_14.md) that adopted method (b) and ratified C-3, and the
freeze/launch re-affirmations. Two important reconciliation points:

* **F-4 (Medium).** `H10_DECISION_RECORD_AWAITING_SIGNATURE.md` still
  states "H-10 remains UNRESOLVED… Campaign 4 remains BLOCKED. C-3 is
  PENDING", superseded in fact by the 2026-10-14 record but **not
  annotated as superseded**. Two on-disk records give conflicting pictures
  of H-10's status; any reader or tool keying on the older file
  mis-derives the project state. Resolution belongs to the owner (a
  supersession annotation), not to this audit.
* **F-5 (Medium).** No automated launch path keys on the READY verdict:
  `continuous_loop`, `core`, and `experiment_adapter` contain no reference
  to the readiness checker ([IR] grep), so launch still requires a human
  to start the loop. The residual risk is interpretive: an operator
  reading READY as authorization. The checker's own output says it
  approves nothing. Additionally, Campaign 4 already consumed its budget
  (32 recorded executions) and is closed, so "READY" describes machine
  checks for a *future* campaign, not a pending C4 action. I changed no
  gate and signed nothing.

## 9. Remaining blockers and exact remediation steps

| ID | Severity | Finding | Evidence | Consequence | Next action |
|---|---|---|---|---|---|
| F-1 | **High** | `family_records.py` has no production caller; campaign-end finalization (`build_multiplicity_record.py`, the script that produced the C4 record) predates and does not use it | [IR] `grep -rln family_records --include=*.py` → only harness comments + the E2E test | A future campaign's campaign-end step could silently repeat the all-unavailable outcome — the same defect class this remediation closed at execution time | Owner-reviewed update (or successor) to the finalization path that consumes persisted blocks via `family_records`, plus a test running that finalization end-to-end on fixtures; owner-reviewed, not urgent for closed C4 |
| F-2 | **Medium** | Five fail-closed paths lack negative tests: member-vs-block identity mismatch; execution-side H-10b floor raise; non-family v1.1.0 primitive (`applicable: false`); member frame < block_weeks weeks; durable `result.json` via the real adapter | [SC] test-file inspection; `family_records._member_identity_check` and the floor raise are unhit by any test | Fail-closed behavior asserted by reading, not by execution; regressions could pass unnoticed | Add the five targeted tests to the wiring suite |
| F-3 | **Critical** (pre-existing, disclosed, unresolved) | Sign-symmetry/exchangeability and week-independence assumptions unestablished; equal-AUC asymmetry size 0.055/0.060 (CP95 ≤ 0.077); Holm-threshold tail under asymmetry unmeasured | Owner record §0/§1; my 400-rep calibration (0.0600 ∈ [0.029, 0.071]) is consistent with the disclosure and validates nothing | Any formal refutation rests on p-values whose super-uniformity is assumed, not shown | Statistical review remains the blocker; no action inside this audit's scope |
| F-4 | **Medium** | Stale `H10_DECISION_RECORD_AWAITING_SIGNATURE.md` (says H-10 unresolved / C4 blocked) not marked superseded by the 2026-10-14 owner record | [IR] both files read; launch_gates records all gates decided | Conflicting governance state on disk; mis-derivation risk either direction | Owner-authored supersession annotation on the stale record |
| F-5 | **Medium** | READY verdict can be over-read as launch permission; readiness counts recorded gates, not authorization semantics | [IR] checker output + no automated consumer of the verdict | Process risk only; no code path auto-launches | None required beyond existing wording; owner treats READY as machine-scope only |
| F-6 | **Low** | `config_sha256` self-referential; not cross-checked against the adapter's spec hash at consumption | [SC] consumption validation chain | Provenance field proves intra-block consistency only | Optional: consumption-side cross-check against the ledger's spec sha |
| F-7 | **Low** | All member CIs and the pooled CI reuse `seeds[0]` — shared-resampling correlation across member intervals, undocumented | [SC] `_family_member_record` bootstrap call | No demonstrated inferential consequence (CIs provisional-only) | Document the seed policy in the wiring section comment |
| F-8 | **Low** | Fixture/implementation shared authorship; rung-2/3, purge refit, and real bootstrap evidence is fixture-only | [SC] fixture vs real-study comparison (§4) | Residual risk of a shared misunderstanding | Real-data integration test (stage-gated, below) discriminates this |
| F-9 | **Info** | The purge family never executed in C4 (record has regime/horizon/complexity only); purge wiring is fixture-only | [IR] C4 campaign-end record families | Purge path is coherent (declared in the frozen table) but unexercised on real data | Covered by the same integration test |

**Justified stages, precisely:**
* **Further technical review — justified now.** Engineering evidence is
  complete within tested scope; F-1/F-2 are closable by ordinary reviewed
  work.
* **Real-data integration testing — justified next, conditionally.** Only
  after F-1 and F-2 are closed, and only as an isolated single-config
  execution against the retained development table in a disposable
  workspace (no campaign, no budget, no persistent state, holdout
  untouched), owner-approved and predeclared.
* **A new campaign — not justified.** F-3 keeps statistical review
  blocking; F-4 governance ambiguity needs owner reconciliation; the
  owner must decide, and no test result here substitutes for that.

## 10. Final verdicts

**Engineering: REMEDIATION VERIFIED WITHIN TESTED SCOPE.**
All seven reported improvements were independently confirmed against the
pre-remediation baseline: v1.1.0 dispatch exists and runs in production
entry-point subprocesses; the v1.0.0 path is line-identical apart from one
additive block; measurements are produced by execution and persisted with
the frozen identities; the approved multiplicity procedure consumes them
correctly; fail-closed behavior is demonstrated for the tested paths; the
import boundary, firewall, and archive integrity hold. Nothing was found
that contradicts the remediation report. The scope qualifier is real:
link 3 has no production caller (F-1), five fail-closed paths are untested
(F-2), and long-horizon/purge behaviors rest on fixtures (F-8).

**Research governance: STATISTICAL REVIEW STILL BLOCKING.**
Correct plumbing does not establish statistical validity. The sign-flip
p-values' exchangeability assumptions remain unestablished exactly as
recorded (F-3), one governance record still contradicts the current
status (F-4), and the machine READY verdict is not — and cannot be —
authorization to launch (F-5). [NC] No conclusion about any trading
hypothesis can be drawn from synthetic fixture results, and none about a
future campaign's outcomes can be drawn from this audit.

**Single highest-priority next action:** close F-1 — wire
`stat_validation_h10/family_records.py` into the reviewed campaign-end
finalization path (or its reviewed successor) with an end-to-end
finalization test on fixtures, so the third link is executable and tested
outside this audit — then add the F-2 negative tests. Stop here; the
owner reviews, decides on governance, and authorizes any next stage.
