# M16 Phase 0 — Live Discovery Bottleneck Audit (Main Report)

Status: investigation only. No code modified, no APIs called, no
investigations launched. Claim labels: **[F]** verified fact (artifact /
code line cited), **[O]** historical observation, **[H]** root-cause
hypothesis, **[Q]** unresolved question.

## 1. Baseline (re-verified from artifacts)

- Offline evidence-required discovery: M9 mean 0.938 **[F]**
  (`integrated_m9_m12_validation.md`), M10 mean 0.906 **[F]**
  (challenge-report table recomputed [1,1,0.25,1,1,1,1,1]).
- Live strict discovery: **0 confirmed in 6 runs M6–M14** **[F]**
  (all `confirmed_findings` empty; scorecards discovery 0.0); M5 0.4
  under an older partial-credit rule **[F]** — a scorer change, not a
  capability drop.
- Live reasoning: **0.6 in all 7 scorecards, byte-identical** **[F]**.
- Team vs single +0.085 on n=1 scenario each (and identical values on two
  different scenarios) **[F]** — a lead, not a result.
- Reliability genuinely improved: tests 260→459, budget compliance
  restored post-M7, reproducibility 1.0 ×7, zero live false positives **[F]**.

## 2. Bottleneck verdicts A–I

### A. Detection failure — REJECTED as root cause (confidence: high)
Every live run detected the suspicious pattern **[F]**: drift direction
(M5/M9int), bias scale (M6), regional gap prose (M7), district ratio 6.2
(M8), pooled numbers (M13), exact cold-start naming (M14 H1). Detection
works. Symptom status: none — detection is a demonstrated strength.

### B. Hypothesis failure — contributing cause, not root (confidence: medium)
Hypotheses are model-worded, broad, and overlapping **[O]**: 20 live
hypotheses across 7 runs; M13 ran with only 2. The offline loop seeds
segment-grounded hypotheses (`autonomous.py` segment seed); the live loop
has no equivalent — hypotheses come only from the model **[F]**
(`engine.py::propose_hypothesis`, origin 'meta'). But M14 shows good
hypotheses still fail (H1 named truth, then contradicted by the metric),
so hypothesis quality alone cannot be the root cause.

### C. Experiment-selection failure — ROOT CAUSE #1 (confidence: high)
Three compounding facts **[F]**: (1) ~half of every 6-experiment budget is
`propose_hypothesis` bookkeeping — real diagnostics per live run average
**3.0** (M5:2, M6:3, M7:5*, M8:3, M9int:3, M13:3, M14:2, *includes breach);
(2) the model picks tools from schemas with only an advisory brief
(`loop.py::run_meta_turn`); `invention.propose`'s discriminating ranking
has **no live caller** (verified: zero imports in loop/driver); (3) the
discriminating probe was never the one run: per-region AUC (M7/M13),
residual-feature correlation (M6), slice-P@K (M14) all existed or were
buildable but were never selected live. Supporting: M8 (the one run with
a localizing probe, `group_column=district`) produced the program's best
evidence (ratio 6.2). Contradicting: none — no live run lacks a missing
discriminating probe.

### D. Evidence-attribution failure — ROOT CAUSE #2 (confidence: high)
`linker.py::_family()` is substring matching **[F]** (`selection.py:52`,
`linker.py:21-50`); attribution mud is artifact-proven twice **[F]**: M8
supports-on-denying-H3; M9int identical supports on all three hypotheses
including two deniers, promoting all to `supported` with empty
`confirmed_findings`. The M9 `denies_family` fix exists
(`attribution.py:101`) but the M14 music contradiction (pooled AUC
contradicting true H1, supporting false H3) shows the deeper defect:
attribution has no *metric-adequacy* concept — a pooled number can
contradict a slice truth without triggering any alarm.

### E. Causal-reasoning failure — ROOT CAUSE #3 (confidence: high)
The signature recurs in 5/7 runs **[O]**: direction found, mechanism
unpinned (M5 day-500 break, M6 device_age, M7 region-W, M13 region,
M14 slice mechanism). `confounders.py` proposes discriminating contrasts
(segment-concentrated vs uniform) but only the offline path consumes them
**[F]**. Schema-vs-district confounding (M8) was correctly *preserved* as
uncertainty — the one causal success, achieved by restraint (corroboration
bar) rather than identification.

### F. Hypothesis-update failure — ROOT CAUSE #4 (confidence: medium-high)
Statuses frozen-`proposed` in M5/M6/M13 **[F]**; the update path exists
(`link_evidence` + corroboration bar) but the live loop rarely invokes
status motion and the model-facing summary channel is broken (invalid/
absent in 4/7 runs). M9int is the mirror failure: statuses moved *wrongly*
(all-supported). So the updater is both under-fired and mis-firable —
a missing closed loop, not a missing rule.

### G. Multi-agent failure — ROOT CAUSE #5 (confidence: high for absence, medium for impact)
Skeptic/judge/challenge kinds: **zero events in all 7 live runs** **[F]**.
`m11/team.py::investigate` runs post-hoc on autonomous investigations;
no live caller exists **[F]**. The +0.085 team lead is offline-only (n=1).
Whether live wiring would help is **[H]**, but the M14 case is exactly the
shape a skeptic exists for (true H1 contradicted by an inadequate metric)
and none was present. Impact magnitude is unmeasured — claimed as
structural gap, not quantified benefit.

