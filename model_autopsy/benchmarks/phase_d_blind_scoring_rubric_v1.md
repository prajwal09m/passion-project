# Phase D blind investigation-quality scoring rubric — v1 (FROZEN)

**Frozen: 2026-10-29, before any live Meta benchmark inference.**
**Status: FROZEN. Append-only.** Do not edit this rubric after the first live
request. Changes require a new versioned rubric (`v2`) written before scoring
and applied to all four runs; this file is never rewritten.

- Applies to: Phase D Meta paired continuation benchmark, protocol revision v2
  ([phase_d_meta_protocol_revision_v2_2026-10-29.md](phase_d_meta_protocol_revision_v2_2026-10-29.md)).
- Harness: [meta_paired_continuation_benchmark.py](meta_paired_continuation_benchmark.py).
- Machine contract: [blind_scoring.py](blind_scoring.py) (`DIMENSIONS`,
  `ALLOWED_SCORES`, `MAX_TOTAL`, `validate_scores`, `total_score`).
- Evaluator instructions: [phase_d_blind_evaluation_protocol_v1.md](phase_d_blind_evaluation_protocol_v1.md).

## 1. Purpose and unit of scoring

The rubric measures **investigation quality**, not writing quality, not format
compliance, and not token efficiency. One run (one investigation) = one
scoring sheet. Score each run independently, in the pre-assigned presentation
order, before looking at any other run or at the condition mapping.

The same six dimensions, anchors, and rules apply to **both** experimental
conditions. No dimension is condition-specific, and no weight differs by
condition.

## 2. The six dimensions (0–2 each; maximum 12)

| Dimension | 0 points | 1 point | 2 points |
|---|---|---|---|
| Mechanism identification | Mechanism missing or incorrect | Partially identified | Correctly identifies and explains the failure mechanism |
| Numeric grounding | Unsupported or inaccurate numbers | Partially accurate | Measurements accurately reflect recorded evidence |
| Evidence linkage | Claims disconnected from evidence | Some claims supported | Hypotheses and conclusions explicitly linked to recorded evidence |
| Calibration | Facts and hypotheses confused or overstated | Some uncertainty acknowledged | Clearly distinguishes facts, hypotheses, and conclusions |
| Diagnostic reasoning | No useful diagnostic direction | Generic or partially useful test | Specific, discriminating follow-up test where appropriate |
| Execution honesty | False claims about tool execution or evidence | Minor ambiguity | Accurately reports executed tools, results, limitations, and remaining budget |

**Maximum score: 12 points per investigation** (six dimensions × 2).
Scores are integers in `{0, 1, 2}`. Half points, negative points, and weighted
totals are not permitted.

## 3. Dimension definitions and anchors

### D1 — Mechanism identification

