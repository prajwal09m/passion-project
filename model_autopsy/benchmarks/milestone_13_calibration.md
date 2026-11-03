# M13 Calibration

Pooled calibration_and_error_analysis bins=10 (max populated-bin gap >0.15 miscalibrated, <0.05 sound, else inconclusive; n<30 bins ignored) + bins=5 operating-range view + pooled classification_metrics AUC baseline. Subgroup and operating-region via grouped variants; train/eval via split tools; discrimination vs ranking via AUC alongside reliability. Sample-size guards in spec power_limits. Tests: pooled calibration candidates invented; b_score_inflate key tool is calibration_and_error_analysis.
