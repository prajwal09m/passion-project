# M14 Predictive Risk (Phase 5)

risk.hypothesize emits risk-hypotheses (thin-segment coverage,
calibration weakness, unusual input dependence, unevaluated shift),
each with evidence, missing evidence, assumptions, uncertainty, and
raise/lower-confidence conditions. prioritize orders them
transparently. early_warning maps each risk to a targeted test and
tool. Risks are research priorities, never confirmed defects; the
flagship surfaces 4 risks on c_robustness with missing evidence
stated. Tests: status, missing-evidence presence, warning mapping
in test_m14_systems.py.
