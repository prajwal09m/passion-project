# Milestone 5 — Meta Investigator Loop

## Pilot project: eval_turbine (recorded rationale)

Forecasting; missed clean level shift at day 500 with chronological
splits (no leakage to find — the tempting wrong answer tests
evidence attribution). Single-diagnostic evidence path keeps the run
inside budget; neutral name/brief; mechanism never discussed with Meta
(the phase_d campaigns investigated Demand Zone only). Presented under
a neutral run/investigation identifier.

## Loop shape (implemented in `live/driver.py`)

1. **Recon**: `build_live_context` — neutral brief, real schema (5-row
   sample), tool names, column guidance. Meta is NOT asked to guess the
   failure; first output must establish task/data/pipeline/risks/gaps.
2. **Hypotheses**: Meta registers competing cards via
   `propose_hypothesis` (mechanism, plausibility, contradicting
   observation, confidence). Backend validates, never authors.
3. **Experiments**: Meta requests diagnostics; each must discriminate
   live hypotheses. `engine.run_tool` validates + executes + records.
4. **Interpretation**: results return as `function_call_output`; Meta
   must state support/contradict/alternatives/confidence deltas.
   Demotion on contradiction is Meta's stated method (ML prompt §3).
5. **Stop**: sufficient conclusion, all hypotheses rejected,
   insufficient evidence, budget cap, request limit, or safety block.
   Stopping uncertain is allowed and recorded as-is.

## Blindness controls

Meta receives: brief, schema sample, model name/framework, methodology,
tool results it requested. Meta never receives: ground-truth file,
reference solution, expected score, mechanism labels, evaluator notes.
Verified by: separation audit (green), live-context token test, driver
source test (no `ground_truth` reference), neutral run identifiers.

## Report contract (§5)

Engine `build_report` (recorded findings/actions only) + frozen final
message + validated structured summary → `finalize` → adapter → scorer.
Every substantive conclusion must cite a recorded action; invented
experiments are impossible by construction (adapter reads actions, not
prose). Verbatim text preserved; invalid summaries preserved with
errors (repair path recorded either way).
