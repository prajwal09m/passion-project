# Milestone 9 — Audit of M8 State (no paid API activity)

Sources: M5–M8 results/validation/challenge docs, `live-dbf6a5b3fbff`
artifacts + `live.sqlite3`, `backend/{engine,tools_registry}.py`,
`backend/causal/*`, `backend/research/*`, `backend/model_adapters/*`,
`backend/eval/m8_challenge.py`, `tests/test_m8_*.py`, dashboard
`CausalPanel.tsx` + `/causal` endpoint. Implementation verified, not
assumed: every claim below was checked against code and records.

## 1. Existing strengths (verified real)

- **Atomic budget management** (`live/governor.py` + driver/resume/loop
  wiring): shared Budget, reserve-before-dispatch, crash-conservative
  reconcile, 9 adversarial tests, live exact-stop 6/6. Genuinely solved.
- **Durable accounting**: `to_state` + `reconcile` + ledger in manifest;
  live run stopped exactly at cap with recorded rationale.
- **Structured reporting**: `m8-v1` contract, fresh-context repair,
  labeled deterministic fallback — live-proven to degrade gracefully
  (both M8 summaries absent → fallback, no crash, no fabrication).
- **Diagnostic coverage** (`causal/coverage.py` + planning boost +
  inapplicable exclusion): missing measurements tracked and selected
  against; offline discovery on region-W/district-C closed.
- **Evidence-linked updates**: linker rules + `update_with_evidence`
  corroboration bar held live (5 revisions, zero single-evidence
  promotions).
- **Challenge infrastructure**: 12 scenarios, dimension scoring,
  leak audit green, honest fractional coverage.
- **Adapters**: 9-framework registry with honest capability probes +
  `/api/model-frameworks` (black_box/sklearn/xgboost/lightgbm/catboost/
  pytorch/tensorflow/huggingface/api). Mostly declarations + probes —
  diagnostic depth through adapters is thin (see §3).
- **Research pipeline skeleton**: `research/lab.py` 11-stage driver,
  `recon.py` artifact inspection, `experiments.py` heuristic design +
  isolated execution, `verification.py`, triage hypothesis generator.
  Real but shallow: triage uses family templates, invention is
  arg-filling, no agenda, no confounder reasoning, no memory.

## 2. M8 limitations — symptoms vs root causes

1. **Over-attribution (mention ⇒ support). Root cause: family matching
   is substring-based** (`_is_subgroup`, `_is_bias` fire on any mention).
   Live H3 explicitly denying district failure still got
   supports-subgroup. Deeper limitation: the linker has no concept of
   *relationship* — only direction. Fix requires an attribution
   redesign, not threshold tuning.
2. **Absent live summaries. Root cause is two-sided**: model
   non-compliance (no block emitted, twice) + contract that lives only
   in prompts the model can ignore. Fallback worked; genuine fix needs
   the agenda/report state to make the summary names, ids, and numbers
   unavoidable (ground the block in recorded artifacts), plus keep the
   fallback.
3. **Schema-vs-district confounding unresolved. Root cause: no
   confounder representation.** Nothing can state "one observation,
   two mechanisms, one shared cause" or design the experiment that
   separates them. New module required.
4. **Incomplete discovery. Root cause: selection is tool-centric, not
   question-centric.** There is no research question, no agenda, no
   discriminating-experiment record — the loop picks good tools but
   cannot say what question it is answering or what would settle it.
5. **n=1 live. Root cause of the generalization gap is methodological**,
   not just sample size: offline harnesses use scripted policies, so
   neither offline nor live evidence covers autonomous question
   generation or invention. M9 evaluation must exercise those.

## 3. Additional gaps found on inspection

- `research/lab.py` triage generates from task-type templates; questions
  are never generated, prioritized, or revised; agenda does not exist.
- No experiment specification object (designs are ephemeral dicts);
  no discrimination record (what outcome favors which hypothesis).
- No cross-run memory: every investigation starts from zero; duplicate
  work across runs is undetectable.
- Adapter capability reporting exists but no diagnostic actually
  dispatches through adapters; framework-independence is declared,
  not demonstrated.
- Dashboard shows loop artifacts, not a research process: no agenda,
  no question graph, no experiment specs, no knowledge reuse.

## 4. Extend / redesign / keep

- **Keep unchanged**: governor, reconcile, report contract + fallback,
  update_with_evidence corroboration bar, challenge harness shapes,
  budget plumbing in driver/resume/loop.
- **Extend**: linker (attribution relationships), selection/planning
  (agenda-driven), recon (knowledge buckets), experiments (spec
  objects), adapters (dispatch proof), challenge (new families/dims),
  dashboard panels, lab driver (agenda loop).
- **Redesign**: evidence attribution (new `attribution.py` semantics);
  hypothesis competition → confounder-aware (new `confounders.py`).
- **New**: research agenda, experiment invention specs, memory store +
  table, M9 challenge scenarios + fixture, flagship demo.
