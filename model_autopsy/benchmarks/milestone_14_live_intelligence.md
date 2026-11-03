# M14 Live Intelligence (Phase 4)

audit_run reads a saved live dir offline and reports per-stage
presence/failure across context, hypotheses, tool selection,
execution, interpretation, linking, planning, reporting, plus one
opportunity row per executed tool with the exact loss stage. parity
replays saved tool calls against the current offline engine and
labels matches vs infrastructure divergence. On the M14 live run
live-ecdd47fafd9d: 6 opportunities, 1 lost at recognized
(artifact_summary proposed but not ran), rest reported — a model
reasoning gap, not an infrastructure gap, preserved diagnosably.
eval_music was unused in M14 development, so no tuning against it
occurred. Tests: audit structure, tracking loss stage, replay
shape in test_m14_systems.py.
