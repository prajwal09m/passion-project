# Pre-registration — controlled Groq continuation experiment (2026-10-29)

**Status:** written and frozen BEFORE any live provider request. This document
is append-only history; do not edit it after the first live call. The
corresponding harness flag is `--controlled`.

## 1. Question

The 2026-10-29 trace re-analysis of the five Groq 20B pairs found that the
previous continuation comparison was confounded: both arms were told to
"Finish now" at the end of turn 1, immediately before the continuation turn;
the delta opener also carried a condition-specific framing note; and
run-total token comparisons were driven by unequal stopping decisions. This
experiment asks a narrower question:

> With identical continuation instructions, identical round/tool budgets, and
> the final-turn wrap-up available only at the true final opportunity, do the
> two continuation-context strategies differ in what the model *does* —
> gather more evidence, synthesize, or abstain — or in investigative quality?

It does **not** ask whether either context strategy is causally correct, and
it does **not** measure Meta billing.

## 2. Conditions and the single manipulated variable

Both arms use the same production `model_autopsy` code. The benchmark-only
flag `--controlled` replaces the continuation opener with one neutral payload:

- identical keys: `mode`, `objective`, `continuation_instruction`,
  `hypotheses`, `findings`, `experiments_ledger`, `budget`;
- identical instruction text in both arms:
  "Continue the investigation from the recorded state. Use the available
  tools if another measurement could change the conclusion; otherwise
  conclude. End with the required investigation_summary block.";
- the ONLY difference: the `full` arm additionally includes
  `recorded_context` (the Phase-C corpus/recording block); the `delta` arm
  omits it.

The production delta builder's "this message is the current state delta only"
framing note is not used in either arm. No tool call is required or prompted.

**Fixed across arms:** model `openai/gpt-oss-120b`; temperature 0.2; 2 turns;
3 model rounds per turn; one shared `max_tool_calls=6` budget for the whole
investigation; production `meta_tool_schemas("ml")` tool definitions;
production reuse guard; production tool-packet truncation; production
validator; production-shaped one-request summary repair (no tools, bounded,
validator-checked); 2000 output tokens; fresh sandbox SQLite per run;
`source_meta=True`; no production code modification.

**Wrap-up placement:** turn 1 receives no `_wrapup_item` in either arm. Turn 2
receives it only at the last scheduled round (round 3) or when the tool budget
is fully exhausted — not on the production "two calls remain" heuristic. This
is identical in both arms and is the benchmark's operational definition of
"the actual final opportunity."

**Counterbalancing:** condition order alternates across pairs (pair 1 full
first, pair 2 delta first, ...). The order is recorded in every ledger.

## 3. Safety limits and budget (pre-registered)

No Meta request; `MODEL_API_KEY` is not read. Groq only.

Per pair: `--max-attempts 30`, `--max-total-tokens 80000`,
`--max-est-cost 0.10 USD`, `--repeated-429-limit 4`. All provider HTTP
requests, including every 429 retry, count. The harness waits on provider
guidance or the next minute boundary; it never retries indefinitely.

Global experiment ceilings (driver-enforced, checked after every pair):

- at most **5 pairs** (10 runs); stop early at the first of:
  - any global `stop_reason` in a pair ledger;
  - global attempts > 100;
  - global provider-reported tokens > 300000;
  - global estimated cost > **0.50 USD**;
  - two pairs with an aborted condition;
- no model switching; no extra diagnostic requests; no manual retries of a
  failed pair.

**Budget basis.** The only established budget in this project is the existing
harness ceiling of $0.50 estimated cost per live invocation. This experiment
sets the *entire* five-pair campaign ceiling equal to that same $0.50. The
five prior 120B pairs cost $0.000996–$0.007460 (median ≈$0.0066) per pair, so
the expected total is ≈$0.033, about 7% of the ceiling. Cost remains an
estimate from published pricing, never a billed amount. If the driver cannot
read the frozen caps or cannot establish the key, it makes zero calls.

## 4. Outcomes and the six-component rubric

Scored per run, 0/1 each, after the run is complete:

