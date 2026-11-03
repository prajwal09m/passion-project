# M21 Evaluation Protocol — Reporting Reliability & Scientific Integrity

Offline-first. No paid provider calls are authorized by this document.
Every definition below is testable with deterministic fixtures and a
mocked provider; the live campaign (if approved) reuses the same
checklist against recorded artifacts.

## 1. Authority ordering

1. Recorded investigation state (hypotheses, ran actions + results,
   evidence refs, verification/resolution events, budget ledger).
2. The M19 transition-based resolution contract (`research.resolve`
   statuses: confirmed / strongly-supported / falsified /
   verified-null / partially-resolved / unresolved).
3. Deterministic assembly (`build_report`, `fallback.compose`,
   `adapter.meta_report_to_eval`, `report_consistency` gates).
4. Model prose (native or repaired) — explanation only, never evidence.

A lower authority may never override a higher one.

## 2. Definitions

### 2.1 Successful native structured summary

ALL of the following hold:

- `validate_structured_summary` returns `valid:true`
  (fenced `investigation_summary` block or bare-`conclusion` JSON;
  M8 schema + M6 semantic checks pass).
- `summary_class` is `valid_structured`.
- No repair was attempted (`summary_repair` events: none for this turn).
- Provenance `report_generation_status` is `model_native`.
- The consistency advisory for the native summary is recorded
  alongside it (M21: `consistency_passed/failures/warnings` on the
  summary result and event; informational — see §4).

### 2.2 Eligible repair case

`summary_class` is one of `prose_without_block`, `malformed_block`,
`schema_invalid`, `semantically_invalid` (M20 eligibility boundary,
`summary_class.repair_eligible_for`). `empty_output` and
`provider_failure` are NEVER eligible: retrying the model cannot fix
them, so the turn goes straight to deterministic fallback with a
recorded reason.

### 2.3 Successful repair

ALL of the following hold:

- Exactly one repair request was sent (fresh full-context, no tools,
  no `previous_response_id` chain), raw repair output persisted
  (truncated) in the repair event.
- The repaired text re-passes `validate_structured_summary`.
- The repaired summary passes ALL `report_consistency`
  gates (`check_repaired_summary`).
- Provenance marks `repaired_via: summary_repair`; the original
  invalid verdict and response id are preserved when the repair is
  rejected.

### 2.4 Expected deterministic fallback

Fallback is expected when: the output class is ineligible; the single
repair attempt raises `MetaUnavailable`/budget refusal; the repair
returns invalid output; or the repair is valid but fails any
consistency gate. The fallback must be `kind:deterministic-fallback`,
records-only, with explicit "not recorded" markers (never invented
content), the original errors preserved, and a `fallback` event.

### 2.5 Report consistency evaluation

`report_consistency.check(summary, snapshot)` over the authoritative
snapshot (`build_snapshot`: hypotheses, ran-action corpus, verification
/ resolution events, budget). Ten guarantees: known hypothesis refs;
recommendable vocabulary (no `confirmed` prose); terminal-state
immobility; confirmation-language only under a `confirmed` contract;
verification claims only with a confirmed probe record; decimals /
percentages present in the recorded corpus; no silent hypothesis drops;
contradicting-action traceability; count/budget figure accuracy;
uncertainty preservation for open hypotheses.

### 2.6 Evidence-provenance check

For every claim class, the cited artifact must exist: hypothesis ids in
this investigation; basis/evidence action ids with `ran` status;
verification claims backed by a `verification` event with
`confirmed:true`; resolution language matching the recorded contract
status. Provenance chain per report: `model_native` /
`model_repaired` / `deterministic_fallback`, each visually distinct in
API (`report_generation_status`, `report_provenance`,
`report_validation`) and dashboard.

### 2.7 Resolution-status check

The final report's resolution language is checked against the actual
recorded events: `resolve.collect_transitions` (real from→to advances)
and the `resolution` event contract. Only a `confirmed` contract
authorizes confirmation language; `strongly-supported` /
`partially-resolved` / `unresolved` must never read as confirmed.

### 2.8 Uncertainty preservation

Open hypotheses (`proposed` / `investigating` / `inconclusive`) must
appear either as recommendations or as carried uncertainties, with the
missing measurement named. Contradictory evidence must be cited or
explicitly acknowledged — never dropped. An honest `unresolved` /
`inconclusive` outranks an unsupported positive conclusion.

