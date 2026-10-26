# Evidence-Grounded Experiment Proposal Layer — Phase 1 Design

**Status:** DESIGN ONLY — nothing in this document has been implemented. No code, config,
ledger, or supervisor state was changed to produce it.

**Date:** 2026-10-04. **Requested by:** project owner. **Author:** Buffy (Codebuff agent).

**Frozen reference (read-only):** `autonomous_agent/MAIN AUDITS AND REFLECTIONS/AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md`
(Campaign 1 audit; 47,940 bytes; SHA-256 `47904cb1ba0f7b58f63a3c19a3853c10d8dcf7f673e060039ac9d076cdfab3e0`).
*Note: this file was found at that path (it was moved there after the audit was written; the
Phase-1 prompt referenced the older `autonomous_agent/` root path). It is treated as immutable
evidence and was only read.*

**Hard constraints honored in this phase:**
no supervisor run; no experiments; no autonomy flag change; no modification of historical
records, the frozen audit, the holdout, or any existing gate; no weakening or bypassing of any
safety, leakage, validation, promotion, provenance, or isolation mechanism.

**Question → section index**

| Q | Section | Q | Section |
|---|---|---|---|
| 1 | A | 11 | C (§ holdout blindness) |
| 2 | A | 12 | E |
| 3 | A | 13 | F (§ duplicate control) |
| 4 | B | 14 | F (§ rediscovery control) |
| 5 | C (§ grounding) | 15 | F |
| 6 | C (§ mutation control) | 16 | D |
| 7 | C (§ surface) | 17 | K |
| 8 | C (§ pre-execution validation) | 18 | B (§ determinism) |
| 9 | E (§ rejection recording) | 19 | H |
| 10 | E (§ state machine) | 20 | I |

---

## A. CURRENT ARCHITECTURE LIMITATIONS

### A.1 What exactly is hard-coded today (inventory)

Verified by reading the current sources (hashes in the Campaign 1 audit appendix; files
unchanged since campaign end):

| # | Hard-coded element | Location | Value / effect |
|---|---|---|---|
| 1 | Research question registry | `core.py` `ResearchPlanner.BASE_DIRECTIONS` | 8 fixed `Hypothesis` tuples (text, motivation, prereqs, priority 1.00→0.60). Nothing generates new questions. |
| 2 | Recipe library | `spec_recipes.py` `RECIPE_LIBRARY` | 3 fixed `Recipe` dataclasses: `feature_arm_nested_ablation`, `model_class_matched_comparison`, `calibration_stability_check` — direction, purpose, target files, parameter grid, required evidence, evaluation criteria, rejection conditions, `max_attempts` (3/3/2), timeout. |
| 3 | Parameter whitelists inside `validate_recipe` | `spec_recipes.py` | `estimator ∈ {LogisticRegression, LightGBM}`; `arm_pair ∈ {A→B, B→C, C→D}` (+ same-arm); `n_boot ∈ [100,2000] int`; `calibration_bins ∈ [3,20] int`. Values outside are refused before a spec exists. |
| 4 | Candidate code templates | `spec_recipes.py` `EXPERIMENT_ENTRYPOINT`, `INIT_CONTENT` | The *only* Python a candidate may contain is a fixed shim that calls `recipe_harness.run_from_config(CONFIG)`. Variation lives exclusively in `experiment_config.json`. |
| 5 | Research harness | `recipe_harness.py` | `ALLOWED_ARMS=("A","B","C","D")`, `ALLOWED_ESTIMATORS=(LR, LightGBM)`, `ALLOWED_FOLDS=(2023,2024,2025)`, `CONFIG_LIMITS` (n_boot, bins, margin bounds), `ALLOWED_CRITERION_KEYS` closed set, fixed metric (pooled OOF ROC-AUC), fixed CI method (moving-block bootstrap, 4-week blocks), feature sets pulled from frozen `study.FEATURE_ARMS`, `HARNESS_VERSION="1.0.0"`. |
| 6 | Planner scoring constants | `core.py` `ResearchPlanner.plan` | `priority + 0.18·success_rate + 0.08·exploration + stagnation_bonus(0.3) − readiness_penalty(10.0·…)`. |
| 7 | Allowed change surface | `experiment_adapter.py` | `ALLOWED_CHANGE_PREFIXES = ("autonomous_agent/experiments",)`; `_require_allowed_path` enforced on every spec file path; `COPY_IGNORE_PATTERNS`, `DEFAULT_RESOURCE_LIMITS`, command-role registry (`unit_tests`, `experiment`, `audit`, `development`), `EVALUATION_CONTRACT` result keys. |
| 8 | Spec identity & duplicate control | `hardening.py` | `spec_fingerprint` (excludes `experiment_id`/`provenance`), `SpecRegistry` append-only ledger, `scrubbed_environment`, `install_network_guard`, `run_with_limits`. |
| 9 | Capacity / exhaustion | `spec_recipes.py` `generation_capacity` + `core.py` `_autonomous_capacity` | Capacity = recipe coverage AND remaining attempts, both permanent; empty capacity ⇒ terminal `research_exhausted`. |
| 10 | Activation flag | `autonomy_config.json` `allow_autonomous_specs` | Single human-set boolean; currently `true` (Campaign 1 state, unchanged). Default false; missing/malformed ⇒ disabled. |
| 11 | Data surface | `recipe_harness.py` docstring + adapter | One input: `study_files/outputs/study_v1/development/event_table.csv` (SHA `232de7db…4d0`); holdout path structurally never opened. |
| 12 | Hypothesis→recipe binding | `spec_recipes.py` `_select_recipe` | First recipe whose `direction` matches; the other 5 directions get `UNSUPPORTED` refusal. |

