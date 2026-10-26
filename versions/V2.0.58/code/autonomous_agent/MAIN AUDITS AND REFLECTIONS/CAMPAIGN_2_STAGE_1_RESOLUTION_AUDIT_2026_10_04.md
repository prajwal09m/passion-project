# CAMPAIGN 2 — STAGE 1 RESOLUTION AUDIT — 2026-10-04

**Status:** COMPLETE (Stage 1 resolution only; Stage 2 NOT started, NOT authorized by this document)
**Predecessor:** `CAMPAIGN_2_STAGE_1_SHADOW_AUDIT_2026_10_04.md`
(sha256 `859b8587caf207a3b8c106a9d07a585a4a48753fc746463c4ab99cb5f1f676a0`)
**Scope:** Resolve OBS-1, OBS-2, OBS-3 from the Stage 1 shadow campaign with
deterministic, test-proven changes; re-run bounded shadow generation for a
BEFORE/AFTER comparison. No experiment was compiled or executed. No proposal
was executed. The supervisor was not started. The holdout was not opened.
Campaign 1 evidence and `autonomy_config.json` were verified unchanged before
and after.

**Proposal ledger state after this audit:** 47 rows (append-only; the
Stage-1 39-row file is a verified byte-prefix),
sha256 `4ceb1f85f95a2e346b17f7fe95630febafaaae1ecef53f509574791395cfc760`.

---

## A. Original observation

Stage 1 (5 shadow cycles, seeds 1–5, `approver=None`) produced: 15 proposals
created, 6 awaiting approval, **9 refused — every refusal reason
`NEAR_DUPLICATE`**, 0 failed validation, 0 compiled. Falsification share 0.47
(7/15), replication 0.00, 15/15 distinct design signatures, 0 exact duplicate
fingerprints, 0 Campaign 1 signature overlap.

* **OBS-1:** Templated hypotheses caused legitimately distinct design
  signatures to reach cross-signature text similarity ≥ 0.90 (worst observed
  0.940) and be refused `NEAR_DUPLICATE`. Only 2/4 executable primitives and
  2/8 directions ever reached validation.
* **OBS-2:** Ranking did not steer away from exhausted direction budgets;
  refused proposals permanently consume total-budget accounting (cap 20), so
  re-ranking signatures already seen (kept at novelty 0.2 by the old code)
  created guaranteed-refusal churn — wasted proposal slots.
* **OBS-3:** 6 proposals passed all gates at creation time T1 (post-creation
  accounting passed then); later refusals pushed their direction records over
  caps (validation 10, calibration 5 vs `max_per_direction` 4). Approval-time
  revalidation would refuse them — the system had no explicit policy for
  proposals whose budget state changed between validation and approval.

## B. Root cause

* **OBS-1:** The third duplicate layer (text similarity) was applied to
  *all* prior proposals regardless of design-signature identity. The
  hypothesis field is a deterministic template
  (`[direction] purpose (params) — …`), so any two proposals of the same
  primitive share most tokens. Wording similarity was being treated as
  scientific duplication across signatures, although layers 1 (fingerprint)
  and 2 (signature) already authoritatively encode "same question".
* **OBS-2:** The generator ranked over the full primitive grid with no
  notion of remaining capacity. A direction whose budget was already
  consumed still produced candidates; each was created and then refused,
  and every refusal permanently consumed more budget — a self-amplifying
  churn loop.
* **OBS-3:** Validation ran only at creation (T1). Approval transitioned
  straight to `ACCEPTED_FOR_EXECUTION` without re-checking current state,
  and no approval provenance was persisted. Whether a stale proposal
  remained valid was therefore undefined (silent state-dependent behavior).

## C. Change made

**Task 1 — OBS-3: Policy B, `revalidate_at_approval@1.0.0` (chosen and
justified over snapshot reservation).**

* `proposal_layer/ledger.py` — `transition()` now refuses any
  `ACCEPTED_FOR_EXECUTION` row that does not persist
  `approval_policy`, `approved_by`, and the exact `quota_state` snapshot
  used for the decision (`LedgerError`, fail-closed). No validated proposal
  can silently become an execution candidate.
* `proposal_layer/cycle.py` — new `_revalidate_and_approve()` re-runs the
  complete 9-gate chain against **current** ledger state at approval time.
  If state changed since T1 the proposal transitions to
  `REFUSED | FAILED_VALIDATION` with the current reason code, the failing
  gate report, and the quota_state snapshot (detail key
  `revalidated_at_approval: true`, `approval_policy:
  revalidate_at_approval@1.0.0`). New restart-safe entry point
  `approve_pending(root, approver=…)` applies the policy to proposals left
  in VALIDATING by earlier runs; it never compiles and never executes.
  Cycle summaries gained `refused_at_approval` / `failed_at_approval`
  buckets. Deterministic and restart-safe: state is reconstructed from the
  append-only ledger only.
