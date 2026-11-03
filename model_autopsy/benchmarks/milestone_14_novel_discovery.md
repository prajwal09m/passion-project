# M14 Novel Discovery (Phase 1)

mechanisms.discover finds error concentration (segment ratio >= 1.5),
residual input tracking (|r| > 0.5), and multi-family co-occurrence
without requiring an ontology label; classification against the
ontology is recorded as bearing, not identity. unknowns() answers
the six unknown-unknown questions explicitly. On c_robustness the
layer reports "error concentrates in machine=m2 (ratio 614.19)" as
an unvalidated candidate at confidence 0.45. A surprising
observation is never a proven mechanism: validation starts
unvalidated and confidence never exceeds the cap. Tests: 4 in
test_m14_discovery.py (concentration found, unknowns structure).
