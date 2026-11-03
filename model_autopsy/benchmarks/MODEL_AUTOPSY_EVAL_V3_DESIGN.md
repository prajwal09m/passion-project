# MODEL_AUTOPSY EVAL V3 — DESIGN (Stage 2)

**Rubric version:** `v3` · **v2 status:** frozen (`backend/eval/scorer.py` untouched;
all thresholds, weights, verdicts byte-identical). Every v3 scorecard carries
`"rubric_version": "v3"`; every v2 scorecard carries/keeps `"v2"` (backfilled
at read time, never rewritten).

## 1. Why v3 (forensic basis)

M22 (`m22-live-01`): correct cold-start hypothesis generated, `supported`
(5 refs), investigation honestly `partially-resolved` (no verification) →
v2 discovery 0.0 via two stacked gates: (a) discovery reads only
`confirmed_findings` titles; (b) `min_gap 0.20` unreachable (fixture always
0.1695, p=0.0005). Counterfactual proof: inserting the correct title into
`confirmed` still scores 0.2; M19 hit exactly that ceiling. v3 separates four
achievements v2 conflates: discover / evidence / verify / confirm.

## 2. Scorer v3 (`backend/eval/scorer_v3.py`, NEW)

`score_v3(pid, report, truth, hypotheses=None) -> dict` — pure function, no DB,
no network. `hypotheses` defaults to the report's embedded hypothesis lists
(confirmed/likely/supported/investigating/proposed/rejected + v2 fallback
`evidence_for_each_finding` with `finding_state`). Works on archived reports;
anything absent → dimension `None` ("unavailable"), never silent 0.

### 2.1 Discovery (did the investigator identify the mechanism?)

- Candidate set: ALL non-duplicate hypotheses (dedupe by normalized text;
  duplicates noted in `notes`, single credit).
- Match (deterministic, explainable): content-token overlap
  `|H∩T|/|T| ≥ 0.25` (tokens: lowercase, len>3, stopword-filtered) AND ≥1
  family word (reuse v2 `fam_words` per family).
- Status credit for best match per truth mechanism: confirmed/likely 1.0;
  supported 0.7; investigating/proposed 0.4; only-rejected/absent 0.0.
  Multiple truth mechanisms → mean. Confirmed distractor (v2 markers) → −0.3,
  floor 0. No LLM judgment anywhere.
- M22 expectation: supported correct match → **0.7** (was 0.0).

### 2.2 Evidence (relevant, connected, traceable?)

From experiments + evidence refs (moving = supports/contradicts from a `ran`
action — same rule as `has_useful_evidence`): (a) 0.4 any moving ref;
(b) 0.3 both support AND contradict present (discrimination); (c) 0.3 ×
(linked ran diagnostics ÷ ran diagnostics). Repeats (identical result digest)
noted, not double-counted. M22 expectation: 0.4+0.3+0.3 = **1.0**.

### 2.3 Verification (independently tested?)

From report `verification` entries + `verification_plan`/`non_verification`
events embedded by adapter: executed + linked + recorded result → 1.0
(outcome affects confirmation, not this score); executed but errored → 0.4;
planned but unexecuted (reason recorded) → 0.2; nothing → 0.0.
M22 expectation: **0.0** (no probe executed; refusal recorded, not a plan).

### 2.4 Confirmation/calibration (conclusion justified?)

Authority = resolution contract states in report. Correct confirmation 1.0;
honest partial/inconclusive WITH discovery>0 → 0.7; honest inconclusive
without discovery → 0.4; unsupported confirmation (confirmed + contradicts, or
confirmed + numbers fail v3 gate) → 0.0; false confirmation on null → 0.0.
M22 expectation: **0.7** (honest partial, discovery 0.7).

### 2.5 Efficiency / reproducibility

v2 concepts preserved. Cost from actual recorded usage
(`token_financial_usage`/`budget`); **missing usage → `None` + flag**,
excluded from aggregate (weights renormalize; >1 core dim missing → overall
`None` + `insufficient_data`). No silent zero-cost.

### 2.6 Overall

`overall = Σ w·dim` over available dims (renormalized), weights
(`rubric_v3.py`): discovery .30 / evidence .20 / verification .15 /
confirmation .20 / efficiency .05 / reproducibility .10. Rationale: finding +
justifying (0.50) outweigh process (0.35); verification (0.15) outweighs
efficiency (0.05) — accuracy over speed. Raw components always published;
`overall: None` when truth missing or data insufficient. Sensitivity analysis
(±0.10 weight shifts) in validation report must show M22's qualitative reading
(found-but-unverified) is stable.

