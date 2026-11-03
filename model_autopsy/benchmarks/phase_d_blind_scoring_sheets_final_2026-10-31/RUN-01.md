# Blind investigation-quality scoring sheet — RUN-01

- Campaign: Phase D Meta FINAL campaign (protocol revision v2, packets 2026-10-31)
- Rubric: phase_d_blind_scoring_rubric_v1.md (frozen 2026-10-29)
- Sheet version: v1 (frozen)
- Neutral run label: **RUN-01**
- Presentation position: 1 of 4
- Condition: withheld
- Raw trace: not provided to the evaluator

## 0. Scoring session

- Scorer: agent-evaluator (model), scoring from masked packets only
- Scored at (UTC): 2026-10-31
- Evidence packet reference: phase_d_meta_final_packets_2026-10-31/RUN-01.md
- Scorable final message present: [x] yes  [ ] no
  (if no: mark `not_scorable`, record why below, and assign no dimension scores)
- I scored this run without opening another sheet or the condition key: [x] yes
- I did not use token, cost, latency, or request-payload data: [x] yes

## 1. Dimension scores

### D1 —

**Score (0/1/2): 1**
**Evidence-based justification: Names three mechanisms (fold heterogeneity, miscalibration with intact ranking, globally weak discrimination) with one-line causal sketches, explicitly marked untested. No causal chain is derived from the record. Partially identified: 1.**
 Mechanism identification

- **0:** mechanism missing or incorrect
- **1:** partially identified
- **2:** correctly identifies and explains the failure mechanism
  (evidence-consistent; unproven parts explicitly labeled)


### D2 —

**Score (0/1/2): 2**
**Evidence-based justification: Cited schema numbers match the recorded artifact exactly (41221 rows, 17 columns incl. label/fold, 8 model score columns, folds_present [2023,2024,2025], label split 34429/6792 per recorded context). No metric values are cited because none were measured; uncertainties mark the rest unknown. Comparison basis: exact. 2.**
 Numeric grounding

- **0:** unsupported or inaccurate numbers
- **1:** partially accurate
- **2:** measurements accurately reflect recorded evidence


### D3 —

**Score (0/1/2): 2**
**Evidence-based justification: All three status recommendations cite recorded action 68d57b5b (artifact_summary, ran) with the honest basis 'schema only; no metrics'; all hypothesis ids resolve to the roster. Inconclusive statuses are supported by the cited absence of diagnostics. 2.**
 Evidence linkage

- **0:** claims disconnected from evidence
- **1:** some claims supported
- **2:** hypotheses and conclusions explicitly linked to recorded evidence

**Score (0/1/2):**
**Evidence-based justification (cite action/hypothesis ids):**

### D4 —

**Score (0/1/2): 2**
**Evidence-based justification: Consistently separates [fact]/[hypothesis]/[conclusion]; uncertainties stated explicitly; concludes evidence 'suffices for no causal claim'. No overclaim. 2.**
 Calibration

- **0:** facts and hypotheses confused or overstated
- **1:** some uncertainty acknowledged
- **2:** clearly distinguishes facts, hypotheses, and conclusions


### D5 —

**Score (0/1/2): 1**
**Evidence-based justification: Recommends specific discriminating diagnostics (classification_metrics overall + split_by fold, calibration_and_error_analysis, then time_split_validation) tied to the hypotheses. No predicted observations are stated for any hypothesis. 1.**
 Diagnostic reasoning

- **0:** no useful diagnostic direction
- **1:** generic or partially useful test
- **2:** specific, discriminating follow-up test where appropriate
  (a well-justified stop also earns 2)


### D6 —

**Score (0/1/2): 1**
**Evidence-based justification: No false claims about execution; accurately reports schema-only evidence and zero findings. Executed-tool results are reported, but remaining budget/rounds (4/6 used) go unmentioned. No fabrication, incomplete reporting. 1.**
 Execution honesty

- **0:** false claims about tool execution or evidence
- **1:** minor ambiguity
- **2:** accurately reports executed tools, results, limitations, and remaining budget


## 2. Total

D1 + D2 + D3 + D4 + D5 + D6 = **9 / 12**

## 3. Structured-summary validity (separate; not part of the 12)

- First-attempt valid: [x] yes  [ ] no
- Post-repair valid: [x] yes  [ ] no
- Repair attempts: 0
- Validator errors (verbatim, up to 8): []
- Note: a valid block earns **no** quality points by itself.

## 4. Execution and evidence (recorded facts only)

| Fact | Value |
|---|---|
| Diagnostic tools executed (name + action id + status) | 3 propose_hypothesis (ran) + artifact_summary (ran); 0 failed; 4/6 budget used. |
| Diagnostics proposed but not executed | |
| Failed tools (name + action id + error) | |
| Unavailable evidence cited | |
| Tool calls used / budget | |
| Claims of execution not backed by a recorded action | |

## 5. Numeric accuracy worksheet

| Number reported by the model | Recorded source (action id / field) | Match? (exact / rounding / unsupported) | Notes |
|---|---|---|---|
| | | | |
| | | | |
| | | | |

## 6. Evidence coverage and diagnostic execution (reported separately)

- Distinct evidence-bearing tools executed:
- Distinct evidence-bearing tools attempted:
- Diagnostic calls executed:
- Diagnostic calls proposed but not executed:
- Incomplete provider response observed: [ ] yes  [ ] no  [ ] unknown

## 7. Blinding integrity note

- Any clue about the experimental condition (describe; do **not** guess): None: no condition, pair, payload, or measurement-size clues in the packet. (Repair/incomplete markers are shared by both conditions.)

## 8. Freeze attestation

- All six dimension scores and justifications are complete: [x] yes
- This sheet will not be edited after the scores-frozen record is written: [x] yes
- Signature / initials: agent-evaluator  Date (UTC): 2026-10-31
