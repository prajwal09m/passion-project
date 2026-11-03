# M17 Phase 0 — Architecture Audit (read-only; no behavior changed)

Scope: trace the live execution path and document exactly why each M16
failure occurred, then state the intended fix. All line references are
to the current working tree. No M9/M10 artifacts touched.

## Live path (the only path that spends money)

`backend/live/cli.py::main` → `driver.run_live_investigation`
(up to 3 outer iterations) → `meta_api/loop.run_meta_turn`
(`max_rounds=2` provider rounds per turn) → `engine.build_report` →
`finalize` → `live/adapter.meta_report_to_eval` → `eval/scorer.score`.
`live/recorder.finalize_run` persists the run dir.

Per-turn order inside `run_meta_turn` (`backend/meta_api/loop.py`):
selection brief → **reservation checkpoint** (once per investigation)
→ provider rounds (tool dispatch w/ per-execution budget reserve) →
linker auto-link → **skeptic review** → grounded summary →
summary validation/repair → usage rollup. The driver then folds
tokens/rounds into the shared `Budget` (`record_turn(..., fold_work=False)`).

## Gap 1 — Reservation fires before hypotheses exist (P0-1 unreachable)

- `loop.py` (~L380-400): the once-per-investigation reservation
  checkpoint runs at turn start, before round 1. The `if not _already`
  guard keys on existing `reservation`-kind events, so after the first
  decline it never retries.
- `reserve.select` requires ≥2 open (`proposed`/`investigating`)
  hypotheses; at turn start there are 0 (the model proposes all 3 via
  tool in round 1). Result in all 10 M16 runs: declined,
  "fewer than 2 open hypotheses".
- Offline unit tests pre-seed hypotheses, so they never reproduce this.
- Intended fix (Phase 1): move the checkpoint to end-of-turn (after the
  round loop, before skeptic-lite) in `run_meta_turn`, keeping the
  exactly-once guard. Reservation then sees round-1 hypotheses, selects
  via `invention.propose/validate`, reserves + executes + links through
  the shared `Budget`, and its result is visible to the skeptic reuse
  path. Decline reasons preserved when unsuitable. Regression test:
  hypotheses proposed in a simulated round 1 → reservation fires after.

## Gap 2 — No live caller for verification/replication/resolution

- `m10/replication.replicate` (different-tool second probe, refuses
  same-tool reruns, links + records `replication` event),
  `research/verification.review_claim` + `record_review` (adversarial
  checklist), and `research/resolve.diagnose/contract` (13 classes,
  6 statuses) all exist and are tested offline. **Zero callers in the
  live path**: grep over `backend/live/*` + `backend/meta_api/*` finds
  no reference to any of them; `adapter.meta_report_to_eval` hardcodes
  `"verification": []`; `engine.build_report` `confirmed` sections only
  fill from `record_finding("confirmed")`, which the live loop never
  calls (only `api.py` + tests do). Strict discovery is therefore
  structurally 0 regardless of evidence quality.
- Additional gap inside `replication.SECOND_PROBE`: families are
  subgroup/leakage/calibration/misspecification/drift — **no ranking
  family**. For eval_music both canned subgroup probes misfire on the
  fixture (verified offline on the artifact, no spend): per-slice AUC
  is uniform (est 0.9743 vs new 0.9818, spread 0.0075 < 0.03 rule band),
  so `classification_metrics` split-by-slice would *contradict* the true
  finding; `residual_feature_dependence` has no numeric input column to
  track (columns are query/slice/relevance/score). Reusing either as the
  "independent" probe would manufacture a false contradiction.
- Intended fix (Phase 2): new `backend/live/verify.py::maybe_verify`,
  called once from the driver after the turn loop, before reporting.
  Eligibility: hypothesis with ≥1 moving support, zero contradicts,
  status investigating/supported (the second probe *completes*
  corroboration; it does not require it upfront). The probe runs
  through the existing `replicate()` machinery (different-tool rule,
  own action id + provenance, result linked, contradictions preserved).
  Success (second moving support, still no contradiction) →
  `record_finding("confirmed")` + `resolve.contract` attached as a
  recorded resolution event; failure/insufficiency → unresolved with
  recorded reason, never confirmation. Budget refused → recorded skip.
  For the ranking family, extend `SECOND_PROBE` with a new
  permutation-significance diagnostic (descriptive gap vs inferential
  gap-is-real test; different method, different code path, shared data
  disclosed) because no existing tool tests the music finding without
  misfiring. Scorer stays frozen: its music band (`gap` ≥ 0.20 under
  `ranking_diagnostics`) is not met by the measured 0.1695 — disclosed
  in the final report, never gamed.

## Gap 3 — Skeptic-lite cannot act on this scenario (advisory-only)

