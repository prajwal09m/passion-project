# Phase D Meta scoring-readiness audit — 2026-10-29

**Offline, read-only. No scoring, no unblinding, no inference.**
**Operator-only:** this report contains evidence details and must not be given
to the blind evaluator as scoring material.

Scope: the four preserved run snapshots, the authoritative
[phase_d_meta_results.json](phase_d_meta_results.json), the raw run manifest,
the frozen [rubric](phase_d_blind_scoring_rubric_v1.md), the
[evaluation protocol](phase_d_blind_evaluation_protocol_v1.md), and the four
scoring sheets.

## 1. Label constraint (important)

The pre-registered `RUN-01`…`RUN-04` ↔ run association is sealed. Per the
explicit prohibition, I did **not** open or inspect the condition key or the
sealed post-run index. A per-`RUN` inventory would require that association and
is therefore not produced here.

This audit uses neutral **audit artifact IDs A1–A4**, assigned by sorted
snapshot-directory name. They are unrelated to the `RUN` labels. The operator
may join A1–A4 to `RUN` labels later using the sealed index when assembling
packets; that join must not be shown to the evaluator.

### Packet hygiene (no labels disclosed)

The snapshot database carries a condition-bearing investigation title, and the
report carries condition metadata. Neither is reproduced here. Any packet must
be built from the blind-sheet extraction (summary, actions, hypotheses, budget)
and must omit the investigation title, condition fields, and run-order metadata.
The A1–A4 → `RUN` relabeling must happen only in operator-side bookkeeping, not
in evaluator-facing files.

## 2. Method

- Read-only SQLite queries against the four preserved snapshots; JSON reads of
  the report and manifest.
- Verified recorded actions and hypotheses against report counts (all match).
- Examined final assistant-message availability, final summary validity, and
  whether the preserved content contains the evidence each rubric dimension
  requires.
- The report was read for run-level evidence; its condition field was not
  used in any scoreability or fair-entry determination, and no condition label
  is reproduced in this audit. No scores were assigned.

## 3. Evidence inventory

