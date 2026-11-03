# Milestone 8 — Real Diagnostic Discovery (Workstream C)

## M7 failure, stated plainly

Discovery scored 0 because per-region AUC was never computed. The deeper
finding: no component could even NOTICE. Planning never requested
segmented measurements, the linker had no rule that reads them, and no
tool args ever passed a group column. A system cannot discover a
mechanism through a measurement it never performs — and nothing tracked
that the measurement was missing.

## The fix (three small extensions, no rebuild)

- **Diagnostic coverage layer** (`causal/coverage.py`): maps each open
  hypothesis's mechanism family to its required measurements, splits them
  into collected vs missing from the ran-tool record, and exposes the
  union. The plan now carries `missing_measurements` and per-hypothesis
  coverage; the dashboard can show exactly what is unknown and why.
- **Selection relevance** (`causal/planning.py`, `selection.py`): tools
  filling a missing measurement are boosted to high with an explicit
  reason; failed tools are excluded; inapplicable tools (learned when arg
  construction fails) are excluded and listed, never re-recommended.
  A distinct `leakage` family (explicit leak words) routes to the
  leakage screen instead of hiding inside split-hygiene.
- **Linker rules for the missing evidence kinds** (`causal/linker.py`):
  per-split AUC spread (supports subgroup at >= 0.10, contradicts below
  0.03, silent between), group-MAE ratio (supports at >= 1.5x), bias vs
  residual spread, reliability-gap calibration, and a leakage screen that
  ignores the label column and model scores and judges only non-score
  inputs (>= 0.95 supports, < 0.5 contradicts, silent between).
  Single evidence moves a hypothesis to investigating; promotion to
  supported still needs corroboration (2 supports, 0 contradicts) —
  evidence quantity never auto-confirms.

## Proof (tests: `test_m8_discovery.py` 9, `test_m8_linker.py` 8)

Coverage maps drift/subgroup families; a regional-gap hypothesis surfaces
`grouped_auc_comparison` as missing; no project/benchmark words act as
family triggers; planning boosts missing-measurement tools with reasons,
excludes failed and inapplicable tools, and stops/continue rules behave.
On REAL fixtures: region-W AUC 0.54 vs ~1.0 links supports-subgroup;
rent-district MAE ratio ~6 links supports-subgroup; credit miscalibration
links supports-calibration; drift hypotheses get no subgroup link;
failed actions never generate evidence; the leakage screen contradicts
(max non-score |r| ~0.37) and demotes.
