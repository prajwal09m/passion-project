# M16 Phase 2 — Controlled Live Evaluation Protocol (Preparation Only)

No API calls were made in this phase. No investigations launched. This
document prepares (not executes) the measurement of Phase 1. Authority
to spend anything live must come explicitly afterwards.

## 1. Phase 1 integration audit (verified pre-registration)

Exercised offline (16→17 tests green; full suite 475→476 pending final
run §7). Findings:

- **Reservation enforced pre-dispatch** (`live/reserve.py::run_reserved`
  → `Budget.reserve` before `INV.execute`; `BudgetExceeded` declines).
  Single-test fix applied in Phase 2 prep: skeptic now iterates **all**
  blocking challenges (previously only the first; the rest vanished
  silently) and **releases** (not settles) the budget token when the
  engine dedups to a prior result — verified by the no-duplicate-spend
  test. No other working-code changes; corroboration, caps, and scoring
  untouched (`causal/hypotheses.py`, `m10/`, `benchmarks/` diff-clean).
- **Slice-aware availability**: `ranking_slice_diagnostics` +
  `segment_quality_screen` in `selection.py` costs/map and `planning.py`
  candidates; reservation's `invention.propose` already emits grouped /
  slice specs when segments exist (M7/M14 replay tests).
- **Column mapping**: `artifact_facts().column_mapping` records
  label/score/segment columns + high/medium/low confidence +
  `mapping_notes` (ambiguity → clarify; missing label → explicit
  limitation). Loader stays strict for explicit `labels=` requests.
- **Attribution adequacy**: pooled-vs-segment and AUC-vs-top-K rules
  return non-moving `relevant_to` (M14 replay: zero moving links from
  pooled AUC to the slice hypothesis; M8-denier contradiction
  preserved; one over-broad trigger narrowed after the m8-linker
  regression caught it — cause fix, re-verified).
- **Update closure**: linker records no-bearing notes; statuses move
  only via `update_with_evidence` (2-independent-tool rule intact);
  `grounded_summary()` is a pure record function; repair prompt carries
  `grounded_facts` + do-not-invent rule; fallback path untouched.
- **Skeptic-lite**: challenges + probes/dissent recorded as `skeptic`
  events; dissent preserved on no-budget/no-spec/refusal; reuse spends
  nothing (engine dedup + budget release).
- **Dashboard**: `/api/investigations/{id}/m16` returns recorded events
  verbatim; the Workspace card renders titles/details/justifications
  only, with empty states pre-turn. Nothing reconstructed.
- **Remaining gaps** (do not block; recorded): reservation fires on the
  first turn only; ranking-claim vocabulary deliberately narrow; judge
  stays offline; no live evidence yet by design.

## 2. Scenario configurations

### eval_music (cold-start slice collapse; baseline: M14 live-ecdd47fafd9d,
inconclusive 0.63, H1-named-but-contradicted, 6/6 exps, 7/12 attempts,
30,170 tokens, $0.037252)
- Artifact: `model_autopsy/tests/fixture_eval/investigator/music_rank.csv`
  (columns: query, slice, relevance, score).
- Initial hypotheses (model-generated as usual; expected shape): a
  slice-specific ranking failure, a sparsity/hygiene artifact, a
  globally-uninformative ranker. Provenance: `propose_hypothesis` tool.
- Reserved experiment: top `invention.propose` discriminating spec
  (expected: `ranking_slice_diagnostics`, slice P@K gap); rationale =
  spec `distinguishes` + `decision_relevance`, recorded in the
  `reservation` event — or a recorded decline with reasons.
- Slice availability check: `artifact_facts().segments` must contain
  `slice`; `column_mapping.label=relevance (medium)`,
  `score=score (high)`.
- Measurement granularity: per-slice P@K + n per slice; pooled P@K kept
  for comparison; thin slices (n<30) inconclusive by construction.
- Expected attribution: pooled/grouped-AUC rules → `relevant_to` (not
  contradicts) against slice/top-K claims; slice-gap ≥0.15 supports the
  slice mechanism; verification via independent second probe.

