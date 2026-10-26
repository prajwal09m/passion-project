# PRIMITIVE ACTIVATION GRANT (R-3) — 2026-10-12

**Status: OWNER GRANT RECORDED FOR PRIMITIVE ACTIVATION ONLY. NO METHOD IS
ADOPTED, NOTHING IS FROZEN, NOTHING IS LAUNCHED.**

## 1. Grant

Provenance: the human owner's answer in this project's workflow thread on
2026-10-12 to the question "The five v1.1.0 primitives are still dormant
(`executable=False`)… How should this proceed?", selecting
**"Grant it now, as parallel work"**:

> Implement the five primitives, the 1.1.0 run modes, frozen
> ladders/margins, and the per-primitive tests while the review is pending.
> Does not adopt any method, does not freeze, does not launch. Shortens the
> post-review critical path by the largest single chunk.

This supersedes only the exclusion recorded in
`HARNESS_V1_1_0_GATE3_AUTHORIZATION_RECORD_2026_10_12.md` §3 that listed
primitive activation as "NOT authorized"; every other boundary in that file
stands.

## 2. Governing constraints carried into the implementation

From the pinned plan (`094827b0…`), unchanged:

- **Freeze-before-generation:** every ladder, primary comparison, margin,
  sample floor, and multiplicity rule is frozen into the primitive
  definitions **before** any proposal is generated. The spec-fidelity test
  enforces byte-identical transfer from definition to generated spec.
- **Margin provenance (H-1):** `-0.01` is a **PROVISIONAL** study-consistency
  margin carried from the existing gates' `ci_lower_min`. It is not
  statistically validated and no cost model exists. Every use is marked
  PROVISIONAL; no point-estimate-only pass exists anywhere.
- **Three-valued model:** ROBUST / REFUTED / INCONCLUSIVE. INCONCLUSIVE
  consumes its execution slot, fails the evaluation gate, cannot promote, and
  is never upgraded to a pass or recorded as a refutation.
- **IUT vs Holm:** IUT governs ROBUST (every member test must independently
  pass its own point + CI condition); Holm governs formal refutation claims
  only. They never substitute for each other.
- **Firewall:** formal `REFUTED` is assigned only by the campaign-end
  multiplicity record; while H-10 is open the p-value gate refuses, so no
  experiment can produce a formal refutation at all.
- **H-10b floors:** `n_boot ≥ 1000` and `n_boot + 1 ≥ 20·m` for every family.
- **Non-goals:** no gate/threshold/bias-floor/duplicate-layer/
  outcome-blindness/approval-policy change; no new data source; no network;
  no LLM; v1.0.0 behavior byte-identical when the 1.1.0 selector is absent.

## 3. Rulings this work depends on

- **R-4** (recorded in `OWNER_AUTHORIZATION_TO_PROCEED_2026_10_12.md` §7):
  a run whose only defects are disclosed Tier-2 columns is an **audit FAIL,
  no partial pass**, never contamination.
- **R-1:** census expected-column set is **100** features.
- **R-2:** the frozen stop set is **14 original + 2 new = 16**.

## 4. Boundary

Activating a primitive makes its *measurement direction* reachable by the
generator and compiler. It does not make any result admissible: every gate,
floor, firewall, multiplicity rule, and stop condition applies exactly as
before, and the campaign still cannot launch until the independent review
closes D2. No experiment was executed to validate these primitives in this
step beyond the synthetic fixtures the test suite uses.