`Captured responses` counts the snapshot's `meta_response` events; `Report
requests` is the report's provider-response list for the same investigation
(repairs included). A smaller captured count means the snapshot ends before
the last request(s); it does **not** mean actions are missing.

| Artifact | Snapshot dir | Report requests / captured | Incomplete responses | Actions | Hypotheses | Repairs t1/t2 | Final summary | Final assistant message |
|---|---|---|---|---|---|---|---|---|
| A1 | `ma-phase-d-run-4uqmerzq` | 6 / 5 | 2 | 5 | 3 | 0 / 1 | invalid | **absent** — last response is tool-call-only; report head length 0 |
| A2 | `ma-phase-d-run-d59tw190` | 5 / 3 | 1 | 4 | 3 | 1 / 0 | **valid** | **partial** — report head 400 chars; final snapshot response absent; conclusion 116 chars |
| A3 | `ma-phase-d-run-f5quqyhn` | 7 / 5 | 3 | 5 | 3 | 1 / 1 | invalid | **absent** — last response is tool-call-only; report head length 0 |
| A4 | `ma-phase-d-run-h5gj3nn0` | 6 / 4 | 4 | 4 | 3 | 1 / 1 | invalid | **complete** — 546-char event detail (below the 600-char cap); report head capped at 400 |

All recorded actions and hypotheses are present in every snapshot; the missing
items are final turn-2 message/repair/usage events. The report is authoritative
for final run-level outcomes and usage, but it is **not** a substitute for
missing investigation content. Usage is not an input to the six quality
dimensions; its report-level rollup is complete and is not a scoring gap.

## 4. Dimension scoreability

`S` = scorable; `P` = partially scorable; `U` = unscorable.
Missing evidence is **not** a zero score.

| Dimension | A1 | A2 | A3 | A4 |
|---|---|---|---|---|
| D1 Mechanism identification | U | S | U | S |
| D2 Numeric grounding | U | P | U | S |
| D3 Evidence linkage | U | U | U | S |
| D4 Calibration | U | S | U | S |
| D5 Diagnostic reasoning | U | U | U | S |
| D6 Execution honesty | U | P | U | S |

### A1 — all dimensions unscorable

- No final assistant message exists in the preserved record: the last turn-2
  response is tool-call-only, the report's final-message head is empty, and the
  final summary is invalid. The failed repair text is not preserved.
- A valid summary from **turn 1** is preserved, but it is not the final output
  and is not used as a substitute. It cannot make D1/D3/D4/D5 fair.
- Actions/hypotheses are complete, but without a final claim set D6 cannot be
  judged.
- **Fair entry: no. Mark `not_scorable`; exclude from the quality average.**

### A2 — two fully scorable dimensions, two partial, two unavailable

- Final summary is **valid**; the report preserves its conclusion and a
  400-character final-message head. The complete final turn-2 message and
  summary block are not preserved (snapshot ends before the final response).
- **D1 scorable:** the final conclusion explicitly abstains; absence of a
  mechanism can be judged without guessing.
- **D2 partial:** the preserved head's structural counts (41,221 rows, three
  folds) match the recorded `artifact_summary`; no diagnostic numbers are in
  the preserved final content, and the complete summary may contain more.
- **D3 unscorable:** `status_recommendations` and `basis` ids from the final
  summary are absent; the preserved conclusion/head cite no action ids.
- **D4 scorable:** the final head labels Fact / Hypothesis / Conclusion and the
  conclusion is explicitly unresolved; the core calibration judgment is
  possible. Missing uncertainties/status entries would only add detail.
- **D5 unscorable:** `recommended_next` is absent, so whether a discriminating
  test or justified stop was offered cannot be judged.
- **D6 partial:** preserved claims ("three competing explanations proposed";
  "no discriminating metric or calibration result was recorded") match the
  recorded actions (three proposals plus one artifact summary); the rest of the
  final message is missing.
- **Fair entry: no complete six-dimension score.** D3/D5 are unavailable, so a
  12-point total would be incomparable. Descriptive use only, with missing
  flags.

### A3 — all dimensions unscorable

- No final assistant message: last response is tool-call-only, report head is
  empty, final summary invalid; the failed repair text is not preserved.
- A valid **turn-1** repair summary (with numbers and recommendations) is
  preserved, but it is not the final output and is not used as a substitute.
- **Fair entry: no. Mark `not_scorable`; exclude from the quality average.**

### A4 — all six dimensions scorable

- Final assistant message is complete (546 chars). The structured summary is
  invalid, which the rubric explicitly allows: quality may be scored from the
  final message and parseable content.
- **D1:** final conclusion is present (fold-shift explanation demoted); whether
  a positive mechanism is identified can be judged.
- **D2:** per-fold AUCs, Brier score, bin counts, and bin gaps match the cited
  recorded action within the precision shown in the final message.
- **D3:** both cited identifiers resolve — action `1773fde2…` and hypothesis
  `1b5a7888…` exist in the same investigation.
- **D4:** Fact / Hypothesis / Conclusion labels are explicit in the final
  message.
- **D5:** no follow-up test or stop justification appears. The final message
  ends at its conclusion and is complete (546 < 600 chars), so the absence is
  not a truncation artifact and can be judged.
- **D6:** the factual claims about the cited action are verifiable; no
  execution claim contradicts the recorded actions.
- **Fair entry: yes**, as a complete six-dimension run, with the invalid summary
  recorded separately.

## 5. Fair-entry and comparison conclusion

- **A1 and A3:** `not_scorable` — no final assistant message. Missing evidence
  is not converted to zero; they are excluded, not scored low.
- **A2:** partially supported only — D1/D4 scorable, D2/D6 partial, D3/D5
  unscorable. It cannot yield a fair 12-point total or enter a paired quality
  comparison.
- **A4:** fully scorable — the only run that can enter the six-dimension
  quality comparison as planned.
- **All four runs do not support a valid quality comparison.** The evidence
  available is one fully scorable run, one partial run, and two not-scorable
  runs. Averages over this set would mix complete and incomplete evidence and
  would be biased by availability, not performance. The provider-reported
  token/cost side is complete, but the frozen decision rule requires
  equal-or-better investigation quality; that condition cannot be established
  from this evidence. No condition-level comparison is made here.

## 6. Exact missing evidence

| Artifact | Needed for fair scoring |
|---|---|
| A1 | Complete final turn-2 assistant message, final summary block, and any repair text. The turn-1 valid summary is not a substitute. |
| A2 | Complete final turn-2 assistant message and summary block: `status_recommendations` with `basis` ids, `uncertainties`, and `recommended_next`. The 400-char head and conclusion are insufficient for D3/D5. |
| A3 | Complete final turn-2 assistant message, final summary block, and any repair text. The turn-1 valid summary is not a substitute. |
| A4 | Nothing further for the six dimensions. A valid structured summary would be additional evidence but is not required. |
| All | Harness-native preservation of the final database state (final message, summary, repair, usage) before the frozen harness deletes its temporary directory. External snapshots cannot reliably catch the last commit. |

## 7. Non-actions and security

- No run was scored; no scoring sheet was filled.
- The sealed condition mapping and sealed post-run index were not opened,
  read, or inspected. The report's condition field was not used and no
  condition label appears in this report.
- No network request, API call, inference, or provider authentication occurred.
- No credential, `.env` content, authorization header, or environment dump was
  accessed or printed.
- No frozen rubric, protocol, scoring sheet, benchmark result, or raw artifact
  was modified. This audit is a new operator-only report.
- Verified after writing: the rubric, protocol, four scoring sheets, and
  `blind_scoring.py` match the freeze manifest; the report and all four
  snapshot hashes match `RUN_MANIFEST.json`; all frozen raw-trace hashes match.
