# Flagship Demonstration Report (Milestone 3, Part 12)

Script: `model_autopsy/demo/flagship_research_lab.py` (offline,
deterministic, no provider calls). Output: `demo/flagship_report.json`.

## Project (non-financial, pipeline-complex)

Premium estimator (insurance, regression): predict monthly premiums
from applicant age and BMI. Brief given to the investigator: "Premiums
look systematically off after a pipeline change." Artifact only —
no hint that training used standardized BMI while serving uses raw
BMI. Same `lab.run_autonomous_investigation` engine as every scenario;
no special-case code for this project.

## Autonomous run (11 stages, 1 experiment)

1. Understanding: regression task, MAE/RMSE + residual-vs-feature
   evaluation, local sklearn availability recorded.
2. Recon: columns [age, bmi, target, prediction, split]; no dates.
3. Hypotheses: segment bias (high), null (low).
4. Selection: regression_metrics (+ leakage screens skipped, honestly
   inapplicable without feature/label framing).
5. Design: single read-only diagnostic; heuristic priority recorded.
6. Execution: `MAE=656 bias=-655.74 featcorr=bmi:-0.99` — residual
   correlates almost perfectly with one input feature.
7. Interpretation: breach (featcorr magnitude 0.99 > 0.5 threshold).
8. Revision: segment-bias card -> supported.
9. Review: upheld (n=1200, method stated, numbers with seed context,
   disproof criterion present).
10. Report: 1 supported / 0 rejected / 0 inconclusive.

## Conclusion

The evidence points at BMI handling (residual-feature correlation
-0.99 with systematic -656 bias): consistent with the planted
standardized-vs-raw mismatch. The report states the statistical
finding and recommends re-running on fresh splits plus a reusable
preprocessing-consistency diagnostic — it does not overclaim the
exact code diff, which would require pipeline source access (recorded
as a limitation).

## Reproducibility

Fixed seed, committed fixture
(`tests/fixture_challenge/pipeline_insurance.csv`), rerunnable via
`py -3 model_autopsy/demo/flagship_research_lab.py` in under 5 s.
