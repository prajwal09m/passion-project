# Investigation Evaluation Methodology (Milestone 3, Part 9)

Implemented in `backend/research/evaluate.py::score_run`.

## Dimensions (never collapsed to one number alone)

| Dimension | What is measured | Assessment class |
|---|---|---|
| Discovery | failure found (bool), false positives, mechanisms identified, unknown issues | deterministic + heuristic |
| Reasoning | hypothesis count, null present, evidence linkage | heuristic |
| Experimentation | n experiments, unnecessary (>4), reproducibility | deterministic |
| Accuracy | numbers present, conclusion valid | deterministic + heuristic |
| Efficiency | experiments, time; tokens only when live usage exists | deterministic |
| Reliability | report complete, evidence preserved | deterministic |

`aggregate = mean(hit, numbers_present, budget_ok)` accompanies the
six dimensions; the methodology forbids reporting it alone.

## Ground-truth rules

Hidden per-scenario `expect` keys (leak_flag, urban_bias,
overlap_and_drift, tail_slice_gap, scaling_mismatch,
leak_plus_subgroup, limited, healthy). `clean`/`limited` score a hit
only with zero confirmations — the correct conclusion can be "no
material issue established". `multi` currently scores on the leak
finding while the report surfaces both (both confirmed in practice).

## Result classes

Deterministic (recomputed metrics, counts), heuristic (triage quality,
validity judgments), LLM-based (NOT YET VALIDATED — reserved for
future live campaigns), human-reviewed (NOT YET — reserved).

## Current scores

9/9 hits; aggregates 1.0 across the board on the 2026-11-01 offline
run (blackbox reaches 1.0 via the honest-limit path: no confirmation
claimed where confirmation is impossible). 13 experiments total, 0
failed, 0 unnecessary (>4 in any run).
