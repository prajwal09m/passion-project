# Milestone 10 Replication

`backend/m10/replication.py`: a replication re-tests the claimed
mechanism with a DIFFERENT tool (per-family second probe:
subgroup→residual_feature_dependence,
leakage→calibration_and_error_analysis,
calibration→regression_metrics,
misspecification→temporal_changepoint_scan,
drift→residual_time_analysis).

Rules: same-tool reruns refused; column mapping adapted from
artifact facts (label/score vs target/prediction); original
evidence preserved; replication recorded as its own event with
`links_applied`. Verified on m10_ward_gap: independent probe ran,
was not in the original spec list, links recorded.
