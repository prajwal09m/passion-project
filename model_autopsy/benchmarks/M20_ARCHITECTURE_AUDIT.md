# M20 Architecture Audit — Reporting Pipeline Forensics

Offline-only. No live calls were made for this audit; all evidence is
reconstructed from recorded artifacts in `live_runs/m19-music-01/`
(`events_dump.json`, `assistant_messages.jsonl`, `manifest.json`,
`scorecard.json`) and the current source.

## 1. Reporting pipeline: exact source files and functions

```
model turn (meta_api/loop.py::run_meta_turn)
  │ final assistant text (text_out)
  ▼
engine.validate_structured_summary (engine.py:304)
  │ regex: fenced ```investigation_summary block, else bare {"conclusion"} JSON
  │ then causal/report_schema.validate (m8-v1: schema+types+refs+overconfidence)
  │ then causal/report_validation.validate (refs/status/confidence/contradiction)
  │ records event kind="summary" (valid bool, errors, raw block ≤600 chars)
  ▼  invalid?
meta_api/loop.py::_attempt_summary_repair (loop.py:257) — exactly ONE attempt
  │ fresh full-context request, no tools, no previous_response_id chain
  │ records event kind="summary_repair"; fallback on MetaUnavailable/budget refusal
  ▼  still invalid?
causal/fallback.compose (fallback.py) — records-only deterministic fallback
  │ explicitly labeled kind="deterministic-fallback", provenance string
  ▼
driver.py / resume.py: engine.build_report → engine.finalize
  │ then live/adapter.meta_report_to_eval → eval_report for scorer.py
  ▼
api.py exposure: inv.final_report verbatim; /api/.../diagnosis trail
(frontend Workspace.tsx shows only "deterministic from recorded evidence")
```

Generation instructions (the entire contract the model ever sees):

- System prompt, loop.py:67-70 — one clause: end with a fenced block
  labeled `investigation_summary`, compact JSON
  `{conclusion, status_recommendations[{hypothesis_id,status,basis}],
  uncertainties[], recommended_next}`.
- Wrapup nudge, loop.py:176-186 — "end with your investigation_summary block".
- Repair rules, loop.py:274-293 — re-emit ONLY the block; conclusion
  non-empty; statuses from vocabulary; ids from allowed list; basis cites
  recorded action ids; uncertainties list; recommended_next string.

## 2. M19 failure reconstruction (m19-music-01)

1. What the model returned. Final-turn text (verbatim, assistant_messages
   seq 17): "Testing whether top results stay relevant across catalog
   slices — measuring precision per slice." No fenced block, no JSON.
2. Why it was rejected. `validate_structured_summary` found zero
   candidates → `no structured summary found in the final message`.
3. Block status. Missing entirely — not malformed, not incomplete.
   M20 class: `prose_without_block`. (Earlier turn text was a similar
   one-line status note, never a report.)
4. Repair request constructed. Error list + rules + recorded state
   (roster, grounded facts, ledger, budget). Correct shape, one attempt.
5. Why repair failed. The repair response ALSO contained no structured
   block — second `summary_repair` event: `valid:false`,
   `continuation:original`, same single error. Model-side non-compliance
   twice in a row, not a transport/parse edge case.
6. Cause split. Model behavior (ignored the block instruction twice) ×
   prompt ambiguity (format taught in one subordinate clause; `basis`
   field name in the contract vs `basis_action_ids` accepted by the
   validator; no required/optional distinction; no status vocabulary in
   the generation contract; no example) × missing enforcement (no
   classification, no consistency gates at assembly, repair output text
   not persisted for audit).
7. Deterministic fallback generated. `fallback.py::compose` →
   `kind:deterministic-fallback`, `fallback_version:m8-fallback-v1`,
   conclusion from recorded hypotheses, uncertainties from open items,
   evidence ids, original errors, provenance string. `fallback_used:true`,
   `fallback_composed:true` in the usage rollup.
8. Evidence preserved. Roster, ledger, grounded summary, skeptic reviews,
   verification, resolution contract, budget ledger all recorded;
   nothing was rewritten by the model path.
9. Could the fallback omit important information? Yes — see §5.
10. Could a repaired model summary introduce unsupported claims? Yes —
    see §6. Nothing in the assembly path re-checks claims against
    authoritative state after `validate` passes.
11. Consumer distinguishability. Partial: `executive_summary` silently
    prefers model conclusion; `structured_summary_valid` bool +
    `fallback_used` bool exist in eval_report, but there is no output
    class, no repair validation record, no consistency result, and the
    human dashboard shows only "deterministic from recorded evidence".

## 3. Existing validation rules

- M6 (`report_validation.py`): conclusion required non-empty string;
  recs must be objects with known hypothesis ids (exact or unique
  prefix), statuses from the 6-value vocabulary, `basis_action_ids`
  citing known action/experiment ids; confidence 0–100; no contradictory
  supported+rejected for one hypothesis; supported recs must cite
  evidence; warnings for missing recs/uncertainties.
- M8 (`report_schema.py`, m8-v1): known schema_version; conclusion
  ≤2000 chars; lists ≤50 items; confidence 100 rejected; supported rec
  needs `basis` or `basis_action_ids`.
- Parsing: fenced block regex, else bare-`conclusion`-JSON regex.
  Multiple candidates: first parseable object wins.

## 4. Existing fallback behavior

Records-only, Honest, Minimal. Keeps conclusion/uncertainties/
recommended_next/evidence ids/errors/provenance. Gaps: no per-finding
sections, no confirmed/supported/rejected/unresolved split, no
verification/adversarial/budget sections, no limitations beyond the
open-hypothesis list; adapter only surfaces the fallback conclusion
when `executive_summary` is empty.

## 5. Data-flow diagram

```
recorded state (hypotheses/actions/ledger/resolution/budget) ─┬─► validate
                                                              │    (refs)
