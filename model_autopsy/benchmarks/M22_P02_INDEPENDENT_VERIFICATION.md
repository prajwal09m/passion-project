# M22 P0.2 Independent Verification — PASS

Stage 2 of the post-M22 program. Production code untouched by this
stage (read-only inspection + test execution). No live calls.

## Independent source inspection

- Origin: `has_useful_evidence` (`causal/linker.py`) reads only
  recorded `Hypothesis.evidence_refs` + `Action.status` — no model
  text, no prompt content, no summary fields. A model cannot set,
  clear, or influence it except by causing real tool executions that
  the linker independently judges.
- Moving refs: only supports/contradicts (linker + `update_with_
  evidence` enforce the vocabulary; `artifact_summary` has no `_rules`
  branch and can never link).
- Staleness: refs are re-validated against live `Action.status ==
  "ran"` at read time; link-time `action_status` snapshots are not
  trusted.
- Reach: adapter provenance (guarded, advisory-only, assembly-safe) +
  manifest top-level key (None when DB unavailable). Both driver and
  resume call `finalize_run`, so resumed runs restore the identical
  value from durable state (proven by the restore test).
- Legacy: old manifests lack the key (`.get` → None); failure-path
  manifests record None without crashing; no schema validation to
  break.

## Test commands and exact results

- Full suite: `py -m pytest model_autopsy/tests -q -p no:cacheprovider`
  → **662 passed, 0 failed** (~219s). Includes M19 35/35, M20 53/53,
  M21 27/27, M22 11 + 10 validation, P0.1 6, adapter 25, M9/M10/API.
- Stage-2 battery (P0.1 + M19/M20/M21/M22 + adapter + budget-driver +
  API): **185 passed, 0 failed**.
- `tsc --noEmit`: exit 0. `npm run build`: succeeds (pre-existing
  chunk-size warning only).
- Separation scan: no sealed/ground-truth refs in touched modules.
  Credential scan: only pre-existing `key_configured` booleans.
  Network scan: no httpx/requests/urlopen in new code; all provider
  contact via monkeypatched fakes.
- Frozen artifacts: `git diff` clean on `live_runs`, M19–M21 docs,
  sealed, scorers; Demand Zone AI untouched (no modifications outside
  the M22/M22-P0.1 scope).

## Scenario validation (§D table)

Zero-executed → `inconclusive` (M22 persistent-silence test). Failed
action → excluded (V5 + helper unit). Baseline-only → `ran` but
`useful_evidence=false`, `completed` + `unresolved` preserved (P0.1
driver test). Unrelated → false (artifact_summary/mentions units).
Genuine moving → true in manifest AND provenance (P0.1 driver test).
Valid summary without useful evidence → existing completion semantics
preserved, contract `unresolved` (P0.1 baseline test). Contradictory
→ no unsupported confirmation (M19 B + consistency gates, green).
Resumed → signal recomputed from durable DB, equality-tested.

## Remaining limitations

Binary per-run signal (any weak link flips True — read with the
contract); linker heuristics define "moving"; live-model behavior
unverified by mandate.

## Classification: PASS

Stage 3 live investigation is authorized to proceed under its $0.65
envelope. No unresolved critical regression.
