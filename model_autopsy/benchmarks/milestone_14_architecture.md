# M14 Architecture

M14 adds observation-first discovery on top of the M13 ontology without
replacing it: research/mechanisms.py (candidates with identity,
phenomenon, context, evidence, competing explanations, confounders,
predictions, experiments, confidence capped at 0.45, validation and
reproduction status) runs alongside agenda/invention/attribution.
research/composed.py adds composed experiments from primitives with
full proposal schema, validation (relevance, executability, inputs,
no sealed leak, meaningful measurement, decision-changing, budget),
and usefulness-first creativity scoring. research/perturb.py runs
perturbations on isolated hashed copies (original hash-guarded) with
stability/degradation measurement and robustness maps where untested
is never safe. live/audit.py + live/parity.py give stage-level loss
accounting and offline replay. research/risk.py, strategies.py,
m12/falsify.py, m12/network.py, m10/eval3.py + runner_c +
scenarios_c + fixture_m10c complete the stack. M9-M13 files changed
only additively: invention segment vocabulary plus data-driven
low-cardinality fallback, agenda vocabulary, evaluator family words
for interaction/robustness, eval2 aggregate skipping non-numeric.
