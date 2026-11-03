# M20 Phase 8 — Offline Validation Report

No live calls, no paid spend, no new benchmark campaigns. All gates
evaluated offline from deterministic tests and recorded state.

## 1. Gate summary

| Gate | Result |
|---|---|
| Full backend test suite | **608 passed, 0 failed** (~174s) — 555 pre-existing + 53 new M20 |
| New M20 tests (`test_m20_reporting.py`) | 53/53 (classification 10, repair 16, integrity 12, fallback 10, regression 5) |
| M19 suites (`test_m19_provider.py`, `test_m19_integration.py`) | 35/35 green, unmodified behavior |
| `test_meta_adapter.py` (incl. legacy repair/fallback contracts) | 25/25 green (4 fixtures updated at cause, see §3) |
| M9/M10/API suites (`test_m9_*`, `test_m10_validation.py`, `test_api.py`, eval-independence, universal) | 77/77 green, grades unchanged |
| TypeScript `tsc --noEmit` | clean (exit 0) |
| Vite production build | succeeds (pre-existing chunk-size warning only) |
| API smoke (TestClient: health, create, causal view) | OK — `report_validation` carries `summaries`/`repairs`/`generation_status`/`fallbacks` |
| Sealed-truth separation audit | clean — no sealed/ground-truth refs in new reporting modules or `live/adapter.py` |
| Credential exposure scan | clean on all touched files |
| M19 historical docs + `live_runs/m19-music-01` | untouched (never written by M20 work) |
| Scorer / M10 evaluators / fixtures / sealed truth | untouched |
| Demand Zone AI | untouched |
| Live provider calls during M20 | zero (all provider interaction via monkeypatched fakes) |

Commands: `py -m pytest model_autopsy/tests -q -p no:cacheprovider`
(608 passed); `./node_modules/.bin/tsc --noEmit` (exit 0);
`npm run build` (built); grep audits above; TestClient smoke above.

## 2. Files changed (M20 scope)

- `backend/causal/summary_class.py` (NEW) — 7-way output classifier +
  repair-eligibility boundary.
- `backend/causal/report_consistency.py` (NEW) — authoritative snapshot
  builder + 10-guarantee check + read-only fingerprint + repair gate.
- `backend/causal/fallback.py` — v2 full-section shape (16 sections);
  all M8 keys preserved byte-identically; optional session/usage inputs.
- `backend/meta_api/loop.py` — compact reporting contract (system prompt
  + wrapup nudge); eligibility-gated single repair; prohibitions +
  example in repair prompt; repair-output persistence; consistency gate
  on repair acceptance with `repaired_via` marking.
- `backend/engine.py` — additive `output_class`/`output_class_reason` on
  validation results + summary events (validation behavior unchanged).
- `backend/live/adapter.py` — additive `report_generation_status` +
  `report_provenance` (status/class/repair/consistency/read-only flag/
  schema/timestamp/fallback reason) on every eval report.
- `backend/api.py` — additive `repairs` trail + `generation_status` in
  the causal diagnosis view (existing keys unchanged).
- `frontend/src/CausalPanel.tsx` — output-class column, one-line
  generation-status badge, repair-attempt line (no redesign).
- `tests/test_m20_reporting.py` (NEW, 53) + this doc +
  `M20_ARCHITECTURE_AUDIT.md` + `M20_FINAL_RESULTS.md`.
- `tests/test_meta_adapter.py` — 4 fixture/expectation updates at cause
  (§3); no production logic weakened for them.

## 3. Failures found during development (all fixed at cause)

1. My first M20 tests used <20-char prose fixtures, which the classifier
   (correctly) calls `empty_output`; repair is skipped by design —
   fixed fixtures to substantive prose, implementation untouched.
2. Strict repair gate rejected my own success fixtures that dropped a
   hypothesis — the gate was right; fixtures now account for every
   hypothesis, matching the specified guarantee.
3. `test_ml_instructions_stay_compact_but_behavioral` (<2000 chars):
   the M20-mandated contract (schema table, vocabulary, representation
   rules, 9 prohibitions, example) cannot fit the old budget alongside
   the required behavioral clauses — bound raised to <4000 with a
   comment; all keyword requirements still enforced.
4. Repair-event count 2→3 (new consistency-gate event) in two legacy
   tests — expectations updated; single-attempt and no-extra-spend
   assertions still pin the behavior.
5. Two legacy fixtures used 13–14-char final messages that no longer
   qualify for repair (correctly: empty→fallback) — messages made
   substantive, restoring the documented repair-path coverage.
6. Full-suite sqlite handle exhaustion (1 flake in 608): M20 tests now
   close sessions via an autouse fixture; full suite re-ran 608/608.

No test was skipped or weakened to pass; no lint/type suppression
added. Production behavior changes are exactly the M20-specified ones.

## 4. Coverage map (Phase 7 requirements)

- Classification (10): valid, prose-without-block (M19 verbatim text),
  malformed, missing-field, bad-type, unknown-hypothesis, empty,
  provider-failure, extra-fields-valid, conflicting-blocks.
- Repair (16): 4 eligible classes succeed end-to-end through the real
  `run_meta_turn`; 8 invalid-repair rejections (malformed return,
  unsupported claims, terminal move, dropped contradiction, invented
  verification, invented tool exec, added refs, changed resolution);
  provider-failure→fallback; single-attempt enforced; empty→no-repair;
  eligibility matrix; raw-output persistence.
- Integrity (12): confirm-only-with-contract, no prose-confirmation,
  no terminal resurrection/demotion, no silent drops, unknown/fake
  refs, fake vs recorded measurements, wrong counts, invented vs
  recorded verification, contradiction preservation, budget figures,
  read-only assembly fingerprint.
- Fallback (10): complete/partial/no-findings/multi-status/
  confirmed+unresolved/contradictions/missing-metadata/provider-failure/
  invalid-summary/large-graph determinism.
- Regression (5): eval-report contract stable, fallback provenance,
  original-preserved-across-repair, M19 suites intact, scorer keys
  unchanged.

## 5. Limitations and known risks

- Number-claim detection covers decimals/percentages against recorded
  corpora; prose counts ("two hypotheses") are unchecked by design.
- Contradiction preservation is action-id-traceable, not
  natural-language understanding: a summary that cites the action but
  misdescribes it passes the gate (validator scope, documented).
- The generation contract adds ~1.8KB to every ml round-trip prompt
  (~440 tokens); wrapup nudge re-states it at low budget.
- Native-valid summaries are recorded-not-rejected on consistency
  findings (audit decision); only repairs must pass all gates.
- Single scenario family (eval_music fixtures), mocked provider only;
  live-model compliance with the new contract is unverified by design
  (M20 is strictly offline; no M21 started).
