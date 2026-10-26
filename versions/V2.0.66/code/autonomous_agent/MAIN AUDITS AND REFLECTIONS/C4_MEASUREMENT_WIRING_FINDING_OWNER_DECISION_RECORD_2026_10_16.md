# OWNER DECISION RECORD — Campaign 4 Measurement-Wiring Finding — 2026-10-16

**Status: OWNER DECISION RECORDED. Accepts the implementation-gap
finding; adopts no method, authorizes no retroactive change, authorizes no
new campaign. The holdout remains SEALED.**

## 0. Verbatim directive (project owner, 2026-10-16, this workflow thread)

> ### Owner Decision — Campaign 4 Measurement-Wiring Finding
>
> **Decision: Accept the audit finding. Do not treat the absent per-cell
> measurements as evidence of statistical success.**
>
> The campaign-end multiplicity record and final archive are retained as
> historical, append-only audit artifacts. The recorded `unavailable`
> status of all 24 family members accurately reflects the absence of the
> required per-member measurements, subject to the verified C-2 Option A
> implementation.
>
> The historical pooled-metric promotion decisions remain recorded as
> executed. Their existence does not establish that the promoted versions
> satisfied the planned per-cell/per-rung statistical evaluation. No
> retrospective changes to promotion decisions are authorized by this
> finding alone.
>
> Before another campaign depends on the Holm families or per-cell IUT
> ladders, the production measurement path must be wired and verified end
> to end. The acceptance test must demonstrate that measurements produced
> during actual execution reach the persisted per-member records, are
> associated with the correct family and comparison, and feed the intended
> multiplicity procedure. The system must fail closed if any required
> measurement is missing.
>
> No unavailable result may be reclassified as a successful test. No
> historical measurement may be reconstructed or substituted without an
> explicit, documented, authorized procedure. The holdout remains sealed.
>
> This decision accepts the implementation-gap finding; it does not
> constitute statistical approval, retroactive validation of the campaign,
> or authorization to launch another campaign.

No handwritten signature is claimed; provenance is the owner's written
message in this project's workflow thread, transcribed verbatim above by
the coding agent (same constraint and method as
`stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md` §0).

## 1. What this decision accepts (evidence the finding rests on)

- **The finding:** the v1.1.0 per-cell/per-rung evaluators
  (`recipe_harness.evaluate_regime_cells` / `evaluate_horizon_rungs` /
  `evaluate_purge_rungs`) were never invoked by the production experiment
  path; their only callers are unit tests. The executed v1.0.0 study
  pipeline emits pooled metrics only.
- **Verification scope (2026-10-16):** all 12 retained poolable
  workspaces' `evaluation.json`, all 32 C4 ledger adjudication rows, and
  the loop memory files — zero per-member deltas, CIs, or week-level
  contributions exist anywhere. The only `above_sma` strings are the
  feature name `spy_above_sma200`.
- **Durable artifacts referenced (append-only, never to be rewritten):**
  - Campaign-end multiplicity record:
    `autonomous_agent/state/campaign_end_multiplicity.jsonl` — 24 members
    (regime 8, horizon 12, complexity 4; purge 0), all `unavailable`
    (C-2 Option A, effective p = 1.0), zero formal refutation labels;
    ledger pinned `d97da2680245be8a690ab097d1e25b1ac99b7668b74ce064cf8068f6a51f9ba8`.
  - Final archive:
    `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_4_FINAL_ARCHIVE_2026-10-16/`
    (README_FINAL.md §4 documents the finding; SHA256SUMS.txt verified,
    12 entries).
  - Builders: `stat_validation_h10/campaign_end_2026_10_16/
    build_multiplicity_record.py`, `build_final_archive.py`.

## 2. Binding requirements carried forward (owner-verbatim, restated as constraints)

1. **Precondition for any future Holm-family- or per-cell-IUT-dependent
   campaign:** wire the production measurement path and verify it end to
   end. The acceptance test must demonstrate all three links:
   (a) measurements produced **during actual execution** reach the
   persisted per-member records, (b) each measurement is associated with
   the **correct family and comparison**, (c) the persisted members **feed
   the intended multiplicity procedure** (the campaign-end record).
2. **Fail closed:** the system must halt/refuse if any required
   measurement is missing — never silently degrade to pooled-only
   evaluation while family membership is declared.
3. **No reclassification:** an `unavailable` member may never be
   re-labeled a successful test; the appended record stands as written.
4. **No retroactive reconstruction:** no historical measurement may be
   reconstructed or substituted without an explicit, documented,
   authorized procedure (a future owner act with its own record).
5. **No retroactive promotion changes:** the 26 promotions
   (V2.0.36 → V2.0.61) remain recorded as executed; this finding does not
   invalidate or revise them, and nothing authorizes revising them.
6. **Holdout:** remains SEALED, uses = 0.

## 3. What this decision does NOT establish (owner-verbatim)

- Not statistical approval of the campaign.
- Not retroactive validation of the campaign.
- Not authorization to launch another campaign.

## 4. Recording metadata

| Field | Value |
|---|---|
| Decided by | project owner (written directive 2026-10-16 in the workflow thread) |
| Recorded by | coding agent (verbatim transcription; no signature claimed) |
| Date recorded | 2026-10-16 |
| Campaign affected | `campaign-4-continuous-2026-10-14` (ended 2026-10-16T22:10:04Z, `EXECUTION_BUDGET`, 32/32) |
| Supersedes | nothing; complements README_FINAL.md §4 and the append-only multiplicity record |
| Owner signature on H-10 decision record | still outstanding (`stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md`), unaffected by this record |
