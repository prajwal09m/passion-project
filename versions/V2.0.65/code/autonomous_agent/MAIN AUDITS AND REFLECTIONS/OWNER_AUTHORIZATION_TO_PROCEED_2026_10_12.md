# PROJECT OWNER AUTHORIZATION TO PROCEED — 2026-10-12

**Status: OWNER AUTHORIZATION RECORDED. CAMPAIGN 4 REMAINS BLOCKED BY ONE\nMANDATORY GATE — THE INDEPENDENT STATISTICAL REVIEW (D2/H-10). NOTHING IS\nFROZEN, LAUNCHED, OR ADOPTED BY THIS FILE.**

## 1. What the owner authorized

Primary evidence: the owner's own message in this project's workflow thread,
dated October 12, 2026, opening "CAMPAIGN 4 — PROJECT OWNER AUTHORIZATION TO
PROCEED". Truthful summary of its substance:

1. Proceed toward launching Campaign 4; resolve every remaining gate that
   can legitimately be resolved.
2. Record this authorization with the actual date, scope, and status.
3. **Do not** represent it as an independent statistical review or as
   approval of a statistical method.
4. **Do not** bypass mandatory independent review, fabricate an approval, or
   declare a blocked gate satisfied without evidence.
5. **Do not** guess or silently alter protected records when reconciling
   configuration discrepancies.
6. Report only a still-blocked gate, its exact basis, and the shortest path
   to resolving it.

This file records that instruction. It creates no signature, no approval,
and no statistical decision of its own.

## 2. Verification performed against actual repository state (2026-10-12)

| Question | Evidence checked | Result |
|---|---|---|
| Has an independent written review been received? | Recursive filename scan of `stat_validation_h10/` and `autonomous_agent/` for assessment/reviewer/expert/opinion artifacts; full mtime listing of both trees for the last 48 h | **No.** 0 assessment-like files exist. Newest artifacts are the agent's own implementation work. The bundle `ee345dab…bb03` is unopened by any reviewer. |
| Is a statistical method approved? | `H10_DECISION_RECORD_AWAITING_SIGNATURE.md` (`b9db3233…`, verified) | **No.** Record is unsigned; D2 DEFERRED, C-3 PENDING. `APPROVED_P_VALUE_METHODS` is empty in code. |
| Is the frozen state intact? | SHA-256 of config `1e0e30b8…`, sidecar match, H-10 record, review bundle, C4 draft `307e98ab…` | **All match.** No protected record altered. |
| Is the holdout sealed? | `prospective/` absence + `holdout_policy` in the frozen config | **SEALED**, uses 0, directory absent. |
| Is anything running? | `loop_state.json`, lock/STOP files | Campaign 3 `STOPPED` at cycle 40 (38/40); no lock, no STOP, no process. |
| Does the owner's authorization close D2? | Owner's own 2026-10-11 record §3 | **No.** That record states D2/C-3 are "NOT satisfied, and not waivable by this instruction", requiring the independent written review. Today's message reaffirms the same boundary. |

**Conclusion: no statistical approval has genuinely been received, so none is
recognized. D2 stays DEFERRED.**

## 3. What today's authorization does authorize

- Recording it (this file).
- Resolving configuration discrepancies from authoritative evidence, and
  presenting the residual rulings to the owner.
- Continuing any **already-authorized** implementation work and its tests.
- Verifying launch prerequisites and reporting the exact blocking gate.

## 4. What it does not authorize

- Closing D2 or ratifying C-3 without the independent review.
- Adopting any p-value method (the gate in `multiplicity.py` stays closed).
- Freezing the C4 draft, launching, or executing any experiment.
- Any change to a gate, threshold, bias floor, duplicate layer,
  outcome-blindness input, approval policy, or the holdout control.

## 5. Discrepancies resolved from evidence (owner's item 4)

