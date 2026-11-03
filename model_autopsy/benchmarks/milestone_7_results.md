# Milestone 7 — Live results (`live-1e19b2cdedfe`)

## Evaluation information

- Project: **eval_credit** (Default risk review; subgroup-AUC failure
  with a leakage distractor; never used in M5/M6 live runs).
- Model / configuration: `muse-spark-1.3`, Meta Responses endpoint,
  secure `.env` loader, temperature 0.2 and prompts unchanged from the
  validated offline gate.
- Run ID: `live-1e19b2cdedfe`, status `completed`, error `None`.
- Investigation rounds: 3/3. Request attempts: 6/12.
- Provider-reported tokens (manifest ledger, authoritative): 32,511 in
  (7,650 cached), 6,160 out, **38,671**/50,000 total.
- Actual expenditure: **$0.058404 / $0.40**.
- **Limit breach (disclosed): experiment executions 8/6.** The
  governor's 6-experiment cap was recorded but never enforced
  pre-execution (the driver only checked rounds; the turn only honored
  the engine's 12-tool budget). Five diagnostics + three hypothesis
  records executed. All other caps respected. Root cause fixed after
  the run (`experiments_left` now caps in-turn executions; driver and
  resume pass the remaining allowance; new test
  `test_experiments_left_caps_executions` proves it offline). The
  breach does not alter the preserved evidence, but the run is
  non-compliant on this one dimension and is reported as such — no
  score is hidden behind it.

## Research scores (independent M4 definitions, post-freeze truth)

- Discovery **0.0** — nothing entered `confirmed_findings`; the
  planted conditional-subgroup mechanism (region W near-random) was not
  named with supporting numbers. The one `classification_metrics` run
  used pooled columns only (AUC 0.97, no per-group gap), so the
  scorer's `min_group_gap 0.10` need was unmet.
- Evidence **1.0** (scorer rule for an honest inconclusive with no
  confirmed claims — a scoring convention, not a quality claim),
  reasoning **0.6**, calibration **1.0**, efficiency **0.4**
  (8 experiments at/over cap), reproducibility **1.0**.
- Overall M4: **0.61**, verdict **`inconclusive`**.
- M6 dims recomputed on this run: experiment_selection 0.4 (one
  discriminating diagnostic, redundant coverage), causal_diagnosis 0.5
  (honestly inconclusive), report_validity **0.0** — the structured
  summary was INVALID in all 3 turns (6 repairs, none won). The M5
  failure mode recurred and is not concealed.
- No false positive: the leakage distractor was never confirmed.

## Hypothesis lifecycle analysis

- Generated: 3 (regional-AUC gap; regional miscalibration;
  base-rate/data-quality artifact).
- Entered investigation: 2 — `data_quality_profile` (clean: 0
  duplicates, no null signal) auto-linked as contradicting H1 and H3
  via the live loop linker (event `linker`, seq 36; revisions
  proposed→investigating with justification and cited action id).
  **This is the first live run in which statuses moved for recorded
  evidence reasons.**
- Supported: 0. Rejected: 0. Inconclusive/proposed remainder: H2
  (miscalibration) untouched — no calibration-by-region evidence ran.
- Confidence: only the two contradicted hypotheses revised (15);
  no invented values elsewhere.

## Adaptive investigation analysis

- The next experiment changed with evidence: after the failed
  `classification_metrics` call (wrong args), the loop retried with
  corrected args rather than abandoning the question; after clean
  quality evidence, follow-ups moved to calibration/shift probes.
- Selection policy influence: PARTIAL. Briefs were injected every turn
  (6 `selection` events) and adherence recorded — but turn 1 briefed
  "top=none" (empty roster; fixed post-run with starter briefs) and the
  subgroup family was missing from the ranker, so two "deviated"
  verdicts blame the brief, not the model — the model correctly chose
  `classification_metrics` for a regional-AUC question the brief
  scored "low". Fixed post-run (subgroup family + coverage mapping;
  proven by `test_subgroup_family_ranking`).
- Redundant experiments: none repeated with identical args (dedup
  held); one failed call retried once with corrected args (legitimate).
- Stopping: no early stop fired (open hypotheses + budget remained);
  the run ended on round exhaustion with an honest inconclusive report.
  No `stopping` event — correct, since stop conditions were not met.

## Scientific outcome

- Discovered: pooled AUC 0.97 with stark regional gap named in prose;
  data-quality artifact ruled out with evidence; calibration status
  unresolved.
- No causal explanation established; uncertainty preserved. The exact
  subgroup mechanism (region W) was not isolated — per-region AUC was
  never computed, the precise analogue of the M5/M6 misses (direction
  found, mechanism unpinned, honestly inconclusive).

## Comparison (no generalization claimed)

- M5 turbine 0.55 partial / M6 claim 0.62 inconclusive / M7 credit 0.61
  inconclusive: different projects, families, and verdict semantics —
  not ranked against each other. The comparable deltas are
  architectural and behavioral: statuses now move live (0→2
  evidence-driven transitions), selection briefs exist and are audited
  (with disclosed quality defects, now fixed offline), the experiment
  cap is now enforced (after a disclosed breach), and summary validity
  regressed to invalid — the next fix.
