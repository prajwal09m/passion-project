# Milestone 3 Final Validation Report (2026-11-01, offline)

## Status ledger

| Item | Status |
|---|---|
| Research orchestration layer (11 stages, provenance) | Implemented + offline tested |
| Recon / understanding docs | Implemented + offline tested |
| Hypothesis lifecycle (evidence-gated transitions, blocked) | Implemented + offline tested |
| Heuristic experiment design (labeled, not Bayesian) | Implemented + offline tested |
| Isolated execution (copy-on-read workspaces, snapshots) | Implemented + offline tested |
| Independent verification (checklist + disagreements kept) | Implemented + offline tested |
| Open-ended discovery (workflow + candidate taxonomy) | Implemented, partially tested |
| 9-scenario challenge suite (8 families + multi) | Implemented + offline tested, 9/9 hits |
| 6-dimension evaluation (aggregate never alone) | Implemented + offline tested |
| Token-efficient contexts (74.8% char-proxy reduction) | Implemented + offline measured |
| Research Lab dashboard (8 sections) | Implemented; tsc + vite build clean |
| Flagship demo (insurance premium, end-to-end) | Demonstrated end-to-end |
| Backward compatibility (Demand Zone + suite) | Validated: full suite green |
| LLM reasoning across new projects | NOT YET VALIDATED (requires paid calls) |
| Human-reviewed assessment class | NOT YET VALIDATED |
| Container-level execution isolation | Known limitation (copy-on-read only) |

## Test counts (actual)

- New: `test_research_lab.py` — 7 tests (recon, lifecycle, design,
  verification, challenge x9, API endpoints, contexts).
- Full suite: 234 passed (209 core incl. 26 universal + 7 research;
  16 meta-readiness + 9 groq benchmark files), 0 failed.
- Challenge: 9/9 scenario hits, 13 experiments, 0 failed, 0.3-2.4 s
  per scenario, no paid calls, no new live-campaign artifacts.
- Frontend: `tsc --noEmit` clean, `vite build` success.

## Failure found and fixed in-build

Nested research-config writes silently lost (SQLAlchemy committed-state
aliasing via shallow copies). Root-caused with flush traces; fixed by
deepcopy-on-write in all research paths; covered by repeated-propose
and API persistence assertions. No weakened assertions, no skips.

## Remaining limitations

Single scenario per family; synthetic strong signals; reasoning-budget
exhaustion risk carried over; TensorFlow/HuggingFace adapters still
guarded-unavailable; ranking card new (one scenario); discovery's
novel-mechanism path exercised lightly (no novel mechanism planted).
