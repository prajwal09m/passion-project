# M16 Roadmap — Prioritized Technical Plan (Audit-Backed)

Every item addresses a verified bottleneck (audit §2). No sophistication
for its own sake. All work offline-first; paid-API needs flagged per item.

## P0-1. Discriminating-probe reservation (bottleneck C)
- Problem: ~3 real diagnostics/run, model-picked, discriminating probes never selected.
- Why existing is insufficient: `invention.propose` ranks by
  distinguishes_n but has no live caller; briefs are advisory.
- Modules: `meta_api/loop.py::run_meta_turn`, `live/governor.py`,
  `research/invention.py::propose/validate/execute`.
- Implementation: reserve 1 of 6 experiments; after round 1, run top
  `invention.propose` spec (validated, non-duplicate) regardless of model
  preference; record deviation rationale. Budget math: 1 reserved + ≤5
  model-chosen; breach-impossible via pre-dispatch reservation.
- Offline tests: reservation accounting under 0/1/6 remaining; model-override logging; no-duplicate guarantee (`test_m8_budget.py` pattern).
- Expected impact: every live run gets ≥1 hypothesis-separating measurement (the M8 district-C shape).
- Risks: model starvation (mitigate: only 1 reserved); wrong auto-pick (mitigate: validate + indecision bands report inconclusive, never force).
- Paid APIs: none for implementation; live validation needs authorized runs (see EVALUATION_PLAN).

## P0-2. Slice-aware live diagnostics (bottlenecks C, E)
- Problem: pooled metrics contradict slice truths (M14); per-segment measurement never selected live (M7/M13).
- Modules: `ml_tools.py::ranking_slice_diagnostics`, new
  `grouped classification` P@K-by-segment wrapper, `causal/planning.py`
  (trigger: segment column + classification/ranking task), `tools_registry.py` (schema).
- Implementation: when artifact has a segment column, auto-offer grouped
  slice diagnostics in the brief top-3 with segment-spread interpretation
  rules; add column-alias tolerance (label/target/y/grade, score//
  prediction/relevance) so `artifact_summary` cannot fail as in M14.
- Offline tests: music_rank.csv slice gap ≥0.15 surfaced; relevance/score naming accepted; thin segments report inconclusive (n<30).
- Expected impact: removes the M14 failure class entirely.
- Risks: extra tool surface (mitigate: trigger only when segments observed); P@K gaming (mitigate: pair with AUC + calibration, never alone).
- Paid APIs: none.

## P1-1. Attribution adequacy gate (bottleneck D)
- Problem: substring supports on deniers; pooled numbers contradicting slice truths unchallenged.
- Modules: `causal/attribution.py::classify`, `causal/linker.py::_rules`,
  `research/pipeline.py` (metric-adequacy note).
- Implementation: two checks before any supports link — (a) denial check
  (`denies_family` must already pass; extend negation set with eval-proven
  misses), (b) granularity check (pooled-only evidence may not support a
  segment-specific hypothesis nor contradict one — at most `relevant_to`).
  Contradictions require the adequate-granularity probe or explicit
  "wrong-granularity" flag.
- Offline tests: M8-H3 denial → not-supports; M9int deniers → contradicts;
  M14 pooled-AUC vs slice-H1 → flagged granularity mismatch; M9 means +
  M10 grades byte-identical (no-regression gate).
- Expected impact: ends proven wrong promotions; surfaces metric gaps as diagnoses.
- Risks: over-strict linking starves hypotheses (mitigate: non-moving relations stay visible; monitor link rates in replay).
- Paid APIs: none.

## P1-2. Hypothesis-update closure (bottleneck F)
- Problem: statuses frozen (M5/M6/M13) or mis-firing (M9int); summary channel broken 4/7.
- Modules: `meta_api/loop.py` (post-tool status pass), `engine.py`
  (status-transition helper with cited-action requirement), `causal/report_schema.py` (grounded summary: ids + numbers pre-filled, model fills prose only).
- Implementation: after each tool result, force one status-maintenance step
  (promote/contradict/leave with cited action id, or record why not);
  summaries generated from a template with hypothesis ids, verdicts, and
  numbers already filled — model writes rationale sentences only;
  template mismatch → fallback (already exists), counted as a metric.
- Offline tests: replay M5/M6 artifacts through the pass (statuses must move on the recorded evidence); template-render tests with missing fields.
- Expected impact: closes the loop that left 3/7 runs with zero status motion.
- Risks: forced motion could repeat M9int wrongness (mitigate: adequacy gate P1-1 runs first; corroboration bar unchanged).
- Paid APIs: none for implementation.

## P1-3. Skeptic-lite in the live loop (bottleneck G)
- Problem: zero live skeptic/judge events; team gains offline-only.
- Modules: `m11/roles.py` (skeptic contract), `m11/ledger.py` (1-call reservation), `meta_api/loop.py` (challenge turn before final round).
- Implementation: reserve 1 call for a skeptic probe (ledger-capped):
  skeptic receives hypotheses + evidence only (not the investigator's
  conclusion), may demand one discriminating probe or register preserved
  dissent; investigator must answer with new evidence or concede the limit.
  Judge stays offline (verdicts need not burn live budget).
- Offline tests: M14-replay simulation (skeptic must flag the pooled-vs-slice mismatch); ledger-exhaustion behavior; dissent-preservation assertions.
- Expected impact: unknown magnitude (honestly unmeasured) — structural coverage of the exact M14 shape.
- Risks: burns 1/6 experiments (mitigate: share the P0-1 reservation when the skeptic's demand coincides with the top discriminating spec); latency.
- Paid APIs: none for implementation (uses existing live calls within cap).

## P2. Localization-aware scoring (bottleneck I)
- Problem: rubric cannot distinguish M8 (measured + restrained) from M13 (measured almost nothing).
- Modules: `eval/scorer.py`, `m10/evaluator.py` (additive `localization` dimension), `benchmarks/*_results.md` (frozen history untouched — new dimensions apply prospectively).
- Implementation: score localization (right granularity measured with moving evidence) separately from confirmation; keep discovery strict. Report both; never average away.
- Offline tests: M8-evidence → localization 1.0 / discovery 0.0; M13-evidence → localization 0.0; historical scorecards recomputed byte-identical on old dimensions.
- Expected impact: M16 progress becomes visible even before first confirmation.
- Risks: dimension creep (mitigate: exactly one new dimension, frozen rubric, preregistered).
- Paid APIs: none.

## Explicitly deferred (not bottlenecks)
- New model families/frameworks: coverage is adequate (5 real + 2 guarded).
- Strategy auto-tuning: tallies are the honest ceiling at n=1 live runs.
- Demand-Zone target-model work: separate system; excluded by constraint.
- Full-judge live wiring: cost/benefit unproven; judge stays offline until skeptic-lite data exists.

## Dependency order
P0-1 + P0-2 (independent, parallelizable) → P1-1 (needs slice evidence shapes) → P1-2 (needs adequacy gate) → P1-3 (needs ledger + reservations) → P2 (needs new live data to score). Total: no paid calls until live validation runs, which require explicit authorization (see EVALUATION_PLAN).
