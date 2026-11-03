# Phase D blind evaluation protocol — v1 (FROZEN)

**Frozen: 2026-10-29, before any live Meta benchmark inference.**
**Status: FROZEN. Append-only.** This protocol governs how the four planned
Meta paired runs are scored. It does not authorize any live request.

Related, frozen:
[rubric v1](phase_d_blind_scoring_rubric_v1.md) ·
[experiment protocol v2](phase_d_meta_protocol_revision_v2_2026-10-29.md) ·
[RESULTS.md](RESULTS.md) · harness
[meta_paired_continuation_benchmark.py](meta_paired_continuation_benchmark.py).

## 1. Roles and materials

**Benchmark operator** runs the benchmark, preserves raw traces, builds the
masked packets, holds the sealed condition key, and performs the unblinded join.
**Evaluator** scores the four investigations from condition-masked material
only, and never opens raw traces or the sealed key.

The evaluator receives exactly:

1. [phase_d_blind_scoring_rubric_v1.md](phase_d_blind_scoring_rubric_v1.md);
2. this protocol;
3. the four sheets in `phase_d_blind_scoring_sheets/` (`run-01.md` …
   `run-04.md`);
4. after each run, one condition-masked evidence packet per sheet.

The evaluator must not open: `benchmarks/.sealed/`, `benchmarks/` raw result
JSON files, the benchmark ledger, the condition mapping, or any file that
contains a run title, pair number, condition, request payload, token count,
cost, or timestamp.

## 2. Neutral identifiers and randomized order

- Before any run, each of the four planned runs is assigned a neutral label
  `RUN-01` … `RUN-04`. The label is unrelated to condition, pair, or run order.
- The four labels define the **presentation order** 1 → 4. That order is a
  system-random permutation of the four planned runs, generated once and stored
  only in the sealed key.
- Sheets contain only the neutral label and presentation position. Filenames
  are `run-01.md` … `run-04.md`; no condition, pair, model, or payload word
  appears in any filename or sheet metadata.
- The condition key lives in `benchmarks/.sealed/` (Git-ignored, never part of
  the scoring packet) and maps label → pair + condition. Its SHA-256 is recorded
  in [phase_d_blind_freeze_manifest_v1.json](phase_d_blind_freeze_manifest_v1.json)
  before inference, so it cannot be swapped unnoticed.

**Blinding is procedural, not cryptographic.** Anyone with repository access
could open the sealed file; the evaluator is instructed and trusted not to.
The key is excluded from version control and from every scoring artifact.

## 3. Condition-masked evidence packet

After each run, the operator builds a packet **from the raw trace, by copying —
never by editing the raw trace**. The packet must contain only:

| Included | Excluded |
|---|---|
| Neutral run label | Condition name/value |
| Final assistant message text | Investigation title and run id |
| Parsed structured summary block (if any) | Pair number and run order timestamps |
| Validator outcome: first attempt and post-repair, errors verbatim | Condition-specific request payloads (`recorded_context`, `context_source`, continuation instructions) |
| Ordered recorded actions: tool name, status, arguments, result, error, action id | Provider model id, base URL, request ids, response ids |
| Hypothesis roster: id, text, status | Token counts, cached tokens, cost, latency, ledger |
| Budget counters: tool calls used/max, iterations used/max | Payload character sizes and file paths |
| Provider response completion status (`completed` / `incomplete` / other) | HTTP headers, authorization data, retry/error bodies |

The packet is a **new file** under the evaluator's packet directory; raw traces
in `benchmarks/phase_d_*.json` remain untouched. The freeze manifest records
the SHA-256 of every raw trace that existed at freeze time.

### Unavoidable leakage (disclosed, not denied)

Raw transport payloads would identify the condition immediately, so they are
excluded. Residual clues can still exist inside model prose (for example, a
summary that refers to "the state delta" or to re-reading the full context), in
the shape of recorded actions, or in the amount of evidence gathered. Complete
blinding is therefore **not claimed**. The evaluator:

- scores only from the packet, never from raw traces;
- records any clue about the experimental condition in the sheet's "Blinding
  integrity note" **without guessing the condition**;
- reports those notes in the unblinded analysis as limitations.

## 4. Independent scoring procedure

1. Score runs one at a time in presentation order (`run-01` → `run-04`).
2. Do not open another sheet, compare runs, or inspect token/cost data while
   scoring the current run.
3. Score the six dimensions using the frozen rubric; write an evidence-based
   justification for every score (action id, recorded field, or absence).
4. Record structured-summary validity: first-attempt valid/invalid and
   post-repair valid/invalid, separately. A valid format earns **zero** quality
   points by itself.
5. Record execution and evidence facts from the packet: diagnostic tools
   executed, proposed-only diagnostics, failed tools, unavailable evidence, and
   tool budget used/max.
6. Complete the numeric-accuracy worksheet: reported number, recorded source,
   match basis. Mark unsupported numbers as unsupported; do not correct them.
7. If the packet contains no scorable final message, mark the sheet
   `not_scorable`, record why, and assign no dimension scores. Report it
   separately from zeros.
8. After all four sheets are complete, compute totals, sign/date each sheet, and
   freeze them: record the SHA-256 of each sheet (and the scoring timestamp) in
   `phase_d_blind_scores_frozen_v1.json`. No sheet may be edited after this
   record is written.

## 5. Unblinding

Unblinding happens only when all four sheets are frozen:

1. Recompute the SHA-256 of the sealed condition key and compare it with the
   digest in the freeze manifest. **Stop if it differs**; do not guess or
   reconstruct a mapping.
2. Open the key and join label → pair + condition.
3. Report the join. **Do not re-score.** If a scoring error is discovered after
   unblinding, record it as a disclosed deviation; do not silently revise the
   sheet.
4. If the key is missing, the campaign is reported as **unblinded/void for the
   quality comparison** rather than reconstructed from memory.

## 6. Comparison and reporting

After the join, report per run and per pair:

- each dimension score and the **0–12 total**;
- **Full average** and **Delta average** quality (means of the four totals,
  excluding `not_scorable` runs and stating the exclusion);
- the **two paired differences** (Delta − Full), listed individually, plus the
  mean paired difference;
- **structured-summary validity separately**: first-attempt valid count and
  post-repair valid count per condition, plus repair attempts;
- **evidence coverage** and **diagnostic execution**: distinct evidence-bearing
  tools executed vs attempted, diagnostic calls executed vs proposed-only;
- **incomplete-response frequency** and **repair frequency**;
- **provider-reported input tokens, cached input tokens, output tokens, and
  estimated cost** per condition (estimate only, never a billed amount).

### Decision rule (unchanged, pre-registered)

> **Retain Phase C Delta only if measured Meta-billed input-token savings are
> demonstrated at equal-or-better investigation quality.**

- Token savings without equal-or-better quality do **not** satisfy the rule.
- Quality parity without measured Meta input-token savings does **not** satisfy
  the rule.
- With two pairs, report direction and magnitude only. **No p-values, no
  "statistically significant", no confidence interval presented as inference.**
- Groq results are not evidence of Meta billing behavior and are not used in
  this decision.

## 7. Reproducibility and integrity

- The rubric, this protocol, the four sheets, and the sealed key were created
  before any live request; the key digest and raw-trace digests are frozen in
  the manifest.
- Raw traces are append-only: packets are copies, scoring never rewrites a
  trace.
- The same rubric and anchors apply to both conditions; no condition-specific
  interpretation is permitted.
- Any deviation (missed packet field, late clue, missing key, scoring error) is
  recorded in the RESULTS entry, not hidden.
- This protocol is offline-only until the owner gives separate explicit
  approval for live inference.
