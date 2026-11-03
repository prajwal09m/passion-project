# M14 Baseline Freeze (Phase 0)

Date: 2026-11-01. M9-M13 preserved; no historical results modified.

Verified implementations:
- Ontology: 19 dimensions (research/ontology.py).
- Invention with info_value + pooled calibration (research/invention.py); adaptive agenda with pivot detection (research/agenda.py); autonomous loop with segment-grounded seed (research/autonomous.py).
- Attribution with cross-family rules (causal/attribution.py); quality rejection via two distinct tools.
- M11 team: mandatory skeptic + investigator responses + independent judge; ablations full/no-skeptic/no-judge.
- M12 knowledge (10 categories, transfer-as-hypothesis) + verify manifests; portfolio assess + scheduler + authorization.
- Eval2 (m10/eval2.py) + corpus B (m10/scenarios_b.py + fixture_m10b 6 artifacts + sealed truth).
- Adapters honest (TF/HF guarded). Live governor caps 3/6/12/50k/$0.40. Lab 6-section workspace + /api/lab/portfolio|knowledge|corpus-b.

Metrics:
- Backend: 425 passed, 0 failed (py -m pytest model_autopsy/tests -q, ~94s).
- Frontend: tsc --noEmit clean, vite build ok.
- M13 flagship b_unit_shift: single 0.688 vs full team 0.773; controls correct; persistence no-duplicate.
- M13 live run live-d8b174527ca5 (eval_credit): completed, 3/3 rounds, 6/6 experiments, 10/12 attempts, 44181/50000 tokens, $0.057/$0.40; verdict inconclusive 0.63, discovery 0.0, no FP.
- 14 milestone_13 docs present. Prior live runs intact.

Known limitations (M14 starting problems):
- Live/offline gap: offline finds unit-shift fault, live scored discovery 0.0.
- No perturbation laboratory; no robustness maps; no mechanism-discovery layer outside ontology labels.
- No replay harness for saved live traces; no opportunity tracking per stage.
- Only 2 corpora; eval3, risk prediction, strategy learning, falsification records absent.
- Scoring frozen: existing eval2/M10 grades must not be redefined silently.
