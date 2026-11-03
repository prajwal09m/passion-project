# M19 Phase 8 — Offline Validation Report

No paid calls made. All gates evaluated offline from deterministic tests
and recorded state.

## 1. Gate summary

| Gate | Result |
|---|---|
| Full backend test suite | **555 passed, 0 failed** (~166s) — 520 pre-existing + 35 new M19 |
| New M19 provider tests (`test_m19_provider.py`) | 16/16 |
| New M19 integration tests (`test_m19_integration.py`) | 19/19 |
| M18 suites (`test_m18_integration.py`, M16/M8/M7) | green — accounting, hold, contract behavior pinned |
| `test_meta_adapter.py` (incl. 4 legacy fallback-contract tests) | green |
| TypeScript `tsc --noEmit` | clean (exit 0) |
| Vite production build | succeeds |
| API / M9 / M10 suites | green, grades unchanged |
| Sealed-truth separation audit | ok — no sealed/ground-truth refs in `live/`+`meta_api` beyond the pre-existing post-freeze scorer path in `driver.py`/`resume.py` (unchanged, scoring-only after finalization) |
| Credential exposure scan | clean on all touched files |
| Historical `benchmarks/` artifacts | unmodified (2 files added, none edited) |
| Scorer / M10 evaluators | untouched |
| Demand Zone AI | untouched |
| **Readiness verdict** | **GO — see `M19_LIVE_READINESS.md`** |

Commands: `py -m pytest model_autopsy/tests -q` (555 passed);
`npx tsc --noEmit` (exit 0); `npm run build` (✓ built); grep audits above.

## 2. Files changed (session scope)

- `backend/meta_api/requests.py` (NEW) — `validate_request` (known-bad
  refusal, unknown-good pass; role/content shape accepted), `failure_category`,
  `fallback_eligible` (chain-status + chain-in-play + unused fallback only;
  auth/transient/network/budget never eligible). No credentials handled.
- `backend/meta_api/loop.py` — pre-dispatch validation (no attempt spent
  on invalid sends); unified in-turn + cross-turn fallback (one/turn,
  full-context rebuild + recorded-results message, no chain id, separate
  attempt reserve + headroom recheck, budget refusal → `budget_exceeded`);
  honest per-round chaining labels; turn-open vs `delta_fallback` rollup;
  post-hypothesis decision nudge (decline-with-reason valid); per-turn
  `investigator_decision` event + `decision` in turn result;
  discrimination rationale scored at decision time; selection brief
  enriched (discrimination + independence + affordability criteria).
- `tests/test_m19_provider.py` (NEW, 16), `tests/test_m19_integration.py`
  (NEW, 19) + this doc + `M19_ARCHITECTURE_AUDIT.md`.

## 3. Failures found during development (all fixed at cause)

1. Validator rejected the role/content message shape (initial context has
   no `type`) — fixed validator to accept it; 5 suites green.
2. Placeholder import left in a draft branch — removed before any run.
3. Fallback dropped `tool_calls_executed/reused` from the rollup during a
   label edit — restored; legacy adapter tests pin them.
4. Rollup `context_mode` contract: legacy tests pin turn-open mode and
   `delta_fallback`-on-recovery — implemented exactly that, with honest
   per-round chaining labels on events.
5. Four `test_meta_adapter.py` legacy fallback-contract tests failed
   after the rework (event titles/details) — fixed the implementation to
   honor the recorded contract (pre-attempt refusal event with status
   detail, success/failure observability events), not the tests.
6. Two `test_m19` expectations miscounted end-of-turn reservation/skeptic
   spend (the turn runs them automatically) — corrected expectations to
   the allocator's real ledger, code untouched.

No test was skipped, weakened, or adjusted to pass (except correcting my
own new-test arithmetic to the authoritative ledger); no lint/type
suppression added. The one production-behavior change to legacy tests:
none — all 520 pre-existing tests pass unmodified.

## 4. Coverage map (Phase 7 requirements)

- Provider resilience (8.1): 16 tests — M18 400-shape recovery, valid
  chained pass, blank chain refusal, empty input/tools refusal,
  unknown-good pass, category/eligibility matrix, fallback success +
  failure, auth/5xx never fallback, fallback budget recheck (spy) +
  attempt refusal, no-dup reuse, new-work-after-recovery.
- Progression (8.2): 10 tests — decision-executed, discriminating probe
  rationale, low-value honesty, decline-with-reason, budget decline,
  no-suitable-tool, dedup reuse, confidence motion, contradiction,
  propose-only flagged incomplete.
- Closure (8.3): 5 tests + M18 suite — reserve→skeptic→verify chain,
  3-way hold competition, same-tool rejection, transition accuracy,
  report provenance (M18 covers the rest).
- Scenarios (8.4): A confirmed, B contradiction, C failure+recovery,
  D no-suitable-diagnostic — all through real `run_meta_turn` with a
  mocked provider, plus driver-level reservation/skeptic/verify callers.

## 5. Limitations and known risks for the live run

- The model writes its own hypotheses and chooses diagnostics; Scenario D
  proves a valid decline, but a propose-only turn with no reason remains
  possible (now explicitly flagged, not silently clean).
- The 400 root trigger (provider-side chain validation vs transient) was
  not determinable offline; the fix handles the class, verified against
  the exact recorded shape.
- Pre-dispatch validation passes unknown-good shapes deliberately — a
  novel invalid shape the validator cannot recognize would still be sent
  once, then recovered by the same fallback.
- Single scenario (`eval_music`), single model, one run.