### 2.9 Token / retry / failure accounting

Every provider interaction reserves budget BEFORE dispatch and settles
after (`attempts`, `experiments`, token headroom, financial cap).
Required records: `meta_request`/`meta_response` events with usage;
`meta_usage` turn rollup (`rounds`, `api_calls`, `api_attempts`,
`tokens`, `fallback_used`, `summary_repair_attempts`); repair
`response_id`/usage; budget-refusal events with `attempt_spent:false`
for pre-dispatch refusals. Retries are bounded: one fallback per turn,
one repair per turn, no recursion.

### 2.10 False confirmation / unsupported science

Any of the following is a FAIL, regardless of report polish: confirmed
language without a `confirmed` contract; independent-verification
claims without a confirmed probe record; evidence refs to unknown or
non-ran actions; dropped relevant hypotheses; unresolved→confirmed
rewrites; proposed mechanisms stated as established causes; numeric
claims absent from the recorded corpus; hidden contradictions;
proposed-only experiments described as executed; provider failures
described as successful investigation.

## 3. Scenario matrix

Deterministic fixtures cover every row before any paid activity.
`H` = harness test in `tests/test_m21_reporting.py` (mocked provider).

| # | Scenario | Expected behavior | Covered by |
|---|---|---|---|
| S1 | Valid native summary | Preserve verbatim; class `valid_structured`; status `model_native`; consistency advisory recorded | H-native |
| S2 | Prose without structured block | Eligible; one bounded repair; fallback + provenance if repair fails | M20 + H-prose |
| S3 | Malformed structured block | Eligible; repair; reject invalid repair output, keep original | M20 + H-malformed |
| S4 | Schema-invalid summary | Eligible; repair; acceptance requires base validation | M20 + H-schema |
| S5 | Semantically invalid summary | Eligible; repair; acceptance requires consistency gates | M20 + H-semantic |
| S6 | Empty provider output | Ineligible → direct fallback, recorded reason | M20 + H-empty |
| S7 | Provider failure | Ineligible → direct fallback; `MetaUnavailable` recorded; no spend on repair | M20 + H-provider |
| S8 | Repair succeeds | Persist repaired output + raw text + usage; provenance `model_repaired` | M20 + H-repair-ok |
| S9 | Repair fails | Preserve original verdict; deterministic fallback; provenance `deterministic_fallback` | M20 + H-repair-fail |
| S10 | Unsupported confirmation | Never silently confirm; consistency failure recorded (native) / repair rejected | H-confirm |
| S11 | Missing verification evidence | Unresolved preserved; verification claim fails the gate | H-verify |
| S12 | Contradictory evidence | Contradiction preserved and traceable; never hidden | H-contradiction |
| S13 | Incorrect numeric claims | Unsupported decimals rejected (repair) / flagged (native advisory) | H-numbers |

Live re-validation (proposal only, §7 of the milestone) exercises S1
against the real provider; S2–S13 stay fixture-driven unless the live
run organically produces the class — organic occurrences are recorded
and checked, never induced.

## 4. Native-valid consistency: record, do not reject (frozen M20 contract)

M20 deliberately enforces consistency gates on repair acceptance while
recording (not rejecting) consistency findings for native-valid
summaries. M21 preserves this contract and closes its observability
gap instead: the advisory is now computed read-only at validation time
and surfaced in the API causal view and dashboard (additive keys
only). Rationale: at summary-validation time the resolution contract
may not exist yet (verification runs after the turn), so a
validation-time gate could falsely reject; the adapter-time check over
final state remains authoritative. Enforcement changes require a
separate milestone and explicit authorization — they are NOT part of
M21.

## 5. Objective live success criteria (for the proposal)

A live run is a PASS only if: provenance is unambiguous in recorded
artifacts; the final report's claims all trace to ran actions / events;
no §2.10 failure appears; budgets respected with honest stop otherwise.
It is INCONCLUSIVE if: provider returns valid summary but
verification budget is refused (finding preserved unresolved — honest,
not a failure); or transport failures force fallback without any model
content to evaluate. It is a FAIL if: any §2.10 violation reaches the
final report; evidence is silently discarded; or provenance is
ambiguous.

## 6. Non-goals

No new report sections, no scorer/threshold changes, no sealed-truth
access changes, no Demand Zone AI changes, no enforcement tightening,
no M22 work.