### A.2 Which parts of experiment generation are still limited to the closed recipe library

Everything downstream of "which of the 8 static directions": direction must be library-covered
(3 of 8); parameters come only from the reviewed cartesian grid, picked by round-robin; the
evaluation protocol and margins come from the recipe; the code package is a fixed template;
the budget and repeat policy are recipe properties; `generation_capacity` treats uncovered
directions as permanently incapable. The provider *is* the only spec source
(`build_default_provider` → `RecipeSpecProvider`); no other generator exists in the codebase.

### A.3 What prevents a genuinely new …

| Target | Blockers (all structural, verified) |
|---|---|
| **Hypothesis** | Static `BASE_DIRECTIONS` registry; planner only selects, never composes; `UNSUPPORTED` refusal for uncovered directions; nothing writes new `Hypothesis` records. |
| **Feature transformation** | Harness reads precomputed arm columns from frozen `FEATURE_ARMS`; no transform language exists; candidate may only write the 3 fixed files; `allow_repeat=False` always; any new transform would require editing `recipe_harness.py` or the frozen study — both outside `ALLOWED_CHANGE_PREFIXES`. |
| **Model comparison** | `estimator` whitelisted to 2 values in *both* `validate_recipe` and `validate_experiment_config`; no hyperparameter surface (frozen study hyperparameters); no model registry hook. |
| **Robustness test** | CI method, block length, seeds policy (`min_seeds`, seed list), and bootstrap count ranges are fixed in `CONFIG_LIMITS`; no protocol slot for alternative robustness designs (e.g., purge sensitivity, regime splits, permutation controls). |
| **Calibration test** | Only `calibration_bins` (3–20) and the two calibration margins vary; no reliability-curve shapes, no alternative calibration metrics (Brier decomposition, ECE variants), no threshold analyses. |
| **Data/protocol analysis** | `folds` must equal exactly `[2023,2024,2025]`; input set fixed; no proposal may open new data sources (by design — this is also a safety property); protocol file read-only; holdout sealed. |

### A.4 The 20 design questions

Answered in sections B–K as indexed above; every question is answered in exactly one section
with an explicit heading.

---

## B. PROPOSED AUTONOMOUS PROPOSAL ARCHITECTURE

### B.1 Design principle

**A proposal is an inert, self-describing JSON record. Nothing the generator writes can
execute.** Execution remains reachable only through the existing, unchanged path: a validated
`ExperimentSpec` → `ExperimentAdapter.run_experiment` under every Campaign 1 gate. The new
layer adds a *stage before* spec creation, not an alternative to it.

### B.2 Q4 — New components required

| Component | Responsibility | Writes to | Must NOT touch |
|---|---|---|---|
| `EvidenceView` (new, read-only) | Assemble the serialized evidence document a generator may see: prior experiment outcomes, open questions, champion metrics, capacity, budget state — via a strict path allowlist (§C holdout blindness). | nothing (pure function) | any file |
| `DesignPrimitiveLibrary` (new, reviewed) | The closed vocabulary of design *primitives* a proposal may compose: transform ops, estimator plugs, robustness probes, calibration metrics, protocol analyses. Each primitive is implemented once in reviewed harness code with declared inputs/outputs/limits. | code (human-reviewed only) | — |
| `ProposalGenerator` (new) | Deterministic compositional generator: given `EvidenceView` + `DesignPrimitiveLibrary` + recorded seed → candidate `ExperimentProposal` JSON records with hypotheses, designs, parameters, evidence citations, falsification criteria. Optional constrained LLM annex (§G LLM assessment). | `state/proposal_ledger.jsonl` (append-only) | anything else |
| `ProposalValidator` (new) | Mechanical pre-execution validation: schema, evidence resolution, duplicate/near-dup, budget, criteria sanity (`CONFIG_LIMITS` bounds), surface check, holdout-string scan, **falsifiability check** (declared measurable rejection rule present). | validation verdict inside ledger row | experiment dirs |
| `BiasGovernor` (new) | Enforces portfolio policy: direction quotas, required share of falsification/null-class proposals, exclusion of any predicted-outcome field from selection scoring (§F). | policy verdict in ledger | — |
| `ProposalLedger` (new) | Append-only journal of every proposal + every state transition with reason codes and hashes; survives restarts; feeds `EvidenceView` back. | `state/proposal_ledger.jsonl` | — |
| `Proposal→Spec compiler` (thin, reuses existing code) | Only for proposals with `VALIDATED` + `APPROVED` status: render an `ExperimentSpec` exactly as `RecipeSpecProvider` does today (same entrypoint template, same `provenance` block plus `proposal_id`), then hand to the *unchanged* execution path (`spec.validate()`, `SpecRegistry`, adapter gates). | `spec_attempts.json`-equivalent via existing registry | — |
| State machine (in ledger) | Lifecycle statuses per Q10 (§E). | — | — |

