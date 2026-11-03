# M22 P0 Evidence-Floor Audit — Does `ran` Mean Useful?

Read-only. No code, tests, or artifacts modified; no live calls. All
claims traced to source lines and the 656-test offline suite.

## 1. Exact completion call path

```
driver.run_live_investigation (live/driver.py:130-294)
  └─ loop: budget.check → stopping() → run_meta_turn (loop.py:443)
       ├─ zero-action recovery (loop.py:~751-800, prose-only, 1/turn)
       ├─ repair + consistency gates (loop.py:1005-1090)
       └─ decision: total_inaction / progress / incomplete (loop.py:~1195)
  ├─ evidence floor (driver.py:235-248): break only if summary valid
  │   AND ≥1 Action(status="ran"); else continue (stall rule bounds)
  ├─ maybe_verify → resolve.contract (research/resolve.py:contract)
  ├─ build_report → finalize → adapter.meta_report_to_eval
  └─ end-gate (driver.py:~291-302): zero ran → "inconclusive",
     else "completed" → finalize_run manifest
resume.py mirrors both gates (:256-269, :~293-303).
```

## 2. What `ran` actually means (source locations)

- `tools_registry.execute` (:607-647): status `"ran"` is recorded iff
  the tool function **returns without raising** (`:641-645`). A
  payload of `{"ok": False}` returned (not raised) would also record
  `"ran"` — though no current `ml_tools.py` function does this (all
  either raise → `record_failed_call`, status `"failed"` — or return
  `{"ok": True, ...}`).
- Usefulness lives elsewhere: `causal/linker.py` attaches
  supports/contradicts refs by content heuristics; `resolve.contract`
  counts only *moving* refs (`evidence_gathered`); verification
  eligibility needs ≥1 moving support + zero contradicts.
- The M22 floor and end-gate count `Action.status == "ran"` only.
  **They cannot see usefulness.**

## 3. Scenario findings

1. **Successful exec, no useful evidence** (e.g. only
   `artifact_summary` runs): `ran`=1 → floor breaks on a valid
   summary → verify skipped → contract `unresolved` → end-gate passes
   (ran>0) → **`completed`**. Run honest (limitations note,
   discovery ≈ 0) but status is a successful completion.
2. **Error/invalid measurement**: raises → `"failed"` → not counted.
   Floor holds; covered by M22 V5 + M18 failure suites.
3. **Unrelated evidence**: `ran` + no links → same as (1):
   **`completed` + `unresolved`**. Linker-level covered
   (`test_m8_linker`); end-to-end completion-with-unrelated is not
   pinned by any test — **gap, test proposed below**.
4. **Useful evidence**: supported path intact (M19 scenario A, M22 V6).
5. **Contradictory evidence**: `unresolved` + preserved contradiction
   (M19 B, M22 fixtures). Honest completion.
6. **Multiple actions, none supporting**: M22 stall test pins
   honest stall-stop; with ≥1 ran it completes as `unresolved`.
   Correct per current contract definitions.
7. **Valid summary after each**: repair/consistency/provenance
   behavior unchanged and green (M20 53/53, M21 27/27, V9/V10).

## 4. Concrete bypass (strict sense)

An investigation with ≥1 successfully executed but diagnostically
worthless action + a valid summary receives run status `completed`.
The M22 floor answers "was anything executed?" — not "was anything
learned?". The primary M21 mechanism (ZERO evidence → completed) is
closed; the quality-blindness above remains. Mitigations already in
place (not gates): contract stays `unresolved`, limitations disclose
unused/failed tools, scorecard punishes discovery, consistency gates
still reject invented numbers/verification/confirmation on repair.

## 5. Question answers

- `ran` = successfully executed, **not** diagnostically useful.
- A valid summary **cannot** bypass the resolution contract
  (conclusions built in `verify.py:68-255`, never from model text;
  `confirmed` requires the contract).
- `completed` with no *useful* evidence: **yes, possible** (§3.1/§3.3).
- The end-gate evaluates **action counts**, not evidence quality.
- Manifest / run status / contract are **consistent by design**:
  status tracks process completion, the contract tracks scientific
  outcome; `completed` + `unresolved` is legal and disclosed.
- Resumed runs have **identical** protections (mirrored gates,
  verified lines above) and the identical quality-blindness.

## 6. Test coverage per condition

Covered: zero-evidence completion (V2, persistent-silence, M21
regressions), failed-action exclusion (V5), repair consistency (M20),
fallback (V10/M21), stall bound (M22 stall test), decline (V8/M19).
**Not covered**: end-to-end completed-with-unrelated-evidence.
Proposed (not written): a driver test where the model runs only
`artifact_summary` + a valid summary, asserting status `completed`
AND contract `unresolved` AND limitations disclosure — pinning the
honest-but-successful outcome so any future gating change is
deliberate.

## 7. Classification: PARTIAL PASS

The P0 mandate as implemented (no zero-evidence completion) holds.
The follow-up's harder question exposes a real, bounded gap:
execution is gated, usefulness is merely reported. No silent
corruption exists anywhere on the path — every downstream consumer
tells the truth — but the run status alone overstates such runs.

## 8. Recommended minimal changes (not implemented)

- Option A (visibility, no gating change): add
  `useful_evidence: bool` (any moving ref) to the manifest budget/
  provenance block. Zero regression risk; dashboards can distinguish
  "completed with evidence" from "completed with measurements".
- Option B (stronger gate): require ≥1 moving evidence ref — not
  just ≥1 ran — for the valid-summary break and `completed` status.
  Trade-off: genuinely uninformative-but-correct diagnostic runs
  would flip to `inconclusive`, changing M8-pinned behavior; needs
  explicit authorization and regression review.
- Recommended: A now, B only with authorization. Do not touch
  scorer weights, contracts, or sealed truth either way.
