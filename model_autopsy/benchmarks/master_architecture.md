# Model Autopsy — Master Architecture (M9–M12)

## Layers
1. Evidence engine (M5–M8): real tools (`ml_tools`,
   `task_diagnostics`, `causal/adaptive`), validation
   (`tools_registry`), durable actions, linker with explicit
   relationships, attribution with denial symmetry and
   mechanism equivalence, coverage, planning, budgets.
2. Autonomous research (M9): question agenda, competing
   hypotheses, spec invention/validation/execution/
   interpretation, confounder analysis, stopping policy.
   All offline, deterministic.
3. Independent validation (M10): sealed corpus, evaluator with
   evidence-required grades, replication, stats, cross-framework.
4. Collaboration (M11): six roles, shared ledger, skeptic +
   judge, preserved dissent.
5. Continuity (M12): file-backed projects, idempotent
   experiments, checkpoints, scheduler, transfer-guarded memory,
   authorization boundary, reproducibility grades, Laboratory
   dashboard (`Lab.tsx` + `/api/lab/*`).
6. Live pilot (all eras): bounded Meta loop
   (`live/driver.py` + `meta_api/loop.py`) under governor caps
   (3 rounds / 6 experiments / 12 attempts / 50k tokens / $0.40),
   preflight with separation audit, preserved artifacts.

## Trust invariants
Correlation ≠ causation; mentioning ≠ evidence; contradiction
needs mechanism-bearing measurement; ambiguous evidence links
nothing; provenance on every link; inconclusive is legitimate;
investigator never sees sealed truth; no fabricated runs.
