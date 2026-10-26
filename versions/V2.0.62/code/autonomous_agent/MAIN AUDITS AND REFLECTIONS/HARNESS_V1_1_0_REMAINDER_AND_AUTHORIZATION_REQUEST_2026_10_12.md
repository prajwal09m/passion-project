# Harness v1.1.0 — remainder inventory and the minimal authorization request

Prepared 2026-10-12 by the coding agent. **Nothing in this file is
authorized, implemented, or activated.** It records (A) exactly what
remains after the one completed item, and (B) the smallest request that
would let the independent part start while the external review is pending.

## A. Gate status (decision sheet, strict order)

| Gate | Requirement | Status today |
|---|---|---|
| 1 | Human resolves D1–D5 / C-1…C-4 and signs the record | **PARTIAL** — D1, D3, D4, D5, C-1, C-2, C-4 recorded in `H10_OWNER_AUTHORIZATION_RECORD_2026_10_11.md` §3; **D2 DEFERRED, C-3 PENDING** (need the independent review) |
| 2 | Signed record stored + integrity pin written/verified | Record `b9db3233…` verified today; **remains unsigned by design** — the owner waived the signature *form* for the administrative items only |
| 3 | **Separate human authorization to implement harness v1.1.0** | **MISSING** — explicitly withheld by the same record §3: *"separate explicit human authorization still required; the owner's no-signature instruction explicitly did not grant it"* |
| 4 | v1.1.0 implemented + tests pass | **NOT STARTED** (see §B) |
| 5 | Governance-suite flake investigated and dispositioned | **DONE 2026-10-11** — test-only fix, 30/30 targeted, 10/10 consecutive full-suite green, evidence `…/GOVERNANCE_SUITE_FLAKE_EVIDENCE_2026_10_11.md` (`72504661…`) |
| 6 | C4 config amended, reviewed, separately frozen | **NOT STARTED** — draft untouched (`307e98ab…`), reconciliation in `CAMPAIGN_4_CONFIG_RECONCILIATION_2026_10_12.md` |
| 7 | Holdout/config/stop/launch gates re-verified | Ran today as a baseline: pins OK, holdout absent, suite 235/235 exit 0 |
| 8 | Explicit human Campaign 4 launch authorization | **ABSENT** |

So of the eight gates: **one closed (5), one partly closed (1), six open.**
The only gate whose closure depends on neither the review nor a freeze is
**gate 3**.

## B. Exactly what remains after the completed flake fix

Verified today by scanning all project source: **none** of the v1.1.0
components exist in the harness. `holm` appears in 0 harness files (only
in the plan, the H-10 documents, and the simulation code); `census` appears
only in the plan; `firewall` only in plan/decision documents; the five
`harness_min_version="1.1.0"` primitives are all still `executable=False`;
and `stop_conditions` is read by **no** Python file in the repository.

### B1. Code touchpoints (plan checklist — all six still unchecked)

1. `recipe_harness.py` — five run modes behind a `harness_version == "1.1.0"`
   selector; v1.0.0 behavior byte-identical when absent.
2. `proposal_layer/primitives.py` — flip five `executable` flags to `True`;
   write frozen ladders/margins/floors/multiplicity families into the
   primitive definitions; bump library version to 1.1.0.
3. `proposal_layer/validator.py` — accept 1.1.0 specs (no gate changes).
4. `continuous_loop.py` — wire `point_in_time_contamination_detected` **and**
   the UNVERIFIABLE-lineage stop, both fail-closed, only after the lineage
   inventory reports verifiable lineage.
5. `experiments/*` — only if a primitive needs a new file in the allowed set
   (minimal, declared delta).
