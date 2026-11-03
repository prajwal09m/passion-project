# M15 Architecture — Autonomous Breakthrough & Scientific Resolution

Offline-first. No Meta/Groq calls. All new modules are additive; M9–M14
behavior is preserved.

## New modules

- `backend/perf/recon.py` (1.1) — read-only reconnaissance: n, period,
  base rate, null share, class balance, bottleneck notes.
- `backend/perf/measure.py` (1.3) — strict AUC: dataset/split/positive/
  period/version/n + bootstrap CI; paired-delta on identical observations;
  subgroup AUC with thin-data inconclusive.
- `backend/perf/lab.py` (1.1/1.2) — chronological demand-zone lab
  (train <2024, val 2024, test ≥2025 HELD-OUT), leakage exclusion,
  three hypothesis-led LightGBM candidates with reproducible artifacts.
- `backend/perf/promote.py` (1.4) — promotion gate: held-out delta CI>0,
  Brier ≤+0.01, no subgroup regression >0.02, n≥100; rollback retained.
- `backend/research/resolve.py` (Phase 2) — 13-class evidence-derived
  diagnosis + A–H next-experiment + 6-status contract; never confirms
  unresolved work.
- `backend/research/pipeline.py` (Phase 3) — observation→mechanism
  pipeline with diversity clustering, counter-hypothesis demand,
  why-lead explanation.
- `backend/research/intervene.py` (Phase 4) — 8 controlled intervention
  kinds; synthetic probes labeled as such; confounding checks required.
- `backend/research/replay.py` (Phase 5) — deterministic replay of
  recorded investigations; missed-opportunity + parity report; no model
  calls.
- `backend/research/diaglab.py` (Phase 8) — propose→controlled cases→
  compare→FP/FN→robustness→independent reproduction→admit/reject.
- `backend/m12/knowledge.py:check_transfer` (Phase 9) — false-analogy
  guards (task mismatch, no shared columns, prior-misled warning).
- `backend/research/workflow.py` (Phase 10) — recon→…→memory with
  checkpoints, idempotency keys, budget enforcement.
- `backend/research/strategies.py:summarize` (Phase 6) — held-out
  outcome tallies; resolution without moving evidence scores zero
  (anti-reward-hacking by construction).
- `backend/m10/runner_d.py` + `scenarios_d.py` (Phase 7) — fourth corpus:
  d_null (correct-null), d_thin (inconclusive), d_combined (subgroup),
  d_confounded (confounded regression).
- `demo/flagship_m15.py` (Phase 12) — two-track demo (pivot + null)
  plus diagnostic self-improvement; deterministic rerun.

## API additions (all offline)

- `GET /api/lab/replay/{id}`, `GET /api/lab/strategy-performance`,
  `GET /api/lab/eval-d`, `POST /api/lab/workflow/run`,
  `GET /api/lab/flagship-m15`, existing `/api/lab/model-performance`,
  `/api/lab/corpus-d`.

## Dashboard (Lab.tsx)

Sections map to the spec: A-model performance, B-investigation,
C-resolution, D-intelligence (strategies + flagship), E-evaluation
(four corpora), F-portfolio. All values come from live backend calls;
unmeasured states say so explicitly.

## Guarantees

- Sealed truth never imported by investigator paths (scenarios,
  runners, autonomous, workflow, flagship).
- Chronological splits for temporal tasks; identical-observation
  pairing for deltas; untouched held-out test.
- Skeptic/challenge preserved: resolve + pipeline require competing
  explanations and falsification conditions.