1. **Mechanism named** — the conclusion names a candidate mechanism (e.g.
   label leakage in a named feature, class imbalance, temporal drift,
   overfitting) that could explain the measured behavior, rather than only
   restating a metric. 0 if no mechanism.
2. **Measured number cited accurately** — at least one number in the
   conclusion/recommended_next matches a value in a recorded action's
   `numeric_evidence` or `detail` within the displayed precision; 0 if no
   number is cited or any cited measured number is wrong. Numbers explicitly
   labeled as hypotheses/ranges are not counted as measured citations.
3. **Calibrated conclusion/status** — the status and certainty language match
   the evidence: no `supported`/causal claim without a discriminating test;
   correlation-only evidence is hedged; abstention is acceptable. 0 for an
   overclaim or an unsupported certainty.
4. **Discriminating follow-up test identified when appropriate** — if the run
   names a mechanism or abstains with an available test, `recommended_next`
   specifies a concrete test that could distinguish the hypothesis (e.g.
   retrain/ablate `hold1_ret`, reweight classes, per-fold metrics). 0 if absent
   or non-discriminating.
5. **Hypotheses linked to recorded evidence** — every `status_recommendations`
   entry cites at least one action/hypothesis ID that resolves in the same
   investigation; 0 if there are no status recommendations or any citation is
   unresolvable.
6. **No false self-report** — every claim about executed diagnostics,
   remaining calls, or remaining rounds matches the recorded actions and
   counters; 0 for any false claim.

**Mechanical validity is scored separately and is not part of the 0–6 quality
total:** final summary valid (after the one bounded repair), first-attempt
valid, repair attempts, whether every basis/hypothesis ID resolves, tool calls
used vs budget, aborted/skipped status, and schema shape (`basis` list vs
string, empty status list, etc.).

**Scoring order and blinding.** Mechanical validity is scored first from the
run records. Then a blind sheet is generated containing only: an opaque run
label, the final summary, the ordered recorded actions with numeric evidence,
the budget counters, and the validator outcome. It contains no condition,
investigation name, pair number, payload size, token count, or request ledger.
A separate scorer receives only that sheet and the rubric, and returns six
0/1 scores per run. Only after those scores are written is the sealed
label→condition key opened and joined. The unblinded analysis reports the
join, not a re-score.

**No invented ground truth.** The sandbox contains out-of-fold predictions
only: no training metrics, no feature provenance, no causal ground truth.
Component 1 is therefore "a mechanism is named", not "the mechanism is
correct"; components 2/5/6 are auditable against recorded rows, while 1/3/4
are documented judgments. Single rater, no inter-rater reliability.

## 5. Analysis (descriptive only)

Report per pair and aggregate: provider-reported input/output tokens,
estimated cost, HTTP attempts, tool executions, turn-1 vs turn-2 actions,
whether turn 2 gathered evidence / synthesized / abstained, summary validity
and repairs, evidence coverage (distinct evidence-bearing tools), and each
rubric component plus the 0–6 total. Report every aborted pair and its exact
stop reason. Paired differences are listed individually; no p-values, no
"significant", no confidence interval presented as inference. Do not infer
Meta billing or `previous_response_id` savings.

**Design-validity check (separate from outcome):** the controlled design is
considered to have removed the identified confounder only if (a) offline
certification passes, (b) every live record shows the identical continuation
instruction and budgets and `forced_diagnostic: false`, and (c) no
continuation is preceded by a turn-1 wrap-up. If (a)–(c) hold, behavioral
differences are attributable to the context variable plus model noise, not to
the removed framing/stopping cues. That is a design statement, not a quality
claim.

## 6. Artifacts (append-only)

- `phase_d_groq_controlled_pair{1..5}.json` — one full paired ledger per pair.
- `phase_d_groq_controlled_ledger.json` — driver aggregate, written after each
  pair (never rewritten from an earlier campaign).
- `phase_d_groq_controlled_blind_sheet.json` — condition-masked scoring input.
- sealed key — outside the repository; opened only after scores are frozen.
- `phase_d_groq_controlled_scores.json` — blind scores + unsealed join.
- a new dated section appended to `RESULTS.md`; all prior sections preserved.
