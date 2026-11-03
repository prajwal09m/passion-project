# Token-Efficiency Generalization Report (2026-10-31, no paid calls)

## What generalized without changes
- Full/Delta machinery (`meta_api/loop.py` context/delta packaging, budgets,
  wrap-up, continuation chaining, per-provider usage accounting) is already
  project-independent: it operates on investigation state, never on
  finance fields. The frozen campaigns proved it on Demand Zone.
- New `backend/contexts.py` exposes it generically: `build_context_package`
  (identity + state + evidence REFERENCES, no blobs) and
  `build_delta_package` (state + only-new items), plus `package_delta_savings`
  which reports char reduction with the explicit caveat that billed savings
  must be measured from provider usage per project.

## What was NOT assumed
- Delta is not assumed cheaper: the package API measures per project, and the
  Meta campaign showed total-input can favor Full under cache warming while
  uncached favors Delta. Strategy choice stays empirical.
- Provider accounting stays separate (Meta cached/uncached vs Groq plain).

## Verification (offline)
- Context package tests: full/delta construction from real DB state, delta
  carries only new hypotheses and no duplicate evidence refs.
- No additional paid requests were made; generalization of billed savings to
  new project types awaits the next authorized campaign, which should repeat
  the paired Full/Delta measurement per project type.
