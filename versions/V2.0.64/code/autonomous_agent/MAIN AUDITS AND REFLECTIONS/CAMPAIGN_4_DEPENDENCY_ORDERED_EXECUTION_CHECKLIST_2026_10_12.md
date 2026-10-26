# Campaign 4 — dependency-ordered execution checklist

Prepared 2026-10-12. Purpose: make the interval between *review received*
and *campaign running* as short as possible by pre-staging everything that
is not gated, and naming every gate exactly once. **Nothing here is an
approval; no step below has been executed unless it says so.**

Legend: **[P]** can run now or in parallel with anything else ·
**[W]** must wait for the gate named in its `blocked-by` ·
**[H]** human-only (agent cannot perform) ·
**[done]** completed and verified today or earlier.

## Track 0 — state now (baseline, 2026-10-12)

- [done] **[P]** Supervisor/lock/STOP absent; no Python process running;
  Campaign 3 `STOPPED` at cycle 40, 38/40 executions, ledger intact
  (350 rows), champion untouched.
- [done] **[P]** Pins verified: frozen C3 config `1e0e30b8…` + pin file
  agree; decision record `b9db3233…`; plan `094827b0…`; flake evidence
  `72504661…`; fixed test `e1de8523…`.
- [done] **[P]** Holdout sealed: `prospective/` absent, `SEALED`, uses 0.
- [done] **[P]** Full suite: **235 tests, OK, exit 0** (100 s).
- [done] **[P]** Gate 5 (flake) closed: 10/10 consecutive green.
- [done] **[P]** Review bundle verified: `ee345dab…bb03`, 13/13 entries,
  11/11 manifest hashes, 11/11 identical to working tree.

## Track 1 — independent review (external, human-only)

- [ ] **[H][P]** Send `stat_validation_h10/H10_D2_REVIEW_SUBMISSION.zip`
  with Part 1 of
  `stat_validation_h10/review_submission/REVIEW_REQUEST_READY_TO_SEND.txt`
  — routes A–D in the same file; pre-send checklist in
  `review_submission/SUBMISSION_CHECKLIST_2026_10_12.md`.
- [ ] **[H][W: send]** Agree scope, independence, fee, deliverable in
  writing **before** sharing the bundle or paying.
- [ ] **[H][W: review returned]** Place the written assessment at
  `stat_validation_h10/D2_EXTERNAL_REVIEW_ASSESSMENT.md` and report it.
- [ ] **[P][W: assessment exists]** Agent validates reviewer independence,
  written form, provenance (manifest hashes on the reviewer side), and
  scope coverage of all six questions. **Outcome not predetermined.**

## Track 2 — implementation (gate 3)

- [ ] **[H][P]** Grant (or refuse) the minimal authorization in
  `…/HARNESS_V1_1_0_REMAINDER_AND_AUTHORIZATION_REQUEST_2026_10_12.md` §C.
  *This is the single highest-leverage action available today: it is the
  only open gate that does not depend on the review.*
- [ ] **[W: gate 3]** Record the grant as a dated provenanced file (no
  invented signature).
- [ ] **[W: gate 3]** Implement B1 items 1–5 (recipe_harness selector,
  primitives flags + frozen families, validator, both stops + wiring,
  experiments delta if needed).
- [ ] **[W: gate 3]** Implement the B1 test list (firewall, Holm, family
  membership, H-10b feasibility, census, safety-gate preservation,
  config↔code stop correspondence, p-value fail-closed gate).
- [ ] **[W: implementation]** Full suite green, every run's exit status
  recorded; results written next to the flake evidence file.
- [ ] **[P][W: implementation]** Independent re-read of the diff for gate/
  threshold drift; pins re-verified after all changes.

## Track 3 — statistical decision (gates 1–2, D2/C-3)

- [ ] **[H][W: assessment]** Decide D2 (adopt / reject / keep deferred) on
  the six-question assessment; record rationale and limitations.