**Q17 (separation)**: generator runs in the supervisor's *planning* phase — no subprocess, no
workspace, no network, no executor imports. The executor never imports the generator; shared
dependencies are schema/constants only. Physically: `autonomous_agent/proposal_layer/*` may
import `hardening`, `spec_recipes` (read-only helpers), never `experiment_adapter`'s run path.
Tests enforce the import direction (H.T14).

**Q18 (determinism/reproducibility)**:
- canonical JSON serialization (sorted keys) for proposal hashing; `proposal_fingerprint`
  excludes volatile fields (timestamps, ids) the same way `spec_fingerprint` does;
- explicit `seed` recorded in each proposal; generator is a pure function of
  `(EvidenceView bytes, seed, generator_version, primitive_library_version)` — property-tested
  for byte-identical output (H.T1);
- `generator_version` and `primitive_library_version` are pinned strings recorded per proposal;
- if the LLM annex is ever introduced: prompt template version, model id, temperature (must be
  0), full request/response bytes hashed into provenance; identical inputs must be re-playable
  from the stored response (the annex output is *data*, never an inline decision);
- no wall-clock or environment dependence in scoring (clock only stamps records, never ranks).

### B.3 What stays untouched

`experiment_adapter.py` gates, `recipe_harness.py`, `hardening.py` fingerprints/registry/
network guard, `VersionManager.promote`, `_validate_outcome`, budgets of the three existing
recipes, `autonomy_config.json`, and the supervisor loop contract. The recipe layer remains a
*permanent fallback*: if the proposal layer is absent or refuses, behavior is exactly Campaign
1 behavior.

---

## C. SAFETY MODEL

### C.1 Q5 — Evidence grounding (every proposal)

Every proposal carries `evidence_citations: [{artifact_path, sha256, what_it_shows}]`. Rules:
1. The generator never emits an uncited claim: schema requires ≥1 citation from the
   `EvidenceView` allowlist plus ≥1 *contradicting-or-contextual* citation (prior REJECTED
   results in the same direction are mandatory when they exist — the Campaign 1 pattern).
2. `ProposalValidator` **re-hashes every cited artifact** at validation time; a citation that
   does not resolve to the recorded hash ⇒ refusal `UNRECALLED_EVIDENCE` (fail-closed).
3. Grounding classes accepted: established baseline, prior experiment result, research-memory
   discovery, champion metrics, frozen protocol, dataset hash. All are already-persisted facts
   — no proposal may cite itself or another *pending* proposal as evidence.

### C.2 Q6 — Preventing arbitrary/random code mutation
1. **No free code in proposals.** A proposal is declarative: `design` = composition of
   `DesignPrimitiveLibrary` entries + parameters inside reviewed ranges. There is no field in
   which arbitrary Python can be expressed.
2. **Primitives are code-reviewed once**, implemented in the reviewed harness, versioned; a
   proposal can only *instantiate* them. Adding a primitive = human code change + tests + review
   — same trust boundary as editing `recipe_harness.py` today.
3. Candidate packages keep the Campaign 1 shape: fixed shim + `experiment_config.json`;
   `validate_experiment_config` extended (not loosened) to accept primitive-config keys, with
   unknown keys still refused outright.
4. Randomness only via recorded seeds; no `eval`/`exec`/dynamic import anywhere in the path
   (test H.T11 asserts absence).
5. **Explicit non-goal for Campaign 2:** generated Python source. If ever added, it requires a
   separate reviewed flag, static analysis gate, and human review — out of scope here.

### C.3 Q7 — Explicit allowed surface
- Proposal layer writes **only** `autonomous_agent/state/proposal_ledger.jsonl` (and a future
  `state/proposals/` scratch of identical records). Neither path is inside
  `ALLOWED_CHANGE_PREFIXES` and neither is reachable by candidates.
- Compiled specs reuse `files_allowed_to_change = (autonomous_agent/experiments/__init__.py,
  run_experiment.py, experiment_config.json)` — unchanged, enforced by `_require_allowed_path`.
- Surface checks are bidirectional: (a) validator refuses any proposal whose design implies a
  file outside the surface; (b) adapter's existing before/after original-tree fingerprint still
  catches any escape at execution time (defense in depth, already proven in Campaign 1).

### C.4 Q8 — Pre-execution validation (ordered gate chain)
`ProposalValidator.validate(proposal)` returns pass/refuse with reason codes; refusal is
permanent (§E). Gates, in order:
1. `SCHEMA` — strict schema, unknown fields refused.
2. `EVIDENCE_RESOLVED` — citations re-hashed (C.1).
3. `FALSIFIABILITY` — measurable rejection rule present, thresholds within `CONFIG_LIMITS`
   bounds; a proposal with no way to fail is refused (`NOT_FALSIFIABLE`).
4. `SURFACE` — design compiles to the allowed file set only (C.3).
5. `HOLDOUT_BLIND` — proposal text/design contains no holdout path or holdout-derived value
   (C.6); evidence view built without holdout handles.
