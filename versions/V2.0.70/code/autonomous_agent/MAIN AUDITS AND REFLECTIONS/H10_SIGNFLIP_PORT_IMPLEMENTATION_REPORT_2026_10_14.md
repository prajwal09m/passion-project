# H-10 Production Sign-Flip Port — Implementation Report (2026-10-14)

**Status: IMPLEMENTED AND ACCEPTED (gate-4 completion evidence).** Written
under the owner-recorded gate-4 authority (`launch_gates.json`:
`implementation_authorized`, 2026-10-12) and the owner's recorded D2
adoption of method (b) on 2026-10-14
(`stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md`).
The binding specification is
`stat_validation_h10/H10_SIGNFLIP_PORT_SPEC_2026_10_13.md`.

## 1. What was built

| Artifact | Path | sha256 (16) |
|---|---|---|
| Production module | `autonomous_agent/proposal_layer/signflip.py` | `3b3d5b3116e36eff…` |
| Acceptance tests (A-1..A-13) | `autonomous_agent/test_signflip_port.py` | `151275bcaabd72c9…` |
| Equivalence fixtures (A-12) | `autonomous_agent/signflip_port_fixtures_2026_10_14.json` | `0bb6339a690de061…` (pinned in the test file) |
| Fixture generator | `autonomous_agent/generate_signflip_fixtures.py` | — |
| Method allowlist | `autonomous_agent/proposal_layer/multiplicity.py` | `APPROVED_P_VALUE_METHODS = {"week_level_signflip_holm"}` |

Method: **`week_level_signflip_holm`** — week-level sign-flip Monte-Carlo
p-values, M = 1000, Holm step-down, familywise α = 0.05.

## 2. Reference equivalence (spec §6, A-12)

The port reproduces the independently developed reference
(`stat_validation_h10/simh10.py`) bit-for-bit:

* draw construction `S = np.random.default_rng(seed).integers(0, 2, size=(M, W)) * 2 - 1` (simh10.py:450),
* linear deltas `flips = (S @ g) / (2 * n_pos * n_neg)` (simh10.py:286-288),
* p-value `p = (1 + #{flips <= delta_hat}) / (M + 1)` (simh10.py:452).

Four frozen fixtures (boundary-exactness/tie case, two pinned 20-week
M=1000 frames at seeds 20261013/20261014, tie-heavy case) store the
**reference's** deltas and p-values; the generation run calls the real
`simh10.TrialStats.sign_flip_deltas` and refuses to write on any drift.
A-12 asserts the port equals every stored value exactly (`float` equality
and `np.array_equal`), and the fixture file hash is pinned in the test.

Additional equivalence evidence (A-3): on three independent synthetic
frames the linear form equals the brute-force full-swap AUC recomputation
(exact pairwise AUC counting, arm scores swapped within flipped weeks,
δ = AUC_A − AUC_B per simh10.py:145) with **max deviation 0.000e+00**
over 200 random flip rows + every single-week flip + the all-minus row.
The port's `linear_deltas` also equals the reference object's own
`sign_flip_deltas` bit-for-bit on reference-constructed `g`.

## 3. Binding conditions C-1 / C-2 / C-5 as implemented

* **C-1 (uniform i.i.d. draw, never curated):** `draw_flips(W, M, seed)`
  is pure and data-blind; A-4 verifies uniform ±1 rows within a 4.5σ
  binomial bound and seed dependence; A-5 verifies byte-identity with the
  raw `default_rng` draw (nothing filtered, deduplicated, reweighted, or
  reordered) and exactly M rows.
* **C-2 (draw is part of the procedure, recorded before outcomes):** the
  frozen campaign config carries `multiplicity_policy.flip_draw` (drawn
  at freeze by `secrets.randbits(64)`, OS CSPRNG, before any Campaign 4
  outcome existed; seed, W=157, M=1000, rows sha256, PCG64/numpy 2.3.3,
  stage `before_outcome_evaluation`). Production obtains it via
  `load_campaign_flip_draw`, which fails closed with
  `FlipProvenanceMissing` on missing/malformed records, stage mismatch,
  W mismatch, or rows-hash mismatch — a re-draw or seed tampering cannot
  pass silently (A-7, A-8).
* **C-5 (procedure-level statements only):** module docstring, the
  `disclosure_fields()` block (validity scope
  `procedure_level_marginal_over_flip_draw` + exchangeability
  assumption), the multiplicity gate basis, and the frozen config all
  state validity at procedure level and never conditional on the
  realized flip set; A-13 scans the modules and the Campaign 4 configs
  for forbidden set-conditional claim phrases and requires the
  procedure-level statements.

## 4. Recorded API adjustment (spec §5, "may be adjusted if recorded")

`signflip_p_value(delta_hat, g, draw, S, *, n_pos, n_neg)` takes the pair
counts as explicit keyword-only arguments (the spec's proposed signature
omitted them). The reference divides by `2 * pair_total` inside the flip
computation (simh10.py:287), so the port cannot know the scale
`delta_hat` lives in without them; guessing or ignoring the scale would
silently change the p-value. Recorded here per the spec's own clause.

## 5. Test results (2026-10-14, this tree)

* `python -m unittest autonomous_agent.test_signflip_port
  autonomous_agent.test_multiplicity` → **58 tests, OK, exit 0**
  (A-1..A-13 including the A-12 fixture equivalence; the multiplicity
  suite now asserts the allowlist matches the recorded decision and the
  approved method runs Holm end-to-end, while every unapproved name still
  raises `PValueMethodUnresolved`).
* Full governance/harness suite `python -m unittest discover -s
  autonomous_agent -t .` → **367 tests, OK, exit 0** (pre- and
  post-install; the freeze-integrity tests were made campaign-aware so
  the live-state invariants hold both before and after the Campaign 4
  config install).

## 6. Ownership / COI statement (spec §10)

This port is **not** independent confirmation. The D2 conflict-of-interest
disclosure applies: the same agent implemented parts of the system under
review and wrote the original Result 2 claim that its own Addendum A
retracts. The independent methodological anchor is the separately
developed reference implementation, pinned to the port by the frozen A-12
fixtures. Acceptance rests on the owner's recorded decision, not on this
report.