- [ ] **[H][W: D2]** If adopting: ratify C-3 (SIM-3 remedial).
- [ ] **[P][W: D2/C-3]** Resolve in writing: the §3 stop-count conflict
  (14 + 2 = 16 vs the plan's "15 original"), the Tier-2 residual ruling,
  and the exact UNVERIFIABLE stop identifier.
- [ ] **[P][W: D2/C-3]** Close or explicitly carry forward H-10b/H-11
  freeze-time checks (census execution, feasibility).

## Track 4 — freeze (gate 6) — strictly after tracks 2 and 3

- [ ] **[W: track 2 + track 3]** Apply the prepared amendment from
  `CAMPAIGN_4_CONFIG_RECONCILIATION_2026_10_12.md` §6 to the draft
  (`multiplicity_policy` with `n_boot ≥ 1000`, four family caps, C-2 rule;
  both new stops; resolved stop list).
- [ ] **[W]** Finalize `campaign_id`, `created_at`, `seed_base`; recompute
  `protocol_fingerprint`.
- [ ] **[W]** Run freeze-time checks: H-10b `n_boot + 1 ≥ 20·m` for every
  family (fail-closed), census-manifest completeness, count-once rule,
  holdout seal, duplicate layers, five gate names/thresholds, stop-list
  correspondence.
- [ ] **[H][W]** Gate 6 freeze approval recorded.
- [ ] **[W: approval]** Copy draft → `autonomous_agent/state/campaign_config.json`,
  write fresh SHA-256 pin, verify pin == file, verify fingerprint.
- [ ] **[W]** Gate 7 re-verification: every launch prerequisite through
  `py -3 -X utf8 autonomous_agent/launch_readiness_check.py` (must exit 0).

## Track 5 — launch (gate 8) — strictly after track 4

- [ ] **[H][W: gate 7]** Explicit launch authorization (30 executions /
  45 proposals restated).
- [ ] **[W: gate 8]** Start the supervisor through the established launch
  mechanism; confirm from **process state + `loop_state.json` +
  `loop_events.jsonl`** — not from intent.
- [ ] **[W]** Run the loop: proposals → validation → execution →
  adjudication → ledger rows, every attempt recorded including failures;
  holdout sealed; all stops armed.
- [ ] **[W]** At campaign end: campaign-end multiplicity record computed
  over complete families (or every provisional signal defaulted to
  INCONCLUSIVE, fail-closed), then final report.

## Parallelization summary

| Can run simultaneously | Must be strictly sequential |
|---|---|
| Review solicitation ∥ gate-3 implementation ∥ stop-count/Tier-2 written resolutions ∥ checker tooling | assessment → D2 → C-3 → amendment applied → freeze approval → pin+fingerprint → gate 7 → gate 8 → launch → campaign-end multiplicity record |

The critical path once the review lands is therefore:
**assess → D2/C-3 → (implementation already done, if gate 3 was granted) →
freeze → verify → launch.** Every step that can be pre-staged has been.

## Status — 2026-10-12 (end of day)

- [done] **[H]** Gate 3 granted for the **D2-independent subset** only
  (`…/HARNESS_V1_1_0_GATE3_AUTHORIZATION_RECORD_2026_10_12.md`).
- [done] **[W]** Subset implemented and tested: Holm + families +
  campaign-end record, firewall, C-2, both stops + correspondence test,
  census validator + draft manifest, freeze-integrity/preservation tests.
  Suite **311 tests, OK, exit 0**.
- [still open] **[H]** the review (nothing sent — no channel exists here).
- [still open] **[W]** primitive activation + 1.1.0 run modes — needs its
  **own** authorization; deliberately not done under the subset grant.
- [still open] **[H]** stop-count conflict ruling; Tier-2 residual ruling;
  freeze approval; launch authorization.

Pre-flight command for every later gate:
`py -3 -X utf8 autonomous_agent/launch_readiness_check.py` — today it
reports **19 PASS / 2 BLOCKED / 8 HUMAN → exit 2 (NOT READY)**, and a
fully-compliant fixture tree reports exit 0 (READY), so a non-zero exit is
informative rather than structural.
