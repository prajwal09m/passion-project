# Milestone 10 Audit — Independent Scientific Validation

## Verdict: VALIDATED with one honest boundary.

## Corpus
8 unseen projects (`tests/fixture_m10/`, frozen generator
`generate.py`), mechanisms disjoint from M9: ward degradation,
proxy-signal leakage, systematic over-scoring, lagged predictions,
district unit inconsistency, drift+gap combo, clean control, thin
pilot. Sealed truth in `fixture_m10/_sealed/truth.json`; the
investigator path imports only `scenarios.py` (briefs + artifact
paths). `test_investigator_path_never_touches_sealed` enforces the
import boundary by source inspection; `audit_unseen_env` scans every
investigator-readable CSV for tool names and distinctive mechanism
phrases (ordinary column words are working material, not leaks).

## Discovery (independent evaluator, evidence-required grades)
5 discovered (ward_gap, proxy_signal, stale_lag, district_scale,
combo — each with a naming hypothesis backed by moving evidence
from a real executed action, key tool measured), 1 relevant-only
(threshold_skew: miscalibration named but never measured — see
boundary), 2 inconclusive-correct (steady clean, sparse thin).
Mean discovery score: 0.906. No lucky guesses: grades require
moving evidence refs; `unsupported` (supported without mechanism
evidence) scores 0.

## Incidents during validation
1. Fixture word "level shift" tripped the M4 separation audit in an
   earlier task; M10 audit was designed token-precise from the start.
2. Grading harness picked investigations via `created_at` ordering;
   ties under rapid runs graded the wrong investigation
   (phantom "incorrect"/"relevant-only" flips). Root cause found by
   hash-seed bisection (ruled out PYTHONHASHSEED: identical across
   seeds 0/1/2). Fixed by carrying `investigation_id` in the
   autonomous behavior dict (one additive line in
   `research/autonomous.py`; no behavior change). All grades since
   deterministic across repeated full-corpus runs.

## Cross-framework
scikit-learn (LogReg + RF: fit, predict_proba,
classification_metrics) and PyTorch (MLP: fit, predict,
regression_metrics) validated end to end. TensorFlow and Hugging
Face not installed: reported unvalidated, no claims made.

## Replication
`replication.replicate` re-tests a claimed mechanism with a
different tool, own provenance, preserved original evidence;
same-tool reruns refused. Column-mapped (label/score vs
target/prediction) via artifact facts. Verified on ward_gap.

## Statistics
`stats.mean_ci` / `stats.subgroup_gap`: effect + interval +
Cohen's d with magnitude words; n<3 refused; independence assumed
and stated; subgroup gaps labeled observational, never causal.

## What remains unproven
Calibration discovery (no pooled-calibration candidate in the
inventor — M9-frozen, deliberately untouched); cross-family
contradiction bridging; TF/HF adapters; broad generalization
(one corpus, offline loop).
