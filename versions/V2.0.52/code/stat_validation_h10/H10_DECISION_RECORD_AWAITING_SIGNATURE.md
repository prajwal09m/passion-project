# H-10 DECISION RECORD — AWAITING SIGNATURE

**Status: human-confirmed choices recorded; NOT SIGNED; NOT IN EFFECT.
H-10 remains UNRESOLVED until this record is signed and stored per D5(a).
Campaign 4 remains BLOCKED. C-3 is PENDING by design.**

Prepared: 2026-10-11. Provenance: the choices below were confirmed by the
human project owner on 2026-10-11 through a structured decision
interaction against the audited draft sheet
`stat_validation_h10/H10_DECISION_SHEET_DRAFT.md`
(SHA-256 `5a62c9d08e642c7e4d4c3e56e34c74d737ddbe0298efc2dc340e148a73257159`,
audit verdict READY FOR HUMAN DECISIONS). This file **records** those
confirmed choices; it does not sign, approve, or ratify anything — the
signature block below is intentionally blank and belongs to the human
owner alone. No agent signature, date, or approval may ever appear here.

## Recorded decisions

**D1 — SIM-3 interpretation: CHOSEN (a) REMEDIAL, with the SIM-3
failure explicitly retained.** The ≤1% disagreement threshold was not met
by any candidate in any tested cell (measured 1.4–10.5%, including the
CI-aligned candidate (a) at 2.1–3.5% null / 10.1% near-null); adoption
under this reading remains conditional on explicit ratification (C-3) and
on an approved method (D2). **The SIM-3 failure stands in the record and
is not erased by this interpretation.**

**D2 — Statistical method: DEFERRED.** Method (b) week-level sign-flip +
Holm is **not adopted and not validated**. Simulations favor it under the
tested synthetic conditions (SIM-2 FWER 0.032–0.0565 over 51 attainable
cells; worst cell 113/2,000, exact one-sided binomial p = 0.1014; mixed
true-H0 rejection 0.0525 at 98.5% H1 power; no significant excess
**detected** — explicitly not proof of FWER ≤ 0.05), but week-level
arm-label exchangeability is unestablished on real data and shared-training
dependence was not simulated. **Closure routes (in order of the owner's
stated preference): independent external statistical review of the
prepared review packet; or an owner-authorized preregistered diagnostic
on development OOF rows only (diagnostic cannot prove exchangeability);
or rejection.** D2 is the sole unresolved scientific-method decision.

**D3 — Outcome semantics: APPROVED as the binding specification.**
ROBUST = every required cell's point + CI pair passes under IUT with all
**six** live gates (unit, data_integrity, leakage, walk_forward,
robustness, evaluation — `experiment_adapter.py:975`; the plan's "five
gates" wording is resolved to the actual six). REFUTED = campaign-end
Holm-adjusted sign-flip decision only, provisional-to-formal firewall
intact. INCONCLUSIVE = everything else per H-8 (slot consumed, gate
failed, no reruns, no relaxation). **These adjudication semantics are not
yet implemented in production (v1.1.0 pending); this approval makes them
the specification, not a live behavior.**

**D4 — Multiplicity terms: APPROVED — M = 1,000, m ≤ 50**, subject to
the selected C-2 rule and final configuration review at freeze.
Feasibility: M + 1 = 1,001 ≥ 20·m ⇒ m ≤ 50 exact (plan: "B=1000 for
m ≤ 50"); C4 family maxima 24/36/36/12 all feasible; infeasibility fails
closed (freeze blocked; such signals can never become formal
refutations); no silent truncation, omission, M increase, or post-hoc
membership change; `n_boot ≥ 1000` remains separately required for the CI.

**D5 — Storage: CHOSEN (a).** Upon signing, this record is stored at
`autonomous_agent/state/h10_decision_record_signed.md` with a companion
bare-hash, single-line pin `autonomous_agent/state/h10_decision_record_signed.sha256`
(mirrors the verified `campaign_config.sha256` convention). **Signing
approves the statistical decision record only** — implementation,
configuration freeze, and launch each remain separate authorizations.

**C-1 — Schema: RETRACTION RATIFIED; no `ci_lower_min` change.** The CI
remains the mandatory uncertainty half of the ROBUST pass pair (plan
forbids point-estimate-only pass conditions); the reviewed `-0.01` pin
(`spec_recipes.py:184`) is unaffected; reinstating the restriction would
require a formally approved protocol amendment.

**C-2 — Unavailable member tests: CHOSEN OPTION A with full
bookkeeping.** An unavailable/failed/missing predeclared member test
counts toward family size m, is recorded with **p = 1.0** in the
campaign-end multiplicity record, **can never be formally REFUTED**, does
not change other members' thresholds, and its experiment-level signal
defaults to INCONCLUSIVE per the firewall. **This bookkeeping convention
is a predeclared rule, never observed evidence; the assigned p = 1.0 must
always be rendered as "unavailable" in any record or report; exclusion of
the member after results exist remains impossible.** To be frozen in the
C4 configuration before any family membership is frozen.

**C-3 — SIM-3 adoption ratification: PENDING by design.** It becomes
decidable only when D1 = remedial (recorded above) **and** D2 closes with
an approved method. If D2 later adopts (b), C-3 requires its own explicit
ratification and signature addendum; this record does not pre-authorize it.

**C-4 — CI roles: RATIFIED.** The percentile CI has exactly three roles:
(1) ROBUST uncertainty criterion (`ci_lower_min`); (2) provisional
refutation signal at adjudication (marker only,
`formal_refutation: false`); (3) reported effect-size summary where
exclusion of zero is not, by itself, a formal decision rule. Formal
REFUTED status arises solely from campaign-end Holm-adjusted decisions.

## Standing limitations (preserved; cannot be removed by signature)

1. Week-level exchangeability is **unverified on the real dataset**; no
   local artifact can prove it.
2. All simulation evidence is a synthetic **falsification battery**, not
   proof of real-data validity; frames were proxies (800–3,600 rows);
   power evidence is light (two probes).
3. SIM-2 establishes only that **no statistically significant excess FWER
   was detected** under its predeclared criterion — never FWER ≤ 0.05 as
   a guarantee.
4. The governance-suite test flake (1 failure in 10 runs, identity not
   captured) remains open and must be dispositioned before implementation
   acceptance.
5. The baseline of record is **BASELINE_RECONSTRUCTED_2026_10**; the
   historical V1.0.1 baseline was never reproduced and no such claim is
   made. No profitability or live-trading claim exists or may be inferred.
6. The sealed holdout (SEALED, uses = 0) remains untouched; nothing in
   this record authorizes its access.

## Effect and non-effect

Signing this record approves the H-10 **statistical decision record
only**. It does not authorize: harness v1.1.0 implementation (separate
authorization required), C4 configuration freeze (separate approval), or
Campaign 4 launch (separate explicit authorization). H-10 becomes
RESOLVED only when this record is signed, dated, stored at the D5(a)
location, and its integrity pin written — and even then C-3 and D2's
closure govern whether any method is adopted.

## Signature block — to be completed by the human project owner only

I confirm the recorded choices above, including the retained limitations.

Human signature: ______________________  Printed name: ______________________

Date: ____________  Conditions (if any): ______________________

C-3 status at signing: PENDING (correct — becomes decidable only after
D2 closes)