6. `DUPLICATE` / `NEAR_DUPLICATE` — fingerprint checks (§F).
7. `BUDGET` — direction/primitive budget remaining (extends `generation_capacity`).
8. `BIAS_POLICY` — portfolio quotas still satisfiable after this proposal (§F).
9. `MECHANICAL` — full `ExperimentSpec.validate()` on the *compiled preview* (compile in
   dry-run mode; no side effects).
10. `APPROVAL` — Campaign 2: human sign-off recorded as a ledger field; deterministic
    confirmatory proposals may be auto-approved **only if** quotas already met (policy-defined,
    recorded).
Only after all gates: `VALIDATED → APPROVED → COMPILED_TO_SPEC`, and only then can the
existing executor see an `ExperimentSpec`.

### C.5 Q9 — Permanent recording of rejections
Every refusal writes a terminal ledger row: `{proposal_id, status: VALIDATION_REFUSED,
reason_code, gate, fingerprint, evidence_hashes, at}` — append-only, never rewritten, survives
restart, included in `EvidenceView` forever (so the generator cannot re-propose the same
refused design and cannot ignore that it was refused). `research_memory` gains a
`discarded_proposals` section (append-only) mirroring counts and reason codes. Refusal codes:
`SCHEMA`, `UNRECALLED_EVIDENCE`, `NOT_FALSIFIABLE`, `SURFACE_ESCAPE`, `HOLDOUT_REFERENCE`,
`DUPLICATE`, `NEAR_DUPLICATE`, `BUDGET_EXHAUSTED`, `BIAS_QUOTA`, `UNSUPPORTED_PRIMITIVE`,
`INVALID_PARENT`, `NOT_APPROVED`.

### C.6 Q11 — Holdout blindness of the generator
- `EvidenceView` is built by an **allowlist builder** (fail-closed): only
  `state/*.json(l)`, `CHAMPION.json`, `versions/*/version.json|evaluation.json`,
  `study_files/outputs/study_v1/development/event_table.csv` *metadata* (hash/rowcount only,
  not rows), protocol JSON, and the frozen audit — with an explicit denylist overlay for
  `study_files/outputs/study_v1/prospective/**` and any path containing `prospective|holdout`
  (excluding the policy record that says "sealed, uses=0", which *is* allowed as status).
- If any allowlisted source embeds a holdout path/value, the builder strips it and stamps
  `holdout_reference_stripped: true` on the view (visible in validation).
- The generator receives only the serialized view — no filesystem handle, no root `Path`, no
  network (it runs in-process with no I/O beyond reading the view it was handed).
- Independent re-check: validator scans final proposal bytes for holdout strings (`HOLDOUT_BLIND`).
- Execution-side holdout gate (`holdout_dir.exists()` check) remains untouched.

---

## D. SCIENTIFIC-VALIDITY MODEL

### D.1 The objective function is NOT "find improvements"

The system's stated objective becomes: **"generate and adjudicate evidence-bearing
experiments over open research questions, preserving all outcomes."** Improvement-finding is
an allowed *outcome*, never the selection criterion. Concretely:

- The generator's ranking/scheduling inputs are: unresolved-question coverage, novelty
  (fingerprint distance), evidence gaps, portfolio quotas — **structurally excluding any
  predicted/expected result field** (see F.2, code-enforced by input-schema banning).
- Expected outcome and falsification rule are **pre-registered in the proposal** but are used
  only for (a) falsifiability validation and (b) post-hoc calibration of predictions — never
  for selection or approval.
- The research record (ledger + research memory + audit trail) preserves **both** successful
  and unsuccessful attempts: refusals, executions that fail gates, executions that fail
  runtime, and accepted results are all permanent, all citable, all fed back into future
  `EvidenceView`s.

### D.2 Q16 — Preserving meaningful falsification opportunity
1. **Falsifiability is a validation gate** (C.4 gate 3): every proposal declares a measurable
   rejection rule (threshold + metric + scope) at proposal time; `NOT_FALSIFIABLE` proposals
   are refused and recorded.
2. **Proposal-class quotas** (F.3): a reserved share of every campaign's budget must be
   *falsification-class* — designs whose plausible outcome is failure of the current champion
   narrative, e.g.:
   - null/adversarial: "champion's advantage vanishes under stricter purge or alternate block length";
   - stability probes: "reported delta does not hold in ≥1 predeclared year/regime";
   - calibration attacks: "champion probabilities degrade beyond margins on the *other* arm";
   - protocol analyses: "ranking flips under alternative predeclared fold boundaries".
3. **The gates themselves are the falsifier of last resort and stay untouched**: negative
   deltas, CI floors, and calibration margins reject exactly as in Campaign 1; nothing in the
   proposal layer can widen them (`CONFIG_LIMITS` still bounds every criterion).
4. **Campaign 2 exit criterion includes demonstrated falsification**: the campaign record must
   show ≥1 proposal refused before execution, and ≥1 executed experiment whose outcome was
   genuinely adverse-or-null *or* a documented argument for why no feasible falsifier existed
   (recorded, reviewed). A 100% acceptance streak in Campaign 2 is a trigger for review, not
   celebration (mirrors Campaign 1 audit §8.2).
5. Negative/null results are promoted to `research_memory` with the same ceremony as accepts
   (`DISCARDED`/`FAILED`/`REJECTED` entries carry the same field completeness).

---

## E. PROVENANCE / RESEARCH-RECORD MODEL