* Applied to the 6 real awaiting proposals (approver
  `stage1-obs3-resolution@1.0.0`): **all 6 → `REFUSED` / `BUDGET_EXHAUSTED`**
  (`VALIDATING → REFUSED`, each row carrying
  `quota_state {total: 15, by_direction: {validation: 10, calibration: 5}}` —
  the exact state used). 0 ACCEPTED_FOR_EXECUTION rows exist in the ledger.
  Ledger 39 → 45 rows, byte-prefix preserved.
* Policy B was chosen over snapshot reservation because reserving budget at
  validation time would let later proposals be refused for slots held by
  proposals that may never be approved, and would allow a proposal to be
  executed under a quota picture no longer true at execution time.
  Revalidation guarantees: never overrun, never bypass current safety
  validation, never silently convert — at the cost of refusing T1-valid
  proposals, which is recorded, explicit, and auditable.

**Task 2 — OBS-1: text gate narrowed to same-signature scope.**

* `proposal_layer/validator.py` — `_gate_duplicate` layer 3 (text
  similarity ≥ 0.90) now iterates **only same-signature** history. A
  same-signature re-ask is refused even with `delta_from_prior` declared if
  the wording is near-identical. Cross-signature text similarity is a
  generation-side wording-diversity *preference* only (still applied in
  `generate_proposals`) and can never refuse a scientifically distinct
  design. Layers 1 (exact proposal fingerprint), 2 (bucketed design
  signature), the already-asked memory, and the prior-campaign recipe
  signature set are unchanged and remain the authoritative duplicate
  controls. No LLM, no semantic heuristic, deterministic.
* Duplicate-layer evaluation (three layers separately):
  1. exact fingerprint → unchanged, refuses byte-identical re-asks;
  2. design signature → unchanged, refuses same-signature re-asks without a
     declared delta, plus `max_signature_count` cap;
  3. text similarity → same-signature only (was: all history).

**Task 3 — OBS-2: fail-closed scheduler.**

* `proposal_layer/generator.py` —
  * `quota_state_from_view()` mirrors the validator's accounting exactly
    (same quota_state, same fingerprint dedupe) so scheduler capacity can
    never diverge from gate behavior;
  * `capacity()` returns conservative remaining budget for total,
    directions, and class budgets (`remaining = cap − current_records`;
    refusals count, are never removed);
  * `_build_candidates()` excludes: exhausted directions
    (remaining ≤ 0), exhausted class budgets, recipe signatures (already
    executed in prior campaigns), already-asked signatures (permanent),
    signature-cap-hit signatures; early-returns `[]` with
    `excluded_total_budget` when the total budget is exhausted. The old
    novelty-0.2 re-ranking tier for seen signatures is **removed** — the
    generator cannot declare `delta_from_prior`, so regenerating them was
    guaranteed refusal churn;
  * `generate_proposals()` caps output by remaining total and by
    per-direction and per-class remaining capacity within the cycle;
  * `scheduler_report()` exposes exclusions, remaining capacity, and an
    `exhausted` flag (research-exhaustion reporting).
* Budgets were **not** increased, quotas were **not** weakened, refused
  records were **not** deleted (`bias_policy.json` untouched:
  max_total 20, max_per_direction 4, max_signature_count 2,
  min_falsification_share 0.35, max_replication_share 0.50,
  class budgets 8/8/2/2).

## D. Why the change is scientifically justified

* **OBS-1:** Scientific identity of a question is defined by its design
  signature (primitive + parameters) — that is the predeclared operational
  definition. Refusing distinct signatures because a *template* repeats
  tokens conflates phrasing with design and systematically destroys
  diversity (Stage 1 lost 9 distinct designs to wording). Deterministic
  text similarity cannot distinguish paraphrase from templating; restricting
  it to where wording actually matters (same-signature re-asks, where even a
  declared delta must produce genuinely different framing) keeps the check
  where it has discriminative power. Exact and signature duplicate
  protection — the layers that answer "same scientific question?" — are
  untouched.
* **OBS-2:** A proposal that cannot pass approval-time budget validation
  must not consume a generation slot: creating it only to be refused adds
  no information, distorts portfolio accounting, and — because refusals
  permanently consume budget — actively destroys future research capacity.
  Excluding exhausted directions/classes *before* ranking is the standard
  fail-closed scheduler behavior; it is derived purely from recorded budget
  counters, never from expected outcomes, so it introduces no outcome
  selection bias.
