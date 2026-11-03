# M16 Pipeline Map — Actual Live Execution Path (Implementation-Level)

Read-only map. Every box names the file, function, and the test or
artifact proving it runs. "Live path" = code that executes during a Meta
investigation (`backend/live/driver.py` → `backend/meta_api/loop.py`).
"Offline path" = code that runs in deterministic evals/demos but has no
live caller. Confusing the two is the central documentation hazard this
map exists to prevent.

```
 PROJECT UPLOAD / RECON
  backend/research/invention.py::artifact_facts()      [A]
   - reads CSV header/columns/segments/temporal cols (offline peek)
   - live caller: meta_api/loop.py context build (column-alias brittle:
     music_rank.csv 'relevance/score' naming broke artifact_summary)
        |
 MODEL PROPOSES HYPOTHESES (tool: propose_hypothesis)
  backend/engine.py::propose_hypothesis()               [B]
   - cap: config.MAX_HYPOTHESES_PER_INVESTIGATION; records origin 'meta'
   - live evidence: 2-3 hypotheses per run (all runs, hypotheses.json)
        |
 SELECTION BRIEF (advisory, model may ignore)
  backend/causal/planning.py::plan_next()              [C]
  backend/causal/selection.py::rank_candidates() /
    score_candidate() — qualitative high/medium/low, NO numeric EIG
    ("no numeric information-gain is fabricated", selection.py:76-80)
   - recorded as 'selection' events (4-6 per run, events_dump.json)
   - M7 defect (fixed): brief ranked subgroup family "low" wrongly
        |
 MODEL PICKS TOOL (live)  ≠  invention.propose (offline only)
  backend/meta_api/loop.py::run_meta_turn()            [D]
   - offers backend/tools_registry.py::meta_tool_schemas(inv.mode)
   - model emits tool calls; Budget reserves pre-dispatch (governor.py)
   - offline invention.py::propose()/validate()/execute()/interpret()
     has NO live caller (verified: no import in loop.py/driver.py)
        |
 TOOL EXECUTES (engine.run_tool → ml_tools / task_diagnostics /
                causal/adaptive)                       [D]
   - 6 actions/run typical; ~3 are propose_hypothesis bookkeeping
   - failures preserved (music artifact_summary, M5 split validation,
     M7 first classification_metrics call)
        |
 ATTRIBUTION (linker; live loop auto-links some runs)
  backend/causal/linker.py::link_tool_result()         [E]
   - _family() substring rules (_is_subgroup/_is_bias/…); negation
     handling added in attribution.py::denies_family() (M9 fix)
   - known mud: same 'supports' attached to denying hypotheses
     (M8 H3, M9int H1-denier/H3-denier — evidence_refs quoted in
     M16_FAILURE_ANALYSIS.md)
   - live linker events: 0 (M5/M6/M13), 1 (M7), 2 (M8/M9int/M14)
        |
 HYPOTHESIS STATUS (often never moves live)
  backend/engine.py::link_evidence() / update path       [F]
   - supports/contradicts move belief; NON_MOVING_RELATIONS stored
     visibly without status change
   - live statuses: frozen-proposed (M5/M6/M13), partial moves (M7/M14),
     active (M8), wrongly-all-supported (M9int)
        |
 MULTI-AGENT (OFFLINE ONLY — no live caller)            [F]
  backend/m11/team.py::investigate() — runs AFTER autonomous base;
    skeptic blocking challenges + judge verdicts recorded in ledger
  backend/m11/roles.py — role contracts (7 tests)
  backend/research/challenge.py — challenge scenarios, NOT a live
    skeptic (name collision hazard: 'challenge' = eval scenarios)
   - live events_dump.json: zero skeptic/judge/challenge kinds, all 7 runs
        |
 RESOLUTION + REPORT (M15 resolve offline-only live)     [G]
  backend/research/resolve.py::diagnose()/contract() — no live caller
  backend/engine.py::build_report()/finalize() + causal/fallback.py
   - structured summaries INVALID or ABSENT in 4/7 live runs
     (M5, M7, M8×2, fallback_used=true in M8/M9int/M13/M14 manifests)
        |
 SCORING (post-freeze, two incompatible families)       [G]
  live: M4-family heuristic scorecard (discovery/evidence/reasoning/
    calibration/efficiency/reproducibility) — scorecard.json
  offline: m10/evaluator.py (moving-evidence rule) → eval2.py → eval3.py
   - discovery = naming hypothesis WITH moving evidence + key tool
     measured; M5 partial-credit vs M6+ strict (rule change documented)
```

