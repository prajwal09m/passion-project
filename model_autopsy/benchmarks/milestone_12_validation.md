# Milestone 12 Validation Gates

- Persistent projects (create/pause/load/list). PASS.
- Safe resume: idempotent experiments, no double count. PASS.
- Durable memory + transfer guard (1-project refused,
  2-project promoted). PASS.
- Scheduling: ranked, budget-capped, paid parks without
  approval (unit + API). PASS.
- Authorization boundary: no self-minting path; UI never
  issues tokens. PASS (by construction + refusal test).
- Reproducibility: exact/approximate/unreproducible. PASS.
- Dashboard + API smoke (7 tests). PASS.
- TypeScript clean. PASS.
