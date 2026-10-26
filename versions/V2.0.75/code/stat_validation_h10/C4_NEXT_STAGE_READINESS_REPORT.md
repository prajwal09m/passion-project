# C4 Next-Stage Readiness Report

Date: 2026-10-17. Scope: F-4, F-5, F-6 remediation, and preparation of the real-data predeclaration
and the statistical review packet. **Campaign 5 was not launched. No campaign, real-data integration
test, or holdout access was performed. No H-10 signature, approval, or launch-gate change was made.**

## 1. Protected-artifact integrity

Protected hashes were captured before any edit to `.c4_protected_hashes_before.json` (11 files:
campaign-end multiplicity record, Campaign 4 archive `SHA256SUMS.txt`, measurement-wiring owner
record, `launch_gates.json`, the H-10 awaiting-signature record, `campaign_config.json` and its
`.sha256`, `proposal_ledger.jsonl`, `loop_state.json`, `experiment_registry.json`, and the D2/C-3
owner record).

Re-verified after all edits: **11 checked, 0 mismatches.** Classification: *independently verified.*

Caveat: `autonomous_agent/` and `stat_validation_h10/` are untracked by git, so a git diff of this
work is not available. The changed files are identified by path and SHA-256 in the predeclaration.
Scope of source changes is listed in §3.

## 2. Test results

| Command | Result |
|---|---|
| `py -3 -X utf8 -m unittest autonomous_agent.test_v110_wiring_e2e.ConfigurationIdentityProvenanceTests autonomous_agent.test_v110_wiring_e2e.FamilyRecordNegativeTests` | 16 tests, OK, exit 0 |
| `py -3 -X utf8 -m unittest discover -p "test_*.py" -t . -v` (full suite) | **428 tests, OK, exit 0** (log `.full_suite.log`) |

Previous reported count was 422; the increase of 6 equals the new F-6 provenance tests. The full
suite includes the import-boundary and freeze-integrity tests (`InertnessTests`), which passed.

Classification: *independently verified* (run in this session). Limitation: the e2e classes take
about 8 minutes; a foreground run timed out in this session, so the suite was run in background.

## 3. F-6: configuration/specification identity

**Defect confirmed (source-inspected).** The persisted `identity.config_sha256` was self-referential:
it was only checked against other copies inside the same block.

**Convention verified (source-inspected).** `recipe_harness.py` (≈ line 1282) computes
`sha256(json.dumps(config, sort_keys=True).encode("utf-8"))`. The ledger's `spec_sha256` is
`hardening.spec_fingerprint(spec)` (`hardening.py`, line 71; `spec_recipes.py` line 695).

**Fix implemented** in `stat_validation_h10/family_records.py`:
- `config_identity_sha256`, `authoritative_identity`, `load_authoritative_identity`,
  `verify_identity_provenance`. The authoritative config is re-read from the executed `spec.json`,
  its fingerprint is recomputed, and it is compared to the append-only ledger's recorded
  `spec_sha256`. Missing, unreadable, malformed, or mismatched authority raises `MemberRecordError`
  (fail closed). No hash is invented.
- `stat_validation_h10/campaign_end_finalization.py` (≈ lines 311–321) requires the provenance
  argument at consumption.
- `autonomous_agent/test_v110_wiring_e2e.py`: existing call sites were updated to pass the new
  required argument, and a new `ConfigurationIdentityProvenanceTests` class covers the five required
  cases: correct fingerprint accepted; changed config with old fingerprint refused; mismatched spec
  fingerprint refused; missing or malformed identity fails closed; self-consistent record that
  disagrees with the authoritative ledger refused. Plus a public-API test requiring the argument.

Classification: *source-inspected and test-verified.* Not yet exercised against a real Campaign 4
execution (none is permitted); that is part of the predeclared integration test (F-8/F-9).

Note on the change: the existing tests were edited to add the required argument. That is a
signature change, not a relaxation of any assertion. It should be reviewed as part of the owner's
sign-off.

## 4. F-4: conflicting H-10 records