## Stage-to-source index (A–G)

- A: `research/invention.py::artifact_facts` (line 25); `research/recon.py`;
  `model_adapters/__init__.py` (9-framework registry); tests
  `test_universal_projects.py`, `test_m9_memory_profile.py` (33).
- B: `engine.py::propose_hypothesis`; `research/hypotheses.py::transition`;
  `research/pipeline.py::candidates/diversify`; `research/mechanisms.py`.
- C: `causal/selection.py::score_candidate/rank_candidates`;
  `causal/planning.py::plan_next`; `causal/coverage.py`;
  `research/invention.py::propose` + `info_value` dict (lines 98–135:
  distinguishes_n + cost + power_limits + mislead_risk — heuristic proxy,
  explicitly not EIG); tests `test_m9_invention.py`.
- D: `meta_api/loop.py::run_meta_turn` (line 321); `live/driver.py`,
  `live/governor.py` (Budget), `live/resume.py`; `tools_registry.py`;
  `ml_tools.py` (+`ranking_slice_diagnostics` — unused live);
  `task_diagnostics/__init__.py`; tests `test_live_investigator.py` (17).
- E: `causal/linker.py::link_tool_result` (line 262);
  `causal/attribution.py::classify/denies_family/same_mechanism`;
  `causal/evidence_graph.py`; `causal/confounders.py`;
  `causal/diagnosis.py`; tests `test_m9_attribution.py`,
  `test_m9_confounders.py`.
- F: `m11/team.py::investigate` (line 42), `m11/roles.py`,
  `m11/ledger.py`; `research/challenge.py::get_scenario` (eval, not live);
  offline `research/pipeline.py::why_lead`, `research/verification.py`;
  `m10/replication.py::replicate` (independent second probe).
- G: `research/resolve.py` (13 classes, 6 statuses);
  `engine.py::build_report/finalize`; `causal/fallback.py`,
  `causal/report_schema.py`, `causal/report_validation.py`;
  `m10/evaluator.py::grade` (line 50), `m10/eval2.py`, `m10/eval3.py`;
  `eval/scorer.py` (live heuristic); `live/audit.py`,
  `research/replay.py`, `research/workflow.py`.

## The two loops, contrasted

| Aspect | Live loop (model-driven) | Offline autonomous loop |
|---|---|---|
| Entry | `live/cli.py` → `driver.py` → `loop.py::run_meta_turn` | `research/autonomous.py::run_autonomous` |
| Hypotheses | model-worded via tool | seeded per family + segment-grounded |
| Experiment choice | model picks from schemas + advisory brief | `invention.propose` ranked by distinguishes_n/cost |
| Attribution | `linker.link_tool_result` (some runs) | same linker + team probes |
| Skeptic/judge | NEVER (0 events, 7 runs) | `m11/team.py` post-pass |
| Resolution | report/fallback only | `resolve.diagnose/contract` recorded |
| Verification | none live | `m10/replication.py` second probe |

M16 implication: every offline strength in the right column needs a
budgeted live caller in the left column — or it cannot affect live
discovery by construction.

## Phase 1 delta (implemented, offline-proven; see
`model_autopsy/benchmarks/M16_PHASE1_IMPLEMENTATION.md`)

- Experiment choice (live): + `live/reserve.py::run_reserved` once per
  investigation — top `invention.propose` spec, budget-enforced;
  `selection.py`/`planning.py` now list `ranking_slice_diagnostics` +
  `segment_quality_screen`.
- Attribution (live): + `attribution.classify` adequacy gates
  (pooled-vs-segment, AUC-vs-top-K → `relevant_to`); linker records
  no-bearing notes.
- Skeptic (live): + `live/skeptic.py::review` at turn end (budgeted
  probe or preserved dissent); judge stays offline.
- Summaries: + `engine.grounded_summary` + grounded repair prompt.
- Facts: + `artifact_facts().column_mapping` confidence record.
- Dashboard: + `GET /api/investigations/{id}/m16` + Workspace M16 card.
