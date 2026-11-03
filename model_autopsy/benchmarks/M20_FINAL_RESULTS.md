# M20 Final Results — Reliable Scientific Reporting & Evidence-Preserving Summary Repair

## 1. Executive summary

M19 closed the first live investigation but exposed a reporting gap:
the model returned prose without a valid structured summary, the
bounded repair also returned prose, and the system fell back to a
minimal deterministic report. M20 makes valid, readable,
evidence-grounded reporting the reliable outcome — not the lucky one —
without touching investigation science. Ship: a 7-way output
classifier, a compact reporting contract with prohibitions and an
example, eligibility-gated single-attempt repair with persisted raw
output, authoritative consistency gates on repair acceptance, a
full-section deterministic fallback, explicit per-report provenance
(`model_native` / `model_repaired` / `deterministic_fallback`),
dashboard/API surfacing, and 53 adversarial + regression tests.
Full suite: **608 passed, 0 failed**. Zero live calls, zero spend,
M19/M9/M10/Demand-Zone untouched.

## 2. M19 summary-repair failure analysis

Two `meta_response` turns produced one-line status prose, never a
```investigation_summary block. Validation failed with a single
generic error (`no structured summary found`). The repair request was
well-formed (errors + rules + roster + grounded facts + ledger +
budget) but the repair response again contained no block — a
model-behavior failure twice in a row, not a transport edge case.
The repair's raw output was never persisted (only valid/errors/usage),
so the exact repair text is unrecoverable from events. The fallback
fired correctly and honestly, but covered only conclusion +
uncertainties + recommended_next + evidence ids.

## 3. Root cause

Six causes (audit: `M20_ARCHITECTURE_AUDIT.md`): (R1) the format
contract was one subordinate clause with a field-name mismatch
(`basis` vs `basis_action_ids`), no vocabulary, no example;
(R2) no output classification — every failure one generic error;
(R3) repair was a bare re-request with unpersisted output;
(R4) assembly trusted a `valid` summary verbatim with no
authoritative re-checks; (R5) fallback minimal and under-surfaced;
(R6) provenance was two booleans.

## 4. Output classification

`causal/summary_class.py`: `valid_structured`, `prose_without_block`,
`malformed_block`, `schema_invalid`, `semantically_invalid`,
`empty_output`, `provider_failure` — recorded on every validation
result and summary event, with repair eligibility
(only the four middle classes). Raw model output preserved in the
existing event payload; never overwritten by repair.

## 5. Structured generation improvements

`loop.py::_SUMMARY_CONTRACT` (~1.8KB): required/optional schema table,
status vocabulary, per-state representation rules
(confirmed/supported/contradicted/open), observation-vs-interpretation
discipline, association-is-not-causation, nine prohibitions
(no invented evidence/tools/verification, no status changes, no
upgrades, no hidden contradictions, no measurement-as-interpretation),
plus a minimal worked example. Wired into the ml system prompt and
the shared wrapup nudge. Prompt-efficiency guard kept (bound
2000→4000, documented).

## 6. Repair behavior

Eligibility gate (empty/provider-failure → direct fallback with a
recorded reason); one attempt, no loops/recursion/retries/tool calls;
repair prompt carries original output, exact errors, schema,
prohibitions, example, and authoritative facts with a
transform-don't-reinterpret instruction; raw repair output persisted
(truncated) in repair events; acceptance requires base validation AND
all consistency gates, else rejection with recorded failures and
deterministic fallback. Single-attempt and no-extra-spend pinned by
tests through the real `run_meta_turn` with a mocked provider.

## 7. Evidence-preservation guarantees

`causal/report_consistency.py`: authoritative snapshot (hypotheses,
actions+results corpus, verification/resolution events, budget) and
ten checks — unknown refs, vocabulary/`confirmed` exclusion,
terminal-state immobility, confirmation-language vs contract,
verification-claim vs probe record, decimal/percentage claims vs
recorded measurements, no silent hypothesis drops, contradicting-action
traceability, count/budget figure accuracy, uncertainty preservation.
Repairs must pass all; native-valid reports are recorded-not-rejected
(audit decision). Assembly read-only proven by state fingerprint
around build/finalize/adapt.

## 8. Deterministic fallback improvements

`fallback.py` v2: all 16 required sections from records only —
identification, executive summary, main/confirmed/supported-but-
unconfirmed/rejected/unresolved findings, per-finding evidence with
action ids and relations, contradicting evidence (session-backed, so
unresolved hypotheses keep their refs), independent verification,
adversarial outcome, tool summary with counts, token/financial usage
(recorded figures or explicit "not recorded"), limitations, final
resolution, generation statement. All M8 keys byte-identical;
missing information is stated, never invented; plain specific
language, no AI filler.

## 9. Report provenance

Every eval report: `report_generation_status` + `report_provenance`
(status, output class, repair attempt/via, consistency pass/failures/
warnings, `assembly_mutated_state`, schema version, timestamp,
fallback reason). Diagnosis API adds the `repairs` trail and
`generation_status`. Dashboard shows an output-class column, a
one-line generation badge, and a repair-attempt line — findings stay
visually primary.

## 10. Dashboard/API changes

Additive only: `api.py` causal view gains `repairs` +
`generation_status`; `CausalPanel.tsx` gains one column and two muted
lines; `api.ts` scorer-critical types untouched; `tsc` clean, Vite
build succeeds, TestClient smoke passes.

## 11. Test results

608/608 full suite (53 new M20: 10 classification, 16 repair, 12
integrity, 10 fallback, 5 regression). M19 35/35 intact. M9/M10/API
77/77, grades unchanged. Six development failures fixed at cause
(validation doc §3); one full-suite sqlite-handle flake fixed by
session cleanup in M20 tests; no test weakened, no suppressions.

## 12. M19 regression confirmation

M19 docs and `live_runs/m19-music-01` never written by M20 work;
M9/M10 scores unchanged (77/77 green); scorer/M10/fixture/sealed
code untouched; separation and credential scans clean; eval-report
scorer keys (`executive_summary`, `confirmed_findings`,
`rejected_hypotheses`, `inconclusive`, `experiments`, `verification`,
`limitations`, `structured_summary_valid`) unchanged in shape.

## 13. Remaining limitations

Number-claim detection is decimal/percentage-scoped; contradiction
preservation is traceability-scoped, not NLU; native-valid
consistency findings are recorded, not enforced; the contract costs
~440 tokens per ml round; live-model compliance unverified (offline
mandate); single fixture family, mocked provider. No M21 started;
no live test launched.

## 14. Capability ledger

| Capability | Status |
|---|---|
| 7-way summary classification + recorded eligibility | new, tested |
| Compact reporting contract (schema, vocabulary, rules, prohibitions, example) | new, live-dormant until authorized run |
| Bounded repair (eligibility, 1 attempt, persisted output, consistency-gated acceptance) | new, tested |
| Evidence-preserving assembly (10 checks, read-only proof) | new, tested |
| Full-section deterministic fallback | improved, tested |
| Per-report provenance (native/repaired/fallback) | new, tested |
| Dashboard/API provenance surfacing | new, smoke-tested |
| M19/M9/M10/Demand-Zone preservation | confirmed |
| Live investigation / spend / new campaigns | none (per mandate) |
