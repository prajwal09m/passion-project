# M14 Robustness (Phase 3)

perturb_copy supports noise, scale, missingness, shuffle,
subset_drop, value_shift on isolated copies in a scratch dir with
content-hash provenance; the original hash is verified unchanged
after the write (RuntimeError otherwise). measure compares baseline
vs perturbed with real diagnostics (prediction stability,
metric degradation via regression_metrics where target+prediction
exist). robustness_map marks stable/sensitive/unexplained and
always includes _untested as never-safe. c_robustness itself is a
scale fault: the lab distinguishes expected sensitivity from
implementation defect by requiring evidence on the project, not by
optimizing for degradation. Tests: isolation proof and map
semantics in test_m14_discovery.py.
