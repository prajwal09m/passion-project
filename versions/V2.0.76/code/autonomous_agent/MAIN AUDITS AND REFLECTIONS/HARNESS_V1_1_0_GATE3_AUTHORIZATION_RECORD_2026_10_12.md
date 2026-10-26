# HARNESS v1.1.0 — GATE 3 IMPLEMENTATION AUTHORIZATION RECORD — 2026-10-12

**Status: ADMINISTRATIVE IMPLEMENTATION AUTHORIZATION RECORDED FOR THE
D2-INDEPENDENT SUBSET ONLY. H-10 REMAINS UNRESOLVED. D2 REMAINS DEFERRED.
C-3 REMAINS PENDING. NOTHING IS ADOPTED, FROZEN, OR LAUNCHED BY THIS FILE.**

## 1. What the owner authorized

Provenance: the human owner's answer in this project's workflow thread on
2026-10-12, selecting the option labelled **"Authorize the D2-independent
subset"** in response to the gate-3 question posed by the coding agent.
The question and its three options are reproduced verbatim in §2 so the
scope is auditable without the thread. This file **records** that decision;
it does not create, infer, or substitute for any signature, and it does not
speak for the owner beyond what they selected.

The requested text (as presented to the owner):

> Build Holm machinery, family bookkeeping, campaign-end multiplicity
> record, provisional→formal firewall, C-2 missing-member rule, both new
> fail-closed stops + a config↔code stop-correspondence test, census
> manifest + tests, and freeze-integrity/protected-state preservation
> tests — with the p-value method left fail-closed behind the unresolved
> H-10 gate, so method (b) is NOT adopted and nothing is frozen or launched.

Options **not** selected: "Authorize the full plan checklist now" (includes
flipping the five primitives to `executable=True` and activating the 1.1.0
run modes) and "Withhold until the review returns".

## 2. Scope — authorized

- Holm step-down adjustment machinery and per-campaign family bookkeeping.
- The campaign-end multiplicity record (append-only, unadjusted + adjusted
  side by side, raw delta and raw CI retained).
- The provisional→formal firewall: no standalone `REFUTED` label in any
  artifact before the campaign-end multiplicity record exists.
- The C-2 missing-member rule (unavailable member counts toward family size
  m, assigned p = 1.0, rendered "unavailable", never formally REFUTED).
- Both new fail-closed stops — `point_in_time_contamination_detected` and
  the UNVERIFIABLE-lineage stop — wired in the loop, plus a test asserting
  correspondence between the config's declared `stop_conditions` and the
  code that can fire them.
- Census manifest module, validator, and tests (H-11 invariants: 101
  columns present, frozen tolerances, tolerance never derived from observed
  mismatches, UNVERIFIABLE never PASS, structural results never upgrade a
  value verdict, missing entry blocks audit PASS).
- Freeze-integrity and protected-state preservation tests.
- The H-10 fail-closed p-value gate: adjusted p-values must refuse to
  compute while H-10 is unresolved, with no silent fallback.

## 3. Scope — NOT authorized by this record

- **No statistical method is adopted.** H-10/D2 remain open; the p-value
  computation itself is left fail-closed. Implementing Holm does not adopt
  method (b), and nothing in this work may be cited as evidence that any
  p-value method is valid.
- No D2 decision, no C-3 ratification, no signature of the H-10 record.
- No change to any gate name or threshold, bias floor, class budget,
  duplicate layer, outcome-blindness input, approval policy, or holdout
  control.
- No change to `bias_policy.json`, the baseline registry, historical
  records, or any Campaign 3 artifact (state, ledger, champion, archive).
- No freezing of the C4 draft, no amendment of its contents by this record.
- No Campaign 4 launch, no budget change, no experiment execution.
- No activation of the five dormant primitives (`executable` stays `False`),
  no `harness_version == "1.1.0"` selector activation in `recipe_harness.py`.
- No network, no new data source, no LLM.

## 4. Constraints the implementation must satisfy

1. v1.0.0 behavior stays byte-identical when the new machinery is unused:
   every addition must be inert unless a caller explicitly opts in.
2. The suite must be green after each component, with every run's exit
   status recorded.
3. Fail-closed everywhere: absent multiplicity record → every provisional
   signal resolves INCONCLUSIVE; absent/unresolvable lineage → stop; infeasible
   granularity → freeze blocked, signals never formal.
4. Nothing is deleted or rewritten in append-only ledgers; additions only.
5. On completion: pins re-verified, holdout re-checked, Campaign 3 artifacts
   untouched, and the resulting diff reported honestly.

## 5. Status of other gates after this record

Gate 1 partial (D2/C-3 still open) · gate 2 unchanged · **gate 3 satisfied
for the subset described in §2** · gate 4 in progress · gate 5 closed ·
gate 6 absent · gate 7 re-run at freeze · gate 8 absent. Campaign 4 remains
BLOCKED pending the independent review, D2/C-3, freeze approval, and launch
authorization.
