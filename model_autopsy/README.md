# Model Autopsy — AI investigation platform backend + dashboard

Two investigation modes share one engine: **Software Autopsy** (bounded review
loop over real git changes and real test runs) and **ML Model Autopsy**
(evidence-backed diagnostics). The runtime investigator, when configured, is
**Muse Spark via the Meta Model API** (Responses API + tool calling). Without
a key the app runs honestly in manual mode: tools still execute for real and
the record clearly states Meta is unavailable.

The Demand Zone AI study (v1.0.2 frozen artifacts under `study_files/`) is the
first ML case study, in strictly read-only mode.

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
