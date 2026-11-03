# M21 Phase 6 — Offline Validation Report

No live calls, no paid spend, no new benchmark campaigns. All gates
evaluated offline from deterministic tests and recorded state.

## 1. Gate summary

| Gate | Result |
|---|---|
| Full backend test suite | **635 passed, 0 failed** (~211s) — 608 pre-existing + 27 new M21 |
| New M21 tests (`test_m21_reporting.py`) | 27/27 (integrity 13, contract pins 3, harness 10, API 1) |
| M19 suites (`test_m19_provider.py`, `test_m19_integration.py`) | 35/35 green, unmodified behavior |
| M20 suite (`test_m20_reporting.py`) | 53/53 green, unmodified behavior |
| `test_meta_adapter.py` (incl. legacy repair/fallback contracts) | 25/25 green, untouched |
| M19+M20+M21+adapter subset | 140/140 in one run |
| M9/M10/API/eval-independence subset | 60/60 green, grades unchanged |
| TypeScript `tsc --noEmit` (frontend-local binary) | clean (exit 0) |
| Vite production build | succeeds (pre-existing chunk-size warning only) |
| Sealed-truth separation audit | clean — no sealed/ground-truth refs in new or touched reporting modules |
| Credential exposure scan | clean — only pre-existing `key_configured` boolean checks |
| Network-call scan on new/changed code | clean — no httpx/requests/urlopen; all provider contact via monkeypatched fakes |
| M19 artifacts / `live_runs` / sealed / scorers / M10 / Demand Zone AI | untouched (`git diff` clean on all frozen paths) |
| Live provider calls during M21 implementation | zero |

Commands: `py -m pytest model_autopsy/tests -q -p no:cacheprovider`
(635 passed); subset runs above; `cd model_autopsy/frontend &&
./node_modules/.bin/tsc --noEmit` (exit 0); `npm run build` (built);
grep audits above.

## 2. Files changed (M21 scope)

- `backend/engine.py` — additive consistency advisory on valid
  validation results + summary events (`consistency_passed/failures/
  warnings`, read-only; validity outcomes unchanged).
- `backend/api.py` — causal view exposes the advisory per summary
  (additive keys only).
- `frontend/src/CausalPanel.tsx` — one muted line surfacing a native
  report's consistency findings (no redesign).
- `tests/test_m21_reporting.py` (NEW, 27) + `M21_EVALUATION_PROTOCOL.md`
  + `M21_ARCHITECTURE_AUDIT.md` + this doc + proposal + final report.

## 3. Failures found during development (all fixed at cause)

1. My "honest advisory" fixture used the word "unconfirmed", which the
   frozen M20 `_CONFIRM_RE` (substring `confirm`) conservatively flags.
   Implementation untouched (regex is M20-frozen by design); fixtures
   reworded to "still open". Two tests affected.
2. My repair-rejection test read `payload["consistency_failures"]` off
   the gate event; the loop records that event as
   `{"passed","failures"}` (the `consistency_*` names live on repair
   *records* and summary events). Test corrected to the recorded
   contract; no production change.
3. Two harness tests assumed `meta_unavailable` turn results carry
   `summary`/`fallback` keys; the honest-stop shape omits them. Tests
   now assert via `.get()` — the early-stop contract, pinned.
4. My traceability test called `finalize` without the legal FSM walk;
   added the shared `ensure_finalizable` helper (the same path the
   driver uses).

No test was skipped or weakened; no lint/type suppression added; no
existing test modified. Production behavior changes are exactly the
M21-specified additive surfacing.

## 4. Coverage map (protocol scenarios S1–S13)

- S1 native: verbatim capture, class, eligibility, advisory, rollup.
- S2/S8 repair success: single attempt, raw text + usage, no-tool
  repair request, `model_repaired` provenance.
- S5/S9 repair rejection: original verdict stands, gate failures
  recorded, deterministic fallback.
- S6 empty: ineligible, no repair, direct fallback.
- S7 provider failure: ineligible, categorized event, honest stop
  (first-round) or fallback (repair-time), never billed as work.
- S10–S13 integrity: confirm-without-contract, terminal moves both
  directions, invented verification, unknown refs, silent drops,
  hidden contradictions (+ preservation pass), invented decimals,
  wrong counts, unledgered-tool warning, missing uncertainties.
- Provenance: three statuses end-to-end distinct through the adapter;
  investigation-id traceability; engine dedup; budget-accounted repair.
- Frozen pins: native record-not-reject preserved AND visible;
  advisory degradation never breaks validation.
- API: causal view advisory keys + `generation_status`, old keys intact.

## 5. Limitations and known risks for the live run

- Advisory regexes are conservative by M20 design (`confirm`
  substring, decimal/percentage scope, traceability-not-NLU for
  contradictions): live prose may trip advisories a human would not.
  They inform; they do not enforce.
- Validation-time snapshot predates the resolution contract, so a live
  confirmation claim may flag at summary time and read clean at
  adapter time (final state authoritative). Both records persist; the
  checklist (§5 of the proposal) reads the final-state one.
- Single fixture family (music_rank), mocked provider; live-model
  compliance with the contract is unverified by design — that is what
  the proposed run measures.
