# C4 Campaign-End Integration Remediation Report — 2026-10-17

**Scope.** Closed findings F-1 and F-2 of
`C4_POST_REMEDIATION_INDEPENDENT_AUDIT_2026_10_16.md` by isolated
implementation work and synthetic-fixture acceptance testing only. No
campaign was run, launched, scheduled, or resumed; neither interrupted
execution was resumed; no real-data experiment was executed and no
execution budget was consumed; the sealed holdout was never opened; no
historical artifact, multiplicity record, archive entry, frozen pin,
launch gate, or signature was modified; no statistical assumption,
family membership, hypothesis definition, or the approved
`week_level_signflip_holm` method was changed. The historical one-shot
builders (`campaign_end_2026_10_16/build_multiplicity_record.py`,
`build_final_archive.py`) were **not** invoked at any point.

---

## 1. F-1: root cause and correction

**Root cause.** The 2026-10-16 measurement-wiring remediation produced
all three wiring links *code-wise* — execution collects per-member
records (recipe_harness collectors), the adapter persists them
(`result.json` metrics copy), and
`stat_validation_h10/family_records.py` consumes them — but link 3 had
no production caller. The audit's `[IR]` evidence: `grep -rln
family_records --include=*.py` found only harness comments and the
wiring test. The only script that has ever built a campaign-end
multiplicity record
(`campaign_end_2026_10_16/build_multiplicity_record.py`, Campaign 4,
2026-10-16 19:07) predates the wiring: it derives the executed poolable
set from the ledger and constructs every predeclared member as
`unavailable` directly, never calling `family_records`. Left as-is, a
future campaign's finalization step could silently repeat the
all-unavailable outcome — the same defect class the remediation closed
at execution time.

`continuous_loop.py` was inspected as tasked: its only campaign-end
interaction is the provisional-to-formal firewall inside `_adjudicate`
(`assert_firewall_intact` over results, which include the block; source
comments at L596/L609). No code path in the loop builds a multiplicity
record; finalization has always been an owner-run step after campaign
end. F-1 therefore belongs in that step, not in the loop.

**Correction (smallest architecture-compliant connection).**

*New file:* `stat_validation_h10/campaign_end_finalization.py` (464
lines) — the reviewed successor finalization entry point for FUTURE
campaigns. Same frozen-API statistics as the historical builder (it
performs none of its own), but it first consumes persisted
per-member records through `family_records`:

* `load_campaign_config` — verifies the config pin against its sha256
  sidecar, the campaign id, the H-10b floors (`n_boot >= 1000`,
  `n_flips >= 1000`), the owner-frozen C-2 policy fields
  (`missing_member_rule == "C-2_option_A"`, `missing_member_p == 1.0`,
  `campaign_end_record_required is true`), and the approved-method
  choke point (`require_approved_method`).
* `poolable_executed_experiments` — mirrors the historical builder's
  ledger derivation (proposals + EXECUTED/ADJUDICATED transitions
  pinned to the campaign id); the experiment id is resolved from the
  transitions themselves (the `EXECUTION_STARTED` detail always carries
  it), so interrupted executions no longer need the
  registry-substring fallback.
* `build_campaign_end_record` — for every executed poolable
  (experiment, primitive): loads
  `autonomous_agent/candidates/<experiment_id>/result.json` through
  `fr.load_member_block` (schema, firewall, ladder, complete member
  set, linear form), verifies block family/primitive association
  against the ledger's predeclared primitive, then feeds the blocks to
  `fr.family_members_from_records` (approved-method unadjusted
  p-values from the campaign's own recorded flip draw; C-2 mapping of
  execution-recorded unavailable members). Interrupted experiments
  (executed, never adjudicated, no durable result — recorded
  FAILED_EXECUTION) receive C-2 Option A unavailable members with the
  recorded reason. The record is computed by
  `fr.campaign_end_record` (Holm step-down, frozen bounds,
  feasibility).
* `finalize_campaign_end` — append-only write through
  `fr.append_record` (fsynced; refuses a second record per campaign)
  plus readback verification. If a record for the campaign already
  exists, a fresh recomputation must equal it **exactly** or
  finalization refuses; history is never re-decided.
* `main` — CLI for the owner-run step (`--campaign-id`, `--root`,
  `--config`, `--ledger`, `--candidates`, `--out`, `--dry-run`);
  refuses with a one-line `FINALIZATION REFUSED (...)` and exit 1 on
  any fail-closed condition; prints the formal vocabulary only once a
  record actually exists (provisional-to-formal firewall).

**Fail-closed contract (audit task §2, point 8):**

* Durable result exists but carries no usable
  `family_measurements` block → `MemberRecordError` (propagated
  unchanged from the consumption module). No pooled-only fallback can
  produce a "completed" family evaluation.
* Adjudicated experiment with no durable result at all →
  `FinalizationError` — required persisted measurements are absent and
  are never defaulted to unavailable. (Stricter than the historical
  builder, whose registry fallback could mask this.)
* Only an interruption *recorded in the ledger* (never adjudicated,
  no durable result) maps to C-2 Option A unavailable.
* Duplicate predeclared member ids, frozen-table/ladder disagreement,
  association mismatch, infeasible granularity, foreign rows in the
  output file, or an existing record that disagrees with a
  recomputation → refusal before/without writing.

*Modified file:* `stat_validation_h10/family_records.py` — **18
additive lines only** (sha256 `f9cf21e4…` → `94cc7df8…`): a
re-export block (`FamilyMember`, `append_record`, `read_records`,
`require_feasible`, `require_approved_method`, `PRIMITIVE_TO_FAMILY`,
`MIN_N_BOOT`, `MIN_N_FLIPS`, `formal_refuted_members`) so the
finalization successor reaches every frozen API through the
consumption facade and this module stays the single consumption-side
entry point. No existing line changed; no logic added; the existing
`test_consumption_facade_is_the_frozen_api_only` test was extended with
four `assertIs` delegation checks over the new surface.

**Import boundary preserved.** The successor lives on the
stat-validation side beside the multiplicity machinery (the same
boundary the historical builder operates under); it imports
`family_records` and `three_valued` only. The freeze-integrity needle
scan (`autonomous_agent/*.py` + `proposal_layer/*.py` for
`"import " + "multiplicity"`) still returns exactly
`{continuous_loop.py, test_multiplicity.py, test_signflip_port.py}`
(freeze suite 23/23 OK), and T12/T13 pass. The wiring test file's
existing self-scan (concatenated needle) also still holds.

**Behavioral evidence against Campaign 4 state (read-only).** The new
entrypoint was probed against the real Campaign 4 inputs with
`--dry-run` and a temporary `--out` (no historical path writable):

```
py -3 -X utf8 stat_validation_h10/campaign_end_finalization.py \
  --campaign-id "campaign-4-continuous-2026-10-14" --dry-run \
  --out "C:/Scratch/c4_probe_out.jsonl"
```
→ exit 1; stderr: `FINALIZATION REFUSED (MemberRecordError): no
family_measurements block: the experiment predates the measurement
wiring or its run failed closed; its members are not computable and may
never be assumed or reconstructed`

The successor therefore cannot recreate Campaign 4's all-unavailable
record, cannot recompute or overwrite it, and cannot be tricked by a
v1.0.0-style pooled-only `result.json`.

## 2. New future campaign-end data flow

```
run_from_config (v1.1.0 branch)
  -> outputs/evaluation.json  results.family_measurements   [link 1]
adapter.run_experiment durable copy
  -> autonomous_agent/candidates/<exp>/result.json
     metrics.family_measurements                            [link 2]
campaign_end_finalization.finalize_campaign_end
  -> fr.load_member_block(result.json)          (validate, fail-closed)
  -> fr.family_members_from_records(blocks, campaign_config=cfg)
       week index W + recorded flip draw hash-verified;
       unadjusted p by the approved week_level_signflip_holm
       (signflip.signflip_p_value on the persisted g);
       C-2 Option A mapping of execution-recorded unavailable members
  -> fr.campaign_end_record  (Holm step-down, bounds, feasibility)
  -> fr.append_record(out, record) + readback verify     [link 3, wired]
```

Campaign id, ledger, config (+pin sidecar), candidates root, and
output path are all parameterized (fixture-testable); defaults match
the production layout under `autonomous_agent/state/`. The workflow
step for a future campaign is: after the loop stops, run
`campaign_end_finalization.py --campaign-id <id>` (owner-run, reviewed,
append-only). The historical Campaign 4 one-shot builder remains the
record of how the Campaign 4 artifact was produced and is not part of
the future workflow.

## 3. F-2 negative-test coverage (11 new tests, all executed)

All tests live in the wiring suite
(`autonomous_agent/test_v110_wiring_e2e.py`, 21 → 32 tests). Every
negative verifies the exact error or recorded status, whether output
files are written, and that no partial artifact can be mistaken for a
completed finalization.

| # | Audit gap | Test | Exact verified behavior | Outputs |
|---|---|---|---|---|
| 1 | Member-vs-block identity mismatch (`_member_identity_check` unhit) | `FamilyRecordNegativeTests.test_member_identity_mismatch_fails_closed` | member with a conflicting `identity` (different `config_sha256`, `n_boot`) → `MemberRecordError: … carries a different experiment identity …` | none (unit level) |
| 2 | H-10b `n_boot` floor (execution-side raise unhit) | `ExecutionFailClosedNegativeTests.test_h10b_n_boot_floor_is_refused_before_evaluation_output` | layer 1: compiler refuses `n_boot=500` at render (`CompileError`, "n_boot"); layer 2: hand-written config (bypassing the compiler) runs the pooled pass then hits the execution raise: exit ≠ 0, stderr `family-feeding experiments require n_boot >= 1000; got 500` | **no** `outputs/evaluation.json` |
| 3 | Non-family v1.1.0 primitive (`applicable: false` untested) | `…test_non_family_v110_primitive_emits_applicable_false` | `point_in_time_data_audit` exits 0; block is `schema` + `applicable: false` + reason, with **no** `members`/`iut_result`/`member_set_complete`/`family` keys; `load_member_block` accepts (schema sound) but `family_members_from_records` raises `MemberRecordError: … declares no applicable family measurements …` — it can never feed a Holm family | evaluation written (correct contract), family evaluation claim impossible |
| 4 | Member frame < `block_weeks` weeks | `…test_member_frame_below_block_weeks_fails_the_run_closed` | fixture knob `starve_below_cell` puts the below cell in 3 W-SUN weeks (both classes, rows, events — never degenerate-unavailable); member bootstrap raises `ValueError: Insufficient calendar weeks…` → exit ≠ 0 | **no** evaluation output (fail-closed, as documented in remediation report §9) |
| 5 | Durable `result.json` through the REAL adapter | `CampaignEndFinalizationE2ETests.test_adapter_execution_persists_the_block_durably` (+ §4 below) | `ExperimentAdapter.run_experiment` with the fixed command registry (experiment role = byte-identical `python -m autonomous_agent.experiments.run_experiment`) writes `candidates/exp-f1-finalization/result.json`; `metrics.family_measurements` complete; `fr.load_member_block(result_path)` round-trips; block survives candidate-workspace destruction (REJECTED case asserts workspace gone, durable file present) | durable artifact present and consumable |
| 6 | SPY-less purge calendar ([SC]-only branch, now executed) | `…test_purge_family_without_the_spy_calendar_fails_closed` | fixture knob `drop_spy` removes `SPY.csv`; purge rungs hit `_study_opens_by_ticker(["SPY"])` → `FileNotFoundError: Missing local OHLCV file: …SPY.csv`; exit ≠ 0 | **no** evaluation output; no fallback calendar |

Plus five finalization-level negatives (task §2 point 8, executed in
§4's scenario harness): pooled-only `result.json`,
execution-time-incomplete member set, adjudicated experiment without
durable result, tampered recorded flip draw (rows-hash), and recorded
week-index disagreement — each refused with its exact error and with
**no output record file created**.

## 4. End-to-end finalization test evidence

`CampaignEndFinalizationE2ETests` (6 tests, 35.3 s; one shared class
fixture).

**Production execution.** `setUpClass` builds the synthetic root
(synthetic frozen-study module mirroring the reviewed contracts, SPY +
AAA/BBB/CCC OHLCV cache, 756-row event table with `thin_below_cell`,
real `spec_recipes` shim, byte-identical harness copies), records the
baseline-reproduced fingerprint, and runs **the real
`ExperimentAdapter.run_experiment`** with its default command registry:
`unit_tests` role = the fixture smoke suite, `experiment` role = the
byte-identical production entry point inside the isolated workspace
(scrubbed environment, network guard, workspace copy of the root). The
spec installs the compiler-rendered v1.1.0 regime-split config
(`n_boot = 1000`, H-10b floor). The thin below-cell fixture yields one
healthy member (`above_sma200`) and one execution-recorded
degenerate-unavailable member (`below_sma200`) — the required mixed
family.

**Durable persistence.** `candidates/exp-f1-finalization/result.json`
carries `metrics.family_measurements` with a complete member set;
`fr.load_member_block(result_path)` reads exactly what execution wrote.
Measurements are produced by execution and persisted by the adapter —
no test constructs or injects member results.

**Finalization sequence.** Each test scenario provides an isolated
synthetic ledger (production row shapes: proposal with
`design.primitives`, COMPILED/EXECUTED/ADJUDICATED transitions whose
details pin `campaign_id` and `experiment_id` exactly as
`continuous_loop` writes them), a frozen-shape campaign config
(`multiplicity_policy.flip_draw` from `signflip.draw_flips(W, 1000,
20261016)` where W = the persisted block's recorded week index,
`missing_member_rule: C-2_option_A`, `campaign_end_record_required:
true`, sha256 pin sidecar), and an **isolated output destination**.
`cef.finalize_campaign_end` then performs load → validate → p-values →
Holm → append-once → readback.

**Verified properties** (in `test_finalization_consumes_persisted_records_end_to_end`):

* Mapping: exactly one family (`regime`), `m = 2`, member ids
  `<exp>:above_sma200` / `<exp>:below_sma200`; every row carries the
  correct family, primitive, and experiment id; `ledger_sha256`
  recorded; `p_value_method == "week_level_signflip_holm"`;
  feasibility feasible.
* Available member: `unadjusted_p` re-derived by the test-local
  **independent pure-Python** counter `_independent_p` (exhaustive over
  the recorded S rows, no numpy) from the *persisted* `g`/`delta_hat`/
  pair counts — agreement to 1e-12; `adjusted_p` re-derived by
  test-local `_independent_holm([p, 1.0])` (independent Holm
  step-down) — agreement to 1e-9; `formal_status == REFUTED` agrees
  with the independent rejection flag (fixture data may legitimately
  refute; refutation is a property of the fixture, not of any real
  hypothesis).
* Unavailable member: C-2 Option A — `status UNAVAILABLE`,
  `formal_status unavailable`, `unadjusted_p null`, reason names C-2,
  counted toward `m = 2` (the independent Holm used effective
  p = 1.0), never formally REFUTED.
* Recorded draw and week index are the ones actually used: a config
  whose recorded `rows_sha256` matches no regenerated draw →
  `FlipProvenanceMissing: … do not hash-match the frozen record …`;
  a config whose recorded `W` disagrees with the persisted block →
  `FlipProvenanceMissing: … does not match the current frame …`;
  both refuse with **no output file**.
* Complete frozen member set is required: removing one member from the
  persisted block (leaving `member_set_complete: true`) →
  `MemberRecordError: … does not match the frozen ladder …`; no output.
* No silent pooled-only fallback: stripping `family_measurements` from
  a durable result that still carries pooled metrics →
  `MemberRecordError: no family_measurements block …`; no output; the
  workflow cannot report a completed family evaluation.
* Adjudicated but result-less experiment → `FinalizationError: …
  durable result.json is missing …`; no output.
* Append-only: exactly one row written; an immediate rerun recomputes
  an identical record, refuses to append (`written: False`), and the
  file still holds one row.
* Campaign 4's historical record is asserted unchanged inside the test
  itself (sha256 `75477043…`), and the suite's module-level guards
  re-assert record / archive-manifest / owner-decision /
  launch-gates bit-identity before and after the whole run.

## 5. Independent verification of p-values and Holm adjustment

Unadjusted p-values: the production path is
`signflip.signflip_p_value` (lower tail, `+1` correction, `<=` ties,
procedure-level validity), computed inside
`family_members_from_records` from the persisted `g` with the
campaign's hash-verified recorded draw. The E2E test re-derives every
consumed p-value by exhaustive pure-Python enumeration of the same
recorded S rows (`_independent_p`) — 12-decimal agreement.

Holm adjustment: production is `multiplicity.holm_step_down` (prefix-
max, cap at 1.0, stop-at-first-non-rejection) over the complete family
with C-2 effective p = 1.0 for unavailable members. The E2E test
re-derives adjusted values and rejection flags with its own step-down
implementation (`_independent_holm`) — 9-decimal agreement. The
existing `HandVerifiedMultiplicityTests` (engineered members over a
recorded W=8 draw) continue to pass unchanged.

## 6. Exact commands, test counts, and exit codes

All runs executed fresh on 2026-10-17 in this checkout; exit codes
captured directly, not through pipelines.

| Command | Exit | Result |
|---|---|---|
| `py -3 -X utf8 -m py_compile autonomous_agent/test_v110_wiring_e2e.py stat_validation_h10/campaign_end_finalization.py stat_validation_h10/family_records.py` | 0 | COMPILE OK |
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_wiring_e2e.FamilyRecordNegativeTests -v` | 0 | Ran 10 tests — OK (0.01 s) |
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_wiring_e2e.ExecutionFailClosedNegativeTests -v` | 0 | Ran 4 tests — OK (103.8 s) |
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_wiring_e2e.CampaignEndFinalizationE2ETests -v` | 0 | Ran 6 tests — OK (35.3 s) |
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_wiring_e2e -v` | 0 | **Ran 32 tests — OK (497.5 s)** (21 pre-existing + 11 new) |
| `py -3 -X utf8 -m unittest autonomous_agent.test_freeze_integrity` | 0 | Ran 23 tests — OK (2.5 s) — needle scan still exactly the frozen allowlist; pinned artifacts match |
| `py -3 -X utf8 -m unittest autonomous_agent.test_recipe_harness` | 0 | Ran 11 tests — OK (16.9 s) — v1.0.0 path unchanged |
| `py -3 -X utf8 -m unittest autonomous_agent.test_signflip_port` | 0 | Ran 16 tests — OK (0.08 s) |
| `py -3 -X utf8 -m unittest autonomous_agent.test_proposal_layer -k t12 -k t13` | 0 | Ran 2 tests — OK (0.14 s) — T12/T13 import boundaries |
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_primitives` | 0 | Ran 32 tests — OK |
| `py -3 -X utf8 -m unittest autonomous_agent.test_multiplicity` | 0 | Ran 42 tests — OK |
| `py -3 -X utf8 -m unittest discover -p "test_*.py" -t .` | 0 | **Ran 422 tests — OK (569.1 s)** (411 pre-existing + 11 new) |
| `py -3 -X utf8 stat_validation_h10/campaign_end_finalization.py --campaign-id "campaign-4-continuous-2026-10-14" --dry-run --out "C:/Scratch/c4_probe_out.jsonl"` | 1 (refusal) | `FINALIZATION REFUSED (MemberRecordError): no family_measurements block …` — no write; historical paths not targeted |
| `sha256sum -c SHA256SUMS.txt` (Campaign 4 final archive) | 0 | 12/12 entries OK |

## 7. Protected-artifact integrity verification

Before/after SHA-256 capture of 47 protected files (append-only record,
final archive + all manifest entries, both freeze directories and
their pins, owner decision record, `launch_gates.json`, the outstanding
H-10 decision record, both C4 reports, the consumption module, the
historical builders, and the six frozen state files). Diff result:
**46 of 47 byte-identical; the single change is the intended 18-line
additive facade extension** to `stat_validation_h10/family_records.py`
(`f9cf21e4…` → `94cc7df8…`), documented in §1 and covered by the
delegation-assert test extension. Key pins re-confirmed:

| Artifact | sha256 (prefix) | Status |
|---|---|---|
| `state/campaign_end_multiplicity.jsonl` | `75477043…` | UNCHANGED (audit value) |
| Campaign 4 final archive, 12 manifest entries | 12/12 | UNCHANGED |
| `C4_MEASUREMENT_WIRING_FINDING_OWNER_DECISION_RECORD_2026_10_16.md` | `7d837caa…` | UNCHANGED (audit value) |
| `launch_gates.json` | `dfed21cd…` | UNCHANGED (audit value) |
| `H10_DECISION_RECORD_AWAITING_SIGNATURE.md` | `b9db3233…` | UNCHANGED (audit value; still unsigned) |
| `state/campaign_config.json` + sidecar | `d8bff195…` / `105a6486…` | UNCHANGED (freeze-test pin) |
| `freeze_2026_10_14/*`, `freeze_2026_10_15/*` | (all) | UNCHANGED |
| Historical builders (`build_multiplicity_record.py`, `build_final_archive.py`) | `cf5f0799…` / `524b2ace…` | UNCHANGED — never invoked |

The wiring suite's own module-level guards (record, archive manifest,
owner decision, launch gates, holdout absence) additionally asserted
bit-identity across every suite run today; freeze-integrity's
`PINNED`-digest tests passed (23/23).

**Diff review.** Exactly three files changed today, all intended:
`stat_validation_h10/campaign_end_finalization.py` (new, 464 lines),
`stat_validation_h10/family_records.py` (+18 additive lines),
`autonomous_agent/test_v110_wiring_e2e.py` (imports, two fixture knobs
`starve_below_cell`/`drop_spy`, four helpers, one negative test, two
new test classes, four facade-delegation asserts). No existing test was
weakened or modified beyond additive assertions; no frozen contract
changed; no other file in either source tree was touched.

## 8. Remaining limitations and unresolved statistical assumptions

* **F-3 (unchanged, still blocking).** Week-level sign-symmetry /
  exchangeability under H0 and week-cluster (super-)independence remain
  unestablished exactly as the owner record documents; the Holm-
  threshold tail under asymmetry is unmeasured. This remediation
  changes no statistical surface; every statement here is engineering
  evidence only. Statistical review remains the blocker.
* **F-4 (unchanged).** `H10_DECISION_RECORD_AWAITING_SIGNATURE.md`
  remains superseded-in-fact by the 2026-10-14 owner record without a
  supersession annotation. Not mine to change; the file is untouched
  and still unsigned.
* **F-5 (unchanged).** The machine READY verdict is not authorization;
  nothing in this work keys any launch path on it.
* **F-6 (unchanged).** `config_sha256` is still not cross-checked
  against the adapter's spec hash at consumption (provenance field
  remains intra-block).
* **F-8 / F-9 (unchanged).** Rung-2/3 rebuilds, purge refits, and the
  bootstrap behavior rest on fixture evidence (the synthetic study
  mirrors the reviewed contracts; source-compared, not the frozen
  study). The purge family remains fixture-only. The real-data
  integration execution is the discriminating next stage and stays
  owner-gated.
* **Successor scope.** The successor is wired as an owner-run CLI /
  library step (the shape finalization has always taken); the loop was
  deliberately not modified to auto-finalize — campaign-end records
  remain deliberate, reviewed acts. Its unavailable-member fallback is
  narrower than the historical builder's by design (recorded
  interruptions only; adjudicated-but-result-less is a hard refusal).
* **Fixture statistics.** Every measurement in this report comes from
  synthetic fixtures and is not evidence about any trading hypothesis.

## 9. Explicit confirmations

* No campaign was launched, scheduled, executed, or resumed; Campaign 4
  remains closed and byte-identical (record `75477043…`, archive
  12/12).
* Neither interrupted execution was resumed.
* No real-data experiment was executed; no execution budget was
  consumed. Every execution today was a subprocess inside a disposable
  temporary fixture root (asserted holdout-free), deleted by test
  cleanup; nothing wrote under `autonomous_agent/state/`, and the
  before/after hash capture proves it.
* Holdout access: zero. The sealed prospective directory is absent;
  its absence was hashed before and after the suite; every fixture
  workspace is asserted holdout-free.
* No statistical assumption, family membership, hypothesis definition,
  margin, threshold, or the approved p-value method was changed.
* No H-10 signature, approval, gate change, or launch authorization was
  made or implied. This report approves nothing.
* The one-shot archive and multiplicity-record builders were not run;
  the new finalization entrypoint's only invocation against historical
  inputs was the `--dry-run` refusal probe of §1 (temp `--out`,
  exit-before-write).

## 10. Are F-1 and F-2 genuinely closed?

**F-1 — YES (engineering).** The consumption link now has a
production caller that is the actual future campaign-end workflow
(`campaign_end_finalization.py`), reachable only through
`family_records`, verified end-to-end on fixtures from real execution
through durable persistence to Holm-adjusted record with independently
re-derived p-values and adjusted values; and the same entrypoint
demonstrably *refuses* (exit 1, no write) on Campaign 4's real inputs,
so the all-unavailable outcome cannot silently recur.

**F-2 — YES.** All six audit-identified untested fail-closed paths are
now executed tests asserting their exact errors and the absence of
output artifacts: member-vs-block identity mismatch; H-10b floor (both
the compiler layer and the previously-unhit execution-side raise);
non-family `applicable: false` contract; member frame below the
block-bootstrap week floor; durable `result.json` through the real
adapter; and the SPY-less purge calendar. The full suite is green at
422 tests (exit 0) with every protected artifact unchanged.

**Stage discipline.** Per the audit's staged plan: F-1/F-2 closure
justifies further technical review. The next stage — the isolated,
owner-approved, predeclared real-data single-config integration
execution — is **not** performed here, and a new campaign is **not**
justified (F-3 statistical review still blocks; F-4 needs owner
reconciliation). Stopping for owner review.
