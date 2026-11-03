# M13 Live Results

Single authorized run: live-d8b174527ca5 on eval_credit (credit default classification), max 3 rounds. Status completed. Budget: rounds 3/3, experiments 6/6, attempts 10/12, tokens 44181/50000 (input 37045, cached 17589, output 7136), spend 0.057286/0.40 USD. All ceilings respected. No retry.

Heuristic scorecard: verdict inconclusive, overall 0.63, discovery 0.0 (failure missed entirely), evidence 1.0, reasoning 0.6, calibration 1.0, efficiency 0.8, reproducibility 1.0, false_positive false. Honest inconclusive preferred over unsupported discovery; failure mode preserved for corpus analysis.

Eval2 grading: live path uses heuristic scorer artifact; evidence-required eval2 dimensions apply to offline corpus runs (single 0.688, team 0.773 on b_unit_shift). Live exercised generalized discovery loop, calibration tool use (brier 0.13 recorded), adaptive selection, attribution, shared-budget enforcement, and full artifact preservation (manifest hashes in run dir). Skeptic and judge review remain offline-team strengths; live run did not claim capabilities it did not exercise.

Run dir: model_autopsy/benchmarks/live_runs/live-d8b174527ca5 with manifest, usage, hypotheses, actions, eval_report, scorecard, sandbox db.