### E.1 Q10 — Lifecycle states and their evidence

State machine (append-only transitions; each transition = one ledger row with `at`, `from`,
`to`, `reason_code`, `actor`, `hashes`):

```
PROPOSED ─┬─> VALIDATION_REFUSED   (terminal; permanent record; Q9/C.5)
          └─> VALIDATED ─┬─> REJECTED_BEFORE_APPROVAL (terminal; e.g. quota/policy)
                        └─> APPROVED ─> COMPILED_TO_SPEC ─> EXECUTING ─┬─> FAILED   (runtime/gate crash)
                                                                     ├─> REJECTED_POST_EXECUTION (gates)
                                                                     ├─> ACCEPTED ─┬─> PROMOTED
                                                                     │              └─> NOT_PROMOTED (validation veto)
                                                                     └─> BLOCKED (baseline/registry)
```

Mapping to existing records (nothing replaced, nothing duplicated in meaning):

| State | Authoritative artifact (existing/new) |
|---|---|
| proposed | **new** `state/proposal_ledger.jsonl` row |
| rejected before execution | **new** ledger terminal row (`VALIDATION_REFUSED` etc.) |
| executed | existing `adapter_events.jsonl` `command_run` + `agent_state.experiments[]` |
| failed | existing `result.json status=FAILED` + `agent_state` record |
| accepted | existing `events.jsonl experiment_cycle ACCEPTED` + `result.json PROMOTE` |
| promoted | existing `versions/<v>/version.json` + `CHAMPION.json` |
| proposal linkage | compiled spec carries `provenance.proposal_id`; ledger row carries `spec_sha256` — bidirectional join |

(Q9 is answered fully in C.5; the state machine above is its structural home.)

### E.2 Q12 — Provenance fields captured exactly

`ExperimentProposal` schema (all fields mandatory unless noted):

| Question | Field |
|---|---|
| why generated | `rationale` (structured: `open_question_id`, `evidence_gap`, `generator_trigger` — one of `budget_slot|quota_class|novelty_score|human_request`) |
| evidence used | `evidence_citations[]` with per-artifact SHA-256 (re-hashed at validation) + `evidence_view_sha256` (the exact serialized view the generator saw) |
| parent version | `parent_version` (resolved fail-closed from `CHAMPION.json`, `INVALID_PARENT` refusal otherwise — reuse Campaign 1 `parent_version_for`) |
| generated design | `design.primitives[]` (ids + primitive-library version) + `design.protocol` (folds/seeds/CI method) |
| generated parameters | `parameters` (typed, range-checked; values recorded post-selection, pre-execution) |
| code/spec hash | `proposal_fingerprint` (canonical proposal) → after compile: `spec_sha256` (existing `spec_fingerprint`) + candidate `code_tree_sha256` at execution |
| validation results | `validation[]` (gate, verdict, detail, validator_version, at) |
| execution result | link: `experiment_id` + hashes of `result.json` / `evaluation.json` (written by executor as today) |
| promotion decision | link: `released_version`, `version.json.artifact_sha256`, supervisor verdict (existing `_validate_outcome` + promote records) |

Generator identity is always recorded: `generator_type ∈ {deterministic_compositional,
llm_assisted, human}` — provenance can never misstate authorship (Campaign 1's
`llm_involved` honesty rule preserved and generalized).

---

## F. ANTI-SELECTION-BIAS DESIGN

### F.1 Principle
Bias is controlled **structurally** (what selection can see and what quotas force), not by
reviewer judgment after the fact.

### F.2 Selection cannot use expected results
- The selection/scheduling function's input schema is a **closed set**:
  `{direction, proposal_class, novelty_score, evidence_gap_score, quota_state, priority,
  attempts_in_direction}`. `expected_outcome`, `predicted_delta`, `rationale.sentiment` and
  similar fields are not inputs; a unit test constructs a proposal with a spectacular
  predicted delta and asserts its ranking is unchanged (H.T8).
- Pre-registered expectations travel *with* the proposal but are ignored until adjudication
  (then compared against outcomes — a recorded, auditable calibration signal).
- Approval policy (C.4 gate 10) likewise never sees predicted outcomes.

