# PROPOSED H-10 DECISION RECORD — v3 — for human review and signature

**Status: PROPOSED and UNSIGNED. Not in effect. H-10 remains formally
UNRESOLVED; Campaign 4 launch remains blocked.** Nothing below has been
implemented, frozen, or activated. Agent recommendations are not human
approval; silence, inaction, or the existence of this document does not
constitute approval of D1–D5.

Prepared: 2026-10-11. v3 revises the v2 record per review: adds an explicit
three-outcome decision mapping (D3), multiplicity-family enforcement rules
(D4), and a schema/gate compatibility analysis that **retracts** one v2
proposal (the `ci_lower_min` prohibition) after comparison with the actual
schema and the scientific plan. All quoted plan text verified against
`HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`; all code facts verified
against the actual files and cited by line.

## 0. Scope note on the read-only audit (retained from v2)

A strictly read-only, case-insensitive audit searched the code surface
(live harness source and tests, JSON configuration schemas, the frozen
study backend, `versions/`, root code, documentation) for `holm`,
`holm-bonferroni`, `multiplicity`, `adjusted_p`, `p_adjust`, `family-wise`,
`fwer`, and traced the live call path. Verdict: **confirmed** — no Holm or
adjusted-p computation exists on any live experiment / gate / campaign-end
path; the only executable implementation is the validated reference in the
isolated harness (`stat_validation_h10/simh10.py:67`). The audit
establishes **absence from the searched code surface to the reported
coverage only** (two full-repository greps timed out on data-heavy
directories and were replaced by directory-scoped, include-limited greps
plus `find`-based source inventories; a small residual risk of an
unenumerated stray file remains). It is **not** evidence of statistical
validity on the real dataset.

## D1 — SIM-3 disposition: invoke the plan's reconciliation clause (PROPOSED)

**Proposed decision:** the remedial reading of the SIM-3 criterion is
adopted, with rationale:

1. Exact criterion text: *"disagreement ≤ 1% at α = 0.05; above that, the
   method's decision rule must be reconciled with the gate before
   adoption."* Its stated failure branch mandates
   reconciliation-before-adoption — it is not written as disqualification.
2. Empirical justification: even candidate (a), which uses the CI gate's
   *identical replicates*, exceeded 1% in every SIM-1 cell (2.1–3.5% in
   null cells; 10.1% near-null). The threshold was unattainable for all
   three candidates, so the strict reading would render the predeclared
   battery incapable of resolving H-10 regardless of evidence — a design
   artifact, not a finding against any method.
3. The reconciliation (D3) is a precondition of, not a post-hoc addition
   to, adoption.

**Retained uncertainty:** the remedial interpretation is an
interpretation. A stricter reader could hold that SIM-3 failed outright
and no candidate passes; that reading is recorded as admissible and is
reflected in D5's alternative. H-10 cannot be resolved except by a human
ratifying one reading explicitly (unresolved item **C-3**).

## D2 — Method selection: (b) week-level sign-flip, Holm step-down (PROPOSED)

**Proposed decision:** method (b) is recommended as the sole candidate
surviving SIM-1+SIM-2, **subject to explicit human confirmation; not
activated in the live harness by this record.** Evidence basis:

- **SIM-2 (decisive):** FWER 0.032–0.057 in every attainable cell across
  ρ ∈ {0, 0.3, 0.7}; mixed-config true-H0 rejection 0.0525 at 98.5% H1
  power. (a) reached 0.271 and (c) 0.242 — rejected.
  **Retained uncertainty (finite-sample criterion):** the predeclared
  criterion is *"FWER not significantly above 0.05 (one-sided, exact
  binomial)"*; the worst (b) cell (113/2,000) gives exact p = 0.101 —
  passes as written, but at N=2,000 a true FWER of ~0.055–0.06 would often
  go undetected. The supportable claim is **"no significant excess FWER was
  detected under the tested synthetic conditions," not proof that
  FWER ≤ 0.05.**
- **SIM-3 disagreement rates (documented per clause):** (b) 1.4–2.8%
  across SIM-1 null cells, 8.7% in the near-null power cell
  (δ = −0.01), ~2.0–2.25% in SIM-2 m=1 — lowest of every candidate in
  every cell; (a) 2.1–3.5% / 10.1%; (c) 2.1–3.3% / 10.5%.
- **Retained uncertainty (week-level exchangeability):** (b) rests on
  symmetry of week-level paired contributions about 0; no randomization
  basis exists (arms are deterministic configurations). The synthetic
  cells stressing this (skewed sizes/rates 0.043; regime small-n 0.043;
  ρ ∈ {0, 0.5, 0.9}: 0.050/0.060/0.054) showed no anti-conservative
  distortion. **Week-level exchangeability remains unverified on the real
  dataset**; real frames (~150 weeks, 61k rows) were not simulated; power
  evidence is light (two probes).
