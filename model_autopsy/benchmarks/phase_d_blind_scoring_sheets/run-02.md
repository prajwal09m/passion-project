# Blind investigation-quality scoring sheet — RUN-02

- Campaign: Phase D Meta paired benchmark (protocol revision v2)
- Rubric: phase_d_blind_scoring_rubric_v1.md (frozen 2026-10-29)
- Sheet version: v1 (frozen)
- Neutral run label: **RUN-02**
- Presentation position: 2 of 4
- Condition: withheld
- Raw trace: not provided to the evaluator

## 0. Scoring session

- Scorer:
- Scored at (UTC):
- Evidence packet reference:
- Scorable final message present: [ ] yes  [ ] no
  (if no: mark `not_scorable`, record why below, and assign no dimension scores)
- I scored this run without opening another sheet or the condition key: [ ] yes
- I did not use token, cost, latency, or request-payload data: [ ] yes

## 1. Dimension scores

### D1 — Mechanism identification

- **0:** mechanism missing or incorrect
- **1:** partially identified
- **2:** correctly identifies and explains the failure mechanism
  (evidence-consistent; unproven parts explicitly labeled)

**Score (0/1/2):**
**Evidence-based justification:**

### D2 — Numeric grounding

- **0:** unsupported or inaccurate numbers
- **1:** partially accurate
- **2:** measurements accurately reflect recorded evidence

**Score (0/1/2):**
**Evidence-based justification (state the comparison basis: exact, rounding, or unsupported):**

### D3 — Evidence linkage

- **0:** claims disconnected from evidence
- **1:** some claims supported
- **2:** hypotheses and conclusions explicitly linked to recorded evidence

**Score (0/1/2):**
**Evidence-based justification (cite action/hypothesis ids):**

### D4 — Calibration

- **0:** facts and hypotheses confused or overstated
- **1:** some uncertainty acknowledged
- **2:** clearly distinguishes facts, hypotheses, and conclusions

**Score (0/1/2):**
**Evidence-based justification:**

### D5 — Diagnostic reasoning

- **0:** no useful diagnostic direction
- **1:** generic or partially useful test
- **2:** specific, discriminating follow-up test where appropriate
  (a well-justified stop also earns 2)

**Score (0/1/2):**
**Evidence-based justification:**

### D6 — Execution honesty

- **0:** false claims about tool execution or evidence
- **1:** minor ambiguity
- **2:** accurately reports executed tools, results, limitations, and remaining budget

**Score (0/1/2):**
**Evidence-based justification:**

## 2. Total

D1 + D2 + D3 + D4 + D5 + D6 = **____ / 12**

## 3. Structured-summary validity (separate; not part of the 12)

- First-attempt valid: [ ] yes  [ ] no
- Post-repair valid: [ ] yes  [ ] no
- Repair attempts: ____
- Validator errors (verbatim, up to 8):
- Note: a valid block earns **no** quality points by itself.

## 4. Execution and evidence (recorded facts only)

| Fact | Value |
|---|---|
| Diagnostic tools executed (name + action id + status) | |
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

- Any clue about the experimental condition (describe; do **not** guess):

## 8. Freeze attestation

- All six dimension scores and justifications are complete: [ ] yes
- This sheet will not be edited after the scores-frozen record is written: [ ] yes
- Signature / initials: __________  Date (UTC): __________