### F.3 Portfolio quotas (BiasGovernor, `bias_policy.json` — new file, defaults proposed)
- Every campaign declares: minimum proposal-class mix, e.g. ≥35% falsification/null-class,
  ≥1 proposal in each *library-covered or primitive-covered* direction, ≤50% of budget spent
  on replications/precision re-runs (addresses Campaign 1 limitation #4), and a hard cap on
  proposals of the same design-signature per campaign (addresses limitation #1).
- Quotas are checked at *proposal acceptance* time: if accepting a proposal would violate
  them, `BIAS_QUOTA` refusal (recorded) — the governor steers generation rather than
  post-hoc weighting.
- Quota state is visible to the generator in the `EvidenceView` so it can steer itself — but
  quota satisfaction is validated independently afterward.

### F.4 Q13 — Duplicate / near-duplicate detection
1. **Exact**: canonical `proposal_fingerprint` (excludes ids/timestamps) checked against the
   proposal ledger, plus the existing `spec_fingerprint` vs `SpecRegistry` at compile time
   (two independent layers, Campaign 1 pattern).
2. **Near-duplicate**: `design_signature` = hash of the normalized tuple
   `(primitive_ids sorted, data_source, metric_family, fold_set, parameter_tolerance_buckets)`
   where numeric parameters are bucketed (e.g., n_boot {≤600, ≤1200, >1200}, bins {5,10,20}).
   A matching signature ⇒ `NEAR_DUPLICATE` unless the proposal's `delta_from_prior` field
   explicitly names what differs *and* why new information is expected — that justification is
   stored in the ledger and counts against the replication quota (F.3).
3. **Text-level**: hypothesis strings compared with `difflib.SequenceMatcher` ratio ≥0.90 vs
   all prior hypotheses ⇒ flagged as near-dup of that record (deterministic, no embeddings).

### F.5 Q14 — Never rediscovering the same experiment
- `EvidenceView.already_asked` = every prior proposal (any status) with fingerprint, signature,
  one-line outcome, and refusal codes — cumulative and permanent.
- Terminal refusals and prior outcomes are *inputs to generation*, so re-proposal must either
  change the design (new fingerprint) or is refused with `DUPLICATE`/`NEAR_DUPLICATE`
  immediately.
- Direction-level memory: `direction_stats` (existing) informs quotas; a direction that has
  produced N refusals must diversify primitive class, not retry the same signature
  (enforced by the replication cap + signature cap).
- All of this is restart-safe because it lives in append-only ledgers, not process memory
  (Campaign 1 property, preserved).

---

## G. REQUIRED FILES / CODE CHANGES (future implementation — NOT done now)

### G.1 New files (all additive)

| File | Purpose |
|---|---|
| `autonomous_agent/proposal_layer/__init__.py` | package marker |
| `autonomous_agent/proposal_layer/evidence_view.py` | allowlist `EvidenceView` builder (holdout-blind, fail-closed) |
| `autonomous_agent/proposal_layer/primitives.py` | `DesignPrimitiveLibrary` declarations (ids, ranges, docs) |
| `autonomous_agent/proposal_layer/generator.py` | deterministic compositional `ProposalGenerator` (+ optional LLM annex interface, inert by default) |
| `autonomous_agent/proposal_layer/validator.py` | `ProposalValidator` gate chain (C.4) + refusal codes |
| `autonomous_agent/proposal_layer/bias_governor.py` | quotas + selection-input schema enforcement (F.2/F.3) |
| `autonomous_agent/proposal_layer/ledger.py` | append-only `proposal_ledger.jsonl` writer/reader (atomic append, fsync, crash-safe like `_record_attempt`) |
| `autonomous_agent/proposal_layer/compiler.py` | VALIDATED+APPROVED proposal → `ExperimentSpec` (reuse `spec_recipes` templates/`parent_version_for`) |
| `autonomous_agent/state/proposal_ledger.jsonl` | the record (created at first use) |
| `autonomous_agent/proposal_layer/bias_policy.json` | campaign quota policy (defaults; versioned) |
| `autonomous_agent/PROPOSAL_SPEC.md` | human-facing spec of schema, states, refusal codes, guarantees |

### G.2 Existing files to EXTEND later (additive edits only; every Campaign 1 behavior preserved)

| File | Change | Gate impact |
|---|---|---|
| `recipe_harness.py` | `validate_experiment_config`: accept *primitive config keys* (closed schema extension); optionally add new primitive-backed metrics. `ALLOWED_*`/`CONFIG_LIMITS`/`ALLOWED_CRITERION_KEYS` **only ever tightened or extended with reviewed values, never loosened** | none weakened |
| `core.py` | supervisor planning: try proposal layer first (when enabled by a *new, separate* flag — see G.3), fall back to `RecipeSpecProvider`; capacity function extended to include proposal budgets | recipe fallback intact |
| `spec_recipes.py` | `generation_capacity` reads proposal ledger too; `build_default_provider` unchanged otherwise | budgets remain permanent |
| `research_memory.json` | new append-only `discarded_proposals` section | additive |
| tests | new suite `test_proposal_layer.py` (+ additions elsewhere) | — |

### G.3 Activation (deliberately NOT part of Phase 1)

A **separate** config flag (e.g. `allow_generated_proposals` in `autonomy_config.json`,
default `false`) must gate the proposal layer, independent of `allow_autonomous_specs`.
Changing config, starting the supervisor, or enabling anything is explicitly out of scope
until Phase-1 design review is accepted and implementation is separately authorized.

### G.4 LLM NECESSITY ASSESSMENT (explicit)

**Is an LLM necessary? No — not for Campaign 2, and not for most proposal classes.**

- The proposal classes in §D.1/D.2 (robustness probes, calibration tests, protocol analyses,
  model-class comparisons, primitive-composed feature transforms) are **mechanically
  composable**: their design space is enumerable from `DesignPrimitiveLibrary` × parameters ×
  evidence gaps. A deterministic generator with recorded seeds covers them fully, with perfect
  reproducibility, zero inference cost, and zero new safety surface. Campaign 1 itself
  demonstrates deterministic generation works end-to-end.
- Deterministic generation's honest limitation: it can only *recombine* reviewed ideas — it
  cannot articulate a genuinely novel hypothesis in natural language, notice an unorthodox
  connection between literatures, or draft a creative adversarial framing.
- **Where an LLM would genuinely help (exact insertion points):**
  1. `hypothesis_text` and `rationale` drafting — turning a primitive composition into a
     crisp, novel *research question*;
  2. novelty critique — arguing why a proposed design is/isn't redundant with prior records;
  3. falsifier brainstorming — drafting adversarial/null-class designs the deterministic
     library would not enumerate;
  4. (optionally) near-duplicate semantic judgment as a *second opinion* beside the
     deterministic fingerprint checks.
- **Constraints if/when introduced:** strictly offline-one-shot (single request → JSON
  proposal fragment); temperature 0; prompt template + model id + full response hashed into
  provenance with `generator_type: llm_assisted`; output passes the *same* validator, never
  bypassing any gate; **human approval always mandatory for LLM-assisted proposals**; the LLM
  never supplies numbers, thresholds, or criteria (those come from `CONFIG_LIMITS`/recipes);
  executed only in the planning phase, with no network available to it beyond a reviewed
  retrieval step, and never inside the sandboxed executor.
- **Current factual state:** this project has **no LLM provider** (Campaign 1 audit §3.1;
  `llm_involved: false` is structural). Any future doc must keep claiming only what is true —
  the deterministic annex ships first; the LLM annex is an optional, separately-flagged,
  separately-reviewed upgrade.

---

## H. REQUIRED TESTS

| # | Test | Property guarded |
|---|---|---|
| T1 | Determinism: same `(view, seed, versions)` ⇒ byte-identical proposals | reproducibility (Q18) |
| T2 | EvidenceView excludes holdout: builder run against a fixture tree containing `prospective/` never yields its bytes/paths; stripped-stamp set when a source embeds them | Q11 / C.6 |
| T3 | Citation re-hash mismatch ⇒ `UNRECALLED_EVIDENCE` refusal | Q5 grounding |
| T4 | Schema: unknown/extra field, wrong type, missing falsification rule ⇒ refusal (`SCHEMA`, `NOT_FALSIFIABLE`) | Q8 |
| T5 | Surface: design referencing any path outside `autonomous_agent/experiments` ⇒ `SURFACE_ESCAPE`; compiled spec files all pass `_require_allowed_path` | Q7 |
| T6 | Duplicate: exact fingerprint and bucketed-signature near-dup refusals; `delta_from_prior` justification path recorded | Q13/Q14 |
| T7 | Rediscovery: replaying Campaign 1's eight attempts through the new validator ⇒ all `DUPLICATE` | Q14 regression |
| T8 | Selection blindness: perturbing `expected_outcome` fields does not change scheduling order (input-schema closed set) | Q15 / F.2 |
| T9 | Quota steering: generator under quota pressure produces falsification-class proposals; violating acceptance ⇒ `BIAS_QUOTA` | Q15 / F.3 |
| T10 | State machine: illegal transitions refused; every terminal state persistable and reloadable; ledger append-only (rewrite attempt raises) | Q9/Q10 |
| T11 | Static: no `eval`/`exec`/`pickle`/`joblib`/dynamic-import in proposal layer (AST scan) | Q6 |
| T12 | Boundary: proposal-layer modules import nothing from executor run path; executor imports nothing from generator | Q17/K |
| T13 | Ledger crash-safety: kill mid-append ⇒ previous content intact, no partial row (mirrors `_record_attempt` fsync+replace tests) | durability |
| T14 | Generator isolation: generator process/function performs zero writes outside its ledger (monkeypatched `open`/`Path.write*` audit) | C.1/C.3 |
| T15 | Budget permanence: spent proposal budgets refuse forever across restart | Q8/B |
| T16 | Compiled spec passes the *existing* `validate()` + `SpecRegistry` and runs the full Campaign 1 unit suite unchanged (no regression) | inheritance of all gates |
| T17 | `INVALID_PARENT` fail-closed reuse: malformed `CHAMPION.json` ⇒ proposal refuses, never guesses | provenance |
| T18 | LLM annex (if built): temperature≠0 / missing prompt-hash / missing human-approval field ⇒ refusal; recorded response replays byte-identically | Q18 / G.4 |

Full existing suites (117 agent + 22 study) must stay green after any implementation.

---

## I. CAMPAIGN 2 EXECUTION PLAN (before any continuous operation)

**Preconditions (all required):** Phase-1 design accepted; implementation completed with H.T1–T18
green; human review of `DesignPrimitiveLibrary` + `bias_policy.json`; separate activation flag
reviewed (still default-off); Campaign 1 audit untouched.

| Stage | What runs | Scope | Exit criteria |
|---|---|---|---|
| 0. Shadow generation | Proposal generator + validator only (no executor) | 20–40 proposals over ~1 week of offline runs | Quotas met; ≥1 refusal of each major code; all citations resolve; human reviewer marks ≥80% designs "reasonable or better" |
| 1. Curated execution | Human approves a small batch (e.g. 6–10 proposals, mixed classes: ≥1 falsification, ≥1 new primitive composition, ≤1 replication) executed via the *existing* supervisor path with small per-direction budgets | full gates, holdout sealed | Every outcome recorded (accept/reject/fail); **≥1 adverse-or-null outcome or documented falsifier gap**; zero safety events |
| 2. Adversarial review | Independent read-only audit of Campaign 2 (mirror of Campaign 1 audit format) | all evidence | Bias/validity verdicts written; no unexplained acceptance streak |
| 3. Primitive expansion (optional) | 1–3 new reviewed primitives (e.g., purge-sensitivity probe, reliability-curve metric) added through normal code review | tests first | Study suite + proposal suite green |
| 4. Bounded autonomous operation | Only after Stages 0–3 pass: proposal+recipe hybrid under fixed budgets, per-campaign quotas, periodic human audit triggers (auto-pause if acceptance streak ≥ N or falsification share < quota) | capped budget | Continuous operation considered only at this point |

**Campaign 2 must NOT:** open the holdout, raise any budget beyond declared caps, auto-approve
LLM-assisted proposals, weaken any gate, or delete any record.

---

## J. RISKS AND FAILURE MODES

| Risk | Failure mode | Mitigation |
|---|---|---|
| Quota gaming | Generator produces nominally falsification-class proposals that are really soft | Class definitions mechanical (primitive-based) + human review in Stage 0/1 + auditor spot-checks |
| Primitive library ossification | "New" layer reduces to recipe-library v2 | Stage-0 novelty metric: fraction of proposals with unseen design signatures; explicit primitive-expansion track (Stage 3) |
| Evidence-view leakage | Holdout metadata leaks via an allowlisted source | Fail-closed builder + strip stamp + independent string scan (C.6, H.T2) |
| Ledger poisoning | Generator spams proposals to fill budget with noise | Per-campaign proposal caps, signature caps, fsync'd append-only ledger, quota steering, validator first |
| Duplicate churn across restarts | Forgetting refusals | Ledger-derived `already_asked` is authoritative; process memory never trusted (H.T7/T13) |
| Perverse incentives in scoring | Future edit sneaks outcome-proxies into selection inputs | Closed input schema + golden test (H.T8) + audit of scoring diffs in code review checklist |
| Over-validation paralysis | Everything refused; campaign idles | Refusal telemetry in `EvidenceView`; staged quotas; Stage-0 dry-run tuning of thresholds before any execution |
| Scope creep toward free code | Pressure to "just allow generated Python" | Explicit non-goal (C.2); requires separate design + static-analysis gate + human review |
| LLM provenance dilution | Records implying LLM authored what it didn't (or vice versa) | `generator_type` field mandatory; response hashes; honesty rule generalized from Campaign 1 |
| Two-ledger divergence | Proposal ledger and experiment records disagree | Bidirectional `proposal_id ↔ spec_sha256` links validated in CI (H.T10) + audit reconciliation step |
| Config confusion | Users assume flag changes are part of Phase 1 | G.3: separate flag, default off, nothing touched until authorized |

---

## K. EXACT BOUNDARY: "PROPOSAL GENERATION" vs "EXPERIMENT EXECUTION"

**Proposal generation** (new layer — inert):
- Input: serialized `EvidenceView` bytes + seed + versions. No filesystem root, no network, no
  subprocess, no model deserialization, no holdout handle.
- Output: append-only rows in `state/proposal_ledger.jsonl` and nothing else.
- Actions: compose declarative designs from reviewed primitives; validate; quota-check; refuse
  permanently; mark `APPROVED` (human or policy).
- Cannot: write any candidate file, create workspaces, spawn processes, touch
  `CHAMPION.json`/`versions/`/ledgers of execution, modify gates or config, influence
  *post-hoc* adjudication.

**Experiment execution** (existing system — unchanged):
- Input: an `ExperimentSpec` that exists **only** after `COMPILED_TO_SPEC` from an
  `APPROVED` proposal (or a Campaign 1 recipe, still available).
- Entry: the single existing seam — `build_experiment_runner(..., spec_provider=...)` →
  `ExperimentAdapter.run_experiment` with `spec.validate()`, `SpecRegistry`, baseline gate,
  original-tree fingerprint, isolated workspace, scrubbed env, network guard, six gates,
  `decision_criteria_pass`, destroy-on-non-accept, `_validate_outcome` revalidation,
  `VersionManager.promote`.
- Cannot: generate new designs, see proposal rankings/quotas, or alter the ledger.

**The crossing point is one function call with one contract:** `compiler.py` produces an
`ExperimentSpec` (already carrying `provenance.proposal_id`) and hands it to the existing
provider interface. Everything before that line is generation; everything after is execution
under Campaign 1 rules, byte-for-byte the same gates the Campaign 1 audit verified.

```
[EvidenceView] → ProposalGenerator → proposal_ledger (PROPOSED)
                     ↓ ProposalValidator + BiasGovernor
        VALIDATION_REFUSED (terminal, recorded)      VALIDATED → APPROVED
                                                            ↓ compiler.py
                                              ExperimentSpec (proposal_id + spec_sha256)
                                                            ↓ EXISTING, UNCHANGED
                        ExperimentAdapter → gates → result → supervisor → promote/record
```

---

## Read-Only Verification (performed after writing this design)

Recorded in the chat deliverable accompanying this document: Campaign 1 evidence hashes,
holdout absence, config hash, supervisor state hashes, experiment/attempt counts, and audit-file
integrity — all checked without modifying anything.