model text ─► parse ─► schema/semantic checks ─► valid? ──yes─┴─► eval_report
  │ invalid                                          (conclusion trusted verbatim)
  ▼ repair (1×, same checks on output)
  │ still invalid → fallback (records-only, minimal sections)
  ▼
assembly (NO re-validation of claims vs authoritative state)
```

## 6. Root causes

R1. Generation contract is one subordinate clause + one nudge line: no
    schema table, no field requirements, no status vocabulary, no
    example, field-name mismatch (`basis` vs `basis_action_ids`).
R2. No output classification: every failure is one generic error.
R3. Repair is a bare re-request: no example, no field contract, and its
    raw output is not persisted (only valid/errors/usage) — the M19
    repair text is unrecoverable from events.
R4. Assembly trusts a `valid` summary verbatim: no evidence-ref,
    measurement, verification-claim, budget, or resolution re-checks
    against authoritative state.
R5. Fallback is minimal and its use is under-surfaced to humans.
R6. Provenance is two booleans; dashboard/API consumers cannot tell
    native / repaired / fallback apart at a glance.

## 7. Minimal proposed changes (M20 phases)

- P1: `causal/summary_class.py` — 7-way classifier, recorded in the
  `summary` event payload, raw text preserved (existing payload).
- P2: compact schema-contract block (required/optional table, statuses,
  prohibitions, one minimal example) appended to the final-message
  clause and wrapup nudge; token-cheap, no new round trips.
- P3: repair eligibility per class (no repair for provider_failure /
  empty_output), repair prompt carries example + prohibitions, repair
  output persisted (truncated) in the repair event, one-attempt limit
  kept, repaired output must pass P4 gates.
- P4: `causal/report_consistency.py` — read-only checks (refs exist,
  measurements match ledger, statuses match authoritative state,
  verification claims have probe records, contradictions preserved,
  budget figures match, resolution conclusions match contract);
  enforced on repaired summaries and recorded for every final report.
- P5: fallback extended to the full section shape from records only,
  explicit "not recorded" markers, plain language.
- P6: `report_generation_status` (model_native/model_repaired/
  deterministic_fallback) + class/repair/consistency/schema/timestamp
  in eval_report and the diagnosis trail; one-line dashboard badge.
- P7: classification × repair × integrity × fallback × regression
  matrix, mocked provider only.

## 8. Risks of changing report generation

- Prompt edits could alter live model behavior (token cost, compliance
  rate). Mitigation: additive clauses only, no new round trips,
  offline tests with fixtures; live behavior unchanged until a future
  authorized live run.
- Stricter gates could reject currently-accepted summaries.
  Mitigation: regression fixtures from M19 artifacts; gates apply to
  repair acceptance first, assembly records (not rejects) native-valid
  reports during M20.
- Fallback shape change could break consumers. Mitigation: additive
  keys only; scorer-critical keys byte-identical.
- No evidence/resolution/budget logic is touched; assembly stays
  read-only (mutation audit in P8).
