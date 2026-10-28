# Model Autopsy — Judge Demonstration Script

**Validated end to end** (2026-10-28) in an isolated sandbox DB against the real
Demand Zone artifact and again read-only on the live app DB. Everything below
was actually executed — nothing in this script assumes.

## Pre-flight (2 minutes before the judge arrives)

Option A — **Sandboxed demo (recommended: zero writes to the app DB).**

```bash
cd "C:\Prajwal MIT\Passion"

# 1. Backend on the real artifact, but a throwaway DB:
set MODEL_AUTOPSY_DB_PATH=%TEMP%\ma-sandbox\sandbox.db
py -3 -m uvicorn model_autopsy.backend.api:app --host 127.0.0.1 --port 8002 &

# 2. Vite dev server proxying to that backend (port 5175):
cd model_autopsy/frontend
set VITE_PROXY_PORT=8002
# (or simply run one-off:)
node -e "import('vite').then(async v=>{const s=await v.createServer({root:'.',server:{port:5175},proxy:{'/api':{target:'http://127.0.0.1:8002',changeOrigin:true}}});await s.listen();console.log('sandbox UI on 5175')})" &
```

Open **http://localhost:5175/** and confirm the landing shows
"0.590 / 0.672 / 0.661 / 0.678 — pooled AUC recomputed live."

Option B — **Live demo.** Run the app normally (`py -3 -m model_autopsy.backend`
+ `npm run dev`) with the real DB. Manual investigation actions in this mode
record into the real database — history stays intact and immutable.

## The 6-step sequence (~4 minutes)

1. **The problem.** On the landing: "When performance hides the truth."
   Point at the live counters and the sentence
   *"pooled AUC recomputed live from the actual OOF artifact"*. Then the
   calibration / chronology charts — labeled **"computed from the real
   artifact"** — vs the leakage chart, explicitly labeled
   **"conceptual illustration — not a measured result."**

2. **Open the case.** Footer card "Demand Zone AI — FROZEN V1.0.2 CHAMPION" →
   open it. Note the honest framing:
   *"The archived 0.97→0.676 narrative cannot be recomputed here — the
   leaked-feature dataset is not preserved. Everything shown is currently
   reproducible from the artifact."*
   Do NOT claim we reproduce 0.97/0.98 AUC.

3. **Run a meaningful diagnostic.** In the workspace, the recorded actions are
   already visible (classification_metrics, calibration_and_error_analysis,
   time_split_validation, grouped_auc_comparison). Re-run one (a tool call
   against the real 41,221-row `oof_predictions.csv`, recorded as evidence,
   budget 5/12). The proof of life: a new action card + timeline event.

4. **Show how results challenge a hypothesis.** The recorded arc is the money
   shot of the demo:
   - Hypothesis proposed: "LightGBM_C has materially lower pooled AUC…"
   - `classification_metrics` on the real artifact: **AUC 0.6835 — the
     *highest* of all arms.** Data retells the story.
   - Hypothesis → **rejected**, with contradiction-linked evidence
     (action hash c8c80b3f…).
   - Second hypothesis: "LogisticRegression_A is materially weaker than the
     tree arms" → **supported** by a ticker-cluster bootstrap
     (ΔAUC +0.0818, CI 0.0637–0.1010, 2000 replicates, seed 42).

5. **Trace a finding to its evidence.** In FINDINGS, each entry ends with
   "evidence: action #6 calibration_and_error_analysis" etc. Clicking through
   the EVIDENCE WORKSPACE shows the exact JSON a tool returned and the
   absolute path of the artifact it came from. Every number is recomputable
   (independently verified: pooled AUCs, Brier 0.130634, precision/recall@0.5
   matched a pandas recomputation to 6 decimals).

6. **The final report.** Scroll to FINAL REPORT: deterministic, generated
   "from recorded evidence" — CONFIRMED OBSERVATIONS (with evidence hashes),
   SUPPORTED / LIKELY EXPLANATIONS, REJECTED EXPLANATIONS,
   UNRESOLVED (tools never run, budget), and the limitations section
   (e.g., "row-level bootstrap is a cross-sectional approximation; the
   case-study chart uses ticker-cluster resampling").

## Optional: honesty hail-Mary (10 seconds)

Click **"Run bounded Meta turn (≤3 rounds)"** with no `MODEL_API_KEY`
configured. The UI says exactly this (fully honest failure, no fake model
output):

> Meta unavailable: MODEL_API_KEY is not configured. Set it in the backend
> environment (see model_autopsy/.env.example) and restart, then use the
> connection test on the Integrations page.

If the judge wants the AI-driven path: put a valid Meta key in the backend
env (Integrations page → connection test first), then run it on an
investigation and watch every call get recorded as evidence.

## Talking points for judges

- All ML tools are **read-only**: they never modify the artifact or the model.
- Investigation history is immutable — every event, tool result, hypothesis
  revision and finding has a timestamp and is on the record.
- Confidence labels are honest: rejected/supported/inconclusive always trace
  back to recorded tool evidence, never vibes.
- Test data is quarantined: 55 legacy practice records exist in the DB and are
  hard-flagged `is_test_record=True` — the UI never mixes them into real
  case work.