* **OBS-3:** Budget caps are safety/scientificity invariants. Checking them
  only at creation allows drift between validation and execution — the exact
  hole that lets a proposal execute outside its predeclared portfolio
  picture. Revalidation at approval makes the invariant hold at the moment
  it matters (right before a proposal could become executable), with the
  decision, the policy version, and the exact state persisted — i.e.,
  reproducible and auditable rather than implicit.

## E. Tests proving the change

Full suites after the change:

| Suite | Result |
|---|---|
| proposal layer (`autonomous_agent.test_proposal_layer`) | **41/41 OK** (27 original + 14 new) |
| autonomous agent (core, experiment_adapter, hardening, baseline, spec_recipes, recipe_harness) | **117/117 OK** |
| frozen study (`discover -s study_files/backend/tests`) | **22/22 OK** |
| Campaign 1 immutability (`test_campaign1_evidence_unchanged` + manual hash re-verification) | **PASS** |

New regression tests:

* **Task 1 / OBS-3:**
  * `test_t19_obs3_state_change_between_validation_and_approval` —
    validation at T1 → state change at T2 (second same-direction record
    refused) → `approve_pending` at T2 → expected final state
    `REFUSED`/`BUDGET_EXHAUSTED`; approval provenance
    (`approval_policy`, `approval_attempted_by`, `quota_state` snapshot
    with the exact direction counts) persisted; **no**
    ACCEPTED_FOR_EXECUTION row anywhere; the T2 refusal record intact.
  * `test_t19b_obs3_restart_between_validation_and_approval` — restart
    (fresh ledger instance) between T1 and T2; approval reads state from
    disk only; identical outcome; second approval attempt is a no-op
    (idempotent, no duplicate rows).
  * `test_t19c_obs3_sequential_approvals_persist_provenance` — sequential
    proposals both within budget are approved with full provenance each;
    approval compiles/executes nothing.
  * `test_t19d_obs3_ledger_requires_approval_provenance` — ledger rejects
    ACCEPTED_FOR_EXECUTION without provenance, with partial provenance, and
    accepts only complete provenance (fail-closed contract).
* **Task 2 / OBS-1:**
  * `test_t20a_duplicate_layer_exact_fingerprint_refused` — identical
    re-ask → REFUSED/DUPLICATE.
  * `test_t20b_duplicate_layer_same_signature_high_text_refused` —
    same signature + ≥0.90 text (even with `delta_from_prior` declared) →
    REFUSED/NEAR_DUPLICATE; same signature without delta → refused by the
    signature layer.
  * `test_t20c_cross_signature_templated_text_allowed` — asserts the
    trigger condition (text similarity ≥ 0.90) between two **distinct**
    signatures and asserts validation passes (no DUPLICATE-layer failure).
  * `test_t20d_semantic_equivalence_is_a_documented_limitation` —
    prior-campaign replay refused deterministically; identical wording
    across different signatures allowed (limitation pinned, see §G).
* **Task 3 / OBS-2:**
  * `test_t21a_exhausted_direction_excluded_from_ranking` — exhausted
    direction absent from generated payloads and listed in
    `excluded_exhausted_directions`; other directions still produce.
  * `test_t21b_exhausted_signature_excluded_from_generation` —
    cap-hit signature never re-emitted.
  * `test_t21c_refusal_remains_in_ledger_and_is_never_regenerated` —
    refusal row permanent across restart; failed proposal never regenerated
    for seeds 1–5; refusal row still present after generation.
  * `test_t21d_restart_preserves_exhaustion` — fresh ledger + rebuilt view
    show the same zero remaining capacity.
  * `test_t21e_all_exhausted_reports_research_exhaustion` — all executable
    directions at cap → `scheduler_report()["exhausted"] is True`,
    `candidates_remaining == 0`, `generate_proposals` returns `[]`
    (research exhaustion reported, no pointless proposals); total-budget
    exhaustion also fail-closed.
  * `test_t21f_exhausted_class_budget_excluded_from_ranking` — class at
    budget cap never ranked; every payload the scheduler does emit passes
    validation end-to-end (no doomed creations).
* Existing tests updated only where they encoded the old contracts:
  direct `ACCEPTED_FOR_EXECUTION` transitions now go through an approval
  helper carrying provenance; `test_t6` case (d) now asserts the Task-2
  behavior (cross-signature templated wording → allowed). Duplicate,
  signature-cap, budget, lifecycle, holdout, no-IO, no-execution,
  selection-blindness and Campaign 1 tests all unchanged and green.

