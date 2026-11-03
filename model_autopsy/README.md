# Model Autopsy — AI investigation platform backend + dashboard

Two investigation modes share one engine: **Software Autopsy** (bounded review
loop over real git changes and real test runs) and **ML Model Autopsy**
(evidence-backed diagnostics). The runtime investigator, when configured, is
**Muse Spark via the Meta Model API** (Responses API + tool calling). Without
a key the app runs honestly in manual mode: tools still execute for real and
the record clearly states Meta is unavailable.

The Demand Zone AI study (v1.0.2 frozen artifacts under `study_files/`) is the
first ML case study, in strictly read-only mode.

## M15 — Autonomous Breakthrough & Scientific Resolution (offline-first)

M15 adds: strict chronological AUC lab with held-out promotion gate
(`backend/perf/`), 13-class resolution engine (`research/resolve.py`),
observation→mechanism pipeline (`research/pipeline.py`), 8-kind
intervention engine (`research/intervene.py`), deterministic
trace-replay + parity (`research/replay.py`), versioned diagnostic lab
(`research/diaglab.py`), false-analogy transfer guards
(`m12/knowledge.py:check_transfer`), integrated workflow
(`research/workflow.py`), held-out strategy tallies, corpus D
(`m10/scenarios_d.py` + `runner_d.py`), and the two-track flagship
demo (`demo/flagship_m15.py`). Measured demand-zone result: baseline
held-out AUC 0.7177 → candidate 0.7226 (Δ +0.0048 [0.0009, 0.0083],
n=15,871, Brier 0.1466→0.1449). Details: `benchmarks/M15_ARCHITECTURE.md`
and `benchmarks/M15_FINAL_REPORT.md`.

## Layout

```
model_autopsy/
  backend/              FastAPI + SQLite (no secrets here)
    config.py           env-driven config, restricted path resolution
    db.py               investigations / hypotheses / actions / events
    engine.py           finite-state investigation engine (iteration + tool budgets)
    tools_registry.py   allowlists + validation + evidence recording
    software_tools.py   git diff inspection, pytest runs (never from model-chosen commands)
    ml_tools.py         real pandas/sklearn diagnostics on real artifacts
    meta_api/client.py  Responses API adapter (dev.meta.ai verified shapes)
    meta_api/loop.py    bounded tool-calling loop with function_call_output round-trips
    api.py              explicit REST contract
  frontend/             React + Vite + TS dashboard (5 pages)
  tests/                pytest suite (29 tests) incl. real-artifact checks
  .env.example          placeholder-only env template
```

## Run locally

