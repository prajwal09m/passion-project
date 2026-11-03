# M14 Evaluation 3.0 (Phase 9)

Corpus C: 6 scenarios (interaction, robustness, saturation,
combined, steady, thin) with new columns (county, machine,
sensor) and sealed truth; investigator sees briefs plus
artifacts only. eval3 extends eval2 with novel_discovery,
robustness_discovery, risk_prioritization, falsification_quality,
parity, and generalization (n/a when untestable, never
zero-filled); per-scenario rows preserved with the small-sample
limitation note. eval2.aggregate now skips non-numeric values.
Commands: py model_autopsy/tests/fixture_m10c/generate.py;
py -m pytest model_autopsy/tests/test_m14_eval3.py -q (4 passed).