### H. Resolution failure — symptom, not root (confidence: medium)
`resolve.py` (13 classes, 6 statuses) has no live caller **[F]**; live
runs end via round/budget exhaustion with fallback prose. But resolution
only packages what the pipeline produced — with 3 thin diagnostics and
muddy attribution there is nothing to resolve *to*. Fix C/D first; H is
downstream packaging.

### I. Reporting/scoring failure — real but secondary (confidence: high)
Invalid/absent summaries in 4/7 runs **[F]**; fallback preserved honesty
(no fabrication — a genuine success). The M4-family live scorecard cannot
score the M8-style correct-restraint above 0.62 (discovery 0.0 by
construction when `confirmed_findings` is empty) **[F]**. So reporting
loses information (summaries) and scoring undervalues restraint — both
real, neither explains 0/6 discoveries.

## 3. Ranked top 5 bottlenecks
1. **C — Experiment selection/execution**: model-picked tools, advisory-only briefs, ~3 real diagnostics/run, discriminating probes never selected. (Root cause.)
2. **D — Attribution**: substring families, no metric-adequacy check, proven wrong promotions. (Root cause.)
3. **E — Mechanism pinning**: direction without isolation, 5/7 runs; confounder contrasts offline-only. (Root cause.)
4. **F — Update loop**: frozen or mis-firing status motion; broken summary channel. (Root cause, loop-closure.)
5. **G — Multi-agent absent live**: zero live skeptic/judge events; team gains offline-only. (Structural gap; impact unmeasured.)

## 4. Experiment-selection audit (summary; detail in PIPELINE_MAP §C)
- `info_value` is a **heuristic proxy** (distinguishes_n count + cost +
  prose power_limits/mislead_risk — `invention.py:98-135`), explicitly "no
  numeric information-gain fabricated" (`selection.py:76-80`) **[F]**.
  Of the 8 discrimination questions: cost ✓, redundancy ✓ (exact-args
  dedup), evidence quality (partial — indecision bands, no quality gate),
  EIG ✗, falsifiability (partial — interpretation rules exist offline,
  unused live), subgroup effects (partial — grouped specs exist, never
  chosen live), confounding ✗ live, subgroup-P@K ✗ live.
- Slice-aware diagnostics exist (`ml_tools.py::ranking_slice_diagnostics`,
  `grouped classification_metrics`) but have **no live-path trigger**:
  zero matches for slice/P@K in `loop.py`/`driver.py`/`planning.py` **[F]**.
  The M15 slice-gap screen (`diaglab.py`) is admitted offline; no live
  caller.

## 5. Multi-agent audit (summary)
- Implemented (offline): role contracts, ledger, designer +1 probe,
  mandatory skeptic with blocking challenges, judge verdicts, preserved
  dissent (`team.py:42-120+`, `roles.py`) **[F]**.
- Demonstrated: division of labor, dissent preservation, ≤1 extra call
  overhead **[O]** (collab docs). Not demonstrated: discovery superiority
  (parity on ward_gap), independent reasoning (heuristic screens).
- Live: entirely absent **[F]**. Open **[Q]**: can a budgeted skeptic-lite
  (one reserved probe + dissent record) fit the 6-experiment cap without
  starving diagnostics? M16 must answer with ledger math, not prose.

## 6. Evaluation-methodology audit (summary)
- Live scorecard rewards restraint (evidence 1.0 / calibration 1.0 for
  honest inconclusives) but caps it at ~0.63 and scores correct restraint
  (M8) identically to thin probing (M13) **[F]** — the rubric cannot see
  the difference between "measured the concentration and held back" and
  "measured almost nothing." **[H]**: this compresses the exact signal
  M16 needs (is the system getting closer?).
- The four scientific levels (detect → hypothesize → support → confirm)
  are conflated in one discovery number **[O]**; M8 scores 0.0 discovery
  with ratio-6.2 evidence linked. M16 should score *localization* (right
  granularity measured) separately from *confirmation*.
- Offline grader is sound (moving-evidence rule, key-tool requirement)
  but offline≠live drivers, so offline gains do not transfer by
  construction **[F]** (M15 baseline §failure-analysis).

## 7. Executive summary
1. **Genuinely good at**: honest detection (7/7), restraint under
   uncertainty (0 live false positives), durability/reproducibility
   (1.0 ×7, byte-identical reruns), budget discipline, offline
   evidence-required discovery (0.906–0.938 with controls).
2. **Biggest scientific weakness**: turning detected suspicion into
   isolated, confirmed mechanism — 0/6 strict live discoveries with
   reasoning frozen at 0.6.
3. **Why live discovery struggles**: the live loop is model-driven tool
   selection with advisory briefs (~3 real diagnostics/run), substring
   attribution with no metric-adequacy check, no status-closing loop, no
   skeptic, and no slice-aware probes — while all the machinery that
   fixes these (invention ranking, team review, resolve, replication)
   has no live caller.
4. **M16 first**: reserve 1 experiment for a *discriminating* probe chosen
   by `invention.propose` (not the model) + wire slice-aware/P@K ranking
   diagnostics into the live tool path (see ROADMAP P0).
5. **Success looks like**: same-scenario repeats (eval_music, eval_credit)
   showing per-region/slice localization measured live, statuses moving on
   evidence, and at least one confirmed finding surviving the independent
   second probe — with CIs from n≥5, not a single anecdote.
