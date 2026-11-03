# Milestone 10 Architecture — Separation of Powers

```
tests/fixture_m10/*.csv  (+ briefs in backend/m10/scenarios.py)
        |  investigator sees ONLY this
        v
backend/m10/runner.py -> research.autonomous (M9 machinery, unchanged)
        |  behavior + investigation_id (no truth)
        v
backend/m10/evaluator.py  +  backend/m10/sealed.py (_sealed/truth.json)
        |  grades discovery; requires moving evidence refs
        v
backend/m10/replication.py (independent second probe, own provenance)
backend/m10/stats.py (effects + intervals, documented limits)
backend/m10/cross_framework.py (sklearn + torch exercised; TF/HF excluded)
```

Trust rules: investigator modules never import `sealed`
(source-inspected test); truth file lives outside any investigator
search path; the M10 audit scans artifacts for tool names and
distinctive mechanism phrases; the M4 audit still guards the eval
tree. The evaluator never feeds information back into the
investigation — grading is post-freeze, one direction.