- `m11/roles.skeptic` blocks only `unsupported-support` (supported
  status with <2 moving supports). On eval_music nothing reaches
  `supported` with <2 supports before review, and the granularity
  challenges (`live/skeptic._granularity_challenges`) only block when
  segment/slice measurement is *absent* — but the model always runs the
  slice probe first. Hence 0 blocking in 10/10 M16 runs; the probe
  branch (present in `skeptic.review`) never triggers.
- `skeptic.review` also never *gates* anything: hypothesis statuses
  move via linker regardless of open challenges; there is no
  investigator-response obligation.
- Intended fix (Phase 3): blocking challenges gate advancement — a
  hypothesis with an unanswered blocking challenge cannot move to
  `supported` until the investigator (model turn or deterministic
  responder) answers with cited recorded evidence or explicitly logs
  unresolved dissent; a blocking challenge may request one budgeted
  experiment via the shared `Budget` (dedup reuse releases the hold;
  6-experiment/12-attempt caps unchanged). Skeptic disagreement is
  never auto-recorded as evidence against a hypothesis. Tests: one
  actionable blocking + one advisory non-blocking case.

## Gap 4 — Attribution fallthrough creates denier-supports

- Root line: `attribution.classify`, `if same_mechanism(primary,
  rule_family) or (names_seg and not denial)` → returns the rule's
  direction as moving. `names_seg` is true whenever the hypothesis
  names a measured segment token; `denies()` (4-token negation window
  before the segment word) misses euphemistic uniformity
  ("any slice differences are sampling noise / reflect base rates"),
  and `denies_family` only knows the literal word "subgroup".
  Reproduced offline: "no slice underperforms" → contradicts (correct);
  "differences are sampling noise" → supports (wrong; moved 3 M16
  uniformity rivals to `supported`).
- Intended fix (Phase 4): effect-denial recognition — uniformity /
  noise / base-rate-explanation phrasing scoped to the measured segment
  or rule family triggers denial symmetry (evidence FOR the denied
  effect contradicts); genuine subgroup-worse claims keep moving
  support; base-rate-rival claims (competing mechanism, untested by gap
  evidence) and insufficient-evidence claims go non-moving
  (`relevant_to`/`uncertain`), never auto-support, never auto-contradict.
  Regression cases for all five required wordings through the real
  `classify` + `update_with_evidence` path; full suite must stay green
  (M9/M14 shapes rely on adjacent bands).

## Gap 5 — Token cap is a gate, not a ceiling

- `governor.Budget.check` refuses when `total_tokens() >= cap`, but
  `run_meta_turn` never calls `check()` before provider requests — it
  only `reserve("attempts", 1)`. Tokens fold after the fact via
  `record_turn`. A dispatched long round therefore overshoots (M16 B2
  53,622 / B5 55,113 vs 50,000 nominal). Cost is unaffected ($0.069
  max vs $0.40) but the nominal token ceiling is not enforced.
- Intended fix (Phase 5): conservative headroom — before each provider
  dispatch, refuse when `total + est_input + EST_OUTPUT` would breach
  the cap (EST_OUTPUT fixed conservative constant); driver turn-boundary
  check keeps the same headroom; refusals stop honestly with a recorded
  budget-limited state. Nominal 50k / $0.40 / 12-attempt / 6-experiment
  caps unchanged; no silent redefinition (overshoot still disclosed if
  it ever occurs).

## Gap 6 — End-to-end workflow (Phase 6 checklist vs today)

1 Inspect ✓ (recon) · 2 Detect ✓ (gap measured 10/10) · 3 Competing
hypotheses ✓ (model proposes 3) · 4 Reserve ✗ (Gap 1) · 5 Execute ✓ ·
6 Measure subgroups ✓ · 7 Link ✗-partial (Gap 4 wordings) · 8 Status
motion ✓ (27/30) · 9 Skeptic challenge ✓-advisory only (Gap 3) ·
10 Respond ✗ (no obligation path) · 11 Verify ✗ (Gap 2) ·
12 Resolve ✗ (contract never built live) · 13 Report ✓ (deterministic,
limitations stated) · 14 Preserve ✓ (run dirs + sqlite).
Phases 1–5 close 4, 7(partial), 9, 10, 11, 12; 12 via a driver-level
`resolve.diagnose` + `contract` step recorded as a `resolution` event
(informational; report verdict stays scorer-driven; unresolved is never
relabeled).

## What is explicitly NOT changing

Scorer (`eval/scorer.py`) and M10/M9 evaluators frozen; historical
`benchmarks/` artifacts byte-identical; sealed ground truth never
enters loop/scenarios/runner; Demand Zone AI untouched; no new model
families; no dashboard redesign. The only new measurement code is the
single permutation-significance diagnostic required by Gap 2 (no
existing tool tests the music finding without misfiring — verified
above), routed entirely through existing `replicate`/`linker`/
`record_finding`/`resolve` machinery.