- **Retained uncertainty (synthetic DGP):** a falsification battery under
  predeclared plausible DGPs, **not** establishment of real-data validity;
  proxy frames; custom fast path (11/11 self-tests + bit-identical backend
  equivalence mitigate, not eliminate, residual bug risk).

## D3 — Three-outcome decision mapping and gate/schema compatibility

### D3.1 Proposed mapping for all three outcomes (compared against the plan)

**ROBUST.** *Definition:* every predeclared primary condition passes its
**point + CI pair** — the per-primitive predeclared practical-significance
margin (`primary_metric_min_delta`, margins declared in the primitive
definition and copied into each spec; the −0.01 study-consistency margin
remains **provisional** per H-1) **and** its uncertainty requirement
(`ci_lower_min`) — for **every required regime/cell**: regime cells
(above/below SMA200, 2 per `regime_split_analysis` experiment), horizon
rungs (1/2/3 sessions, 3 per experiment), purge rungs (+0/+5/+10, 3 per
experiment), complexity primary rung (1 per experiment); with **all six
gates PASS** (unit, data_integrity, leakage, walk_forward, robustness,
evaluation). Per the plan, IUT governs the pass direction — *"no
multiplicity correction is applied to the pass direction — every member
test must independently pass its own point + CI condition"* — and only
ROBUST can satisfy the evaluation gate. **A nonsignificant adjusted
p-value is not evidence of robustness:** Holm governs refutation claims
only and can never upgrade a member to ROBUST.

**REFUTED.** *Definition:* a predeclared primary condition refuted in the
**predeclared direction** (H1: degradation vs reference, δ = AUC(candidate)
− AUC(reference) < 0) under the applicable **Holm-adjusted sign-flip
decision** (familywise α = 0.05) over the **complete predeclared family**,
with the campaign-end multiplicity procedure completed and its append-only
record written. Per the plan's provisional-to-formal firewall, adjudication
may record only a *provisional* signal (provisional-REFUTED if the
unadjusted CI upper < 0, `formal_refutation: false`); **the bare label
`REFUTED` must not appear anywhere before the campaign-end multiplicity
record assigns it via the Holm-adjusted decision.** If the campaign
terminates early, the multiplicity pass still runs as a mandatory
finalization step on the archived ledger; if it can never run, every
provisional signal defaults to INCONCLUSIVE (fail-closed) and no formal
refutation exists.

**INCONCLUSIVE.** *Definition:* neither ROBUST nor formally REFUTED is
established. Includes, per existing rules: under-powered / under-sized /
wide-CI outcomes (H-8: consumes its execution slot, fails the evaluation
gate, no automatic reruns, no threshold relaxation, never upgraded to a
pass nor recorded as a refutation); **failed or unavailable required
tests** (counted per the D4 counting rule); **unresolved critical
lineage** (C4 stop condition `point_in_time_contamination_detected` →
STOP for human data-lineage review); **infeasible multiplicity
configuration** (H-10b fail-closed: freeze blocked; such signals can never
become formal refutations); and **incomplete campaign-end adjudication**
(see firewall above).

*Comparison result:* the three definitions above are consistent with the
plan's exact definitions (ROBUST/REFUTED/INCONCLUSIVE at plan L75–87;
INCONCLUSIVE handling H-8 at L80–84; IUT/Holm separation at L89–101; the
provisional-to-formal firewall at L117–146). The INCONCLUSIVE extensions
(lineage, infeasible config, incomplete adjudication) align with existing
C4-draft stop conditions and H-10b, adding no new statistical criterion.
No existing margin, directionality, required cell, or gate condition is
replaced or weakened.

### D3.2 The CI's three distinct roles (clarity, not change)

1. **ROBUST uncertainty criterion** — `ci_lower_min` as the CI half of the
   mandatory point+CI pass pair (opt-in per recipe; default −inf =
   unbounded).
2. **Provisional refutation signal** — unadjusted CI upper < 0 produces
   only a provisional marker at adjudication (predeclared protocol
   machinery).
3. **Reported effect-size summary** — the percentile CI is reported
   alongside every decision and is **descriptive in that role: exclusion
   of zero is not, by itself, a formal decision rule**; a formal REFUTED
   label requires campaign-end Holm adjudication.

Roles 1 and 2 are predeclared protocol components and are **not** altered
by the descriptive labeling of role 3.

### D3.3 Schema and gate compatibility — RETRACTION of the v2 prohibition

