# Evidence Provenance Specification (Milestone 3, research extension)

Base provenance (unchanged): every tool call is an `Action` row
(seq, args, result/error, iteration); every state change is an
append-only `Event`; findings link `evidence_action_id`; final reports
assemble deterministically from recorded rows only.

## Research-layer additions

| Record | Location | Contents |
|---|---|---|
| Stage outputs | `research.stages.{11 names}` + `tool_result` events | inputs summarized, outputs, key lists |
| Hypothesis cards | `research.hypotheses[]` + `hypothesis` events | full card + transition history with notes |
| Experiments | `research_runs/{inv}/{exp}/` + report `experiments[]` | plan snapshot, seed, elapsed, result numbers, `original_modified: false` |
| Reviews | `research.reviews[]` + `hypothesis` events | verdict, per-check pass/fail, preserved disagreement |
| Candidate taxonomy | `research.taxonomy` + `finding` events | `base[]` + `novel[]` (status `candidate` only) |
| Forensic report | `research.report` + `report` event | confirmed/rejected/inconclusive/open, verification, limits |

## Rules

1. `supported`/`rejected` require evidence references (enforced).
2. Summaries carry references (ids), never blobs; full outputs stay in
   durable records addressable by id.
3. Disagreements preserved, never auto-resolved.
4. Novel mechanisms enter taxonomy as `candidate`, never `confirmed`,
   without replicated evidence + review.
5. `original_modified: false` on every isolated run; no lab path can
   rewrite project artifacts.

## Verification

`test_research_api_endpoints` asserts stage/report persistence across
requests; challenge runs assert evidence-linked confirmations; the
deepcopy persistence fix is covered by repeated-propose assertions.
