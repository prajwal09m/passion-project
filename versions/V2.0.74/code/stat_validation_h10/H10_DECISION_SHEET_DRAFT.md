# DRAFT — H-10 FINAL HUMAN DECISION SHEET

**Type: DRAFT decision sheet for human completion. Not an approval, not a
signature, not in effect. H-10 remains UNRESOLVED; Campaign 4 remains
BLOCKED until every decision below is explicitly recorded.**

Prepared: 2026-10-11. Authoritative sources verified by direct read:
- Decision record: `stat_validation_h10/H10_DECISION_RECORD_PROPOSED.md`
  (v3, PROPOSED/UNSIGNED), SHA-256 `75bb6c03f1be38da…` (re-verified at
  drafting time).
- Protocol: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`,
  SHA-256 `094827b0e9a5f1c1…` (re-verified; clauses quoted verbatim below).
- Live enforcement: `autonomous_agent/experiment_adapter.py`,
  `recipe_harness.py`, `continuous_loop.py`, `proposal_layer/*` (read-only).

**Disclosed discrepancies (not silently resolved):** (1) the plan refers to
"five gates"; the live adapter enforces **six** (`unit, data_integrity,
leakage, walk_forward, robustness, evaluation`,
`experiment_adapter.py:975`) — this sheet references the actual six.
(2) The C-2 counting rule is **new** and appears nowhere in the plan; it
cannot count as predeclared until chosen below.

---

## D1 — SIM-3 interpretation

**Question:** When the predeclared SIM-3 criterion failed for *all three
candidates*, does the protocol's reconciliation clause permit adoption
after gate reconciliation (remedial), or does the failure disqualify every
candidate (strict)?

**Choices:** (a) Remedial reading. (b) Strict reading.

**Evidence & clause:** Plan SIM-3 clause, verbatim: *"Pass criterion:
disagreement ≤ 1% at α = 0.05; **above that, the method's decision rule
must be reconciled with the gate before adoption**, else the gates and the
multiplicity record can contradict each other."* Measured: every candidate
exceeded 1% — (a) 2.1–3.5% (null cells) / 10.1% (near-null), (b)
1.4–2.8% / 8.7%, (c) 2.1–3.3% / 10.5% — even (a), which shares the CI
gate's identical replicates. The ≤1% threshold was not met by any
candidate in any tested cell (measured rates 1.4–10.5%), so under the
strict reading no candidate could ever pass this battery as executed.

**Consequences:** (a) → D2/D3 become adoptable with reconciliation as a
precondition; the record's remedial reading takes effect only by your
explicit ratification here. (b) → no candidate can pass this battery;
H-10 stays UNRESOLVED and C4 stays blocked under the predeclared fail-closed
rule, potentially permanently (a design artifact, not evidence against
method (b)).

**Recommendation (agent recommendation, not approval):** (a) Remedial.

**Human decision:** APPROVE (a) / APPROVE (b) / DEFER —
Rationale: ______________________  Date: ______  Conditions: ____________

## D2 — Statistical method

**Question:** Adopt or reject the week-level sign-flip test with Holm
step-down (familywise α = 0.05) at M = 1,000 as Campaign 4's family-wise
method?

**Choices:** (a) Adopt (subject to D3/D4). (b) Reject — H-10 stays
UNRESOLVED unless another valid method is later approved (none currently
exists; (a) and (c) were rejected under the predeclared SIM-2 criterion —
significantly anti-conservative in every tested family configuration, FWER
up to 0.271/0.242; both had formally passed SIM-1's per-cell criterion
with a consistent mild liberality).

**Evidence & clause:** Plan decision rule (verbatim): *"a candidate is
adoptable only if it passes SIM-1 (no liberal cell), SIM-2, SIM-3, and
SIM-4. If exactly one passes, it is adopted subject to explicit human
confirmation…"*. SIM-2 (N=2,000/config): sign-flip FWER 0.032–0.057 in
every attainable cell; worst cell exact one-sided binomial p = 0.101 under
the predeclared criterion *"FWER not significantly above 0.05"*; sign
proportion reached 0.271 and normal-z 0.242 (rejected); mixed-config true-H0
rejection 0.0525 at 98.5% H1 power.

**Mandatory disclosures (not waivers):**
- Synthetic tests **did not establish validity on the real dataset**; they
  are a falsification battery under predeclared synthetic DGPs.
- **Week-level exchangeability is unverified on real data** (arms are
  deterministic configurations; no randomization basis). Adopting (b)
  accepts this assumption at the owner's risk.
- SIM-2 found **no statistically significant excess FWER under its
  predeclared criterion; it did not prove FWER ≤ 0.05** (at N=2,000 a true
  FWER ≈ 0.055–0.06 would often pass undetected).
- Power evidence is light (two probes); simulated frames were proxies.

**Consequences:** (a) → family-wise claims rest on the disclosed
assumption, mitigated by fail-closed design; implementation may begin only
after separate authorization. (b) → C4 blocked; no default method may be
substituted.

**Recommendation:** (a) Adopt, with the disclosures written into the
signed record.

**Optional, non-blocking addendum (NOT an existing protocol requirement;
requires its own preregistration before any data inspection if
requested):** a real-data week-symmetry diagnostic on development OOF rows
only (holdout never touched) — preregistering: the exact per-week
paired-contribution statistic, its asymmetry threshold, the data scope,
and its semantics (diagnostic/disclosure only). It can detect gross
asymmetry inconsistent with week-level exchangeability in the development
data; it **cannot establish exchangeability, prove validity, or measure
FWER**. A failed preregistered diagnostic does not auto-block adoption; it
triggers mandatory human re-review before freeze. **Blocking semantics:
none by itself.**

**Human decision:** APPROVE (a) / APPROVE (b) / DEFER —
Rationale: ______________________  Date: ______  Conditions: ____________

## D3 — Gate and outcome reconciliation

**Question:** Approve the three-outcome definitions and CI-role separation
as the binding adjudication semantics for Campaign 4?

**Proposed definitions (plan-verbatim anchors):**
- **ROBUST** — *"every predeclared primary condition passes, including its
  CI requirement. Only ROBUST can satisfy the evaluation gate."* Each
  required cell pairs the predeclared practical-significance margin
  (`primary_metric_min_delta`, margins per primitive definition, −0.01
  study-consistency margin remains provisional per H-1) with its
  uncertainty criterion (`ci_lower_min`); IUT governs the pass direction;
  all **six** live gates must PASS.
- **REFUTED** — formal status only via campaign-end Holm-adjusted
  sign-flip decision over the complete family, in the predeclared
  direction (degradation vs reference). Firewall, plan-verbatim: *"The bare
  three-valued label `REFUTED` must not appear anywhere — ledger rows,
  loop events, stdout, reports, or summaries — until the campaign-end
  multiplicity record exists and assigns it via the Holm-adjusted
  decision."*
- **INCONCLUSIVE** — neither, per H-8, verbatim: *"consumes its authorized
  execution slot, fails the evaluation gate, and cannot promote a
  candidate. No automatic reruns. No threshold relaxation."* Includes
  failed/unavailable tests, unresolved lineage (C4 stop
  `point_in_time_contamination_detected`), infeasible multiplicity
  configuration, and incomplete campaign-end adjudication (provisional
  signals default INCONCLUSIVE if the pass can never run).

**Preserved unchanged:** target definition; practical-significance
margins; required regimes/cells (regime above/below SMA200; horizon
1/2/3 sessions; purge +0/+5/+10; complexity primary rung); uncertainty
criteria; leakage controls; standard purge; outcome-blindness closed
inputs; bias-governor floors; sealed holdout; all fail-closed rules.

**Unresolved conflict identified, not invented away:** the plan's
provisional-REFUTED signal uses the unadjusted percentile CI while formal
REFUTED uses the Holm-adjusted p — these can disagree at 1.4–8.7% near the
boundary; the plan already reconciles this via the provisional-to-formal
firewall (ratify under C-4).

**Implementation status (not yet live):** these adjudication semantics
are documented in the plan but **not yet implemented** in production
(harness v1.1.0 pending); approving D3 establishes them as the binding
specification for that implementation.

**Consequences:** approve → implementation has unambiguous semantics;
reject/defer → implementation cannot start.

**Recommendation:** Approve as written.

**Human decision:** APPROVE / REJECT / DEFER —
Rationale: ______________________  Date: ______  Conditions: ____________

## D4 — Multiplicity and feasibility

**Question:** Approve M = 1,000, m ≤ 50, frozen family membership,
fail-closed feasibility, and the C-2 unavailable-member rule (below)?

**Proposed terms:** families = Regime (2 tests/exp), Horizon (3/exp),
Purge (3/exp), Complexity (1/exp); *"Family membership rules are frozen
here before proposal generation and may not be broadened, narrowed, or
redefined after results exist."* Feasibility inequality (H-10b):
**M + 1 ≥ 20·m** → 1,001 ≥ 20·m → **m ≤ 50** (plan: *"B=1000 for m ≤ 50"*).
C4 maxima under `max_per_direction: 12`: 24/36/36/12 — all feasible. An
oversized or infeasible family blocks freeze; such signals can never become
formal refutations. No silent truncation, omission, M increase, or
post-hoc membership change; any change to M or the cap requires a
separately reviewed and approved configuration revision. (The plan's
literal H-10b test is written on `n_boot`; for the adopted method the
discrete p-value floor is the sign-flip count M, so the freeze test
applies `M + 1 ≥ 20·m` — and `n_boot ≥ 1000` remains separately required
for the CI.)

**Granularity ≠ power ≠ validity:** `M+1 ≥ 20·m` establishes only that
discrete p-values can attain Holm's first threshold (SIM-2's mechanical
zeros: floor-blocked cells have FWER exactly 0 — nothing is representable).

**Human decision:** APPROVE / REJECT / DEFER —
Rationale: ______________________  Date: ______  Conditions: ____________

## C-1 — CI-schema retraction (governed under D3's signature)

**Question:** Ratify the retraction of the v2 proposal to schema-reject
`ci_lower_min` above −inf, keeping "no schema change"?

**Evidence:** Plan, verbatim: *"Point-estimate-only pass conditions are
forbidden everywhere in this plan: every pass condition pairs a
point-estimate threshold with its CI requirement."* Prohibiting the CI
half would violate this and weaken the standard. An existing reviewed
recipe pins `ci_lower_min: -0.01`
(`autonomous_agent/spec_recipes.py:184`, non-inferiority floor) — the
prohibition would invalidate or silently alter it. Precision: *any
present* `ci_lower_min` value is "above −∞" — validation accepts only
numerics in [−1, 1] (`recipe_harness.py:57,115-121`), so −∞ itself cannot
be pinned and the default when the key is absent is −∞ (`:157`); the v2
prohibition would therefore have rejected any pin, including this
reviewed one.

**Choices:** (a) Ratify retraction — no schema change; CI stays the
mandatory uncertainty half of the ROBUST pair. (b) Reinstate the
restriction — requires a **formally approved protocol amendment** to the
point-and-CI rule and re-review of the affected recipe (not a routine
implementation detail).

**Recommendation:** (a).

**Human decision:** RATIFY (a) / REINSTATE (b) / DEFER —
Rationale: ______________________  Date: ______

## C-2 — Unavailable family members (must be chosen before any family is frozen)

**Question:** How does an unavailable/failed/missing member test count at
campaign-end Holm adjudication?

**Option A (per-member conservatism):** an unavailable/failed/missing
member test counts toward m, receives **p = 1.0** in the multiplicity
record — it can never be formally REFUTED, and other members' thresholds
are unchanged — while the rest of the family is adjudicated normally; the
unavailable member's *experiment-level* signal defaults to INCONCLUSIVE
per the firewall.
**Option B (family-level veto):** any unavailable member makes the
**entire family** produce no formal refutation claims at all — every
member ends not-REFUTED/INCONCLUSIVE for the campaign, regardless of
other members' p-values.

**Distinction:** A preserves the family's adjudication and the
auditability of genuine refutations while being conservative exactly
where evidence is missing; B is maximally fail-closed but erases all
refutation claims in the family when any single member is unavailable.
Exclusion of the member is **not** available — it would redefine
membership after results exist (plan: frozen before generation, *"may not
be broadened, narrowed, or redefined after results exist"*). The plan
requires the campaign-end record to list *"every member test, its
unadjusted p-value/CI/delta, its adjusted p-value, and its final
REFUTED/not-REFUTED status"* but is silent on unavailable members —
**both options are new predeclared rules; neither is favored by governing
language or by this audit, and neither is approved.**

**Timing constraint:** the chosen rule must be predeclared **before family
membership is frozen and before any results are observed**.

**Human decision:** OPTION A / OPTION B / DEFER —
Rationale: ______________________  Date: ______

## C-3 — SIM-3 ratification (separate governance act)

**Question:** Do you explicitly ratify adopting method (b) **despite**
SIM-3's ≤1% failure, via the reconciliation clause?

**Why separate from D1 (governing language):** D1 chooses the
*interpretation* of the criterion (whether the remedial branch is
available). The plan separately requires, verbatim: *"it is adopted
subject to explicit human confirmation"* and *"H-10 stays open until that
evidence exists and a human decision is recorded"*, under a fail-closed
rule (*"if none passes, H-10 stays UNRESOLVED and Campaign 4 launch is
blocked"*). Because SIM-3 failed for every candidate, adoption under the
remedial reading cannot be absorbed implicitly by approving D1/D2 — the
plan's fail-closed posture requires the SIM-3 failure to be addressed by
an explicit, separately recorded ratification. Ratifying C-1 does not
resolve C-3, and vice versa: C-1 concerns schema/gate design that stands
under either interpretation; C-3 concerns whether (b) is adoptable at all.

**Consequences:** ratify → D2's adoption is validly recorded; reject →
H-10 stays UNRESOLVED (strict outcome by owner decision).

**Recommendation:** Ratify (consistent with choosing (a) in D1).

**Human decision:** RATIFY / REJECT / DEFER —
Rationale: ______________________  Date: ______

## C-4 — Confidence intervals and provisional signals

**Question:** Ratify the three-role interpretation of the percentile CI?

**Plan-verbatim provisional rule:** *"each refutation test's unadjusted
results are recorded at adjudication as today (three-valued provisional
label: provisional-REFUTED if the unadjusted CI upper < 0, else
provisional-ROBUST/INCONCLUSIVE)"*, with formal status assigned only by
the campaign-end Holm record (firewall quoted under D3).

**Proposed interpretation to ratify:** the CI has exactly three roles —
(1) ROBUST uncertainty criterion (`ci_lower_min` in the point+CI pair);
(2) provisional refutation signal at adjudication (marker only,
`formal_refutation: false`); (3) reported effect-size summary where
*"exclusion of zero is not, by itself, a formal decision rule"*. The word
"descriptive" applies **only to role 3** and does not remove roles 1–2.

**Consequences:** ratify → reporting schema and adjudication code have an
unambiguous spec; reject → interpretation is unresolved and blocks the
D3 implementation spec.

**Recommendation:** Ratify as written.

**Human decision:** RATIFY / REJECT / DEFER —
Rationale: ______________________  Date: ______

## D5 — Record storage and effect

**Question:** Where is the signed H-10 record stored and integrity-pinned,
and what does signing authorize?

**Choices:** (a) Store as `autonomous_agent/state/h10_decision_record_signed.md`
(this record once signed) with a companion bare-hash, single-line pin
`autonomous_agent/state/h10_decision_record_signed.sha256` — verified
compatible with the repository convention (`state/` already holds
`campaign_config.sha256` in exactly that format, and no existing code
enumerates `state/` files, so the added file is inert until the future
fail-closed p-value gate test reads it). (b) Designate another
location/format, specified explicitly at signing.

**Consequences:** (a) → the future gate test verifies presence + integrity
by the same pattern used for the campaign config; (b) → the location must
be recorded in the signed record itself. Either way, **signing H-10
approves the statistical decision record only** — it does not authorize
implementation, configuration freeze, or launch; each is a separate gate
below.

**Recommendation (agent recommendation, not approval):** (a).

**Human decision:** CHOICE (a) / CHOICE (b) / DEFER —
Rationale: ______________________  Date: ______  Conditions: ____________

---

## Signature table (blank — no approvals pre-filled; silence is not consent)

| Item | Decision (APPROVE/REJECT/DEFER or as labeled) | Human rationale | Date | Conditions |
|---|---|---|---|---|
| D1 SIM-3 interpretation | | | | |
| D2 method (b) adoption | | | | |
| D3 outcome mapping + CI roles | | | | |
| D4 multiplicity/feasibility | | | | |
| D5 storage location | | | | |
| C-1 retraction ratification | | | | |
| C-2 unavailable-member rule | | | | |
| C-3 SIM-3 ratification | | | | |
| C-4 CI three-role ratification | | | | |

## Remaining approval gates (strict order)

1. Human resolves D1–D5 and C-1…C-4 (this sheet) and signs the record.
2. Signed record stored at the designated path; integrity pin written and
   verified. *(Human approval)*
3. Separate human authorization to implement harness v1.1.0 per the
   signed record. *(Human authorization)*
4. v1.1.0 implemented (ported sign-flip + Holm, multiplicity record,
   firewall, M knob, H-10b freeze test, p-value fail-closed gate,
   point-in-time stop wiring, dual-comparison recording); tests pass.
   *(Authorized implementation + validation)*
5. The unresolved governance-suite test failure (1 failure in 10 runs,
   identity not captured) is investigated and dispositioned. *(Validation)*
6. C4 configuration amended (n_boot/M pins, families, C-2 rule, stops),
   reviewed, and separately frozen with fresh SHA pin + fingerprint.
   *(Human freeze approval)*
7. Holdout isolation, config hashes, stop conditions, and all launch
   gates re-verified. *(Validation)*
8. Explicit human Campaign 4 launch authorization. *(Launch authorization)*

## Boundaries observed in preparing this sheet

No signature created; no plan, code, schema, config, or existing decision
record modified; no simulation or experiment run; holdout untouched; no
freeze or launch. H-10 UNRESOLVED; Campaign 4 BLOCKED.