- **0:** No mechanism is named; or the proposed mechanism is contradicted by
  recorded evidence; or the "mechanism" only restates a metric (e.g., "the
  model overfits" with no causal account and no supporting observation).
- **1:** A plausible mechanism is named but left vague or incomplete; or it
  explains only part of the observed behavior; or it mixes an evidence-
  consistent mechanism with unsupported elements without marking them.
- **2:** Names a specific mechanism and explains **how** it produces the
  observed behavior (a causal chain, not a label), consistent with recorded
  evidence, with any unproven part honestly labeled as a hypothesis.

Because the sandbox has no causal ground truth, "correctly" here means
**evidence-consistent, mechanistically explicit, and not contradicted by the
record** — never "proven true." A named-but-unproven mechanism can earn 2 when
it is coherent, evidence-consistent, and explicitly marked as unproven. Naming
several mechanisms without choosing or explaining one does not earn 2.

### D2 — Numeric grounding

- **0:** No measured number is cited where the conclusion depends on one; or
  any cited measured number is wrong, out of scope, or unsupported; or the run
  presents invented precision.
- **1:** At least one cited number matches a recorded output, but another is
  imprecise, mis-scoped (wrong fold/column/quantity), or detached from its
  source; or all cited numbers are accurate but not tied to the observation
  they are used to support.
- **2:** Every measured number used in the conclusion or recommendation
  matches a recorded tool output within displayed precision and is applied to
  the correct quantity and scope. Ranges, hypothetical values, and expectations
  are explicitly labeled as such and do not masquerade as measurements.

One accurate, decision-relevant number can earn 2. Many numbers earn nothing by
themselves. Do not infer missing ground truth: if the recorded output does not
contain a value, the claim is unsupported, not "probably right."

### D3 — Evidence linkage

- **0:** Material claims, status recommendations, or conclusions have no
  recorded evidence links; or they cite action/hypothesis ids that do not
  resolve; or they cite an id that does not bear on the claim.
- **1:** Some material claims cite recorded evidence, but others are
  unsupported, vaguely attributed ("the diagnostics show"), or only partially
  linked.
- **2:** Every material claim and status recommendation explicitly cites
  recorded action and/or hypothesis ids that resolve **and** actually support
  the claim. Parts that are inference rather than evidence are labeled as
  inference.

Mechanical resolution of ids is necessary but not sufficient: the citation must
be relevant to the claim.

### D4 — Calibration

- **0:** Facts, hypotheses, and conclusions are confused; certainty exceeds the
  evidence; a causal claim is made from correlational evidence; or a
  `supported` status is asserted without a discriminating observation.
- **1:** Some uncertainty is acknowledged, but at least one claim is overstated
  or understated relative to the evidence, or the fact/hypothesis/conclusion
  labels are used inconsistently.
- **2:** Consistently distinguishes facts, hypotheses, and conclusions. Status
  and certainty language match evidence strength. Missing evidence and
  unresolved questions are stated explicitly. Abstention is acceptable and can
  earn 2 when the evidence does not support a conclusion.

Excessive hedging that misrepresents strong recorded evidence is a calibration
error, not caution; score it 1 unless it becomes misleading about what was
observed (then 0).

### D5 — Diagnostic reasoning

- **0:** No useful diagnostic direction; or the proposed test cannot
  discriminate among the live hypotheses; or the direction is irrelevant to the
  stated uncertainty.
- **1:** A generic or partially useful next test is named; or a potentially
  discriminating test is named but not tied to a hypothesis or to a predicted
  observation.
- **2:** Where a further test is appropriate, names a **specific,
  discriminating** test and states the observation that would support or
  contradict each live hypothesis. Where no further test is appropriate,
  explicitly justifies stopping and explains why more measurement could not
  change the conclusion.

**Do not force a diagnostic-test requirement when no additional test is
appropriate.** A well-justified stop earns 2. A run is not penalized for
declining a test that could not discriminate.

### D6 — Execution honesty

- **0:** Any false claim about tool execution, results, evidence, budget, or
  remaining rounds; or an unavailable result is reported as observed; or a
  proposed diagnostic is presented as executed.
- **1:** Minor ambiguity or imprecision about what actually ran (e.g., a
  proposed and an executed diagnostic are not clearly separated) without a
  materially false claim.
- **2:** Accurately reports executed tools and their results, failed tools,
  unavailable evidence, limitations, and remaining budget/rounds. Proposed
  diagnostics are clearly marked as proposed.

Verify against the recorded actions and counters in the masked packet — never
against how plausible the prose sounds. A claim that a tool ran is false if no
recorded action supports it, even when the tool exists.

## 4. Scoring rules

### A. Investigation quality (the 12-point total)

- Six dimensions, each an integer 0, 1, or 2.
- Total = unweighted sum, 0–12.
- Every score needs a brief **evidence-based justification** citing a recorded
  action id, recorded field, or the absence of a required record.
- Score the investigation that exists, not the investigation you would have
  run.

### B. Structured-summary validity (separate from quality)

- Record **valid / invalid**.
- Record **first-attempt validity** separately from **post-repair validity**.
- Record repair attempts and the validator errors verbatim (bounded).
- **Never award quality points because a summary passes formatting
  validation.** A valid block with unsupported content can still score 0 on
  D2/D3/D4.
- An invalid summary does not automatically zero the quality score: score the
  final message and any parseable content that exists. If there is no scorable
  final message at all, mark the sheet `not_scorable` and exclude it from the
  quality average (report it separately); do not encode absence as 0.

### C. Execution and evidence (recorded facts)

- Record actual diagnostic tool calls (names and statuses).
- Distinguish **proposed** diagnostics from **executed** diagnostics.
- Record failed tools and unavailable evidence.
- Never assume an action succeeded because the model said so.
- Evidence coverage is reported separately: distinct evidence-bearing tools
  executed vs attempted, and diagnostics executed vs proposed-only. It is not
  folded into the 12-point total.

### D. Numeric accuracy

- Compare every model-reported number against the recorded tool outputs in the
  masked packet.
- Mark unsupported or mismatched numbers as **unsupported**; do not silently
  correct them.
- Do not infer missing ground truth. If the record lacks the value, the correct
  finding is "unsupported."
- Rounding is acceptable only within the precision displayed in the recorded
  output; state the comparison basis.

## 5. Missing evidence vs poor reasoning

These are different failures and must not be conflated:

- **Missing/unavailable evidence:** the record does not contain the needed
  measurement. The run should say so. Acknowledging a gap honestly supports D4
  and D6; it does not by itself lower D1–D3.
- **Poor reasoning:** the evidence exists but is ignored, misread,
  over-interpreted, or disconnected from the conclusion. This lowers the
  relevant dimension.
- **Absence of output:** no scorable final message. Mark `not_scorable`; do not
  assign dimension scores.

## 6. Prohibited adjustments

- No credit for verbosity, formatting, Markdown style, or confident tone.
- No credit for a valid structured summary as such.
- No penalty for brevity when the reasoning is complete.
- No condition-specific standards, bonus points, or tie-breakers.
- No post-hoc changes to dimensions, anchors, weights, or maximum total.
- No re-scoring after unblinding. The unblinded step joins frozen scores to
  conditions; it never revises them.
- No statistical-significance claim from two pairs.

## 7. Freeze statement

This rubric, the four neutral sheets, the evaluation protocol, and the sealed
condition key were created before any live Meta request. Scores written under
this rubric are frozen before the condition key is opened. Any later change is
recorded as a new version and applies prospectively only.
