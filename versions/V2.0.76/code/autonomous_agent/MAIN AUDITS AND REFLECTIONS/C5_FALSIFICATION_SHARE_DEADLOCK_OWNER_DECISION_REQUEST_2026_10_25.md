# C5 Owner Decision Request: Falsification-Share Steering Blocks All 5 Authorized Error-Cluster Rows

**Date**: 2026-10-25
**Status**: DECIDED - Option A (owner, live chat 2026-10-25)
**Implementation**: [c5_steering_exception]; pinned record
`C5_STEERING_EXCEPTION_DECISION_A_2026_10_25.json` + sha256 pin; behavior
pins in `autonomous_agent/test_c5_steering_exception.py`
**Supersedes nothing; supplements** `C5_ERROR_CLUSTER_AUTHORIZATION_SUMMARY_2026_10_25.md`
(A1-A4 = YES) and the frozen predeclaration
`C5_ERROR_CLUSTER_PREDECLARATION_2026_10_25.json`.

## Executive Summary

The owner authorized (A4) five new error-clustering experiment rows, and the
frozen predeclaration's feasibility arithmetic explicitly counted them
("exploration class budget 16 with 3 used, 5 more fits", predeclaration
line 202). That arithmetic counted class budgets and direction capacity but
**did not count the post-creation falsification-share steering projection**
(`min_falsification_share = 0.3`, frozen campaign policy). Under the frozen,
test-pinned steering behavior, **every one of the 5 authorized rows is
 refused at pre-creation** (`BIAS_QUOTA`), so the generator produces zero
candidates and the resumed loop stops immediately at its predeclared
`PORTFOLIO_COMPLETE` stop. No code path exists that admits the rows without
either an owner-signed exception or an owner-signed reframing.

No fix was implemented unilaterally: the steering behavior is frozen,
tested behavior (T9 pins the exact post-creation interpretation used here),
and the campaign configuration is frozen.

## Verified Facts (all reproduced mechanically 2026-10-25)

1. **Resume attempt (22:19 UTC)**: relaunch via `launch_campaign5.py`;
   campaign-5 preflight `APPROVED` (reason_codes empty, allowed=true);
   loop started on the campaign-5 pin; `phase_generate` created **0**
   proposals; loop stopped durably `STOPPED / PORTFOLIO_COMPLETE`
   ("minimums met and no admissible proposal") at cycle 25.
2. **Ledger**: 797 rows; **zero** rows mention `error_cluster` — the 5
   authorized rows were never created (this is a generation-time block,
   not a validation/approval drop).
3. **Campaign-5-scoped quota state** (scope `campaign-5-regime-error-
   analysis-2026-10-22`): total 23, falsification 7, share 7/23 = 0.3043
   (standing state is above the 0.30 floor).
4. **Post-creation projection for an exploration row** (all 5 axes
   identical in class behavior): total → 24, falsification stays 7,
   share 7/24 = 0.29167 < 0.30 →
   `check_accept -> False, RC_BIAS_QUOTA, "accepting exploration keeps
   falsification share at 0.29 < required 0.30"`.
   The generator's pre-creation guardian uses exactly this projection
   (2026-10-15 repair), so the candidates are never ranked.
5. **Design-space exhaustion**: with the real 797-row ledger,
   `_build_candidates` yields 0 remaining candidates: 93 signatures already
   asked (permanent), `validation` direction exhausted, 8 excluded by the
   same `BIAS_QUOTA` projection. The falsification class budget has 17
   remaining **slots**, but every falsification-reachable design signature
   is already asked — there is no falsification row that could be created
   first to lift the share to ≥ 0.30. This is a hard steered deadlock.
6. **Control (for the decision)**: the identical error-cluster design
   framed as `falsification` **passes** the governor unchanged
   (`within portfolio policy`; post share 8/24 = 0.3333 ≥ 0.30). The
   framing lives in the primitive declaration
   (`default_class="exploration"`, `falsification_capable=False`),
   which the A2 freeze covers.