Drafted `stat_validation_h10/H10_RECORD_SUPERSESSION_PROPOSAL.md`. Hashes verified:
- `H10_DECISION_RECORD_AWAITING_SIGNATURE.md`: `b9db3233…9f0a42` (older; D2 deferred, C4 blocked)
- `H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md`: `6dd40555…528e0` (newer; D2 adopted, C-3 ratified)
- `D2_AI_INDEPENDENT_STATISTICAL_REVIEW.md`: `0bfcf1df…` (matches the owner record's prefix)

The proposal is **not applied**. The older record is unchanged. Status: *source-inspected; owner-pending.*

## 5. F-5: machine READY versus authorization

Verified by running the read-only checker (`launch_readiness_check.py --json`):
verdict `READY (machine checks pass and all human gates recorded)`, exit 0, counts PASS 31,
RECORDED 7.

Findings (source-inspected):
1. **Scope.** The checker is titled "CAMPAIGN 4 LAUNCH READINESS". No Campaign 5 gate record exists.
   `READY` cannot be read as Campaign 5 readiness.
2. **Independent review is satisfied by substitution.** `launch_gates.json` marks `review_received`
   as decided, based on the owner's substitute route. Its own text says the external reviewer
   requirement is satisfied "by owner-recorded substitution, not by an invented external reviewer."
   The owner record discloses that the reviewing AI also implemented parts of the system.
3. **Human gates are recorded by an agent, not verified.** The record notes "recorded by coding
   agent" for several entries. `readiness` only checks that each gate has its required fields.
4. **Possible bypass (owner review required).** `grep` shows `launch_gates.json` is referenced only
   by `launch_readiness_check.py` and its test file (checked in `autonomous_agent/*.py`,
   `stat_validation_h10/*.py`, and `proposal_layer/*.py`). The campaign runner
   (`autonomous_agent/continuous_loop.py`, `ContinuousLoop.run`, line 880) does **not** read the
   human-gate record. Its launch controls are the campaign-config SHA pin, the lock, the execution
   budget, and stop conditions. A valid config and an unlocked state can therefore start the loop
   without consulting the gates. The config it would load is the closed Campaign 4 config, so this
   is a gap for any future campaign rather than an active risk today. I did not run the loop. Per the directive, **this is stopped for
   owner review**: the owner should decide whether the loop must check `launch_gates.json` before
   starting.

Classification: items 1–3 *source-inspected*; item 4 *source-inspected, owner-review required.*

## 6. Real-data integration predeclaration (F-8/F-9)

Drafted `stat_validation_h10/C4_REAL_DATA_INTEGRATION_PREDECLARATION.md`. Contains fingerprints for
the development inputs and code, prohibitions, the required isolation, and the fail-closed rules.

Left **unresolved**, not invented: the single configuration under test; the exact entry-point
invocation; the expected per-family member identifiers and counts; the week-alignment and purge
expectations; the frozen anchor values; and the tolerances. The holdout boundary of the development
files is not yet verified by the owner.

Owner authorization: **not granted.** Status: *drafted; owner-pending; not executed.*

## 7. Statistical review packet (F-3)

Drafted `stat_validation_h10/H10_STATISTICAL_REVIEW_PACKET.md`: nine specific questions (exchangeability,
temporal dependence, super-uniformity with the reported size 0.055/0.060, calibration sufficiency,
Monte-Carlo resolution at M = 1000, discrete Holm validity, conventions, the SIM-3 1.4–8.7% failure,
and the conflict of interest).

Status of F-3: **unresolved; reviewer-pending.** The owner adopted the method on a disclosed
substitute AI review. The packet does not describe the substitute as independent review, and it does
not claim the method is validated. Classification: *drafted; reviewer-pending.*

## 8. Campaign 5 and the advanced directives

- **Campaign 5: not launched.** Blockers: the only campaign config in the repository is
  `campaign-4-continuous-2026-10-14` (Campaign 4, closed); no Campaign 5 configuration, execution
  budget, or gate record was found; F-3 has no independent statistical assessment beyond
  the owner-accepted substitute; the loop-gate question in §5.4 is open; the real-data integration
  test is not authorized.
- **Autonomous model-discovery upgrade:** not started. It needs an owner-approved scientific
  scope first, because changing candidate selection or promotion touches the frozen protocol. Not
  attempted in this session.
- **Profitability and trading simulation:** not evaluated. No simulation objective is in the frozen
  design, and none may be added to Campaign 5 silently.

## 9. Status summary

| Item | Status |
|---|---|
| Protected historical hashes (11) | independently verified, unchanged |
| Full test suite, 428 tests | independently verified, exit 0 |
| F-6 provenance cross-check and five required tests | source-inspected and test-verified; real-data use pending |
| F-4 supersession proposal | drafted; owner-pending; not applied |
| F-5 readiness scope and substitute-review gate | source-inspected |
| F-5 possible loop bypass of human gates | source-inspected; **owner review required** |
| Real-data integration predeclaration | drafted; owner-pending; not executed |
| F-3 statistical review packet | drafted; reviewer-pending; method unresolved |
| Campaign 5 launch | **not performed; blocked** |