## 3. Benchmark calibration (`rubric_v3.py`, versioned rubric)

- 0.20 origin: `m4_scoring_methodology.md` band table, no rationale recorded —
  round-number band; M17/M18/M19 docs already flagged the 0.1695 conflict.
- Fixture ground truth (new-item relevance 0.10 vs est 0.50) is a LARGE
  practical effect; permutation p=0.0005. Fixture is CORRECT; threshold wrong.
- v3 threshold: **`min_gap = 0.15`** for slice family. Defensible method:
  (1) pre-existing test-suite meaningfulness floor — `test_m15_resolution.py`
  and `test_m16_phase1.py` assert `max_slice_gap >= 0.15` as the tool's pass
  bar on this fixture class (predates this task; NOT fitted to 0.1695);
  (2) clears the deterministic effect (0.1695) with ~12% margin;
  (3) far above noise (p=0.0005 at observation); (4) null fixtures have no
  slice structure → gap absent → gate requires presence, no FP inflation.
- Statistical vs practical significance kept distinct: v3 gate =
  `gap ≥ 0.15 AND (p_value < 0.05 if a significance number is attached)`.
- v2 fixture + truth + 0.20 UNCHANGED. Differences documented here; no v3
  fixture needed (nothing wrong with the data).

## 4. Metric normalization (`backend/eval/normalize.py`, NEW)

Canonical key: **`gap`** (float). Priority: explicit `gap` > `max_slice_gap`
alias > absent. Rules: gap-only → keep; alias-only → `gap` + note
`alias_from=max_slice_gap`; both equal (|Δ|≤1e-9) → `gap`; both conflict →
explicit `gap` wins + `gap_conflict: true` flag, originals preserved;
neither → absent (never 0); invalid (non-numeric/NaN/bool/negative) → dropped
+ `gap_invalid: true`. API: `normalize_numbers(tool, numbers) ->
(numbers, flags)`; scorer v3 reads canonical `gap` exactly once (no
double-count). Adapter (`live/adapter.py::_numbers_only`, additive) applies it
at the boundary; v2 scorer reads raw archives unchanged.

## 5. Verification workflow (`backend/live/verification.py`, NEW)

Existing `live/verify.py::maybe_verify` (eligibility/independence/budget/
contract) is KEPT and delegated to — no rewrite. New wrapper layer:
- `plan_verification(session, inv, hypothesis_id)`: records
  `verification_plan` event {claim, probe tool (family SECOND_PROBE minus
  already-ran tools), expected pro/con observations, budget check}. No
  blind force: unsuitable claim → plan records "no suitable probe" instead.
- Dispatch via existing `maybe_verify`; skip paths mapped to structured
  `non_verification` events with reason codes: `no_suitable_tool |
  insufficient_data | budget_exhausted | unsafe_or_inappropriate |
  info_unavailable | experiment_failed | stopped_before_verification`.
- `verification_status(session, inv)`: {planned, executed, unexecuted[]}
  for adapter/v3 (proposed ≠ executed always distinguishable).
- Bounds: ≤1 probe/hypothesis/phase, existing budgets/timeouts/retries/stops
  unchanged; `partially-resolved`/`inconclusive` remain legal outputs.
- Driver: one-line switch `maybe_verify` → `run_verification_phase`
  (same args + artifact); adapter fills report `verification` list from
  `verification_status` (v2 archives keep `[]` → v3 shows unavailable, honest).

## 6. Reporting + dashboard

- Backend: v3 scorecards render wherever v2 does (same shape + dimensions,
  `rubric_version`, `notes`, `unavailable[]`). Historical v2 reports render
  unchanged; v2 dims never shown as v3.
- `Eval.tsx` (+ generic dimension renderer already exists): add rubric-version
  label, verification detail (executed vs proposed-but-unexecuted), and a
  "why not confirmed" explainer when discovery>0 and confirmation<1.0.
  Existing visual language only.

## 7. Backward compatibility & test plan

v2 byte-identical (regression test pins v2 outputs on archived reports);
v3 additive files only; adapter change covered by old+new assertions;
full suite + tsc + build + scans in Stage 7; v2-vs-v3 comparison table from
computed values with unavailable labeled (Stage 7).
