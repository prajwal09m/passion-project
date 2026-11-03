# Autonomous Research Architecture (Milestone 3, Part 1)

Offline implementation; no provider calls, no paid campaigns. All
measurements below are from deterministic runs on 2026-11-01 unless
stated otherwise.

## Layering (what was preserved, what was added)

Preserved untouched: universal investigation engine (`engine.py` FSM,
budgets, evidence links, deterministic `build_report`), project/model
adapters, diagnostic registry + capability selection, provider
interface, Full/Delta context packages, evidence provenance, Demand
Zone endpoints/charts/reports, frozen benchmark artifacts, credential
handling (keys only from env, never stored/logged/returned).

Added `backend/research/` ABOVE the engine (never a rewrite):

| Module | Responsibility | State / persistence |
|---|---|---|
| `recon.py` | Project-understanding document (Part 2) | returned doc + `research.stages.project_understanding` |
| `hypotheses.py` | Hypothesis cards + validated transitions (Part 3) | `research.hypotheses[]` in investigation config (no DB migration) |
| `experiments.py` | Heuristic experiment design + isolated execution (Parts 4-5) | run workspaces under `backend/data/research_runs/{inv}/{exp}/` |
| `verification.py` | Independent deterministic review (Part 6) | `research.reviews[]`; disagreements preserved |
| `discovery.py` | Anomaly workflow + candidate taxonomy (Part 7) | `research.taxonomy` (`base` + `novel: candidate`) |
| `lab.py` | 11-stage orchestration driver | `research.stages.*` + `research.report` + timeline events |
| `challenge.py` | 9-scenario suite definitions (Part 8) | fixtures + sealed ground truth (tests only) |
| `evaluate.py` | 6-dimension scoring (Part 9) | per-run score dicts |
| `rcontexts.py` | Reference summaries + dedup + measurement (Part 10) | char-proxy + optional billed usage |

## The 11 stages (explicit state, inputs, outputs, provenance)

`lab.STAGES`: project_understanding -> reconnaissance -> planning ->
hypothesis_generation -> diagnostic_selection -> experiment_design ->
experiment_execution -> result_interpretation -> hypothesis_revision ->
independent_verification -> final_reporting.

Each stage writes `research.stages.{name}` (inputs summarized, outputs
recorded) plus a `tool_result` timeline event (`Research stage:
{name}`), so the full pipeline is replayable from the record. The
final forensic report is persisted as `research.report` with a
`report` event. Provider independence: the driver takes no LLM import;
the default reasoner is deterministic triage (`_triage_hypotheses`).
A provider-backed reasoner can be injected later behind the same
hypothesis/experiment interfaces.

## Data-flow integrity fix found during build

Repeated in-place appends to nested `research.*` lists silently lost
writes: SQLAlchemy's committed-state snapshot shares nested objects
with shallow copies, so flush compared equal and issued no UPDATE.
Fixed by `copy.deepcopy` on every research read-modify-write path
(`hypotheses._space`, `lab._stage`/report, `verification`,
`discovery`). Covered by `test_hypothesis_lifecycle_*` (second-propose
persistence) and the research API test. The pre-existing engine module
already used `list(...)` copies and was unaffected.

## API + UI surface

- `POST /api/investigations/{id}/research/run` — offline autonomous cycle.
- `GET /api/investigations/{id}/research` — stages, hypotheses, reviews,
  taxonomy, report.
- `POST .../research/hypotheses` + `POST /api/research/hypotheses/{hid}/transition`.
- Frontend: `ResearchLabPanel` (8 sections per Part 11) embedded in the
  ML Workspace; `api.ts` `researchRun/researchState` + types.

## Status

Implemented + offline-tested (7 research tests green, 9/9 challenge
scenarios hit). Requires-live-inference: LLM reasoning quality across
new projects (needs paid calls; prior frozen Demand Zone campaigns
cover the method, not these projects).