v2 proposed schema-rejecting `ci_lower_min` pinned above −inf for C4
recipes. **Verified against the actual files, this proposal is withdrawn:**

1. **It conflicts with the plan.** *"Point-estimate-only pass conditions
   are forbidden everywhere in this plan: every pass condition pairs a
   point-estimate threshold with its CI requirement"* (L88–89).
   Prohibiting the CI half would force the ROBUST pass condition to be
   point-estimate-only — a direct violation, and a weakening of the
   uncertainty standard, not a strengthening.
2. **It would break an existing reviewed recipe.** The recipe library pins
   `ci_lower_min: -0.01` (`spec_recipes.py:184`,
   `feature_arm_nested_ablation`, a non-inferiority floor: *"Arm B must not
   lose discrimination versus arm A"*). The prohibition would either
   invalidate that reviewed recipe or silently change its pass condition.
3. **Actual schema facts** (all in `recipe_harness.py`): `ci_lower_min` is
   an allowed criterion key (L65) with limits (−1.0, 1.0) (L57),
   validated only when present (L115–121), defaulting to −inf in
   `decision_criteria_pass` (L157), whose checks are
   `delta_at_least_min_delta`, `ci_lower_at_least_floor`,
   `folds_sufficient` plus optional brier/ece margins (L158–164). The
   evaluation gate additionally requires `decision_criteria_passed`,
   `primary.delta ≥ min_delta`, and release metadata
   (`experiment_adapter.py` ~L950–960).

**Minimal proposed resolution (for separate approval):** **no schema
change and no gate change.** The six gate names, all `CONFIG_LIMITS`, the
brier/ece margins, and every existing criterion remain byte-identical.
`primary_metric_min_delta` is retained and explicitly labeled a
**practical-significance filter, not an error-controlled hypothesis test**.
The only evaluation-path *addition* is the plan's own v1.1.0 machinery: the
campaign-end multiplicity record, which supplies the formal
REFUTED/not-REFUTED status. Implementation adds (a) a fixture test that
no CI criterion can emit a formal `REFUTED` label (structurally guaranteed
by the firewall) and (b) explicit CI-role labeling in the campaign-end
record. Unrelated campaigns and recipes are untouched: nothing about the
existing recipe, its −0.01 floor, or its gate inputs changes.

## D4 — Multiplicity-family enforcement (PROPOSED)

**Families and membership (as frozen in the plan, L102–118):** the Regime
family (2 tests per `regime_split_analysis` experiment: above/below
SMA200), Horizon family (3 per `target_horizon_robustness`: 1/2/3
sessions), Purge family (3 per `purge_sensitivity_probe`: +0/+5/+10), and
Complexity family (1 per `complexity_reduction_check`). *"Family
membership rules are frozen here before proposal generation and may not be
broadened, narrowed, or redefined after results exist."* Campaign 1–3
tests are never pooled in.

**Proposed enforcement rules (item C-2 below is new and needs human
approval):**

1. **Freeze membership before experiment generation**, per family, from
   the declared primitive executions; write the member list into the
   frozen config (or its declared derivation rule) at freeze time.
2. **Counting rule (proposed):** every predeclared member counts toward
   family size m regardless of outcome. A member whose test fails, is
   unavailable, or produces no p-value receives **p = 1.0** in the
   campaign-end record (it can never reject; Holm thresholds for other
   members are unaffected). Members with inconclusive-but-computed results
   keep their actual p-values. Family size m is **never** recomputed,
   truncated, or redefined after results exist.
3. **Granularity enforcement:** with **M = 1,000**, `M + 1 = 1,001 ≥ 20·m`
   ⇒ **m ≤ 50** (floor(1001/20) = 50), matching H-10b's exact bound
   (*"B=1000 for m ≤ 50"*). C4-draft consistency (verified): with
   `max_per_direction: 12` and `max_total_executions: 30`, family maxima
   are regime 2×12 = 24, horizon 3×12 = 36, purge 3×12 = 36, complexity
   1×12 = 12 — **all ≤ 50, feasible at M = 1,000.** The unbound
   contingency (no direction cap, m = 90, per SIM-4) would require
   M ≥ 1,799 — outside the grid → infeasible → fail closed.
4. **Fail-closed:** an oversized or infeasible family **blocks freeze**
   (H-10b freeze-time test) and, post-hoc, such signals can never become
   formal refutations (they end INCONCLUSIVE). **No silent family
   truncation, no omitted tests, no M increase, and no membership
   redefinition after results exist.**
5. **Change control:** any change to M or to the m ≤ 50 cap requires a
   **separately reviewed and approved configuration revision** (new config
   SHA-256 pin at freeze time); it may never be applied mid-campaign.

**Granularity ≠ validity ≠ power (explicit):** `M + 1 ≥ 20·m` establishes
only that discrete p-values can attain Holm's first threshold. SIM-2
documented the mechanical counterpart: floor-blocked cells have FWER
exactly 0.000 — no rejection is representable. As the plan states,
*"Resolution ≠ validity ≠ power."*

## D5 — Storage and effect (PROPOSED)

This record takes effect only when **signed by the human and stored** at
the designated state location; the (future) p-value gate test reads its
presence and refuses adjusted p-values without it (fail-closed). Until
then **Campaign 4 launch remains blocked**. Recording D1–D5 requires an
explicit signed act.

## Scientific safeguards (consolidated, retained from v2 + additions)

- SIM-3's remedial interpretation is proposed and requires explicit human
  ratification (C-3).
- SIM-2 supports only "no significant excess FWER detected under the
  tested synthetic conditions"; it does not prove FWER ≤ 0.05.
- Week-level exchangeability remains unverified on the real dataset;
  synthetic validation does not establish real-data validity.
- The existing target definition, practical-significance margins
  (provisional per H-1), leakage controls, standard purge, required
  regimes/cells and rungs, outcome-blindness closed inputs, bias-governor
  floors, sealed holdout (SEALED, uses = 0, `prospective/` never opened),
  duplicate layers, and all fail-closed rules are **preserved unchanged**.
- **No profitability claims:** results remain discrimination-only; *"no
  cost or trading simulation is claimed"*; backtest remains NOT_RUN.

## Exact changes required for separate approval (NOT applied)

1. **New harness module (v1.1.0) — port, not write-from-scratch:** port
   the validated reference implementation of the week-level sign-flip
   statistic and deterministic Holm step-down from the isolated harness
   (`stat_validation_h10/simh10.py`, self-test- and equivalence-verified)
   into the live production path, with the M knob (default 1000) and
   declared family membership. The isolation distinction is preserved:
   `stat_validation_h10/` stays isolated and is never imported by
   production; production contains its own reviewed implementation,
   verified by fixture equivalence against the reference. Add the
   fail-closed gate test (adjusted p-values refused unless the signed D5
   record exists). Write unadjusted p, Holm-adjusted p, the descriptive
   CI, and the CI-role label side by side in the campaign-end record.
2. **No schema or gate change** (revising v2 item 2): instead, the two
   fixture/labeling additions specified in D3.3 — no CI criterion can
   emit a formal `REFUTED` label; CI roles labeled in the record.
3. **C4 config freeze (separate freeze approval):** pin `n_boot ≥ 1000`
   and `M = 1000`; freeze the four families' membership derivation and
   verify each declared family's m ≤ 50; keep all criteria unchanged.
4. **Tests:** H-10b feasibility test on declared families; Holm fixtures
   (reference-vs-port equivalence, tie handling, p=1.0 unavailable-member
   rule); provisional-to-formal firewall test; safety-gate preservation
   suite (six gate names and thresholds unchanged).
5. **Store this signed record** at the state location the human designates.

## Unresolved contradictions requiring human decisions

- **C-1:** the retraction of the v2 `ci_lower_min` prohibition (D3.3) —
  ratify "no schema change; CI remains the mandatory uncertainty half of
   the ROBUST pass pair" over the v2 proposal.
- **C-2:** the D4 counting rule (unavailable members count toward m and
  receive p = 1.0) is a **new predeclared rule** not present in the plan;
  it must be explicitly approved (or an alternative chosen) before
  freeze, because family membership semantics may not be defined after
  results exist.
- **C-3:** D1's remedial interpretation of SIM-3 requires explicit
  ratification; the strict reading (none passes → H-10 stays UNRESOLVED)
  remains admissible.
- **C-4:** confirm that "CI is descriptive" (D3.2 role 3) does not remove
  the plan's predeclared provisional-signal machinery (roles 1 and 2).

## Signature block (to be completed by the human reviewer)

- D1 (remedial SIM-3 reading): APPROVED / REJECTED — ____________ date ______
- D2 (adopt method (b), subject to D3/D4): APPROVED / REJECTED — ____________ date ______
- D3 (three-outcome mapping + no-schema-change resolution, C-1/C-4): APPROVED / REJECTED — ____________ date ______
- D4 (M=1000, m≤50, counting rule C-2, fail-closed): APPROVED / REJECTED — ____________ date ______
- D5 (storage location): ______________________

No plan edit, live-code change, schema change, campaign-config change,
freeze, simulation run, holdout access, or Campaign 4 launch has occurred
or is authorized by this document.
