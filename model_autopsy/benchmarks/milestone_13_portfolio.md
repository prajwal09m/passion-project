# M13 Portfolio

m12/projects persistence plus scheduler rank (importance * info_gain / cost) plus authorization gate (paid needs human token; scheduler ticks offline only). portfolio.assess advises promising, blocked, needs_review, pausable. API: /api/lab/portfolio, /api/lab/projects, /tick, /status, /propose. Dashboard section 1 shows all four buckets. Tests: portfolio assess plus m12 scheduler, budget, idempotency.
