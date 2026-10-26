# Harness v1.1.0 — D2-independent implementation report (2026-10-12)

**Scope:** the D2-independent subset authorized by the human owner on
2026-10-12 (`HARNESS_V1_1_0_GATE3_AUTHORIZATION_RECORD_2026_10_12.md`).
**No statistical method is adopted. H-10/D2 remain open; nothing is frozen
or launched.**

## 1. What was built

| Component | File (SHA-256 prefix) | Tests |
|---|---|---|
| Holm step-down, family bookkeeping, campaign-end multiplicity record, provisional→formal firewall, C-2 missing-member rule, H-10 p-value gate, audit-stop signals | `proposal_layer/multiplicity.py` (`5865cc3d…`) | `test_multiplicity.py` (`c27473e5…`) — 36 tests |
| Census manifest model, frozen-tolerance policy, validator, header scaffolder | `proposal_layer/census.py` (`12f61179…`) | `test_census_manifest.py` (`4eaa7963…`) — 20 tests |
| Two new fail-closed stops + firewall enforcement wired into the loop | `continuous_loop.py` (`da3bb77f…`) | exercised by the loop tests below |
| Freeze-integrity, protected-state preservation, stop↔code correspondence, inertness, new-stop loop behavior | `test_freeze_integrity.py` (`9486d9d7…`) — 20 tests | — |
| Draft census manifest (scaffold, **not** an audit result) | `…/CENSUS_MANIFEST_DRAFT_2026_10_12.json` (`aa5bd380…`) | validated by the census tests |
| Launch-readiness checker (marker scan updated to match the implementation) | `launch_readiness_check.py` (`c2e808d8…`) | fixture-verified: compliant tree → exit 0/READY; real tree → exit 2/NOT READY |

**Suite: 311 tests, OK, exit 0** (235 before this work → +76). Every run's
exit status was captured directly, not through a pipeline filter.

## 2. Design decisions worth recording

1. **The p-value gate is the single choke point.**
   `APPROVED_P_VALUE_METHODS` is an **empty** allowlist, so
   `require_approved_method()` raises `PValueMethodUnresolved` for every
   method name — including "b", the simulation's candidate. Holm machinery
   therefore cannot smuggle in method (b); a test asserts the allowlist is
   empty and that `adjust_family()` / `campaign_end_record()` refuse before
   computing anything. Adding a method is an owner decision recorded in the
   H-10 record, never a code-only change.
2. **Order of refusals inside `adjust_family`** is deliberate: method gate
   → family coherence → granularity feasibility. Infeasible granularity
   (`n_boot + 1 < 20·m`, or `m > 50`, or `n_boot < 1000`) returns
   **INCONCLUSIVE for every member**, so an infeasible experiment can never
   produce a formal refutation.
3. **C-2 is enforced structurally**: `FamilyMember.effective_p` is 1.0 for
   an unavailable member, it occupies a slot in `m`, its formal status is
   `unavailable`, and a test proves the slot shifts the step-down threshold
   (p = 0.03 survives alone, does not survive beside an unavailable member).
4. **The bare label `REFUTED` is reserved.** `find_formal_refutation_labels`
   matches the standalone uppercase token only, so `provisional_refutation_signal`
   and `formal_refutation: false` are legal everywhere. The loop asserts the
   firewall before writing any adjudication detail and halts with
   `FIREWALL_VIOLATION` (journaled) if it trips — the label can never reach a
   ledger row, loop event, or report.
5. **Audit stops are durable before they are fatal.** On a confirmed
   point-in-time audit finding the loop writes a `FAILED_EXECUTION`
   transition carrying the audit detail, journals `audit_stop`, then raises.
   The restart guard (`_enforce_audit_stops`) folds the ledger and stops
   again — but **only for configs that declare the stops**, so Campaign 3's
   frozen config is behaviorally untouched (asserted by a test).
6. **`stop_conditions` in a campaign config is declarative** (nothing read
   it before today). The new `STOP_ENFORCEMENT` map in
   `test_freeze_integrity.py` binds each declared stop name to literal
   markers that must exist in the source; a config that declares a stop with
   no wiring now fails the suite, and a newly declared stop must be added to
   the map.
7. **Census tolerances cannot be invented.** A Tier-1 float column without
   documented input precision raises `CensusError`; a tolerance whose origin
   is `OBSERVED_MISMATCH` is refused by both the builder and the validator;
   a Tier-2 column is `UNVERIFIABLE` by declaration and can never be PASS or
   yield contamination; structural results never upgrade a value verdict.
   The scaffolded draft manifest currently fails validation with 97
   "tolerance not frozen" errors — **correctly**: it cannot back an audit
   PASS until the freeze declares the tolerances.