7. **Behavior provenance**: `bias_governor.check_accept` computes the
   steering share from the POST-creation state, and
   `test_proposal_layer.py::test_t9_quota_steering_and_enforcement` pins
   exactly that interpretation: the shipped behavior is intentional and
   tested, not a regression introduced by the A3 activation work.

## The Frozen Artifacts In Conflict

| Artifact | Provisions |
|---|---|
| Predeclaration (A2 frozen) | 5 axes, ages/executable under harness 1.3.0, "exploration class budget 16 with 3 used, 5 more fits" |
| Campaign config (frozen, byte-pinned `29c905aa...`) | `policy.min_falsification_share = 0.3`; `class_budgets.exploration = 16`; `class_budgets.falsification = 24`; `max_per_direction = 15` |
| Bias governor (frozen, T9-pinned) | post-creation share: non-falsification refused while projected share < floor |
| Proposal library (pin-verified) | `error_clustering_analysis`: `default_class="exploration"`, `falsification_capable=False` |

## Why This Cannot Be Self-Healed

- The loop's own stop is the honest predeclared outcome: minimums met, no
  admissible proposal. The campaign-end multiplicity machinery correctly
  appended `campaign_end_multiplicity_missing -> INCONCLUSIVE`.
- Any code change that admits the rows (floor exception, new framing,
  state adjustment) alters a frozen artifact or a tested frozen behavior
  and therefore requires an owner signature per campaign discipline.
- Re-running the loop without a change reproduces the same clean stop
  (verified once on resume); repeated relaunches will not change the
  outcome.

## Options for the Owner Decision

**Option A - Signed steering exception for the 5 predeclared rows.**
An owner-signed amendment (e.g., to the campaign policy section via a
records-signed override, or a governor exception keyed to
`error_clustering_analysis` + the A4 authorization id) admits exactly the
5 predeclared rows with their frozen exploration framing and frozen
identity. Effect: share temporarily dips to 0.29167 on the first row and
climbs only if falsifications run; the disclosed deficit is the cost of
the diagnostic family. Code touched: exception path + signature-verified
records + tests; no scientific identity changes.

**Option B - Reframe the 5 rows as falsification.**
Owner re-declares the error-cluster rows falsification-class (primitive
`falsification_capable=True` + compiler/generator frame update +
re-predeclaration signature). The rows then pass the unfrozen governor
today (verified control in fact 6) and the share rises per row. This
changes the A2-frozen scientific framing (accept/refute semantics become
cluster-refuting rather than exploratory), so it must be signed like any
identity change.

**Option C - Stand down honestly.**
Record the campaign as ended INCONCLUSIVE with the 5 authorized rows
unexecuted (a one-line "not executed: governor-blocked, see this packet"
note in the authorization summary). No code changes; the loop state is
already durable.

## Recommended Option

**Option A**, with the exception scoped narrowly (primitive id + axis set +
authorization id), disclosed in the ledger detail and in the campaign-end
multiplicity record, so the campaign's outcome accounting never presents
the diagnostic rows as share-compliant. It preserves the signed A2/A3
scientific identity exactly and requires the smallest, auditable code
delta. (Option B is scientifically defensible — the IUT verdict genuinely
refutes failing clusters — but it rewrites a frozen declaration six days
into execution and should only be chosen if the owner wants that semantics.)

## Current Campaign State (2026-10-25, after resume attempt)

- `loop_state.json`: `STOPPED`, `last_stop_reason=PORTFOLIO_COMPLETE`,
  campaign-5 pin intact, 23/45 executions used, lock-free, no STOP file.
- Preflight audit: last entries `APPROVED`.
- Ledger: campaign-5 scope total 23 (7 falsification = 0.3043 standing).
- The 5 authorized error-cluster rows: **not created** (governor-blocked).
- Holdout: untouched (0 uses); data boundary unchanged.

## Sign-off

Owner decision required on Options A / B / C before any code change or
further relaunch. Per campaign discipline the decision should be recorded
as a signed record; the A3-activation flow (record + re-pin + tests) is
the template.