| Discrepancy | Authoritative evidence | Resolution |
|---|---|---|
| **Family-group counts** | Actual header of `study_files/outputs/study_v1/development/event_table.csv` (114 columns), classified by the lineage inventory's own family definitions | **Resolved.** `ob_unmitigated_bull_count`/`ob_unmitigated_bear_count` are order-block structure (34 = 16+16+2) and `relative_strength_*` is price/volume technical (the plan lists `relative_*` there). Corrected families: **47 / 11 / 8 / 34 = 100**. The inventory's benchmark (11), zone-base (8) and order-block (34) counts reproduce exactly; only price/volume differs (48 claimed vs 47 actual). Classifier corrected in `census.py`; 22 census tests green. |
| **Feature-column count** | Same header; 114 total − 14 label/meta (5 label machinery + 9 identity/label) = **100 features** | **Surfaced, not guessed.** The inventory claims 101 features + 13 label/meta. Its own arithmetic is off by exactly one column it counted as technical that is in fact label/meta; the inventory does not enumerate its 13, so the identity of that column cannot be recovered from documentation. Requires a **freeze-time ruling**. |
| **Stop-condition count** | Frozen C3 config declares **14**; the plan safety bullet says "**15 original** + 2 new" | **Surfaced.** No document enumerates a 15th original stop, and no code reads `stop_conditions` at all. Evidence supports **14 + 2 = 16**. Requires ratification because the plan's wording conflicts. |
| **Bootstrap settings** | H-10b rule `n_boot + 1 ≥ 20·m`, D4 `m ≤ 50`, floor `n_boot ≥ 1000` | **Resolved, no decision needed.** Under the corrected family bounds (regime 24, horizon 36, purge 36, complexity 12) and `n_boot = 1000`: 1001 ≥ 480 / 720 / 720 / 240, all pass, and the global cap 50 gives 1001 ≥ 1000 (margin 1). Enforced by `feasibility()` with tests. |
| **Missing lineage controls** | Plan code-touchpoints require the UNVERIFIABLE-lineage stop wired **and** declared | **Half done.** Both stops are wired and tested in `continuous_loop.py`; neither is **declared** in any config. The amendment block in `CAMPAIGN_4_CONFIG_RECONCILIATION_2026_10_12.md` §6 carries the declaration and is applied only at freeze. |
| **Census tolerances** | `census.py` validator | **Not frozen (correctly).** The draft manifest fails validation with 97 "tolerance not frozen" errors, so it cannot back an audit PASS until the freeze declares tolerances from documented precision. |

## 6. The one gate that still blocks launch

**Gate 1 / D2 — the independent written statistical review.**

- **Governing rule:** decision sheet gate 1 and the plan's decision rule —
  method (b) "is adopted subject to explicit human confirmation" only after
  the predeclared evidence; H-10 stays open "until that evidence exists and
  a human decision is recorded"; the p-value gate refuses adjusted p-values
  while H-10 is open, which blocks launch fail-closed.
- **Evidence needed:** a written assessment from a reviewer independent of
  this project's authorship answering the six questions in
  `review_submission/REVIEW_REQUEST_READY_TO_SEND.txt` Part 1, placed at
  `stat_validation_h10/D2_EXTERNAL_REVIEW_ASSESSMENT.md`.
- **Who can supply it:** a human reviewer — not the owner's authorization,
  not this agent, not the project author. The owner's own 2026-10-11 record
  already held this line, and today's instruction reaffirms it.
- **Shortest actionable path:** the owner sends the verified bundle
  (`ee345dab…bb03`, 13/13 entries, 11/11 manifest hashes) with the
  paste-verbatim message; the assessment lands in the repo; the agent
  validates provenance and scope; the owner records D2 (+ C-3 if adopting);
  then freeze → gate 7 verification → launch authorization → launch.
  Everything on that path after the first step is already prepared.

## 7. Owner rulings recorded 2026-10-12 (workflow answers)

The owner answered four questions that only the owner could decide. Recorded
verbatim in substance:

| # | Ruling | Effect |
|---|---|---|
| R-1 | **Ratify 100 features + 14 label/meta.** The actual header is authoritative; the inventory's 101/13 is an off-by-one. | Census expected-column set = **100**. Inventory erratum required, not a silent edit. |
| R-2 | **Ratify 14 original + 2 new = 16 stop conditions.** The plan's "15 original" is a wording error; the frozen C3 config's 14 are the originals. | C4 must carry all 14 verbatim plus `point_in_time_contamination_detected` and `unverifiable_lineage_detected`. `STOP_ENFORCEMENT` already covers all 16. |
| R-3 | **Grant primitive activation as parallel work.** | The five v1.1.0 primitives may be implemented and tested now. This adopts no method, freezes nothing, and launches nothing. |
| R-4 | **Audit FAIL — no partial pass** when a run's only defects are disclosed Tier-2 columns. | Matches the lineage inventory's documented semantics and is fail-closed. Never contamination; disclosed separately. |

R-3 is recorded as a separate grant file because it changes what the harness
can execute; R-1/R-2/R-4 are rulings on documentation conflicts and change no
code behavior by themselves.

## 8. Boundary statement

No signature created; no review fabricated; no method adopted; no config
frozen; no campaign launched; no experiment executed; no holdout access; no
protected record altered. Pins re-verified after all changes.

**The blocking gate is unchanged by these rulings: the independent written
statistical review (D2/H-10), and nothing in this file substitutes for it.**