### eval_credit (regional discrimination gap; baselines: M7
live-1e19b2cdedfe inconclusive 0.61 with disclosed 8/6 breach; M13
live-d8b174527ca5 inconclusive 0.63, pooled-only probing, 6/6 exps,
10/12 attempts, 44,181 tokens, $0.057286)
- Artifact: `model_autopsy/tests/fixture_eval/investigator/`
  `credit_default.csv` (region, label, score + covariates).
- Initial hypotheses (expected shape): regional-AUC gap, regional
  miscalibration, base-rate/quality artifact.
- Reserved experiment: top discriminating spec (expected grouped
  `classification_metrics` with `split_by=region` or slice screen).
- Measurement granularity: per-region AUC + n per region; pooled AUC
  for comparison; no region claim may be contradicted by pooled-only
  evidence (adequacy gate).
- Attribution/transition expectations: `data_quality_profile` clean →
  contradicts quality rival (as in M7); status motion recorded with
  cited action ids or explicit no-motion notes.

## 3. Outcome categories (kept separate; confirmation bar unchanged)

- **Detection**: suspicious behavior identified (any moving or
  non-moving evidence referencing the anomaly).
- **Localization**: affected segment/subgroup measured at adequate
  granularity with moving evidence (e.g. slice P@K gap, per-region AUC
  spread) — reported separately from discovery.
- **Mechanism**: causal explanation supported by appropriate-granularity
  evidence (still short of confirmation).
- **Confirmed discovery**: corroboration requirements met (≥2
  independent moving supports, no contradiction) **including the
  independent second probe** (`m10/replication.py` rule: different tool).
- **Correctly inconclusive**: insufficient evidence, no overclaim
  (fallback/report states the bound).
- **False positive**: confirmed an unsupported/incorrect finding
  (must be 0; any FP invalidates the run's discovery claim).

## 4. Comparison arms (isolate contributions; report confounds)

Same scenario, same budgets (3 rounds / 6 exps / 12 attempts / 50k
tokens / $0.40), same frozen rubric + new localization dimension:
- **Arm A (status quo ante)**: reservation + skeptic disabled via flags
  (code path: skip `run_reserved` and `sk.review`; briefs/advisory
  unchanged). Measures the M13/M14-shape baseline.
- **Arm B (reservation only)**: skeptic disabled. Isolates P0-1 + P0-2.
- **Arm C (full Phase 1)**: reservation + skeptic-lite. Measures the
  complete package; B-vs-C isolates skeptic-lite.
- Arm differences are exactly these flags; everything else identical.
  If a component cannot be isolated (e.g. slice tools help only when
  the reservation picks them), report the interaction, not causality.
- Minimum: arms B+C × 5 runs on eval_music (10 runs). Preferred: arms
  A+B+C × 5 on eval_music + arms B+C × 5 on eval_credit (25 runs).
  Per-run cost history ($0.031–0.058) bounds the campaign at ~$0.3–1.5.

## 5. Statistical reporting (template)

Per run: scenario, arm, initial hypotheses (provenance), reserved spec +
rationale/decline, model-selected tools, slice availability/execution,
per-slice n + granularity, evidence links + adequacy decisions
(counts of supports/contradicts/relevant_to/insufficient),
status transitions + no-motion notes, skeptic challenges/probes/dissent,
resolution + unresolved questions, exps/attempts/tokens/cost/duration.
Per scenario + aggregate: localization rate, strict discovery rate,
FP and correct-null rates, status-movement rate, attribution-error
count (denier-supports; must be 0), replication outcomes, mean/median
tokens + cost. Wilson 95% CIs on all rates. Paired descriptives vs the
frozen M13/M14 baselines. **No significance claims below the
preregistered bar** (Fisher exact on 5-vs-0 splits only, or nothing).

## 6. Safeguards and reproducibility

Caps enforced pre-dispatch (Budget reserve/settle/release; M7-breach
rule: any cap breach invalidates that run's comparability, disclosed
not hidden). Corroboration unchanged. Sealed truth never enters
`scenarios`/`runner`/loop (boundary audit pre-launch). M9/M10 scores
and artifacts frozen (re-run gates pre/post campaign). Reproduction:
`backend/live/cli.py` + `preflight` + run-dirs with manifests/usage/
actions/hypotheses/events (same recorders as M5–M14); protocol version
pinned to this document's git hash at authorization time.