Backend (Python 3.13, deps from the repo's requirements.txt plus fastapi):

```bash
py -3 -m model_autopsy.backend          # serves http://127.0.0.1:8000
```

Frontend:

```bash
cd model_autopsy/frontend
npm install && npm run dev              # http://localhost:5173 (proxies /api)
```

Tests:

```bash
py -3 -m pytest model_autopsy/tests -q
```

## Configure Meta (later, when you have the key)

1. Copy `model_autopsy/.env.example` values into your environment with a real
   `MODEL_API_KEY`.
2. Restart the backend.
3. Open **Integrations & Settings** → *Test connection* (GET /models, no spend).
4. Start an investigation → *Run Meta (Muse Spark) turn*.

The key lives only in the backend process environment. It is never returned
by any endpoint and never appears in frontend code.

## Safety properties already enforced

- Tool requests from Meta are validated against per-mode allowlists; unknown
  tools are refused and recorded as failures (never silently).
- Paths resolve only inside `MODEL_AUTOPSY_ALLOWED_WORKSPACES`.
- Test commands are fixed (`pytest`-family); Meta picks scope, not commands.
- Iteration and tool-call caps (3 / 12) are enforced in the engine and shown
  in the UI.
- Applying anything to the operational Demand Zone program requires an
  explicit owner approval flag; Meta alone can never grant it.
- The autonomous campaign supervisor (`autonomous_agent/`) is untouched and
  unreachable from this platform.

## Honest limitations (current build)

- The bounded revision *delivery* to a coding agent is workflow-based
  (recorded instructions in the investigation), not a live agent API —
  connect later via the documented integration point.
- Demand Zone's historical suspicious-AUC (0.97→0.676) narrative comes from
  project records; the platform recomputes only what its artifacts support
  (the four-arm OOF contrast) and labels stored claims as stored.

## Universal projects (new)

Model Autopsy is project-agnostic. To investigate a new project:
1. Describe it with a `ProjectSpec` (`backend/projects/`) and register an
   adapter (one call; see `PROJECT_ADAPTER_DEVELOPMENT_GUIDE.md`).
2. Pick a model adapter (`/api/model-frameworks` shows what is usable here;
   black-box predictions files always work).
3. Create the investigation with `"project_id"` and use the dashboard
   Projects page or `select_tools` for capability-aware diagnostics.
4. Add regression diagnostics for new tasks per
   `DIAGNOSTIC_TOOL_DEVELOPMENT_GUIDE.md` (no engine changes needed).

Demand Zone AI remains the built-in reference project; its endpoints,
charts, and frozen campaign evidence are unchanged.

## Research lab (autonomous investigations)

Give the lab an unfamiliar ML project and ask what is wrong with it:
1. Create an ML investigation (with `"project_id"` when registered).
2. Open the Workspace **Research lab** section and press
   **Run autonomous cycle (offline)** — or `POST
   /api/investigations/{id}/research/run`. No key, no spend.
3. Read hypotheses, experiments, independent review, and the forensic
   report; full evidence stays addressable by id. Details and honesty
   boundaries: `benchmarks/MILESTONE_3_FINAL_VALIDATION_REPORT.md`.

## Independent evaluation (Milestone 4)

Unfamiliar projects with concealed failure mechanisms, scored against
sealed ground truth — fully offline, no keys, no network:

```bash
py -3 -m model_autopsy.backend.eval.runner --all \
  --out model_autopsy/benchmarks/eval_runs
```

Or open the dashboard **Evaluation** section (projects, runs,
per-dimension scorecards, evidence drill-down, blind human review).
Details: `benchmarks/m4_evaluation_instructions.md` (+ design,
separation, scoring, security, human-review, results docs).
The runner refuses to start if provider credentials are set.

## Live Meta pilot (Milestone 5 — authorized single run only)

Exactly one live investigation with Meta AI (Muse Spark) as
investigator, hard-capped (3 rounds / 6 experiments / 12 attempts /
50k tokens / $0.40). CLI only — the dashboard cannot spend:

```bash
# Preflight first (refuses launch on any failure, before any request):
py -3 -m model_autopsy.backend.live.cli --project eval_turbine
```

Pilot executed 2026-11-01: `live-140167117ef5` (eval_turbine)
completed — verdict `partial`, overall 0.55, $0.0308 spent
($0.0921 incl. preserved infra-failed first attempt). An earlier
infra attempt is preserved alongside it; both are visible read-only
under **Evaluation** → **Live Meta pilot**.
Details: `benchmarks/milestone_5_*.md`.
Do not run additional live investigations without explicit
authorization; never compare the live score against the deterministic
0.945 baseline as if they measured the same thing.

## Milestone 6 — Autonomous causal diagnosis (offline complete; live interrupted)

New engine: hypothesis competition, selection rationale, changepoint /
residual-time / shift diagnostics, evidence graph, causal discipline
gate, extended report validation, 14-stage workflow, 12-scenario
concealed challenge suite, dashboard causal view.
Details: `benchmarks/milestone_6_{postmortem,validation,results}.md`.
The single authorized live run (`eval_claim`, `live-ae844753edce`)
was interrupted by an operator timeout in round 2, then resumed in
place under fresh authorization to `completed`: M4 `inconclusive`
0.62, valid structured summary, $0.054/$0.40 spent. Same run ID, no
duplicate work; interruption history preserved (`INTERRUPTED.md`).
Do not run further live evaluations without fresh authorization.

## Milestone 7 — Closed-loop autonomous investigation (offline complete; one live run)

Closed feedback loop: deterministic post-tool evidence linking (statuses
move in the live path), per-turn selection briefs with adherence records,
driver stopping gate, `residual_feature_dependence` diagnostic, hardened
recovery. Live run `live-1e19b2cdedfe` (`eval_credit`) completed with the
first evidence-driven status transitions — but exceeded the experiment
cap (8/6, disclosed) and the summary stayed invalid; both fixed offline
and proven by tests. Details: `benchmarks/milestone_7_*.md`.
Do not run further live evaluations without fresh authorization.

## Milestone 8 — Autonomous research reliability, discovery & validation (offline complete; one live run)

Atomic execution safety (one shared Budget across driver/loop/resume;
crash-conservative reconcile; the M7 8/6 breach shape cannot recur),
versioned `m8-v1` report contract with fresh-context repair and a
labeled records-only deterministic fallback, diagnostic coverage layer
with missing-measurement-driven selection, subgroup/calibration/leakage
linker rules (per-segment gaps now link to hypotheses), 12-scenario blind
challenge with dimension means (evidence/selection/reporting/efficiency
1.0, discovery 0.917, coverage 0.665), dashboard coverage + validation
views. Live run `live-dbf6a5b3fbff` (`eval_rent`) completed **within
all caps** (6/6 experiments exact stop, $0.03394/$0.40): district-C MAE
concentration (ratio 6.2) measured live with evidence links, 5
evidence-driven revisions, honest inconclusive fallback (both model
summaries absent). M4 `inconclusive` 0.62 (not comparable across
milestones). Details: `benchmarks/milestone_8_*.md`.
Do not run further live evaluations without fresh authorization.

## Milestones 9–12 — Research laboratory, validation, collaboration, continuity (offline complete; one integrated live run)

M9: autonomous research loop (agenda → competing hypotheses → invented
specs → attribution → confounders → stopping) + 8-scenario challenge
with frozen means; M7 double-contradiction incompatibility diagnosed
and resolved (mechanism equivalence + rewritten test + denial-symmetry
hardening from a live-run finding). M10: 8 unseen projects with sealed
truth, evidence-required independent evaluator (discovery 0.906),
replication, stats, sklearn+torch cross-framework (TF/HF unclaimed).
M11: six contracted roles, thread-safe shared ledger, blocking skeptic
challenges, independent judge, preserved dissent. M12: persistent
projects, idempotent resume, approval-gated scheduler,
transfer-guarded memory, reproducibility grades, Laboratory dashboard
tab (`/api/lab/*`). Integrated live run `live-c0cae8776976`
(`eval_turbine`) completed within all caps (2/3 rounds, 6/6
experiments, $0.035/$0.40), verdict inconclusive 0.62. Details:
`benchmarks/milestone_9_finalization.md`, `milestone_10_*.md`,
`milestone_11_*.md`, `milestone_12_*.md`,
`integrated_m9_m12_validation.md`, `integrated_m9_m12_live_results.md`.
Do not run further live evaluations without fresh authorization.

## Setup (unchanged, verified)

## Milestone 13 — Generalized discovery, verification, portfolio (offline complete; one live run)

M13A discovery: 19-dimension diagnostic ontology, invention with pooled
calibration (bins 10/5) and info-value on every spec, adaptive agenda
with pivot detection, segment-grounded hypothesis seeding. M13B:
cross-family belief moves only on explicit commitments, quality
rejection via two distinct tools. M13C: mandatory skeptic with
investigator responses and independent judge, evaluated full vs
no-skeptic vs no-judge. M13D/E: structured knowledge with
transfer-as-hypothesis plus independent verification manifests. M13F:
eval2 multi-dimension scoring plus second corpus B (6 scenarios,
sealed truth) plus novelty reporting. M13G/I: portfolio intelligence
plus approval-gated scheduler and atomic budget. Adapters stay
honest (TF/HF guarded). Dashboard Lab is a 6-section research
workspace; new APIs `/api/lab/portfolio`, `/api/lab/knowledge`,
`/api/lab/corpus-b`. Flagship `demo/flagship_m13.py` on unfamiliar
`b_unit_shift`: single 0.688 vs team 0.773. Live run
`live-d8b174527ca5` (`eval_credit`) completed within all caps
(3/3 rounds, 6/6 experiments, 10/12 attempts, 44181/50000 tokens,
$0.057/$0.40), verdict inconclusive 0.63 with no false positive.
Details: `benchmarks/milestone_13_*.md` (14 docs).
Do not run further live evaluations without fresh authorization.

## Setup (unchanged, verified)

Backend: `py -m pytest model_autopsy/tests` (439 passing, file DB; 425 at M13 close plus 14 M14 tests).

## Milestone 14 — The autonomous ML scientist (offline complete; one live run)

M14 adds observation-first discovery (mechanism candidates with
capped confidence, unknown-unknown reporting), composed experiment
invention with sealed-leak validation, a hash-guarded perturbation
lab with never-safe-untested maps, live audit/parity/opportunity
tracking, predictive risk hypotheses, versioned research strategies,
falsification with layered confidence, a cross-project research
network, and Evaluation 3.0 with third corpus C (interaction,
robustness, novel saturation, combined, clean, thin; sealed truth).
M9–M13 changed only additively (segment vocabulary plus
data-driven fallback, interaction/robustness evaluator words,
non-numeric-safe aggregation). Flagship `demo/flagship_m14.py` on
unfamiliar c_robustness runs all 17 stages (single 0.688 vs team
0.773, mechanism found, verification honestly not-reproduced via
independent tool). Live run `live-ecdd47fafd9d` (`eval_music`,
unused in development) completed within caps (2/3 rounds, 6/6
experiments, 30170/50000 tokens, $0.037/$0.40), verdict
inconclusive 0.63 with no false positive; audit shows 6
opportunities with 1 diagnosable loss at recognition. Details:
`benchmarks/milestone_14_*.md` (18 docs). Do not run further live
evaluations without fresh authorization.
Frontend: `cd model_autopsy/frontend && npx tsc --noEmit && npm run build`
(tsc + vite clean). No network or API keys are needed for tests; live
campaigns are separate, authorized operations with their own frozen
protocols.
