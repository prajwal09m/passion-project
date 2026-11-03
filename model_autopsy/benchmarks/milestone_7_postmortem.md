# Milestone 7 — Root-cause postmortem (M6 live run `live-ae844753edce`)

No paid API activity during reconnaissance. Sources: the run's
`live.sqlite3` (50 events, 6 actions, 3 hypotheses), `eval_report.json`,
`scorecard.json` (M4 inconclusive 0.62), `m6_scorecard.json` (9-dim
0.678), `backend/meta_api/loop.py`, `backend/live/{driver,resume}.py`,
`backend/causal/*`, `backend/{engine,tools_registry,task_diagnostics}.py`.

## 1. Why hypothesis statuses never moved

The loop (`meta_api/loop.py`) contains **zero references** to
`update_hypothesis`, `link_evidence`, or `update_with_evidence`
(verified by search). The ML system prompt forbids the model from
setting statuses itself ("recommend changes only in the final summary;
you cannot set them yourself"), and no backend step applies the
recommendations to the DB either — the valid summary's recommendations
were scored from the eval report, never written back. Result, verified
in the DB: all 3 hypotheses `status=proposed`, `confidence=NULL`,
`evidence_refs=NULL`, `revisions=NULL`, `status_justification=NULL`,
despite 3 substantive diagnostics whose results confirmed one direction
and contradicted a rival.

## 2. Disconnected, not incomplete

The transition system is correct: `engine.update_hypothesis` supports
all six statuses (incl. `blocked`), `link_evidence` enforces real
action ids with dedup, `causal/hypotheses.update_with_evidence`
implements evidence-graded confidence with justification — all tested
offline. It is simply never invoked on the live path. This is a wiring
defect, the highest-leverage fix in the milestone.

## 3. Why selection policy never influenced decisions

`backend/causal/selection.py` is unreferenced by the loop, driver,
prompts, and events (zero matches; zero `selection`-kind events in the
run). The investigator received roster + experiments-ledger + budget —
but no ranked candidates, no expected-observation-per-candidate, no
redundancy signal beyond exact-argument dedup. The model chose tools
unaided; 3 of 6 experiment executions were `propose_hypothesis` records
(zero evidence), and the two new M6 diagnostics most relevant to
follow-up questions were never suggested to it.

## 4. Was the investigator sufficiently informed? Mostly, but not decisively

It had schema, sample rows, ledger digests, and budget. What it lacked:
(a) discrimination framing — which tool separates the live hypotheses;
(b) the one number its verdict needed. The scorer required
`residual_feature_corr` for eval_claim; **no diagnostic computes a
residual-vs-feature correlation** — `regression_metrics` computes only
`corr(|resid|, |pred−mean|)` ("heteroscedasticity_hint"). The evidence
needed for discovery was literally unproducible. The investigator cannot
be blamed for not citing a number no tool returns.

## 5. Budget allocation

6/6 experiments used, 8/12 attempts, 37k/50k tokens, $0.054/$0.40 —
disciplined but misallocated: half the experiment budget bought
hypothesis records instead of evidence, and the final two diagnostics
(`data_quality_profile`, `regression_metrics`) were chosen without
ranking guidance. No policy existed to stop spending on hypotheses or
to prefer the discriminating test.

## 6. What prevented `device_age` discovery

A three-link chain, all verified: (i) no tool computes per-feature
residual correlation; (ii) no selection brief pointed at
feature-dependence testing; (iii) no post-tool step linked the
`calibration_snapshot` bias (−131.77) back to H1/H2 as supporting or
contradicting evidence. Any one link repaired might have helped; all
three missing guaranteed the miss.

## 7. How the pieces should communicate

`driver` owns rounds/budget/finalize; `loop` owns provider turns and
already commits every tool result synchronously — it is the natural
place for a deterministic post-tool evidence-linking step (backend rule
→ `update_with_evidence`, recorded with justification). Selection
belongs as a compact brief injected per turn (ranked candidates +
targets + rationale + budget), with adherence recorded post-turn.
Stopping belongs in the driver between iterations (supported diagnosis
vs. open questions vs. remaining budget), recorded as an event. The
model keeps judgment over prose and choices; the backend owns
transitions, accounting, and gates.

## 8. Largest measurable improvements (ordered)

1. Post-tool auto-linker in the live turn (statuses actually move;
   directly targets M6's 0.0-discovery failure signature).
2. `residual_feature_dependence` diagnostic (makes the required
   evidence producible — unblocks discovery on input-dependence cases).
3. Per-turn selection brief + adherence record (targets selection 0.4).
4. Driver stopping gate with rationale (targets wasted-budget patterns;
   keeps inconclusive honest).
5. Prompt deltas referencing the new machinery (roster statuses now
   change; follow the brief; compare predictions vs observations).
6. Closed-loop challenge harness proving the wiring with scripted
   providers (no paid traffic).
