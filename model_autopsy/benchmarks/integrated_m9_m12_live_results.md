# Integrated M9–M12 Live Results — run live-c0cae8776976

## Run details
- Run ID: live-c0cae8776976. Project: eval_turbine (time-series
  forecasting). Model: muse-spark-1.3 via the configured endpoint.
- Rounds used 2/3. Experiments 6/6. API attempts 7/12.
  Provider-reported tokens 29,818/50,000 (input 24,030, cached
  17,845, output 5,788). Spend $0.0350/$0.40. No ceiling
  breached. Status: completed (no abort, no retry hacks; one
  bounded summary repair, recorded).
- Artifacts preserved: manifest, usage.jsonl, actions,
  hypotheses, events_dump, assistant_messages, eval_report,
  scorecard (hashes in manifest.json).

## Research results
Model proposed 3 competing hypotheses (level-shift regime change;
persistent bias/miscalibration; data-quality artifact) and ran 3
diagnostics (changepoint scan, residual-time analysis,
distribution-shift profile). All drift probes fired supports.

## Budget compliance
Rounds 2≤3, experiments 6≤6, attempts 7≤12, tokens 29,818≤50,000,
spend $0.035≤$0.40. Compliant on every ceiling.

## Independent assessment (old M5 scorer)
Verdict inconclusive, overall 0.62 (discovery 0.0, evidence 1.0,
reasoning 0.6, calibration 1.0, efficiency 0.6,
reproducibility 1.0); "failure missed entirely", no false
positive. The scorer's bar (naming the day-500 level shift with
clean splits) was not met: the model circled drift without
isolating the break or ruling splits in/out.

## Live-path finding (fixed same session)
Post-run audit showed all three hypotheses recorded changepoint
and residual-time supports — including two that explicitly deny
a level change ("not a new level change", "not a true level
shift"). Root cause: `_family_of` is negation-blind, so denial
wording mapped every hypothesis to drift and drift-supports
moved belief the wrong way. Fix (offline, fully regressed):
family-level denial symmetry in `attribution.py` — evidence for
a denied mechanism contradicts; evidence of its absence supports
the denial — with a dedicated negation set that excludes
"artifact" (a claim word, not a denial). Verified: deniers now
contradicted, affirmers supported, quality-clean still
contradicts quality claims. Full suite 407→408 pass; M9 means
and M10 grades byte-identical.

## Limitations
One run cannot generalize. The scorer is the pre-M10 heuristic,
not the M10 evaluator (kept for comparability; its "missed
entirely" is harsh — drift was measured, not isolated). The live
loop uses model-worded hypotheses, so family-denial wording
effects remain a live-path sensitivity. No multi-agent live
comparison (one-campaign ceiling).
