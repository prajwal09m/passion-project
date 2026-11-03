# M13 Validation

Backend: py -m pytest model_autopsy/tests -q full suite; targeted suites include test_m13_discovery, test_m13_eval2, test_m12_lab, test_m11_team, test_m10_validation, all green. Scientific: sealed truth separation, evidence-required grading, no label leakage, no report-only shortcuts, no unsupported causal claims, no false reproduction. Frontend: npx tsc --noEmit clean and npm run build ok. Security: .env ignored, no secrets in logs or artifacts, no unapproved paid calls, unsafe adapters guarded.
