# Milestone 10 Validation Gates

- Investigator/evaluator separation: import-boundary test +
  artifact audit (`audit_unseen_env` ok, 0 violations). PASS.
- Sealed ground-truth isolation: truth in `_sealed/`, never
  imported by `scenarios`/`runner` (source-inspected). PASS.
- Unseen projects: 8 frozen artifacts, mechanisms disjoint from
  M9. PASS.
- Novel mechanisms: proxy leakage, unit inconsistency, lag,
  combo, threshold skew — none in the M9 template set. PASS
  (threshold skew exposed a library boundary, honestly graded).
- Cross-framework: sklearn + torch exercised; TF/HF excluded
  with explicit non-claims. PASS.
- Independent replication: different-tool second probe with own
  provenance; reruns refused. PASS.
- Statistics: effects + intervals + limits; n<3 refused; no
  p-values. PASS.
- Anti-contamination: dev corpus == eval corpus here (single
  frozen set, no tuning against grades — inventor untouched
  since M9 freeze); negative controls (steady, sparse) both
  correct. PASS with noted limitation: a larger held-out split
  awaits future work.
