# H-10 D2 — SUBMISSION CHECKLIST (independent statistical review)

Prepared: 2026-10-12 by the coding agent. Status before and after this file:
**REVIEW NOT YET OBTAINED.** No reviewer has been contacted, no message has
been sent, no fee has been offered, and nothing in this checklist is an
assessment. This file only makes the handoff mechanically unambiguous.

## 1. Integrity verification performed 2026-10-12 (all green)

| Check | Method | Result |
|---|---|---|
| Bundle hash | `sha256sum` of the zip | `ee345dab3a587b5183e3d80b7a45f2283047f6d1d972c6eff5fc3bb47b74bb03` — matches the value recorded in `H10_OWNER_AUTHORIZATION_RECORD_2026_10_11.md` §5 |
| Archive integrity | `zipfile.testzip()` | no corrupt entry; **13/13 entries** readable |
| Manifest vs archive contents | SHA-256 recomputed per entry | **11/11 hashed entries match**, 0 missing, 0 mismatch |
| Archive vs working tree | SHA-256 of each bundled file against the repository copy | **11/11 byte-identical**, 0 drifted, 0 absent |
| Request file present | direct read | `REVIEW_REQUEST_READY_TO_SEND.txt` (8,160 bytes), Part 1 message + 4 routes + post-return steps |
| Six questions present | direct read of Part 1 | all six present, verbatim, with a stated deliverable and scope/conflict-of-interest requirements |
| Packet sufficiency | `H10_D2_EXTERNAL_REVIEW_PACKET.md` §1–§10 | statistic + null, evidence classification, SIM-1…SIM-5 protocols, CI-vs-p question, unverifiable exchangeability assumption, dependence structures *not* simulated, Holm families + missing-member rule, known discrepancies, six questions + adoption criteria, provenance table |

## 2. Exact repository-relative paths (submit exactly these)

Attachment (one file):

- `stat_validation_h10/H10_D2_REVIEW_SUBMISSION.zip` — 64,349 bytes,
  SHA-256 `ee345dab…bb03`. Contains the packet, evidence report,
  `simh10.py`, `run_sim.py`, `run_sharded_sim2.sh`, six `results/*.json`
  summaries, the manifest, and the outgoing request text.

Supporting files you read but do not send:

- `stat_validation_h10/review_submission/REVIEW_REQUEST_READY_TO_SEND.txt`
  — paste Part 1 verbatim; Part 2 lists routes A–D.
- `stat_validation_h10/review_submission/BUNDLE_MANIFEST.txt` — the
  reviewer-side integrity list (also inside the zip).
- `stat_validation_h10/H10_D2_EXTERNAL_REVIEW_PACKET.md` — §9 holds the
  six questions in packet form.

Destination for the returned deliverable:

- `stat_validation_h10/D2_EXTERNAL_REVIEW_ASSESSMENT.md` — the written
  assessment must land here (or another path you name in writing), then be
  reported to the workflow.

## 3. The six review questions (identical in the message and packet §9)

1. Does the proposed sign-flip test's null (sharp within-week arm-label
   exchangeability) match the intended scientific claim, given that the
   claim of interest concerns the aggregate AUC difference rather than the
   sharp null?
2. Do shared-training dependence (both arms' OOF predictions from models
   fitted on overlapping training windows) and week-to-week serial
   dependence materially undermine marginal calibration? Would you
   recommend block-level flips (per the bootstrap's 4-week block unit) or a
   different construction?
3. Do the simulations (SIM-1…SIM-5, proxy frames of 800–3,600 rows versus
   the real ~61k-row frame) adequately test the proposed use case? What
   cell, frame size, or mechanism is missing in a way that blocks
   adoption?
4. Is the documented CI-vs-p disagreement reconciliation statistically
   defensible: formal decisions via Holm-adjusted p-values only, with the
   percentile-bootstrap CI kept as a disclosed provisional/effect-size
   functional?
5. Are the Holm family definitions and the missing-member rule (an
   unavailable member test counts toward family size m and is assigned
   p = 1.0, rendered "unavailable", never formally REFUTED) coherent and
   conservative as claimed?
6. What additional evidence, if any, is necessary before adoption?

## 4. Pre-send checklist (owner executes; agent has done none of these)

- [ ] Reviewer is independent of this project's authorship and of the
      simulation design.
- [ ] Scope, confidentiality/non-redistribution, deliverable (a written
      assessment answering the six questions), fee, and turnaround agreed
      **in writing before** the bundle or any payment is shared.
- [ ] Reviewer confirms the bundle manifest hashes on receipt
      (expected: 11/11 as verified above).
- [ ] Reviewer is told plainly: this is a methods-and-code audit, the
      simulation battery is a falsification exercise on synthetic data, and
      it cannot establish real-data validity.
- [ ] Reviewer's name, affiliation, date engaged, and terms recorded in
      your own notes (do **not** edit any H-10 file to record an engagement
      that has not produced a written assessment).
- [ ] Returned assessment placed at the path in §2 and reported to the
      workflow.

## 5. Two known discrepancies in the outgoing material (disclosed, not fixed)

Both are disclosed rather than repaired because correcting either one
requires rebuilding the bundle, and the bundle hash `ee345dab…bb03` is
already recorded as verified in
`stat_validation_h10/H10_OWNER_AUTHORIZATION_RECORD_2026_10_11.md` §5, in
the packet's own provenance table, and in earlier campaign reports.

1. **Bundle size text.** `REVIEW_REQUEST_READY_TO_SEND.txt` Part 2c says
   "H10_D2_REVIEW_SUBMISSION.zip (~200 KB)". The actual file is 64,349
   bytes (~63 KB). Cosmetic; integrity is established by the manifest
   hashes, not by the size estimate. *If you prefer an accurate file
   size, say so and the bundle will be rebuilt and every recorded hash
   re-pinned in one pass.*
2. **Stale flake status inside the bundle.** `BUNDLE_MANIFEST.txt`
   ("WHAT THIS BUNDLE IS NOT") and packet §8 state that the
   governance-suite test flake "remains open, identity not captured".
   That was true when the bundle was sealed on 2026-10-11 and is no
   longer: the flake was dispositioned the same day with a test-only fix
   and a 10/10-consecutive-green acceptance loop. Evidence:
   `autonomous_agent/MAIN AUDITS AND REFLECTIONS/GOVERNANCE_SUITE_FLAKE_EVIDENCE_2026_10_11.md`
   (SHA-256 `725046614c4dab73…`). *Recommended:* attach that file
   alongside the zip as a dated addendum, or mention in the covering
   note that the flake was closed after bundling — a strictly-more-
   accurate status than the bundle contains. Do not describe the
   assessment as covering it; the reviewer was never sent it.

## 6. What this checklist does not do

It does not contact anyone, choose or name a reviewer, spend anything,
imply that a review exists, close D2 or C-3, authorize implementation,
freeze the C4 draft, or authorize launch. Status remains
**REVIEW NOT YET OBTAINED / D2 DEFERRED / C-3 PENDING**.
