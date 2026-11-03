# M22 P0.1 Evidence Visibility — Implementation Report (Option A Only)

No live calls. Completion semantics unchanged by construction.

## Exact files modified

- `backend/causal/linker.py` — added `MOVING_RELATIONS` and
  `has_useful_evidence(session, inv) -> bool`: True iff any
  supports/contradicts ref on this investigation's hypotheses cites
  an action that `ran` in this investigation. Pure read; no writes.
- `backend/live/adapter.py` — `report_provenance["useful_evidence"]`
  (None only if the check itself errors; never breaks assembly).
- `backend/live/recorder.py` — manifest top-level `"useful_evidence"`
  (None when DB unavailable, e.g. failure path without a session).
- `tests/test_m22_p01.py` (NEW, 6 tests). No other files touched.
  Option B explicitly NOT implemented: `ran` floor, resolution
  contracts, confirmation rules, scorer weights, sealed truth, M8
  behavior all byte-identical in logic.

## Field definition and derivation

Moving refs come only from the authoritative linker
(`link_tool_result` only links `ran` actions; `update_with_evidence`
/ `link_evidence` restrict relations to supports/contradicts plus
audited non-moving relations). The helper re-verifies each cited
action's current `ran` status in the same investigation, so failed
actions cited as supports, non-moving relations (`mentions`, etc.),
unlinked baseline artifacts (`artifact_summary` has no `_rules`
branch and can never link), and other investigations' refs all yield
False. No model text is read.

## Data-flow changes

None to existing flows: two additive, read-only taps (adapter
provenance at finalization; manifest at `finalize_run`, recomputed
from durable state so resumed runs restore it identically — proven by
the restore test reading back `sandbox_final.db`).

## Tests added (6)

Helper: moving/failed/non-moving/other-investigation cases;
driver baseline-only (`artifact_summary` only → manifest +
provenance False, status still `completed`, contract `unresolved`,
limitations disclose unused diagnostics); driver with real evidence
(both True); restore-from-persisted-DB equality; backward compat
(M19 manifest lacks the key; error-path manifest records None).

## Compatibility

Additive keys only; old manifests parse unchanged (`.get` → None);
failure-path manifests record None rather than crashing; scorer,
contracts, and frozen artifacts untouched.

## Known limitations

The signal is binary per run (any moving ref), not per-claim; a
single weak link flips it True while the contract may stay
`unresolved` — the two fields must be read together. Linker
heuristics define "moving"; mislinked content would propagate (no
such case observed; attribution is M9-pinned).
