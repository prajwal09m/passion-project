# M14 Strategy Learning (Phase 6)

strategies.py versions five policies (m13-baseline m13.0,
info-value m14.1, adaptive-discovery m14.2, memory-assisted m14.3,
combined m14.4) as ranking functions over the same candidates;
nothing rewrites linker/attribution/invention gates. record
persists project profile, questions, selection, and outcomes to
strategy_records.jsonl. compare reports deltas vs the frozen
baseline with a no-sealed-tuning note. Tests: ranking preference
and held-out comparison math in test_m14_systems.py.
