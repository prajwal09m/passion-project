# M21 Architecture Audit — Reporting Lifecycle End to End

Offline-only. No live calls for this audit. Sources: M20 docs, current
source, M19 `live_runs/m19-music-01` artifacts (read-only).

## 1. Lifecycle trace (exact path)

```
run_meta_turn (meta_api/loop.py)
 │ final assistant text (text_out, meta_response event, verbatim payload)
 ▼
engine.validate_structured_summary (engine.py:304)
 │ regex: fenced block, else bare {"conclusion"} JSON
 │ → causal/report_schema.validate (m8-v1) → causal/report_validation
 │ records kind="summary" (valid/errors/output_class/repair_eligible/raw)
 │ M21: + read-only consistency advisory (consistency_passed/failures/
 │   warnings) on valid results and on the summary event payload
 ▼ invalid?
summary_class.repair_eligible_for (loop.py, one block per turn max)
 │ eligible (S2–S5) → _attempt_summary_repair: fresh full-context prompt,
 │   no tools, no chain; budget reserve + headroom recheck; raw repair
 │   text persisted (truncated) in kind="summary_repair" events
 │ ineligible (S6–S7) → direct fallback, recorded reason
 ▼ repair returned?
check_repaired_summary (report_consistency: base-valid AND all 10 gates)
 │ pass → repaired_via="summary_repair", text_out replaced
 │ fail  → original verdict stands, fallback.compose (records-only)
 ▼
driver/resume: build_report → finalize → live/adapter.meta_report_to_eval
 │ adapter recomputes snapshot over FINAL state (post-verification),
 │   records consistency in report_provenance; executive_summary =
 │   model conclusion verbatim (native/repaired) or fallback conclusion
 ▼
api.py causal view (/causal) + CausalPanel.tsx; eval scorer consumes
eval_report (scorer-critical keys byte-identical since M8)
```

## 2. Per-stage contracts

| Stage | Input contract | Output contract | Failure condition |
|---|---|---|---|
| Generation | system `_SUMMARY_CONTRACT` + wrapup nudge | one fenced JSON block | model ignores format (M19: prose, twice) |
| Parse | final text | first parseable object wins | no candidate / bad JSON → S2/S3 |
| Schema/semantic | parsed obj + hyp/action id sets | valid bool + normalized | S4/S5 classes |
| Classification | text + validation result + provider error | 1 of 7 classes + eligibility | never fails (pure function) |
| Repair | errors + roster + ledger + budget | valid+consistent, or rejection | transport / budget / bad output / gate fail |
| Consistency | summary + authoritative snapshot | passed/failures/warnings | any of 10 guarantees violated |
| Fallback | final_report + errors + session + usage | 16-section records-only report | session unreadable → degrades to report dicts |
| Assembly (adapter) | final + message + summary + fallback | eval_report + provenance | none (pure assembly; fingerprint-proven read-only) |
| Exposure | events + final_report | causal view / dashboard / run manifest | advisory invisible (fixed M21, §4) |

## 3. M20 limitation under investigation

**Question:** native-valid summaries are recorded-not-rejected on
consistency findings, while repairs must pass all gates. Can a final
report mislead?

**Answer: yes, in a bounded way, and M20 disclosed it.** A
native-valid summary can pass schema/semantic validation while
violating an authoritative guarantee the validator does not check —
e.g. claiming independent verification with no probe record, citing a
decimal absent from the corpus, or using confirmation language while
the contract is `unresolved`. The adapter records this in
`report_provenance.consistency_failures`, but NOTHING rejected the
report, and the human dashboard never showed it (CausalPanel rendered
consistency only for repairs). `executive_summary` carries the model's
conclusion verbatim into the scored report.

**Why not enforce (reject) native-valid on consistency failure?**
Two reasons, both structural: (a) at summary-validation time the
resolution contract often does not exist yet — verification
(`maybe_verify`) runs in the driver AFTER the turn — so a hard gate
there could falsely reject confirmation language that later-state
checks would contextualize; the adapter-time snapshot over final state
is the authoritative one. (b) Changing accept→reject alters the frozen
M20 contract silently; enforcement is a policy decision for a later
milestone with its own authorization.

**Smallest safe correction (M21, implemented + tested):** make the
native advisory VISIBLE instead of invisible. `validate_structured_
summary` computes the read-only check at validation time and attaches
`consistency_passed/failures/warnings` to the result and the summary
event (additive, validity unchanged); the causal API exposes them per
summary; the dashboard renders one muted line for native summaries
with findings. No accept/reject change, no scorer-key change, no
enforcement change. Residual risk (a human ignoring the line) is
documented in the final report as a known limitation with enforcement
deferred.

## 4. Silent-discard analysis

Walked every handoff for evidence loss:

- Model text → event payload: verbatim (`meta_response`), never
  overwritten by repair (repair text goes to `summary_repair` events).
- Invalid summary → repair prompt: errors + original class carried;
  original verdict kept on rejection.
- Repair → acceptance: valid-but-inconsistent repairs rejected WITH
  failures recorded; fallback composed from records.
- Assembly: `state_fingerprint` before/after proves hypotheses,
  actions, counts, findings untouched (M20 pin + M21 regression).
- Fallback: unresolved/contradictions carried from session rows when
  available; "not recorded" markers where not — absence stated, never
  filled.
- Budget refusals: pre-dispatch refusals reserve nothing
  (`attempt_spent:false`); post-dispatch settles conservatively.

**No silent discard found.** The one visibility gap (§3) is fixed by
surfacing, not by new enforcement.

## 5. Provenance boundaries (must stay distinguishable)

- `model_native`: summary valid, no `repaired_via`, no fallback.
- `model_repaired`: `repaired_via: summary_repair` + repair events
  (valid → accepted; rejected → fallback instead).
- `deterministic_fallback`: `fallback` event + `fallback_used:true` +
  `kind:deterministic-fallback`.

API `generation_status`, adapter `report_generation_status` +
`report_provenance`, and the dashboard badge each derive from the same
rule (fallback > repaired > native > none_yet). M21 adds the native
consistency advisory to the same surfaces. Tests pin all three
statuses end to end through `run_meta_turn` with a mocked provider.

## 6. What was NOT changed

M19 artifacts/results/frozen data; benchmark scorers/thresholds;
sealed truth and investigator access boundaries; Demand Zone AI;
existing tests (none weakened); unrelated subsystems; dependencies
(none added). One production-behavior note: validation now performs
read-only snapshot queries (no writes, no model calls); validity
outcomes are unchanged by construction (advisory keys only).