6. Tests (plan's required list, all absent today):
   - spec-fidelity test (acceptance criteria byte-identical to definitions)
   - three-valued evaluator tests per primitive, incl. **underpowered
     wide-CI → INCONCLUSIVE** and under-sized regime cell → INCONCLUSIVE
   - `test_recipe_harness.py` happy-path + refutation-path per primitive
   - horizon test (label rebuild, exit-date recompute, maturity purge)
   - PIT tri-state test (UNVERIFIABLE → never PASS; CONFIRMED → stop fires)
   - ladder-enum test (frozen enums, no runtime computation)
   - Holm test (adjustment within family; unadjusted retained)
   - family-membership tests (C4 pooling only; C1–C3 excluded; families read
     from frozen config, not results)
   - adjustment test incl. unadjusted-refutation-that-fails-adjustment →
     INCONCLUSIVE
   - unadjusted-retention test (raw delta/CI/unadjusted p/adjusted p all in
     the campaign-end record)
   - **provisional-vs-formal firewall test** (no standalone `REFUTED` before
     the campaign-end record; no record at all → everything INCONCLUSIVE)
   - Holm-outcome fixture test (hand-computed step-down, both survivors and
     non-survivors)
   - mirrored/related-experiment tests (`related_primitive` linkage, claim-
     prohibition lints ×2, count-once rule)
   - **p-value-method gate test** (H-10 unresolved → adjusted p computation
     fails closed, no silent fallback)
   - **H-10b freeze-time feasibility test** (`n_boot + 1 ≥ 20·m`; infeasible
     blocks freeze; infeasible signals can never become formal refutations)
   - **census-manifest tests (H-11)** (101 columns, frozen tolerances,
     tolerance never derived from observed mismatches, UNVERIFIABLE never
     PASS, structural checks never upgrade a value verdict, missing entry
     blocks audit PASS)
   - **safety-gate preservation suite** (five gates' names/thresholds, holdout
     seal, five duplicate layers, bias floors, outcome blindness, approval
     policy, the full original stop list, v1.0.0 byte-identical)
   - `test_proposal_layer.py` new directions + duplicate-layer refusals
   - `test_stage5_readiness_safety_contract.py` fail-closed stops, seal,
     back-compat
   - a test asserting **no** change to the five existing gate names/thresholds
   - **not in the plan but required by finding B of the reconciliation:**
     a config↔code stop-correspondence test (today the declared stop list is
     enforced by nothing)

### B2. Freeze-time work that is neither code nor freeze (still pending)

- Census execution for the 90 untested feature columns + 9 remaining market
  columns (H-11 resolved as *coverage*, execution pending); Tier-2
  (`rsi14`, `atr_pct`, `zone_width_pct`) stays UNVERIFIABLE forever.
- Residual ruling: how the audit's three-state outcome treats a run whose
  only defects are disclosed Tier-2 columns — **must be decided and recorded
  before the primitive is implemented**, never inferred from results.
- Freeze checks: SIM-4/H-10b feasibility, census-manifest completeness,
  count-once evidence rule.

## C. Smallest necessary authorization request

**Not granted. Not assumed. Prepared for one sentence of approval.**

> I authorize implementation of harness v1.1.0 per the pinned plan
> `HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`
> (`094827b0…8eb4e`), **with the p-value method left fail-closed behind the
> unresolved H-10 gate**: Holm machinery, family bookkeeping, the
> campaign-end multiplicity record, the provisional→formal firewall,
> the C-2 missing-member rule, both new fail-closed stops plus a
> config↔code stop-correspondence test, the census manifest and its tests,
> freeze-integrity/protected-state preservation tests, and the safety-gate
> preservation suite. No method (b) is adopted by this authorization; no
> gate, threshold, bias floor, duplicate layer, approval policy, or holdout
> control changes; nothing is frozen or launched.

Why this is the *smallest* useful request rather than the whole plan:

- **It presupposes no statistical decision.** Holm adjusts p-values from
  whatever method D2 later approves; while H-10 is open the gate test must
  *refuse* to compute adjusted p-values (the plan's own design). Building
  the machinery therefore cannot smuggle in method (b).
- **It is the critical path.** Gate 3 is the only gate that does not wait on
  the review (gate 1/2) or on the freeze (gate 6) or on launch (gate 8).
  Doing it now converts review→launch from *implement + test + freeze +
  launch* into *freeze + launch*.
- **It is falsifiable.** If D2 later rejects method (b), the only
  method-specific line — the p-value computation — is unimplemented and
  there is nothing to unwind; the firewall, stops, census, and preservation
  tests remain valid regardless.

**Deliberately excluded** (would need a separate, explicit grant): flipping
the five primitives to `executable=True` and activating the 1.1.0 run modes
in `recipe_harness.py`, because that makes the new measurement directions
reachable and the plan ties their margins to PROVISIONAL (H-1) values;
freezing the C4 config; launching.

If you prefer one authorization covering the full plan checklist in §B1
including the primitive activation, say so explicitly and it will be
recorded as such — the difference is noted, not hidden.

## D. What happens on approval

1. Record the authorization as a dated, provenanced file next to this one
   (same pattern as the 2026-10-11 record; no signature invented).
2. Implement in plan order with tests written alongside; run the full suite
   after each component; report every run's exit status.
3. No frozen protocol value changes; no threshold touched; holdout never
   opened; Campaign 3 artifacts untouched.
4. Stop and report if any implementation step would require changing a
   gate, threshold, stop semantics, or the H-10 fail-closed gate.

## E. Implementation status — 2026-10-12 (owner granted §C option 1)

Full detail: `HARNESS_V1_1_0_IMPLEMENTATION_REPORT_2026_10_12.md`.
Suite **311 tests, OK, exit 0** (was 235); protected pins, holdout, and
Campaign 3 state unchanged.

| §B item | Status |
|---|---|
| B1.1 `recipe_harness.py` 1.1.0 run modes | **NOT DONE — outside the grant** |
| B1.2 primitives → `executable=True` + frozen ladders/families | **NOT DONE — outside the grant** |
| B1.3 validator accepts 1.1.0 specs | not required yet (follows B1.2) |
| B1.4 both stops wired (fail-closed) | **DONE** |
| B1.5 `experiments/*` allowed-set delta | not required yet |
| Holm / family-membership / adjustment / unadjusted-retention tests | **DONE** (36) |
| Provisional-vs-formal firewall test | **DONE** (module + loop-level) |
| p-value-method gate test (fail-closed, no fallback) | **DONE** |
| H-10b feasibility logic + family bounds | **DONE** (module-level; the freeze-time *config* check runs at freeze) |
| Census-manifest tests (H-11 invariants) | **DONE** (20) |
| Config↔code stop-correspondence test | **DONE** (was missing entirely) |
| Freeze-integrity / protected-state preservation tests | **DONE** (20) |
| B1 per-primitive three-valued evaluator / spec-fidelity / horizon / PIT-tri-state / ladder-enum tests | **NOT DONE — follow primitive activation** |
| Safety-gate preservation suite (gates, seal, duplicate layers, floors) | **PARTIAL** — the surface is asserted in `test_freeze_integrity.py`; the byte-identical v1.0.0 back-compat suite lands with the 1.1.0 selector |
| B2 census execution + Tier-2 residual ruling | **NOT DONE — freeze-time, needs the Tier-2 ruling** |