## 3. Two discrepancies surfaced (not silently reconciled)

- **Feature-column count.** The development table header has 114 columns;
  removing the 14 documented non-feature columns leaves **100** feature
  columns, while the plan/inventory says **101**. The scaffold records both
  numbers with `inventory_count_matches_observed: false`. Ruling needed at
  freeze.
- **Family membership.** The scaffold's name-prefix classifier yields
  price/volume 46, market-benchmark 14, zone-base 8, order-block 32, which
  does not reproduce the inventory's 48/11/8/34. Both the per-family
  membership and the count are freeze-time human decisions; the classifier
  is labelled as a grouping heuristic, not an authority.
- **Stop-count conflict** (plan's "15 original" vs Campaign 3's 14) is
  unchanged and still needs a human ruling; the correspondence map covers
  the 14 real ones plus the two new ones = 16.

## 4. Verification performed after the changes

| Check | Result |
|---|---|
| Full suite | **311 tests, OK, exit 0** (70 s) |
| Protected pins (plan `094827b0…`, H-10 record `b9db3233…`, review bundle `ee345dab…`, C3 config `1e0e30b8…` + sidecar, C4 draft `307e98ab…`, flake evidence `72504661…`, flake-fixed test `e1de8523…`) | **all unchanged** |
| Holdout | `prospective/` absent; policy `SEALED`, uses 0 |
| Campaign 3 state | `STOPPED`, cycle 40, 38/40, ledger 350 rows, folds strictly |
| Locks / STOP | none |
| Launch-readiness checker | 19 PASS / 2 BLOCKED / 8 HUMAN → exit 2 (NOT READY); fixture tree → exit 0 (READY) |

The two remaining machine blockers are exactly the two that must remain:
**no frozen C4 config** and **five dormant primitives** (activation was
deliberately excluded from this authorization).

## 5. What this work does *not* do

No method adopted (H-10/D2 open) · no primitive activation · no
`harness_version == "1.1.0"` run-mode selector in `recipe_harness.py` · no
gate, threshold, bias floor, class budget, duplicate layer, outcome-blindness
input, or approval policy changed · `bias_policy.json`, the baseline
registry, and every Campaign 3 artifact untouched · no freeze · no launch ·
no experiment executed · no holdout access · no network.

## 6. Remaining path to launch (unchanged order)

1. Independent review → D2 → C-3 *(human, external)*
2. Stop-count conflict + Tier-2 residual rulings *(human)*
3. Remaining implementation needing its **own** authorization: five
   primitives executable + 1.1.0 run modes + frozen ladders/margins +
   spec-fidelity/three-valued-evaluator/primitive tests (plan checklist B1
   items 1–2 and the per-primitive tests)
4. Freeze-time work: census tolerances declared and census executed, H-10b
   feasibility check, count-once rule, freeze approval, fresh pin +
   fingerprint
5. Gate 7 re-verification (`launch_readiness_check.py` must exit 0) →
   gate 8 launch authorization → run
6. Campaign end: multiplicity record computed over complete families, else
   every provisional signal defaults to INCONCLUSIVE (fail-closed)

## 7. Addendum — final verification after the R-3 activation (2026-10-12)

This section supersedes the §4 numbers; §4 remains the verification at the
end of the gate-3 subset.

After the gate-3 subset, the owner's separate **R-3 primitive-activation
grant** (`PRIMITIVE_ACTIVATION_GRANT_R3_2026_10_12.md`) authorized flipping
the five v1.1.0 primitives to executable and adding the 1.1.0 compile/render
path. Verification of the combined state:

| Check | Result |
|---|---|
| Full suite | **347 tests, OK, exit 0** (91 s), exit status captured directly |
| Protected pins (plan `094827b0…`, H-10 record `b9db3233…`, review bundle `ee345dab…`, C3 config `1e0e30b8…` + sidecar, C4 draft `307e98ab…`, flake evidence `72504661…`, flake-fixed test `e1de8523…`) | **all unchanged** (freeze suite 20/20) |
| Holdout | `prospective/` absent; policy `SEALED`, uses 0 |
| Launch-readiness checker | **20 PASS / 1 BLOCKED / 8 HUMAN** → the only machine blocker left is `c4.not_frozen`, which is deliberately deferred until D2/C-3 and gate 6 |
| Primitive activation | authorized-state pin: v1.1.0 primitives active **only** under the recorded R-3 grant |

No method adopted (H-10/D2 open) · no config frozen · no launch · no
experiment executed · no holdout access.
