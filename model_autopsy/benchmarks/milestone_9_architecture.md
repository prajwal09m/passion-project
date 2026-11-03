# Milestone 9 — Architecture Design

## Design principle

M8 made the loop reliable; M9 gives it a mind. Every new structure is
question-centric: research questions own hypotheses, hypotheses own
discriminating experiments, experiments own interpretation rules, and
all of it is durable, provenance-linked, and visible.

## New modules (all additive)

- `causal/attribution.py` — relationship classifier. Input: rule hit
  (family, direction, measured detail) + hypothesis text + primary
  family. Output: one of `supports | contradicts | relevant_to |
  mentions | neutral | insufficient | uncertain`, with justification
  and `moves_belief` flag. Only supports/contradicts with a direct
  mechanism bearing move confidence/status; the rest are recorded as
  visible, non-moving evidence refs.
- `causal/confounders.py` — shared-evidence analysis. Flags when one
  action supports 2+ competing hypotheses (common-cause candidate),
  checklists artifact-grounded confounder candidates (composition,
  collection, temporal, preprocessing, metric), and proposes the
  discriminating measurement for the unresolved M8 schema-vs-district
  case without hardcoding its answer.
- `research/agenda.py` — ResearchQuestion generation from recon facts
  + coverage gaps + families (project-grounded: names real columns,
  groups, horizons), qualitative prioritization with stated reasons,
  durable agenda in `inv.config["research_agenda"]` + events, revision
  on new evidence / weakened hypotheses / emerging confounders.
- `research/invention.py` — ExperimentSpec objects: question ids,
  hypotheses distinguished, expected outcome under each, tool + args,
  validation (columns exist, not duplicate, budget fits), execution via
  `engine.run_tool`, interpretation rules applied post-hoc, provenance
  recorded. Novelty = new compositions from artifact facts (group
  choices, thresholds, feature subsets, horizons), never new black-box
  tools.
- `research/memory.py` + `MemoryEntry` table — reusable methodology,
  observations, outcomes, failures, with source run/project/experiment
  provenance; retrieval by family/mechanism with similarity guard;
  explicit non-transfer rules across unrelated projects.
- `research/recon_knowledge.py` — partitions recon output into
  observed / inferred / missing / assumptions; never upgrades an
  inference to a fact.

## Extended modules

- `linker.py`: emits attribution via `attribution.py`; `relevant_to`
  refs stored, never counted; counts in `update_with_evidence` paths
  ignore non-moving relations (verified: only supports/contradicts
  counted).
- `engine.link_evidence`: accepts `relevant_to` (stored, no status or
  confidence change); validation of the other relations unchanged.
- `selection/planning.py`: agenda-aware brief (current question, what
  would settle it); unchanged scoring otherwise.
- `lab.py`: agenda loop stage (question → competing explanations →
  discriminating spec → execute → attribute → revise agenda) using the
  same offline deterministic policy as the challenge harness.
- `eval/m9_challenge.py`: new fixture family (neural image-tag
  classifier CSV: subgroup failure + miscalibration + prevalence
  confounder), dev/held-out split, new dims (understanding, invention,
  confounder handling, attribution precision), anti-overfitting audit.
- Dashboard: agenda, relationship-typed graph, experiment lab,
  knowledge explorer, confounder + attribution sections in report view.

## Unchanged

Governor/resume/loop budget plumbing, report contract + fallback,
corroboration thresholds, M4/M6/M7/M8 scorers and artifacts, API
compat (only additive keys/endpoints).

## Interfaces

- `attribution.classify(hypothesis, rule_hit) -> dict`
- `confounders.analyze(hypotheses, actions, recon_facts) -> dict`
- `agenda.generate(recon_knowledge, coverage, budget) -> list[Question]`
- `agenda.prioritize(questions, state) -> ranked`
- `invention.propose(question, hypotheses, artifact_facts, ran) -> Spec`
- `invention.validate(spec, artifact_facts, ran, budget) -> verdict`
- `memory.store(entry) / memory.retrieve(family, mechanism, k)`
