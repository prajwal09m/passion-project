# Milestone 12 Architecture

```
project JSON (atomic writes)          memory.jsonl (kind-tagged, pinned)
        |                                        |
scheduler.tick --> offline executor | paid --> awaiting-approval
        |                                        |
authorization.require (human token, single-use, per-scope)
        |
repro.snapshot/grade --> exact | approximate | unreproducible
        |
FastAPI /api/lab/* --> Lab.tsx (Laboratory tab)
```

No background daemons: scheduling happens on explicit ticks
(API call or offline runner), so nothing can silently spend.
The lab root defaults to model_autopsy/.lab (git-ignored).