## F. Before/after shadow-generation comparison

Same bounded protocol: 5 cycles, seeds 1–5, real evidence view, real
ledger, `approver=None` (approval step unreachable → no compile possible).

| Metric | BEFORE (Stage 1, 39-row ledger) | AFTER (resolution, 47-row ledger) |
|---|---|---|
| proposals created (5 cycles) | 15 | **1** |
| awaiting approval | 6 | 1 |
| refusals at creation | 9 | **0** |
| refusal reasons | NEAR_DUPLICATE ×9 | (creation) none; approval-time BUDGET_EXHAUSTED ×6 recorded by Task 1 policy application |
| text-similarity refusals (new) | 9 | **0** |
| already-asked refusals (new) | 0 | 0 |
| exhausted-direction refusals (new) | 0 (latent churn instead) | 0 (excluded **before** creation) |
| budget-exhaustion refusals | 0 at creation (over-cap state latent) | 6 at approval (deterministic, with quota snapshots) |
| falsification share (ledger) | 0.47 (7/15) | **0.50 (8/16)** — floor 0.35 satisfied |
| replication share | 0.00 | 0.00 (cap 0.50 satisfied) |
| unique design signatures | 15/15 | **16/16** |
| exact duplicates | 0 | 0 |
| Campaign 1 signature overlap | 0 | 0 |
| genuinely distinct designs | 15 | 16 |
| proposals capable of null/adverse results (falsification-class, predeclared refute rule) | 7 | 8 |
| total budget used | 15/20 | 16/20 |
| scheduler exhaustion reporting | none | seeds 2–5: `exhausted=True`, 0 generated |

New proposal: `prop-e8cecbc65f31-1` — feature_engineering,
falsification-class, distinct signature, passed all 9 gates at creation,
status VALIDATING (awaiting approval; **not** approved in this phase).

Scheduler trace: seed 1 → candidates 14, excluded directions
[calibration, validation], excluded classes [confirmatory]; created 1.
Seeds 2–5 → `exhausted=True`, candidates 0 (both class budgets at cap:
confirmatory 8/8, falsification 8/8), nothing generated.

**Nine-probe determination:**

1. **OBS-1 improved? YES.** 0 new text-similarity refusals (was 9). The 9
   historical NEAR_DUPLICATE payloads, re-validated read-only under the new
   chain, now fail at BUDGET/BUDGET_EXHAUSTED — **0 still fail at the
   DUPLICATE gate** — proving the wording gate no longer refuses them while
   budgets remain fail-closed. They were 9/9 distinct signatures; 10
   cross-signature pairs ≥0.90 (max 0.992) quantify the templating.
2. **OBS-2 improved? YES.** Refusal churn eliminated (9/15 = 60% refusal
   rate → 0%); exhausted directions and classes excluded before ranking;
   refusal records preserved; scheduler reports research exhaustion instead
   of regenerating doomed proposals.
3. **OBS-3 deterministic and unambiguous? YES.** One policy id/version
   (`revalidate_at_approval@1.0.0`) persisted in every approval and
   approval-attempt row with the exact quota_state used; ledger rejects
   provenance-less acceptance; 6/6 real awaiting proposals resolved to
   REFUSED/BUDGET_EXHAUSTED; restart + sequential behavior covered by
   T19a–d.
4. **Duplicate protection remained effective? YES.** Exact-fingerprint
   (T20a), same-signature (T20b), recipe-replay (T7, T20d) refusals all
   green; 0 exact duplicates and 0 Campaign 1 overlaps in the new
   portfolio; already-asked memory permanent (T21c).
5. **Falsification coverage ≥ floor? YES.** 0.50 ≥ 0.35 (ledger-wide);
   the single new proposal is falsification-class; steering logic and
   class budgets unchanged.
6. **Expected outcomes excluded from selection? YES.** Selection inputs
   remain the closed 7-field set (T8 green); new scheduler exclusions read
   only budget counters (records), never outcomes or expectations;
   `preregistered_expectation` remains recorded-after-ranking and unscored.
7. **Provenance complete? YES.** All 47 ledger rows carry reason codes and
   detail; approval rows additionally carry policy id, approver, and
   quota_state; generator/validator/bias-policy versions recorded in
   payloads as before.
8. **Holdout blindness intact? YES.** No `prospective`/holdout path string
   anywhere in the 47-row ledger; `study_files/outputs/study_v1/`
   contains only `development` and `models`; T2 (view refuses holdout
   reads, no holdout file opened during build) green.
9. **Any new selection bias? NONE DETECTED.** The only new exclusions are
   capacity-based (direction/class/signature/total counters derived from
   the append-only record). They are a function of recorded budget state,
   not of predicted or prior success; ranking within admissible candidates
   is unchanged. Effect on *diversity* is the intended conservative
   trade-off: near exhaustion the system narrows rather than churns.

## G. Remaining limitations

1. **Cross-signature semantic equivalence is not deterministically
   decidable.** Two different signatures that are semantically the same
   scientific question (e.g., identical wording, different `n_boot`) cannot
   be refused without an LLM or an arbitrary semantic heuristic — both
   forbidden. The system distinguishes them only through signature-level
   accounting (`max_signature_count`, per-direction caps). Documented, not
   heuristically "solved"; behavior pinned by `test_t20d`.
2. **Refusals permanently consume budget** (deliberate bias protection:
   forgetting refusals is the bias risk). Combined with fixed caps this
   means the proposal space can reach genuine exhaustion — the correct
   conservative outcome, but it bounds campaign lifetime (see §H).
3. **Capacity exclusion narrows diversity near exhaustion.** By design
   fail-closed; a direction/class with zero remaining capacity can never
   emit a proposal even if a scientifically valuable design exists.
4. **`excluded_signature_cap` is defense-in-depth.** For in-grid
   signatures the already-asked exclusion fires first; out-of-grid
   parameterizations (e.g., `n_boot=1500`, outside the generator grid)
   are never candidates. The cap counter alone does not cover them — the
   DUPLICATE/BIAS gates still do at validation.
5. **Single-process sequential approval.** `approve_pending` processes
   pending proposals sequentially on one append-only, fsync'd ledger.
   Crash between validation and approval is covered (restart-safe,
   T19b); concurrent multi-writer approval is out of scope for Stage 1.
6. **`approve_pending` does not compile.** Compilation remains a separate
   stage-2 concern; nothing in this resolution can produce an executable
   artifact.

## H. Stage 2 readiness assessment

**Mechanically READY; portfolio-capacity NOT READY without an explicit
human budget decision.**

Mechanical readiness (all verified green):

* Proposal lifecycle intact and enforced (41 proposal-layer tests,
  including illegal-transition and provenance-contract tests).
* Ledger append-only (39 → 45 → 47 verified as byte-prefix growth).
* Duplicate protection active (3 layers), falsification quota active
  (floor 0.35), outcome-blind selection active (closed input set),
  holdout sealed (`prospective/` absent, 0 references in ledger).
* Approval boundary fail-closed: no proposal can reach
  `ACCEPTED_FOR_EXECUTION` without recorded policy, approver, and quota
  snapshot, revalidated against current state.
* Campaign 1 evidence, historical V1.x/V2.x evidence and
  `autonomy_config.json` hashes unchanged; ExperimentAdapter never invoked;
  no candidate workspace created; registry/spec_attempts unchanged (8/8);
  no STOP flag; supervisor not running.

Portfolio-capacity blocker (must be decided by the human, not by this
phase): under the predeclared caps the proposal space is exhausted —
confirmatory 8/8, falsification 8/8 (class budgets), validation 10/4 and
calibration 5/4 (direction caps), total 16/20 with no class capacity. The
fail-closed scheduler therefore reports `exhausted=True` and generates
nothing. Exactly **one** admissible proposal exists
(`prop-e8cecbc65f31-1`, falsification-class, VALIDATING), which cannot
satisfy Stage 2's mixed-portfolio requirement (≥1 falsification **and** ≥1
confirmatory/replication class). Options, all requiring explicit human
authorization outside this phase:

1. a NEW Stage 2 campaign configuration that **predeclares** additional
   proposal budget (a policy change: stop, record reason, new hashed
   config — exactly the Stage 2A mechanism); or
2. Stage 4 primitive expansion (explicitly not authorized); or
3. accept proposal-space exhaustion under current caps (research
   exhaustion is a legitimate scientific end state).

**Verdict: Stage 2 execution is NOT authorized-ready on portfolio grounds.
No budget was increased here to make it ready — that would contradict the
resolution's explicit constraints.** Safety, determinism, provenance and
scientific-validity machinery are ready; the budget question is a human
decision.

---

*Resolution executed 2026-10-04 under Campaign 2 Stage 1 constraints:
no experiment execution, no supervisor, no compilation for execution, no
holdout access, no Campaign 1 or `autonomy_config.json` modification, no
budget/quota weakening, refusal records preserved.*
